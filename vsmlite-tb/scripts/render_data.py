#!/usr/bin/env python3
"""render_data.py — собирает monitor/data.js (window.VSM_DATA) для forward-контракта vsmforge.

Форма — см. ref/vsmforge-target.md. vsmforge (когда будет разработан) парсит
регэкспом `window\\.VSM_DATA\\s*=\\s*(\\{.*?\\})\\s*;?\\s*$`.

Источники:
  state/status.json     → systems
  state/maturation.json → metrics.{autonomy_score, maturation_phase}
  state/metrics.json    → metrics.{coverage_ratio, validate_pass_rate, drift_score}
  state/audit.json      → audit
  state/intel.json      → intel
  state/heartbeat.json  → heartbeat
  issues/VSM-*.yaml     → issues
  state/live_metrics.json → units[], activity[] (от collect_metrics.py)
  state/dev_metrics.json → eval (pass-rate Terminal-Bench Dev Set v2, VSM-005)
  state/eval_history.json → eval.trend (per-run снэпшоты для S4)

Usage:
  python3 scripts/render_data.py
"""
from __future__ import annotations
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
MONITOR = ROOT / "monitor"


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _read_issues():
    """Парсит issues/VSM-*.yaml через PyYAML → полный набор полей для UI-карточки.

    Возвращает список словарей с плоскими и блочными полями (summary/proposal/
    evidence/acceptance/policy_question/options), которые рендерит issues.html.
    Fall back: если YAML невалиден — возвращает минимум (id/title/status), чтобы
    одна битая карточка не валила весь дашборд.
    """
    import yaml
    issues = []
    for f in sorted((ROOT / "issues").glob("VSM-*.yaml")):
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8", errors="replace")) or {}
        except yaml.YAMLError:
            # минимума достаточно, чтобы карточка появилась с пометкой
            doc = {"id": f.stem, "title": "(невалидный YAML)", "status": "triage",
                   "_parse_error": True}
        if not isinstance(doc, dict):
            continue
        doc.setdefault("status", "triage")
        doc.setdefault("needs_human_decision", False)
        doc.setdefault("options", [])
        # options нормализуем: строки → {id,label}, объекты пропускаем
        opts = []
        for o in doc.get("options") or []:
            if isinstance(o, str):
                opts.append({"id": o, "label": o, "hint": ""})
            elif isinstance(o, dict):
                opts.append({"id": o.get("id") or o.get("label", "?"),
                             "label": o.get("label") or o.get("id", "?"),
                             "hint": o.get("hint", "")})
        doc["options"] = opts
        # PyYAML парсит bare `2026-07-13` как datetime.date → приводим к строке для JSON.
        for k in ("created", "updated"):
            v = doc.get(k)
            if hasattr(v, "isoformat"):
                doc[k] = v.isoformat()
        issues.append(doc)
    return issues


