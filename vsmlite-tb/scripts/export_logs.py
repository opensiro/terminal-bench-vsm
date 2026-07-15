#!/usr/bin/env python3
"""export_logs.py — экспорт логов процесса + оценка агентов (VSM-025).

Два слоя, одна точка интеграции (render_data.py — вызывается в конце каждого
cycle/eval/mature/init). Чистый авто-детект дельт state/; ноль правок в агентах/командах.

Слой 1 — process log: сравнивает key-path'и state/ с прошлым прогоном
  (state/_events_snapshot.json), эмитит события ТОЛЬКО при реальной дельте →
  state/events.json (machine, cap 500) + logs/process.log (human, cap 1000 строк).

Слой 2 — agent eval: делегирует scripts/agent_eval.py (0-10, A-E) →
  state/agent_eval.json + сводная секция в process.log.

Первый прогон (нет snapshot) = seed: пишет snapshot без событий.

Usage (из render_data.py):
  from export_logs import detect_and_log
  detect_and_log()
"""
from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
LOGS = ROOT / "logs"

EVENTS_CAP = 500            # state/events.json: последние 500 событий
PROCESS_LOG_CAP = 1000      # logs/process.log: последние 1000 строк

# key-path'и для детекта структурных дельт (Слой 1). Файл → путь → событие.
SNAPSHOT_KEYS = [
    "maturation.json", "metrics.json", "dev_metrics.json",
    "interventions.json", "audit.json", "intel.json", "status.json",
]


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _now() -> str:
    """ISO 8601 timestamp — repo convention (render_data.py:115)."""
    return datetime.now().isoformat(timespec="seconds")


# ── Сбор текущего snapshot state (агрегат для agent_eval + детект) ──
def _collect_state() -> dict:
    """Читает state/*.json → плоский dict {имя_без_json: данные, ...}.

    Защищён от пустых/битых файлов (defensive fallback). Ключи совпадают с
    SYSTEM_FILE в agent_eval (owner-mapping системных агентов).
    """
    snap = {}
    for fname in SNAPSHOT_KEYS:
        key = fname.removesuffix(".json")
        snap[key] = _read(STATE / fname, None)
    return snap


def _read_issue_ids() -> list[str]:
    """Список id issues (для count + per-status). Markdown/YAML-agnostic: grep id."""
    ids = []
    for f in sorted((ROOT / "issues").glob("VSM-*.yaml")):
        text = f.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'^id:\s*(VSM-\d+)\s*$', text, re.M)
        if m:
            ids.append(m.group(1))
    return ids


def _read_issue_records() -> list[dict]:
    """Лёгкие issue-записи для regression-check в agent_eval."""
    records = []
    for f in sorted((ROOT / "issues").glob("VSM-*.yaml")):
        text = f.read_text(encoding="utf-8", errors="replace")
        def field(name, default=None):
            m = re.search(rf'^{name}:\s*(.+?)\s*$', text, re.M)
            return m.group(1).strip('"\'') if m else default
        records.append({
            "id": field("id", f.stem),
            "status": field("status", "triage"),
            "severity": field("severity", "S2"),
            "signal_type": field("signal_type", "gap"),
        })
    return records


