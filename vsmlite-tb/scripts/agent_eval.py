#!/usr/bin/env python3
"""agent_eval.py — скоринг 0-10 + буквенный A/B/C/D/E работы агентов (VSM-025).

Два контура:
  1. Продуктовые агенты (TB-задачи): read-only из state/dev_metrics.json#tasks[]
     (формат стабилен по контракту VSM-024:59). Per-task score.
  2. Системные агенты (vsmlite S1-S5): per-cycle, атрибуция по owner state-файла.

Скоринг: 0-10 (<5 = FAIL). Буква A/B/C/D/E где D < 0.5 (C ≥ 0.5 = pass):
  A ≥ 9.0 (≥0.90) | B ≥ 7.5 (≥0.75) | C ≥ 5.0 (≥0.50, pass) |
  D ≥ 2.5 (≥0.25, FAIL) | E < 2.5 (<0.25)

trace_len — info-only (VSM-022 superseded→VSM-024: harbour управляет tool-surface).
harbor-блок task["harbor"]={terminated_by, attempts, reward} подхватывается
оппортунистически как progressive enhancement (post-VSM-024 smoke).

Веса tunable (см. WEIGHTS / SYSTEM_WEIGHTS ниже), как пороги в autonomy.py:35-43.

Usage (из export_logs.detect_and_log):
  from agent_eval import evaluate
  result = evaluate()        # → {product: [...], systems: [...], summary: {...}}
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"

# ── Грейды: score → grade. D < 0.5 (C ≥ 0.5 = pass) ──
GRADE_BOUNDS = [
    ("A", 9.0),
    ("B", 7.5),
    ("C", 5.0),
    ("D", 2.5),
    ("E", 0.0),
]


def grade(score: float) -> str:
    """Score 0-10 → A/B/C/D/E (D < 0.5, т.е. C ≥ 5.0 = pass)."""
    for g, bound in GRADE_BOUNDS:
        if score >= bound:
            return g
    return "E"


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


# ── Веса продуктового скоринга (TB-task). Сумма = 10.0 max ──
WEIGHTS = {
    "verdict_pass": 6.0,   # passed → +6; failed → +1; error → +0
    "verdict_fail": 1.0,
    "verdict_err": 0.0,
    "pytest_max": 2.0,     # pytest ratio × 2 (max 2)
    "eff_fast": 1.5,       # ≤300s
    "eff_med": 1.0,        # 301-900s
    "eff_slow": 0.5,       # >900s
    "pen_timeout": -1.0,   # timed_out
    "pen_exit": -0.5,      # agent_exit_code != 0
}


def _efficiency(duration: float | None) -> float:
    """Балл за скорость (bucket)."""
    if duration is None or duration <= 0:
        return 0.0
    if duration <= 300:
        return WEIGHTS["eff_fast"]
    if duration <= 900:
        return WEIGHTS["eff_med"]
    return WEIGHTS["eff_slow"]


def _harbor_bonus(harbor: dict) -> float:
    """Progressive enhancement: бонус/штраф из harbor trial-блока (post-VSM-024).

    terminated_by: normal → +0.5; verifier_fail → -0.5; timeout → -0.3
    attempts: 1 → +0.3 (с первой попытки); >1 → -0.2 за каждую лишнюю
    reward (0-1): ×0.5 как cross-check с pytest (reward high при pytest fail → подозрение)
    Clamp [-1, +1]. Возвращает 0 если блока нет.
    """
    if not harbor or not isinstance(harbor, dict):
        return 0.0
    bonus = 0.0
    term = harbor.get("terminated_by", "")
    if term == "normal":
        bonus += 0.5
    elif term in ("verifier_fail", "verifier"):
        bonus += -0.5
    elif term == "timeout":
        bonus += -0.3
    attempts = harbor.get("attempts")
    if isinstance(attempts, (int, float)):
        if attempts <= 1:
            bonus += 0.3
        else:
            bonus += -0.2 * (attempts - 1)
    # reward cross-check убран из числового (info-only, как trace) — слишком косвенно
    return max(-1.0, min(1.0, bonus))


def score_task(task: dict) -> dict:
    """Скоринг одной TB-задачи → {score 0-10, grade, summary ≤500, components}."""
    tid = task.get("task_id", "?")
    status = task.get("status", "error")
    pytest_p = task.get("pytest_passed") or 0
    pytest_f = task.get("pytest_failed") or 0
    duration = task.get("agent_duration_sec")
    trace_len = task.get("trace_len") or 0
    timed_out = bool(task.get("timed_out"))
    exit_code = task.get("agent_exit_code")
    harbor = task.get("harbor") or {}

    components = {}

    # verdict
    vkey = {"passed": "verdict_pass", "failed": "verdict_fail"}.get(status, "verdict_err")
    components["verdict"] = WEIGHTS[vkey]

    # pytest ratio × 2
    pytest_total = pytest_p + pytest_f
    pytest_ratio = pytest_p / pytest_total if pytest_total else 0.0
    components["pytest"] = round(pytest_ratio * WEIGHTS["pytest_max"], 2)

    # efficiency
    components["efficiency"] = _efficiency(duration)

    # harbor bonus (progressive; 0 если блока нет)
    hb = _harbor_bonus(harbor)
    components["harbor_bonus"] = round(hb, 2)

    # penalties
    components["penalty_timeout"] = WEIGHTS["pen_timeout"] if timed_out else 0.0
    components["penalty_exit"] = WEIGHTS["pen_exit"] if exit_code not in (None, 0) else 0.0

    score = sum(components.values())
    score = max(0.0, min(10.0, round(score, 2)))
    g = grade(score)
    passed = score >= 5.0

    cat = task.get("category", "?")
    diff = task.get("difficulty", "?")
    # human summary ≤ 500 chars
    summary = (
        f"{tid} [{score}/{g}] {cat}·{diff} · "
        f"{duration or 0:.0f}s · trace{trace_len} · "
        f"pytest{pytest_p}/{pytest_f} · exit{exit_code if exit_code is not None else 0}."
    )
    if harbor:
        summary += f" harbor(terminated_by={harbor.get('terminated_by','?')}, attempts={harbor.get('attempts','?')})."
    else:
        summary += " (no harbor block — pre-VSM-024; trace_len info-only)"

    return {
        "task_id": tid, "score": score, "grade": g, "passed": passed,
        "components": components, "summary": summary[:500],
        "category": cat, "difficulty": diff,
    }


# ── Системные агенты: owner state-файла → кто отработал в цикле ──
# Маппинг: системный агент → state-файл, который он пишет.
SYSTEM_FILE = {
    "S1": "maturation.json",
    "S2": "status.json",
    "S3": "metrics.json",
    "S3*": "audit.json",
    "S4": "intel.json",
    "S5": "interventions.json",
}

# Веса системного скоринга. Сумма = 10.0 max.
SYSTEM_WEIGHTS = {
    "produced_output": 4.0,   # файл owner'а изменился в цикле
    "quality_delta": 4.0,     # A(t)↑ / coverage↑ / drift↓ / signals added
    "no_regressions": 2.0,    # нет red audit findings, нет блокеров
}


def score_system(name: str, owner_file: str, changed: bool, prev: dict, cur: dict,
                 prev_issues: list, cur_issues: list) -> dict | None:
    """Скоринг системного агента (per-cycle).

    name: S1..S5/S3*. owner_file: state-файл. changed: изменился ли он в цикле.
    prev/cur: полный snapshot state (для quality-delta). issues: для regression-check.
    Возвращает None если агент idle (файл не менялся) → не оценивается.
    """
    if not changed:
        return None  # idle — не оцениваем

    components = {"produced_output": SYSTEM_WEIGHTS["produced_output"]}

    # quality delta — контур-специфичная логика по owner'у
    qd = 0.0
    if name == "S3":  # A(t) + coverage + drift
        a_prev = prev.get("metrics", {}).get("kpi", {}).get("autonomy_score", 0)
        a_cur = cur.get("metrics", {}).get("kpi", {}).get("autonomy_score", 0)
        if a_cur > a_prev:
            qd += 2.0
        cov_prev = prev.get("metrics", {}).get("kpi", {}).get("coverage_ratio", 0)
        cov_cur = cur.get("metrics", {}).get("kpi", {}).get("coverage_ratio", 0)
        if cov_cur > cov_prev:
            qd += 1.0
        drift_prev = prev.get("metrics", {}).get("kpi", {}).get("drift_score", 0)
        drift_cur = cur.get("metrics", {}).get("kpi", {}).get("drift_score", 0)
        if drift_cur < drift_prev:
            qd += 1.0
    elif name == "S4":  # intel signals added
        sig_prev = len(prev.get("intel", {}).get("signals", []))
        sig_cur = len(cur.get("intel", {}).get("signals", []))
        if sig_cur > sig_prev:
            qd += 4.0
        elif sig_cur == sig_prev and sig_cur > 0:
            qd += 2.0  # поддержание разведки
    elif name == "S3*":  # audit findings produced (независимый аудит = ценность)
        f_prev = len(prev.get("audit", {}).get("findings", []))
        f_cur = len(cur.get("audit", {}).get("findings", []))
        if f_cur > 0:
            qd += min(4.0, 1.0 + f_cur - f_prev)
    elif name == "S2":  # status sweep — поддержание координации
        qd += 2.0
    elif name == "S5":  # minimal intervention — чем меньше, тем лучше
        interv_prev = len(prev.get("interventions", {}).get("interventions", []))
        interv_cur = len(cur.get("interventions", {}).get("interventions", []))
        if interv_cur == interv_prev:
            qd += 4.0  # рутинно бездействовал = идеальный S5
        else:
            qd += 2.0  # вмешался, но структурно (задокументировано)
    elif name == "S1":  # maturation / cycle progression
        cyc_prev = prev.get("maturation", {}).get("cycle_count", 0)
        cyc_cur = cur.get("maturation", {}).get("cycle_count", 0)
        if cyc_cur > cyc_prev:
            qd += 4.0
        else:
            qd += 2.0  # операционная активность

    components["quality_delta"] = round(qd, 2)

    # no regressions: нет red audit findings, нет severity S0/S1 в новых issues
    regressions = 0
    red = [f for f in cur.get("audit", {}).get("findings", []) if f.get("verdict") == "red"]
    if red:
        regressions += 1
    new_critical = [i for i in cur_issues
                    if i not in prev_issues
                    and (i.get("severity") in ("S0", "S1") or i.get("signal_type") == "algedonic")]
    if new_critical:
        regressions += 1
    components["no_regressions"] = SYSTEM_WEIGHTS["no_regressions"] if regressions == 0 else 0.0

    score = sum(components.values())
    score = max(0.0, min(10.0, round(score, 2)))
    g = grade(score)
    passed = score >= 5.0

    # summary ≤ 500
    status_note = "active" if changed else "idle"
    summary = f"{name} [{score}/{g}] {status_note}. " + " ".join(
        f"{k}={v}" for k, v in components.items())
    if red:
        summary += f" ⚠ {len(red)} RED audit finding(s)."
    summary = summary[:500]

    return {
        "agent": name, "score": score, "grade": g, "passed": passed,
        "components": components, "summary": summary, "idle": not changed,
    }


def evaluate(prev_snapshot: dict | None, cur_snapshot: dict,
             prev_issues: list, cur_issues: list, is_seed: bool = False) -> dict:
    """Полная оценка: продуктовые + системные агенты.

    prev_snapshot/cur_snapshot: агрегат state от export_logs (см. там _collect_state).
        {maturation, metrics, dev_metrics, interventions, audit, intel, status, ...}
    prev=None (или is_seed=True) → первый прогон: продуктовые оцениваем по cur,
        системные idle (нет базы для сравнения изменений — не оцениваем).
    prev_issues/cur_issues: списки issue-dicts (для regression-check).

    Возвращает {product: [...], systems: [...], breakdown: {...}, summary: {...}}.
    """
    prev_snapshot = prev_snapshot or {}
    cur_snapshot = cur_snapshot or {}

    # ── Продуктовые агенты (TB-tasks) ──
    product = []
    tasks = (cur_snapshot.get("dev_metrics") or {}).get("tasks", []) or []
    for t in tasks:
        product.append(score_task(t))

    # breakdown по difficulty/category
    breakdown = {"by_difficulty": {}, "by_category": {}}
    for key in ("by_difficulty", "by_category"):
        src = (cur_snapshot.get("dev_metrics") or {}).get(key, {}) or {}
        for label, counts in src.items():
            if isinstance(counts, dict):
                breakdown[key][label] = {
                    "total": counts.get("total", 0),
                    "passed": counts.get("passed", 0),
                    "pass_rate": counts.get("pass_rate", 0.0),
                }

    # ── Системные агенты (S1-S5) ──
    systems = []
    for name, owner_file in SYSTEM_FILE.items():
        if is_seed:
            continue  # seed-прогон: нет базы для «changed» → все idle, не оцениваем
        prev_owner = prev_snapshot.get(_owner_key(owner_file))
        cur_owner = cur_snapshot.get(_owner_key(owner_file))
        changed = _state_changed(prev_owner, cur_owner)
        res = score_system(name, owner_file, changed, prev_snapshot, cur_snapshot,
                           prev_issues, cur_issues)
        if res is not None:
            systems.append(res)

    # ── Summary ──
    prod_scores = [p["score"] for p in product]
    sys_scores = [s["score"] for s in systems]
    summary = {
        "product_count": len(product),
        "product_avg": round(sum(prod_scores) / len(prod_scores), 2) if prod_scores else None,
        "product_pass": sum(1 for p in product if p["passed"]),
        "system_count": len(systems),
        "system_avg": round(sum(sys_scores) / len(sys_scores), 2) if sys_scores else None,
        "system_idle": len(SYSTEM_FILE) - len(systems),
    }
    if is_seed:
        summary["seed_note"] = "first run — system agents idle (no baseline to detect changes)"
    return {"product": product, "systems": systems, "breakdown": breakdown, "summary": summary}


def _owner_key(filename: str) -> str:
    """Имя state-файла → ключ в snapshot-агрегате export_logs (без .json)."""
    return filename.removesuffix(".json")


def _state_changed(prev, cur) -> bool:
    """Изменился ли owner state-файл (глубокое сравнение JSON)."""
    return prev != cur
