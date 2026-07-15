#!/usr/bin/env python3
"""run_cycle.py — детерминистический оркестратор цикла созревания (VSM-031).

Замыкает контур «наблюдение → решение» без LLM. Существует в двух режимах:
  1. BATCH-TRIGGERED — вызывается из eval/modes.py:_run_batch() после record_batch.
     Принимает batch_summary, enriches его observations/decision, авто-issue при critical.
  2. STATE-TRIGGERED — `make cycle` / CLI без батча. Наблюдает текущий aggregate
     dev_metrics.json (аккумулирует upsert по task_id — интервалы сливаются сами).

Шаги (маппинг на .claude/commands/vsmlite-cycle.md, но детерминистически, без
спавна агентов; LLM-цикл /vsmlite-cycle остаётся слоем над этим скриптом):
  1. A(t) recompute        — import autonomy; пересчёт из 5 знаков → maturation.autonomy
  2. status sweep          — health систем из state-файлов (≠ "unknown")
  3. observe               — rule-based детекторы: regression/zero_pass/infra/low/improvement
  4. decide                — needs_human_decision | ok_with_concerns | ok_no_action
  5. auto-issue (opt.)     — VSM-NNN при critical observations (monotonic id, dedup)
  6. enrich batch          — дописать observations/decision в batch_summary.json
  7. cycle_count++         — ЕДИНСТВЕННОЕ место инкремента (владение)
  8. render_data           — subprocess → monitor/data.js (+ history, export_logs)
  9. validate              — subprocess, non-fatal (warn не валит)

Главный инвариант (validate.sh): read-only из ../vsm/ и ../src/ — как collect_metrics.py.
Все записи в state/, issues/, monitor/. Non-fatal: не валит батч-вызывающего.

Usage:
  python3 scripts/run_cycle.py                 # state-mode: наблюдать текущий aggregate
  python3 scripts/run_cycle.py --batch <path>  # обработать конкретный batch_summary.json
  python3 scripts/run_cycle.py --no-issue      # не создавать VSM-NNN при critical
  python3 scripts/run_cycle.py --check         # пробный прогон без мутаций state
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# vsmlite-tb/ — корень (этот файл: scripts/run_cycle.py → parent.parent)
ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
ISSUES = ROOT / "issues"
SCRIPTS = ROOT / "scripts"

# Скрипты vsmlite лежат в scripts/ как плоские модули (без __init__.py). Для
# импорта autonomy нужно отдать scripts/ в sys.path (как делает render_data.py
# для export_logs). Вставляем ПЕРЕД собственной логикой.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


# ── helpers: read / atomic-write ──────────────────────────────────────────────

def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _atomic_write(path: Path, data) -> None:
    """tempfile в той же директории + os.replace → atomic publish.

    JSON-объекты → json.dumps; строки (plain text/YAML) → пишутся как есть.
    Переиспользует паттерн eval/metrics.py:_atomic_write (VSM-031). Ни при
    каких обстоятельствах не пишет в ../vsm/ или ../src/ (главный инвариант).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, (dict, list)):
        payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    else:
        payload = str(data)
        if not payload.endswith("\n"):
            payload += "\n"
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ── step 1: A(t) recompute ───────────────────────────────────────────────────

def _recompute_autonomy() -> tuple[dict, float, str]:
    """Пересчитать A(t) из 5 знаков → maturation.json.

    Делегирует в scripts/autonomy.py (compute + write). Возвращает op_signs,
    score и verdict для последующего status sweep / digest.
    """
    import autonomy
    op_signs, eval_result, score, verdict = autonomy.compute()
    mat_path = STATE / "maturation.json"
    mat = _read(mat_path, {})
    mat.setdefault("autonomy", {})
    sign_from = {"s5_sign": "interventions", "s4_sign": "intel",
                 "s3_sign": "units", "s1_sign": "activity"}
    mat["autonomy"].update({
        "current": score,
        "verdict": verdict,
        "signs": {k: {"value": s["value"], "from": sign_from[k], "meets": s["meets"]}
                  for k, s in op_signs.items()},
    })
    mat["autonomy"]["signs"]["eval_sign"] = {
        "value": eval_result["value"], "from": "dev_metrics", "meets": eval_result["meets"],
    }
    mat["autonomy"]["weights"] = {"operational": autonomy.W_OPERATIONAL, "eval": autonomy.W_EVAL}
    mat["updated"] = datetime.now().date().isoformat()
    _atomic_write(mat_path, mat)
    return op_signs, score, verdict


