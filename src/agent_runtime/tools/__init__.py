"""tools — per-role MCP tool handlers for agent runtime (VSM-013).

Submodules register tool handlers onto an MCPServer for each role:
  coord.py:           S2 coordination (state_bus read/write, conflict, retry authorize)
  classifier_tools.py: S3 classification (taxonomy, signal match, policy select)
  audit_tools.py:     S3* audit (read-only state, audit check)

Each register_* function takes (server, *args) and calls server.register(),
following the pattern in mcp_server/tools/{filesystem,shell,git}.py.
"""
