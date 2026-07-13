# `src/session_sync/` — session sync для мультиагентных прогонов (FUTURE)

> **Status: НЕ НУЖЕН (mono-agent).** Создан как placeholder для future.

## Решение (T5)

T2 CONTRACT определяет S1 как single solver per invocation (stateless,
fresh-per-invocation). Это **mono-agent** — session sync не нужен.

- Нет shared state между агентами в одном invocation — агент один.
- S2 координирует retry между invocations (не между агентами).
- State живёт в `recovery_directive` (input) + `trace` (output), не в shared store.

## Когда понадобится

Если S1 станет мультиагентным через OSM-примитив **Split** (planner + executor +
verifier), понадобится session sync — shared state между суб-агентами одной задачи:

- **Shared state format**: artifacts, exploration map, intermediate results.
- **Isolation**: per-task session, не протекает между задачами.
- **Consistency**: eventual / strong (зависит от архитектуры).

Это structural change (Split), требующий родительского решения (VSM-006:
identity/values change — единственное исключение автономии product S5).

## Contract (future, когда Split применится)

```
session = {
  task_id: <string>,
  agents: [<agent_id>],           # planner, executor, verifier
  shared_state: {
    artifacts: [<path>],
    exploration_map: {<path>: <status>},
    intermediate_results: {<key>: <value>}
  },
  created: <iso8601>,
  ttl: <seconds>                  # cleanup after task completion
}
```

_Пока — placeholder. Реализация — после Split (если применимо)._
