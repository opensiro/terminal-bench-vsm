"""dispatcher — s1-dispatcher runtime (T2 CONTRACT §4 lifecycle).

Stateless (CONTRACT §5): fresh-per-invocation. No state between runs.

Two execution modes:
  1. AgentLoop (default, for testing): RuleBasedSolver drives MCP tools in-process.
  2. HarnessRunner (production): external harness (Claude Code / Goose) drives
     MCP server as subprocess. Harness = brain, MCP = hands (VSM-005 membrane).
"""
from __future__ import annotations

from pathlib import Path
from .types import S1Input, S1Output, Verdict
from .budget import BudgetTracker
from .artifacts import snapshot, diff


class S1Dispatcher:
    """S1 dispatcher: launch → isolate → trace → collect output.

    Stateless: each invoke() is independent. No state between invocations.

    Args:
        mcp_server: in-process MCP server (for AgentLoop mode). If None + no
            harness, creates one automatically.
        harness: HarnessRunner for production mode. If set, uses external harness
            instead of in-process AgentLoop.
    """

    def __init__(self, mcp_server=None, harness=None):
        self._mcp_server = mcp_server
        self._harness = harness

    def invoke(self, input: S1Input) -> S1Output:
        """One invocation of S1 solver (CONTRACT §4 lifecycle).

        1. Snapshot filesystem (for artifacts diff).
        2. Launch solver (AgentLoop or HarnessRunner), under budget.
        3. Solver works until verdict OR budget exhaustion.
        4. Collect trace + artifacts diff + failure_observations.
        """
        # Harness mode: external harness + MCP subprocess
        if self._harness is not None:
            return self._harness.invoke(input)

        # AgentLoop mode: in-process solver + MCP
        return self._invoke_agent_loop(input)

    def _invoke_agent_loop(self, input: S1Input) -> S1Output:
        """In-process AgentLoop mode (for testing)."""
        from .solver import solve

        # 1. Snapshot
        fs_before = snapshot(input.workspace)

        # 2. Budget tracker
        budget = BudgetTracker(
            time_seconds=input.budget.time_seconds,
            tokens=input.budget.tokens,
            actions=input.budget.actions,
        )

        # 3. Get MCP server
        if self._mcp_server is None:
            from mcp_server.server import create_server
            self._mcp_server = create_server(str(input.workspace))

        # 4. Run solver
        output = solve(input, self._mcp_server, budget)

        # 5. Artifacts diff
        fs_after = snapshot(input.workspace)
        output.artifacts = diff(fs_before, fs_after, input.workspace)

        # 6. Budget check
        if budget.exhausted and output.verdict != Verdict.TASK_RESOLVED:
            output.verdict = Verdict.BUDGET_EXHAUSTED

        output.cost = budget.summary()
        return output


def invoke(input: S1Input, mcp_server=None, harness=None) -> S1Output:
    """Convenience function: create dispatcher and invoke.

    If harness is provided, uses HarnessRunner (production mode).
    Otherwise uses AgentLoop with RuleBasedSolver (testing mode).
    """
    dispatcher = S1Dispatcher(mcp_server=mcp_server, harness=harness)
    return dispatcher.invoke(input)
