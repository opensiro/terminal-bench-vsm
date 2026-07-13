# S2 — coordinator (child) · PIPELINES

> **Phase 2+ (активен).** S2 coordination pipelines. Введён workstream'ом T5.
> Описывает: recovery coordination, anti-oscillation, conflict triggers,
> session sync decision. Это **протокол**, не реализация — конкретный runtime
> на будущих фазах.

## 1. Purpose

S2 координирует recovery между S1 (солвер) и S3 (failure classifier + recovery
policy selector). S2 — arbiter: гарантирует что retry не конфликтует, не
осциллирует, не нарушает anti-repeat. S2 НЕ классифицирует (S3), НЕ применяет
policy (recovery executor), НЕ запускает S1 (s1-dispatcher).

## 2. Recovery coordination pipeline

Когда S3-classifier (T3) выдаёт recovery_directive, S2 arbiter-ит retry:

```
S3-classifier → recovery_directive
  │
  ▼
S2 arbiter checks:
  ┌─────────────────────────────────────────────────────────────┐
  │ 1. ANTI-REPEAT CHECK                                       │
  │    policy_attempt < limit (из taxonomy s2_anti_repeat)?     │
  │    Если NO → block retry, escalate (bypass detection,       │
  │    CLASSIFIER.md §6) → S3-mark flaky → S4 expansion         │
  ├─────────────────────────────────────────────────────────────┤
  │ 2. CONFLICT CHECK                                          │
  │    Retry не конфликтует с другими attempts?                 │
  │    (resource_overlaps, output_contradictions — см. §4)     │
  │    Если конфликт → изоляция + очередь                      │
  ├─────────────────────────────────────────────────────────────┤
  │ 3. OSCILLATION CHECK                                       │
  │    Не осциллирует ли (паттерн A→B→A→B по попыткам)?         │
  │    (см. §3 anti-oscillation)                               │
  │    Если осцилляция → стоп, escalate S3/S5                  │
  ├─────────────────────────────────────────────────────────────┤
  │ 4. AUTHORIZE RETRY                                         │
  │    Все checks pass → S2 формирует новый S1 input с         │
  │    recovery_directive заполненным → s1-dispatcher.invoke   │
  └─────────────────────────────────────────────────────────────┘
```

S2 — единственный, кто авторизует retry. S3 предлагает (directive), S2 проверяет
и запускает. Это разделение control (S3) и coordination (S2).

## 3. Anti-oscillation

Осцилляция = паттерн где retry чередуется между двумя+ классами/policies без
прогресса: A→B→A→B→A→B. Признаки:

- **Policy ping-pong**: InstallTool → CreateFreshVenv → InstallTool → ...
  (класс качается между ToolNotFound и DependencyConflict).
- **Class flip-flop**: ImportError → DependencyConflict → ImportError → ...
  (classifier даёт разные классы на похожие observations).
- **No-progress retry**: >3 retry без изменения verdict (всё task_failed).

Detection:
- S2 трекает sequence of (failure_class, policy_applied) per task.
- Pattern match: чередование 2+ классов/policies >2 циклов → oscillation.
- No-progress: verdict не меняется >3 retry → oscillation.

Response:
- **Стоп retry** — блокирует дальнейшие retry этой задачи.
- **Escalate S3** — S3 реклассификация с расширенным context; S3\* independently
  audits (VSM-005 §5) — может выявить misclassification или structural gap.
- **Если S3/S3\* не справляются** → алгедоник → S5 (архитектор) intervention
  (VSM-005: +1 к intervention metric).
- **Если structural gap** (taxonomy не покрывает) → Unknown share растёт →
  S4 expansion → new_failure_class_introduction.

## 4. Conflict detection (из vsm.yaml → system_2.conflict_detection)

### resource_overlaps
Два retry одной задачи (или разные задачи) конкурируют за ресурсы:
- Один workspace (filesystem conflict).
- Один git ref (merge conflict).
- Один port/process (runtime conflict).

Response: изоляция — каждый retry в свой task-scoped workspace (T2 CONTRACT §2
`environment.workspace`). Если конфликт — очередь, не параллель.

