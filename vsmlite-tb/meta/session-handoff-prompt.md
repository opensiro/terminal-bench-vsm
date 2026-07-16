# Промпт для новой сессии — VSM train eval-pipeline

Скопируй текст ниже в начало новой сессии (после `# Промпт` маркера).

---

# Промпт

Ты работаешь в vsmlite-tb (`/mnt/e/workplace/commercial-projects/Opensiro Collections/terminal-bench-vsm/vsmlite-tb`). Это **родительский VSM** (S5=архитектор), его операция S1 = синтезировать дочерний VSM прикладной области (`../vsm/` + `../src/`) до автономного состояния. Главная цель текущего этапа — **eval-пайплайн для Terminal-Bench train (tb-dev-v2)**: гонять продукт (vsm-product triad, glm-5.2) на задачах, измерять pass-rate, растить A(t) к автономности.

## Контекст предыдущей сессии (кратко)

Предыдущая сессия (2026-07-16) проделала большую работу по починке eval-infra. **Все коммиты уже в main** (HEAD=`7dc63e1`). Прочитай эти файлы ПЕРЕД работой — они содержат весь контекст:

1. **`meta/cycle-runbook.md`** — СТАНДАРТ запуска eval-цикла. Читать первым. Содержит: предусловия (vsm-tools build, pre-pull bases), команды запуска, OOM-митигацию, мониторинг, чеклист перед прогонами.
2. **`meta/verifier-architecture.md`** — ASCII-схема verifier-фазы (как reward течёт от TB test.sh через harbour до A(t)) + 3 слоя верификации.
3. **`issues/VSM-{034,035,036,037}.yaml`** — 4 зафиксированных находки с root cause + fix.
4. **`state/true_verification.json`** — baseline registry: 14 genuine_pass, 8 false_positive, strict 5.6% vs TB 8.8%.
5. **`state/archives/runs-20260716-172304.manifest.md`** — архив 265 исторических trials (восстановим через `tar -xzf`).

## Что уже сделано (5 инфра-фиксов, валидированы)

| Fix | Проблема | Решение |
|---|---|---|
| VSM-035 | DNS в harbour-build network (pypi/ghcrio/github timeout) | offline vsm-tools layer: `scripts/build_tools_images.py` строит `vsm-tools:{core,sci}` (goose/uv/get-pip/wheels cp311/312/313) через host docker build; overlay получает через `COPY --from` (zero network) |
| VSM-036 | WORKDIR ≠ /app у 48% train-задач (chdir fail → infra_error attempts=0) | WORKSPACE-probe в `harbor_adapter.py` + `mkdir /app` в overlay |
| — | python3 отсутствует в ubuntu-base задачах | restore `apt-get install python3 python3-pip` в offline overlay |
| — | `No module named yaml` на python 3.12 | 3-я builder stage в `build_tools_images.py` (cp311+cp312+cp313 wheels) |
| VSM-037 | Ложный PASS от overlay-collision (broken-python: overlay ставит pip → test.sh проверяет `import pip` → reward=1.0 без действий продукта) | `scripts/true_verifier.py` — детерминистический post-trial attribution (no LLM): сигнатура `reward=1.0 + s1_control=fail_no_checkpoint + no_observations + s1_artifacts=[]`. Интегрирован в `harbor_bridge.py` (strict_verdict рядом с TB reward). **0 false-alarm на 14 genuine PASS.** |

**Результат:** на 251 trial — 0 NEW chdir/yaml/DNS ошибок. Продукт доходит до работы на всех задачах. Архив: `state/archives/runs-20260716-172304.tar.gz`.

## ПРИОРИТЕТ — что сделать (в порядке важности)

### 🔴 #1 (главное): Task-own Dockerfile deps offline
**Проблема:** vsm-tools покрывает только **product-runtime deps** (pyyaml/pytest/goose/uv). Но ~5 задач имеют сетевые `RUN` в **своём собственном** task-Dockerfile (`uv pip install pandas==2.2.3 scikit-learn`, `apt-get update`) — те падают на той же ненадёжной harbour-build-network. Это **последний инфра-барьер** перед чисто продуктовыми данными.
**Затронуто:** anomaly-detection-ranking, sakila-sqlite-queries, log-summary, и др. (scan: `grep -rl "pip install\|apt-get" .cache/tb-dev-v2/*/environment/Dockerfile`).
**Пути решения (исследуй и выбери):**
- (A) `--network=host` для harbour-build — host-сеть работает (проверено: `docker build` на host ставит pip/pyyaml OK). Корневое решение, но проверь поддерживает ли harbour 0.18.0 это (через config или env).
- (B) Расширить `build_tools_images.py`: сканировать все task-Dockerfile'ы, извлекать их pip-deps, качать wheels на host, класть в vsm-tools. Overlay тогда ставит task-deps из локального wheels тоже.
- (C) Task-specific prebuild (как VSM-033 для TB-2.1) — тяжело для 100 разных Dockerfile'ов.

