"""harbor_bridge — parse harbor trial results → state/dev_metrics.json.

VSM-024: harbor writes trial outputs to trials/<task>__<id>/ (result.json +
agent/trajectory.json + verifier/reward.txt). This bridge reads a trial dir,
converts it into the task_result dict shape that metrics.record() expects (same
shape as runner._base_result), and records it into dev_metrics.json via the
existing metrics.py writer. The dev_metrics.json format is unchanged — only the
data source differs (harbor trial dir instead of the old agent_phase/grader).

This is the ONLY coupling between harbor outputs and our A(t) metric format.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from .config import EvalConfig
from . import metrics


def find_latest_trial(trials_dir: Path, task_id: str) -> Path | None:
    """Find the most recent trial dir for a task_id.

    Harbor names trials `<task_id>__<short-id>`; multiple runs accumulate.
    Returns the newest by mtime, or None if no match.
    """
    candidates = sorted(
        (p for p in trials_dir.glob(f"{task_id}__*") if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def parse_trial(trial_dir: Path) -> dict:
    """Parse a harbor trial dir → task_result dict (metrics.record format).

    Fields mirror runner._base_result + the extras set in run_single, so the
    downstream summary/by_category/by_difficulty aggregation works identically.
    """
    result_json = _read_json(trial_dir / "result.json") or {}
    trajectory = _read_json(trial_dir / "agent" / "trajectory.json") or {}
    reward_txt = _read_text(trial_dir / "verifier" / "reward.txt")

    # Harbor reward: 1.0 = pass, 0.0 = fail. reward.txt may be absent if the
    # verifier didn't run (e.g. infra error/timeout before verification).
    reward_value = _parse_reward(reward_txt, result_json)
    passed = reward_value >= 1.0

    task_id = result_json.get("task_name") or trial_dir.name.split("__")[0]

    # Trace length: count ATIF steps (agent + tool-call granularity). trajectory
    # may be absent if the adapter failed before writing it.
    trace_len = 0
    if trajectory and isinstance(trajectory, dict):
        steps = trajectory.get("steps", [])
        trace_len = len(steps)

    # Timing: harbor records started_at/finished_at (ISO 8601 UTC) in result.json.
    agent_duration_sec = _compute_duration(result_json)

    # Category/difficulty: harbor's task config doesn't carry TB metadata, so we
    # leave them as "unknown" here — the caller (harbor_run) enriches from the
    # loader's TaskMeta (task.toml) before calling metrics.record.
    task_result = {
        "task_id": task_id,
        "status": "passed" if passed else "failed",
        "passed": passed,
        "category": "unknown",
        "difficulty": "unknown",
        "agent_duration_sec": round(agent_duration_sec, 1),
        "trace_len": trace_len,
        "failure_obs_count": 0,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "error": None,
        "agent_exit_code": _exec_return_code(result_json),
        "timed_out": False,
    }

    # Stash harbor-specific fields (adapter metadata, terminated_by) for richer
    # analysis; metrics.record ignores unknown keys (upsert only reads known ones).
    # Guard against missing/partial result.json (timeout/infra error mid-trial).
    agent_result = result_json.get("agent_result") or {}
    agent_meta = agent_result.get("metadata") or {} if isinstance(agent_result, dict) else {}
    # If the trial errored (exception_info present), surface it as an error status.
    exception_info = result_json.get("exception_info") or {}
    if exception_info and not passed:
        task_result["status"] = "error"
        task_result["passed"] = False
        task_result["error"] = f"{exception_info.get('type', 'unknown')}: {exception_info.get('message', '')}"
    task_result["harbor"] = {
        "trial_name": result_json.get("trial_name", trial_dir.name),
        "terminated_by": agent_meta.get("terminated_by"),
        "verdict": agent_meta.get("verdict"),
        "attempts": agent_meta.get("total_attempts"),
        "reward": reward_value,
        # VSM-037: strict attribution verdict (detects false-positive PASS from
        # overlay-collision). Added alongside TB reward (ground truth) — does NOT
        # overwrite reward. strict_reward=1.0 only for genuine_pass (product
        # actually worked); 0.0 for false_positive (overlay masked) / fail / unknown.
        "strict_verdict": _strict_verdict(trial_dir),
    }
    task_result["harbor"]["strict_reward"] = (
        1.0 if task_result["harbor"]["strict_verdict"] == "genuine_pass" else 0.0
    )
    return task_result


def record_trial(config: EvalConfig, task_result: dict) -> dict:
    """Record a parsed trial result into dev_metrics.json (idempotent upsert).

    Thin wrapper over metrics.record so category/difficulty can be enriched by
    the caller before this call (harbor_run enriches from task.toml).
    """
    return metrics.record(config, task_result)


# ── helpers ──

def _strict_verdict(trial_dir: Path) -> str:
    """VSM-037: strict attribution verdict via true_verifier (post-trial).

    Lazy-imports scripts/true_verifier.py (flat module, like collect_metrics).
    Returns verdict string (genuine_pass/false_positive/fail/unknown). On any
    error → 'unknown' (non-fatal: true_verifier is observability, not a blocker).
    """
    try:
        import sys as _sys
        _scripts = str(Path(__file__).resolve().parent.parent / "scripts")
        if _scripts not in _sys.path:
            _sys.path.insert(0, _scripts)
        from true_verifier import verify_trial
        v = verify_trial(Path(trial_dir))
        return v.get("strict_verdict", "unknown")
    except Exception:
        return "unknown"


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _parse_reward(reward_txt: str, result_json: dict | None) -> float:
    """Extract reward as float. Prefer reward.txt (verifier output), fall back
    to result.json.verifier_result.rewards.reward, default 0.0 (fail).
    """
    if reward_txt:
        try:
            return float(reward_txt)
        except ValueError:
            pass
    if result_json:
        rewards = (result_json.get("verifier_result") or {}).get("rewards") or {}
        try:
            return float(rewards.get("reward", 0.0))
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _compute_duration(result_json: dict | None) -> float:
    """Seconds between agent_execution.started_at and finished_at, else 0.0."""
    if not result_json:
        return 0.0
    agent_exec = result_json.get("agent_execution") or {}
    started = agent_exec.get("started_at")
    finished = agent_exec.get("finished_at")
    if not started or not finished:
        return 0.0
    try:
        from datetime import datetime as _dt
        s = _dt.fromisoformat(started.replace("Z", "+00:00"))
        f = _dt.fromisoformat(finished.replace("Z", "+00:00"))
        return max(0.0, (f - s).total_seconds())
    except (ValueError, TypeError):
        return 0.0


def _exec_return_code(result_json: dict | None) -> int:
    """Best-effort agent exit code. Harbor doesn't always expose it directly;
    exception_info presence implies non-zero. Defaults to 0."""
    if not result_json:
        return 0
    if result_json.get("exception_info"):
        return 1
    return 0


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)
