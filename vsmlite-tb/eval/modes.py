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

from .config import EvalConfig
from .loader import load_tasks, sample_tasks
from . import metrics


def _log(msg: str) -> None:
    """Прогресс в stderr (stdout чист для машиночитаемых результатов)."""
    print(msg, file=sys.stderr, flush=True)


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
    results = []
    for i, tid in enumerate(task_ids, 1):
        _log(f"[{i}/{total}] {tid}")
        try:
            result = run_trial(tid, config)
            if result:
                results.append(result)
            else:
                _log(f"  ✗ trial вернул пустой результат (infra error?)")
        except Exception as e:
            _log(f"  ✗ trial failed: {type(e).__name__}: {e}")
            results.append({"task_id": tid, "status": "error",
                            "error": f"{type(e).__name__}: {e}"})

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
