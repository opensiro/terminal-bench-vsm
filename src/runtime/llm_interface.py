"""llm_interface — protocol for pluggable LLM solvers (future).

Defines the interface that a real LLM solver would implement.
The actual LLM integration (OpenAI, Anthropic, etc.) is future work;
this module defines the contract.

Stateless (CONTRACT §5): solvers do not persist state between invocations.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
from .types import TraceEntry


@runtime_checkable
class LLMSolverProtocol(Protocol):
    """Protocol for LLM-based solvers.

    A real implementation would:
    1. Construct a prompt from task_prompt + trace history + available tools.
    2. Call an LLM API (OpenAI, Anthropic, local model, ...).
    3. Parse the LLM response into a tool call decision.
    4. Return the decision (same format as SolverProtocol.decide_next_action).

    Cross-provider note (VSM-001): S3* must use a different provider than S1.
    S1's LLM provider is configured here; S3*'s is in audit/config.py.
    """

    provider: str  # "openai" | "anthropic" | "local" | ...

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
    """Configuration for LLM solver (future implementation).

    The actual API key and model are set at deployment, not hardcoded.
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
        if self.provider not in ("openai", "anthropic", "local", "custom"):
            return f"unknown provider: {self.provider}"
        return None


def build_llm_solver(config: LLMConfig) -> LLMSolverProtocol:
    """Factory: create LLM solver from config.

    Future: implement actual LLM integration.
    Currently raises NotImplementedError — use RuleBasedSolver for testing.
    """
    error = config.validate()
    if error:
        raise ValueError(f"invalid LLM config: {error}")
    raise NotImplementedError(
        "LLM solver not yet implemented. Use RuleBasedSolver from agent_loop.py for testing. "
        "Future: implement OpenAI/Anthropic/local model integration here."
    )
