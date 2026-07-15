"""harbor_run — CLI wrapper: resolve paths, run a harbor trial, record the result.

VSM-024: entry point for harbor-based eval runs. The cwd contains a space
("Opensiro Collections") which harbor/docker bind-mounts handle poorly, so this
script generates a resolved config (absolute paths) in /tmp and invokes harbor
trial start with it. After the trial, harbor_bridge parses the output into
dev_metrics.json via the existing metrics.py.

Usage:
    python3 -m eval.harbor_run --task jsonl-aggregator
    python3 -m eval.harbor_run --task jsonl-aggregator --keep-config  # debug

This is the eval entry point for harbor-based runs. Phase 2: runs the real
triad (goose sub-agents) inside the container; API keys are propagated via --ae
from the host goose secrets.yaml so the container never needs the secrets file.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import EvalConfig
from .loader import load_tasks
from . import harbor_bridge
from . import metrics


def _resolve_repo_root() -> Path:
    """vsmlite-tb/.. = the monorepo root (parent of this package)."""
    return Path(__file__).resolve().parent.parent.parent


# Cache for API keys read from the host goose secrets.yaml (lazily populated).
_SECRETS: dict[str, str] = {}


def _read_goose_secrets() -> list[str]:
    """Read API keys from ~/.config/goose/secrets.yaml (host) into _SECRETS.

    Returns the list of key NAMES that were found (caller uses them to build
    --ae KEY=VALUE flags). Goose 1.42 stores keys under their provider-specific
    env-var name (ZHIPU_API_KEY for zai). We never print values — only names.
    Falls back to os.environ if the secrets file is absent or unreadable.
    """
    if _SECRETS:
        return list(_SECRETS.keys())

    # Try goose secrets.yaml first (canonical source on this host).
    secrets_path = Path.home() / ".config" / "goose" / "secrets.yaml"
    found: dict[str, str] = {}
    if secrets_path.exists():
        try:
            import re
            for line in secrets_path.read_text(encoding="utf-8").splitlines():
                m = re.match(r"^([A-Z][A-Z0-9_]*_API_KEY)\s*:\s*(.+)$", line.strip())
                if m:
                    found[m.group(1)] = m.group(2).strip().strip('"').strip("'")
        except OSError:
            pass

    # Fall back to env (covers CI / other hosts without a goose secrets file).
    for key in ("ZHIPU_API_KEY", "ANTHROPIC_API_KEY", "ZAI_API_KEY"):
        val = os.environ.get(key)
        if val and key not in found:
            found[key] = val

    _SECRETS.update(found)
    return list(_SECRETS.keys())


def _generate_config(task_path: Path, trials_dir: Path, config_out: Path) -> Path:
    """Render the harbor trial config with absolute paths substituted.

    Copies the template and replaces <ABS_*> placeholders. Paths with spaces
    ("Opensiro Collections") are kept verbatim — harbor passes them to docker
    which accepts quoted bind-mount sources.
    """
    repo = _resolve_repo_root()
    template = Path(__file__).resolve().parent / "harbor_config_template.yaml"
    text = template.read_text(encoding="utf-8")
    replacements = {
        "<ABS_SRC>": str(repo / "src"),
        "<ABS_VSM>": str(repo / "vsm"),
        "<ABS_EVAL>": str(Path(__file__).resolve().parent),
        "<ABS_TASK>": str(task_path),
        "<ABS_TRIALS>": str(trials_dir),
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    config_out.write_text(text, encoding="utf-8")
    return config_out


def run_trial(task_id: str, config: EvalConfig, keep_config: bool = False) -> dict:
    """Run one harbor trial for task_id, parse it, record into dev_metrics.json.

    Returns the task_result dict that was recorded.
    """
    trials_dir = config.results_dir / "harbor-trials"
    trials_dir.mkdir(parents=True, exist_ok=True)

    # Resolve the task dir from the dataset cache (same loader the old eval used).
    tasks = load_tasks(config)
    task = next((t for t in tasks if t.task_id == task_id), None)
    if task is None:
        print(f"✗ task not found: {task_id}", file=sys.stderr)
        return {}

    task_path = task.task_dir

    with tempfile.TemporaryDirectory(prefix="harbor-cfg-") as tmpdir:
        config_path = Path(tmpdir) / "harbor-config.yaml"
        _generate_config(task_path, trials_dir, config_path)

        print(f"── harbor trial: {task_id} ──", file=sys.stderr)
        print(f"  task: {task_path}", file=sys.stderr)
        print(f"  config: {config_path}", file=sys.stderr)
        print(f"  trials: {trials_dir}", file=sys.stderr)

        cmd = [
            "harbor", "trial", "start",
            "--path", str(task_path),
            "--config", str(config_path),
            "--trials-dir", str(trials_dir),
        ]

        # Propagate LLM API keys into the container as env overlay (--ae). Goose
        # sub-agents (triad planner/test-controller/verifier) read these to call
        # the model. Keys are read from the host goose secrets.yaml (not env, which
        # is empty for these names), so the container doesn't need the file mounted.
        # ZHIPU_API_KEY → zai/glm-5.2 (S1/S2/S3/S4/S5); ANTHROPIC_API_KEY → S3* (opt).
        for key in _read_goose_secrets():
            cmd.extend(["--ae", f"{key}={_SECRETS[key]}"])
            print(f"  --ae {key}=<redacted>", file=sys.stderr)

        print(f"  $ {' '.join(cmd[:6])} ...", file=sys.stderr)

        # Harbor runs under its own python (uv tools); it imports our ProductAdapter
        # via import_path "eval.harbor_adapter:ProductAdapter". For that import to
        # resolve, our cwd (the vsmlite-tb/ root containing the eval/ package) must
        # be on PYTHONPATH. subprocess inherits env, so prepend cwd explicitly.
        env = os.environ.copy()
        cwd_abs = str(Path(__file__).resolve().parent.parent)
        env["PYTHONPATH"] = cwd_abs + os.pathsep + env.get("PYTHONPATH", "")

        proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if proc.stdout:
            print(proc.stdout, file=sys.stderr)
        if proc.returncode != 0:
            # Trial failed (timeout, infra error), but harbor still writes a trial
            # dir with partial result.json (exception_info, timing). Don't bail —
            # fall through to parse_trial so the failure is recorded in metrics
            # instead of silently dropped.
            print(f"⚠ harbor trial non-zero exit {proc.returncode} (parsing partial trial)", file=sys.stderr)
            print(proc.stderr, file=sys.stderr)

        if keep_config:
            kept = trials_dir / f"{task_id}-last-config.yaml"
            shutil.copy(config_path, kept)
            print(f"  config kept: {kept}", file=sys.stderr)

    # Parse the most recent trial for this task.
    trial_dir = harbor_bridge.find_latest_trial(trials_dir, task_id)
    if trial_dir is None:
        print(f"✗ no trial dir found for {task_id} in {trials_dir}", file=sys.stderr)
        return {}

    print(f"  parsing trial: {trial_dir.name}", file=sys.stderr)
    task_result = harbor_bridge.parse_trial(trial_dir)

    # Enrich with category/difficulty from task.toml (harbor doesn't carry TB metadata).
    task_result["category"] = task.meta.category
    task_result["difficulty"] = task.meta.difficulty

    # Record into dev_metrics.json via the existing writer (idempotent upsert).
    recorded = harbor_bridge.record_trial(config, task_result)
    summary = recorded.get("summary", {})
    print(f"  recorded: {task_result['status']} "
          f"(trace_len={task_result['trace_len']}, "
          f"duration={task_result['agent_duration_sec']}s)", file=sys.stderr)
    print(f"  dev_metrics: pass_rate={summary.get('pass_rate', 0.0):.1%} "
          f"({summary.get('passed', 0)}/{summary.get('total', 0)})", file=sys.stderr)
    return task_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a harbor trial for one task.")
    parser.add_argument("--task", required=True, help="task_id to run")
    parser.add_argument("--keep-config", action="store_true",
                        help="keep the resolved harbor config for debugging")
    parser.add_argument("--dataset-dir", default=None,
                        help="override dataset cache dir (env EVAL_DATASET_DIR)")
    args = parser.parse_args()

    config = EvalConfig()
    if args.dataset_dir:
        config.dataset_dir = Path(args.dataset_dir)

    result = run_trial(args.task, config, keep_config=args.keep_config)
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
