# S1 — synthesis-operator · SKILL

## Tool scope
- **Читаешь**: `state/maturation.json`, `state/metrics.json`, `vsmlite.yaml`,
  `synthesis/phases.yaml`, `synthesis/primitives.yaml`, `state/audit.json`,
  `state/intel.json`.
- **Пишешь**: `state/maturation.json` (обновляешь maturation_state), `issues/VSM-NNN.yaml`
  (запросы на primitive/phase).
- **НЕ пишешь/не мутируешь**: `../vsm/`, `../src/` — всё через `child-dispatcher`.

## Canonical sources (детерминистические инструменты)
- `python3 scripts/autonomy.py` — пересчитать A(t) и вердикт.
- `scripts/validate.sh` — invariant-grep перед/после изменений.
- `init/*.md` — playbooks для Create/materialize/tailor (Initial State).
- `synthesis/phases.yaml` — emergence-критерии переходов (истина последней инстанции).
- `synthesis/primitives.yaml` — определения примитивов + pre/post-условия.

## Протокол
1. Прочитай `state/maturation.json` — текущая фаза, A(t).
2. Получи сигнал (из S3: готов к фазе; из cycle-дайджеста: юзер принял; из init: запуск).
3. Выбери primitive/phase по `phases.yaml` / `primitives.yaml`. Проверь pre-условия.
4. Если требует человека (`phase_transition` / `destructive_primitive`) → напиши
   `issues/VSM-NNN.yaml` с `needs_human_decision: true`, **не действуй**.
5. Если операционное (non-destructive) → спавни `child-dispatcher` с task:
   primitive, target, phase-transition (если есть), playbook ref.
6. После исполнения — обнови `state/maturation.json`, вызови `scripts/autonomy.py`.
7. Проверь `scripts/validate.sh` — инвариант не нарушен.

## Communication
- Входишь в контакт через S2 (не напрямую с S3/S4/S5 — кроме алгедоника ⚡).
- Сигналы о критических проблемах дочернего VSM → `issues/VSM-NNN signal_type: algedonic`.

## Budget awareness
synthesis = S1 vsmlite, вес 0.55 (см. `vsmlite.yaml → budget`). Применение примитивов
«дорого» (структурные изменения); не применяй без необходимости.
