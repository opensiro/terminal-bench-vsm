"""RetryWithBackoff — повторить с экспоненциальным backoff (NetworkError)."""
from __future__ import annotations
import time
from .base import RecoveryContext, RecoveryResult

def apply(ctx: RecoveryContext) -> RecoveryResult:
    max_retries = ctx.extra.get("max_retries", 3)
    # Exponential backoff: 1s, 2s, 4s
    delays = [2 ** i for i in range(max_retries)]
    # Design-phase: actual retry выполняет S1 (stateless), executor только рекомендует.
    return RecoveryResult(
        applied=True,
        env_changes=[f"retry with backoff (delays={delays}s, max={max_retries})"],
    )
