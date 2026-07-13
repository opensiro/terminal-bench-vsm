"""ResetAndReplay — git reset на чистое состояние задачи (GitConflict)."""
from __future__ import annotations
import subprocess
from .base import RecoveryContext, RecoveryResult

def apply(ctx: RecoveryContext) -> RecoveryResult:
    workspace = str(ctx.workspace)
    clean_ref = ctx.extra.get("clean_ref", "HEAD")
    try:
        # Abort любой конфликтующей операции
        for cmd in (["git", "merge", "--abort"], ["git", "rebase", "--abort"]):
            subprocess.run(cmd, cwd=workspace, capture_output=True, timeout=10)
        # Reset
        subprocess.run(["git", "reset", "--hard", clean_ref], cwd=workspace, check=True, capture_output=True, timeout=30)
        subprocess.run(["git", "clean", "-fd"], cwd=workspace, check=True, capture_output=True, timeout=30)
        return RecoveryResult(applied=True, env_changes=[f"git reset to {clean_ref}", "git clean -fd"])
    except subprocess.CalledProcessError as exc:
        return RecoveryResult(blocked=f"git reset failed: {exc}")
