"""recovery_policies — executors для recovery policies (T3 runtime).

Каждая policy из failure_taxonomy.yaml имеет executor здесь. Executor применяет
policy к environment ВНЕ S1 — меняет env/state перед retry.

General-purpose по построению (не привязан к конкретному оценочному набору).
"""
from .base import RecoveryContext, RecoveryResult, get_executor

__all__ = ["RecoveryContext", "RecoveryResult", "get_executor"]
