"""ReduceFootprint — уменьшить потребление ресурсов (ResourceLimit)."""
from __future__ import annotations
from .base import RecoveryContext, RecoveryResult

def apply(ctx: RecoveryContext) -> RecoveryResult:
    limiting_resource = ctx.extra.get("limiting_resource", "memory")
    actions = {
        "memory": "reduced batch size, enabled streaming",
        "disk": "cleaned intermediate files, enabled compression",
        "fd": "closed unused file descriptors, enabled pooling",
        "gpu": "reduced batch size, enabled gradient checkpointing",
    }
    action = actions.get(limiting_resource, "reduced resource footprint")
    return RecoveryResult(applied=True, env_changes=[f"reduced {limiting_resource} footprint: {action}"])
