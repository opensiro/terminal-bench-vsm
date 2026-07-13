# init/ — bootstrap-пайплайн vsmlite (`/vsmlite-init`)

Сценарий: vsmlite скопирован в папку как `vsmlite/`; `../src/` и `../vsm/` ещё
нет (или `src/` есть, а `vsm/` нет). Init за **один REPL-проход** обнаруживает
прикладной домен, формулирует Intent (OSM Phase 0), зарождает дочерний `../vsm/`
из `seed/child/`, подключает `../src/` как дочерний S1, tailored доменные blanks и
валидирует результат.

## Пайплайн (lite single-session)

```
/vsmlite-init
  ├─ 1. scan_domain        (scan-first) читает целевую папку → state/domain_draft.yaml
  ├─ 2. discover_intent    (OSM Phase 0) интервью на основе драфта → ../vsm/.intent.yaml
  ├─ 3. materialize_child  копирует seed/child/ → ../vsm/, подключает ../src/, maturation→Phase 1
  ├─ 4. tailor_child       заполняет доменные blanks в ../vsm/vsm.yaml (ПЕРЕИСПОЛЬЗУЕТСЯ в cycle)
  └─ 5. validate_init      структурный gate → flip meta.initialized: true ПОСЛЕДНИМ (ПЕРЕИСПОЛЬЗУЕТСЯ)
```

## Формат playbooks

Как в vsmforge `seeds/coordination/skills/` — **prompt-template markdown без YAML
front-matter**. Каждый файл:

```
# Skill: <name>
## Purpose         — зачем существует (2–6 строк)
## Inputs          — что должно быть прочитано/существовать до запуска
## <Scan | Ask the developer> — процедура: что читать или какие вопросы задать
## Output          — fenced ```yaml блок с точной формой артефакта
## Anti-patterns   — явный reject-list
## After           — что запускается следующим
```

`/vsmlite-init` (`.claude/commands/vsmlite-init.md`) печатает handoff-промпт;
сессия читает playbooks по порядку. `tailor_child` и `validate_init`
**переиспользуются** вне init: `tailor_child` — в `/vsmlite-cycle` (при изменении
домена), `validate_init` — в `/vsmlite-check`.

## Философия: scan-first дополнение к vsmforge

vsmforge намеренно **не сканирует кодовую базу** — discovery там это
интервью-only («intent stated, not guessed»). vsmlite-lite **позволяет себе
scan-first** для скорости обнаружения прикладного домена: сначала формируется
драфт по существующим материалам (`scan_domain`), затем **короткое** интервью
уточняет Intent (`discover_intent`). Это прагматика lite-темплейта: домен уже
есть (в `../src/` или в окружающих материалах), vsmlite должен его *узнать*, а не
угадывать с чистого листа.

**Граница scan-first:** `scan_domain` читает README/доки/заметки/код — **только
read-only**, никаких мутаций. Весь materialize/tailor — через `child-dispatcher`.
Anti-pattern — «галлюцинированный домен»: если материал не убедителен, вернуть
юзеру запрос уточнить, а не додумывать.

## Что делает каждый playbook

| Playbook | Роль | Output | Только init? |
|---|---|---|---|
| [`scan_domain.md`](scan_domain.md) | read-only обзор целевой папки + `meta.layout` | `state/domain_draft.yaml` | да |
| [`discover_intent.md`](discover_intent.md) | OSM Phase 0: миссия, basta, autonomous-target | `../vsm/.intent.yaml` | да |
| [`materialize_child.md`](materialize_child.md) | копирование seed/child/ → ../vsm/ + подключение ../src/ | `../vsm/` (материализован) | да |
| [`tailor_child.md`](tailor_child.md) | доменные blanks в `../vsm/vsm.yaml` | правки в `../vsm/vsm.yaml` | **нет** (cycle) |
| [`validate_init.md`](validate_init.md) | структурный gate → `meta.initialized: true` | verdict + флаг | **нет** (check) |

## После init

- maturation_state = `Phase 1` (Operational Formation). Дальнейший рост — через
  `/vsmlite-cycle` и `/vsmlite-mature` по emergence-критериям из
  [`../synthesis/phases.yaml`](../synthesis/phases.yaml).
- Когда **vsmforge будет разработан**, `seed/child/` можно будет брать из
  `vsmforge scaffold` вместо встроенного (см. [`../seed/child/README.md`](../seed/child/README.md)).
