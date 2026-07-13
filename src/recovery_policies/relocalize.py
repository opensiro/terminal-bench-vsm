"""RelocalizeAndReplay — переискать целевой файл/символ (FileLocalizationError)."""
from __future__ import annotations
import subprocess
from pathlib import Path
from .base import RecoveryContext, RecoveryResult

def apply(ctx: RecoveryContext) -> RecoveryResult:
    pattern = ctx.extra.get("search_pattern")
    if not pattern:
        return RecoveryResult(blocked="missing search_pattern")
    repo_root = str(ctx.workspace)
    try:
        result = subprocess.run(
            ["grep", "-rl", "--include=*.py", pattern, repo_root],
            capture_output=True, text=True, timeout=30,
        )
        files = [f for f in result.stdout.strip().split("\n") if f]
        if files:
            return RecoveryResult(
                applied=True,
                env_changes=[f"relocalized: {files[0]} (found {len(files)} matches)"],
            )
        return RecoveryResult(blocked=f"pattern '{pattern}' not found in {repo_root}")
    except subprocess.TimeoutExpired:
        return RecoveryResult(blocked="grep timeout")
