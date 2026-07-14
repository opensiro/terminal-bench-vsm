#!/usr/bin/env python3
"""autonomy.py — A(t) ∈ [0,1] из 5 поведенческих знаков, forward-совместимо с дизайном vsmforge.

Знаки (см. ref/vsmforge-target.md):
  S5-sign ← interventions[] : доля циклов без S5-вмешательств (VSM-005); lower intervention = more autonomous
  S4-sign ← intel[]     : есть self-closed сигналы
  S3-sign ← units[]     : ≥2 юнитов, низкое pressure
  S1-sign ← activity[]  : ≥3 активных git-дней в ../vsm/
  eval-sign ← dev_metrics.json : pass-rate Terminal-Bench Dev Set v2 (VSM-005 входной индикатор)

A(t) = w_op * operational_score + w_eval * eval_score
  operational_score ∈ {0, 0.25, 0.5, 0.75, 1.0} — доля 4 operational знаков что meets
  eval_score ∈ [0, 1] — pass-rate как есть (или 0 если eval не запускался)
Веса: w_op=0.7, w_eval=0.3 (eval растёт по фазам; см. VSM-004/005). Если eval
не запускался (dev_metrics.json пустой) — eval_score=0, w_eval сохраняется: это
штраф за «не оценён», стимулирующий запускать eval.

Вердикт: AUTONOMOUS (A(t)≥0.8) / SEMI-AUTONOMOUS (0.3..0.8) / DEPENDENT (<0.3).

Usage:
  python3 scripts/autonomy.py            # посчитать и обновить state/maturation.json
  python3 scripts/autonomy.py --check    # только напечатать, без записи
"""
from __future__ import annotations
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
CHILD = ROOT / "../vsm"

# Пороги (по дизайну vsmforge; см. ref/vsmforge-target.md)
INTERVENTION_HIGH_SHARE = 0.5  # VSM-005 S5-sign: доля циклов с S5-вмешательствами выше этой → не autonomous
ACTIVITY_MIN_DAYS = 3         # S1-sign: минимум активных дней
UNITS_MIN = 2                 # S3-sign: минимум юнитов

# Веса A(t): operational (4 знака) vs eval (pass-rate, VSM-005 входной индикатор)
W_OPERATIONAL = 0.7
W_EVAL = 0.3
AUTONOMOUS_THRESHOLD = 0.8
DEPENDENT_THRESHOLD = 0.3


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _read_interventions():
    """Считает S5-вмешательства из state/interventions.json (VSM-005).

    Формат: [{cycle, timestamp, trigger, action, ...}].
    Вмешательство = случай когда автономии VSM не хватило и S5 (архитектор)
    применил структурное изменение. Чем меньше — тем автономнее.
    """
    data = _read_json(STATE / "interventions.json", {})
    return data.get("interventions", []) if isinstance(data, dict) else []


def s5_sign(interventions, cycle_count):
    """Доля циклов без S5-вмешательств (VSM-005). Высокая → autonomous.

    interventions: list of S5 intervention records.
    cycle_count: общее число циклов (из maturation.json).
    """
    if cycle_count == 0:
        return {"value": 0.0, "meets": True, "detail": "no cycles yet"}
    intervened_cycles = {i.get("cycle") for i in interventions if i.get("cycle") is not None}
    # Доля циклов БЕЗ вмешательств (high = autonomous)
    non_intervention_share = 1.0 - (len(intervened_cycles) / cycle_count)
    return {"value": round(non_intervention_share, 3),
            "meets": non_intervention_share >= (1.0 - INTERVENTION_HIGH_SHARE),
            "detail": f"{len(intervened_cycles)}/{cycle_count} cycles had S5 intervention"}


def s4_sign(intel):
    """Есть self-closed сигналы (status in done/review). ≥1 → autonomous."""
    signals = intel.get("signals", []) if intel else []
    if not signals:
        return {"value": 0, "meets": False, "detail": "no signals"}
    self_closed = [s for s in signals if s.get("status") in ("done", "review")]
    return {"value": len(self_closed), "meets": len(self_closed) >= 1,
            "detail": f"{len(self_closed)} self-closed"}


def s3_sign(units):
    """≥2 юнитов, низкое pressure."""
    units = units or []
    if len(units) < UNITS_MIN:
        return {"value": len(units), "meets": False,
                "detail": f"{len(units)} units (< {UNITS_MIN})"}
    open_issues = sum(u.get("open_issues", 0) for u in units)
    return {"value": len(units), "meets": True,
            "detail": f"{len(units)} units, {open_issues} open issues"}


