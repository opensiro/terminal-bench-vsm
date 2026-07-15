"""git tools — clone/commit/diff/status/checkout + in-invocation checkpoint primitives (VSM-019)."""
from __future__ import annotations
import subprocess
import time


def register_git_tools(server, workspace: str):
    def _git(args: list[str], cwd: str = workspace) -> dict:
        start = time.time()
        try:
            result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=30)
            return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode, "time_seconds": time.time() - start}
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "git timeout", "exit_code": 124, "time_seconds": 30.0}

    def git_clone(url: str, dest: str) -> dict:
        return _git(["clone", url, dest])

    def git_commit(message: str, paths: list[str] | None = None) -> dict:
        if paths:
            _git(["add"] + paths)
        return _git(["commit", "-m", message])

    def git_diff(ref_a: str = "HEAD", ref_b: str = "") -> dict:
        args = ["diff", ref_a]
        if ref_b:
            args.append(ref_b)
        return _git(args)

    def git_status() -> dict:
        return _git(["status", "--porcelain"])

    def git_checkout(ref: str) -> dict:
        return _git(["checkout", ref])

    # ── In-invocation checkpoint primitives (VSM-019, CONTRACT §5.1) ──
    # Used by CheckpointManager + s1-test-controller to implement the
    # solve→control→verify triad's revert loop. Lifecycle = one invoke().

    def git_stash_push(message: str = "") -> dict:
        """git stash push -u -m <message>; captures tracked+untracked into a stash ref."""
        args = ["stash", "push", "-u"]
        if message:
            args += ["-m", message]
        return _git(args)

    def git_rev_parse(ref: str = "HEAD") -> dict:
        """git rev-parse <ref>; resolves a ref to its SHA (checkpoint identity)."""
        return _git(["rev-parse", ref])

    def git_reset_hard(ref: str) -> dict:
        """git reset --hard <ref> + git clean -fd; reverts workspace to a checkpoint."""
        reset_res = _git(["reset", "--hard", ref])
        clean_res = _git(["clean", "-fd"])
        return {
            "stdout": reset_res["stdout"] + clean_res["stdout"],
            "stderr": reset_res["stderr"] + clean_res["stderr"],
            "exit_code": reset_res["exit_code"] or clean_res["exit_code"],
            "time_seconds": reset_res["time_seconds"] + clean_res["time_seconds"],
        }

    server.register("git.clone", "clone repository", {"type": "object", "properties": {"url": {"type": "string"}, "dest": {"type": "string"}}, "required": ["url", "dest"]}, git_clone)
    server.register("git.commit", "commit changes", {"type": "object", "properties": {"message": {"type": "string"}, "paths": {"type": "array", "items": {"type": "string"}}}, "required": ["message"]}, git_commit)
    server.register("git.diff", "show diff", {"type": "object", "properties": {"ref_a": {"type": "string", "default": "HEAD"}, "ref_b": {"type": "string", "default": ""}}}, git_diff)
    server.register("git.status", "show status", {"type": "object"}, git_status)
    server.register("git.checkout", "checkout ref", {"type": "object", "properties": {"ref": {"type": "string"}}, "required": ["ref"]}, git_checkout)
    server.register("git.stash_push", "stash tracked+untracked changes (checkpoint primitive, VSM-019)", {"type": "object", "properties": {"message": {"type": "string", "default": ""}}}, git_stash_push)
    server.register("git.rev_parse", "resolve ref to SHA (checkpoint identity, VSM-019)", {"type": "object", "properties": {"ref": {"type": "string", "default": "HEAD"}}}, git_rev_parse)
    server.register("git.reset_hard", "reset --hard + clean -fd to revert to checkpoint (VSM-019)", {"type": "object", "properties": {"ref": {"type": "string"}}, "required": ["ref"]}, git_reset_hard)

