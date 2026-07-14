"""config — конфигурация eval-пайплайна.

Все пути вычисляются относительно vsmlite-tb/ (родителя), не от cwd.
Перекрывается env-переменными (.env) или аргументами CLI.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# vsmlite-tb/ — корень родителя (этот файл: eval/config.py → parent.parent)
VSMLITE_ROOT = Path(__file__).resolve().parent.parent
# ../src — продуктовый код (монтируется read-only в контейнер)
PRODUCT_SRC = (VSMLITE_ROOT / "../src").resolve()

# Канонические пути TB внутри контейнера (Terminal-Bench convention)
CONTAINER_WORKSPACE = "/app"
CONTAINER_LOGS = "/logs"
CONTAINER_TESTS = "/tests"
CONTAINER_TRACE = f"{CONTAINER_LOGS}/trace.json"
CONTAINER_REWARD = f"{CONTAINER_LOGS}/verifier/reward.txt"
CONTAINER_MCP_SRC = "/opt/mcp_server_src"

# Датасет по умолчанию — Terminal-Bench Dev Set v2 (OpenThoughts)
DEFAULT_DATASET_REPO = "open-thoughts/OpenThoughts-TB-dev-v2"


@dataclass
class EvalConfig:
    """Конфигурация eval-прогона.

    Пути по умолчанию:
      dataset_dir  — vsmlite-tb/.cache/tb-dev-v2/  (gitignored)
      results_dir  — vsmlite-tb/state/             (dev_metrics.json)
      product_src  — ../src                         (read-only mount)
    """

    # Источник данных
    dataset_repo: str = field(default_factory=lambda: os.environ.get(
        "EVAL_DATASET_REPO", DEFAULT_DATASET_REPO,
    ))
    dataset_dir: Path = field(default_factory=lambda: Path(os.environ.get(
        "EVAL_DATASET_DIR", str(VSMLITE_ROOT / ".cache" / "tb-dev-v2"),
    )))

    # Продукт (оцениваемый harness). Монтируется read-only в контейнер.
    product_src: Path = field(default_factory=lambda: PRODUCT_SRC)

    # Harness (мозг агента). claude-code | goose | custom.
    harness_type: str = field(default_factory=lambda: os.environ.get(
        "EVAL_HARNESS", "claude-code",
    ))
    harness_binary: str = ""          # авто-детект если пусто
    harness_max_turns: int = 20       # → goose --max-turns
    harness_extra_args: list[str] = field(default_factory=list)

    # Фильтры выбора задач (применяются в loader/runner)
    filter_difficulty: str | None = None   # easy | medium | hard | extreme
    filter_category: str | None = None
    filter_task_ids: list[str] | None = None  # whitelist task_id

    # Таймауты (перекрываются task.toml [agent]/[verifier]/[environment])
    default_agent_timeout_sec: float = 900.0
    default_verifier_timeout_sec: float = 900.0
    default_build_timeout_sec: float = 600.0

    # Масштабирование прогонов
    limit: int | None = None          # максимум задач в батче (None = все)

    # Результаты
    results_dir: Path = field(default_factory=lambda: VSMLITE_ROOT / "state")

    # Docker
    docker_compose_project: str = "vsmlite-eval"   # префикс имён контейнеров

    # HF-токен (опционально; датасет публичный)
    hf_token: str | None = field(default_factory=lambda: os.environ.get("HF_TOKEN"))

    @property
    def dev_metrics_file(self) -> Path:
        """state/dev_metrics.json — метрика автономности (VSM-004/005)."""
        return self.results_dir / "dev_metrics.json"

    def task_filter_description(self) -> str:
        """Человекочитаемое описание активных фильтров (для лога)."""
        parts = []
        if self.filter_difficulty:
            parts.append(f"difficulty={self.filter_difficulty}")
        if self.filter_category:
            parts.append(f"category={self.filter_category}")
        if self.filter_task_ids:
            parts.append(f"ids={len(self.filter_task_ids)}")
        if self.limit:
            parts.append(f"limit={self.limit}")
        return ", ".join(parts) or "all"
