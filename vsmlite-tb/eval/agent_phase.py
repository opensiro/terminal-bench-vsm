"""agent_phase — фаза агента: harness (мозг) + продуктовый MCP (руки).

Архитектура "docker-exec MCP bridge":
  - Harness (claude-code/goose) запускается НА ХОСТЕ.
  - Продуктовый MCP-сервер (../src/mcp_server/) запускается ВНУТРИ контейнера
    через `docker exec -i <container> python3 -m mcp_server.server`.
  - Harness подключается к MCP через mcp_config.json (command: docker).
  - Каждый shell.exec MCP выполняется в контейнере → реальное TB-окружение.
  - Trace пишется продуктовым MCP в /logs/trace.json (T2 CONTRACT §3 формат).

Продукт НЕ модифицируется и НЕ импортируется как модуль — только read-only
bind mount (см. container.py) + subprocess. Мембрана сохранена.

Логика сборки harness-аргументов НЕ импортируется из src/runtime/harness.py
(чтобы не сцепляться с внутренним API продукта) — минимально необходимая
логика скопирована сюда.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import (
    CONTAINER_LOGS, CONTAINER_MCP_SRC, CONTAINER_TRACE, CONTAINER_WORKSPACE,
    EvalConfig,
)
from .container import TBContainer

# Имя продуктового MCP-сервера (одно на обе стороны bridge'а: mcp_config.json +
# claude-code --allowedTools wildcard). Дубликат server.py:122 serverInfo.name.
MCP_SERVER_NAME = "coding-harness-tools"


@dataclass
class AgentPhaseResult:
    """Результат фазы агента одной задачи."""

    exit_code: int = -1
    duration_sec: float = 0.0
    stdout: str = ""
    stderr: str = ""
    trace: list[dict] = field(default_factory=list)
    failure_observations: list[dict] = field(default_factory=list)
    timed_out: bool = False
    trace_collected: bool = False


def _resolve_harness_binary(config: EvalConfig) -> str:
    """Определить путь к бинарнику harness (авто-детект если не задан)."""
    if config.harness_binary:
        return config.harness_binary
    if config.harness_type == "claude-code":
        return "claude"
    elif config.harness_type == "goose":
        return "goose"
    else:
        return config.harness_type


def _build_mcp_config(container: TBContainer, config: EvalConfig) -> dict:
    """mcp_config.json: MCP-сервер запускается ВНУТРИ контейнера через docker exec.

    PYTHONPATH=/opt/mcp_server_src чтобы `python3 -m mcp_server.server` резолвился
    из read-only mount'а ../src. WORKSPACE_ROOT=/app — продуктовая конвенция.
    """
    container_name = container.name
    return {
        "mcpServers": {
            MCP_SERVER_NAME: {
                "transport": "stdio",
                "command": "docker",
                "args": [
                    "exec", "-i",
                    "-e", f"PYTHONPATH={CONTAINER_MCP_SRC}",
                    "-e", f"WORKSPACE_ROOT={CONTAINER_WORKSPACE}",
                    container_name,
                    "python3", "-m", "mcp_server.server",
                    "--workspace", CONTAINER_WORKSPACE,
                    "--trace-file", CONTAINER_TRACE,
                ],
            }
        }
    }


def _build_mcp_wrapper(container: TBContainer, config: EvalConfig, tmpdir: Path) -> str:
    """Bash-wrapper для goose (--with-extension; не парсит пути с пробелами).

    Аналог workaround из src/runtime/harness.py, но MCP запускается в контейнере.
    """
    wrapper_path = tmpdir / "mcp_server_wrapper.sh"
    lines = [
        "#!/usr/bin/env bash",
        f'docker exec -i '
        f'-e PYTHONPATH="{CONTAINER_MCP_SRC}" '
        f'-e WORKSPACE_ROOT="{CONTAINER_WORKSPACE}" '
        f'{container.name} '
        f'python3 -m mcp_server.server '
        f'--workspace "{CONTAINER_WORKSPACE}" '
        f'--trace-file "{CONTAINER_TRACE}" "$@"',
        "",
    ]
    wrapper_path.write_text("\n".join(lines), encoding="utf-8")
    wrapper_path.chmod(0o755)
    return str(wrapper_path)


def _build_harness_args(
    config: EvalConfig,
    task_prompt: str,
    mcp_config_path: str | None,
    mcp_wrapper_path: str | None,
) -> list[str]:
    """Сборка аргументов для harness (не импортирует src/runtime/harness.py).

    Минимально необходимая логика, скопированная из HarnessConfig.build_harness_args.
    """
    binary = _resolve_harness_binary(config)
    if config.harness_type == "claude-code":
        # VSM-022 решение A: ограничить tool-surface до продуктового MCP.
        # Без --allowedTools claude-code сохраняет нативные Bash/Read/Write/Edit
        # на хосте и решает задачу минуя MCP bridge → trace пуст, pass_rate
        # измеряет harness, а не автономность продукта.
        # mcp__<server>__* — wildcard-форма, разрешает ВСЕ инструменты сервера
        # (синтаксис подтверждён claude --help + code.claude.com/docs/en/permissions).
        # Нативные тулы (Bash/Read/Write/Edit/...) не перечислены → отключены.
        return [
            binary,
            "--mcp-config", mcp_config_path or "",
            "--allowedTools", f"mcp__{MCP_SERVER_NAME}__*",
            "--print",
            "--dangerously-skip-permissions",
            *config.harness_extra_args,
            task_prompt,
        ]
    elif config.harness_type == "goose":
        # VSM-023 (под-issue от VSM-022): goose не имеет эквивалента --allowedTools.
        # --with-extension подключает MCP, но НЕ отключает built-in tools (developer,
        # computer-controller, ...). trace может остаться пустым, если goose решает
        # через свои built-in. --no-profile убирает user-профиль, но не core builtins.
        args = [
            binary, "run",
            "--text", task_prompt,
            "--no-session",
            "--no-profile",
            "--max-turns", str(config.harness_max_turns),
            "--output-format", "text",
        ]
        if mcp_wrapper_path:
            args.extend(["--with-extension", mcp_wrapper_path])
        args.extend(config.harness_extra_args)
        return args
    else:
        return [binary, *config.harness_extra_args, task_prompt]


def run_agent_phase(
    container: TBContainer,
    task_prompt: str,
    config: EvalConfig,
) -> AgentPhaseResult:
    """Запустить harness с docker-exec MCP bridge, собрать trace.

    task_prompt уже нейтрализован мембраной (см. membrane.py).
    Таймаут = task.meta.agent_timeout_sec (или config.default_agent_timeout_sec).
    """
    result = AgentPhaseResult()
    timeout_sec = int(getattr(container.task.meta, "agent_timeout_sec", None)
                      or config.default_agent_timeout_sec)

    with tempfile.TemporaryDirectory(prefix="eval-agent-") as tmpdir:
        tmpdir_path = Path(tmpdir)

        # MCP config / wrapper в зависимости от harness
        mcp_config_path: str | None = None
        mcp_wrapper_path: str | None = None
        if config.harness_type == "goose":
            mcp_wrapper_path = _build_mcp_wrapper(container, config, tmpdir_path)
        else:
            mcp_config = _build_mcp_config(container, config)
            mcp_config_path = str(tmpdir_path / "mcp_config.json")
            Path(mcp_config_path).write_text(
                json.dumps(mcp_config, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        harness_args = _build_harness_args(
            config, task_prompt, mcp_config_path, mcp_wrapper_path,
        )
        env = os.environ.copy()

        start = time.time()
        try:
            proc = subprocess.run(
                harness_args,
                capture_output=True, text=True,
                timeout=timeout_sec,
                env=env,
            )
            result.exit_code = proc.returncode
            result.stdout = proc.stdout or ""
            result.stderr = proc.stderr or ""
        except subprocess.TimeoutExpired as e:
            result.timed_out = True
            result.exit_code = 124
            result.stdout = e.stdout or "" if isinstance(e.stdout, str) else ""
            result.stderr = (e.stderr or "" if isinstance(e.stderr, str) else "") + \
                f"\n[harness timed out after {timeout_sec}s]"
        except FileNotFoundError:
            result.exit_code = 127
            result.stderr = f"harness binary not found: {_resolve_harness_binary(config)}"
        result.duration_sec = time.time() - start

        # Собрать trace из контейнера (продуктовый MCP пишет в /logs/trace.json)
        trace_raw = container.read_file(CONTAINER_TRACE)
        if trace_raw:
            try:
                data = json.loads(trace_raw)
                result.trace = data.get("trace", [])
                result.failure_observations = data.get("failure_observations", [])
                result.trace_collected = True
            except json.JSONDecodeError:
                result.stderr += "\n[trace.json невалидный JSON]"

    return result
