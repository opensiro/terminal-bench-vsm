---
description: Bootstrap. scan-first интервью → создание ../vsm/ из seed/child/ + подключение ../src/ за один REPL-проход. Lite single-session init-пайплайн (см. init/README.md).
argument-hint: ""
allowed-tools: Read, Edit, Write, Bash, Agent
---

# /vsmlite-init

Сценарий: vsmlite скопирован в папку, `../src/` и `../vsm/` ещё нет (или `src/`
есть, `vsm/` нет). Init за один REPL-проход обнаруживает прикладной домен,
формулирует OSM Phase 0 Intent, зарождает дочерний `../vsm/`, подключает `../src/`,
tailored blanks, валидирует.

## Контекст (прочитай)

1. [`CLAUDE.md`](../../CLAUDE.md) — S5-конституция + главный инвариант.
2. [`init/README.md`](../../init/README.md) — каталог пайплайна + философия scan-first.
3. [`synthesis/phases.yaml`](../../synthesis/phases.yaml) — фазы созревания.
4. [`synthesis/primitives.yaml`](../../synthesis/primitives.yaml) → `Create` (Initial State).

## Пайплайн (5 шагов, playbooks)

```
1. scan_domain        (scan-first, read-only) → state/domain_draft.yaml
2. discover_intent    (OSM Phase 0, интервью) → ../vsm/.intent.yaml (после шага 3)
3. materialize_child  (cp seed/child/ → ../vsm/, подключить ../src/) → Phase 1
4. tailor_child       (доменные blanks в ../vsm/vsm.yaml)
5. validate_init      (структурный gate → flip meta.initialized: true последним)
```

## Что делает оркестратор (ты)

1. Проверь pre-condition: `../vsm/` не существует или пуст. Если есть и непустой —
   STOP, спроси юзера (возможно resume, а не init).
2. **Шаг 1 — `scan_domain`**: прочитай [`init/scan_domain.md`](../../init/scan_domain.md),
   выполни scan (read-only!) `..` + `../src/`, запиши `state/domain_draft.yaml`.
3. **Шаг 2 — `discover_intent`**: прочитай [`init/discover_intent.md`](../../init/discover_intent.md),
   проведи **короткое** интервью на основе драфта (5 вопросов max). Запиши intent
   во временную переменную (`.intent.yaml` ляжет в `../vsm/` после materialize).
4. **Шаг 3 — `materialize_child`**: спавни `child-dispatcher` с task:
   `materialize` + intent + domain_draft. Создаст `../vsm/` из `seed/child/`,
   подключит `../src/`. Обновит `state/maturation.json` → Phase 1.
5. **Шаг 4 — `tailor_child`**: прочитай [`init/tailor_child.md`](../../init/tailor_child.md),
   спавни `child-dispatcher` с task: `tailor` + tailored blanks.
6. **Шаг 5 — `validate_init`**: прочитай [`init/validate_init.md`](../../init/validate_init.md),
   прогони 8 проверок. Только при `verdict: green` → спавни `child-dispatcher`
   с task: `flip_initialized` (последним!).
7. `python3 scripts/render_data.py` (initial telemetry).
8. `scripts/validate.sh` — green.

## Главное

- **scan_domain — read-only.** Никаких мутаций в scan.
- **Все мутации `../` — через `child-dispatcher`.** Ты сам не делаешь `Write`/`cp` в `..`.
- **`meta.initialized: true` flip'ается ПОСЛЕДНИМ**, только при green validate.
- **Не додумывай домен.** Если материал слабый (`confidence: low`) — доaskни, не
  выдумывай миссию.
- **Создать `../src/`**, если его нет: `child-dispatcher` создаст placeholder
  `../src/README.md` с пометкой «прикладной домен — заполнить».

## После init

- maturation_state: `Phase 1` (Operational Formation).
- Дальше — `/vsmlite-cycle` для роста по фазам OSM.
- `monitor/data.js` — initial telemetry (forward-контракт vsmforge).
