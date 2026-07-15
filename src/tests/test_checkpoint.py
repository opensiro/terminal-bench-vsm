"""test_checkpoint — in-invocation git checkpoint primitive (VSM-019, CONTRACT §5.1).

Tests CheckpointManager: create/revert/diff lifecycle, non-git graceful
degradation, idempotent revert.

Run:
    cd ../src && python3 tests/test_checkpoint.py
    # or:
    cd ../src && python3 -m pytest tests/test_checkpoint.py -v

Requires git on PATH (most test cases). Non-git cases skip gracefully.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from runtime.checkpoint import Checkpoint, CheckpointManager
from runtime.artifacts import snapshot


GIT = shutil.which("git") is not None


def _git_repo() -> tuple[tempfile.TemporaryDirectory, Path]:
    """Create a temp dir with a git repo + initial commit. Returns (tmp, path)."""
    tmp = tempfile.TemporaryDirectory(prefix="ckpt-test-")
    p = Path(tmp.name)
    subprocess.run(["git", "init", "-q"], cwd=p, check=True)
    subprocess.run(["git", "config", "user.email", "test@vsm.local"], cwd=p, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=p, check=True)
    (p / "README.md").write_text("init\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=p, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=p, check=True)
    return tmp, p


# ── Tests ──

def test_create_returns_valid_sha():
    if not GIT:
        print("SKIP test_create_returns_valid_sha (no git)"); return
    tmp, p = _git_repo()
    try:
        mgr = CheckpointManager(p)
        cp = mgr.create("solve-start")
        assert cp.ref != "none", "ref should be a SHA in a git repo"
        assert len(cp.ref) == 40, f"expected SHA-1, got {cp.ref!r}"
        assert cp.label == "solve-start"
        print("PASS test_create_returns_valid_sha")
    finally:
        tmp.cleanup()


def test_revert_restores_deleted_file():
    if not GIT:
        print("SKIP test_revert_restores_deleted_file (no git)"); return
    tmp, p = _git_repo()
    try:
        mgr = CheckpointManager(p)
        # Add a real source file and checkpoint it.
        (p / "solution.py").write_text("def solve(): return 42\n", encoding="utf-8")
        cp = mgr.create("with-solution")
        assert cp.ref != "none"

        # Mutate: delete the file and break another.
        (p / "solution.py").unlink()
        (p / "bug.py").write_text("syntax error !!!\n", encoding="utf-8")
        assert not (p / "solution.py").exists()

        ok = mgr.revert(cp)
        assert ok, "revert should succeed in git repo"
        assert (p / "solution.py").exists(), "deleted file must be restored"
        assert (p / "solution.py").read_text() == "def solve(): return 42\n"
        assert not (p / "bug.py").exists(), "file created after checkpoint must be removed by clean -fd"
        print("PASS test_revert_restores_deleted_file")
    finally:
        tmp.cleanup()


def test_revert_restores_modified_content():
    if not GIT:
        print("SKIP test_revert_restores_modified_content (no git)"); return
    tmp, p = _git_repo()
    try:
        mgr = CheckpointManager(p)
        (p / "mod.txt").write_text("original\n", encoding="utf-8")
        cp = mgr.create("original-state")

        (p / "mod.txt").write_text("BROKEN\n", encoding="utf-8")
        assert (p / "mod.txt").read_text() == "BROKEN\n"

        mgr.revert(cp)
        assert (p / "mod.txt").read_text() == "original\n", "modified content must be restored"
        print("PASS test_revert_restores_modified_content")
    finally:
        tmp.cleanup()


def test_diff_since_detects_changes():
    if not GIT:
        print("SKIP test_diff_since_detects_changes (no git)"); return
    tmp, p = _git_repo()
    try:
        mgr = CheckpointManager(p)
        (p / "keep.py").write_text("x=1\n", encoding="utf-8")
        cp = mgr.create("baseline")

        (p / "new.py").write_text("y=2\n", encoding="utf-8")
        (p / "keep.py").write_text("x=2\n", encoding="utf-8")  # modified

        diffs = mgr.diff_since(cp)
        ops = {a.path: a.op for a in diffs}
        assert ops.get("new.py") == "created", f"new.py should be created, got {ops}"
        assert ops.get("keep.py") == "modified", f"keep.py should be modified, got {ops}"
        print("PASS test_diff_since_detects_changes")
    finally:
        tmp.cleanup()


def test_revert_idempotent():
    """Reverting twice to the same checkpoint should not error."""
    if not GIT:
        print("SKIP test_revert_idempotent (no git)"); return
    tmp, p = _git_repo()
    try:
        mgr = CheckpointManager(p)
        (p / "a.txt").write_text("v1\n", encoding="utf-8")
        cp = mgr.create("v1")
        (p / "a.txt").write_text("v2\n", encoding="utf-8")
        assert mgr.revert(cp)
        assert mgr.revert(cp), "second revert should also succeed (idempotent)"
        assert (p / "a.txt").read_text() == "v1\n"
        print("PASS test_revert_idempotent")
    finally:
        tmp.cleanup()


def test_non_git_workspace_degrades_gracefully():
    """Non-git workspace: create → ref='none', revert → False, diff → []."""
    tmp = tempfile.TemporaryDirectory(prefix="ckpt-nogit-")
    try:
        p = Path(tmp.name)
        # No git init.
        mgr = CheckpointManager(p)
        cp = mgr.create("no-git")
        assert cp.ref == "none", f"non-git ref must be 'none', got {cp.ref!r}"
        assert cp.empty, "non-git checkpoint should be marked empty"
        assert mgr.revert(cp) is False, "revert on non-git must return False"
        assert mgr.diff_since(cp) == [], "diff on non-git must be empty"
        assert mgr.current_ref() == "none"
        print("PASS test_non_git_workspace_degrades_gracefully")
    finally:
        tmp.cleanup()


def test_empty_tree_checkpoint_is_valid_ref():
    """Checkpoint on a clean tree (--allow-empty) yields a valid ref to revert to."""
    if not GIT:
        print("SKIP test_empty_tree_checkpoint_is_valid_ref (no git)"); return
    tmp, p = _git_repo()
    try:
        mgr = CheckpointManager(p)
        cp = mgr.create("clean")
        assert cp.ref != "none", "clean-tree checkpoint should still resolve HEAD"
        # Revert to it (no changes since) — should be a no-op success.
        assert mgr.revert(cp)
        print("PASS test_empty_tree_checkpoint_is_valid_ref")
    finally:
        tmp.cleanup()


def _main():
    tests = [
        test_create_returns_valid_sha,
        test_revert_restores_deleted_file,
        test_revert_restores_modified_content,
        test_diff_since_detects_changes,
        test_revert_idempotent,
        test_non_git_workspace_degrades_gracefully,
        test_empty_tree_checkpoint_is_valid_ref,
    ]
    for t in tests:
        t()
    print(f"\nAll {len(tests)} checkpoint tests passed.")


if __name__ == "__main__":
    _main()