def _collect_runs(trials_dir: Path, limit: int = 50):
    """VSM-029: per-run саммари из state/harbor-trials/ для раздела Runs в мониторе.

    Проходит state/harbor-trials/*/, читает result.json каждого trial'а и
    собирает светлые поля (без тяжёлых trajectory.json/step_results). Источник
    полей установлен по реальной структуре harbor result.json (19 ключей):
      - trial_name/task_name — на верхнем уровне
      - verdict/terminated_by/total_attempts — agent_result.metadata
      - reward — verifier_result.rewards.reward
      - started_at/finished_at — на верхнем уровне (ISO Z)
      - tokens — agent_result.n_{input,cache,output}_tokens (часто None)

    Возвращает список runs, отсортированный по started_at (desc), обрезанный до
    limit. Один битый trial не валилит весь сбор (skip + continue).
    """
    if not trials_dir.exists():
        return []
    runs = []
    for tdir in sorted(trials_dir.iterdir(), reverse=True):
        if not tdir.is_dir():
            continue
        rpath = tdir / "result.json"
        try:
            r = json.loads(rpath.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        if not isinstance(r, dict):
            continue
        try:
            meta = (r.get("agent_result") or {}).get("metadata") or {}
            rewards = ((r.get("verifier_result") or {}).get("rewards") or {})
            reward = rewards.get("reward")
            started = r.get("started_at")
            finished = r.get("finished_at")
            duration = _duration_sec(started, finished)
            exc = r.get("exception_info")
            # status: exception → error; reward 1.0 → passed; 0.0 → failed; иначе unknown
            if exc:
                status = "error"
            elif reward is None:
                status = "unknown"
            else:
                status = "passed" if reward >= 1.0 else "failed"
            ar = r.get("agent_result") or {}
            runs.append({
                "trial_name": r.get("trial_name") or tdir.name,
                "task_id": r.get("task_name") or tdir.name.split("__")[0],
                "status": status,
                "verdict": meta.get("verdict"),
                "reward": reward,
                "terminated_by": meta.get("terminated_by"),
                "attempts": meta.get("total_attempts"),
                "started_at": started,
                "finished_at": finished,
                "duration_sec": duration,
                "tokens": {
                    "input": ar.get("n_input_tokens"),
                    "cache": ar.get("n_cache_tokens"),
                    "output": ar.get("n_output_tokens"),
                },
                "cost_usd": ar.get("cost_usd"),
            })
        except Exception:
            continue
    # сортировка по started_at desc (None — в конец)
    runs.sort(key=lambda x: x.get("started_at") or "", reverse=True)
    return runs[:limit]


def _duration_sec(started, finished):
    """Парсит ISO-Z таймстампы, возвращает разницу в секундах (int) или None."""
    if not started or not finished:
        return None
    try:
        s = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        f = datetime.fromisoformat(str(finished).replace("Z", "+00:00"))
        return int((f - s).total_seconds())
    except (ValueError, TypeError):
        return None


def main():
    project = ROOT.name
    try:
        from datetime import datetime
        # name из vsmlite.yaml если есть
        ytxt = (ROOT / "vsmlite.yaml").read_text(encoding="utf-8", errors="replace")
        m = re.search(r'^name:\s*(.+?)\s*$', ytxt, re.M)
        if m: project = m.group(1)
    except Exception:
        pass

    status = _read(STATE / "status.json", {})
    maturation = _read(STATE / "maturation.json", {})
    metrics = _read(STATE / "metrics.json", {})
    audit = _read(STATE / "audit.json", {})
    intel = _read(STATE / "intel.json", {})
    heartbeat = _read(STATE / "heartbeat.json", {})
    live = _read(STATE / "live_metrics.json", {})
    history = _read(STATE / "history.json", [])
    interventions = _read(STATE / "interventions.json", {})
    dev_metrics = _read(STATE / "dev_metrics.json", {})
    eval_history = _read(STATE / "eval_history.json", [])

    autonomy = maturation.get("autonomy", {}) if maturation else {}
    kpi = metrics.get("kpi", {}) if metrics else {}
    intervention_list = interventions.get("interventions", []) if isinstance(interventions, dict) else []
    cycle_count = maturation.get("cycle_count", 0) if maturation else 0

    # eval (Terminal-Bench Dev Set v2) — VSM-005 входной индикатор автономности
    eval_summary = dev_metrics.get("summary", {}) if isinstance(dev_metrics, dict) else {}
    eval_trend = _eval_trend(eval_history)
    # VSM-029: per-run саммари из harbor-trials/ для раздела Runs в мониторе
    runs = _collect_runs(STATE / "harbor-trials")

    data = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "project": project,
        "operational_mode": status.get("operational_mode", "normal"),
        "systems": status.get("systems", {}),
        "units": live.get("units", []),
        "metrics": {
            "autonomy_score": autonomy.get("current", 0.0),
            "maturation_phase": maturation.get("maturation_state", "Initial State"),
            "coverage_ratio": kpi.get("coverage_ratio", 0.0),
            "validate_pass_rate": kpi.get("validate_pass_rate"),
            "drift_score": kpi.get("drift_score", 0.0),
            "token_spend_estimate": kpi.get("token_spend_estimate", 0),
            "triple_index": (metrics or {}).get("triple_index", {}) if metrics else {},
            "balance_s3_s4": (metrics or {}).get("balance_s3_s4", {}) if metrics else {},
            "s5_intervention_count": len(intervention_list),   # VSM-005: lower = more autonomous
            "s5_intervention_cycles": len({i.get("cycle") for i in intervention_list if i.get("cycle") is not None}),
            "intervention_share": round(len({i.get("cycle") for i in intervention_list if i.get("cycle") is not None}) / cycle_count, 3) if cycle_count else 0.0,
            "eval_pass_rate": eval_summary.get("pass_rate", None),   # VSM-005: Terminal-Bench Dev Set v2
        },
        "eval": {
            "dataset": dev_metrics.get("dataset") if isinstance(dev_metrics, dict) else None,
            "harness": dev_metrics.get("harness") if isinstance(dev_metrics, dict) else None,
            "generated": dev_metrics.get("generated") if isinstance(dev_metrics, dict) else None,
            "summary": eval_summary,
            "by_difficulty": dev_metrics.get("by_difficulty", {}) if isinstance(dev_metrics, dict) else {},
            "by_category": dev_metrics.get("by_category", {}) if isinstance(dev_metrics, dict) else {},
            "trend": eval_trend,   # {current, previous, delta, direction} для S4/UI
            "history": eval_history[-30:] if isinstance(eval_history, list) else [],  # последние 30 прогонов
            "runs": runs,   # VSM-029: per-run саммари из harbor-trials/ (последние 50)
        },
        "maturation": {
            "state": maturation.get("maturation_state", "Initial State"),
            "phase_activated": maturation.get("phase_activated", []),
            "autonomy_verdict": autonomy.get("verdict", "DEPENDENT"),
            "autonomy_target": autonomy.get("target", 1.0),
            "autonomy_signs": autonomy.get("signs", {}),
            "last_primitive": maturation.get("last_primitive"),
            "last_transition": maturation.get("last_transition"),
            "child_initialized": maturation.get("child_initialized", False),
            "child_path": maturation.get("child_path"),
            "cycle_count": maturation.get("cycle_count", 0),
            "updated": maturation.get("updated"),
        },
        "audit": audit.get("findings", []) if audit else [],
        "audit_caveats": audit.get("caveats", []) if audit else [],
        "intel": intel.get("signals", []) if intel else [],
        "intel_coverage": intel.get("coverage", {}) if intel else {},
        "heartbeat": heartbeat.get("systems", {}) if heartbeat else {},
        "issues": _read_issues(),
        "history": history,
        "activity": live.get("activity", []),
        "interventions": intervention_list,   # VSM-005: S5 intervention log (публичный индикатор автономности)
    }

    MONITOR.mkdir(exist_ok=True)
    target = MONITOR / "data.js"
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    target.write_text(f"window.VSM_DATA = {payload};\n", encoding="utf-8")

    # (опц.) снэпшот дня в history.json для S4 trend
    _maybe_snapshot(history, data["metrics"])

    # VSM-025: process log + agent eval (авто-детект дельт state + скоринг 0-10).
    # Единственная точка интеграции: render_data вызывается в конце каждого
    # cycle/eval/mature/init. Read-only из state/, пишет events.json + agent_eval.json
    # + logs/process.log. Ноль правок в агентах/командах.
    try:
        from export_logs import detect_and_log
        log_report = detect_and_log()
        events_str = "seed" if log_report["seeded"] else f"{log_report['events']} events"
        data["_export_logs"] = log_report
    except Exception as e:  # лог не должен валировать телеметрию
        print(f"  ⚠ export_logs skipped: {e}")
        log_report = None

    print(f"── render_data ──")
    print(f"  project: {project}")
    print(f"  A(t): {data['metrics']['autonomy_score']} | phase: {data['metrics']['maturation_phase']}")
    pr = data['metrics'].get('eval_pass_rate')
    eval_str = f"{pr:.0%}" if pr is not None else "—"
    print(f"  eval: {eval_str} pass-rate ({data['eval']['trend']['direction']})")
    print(f"  issues: {len(data['issues'])} | units: {len(data['units'])} | activity days: {len(data['activity'])}")
    if log_report:
        print(f"  logs: {events_str} | agents: {log_report['product_agents']} product, {log_report['system_agents']} system (active)")
    print(f"  → {target.relative_to(ROOT)}")


