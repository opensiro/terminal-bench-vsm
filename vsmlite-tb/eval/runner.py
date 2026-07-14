"""runner — оркестрация eval-прогона одной задачи и батча.

Полный цикл одной задачи (run_single):
  1. download (если нужно) → load task
  2. membrane translate → verify neutrality (мембрана VSM-002)
  3. container build + start (Docker песочница)
  4. agent phase (harness + docker-exec MCP bridge) — продукт решает задачу
  5. grade (копировать tests/, запустить test.sh, прочитать reward.txt)
  6. container stop + remove (контекст-менеджер гарантирует)
  7. record → state/dev_metrics.json (метрика автономности A(t))

run_all: итерация по задачам (с фильтрами), агрегация, печать итогов.
Каждая задача изолирована: ошибка одной не валит батч. Контейнер всегда
останавливается (try/finally + контекст-менеджер TBContainer).
"""
from __future__ import annotations

import sys
import traceback
from dataclasses import asdict
from datetime import datetime

from .agent_phase import run_agent_phase
from .config import EvalConfig
from .container import ContainerError, TBContainer
from .grader import grade
from .loader import TBTask, load_tasks
from . import membrane
from . import metrics


def _log(msg: str) -> None:
    """Прогресс в stderr (stdout чист для машиночитаемых результатов)."""
    print(msg, file=sys.stderr, flush=True)


def _find_task(task_id: str, config: EvalConfig) -> TBTask | None:
    """Найти задачу по task_id, снимая фильтры (run --task точечный)."""
    lookup_config = EvalConfig(
        dataset_dir=config.dataset_dir,
        product_src=config.product_src,
        harness_type=config.harness_type,
        hf_token=config.hf_token,
    )
    lookup_config.filter_task_ids = [task_id]
    tasks = load_tasks(lookup_config)
    return tasks[0] if tasks else None


def run_single(task_id: str, config: EvalConfig) -> dict:
    """Прогнать одну задачу. Возвращает task_result dict (для metrics.record).

    Статусы: passed | failed | error (error = инфраструктурный сбой: build/мембрана/...).
    """
    _log(f"── task: {task_id} ──")

    # 1. Найти задачу
    task = _find_task(task_id, config)
    if task is None:
        _log(f"  ✗ задача не найдена: {task_id}")
        result = _base_result(task, config, status="error", error="task not found")
        metrics.record(config, result)
        return result

    # 2. Мембрана → нейтральный prompt
    try:
        task_prompt = membrane.translate(task)
        membrane.verify_neutrality(task_prompt)
    except ValueError as e:
        _log(f"  ✗ membrane leak: {e}")
        result = _base_result(task, config, status="error", error=f"membrane: {e}")
        metrics.record(config, result)
        return result

    # 3-6. Контейнер + фаза агента + грейдинг (контекст-менеджер → гарантированная очистка)
    try:
        with TBContainer(task, config) as container:
            # 4. Фаза агента
            _log(f"  → agent phase ({config.harness_type}, "
                 f"timeout={int(task.meta.agent_timeout_sec)}s)…")
            agent_result = run_agent_phase(container, task_prompt, config)
            _log(f"  ← agent: exit={agent_result.exit_code}, "
                 f"trace={len(agent_result.trace)}, "
                 f"obs={len(agent_result.failure_observations)}, "
                 f"dur={agent_result.duration_sec:.0f}s")

            # 5. Грейдинг
            _log(f"  → grade (verifier timeout="
                 f"{int(task.meta.verifier_timeout_sec)}s)…")
            grade_result = grade(container, config)
            status = "passed" if grade_result.passed else "failed"
            pytest_str = ""
            if grade_result.pytest_passed is not None:
                pytest_str = (f", pytest={grade_result.pytest_passed} passed/"
                              f"{grade_result.pytest_failed or 0} failed")
            _log(f"  ← grade: {'PASS' if grade_result.passed else 'FAIL'} "
                 f"(reward={grade_result.reward_raw!r}{pytest_str})")

            result = _base_result(task, config, status=status)
            result["agent_duration_sec"] = round(agent_result.duration_sec, 1)
            result["agent_exit_code"] = agent_result.exit_code
            result["trace_len"] = len(agent_result.trace)
            result["failure_obs_count"] = len(agent_result.failure_observations)
            result["timed_out"] = agent_result.timed_out
            result["pytest_passed"] = grade_result.pytest_passed
            result["pytest_failed"] = grade_result.pytest_failed
            if grade_result.pytest_error:
                result["grade_error"] = grade_result.pytest_error

    except ContainerError as e:
        _log(f"  ✗ container: {e}")
        result = _base_result(task, config, status="error", error=f"container: {e}")
    except Exception as e:
        _log(f"  ✗ unexpected: {e}")
        _log(traceback.format_exc())
        result = _base_result(
            task, config, status="error",
            error=f"{type(e).__name__}: {e}",
        )

    metrics.record(config, result)
    _log(f"  → recorded: {result['status']}")
    return result


def run_all(config: EvalConfig) -> dict:
    """Прогнать все задачи (по фильтрам config). Печать итогового summary."""
    _log(f"── run-all: фильтры [{config.task_filter_description()}] ──")
    tasks = load_tasks(config)
    if not tasks:
        _log("нет задач для прогона (проверьте dataset_dir и фильтры)")
        return {}

    _log(f"задач к прогону: {len(tasks)}")
    results = []
    for i, task in enumerate(tasks, 1):
        _log(f"\n[{i}/{len(tasks)}] {task.task_id}")
        result = run_single(task.task_id, config)
        results.append(result)

    # Итоговый summary
    _log("\n" + "=" * 60)
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    error = sum(1 for r in results if r["status"] == "error")
    total = len(results)
    pr = passed / total if total else 0.0
    _log(f"batch pass-rate: {passed}/{total} = {pr:.1%}  "
         f"(failed={failed}, error={error})")

    # Зафиксировать снэпшот прогона в eval_history.json (trend для S4/autonomy)
    snapshot = metrics.record_run(config)
    trend = metrics.compute_trend(config)
    _log(f"trend: {trend['direction']} (delta={trend['delta']:+.1%})")
    _log(f"→ {config.dev_metrics_file}")
    _log(f"→ {config.results_dir / 'eval_history.json'}")

    return metrics.load(config)


def _base_result(
    task: TBTask | None, config: EvalConfig, status: str, error: str = "",
) -> dict:
    """Каркас task_result dict с метаполями (для агрегации by_category/difficulty)."""
    return {
        "task_id": task.task_id if task else "?",
        "status": status,
        "passed": status == "passed",
        "category": task.meta.category if task else "unknown",
        "difficulty": task.meta.difficulty if task else "unknown",
        "agent_duration_sec": 0.0,
        "trace_len": 0,
        "failure_obs_count": 0,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "error": error or None,
    }
