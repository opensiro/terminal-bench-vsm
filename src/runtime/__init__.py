"""runtime — s1-dispatcher runtime (T2 CONTRACT implementation).

S1 stateless: fresh-per-invocation. Budget enforcement. Trace collection.
Failure observations extraction. Artifacts diff.

Two execution modes:
  1. AgentLoop (testing): RuleBasedSolver drives MCP tools in-process.
  2. HarnessRunner (production): external harness (Claude Code / Goose) drives
     MCP server as subprocess. Harness = brain, MCP = hands (VSM-005 membrane).
"""
from .types import S1Input, S1Output, TraceEntry, FailureObservation, Verdict, Budget, RecoveryDirective, Artifact
from .budget import BudgetTracker
from .dispatcher import S1Dispatcher, invoke
from .agent_loop import AgentLoop, RuleBasedSolver, SolverProtocol
from .llm_interface import LLMConfig, LLMSolverProtocol, build_llm_solver
from .harness import HarnessRunner, HarnessConfig

__all__ = [
    "S1Dispatcher", "invoke",
    "S1Input", "S1Output", "TraceEntry", "FailureObservation", "Verdict",
    "Budget", "RecoveryDirective", "Artifact",
    "BudgetTracker",
    "AgentLoop", "RuleBasedSolver", "SolverProtocol",
    "LLMConfig", "LLMSolverProtocol", "build_llm_solver",
    "HarnessRunner", "HarnessConfig",
]
