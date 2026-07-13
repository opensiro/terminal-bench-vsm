# S1 — dispatcher (child) · MCP integration

> Как S1 использует MCP tools-server (T4). Tool surface — в
> [`../../../src/mcp_server/README.md`](../../../src/mcp_server/README.md).

## Integration

S1 получает tool surface через MCP (см. [CONTRACT.md §2 `tools`](CONTRACT.md)):

```
tools: {
  transport: "stdio"|"http",
  config_ref: <path>              # напр. ".claude/mcp.json"
}
```

`s1-dispatcher` при launch:
1. Читает `tools.config_ref` → MCP server config.
2. Запускает MCP server (stdio: subprocess; http: connect).
3. Предоставляет S1-солверу tools через standard MCP protocol.
4. Каждый tool call логируется в trace (observability).

## Tool surface (summary)

Standard coding-agent tools — без eval-access (VSM-005 MCP restriction):

- **filesystem**: read/write/edit/list/glob/grep
- **shell**: exec (с обязательным timeout)
- **git**: clone/commit/diff/status/checkout
- **browser** (опц.): fetch/search

Полный contract — в [`../../../src/mcp_server/README.md`](../../../src/mcp_server/README.md).

## MCP access restriction (VSM-005)

Tool surface структурно не включает eval-access. S1 не может обратиться к
eval-данным, потому что такого tool нет в MCP-сервере. Это не runtime-policy
(которую можно обойти), а design-time структурное ограничение.

**S1 не знает о restriction** — для него tool surface просто "таков". Мембрана =
отсутствие инструмента, не фильтр.

## Observability → failure_observations

Tool calls логируются в trace. S3-classifier (T3) парсит observations:
- `shell.exec` stderr → `error_string` (match по taxonomy signals).
- `shell.exec` exit_code → `exit_code` (auxiliary).
- tool call timeout → `timeout` (TimeoutExpired/HangDetected).
- process killed → `signal` (ResourceLimit/OOM).

Формат — в [CONTRACT.md §6](CONTRACT.md).

## Non-goals

- S1 НЕ выбирает какие tools доступны (tool surface фиксирован MCP-сервером).
- S1 НЕ может создать новый tool (нет tool для этого).
- MCP-сервер НЕ знает про оценочные наборы (general-purpose tool surface).
