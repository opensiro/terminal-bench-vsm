# S1 — dispatcher (child) · HEARTBEAT

On-demand (Phase 1+). cadence — по invocation (harness запускает S1 на задаче).

| Mode | Trigger | Действие |
|---|---|---|
| normal | harness invoke (recovery_directive = null) | один run: launch → trace → collect output |
| elevated | `recovery_directive ≠ null` (Phase 3+) | retry-run: env уже изменён policy, S1 стартует fresh с directive |
| crisis | budget_exhausted повторно / unknown verdict | ⚡ flag в output → S3/S5 (basta если new_failure_class) |

В отличие от S2-S5 (on-demand по cycle), S1 активируется **на задачу** — это
operational unit, а не координатор/контролёр. S1 stateless: каждый invocation
независим, состояние между запусками не хранится (см. [CONTRACT.md §5](CONTRACT.md)).
