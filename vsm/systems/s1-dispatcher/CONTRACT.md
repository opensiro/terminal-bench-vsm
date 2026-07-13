# S1 — dispatcher (child) · CONTRACT

> **Phase 1+ (активен).** Этот файл — interface-контракт S1 продукта. Введён
> workstream'ом T2. Специфицирует, что S1-солвер принимает, что возвращает, как
> трассируется, как retry'ится. Это **контракт**, не реализация: конкретный
> runtime (python/docker/...) — будущие фазы, не здесь.

## 1. Purpose

`S1` продукта = **солвер long-horizon coding-задач**. `s1-dispatcher` —
**boundary-агент** этого VSM, запускающий солвер на одной задаче под бюджетом,
изолирующий его в task-scoped окружении и собирающий наблюдаемый trace.

Аналогично `child-dispatcher` родительского vsmlite (boundary родителя ↔ дочерний
VSM), `s1-dispatcher` — boundary дочернего VSM ↔ его S1-домен (`../src/`).

**Что делает s1-dispatcher**: launch → isolate → trace → collect output.
**Что НЕ делает**: не классифицирует failures (это S3), не выбирает recovery
policy (это S3), не координирует retry (это S2), не знает про оценочные наборы.

## 2. Input contract

```
{
  task: {                           # нейтральная coding-задача (framing уже снят мембраной родителя)
    prompt: <string>,               #   нейтральный prompt без упоминаний оценочных наборов
    spec: <string|null>             #   optional: более формальная спецификация/тесты
  },
  tools: {                          # tool surface через MCP (детализация — T4; здесь только ссылка)
    transport: "stdio"|"http",
    config_ref: <path>              #   напр. ".claude/mcp.json" (T4 определит формат)
  },
  environment: {                    # task-scoped workspace
    workspace: <path>,              #   изолированный каталог задачи
    shell: <string>,                #   напр. "bash"
    git: <bool>                     #   доступен ли git в workspace
  },
  budget: {                         # ceiling; S1 обязан остановиться при достижении
    time_seconds: <int>,
    tokens: <int>,
    actions: <int>                  #   max число tool calls
  },
  recovery_directive: <object|null>   # от S3 (когда активен); null для первого запуска
}
```

### `recovery_directive` (optional, от S3)

```
{
  failure_class: <id из failure_taxonomy.yaml>,   # какой класс ожидается
  policy_applied: <id policy>,                    # какая recovery policy применена к environment
  env_changes: [<string>],                        # что изменилось в env (напр. "installed: pytest")
  policy_attempt: <int>                           # номер попытки этой policy (anti-repeat)
}
```

`recovery_directive = null` на первом запуске. При retry (Phase 3+) S3 заполняет
его после классификации сбоя прошлой попытки и применения recovery policy к
environment. S1 читает его как индикатор: «это retry, env был изменён такой-то
policy, ожидается такой-то класс сбоя». S1 **не получает** trace/artifacts прошлой
попытки — см. §5.

## 3. Output contract

```
{
  trace: [                          # упорядоченная последовательность действий
    {
      idx: <int>,
      action: { tool: <string>, args: <object> },
      observation: <string>,        #   stdout/stderr/результат
      ts: <iso8601>,
      cost: { tokens: <int>, time_seconds: <float> }
    }
  ],
  verdict: "task_resolved"|"task_failed"|"budget_exhausted"|"unknown",
  artifacts: [                      # diff filesystem/git относительно snapshot на start
    { path: <string>, op: "created"|"modified"|"deleted" }
  ],
  failure_observations: [           # сигналы для S3-classifier (см. §6); всегда полный
    { kind: "error_string", value: <string>, source: "stdout"|"stderr", at_action: <int> },
    { kind: "exit_code",     value: <int>,    command: <string>,                  at_action: <int> },
    { kind: "timeout",       action: <string>, deadline_seconds: <int>,           at_action: <int> },
    { kind: "signal",        value: <string>,                                     at_action: <int> }
  ],
  cost: {                           # фактическое потребление
    time_used: <float>,
    tokens_used: <int>,
    actions_taken: <int>
  }
}
```

## 4. Lifecycle

```
harness (этот VSM)
  │
  │ формирует input (task, tools, environment, budget)
  │ recovery_directive = null на первом запуске
  ▼
s1-dispatcher.invoke(input)
  │
  │ 1. snapshot filesystem/git (для artifacts diff)
  │ 2. launch solver в task-scoped окружении
  │ 3. solver работает до verdict ИЛИ исчерпания budget
  │ 4. trace собирается по ходу (observability — см. T4 MCP)
  │ 5. на выходе: collect trace + artifacts diff + failure_observations
  ▼
output (verdict, trace, artifacts, failure_observations, cost)
  │
  │ если verdict ∈ {task_failed, budget_exhausted} и S3 активен (Phase 3+):
  │   → S3-classifier парсит failure_observations → failure_class
  │   → S3 выбирает recovery_policy (из failure_taxonomy.yaml)
  │   → recovery executor (T3) применяет policy к environment ВНЕ S1
  │   → S2 координирует retry (anti-repeat check, conflict check)
  │   → новый input: recovery_directive заполнен (что изменилось, какой класс)
  ▼
s1-dispatcher.invoke(input')   ← retry (см. §5)
```

