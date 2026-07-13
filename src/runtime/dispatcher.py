"""dispatcher — s1-dispatcher runtime (T2 CONTRACT §4 lifecycle).

Stateless (CONTRACT §5): fresh-per-invocation. No state between runs.
Budget enforcement. Trace collection. Failure observations extraction.
"""
from __future__ import annotations
import time
from pathlib import Path
from .types import S1Input, S1Output, Verdict
from .budget import BudgetTracker
from .artifacts import snapshot, diff
from .solver import solve


class S1Dispatcher:
    """S1 dispatcher: launch → isolate → trace → collect output.

    Stateless: each invoke() is independent. No state between invocations.
    """

    def __init__(self, mcp_server=None):
        self._mcp_server = mcp_server

    def invoke(self, input: S1Input) -> S1Output:
        """One invocation of S1 solver (CONTRACT §4 lifecycle).

        1. Snapshot filesystem (for artifacts diff).
        2. Launch solver in task-scoped workspace, under budget.
        3. Solver works until verdict OR budget exhaustion.
        4. Collect trace + artifacts diff + failure_observations.
        """
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


def invoke(input: S1Input, mcp_server=None) -> S1Output:
    """Convenience function: create dispatcher and invoke."""
    dispatcher = S1Dispatcher(mcp_server=mcp_server)
    return dispatcher.invoke(input)