### output_contradictions
Два прогона одной задачи дают разные verdicts или разные recovery-пути:
- Run 1: task_failed (ImportError) vs Run 2: task_failed (GitConflict) —
  недетерминизм классификации (custom_trigger).
- Run 1: task_resolved vs Run 2: task_failed — flaky test или env difference.

Response: S2 flagged → S3 investigates (classifier precision check) → S3\* audit.

### custom_triggers (из vsm.yaml, tailored VSM-002)
1. **Солвер расходится с recovery policy**: S1 пытается иной путь вместо
   предписанной policy (circumvent_recovery). → S2 блок, escalate S3.
2. **S3 и S1 расходятся в типе сбоя**: S1 считает "ошибка в коде", S3
   классифицировал как "dependency". → S2 flagged → S3\* audit (VSM-005 §5).
3. **Недетерминизм recovery-путей**: два прогона → разные recovery-пути.
   → S2 flagged → S3 investigates classifier stability.

## 5. Uncertainty probing (VSM-005 §5)

При low-confidence (солвер колеблется, нет готового pattern), S2 проводит
probing — маленькие изолированные пробы для уточнения характера задачи:

- **Probing ≠ solve**: reconnaissance, не полноценный solve. Маленький budget,
  узкий scope.
- **Isolated**: каждый probe в свой task-scoped workspace (не загрязняет main).
- **Results → S3/S4**: probing уточняет характер задачи → S3 optimization
  (budget/policy), S4 expansion (knowledge).
- **S3\* audit** (VSM-005 §5): S3\* проверяет что probing достаточен, не избыточен,
  релевантен. Если S3\* находит reaction нежизнеспособной → алгедоник → S5.

Probing — это S2 pipeline, не S1 retry. S1 не знает про probing; S2 координирует
эксперименты и доносит результаты в S3/S4.

## 6. Session sync decision

**Решение: mono-agent — session sync НЕ нужен.**

T2 CONTRACT определяет S1 как single solver per invocation (stateless,
fresh-per-invocation). Нет shared state между агентами в одном invocation —
потому что агент один. S2 координирует retry между invocations (не между
агентами); state живёт в recovery_directive (input) + trace (output), не в
shared session store.

**Исключение (future):** если S1 станет мультиагентным через OSM-примитив Split
(planner + executor + verifier), понадобится session sync — shared state между
суб-агентами одной задачи. Но это structural change (Split), требующий
родительского решения (VSM-006: identity/values change — единственное исключение
автономии product S5). До Split — session sync не нужен.

**Stub:** `src/session_sync/` НЕ создаётся сейчас. Если Split применится —
создастся `src/session_sync/README.md` с contract (shared state format,
isolation, consistency). Сейчас — явно помечено «не нужен (mono-agent)».

## 7. Escalation ladder

```
S2 detects issue (anti-repeat / conflict / oscillation)
  │
  ├─ operational (anti-repeat limit, resource overlap) → block + S3
  │   S3 реклассификация / смена policy / S4 expansion
  │
  ├─ structural (oscillation, class flip-flop, no-progress) → S3 + S3* audit
  │   S3* independently checks (VSM-005 §5)
  │   Если S3/S3* не справляются → алгедоник
  │
  └─ алгедоник → S5 (архитектор) intervention
      S5 применяет структурное изменение (OSM-примитив)
      +1 к intervention metric (VSM-005)
      VSM не знает о вмешательстве (parent isolation)
```

## 8. KPI (S2 contribution)

S2 не имеет собственных KPI, но влияет на:
- `retry_efficiency` (S3 KPI) — anti-oscillation предотвращает waste.
- `policy_effectiveness` (S3 KPI) — anti-repeat предотвращает ineffective retries.
- `classifier_precision` (S3 KPI) — conflict detection выявляет misclassification.

## 9. Dependencies

- **T1** (taxonomy): `s2_anti_repeat` per class — limit для anti-repeat.
- **T3** (CLASSIFIER): recovery_directive format, bypass detection.
- **T2** (S1 CONTRACT): retry lifecycle, stateless semantics.
- **VSM-005 §5**: S2 uncertainty probing, S3\* audit of reactions.
- **VSM-006**: S5 product autonomous — escalation к S5 (не human).
