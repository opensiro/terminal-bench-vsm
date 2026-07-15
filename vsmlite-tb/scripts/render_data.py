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
  state/batch_summaries/ → batches (per-batch саммари + cycle observations, VSM-030)
  state/cycle_history.json → cycle_history (trend per-cycle, VSM-031)

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


def _run_config(cfg: dict, meta: dict):
    """VSM-029: светлые конфиг-поля trial'а для деталей в мониторе.

    Whitelist: только известные безопасные поля. agent.env намеренно исключён —
    там могут быть секреты (API keys, tokens). meta — agent_result.metadata
    (adapter/adapter_version).
    """
    agent = cfg.get("agent") or {}
    env = cfg.get("environment") or {}
    return {
        "adapter": agent.get("import_path"),
        "adapter_name": meta.get("adapter"),
        "adapter_version": meta.get("adapter_version"),
        "model_name": agent.get("model_name"),
        "timeout_multiplier": cfg.get("timeout_multiplier"),
        "agent_timeout_multiplier": cfg.get("agent_timeout_multiplier"),
        "verifier_timeout_multiplier": cfg.get("verifier_timeout_multiplier"),
        "environment_type": env.get("type"),
        "install_only": cfg.get("install_only"),
    }


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
                # VSM-029 follow-up: светлые конфиг-поля из result.json:config.
                # agent.env намеренно НЕ поднимаем (там секреты: API keys и т.п.).
                "config": _run_config(r.get("config") or {}, meta),
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


def _collect_batches(batches_dir: Path, limit: int = 50):
    """VSM-030: per-batch саммари из state/batch_summaries/ для таймлайна батчей.

    Каждый batch_summary.json пишется eval/modes.py:_run_batch (через
    metrics.record_batch) и enrich'ится scripts/run_cycle.py (observations[],
    decision, issues_raised). Это артефактный слой контура «наблюдение → решение»:
    таймлайн показывает «что cycle увидел в батче → какое решение принял».

    Возвращает светлые поля (без тяжёлого per_task, который в data.js не нужен —
    детали по клику → файл). Сортировка по timestamp desc, последние limit.
    Один битый batch не валилит сбор (skip + continue).
    """
    if not batches_dir.exists():
        return []
    batches = []
    for f in sorted(batches_dir.glob("*.json"), reverse=True):
        try:
            b = json.loads(f.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            continue
        if not isinstance(b, dict):
            continue
        batches.append({
            "batch_id": b.get("batch_id"),
            "profile": b.get("profile"),
            "timestamp": b.get("timestamp") or b.get("started_at"),
            "wall_clock_sec": b.get("wall_clock_sec"),
            "workers": b.get("workers"),
            "tasks_total": b.get("tasks_total") or len(b.get("per_task", [])),
            "summary": b.get("summary", {}),
            "trend_direction": b.get("trend_direction"),
            "trend_delta": b.get("trend_delta"),
            # cycle-enriched (run_cycle.py заполняет; пусто если батч без cycle):
            "observations": b.get("observations", []),
            "decision": b.get("decision", ""),
            "issues_raised": b.get("issues_raised", []),
            "decided_at": b.get("decided_at"),
        })
    # сортировка по timestamp desc (None — в конец)
    batches.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return batches[:limit]


def _read_cycle_history(limit: int = 50):
    """VSM-031: state/cycle_history.json — память цикла для trend (гранулярность = цикл).

    Пишется каждым запуском run_cycle.py: {cycle, timestamp, pass_rate, autonomy,
    verdict, decision, issue_created}. В отличие от eval_history (daily-snapshot
    из _run_batch) — пишется каждым циклом, надёжна для интервальных прогонов.
    Возвращает последние limit записей (asc — для trend-графика по времени).
    """
    history = _read(STATE / "cycle_history.json", [])
    if not isinstance(history, list):
        return []
    return history[-limit:]


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
    # VSM-030: per-batch саммари из state/batch_summaries/ (cycle-enriched)
    batches = _collect_batches(STATE / "batch_summaries")
    # VSM-031: cycle_history — память цикла для trend (гранулярность = цикл)
    cycle_history = _read_cycle_history()

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
        # VSM-030: per-batch саммари (cycle-enriched: observations/decision/issues).
        # Таймлайн «что cycle увидел в батче → какое решение принял».
        "batches": batches,
        # VSM-031: cycle_history — trend pass_rate/A(t) per-cycle (надёжнее
        # eval_history для интервальных прогонов: пишется каждым циклом).
        "cycle_history": cycle_history,
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
    print(f"  batches: {len(data['batches'])} (cycle-enriched) | cycle_history: {len(data['cycle_history'])} cycles")
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
