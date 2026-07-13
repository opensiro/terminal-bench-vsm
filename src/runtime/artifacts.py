"""artifacts — filesystem diff (CONTRACT §3 artifacts)."""
from __future__ import annotations
import os
from pathlib import Path
from .types import Artifact


def snapshot(workspace: Path) -> dict[str, float]:
    """Take a snapshot of file mtimes in workspace."""
    snapshot = {}
    for root, dirs, files in os.walk(workspace):
        # Skip hidden dirs (.git, .venv, __pycache__)
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        for f in files:
            p = Path(root) / f
            try:
                rel = str(p.relative_to(workspace))
                snapshot[rel] = p.stat().st_mtime
            except (OSError, ValueError):
                pass
    return snapshot


def diff(before: dict[str, float], after: dict[str, float], workspace: Path) -> list[Artifact]:
    """Compute artifacts diff between two snapshots."""
    artifacts = []
    all_paths = set(before.keys()) | set(after.keys())
    for rel in sorted(all_paths):
        was_in = rel in before
        is_in = rel in after
        if is_in and not was_in:
            artifacts.append(Artifact(path=rel, op="created"))
        elif not is_in and was_in:
            artifacts.append(Artifact(path=rel, op="deleted"))
        elif is_in and was_in and before[rel] != after[rel]:
            artifacts.append(Artifact(path=rel, op="modified"))
    return artifacts