def s1_sign(activity):
    """≥3 активных git-дней. activity[] = [{date, total}]."""
    activity = activity or []
    days = len({a.get("date") for a in activity if a.get("date")})
    return {"value": days, "meets": days >= ACTIVITY_MIN_DAYS,
            "detail": f"{days} active days (need {ACTIVITY_MIN_DAYS})"}


def eval_sign(dev_metrics):
    """Pass-rate Terminal-Bench Dev Set v2 — ВХОДНОЙ индикатор автономности (VSM-005).

    dev_metrics: state/dev_metrics.json (от eval/ пайплайна).
    Pass-rate ∈ [0,1]. meets=True при pass_rate ≥ 0.5 (порог «не зависимый»).
    Если eval не запускался — value=0, meets=False (стимул запускать).
    """
    if not dev_metrics:
        return {"value": 0.0, "meets": False, "detail": "eval не запускался"}
    summary = dev_metrics.get("summary", {}) if isinstance(dev_metrics, dict) else {}
    total = summary.get("total", 0)
    pass_rate = summary.get("pass_rate", 0.0)
    if total == 0:
        return {"value": 0.0, "meets": False, "detail": "eval: 0 задач"}
    passed = summary.get("passed", 0)
    meets = pass_rate >= 0.5
    return {"value": round(pass_rate, 3), "meets": meets,
            "detail": f"eval pass-rate: {passed}/{total} = {pass_rate:.0%}"}


def verdict(op_signs, eval_result):
    """Финальный A(t): w_op * operational_score + w_eval * eval_score.

    op_signs: 4 operational знака (s5/s4/s3/s1) с полем 'meets'.
    eval_result: eval_sign результат (value = pass-rate).
    """
    op_meets = sum(1 for s in op_signs.values() if s["meets"])
    operational_score = op_meets / len(op_signs)
    eval_score = eval_result["value"]

    score = round(W_OPERATIONAL * operational_score + W_EVAL * eval_score, 3)
    if score >= AUTONOMOUS_THRESHOLD:
        return "AUTONOMOUS", score
    if score < DEPENDENT_THRESHOLD:
        return "DEPENDENT", score
    return "SEMI-AUTONOMOUS", score


def compute():
    interventions = _read_interventions()
    intel = _read_json(STATE / "intel.json", {})
    mat = _read_json(STATE / "maturation.json", {})
    units = mat.get("units", [])
    cycle_count = mat.get("cycle_count", 0)
    # units обычно в live_metrics; пробуем
    live = _read_json(STATE / "live_metrics.json", {})
    units = units or live.get("units", [])
    activity = live.get("activity", [])

    op_signs = {
        "s5_sign": s5_sign(interventions, cycle_count),
        "s4_sign": s4_sign(intel),
        "s3_sign": s3_sign(units),
        "s1_sign": s1_sign(activity),
    }
    # eval-sign: pass-rate Terminal-Bench Dev Set v2 (VSM-005 входной индикатор)
    dev_metrics = _read_json(STATE / "dev_metrics.json", {})
    eval_result = eval_sign(dev_metrics)

    v, score = verdict(op_signs, eval_result)
    return op_signs, eval_result, score, v


def main():
    check_only = "--check" in sys.argv
    op_signs, eval_result, score, v = compute()

    print("── autonomy (A(t)) ──")
    for name, s in op_signs.items():
        mark = "✓" if s["meets"] else "✗"
        print(f"  {mark} {name}: {s['detail']}")
    mark = "✓" if eval_result["meets"] else "✗"
    print(f"  {mark} eval_sign: {eval_result['detail']}")
    op_meets = sum(1 for s in op_signs.values() if s["meets"])
    print(f"  A(t) = {score}  "
          f"(op={op_meets}/4 ×{W_OPERATIONAL} + eval={eval_result['value']} ×{W_EVAL})  "
          f"verdict = {v}")

    if check_only:
        return

    # Обновить state/maturation.json
    mat_path = STATE / "maturation.json"
    mat = _read_json(mat_path, {})
    mat.setdefault("autonomy", {})
    mat["autonomy"].update({
        "current": score,
        "verdict": v,
        "signs": {k: {"value": s["value"], "from": {"s5_sign": "interventions", "s4_sign": "intel",
                      "s3_sign": "units", "s1_sign": "activity"}[k], "meets": s["meets"]}
                  for k, s in op_signs.items()},
    })
    mat["autonomy"]["signs"]["eval_sign"] = {
        "value": eval_result["value"], "from": "dev_metrics", "meets": eval_result["meets"],
    }
    mat["autonomy"]["weights"] = {"operational": W_OPERATIONAL, "eval": W_EVAL}
    mat["updated"] = date.today().isoformat()
    mat_path.write_text(json.dumps(mat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  → обновлён {mat_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
