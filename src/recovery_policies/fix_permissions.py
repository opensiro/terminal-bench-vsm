"""FixPermissions — минимальная правка прав (PermissionDenied)."""
from __future__ import annotations
import os
import stat
from pathlib import Path
from .base import RecoveryContext, RecoveryResult

def apply(ctx: RecoveryContext) -> RecoveryResult:
    path = ctx.extra.get("path")
    required_access = ctx.extra.get("required_access", "write")
    if not path:
        return RecoveryResult(blocked="missing path")
    try:
        p = Path(path)
        mode = p.stat().st_mode
        if required_access == "write":
            os.chmod(p, mode | stat.S_IWUSR)
        elif required_access == "read":
            os.chmod(p, mode | stat.S_IRUSR)
        elif required_access == "exec":
            os.chmod(p, mode | stat.S_IXUSR)
        return RecoveryResult(applied=True, env_changes=[f"chmod {path} (+{required_access})"])
    except OSError as exc:
        return RecoveryResult(blocked=f"chmod failed: {exc}")