# ── Детект дельт → события ──
def _detect_events(prev: dict, cur: dict, prev_issues: list[str],
                   cur_issues: list[str]) -> list[dict]:
    """Сравнивает snapshot'ы → список событий. Пустой если нет дельт (или seed)."""
    if prev is None:
        return []  # seed-прогон: событий нет
    events = []
    ts = _now()

    def emit(etype, field, frm, to, detail=""):
        events.append({
            "ts": ts, "type": etype, "field": field,
            "from": frm, "to": to, "detail": detail,
        })

    mat_p = (prev.get("maturation") or {})
    mat_c = (cur.get("maturation") or {})
    # autonomy.current
    a_p = (mat_p.get("autonomy") or {}).get("current")
    a_c = (mat_c.get("autonomy") or {}).get("current")
    if a_p != a_c and a_c is not None:
        emit("autonomy.changed", "autonomy.current", a_p, a_c,
             f"A(t) {a_p} → {a_c}")
    # autonomy.verdict
    v_p = (mat_p.get("autonomy") or {}).get("verdict")
    v_c = (mat_c.get("autonomy") or {}).get("verdict")
    if v_p != v_c and v_c:
        emit("autonomy.verdict", "autonomy.verdict", v_p, v_c,
             f"{v_p or '?'} → {v_c}")
    # phase
    ph_p = mat_p.get("maturation_state")
    ph_c = mat_c.get("maturation_state")
    if ph_p != ph_c and ph_c:
        emit("phase.transition", "maturation_state", ph_p, ph_c,
             f"{ph_p or '?'} → {ph_c}")
    # cycle_count
    cy_p = mat_p.get("cycle_count")
    cy_c = mat_c.get("cycle_count")
    if cy_p != cy_c and cy_c is not None:
        emit("cycle.completed", "cycle_count", cy_p, cy_c,
             f"#{cy_p} → #{cy_c}")

    # eval pass_rate / total
    dev_p = (prev.get("dev_metrics") or {})
    dev_c = (cur.get("dev_metrics") or {})
    s_p = (dev_p.get("summary") or {})
    s_c = (dev_c.get("summary") or {})
    if s_p.get("pass_rate") != s_c.get("pass_rate") or s_p.get("total") != s_c.get("total"):
        pr_p, pr_c = s_p.get("pass_rate"), s_c.get("pass_rate")
        emit("eval.run", "summary.pass_rate", pr_p, pr_c,
             f"{'{:.0%}'.format(pr_c) if pr_c is not None else '?'} "
             f"({s_c.get('total', 0)} tasks)")

    # metrics drift
    kpi_p = ((prev.get("metrics") or {}).get("kpi") or {})
    kpi_c = ((cur.get("metrics") or {}).get("kpi") or {})
    for k in ("coverage_ratio", "validate_pass_rate", "drift_score"):
        if kpi_p.get(k) != kpi_c.get(k):
            emit("metrics.drift", f"kpi.{k}", kpi_p.get(k), kpi_c.get(k))

    # interventions count
    iv_p = len((prev.get("interventions") or {}).get("interventions", []))
    iv_c = len((cur.get("interventions") or {}).get("interventions", []))
    if iv_p != iv_c:
        emit("intervention.added", "interventions.count", iv_p, iv_c,
             f"{iv_p} → {iv_c}")

    # issues count + new ids
    new_ids = sorted(set(cur_issues) - set(prev_issues))
    if len(cur_issues) != len(prev_issues) or new_ids:
        emit("issue.changed", "issues.count", len(prev_issues), len(cur_issues),
             (f"+{','.join(new_ids)}" if new_ids else "status deltas"))

    return events


# ── Writers ──
def _write_events(events: list[dict]) -> None:
    """Append в state/events.json (cap EVENTS_CAP)."""
    path = STATE / "events.json"
    existing = _read(path, [])
    if not isinstance(existing, list):
        existing = []
    existing.extend(events)
    existing = existing[-EVENTS_CAP:]
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def _format_log_line(ev: dict) -> str:
    """Событие → human-строка для process.log."""
    ts_short = ev["ts"][5:16].replace("T", " ")  # MM-DD HH:MM
    typ = ev["type"].split(".")[0].ljust(8)
    detail = ev.get("detail", "")
    return f"{ts_short}  {typ}  {detail}"


def _write_process_log(events: list[dict], agent_lines: list[str]) -> None:
    """Append в logs/process.log (cap PROCESS_LOG_CAP строк)."""
    LOGS.mkdir(exist_ok=True)
    path = LOGS / "process.log"
    try:
        existing = path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError):
        existing = []

    block = []
    if events:
        block.append(f"── {_now()} ──")
        block.extend(_format_log_line(e) for e in events)
    if agent_lines:
        if events:
            block.append("")
        block.append(f"── agent eval {_now()} ──")
        block.extend(agent_lines)

    if not block:
        return  # ничего нового (heartbeat пропускаем для шума ↓)

    existing.extend(block)
    existing = existing[-PROCESS_LOG_CAP:]
    path.write_text("\n".join(existing) + "\n", encoding="utf-8")


