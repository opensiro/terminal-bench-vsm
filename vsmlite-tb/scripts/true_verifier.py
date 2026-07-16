#!/usr/bin/env python3
"""true_verifier.py — post-trial attribution check (VSM-037).

КОНТЕКСТ (исследовано при планировании):
  TB `tests/test.sh` = ground truth, детерминистический, запускается harbour в
  ТОМ ЖЕ контейнере где работал продукт. LLM-judge НЕ нужен (0% задач требуют).
  НО: overlay ставит deps (pip, goose, ...) которые test.sh может проверить как
  «продукт решил» → reward=1.0 БЕЗ действий продукта = false-positive PASS.

  Канонический кейс (broken-python): overlay ставит pip (для product runtime),
  test.sh проверяет `import pip` → reward=1.0, хотя продукт сделал 0 работы
  (fs.list + pytest → стоп, s1_control=fail_no_checkpoint, s1_artifacts=[]).

РЕШЕНИЕ (детерминистический attribution, no LLM):
  Post-trial скрипт читает артефакты (result.json, product-trace.json) и выносит
  strict verdict: reward=1.0 — это genuine_pass (продукт работал) или
  false_positive (overlay-collision, продукт не решал)?

  False-positive signature (4 поля, 0 false-alarm на 11 genuine PASS):
    reward == 1.0
    s1_control[].verdict == "fail_no_checkpoint"  (продукт сам признал провал)
    terminated_by == "no_observations"            (triad не нашла что тестить)
    s1_artifacts == [] (или missing)               (продукт ничего не создал)

  Genuine PASS с no_observations (convolutional-layers, fix_async) имеют
  НЕПУСТЫЕ s1_artifacts → дискриминатор надёжный.

ИСПОЛЬЗОВАНИЕ:
  python3 scripts/true_verifier.py <trial_dir>           # один trial
  python3 scripts/true_verifier.py --batch <summary.json> # все PASS в батче
  python3 scripts/true_verifier.py --all                  # все trials → registry
  python3 scripts/true_verifier.py --all --json           # machine-readable

ВЫВОД:
  strict_verdict ∈ {genuine_pass, false_positive, fail, unknown}
  strict_reward: 1.0 если genuine_pass, иначе 0.0 (fail/false_positive/unknown)
  НЕ затирает TB reward (ground truth) — добавляет strict_verdict рядом.

БЕЗОПАСНОСТЬ:
  - Только читает state/, .cache/, не мутирует ../vsm ../src (validate.sh OK).
  - Non-fatal: битые/отсутствующие артефакты → verdict "unknown", не валит.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
TRIALS = STATE / "harbor-trials"


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _extract_signals(trial_dir: Path) -> dict:
    """Извлечь сигналы из артефактов trial'а (read-only).

    Возвращает {reward, terminated_by, s1_control_verdicts, s1_artifacts,
    has_s1_block, tool_calls, total_steps}. None если артефакты битые.
    """
    result_json = trial_dir / "result.json"
    if not result_json.exists():
        return {"_error": "no result.json"}
    rj = _read(result_json, {})
    vr = (rj.get("verifier_result") or {}).get("rewards") or {}
    reward = vr.get("reward")
    md = (rj.get("agent_result") or {}).get("metadata") or {}
    terminated_by = md.get("terminated_by")

    # trajectory.json для tool_calls/total_steps (fallback сигналы).
    traj = _read(trial_dir / "agent" / "trajectory.json", {})
    final = (traj.get("final_metrics") or {}) if isinstance(traj, dict) else {}
    extra = final.get("extra") or {}
    tool_calls = extra.get("tool_calls")
    total_steps = final.get("total_steps")

    # product-trace.json — ключевой артефакт атрибуции.
    pt = _read(trial_dir / "agent" / "product-trace.json", {})
    has_s1_block = isinstance(pt, dict) and "s1_control" in pt
    s1_control = pt.get("s1_control") if isinstance(pt, dict) else None
    s1_verdicts = []
    if isinstance(s1_control, list):
        s1_verdicts = [c.get("verdict") for c in s1_control if isinstance(c, dict)]
    s1_artifacts = pt.get("s1_artifacts") if isinstance(pt, dict) else None
    pt_terminated = pt.get("terminated_by") if isinstance(pt, dict) else None

    return {
        "reward": reward,
        "terminated_by": terminated_by or pt_terminated,
        "s1_verdicts": s1_verdicts,
        "s1_artifacts": s1_artifacts,
        "has_s1_block": has_s1_block,
        "tool_calls": tool_calls,
        "total_steps": total_steps,
    }


def verify_trial(trial_dir: Path) -> dict:
    """Strict attribution verdict для одного trial'а.

    Возвращает {task, trial, tb_reward, strict_verdict, strict_reward, reason}.
    strict_verdict:
      genuine_pass   — reward=1.0, продукт реально работал (артефакты/s1_control=pass)
      false_positive — reward=1.0 НО overlay-collision (продукт fail_no_checkpoint,
                       no artifacts) — reward от overlay, не от продукта
      fail           — reward<1.0 (TB verifier не прошёл; не наша забота)
      unknown        — артефактов недостаточно для атрибуции
    """
    trial_dir = Path(trial_dir)
    trial_name = trial_dir.name
    task = trial_name.split("__")[0] if "__" in trial_name else trial_name

    sig = _extract_signals(trial_dir)
    if "_error" in sig:
        return {"task": task, "trial": trial_name, "tb_reward": None,
                "strict_verdict": "unknown", "strict_reward": 0.0,
                "reason": sig["_error"]}

    reward = sig["reward"]
    terminated_by = sig["terminated_by"]
    s1_verdicts = sig["s1_verdicts"]
    s1_artifacts = sig["s1_artifacts"]

    # reward<1.0 → fail (не атрибутируем, TB уже сказал нет).
    if reward is None or reward < 1.0:
        return {"task": task, "trial": trial_name, "tb_reward": reward,
                "strict_verdict": "fail", "strict_reward": 0.0,
                "reason": "TB reward<1.0 (verifier не прошёл)"}

    # reward=1.0 → атрибуция: genuine или false_positive?
    # false_positive signature (все 4 условия одновременно):
    #   s1_control содержит fail_no_checkpoint
    #   terminated_by == no_observations
    #   s1_artifacts пуст (или missing)
    has_fail_no_checkpoint = "fail_no_checkpoint" in s1_verdicts
    artifacts_empty = (s1_artifacts is None) or (
        isinstance(s1_artifacts, list) and len(s1_artifacts) == 0
    )
    is_no_obs = terminated_by == "no_observations"

    reasons = []
    if has_fail_no_checkpoint:
        reasons.append(f"s1_control.verdict=fail_no_checkpoint (продукт признал провал)")
    if is_no_obs:
        reasons.append(f"terminated_by=no_observations (triad не нашла что тестить)")
    if artifacts_empty:
        reasons.append("s1_artifacts пуст (продукт ничего не создал)")

    if has_fail_no_checkpoint and is_no_obs and artifacts_empty:
        return {
            "task": task, "trial": trial_name, "tb_reward": reward,
            "strict_verdict": "false_positive", "strict_reward": 0.0,
            "reason": "overlay-collision: reward=1.0 но продукт не работал (" +
                      "; ".join(reasons) + ")",
        }

    # Genuine pass: reward=1.0 + продукт работал (артефакты ИЛИ s1_control=pass
    # ИЛИ terminated_by=task_resolved). Достаточно любого признака работы.
    work_signals = []
    if isinstance(s1_artifacts, list) and len(s1_artifacts) > 0:
        work_signals.append(f"s1_artifacts={len(s1_artifacts)} files")
    if "pass" in s1_verdicts:
        work_signals.append("s1_control.verdict=pass")
    if terminated_by == "task_resolved":
        work_signals.append("terminated_by=task_resolved")
    calls = sig.get("tool_calls")
    if calls is None:
        calls = sig.get("total_steps")
    if calls is not None and calls > 2:
        work_signals.append(f"tool_calls={calls}")

    if work_signals:
        return {
            "task": task, "trial": trial_name, "tb_reward": reward,
            "strict_verdict": "genuine_pass", "strict_reward": 1.0,
            "reason": "продукт работал: " + ", ".join(work_signals),
        }

    # reward=1.0 но НЕТ чётких сигналов работы ни в одну сторону → unknown
    # (артефактов мало, s1_block может отсутствовать — не можем атрибутировать).
    return {
        "task": task, "trial": trial_name, "tb_reward": reward,
        "strict_verdict": "unknown", "strict_reward": 0.0,
        "reason": "reward=1.0 но сигналов продукта недостаточно для атрибуции",
    }


def verify_all() -> list[dict]:
    """Проверить все trials в state/harbor-trials/. Возвращает list of verdicts."""
    results = []
    if not TRIALS.exists():
        return results
    for trial_dir in sorted(TRIALS.iterdir()):
        if not trial_dir.is_dir() or not (trial_dir / "result.json").exists():
            continue
        results.append(verify_trial(trial_dir))
    return results


def verify_batch(batch_summary_path: Path) -> list[dict]:
    """Проверить все PASS trials упомянутые в batch_summary (по per_task trial_name)."""
    bs = _read(batch_summary_path, {})
    results = []
    for pt in bs.get("per_task", []):
        trial_name = pt.get("trial_name") or pt.get("task_id")
        if not trial_name:
            continue
        # Найти trial_dir по имени (trial_name может быть task или task__id).
        trial_dir = None
        if "__" in str(trial_name):
            trial_dir = TRIALS / trial_name
        else:
            # Найти последний trial этой задачи.
            matches = sorted(TRIALS.glob(f"{trial_name}__*/"), reverse=True)
            if matches:
                trial_dir = matches[0]
        if trial_dir and trial_dir.exists():
            v = verify_trial(trial_dir)
            v["batch_task"] = pt.get("task_id")
            results.append(v)
    return results


def _print_verdict(v: dict, verbose: bool = False) -> None:
    mark = {
        "genuine_pass": "✓", "false_positive": "⚠",
        "fail": "✗", "unknown": "?",
    }.get(v["strict_verdict"], "·")
    print(f"{mark} {v['task']:<36} tb={v['tb_reward']} strict={v['strict_verdict']}")
    if verbose:
        print(f"    trial: {v['trial']}")
        print(f"    reason: {v['reason']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="true_verifier",
        description="Post-trial attribution check (VSM-037) — detect false-positive PASS",
    )
    parser.add_argument("trial_dir", nargs="?", type=Path, default=None,
                        help="trial directory to verify")
    parser.add_argument("--batch", type=Path, default=None,
                        help="batch_summary.json — verify all its PASS trials")
    parser.add_argument("--all", action="store_true",
                        help="verify all trials in state/harbor-trials/")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable JSON output")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="show reason for each verdict")
    parser.add_argument("--write-registry", action="store_true",
                        help="write state/true_verification.json (with --all)")
    args = parser.parse_args()

    if args.batch:
        verdicts = verify_batch(args.batch)
    elif args.all:
        verdicts = verify_all()
    elif args.trial_dir:
        verdicts = [verify_trial(args.trial_dir)]
    else:
        parser.error("укажите trial_dir, --batch, или --all")
        return 2

    if args.json:
        print(json.dumps(verdicts, ensure_ascii=False, indent=2))
        return 0

    # Summary + per-verdict.
    counts = {"genuine_pass": 0, "false_positive": 0, "fail": 0, "unknown": 0}
    for v in verdicts:
        counts[v["strict_verdict"]] = counts.get(v["strict_verdict"], 0) + 1
        _print_verdict(v, verbose=args.verbose)

    total = len(verdicts)
    print(f"\n── true_verifier summary ──")
    print(f"  total: {total}")
    print(f"  genuine_pass:  {counts['genuine_pass']}")
    print(f"  false_positive: {counts['false_positive']} (reward=1.0 от overlay, не от продукта)")
    print(f"  fail:           {counts['fail']}")
    print(f"  unknown:        {counts['unknown']}")
    if total > 0:
        strict_pass = counts["genuine_pass"]
        print(f"  strict pass-rate: {strict_pass}/{total} = {strict_pass/total:.1%}")
        tb_pass = counts["genuine_pass"] + counts["false_positive"] + counts.get("unknown_pass", 0)
        # TB reward=1.0 count (genuine + false_positive, excluding unknown/fail)
        tb_pass_count = sum(1 for v in verdicts if v.get("tb_reward") == 1.0)
        print(f"  TB pass-rate (raw reward=1.0): {tb_pass_count}/{total} = "
              f"{tb_pass_count/total:.1%}")

    if args.write_registry and args.all:
        reg_path = STATE / "true_verification.json"
        reg_path.write_text(
            json.dumps({
                "_comment": "true_verifier registry — strict attribution verdicts (VSM-037).",
                "generated": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
                "total": len(verdicts),
                "counts": counts,
                "verdicts": verdicts,
            }, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\n→ {reg_path.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
