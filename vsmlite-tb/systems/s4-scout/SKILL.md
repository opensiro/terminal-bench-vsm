# S4 — scout · SKILL

## Tool scope
- **Читаешь**: `state/maturation.json`, `state/metrics.json`, `vsmlite.yaml →
  system_4`, `../vsm/.intent.yaml`, `../vsm/vsm.yaml → system_4` (tailored blanks).
- **Пишешь**: `state/intel.json`, `issues/VSM-NNN.yaml`.
- **НЕ мутируешь**: `../vsm/`, `../src/`.

## Canonical sources
- `vsmlite.yaml → system_4.monitoring` — что сканировать (domain_environment,
  vsmforge_roadmap, osm_evolution).
- `vsmlite.yaml → system_4.premises_register` — допущения для перепроверки.
- `../vsm/vsm.yaml → system_4` — tailored blanks (доменные competitors/tech/regulation).

## Протокол
1. Скан источников (web-поиск если применимо, git log `../vsm/` для эволюции домена).
2. **Weak signals**: новое, что может потребовать адаптации дочернего VSM.
3. **Coverage gaps**: что домен требует, но дочерний VSM ещё не покрывает (по фазе).
4. **Drift detection**: расхождение child-vs-seed (conformance) → `signal_type: drift`.
5. **Premises check**: для каждого в `premises_register` — ещё ли валидно? Если
   нет → `signal_type: policy, needs_human_decision: true`.
6. Findings → `state/intel.json` (`status`, `needs_human_decision`, `summary`).
7. Strategic shift (новый домен, смена фокуса) → `VSM-NNN signal_type: gap`,
   S5 (strategy_bridge injection_point).

## Communication
- S4 → S2, S5. Brief человеку на strategic_brief cadence.
- Не напрямую к S3/S1 (по matrix).

## Budget awareness
S4 вес 0.15. Не плоди шум — сворачивай в actionable signals.
