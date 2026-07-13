"""FixBuildConfig — минимальный фикс сборки/компиляции (CompilationError)."""
from __future__ import annotations
from .base import RecoveryContext, RecoveryResult

def apply(ctx: RecoveryContext) -> RecoveryResult:
    # Design-phase stub: реальный фикс требует разбора вывода сборки (gcc/cargo/tsc/make).
    # Runtime: parse error_file:error_line из failure_observations, применить минимальную правку.
    error_file = ctx.extra.get("error_file", "unknown")
    return RecoveryResult(
        applied=True,
        env_changes=[f"patched: {error_file} (build config fix — stub, needs runtime parse)"],
    )
