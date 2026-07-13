# WORKSTREAM — план работ для следующих сессий

> Self-contained: новая сессия читает этот файл + [`vsmlite-tb/CLAUDE.md`](vsmlite-tb/CLAUDE.md)
> + [`vsmlite-tb/issues/VSM-002.yaml`](vsmlite-tb/issues/VSM-002.yaml) и может
> продолжать без контекста предыдущей беседы.

## Контекст (где мы сейчас)

**Продукт** = failure-aware coding harness для long-horizon агентов (дочерний VSM
в [`vsm/`](vsm/)). Полностью benchmark-agnostic — не знает, что его оценивают.
Phase 1 OSM (активен только S1), `meta.initialized: true`, A(t)=0.1 DEPENDENT.

**Родитель-оценщик** = [`vsmlite-tb/`](vsmlite-tb/). Знает про Terminal Bench 2.1,
оценивает продукт через калибровочный стенд. Мембрана product↔evaluation — на
стороне родителя (VSM-002).

**Архитектура**: VSM сам и есть harness. Солвер = S1; harness-функции
(классификация/восстановление) = S2/S3-слой продукта. `src/` — данные продукта:
[`failure_taxonomy.yaml`](src/failure_taxonomy.yaml) (skeleton: 5 классов),
кэш прогонов, Skill DB, session sync.

**Главный инвариант** (см. [`vsmlite-tb/CLAUDE.md`](vsmlite-tb/CLAUDE.md)):
мутации `vsm/` и `src/` — **только через `child-dispatcher`** (субагент
родителя, спавнится из `vsmlite-tb/`). Ядро vsmlite-tb и агенты продукта
физически не трогают `../vsm/` и `../src/` напрямую. Read-only наблюдение —
разрешено (`collect_metrics.py`). Проверяется `vsmlite-tb/scripts/validate.sh`.

**Hard constraints продукта** (NEVER, см. [`vsm/vsm.yaml`](vsm/vsm.yaml)):
`optimize_for_specific_evaluator`, `skip_failure_classification`,
`circumvent_recovery`. Нигде в продукте не упоминать Terminal Bench / benchmark /
eval / grading — проверяется grep.

## Стратегия: сначала фундамент

Не все 5 потоков параллелятся сразу. Сначала фундамент (taxonomy + S1-дизайн),
потому что retry/MCP/S2-пайплайны строятся поверх них — без фундамента это
блуждающие абстракции.

```
Волна 1 (параллельно, 2 сессии):
   T1: failure taxonomy   ──┐
                             ├── Sync 1 (сверка: failures из S1 ↔ классы taxonomy)
   T2: S1-агент дизайн    ──┘
                             │
Волна 2 (после Sync 1, параллельно, 2 сессии):
   T3: retry-механизм     ──┐  (зависит от T1+T2)
                             ├── Sync 2
   T4: MCP tools-server   ──┘  (зависит от T2)
                             │
Волна 3 (после Sync 2):
   T5: S2-пайплайны          (зависит от T1+T3)
```

## Workstreams

