"""loader — скачивание и парсинг Terminal-Bench Dev Set v2.

Датасет НЕ табличный — это 100 папок задач на диске, скачиваемых через
snapshot_download. Каждая папка:
  task.toml            — метаданные (slug = task_id = имя папки)
  instruction.md       — промпт агенту
  environment/Dockerfile — песочница
  solution/solve.sh    — эталонное решение
  tests/test.sh        — verifier (пишет 1/0 в /logs/verifier/reward.txt)
  tests/test_outputs.py — pytest assertions (опц., ~94/100)

task.toml (TOML, парсится stdlib tomllib):
  version = "1.0"
  [metadata] difficulty/category/tags/author_*/expert_time_estimate_min
  [agent] timeout_sec
  [verifier] timeout_sec / restart_environment
  [environment] build_timeout_sec
"""
from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .config import EvalConfig


@dataclass
class TaskMeta:
    """Метаданные задачи из task.toml (по умолчанию безопасные значения)."""

    difficulty: str = "unknown"
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    author_name: str = "unknown"
    author_email: str = "unknown"
    agent_timeout_sec: float = 900.0
    verifier_timeout_sec: float = 900.0
    verifier_restart_environment: bool = False
    build_timeout_sec: float = 600.0


@dataclass
class TBTask:
    """Одна Terminal-Bench задача (одна папка на диске)."""

    task_id: str                 # slug = имя папки
    task_dir: Path               # путь к папке задачи в dataset_dir
    instruction: str             # содержимое instruction.md (до мембраны)
    dockerfile_path: Path        # environment/Dockerfile
    tests_dir: Path              # tests/
    solve_script: Path           # solution/solve.sh
    meta: TaskMeta = field(default_factory=TaskMeta)


def download(config: EvalConfig) -> Path:
    """Скачать датасет в config.dataset_dir (идемпотентно).

    Использует huggingface_hub.snapshot_download. Датасет публичный — токен
    опционален. Возвращает путь к локальной копии.
    """
    config.dataset_dir.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print(
            "ERROR: huggingface_hub не установлен.\n"
            "  pip install huggingface_hub",
            file=sys.stderr,
        )
        raise

    local_dir = snapshot_download(
        repo_id=config.dataset_repo,
        repo_type="dataset",
        local_dir=str(config.dataset_dir),
        token=config.hf_token,
    )
    return Path(local_dir)


def _parse_task_toml(task_dir: Path) -> TaskMeta:
    """Распарсить task.toml → TaskMeta. Толерантно к отсутствию полей."""
    toml_path = task_dir / "task.toml"
    meta = TaskMeta()
    if not toml_path.exists():
        return meta

    with toml_path.open("rb") as f:
        data = tomllib.load(f)

    m = data.get("metadata", {})
    meta.difficulty = m.get("difficulty", meta.difficulty)
    meta.category = m.get("category", meta.category)
    meta.tags = list(m.get("tags", []))
    meta.author_name = m.get("author_name", meta.author_name)
    meta.author_email = m.get("author_email", meta.author_email)

    agent = data.get("agent", {})
    meta.agent_timeout_sec = float(agent.get("timeout_sec", meta.agent_timeout_sec))

    verifier = data.get("verifier", {})
    meta.verifier_timeout_sec = float(verifier.get("timeout_sec", meta.verifier_timeout_sec))
    meta.verifier_restart_environment = bool(verifier.get("restart_environment", False))

    env = data.get("environment", {})
    meta.build_timeout_sec = float(env.get("build_timeout_sec", meta.build_timeout_sec))

    return meta


def _read_instruction(task_dir: Path) -> str:
    """Прочитать instruction.md. Если отсутствует — пустая строка."""
    path = task_dir / "instruction.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _load_one(task_dir: Path) -> TBTask | None:
    """Загрузить одну задачу из папки. None если папка — не задача."""
    # Минимальные обязательные файлы задачи: instruction + Dockerfile.
    instruction_path = task_dir / "instruction.md"
    dockerfile_path = task_dir / "environment" / "Dockerfile"
    if not instruction_path.exists() or not dockerfile_path.exists():
        return None

    return TBTask(
        task_id=task_dir.name,
        task_dir=task_dir,
        instruction=_read_instruction(task_dir),
        dockerfile_path=dockerfile_path,
        tests_dir=task_dir / "tests",
        solve_script=task_dir / "solution" / "solve.sh",
        meta=_parse_task_toml(task_dir),
    )


def load_tasks(config: EvalConfig) -> list[TBTask]:
    """Загрузить все задачи из dataset_dir, применить фильтры config.

    Авто-скачивание если dataset_dir пуст.
    """
    if not config.dataset_dir.exists() or not any(config.dataset_dir.iterdir()):
        print(f"dataset_dir пуст — скачиваю {config.dataset_repo}…", file=sys.stderr)
        download(config)

    tasks: list[TBTask] = []
    for entry in sorted(config.dataset_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        task = _load_one(entry)
        if task is not None:
            tasks.append(task)

    tasks = _apply_filters(tasks, config)
    return tasks


def _apply_filters(tasks: list[TBTask], config: EvalConfig) -> list[TBTask]:
    """Применить фильтры config к списку задач."""
    if config.filter_task_ids:
        wanted = set(config.filter_task_ids)
        tasks = [t for t in tasks if t.task_id in wanted]
    if config.filter_difficulty:
        tasks = [t for t in tasks if t.meta.difficulty == config.filter_difficulty]
    if config.filter_category:
        tasks = [t for t in tasks if t.meta.category == config.filter_category]
    if config.limit is not None:
        tasks = tasks[: config.limit]
    return tasks


def list_tasks(config: EvalConfig) -> None:
    """CLI: вывести таблицу задач (id, difficulty, category, agent timeout)."""
    tasks = load_tasks(config)
    if not tasks:
        print("нет задач (проверьте dataset_dir и фильтры)")
        return

    print(f"{'task_id':<45} {'difficulty':<10} {'category':<28} {'agent_to':>8}")
    print("-" * 95)
    for t in tasks:
        print(
            f"{t.task_id:<45} {t.meta.difficulty:<10} {t.meta.category:<28} "
            f"{int(t.meta.agent_timeout_sec):>7}s"
        )
    print(f"\nвсего: {len(tasks)} задач")
