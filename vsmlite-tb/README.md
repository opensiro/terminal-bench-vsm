# vsmlite-template

Шаблон репозитория **vsmlite** — лёгкого VSM, чья миссия (S1) — вырастить
соседний прикладной VSM (`../vsm/`) до автономного состояния по принципам
[Organizational Synthesis Model](synthesis/osm.md) (OSM).

> Это **шаблон**. Скопируй этот каталог как `vsmlite/` внутрь своего прикладного
> проекта (рядом с будущими `src/` и `vsm/`) и запусти `/vsmlite-init`.

## Зачем

[Классический VSM](ref/vsm-theory.md) (Стаффорд Бир) отвечает: *«какая структура
делает организацию жизнеспособной?»*. [OSM](synthesis/osm.md) отвечает на
сопутствующий вопрос: *«как жизнеспособные организации синтезируют другие
жизнеспособные организации?»*.

**vsmlite** — это родительский оператор синтеза из OSM §7:

> *Support is performed by dedicated operational units (S1) of the parent VSM
> whose mission is organizational synthesis and maturation.*

Конкретно: vsmlite сам устроен как (урезанный) VSM, а его **S1 = синтезировать
`../vsm/` до автономии**. По мере роста автономности `A(t)` (0 → 1) функции
передаются дочерней системе, и vsmlite постепенно отходит в сторону.

### Метацель: vsmforge

Конечный смысл существования vsmlite — формировать данные для **vsmforge**
(фабрики VSM, способной порождать автономные VSM). vsmforge сейчас **не
разработан**, поэтому держим его как [forward-контракт](ref/vsmforge-target.md),
не как runtime-зависимость: vsmlite эмитит телеметрию `monitor/data.js` в той
форме, которую vsmforge по своей архитектуре будет потреблять. Когда фабрика
появится — агрегация S3/S4-автономности заработает без переделок.

## Форма проекта

```
<project>/
├── src/        прикладной домен (дочерний S1: реальная работа)
├── vsm/        дочерний VSM, выращиваемый до автономии (A(t) → 1)
└── vsmlite/    ЭТОТ темплейт — родительский VSM, синтезирующий ../vsm/ по OSM
```

- `src/` — рабочая папка прикладной области (по типу `opensiro-arctic/*` кроме
  `vsm/`). Появляется на Phase 1 (Operational Formation) или существует заранее.
- `vsm/` — формируемый до автономности VSM прикладной области. Создаётся из
  [`seed/child/`](seed/child/) на шаге `materialize_child` пайплайна init.
- `vsmlite/` — этот каталог; управляет созреванием соседей, **не трогая их
  напрямую** (см. граничный инвариант ниже).

## Состояния созревания (OSM)

`Initial State` → `Phase 0 (Intent)` → `Phase 1 (S1)` → `Phase 2 (S2)` →
`Phase 3 (S3)` → `Phase 4 (S3*)` → `Phase 5 (S4)` → `Phase 6 (S5)` →
`Autonomous`. Полное определение — в [`synthesis/phases.yaml`](synthesis/phases.yaml);
текущее состояние — в `state/maturation.json`.

Примитивы OSM (применяются `synthesis-operator`): `Create` (только из Initial
State) + `Split / Merge / Intersection / Remove / Reconfigure` — см.
[`synthesis/primitives.yaml`](synthesis/primitives.yaml).

## Быстрый старт

```bash
# 1. Скопировать шаблон как vsmlite/ внутрь прикладного проекта
cp -r /path/to/vsmlite-template  <project>/vsmlite

# 2. В сессии Claude Code, открытой в <project>/vsmlite/:
/vsmlite-init          # scan-first интервью → создание ../vsm/ + подключение ../src/

# 3. Дальше — по требованию:
/vsmlite-cycle         # ЦЕНТР: REPL-цикл созревания → дайджест → твои решения → исполнение → телеметрия
/vsmlite-mature        # продвинуть child к следующей фазе
/vsmlite-check         # viability-проверка модели + инвариант-grep
/vsmlite-telemetry     # эмитить monitor/data.js (экспорт для vsmforge)
/vsmlite-scan          # только S4 (скан среды домена)
```

Юзер — инициатор цикла: запускает, получает дайджест изменений, решает когда
нужно (S5 *basta: prepare_only* — готовит решения, не принимает за человека).

## Граничный инвариант

Один boundary-агент — **`child-dispatcher`** — единственный, кто касается
`../vsm/` и `../src/`. Всё остальное в `vsmlite/` (слэш-команды, S2–S5,
`synthesis-operator` как планировщик) **только**: спавнит субагентов, читает
`state/`, пишет `issues/` и `monitor/data.js`. Read-only исключение —
`scripts/collect_metrics.py`. Проверяется `scripts/validate.sh`.

Это прямое зеркало того, как `opensiro-arctic/vsm` достигает `../<repo>` только
через `s1-dispatcher`: контрольная плоскость никогда не трогает операции
напрямую.

## Структура каталогов (шпаргалка)

```
vsmlite/
├── CLAUDE.md            S5-конституция vsmlite (ты здесь рядом)
├── vsmlite.yaml         модель (child, src, synthesis, systems S2-S5, telemetry, OSM)
├── meta/                выжимки: почему vsmlite существует (vsmforge-digest, osm-summary)
├── synthesis/           OSM первоклассно: osm.md RFC + primitives.yaml + phases.yaml
├── init/                init-пайплайн playbooks (scan_domain → intent → materialize → tailor → validate)
├── systems/             SOUL/SKILL/HEARTBEAT/TASK для S2-S5 + synthesis-operator + permission matrix
├── issues/              алгедонический канал: VSM-NNN записи + обобщённая schema
├── state/               runtime-состояние (maturation.json, metrics.json, ...)
├── monitor/data.js      телеметрия window.VSM_DATA (для агрегации в vsmforge)
├── scripts/             детерминистические инструменты (агенты зовут их, не делают сами)
├── seed/child/          скелет дочернего vsm (полное Phase-6 состояние; progressive-reveal)
├── ref/                 теория: vsm-theory, osm-theory, vsmforge-target, bibliography
└── .claude/{agents,commands}/   субагенты и слэш-команды
```

Подробнее — в [`CLAUDE.md`](CLAUDE.md) (S5-идентичность), [`vsmlite.yaml`](vsmlite.yaml)
(модель), [`synthesis/README.md`](synthesis/README.md) (как OSM применяется).

## Источники

- Эталонная реализация одного управляющего VSM: `opensiro-arctic/vsm`
  (адаптация схемы ViableOS под Claude-субагентов).
- OSM RFC (включён как [`synthesis/osm.md`](synthesis/osm.md)) — расширение VSM
  Стаффорда Бира.
- vsmforge (не разработан) — целевая фабрика; контракт агрегации описан в
  [`ref/vsmforge-target.md`](ref/vsmforge-target.md) и [`meta/vsmforge-digest.md`](meta/vsmforge-digest.md).

## Audit (for external reviewers)

- [`POC_LOGS.md`](POC_LOGS.md) — proof-of-concept evidence: chronological record
  of what the maturation loop and eval pipeline have actually run (15 cycles,
  5 train batches, eval runs), with explicit caveats about what is proven
  (pipeline integrity) vs. what is not (full benchmark performance).
- [`SECURITY.md`](SECURITY.md) — secret-handling policy, reporting process, and
  pre-publish checklist.
- [`public-report/`](public-report/) — external baseline cards (frontier anchors
  for A(t), kept separate from our own runs).