# ── step 2: status sweep (детерминистический, из state-файлов) ────────────────

def _derive_health(op_signs: dict, autonomy_score: float, autonomy_verdict: str,
                   cycle_count: int | None = None) -> dict:
    """Заполнить state/status.json: health систем ≠ "unknown".

    Health выводится из конкретных state-артефактов (не из «агент сказал»):
      S1 ← cycle_count / activity (есть циклы → active)
      S2 ← сам cycle orchestration работает → healthy
      S3 ← autonomy verdict (DEPENDENT=warn)
      S3* ← audit.json findings count
      S4 ← intel.json signals count
      S5 ← interventions count (low=healthy: мало вмешательств = автономно)

    cycle_count: передаётся извне (уже инкрементированный), чтобы S1 summary
    показывал актуальный номер цикла этого запуска.
    """
    mat = _read(STATE / "maturation.json", {})
    audit = _read(STATE / "audit.json", {})
    intel = _read(STATE / "intel.json", {})
    interventions = _read(STATE / "interventions.json", {})
    if cycle_count is None:
        cycle_count = mat.get("cycle_count", 0)

    audit_findings = len(audit.get("findings", [])) if isinstance(audit, dict) else 0
    intel_signals = len(intel.get("signals", [])) if isinstance(intel, dict) else 0
    interv_list = interventions.get("interventions", []) if isinstance(interventions, dict) else []
    interv_count = len(interv_list)

    def _h(healthy_cond, active_cond=None):
        if active_cond:
            return "active"
        return "healthy" if healthy_cond else "warn"

    systems = {
        "S1": {
            "name": "synthesis-operator",
            "health": "active" if cycle_count > 0 else "idle",
            "summary": f"cycle #{cycle_count}; orchestrating child maturation",
            "current_task": f"A(t)={autonomy_score:.3f} ({autonomy_verdict})",
        },
        "S2": {
            "name": "s2-coordinator",
            "health": "healthy",
            "summary": "cycle orchestration operational (deterministic)",
            "current_task": "no conflicts detected",
        },
        "S3": {
            "name": "s3-optimizer",
            "health": "healthy" if autonomy_verdict != "DEPENDENT" else "warn",
            "summary": f"A(t)={autonomy_score:.3f} verdict={autonomy_verdict}",
            "current_task": f"eval_sign meets={op_signs.get('eval_sign', {}).get('detail', '?')}"
                            if False else f"op signs: {sum(1 for s in op_signs.values() if s['meets'])}/4 meet",
        },
        "S3*": {
            "name": "s3-star-auditor",
            "health": "healthy" if audit_findings == 0 else "warn",
            "summary": f"{audit_findings} audit findings" if audit_findings else "no findings",
            "current_task": "idle" if audit_findings == 0 else "review findings",
        },
        "S4": {
            "name": "s4-scout",
            "health": "active" if intel_signals > 0 else "idle",
            "summary": f"{intel_signals} intel signals" if intel_signals else "no signals yet",
            "current_task": "scanning" if intel_signals == 0 else "signals in triage",
        },
        "S5": {
            "name": "s5-guardian",
            "health": "healthy",
            "summary": f"{interv_count} interventions (low=autonomous)" if interv_count == 0
                       else f"{interv_count} interventions",
            "current_task": "prepare_only (basta)",
        },
    }
    status = {
        "_comment": _read(STATE / "status.json", {}).get("_comment",
                    "status.json — health систем vsmlite (S1-S5+S3*)."),
        "generated": datetime.now().isoformat(timespec="seconds"),
        "operational_mode": "normal",
        "systems": systems,
    }
    _atomic_write(STATE / "status.json", status)
    return systems