def _maybe_snapshot(history, metrics):
    """Один снэпшот в день для S4 trend extraction."""
    today = datetime.now().date().isoformat()
    metrics = {k: v for k, v in metrics.items() if k != "token_spend_estimate"}
    snapshot = {"date": today, **metrics}
    if history and history[-1].get("date") == today:
        history[-1] = snapshot
    else:
        history.append(snapshot)
    # оставляем последние 90 дней
    history = history[-90:]
    (STATE / "history.json").write_text(
        json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _eval_trend(eval_history):
    """Trend pass-rate из eval_history.json: delta + direction.

    eval_history: list of {date, pass_rate, ...} снэпшотов (от eval/metrics.py).
    Возвращает {current, previous, delta, direction} или пустой каркас если нет.
    """
    if not eval_history or not isinstance(eval_history, list):
        return {"current": 0.0, "previous": None, "delta": 0.0, "direction": "none"}
    current = eval_history[-1].get("pass_rate", 0.0)
    if len(eval_history) < 2:
        return {"current": current, "previous": None, "delta": 0.0, "direction": "none"}
    previous = eval_history[-2].get("pass_rate", 0.0)
    delta = round(current - previous, 4)
    if delta > 0.005:
        direction = "up"
    elif delta < -0.005:
        direction = "down"
    else:
        direction = "flat"
    return {"current": current, "previous": previous, "delta": delta, "direction": direction}


if __name__ == "__main__":
    main()