### 🟡 #2: Pre-flight check перед стартом батча
**Проблема:** race-condition — батч стартовал, пока vsm-tools ещё перестраивался → первые задачи взяли stale tools (`No module named yaml`).
**Решение:** добавить в `eval/modes.py:run_train` (или `_run_batch`) pre-flight проверку: `vsm-tools:<profile>` существует + содержит cp312 wheels (`docker run --rm --entrypoint sh vsm-tools:core -c "ls /opt/wheels | grep -c cp312"`). Если нет — отказать старту с понятным сообщением.

### 🟡 #3: Upsert-баг metrics.record
**Проблема:** `eval/metrics.py:record` делает upsert по `task_id` — последний trial в батче затирает предыдущие. batch_summary показывал `total=1` вместо 15, dev_metrics терял историю. Cycle даёт ложный `zero_pass`.
**Решение:** `metrics.record_batch` (batch-mode, не per-task upsert) или append + dedup по trial_name. Это чинит cycle observations (pass-rate будет корректный).

### 🟢 #4 (опц.): broken-python intent-collision
**Проблема:** overlay ставит pip (для product runtime), но broken-python = задача «почини pip» → overlay маскирует intent. True-verifier **ловит** (8 false_positive), но overlay всё ещё ставит pip.
**Решение:** detect-and-skip-overlay-deps для intent-сломанных задач (grep Dockerfile на «intentionally break» комментарии). Низкий приоритет — true-verifier уже детектит.

## Главные инварианты (НЕ нарушать)

- **НЕ мутируй `../vsm/` и `../src/` напрямую** — только через субагента `child-dispatcher`. `make validate` проверяет (grep). Read-only наблюдение ОК (`collect_metrics.py`, `true_verifier.py`).
- **TB `tests/test.sh` = ground truth** — детерминистический, не переписывай. True-verifier добавляет атрибуцию, НЕ заменяет reward.
- **`make validate` должен быть GREEN** перед каждым коммитом.
- **Коммить на main** (предыдущие циклы коммитились прямо туда по решению юзера).
- Архив `state/archives/*.tar.gz` — в gitignore (regenerable). Manifest'ы трекаются.

## Как запустить eval-батч (кратко, детали в cycle-runbook.md)

```bash
# 0. Предусловия (один раз):
python3 scripts/build_tools_images.py core sci   # offline tools layer
# pre-pull bases (скрипт в cycle-runbook.md)

# 1. Батч (workers=1 безопасно на 7.8GB RAM; на мощной машине — 2-3):
python3 -m eval --workers 1 run-all --sample 15 --seed 44

# 2. Полный датасет (100 задач):
python3 -m eval --workers 2 run-all

# 3. Между прогонами — чисти cache (важно для OOM):
docker builder prune -f && docker container prune -f

# 4. После батча — true-verifier + cycle:
python3 scripts/true_verifier.py --all --write-registry
python3 scripts/run_cycle.py && python3 scripts/cycle_digest.py
make validate && git add ... && git commit
```

## Что НЕ делать
- НЕ используй LLM для verifier (исследовано: 0% задач требуют, все детерминистические).
- НЕ перезаписывай TB reward — добавляй strict_verdict рядом (как в harbor_bridge.py).
- НЕ стартуй батч не дождавшись rebuild vsm-tools (race-condition).
- НЕ запускай workers≥3 на 7.8GB RAM (OOM смерти уже были).

## С чего начать
1. Прочитай `meta/cycle-runbook.md` + `meta/verifier-architecture.md`.
2. Исследуй приоритет #1 (task-own deps offline) — начни с проверки `--network=host` поддержки в harbour (самый чистый путь).
3. Предложи план, дождись approval, реализуй.
