"""checkpoint — in-invocation git checkpoints (VSM-019, CONTRACT §5.1).

High-level primitive over git for the S1 triad's solve→control→verify revert
loop. A CheckpointManager captures workspace state as a git commit, and can
revert to it when test-control fails.

Lifecycle: ONE invoke(). Checkpoints are ephemeral temp-refs that do NOT
survive across invocations (CONTRACT §5.1: operational axis, not memory axis).
This preserves S1 statelessness between invocations (§5).

Design:
  - create() = `git add -A && git commit` on the current branch, returning the
    SHA. The commit is a normal commit (visible in git log), but the triad
    treats it as a temporary marker.
  - revert() = `git reset --hard <ref> && git clean -fd` (mirrors
    recovery_policies/reset_and_replay.py, but scoped to in-invocation use).
  - diff_since() = `git diff --name-status <ref>..HEAD` → list[Artifact].

Non-git workspaces degrade gracefully: create() returns a Checkpoint with
ref="none" and revert() is a no-op. This keeps the triad usable in workspaces
without git (the rule-based stubs / tests).
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .types import Artifact


@dataclass
class Checkpoint:
    """A single in-invocation checkpoint (git SHA or 'none' for non-git)."""
    ref: str               # git SHA, or "none" if workspace is not a git repo
    label: str             # human-readable, e.g. "pre-solve-iter-1"
    created_at: str        # iso8601
    empty: bool = False    # True if nothing to commit (clean tree)


@dataclass
class CheckpointManager:
    """In-invocation git checkpoints. Lifecycle = one invoke().

    Args:
        workspace: path to the task-scoped workspace.
        commit_prefix: prefix for checkpoint commit messages (auditability).
    """
    workspace: Path
    commit_prefix: str = "s1-checkpoint"
    _git_available: bool | None = field(default=None, init=False, repr=False)

    # ── git probe ──

    def _is_git(self) -> bool:
        """True if workspace is inside a git repo (cached after first call)."""
        if self._git_available is None:
            res = self._run(["rev-parse", "--is-inside-work-tree"])
            self._git_available = res.returncode == 0 and res.stdout.strip() == "true"
        return self._git_available

    def _run(self, args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Run git in workspace; returns CompletedProcess (never raises)."""
        try:
            return subprocess.run(
                ["git"] + args, cwd=str(self.workspace),
                capture_output=True, text=True, timeout=timeout,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Return a synthetic non-zero result so callers treat it as failure.
            return subprocess.CompletedProcess(
                args=["git"] + args, returncode=1, stdout="", stderr="git unavailable",
            )

    # ── public API ──

    def create(self, label: str) -> Checkpoint:
        """Create a checkpoint: `git add -A && git commit`. Returns the checkpoint.

        If the workspace is not a git repo, returns a no-op Checkpoint(ref="none").
        If the tree is clean (nothing to commit), returns an empty checkpoint
        with ref=HEAD SHA; revert() to it is still valid (restores to current state).
        """
        if not self._is_git():
            return Checkpoint(ref="none", label=label, created_at=_now_iso(), empty=True)

        ts = _now_iso()
        msg = f"{self.commit_prefix}: {label} @ {ts}"

        # Stage everything (tracked + new, including deletions).
        self._run(["add", "-A"])
        # Commit; --allow-empty so a clean-tree checkpoint is still a valid ref.
        commit_res = self._run(["commit", "--allow-empty", "-m", msg])
        empty = False
        if commit_res.returncode != 0:
            # `git commit` fails when there's nothing to commit AND --allow-empty
            # is unsupported (very old git) or in a detached/broken state. Fall
            # back to the current HEAD as the checkpoint ref.
            empty = True

        sha_res = self._run(["rev-parse", "HEAD"])
        ref = sha_res.stdout.strip() if sha_res.returncode == 0 else "none"
        return Checkpoint(ref=ref, label=label, created_at=ts, empty=empty)

    def revert(self, checkpoint: Checkpoint) -> bool:
        """Revert workspace to a checkpoint: `git reset --hard + git clean -fd`.

        Returns True if the revert succeeded. For a non-git checkpoint (ref="none"),
        returns False (caller should treat as unable-to-revert).
        """
        if checkpoint.ref == "none":
            return False
        if not self._is_git():
            return False

        # Abort any conflicting op first (mirrors reset_and_replay.py).
        for cmd in (["merge", "--abort"], ["rebase", "--abort"]):
            self._run(cmd, timeout=10)

        reset_res = self._run(["reset", "--hard", checkpoint.ref])
        self._run(["clean", "-fd"])
        return reset_res.returncode == 0

    def diff_since(self, checkpoint: Checkpoint) -> list[Artifact]:
        """List artifacts changed since a checkpoint, including uncommitted work.

        Combines two git queries:
          - `git diff --name-status <ref>` → tracked modifications/deletions.
          - `git ls-files --others --exclude-standard` → new untracked files
            (the solver creates these via fs.write after the checkpoint).

        This is the semantic the triad's control phase needs: "everything in
        the working tree that differs from the checkpoint state."

        Returns [] for non-git checkpoints or on error.
        """
        if checkpoint.ref == "none":
            return []
        if not self._is_git():
            return []

        artifacts: list[Artifact] = []

        # Tracked changes (modified/deleted/renamed since checkpoint).
        res = self._run(["diff", "--name-status", checkpoint.ref])
        if res.returncode == 0:
            for line in res.stdout.strip().splitlines():
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                status, path = parts[0], parts[-1]
                if status.startswith("D"):
                    artifacts.append(Artifact(path=path, op="deleted"))
                else:
                    artifacts.append(Artifact(path=path, op="modified"))

        # Untracked new files (created after checkpoint, never staged).
        ls_res = self._run(["ls-files", "--others", "--exclude-standard"])
        if ls_res.returncode == 0:
            for line in ls_res.stdout.strip().splitlines():
                path = line.strip()
                if path:
                    artifacts.append(Artifact(path=path, op="created"))

        return artifacts

    def current_ref(self) -> str:
        """Return current HEAD SHA (or 'none' if not a git repo)."""
        if not self._is_git():
            return "none"
        res = self._run(["rev-parse", "HEAD"])
        return res.stdout.strip() if res.returncode == 0 else "none"


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
