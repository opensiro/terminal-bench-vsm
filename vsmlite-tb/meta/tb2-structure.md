# meta/tb2-structure.md — структура Terminal-Bench 2.1 (verified)

> **STABLE digest** — статичное описание бенчмарка как оценочного стенда. Меняется
> редко (новый релиз TB / новая версия). Обновляется `s4-bench-scout` при
> `elevated` (новая TB-версия). Динамичная часть (pass-rate моделей) — в
> [`frontier-baselines.md`](frontier-baselines.md).
>
> Источник: `.cache/tb-2-verified/` (датасет `zai-org/terminal-bench-2-verified`,
> релиз 2026-05-08, коллаборация с official TB-командой) + `README.md` / `changes_instructions.md`.

## Что такое Terminal-Bench 2.1

Terminal-Bench (Merrill et al. 2026, arXiv:2601.11868) — бенчмарк long-horizon
agentic coding-задач: агент работает в реальном Linux-окружении (Docker), решает
задачу в терминале, verifier проверяет результат. **2.1 verified** = исправленный
2.0 (env-fixes 89 + instruction-fixes 11, см. ниже), коллаборация с official
TB-командой. Формат — folder-based Harbor: каждая задача = директория.

- **Repo (HF):** `zai-org/terminal-bench-2-verified`
- **Релиз:** 2026-05-08
- **Размер:** 89 задач
- **Локальный кеш:** `.cache/tb-2-verified/` (gitignored; override через `EVAL_DATASET_DIR`)
- **Pre-built Docker images:** `xiangyangli/<task-name>:20260204` на Docker Hub

## Распределение по сложности

| Difficulty | Кол-во | Доля |
|---|---:|---:|
| medium | 55 | 61.8% |
| hard | 30 | 33.7% |
| easy | 4 | 4.5% |

Skew в сторону medium/hard (~95%). «easy» почти нет — бенчмарк не про trivial ops.

## Распределение по категориям (16)

| Категория | Кол-во | Доля |
|---|---:|---:|
| software-engineering | 26 | 29.2% |
| system-administration | 9 | 10.1% |
| security | 8 | 9.0% |
| scientific-computing | 8 | 9.0% |
| data-science | 8 | 9.0% |
| file-operations | 5 | 5.6% |
| debugging | 5 | 5.6% |
| model-training | 4 | 4.5% |
| mathematics | 4 | 4.5% |
| data-processing | 4 | 4.5% |
| machine-learning | 3 | 3.4% |
| video-processing | 1 | 1.1% |
| personal-assistant | 1 | 1.1% |
| optimization | 1 | 1.1% |
| games | 1 | 1.1% |
| data-querying | 1 | 1.1% |

Top-5 категорий (software-engineering + sysadmin + security + scientific-computing
+ data-science) = ~67% задач. Доминирует software-engineering (~29%).

## task.toml — schema

```toml
version = "1.0"

[metadata]
author_name = "…"
author_email = "…"
difficulty = "easy|medium|hard"
category = "<одна из 16>"
tags = ["…", …]
expert_time_estimate_min = <float, опц.>
junior_time_estimate_min = <float, опц.>

[verifier]
timeout_sec = <float>           # 900 / 1200 / 1800 / 3600

[agent]
timeout_sec = <float>           # обычно = verifier.timeout_sec

[environment]
build_timeout_sec = <float>     # стабильно 600
docker_image = "xiangyangli/<task>:20260204"
cpus = <int>                    # 1 (набл.)
memory = "<2G|4G>"
storage = "10G"
```

TB-2.1-специфичные поля `[environment]` (`docker_image`/`cpus`/`memory`/`storage`)
отсутствуют в dev-v2 (train-профиль) — это маркер verified-версии.

## Структура директории задачи

| Путь | Назначение |
|---|---|
| `task.toml` | метаданные + timeouts + environment |
| `instruction.md` | промпт агенту (мембрана VSM-002 снимает TB-фрейминг перед продуктом) |
| `environment/Dockerfile` | песочница (ubuntu-based, pre-built image на Docker Hub) |
| `solution/solve.sh` | эталонное решение |
| `tests/test.sh` | verifier (пишет `1`/`0` в `/logs/verifier/reward.txt`) |
| `tests/test_outputs.py` | pytest-assertions (в большинстве задач) |

