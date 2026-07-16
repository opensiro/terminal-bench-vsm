# Промпт для новой сессии — VSM train eval-pipeline

Скопируй текст ниже в начало новой сессии (после `# Промпт` маркера).

---

# Промпт

Ты работаешь в vsmlite-tb (`/mnt/e/workplace/commercial-projects/Opensiro Collections/terminal-bench-vsm/vsmlite-tb`). Это **родительский VSM** (S5=архитектор), его операция S1 = синтезировать дочерний VSM прикладной области (`../vsm/` + `../src/`) до автономного состояния. Главная цель текущего этапа — **eval-пайплайн для Terminal-Bench train (tb-dev-v2)**: гонять продукт (vsm-product triad, glm-5.2) на задачах, измерять pass-rate, растить A(t) к автономности.

## Контекст предыдущей сессии (кратко)

Предыдущая сессия (2026-07-16) проделала большую работу по починке eval-infra. **Все коммиты уже в main** (HEAD=`0fd4f66`). Прочитай эти файлы ПЕРЕД работой — они содержат весь контекст:

1. **`meta/cycle-runbook.md`** — СТАНДАРТ запуска eval-цикла. Читать первым. Содержит: предусловия (vsm-tools build, pre-pull bases), команды запуска, OOM-митигацию, мониторинг, чеклист перед прогонами. **Внимание: не упоминает VSM-038 (host-network) — см. ниже.**
2. **`meta/verifier-architecture.md`** — ASCII-схема verifier-фазы (как reward течёт от TB test.sh через harbour до A(t)) + 3 слоя верификации.
3. **`issues/VSM-{034,035,036,037,038}.yaml`** — 5 зафиксированных находок с root cause + fix.
4. **`state/true_verification.json`** — baseline registry (архивный snapshot): 14 genuine_pass, 8 false_positive (на момент архива).
5. **`state/archives/runs-20260716-172304.manifest.md`** — архив 265 исторических trials (восстановим через `tar -xzf`).

## Что уже сделано (6 инфра-фиксов, валидированы)

| Fix | Проблема | Решение |
|---|---|---|
| VSM-035 | DNS в harbour-build network (pypi/ghcrio/github timeout) | offline vsm-tools layer: `scripts/build_tools_images.py` строит `vsm-tools:{core,sci}` (goose/uv/get-pip/wheels cp311/312/313) через host docker build; overlay получает через `COPY --from` (zero network) |
| VSM-036 | WORKDIR ≠ /app у 48% train-задач (chdir fail → infra_error attempts=0) | WORKSPACE-probe в `harbor_adapter.py` + `mkdir /app` в overlay |
| — | python3 отсутствует в ubuntu-base задачах | restore `apt-get install python3 python3-pip` в offline overlay |
| — | `No module named yaml` на python 3.12 | 3-я builder stage в `build_tools_images.py` (cp311+cp312+cp313 wheels) |
| VSM-037 | Ложный PASS от overlay-collision (broken-python: overlay ставит pip → test.sh проверяет `import pip` → reward=1.0 без действий продукта) | `scripts/true_verifier.py` — детерминистический post-trial attribution (no LLM): сигнатура `reward=1.0 + s1_control=fail_no_checkpoint + no_observations + s1_artifacts=[]`. Интегрирован в `harbor_bridge.py` (strict_verdict рядом с TB reward). **0 false-alarm на 14 genuine PASS.** |
| **VSM-038** | **test.sh RewardFileNotFoundError**: TB canonical test.sh (apt-get update + curl uv + uv pip install) падал на bridge DNS. Блокировал ВСЕ задачи где verifier uses network (большинство). | **`network_mode: host`** через `eval/host-network-compose.yaml` + wiring в `harbor_config_template.yaml` (extra_docker_compose). Контейнер (agent+verifier) использует host-сеть → DNS работает. **test.sh НЕ модифицирован** (TB ground truth). ВАЛИДНО: acl-permissions task_resolved reward=1.0 (был RewardFileNotFoundError). Submission-safe. |

**Результат:** на последнем батче (26 trials, host-network) — **0 RewardFileNotFoundError, 0 DNS/chdir/yaml errors**. TB raw = strict pass-rate = 11.5% (впервые совпали — все PASS легитимны). Pipeline производит валидные runs для leaderboard-сабмита.

