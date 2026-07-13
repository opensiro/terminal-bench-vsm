"""ClarifySpec — зафиксировать интерпретацию, отметить предположение (AmbiguousSpec)."""
from __future__ import annotations
from .base import RecoveryContext, RecoveryResult

def apply(ctx: RecoveryContext) -> RecoveryResult:
    interpretation = ctx.extra.get("interpretation", "default interpretation chosen")
    return RecoveryResult(
        applied=True,
        env_changes=[f"recorded interpretation: {interpretation}"],
    )
