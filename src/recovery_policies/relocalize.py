"""RelocalizeAndReplay — переискать целевой файл/символ (FileLocalizationError)."""
from __future__ import annotations
import re
import subprocess
from pathlib import Path
from .base import RecoveryContext, RecoveryResult

# VSM-034 SECONDARY-1: extract a search pattern from "No such file" style
# observation messages. Orchestrator does not populate ctx.extra (no plumbing
# for it), so we derive the pattern directly from failure_observations, which
# already carry the raw error strings (e.g. "can't open file '/x/y.py'",
# "No module named z", "No such file or directory: foo"). The basename or
# module name is a good grep pattern to relocalize the missing artifact.
_FILE_RE = re.compile(r"(?:can't open file |No such file or directory[^\n]*?|open: )[']([^']+)'")
_MODULE_RE = re.compile(r"No module named\s+([A-Za-z_][\w.]*)")
_PATH_RE = re.compile(r"([A-Za-z_][\w./-]+\.(?:py|sh|toml|yaml|yml|json|txt|md))")


def _derive_search_pattern(failure_observations: list[dict]) -> str | None:
    """Best-effort: pull a file/module name out of error strings.

    Returns a grep-friendly pattern (file basename or module name), or None if
    nothing recognizable is found (caller keeps the current 'blocked' behavior).
    """
    seen: list[str] = []
    for obs in failure_observations or []:
        # observations carry 'value' (T2 CONTRACT §6) — fall back to common keys.
        text = str(obs.get("value") or obs.get("observation_value") or obs.get("message") or "")
        if not text:
            continue
        for rx in (_FILE_RE, _MODULE_RE, _PATH_RE):
            m = rx.search(text)
            if m:
                candidate = m.group(1).strip()
                # Reduce to basename — grep -r walks the tree anyway, and a full
                # path from a wrong cwd would never match under repo_root.
                candidate = candidate.split("/")[-1]
                if candidate and candidate not in seen:
                    seen.append(candidate)
                break
    return seen[0] if seen else None


def apply(ctx: RecoveryContext) -> RecoveryResult:
    # VSM-034 SECONDARY-1: orchestrator does not populate ctx.extra today.
    # Prefer an explicit hint if one is supplied; otherwise derive it from the
    # failure observations that drove the FileLocalizationError classification.
    pattern = ctx.extra.get("search_pattern") or _derive_search_pattern(
        getattr(ctx, "failure_observations", []) or []
    )
    if not pattern:
        return RecoveryResult(blocked="missing search_pattern")
    repo_root = str(ctx.workspace)
    try:
        result = subprocess.run(
            ["grep", "-rl", "--include=*.py", pattern, repo_root],
            capture_output=True, text=True, timeout=30,
        )
        files = [f for f in result.stdout.strip().split("\n") if f]
        if files:
            return RecoveryResult(
                applied=True,
                env_changes=[f"relocalized: {files[0]} (found {len(files)} matches)"],
            )
        return RecoveryResult(blocked=f"pattern '{pattern}' not found in {repo_root}")
    except subprocess.TimeoutExpired:
        return RecoveryResult(blocked="grep timeout")
