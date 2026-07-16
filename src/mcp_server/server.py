"""server — MCP server over stdio (JSON-RPC 2.0).

Minimal MCP protocol implementation. Registers tools, handles tool calls,
logs each call to trace (observability for S3-classifier).

MCP access restriction (VSM-005): tool surface structuraly does NOT include
eval-access. There is no tool for eval-data, eval-labels, or parent access.
The absence of the tool IS the membrane — not a filter.
"""
from __future__ import annotations
import json
import signal
import sys
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolCall:
    """Logged tool call — trace entry (T2 CONTRACT §3 format)."""

    idx: int
    tool: str
    args: dict[str, Any]
    observation: str
    exit_code: int = 0
    error: str | None = None
    cost_seconds: float = 0.0


@dataclass
class MCPServer:
    """MCP server: registers tools, handles JSON-RPC calls, logs trace."""

    tools: dict[str, dict] = field(default_factory=dict)
    handlers: dict[str, Callable] = field(default_factory=dict)
    trace: list[ToolCall] = field(default_factory=list)
    _call_counter: int = 0

    def register(self, name: str, description: str, input_schema: dict, handler: Callable):
        self.tools[name] = {"name": name, "description": description, "inputSchema": input_schema}
        self.handlers[name] = handler

    def call_tool(self, name: str, args: dict[str, Any]) -> dict:
        self._call_counter += 1
        idx = self._call_counter
        handler = self.handlers.get(name)
        if handler is None:
            tc = ToolCall(idx=idx, tool=name, args=args, observation="", error=f"unknown tool: {name}")
            self.trace.append(tc)
            return {"error": tc.error}
        try:
            result = handler(**args)
            obs = result.get("stdout", "") + result.get("stderr", "")
            exit_code = result.get("exit_code", 0)
            tc = ToolCall(
                idx=idx, tool=name, args=args,
                observation=obs, exit_code=exit_code,
                cost_seconds=result.get("time_seconds", 0.0),
            )
            self.trace.append(tc)
            return result
        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {exc}"
            tc = ToolCall(idx=idx, tool=name, args=args, observation=err_msg,
                          exit_code=1, error=err_msg)
            self.trace.append(tc)
            # VSM-034 TERTIARY-1: surface exceptions as stderr+exit_code=1 so the
            # agent loop records a failure_observation (was: silent {"error":...}
            # with no exit_code → invisible failure, file not created but step
            # treated as success).
            return {"stdout": "", "stderr": err_msg, "exit_code": 1,
                    "time_seconds": 0.0}

    def list_tools(self) -> list[dict]:
        return list(self.tools.values())

    def get_trace(self) -> list[dict]:
        """Returns trace as list of dicts (T2 CONTRACT §3 trace format)."""
        return [
            {
                "idx": tc.idx,
                "action": {"tool": tc.tool, "args": tc.args},
                "observation": tc.observation,
                "exit_code": tc.exit_code,
                "error": tc.error,
                "cost": {"tokens": 0, "time_seconds": tc.cost_seconds},
            }
            for tc in self.trace
        ]

    def get_failure_observations(self) -> list[dict]:
        """Extract failure observations from trace (T2 CONTRACT §6 format)."""
        observations = []
        for tc in self.trace:
            if tc.exit_code != 0 and tc.observation:
                observations.append({
                    "kind": "error_string",
                    "value": tc.observation[:500],
                    "source": "stderr",
                    "at_action": tc.idx,
                })
                observations.append({
                    "kind": "exit_code",
                    "value": tc.exit_code,
                    "command": tc.tool,
                    "at_action": tc.idx,
                })
            if tc.error:
                observations.append({
                    "kind": "error_string",
                    "value": tc.error,
                    "source": "internal",
                    "at_action": tc.idx,
                })
        return observations

    def handle_request(self, request: dict) -> dict | None:
        """Handle a single JSON-RPC request. Returns response or None (for notifications)."""
        method = request.get("method")
        req_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            return {"jsonrpc": "2.0", "id": req_id, "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "coding-harness-tools", "version": "0.1.0"},
            }}
        elif method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.list_tools()}}
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {})
            result = self.call_tool(name, args)
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}}
        elif method == "notifications/initialized":
            return None
        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"method not found: {method}"}}


def create_server(workspace: str = ".") -> MCPServer:
    """Create and register all tools."""
    from .tools.filesystem import register_filesystem_tools
    from .tools.shell import register_shell_tools
    from .tools.git import register_git_tools
    from .tools.browser import register_browser_tools

    server = MCPServer()
    register_filesystem_tools(server, workspace)
    register_shell_tools(server, workspace)
    register_git_tools(server, workspace)
    register_browser_tools(server)
    return server


def serve_stdio(workspace: str = ".", trace_file: str | None = None):
    """Run MCP server over stdio (JSON-RPC 2.0 line-delimited).

    If trace_file is set, writes the full trace (T2 CONTRACT §3 format) to that
    file on exit — for external collection by HarnessRunner or other orchestrator.
    """
    server = create_server(workspace)

    def _write_trace():
        if trace_file:
            try:
                from pathlib import Path
                trace_data = {
                    "trace": server.get_trace(),
                    "failure_observations": server.get_failure_observations(),
                }
                Path(trace_file).write_text(
                    json.dumps(trace_data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            except Exception:
                traceback.print_exc(file=sys.stderr)

    # Register signal handler so trace is written when harness sends SIGTERM.
    # Without this, the `finally` block is skipped on signal-based termination
    # and trace_file is never written.
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
                err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
                sys.stdout.write(json.dumps(err) + "\n")
                sys.stdout.flush()
            except Exception:
                traceback.print_exc(file=sys.stderr)
    finally:
        _write_trace()


def _main():
    """CLI entry point: python3 -m mcp_server.server [options]."""
    import argparse
    parser = argparse.ArgumentParser(description="MCP tools-server for coding harness")
    parser.add_argument("--workspace", default=".", help="workspace root path")
    parser.add_argument("--trace-file", default=None, help="write trace to this file on exit")
    args = parser.parse_args()
    serve_stdio(workspace=args.workspace, trace_file=args.trace_file)


if __name__ == "__main__":
    _main()
