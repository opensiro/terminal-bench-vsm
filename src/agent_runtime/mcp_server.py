"""mcp_server — per-role MCP tool surface for agent runtime (VSM-013).

A dedicated MCP server that registers a configurable tool surface per VSM system
role. Launched by goose_runner via --with-extension wrapper. Writes trace on exit.

Unlike mcp_server/server.py (S1-only, fixed coding tools), this server's tool
surface is selected at launch via --tools flag: a comma-separated list from the
per-role registry below.

Tool registry (per role):
  coding: fs, shell, git            (reuses mcp_server/tools/ handlers)
  coord:  state_bus_read, state_bus_write, conflict_check, retry_authorize
  class3: taxonomy_read, signal_match, policy_select
  audit:  state_bus_read, audit_check      (read-only; S3* = cross-provider)
  scout:  pattern_store, browser_search

Membrane (VSM-002): no eval/benchmark/terminal-bench references. Coordination
tools operate on the generic state-bus + taxonomy, benchmark-agnostic.
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

# Reuse the MCP protocol implementation from the S1 server (DRY).
from mcp_server.server import MCPServer


def create_server(
    workspace: str, trace_file: str | None, tools: list[str],
    state_bus_root: str | None = None,
) -> MCPServer:
    """Create an MCP server with the requested tool surface.

    Args:
        workspace: workspace root (for coding tools).
        trace_file: where to write the trace on exit.
        tools: list of tool module names to register (per-role surface).
        state_bus_root: state-bus root dir (for coord tools; default temp).
    """
    server = MCPServer()

    tool_set = set(tools)

    # ── Coding tools (S1) — reuse existing handlers ──
    if tool_set & {"fs", "shell", "git", "browser"}:
        from mcp_server.server import create_server as _create_s1
        # Register coding tools onto our server by delegating to the S1 registrar
        if "fs" in tool_set:
            from mcp_server.tools.filesystem import register_filesystem_tools
            register_filesystem_tools(server, workspace)
        if "shell" in tool_set:
            from mcp_server.tools.shell import register_shell_tools
            register_shell_tools(server, workspace)
        if "git" in tool_set:
            from mcp_server.tools.git import register_git_tools
            register_git_tools(server, workspace)
        if "browser" in tool_set:
            from mcp_server.tools.browser import register_browser_tools
            register_browser_tools(server)

    # ── Coordination tools (S2) ──
    if tool_set & {"state_bus_read", "state_bus_write", "conflict_check", "retry_authorize"}:
        from .tools.coord import register_coord_tools
        register_coord_tools(server, state_bus_root)

    # ── Classification tools (S3) ──
    if tool_set & {"taxonomy_read", "signal_match", "policy_select"}:
        from .tools.classifier_tools import register_classifier_tools
        register_classifier_tools(server, workspace)

    # ── Audit tools (S3*) ──
    if "audit_check" in tool_set:
        from .tools.audit_tools import register_audit_tools
        register_audit_tools(server, state_bus_root)

    # ── Scout tools (S4) ──
    if tool_set & {"intel_write", "intel_read"}:
        from .tools.scout_tools import register_scout_tools
        register_scout_tools(server, workspace)
    # S4 also gets taxonomy_read (coverage gap check) — reuse classifier tools
    if "taxonomy_read" in tool_set and not (tool_set & {"signal_match", "policy_select"}):
        from .tools.classifier_tools import register_classifier_tools
        register_classifier_tools(server, workspace)

    # ── Guardian tools (S5) ──
    if tool_set & {"identity_read", "osm_apply", "issue_resolve", "algedonic_log"}:
        from .tools.guardian_tools import register_guardian_tools
        register_guardian_tools(server, workspace)

    return server


def serve_stdio(
    workspace: str, trace_file: str | None, tools: list[str],
    state_bus_root: str | None = None,
) -> None:
    """Run MCP server over stdio (JSON-RPC line-delimited). Writes trace on exit."""
    server = create_server(workspace, trace_file, tools, state_bus_root)

    def _write_trace():
        if not trace_file:
            return
        try:
            data = {
                "trace": server.get_trace(),
                "failure_observations": server.get_failure_observations(),
            }
            Path(trace_file).write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except Exception:
            traceback.print_exc(file=sys.stderr)

    def _signal_handler(signum, frame):
        _write_trace()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = server.handle_request(request)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError:
                err = {"jsonrpc": "2.0", "id": None,
                       "error": {"code": -32700, "message": "parse error"}}
                sys.stdout.write(json.dumps(err) + "\n")
                sys.stdout.flush()
            except Exception:
                traceback.print_exc(file=sys.stderr)
    finally:
        _write_trace()


def _main():
    parser = argparse.ArgumentParser(description="Agent-runtime MCP server")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--trace-file", default=None)
    parser.add_argument("--tools", default="", help="comma-separated tool names")
    parser.add_argument("--state-bus-root", default=None)
    args = parser.parse_args()

    tools = [t.strip() for t in args.tools.split(",") if t.strip()]
    serve_stdio(args.workspace, args.trace_file, tools, args.state_bus_root)


if __name__ == "__main__":
    _main()
