"""config — конфигурация eval-пайплайна.

Все пути вычисляются относительно vsmlite-tb/ (родителя), не от cwd.
Перекрывается env-переменными (.env) или аргументами CLI.

Режимы (VSM-026): профиль задаёт источник данных + файл метрик. Ортогонально
выбору раннера (VSM-024: harbour-раннер), питает оба пайплайна через EvalConfig.
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


# ── Профили датасетов (VSM-026): режим = источник данных + файл метрик ──
# Профиль ортогонален раннеру (VSM-024 harbour) — питает любой пайплайн через
# EvalConfig. train = dev-v2 (метрика A(t)); eval-test/eval-dataset = TB-2.1
# verified (zai-org/terminal-bench-2-verified, 89 задач, релиз 2026-05-08).
@dataclass(frozen=True)
class DatasetProfile:
    """Один eval-режим: источник датасета + куда писать метрики."""

    key: str               # train | eval-test | eval-dataset
    repo: str              # HF repo_id для snapshot_download
    cache_subdir: str      # поддиректория в .cache/ (vsmlite-tb/.cache/<subdir>)
    metrics_filename: str  # имя файла метрик в results_dir (state/)
    label: str             # человекочитаемое описание


DATASET_PROFILES: dict[str, DatasetProfile] = {
    "train": DatasetProfile(
        key="train",
        repo="open-thoughts/OpenThoughts-TB-dev-v2",
        cache_subdir="tb-dev-v2",
        metrics_filename="dev_metrics.json",
        label="TB Dev Set v2 (train)",
    ),
    "eval-test": DatasetProfile(
        key="eval-test",
        repo="zai-org/terminal-bench-2-verified",
        cache_subdir="tb-2-verified",
        metrics_filename="eval_test_metrics.json",
        label="TB-2.1 verified (eval-test)",
    ),
    "eval-dataset": DatasetProfile(
        key="eval-dataset",
        repo="zai-org/terminal-bench-2-verified",
        cache_subdir="tb-2-verified",
        metrics_filename="eval_dataset_metrics.json",
        label="TB-2.1 verified (final test)",
    ),
}
DEFAULT_PROFILE = "train"


@dataclass
class EvalConfig:
    """Конфигурация eval-прогона.

    Пути по умолчанию (по профилю, VSM-026):
      profile      — train (default) | eval-test | eval-dataset
      dataset_dir  — vsmlite-tb/.cache/<profile.cache_subdir>/  (gitignored)
      results_dir  — vsmlite-tb/state/  (<profile.metrics_filename>)
      product_src  — ../src              (read-only mount)

    Профиль задаёт источник данных + файл метрик. env EVAL_DATASET_REPO /
    EVAL_DATASET_DIR / EVAL_DATASET_SUBDIR перекрывают профиль (backward-compat
    для существующих прогонов и harbor_run.py из VSM-024).
    """

    # Режим (VSM-026): определяет источник данных + файл метрик. Ортогонален
    # раннеру (VSM-024 harbour) — профиль питает любой пайплайн.
    profile: str = field(default_factory=lambda: os.environ.get(
        "EVAL_PROFILE", DEFAULT_PROFILE,
    ))

    # Источник данных. По умолчанию из профиля; env перекрывает (backward-compat).
    dataset_repo: str = field(default="")        # "" → из профиля (см. __post_init__)
    dataset_dir: Path = field(default=None)      # None → из профиля (см. __post_init__)

    # Продукт (оцениваемый harness). Монтируется read-only в контейнер.
    product_src: Path = field(default_factory=lambda: PRODUCT_SRC)

    # Harness (мозг агента). claude-code | goose | custom.
    harness_type: str = field(default_factory=lambda: os.environ.get(
        "EVAL_HARNESS", "claude-code",
    ))
    harness_binary: str = ""          # авто-детект если пусто
    harness_max_turns: int = 20       # → goose --max-turns
    harness_extra_args: list[str] = field(default_factory=list)

    # Sanity-проверка (VSM-026): структурная проверка датасета «из-под коробки»
    # перед агентом — без Docker-build, локально. True по умолчанию: задача с
    # битой структурой → status=error без запуска контейнера/агента.
    sanity_check: bool = True

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

    # eval-test сэмплинг (VSM-026): N задач из TB-2.1 verified, random seed=42.
    # Детерминированный random → точки сравнимы между итерациями.
    eval_test_sample_size: int = 20
    eval_test_seed: int = 42

    # Результаты
    results_dir: Path = field(default_factory=lambda: VSMLITE_ROOT / "state")

    # Docker
    docker_compose_project: str = "vsmlite-eval"   # префикс имён контейнеров

    # HF-токен (опционально; датасет публичный)
    hf_token: str | None = field(default_factory=lambda: os.environ.get("HF_TOKEN"))

    def __post_init__(self) -> None:
        """Разрешить профиль → дефолтные dataset_repo/dir (если не заданы явно).

        backward-compat: env EVAL_DATASET_REPO / EVAL_DATASET_DIR перекрывают
        профиль (для существующих прогонов и harbor_run.py из VSM-024).
        """
        prof = DATASET_PROFILES.get(self.profile)
        if prof is None:
            raise ValueError(
                f"неизвестный профиль: {self.profile!r} "
                f"(доступны: {', '.join(DATASET_PROFILES)})"
            )
        # dataset_repo: "" → из профиля, иначе env-override / явное значение.
        if not self.dataset_repo:
            self.dataset_repo = os.environ.get("EVAL_DATASET_REPO") or prof.repo
        # dataset_dir: None → из профиля, иначе env-override / явное значение.
        if self.dataset_dir is None:
            env_dir = os.environ.get("EVAL_DATASET_DIR")
            if env_dir:
                self.dataset_dir = Path(env_dir)
            else:
                self.dataset_dir = VSMLITE_ROOT / ".cache" / prof.cache_subdir

    @property
    def profile_meta(self) -> DatasetProfile:
        """DatasetProfile активного режима (source/label/metrics_filename)."""
        return DATASET_PROFILES[self.profile]

    @property
    def dev_metrics_file(self) -> Path:
        """Файл метрик режима: state/<profile.metrics_filename>.

        VSM-026: каждый режим пишет в свой файл (A(t) не смешивается):
          train → dev_metrics.json, eval-test → eval_test_metrics.json,
          eval-dataset → eval_dataset_metrics.json.
        """
        return self.results_dir / self.profile_meta.metrics_filename

    def task_filter_description(self) -> str:
        """Человекочитаемое описание активных фильтров (для лога)."""
        parts = [f"profile={self.profile}"]
        if self.filter_difficulty:
            parts.append(f"difficulty={self.filter_difficulty}")
        if self.filter_category:
            parts.append(f"category={self.filter_category}")
        if self.filter_task_ids:
            parts.append(f"ids={len(self.filter_task_ids)}")
        if self.limit:
            parts.append(f"limit={self.limit}")
        return ", ".join(parts)
