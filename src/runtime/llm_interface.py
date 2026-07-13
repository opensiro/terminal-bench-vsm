"""llm_interface — protocol and adapter for LLM-backed solvers.

Production LLM path = external harness (Goose / Claude Code) via HarnessRunner.
The harness IS the LLM brain; our MCP server provides restricted tools (the
"hands", VSM-005 membrane). This module therefore does NOT make in-process LLM
API calls — the in-process API path is deliberately closed: Goose+ZAI (and
Claude Code) are reached through HarnessRunner as a subprocess that connects to
our MCP server as its tool provider.

LLMSolverProtocol below is the CONTRACT such a solver would satisfy if an
in-process API integration were ever added. HarnessSolverAdapter implements
that contract by delegating to HarnessRunner, so the production path can be
wired through AgentLoop where convenient (though typically HarnessRunner is
used directly via S1Dispatcher.invoke(harness=...)).

Stateless (CONTRACT §5): solvers do not persist state between invocations.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
from .types import TraceEntry


@runtime_checkable
class LLMSolverProtocol(Protocol):
    """Protocol for LLM-based solvers (contract).

    A full in-process implementation would:
    1. Construct a prompt from task_prompt + trace history + available tools.
    2. Call an LLM API (OpenAI, Anthropic, local model, ...).
    3. Parse the LLM response into a tool call decision.
    4. Return the decision (same format as SolverProtocol.decide_next_action).

    NOTE: the in-process API path is not implemented — production reaches the
    LLM through HarnessRunner (external harness subprocess + MCP server).
    HarnessSolverAdapter is the bridge that satisfies this protocol via the
    harness.

    Cross-provider note (VSM-001): S3* must use a different provider than S1.
    S1's LLM provider is configured here; S3*'s is in audit/config.py.
    """

    provider: str  # "openai" | "anthropic" | "local" | "zai" | "goose" | ...

    def decide_next_action(
        self,
        task_prompt: str,
        trace: list[TraceEntry],
        available_tools: list[str],
        recovery_directive: dict | None,
        budget_remaining: dict[str, float],
    ) -> dict[str, Any]:
        """Decide next tool call based on LLM reasoning.

        Returns:
            {"tool": <name>, "args": {...}, "thought": <reasoning>}
            or {"tool": "__done__", "verdict": "task_resolved"|"task_failed", "thought": "..."}
        """
        ...


@dataclass
class LLMConfig:
    """Configuration for LLM solver.

    provider/model are documented here for the S3* cross-provider constraint
    (VSM-001): S3* must use a different provider than S1. The actual production
    path consumes these via the harness (HarnessRunner), not in-process API
    calls. API key and model are set at deployment, not hardcoded.
    """

    provider: str = "openai"           # must be set at deployment
    model: str = "gpt-4"               # default model
    max_tokens_per_call: int = 2000    # token budget per LLM call
    temperature: float = 0.1           # low for deterministic coding
    system_prompt: str = ""            # task-specific system prompt

    # API configuration (set at deployment, NOT hardcoded in source)
    api_key_env: str = "LLM_API_KEY"   # environment variable name
    base_url: str | None = None        # custom base URL (for local models)

    def validate(self) -> str | None:
        """Returns error message if config invalid, None if OK."""
        if not self.provider:
            return "provider not set"
        if self.provider not in ("openai", "anthropic", "local", "custom",
                                 "zai", "goose"):
            return f"unknown provider: {self.provider}"
        return None


@dataclass
class HarnessSolverAdapter:
    """Adapter: HarnessRunner as SolverProtocol implementation.

    Production LLM path = external harness (Goose / Claude Code) via
    HarnessRunner. The harness IS the LLM brain; our MCP server provides
    restricted tools. This adapter wraps HarnessRunner so it can be used as a
    SolverProtocol in AgentLoop (though typically HarnessRunner is used directly
    via S1Dispatcher.invoke(harness=...)).
    """
    harness: Any  # HarnessRunner
    input: Any    # S1Input template

    def decide_next_action(self, task_prompt, trace, available_tools,
                           recovery_directive, budget_remaining):
        """Delegate to harness.invoke. Returns __done__ with harness verdict."""
        # Note: HarnessRunner.invoke runs the FULL solver loop internally
        # (harness decides all actions, calls MCP tools, exits). It doesn't
        # do one-action-per-call. So this adapter is a bridge: it runs the
        # harness to completion and returns the final verdict.
        from .types import S1Input, S1Output, Verdict
        output = self.harness.invoke(self.input)
        verdict_str = output.verdict.value if hasattr(output.verdict, 'value') else str(output.verdict)
        return {
            "tool": "__done__",
            "verdict": verdict_str,
            "thought": f"harness completed: {verdict_str}",
        }


def build_llm_solver(config: LLMConfig, harness=None, input=None) -> LLMSolverProtocol:
    """Factory: create LLM solver from config.

    Production LLM path = external harness (Goose / Claude Code) via
    HarnessRunner. This is NOT an in-process API call — the harness runs as a
    subprocess and connects to our MCP server as its tool provider.

    Args:
        config: LLMConfig (provider/model documented for the S3* cross-provider
            constraint, VSM-001).
        harness: HarnessRunner instance (required for production).
        input: S1Input template (required for HarnessSolverAdapter).
    """
    error = config.validate()
    if error:
        raise ValueError(f"invalid LLM config: {error}")
    if harness is None:
        raise ValueError(
            "LLM solver requires a HarnessRunner instance. "
            "Production LLM path = external harness (Goose / Claude Code), "
            "not in-process API calls. Pass harness=HarnessRunner(...)."
        )
    return HarnessSolverAdapter(harness=harness, input=input)
