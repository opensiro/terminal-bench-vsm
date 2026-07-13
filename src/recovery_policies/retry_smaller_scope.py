"""RetryWithSmallerScope — декомпозировать действие, повторить с меньшим scope (TimeoutExpired)."""
from __future__ import annotations
from .base import RecoveryContext, RecoveryResult

def apply(ctx: RecoveryContext) -> RecoveryResult:
    # Не мутирует env; возвращает directive для S1 — декомпозировать.
    original_action = ctx.extra.get("original_action", "unknown")
    return RecoveryResult(
        applied=True,
        env_changes=[f"decomposed: {original_action} (reduced scope for retry)"],
    )