**На ранних фазах** (Phase 1-2, S3/S2 не активны): retry не происходит — солвер
работает до verdict/budget, output фиксируется. Recovery-цикл активируется с
Phase 3 (когда S3 проявляется). До этого harness компенсирует недостающие функции
(OSM §7 Assisted Viability).

## 5. Retry semantics (stateful-vs-stateless — решено)

**Решение: S1 stateless — fresh-per-invocation.**

S1 стартует заново на каждом invocation (включая retry). S1 **не получает** trace,
artifacts или иную историю прошлой попытки. Единственный канал информации о retry
— `recovery_directive` в input (§2): он сообщает, какой класс сбоя ожидается и что
изменилось в environment.

**Две оси разделены** (state vs memory):

**State axis** (env, fs, git) — управляется recovery policy ВНЕ S1:
- InstallTool → установлен пакет в окружение.
- CreateFreshVenv → создано свежее venv.
- ResetAndReplay → git откатан к чистому состоянию задачи.
- RetryWithSmallerScope → декомпозирована задача.
Это делает recovery executor (T3), не S1. В этом смысле retry «stateful» на уровне
environment — но это не дело S1, и S1 об этом знает только через `env_changes` в
`recovery_directive`.

**Memory axis** (что S1 помнит о прошлой попытке) — **ничего**. S1 не хранит
состояние между invocation'ами. Прошлая попытка полностью забыта; S1 видит только
текущий input + `recovery_directive` (если есть).

**Обоснование выбора stateless**:
- *Аудируемость*: S3* видит input (включая directive) + output — явный audit trail,
  нет скрытого state в S1.
- *Простота*: нет checkpoint/restore логики в S1; весь state в input + env.
- *General-purpose discipline*: S1 не накапливает product-internal feedback,
  который мог бы привязать его к конкретному характеру задач. Каждый run — чистый.
- *Стоимость*: теряется прогресс прошлой попытки (S1 может повторить исследование).
  Это сознательный компромисс в пользу простоты и чистоты; если long-horizon
  эффективность станет узким местом — пересмотреть (но не режимами, а через
  recovery_directive, расширив его optional полями по мере необходимости).

## 6. Failure observations format (что S3 парсит)

Всегда полный в output. S3-classifier (T3) маппит эти наблюдения на failure class
по `signals` из [`../../../src/failure_taxonomy.yaml`](../../../src/failure_taxonomy.yaml).

```
failure_observations: [
  { kind: "error_string", value: "No module named 'pytest'", source: "stderr", at_action: 3 },
  { kind: "exit_code",     value: 1,                           command: "pytest tests/", at_action: 3 },
  { kind: "timeout",       action: "npm install",              deadline_seconds: 120,  at_action: 7 },
  { kind: "signal",        value: "SIGKILL",                                           at_action: 7 }
]
```

**Kinds**:
- `error_string`: точная строка ошибки из stdout/stderr. S3-classifier матчует
  по regex/substring из `signals` taxonomy.
- `exit_code`: ненулевой exit code команды.
- `timeout`: action превысил deadline.
- `signal`: процесс убит сигналом (OOM, SIGKILL, ...).

Если ни одно observation не матчится на класс taxonomy → S3 маркирует `Unknown`
→ эскалация (см. `failure_taxonomy.yaml → Unknown.recovery_steps`).

## 7. Non-goals (явно)

S1-солвер и `s1-dispatcher` **НЕ**:
- классифицируют failures (это S3, Phase 3+);
- выбирают recovery policy (это S3);
- применяют recovery policy к environment (это recovery executor, T3);
- координируют retry между попытками / агентами (это S2, Phase 2+);
- хранят состояние между invocation'ами (stateless — см. §5);
- знают о каком-либо оценочном наборе или о факте оценки (never_do:
  `optimize_for_specific_evaluator`; мембрана product↔evaluation — на стороне
  родителя);
- порождают новые recovery policies (это S4 через `new_failure_class_introduction`).

## 8. Dependencies

- **T1** (failure taxonomy): `signals` из taxonomy → формат `failure_observations`
  (S3-classifier маппит observations на classes). Sync 1 сверяет, что каждый
  signal-паттерн из этого CONTRACT маппится на класс T1.
- **T3** (retry-механизм): `recovery_directive` (input) и retry lifecycle (§4)
  реализуются retry director'ом T3; classifier парсит `failure_observations`.
- **T4** (MCP tools-server): `tools` (input) — tool surface, transport, config;
  observability: tool calls логируются в trace (§3).

## 9. Versioning

`CONTRACT.md` — semver-light. Любое изменение input/output schema или retry
semantics — пересмотр контракта, фиксируется в `VSM-NNN` (monotonic). Additive
изменения (новые optional поля, новые `kind` в failure_observations) — minor;
изменение семантики существующих полей — major (требует синхронизации с
T3/S3-classifier).
