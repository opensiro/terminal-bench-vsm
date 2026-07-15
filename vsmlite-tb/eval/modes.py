"""modes — batch-фасад для 3 eval-режимов (VSM-026).

ИЗОЛИРОВАННЫЙ модуль поверх публичного API harbor_run.run_trial(task_id,
config). НЕ модифицирует harbor_*.py (зона VSM-024 агента) — только импортирует
run_trial и итерирует его по батчу задач. Если VSM-024 агент меняет internals
harbor_run, фасад остаётся рабочим (контракт = run_trial signature).

Режимы (ортогональны раннеру — профиль задаёт источник данных + файл метрик):
  run_train(config)       — dev-v2 все (или по фильтру); делегирует runner.run_all
                            (существующий путь, backward-compat).
  run_eval_test(config)   — TB-2.1 verified, N сэмплов (random seed=42).
  run_eval_dataset(config)— TB-2.1 verified, все 89 (финальный test).

Изоляция ошибок: одна задача не валит батч (try/except вокруг каждого trial).
В конце каждого батча — metrics.record_run (snapshot trend) + печать summary.
"""
from __future__ import annotations

import sys
import subprocess
from datetime import datetime

from .config import EvalConfig, VSMLITE_ROOT
from .loader import load_tasks, sample_tasks
from . import metrics


def _log(msg: str) -> None:
    """Прогресс в stderr (stdout чист для машиночитаемых результатов)."""
    print(msg, file=sys.stderr, flush=True)


def _trigger_cycle(batch_record: dict) -> None:
    """VSM-031: запустить детерминистический cycle после батча (non-fatal).

    Замыкает контур «батч → наблюдение → решение»: run_cycle.py наблюдает
    batch_summary (rule-based observations), решает (decision), при critical
    создаёт VSM-NNN, обновляет status/A(t)/cycle_count, эмитит monitor/data.js.

    Subprocess (не import): scripts/ — плоские модули без __init__.py, как
    collect_metrics.py/render_data.py. Изоляция: цикл не завязан на структуру
    пакетов eval/, падение цикла не валит батч. stdout/stderr цикла → в наш
    stderr (помечены), stdout батча остаётся машиночитаемым.
    """
    import sys as _sys
    script = VSMLITE_ROOT / "scripts" / "run_cycle.py"
    if not script.exists():
        _log(f"  ⚠ cycle skipped: {script.name} not found")
        return
    batch_id = batch_record.get("batch_id", "")
    batch_path = VSMLITE_ROOT / "state" / "batch_summaries" / f"{batch_id}.json"
    try:
        r = subprocess.run(
            [_sys.executable, str(script), "--batch", str(batch_path)],
            capture_output=True, text=True, timeout=180,
        )
        # digest цикла пишем в stderr (последняя строка = decision-строка).
        if r.stdout:
            last = [ln for ln in r.stdout.strip().splitlines() if ln.strip()][-1:]
            for ln in last:
                _log(f"  cycle: {ln}")
        if r.returncode != 0 and r.stderr:
            _log(f"  ⚠ cycle stderr: {r.stderr.strip()[-300:]}")
    except subprocess.TimeoutExpired:
        _log("  ⚠ cycle timed out (180s) — batch results intact")
    except Exception as e:
        _log(f"  ⚠ cycle failed (non-fatal): {type(e).__name__}: {e}")


def _build_batch_record(config: EvalConfig, results: list[dict],
                        started_at: datetime, finished_at: datetime,
                        wall_clock: float, summary: dict, trend: dict) -> dict:
    """VSM-031: собрать rich batch-кортеж для observability (cycle + UI).

    Поля observations/decision/issues_raised — светлые плейсхолдеры; их заполнит
    run_cycle.py (rule-based наблюдение + decision). Без cycle артефакт всё равно
    пишется (есть для UI-таймлайна батчей в monitor/).
    """
    batch_id = f"{config.profile}__{started_at.strftime('%Y%m%d-%H%M%S')}"
    per_task = [
        {
            "task_id": r.get("task_id"),
            "status": r.get("status"),
            "duration_sec": r.get("agent_duration_sec"),
            "reward": (r.get("harbor") or {}).get("reward"),
        }
        for r in results
    ]
    return {
        "batch_id": batch_id,
        "profile": config.profile,
        "timestamp": started_at.isoformat(timespec="seconds"),
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds"),
        "wall_clock_sec": round(wall_clock, 1),
        "tasks_total": len(results),
        "summary": summary,
        "trend_direction": trend["direction"],
        "trend_delta": trend["delta"],
        "per_task": per_task,
        # VSM-031 плейсхолдеры — заполняются run_cycle.py:
        "observations": [],
        "decision": "",
        "issues_raised": [],
    }


def _write_batch_summary(config: EvalConfig, batch: dict):
    """VSM-031: atomic-write batch_summary в state/batch_summaries/<id>.json."""
    import json, os, tempfile
    out_dir = config.results_dir / "batch_summaries"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{batch['batch_id']}.json"
    payload = json.dumps(batch, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(out_dir), prefix=out.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp, out)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return out


