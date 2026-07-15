# S4 — scout (child) · SKILL

## Tool scope
- **Read**: `state/metrics.json`, `vsm.yaml → system_4` (tailored), `.intent.yaml`,
  `../src/failure_taxonomy.yaml`.
- **Write**: `state/intel.json`.
- **Do not mutate**: `../../vsmlite/`, `../src/`.
- **Web access (runtime)**: open, scope = general-purpose coding patterns and
  recovery-policy candidates; everything found is agnostic by construction.

## Canonical sources
- `vsm.yaml → system_4.monitoring` (tailored technology/regulation/competitors).
- `vsm.yaml → system_4.weak_signals`, `premises_register`.
- `vsm.yaml → system_4.runtime_internet_access` (mode: open).

## Protocol
1. Scan domain environment sources (coding patterns, recovery techniques, tool discovery).
2. Weak signals / coverage gaps / drift (including failure taxonomy gaps).
3. Premises check (general-purpose invariant; taxonomy coverage; policy determinism).
4. Found coding patterns / recovery-policy candidates → Skill DB (`../src/`).
5. Strategic shift (e.g. a new failure class) → `VSM-NNN signal_type: gap` → S5
   (new_failure_class_introduction — basta).