### T1 — Failure taxonomy (фундамент)
- **Status**: ✅ done (волна 1, завершено 2026-07-13)
- **Зависимости**: нет (стартует сразу)
- **Что было**: [`src/failure_taxonomy.yaml`](src/failure_taxonomy.yaml) — skeleton с 5 классами (ToolNotFound, DependencyConflict, GitConflict, TimeoutExpired, Unknown).
- **Задача**: наполнить реальными классами из опыта long-horizon coding-агентов. Не выдумывать — брать из literature/SWE-bench postmortems/observed traces. Каждый класс: id, description, signals (error strings/regex), recovery_policy, recovery_steps, s2_anti_repeat.
- **Кандидаты классов** (добавить сверх skeleton): ImportError/ModuleNotFound, SyntaxError, AssertionError/TestFailure, OOM/ResourceLimit, PermissionDenied, NetworkError, GitAuthFailure, CompilationError, HangDetected (timeout на action level vs task level), AmbiguousSpec (задача допускает несколько интерпретаций).
- **Deliverable**: `src/failure_taxonomy.yaml` v0.2, ≥12 классов, каждый с recovery policy. `Unknown` класс — escape hatch, помечен «если >N% за цикл → S3 расширяет taxonomy (basta: new_failure_class_introduction)».
- **Acceptance**:
  - [x] YAML валиден, парсится. — v0.2.0, 16 классов, `yaml.safe_load` OK
  - [x] Каждый класс имеет непустые `signals` (минимум 1) и `recovery_policy`. — все 16 (Unknown — escape hatch, signals пуст по design, recovery_policy: EscalateToS3)
  - [x] `policy_effectiveness_tracking` определён (порог ниже которого policy помечается flaky). — threshold: 0.6, window: per_cycle, below_threshold_action, flaky_policies[]
  - [x] НИ ОДНОГО упоминания Terminal Bench / benchmark / eval (проверка grep). — grep по vsm/+src/ чист
  - [x] Краткое обоснование: почему именно эти классы (2-3 предложения в комментарии или NOTES-блоке). — 5 notes: источники (SWE postmortems, MAST, traces), группировка по category, general-purpose инвариант
- **Доп. сверх acceptance**: `unknown_share_threshold: 0.15` (escape hatch порог), `classifier_guidance` (match_order + multi_match_resolution + evidence_required для S3-classifier — контракт для T3).
- **How-to-start**: спавни `child-dispatcher` из `vsmlite-tb/` с task `tailor: failure_taxonomy_v0.2`. Доступ: чтение literature (через WebSearch — разрешён, не через child-dispatcher), запись `../src/failure_taxonomy.yaml` — через child-dispatcher.
- **Результат**: 16 классов в 8 категориях (environment/dependency×3/code×3/git×2/resource×4/network/spec/fallback). Источники: SWE engineering postmortems (file localization, test failures), agent fault taxonomies (MAST — spec/verification), runtime faults (import/compilation/hang/OOM/permission/network). Главный инвариант соблюдён: обе мутации (запись v0.2 + правка опечатки) — через child-dispatcher. validate.sh GREEN.

### T2 — S1-агент дизайн (фундамент)
- **Status**: ✅ done (волна 1, сессия 2026-07-13)
- **Зависимости**: нет ( стартует сразу, параллельно T1)
- **Что есть**: [`vsm/vsm.yaml → system_1`](vsm/vsm.yaml) — `solver`, purpose зафиксирован на intent-level. Конкретизации interface НЕТ.
- **Задача**: дизайн S1-агента как interface. Что принимает, что возвращает, как трассируется. Не код — контракт.
- **Специфицируй**:
  - **Input contract**: coding task (neutral prompt — уже без TB-фрейминга, мембрана родителя), tools (через MCP, см. T4), environment (filesystem, shell), budget (time/tokens), recovery directives (от S3 — какой failure класс ожидается, какую policy применить).
  - **Output contract**: trace (последовательность actions + observations), verdict (task-resolved / task-failed / unknown), artifacts (изменения filesystem/git), failure observations (сигналы для S3-classifier — какие errors наблюдались).
  - **Lifecycle**: harness (этот VSM) запускает S1 на задаче → S1 работает до verdict/budget → в случае failure S3 классифицирует, S2 координирует retry с recovery directive → S1 запускается снова (stateful или fresh — специфицировать решение).
  - **Stateful vs stateless retry**: критичный дизайн-вопрос. Stateless = каждый retry с нуля (проще, но теряет прогресс). Stateful = retry с континуации (сложнее, но эффективнее). Решение зафиксировать с обоснованием.
