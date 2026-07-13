"""harness — HarnessRunner: orchestrate external coding harness (Claude Code / Goose).

Instead of raw LLM API calls, delegates the solver loop to an external harness
that connects to our MCP server as its tool provider. The harness is the "brain";
our MCP server is the "hands" (restricted tool surface, VSM-005 membrane).

Architecture:
  HarnessRunner.invoke(S1Input)
    1. Create task-scoped workspace
    2. Write MCP config (pointing to our server with --trace-file)
    3. Launch MCP server as subprocess (stdio transport)
    4. Launch harness (claude-code / goose / custom) with MCP config + task prompt
    5. Wait for harness completion (timeout = budget.time_seconds)
    6. Collect trace from trace-file (written by MCP server on exit)
    7. Extract failure_observations from trace
    8. Compute artifacts diff (filesystem snapshot before/after)
    9. Return S1Output

Stateless (CONTRACT §5): each invoke is independent.
Budget enforcement: harness killed if exceeds budget.time_seconds.
General-purpose: НИКАКИХ упоминаний terminal bench/benchmark/eval/harbor.
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

from .types import S1Input, S1Output, TraceEntry, FailureObservation, Verdict, Artifact
from .budget import BudgetTracker
from .artifacts import snapshot, diff


@dataclass
class HarnessConfig:
    """Configuration for external harness integration.

    The harness is the "brain" — it decides actions, calls MCP tools.
    Our MCP server is the "hands" — restricted tool surface (VSM-005).
    """

    harness_type: str = "claude-code"  # "claude-code" | "goose" | "custom"
    binary: str = ""                   # path to harness binary (auto-detect if empty)
    extra_args: list[str] = field(default_factory=list)
    mcp_server_module: str = "mcp_server.server"  # our MCP server python module
    python_bin: str = sys.executable   # python to run MCP server
    env: dict[str, str] = field(default_factory=dict)  # extra env vars for harness
    max_turns: int = 20                # maps to goose --max-turns (budget.actions-derived)

    def resolve_binary(self) -> str:
        """Resolve harness binary path (auto-detect if not set)."""
        if self.binary:
            return self.binary
        if self.harness_type == "claude-code":
            return "claude"  # Claude Code CLI
        elif self.harness_type == "goose":
            return "goose"  # Goose CLI
        else:
            return self.harness_type  # custom: use type name as binary

    def build_harness_args(
        self,
        task_prompt: str,
        workspace: str,
        trace_file: str,
        mcp_config_path: str | None = None,
        mcp_wrapper_path: str | None = None,
    ) -> list[str]:
        """Build command-line args for the harness.

        Override in subclasses or extend extra_args for custom harnesses.

        Args:
            task_prompt: the task text passed to the harness.
            workspace: absolute path to the task-scoped workspace.
            trace_file: absolute path to the MCP server trace output.
            mcp_config_path: path to mcp_config.json (used by claude-code).
            mcp_wrapper_path: path to a bash wrapper script (used by goose via
                --with-extension, since Goose parses --with-extension by whitespace
                and cannot handle paths containing spaces).
        """
        binary = self.resolve_binary()
        if self.harness_type == "claude-code":
            # Claude Code: --mcp-config + --print (non-interactive) + prompt
            return [
                binary,
                "--mcp-config", mcp_config_path or "",
                "--print",
                "--dangerously-skip-permissions",  # no prompts in automated mode
                *self.extra_args,
                task_prompt,
            ]
        elif self.harness_type == "goose":
            # Goose CLI: stateless run, no profile (restricted tool surface only,
            # VSM-005 membrane), MCP attached via --with-extension wrapper script.
            # --no-session keeps each invoke independent (CONTRACT §5).
            args = [
                binary, "run",
                "--text", task_prompt,
                "--no-session",
                "--no-profile",
                "--max-turns", str(self.max_turns),
                "--output-format", "text",
            ]
            if mcp_wrapper_path:
                args.extend(["--with-extension", mcp_wrapper_path])
            args.extend(self.extra_args)
            return args
        else:
            # Custom: binary + extra_args + prompt
            return [binary, *self.extra_args, task_prompt]

    def build_mcp_wrapper(
        self,
        tmpdir: str,
        workspace: str,
        trace_file: str,
    ) -> str:
        """Generate a bash wrapper script that launches our MCP server.

        Goose's --with-extension parses `ENV=val cmd args` by whitespace, so it
        cannot represent a workspace/src path that contains spaces (e.g. our
        repo under "Opensiro Collections/"). We work around this by writing a
        bash wrapper with PYTHONPATH and the server command baked in directly,
        then passing only the wrapper's own path (single token) to
        --with-extension.

        PYTHONPATH is derived from this module's location (src/ directory), so
        `python3 -m mcp_server.server` resolves regardless of the caller's cwd.

        Args:
            tmpdir: temp directory to host the wrapper script.
            workspace: absolute path to the task-scoped workspace.
            trace_file: absolute path the MCP server writes its trace to.

        Returns:
            Absolute path to the generated (and chmod 0o755) wrapper script.
        """
        # src/ is the parent of the runtime/ package this module lives in.
        src_dir = str(Path(__file__).resolve().parent.parent)
        wrapper_path = Path(tmpdir) / "mcp_server_wrapper.sh"

        # Quote paths to be safe against spaces (the wrapper itself is invoked
        # as a single token by goose, but its contents must handle spaces).
        wrapper_lines = [
            "#!/usr/bin/env bash",
            f'export PYTHONPATH="{src_dir}"',
            f'export WORKSPACE_ROOT="{workspace}"',
            f'exec {self.python_bin} -m {self.mcp_server_module} '
            f'--workspace "{workspace}" --trace-file "{trace_file}" "$@"',
            "",
        ]
        wrapper_path.write_text("\n".join(wrapper_lines), encoding="utf-8")
        wrapper_path.chmod(0o755)
        return str(wrapper_path)

    def build_mcp_config(self, workspace: str, trace_file: str) -> dict:
        """Build MCP server config (mcp.json-style) for the harness."""
        return {
            "mcpServers": {
                "coding-harness-tools": {
                    "transport": "stdio",
                    "command": self.python_bin,
                    "args": [
                        "-m", self.mcp_server_module,
                        "--workspace", workspace,
                        "--trace-file", trace_file,
                    ],
                    "env": {
                        "WORKSPACE_ROOT": workspace,
                    },
                }
            },
        }


@dataclass
class HarnessRunner:
    """Runs an external harness (Claude Code / Goose) connected to our MCP server.

    The harness is the solver "brain"; our MCP server provides restricted tools.
    Trace is collected from the MCP server's --trace-file output.
    """

    config: HarnessConfig = field(default_factory=HarnessConfig)

    def invoke(self, input: S1Input) -> S1Output:
        """One invocation: launch MCP + harness → wait → collect trace → output.

        1. Snapshot filesystem.
        2. Write MCP config + trace file path.
        3. Launch harness (which spawns MCP server via config).
        4. Wait for completion (timeout = budget).
        5. Read trace from trace-file.
        6. Extract failure_observations.
        7. Compute artifacts diff.
        """
        workspace = str(input.workspace.resolve())
        fs_before = snapshot(input.workspace)

        budget = BudgetTracker(
            time_seconds=input.budget.time_seconds,
            tokens=input.budget.tokens,
            actions=input.budget.actions,
        )

        # Create temp files for MCP config + trace
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_config_path = Path(tmpdir) / "mcp_config.json"
            trace_file = Path(tmpdir) / "trace.json"

            # Goose attaches the MCP server via a wrapper script (workaround
            # for --with-extension whitespace parsing); claude-code/custom use
            # a JSON mcp_config. Build whichever is relevant for this harness.
            mcp_wrapper_path: str | None = None
            if self.config.harness_type == "goose":
                mcp_wrapper_path = self.config.build_mcp_wrapper(
                    tmpdir, workspace, str(trace_file)
                )
            else:
                # claude-code / custom: write JSON mcp_config as before.
                mcp_config = self.config.build_mcp_config(workspace, str(trace_file))
                mcp_config_path.write_text(
                    json.dumps(mcp_config, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

            # Build task prompt (include recovery directive if present)
            task_prompt = input.task_prompt
            if input.recovery_directive:
                directive_text = self._format_directive(input.recovery_directive)
                task_prompt = f"{task_prompt}\n\n--- Recovery context ---\n{directive_text}"

            # Launch harness
            harness_args = self.config.build_harness_args(
                task_prompt=task_prompt,
                workspace=workspace,
                trace_file=str(trace_file),
                mcp_config_path=str(mcp_config_path),
                mcp_wrapper_path=mcp_wrapper_path,
            )

            env = os.environ.copy()
            env.update(self.config.env)

            try:
                result = subprocess.run(
                    harness_args,
                    cwd=workspace,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=budget.time_seconds,
                )
                harness_exit = result.returncode
                harness_stdout = result.stdout
                harness_stderr = result.stderr
            except subprocess.TimeoutExpired:
                return self._make_output(
                    Verdict.BUDGET_EXHAUSTED, [], [], fs_before, input.workspace, budget
                )
            except FileNotFoundError:
                return self._make_output(
                    Verdict.UNKNOWN, [], [], fs_before, input.workspace, budget,
                    error=f"harness binary not found: {self.config.resolve_binary()}",
                )

            # Read trace from MCP server's trace-file
            trace_entries: list[TraceEntry] = []
            failure_obs: list[FailureObservation] = []

            if trace_file.exists():
                try:
                    trace_data = json.loads(trace_file.read_text(encoding="utf-8"))
                    trace_entries = self._parse_trace(trace_data.get("trace", []))
                    failure_obs = self._parse_observations(trace_data.get("failure_observations", []))
                except (json.JSONDecodeError, KeyError):
                    pass

            # If no trace (MCP server didn't write or harness didn't use MCP),
            # try to infer from harness stdout/stderr
            if not trace_entries:
                trace_entries, failure_obs = self._infer_from_harness_output(
                    harness_stdout, harness_stderr, harness_exit
                )

            # Determine verdict
            verdict = self._determine_verdict(harness_exit, failure_obs, trace_entries)

            return self._make_output(
                verdict, trace_entries, failure_obs,
                fs_before, input.workspace, budget,
            )

    def _format_directive(self, directive) -> str:
        """Format recovery directive for inclusion in task prompt."""
        lines = [
            f"This is a retry. Previous attempt failed with: {directive.failure_class}",
            f"Recovery policy applied: {directive.policy_applied}",
        ]
        if directive.env_changes:
            lines.append(f"Environment changes: {', '.join(directive.env_changes)}")
        lines.append(f"Policy attempt: {directive.policy_attempt}")
        return "\n".join(lines)

    def _parse_trace(self, raw_trace: list[dict]) -> list[TraceEntry]:
        """Parse trace dicts from MCP server into TraceEntry objects."""
        entries = []
        for raw in raw_trace:
            entries.append(TraceEntry(
                idx=raw.get("idx", 0),
                action=raw.get("action", {"tool": "unknown", "args": {}}),
                observation=raw.get("observation", ""),
                ts=raw.get("ts", ""),
                cost=raw.get("cost", {"tokens": 0, "time_seconds": 0.0}),
            ))
        return entries

    def _parse_observations(self, raw_obs: list[dict]) -> list[FailureObservation]:
        """Parse failure observation dicts into FailureObservation objects."""
        obs = []
        for raw in raw_obs:
            obs.append(FailureObservation(
                kind=raw.get("kind", "error_string"),
                value=raw.get("value", ""),
                source=raw.get("source", "stderr"),
                command=raw.get("command"),
                action=raw.get("action"),
                deadline_seconds=raw.get("deadline_seconds"),
                at_action=raw.get("at_action", 0),
            ))
        return obs

    def _infer_from_harness_output(
        self, stdout: str, stderr: str, exit_code: int
    ) -> tuple[list[TraceEntry], list[FailureObservation]]:
        """When MCP trace is unavailable, infer from harness stdout/stderr."""
        trace = []
        obs = []
        observation = (stdout or "") + (stderr or "")
        trace.append(TraceEntry(
            idx=1,
            action={"tool": "harness", "args": {}},
            observation=observation[:5000],
            ts=time.strftime("%Y-%m-%dT%H:%M:%S"),
            cost={"tokens": 0, "time_seconds": 0.0},
        ))
        if exit_code != 0:
            if stderr:
                obs.append(FailureObservation(
                    kind="error_string", value=stderr[:500],
                    source="stderr", at_action=1,
                ))
            obs.append(FailureObservation(
                kind="exit_code", value=exit_code,
                command="harness", at_action=1,
            ))
        return trace, obs

    def _determine_verdict(
        self,
        harness_exit: int,
        failure_obs: list[FailureObservation],
        trace: list[TraceEntry],
    ) -> Verdict:
        """Determine verdict from harness exit code + failure observations."""
        if harness_exit == 0 and not failure_obs:
            return Verdict.TASK_RESOLVED
        if failure_obs:
            return Verdict.TASK_FAILED
        if harness_exit != 0:
            return Verdict.TASK_FAILED
        return Verdict.UNKNOWN

    def _make_output(
        self,
        verdict: Verdict,
        trace: list[TraceEntry],
        failure_obs: list[FailureObservation],
        fs_before: dict,
        workspace: Path,
        budget: BudgetTracker,
        error: str | None = None,
    ) -> S1Output:
        """Construct S1Output with artifacts diff."""
        fs_after = snapshot(workspace)
        artifacts = diff(fs_before, fs_after, workspace)

        output = S1Output(
            trace=trace,
            verdict=verdict,
            artifacts=artifacts,
            failure_observations=failure_obs,
            cost=budget.summary(),
        )

        if error:
            output.failure_observations.append(FailureObservation(
                kind="error_string", value=error,
                source="internal", at_action=0,
            ))

        return output