## Что было исправлено в 2.0 → 2.1 verified

Два типа фиксов (из `README.md` + `changes_instructions.md`):

### 1. Environment fixes (89 задач — все)
Поддержка Claude Code Agent runtime без изменения логики задач:
- **(a)** `procps` + `python3` + `python3-pip` во все 89 Dockerfile'ов (чинит краш
  KillShell из-за отсутствия `ps`);
- **(b)** nproc-wrapper на 4 ядра для `caffe-cifar-10` (против OOM при `make -j$(nproc)`);
- **(c)** multimodal-декларация в 5 задачах (`code-from-image`, `chess-best-move`,
  `financial-document-processor`, `path-tracing`, `extract-moves-from-video`) —
  предупреждение моделям без vision не читать картинки/PDF через Read.

### 2. Instruction fixes (11 задач)
Исправление instruction/test mismatches:
- **Category A** (4 — test хардкодит пути/форматы): `build-pmars`, `hf-model-inference`,
  `install-windows-3.11`, `caffe-cifar-10`
- **Category B** (4 — неоднозначное API/tool usage): `train-fasttext`, `mteb-retrieve`,
  `adaptive-rejection-sampler`, `protein-assembly`
- **Category C** (3 — строгие test-constraints неCommunicated): `polyglot-c-py`,
  `path-tracing`, `sam-cell-seg`

## Полный список 89 задач

```
adaptive-rejection-sampler        gpt2-codegolf                     polyglot-c-py
bn-fit-modify                     headless-terminal                 polyglot-rust-c
break-filter-js-from-html         hf-model-inference                portfolio-optimization
build-cython-ext                  install-windows-3.11              protein-assembly
build-pmars                       kv-store-grpc                     prove-plus-comm
build-pov-ray                     large-scale-text-editing          pypi-server
caffe-cifar-10                    largest-eigenval                  pytorch-model-cli
cancel-async-tasks                llm-inference-batching-scheduler  pytorch-model-recovery
chess-best-move                   log-summary-date-ranges           qemu-alpine-ssh
circuit-fibsqrt                   mailman                           qemu-startup
cobol-modernization               make-doom-for-mips                query-optimize
code-from-image                   make-mips-interpreter             raman-fitting
compile-compcert                  mcmc-sampling-stan                regex-chess
configure-git-webserver           merge-diff-arc-agi-task           regex-log
constraints-scheduling            model-extraction-relu-logits      reshard-c4-data
count-dataset-tokens              modernize-scientific-stack        rstan-to-pystan
crack-7z-hash                     mteb-leaderboard                  sam-cell-seg
custom-memory-heap-crash          mteb-retrieve                     sanitize-git-repo
db-wal-recovery                   multi-source-data-merger          schemelike-metacircular-eval
distribution-search               nginx-request-logging             sparql-university
dna-assembly                      openssl-selfsigned-cert           sqlite-db-truncate
dna-insert                        overfull-hbox                     sqlite-with-gcov
extract-elf                       password-recovery                 torch-pipeline-parallelism
extract-moves-from-video          path-tracing                      torch-tensor-parallelism
feal-differential-cryptanalysis  path-tracing-reverse              train-fasttext
feal-linear-cryptanalysis         tune-mjcf                         write-compressor
filter-js-from-html               video-processing
financial-document-processor      vulnerable-secret
fix-code-vulnerability            winning-avg-corewars
fix-git
fix-ocaml-gc
gcode-to-text
git-leak-recovery
git-multibranch
```

> Примечание: полный канонический список = содержимое `.cache/tb-2-verified/`
> (89 директорий). Выше — перечисление для навигации; при расхождении источник
> правды — файловая система (`make eval-list --profile eval-test`).

## Связанные артефакты

- [`frontier-baselines.md`](frontier-baselines.md) — динамичные pass-rate'ы моделей на этом бенчмарке.
- [`../public-report/`](../public-report/) — baseline-карточки (external + internal snapshot).
- [`../eval/README.md`](../eval/README.md) — пайплайн оценки (profiles: train / eval-test / eval-dataset).
- [`../eval/config.py`](../eval/config.py) — `DatasetProfile` (cache_subdir, metrics_filename).
