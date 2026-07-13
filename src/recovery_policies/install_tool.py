"""InstallTool — установить требуемый tool/CLI в окружение (ToolNotFound)."""
from __future__ import annotations
import shutil
import subprocess
from .base import RecoveryContext, RecoveryResult

# Менеджеры пакетов по приоритету
_PKG_MANAGERS = ["apt-get", "brew", "dnf", "pacman"]


def _detect_pkg_manager() -> str | None:
    for pm in _PKG_MANAGERS:
        if shutil.which(pm):
            return pm
    return None


def apply(ctx: RecoveryContext) -> RecoveryResult:
    tool_name = ctx.extra.get("tool_name")
    if not tool_name:
        return RecoveryResult(blocked="missing tool_name")
    # Сначала пробуем pip (python packages часто являются CLI tools)
    pip_path = shutil.which("pip") or shutil.which("pip3")
    if pip_path:
        try:
            subprocess.run([pip_path, "install", tool_name], check=True, capture_output=True, timeout=120)
            if shutil.which(tool_name):
                return RecoveryResult(applied=True, env_changes=[f"installed: {tool_name} (pip)"])
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
    # Затем системный package manager
    pm = _detect_pkg_manager()
    if pm:
        try:
            subprocess.run([pm, "install", "-y", tool_name], check=True, capture_output=True, timeout=120)
            return RecoveryResult(applied=True, env_changes=[f"installed: {tool_name} ({pm})"])
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
    return RecoveryResult(blocked=f"could not install {tool_name}: no working package manager")