**Результат:** на 251 trial — 0 NEW chdir/yaml/DNS ошибок. Продукт доходит до работы на всех задачах. Архив: `state/archives/runs-20260716-172304.tar.gz`.

## ПРИОРИТЕТ — что сделать (в порядке важности)

### 🔴 #1 (ГЛАВНОЕ): VSM-034 — product surrender (продуктовая проблема в ../src/)

**Инфра полностью починена** (VSM-035..038). Pipeline производит валидные runs.
Теперь главный блокер роста pass-rate = **продукт** (vsm-product triad), не инфра.

**Проблема (VSM-034):** продукт "surrenders" на задачах где workspace пуст/needs prep —
делает ровно `fs.list(".")` + `pytest` → стоп (2 tool_calls, no_observations). Не читает
task_prompt, не создаёт артефакты. ~33% задач (breast-cancer, california-housing,
multi-labeller в батчах). Pass-rate ≈ 11% держится именно из-за этого.

**Корневая причина (3-звенная цепочка, исследована):**
1. **Silent fallback** (`../src/runtime/triad_solver.py:519-524`): goose-planner не вернул
   parseable JSON → тихий откат к rule-based `_default_planner` (hardcoded fs.list+pytest,
   не читает task_prompt). **Ноль observability** — в trace не видно что rule-based ran.
2. **Test-controller PASS on empty** (`triad_solver.py:421-428`): "0 tests collected" =
   no error keywords → verdict=pass (считает пустой workspace успешным).
3. **Orchestrator no_observations** (`../src/orchestrator.py:174-186`): 0 failure_observations
   (pytest exit 0 из-за `|| true`) → terminate after attempt 1.

**Где фикс (через child-dispatcher, НЕ напрямую ../src/):**
- (A) **Убрать silent fallback** — логировать/errors при goose failure (triad_solver.py:519-524,
  654-655). Дать сигнал что rule-based ran вместо goose. Самый глубокий корень.
- (B) **Усилить _default_planner** — читать task_prompt, создавать артефакты (не только
  fs.list+pytest). triad_solver.py:364-392. Делает fallback безопасным.
- (C) **Test-controller: "no_attempt" verdict** — отличать "0 tests collected" от реального
  pass. triad_solver.py:421-428. acceptance: `s1_control.verdict=no_attempt` при 0 artifacts.
- (D) **Orchestrator: retry instead of terminate** — 2-я попытка с другим framing при
  no_observations. orchestrator.py:174-186.

**ВАЖНО:** VSM-034 = `needs_human_decision: true`. Нужно решение стратегии (A/B/C/D или
комбинация) В `issues/VSM-034.yaml → decision` перед child-dispatcher. Read
`../vsm/systems/s1-planner/{SOUL,SKILL}.md` — там уже описано "MUST create artifact",
просто не доходит до goose из-за silent fallback.

### 🟡 #2: Task-own Dockerfile deps (build-network, ЧАСТИЧНО фиксировано)
VSM-038 (host-network) починил **runtime** (test.sh в контейнере). Но **build** network
всё ещё bridge — task-specific deps в Dockerfile задачи (pandas/scikit/jq у anomaly/sakila/
log-summary) падают на DNS. VSM-035 offline layer покрывает product-runtime, не task-specific.
**Решение:** `build: network: host` в task docker-compose, или расширить vsm-tools scan.
Низший приоритет — host-network уже покрыл большинство (test.sh = canonical blocker).

### 🟡 #3: Pre-flight check (race-condition)
Батч стартовал до завершения rebuild vsm-tools → stale tools. Решение: pre-flight в
`eval/modes.py:run_train` проверять `vsm-tools:<profile>` + cp312 wheels перед стартом.

### 🟡 #4: Upsert-баг metrics.record
`eval/metrics.py:record` upsert по task_id затирает предыдущие trials. dev_metrics показывает
total=1 вместо 15. Решение: `metrics.record_batch` или append+dedup по trial_name.

### 🟢 #5 (опц.): broken-python intent-collision
Overlay ставит pip (product runtime), но broken-python просит продукт починить pip.
True-verifier **ловит** (0 false_positive в последнем батче). Detect-and-skip-overlay-deps
для intent-сломанных задач. Низший приоритет.

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
