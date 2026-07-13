"""base — shared types для recovery policy executors."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Anti-repeat limits per class (parsed from taxonomy s2_anti_repeat).
# Ключ — policy_id; значение — max attempts before bypass detection.
DEFAULT_POLICY_LIMITS: dict[str, int] = {
    "InstallTool": 1,
    "InstallDependency": 1,
    "CreateFreshVenv": 1,
    "FixBuildConfig": 2,
    "FixSyntax": 2,
    "DiagnoseAndPatch": 2,
    "RelocalizeAndReplay": 1,
    "ResetAndReplay": 1,
    "UseAlternateAuth": 1,
    "RetryWithSmallerScope": 2,
    "KillAndRestart": 1,
    "ReduceFootprint": 1,
    "FixPermissions": 1,
    "RetryWithBackoff": 3,
    "ClarifySpec": 1,
}


@dataclass
class RecoveryContext:
    """Вход для recovery executor."""

    policy_id: str
    failure_class: str
    workspace: Path
    failure_observations: list[dict[str, Any]]
    policy_attempt: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def limit(self) -> int:
        return DEFAULT_POLICY_LIMITS.get(self.policy_id, 2)

    @property
    def limit_exceeded(self) -> bool:
        return self.policy_attempt >= self.limit


@dataclass
class RecoveryResult:
    """Выход recovery executor."""

    applied: bool = False
    env_changes: list[str] = field(default_factory=list)
    blocked: str | None = None
    error: str | None = None


def check_anti_repeat(ctx: RecoveryContext) -> str | None:
    """Возвращает reason если anti-repeat limit превышен, иначе None."""
    if ctx.limit_exceeded:
        return (
            f"anti_repeat_limit_exceeded: policy={ctx.policy_id} "
            f"attempt={ctx.policy_attempt} limit={ctx.limit}"
        )
    return None


def get_executor(policy_id: str):
    """Возвращает функцию-executor для policy_id, или None."""
    from . import (
        install_tool, install_dependency, create_fresh_venv,
        fix_build_config, fix_syntax, diagnose_and_patch,
        relocalize, reset_and_replay, use_alternate_auth,
        retry_smaller_scope, kill_and_restart, reduce_footprint,
        fix_permissions, retry_with_backoff, clarify_spec,
    )
    registry = {
        "InstallTool": install_tool.apply,
        "InstallDependency": install_dependency.apply,
        "CreateFreshVenv": create_fresh_venv.apply,
        "FixBuildConfig": fix_build_config.apply,
        "FixSyntax": fix_syntax.apply,
        "DiagnoseAndPatch": diagnose_and_patch.apply,
        "RelocalizeAndReplay": relocalize.apply,
        "ResetAndReplay": reset_and_replay.apply,
        "UseAlternateAuth": use_alternate_auth.apply,
        "RetryWithSmallerScope": retry_smaller_scope.apply,
        "KillAndRestart": kill_and_restart.apply,
        "ReduceFootprint": reduce_footprint.apply,
        "FixPermissions": fix_permissions.apply,
        "RetryWithBackoff": retry_with_backoff.apply,
        "ClarifySpec": clarify_spec.apply,
    }
    return registry.get(policy_id)


def run_executor(ctx: RecoveryContext) -> RecoveryResult:
    """Запускает executor для ctx, с anti-repeat check."""
    reason = check_anti_repeat(ctx)
    if reason:
        return RecoveryResult(applied=False, blocked=reason)
    executor = get_executor(ctx.policy_id)
    if executor is None:
        return RecoveryResult(applied=False, blocked=f"unknown_policy: {ctx.policy_id}")
    try:
        result = executor(ctx)
        if not isinstance(result, RecoveryResult):
            return RecoveryResult(applied=False, error="executor returned non-RecoveryResult")
        return result
    except Exception as exc:
        return RecoveryResult(applied=False, error=f"{type(exc).__name__}: {exc}")