def _run_batch(task_ids: list[str], config: EvalConfig) -> dict:
    """Прогнать список task_id через harbor_run.run_trial, изолируя ошибки.

    Каждый trial → task_result dict (записывается harbor_run в metrics_file
    профиля). Ошибка одной задачи логируется, но не валит батч. В конце —
    snapshot trend + summary.

    Lazy import harbor_run: он живёт в зоне VSM-024; импортируем здесь, чтобы
    modes.py не падал при import-time если harbor-зависимости недоступны
    (sanity/list не нуждаются в harbor).
    """
    from .harbor_run import run_trial  # lazy: зона VSM-024

    total = len(task_ids)
    started_at = datetime.now()
    results = []
    for i, tid in enumerate(task_ids, 1):
        _log(f"[{i}/{total}] {tid}")
        try:
            result = run_trial(tid, config)
            if result:
                results.append(result)
            else:
                _log(f"  ✗ trial вернул пустой результат (infra error?)")
                results.append({"task_id": tid, "status": "error",
                                "error": "empty trial result"})
        except Exception as e:
            _log(f"  ✗ trial failed: {type(e).__name__}: {e}")
            results.append({"task_id": tid, "status": "error",
                            "error": f"{type(e).__name__}: {e}"})
    finished_at = datetime.now()
    wall_clock = (finished_at - started_at).total_seconds()

    # Итоговый summary (метрики уже записаны harbor_run → metrics_file профиля).
    _log("\n" + "=" * 60)
    data = metrics.load(config)
    summary = data.get("summary", {})
    _log(f"batch [{config.profile}] pass-rate: "
         f"{summary.get('passed', 0)}/{summary.get('total', 0)} = "
         f"{summary.get('pass_rate', 0.0):.1%}")

    # Snapshot trend (один в день per-режима).
    snapshot = metrics.record_run(config)
    trend = metrics.compute_trend(config)
    _log(f"trend: {trend['direction']} (delta={trend['delta']:+.1%})")
    _log(f"→ {config.dev_metrics_file}")
    _log(f"→ {metrics._history_path(config)}")

    # VSM-031: rich batch-артефакт для cycle observability. Пишется в
    # state/batch_summaries/<batch_id>.json — per-batch саммари со светлыми
    # полями. observations/decision/issues_raised — плейсхолдеры; их заполнит
    # run_cycle.py (rule-based наблюдение + decision). Без cycle артефакт всё
    # равно пишется (есть для UI-таймлайна батчей).
    batch_record = _build_batch_record(
        config, results, started_at, finished_at, wall_clock, summary, trend,
    )
    batch_path = _write_batch_summary(config, batch_record)
    _log(f"→ {batch_path}")

    # VSM-031: авто-цикл после батча — замыкает контур «наблюдение → решение».
    # Флаг no_cycle: отключить для разовых прогонов / CI smoke-тестов.
    # Non-fatal: цикл — observability слой, не должен валить батч-результаты.
    if not getattr(config, "no_cycle", False):
        _trigger_cycle(batch_record)

    return data


def run_eval_test(config: EvalConfig, sample_size: int | None = None) -> dict:
    """TB-2.1 verified, N сэплов (random seed=42) → оценка репрезентативности.

    sample_size override (CLI --sample); default = config.eval_test_sample_size.
    """
    n = sample_size if sample_size is not None else config.eval_test_sample_size
    _log(f"── eval-test: profile={config.profile}, sample={n} (seed={config.eval_test_seed}) ──")

    tasks = load_tasks(config)
    if not tasks:
        _log("нет задач для eval-test (проверьте dataset_dir)")
        return {}

    sampled = sample_tasks(tasks, n, config.eval_test_seed)
    _log(f"задач к прогону: {len(sampled)} (из {len(tasks)} загруженных)")
    _log("выборка: " + ", ".join(t.task_id for t in sampled))

    return _run_batch([t.task_id for t in sampled], config)


def run_eval_dataset(config: EvalConfig) -> dict:
    """TB-2.1 verified, все 89 → финальный test (метрика уходит в eval_dataset)."""
    _log(f"── eval-dataset: profile={config.profile} (полный прогон) ──")

    tasks = load_tasks(config)
    if not tasks:
        _log("нет задач для eval-dataset (проверьте dataset_dir)")
        return {}

    # Уважать явные фильтры/limit если заданы (точечный прогон подмножества).
    _log(f"задач к прогону: {len(tasks)}")
    return _run_batch([t.task_id for t in tasks], config)


def run_train(config: EvalConfig) -> dict:
    """train: dev-v2 все (или по фильтру) → harbor batch (VSM-024 Phase 3).

    Раньше делегировала runner.run_all (старый пайплайн container/agent_phase/
    grader). Phase 3 cleanup переключил train на harbour — тот же _run_batch, что
    eval-test/eval-dataset. runner.py/container.py/agent_phase.py/grader.py
    удалены как устаревшие (superseded VSM-024).
    """
    _log(f"── train: profile={config.profile} (harbour batch) ──")
    tasks = load_tasks(config)
    if not tasks:
        _log("нет задач для train (проверьте dataset_dir и фильтры)")
        return {}
    _log(f"задач к прогону: {len(tasks)}")
    return _run_batch([t.task_id for t in tasks], config)
