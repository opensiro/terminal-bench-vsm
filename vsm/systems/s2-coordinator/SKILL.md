# S2 — coordinator (child) · SKILL

## Tool scope
- **Read**: `state/{status,metrics,audit,intel}.json`, `vsm.yaml → system_2`,
  `../src/failure_taxonomy.yaml` (s2_anti_repeat limits),
  [`../../../src/recovery_policies/policies.yaml`](../../../src/recovery_policies/policies.yaml).
- **Write**: `state/status.json`, `state/heartbeat.json → S2`.
- **Do not mutate**: `../../vsmlite-tb/`, `../src/`.

## Canonical sources
- `vsm.yaml → system_2.coordination_rules` (tailored, includes uncertainty probing VSM-005 §5).
- `vsm.yaml → system_2.conflict_detection` (resource_overlaps, output_contradictions, custom_triggers).
- [`PIPELINES.md`](PIPELINES.md) — recovery coordination, anti-oscillation, conflict, session sync (T5).
- `../src/failure_taxonomy.yaml` — `s2_anti_repeat` per class (anti-repeat limits).

## Protocol
1. **Status sweep** → `state/status.json → systems[*]` (summary + current_task).
2. **Recovery coordination** (see [PIPELINES.md §2](PIPELINES.md)):
   - When S3 produces a recovery_directive → arbiter checks:
     anti-repeat (policy_attempt < limit) → conflict check → oscillation check.
   - All pass → authorize retry (shapes the S1 input with the directive).
   - Any fail → block + escalate (§7 ladder).
3. **Conflict detection** (see [PIPELINES.md §4](PIPELINES.md)):
   - resource_overlaps: isolation in the task-scoped workspace.
   - output_contradictions: S2 flags → S3 investigates.
   - custom_triggers: circumvent_recovery, S3↔S1 class mismatch, recovery-path nondeterminism.
4. **Anti-oscillation** (see [PIPELINES.md §3](PIPELINES.md)):
   - Track the (failure_class, policy_applied) sequence per task.
   - Detect: ping-pong, flip-flop, no-progress >3 retries.
   - Response: stop retry, escalate to S3 + S3\* audit.
5. **Uncertainty probing** (VSM-005 §5, see [PIPELINES.md §5](PIPELINES.md)):
   - On low-confidence → small isolated probes (reconnaissance).
   - Results → S3 (optimization) + S4 (expansion).
   - S3\* audits probing viability.
6. **Session sync**: mono-agent — not needed (see [PIPELINES.md §6](PIPELINES.md)).
7. **Escalation** (see [PIPELINES.md §7](PIPELINES.md)):
   - operational → S3.
   - structural → S3 + S3\*.
   - algedonic → S5 (architect, VSM-005 intervention).
8. Unresolved >1 cycle → S3.

## Communication
- S2 → S1 (via s1-dispatcher, retry authorization), S3 (escalation), S5 (algedonic).
- S2 → S3\* (flag for audit).

## Budget awareness
S2 weight 0.05. Lightweight coordinator — the key is arbiter decision quality.