# ── step 3: observe (rule-based детекторы) ───────────────────────────────────

# Пороги детекторов (см. план VSM-031).
REGRESSION_DELTA = -0.10   # pass_rate упал более чем на 10 п.п. → critical
IMPROVEMENT_DELTA = 0.10   # вырос более чем на 10 п.п. → info (позитив)
INFRA_ERROR_SHARE = 0.30   # >30% задач в error → infra-кластер
LOW_PASS_THRESHOLD = 0.50  # pass_rate < 50% → low_pass_rate


def _observe(summary: dict, trend: dict, per_task: list | None = None) -> list[dict]:
    """Rule-based классификация состояния батча/aggregate'а.

    summary: {total, passed, failed, error, pass_rate}
    trend: {current, previous, delta, direction} — из cycle_history (надёжный,
           не завязан на eval_history granularность).
    per_task: опц. список per-task результатов (для infra-кластер детекции).

    Возвращает observations[]: [{type, severity, detail, detector}].
    """
    obs: list[dict] = []
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    error = summary.get("error", 0)
    pass_rate = summary.get("pass_rate", 0.0)
    delta = trend.get("delta", 0.0)

    # zero_pass: ни одна задача не пройдена (при наличии задач).
    if total > 0 and passed == 0:
        obs.append({
            "type": "zero_pass", "severity": "warn",
            "detail": f"0/{total} passed — no task resolved",
            "detector": "rule:zero_pass",
        })

    # regression: pass_rate упал относительно прошлого цикла.
    if delta <= REGRESSION_DELTA:
        prev = trend.get("previous")
        obs.append({
            "type": "regression", "severity": "critical",
            "detail": f"pass_rate {prev:.1%} → {pass_rate:.1%} (delta {delta:+.1%})"
                      if prev is not None else f"pass_rate dropped (delta {delta:+.1%})",
            "detector": "rule:trend_delta",
        })

    # improvement: pass_rate вырос (позитивный сигнал).
    if delta >= IMPROVEMENT_DELTA:
        prev = trend.get("previous")
        obs.append({
            "type": "improvement", "severity": "info",
            "detail": f"pass_rate {prev:.1%} → {pass_rate:.1%} (delta {delta:+.1%})"
                      if prev is not None else f"pass_rate up (delta {delta:+.1%})",
            "detector": "rule:trend_delta",
        })

    # infra_cluster: >30% задач в error (контейнер/сеть/агент упал, не логика).
    if total > 0 and per_task is not None:
        err_count = sum(1 for t in per_task if (t or {}).get("status") == "error")
        share = err_count / total
        if share > INFRA_ERROR_SHARE:
            obs.append({
                "type": "infra_cluster", "severity": "warn",
                "detail": f"{err_count}/{total} ({share:.0%}) tasks errored — likely infra",
                "detector": "rule:infra_share",
            })
    elif total > 0 and error > 0 and (error / total) > INFRA_ERROR_SHARE:
        obs.append({
            "type": "infra_cluster", "severity": "warn",
            "detail": f"{error}/{total} ({error/total:.0%}) errors — likely infra",
            "detector": "rule:error_share",
        })

    # low_pass_rate: pass_rate < 50% при наличии задач (и не zero_pass — тот уже выше).
    if total > 0 and passed > 0 and pass_rate < LOW_PASS_THRESHOLD:
        obs.append({
            "type": "low_pass_rate", "severity": "warn",
            "detail": f"pass_rate {pass_rate:.1%} < {LOW_PASS_THRESHOLD:.0%} threshold",
            "detector": "rule:low_pass",
        })

    return obs


# ── step 3b: trend из cycle_history (надёжный, не eval_history) ───────────────

