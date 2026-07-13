#!/usr/bin/env python3
"""autonomy.py — A(t) ∈ [0,1] из 4 поведенческих знаков, forward-совместимо с дизайном vsmforge.

Знаки (см. ref/vsmforge-target.md):
  S5-sign ← interventions[] : доля циклов без S5-вмешательств (VSM-005); lower intervention = more autonomous
  S4-sign ← intel[]     : есть self-closed сигналы
  S3-sign ← units[]     : ≥2 юнитов, низкое pressure
  S1-sign ← activity[]  : ≥3 активных git-дней в ../vsm/

Вердикт: AUTONOMOUS / SEMI-AUTONOMOUS / DEPENDENT.

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


def verdict(signs):
    meets = sum(1 for s in signs.values() if s["meets"])
    if meets == 4:
        return "AUTONOMOUS", 1.0
    if meets == 0:
        return "DEPENDENT", 0.0
    # Линейная интерполяция для SEMI-AUTONOMOUS
    return "SEMI-AUTONOMOUS", round(meets / 4, 2)


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

    signs = {
        "s5_sign": s5_sign(interventions, cycle_count),
        "s4_sign": s4_sign(intel),
        "s3_sign": s3_sign(units),
        "s1_sign": s1_sign(activity),
    }
    v, score = verdict(signs)
    return signs, score, v


def main():
    check_only = "--check" in sys.argv
    signs, score, v = compute()

    print("── autonomy (A(t)) ──")
    for name, s in signs.items():
        mark = "✓" if s["meets"] else "✗"
        print(f"  {mark} {name}: {s['detail']}")
    print(f"  A(t) = {score}  verdict = {v}")

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
                  for k, s in signs.items()},
    })
    mat["updated"] = date.today().isoformat()
    mat_path.write_text(json.dumps(mat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  → обновлён {mat_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
