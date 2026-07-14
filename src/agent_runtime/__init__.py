"""agent_runtime — foundation for full agentization S1–S5 (VSM-012/013).

Inter-process agent runtime: each system (S1 solver, S2 coordinator, S3
optimizer, S3* auditor, S4 scout, S5 guardian) becomes a goose-agent running
as a subprocess, coordinated via a file-based shared state-bus.

Three components (VSM-013):
  - state_bus.py: inter-process shared state (file-based, atomic writes).
    Generalizes session_sync.SessionStore (in-process) to multi-process.
  - goose_runner.py: generic agent launcher. Builds SOUL/SKILL/TASK prompt,
    attaches per-role MCP tool surface, runs goose as subprocess, parses result.
  - protocol.py: coordination API. Each recovery-cycle step = state-bus write
    → goose-runner → state-bus read. Replaces direct Python calls in
    orchestrator.py.

Membrane (VSM-002): agent_runtime is part of the product, benchmark-agnostic.
No mentions of terminal-bench/benchmark/eval/harbor.

Stateless (CONTRACT §5): each agent invocation is a fresh subprocess. The only
state between attempts is the state-bus (per-task) + recovery_directive.
"""
from .state_bus import StateBus, TaskState

__all__ = ["StateBus", "TaskState"]
