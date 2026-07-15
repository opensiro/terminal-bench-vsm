#!/usr/bin/env python3
"""cycle_digest.py — собирает REPL-дайджест для s5-guardian (центр UX vsmlite).

Читает state/*.json + issues/*.yaml и формирует человекочитаемую сводку:
  - что изменилось (delta A(t)/maturation с прошлого цикла)
  - A(t) текущий + trend
  - maturation_state + готовность к фазе (по emergence-критериям)
  - критические запросы (алгедоник)
  - решения, требующие человека (VSM-NNN needs_human_decision)
  - operational итог

Вывод — в stdout (s5-guardian дописывает варианты и отдаёт в REPL).

Usage:
  python3 scripts/cycle_digest.py
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _pending_human_issues():
    """VSM-NNN со status=triage и needs_human_decision=true."""
    pending = []
    for f in sorted((ROOT / "issues").glob("VSM-*.yaml")):
        text = f.read_text(encoding="utf-8", errors="replace")
        def field(name, default=None):
            m = re.search(rf'^{name}:\s*(.+?)\s*$', text, re.M)
            return m.group(1).strip('"\'') if m else default
        def bool_field(name):
            m = re.search(rf'^{name}:\s*(\w+)', text, re.M)
            return bool(m and m.group(1).lower() == "true")
        if field("status", "triage") == "triage" and bool_field("needs_human_decision"):
            pending.append({
                "id": field("id"),
                "title": field("title"),
                "severity": field("severity"),
                "signal_type": field("signal_type"),
                "source_system": field("source_system"),
            })
    return pending


def _eval_line(dev_metrics, eval_history):
    """Строка eval pass-rate + trend для REPL-дайджеста S5.

    Формат: «▸ eval: 42% (↑ +4% от прошлого прогона, 42/100)» или
    «▸ eval: не запускался (make eval-all для прогона)».
    """
    if not dev_metrics or not isinstance(dev_metrics, dict):
        return "▸ eval: не запускался (`make eval-all` для прогона)"
    summary = dev_metrics.get("summary", {})
    total = summary.get("total", 0)
    if total == 0:
        return "▸ eval: 0 задач (`make eval-all` для прогона)"
    pass_rate = summary.get("pass_rate", 0.0)
    passed = summary.get("passed", 0)

    # trend из eval_history
    trend_str = ""
    if eval_history and isinstance(eval_history, list) and len(eval_history) >= 2:
        current = eval_history[-1].get("pass_rate", 0.0)
        previous = eval_history[-2].get("pass_rate", 0.0)
        delta = current - previous
        if delta > 0.005:
            arrow = "↑"
        elif delta < -0.005:
            arrow = "↓"
        else:
            arrow = "→"
        trend_str = f" ({arrow} {delta:+.0%} от прошлого прогона)"
    elif eval_history:
        trend_str = " (первый прогон)"

    return f"▸ eval: **{pass_rate:.0%}**{trend_str} — {passed}/{total} tasks"


def _cycle_observation_block():
    """VSM-030/031: блок observations/decision последнего cycle из cycle_history.

    Даёт S5 контекст «что детерминистический cycle уже обнаружил» ДО глубокого
    LLM-анализа. cycle_history пишется каждым run_cycle.py; последний batch_summary
    (state/batch_summaries/) содержит полные observations[].

    Возвращает список строк (пустой если cycle_history нет) — последний cycle:
    decision + observations (critical/warn/info) + issue если создан.
    """
    ch = _read(STATE / "cycle_history.json", [])
    if not isinstance(ch, list) or not ch:
        return []
    last = ch[-1]
    lines = []
    cycle_n = last.get("cycle", "?")
    decision = last.get("decision", "")
    issue = last.get("issue_created")
    lines.append(f"▸ cycle #{cycle_n} (детерминистический): **{decision}**")
    if issue:
        lines.append(f"  ⚡ auto-created {issue} (needs_human_decision)")

    # последние observations из последнего batch_summary (если есть).
    bs_dir = STATE / "batch_summaries"
    if bs_dir.exists():
        # последний по timestamp (mtime — proxy; batch_id содержит дату).
        summaries = []
        for f in bs_dir.glob("*.json"):
            try:
                b = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(b, dict):
                    summaries.append(b)
            except (json.JSONDecodeError, OSError):
                continue
        summaries.sort(key=lambda x: x.get("timestamp") or x.get("batch_id") or "",
                       reverse=True)
        if summaries:
            obs = summaries[0].get("observations", [])
            if obs:
                lines.append(f"  observations ({len(obs)}):")
                for o in obs[:6]:  # потолок 6 в дайджесте
                    sev = o.get("severity", "?")
                    mark = {"critical": "⚡", "warn": "⚠", "info": "▸"}.get(sev, "·")
                    lines.append(f"    {mark} [{sev}] {o.get('type','?')}: {o.get('detail','')}")
    return lines





def main():
    mat = _read(STATE / "maturation.json", {})
    status = _read(STATE / "status.json", {})
    audit = _read(STATE / "audit.json", {})
    intel = _read(STATE / "intel.json", {})
    dev_metrics = _read(STATE / "dev_metrics.json", {})
    eval_history = _read(STATE / "eval_history.json", [])

    autonomy = mat.get("autonomy", {}) if mat else {}
    score = autonomy.get("current", 0.0)
    verdict_a = autonomy.get("verdict", "DEPENDENT")
    phase = mat.get("maturation_state", "Initial State")
    cycle = mat.get("cycle_count", 0)

    # eval pass-rate (VSM-005 входной индикатор) + trend
    eval_line = _eval_line(dev_metrics, eval_history)

    pending = _pending_human_issues()
    critical = [p for p in pending if p["severity"] in ("S0", "S1")
                or p["signal_type"] == "algedonic"]
    decisions = [p for p in pending if p not in critical]

    # Findings red из audit
    red_findings = [f for f in (audit.get("findings", []) if audit else [])
                    if f.get("verdict") == "red"]

    lines = []
    lines.append(f"## Цикл {cycle} — digest")
    lines.append("")
    lines.append(f"▸ A(t): **{score}** ({verdict_a}) | maturation: **{phase}**")
    lines.append(eval_line)
    # VSM-030/031: что детерминистический cycle уже обнаружил (контекст для S5).
    cycle_lines = _cycle_observation_block()
    if cycle_lines:
        lines.extend(cycle_lines)
    if red_findings:
        lines.append(f"▸ ⚠️ S3* audit: {len(red_findings)} RED finding(s) — см. state/audit.json")
    if intel and intel.get("signals"):
        lines.append(f"▸ S4: {len(intel['signals'])} signal(s) (см. state/intel.json)")

    lines.append("")
    if critical:
        lines.append("⚡ **Критические (алгедоник):**")
        for c in critical:
            lines.append(f"   • {c['id']} [{c['severity']}/{c['signal_type']}]: {c['title']}")
    else:
        lines.append("⚡ Критические: нет")

    lines.append("")
    if decisions:
        lines.append("❓ **Решения для тебя:**")
        for d in decisions:
            lines.append(f"   • {d['id']} [{d['source_system']}]: {d['title']}")
            lines.append(f"     `[accept | defer | wontfix]` → /vsmlite-decide {d['id']} <...>")
    else:
        lines.append("❓ Решения для тебя: нет (operational only)")

    lines.append("")
    lines.append("▸ Operational: S3/synthesis-operator продолжат без тебя (если нет blocked).")
    lines.append("")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
