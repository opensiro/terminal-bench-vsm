# Train Batch 2 Analysis — seed=43, 15 tasks × 5 workers (offline overlay)

**Batch:** `state/logs/train-batch2.log` (seed=43, disjoint от batch1 почти полностью — 1 overlap)
**Date:** 2026-07-16
**Infra:** vsm-tools:{core,sci} + pre-pulled bases (incl. eclipse-temurin для okhttp)
**Result:** батч прерван на 10/15; продуктовые данные согласованы с Batch 1

> Batch 2 подтверждает Batch 1 + выявляет ОГРАНИЧЕНИЕ offline-фикса: task's-own
> Dockerfile deps (pandas/scikit-learn/jq) всё ещё тянутся через ненадёжную
> build-network. Покрываем product-runtime deps, но не произвольные task-deps.

## Задачи (seed=43, новые категории: general/parsing/chess/sql/backend/sci)

| task | category | outcome | note |
|---|---|---|---|
| application-debug | debugging | failed (task_resolved, r=0.0, 117s, 3 steps) | продукт работал, продуктовый провал |
| bracket-sequence-restoration | general | failed (infra_error, 0.6s) | attempts=0, продукт не стартовал |
| grid-pathfinding | general | failed (infra_error, 0.6s) | attempts=0 |
| anomaly-detection-ranking | general | error | **task Dockerfile: uv pip pandas/scikit → DNS fail** |
| log-summary | sysadmin | error | **task Dockerfile: apt-get update → DNS fail** |
| sakila-sqlite-queries | sql | error | **task Dockerfile: uv pip pandas/numpy → DNS fail** |
| sign-vector-game | machine-learning | error | (task-deps DNS) |
| rsa-jwt-token-api-redis-blacklist | security | error | no exception (product/verifier) |
| pgn-chess-repair-puzzles | chess | error | (task-deps DNS likely) |
| chained-forensic-extraction | security | error | (killed mid) |
| остальные (5) | — | killed (batch stop) | — |

**Pass-rate: 0/10 завершённых = 0%.** (как и Batch 1, исключая ложный broken-python)

## Ключевая находка: ОГРАНИЧЕНИЕ offline-фикса (task's-own Dockerfile deps)

Offline-overlay (VSM-035) покрывает **product-runtime deps** (pyyaml/pytest/goose/uv
через vsm-tools). Но многие train-задачи имеют в **своём собственном Dockerfile**
сетевые RUN для task-specific deps:

```
# anomaly-detection-ranking/environment/Dockerfile (самой задачи):
RUN uv pip install --system pandas==2.2.3 scikit-learn==1.6.1 scipy==1.15.0
  → "failed to lookup address information: Temporary failure in name resolution"

# log-summary/environment/Dockerfile:
RUN apt-get update ... → DNS fail (index files failed to download)

# sakila-sqlite-queries/environment/Dockerfile:
RUN uv pip install --system pandas==2.2.3 numpy==2.2.0 → DNS fail
```

Эти RUN выполняются **до** нашего overlay-stage (они в `todo-task-base` = первый
FROM). vsm-tools не помогает — задача качает свои deps сама, через ту же
ненадёжную build-network. **4-5 задач Batch 2 упали на этом.**

**Это фундаментальное ограничение:** нельзя офлайн-кэшировать произвольные deps
из 100 разных task-Dockerfile'ов (каждая задача тянет свой стек). Варианты:
- pre-pull task-specific deps тоже (но они все разные — нужен scan всех Dockerfile'ов)
- `--network=host` для build (host-сеть работает — корневое решение)
- task-specific prebuild images (как VSM-033 для TB-2.1, но для train — тяжело)

## Подтверждение продуктовых паттернов из Batch 1

- **application-debug** (3 steps, 117s, task_resolved r=0.0): продукт отработал
  full agent phase, но не решил — продуктовый провал, не surrender.
- **bracket-sequence / grid-pathfinding** (infra_error, attempts=0, 0.6s): тот же
  класс 2 из Batch 1 — продукт падает на init, recovery-cycle не стартует.
- **Новых no_observations-surrender в завершённых** не зафиксировано (батч
  прерван), но класс представлен в Batch 1 (3/9) — системный.

## Cross-batch синтез (Batch 1 + Batch 2, ~25 уникальных задач)

**Согласованный вывод по 2 батчам:**
1. **Продуктовая способность продукта (vsm-product / glm-5.2 triad) на train
   КРИТИЧЕСКИ НИЗКАЯ: 0 реальных pass (~20 завершённых с verdict).** Единственный
   PASS (broken-python) — ложный (overlay маска).
2. **Доминирующий failure-класс — продуктовый, не infra:**
   - VSM-034 empty-workspace surrender (3 в B1) — системный продуктовый баг
   - infra_error/attempts=0 (B1: 2, B2: 2) — продукт падает на init
   - продуктовый провал при полной работе (application-debug ×2, task_resolved r=0)
3. **Infra-барьер снят offline-фиксом для product-runtime deps, но остаётся для
   task-specific deps** (pandas/scikit/jq в task's-own Dockerfile) — 4-5 задач B2.

**Для обучения VSM до автономности (главная цель):** pass-rate ≈ 0% означает
A(t) eval_sign не meets (pass_rate < 0.5). VSM не autonomous по eval-критерию.
Корневая продуктовая проблема (VSM-034 surrender) блокирует рост A(t).

## Артефакты
- `state/harbor-trials/<batch2-task>__<id>/` — trajectories, exceptions
- `state/logs/train-batch2.log`
- `meta/train-batch1-analysis.md` — Batch 1 (согласованные выводы)