CYCLE_HISTORY_PATH = STATE / "cycle_history.json"


def _cycle_trend(current_pass_rate: float) -> dict:
    """Trend pass_rate относительно прошлого цикла.

    Использует state/cycle_history.json (собственная память цикла), а НЕ
    eval_history.json — потому что eval_history пишется только из _run_batch
    daily-snapshot'ом, и при интервальных прогонах (harbor trial start) вообще
    не пишется. cycle_history пишется каждым циклом → гранулярность = цикл.
    """
    history = _read(CYCLE_HISTORY_PATH, [])
    if not history:
        return {"current": current_pass_rate, "previous": None, "delta": 0.0, "direction": "none"}
    previous = history[-1].get("pass_rate")
    if previous is None:
        return {"current": current_pass_rate, "previous": None, "delta": 0.0, "direction": "none"}
    delta = round(current_pass_rate - previous, 4)
    if delta > 0.005:
        direction = "up"
    elif delta < -0.005:
        direction = "down"
    else:
        direction = "flat"
    return {"current": current_pass_rate, "previous": previous, "delta": delta, "direction": direction}


# ── step 4: decide ───────────────────────────────────────────────────────────

def _decide(observations: list[dict]) -> str:
    """Decision logic из observations.

    critical → needs_human_decision (триггерит auto-issue).
    warn (без critical) → ok_with_concerns.
    только info/пусто → ok_no_action.
    """
    has_critical = any(o["severity"] == "critical" for o in observations)
    warn_count = sum(1 for o in observations if o["severity"] == "warn")
    if has_critical:
        crit = [o for o in observations if o["severity"] == "critical"]
        reasons = ", ".join(o["type"] for o in crit)
        return f"needs_human_decision: {reasons}"
    if warn_count:
        return f"ok_with_concerns: {warn_count} warnings"
    return "ok_no_action"


# ── step 5: auto-issue (VSM-NNN, monotonic, dedup) ───────────────────────────

def _next_issue_id() -> int:
    """Монотонный следующий id: max(существующие) + 1.

    id никогда не переиспользуется (даже после wontfix) — инвариант CLAUDE.md.
    Glob безопасен: issues/ расшарена, но циклы не параллелятся между собой.
    """
    ids = []
    for f in ISSUES.glob("VSM-*.yaml"):
        try:
            ids.append(int(f.stem.split("-")[1]))
        except (ValueError, IndexError):
            continue
    return (max(ids) + 1) if ids else 1


def _issue_signature(observations: list[dict], batch_id: str | None) -> str:
    """Сигнатура для дедупа: не плодить issue на одно и то же состояние.

    Ключ = sorted critical-types + batch_id (если есть). Если та же комбинация
    critical-наблюдений уже в triage-статусе → не создаём повторно.
    """
    crit = sorted(o["type"] for o in observations if o["severity"] == "critical")
    return "|".join(crit) + (f"@{batch_id}" if batch_id else "")


def _existing_triage_signatures() -> set[str]:
    """Найти сигнатуры уже открытых (triage) issues — для дедупа."""
    import re
    sigs = set()
    for f in ISSUES.glob("VSM-*.yaml"):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        # Пропускаем не-triage (уже решённые).
        if not re.search(r"^status:\s*triage\s*$", text, re.MULTILINE):
            continue
        # Извлекаем dedup_signature (если записан).
        m = re.search(r"^# dedup_signature:\s*(.+)$", text, re.MULTILINE)
        if m:
            sigs.add(m.group(1).strip())
    return sigs


_SIGNAL_MAP = {
    "regression": "drift",
    "zero_pass": "quality",
    "low_pass_rate": "quality",
    "infra_cluster": "gap",
    "improvement": "gap",
}


