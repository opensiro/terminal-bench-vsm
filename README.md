# terminal-bench-vsm

> **Конечный продукт — VSM.** Этот monorepo содержит родительский VSM
> (`vsmlite-tb/`), выращиваемый дочерний VSM прикладного домена (`vsm/`) и
> сам прикладной домен (`src/`). Миссия — жизнеспособное решение задач
> Terminal Bench 2.1 в рамках его правил, с формированием reusable
> benchmark-agnostic Skill DB.

## Структура monorepo

```
terminal-bench-vsm/
├── vsmlite-tb/   родительский VSM — оператор синтеза (выращивает ../vsm до автономии по OSM)
├── vsm/          дочерний VSM прикладного домена (Phase 1, выращивается)
└── src/          прикладной домен (дочерний S1): агент-решатель + harness + обёртка грейдера
```

Подробности — в [`vsmlite-tb/README.md`](vsmlite-tb/README.md) (template vsmlite) и
[`vsmlite-tb/CLAUDE.md`](vsmlite-tb/CLAUDE.md) (S5-конституция родителя).

## Два режима рабочей директории (cwd)

Структура задумана **portable**: никаких хардкодов абсолютных путей, только
относительные. Поведение зависит от того, кто входит:

| Режим | cwd | Кто работает | Что видно |
|---|---|---|---|
| **dev** | `vsmlite-tb/` | человек + Claude Code (разработка родительского VSM) | вся структура monorepo; команды `/vsmlite-*` |
| **prod** | cwd TB harness (обычно контейнер, напр. `/app`) | решающий агент (S1-solver) | **только** task + tools + environment; VSM/бенчмарк-структура **физически невидимы** |

**Runtime membrane (VSM-001).** В prod-режиме TB harness запускает агента в
изолированном cwd контейнера — это физический слой мембраны. Солвер не знает,
что решает Terminal Bench: VSM снимает TB-маркеры на транедукционной границе,
агент получает generic agentic task. Полная формулировка — в
[`vsm/.intent.yaml`](vsm/.intent.yaml) → `runtime_membrane` и
[`vsm/vsm.yaml`](vsm/vsm.yaml) → `identity.runtime_membrane`.

## Hard constraints (NEVER)

- `train_on_eval` — тренировка на eval-разметке TB запрещена правилами бенчмарка.
- `use_harbor_tb2` — `github.com/harbor-framework/terminal-bench-2` не используется
  ни в каком виде (явное требование).
- `auto_submit` — автоматическая отправка результатов вовне (только человек, basta).
- `runtime_aware_of_benchmark` — решающий агент и runtime-функции S2–S4 не должны
  знать, что это Terminal Bench (blinded-eval, VSM-001).

## Basta (только человек принимает решения)

- публикация / сабмит результатов;
- смена целевой версии TB;
- удаление прогонов / данных / логов;
- изменения identity / values / never-do дочернего VSM.

## Quick start

```bash
# dev-режим: открыться в vsmlite-tb/ в Claude Code
cd vsmlite-tb/
# дальше — команды родительского VSM:
#   /vsmlite-init     (уже выполнен; resume не нужен)
#   /vsmlite-cycle    (полный S2→S3→S3*→S4→S5 с дайджестом)
#   /vsmlite-check    (viability-check + invariant-grep)

# монитор (static HTML, без бэкенда):
cd vsmlite-tb/monitor && python3 -m http.server 8765
#   → http://localhost:8765/            (maturation / системы / 4 знака A(t))
#   → http://localhost:8765/issues.html  (VSM-NNN карточки, в т.ч. VSM-001)
```

## Лицензия

**TBD.** Intent — open source (см. [`vsm/.intent.yaml`](vsm/.intent.yaml) →
`license_intent`). Конкретная лицензия — basta-решение человека (юридическое),
не выбрано на момент этого коммита. До выбора применяется default: все права
защищены, external use — после явного лицензирования.

## История vsmlite-tb

`vsmlite-tb/` изначально был отдельным git-репозиторием (template, 5 коммитов).
При объединении в monorepo его история сохранена в git bundle (не в дереве);
полная pre-monorepo история доступна через `git bundle unbundle` при необходимости.
