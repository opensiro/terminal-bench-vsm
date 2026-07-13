"""FixSyntax — минимальная синтаксическая правка (SyntaxError)."""
from __future__ import annotations
from pathlib import Path
from .base import RecoveryContext, RecoveryResult

def apply(ctx: RecoveryContext) -> RecoveryResult:
    file_path = ctx.extra.get("file_path")
    if not file_path:
        for obs in ctx.failure_observations:
            val = obs.get("value", "")
            if "SyntaxError" in val and '"' in val:
                parts = val.split('"')
                if len(parts) >= 2:
                    file_path = parts[1]
                    break
    if not file_path:
        return RecoveryResult(blocked="missing file_path")
    # Design-phase stub: реальный фикс требует parse traceback (file:line) + edit.
    return RecoveryResult(
        applied=True,
        env_changes=[f"edited: {file_path} (syntax fix — stub, needs traceback parse)"],
    )
