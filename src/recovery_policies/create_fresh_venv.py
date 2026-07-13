"""CreateFreshVenv — создать свежее venv, установить deps заново (DependencyConflict)."""
from __future__ import annotations
import subprocess
import venv
from pathlib import Path
from .base import RecoveryContext, RecoveryResult


def apply(ctx: RecoveryContext) -> RecoveryResult:
    workspace = ctx.workspace
    venv_path = workspace / ".venv_recovery"
    deps_file = ctx.extra.get("deps_file")
    if not deps_file:
        for candidate in ["requirements.txt", "pyproject.toml", "setup.py", "package.json"]:
            if (workspace / candidate).exists():
                deps_file = candidate
                break
    try:
        venv.create(venv_path, with_pip=True, clear=True)
        pip = str(venv_path / "bin" / "pip")
        changes = [f"created venv: {venv_path}"]
        if deps_file:
            if deps_file.endswith(".txt"):
                subprocess.run([pip, "install", "-r", deps_file], check=True, capture_output=True, timeout=300)
                changes.append(f"reinstalled deps from {deps_file}")
            elif deps_file == "pyproject.toml":
                subprocess.run([pip, "install", "."], cwd=str(workspace), check=True, capture_output=True, timeout=300)
                changes.append(f"reinstalled deps from {deps_file}")
            elif deps_file == "package.json":
                subprocess.run(["npm", "install"], cwd=str(workspace), check=True, capture_output=True, timeout=300)
                changes.append(f"reinstalled deps from {deps_file}")
        return RecoveryResult(applied=True, env_changes=changes)
    except Exception as exc:
        return RecoveryResult(blocked=f"venv creation failed: {exc}")
