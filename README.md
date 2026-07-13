# terminal-bench-vsm

> **Продукт = failure-aware coding harness.** Этот monorepo содержит продукт
> (`vsm/` + `src/`) и его калибровочный стенд / layer оценки (`vsmlite-tb/`).
> Продукт — benchmark-agnostic: он не знает, что его оценивают. Калибровочный
> стенд сейчас — Terminal Bench 2.1, но взаимозаменяем (мог быть SWE-bench,
> мог быть реальный поток тикетов).

## Архитектура: продукт ↔ оценщик

```
┌──────────────────────────────────────────────────────────────────┐
│  vsmlite-tb/  — РОДИТЕЛЬ = evaluation/growing layer              │  ← ЗНАЕТ про TB
│  миссия: вырастить продукт и оценить его через Terminal Bench      │     (это «стенд»)
│  S3: pass_rate / coverage по категориям TB                         │
│  S4: эволюция TB (когда сменится версия — basta)                   │
│  S5: identity оценщика + membrane (transduction на границе)        │
│  hard constraints: train_on_eval, use_harbor_tb2,                  │
│    leak_evaluation_context_to_product                              │
└──────────────────────┬───────────────────────────────────────────┘
                       │ мембрана product↔evaluation (VSM-002)
                       │ TB-задача → generic coding task (TB-фрейминг снимается)
┌──────────────────────▼───────────────────────────────────────────┐
│  vsm/  — ПРОДУКТ (дочерний VSM = failure-aware coding harness)    │  ← НЕ ЗНАЕТ про TB
│  миссия: жизнеспособный coding harness для long-horizon агентов    │     (вовсе)
│  S1: солвер (запускается harness'ем = этим VSM)                    │
│  S2: координация recovery (anti-repetition одинаковых неудач)      │
│  S3: failure classifier → recovery policy → retry                  │
│  S3*: независимый аудит recovery                                   │
│  S4: coding patterns / recovery-policy expansions (интернет)       │
│  S5: identity продукта (general-purpose, не оптимизируется под     │
│       конкретный оценочный набор)                                  │
│  KPI: failure_recovery_rate, retry_efficiency,                     │
│       policy_effectiveness, classifier_precision                   │
└──────────────────────┬───────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────┐
│  src/  — данные и инфраструктура продукта                          │  ← НЕ ЗНАЕТ про TB
│  - failure_taxonomy.yaml — первичная онтология (классы сбоев →     │
│    recovery policies: InstallTool / CreateFreshVenv /              │
│    ResetAndReplay / RetryWithSmallerScope / EscalateToS3)          │
│  - run cache: traces + verdicts (verdict — от продукта)            │
│  - Skill DB: general-purpose coding patterns (пополняется S4)      │
│  - session sync: coordination space для мультиагентных прогонов    │
└──────────────────────────────────────────────────────────────────┘
```

**Принцип оценки (blinded).** Продукт (`vsm/` + `src/`) полностью agnostic — не
знает о Terminal Bench ни в design-time, ни в runtime, ни в S5. Даже факт, что
его оценивают, скрыт. Это делает меру качества честной: продукт не может
оптимизироваться под оценочный набор. Знание о TB живёт только в `vsmlite-tb/`
(родитель-оценщик) и в этом корневом README.

## Два режима рабочей директории (cwd)

Структура **portable**: никаких хардкодов абсолютных путей, только относительные.

| Режим | cwd | Кто работает | Что видно |
|---|---|---|---|
| **dev** | `vsmlite-tb/` | человек + Claude Code (разработка/оценка продукта) | вся структура monorepo; команды `/vsmlite-*` |
| **prod** | cwd оценочного стенда (контейнер) | продукт (`vsm/`) как harness для солвера | **только** coding task + tools + environment; TB-структура физически невидима (мембрана усиливается изоляцией контейнера) |

В prod продукт сам поднимается как harness для солвера (архитектура: VSM = harness,
солвер = S1). Оценочный стенд подаёт TB-задачи через membrane; продукт получает
generic coding task.

## Hard constraints (NEVER)

**В продукте (`vsm/` + `src/`)** — product-level, не знают про TB:
- `optimize_for_specific_evaluator` — оставаться general-purpose coding harness.
- `skip_failure_classification` — всегда failure → classifier → policy → retry (blind retry запрещён).
- `circumvent_recovery` — не повторять одну и ту же неудачу >N раз.

**В оценщике (`vsmlite-tb/`)** — evaluation-stand constraints:
- `train_on_eval` — тренировка на eval-разметке TB запрещена правилами бенчмарка.
- `use_harbor_tb2` — `github.com/harbor-framework/terminal-bench-2` не используется
  ни в каком виде (явное требование).
- `leak_evaluation_context_to_product` — не протекать знанием о TB в продукт.

## Basta (только человек принимает решения)

- публикация / сабмит результатов;
- смена целевой версии TB;
- удаление прогонов / данных / логов;
- изменения identity / values / never-do (продукта или оценщика);
- добавление нового класса сбоя в failure taxonomy продукта.

## Quick start

```bash
# dev-режим: открыться в vsmlite-tb/ в Claude Code
cd vsmlite-tb/
# команды родительского VSM (оценщика):
#   /vsmlite-cycle    (полный S2→S3→S3*→S4→S5 с дайджестом)
#   /vsmlite-check    (viability-check + invariant-grep)

# монитор (static HTML, без бэкенда):
cd vsmlite-tb/monitor && python3 -m http.server 8765
#   → http://localhost:8765/            (maturation продукта / 4 знака A(t))
#   → http://localhost:8765/issues.html  (VSM-NNN, вкл. VSM-002 — концептуальный поворот)
```

## Лицензия

**TBD.** Intent — open source. Конкретная лицензия — basta-решение человека
(юридическое), не выбрано. До выбора: default — все права защищены.

## История

`vsmlite-tb/` изначально был отдельным git-репозиторием (template, 5 коммитов);
история сохранена в git bundle. Концептуальная эволюция продукта видна в коммитах:
init → TB-bound → `refactor(product)` (VSM-002) → benchmark-agnostic failure-aware
coding harness.
