"""sanity — встроенная структурная проверка датасета «из-под коробки ок».

VSM-026: перед запуском агента/контейнера каждая задача проверяется локально
(без Docker-build, без LLM). Битая по структуре задача → status=error сразу,
экономя время контейнерного прогона и давая явный сигнал «датасет битый».

Проверки (каждая = обязательный файл Harbor task-format для runnable-задачи):
  - instruction.md непустой (есть текст промпта)
  - environment/Dockerfile существует (песочница собирается)
  - task.toml валиден (парсится tomllib, секции на месте)
  - tests/test.sh существует (verifier есть)
  - solution/solve.sh существует (reference solution есть)

«Из-под коробки ок» = задача готова к прогону (runnable). Отсутствие
difficulty/category в [metadata] — это metadata gap (задача попадает в
"unknown"/"general" bucket при агрегации), НЕ structural failure: задача
всё равно runnable. Такие случае отмечаются как warning, не fail.

Ортогонально раннеру (VSM-024 harbour / старый docker-exec): проверяет только
целостность данных на диске, не запуская ничего. Используется:
  1. автоматически в runner.run_single перед агентом (config.sanity_check),
  2. явно через CLI `python -m eval sanity --profile <P>`.
"""
from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, field

from .config import EvalConfig
from .loader import TBTask, load_tasks


@dataclass
class SanityResult:
    """Результат sanity-проверки одной задачи."""

    task_id: str
    ok: bool                      # True = runnable (hard checks passed)
    checks: list[tuple[str, bool, str]] = field(default_factory=list)
    # (check_name, passed, detail) — detail пустой если passed
    warnings: list[str] = field(default_factory=list)
    # non-blocking gaps (metadata missing); задача всё равно runnable

    @property
    def failed_checks(self) -> list[str]:
        """Имена проваленных hard-проверок (для error-сообщения)."""
        return [name for name, passed, _ in self.checks if not passed]


# Hard checks: отсутствие = задача НЕ runnable (structural failure).
HARD_CHECKS = (
    "instruction.md",
    "environment/Dockerfile",
    "task.toml parses",
    "tests/test.sh",
    "solution/solve.sh",
)


def sanity_check_task(task: TBTask) -> SanityResult:
    """Структурная проверка одной задачи. Не запускает Docker/агента.

    ok=True если все hard checks прошли (задача runnable). Отсутствие
    difficulty/category — warning (metadata gap), не влияет на ok.
    """
    checks: list[tuple[str, bool, str]] = []
    warnings: list[str] = []

    # 1. instruction.md непустой
    instr_ok = bool(task.instruction.strip())
    checks.append((
        "instruction.md", instr_ok,
        "" if instr_ok else "пустой или отсутствует",
    ))

    # 2. environment/Dockerfile существует
    df_ok = task.dockerfile_path.exists()
    checks.append((
        "environment/Dockerfile", df_ok,
        "" if df_ok else "отсутствует",
    ))

    # 3. task.toml парсится (повторный parse — независимая проверка целостности)
    toml_path = task.task_dir / "task.toml"
    toml_ok = False
    toml_detail = ""
    if not toml_path.exists():
        toml_detail = "task.toml отсутствует"
    else:
        try:
            with toml_path.open("rb") as f:
                tomllib.load(f)
            toml_ok = True
        except (tomllib.TOMLDecodeError, OSError) as e:
            toml_detail = f"TOML невалиден: {e}"
    checks.append(("task.toml parses", toml_ok, toml_detail))

    # 4. tests/test.sh существует (verifier)
    test_sh = task.tests_dir / "test.sh"
    test_ok = test_sh.exists()
    checks.append((
        "tests/test.sh", test_ok,
        "" if test_ok else "отсутствует verifier",
    ))

    # 5. solution/solve.sh существует (reference solution)
    sol_ok = task.solve_script.exists()
    checks.append((
        "solution/solve.sh", sol_ok,
        "" if sol_ok else "отсутствует reference solution",
    ))

    # 6-7. difficulty/category — warnings (metadata gap, не blocking).
    # Задача runnable и без них; просто попадёт в "unknown"/"general" bucket.
    if task.meta.difficulty == "unknown":
        warnings.append("difficulty не задана в [metadata]")
    if task.meta.category == "general":
        warnings.append("category не задана в [metadata]")

    # ok = все HARD checks passed (warnings не влияют).
    hard_ok = all(
        passed for name, passed, _ in checks if name in HARD_CHECKS
    )
    return SanityResult(
        task_id=task.task_id,
        ok=hard_ok,
        checks=checks,
        warnings=warnings,
    )


def sanity_check_dataset(config: EvalConfig) -> dict:
    """Прогнать sanity по всем задачам профиля, вернуть summary.

    Возвращает {total, ok, fail, warns, fails, warnings}.
    ok/fail — по hard checks (runnable); warns — metadata gaps (non-blocking).
    Не пишет метрики — это пред-проверка, не результат прогона.
    """
    tasks = load_tasks(config)
    total = len(tasks)
    ok_count = 0
    warns_count = 0
    fails: list[dict] = []
    warnings: list[dict] = []

    for task in tasks:
        result = sanity_check_task(task)
        if not result.ok:
            fails.append({
                "task_id": result.task_id,
                "failed_checks": result.failed_checks,
            })
        else:
            ok_count += 1
        if result.warnings:
            warns_count += 1
            warnings.append({
                "task_id": result.task_id,
                "warnings": result.warnings,
            })

    return {
        "profile": config.profile,
        "dataset": config.dataset_repo,
        "total": total,
        "ok": ok_count,
        "fail": total - ok_count,
        "warns": warns_count,
        "fails": fails,
        "warnings": warnings,
    }


def print_sanity_report(summary: dict) -> int:
    """CLI: вывести отчёт sanity-проверки. Возвращает exit code (0=ok, 1=fail)."""
    total = summary["total"]
    ok = summary["ok"]
    fail = summary["fail"]
    warns = summary["warns"]
    profile = summary["profile"]
    dataset = summary["dataset"]

    print(f"── sanity: profile={profile} ──")
    print(f"  dataset: {dataset}")
    print(f"  total: {total}  ok: {ok}  fail: {fail}  warns(meta): {warns}")
    print()

    if fail > 0:
        print(f"  ✗ {fail} задач с ошибками структуры (НЕ runnable):")
        for entry in summary["fails"]:
            checks = ", ".join(entry["failed_checks"])
            print(f"    {entry['task_id']}: {checks}")
        print()

    if warns > 0:
        print(f"  ⚠ {warns} задач с metadata gaps (runnable, но метаданные неполны):")
        for entry in summary["warnings"][:10]:
            ws = "; ".join(entry["warnings"])
            print(f"    {entry['task_id']}: {ws}")
        if warns > 10:
            print(f"    ... и ещё {warns - 10}")
        print()

    if fail == 0:
        print(f"  ✓ все {total} задач runnable (прошли hard checks)")
        return 0
    return 1


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)
