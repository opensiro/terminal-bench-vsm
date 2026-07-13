"""DiagnoseAndPatch — диагностика assertion, минимальная правка в реализации (TestFailure)."""
from __future__ import annotations
from .base import RecoveryContext, RecoveryResult

def apply(ctx: RecoveryContext) -> RecoveryResult:
    # Design-phase stub: реальный фикс требует parse failed assertion (expected vs actual).
    # NEVER править тест чтобы он прошёл (circumvent_recovery).
    test_name = ctx.extra.get("test_name", "unknown")
    return RecoveryResult(
        applied=True,
        env_changes=[f"patched implementation for {test_name} (stub — needs assertion parse)"],
    )
