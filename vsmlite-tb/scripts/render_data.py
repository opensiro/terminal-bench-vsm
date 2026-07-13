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

    autonomy = maturation.get("autonomy", {}) if maturation else {}
    kpi = metrics.get("kpi", {}) if metrics else {}
    intervention_list = interventions.get("interventions", []) if isinstance(interventions, dict) else []
    cycle_count = maturation.get("cycle_count", 0) if maturation else 0

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

    print(f"── render_data ──")
    print(f"  project: {project}")
    print(f"  A(t): {data['metrics']['autonomy_score']} | phase: {data['metrics']['maturation_phase']}")
    print(f"  issues: {len(data['issues'])} | units: {len(data['units'])} | activity days: {len(data['activity'])}")
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


if __name__ == "__main__":
    main()
