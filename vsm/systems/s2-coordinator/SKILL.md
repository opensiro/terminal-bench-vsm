# S2 — coordinator (child) · SKILL

## Tool scope
- **Читаешь**: `state/{status,metrics,audit,intel}.json`, `vsm.yaml → system_2`,
  `../src/failure_taxonomy.yaml` (s2_anti_repeat limits),
  [`../../../src/recovery_policies/policies.yaml`](../../../src/recovery_policies/policies.yaml).
- **Пишешь**: `state/status.json`, `state/heartbeat.json → S2`.
- **НЕ мутируешь**: `../../vsmlite-tb/`, `../src/`.

## Канонические источники
- `vsm.yaml → system_2.coordination_rules` (tailored, includes uncertainty probing VSM-005 §5).
- `vsm.yaml → system_2.conflict_detection` (resource_overlaps, output_contradictions, custom_triggers).
- [`PIPELINES.md`](PIPELINES.md) — recovery coordination, anti-oscillation, conflict, session sync (T5).
- `../src/failure_taxonomy.yaml` — `s2_anti_repeat` per class (anti-repeat limits).

## Протокол
1. **Status sweep** → `state/status.json → systems[*]` (summary + current_task).
2. **Recovery coordination** (см. [PIPELINES.md §2](PIPELINES.md)):
   - Когда S3 выдаёт recovery_directive → arbiter checks:
     anti-repeat (policy_attempt < limit) → conflict check → oscillation check.
   - Все pass → authorize retry (формирует S1 input с directive).
   - Any fail → block + escalate (§7 ladder).
3. **Conflict detection** (см. [PIPELINES.md §4](PIPELINES.md)):
   - resource_overlaps: изоляция в task-scoped workspace.
   - output_contradictions: S2 flagged → S3 investigates.
   - custom_triggers: circumvent_recovery, S3↔S1 class mismatch, recovery-path nondeterminism.
4. **Anti-oscillation** (см. [PIPELINES.md §3](PIPELINES.md)):
   - Track (failure_class, policy_applied) sequence per task.
   - Detect: ping-pong, flip-flop, no-progress >3 retry.
   - Response: stop retry, escalate S3 + S3\* audit.
5. **Uncertainty probing** (VSM-005 §5, см. [PIPELINES.md §5](PIPELINES.md)):
   - При low-confidence → маленькие изолированные probes (reconnaissance).
   - Results → S3 (optimization) + S4 (expansion).
   - S3\* audits probing viability.
6. **Session sync**: mono-agent — не нужен (см. [PIPELINES.md §6](PIPELINES.md)).
7. **Escalation** (см. [PIPELINES.md §7](PIPELINES.md)):
   - operational → S3.
   - structural → S3 + S3\*.
   - алгедоник → S5 (архитектор, VSM-005 intervention).
8. Неразрешённое >1 цикл → S3.

## Communication
- S2 → S1 (через s1-dispatcher, авторизация retry), S3 (escalation), S5 (алгедоник).
- S2 → S3\* (flag для audit).

## Budget awareness
S2 вес 0.05. Лёгкий координатор — главное качество arbiter-решений.