- **Deliverable**: `vsm/systems/s1-dispatcher/` (НОВЫЙ каталог) с `SOUL.md` + `SKILL.md` + `CONTRACT.md` (interface). Возможно обновить `vsm/vsm.yaml → system_1` с ссылкой на contract.
- **Результат**: создан `vsm/systems/s1-dispatcher/` (5 файлов: CONTRACT/SOUL/SKILL/TASK/HEARTBEAT) + `vsmlite-tb/.claude/agents/s1-dispatcher.md`. CONTRACT.md — interface S1: input (task/tools/environment/budget/recovery_directive), output (trace/verdict/artifacts/failure_observations/cost), lifecycle, failure observations format (§6, что S3 парсит). Stateful-vs-stateless решён: **S1 stateless, fresh-per-invocation** (CONTRACT.md §5) — retry доносит только `recovery_directive` (какой класс ожидается, что изменилось в env). Обоснование: аудируемость, простота, general-purpose discipline.
- **Откат R0/R1/R2 (та же сессия)**: изначально T2 включал retry feedback-channel как спектр R0/R1/R2 (VSM-003, feedback_mode/prior_attempt в input). Человек передумал — «не усложнять». R0/R1/R2 вычищены из всех 5 файлов s1-dispatcher + agent file (через child-dispatcher для `../vsm/`; напрямую для `vsmlite-tb/`). VSM-003 → superseded (monotonic id сохранён в истории). Заменено простым stateless-решением. Гrep R0/R1/R2 по продукту (`vsm/`+`src/`) — чист. validate.sh GREEN.
- **Acceptance**:
  - [x] `vsm/systems/s1-dispatcher/CONTRACT.md` существует, описывает input/output/lifecycle.
  - [x] stateful-vs-stateless retry решение зафиксировано с обоснованием (CONTRACT.md §5: stateless, fresh-per-invocation).
  - [x] Failure observations формат определён (CONTRACT.md §6; что S3 будет парсить).
  - [x] `.claude/agents/s1-dispatcher.md` создан (placeholder agent definition, как у других систем).
  - [x] НИ ОДНОГО упоминания Terminal Bench / benchmark / eval.
- **How-to-start**: спавни `child-dispatcher` из `vsmlite-tb/` с task `tailor: s1_design`. Запись `../vsm/systems/s1-dispatcher/` — через child-dispatcher.

### Sync 1 — точка синхронизации (после T1 + T2)
- **Status**: ✅ ready (оба dependency done: T1 + T2)
- **Что**: сверка failure observations из T2 CONTRACT ↔ классы в T1 taxonomy.
- **Критерий pass**: каждый signal-паттерн в T2 CONTRACT маппится хотя бы на один класс в T1 taxonomy (или добавляется новый). Иначе — итерация: T1 дополняет классы, или T2 уточняет observation format.
- **Решает человек** (или сессия, выполняющая sync): есть ли расхождения, требующие доработки T1/T2.

### T3 — Retry-механизм (волна 2)
- **Status**: blocked on Sync 1
- **Зависимости**: T1 (taxonomy → recovery policies), T2 (S1 CONTRACT → retry interface)
- **Задача**: реализовать failure → classifier → recovery policy → retry pipeline.
- **Компоненты**:
  - **Failure classifier** (часть S3): парсит failure observations из S1 trace → определяет failure class (по signals из taxonomy) → выбирает recovery policy. Если ни один class не matches → `Unknown` → эскалация S3/human.
  - **Recovery policy executor**: применяет policy (InstallTool/CreateFreshVenv/ResetAndReplay/...) — меняет environment/state перед retry.
  - **Retry director**: формирует recovery directive для S1 (какой failure ожидается, какую policy применили, что changed).
  - **Anti-repeat (S2)**: трекает attempts, блокирует circumvent_recovery (повтор одной неудачи >N раз).
- **Deliverable**: `vsm/systems/s3-optimizer/CLASSIFIER.md` + `src/recovery_policies/` (НОВЫЙ каталог с per-policy реализацией или декларацией). Обновить `vsm/systems/s3-optimizer/SKILL.md` под classifier protocol.
- **Acceptance**:
  - classifier protocol описан end-to-end (trace → class → policy → retry).
  - каждая recovery policy из T1 taxonomy имеет executor (или явно помечена «stub, реализуется на Phase 3+»).
  - anti-repeat интегрирован (ссылка на S2).
  - bypass detection: если policy применяется но failure рецидивирует → эскалация.
  - НИ ОДНОГО упоминания Terminal Bench.