def _write_agent_eval(result: dict) -> None:
    """state/agent_eval.json — полная оценка (machine-readable)."""
    path = STATE / "agent_eval.json"
    out = {
        "_comment": "agent_eval.json — скоринг 0-10 (A-E, D<0.5=FAIL) работы агентов (VSM-025). Пишет export_logs.py из agent_eval.evaluate().",
        "generated": _now(),
        "grade_scale": "A≥9.0 | B≥7.5 | C≥5.0 (pass) | D≥2.5 (FAIL) | E<2.5",
        "trace_note": "trace_len info-only (VSM-022 superseded→VSM-024); harbor block — progressive enhancement",
        "token_note": "token-spend deferred→VSM-024 (instrumentation pending)",
        **result,
    }
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def _agent_log_lines(result: dict) -> list[str]:
    """Сводная секция agent-eval для process.log (human)."""
    lines = []
    s = result.get("summary", {})
    # breakdown
    for kind in ("by_difficulty", "by_category"):
        bd = result.get("breakdown", {}).get(kind, {})
        if bd:
            lines.append(f"  [{kind}]")
            for label, c in sorted(bd.items()):
                pr = c.get("pass_rate", 0.0)
                lines.append(f"    {label:<16} {c.get('passed', 0)}/{c.get('total', 0)} ({pr:.0%})")
    # products
    for p in result.get("product", []):
        lines.append(f"  {p['summary']}")
    # systems
    for sy in result.get("systems", []):
        lines.append(f"  {sy['summary']}")
    idle = s.get("system_idle", 0)
    if idle:
        lines.append(f"  ({idle} системных агентов idle — не оценивались)")
    return lines


# ── Точка входа (вызывается из render_data.py) ──
def detect_and_log() -> dict:
    """Авто-детект дельт state → events.json + process.log + agent_eval.json.

    Возвращает отчёт {events: N, seeded: bool, agents: {...}} для stdout-вывода
    render_data.py. Идемпотентна: seed-прогон пишет snapshot без событий.
    """
    snapshot_path = STATE / "_events_snapshot.json"
    prev_snapshot = _read(snapshot_path, None)
    cur_snapshot = _collect_state()
    prev_issues = prev_snapshot.get("_issue_ids", []) if isinstance(prev_snapshot, dict) else []
    cur_issues = _read_issue_ids()
    is_seed = prev_snapshot is None

    # детект событий (передаём агрегат с ключами-владельцами для agent_eval)
    events = _detect_events(prev_snapshot, cur_snapshot, prev_issues, cur_issues)

    # agent eval (Слой 2)
    from agent_eval import evaluate  # рядом в scripts/
    prev_issues_recs = (_read_issue_records() if is_seed else
                        [r for r in _read_issue_records() if r["id"] in set(prev_issues)])
    # prev-records не хранятся в snapshot (могли измениться); используем cur-records
    # отфильтрованные по prev_issue_ids — достаточно для regression-check.
    cur_issues_recs = _read_issue_records()
    prev_for_eval = prev_snapshot if isinstance(prev_snapshot, dict) else None
    eval_result = evaluate(prev_for_eval, cur_snapshot, prev_issues_recs, cur_issues_recs,
                           is_seed=is_seed)

    # writers
    if events:
        _write_events(events)
    _write_agent_eval(eval_result)
    agent_lines = _agent_log_lines(eval_result)
    _write_process_log(events, agent_lines)

    # обновляем snapshot (текущее состояние → база для след. прогона)
    cur_snapshot["_issue_ids"] = cur_issues
    snapshot_path.write_text(
        json.dumps(cur_snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    return {
        "events": len(events),
        "seeded": is_seed,
        "product_agents": len(eval_result.get("product", [])),
        "system_agents": len(eval_result.get("systems", [])),
    }


def main():
    """Standalone запуск (для отладки, без render_data)."""
    report = detect_and_log()
    print("── export_logs ──")
    if report["seeded"]:
        print("  seed-прогон: snapshot записан, событий нет (норма для первого прогона)")
    else:
        print(f"  событий эмитировано: {report['events']}")
    print(f"  продуктовых агентов: {report['product_agents']}")
    print(f"  системных агентов (active): {report['system_agents']}")
    print(f"  → state/events.json, state/agent_eval.json, logs/process.log")


if __name__ == "__main__":
    main()
