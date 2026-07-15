# S3 — optimizer (child) · SKILL

## Tool scope
- **Read**: `state/*`, `vsm.yaml → system_3`, `../src/failure_taxonomy.yaml`,
  [`../../../src/recovery_policies/policies.yaml`](../../../src/recovery_policies/policies.yaml).
- **Write**: `state/metrics.json`.
- **Do not mutate**: `../../vsmlite-tb/`, `../src/`.

## Canonical sources
- `vsm.yaml → system_3.kpi_list` (tailored — product KPI: recovery/retry/policy).
- `vsm.yaml → system_3.triple_index`, `deviation_logic`, `uncertainty_optimization` (VSM-005 §5).
- `../src/failure_taxonomy.yaml` — failure classes → recovery policies + `classifier_guidance`.
- [`CLASSIFIER.md`](CLASSIFIER.md) — failure classifier protocol (T3): observations → class → policy → directive.
- `../src/recovery_policies/policies.yaml` — executor registry.

## Protocol
1. Collect failures from traces (read-only from ../src/ via s1-dispatcher output).
2. **Classify** per `../src/failure_taxonomy.yaml` (see [CLASSIFIER.md §3](CLASSIFIER.md)):
   - match observations by signals, following match_order.
   - multi_match_resolution: more specific signals → win.
   - evidence_required: record the matched signal + class.
   - 0 matches → Unknown.
3. **Select a recovery policy** (class.recovery_policy from the taxonomy).
   - Anti-repeat check: policy_attempt < limit (from s2_anti_repeat).
   - Limit exceeded → bypass detection (CLASSIFIER.md §6).
4. **Form a recovery_directive** (CLASSIFIER.md §5) → delegate to the recovery executor + S2.
5. **Track effectiveness**: `failure_recovery_rate`, `retry_efficiency`,
   `policy_effectiveness`, `classifier_precision` in `state/metrics.json`.
6. **Uncertainty optimization** (VSM-005 §5): on low-confidence → redistribute
   budget, switch policy, emit OSM signals.
7. Deviations > threshold (15%) → digest to S5.
