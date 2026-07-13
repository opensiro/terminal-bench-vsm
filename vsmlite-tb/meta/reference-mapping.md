# meta/reference-mapping.md — как темплейт соотносится с источниками

> Карта заимствований и отличий vsmlite-template от своих источников.

## Источник 1: `opensiro-arctic/vsm` — эталон одного управляющего VSM

Зрелая реализация VSM-мета-среды для конкретного проекта (Opensiro Collections:
ontology → benchmark → models → web). **vsmlite заимствует структуру**, но
переинтерпретирует роли:

| В opensiro-arctic/vsm | В vsmlite-template | Что изменилось |
|---|---|---|
| Управляет 6 S1-репо проекта | Управляет **одним** дочерним VSM (`../vsm/`) | Сфокусировано на синтезе одного домена, не флота репо |
| `s1-dispatcher` (boundary в `../<repo>`) | `child-dispatcher` (boundary в `../vsm/`+`../src/`) | Та же идея, другой target |
| `issue-liaison` → Gitea | **убран** | Решения в REPL-дайджесте, не во внешнем трекере |
| HTML-дашборд (`monitor/*.html`) | **убран** | UX — терминальный/REPL; `monitor/data.js` остаётся как телеметрия |
| `vsm.yaml` (units + S2-S5 + budget + algedonic→Gitea) | `vsmlite.yaml` (child + synthesis + S2-S5 + telemetry→vsmforge) | S1 = синтез вместо флота юнитов; Gitea → forward-контракт vsmforge |
| 5×4 `{SOUL,SKILL,HEARTBEAT,TASK}` (S2-S5) | **то же** + `synthesis-operator` (6-й) | +1 система: S1 как оператор синтеза |
| `issues/vsm-issue.schema.json` | `issues/vsmlite-issue.schema.json` | `target_unit` обобщён (свободная строка + `child`/`meta`) |
| `scripts/prompt.sh` (композер) | **то же** | — |
| `ref/vsm-theory.md` | **то же** (доменно-agnostic) | — |

**Сохранённый инвариант:** контрольная плоскость никогда не трогает операции
напрямую — только через boundary-агента. Это сердце архитектуры.

## Источник 2: vsmforge (не разработан) — целевая фабрика

vsmforge = VSM, чей S1 производит другие VSM. vsmlite — **поставщик телеметрии**
для будущей агрегации S3/S4 у vsmforge. Контракт односторонний и file-based:

```
vsmlite/monitor/data.js  ──(rsync/local)──►  vsmforge sources.yaml
                                                 │
                                                 ▼
                                       fleet autonomy scoring
                                       (4 знака: S5/S4/S3/S1-sign)
```

| Что vsmlite эмитит | Что vsmforge (будет) потреблять |
|---|---|
| `window.VSM_DATA = { project, systems, units[], metrics{autonomy_score, maturation_phase,...}, audit[], intel[], heartbeat{}, issues[], history[], activity[] }` | `telemetry.py` accessor'ы; `autonomy.py` scorer → AUTONOMOUS/SEMI/DEPENDENT |
| `issues[]` со `status` + `needs_human_decision` | S5-sign (доля эскалаций) |
| `intel[]` self-closed | S4-sign |
| `units[]` ≥2 | S3-sign |
| `activity[]` ≥3 git-дней | S1-sign |

Подробности контракта — [`ref/vsmforge-target.md`](../ref/vsmforge-target.md).

**Заимствования из архитектуры vsmforge (по её docs, даже до разработки):**
- **Init-pipeline pattern**: `discover_* → tailor → realize → validate → flip
  meta.initialized последним`. vsmlite повторяет в [`init/`](../init/), но
  упрощает до lite single-session + добавляет scan-first (которого vsmforge
  намеренно избегает: «intent stated, not guessed»).
- **Playbook format**: `# Skill:` + секции `Purpose / Inputs / Ask / Output /
  Anti-patterns / After` (без YAML front-matter).
- **«There is no compiler»**: VSM — это IR, выводимый агентами, не hand-written.
  vsmlite не пытается «скомпилировать» дочерний VSM — он его **выращивает** по фазам.

## Источник 3: OSM RFC (`osm.md`) — операционная логика

OSM — первоклассна в vsmlite: примитивы и фазы **управляют** созреванием, а не
только документируют. Расширение vsmlite над RFC: **`Create` допустим в Initial
State** (прагматика: иначе рекурсия фабрик). См.
[`synthesis/README.md`](../synthesis/README.md).

## Что НЕ заимствовано (намеренно)

- **Gitea/issue-liaison** — внешний трекер избыточен для lite-темплейта; REPL
  дайджест + `VSM-NNN.yaml` достаточно.
- **HTML-дашборд** — `monitor/data.js` (телеметрия) есть, UI — нет.
- **Доменно-специфичные скрипты** (`bench_match.py`, `taxonomy_counts.py`,
  `coverage_*.py`) — паттерн «агенты зовут канонические скрипты» сохранён, но
  конкретные скрипты — свои (`autonomy.py`, `collect_metrics.py`, `cycle_digest.py`).
- **Heartbeats как основной режим** — vsmlite on-demand (юзер запускает цикл);
  heartbeats опциональны.
