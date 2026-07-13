# S3 — optimizer (child) · CLASSIFIER

> **Phase 3+ (активен).** Failure Classifier → Recovery Policy selector. Введён
> workstream'ом T3. Описывает end-to-end pipeline: trace → class → policy → retry.
> Это **протокол**, не реализация — конкретный runtime (python/docker/...) на
> будущих фазах. Контракт S1 (input/output) — в
> [`../s1-dispatcher/CONTRACT.md`](../s1-dispatcher/CONTRACT.md).

## 1. Purpose

S3-classifier читает `failure_observations` из output S1 (см.
[CONTRACT.md §6](../s1-dispatcher/CONTRACT.md)), определяет failure class по
`signals` из [`../../../src/failure_taxonomy.yaml`](../../../src/failure_taxonomy.yaml),
выбирает recovery policy, формирует `recovery_directive` для retry.

**Что делает classifier**: observations → class → policy → directive.
**Что НЕ делает**: не применяет policy к environment (это recovery executor);
не запускает retry (это S2 coordinator); не знает про оценочные наборы.

## 2. Pipeline (end-to-end)

```
S1 output (failure_observations[])
  │
  ▼
┌─────────────────────────────────────────────────────┐
│ 1. CLASSIFY                                         │
│    Для каждого observation:                         │
│    - match по signals из taxonomy (substring/regex) │
│    - по classifier_guidance.match_order             │
│    - multi_match_resolution: точнее signals → win   │
│    - evidence_required: записать matched signal     │
│    Если 0 matches → Unknown                         │
├─────────────────────────────────────────────────────┤
│ 2. SELECT POLICY                                    │
│    class.recovery_policy (из taxonomy)              │
│    Проверка anti-repeat: policy_attempt < limit     │
│    (из class.s2_anti_repeat)                        │
│    Если limit exceeded → эскалация (bypass detect)  │
├─────────────────────────────────────────────────────┤
│ 3. FORM DIRECTIVE                                   │
│    recovery_directive = {                           │
│      failure_class: <id>,                           │
│      policy_applied: <policy id>,                   │
│      env_changes: [<что executor изменит>],         │
│      policy_attempt: <int>                          │
│    }                                                │
├─────────────────────────────────────────────────────┤
│ 4. DELEGATE EXECUTION                               │
│    → recovery executor (применяет policy к env)     │
│    → S2 coordinator (anti-repeat check, retry)      │
│    → S1 получает recovery_directive в input         │
└─────────────────────────────────────────────────────┘
```

## 3. Classification rules

### Match order (из taxonomy `classifier_guidance.match_order`)

1. **code** — SyntaxError/TestFailure/FileLocalizationError (точные паттерны)
2. **dependency** — ImportError/DependencyConflict/CompilationError
3. **git** — GitConflict/GitAuthFailure
4. **resource** — TimeoutExpired/HangDetected/ResourceLimit/PermissionDenied
5. **network** — NetworkError
6. **environment** — ToolNotFound (часто перекрывается с ImportError)
7. **spec** — AmbiguousSpec (diagnostic, no explicit error)
8. **fallback** — Unknown (последний)

### Multi-match resolution

Если несколько классов матчат — предпочитать тот, чьи signals точнее (literal >
regex). При равенстве — category текущей фазы прогона (setup→environment/
dependency, execution→code/resource, comprehension→spec).

### Evidence

Classifier обязан записать в trace: matched signal string + matched class id.
Без evidence — классификация невалидна (S3\* audit отклонит).

## 4. Recovery policy selection

Каждый class в taxonomy имеет `recovery_policy` (id). Classifier выбирает его
автоматически. Anti-repeat check (из `s2_anti_repeat`):

- `policy_attempt` инкрементится при каждом применении той же policy.
- Если `policy_attempt` превышает limit (из s2_anti_repeat формулировки) →
  **bypass detected** — policy применяется но failure рецидивирует.
- Bypass → эскалация: S3-mark policy как flaky (в `policy_effectiveness_tracking.
  flaky_policies`), S4 ищет alternative, при рецидиве → new_failure_class
  _introduction (basta — но product S5 автономен по VSM-006, резолвит сам).

## 5. Recovery directive format

Передаётся в S1 input (см. [CONTRACT.md §2](../s1-dispatcher/CONTRACT.md)):

```
recovery_directive = {
  failure_class: <id из taxonomy>,
  policy_applied: <id policy>,
  env_changes: [<string>],        # что recovery executor изменил в env
  policy_attempt: <int>           # номер попытки этой policy (anti-repeat)
}
```

S1 читает directive как индикатор: «это retry, env был изменён, ожидается
такой-то класс». S1 не получает trace прошлой попытки (stateless — CONTRACT §5).

## 6. Bypass detection

Если recovery policy применена, но failure рецидивирует (тот же class после
retry) → возможные причины:

1. **Policy ineffective** — policy не устраняет root cause. → S3-mark flaky,
   S4 ищет alternative.
2. **Misclassification** — classifier дал неверный class. → S3 реклассификация
   с расширенным context; S3\* independently audits (VSM-005 §5).
3. **Structural gap** — taxonomy не покрывает реальный failure mode. →
   Unknown share растёт → S4 expansion → new_failure_class_introduction.

Bypass → алгедоник (severity S1) → S5 (архитектор) если S3/S3\*/S4 не справляются.

## 7. Recovery policies (registry)

Каждая policy из taxonomy имеет executor (или stub). Реестр — в
[`../../../src/recovery_policies/`](../../../src/recovery_policies/).

| Policy | Class | Executor status |
|---|---|---|
| InstallTool | ToolNotFound | executor |
| InstallDependency | ImportError | executor |
| CreateFreshVenv | DependencyConflict | executor |
| FixBuildConfig | CompilationError | executor |
| FixSyntax | SyntaxError | executor |
| DiagnoseAndPatch | TestFailure | executor |
| RelocalizeAndReplay | FileLocalizationError | executor |
| ResetAndReplay | GitConflict | executor |
| UseAlternateAuth | GitAuthFailure | executor |
| RetryWithSmallerScope | TimeoutExpired | executor |
| KillAndRestart | HangDetected | executor |
| ReduceFootprint | ResourceLimit | executor |
| FixPermissions | PermissionDenied | executor |
| RetryWithBackoff | NetworkError | executor |
| ClarifySpec | AmbiguousSpec | executor |
| EscalateToS3 | Unknown | n/a (эскалация) |

## 8. KPI (из vsm.yaml → system_3.kpi_list)

Classifier трекает:
- `failure_recovery_rate` — доля сбоев, успешно восстановленных.
- `retry_efficiency` — медиана попыток до успеха.
- `policy_effectiveness` — per-policy success rate.
- `classifier_precision` — доля однозначных классификаций (не Unknown).
- `trace_observability` — доля прогонов с полной трассой.

## 9. Dependencies

- **T1** (failure taxonomy): `signals`, `classifier_guidance`, `s2_anti_repeat`.
- **T2** (S1 CONTRACT): `failure_observations` format, `recovery_directive` input.
- **T4** (MCP): tool calls → trace → observations (observability).
- **S3\*** (VSM-005 §5): independently audits classifier decisions (uncertainty).
