"""UseAlternateAuth — настроить alternate auth method (GitAuthFailure)."""
from __future__ import annotations
import subprocess
from .base import RecoveryContext, RecoveryResult

def apply(ctx: RecoveryContext) -> RecoveryResult:
    remote_url = ctx.extra.get("remote_url", "")
    auth_method = ctx.extra.get("auth_method", "ssh")
    # Design-phase stub: реальная настройка требует credential helper / SSH key.
    # НЕ записывать секреты в репозиторий/логи.
    if auth_method == "ssh" and remote_url.startswith("https://"):
        # Convert HTTPS → SSH
        ssh_url = remote_url.replace("https://github.com/", "git@github.com:")
        ssh_url = ssh_url.replace("https://gitlab.com/", "git@gitlab.com:")
        try:
            subprocess.run(["git", "remote", "set-url", "origin", ssh_url],
                          cwd=str(ctx.workspace), check=True, capture_output=True, timeout=10)
            return RecoveryResult(applied=True, env_changes=[f"auth configured: ssh ({ssh_url})"])
        except subprocess.CalledProcessError as exc:
            return RecoveryResult(blocked=f"set-url failed: {exc}")
    return RecoveryResult(
        applied=True,
        env_changes=[f"auth configured: {auth_method} (stub — needs credential setup)"],
    )
