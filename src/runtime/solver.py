"""solver — S1 solver entry point (T2 CONTRACT §4 lifecycle).

Uses AgentLoop with a pluggable solver (RuleBasedSolver for testing,
LLMSolver for production). Stateless (CONTRACT §5).
"""
from __future__ import annotations
from .types import S1Input, S1Output, Verdict
from .budget import BudgetTracker
from .agent_loop import AgentLoop, RuleBasedSolver


# Default solver: RuleBasedSolver (deterministic stub).
# Production: replace with LLM solver from llm_interface.py.
_default_solver = RuleBasedSolver()


def solve(input: S1Input, mcp_server, budget: BudgetTracker) -> S1Output:
    """Run solver on task using AgentLoop.

    Uses the default RuleBasedSolver. For LLM solver, pass a custom AgentLoop
    to S1Dispatcher.
    """
    loop = AgentLoop(solver=_default_solver, mcp_server=mcp_server)
    return loop.run(input, budget)


def solve_with_solver(input: S1Input, mcp_server, budget: BudgetTracker, solver) -> S1Output:
    """Run solver with a custom solver (e.g., LLM solver).

    solver must implement SolverProtocol (see agent_loop.py).
    """
    loop = AgentLoop(solver=solver, mcp_server=mcp_server)
    return loop.run(input, budget)
