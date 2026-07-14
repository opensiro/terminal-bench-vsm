"""grader — честный outcome-based грейдинг TB-задачи.

Terminal-Bench convention: tests/test.sh внутри контейнера пишет '1' или '0'
в /logs/verifier/reward.txt. Pass iff reward == '1'.

Анти-reward-hacking: tests/ копируются в контейнер ПОСЛЕ фазы агента — агент
никогда не видит тестов и не может подсмотреть ожидаемые значения.

Дополнительно: мягкая распаковка pytest-сводки из stdout (сколько PASSED/FAILED)
для richer signal, но итоговый вердикт определяется только reward.txt.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import CONTAINER_REWARD, CONTAINER_TESTS, EvalConfig
from .container import TBContainer


@dataclass
class GradeResult:
    """Результат грейдинга одной задачи."""

    passed: bool = False
    reward_raw: str = ""           # содержимое reward.txt (обрезанное)
    test_exit_code: int = -1
    test_stdout: str = ""          # обрезанное до ~4000 символов
    test_stderr: str = ""
    pytest_passed: int | None = None   # распарсено из summary, если найдено
    pytest_failed: int | None = None
    pytest_error: str | None = None    # причина если грейдинг не удался
    timed_out: bool = False


# pytest summary line: "=== 3 passed, 1 failed in 1.23s ===" или "=== 5 passed ==="
PYTEST_SUMMARY_RE = re.compile(
    r"=+\s*(?:(\d+)\s*passed)?\s*,?\s*(?:(\d+)\s*failed)?\s*,?\s*(?:(\d+)\s*skipped)?\s*"
    r"(?:(\d+)\s*errors?)?\s*in\s*[\d.]+s\s*=+",
    re.IGNORECASE,
)


def _parse_pytest_summary(stdout: str) -> tuple[int | None, int | None]:
    """Извлечь passed/failed из pytest summary. (None, None) если не найдено."""
    m = PYTEST_SUMMARY_RE.search(stdout)
    if not m:
        return None, None
    passed = int(m.group(1)) if m.group(1) else 0
    failed = int(m.group(2)) if m.group(2) else 0
    errors = int(m.group(4)) if m.group(4) else 0
    return passed, failed + errors


def grade(container: TBContainer, config: EvalConfig) -> GradeResult:
    """Проверить решение: скопировать tests/, запустить test.sh, прочитать reward.

    Предусловие: контейнер запущен, фаза агента завершена (state контейнера
    содержит результат работы агента).
    """
    result = GradeResult()
    task = container.task

    # 1. Копировать tests/ в контейнер (ПОСЛЕ фазы агента).
    if not task.tests_dir.exists():
        result.pytest_error = f"tests/ отсутствует: {task.tests_dir}"
        return result

    try:
        container.cp_to(task.tests_dir, CONTAINER_TESTS)
    except Exception as e:
        result.pytest_error = f"cp tests/ failed: {e}"
        return result

    # test.sh должен быть внутри tests/ → /tests/test.sh
    test_script = f"{CONTAINER_TESTS}/test.sh"
    timeout = int(task.meta.verifier_timeout_sec or config.default_verifier_timeout_sec)

    # 2. Запустить test.sh внутри контейнера.
    try:
        proc = container.exec(
            f"chmod +x {test_script} 2>/dev/null; bash {test_script}",
            timeout=timeout,
        )
        result.test_exit_code = proc.returncode
        result.test_stdout = (proc.stdout or "")[-4000:]
        result.test_stderr = (proc.stderr or "")[-2000:]
    except Exception as e:
        # exec timeout → грейдинг не удался (но reward может быть уже записан)
        if "timeout" in str(e).lower():
            result.timed_out = True
            result.test_stdout = f"[grader timeout after {timeout}s]"
        else:
            result.pytest_error = f"test execution failed: {e}"
            return result

    # 3. Распарсить pytest summary (мягкий signal).
    p, f = _parse_pytest_summary(result.test_stdout)
    result.pytest_passed = p
    result.pytest_failed = f

    # 4. Прочитать reward.txt — единственный источник истины для verdict.
    reward = container.read_file(CONTAINER_REWARD)
    if reward is None:
        result.pytest_error = f"reward.txt не найден: {CONTAINER_REWARD}"
        # Fallback: если pytest summary показал 0 failed и есть passed — засчитать
        if result.pytest_failed == 0 and result.pytest_passed and result.pytest_passed > 0:
            result.passed = True
        return result

    result.reward_raw = reward.strip()
    result.passed = result.reward_raw == "1"
    return result
