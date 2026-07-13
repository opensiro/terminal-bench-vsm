# `src/mcp_server/` — MCP tools-server для S1-солвера (T4)

> MCP-сервер как tools-server для S1-солвера. Benchmark-agnostic по построению.
> S1 вызывает tools через MCP (transport: stdio/http). Tool calls логируются в
> trace (для S3-classifier). **VSM-005 MCP access restriction**: tool surface
> структурно не включает eval-access — отсутствие инструмента, не фильтр.

## Tools surface

Стандартный набор для coding-агента. Каждый tool имеет input/output contract.

### filesystem (read/write/edit)
- `fs.read(path) → content` — чтение файла.
- `fs.write(path, content) → ok` — запись файла.
- `fs.edit(path, old_string, new_string) → ok` — точечная замена.
- `fs.list(path) → entries[]` — список директории.
- `fs.glob(pattern) → paths[]` — поиск файлов по паттерну.
- `fs.grep(pattern, path) → matches[]` — поиск по содержимому.

### shell (exec)
- `shell.exec(command, cwd, timeout) → {stdout, stderr, exit_code}` — выполнение
  команды. Timeout обязателен (prevents HangDetected).

### git (clone/commit/diff)
- `git.clone(url, dest) → ok` — клонирование репозитория.
- `git.commit(message, paths) → sha` — коммит.
- `git.diff(ref_a, ref_b) → diff` — diff между refs.
- `git.status() → status` — статус рабочего дерева.
- `git.checkout(ref) → ok` — переключение ref.

### browser (опц., для web-задач)
- `browser.fetch(url) → content` — HTTP GET (без JS rendering).
- `browser.search(query) → results[]` — веб-поиск (для S4-like reconnaissance
  внутри S1, если задача требует).

## MCP access restriction (VSM-005, structural)

**Tool surface НЕ включает eval-access.** Это design-time структурное ограничение:
- Нет tool для доступа к eval-данным.
- Нет tool для доступа к eval-разметке/expected outputs.
- Нет tool для запроса "правильного ответа".
- Нет tool для доступа к родительскому vsmlite-tb/ (parent isolation).

S1 не может обратиться к eval-данным, потому что такого tool нет в MCP-сервере.
Продукт не знает о restriction — для него tool surface просто "таков".
Мембрана = отсутствие инструмента, не фильтр.

## Integration

- **Transport**: stdio (по умолчанию) | http (для remote).
- **Config**: `.claude/mcp.json` (или эквивалент) — S1 загружает config при launch.
- **Server**: python (fastmcp/anthropic-mcp) или node — runtime-фаза реализует.

### Config example (`.claude/mcp.json`-style)

```json
{
  "mcpServers": {
    "coding-harness-tools": {
      "transport": "stdio",
      "command": "python3",
      "args": ["-m", "src.mcp_server.server"],
      "env": {
        "WORKSPACE_ROOT": "${workspace}"
      }
    }
  }
}
```

_Сейчас — декларация. Реализация (server module) — на runtime-фазе._

## Observability

Каждый tool call логируется в trace (совместим с T2 failure_observations):

```
trace_entry = {
  idx: <int>,
  action: { tool: "shell.exec", args: {command: "pytest", timeout: 30} },
  observation: "stdout: ... stderr: ... exit_code: 1",
  ts: <iso8601>,
  cost: { tokens: 0, time_seconds: 2.3 }
}
```

Tool calls → observations (S3-classifier парсит):
- `error_string`: stderr content → match по taxonomy signals.
- `exit_code`: nonzero exit → auxiliary signal.
- `timeout`: tool call превысил timeout → TimeoutExpired/HangDetected.
- `signal`: процесс убит → ResourceLimit.

## Hard constraints (NEVER)

- **`optimize_for_specific_evaluator`** — tool surface general-purpose, не
  включает eval-specific tools.
- **MCP access restriction (VSM-005)** — структурное отсутствие eval-access.
- Tool calls логируются (observability для S3/S3\*).
