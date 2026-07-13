"""mcp_server — MCP tools-server для S1-солвера (T4 runtime).

Tools surface: filesystem, shell, git, browser. General-purpose.
MCP access restriction (VSM-005): structural — tool surface не включает eval-access.
"""
from .server import MCPServer, serve_stdio

__all__ = ["MCPServer", "serve_stdio"]