- **How-to-start**: после Sync 1, спавни `child-dispatcher` с task `implement: retry_mechanism`.

### T4 — MCP tools-server (волна 2)
- **Status**: blocked on Sync 1 (точнее на T2 CONTRACT)
- **Зависимости**: T2 (S1 CONTRACT → какие tools нужны)
- **Задача**: MCP-сервер как tools-server для S1-солвера. Benchmark-agnostic по построению.
- **Специфицируй**:
  - **Tools surface**: filesystem (read/write/edit), shell (exec), browser (если нужно для web-задач), git (clone/commit/diff). Стандартный набор для coding-агента.
  - **Boundary**: что tools НЕ делают (напр. не предоставляют доступ к сети для TB-leak — но это membrane, не MCP; MCP сам agnostic).
  - **MCP access restriction (VSM-005, structural)**: MCP tools-server продукта **структурно не предоставляет eval-access**. Tool surface просто не включает eval-доступ — это не runtime-policy (которую можно обойти), а design-time структурное ограничение. S1 не может обратиться к eval-данным, потому что такого tool нет в MCP-сервере. Мембрана = отсутствие инструмента, не фильтр. Продукт не знает о restriction.
  - **Integration**: как S1 вызывает MCP (transport: stdio/http; конфиг: `.claude/mcp.json` или эквивалент).
  - **Observability**: tool calls логируются в trace (для S3-classifier).
- **Deliverable**: `src/mcp_server/` (НОВЫЙ) с минимальной реализацией или декларацией server config + `vsm/systems/s1-dispatcher/MCP.md` (как S1 использует MCP).
- **Acceptance**:
  - tools surface определён (список tools с input/output).
  - **MCP access restriction (VSM-005)**: tool surface явно НЕ включает eval-access; структурное отсутствие, не фильтр.
  - MCP server config пример (`mcp.json`-style) включён.
  - observability: tool calls → trace format зафиксирован (совместим с T2 failure observations).
  - НИ ОДНОГО упоминания Terminal Bench.
- **How-to-start**: после Sync 1, спавни `child-dispatcher` с task `implement: mcp_tools_server`. Зависит преимущественно от T2, слабо от T1.

### Sync 2 — точка синхронизации (после T3 + T4)
- **Что**: end-to-end dry-run дизайн-проверки. S1 (T2) + MCP (T4) + retry (T3) + taxonomy (T1) → могут ли они вместе обработать один synthetic failure end-to-end (на бумаге).
- **Критерий pass**: trace сценария «солвер упал с ModuleNotFound → classifier → InstallTool → retry → успех» проходит через все компоненты без gaps.

### T5 — S2-пайплайны (волна 3)
- **Status**: blocked on Sync 2
- **Зависимости**: T1 (taxonomy → что конфликт), T3 (retry → что координировать)
- **Задача**: S2 coordination pipelines. Anti-oscillation, recovery coordination, multi-agent session sync.
- **Компоненты**:
  - **Recovery coordination**: когда S3 даёт retry directive, S2 гарантирует что retry не конфликтует с другими attempts (для multi-agent).
  - **Session sync** (в `src/`): shared state между агентами в одной сессии (если S1 мультиагентный — planner+executor+verifier).
  - **Conflict detection** (уже есть в `vsm/vsm.yaml → system_2.conflict_detection.custom_triggers`): реализовать триггеры.
  - **Anti-oscillation**: паттерн «солвер повторяет одну неудачу >N раз» → стоп, эскалация.
- **Deliverable**: `vsm/systems/s2-coordinator/PIPELINES.md` + `src/session_sync/` (если multi-agent). Обновить `vsm/systems/s2-coordinator/SKILL.md`.
- **Acceptance**:
  - recovery coordination protocol описан (как S2 arbiter-ит retry directives).
  - session sync contract определён (если multi-agent; если mono-agent — явно пометить «не нужен»).
  - conflict triggers из `vsm/vsm.yaml` реализованы или явно stub.
  - НИ ОДНОГО упоминания Terminal Bench.
