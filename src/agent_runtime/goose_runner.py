"""goose_runner — generic agent launcher for any VSM system (VSM-013).

Generalizes HarnessRunner (src/runtime/harness.py, S1-only) + eval docker-exec
bridge (vsmlite-tb/eval/agent_phase.py) to ALL systems (S1–S5). Each system
becomes a goose-agent: build SOUL/SKILL/TASK prompt → attach per-role MCP tool
surface → run goose as subprocess → parse structured result → write trace.

Per-role tool registry (each role gets a different MCP tool surface):
  S1: fs/shell/git (coding) — reuses mcp_server/tools/
  S2: state_bus (read/write), conflict_check, retry_authorize
  S3: taxonomy_read, signal_match, policy_select
  S3*: state_bus (read-only), audit_check [OTHER provider — cross-provider flag]
  S4: browser (internet), pattern_store
  S5: policy_read, identity_check, algedonic_send

Cross-provider (VSM-001/S3*): S3* runs goose with a DIFFERENT provider config
(provider field in AgentConfig). The runner passes this as an env flag to goose.

The runner does NOT implement the tools themselves — it wires MCP tool surfaces.
Tool handlers live in mcp_server/tools/ (coding) + agent_runtime/tools/ (coord).
This module = orchestration: prompt assembly + subprocess + result parsing.

Stateless (CONTRACT §5): each run() is a fresh goose subprocess.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# src/ is the sys.path root; agent_runtime and mcp_server are siblings here.
_SRC_DIR = Path(__file__).resolve().parent.parent


@dataclass
class AgentConfig:
    """Configuration for one VSM system agent.

    Args:
        system_name: "s1-dispatcher" | "s2-coordinator" | "s3-optimizer" |
                     "s3-star-auditor" | "s4-scout" | "s5-guardian"
        systems_dir: path to vsm/systems/ (where SOUL/SKILL/TASK live)
        provider: LLM provider for goose (VSM-001: S3* must differ from S1).
        tools: list of MCP tool module names to attach (per-role surface).
        max_turns: goose --max-turns.
        binary: goose binary path (auto-detect if empty).
    """

    system_name: str
    systems_dir: Path
    provider: str = "zai"             # VSM-001: s3star must use a different one
    tools: list[str] = field(default_factory=list)
    max_turns: int = 20
    binary: str = ""
    # VSM-015: override the per-role output contract. Used when the same agent
    # role produces a DIFFERENT output shape depending on mode (e.g. S3* in
    # parallel mode classifies like S3, instead of auditing). Empty = use the
    # default contract for system_name from _output_contract().
    contract_override: str = ""

    def resolve_binary(self) -> str:
        return self.binary or "goose"


@dataclass
class AgentResult:
    """Result of one agent invocation."""

    system_name: str
    ok: bool = False
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    duration_sec: float = 0.0
    parsed: dict[str, Any] | None = None   # structured output (JSON from stdout)
    trace_path: Path | None = None         # where the agent trace was written
    timed_out: bool = False


# ── Prompt assembly ──

def build_prompt(config: AgentConfig, task_input: str) -> str:
    """Assemble SOUL + SKILL + TASK + task input into a single goose prompt.

    The agent's identity (SOUL), capabilities (SKILL), and concrete task (TASK)
    are concatenated, followed by the structured task input (from state-bus).
    """
    sys_dir = config.systems_dir / config.system_name
    parts: list[str] = []

    for doc in ("SOUL.md", "SKILL.md", "TASK.md"):
        path = sys_dir / doc
        if path.exists():
            parts.append(path.read_text(encoding="utf-8", errors="replace").strip())

    parts.append("── Task input (from state-bus) ──")
    parts.append(task_input)
    # VSM-015: contract_override takes precedence (e.g. S3* in parallel mode)
    parts.append(config.contract_override or _output_contract(config.system_name))
    return "\n\n".join(parts)


def _output_contract(system_name: str) -> str:
    """Per-role output contract: the exact JSON shape the orchestrator parses.

    LLM-agents are unstable in their output format. An explicit per-role schema
    (with required fields and a concrete example) dramatically improves the rate
    of parseable results. The orchestrator's _obs_from_agent tolerates extra
    fields, but missing required ones (e.g. failure_observations on task_failed)
    break the recovery cycle.
    """
    contracts = {
        "s1-dispatcher": (
            "── Output contract (S1) ──\n"
            "End your response with a JSON block enclosed in ```json ... ```:\n"
            "```\n"
            '{"verdict": "task_resolved" | "task_failed" | "budget_exhausted",\n'
            ' "failure_observations": [\n'
            '   {"kind": "error_string|exit_code|timeout|signal", "value": <str|int>,\n'
            '    "source": "stderr|stdout|internal", "at_action": <int>}\n'
            " ],\n"
            ' "cost": {"time_used": <int>, "tokens_used": <int>, "actions_taken": <int>}}\n'
            "```\n"
            "REQUIRED: if verdict is 'task_failed', failure_observations MUST be non-empty "
            "(the recovery cycle cannot proceed without observations to classify)."
        ),
        "s2-coordinator": (
            "── Output contract (S2) ──\n"
            "End your response with a JSON block enclosed in ```json ... ```:\n"
            "```\n"
            '{"authorized": <bool>, "blocked_by": <string|null>, "reason": <string>}\n'
            "```\n"
            "Use the retry_authorize tool to run the 4-check; return its result "
            "plus your reasoning in 'reason'."
        ),
        "s3-optimizer": (
            "── Output contract (S3) ──\n"
            "End your response with a JSON block enclosed in ```json ... ```:\n"
            "```\n"
            '{"failure_class": <string>, "recovery_policy": <string>,\n'
            ' "confidence": "high|medium|low", "ambiguous": <bool>,\n'
            ' "alternative_classes": [<string>], "reason": <string>}\n'
            "```\n"
            "Use the signal_match tool to ground your classification in taxonomy evidence."
        ),
        "s3-star-auditor": (
            "── Output contract (S3*) ──\n"
            "End your response with a JSON block enclosed in ```json ... ```:\n"
            "```\n"
            '{"passed": <bool>, "findings": [{"severity": <string>, "type": <string>,\n'
            '                                "message": <string>}],\n'
            ' "algedonic": <bool>}\n'
            "```\n"
            "Audit INDEPENDENTLY (you are on a different provider). Use the audit_check "
            "tool for deterministic facts, then apply your own judgment."
        ),
        "s4-scout": (
            "── Output contract (S4) ──\n"
            "End your response with a JSON block enclosed in ```json ... ```:\n"
            "```\n"
            '{"signals": [{"type": "pattern|gap|drift|weak_signal",\n'
            '              "severity": "info|warn|critical",\n'
            '              "summary": <string>, "detail": <string>,\n'
            '              "status": "triage|done"}],\n'
            ' "strategic_shifts": [{"type": "new_failure_class|policy_expansion",\n'
            '                       "summary": <string>, "requires_vsm_nnn": <bool>}],\n'
            ' "patterns_discovered": <int>}\n'
            "```\n"
            "Use browser.search for web discovery. Write signals to intel.json via "
            "intel_write. Strategic shifts (new failure class, policy expansion) "
            "require a VSM-NNN (basta — human decision)."
        ),
    }
    return contracts.get(
        system_name,
        # Generic fallback
        "── Output contract ──\n"
        "End your response with a JSON block enclosed in ```json ... ``` containing "
        "your structured result. The orchestrator parses this block.",
    )


# ── Result parsing ──

def parse_result(stdout: str) -> dict[str, Any] | None:
    """Extract the trailing ```json ... ``` block from goose stdout.

    Goose outputs free text; the agent is instructed (via prompt) to end with a
    fenced JSON block. We find the LAST such block and parse it. Returns None if
    no valid block is found.
    """
    import re
    # Match the last ```json ... ``` block (non-greedy within, greedy across blocks)
    blocks = re.findall(r"```json\s*\n(.*?)\n```", stdout, re.DOTALL)
    if not blocks:
        # Fallback: try bare ``` ... ``` blocks
        blocks = re.findall(r"```\s*\n(\{.*?\})\n```", stdout, re.DOTALL)
    if not blocks:
        return None
    try:
        return json.loads(blocks[-1].strip())
    except json.JSONDecodeError:
        return None


# ── MCP wrapper (goose --with-extension) ──

def build_mcp_wrapper(tools: list[str], workspace: str, trace_file: str, tmpdir: Path) -> str | None:
    """Generate a bash wrapper that launches an MCP server with the given tools.

    Goose's --with-extension parses `ENV=val cmd args` by whitespace, so we write
    a wrapper (single token) with the command baked in. This mirrors the workaround
    in runtime/harness.py and eval/agent_phase.py.

    The wrapper launches a dedicated MCP server (agent_runtime/mcp_server.py)
    that registers the per-role tool surface, bound to <workspace>, writing its
    trace to <trace_file>.

    Returns None if no tools requested (agent runs without MCP).
    """
    if not tools:
        return None
    wrapper_path = tmpdir / "mcp_wrapper.sh"
    tools_arg = ",".join(tools)
    lines = [
        "#!/usr/bin/env bash",
        f'export PYTHONPATH="{_SRC_DIR}"',
        f'export MCP_TOOLS="{tools_arg}"',
        f'export WORKSPACE_ROOT="{workspace}"',
        f'exec {sys.executable} -m agent_runtime.mcp_server '
        f'--workspace "{workspace}" --trace-file "{trace_file}" --tools "{tools_arg}" "$@"',
        "",
    ]
    wrapper_path.write_text("\n".join(lines), encoding="utf-8")
    wrapper_path.chmod(0o755)
    return str(wrapper_path)


# ── Runner ──

@dataclass
class GooseRunner:
    """Runs a VSM system as a goose-agent subprocess.

    The runner is generic over AgentConfig. It does not know what the system
    does — it only assembles the prompt, wires MCP, runs goose, parses output.
    """

    def run(
        self,
        config: AgentConfig,
        task_input: str,
        timeout_sec: int = 300,
    ) -> AgentResult:
        """Run one agent invocation.

        Args:
            config: AgentConfig for the system.
            task_input: structured task input (text — typically JSON from state-bus).
            timeout_sec: wall-clock cap (maps to goose --max-turns indirectly).
        """
        result = AgentResult(system_name=config.system_name)
        prompt = build_prompt(config, task_input)

        with tempfile.TemporaryDirectory(prefix=f"agent-{config.system_name}-") as tmpdir:
            tmpdir_path = Path(tmpdir)
            trace_file = tmpdir_path / "trace.json"
            workspace = str(config.systems_dir.parent)  # vsm/ — agents read state/ here

            mcp_wrapper = build_mcp_wrapper(
                config.tools, workspace, str(trace_file), tmpdir_path,
            )

            args = [
                config.resolve_binary(), "run",
                "--text", prompt,
                "--no-session",       # CONTRACT §5: stateless
                "--no-profile",       # restricted tool surface only
                "--max-turns", str(config.max_turns),
                "--output-format", "text",
            ]
            if mcp_wrapper:
                args.extend(["--with-extension", mcp_wrapper])

            env = os.environ.copy()
            # Provider hint for goose (VSM-001 cross-provider for S3*)
            env["AGENT_PROVIDER"] = config.provider

            start = time.time()
            try:
                proc = subprocess.run(
                    args, capture_output=True, text=True,
                    timeout=timeout_sec, env=env,
                )
                result.exit_code = proc.returncode
                result.stdout = proc.stdout or ""
                result.stderr = proc.stderr or ""
            except subprocess.TimeoutExpired as e:
                result.timed_out = True
                result.exit_code = 124
                result.stdout = (e.stdout or "") if isinstance(e.stdout, str) else ""
                result.stderr = ((e.stderr or "") if isinstance(e.stderr, str) else "") + \
                    f"\n[agent timed out after {timeout_sec}s]"
            except FileNotFoundError:
                result.exit_code = 127
                result.stderr = f"goose binary not found: {config.resolve_binary()}"
            result.duration_sec = time.time() - start

            # Parse structured output
            result.parsed = parse_result(result.stdout)
            result.ok = result.parsed is not None and result.exit_code == 0

            # Preserve trace path if written
            if trace_file.exists():
                result.trace_path = trace_file

        return result
