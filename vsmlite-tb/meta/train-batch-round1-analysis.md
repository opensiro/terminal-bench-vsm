# Train Batch — Round 1 Analysis (seed=42, 15 tasks × 5 workers)

**Batch:** `state/batch_summaries/train__20260716-002958.json`
**Date:** 2026-07-16
**Result:** 0/15 passed = **0% pass-rate (100% infra-error)**

> Round 1 провалился полностью на infra (overlay Dockerfile build errors).
> Продукт ни разу не запустился (`trace_len=0`, `duration=0.0s` у всех 15).
> Это **системная infra-проблема**, зафиксированная как VSM-035. Round 2 = повтор
> после фикса overlay.

## Задачи (seed=42, детерминированный sample)

| # | task_id | difficulty | category | outcome |
|---|---|---|---|---|
| 1 | broken-python | easy | software-engineering | error (no pip in image) |
| 2 | api-endpoint-permission-canonicalizer | medium | software-engineering | error |
| 3 | application-debug | hard | debugging | error (uv SSL) |
| 4 | fix-js-network-controller | medium | debugging | error |
| 5 | california-housing-api | easy | machine-learning | error (uv SSL) |
| 6 | distributed-test-execution-scheduler | medium | build-and-dependency-mgmt | error |
| 7 | publisher-market-analysis | hard | market_analysis | error |
| 8 | breast-cancer-mlflow | hard | machine-learning | error |
| 9 | book-portfolio-analysis | expert | data_engineering | error |
| 10 | security-breach-incident-response | medium | cybersecurity | error |
| 11 | simple-database-query-tool | hard | databases | error |
| 12 | reverse-engineer-stack-vm | hard | security | error |
| 13 | multi-labeller | hard | machine-learning | error (DNS numpy) |
| 14 | task-xxe-exploit | medium | security | error (build timeout) |
| 15 | git-repo-forensics | medium | forensics | error (DNS pyyaml) |

Все 15 = `terminated_by=error`, `trace_len=0`, `duration=0.0s`.

## Каталог infra-ошибок (4 класса)

Все ошибки — на этапе Docker build overlay (VSM-033 `_prepare_overlay_task`),
ДО запуска продукта. Продукт (vsm-product triad) ни разу не стартовал.

### Класс A: `No module named pip` (broken-python)
```
#10 0.604 /usr/local/bin/python3: No module named pip
RUN python3 -m pip install ... pyyaml pytest ... → exit 1
```
**Root cause:** broken-python — задача-ловушка. Её собственный Dockerfile
**намеренно ломает Python** (`# Intentionally break the Python installation by
removing critical files`). Overlay пытается pip-install в уже сломанный python.
Это уникально для broken-python — задача требует, чтобы ПРОДУКТ починил pip
(см. instruction: «I can't seem to install packages with pip», эталон solve.sh
качает get-pip.py).

### Класс B: `SSL_ERROR_SYSCALL` на uv download (application-debug, california-housing, ...)
```
curl: (35) OpenSSL SSL_connect: SSL_ERROR_SYSCALL ... release-assets.githubusercontent.com:443
failed to download https://github.com/astral-sh/uv/.../uv-x86_64-unknown-linux-gnu.tar.gz
RUN curl -LsSf https://astral.sh/uv/0.7.13/install.sh | sh ... → exit 1
```
**Root cause:** flaky network на GitHub release-assets. **Нет retry-wrapper**
для uv-install (retry есть только для goose, см. `_prepare_overlay_task` строки
227-237). Один transient SSL → весь build падает.

### Класс C: DNS resolution failure (git-repo-forensics, multi-labeller)
```
NameResolutionError("HTTPSConnection(host='pypi.org'...): Failed to resolve 'pypi.org' ([Errno -3] Temporary failure in name resolution)")
ERROR: No matching distribution found for pyyaml / numpy==2.1.3
```
**Root cause:** harbor-build network не резолвит pypi.org через VPN-TUN
(198.18.0.x). Ручной `docker build` с того же хоста работает (DNS
172.22.160.1, pyyaml ставится OK). Значит harbour использует иной network
context (docker compose / иной bridge), где DNS-резолв WSL2+VPN не работает.
**Flaky**: ручной тест python:3.13-slim + pip pyyaml = OK; harbour-build тех же
задач = DNS fail. Наблюдается intermittently.

### Класс D: `EnvironmentStartTimeoutError` (task-xxe-exploit)
```
harbor/trial/trial.py:1110 raise EnvironmentStartTimeoutError(
  "Environment start timed out after {build_timeout_sec} seconds")
```
**Root cause:** build превысил `build_timeout_sec` (default 600s). Возможно
каскад от класса B/C retry-таймаутов, либо тяжёлая задача.

## Cross-task синтез

**Что Round 1 показал:**
1. **Train-датасет требует иного overlay-фикса, чем TB-2.1.** TB-2.1 (VSM-033)
   решается prebuild-образами (docker_image patch). Train = build-context:
   overlay Dockerfile строится harbor'ом каждый раз, и падает на сетевых
   операциях (pip/uv/curl downloads) из-за flaky DNS/SSL + отсутствия retry.
2. **Продуктовый анализ невозможен** — все 15 упали до запуска агента. Нет ни
   одной trajectory с tool_calls > 0. Нельзя сказать «продукт силён/слаб в
   категории X» — данных ноль.
3. **`broken-python` — структурный конфликт:** overlay-логика (pip install deps
   в build) несовместима с задачами, где сломанный python — часть задачи
   (intent). Overlay ломает intent ещё до старта продукта.
4. **Retry-wrapper нужен для ВСЕХ сетевых RUN**, не только goose. uv и pip
   скачивают из сети в build — один transient fail = весь trial потерян.

**Что Round 1 НЕ показал (нет данных):**
- Поведение продукта на train-задачах (VSM-034 empty-workspace surrender
  паттерн — не подтверждён/опровергнут для train).
- Способность продукта по категориям/difficulty.
- Сравнение с frontier-baselines GLM-5.2.

## Решение для Round 2

**Системная ошибка найдена → Round 2 = повтор тех же 15 после фикса overlay**
(см. VSM-035). Без фикса повтор даст идентичный 0/15 infra-error — это
детерминированный провал, не валидация.

Fix-направления (non-binding, VSM-035):
1. Retry-wrapper для uv-install (как для goose) — 5 попыток с backoff.
2. Retry/fallback для pip-install (`|| pip install ...` или pre-bundled wheel).
3. `--network=host` для harbor-build (если harbour поддерживает) — обойти
   DNS-проблемы VPN-TUN.
4. Для broken-python-like задач: overlay не должен pip-install в образ, где
   python сломан по intent — detect или skip-overlay-deps.

## Артефакты
- `state/batch_summaries/train__20260716-002958.json` — batch record (0/1, infra)
- `state/harbor-trials/<task>__<id>/exception.txt` — 15 build-failure traces
- `state/logs/train-round1.log` — полный лог батча
