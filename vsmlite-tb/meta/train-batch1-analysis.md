# Train Batch 1 Analysis — seed=42, 15 tasks × 5 workers (offline overlay)

**Batch:** `state/batch_summaries/train__20260716-*` (Round 4, full offline)
**Date:** 2026-07-16
**Infra:** vsm-tools:{core,sci} + pre-pulled bases — **0 DNS-build-fail** (vs 15/15 in Round 1)
**Result:** батч прерван на 12/15, но продуктовые данные собраны

> Это первый батч где продукт РЕАЛЬНО запускался (durations 119-183s, product
> agent phase работал). Round 1/2/3 падали на infra. Offline-fix (VSM-035)
> снял infra-барьер — теперь видна истинная продуктовая способность.

## Задачи (seed=42, 9 категорий, easy 3 / medium 6 / hard 5 / expert 1)

| task | diff | category | outcome | trace | duration |
|---|---|---|---|---|---|
| broken-python | easy | software-engineering | **PASS** (r=1.0) | 3 | 161s |
| application-debug | hard | debugging | failed | 6 | 183s |
| breast-cancer-mlflow | hard | machine-learning | failed (no_obs) | 3 | 169s |
| california-housing-api | easy | machine-learning | failed (no_obs) | 3 | 176s |
| multi-labeller | hard | machine-learning | failed (no_obs) | 3 | — |
| book-portfolio-analysis | expert | data_engineering | failed (infra) | 2 | 0.7s |
| git-repo-forensics | medium | forensics | failed (infra) | 2 | 0.7s |
| publisher-market-analysis | hard | market_analysis | failed (infra) | — | — |
| simple-database-query-tool | hard | databases | failed (infra) | — | — |
| fix-js-network-controller | medium | debugging | error (build timeout) | — | — |
| reverse-engineer-stack-vm | hard | security | error (overlay-bug) | — | — |
| task-xxe-exploit | medium | security | error (verifier timeout) | — | — |
| api-endpoint, distributed-test, security-breach | — | — | killed (batch stop) | — | — |

**Pass-rate (по завершённым): 1/9 ≈ 11%** (broken-python — ложный PASS, см. ниже).
**Реальный продуктовый pass-rate: 0/9 = 0%** (исключая broken-python overlay-маску).

## Классы продуктовых провалов (3 класса)

### Класс 1: VSM-034 empty-workspace surrender (ПОДТВЕРЖДЁН на train)
**Задачи:** breast-cancer-mlflow, california-housing-api, multi-labeller
**Паттерн (идентичный во всех трёх):**
```
[1 user] <task prompt>
[2 agent] fs.list({"path": "."})          → продукт смотрит CWD
[3 agent] shell.exec("python3 -m pytest") → запускает pytest по пустому workspace
СТОП. terminated_by=no_observations, 2 tool_calls.
```
**Root cause:** продукт делает `fs.list(".")` (относительный путь), видит
пустоту/неполное, и вместо исследования (`fs.list("/app")`, чтение task prompt,
создание файла) — запускает pytest который ничего не находит, и triad завершается.
**Это СИСТЕМНЫЙ продуктовый баг** (VSM-034), не сложность задачи. Продукт не
следует инструкции — он делает ровно 2 вызова и сдаётся, независимо от task.

**Контраст — task prompt breast-cancer-mlflow** просил: «Build ML pipeline, train
models, MLflow tracking, FastAPI deploy». Эталон solve.sh = 40+ строк Python
(загрузка CSV, sklearn, mlflow.log_metrics, register model). Продукт сделал:
`fs.list(".")` + `pytest` → 0 тестов → стоп. **Не предпринял НИ ОДНОГО шага
задачи.**

### Класс 2: infra_error / attempts=0 (продукт не стартовал recovery-cycle)
**Задачи:** book-portfolio-analysis, git-repo-forensics
**Паттерн:** `recovery-cycle complete: terminated_by=infra_error, attempts=0,
verdict=unknown` — triad упал на init, product даже не запустился (0 tool_calls).
**Root cause:** TBD — продукт падает на инициализации для этих задач. Возможно
book-portfolio (data в /workdir/ не /app/) или git-repo (нужен git в workspace).
Требует отладки product-trace — но это уже продуктовая проблема, не overlay.

### Класс 3: timeout / overlay-bug / verifier-timeout (окружение)
**Задачи:**
- fix-js-network-controller: `EnvironmentStartTimeoutError` 300s — build timeout
- reverse-engineer-stack-vm: overlay-bug (многостадийный Dockerfile, `todo-task-base`
  unresolved) — **исправлен** в этом цикле (alias последнего FROM)
- task-xxe-exploit: `VerifierTimeoutError` 60s — продукт task_resolved!, но verifier
  упал по timeout (верификатор слишком тяжёлый / 60s мало)

## broken-python: ЛОЖНЫЙ PASS (overlay маскирует intent)
broken-python = задача-ловушка: «I can't install packages with pip». Intent =
python сломан (Dockerfile intentionally удаляет pip). Эталон solve.sh качает
get-pip.py. Но наш **overlay устанавливает pip через get-pip bootstrap ДО старта
продукта** → pip уже работает → verifier проверяет `pip install` → PASS.
**Продукт не заслугил PASS** (он сделал fs.list+pytest, 0 шагов задачи). Overlay
«решил» задачу вместо продукта. Это структурный конфликт (VSM-035 note) — overlay
не должен чинить то, что задача просит сломать.

## Cross-task синтез (Batch 1)

**Продуктовая способность: КРИТИЧЕСКИ НИЗКАЯ.** Из 9 завершённых с verdict:
- 0 реальных продуктовых успехов (broken-python — маска)
- 3 VSM-034 surrender (системный продуктовый баг)
- 2 infra_error/attempts=0 (продукт не стартует)
- остальное — timeout/окружение

**Доминирующий failure-класс: VSM-034 empty-workspace surrender** (3/9 = 33%
завершённых). Это повторяемый поведенческий паттерн, не случайность — те же
2 вызова (fs.list+pytest) в breast-cancer, california, multi-labeller. Подтверждает
VSM-034 находку с eval-test (TB-2.1) на train-датасете: **продукт системно не
исследует workspace и не следует task prompt.**

**Что продукт МОЖЕТ (из application-debug, 6 steps):** при благоприятных условиях
продукт делает несколько шагов (183s работы) — значит triad функционален, но
trigger-логика «когда сдаться» слишком агрессивна (2 вызова при пустом fs.list).

## Артефакты
- `state/harbor-trials/<task>__<id>/` — trajectory.json, product-trace.json, result.json
- `state/logs/train-round4.log` — батч-лог
- VSM-034 (empty-workspace surrender) — подтверждён количественно (3/9)
- VSM-035 (offline overlay) — валидирован (0 DNS-build-fail, продукт работает)