- **How-to-start**: после Sync 2, спавни `child-dispatcher` с task `implement: s2_pipelines`.

## Как поднять в новой сессии

1. Открыть `terminal-bench-vsm/vsmlite-tb/` в Claude Code (dev-cwd).
2. Прочитать (в порядке):
   - этот файл (`../WORKSTREAM.md`)
   - [`vsmlite-tb/CLAUDE.md`](vsmlite-tb/CLAUDE.md) (S5-конституция + главный инвариант)
   - [`vsmlite-tb/issues/VSM-002.yaml`](vsmlite-tb/issues/VSM-002.yaml) (концептуальный поворот)
   - [`vsm/vsm.yaml`](vsm/vsm.yaml) (текущее состояние продукта)
   - [`src/failure_taxonomy.yaml`](src/failure_taxonomy.yaml) (skeleton)
3. Выбрать workstream по статусу (ready / blocked). Обновить status в этом файле.
4. Все мутации `vsm/` и `src/` — через `child-dispatcher` (спавнить из `vsmlite-tb/`). Ядро vsmlite-tb + новая сессия не трогают `../vsm/` и `../src/` напрямую.
5. После завершения workstream: обновить status + acceptance checkboxes в этом файле. Создать `VSM-NNN.yaml` (monotonic, след. номер после VSM-002) если было identity-affecting решение.
6. Для cross-session координации: статус в этом файле = source of truth. Каждая сессия перед стартом читает его.

## Status-таблица (summary)

| Workstream | Status | Зависимости | Волна |
|---|---|---|---|
| T1: failure taxonomy | **✅ done** | — | 1 |
| T2: S1-агент дизайн | **✅ done** | — | 1 |
| Sync 1 | **ready** | T1✅, T2✅ | — |
| T3: retry-механизм | blocked | Sync 1 | 2 |
| T4: MCP tools-server | blocked | Sync 1 (T2) | 2 |
| Sync 2 | blocked | T3, T4 | — |
| T5: S2-пайплайны | blocked | Sync 2 | 3 |

**Глобальные acceptance (для всех workstream'ов):**
- `vsmlite-tb/scripts/validate.sh` GREEN после каждого.
- `grep -rin 'terminal bench\|terminal-bench\|benchmark\|бенчмарк\|harbor' vsm/ src/` — пусто (только `vsmlite-tb` как путь родителя).
- YAML/JSON валидны во всех затронутых файлах.
- Главный инвариант соблюдён: мутации `vsm/` и `src/` — через `child-dispatcher`.

## Открытые вопросы (basta — для человека)

- [ ] LICENSE: TBD (open_source intent; конкретная лицензия — юридическое решение).
- [ ] remote для git push (нет remote; push — basta: `submit_or_publish_results`).
- [x] `runtime_policy.child_mutation`: сейчас `allowed` + `scope: workstream` (для волн 1-2). Вернуть `paused` после завершения workstream-волны 2.
- [x] stateful-vs-stateless retry (T2) — РЕШЕНО: **S1 stateless, fresh-per-invocation** (CONTRACT.md §5). R0/R1/R2 (VSM-003) откатаны в той же сессии — «не усложнять»; VSM-003 → superseded. Retry доносит только `recovery_directive`.
- [ ] **VSM-004 (pending, needs_human_decision)**: концептуальный поворот — Terminal-Bench Dev Set v2 как индикатор автономности (не training data), self-modification продукта = OSM-синтез через vsmlite (не fine-tuning). Человек: «продукт не тренируют, его строят до автономности с учётом метрики проходимости dev-бенча». Инварианты сохраняются: `train_on_eval` (нет ML), `optimize_for_specific_evaluator` (продукт не знает про TB), мембрана (Dev Set → generic tasks). Ждёт решения человека.
