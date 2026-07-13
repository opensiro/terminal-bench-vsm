"""s2 — coordinator runtime (PIPELINES.md implementation).

S2 is the arbiter: the only component that authorizes retry.
4-check pipeline: anti-repeat → conflict → oscillation → authorize.
"""
from .types import AttemptRecord, RetryHistory, ResourceClaim, AuthorizationResult
from .coordinator import S2Coordinator
from .conflict import ConflictDetector

__all__ = [
    "AttemptRecord", "RetryHistory", "ResourceClaim", "AuthorizationResult",
    "S2Coordinator", "ConflictDetector",
]
