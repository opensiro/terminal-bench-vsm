"""container — Docker-жизненный цикл TB-задачи.

TB-задача = Docker-песочница. Каждая задача имеет environment/Dockerfile;
docker-compose.yaml генерируется на лету (OpenThoughts v2 имеет только
Dockerfile + task.toml, без готового compose).

Жизненный цикл:
  build()  — docker compose build (таймаут build_timeout_sec из task.toml)
  start()  — docker compose up -d; контейнер на "sleep infinity"
  exec(cmd) — выполнить команду внутри (для agent_phase + grader)
  cp_to(host, ctr) / cp_from(ctr, host) — копирование файлов (tests/, trace.json)
  stop() + remove() — очистка

Монтирование ../src read-only в /opt/mcp_server_src — чтобы продуктовый
MCP-сервер запускался внутри контейнера (docker-exec MCP bridge). Продукт
НЕ модифицируется, только read-only bind mount.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

from .config import (
    CONTAINER_LOGS, CONTAINER_MCP_SRC, EvalConfig, PRODUCT_SRC,
)
from .loader import TBTask


class ContainerError(RuntimeError):
    """Ошибка Docker-операции (build/exec/cp)."""


@dataclass
class TBContainer:
    """Docker-контейнер одной TB-задачи. Контекст-менеджер для очистки."""

    task: TBTask
    config: EvalConfig
    _compose_dir: Path = field(default_factory=lambda: Path(tempfile.mkdtemp(prefix="eval-compose-")))
    _compose_file: Path = field(default=Path(""))
    _container_name: str = ""
    _started: bool = False

    def __post_init__(self):
        self._container_name = f"{self.config.docker_compose_project}-{self.task.task_id}"
        self._compose_file = self._compose_dir / "docker-compose.yaml"

    # ── Контекст-менеджер: гарантированная очистка ──

    def __enter__(self) -> "TBContainer":
        self.build()
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        self.remove()
        self._cleanup_compose_dir()
        return False  # не подавлять исключения

    # ── Compose-генерация ──

    def _write_compose(self) -> None:
        """Сгенерировать docker-compose.yaml для задачи.

        Сервис 'client': build из environment/, sleep infinity, /logs volume.
        Bind-mount ../src read-only в /opt/mcp_server_src (для MCP-сервера).
        """
        env_dir = self.task.dockerfile_path.parent
        # docker-compose пути должны быть абсолютными (запускаем из tmpdir)
        env_abs = env_dir.resolve()

        compose = f"""\
services:
  client:
    build: "{env_abs}"
    container_name: {self._container_name}
    command: ["sleep", "infinity"]
    volumes:
      - "{PRODUCT_SRC}:{CONTAINER_MCP_SRC}:ro"
"""
        self._compose_file.write_text(compose, encoding="utf-8")

    def _compose_cmd(self, *args: str) -> list[str]:
        """docker compose -f <file> -p <project> <args>..."""
        return [
            "docker", "compose",
            "-f", str(self._compose_file),
            "-p", f"{self.config.docker_compose_project}-{self.task.task_id}",
            *args,
        ]

    # ── Жизненный цикл ──

    def build(self) -> None:
        """docker compose build. Таймаут из task.toml [environment].build_timeout_sec."""
        self._write_compose()
        timeout = int(self.task.meta.build_timeout_sec or self.config.default_build_timeout_sec)
        try:
            result = subprocess.run(
                self._compose_cmd("build"),
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise ContainerError(
                f"build timeout ({timeout}s) для {self.task.task_id}"
            )
        if result.returncode != 0:
            raise ContainerError(
                f"build failed для {self.task.task_id}:\n{result.stderr[-2000:]}"
            )

    def start(self) -> None:
        """docker compose up -d."""
        try:
            result = subprocess.run(
                self._compose_cmd("up", "-d"),
                capture_output=True, text=True, timeout=120,
            )
        except subprocess.TimeoutExpired:
            raise ContainerError(f"up timeout для {self.task.task_id}")
        if result.returncode != 0:
            raise ContainerError(
                f"up failed для {self.task.task_id}:\n{result.stderr[-2000:]}"
            )
        self._started = True
        # Подготовить /logs/verifier внутри контейнера
        self.exec(f"mkdir -p {CONTAINER_LOGS}/verifier")

    def exec(self, command: str, timeout: int = 120) -> subprocess.CompletedProcess:
        """docker exec <container> bash -c '<command>'.

        Возвращает CompletedProcess. Не бросает на ненулевой exit (caller решает).
        Бросает ContainerError только по таймауту.
        """
        try:
            return subprocess.run(
                ["docker", "exec", self._container_name, "bash", "-c", command],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise ContainerError(
                f"exec timeout ({timeout}s): {command[:120]}"
            )

    def cp_to(self, host_path: Path, container_path: str) -> None:
        """docker cp <host> <container>:<path>."""
        result = subprocess.run(
            ["docker", "cp", str(host_path), f"{self._container_name}:{container_path}"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise ContainerError(
                f"cp_to failed ({host_path} → {container_path}):\n{result.stderr[-1000:]}"
            )

    def cp_from(self, container_path: str, host_path: Path) -> bool:
        """docker cp <container>:<path> <host>. Возвращает False если путь не существует."""
        # Сначала проверить существование внутри контейнера
        check = self.exec(f"test -e {container_path} && echo exists", timeout=10)
        if "exists" not in (check.stdout or ""):
            return False
        result = subprocess.run(
            ["docker", "cp", f"{self._container_name}:{container_path}", str(host_path)],
            capture_output=True, text=True, timeout=60,
        )
        return result.returncode == 0

    def read_file(self, container_path: str) -> str | None:
        """Прочитать файл из контейнера. None если не существует."""
        result = self.exec(f"cat {container_path} 2>/dev/null", timeout=10)
        if result.returncode != 0:
            return None
        return result.stdout

    def stop(self) -> None:
        """docker compose down. Идемпотентно."""
        if not self._started:
            return
        try:
            subprocess.run(
                self._compose_cmd("down"),
                capture_output=True, text=True, timeout=60,
            )
        except subprocess.TimeoutExpired:
            pass  # best-effort
        self._started = False

    def remove(self) -> None:
        """Удалить контейнер напрямую (если compose down не подхватил). Идемпотентно."""
        subprocess.run(
            ["docker", "rm", "-f", self._container_name],
            capture_output=True, text=True, timeout=30,
        )

    def _cleanup_compose_dir(self) -> None:
        """Удалить tmp compose-директорию."""
        try:
            shutil.rmtree(self._compose_dir, ignore_errors=True)
        except Exception:
            pass

    # ── Интроспекция ──

    @property
    def name(self) -> str:
        return self._container_name