def _create_vsm_issue(observations: list[dict], batch_id: str | None,
                      summary: dict, trend: dict) -> str | None:
    """Создать issues/VSM-NNN.yaml при critical observations.

    Монотонный id, source_system=S4 (rule-based эмулирует S4-скан), severity=S2.
    needs_human_decision=true, status=triage (basta: prepare_only — готовит, не
    постановляет). Дедуп: если сигнатура уже в triage → пропускаем.

    Возвращает путь к созданному файлу или None (дедуп / нет critical).
    """
    crit = [o for o in observations if o["severity"] == "critical"]
    if not crit:
        return None

    sig = _issue_signature(observations, batch_id)
    if sig in _existing_triage_signatures():
        return None

    n = _next_issue_id()
    issue_id = f"VSM-{n:03d}"
    today = datetime.now().date().isoformat()
    signal_type = _SIGNAL_MAP.get(crit[0]["type"], "gap")

    title_reason = ", ".join(o["type"] for o in crit)
    title = f"Batch {batch_id or 'aggregate'}: {title_reason} (auto, cycle)"
    if len(title) > 80:
        title = title[:77] + "..."

    evidence_lines = [
        f"state/dev_metrics.json#summary: pass_rate={summary.get('pass_rate', 0.0):.1%} "
        f"({summary.get('passed', 0)}/{summary.get('total', 0)})",
        f"trend: delta={trend.get('delta', 0.0):+.1%} direction={trend.get('direction', '?')}",
    ]
    if batch_id:
        evidence_lines.append(f"state/batch_summaries/{batch_id}.json")
    for o in crit:
        evidence_lines.append(f"{o['detector']}: {o['detail']}")

    content = f"""# Auto-created by scripts/run_cycle.py (VSM-031 cycle automation).
# dedup_signature: {sig}
id: {issue_id}
source_system: S4            # rule-based scan эмулирует S4-наблюдение батча
signal_type: {signal_type}   # auto-mapped from observation type
severity: S2                 # бьёт по核心 A(t) — self-correcting контур
target_unit: child           # продукт плохо справился (eval pass-rate)

title: "{title}"
summary: |
  Автоматически обнаружено детерминистическим cycle (run_cycle.py) после
  eval-батча. Critical observations: {title_reason}.

  Это фиксация gap'а для human-decision. S5 (basta: prepare_only) готовит
  решение, не постановляет. См. observations в batch_summary.

evidence:"""
    for ev in evidence_lines:
        content += f"\n  - \"{ev}\""
    content += f"""

proposal: |
  Non-binding. Возможные направления (решает человек):
  - диагностика регрессии (какой commit/фактор вызвал просадку pass_rate);
  - infra-фикс (если infra_cluster — контейнер/сеть/агент setup);
  - принять как known-noise (если single-task flake).

acceptance:
  - "pass_rate восстанавливается выше порога в следующем цикле (cycle_history)"
  - "root cause идентифицирован и зафиксирован в issues"

needs_human_decision: true

# Observations (авто-классификация run_cycle.py; полные детали — в batch_summary):
"""
    # Каждый observation — YAML-flow строка, безопасно комментируется построчно.
    for o in observations:
        content += f"#   [{o['severity']}] {o['type']}: {o['detail']} ({o['detector']})\n"
    content += f"""
status: triage
decision: ""
selected_options: []

created: {today}
updated: {today}
"""
    path = ISSUES / f"{issue_id}.yaml"
    _atomic_write(path, content)
    return issue_id


# ── step 6: enrich batch_summary ─────────────────────────────────────────────

def _enrich_batch(batch_summary: dict, observations: list[dict],
                  decision: str, issue_id: str | None) -> None:
    """Дописать observations/decision/issues_raised в batch_summary.json.

    batch_summary пришёл из eval/metrics.record_batch (layer-1 VSM-030 seam с
    пустыми плейсхолдерами). Этот шаг — layer-2/3 (наблюдение + решение).
    """
    batch_id = batch_summary.get("batch_id")
    if not batch_id:
        return
    batch_summary["observations"] = observations
    batch_summary["decision"] = decision
    batch_summary["issues_raised"] = [issue_id] if issue_id else []
    batch_summary["decided_at"] = datetime.now().isoformat(timespec="seconds")
    out = STATE / "batch_summaries" / f"{batch_id}.json"
    _atomic_write(out, batch_summary)


