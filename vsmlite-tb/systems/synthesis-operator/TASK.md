# S1 — synthesis-operator · TASK

Ты запущен, чтобы применить OSM-трансформацию для созревания дочернего VSM `../vsm/`.

**Контекст сейчас:**
- maturation_state: `{из state/maturation.json}`
- A(t): `{из state/maturation.json}`
- сигнал: `{что triggered: S3 ready-to-phase / cycle decision / init step}`

**Твоя задача:**
1. Прочитай `synthesis/phases.yaml` для текущей фазы → `emergence_criteria_to_next`.
2. Прочитай `synthesis/primitives.yaml` → выбери примитив (или phase-transition).
3. Проверь `pre_condition`. Если не выполнено → STOP, доложи S2.
4. Если требует человека (`phase_transition` / `destructive_primitive`) → напиши
   `issues/VSM-NNN.yaml` с `needs_human_decision: true` и ЗАВЕРШИ (не действуй).
5. Иначе — спавни `child-dispatcher` с task:
   - primitive (напр. `Reconfigure`)
   - target: `../vsm/`
   - phase_transition: `{Phase N → N+1}` (если есть)
   - playbook: `{init/materialize_child.md | tail of cycle plan}`
6. После исполнения: обнови `state/maturation.json`, вызови `python3 scripts/autonomy.py`.
7. `scripts/validate.sh` — green.

**Результат:** maturation_state продвинут; A(t) пересчитан; инвариант соблюдён;
если нужно решение человека — `VSM-NNN` написан, ты не действовал.
