"""runtime — s1-dispatcher runtime (T2 CONTRACT implementation).

S1 stateless: fresh-per-invocation. Budget enforcement. Trace collection.
Failure observations extraction. Artifacts diff. Agent loop with pluggable solver.
"""
from .types import S1Input, S1Output, TraceEntry, FailureObservation, Verdict
from .budget import BudgetTracker
from .dispatcher import S1Dispatcher, invoke
from .agent_loop import AgentLoop, RuleBasedSolver, SolverProtocol
from .llm_interface import LLMConfig, LLMSolverProtocol, build_llm_solver

__all__ = [
    "S1Dispatcher", "invoke",
    "S1Input", "S1Output", "TraceEntry", "FailureObservation", "Verdict",
    "BudgetTracker",
    "AgentLoop", "RuleBasedSolver", "SolverProtocol",
    "LLMConfig", "LLMSolverProtocol", "build_llm_solver",
]