# ── step 7: cycle_count++ (ЕДИНСТВЕННЫЙ владелец) ────────────────────────────

def _increment_cycle_count() -> int:
    """Инкремент cycle_count в maturation.json.

    КОНТРАКТ: это ЕДИНСТВЕННОЕ место во всём коде, где cycle_count пишется
    (раньше инкремент был «поручен» LLM в prose-prompt vsmlite-cycle.md:49 —
    ни один скрипт его не делал, cycle_count застрял на 0). Сюда же пишем
    last_cycle_at для observability.
    """
    mat_path = STATE / "maturation.json"
    mat = _read(mat_path, {})
    mat["cycle_count"] = int(mat.get("cycle_count", 0)) + 1
    mat["last_cycle_at"] = datetime.now().isoformat(timespec="seconds")
    _atomic_write(mat_path, mat)
    return mat["cycle_count"]


# ── step 8/9: render_data + validate (subprocess, non-fatal) ─────────────────

def _run_subprocess(label: str, cmd: list[str]) -> bool:
    """Запустить subprocess, вернуть True если exit 0. Non-fatal: логирует."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            # validate может вернуть YELLOW (warn) — это exit 0, ок. RED=exit 1.
            print(f"  ⚠ {label}: exit {r.returncode}", file=sys.stderr)
            if r.stderr:
                print(r.stderr[-500:], file=sys.stderr)
        return r.returncode == 0
    except Exception as e:
        print(f"  ⚠ {label} failed (non-fatal): {type(e).__name__}: {e}", file=sys.stderr)
        return False


# ── cycle_history (собственная память цикла для trend) ───────────────────────

def _record_cycle_history(cycle: int, pass_rate: float, autonomy_score: float,
                          verdict: str, decision: str, issue_id: str | None) -> None:
    """Записать точку в state/cycle_history.json.

    Каждый цикл = одна точка. Гранулярность = цикл (не день, как eval_history).
    Нужно для надёжного trend в обоих режимах (batch / state-triggered).
    """
    history = _read(CYCLE_HISTORY_PATH, [])
    history.append({
        "cycle": cycle,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "pass_rate": round(pass_rate, 4),
        "autonomy": round(autonomy_score, 3),
        "verdict": verdict,
        "decision": decision,
        "issue_created": issue_id,
    })
    history = history[-200:]  # потолок хранения
    _atomic_write(CYCLE_HISTORY_PATH, history)


# ── orchestrator ─────────────────────────────────────────────────────────────

def run_cycle(batch_summary: dict | None = None, *,
              auto_issue: bool = True, check_only: bool = False) -> dict:
    """Один цикл созревания (детерминистический, без LLM).

    batch_summary: если передан (batch-mode) — enrich его + observe батч.
                   если None (state-mode) — observe текущий aggregate dev_metrics.
    auto_issue: создавать VSM-NNN при critical (default True).
    check_only: пробный прогон — без мутаций state (только отчёт).

    Возвращает {cycle, observations, decision, issue_created, autonomy, verdict}.
    """
    # 1. A(t) recompute.
    op_signs, score, verdict = _recompute_autonomy() if not check_only else (None, 0.0, "?")
    if check_only:
        import autonomy
        op_signs, eval_result, score, verdict = autonomy.compute()

    # Определяем summary для наблюдения.
    if batch_summary is not None:
        summary = batch_summary.get("summary", {})
        per_task = batch_summary.get("per_task")
        batch_id = batch_summary.get("batch_id")
    else:
        # State-mode: читаем aggregate dev_metrics.json (аккумулирует по task_id).
        dm = _read(STATE / "dev_metrics.json", {})
        summary = dm.get("summary", {})
        per_task = None
        batch_id = None

    pass_rate = summary.get("pass_rate", 0.0)

    # 7. cycle_count++ (ЕДИНСТВЕННЫЙ writer) — ПЕРЕД status sweep, чтобы
    # status.json показывал актуальный номер цикла в S1 summary.
    cycle = _read(STATE / "maturation.json", {}).get("cycle_count", 0)
    if not check_only:
        cycle = _increment_cycle_count()

    # 2. status sweep (только при реальной записи).
    if not check_only:
        _derive_health(op_signs or {}, score, verdict, cycle)

    # 3. observe: trend из cycle_history (надёжный).
    trend = _cycle_trend(pass_rate)
    observations = _observe(summary, trend, per_task)

    # 4. decide.
    decision = _decide(observations)

    # 5. auto-issue.
    issue_id = None
    if auto_issue and not check_only:
        issue_id = _create_vsm_issue(observations, batch_id, summary, trend)

    # 6. enrich batch (если batch-mode).
    if batch_summary is not None and not check_only:
        _enrich_batch(batch_summary, observations, decision, issue_id)

    # cycle_history (для trend следующего цикла).
    if not check_only:
        _record_cycle_history(cycle, pass_rate, score, verdict, decision, issue_id)

    # 8. render_data (subprocess → monitor/data.js).
    if not check_only:
        _run_subprocess("render_data",
                        [sys.executable, str(SCRIPTS / "render_data.py")])

    # 9. validate (non-fatal).
    validate_ok = True
    if not check_only:
        validate_ok = _run_subprocess("validate", ["bash", str(SCRIPTS / "validate.sh")])

    return {
        "cycle": cycle,
        "mode": "batch" if batch_summary is not None else "state",
        "batch_id": batch_id,
        "pass_rate": round(pass_rate, 4),
        "trend": trend,
        "observations": observations,
        "decision": decision,
        "issue_created": issue_id,
        "autonomy": round(score, 3),
        "verdict": verdict,
        "validate_ok": validate_ok,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def _print_digest(report: dict) -> None:
    """Короткий человекочитаемый digest (короче cycle_digest.py)."""
    print(f"── cycle #{report['cycle']} ({report['mode']}-mode) ──")
    pr = report["pass_rate"]
    trend = report["trend"]
    arrow = {"up": "↑", "down": "↓", "flat": "→", "none": "·"}.get(trend["direction"], "?")
    prev = f" (prev {trend['previous']:.1%})" if trend.get("previous") is not None else ""
    print(f"  A(t)={report['autonomy']} [{report['verdict']}]  pass_rate={pr:.1%} {arrow}{prev}")
    if report["observations"]:
        for o in report["observations"]:
            mark = {"critical": "⚡", "warn": "⚠", "info": "▸"}.get(o["severity"], "·")
            print(f"  {mark} {o['type']}: {o['detail']}")
    else:
        print("  ▸ no observations")
    print(f"  decision: {report['decision']}")
    if report["issue_created"]:
        print(f"  ⚡ created {report['issue_created']} (needs_human_decision)")
    print(f"  validate: {'GREEN' if report['validate_ok'] else 'check stderr'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="run_cycle",
        description="vsmlite cycle — детерминистический оркестр созревания (VSM-031)",
    )
    parser.add_argument("--batch", type=Path, default=None,
                        help="обработать конкретный batch_summary.json (batch-mode)")
    parser.add_argument("--no-issue", action="store_true",
                        help="не создавать VSM-NNN при critical observations")
    parser.add_argument("--check", action="store_true",
                        help="пробный прогон без мутаций state (dry-run)")
    args = parser.parse_args()

    batch_summary = None
    if args.batch:
        batch_summary = _read(args.batch, None)
        if batch_summary is None:
            print(f"не читается batch_summary: {args.batch}", file=sys.stderr)
            sys.exit(2)

    report = run_cycle(
        batch_summary=batch_summary,
        auto_issue=not args.no_issue,
        check_only=args.check,
    )
    _print_digest(report)


if __name__ == "__main__":
    main()
