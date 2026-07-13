"""KillAndRestart — убить зависший процесс, очистить ресурсы (HangDetected)."""
from __future__ import annotations
import os
import signal
import subprocess
from .base import RecoveryContext, RecoveryResult

def apply(ctx: RecoveryContext) -> RecoveryResult:
    pid = ctx.extra.get("pid")
    changes = []
    if pid:
        try:
            os.kill(int(pid), signal.SIGKILL)
            changes.append(f"killed pid {pid}")
        except (ProcessLookupError, ValueError, PermissionError):
            pass
    # Очистка temp files
    import tempfile, glob
    temp_dir = tempfile.gettempdir()
    for pattern in ["*.tmp", "*.lock", "*.pid"]:
        for f in glob.glob(os.path.join(temp_dir, pattern)):
            try:
                os.unlink(f)
                changes.append(f"cleaned: {f}")
            except OSError:
                pass
    return RecoveryResult(applied=True, env_changes=changes or ["no processes to kill"])
