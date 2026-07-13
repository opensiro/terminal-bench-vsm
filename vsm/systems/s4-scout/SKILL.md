# S4 — scout (child) · SKILL

## Tool scope
- **Читаешь**: `state/metrics.json`, `vsm.yaml → system_4` (tailored), `.intent.yaml`.
- **Пишешь**: `state/intel.json`.
- **НЕ мутируешь**: `../../vsmlite/`, `../src/`.
- **Веб-доступ (runtime, VSM-001)**: открытый, scope = benchmark-agnostic Skill DB sources; всё через мембрану.

## Канонические источники
- `vsm.yaml → system_4.monitoring` (tailored competitors/tech/regulation).
- `vsm.yaml → system_4.weak_signals`, `premises_register`.
- `vsm.yaml → system_4.runtime_internet_access` (mode: open, transduction via membrane).

## Протокол
1. Скан источников среды домена.
2. Weak signals / coverage gaps / drift.
3. Premises check.
4. Найденные skills → очистка от TB-следов (transduction) → Skill DB.
5. Strategic shift → `VSM-NNN signal_type: gap` → S5.
