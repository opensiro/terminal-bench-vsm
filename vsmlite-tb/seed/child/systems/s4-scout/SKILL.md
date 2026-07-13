# S4 — scout (child) · SKILL

## Tool scope
- **Читаешь**: `state/metrics.json`, `vsm.yaml → system_4` (tailored), `.intent.yaml`.
- **Пишешь**: `state/intel.json`.
- **НЕ мутируешь**: `../../vsmlite/`, `../src/`.

## Канонические источники
- `vsm.yaml → system_4.monitoring` (tailored competitors/tech/regulation).
- `vsm.yaml → system_4.weak_signals`, `premises_register`.

## Протокол
1. Скан источников среды домена.
2. Weak signals / coverage gaps / drift.
3. Premises check.
4. Strategic shift → `VSM-NNN signal_type: gap` → S5.
