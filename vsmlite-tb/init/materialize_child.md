# Skill: materialize_child

## Purpose

Зародить дочерний VSM в `../vsm/` — это применение примитива OSM `Create`
(расширение vsmlite, допустимо только в Initial State, см. `synthesis/osm.md` §4 и
`synthesis/primitives.yaml`). Копирует `seed/child/` (полное Phase-6 состояние),
подставляет `.intent.yaml`, подключает `../src/` как дочерний S1, выставляет
`maturation_state: Phase 1` (Initial State пройден).

## Inputs

- `../vsm/.intent.yaml` — от `discover_intent` (OSM Phase 0).
- `seed/child/` — скелет дочернего VSM (см. `../seed/child/README.md`).
- `state/domain_draft.yaml` — для `candidate_units` (подключение `../src/`).
- `../vsmlite.yaml` — `child.path`, `child.src_path`.

## Procedure

Исполняется через **`child-dispatcher`** (единственный агент с доступом к
`../vsm/` и `../src/`). Ядро vsmlite само **не** делает `Write`/`cp` в `..`.

1. **Проверь pre-condition** (соответствует `primitives.yaml → Create`):
   - `../vsm/` не существует или пуст.
   - `../vsm/.intent.yaml` существует (Phase 0 записан).
   - `seed/child/` присутствует в темплейте.
2. **Скопируй** `seed/child/` → `../vsm/` (рекурсивно, через `child-dispatcher`).
3. **Подставь intent**: `.intent.yaml` уже на месте (шаг 2 его перенёс из
   seed, либо `discover_intent` писал прямо в `../vsm/.intent.yaml` — убедись, что
   файл консистентен).
4. **Подключи `../src/` как дочерний S1:**
   - В `../vsm/vsm.yaml → system_1`: добавь запись для `../src/` (path, purpose,
     owner_agent: `s1-dispatcher` дочернего, recursion_note).
   - В `../vsm/units/README.md`: зарегистрируй юнит(ы) из
     `domain_draft.yaml → candidate_units` (по `meta.layout`).
5. **Выстави maturation_state:**
   - `../vsm/` ещё не «полностью жизнеспособен» (файлы Phase-6 есть, но активны
     только Phase-1 функции). Запиши в `state/maturation.json` (vsmlite):
     `maturation_state: Phase 1`, `A(t): 0.1`, `phase_activated: [S1]`.
   - В `../vsm/vsm.yaml → meta`: `maturation_state: Phase 1`, `initialized: false`
     (валидация ниже flip'нет в `true`).
6. **Создай initial state-скелеты** дочернего VSM (`../vsm/state/*.json`) из
   seed-шаблонов, если seed их не содержит.

## Output

```yaml
# state/maturation.json (vsmlite) — после materialize
{
  "maturation_state": "Phase 1",
  "phase_activated": ["S1"],
  "autonomy": { "current": 0.1, "verdict": "DEPENDENT" },
  "child_path": "../vsm",
  "child_initialized": false,         # → true после validate_init
  "last_primitive": "Create",
  "last_transition": "Initial State → Phase 1",
  "updated": "2026-07-13"
}
```

```yaml
# ../vsm/vsm.yaml → meta (дочерний)
meta:
  name: <domain> VSM
  maturation_state: Phase 1
  initialized: false                  # ПОСЛЕДНИМ flip в validate_init
  parent: vsmlite
```

## Anti-patterns

- **Не создавай `../vsm/` если он уже есть и непустой.** Это не Initial State;
  вернись к юзеру (возможно, это resume, а не init).
- **Не flip'ай `meta.initialized: true` здесь.** Это делает `validate_init`
  последним шагом — флаг это *следствие* формирования, не причина.
- **Не активируй S2–S5 дочернего VSM здесь.** Они «проявляются» по фазам
  (`synthesis/phases.yaml`); на Phase 1 активен только S1. Файлы есть, но
  maturation-трекер помечает их как `phase > current`.
- **Не работай в `../src/`.** Materialize только копирует seed и подключает
  путь; реальная работа в `../src/` — через дочерний s1-dispatcher в будущих
  циклах.
- **Не запускай без `child-dispatcher`.** Ядро vsmlite не трогает `../` напрямую
  (главный инвариант, `CLAUDE.md`).

## After

→ [`tailor_child.md`](tailor_child.md): заполняет доменные blanks в
`../vsm/vsm.yaml` на основе intent + драфта. Затем `validate_init`.
