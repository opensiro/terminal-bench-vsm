# S1 — dispatcher (child) · SKILL

## Tool scope

- **Читаешь**:
  - `vsm.yaml → system_1` (purpose, owner_agent).
  - [`../../../src/failure_taxonomy.yaml`](../../../src/failure_taxonomy.yaml) — для формата
    `failure_observations` (какие `signals` S3 будет матчить; ты не классифицируешь,
    но отдаёшь observations в том формате, который taxonomy описывает).
  - `state/{status,heartbeat}.json` (для фиксации своего состояния).
  - `state/maturation.json` (узнать Phase — активны ли S2/S3 для retry-цикла).
- **Пишешь**:
  - `state/status.json → systems[S1]` (summary + current_task).
  - `state/heartbeat.json → S1.last_run`.
  - trace run-артефакты (location — future runtime; сейчас — `state/runs/` или
    внешний artifact store, решается на runtime-фазе).
- **НЕ мутируешь**: `../../vsmlite-tb/` (родитель), `../src/` вне task-scoped
  workspace (run изоляция).

## Канонические источники

- [`CONTRACT.md`](CONTRACT.md) — interface (input/output/lifecycle/retry semantics).
  Это **главный** источник: любой вопрос «что S1 принимает/возвращает» → туда.
- `vsm.yaml → system_1` — operational unit registry (`solver`, `../src`).
- `../src/failure_taxonomy.yaml` — failure classes + `signals` (что S3 матчит).

## Протокол (один invocation)

1. **Прочитать** input (см. [CONTRACT.md §2](CONTRACT.md)).
2. **Проверить contract**:
   - `task.prompt` непустой.
   - `budget` валиден (все три поля > 0).
   - Если `recovery_directive ≠ null` — Phase ≥ 3 (иначе retry-цикла нет, запуск
     как first attempt). `recovery_directive` сообщает: какой класс сбоя ожидается,
     какая policy применена, что изменилось в env, номер попытки policy.
3. **Snapshot** filesystem/git в workspace (для artifacts diff на выходе).
4. **Запустить solver** в task-scoped окружении, под budget, с tool surface из
   `tools` (MCP — T4). Трассировать каждый tool call.
5. **Остановить** при: verdict от solver'a ИЛИ исчерпании budget (time/tokens/actions).
6. **Собрать output**: trace + verdict (`task_resolved` | `task_failed` |
   `budget_exhausted` | `unknown`) + artifacts diff + `failure_observations`
   (всегда полный — [CONTRACT.md §6](CONTRACT.md)) + cost.
7. **Вернуть** output. Retry (если уместен и S3 активен) формирует следующий input
   — не ты; ты только отдаёшь observations, S3/S2 работают дальше.

## Stateless (см. CONTRACT.md §5)

Между invocation'ами не хранишь состояние. Каждый запуск — fresh start. Прошлый
trace/artifacts не доносятся; единственный сигнал «это retry» — `recovery_directive`
в input.

## Канонические инструменты (future runtime)

- Tool surface — MCP-сервер (T4, `tools.config_ref` в input).
- Budget enforcement — runtime timer/counter (детали на runtime-фазе).
- Trace collection — встроен в tool-call layer (observability — T4).
