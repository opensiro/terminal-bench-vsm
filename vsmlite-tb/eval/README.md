# `eval/` — Terminal-Bench Dev Set v2 пайплайн оценки продукта

> Оценивает продукт (`../src/` — failure-aware harness) на 100 задачах
> [Terminal-Bench Dev Set v2](https://huggingface.co/datasets/open-thoughts/OpenThoughts-TB-dev-v2),
> записывает pass-rate в `state/dev_metrics.json` как метрику автономности A(t)
> (VSM-004/005).
>
> Живёт в **родителе** (`vsmlite-tb/`): знает про Terminal Bench. Продукт
> (`../src/`, `../vsm/`) остаётся **benchmark-agnostic** — мембрана VSM-002
> снимает TB-фрейминг до пересечения границы.

## Архитектура: docker-exec MCP bridge

```
┌─────────────────────── ХОСТ (vsmlite-tb/) ───────────────────────┐
│                                                                   │
│  eval/runner.py  ──run_single──►  eval/agent_phase.py             │
│         │                              │                          │
│         │                              │  запускает harness        │
│         │                              │  (claude-code / goose)    │
│         │                              ▼                          │
│         │                         ┌──────────┐  mcp_config.json    │
│         │                         │  harness │ ─────────────────┐ │
│         │                         │  (мозг)  │                  │ │
│         │                         └──────────┘                  │ │
│         │                              │ JSON-RPC over stdio      │ │
│         │                              ▼                          │ │
│         │                     docker exec -i <ctr> python3 -m     │ │
│         │                     mcp_server.server                   │ │
│         │                              │                          │ │
│ ┌───────┼──────────────────────────────┼──────────────────────────┼─┐
│ │       │   ┌──── DOCKER КОНТЕЙНЕР ─────▼──────────────────────┐  │ │
│ │       │   │  /opt/mcp_server_src  ←── ../src (ro bind mount) │  │ │
│ │       │   │           │                                        │  │ │
│ │       │   │  mcp_server.server (ПРОДУКТ — руки)               │  │ │
│ │       │   │     shell.exec / fs.* / git.*  ──► /app           │  │ │
│ │       │   │     trace ──► /logs/trace.json                    │  │ │
│ │       │   └───────────────────────────────────────────────────┘  │ │
│ │       │                                                           │ │
│ │       ▼                                                           │ │
│ │  eval/grader.py:                                                  │ │
│ │    docker cp tests/ → /tests  (ПОСЛЕ агента)                      │ │
│ │    docker exec ... bash /tests/test.sh                            │ │
│ │    cat /logs/verifier/reward.txt  ──►  passed = (== "1")          │ │
│ │                                                                   │ │
│ └──── eval/metrics.py ──► state/dev_metrics.json ──────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

**Ключевая идея:** продуктовый MCP-сервер (`../src/mcp_server/`) запускается
**внутри** TB-контейнера, а harness — на хосте. Каждый `shell.exec` MCP
выполняется в реальном TB-окружении (`/app`). Trace пишется в продуктовом
формате (T2 CONTRACT §3). Продукт **не модифицируется и не импортируется**
родителем как модуль — только read-only bind mount + subprocess.

## Мембрана (VSM-002)

`membrane.py` — материализация мембраны, которая раньше была концептуальной:

1. **translate(task)** — TB `instruction.md` → нейтральный `task_prompt`:
   вырезается канарейка (`terminal-bench-canary GUID ...`) и оценочные
   термины (`terminal bench`, `TB`, `harbor`, `benchmark`).
2. **verify_neutrality(prompt)** — assert, что prompt чист; бросает `ValueError`
   при утечке. Вызывается перед передачей в продукт.

`validate.sh §2c` (новая проверка) grep'ит `../src/` и `../vsm/` на упоминания
`terminal-bench/harbor` — инвариант теперь исполняемый.

## Быстрый старт

```bash
# 1. Зависимости (единственная новая — huggingface_hub)
pip install -r requirements.txt

# 2. Docker daemon должен быть запущен
docker info >/dev/null && echo "docker OK"

# 3. Список задач (скачивает датасет при первом запуске, ~100 задач)
make eval-list

# 4. Одна задача
make eval-run TASK=acl-permissions-inheritance

# 5. Подмножество по фильтру
make eval-all FILTER=difficulty=easy LIMIT=5

# 6. Текущий pass-rate
make eval-summary
```

## CLI

```
python3 -m eval {list,run,run-all,summary} [options]

  list                                 список задач
  run     --task <id>                  одна задача (--task можно повторять)
  run     --filter difficulty=medium   все по фильтру
  run-all                              все 100 задач
  summary                              pass-rate из state/dev_metrics.json

Опции:
  --harness claude-code|goose|custom   (default: claude-code, env EVAL_HARNESS)
  --filter difficulty=<e|m|h>|category=<name>
  --limit N                            максимум задач в батче
  --dataset-dir <path>                 override кеша (env EVAL_DATASET_DIR)
```

## Модули

| Файл | Роль |
|---|---|
| `config.py` | `EvalConfig` — пути, harness, таймауты, фильтры. Все пути от `vsmlite-tb/`. |
| `loader.py` | `snapshot_download` (HF) + парсинг `task.toml` → `TBTask[]`. TOML через stdlib `tomllib`. |
| `membrane.py` | TB instruction → нейтральный prompt. `translate()` + `verify_neutrality()`. |
| `container.py` | `TBContainer` — Docker-жизненный цикл: build/up/exec/cp/down. Контекст-менеджер. Генерирует `docker-compose.yaml` на лету. |
| `agent_phase.py` | `run_agent_phase()` — harness + docker-exec MCP bridge, сбор `trace.json`. |
| `grader.py` | `grade()` — копирование `tests/` (после агента), запуск `test.sh`, парсинг `reward.txt`. |
| `runner.py` | `run_single()` / `run_all()` — оркестрация полного цикла. Изоляция ошибок. |
| `metrics.py` | запись/чтение `state/dev_metrics.json`. Идемпотентный upsert, пересчёт summary. |

## Формат `state/dev_metrics.json`

```json
{
  "generated": "2026-07-14",
  "dataset": "open-thoughts/OpenThoughts-TB-dev-v2",
  "harness": "claude-code",
  "summary": {"total": 100, "passed": 42, "failed": 50, "error": 8, "pass_rate": 0.42},
  "by_category": {"system-administration": {"total": 10, "passed": 5, "pass_rate": 0.5}},
  "by_difficulty": {"easy": {"total": 20, "passed": 15, "pass_rate": 0.75}},
  "tasks": [{"task_id": "acl-permissions-inheritance", "status": "passed", "category": "...", ...}]
}
```

`summary.pass_rate` — **входной индикатор автономности** A(t) (VSM-004/005):
рост pass_rate ↑ + снижение S5 interventions ↓ = рост автономности.

## Датасет

[open-thoughts/OpenThoughts-TB-dev-v2](https://huggingface.co/datasets/open-thoughts/OpenThoughts-TB-dev-v2) —
**НЕ табличный** датасет. Это 100 папок задач на диске (скачивается через
`snapshot_download`). Каждая папка:

| Путь | Назначение |
|---|---|
| `task.toml` | метаданные (slug=task_id, difficulty, category, `[agent]/[verifier]/[environment]` timeouts) |
| `instruction.md` | промпт агенту |
| `environment/Dockerfile` | песочница (ubuntu:24.04-based) |
| `solution/solve.sh` | эталонное решение |
| `tests/test.sh` | verifier (пишет `1`/`0` в `/logs/verifier/reward.txt`) |
| `tests/test_outputs.py` | pytest assertions (~94/100 задач) |

Кэш скачивания: `.cache/tb-dev-v2/` (gitignored). Override через `EVAL_DATASET_DIR`.

## Инварианты

- **`make validate` GREEN** — мембрана VSM-002 + parent isolation VSM-005.
- **Продукт не модифицируется** — `../src/` только read-only bind mount в контейнер.
- **Мембрана** — `membrane.verify_neutrality()` перед каждым прогоном.
- **Stateless продукта** (CONTRACT §5) — каждый `python -m mcp_server.server` свежий процесс.
- **Анти-reward-hacking** — `tests/` копируются в контейнер ПОСЛЕ фазы агента.

## Требования

- Docker daemon на хосте.
- `huggingface_hub` (для скачивания датасета).
- `python3 >= 3.11` (`tomllib` в stdlib).
- Harness binary: `claude` (claude-code) или `goose`.
- HF_TOKEN опционален (датасет публичный).

См. также: [VSM-008](../issues/VSM-008.yaml) — фиксация решения, [VSM-004](../issues/VSM-004.yaml) — Dev Set как индикатор автономности.
