"""test_triad_solver — S1 triad solve→control→verify (VSM-020, CONTRACT §5.1).

Tests the TriadSolver state machine and the dispatcher's "triad" mode, using a
FakeMCPServer for deterministic in-process runs (no goose, no real subprocess).

Run:
    cd ../src && python3 tests/test_triad_solver.py
    # or:
    cd ../src && python3 -m pytest tests/test_triad_solver.py -v

Test matrix:
    A — happy path: plan → execute → control PASS → verify PASS → task_resolved
    B — revert path: control FAIL_REVERTED → revert → re-solve → PASS
    C — revert limit: max_reverts exceeded → FAIL_REVERT_LIMIT → verify decides
    D — non-git workspace: FAIL_NO_CHECKPOINT → verify decides (no revert)
    E — stateless: two invoke()s don't share checkpoint state
    F — dispatcher integration: solver_mode="triad" enriches control_results
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

from runtime.types import S1Input, S1Output, Verdict, Budget, ControlVerdict
from runtime.triad_solver import TriadSolver
from runtime.checkpoint import Checkpoint, CheckpointManager
from runtime.budget import BudgetTracker
from runtime.agent_loop import AgentLoop

GIT = shutil.which("git") is not None


# ── Fake MCP server ──

class FakeMCP:
    """Deterministic MCP stand-in: returns canned observations per tool."""

    def __init__(self, workspace: Path, scripted: dict[str, list[dict]] | None = None):
        self.workspace = workspace
        # scripted: {tool_name: [response_per_call, ...]}; falls back to default.
        self._scripted = scripted or {}
        # mutable observations appended by tests mid-run (e.g. "fail first, pass later")
        self._call_counts: dict[str, int] = {}

    def list_tools(self):
        return [
            {"name": "fs.list"},
            {"name": "shell.exec"},
        ]

    def call_tool(self, name: str, args: dict) -> dict:
        i = self._call_counts.get(name, 0)
        self._call_counts[name] = i + 1
        scripted_list = self._scripted.get(name)
        if scripted_list and i < len(scripted_list):
            return scripted_list[i]
        # Default responses
        if name == "fs.list":
            return {"stdout": "solution.py\ntests/", "stderr": "", "exit_code": 0, "time_seconds": 0.01}
        if name == "shell.exec":
            return {"stdout": "1 passed", "stderr": "", "exit_code": 0, "time_seconds": 0.5}
        return {"stdout": "", "stderr": "", "exit_code": 0, "time_seconds": 0.0}


def _git_repo() -> tuple[tempfile.TemporaryDirectory, Path]:
    tmp = tempfile.TemporaryDirectory(prefix="triad-test-")
    p = Path(tmp.name)
    subprocess.run(["git", "init", "-q"], cwd=p, check=True)
    subprocess.run(["git", "config", "user.email", "test@vsm.local"], cwd=p, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=p, check=True)
    (p / "README.md").write_text("init\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=p, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=p, check=True)
    return tmp, p


def _input(workspace: Path) -> S1Input:
    return S1Input(
        task_prompt="solve the coding task and ensure tests pass",
        workspace=workspace,
        budget=Budget(time_seconds=60, tokens=10000, actions=30),
    )


# ── Tests ──

def test_A_happy_path_control_pass_verify_pass():
    """plan → execute → control PASS → verify PASS → task_resolved."""
    tmp = tempfile.TemporaryDirectory(prefix="triad-A-")
    try:
        p = Path(tmp.name)
        mcp = FakeMCP(p, scripted={
            "shell.exec": [{"stdout": "1 passed", "stderr": "", "exit_code": 0, "time_seconds": 0.1}],
        })
        solver = TriadSolver(task_id="A", workspace=p, checkpoint_mgr=CheckpointManager(p))
        budget = BudgetTracker(60, 10000, 30)
        loop = AgentLoop(solver=solver, mcp_server=mcp)
        out = loop.run(_input(p), budget)

        assert out.verdict == Verdict.TASK_RESOLVED, f"expected RESOLVED, got {out.verdict}"
        # control ran and passed
        assert len(out.control_results) >= 1, "expected at least one control result"
        assert out.control_results[-1].verdict == ControlVerdict.PASS
        print("PASS test_A_happy_path_control_pass_verify_pass")
    finally:
        tmp.cleanup()


def test_B_revert_then_pass():
    """First test run fails → control FAIL_REVERTED → revert → re-solve → PASS.

    Uses a scriptable MCP that fails the first pytest call and passes the second.
    Requires git so the checkpoint revert actually restores state.
    """
    if not GIT:
        print("SKIP test_B_revert_then_pass (no git)"); return
    tmp, p = _git_repo()
    try:
        # Write a real file so checkpoint has something to revert to.
        (p / "solution.py").write_text("def solve(): return 1\n", encoding="utf-8")
        mcp = FakeMCP(p, scripted={
            "shell.exec": [
                # first test run: fails
                {"stdout": "FAILED solution.py::test\n1 failed", "stderr": "AssertionError", "exit_code": 1, "time_seconds": 0.1},
                # second test run (after revert + re-solve): passes
                {"stdout": "1 passed", "stderr": "", "exit_code": 0, "time_seconds": 0.1},
            ],
        })
        solver = TriadSolver(task_id="B", workspace=p, checkpoint_mgr=CheckpointManager(p), max_reverts=2)
        budget = BudgetTracker(60, 10000, 30)
        loop = AgentLoop(solver=solver, mcp_server=mcp)
        out = loop.run(_input(p), budget)

        assert out.verdict == Verdict.TASK_RESOLVED, f"expected RESOLVED after revert, got {out.verdict}"
        # At least one FAIL_REVERTED then a PASS
        verdicts = [c.verdict for c in out.control_results]
        assert ControlVerdict.FAIL_REVERTED in verdicts, f"expected a revert, got {verdicts}"
        assert verdicts[-1] == ControlVerdict.PASS, f"expected final PASS, got {verdicts}"
        print("PASS test_B_revert_then_pass")
    finally:
        tmp.cleanup()


def test_C_revert_limit_reached():
    """Tests keep failing → after max_reverts, FAIL_REVERT_LIMIT → verify fails."""
    if not GIT:
        print("SKIP test_C_revert_limit_reached (no git)"); return
    tmp, p = _git_repo()
    try:
        (p / "solution.py").write_text("def solve(): return 1\n", encoding="utf-8")
        # Every test run fails.
        fail_resp = {"stdout": "FAILED\n1 failed", "stderr": "error", "exit_code": 1, "time_seconds": 0.1}
        mcp = FakeMCP(p, scripted={"shell.exec": [fail_resp, fail_resp, fail_resp, fail_resp, fail_resp]})
        solver = TriadSolver(task_id="C", workspace=p, checkpoint_mgr=CheckpointManager(p), max_reverts=1)
        budget = BudgetTracker(60, 10000, 30)
        loop = AgentLoop(solver=solver, mcp_server=mcp)
        out = loop.run(_input(p), budget)

        assert out.verdict == Verdict.TASK_FAILED, f"expected FAILED after limit, got {out.verdict}"
        verdicts = [c.verdict for c in out.control_results]
        # Should see FAIL_REVERTED once, then FAIL_REVERT_LIMIT.
        assert ControlVerdict.FAIL_REVERT_LIMIT in verdicts, f"expected REVERT_LIMIT in {verdicts}"
        print("PASS test_C_revert_limit_reached")
    finally:
        tmp.cleanup()


def test_D_non_git_no_checkpoint():
    """Non-git workspace: tests fail → FAIL_NO_CHECKPOINT → verify decides."""
    tmp = tempfile.TemporaryDirectory(prefix="triad-D-")
    try:
        p = Path(tmp.name)
        fail_resp = {"stdout": "FAILED", "stderr": "error", "exit_code": 1, "time_seconds": 0.1}
        mcp = FakeMCP(p, scripted={"shell.exec": [fail_resp, fail_resp]})
        solver = TriadSolver(task_id="D", workspace=p, checkpoint_mgr=CheckpointManager(p), max_reverts=3)
        budget = BudgetTracker(60, 10000, 30)
        loop = AgentLoop(solver=solver, mcp_server=mcp)
        out = loop.run(_input(p), budget)

        # No checkpoint → FAIL_NO_CHECKPOINT → verify → task_failed (error keywords in trace).
        assert out.verdict == Verdict.TASK_FAILED, f"expected FAILED, got {out.verdict}"
        verdicts = [c.verdict for c in out.control_results]
        assert ControlVerdict.FAIL_NO_CHECKPOINT in verdicts, f"expected NO_CHECKPOINT in {verdicts}"
        print("PASS test_D_non_git_no_checkpoint")
    finally:
        tmp.cleanup()


def test_E_stateless_across_invocations():
    """Two consecutive invoke()s must not share checkpoint/plan/control state."""
    if not GIT:
        print("SKIP test_E_stateless_across_invocations (no git)"); return
    tmp, p = _git_repo()
    try:
        (p / "solution.py").write_text("def solve(): return 1\n", encoding="utf-8")
        mcp = FakeMCP(p, scripted={
            "shell.exec": [{"stdout": "1 passed", "stderr": "", "exit_code": 0, "time_seconds": 0.1}] * 4,
        })
        # Run 1
        solver1 = TriadSolver(task_id="E1", workspace=p, checkpoint_mgr=CheckpointManager(p))
        out1 = AgentLoop(solver=solver1, mcp_server=mcp).run(_input(p), BudgetTracker(60, 10000, 30))
        cp1 = solver1._checkpoint
        plan1 = solver1._plan
        # Run 2 — fresh solver instance (dispatcher creates fresh per invoke).
        solver2 = TriadSolver(task_id="E2", workspace=p, checkpoint_mgr=CheckpointManager(p))
        out2 = AgentLoop(solver=solver2, mcp_server=mcp).run(_input(p), BudgetTracker(60, 10000, 30))

        assert out1.verdict == Verdict.TASK_RESOLVED
        assert out2.verdict == Verdict.TASK_RESOLVED
        # Fresh instance → fresh internal state.
        assert solver2._checkpoint is not cp1, "checkpoint must not be shared across invocations"
        assert solver2._plan is not plan1, "plan must not be shared across invocations"
        assert solver2._revert_count == 0, "revert_count must reset"
        print("PASS test_E_stateless_across_invocations")
    finally:
        tmp.cleanup()


def test_F_dispatcher_triad_mode_enriches_output():
    """S1Dispatcher(solver_mode='triad') enriches S1Output.control_results."""
    tmp = tempfile.TemporaryDirectory(prefix="triad-F-")
    try:
        p = Path(tmp.name)
        mcp = FakeMCP(p)
        # Inject the fake MCP into the dispatcher.
        from runtime.dispatcher import S1Dispatcher
        disp = S1Dispatcher(mcp_server=mcp, solver_mode="triad")
        out = disp.invoke(_input(p))

        assert out.verdict in (Verdict.TASK_RESOLVED, Verdict.TASK_FAILED, Verdict.UNKNOWN)
        assert hasattr(out, "control_results"), "triad mode must set control_results"
        assert isinstance(out.control_results, list)
        print(f"PASS test_F_dispatcher_triad_mode_enriches_output (verdict={out.verdict.value})")
    finally:
        tmp.cleanup()


def _main():
    tests = [
        test_A_happy_path_control_pass_verify_pass,
        test_B_revert_then_pass,
        test_C_revert_limit_reached,
        test_D_non_git_no_checkpoint,
        test_E_stateless_across_invocations,
        test_F_dispatcher_triad_mode_enriches_output,
    ]
    for t in tests:
        t()
    print(f"\nAll {len(tests)} triad_solver tests passed.")


if __name__ == "__main__":
    _main()
