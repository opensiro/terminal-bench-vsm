# S4 — scout (child) · SKILL

## Tool scope
- **Читаешь**: `state/metrics.json`, `vsm.yaml → system_4` (tailored), `.intent.yaml`,
  `../src/failure_taxonomy.yaml`.
- **Пишешь**: `state/intel.json`.
- **НЕ мутируешь**: `../../vsmlite/`, `../src/`.
- **Веб-доступ (runtime)**: открытый, scope = general-purpose coding patterns и
  recovery-policy candidates; всё найденное agnostic по построению.

## Канонические источники
- `vsm.yaml → system_4.monitoring` (tailored technology/regulation/competitors).
- `vsm.yaml → system_4.weak_signals`, `premises_register`.
- `vsm.yaml → system_4.runtime_internet_access` (mode: open).

## Протокол
1. Скан источников среды домена (coding patterns, recovery techniques, tool discovery).
2. Weak signals / coverage gaps / drift (включая failure taxonomy gaps).
3. Premises check (general-purpose инвариант; coverage taxonomy; детерминизм policies).
4. Найденные coding patterns / recovery-policy candidates → Skill DB (`../src/`).
5. Strategic shift (напр. новый класс сбоя) → `VSM-NNN signal_type: gap` → S5
   (new_failure_class_introduction — basta).
