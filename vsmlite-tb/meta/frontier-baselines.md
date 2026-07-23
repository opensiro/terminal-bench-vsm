# meta/frontier-baselines.md — frontier-якоря на Terminal-Bench 2.1

> **VOLATILE digest** — динамичная часть benchmark-intelligence: pass-rate'ы
> frontier-моделей и наш прогресс. Обновляется `s4-bench-scout` по каденции (normal:
> каждый scan; elevated: при frontier-сдвиге). Статичная структура бенчмарка — в
> [`tb2-structure.md`](tb2-structure.md).
>
> Источники: `public-report/` (карточки), community/official posts, datasheet'ы.
> External ≠ A(t) (invariant `public-report/README.md`): чужие числа — read-only
> reference, не смешиваются с нашим pass-rate.

## Frontier-таблица (TB-2.1 verified, 89 задач)

| Модель | Pass-rate | Harness | Дата | Reproducibility | Источник |
|---|---:|---|---|---|---|
| **GLM-5.2** (FP8 w + FP8 KV) | **79.8 %** (71/89) | mini-swe-agent | unknown | community self-reported | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1uofoej/) |
| GLM-5.2 (BF16, official) | 81.0 % | Terminus-2 | datasheet | official datasheet | GLM-5.2 datasheet (temp=1.0, top_p=1.0, timeout=4h) |
| Opus 4.5 | 61.80 % | Claude Code v2.1.14 | 2026-05 | reproduced (TB-2.1 fixes) | TB-2.1 verified README |
| GLM-5 | 61.12 % | (TB-2.1 fixes) | 2026-05 | reproduced (instr+env fixes) | TB-2.1 verified README |
| Sonnet 4.5 | 50.34 % | Claude Code v2.1.14 | 2026-05 | reproduced (TB-2.1 fixes) | TB-2.1 verified README |
| Sonnet 4.5 (original TB-2.0) | 44.57 % | Claude Code | pre-fix | original 2.0 | TB-2.1 verified README |
| Opus 4.5 (original TB-2.0) | 52.43 % | Claude Code | pre-fix | original 2.0 | TB-2.1 verified README |
| **vsm (наш продукт)** | **TBD** (инфра в достройке) | claude-code | 2026-07-15 | verified-in-this-repo (structural snapshot) | [`public-report/vsm-baseline-0.0.1.md`](../public-report/vsm-baseline-0.0.1.md) |

> Frontline = **GLM-5.2 ≈ 79.8–81 %**. Наш baseline = структурная точка отсчёта
> (контракты T1-T5, A(t)=0.475); pass-rate замер отложен до готовности инфра-раннера.

## Кластеризация общих fail'ов (GLM-5.2, 17 failed + 1 errored)

Кластеры задач, на которых спотыкается frontier — приоритетные направления для
recovery/taxonomy-анализа продукта. Источник: `public-report/GLM-5.2-FP8_TB-2.1_mini-swe-agent.md`.

| Кластер | Задачи | Признак |
|---|---|---|
| **Sci/bio tooling** | `dna-assembly`, `dna-insert`, `protein-assembly`, `raman-fitting` | нишевые научные библиотеки, длинные pipeline |
| **ML/torch** | `torch-pipeline-parallelism`, `model-extraction-relu-logits`, `torch-tensor-parallelism`* | низкоуровневый distributed/torch internals |
| **Multimedia** | `extract-moves-from-video`, `video-processing`, `gcode-to-text` | мультимодальный ввод / нестандартные кодеки |
| **Data/leaderboard** | `mteb-leaderboard`, `query-optimize` | SQL/optimization, scrape-then-submit |
| **Puzzles/misc** | `regex-chess`, `winning-avg-corewars`, `filter-js-from-html` | game-strategy / нетривиальная логика |
| **Sysadmin/recovery** | `configure-git-webserver`, `db-wal-recovery`, `install-windows-3.11` | конфигурация сервисов, env-специфика |

`*` torch-tensor-parallelism — **errored** (VerifierTimeoutError, not re-run); true
status unresolved. Реальный pass-rate GLM-5.2 может быть ±~1 п.п.

## Что режет frontier (наблюдения)

- **Hard-задачи** (30 шт, 34% датасета) дают львиную долю fail'ов: у GLM-5.2 в
  выборке failed — skew в hard (~56% failed vs 34% в датасете).
- **Длинные compute-задачи** (timeout 3600s: `regex-chess`, `video-processing`,
  `mteb-leaderboard`, `winning-avg-corewars`) — timeout/ресурсные ограничения.
- **Мультимодальные** (`extract-moves-from-video`, `code-from-image`) — требуют
  vision-способностей; были помечены env-fix'ом в 2.1.
- **Нишевые библиотеки/API** (`dna-*`, `raman-fitting`, `mteb-*`) — длинный tail
  domain-знаний, который модель знает хуже.
- **Harness-эффект**: GLM-5.2 official (Terminus-2) = 81.0% vs community
  (mini-swe-agent) = 79.8% — ~1.2 п.п. от harness. Наш harness (claude-code) —
  третий; прямое сравнение требует harness-normalization.

## Web-intel: GLM-5.2 + Terminal-Bench (обзор)

> Что известно из открытых источников на 2026-07-15. Обновляется bench-scout.

- **GLM-5.2** (Zhipu/Z.ai, open-weights) — frontier на agentic-бенчмарках.
  Сильный на Terminal-Bench (datasheet 81.0% Terminus-2). FP8-квантизация +
  FP8 KV cache даёт community-reproducible 79.8% на mini-swe-agent при cache-hit
  98.8%.
- **Terminal-Bench** (Merrill et al. 2026, arXiv:2601.11868) — становится
  стандартом оценки long-horizon agentic coding. **2.1 verified** (2026-05-08) —
  official-коллаборация, исправившая env/instruction-проблемы 2.0. Pre-built
  Docker images на Docker Hub降低了 reproducibility-барьер.
- **Harness-фрагментация**: Terminus-2 (official), mini-swe-agent, Claude Code,
  SWE-agent, DeepSWE — числа НЕ прямо сравнимы без normalization. Это known gap.

## Открытые вопросы для bench-scout (→ VSM-NNN)

- [ ] **Наш pass-rate на полном TB-2.1** — заблокирован инфра-раннером
  (отдельный агент достраивает). Разблокировка → заполнить строку vsm в таблице +
  карточку `public-report/vsm-baseline-0.0.1.md` (pass-rate секция).
- [ ] **Harness-normalization**: наш harness = claude-code, frontier = mixed.
  Нужен ли harness-comparison-контур (отдельный вопрос S5).
- [ ] **Leaderboard-эволюция**: отслеживать новые community-результаты на TB-2.1
  (новые карточки в `public-report/`).
- [ ] **Failure-cluster mapping**: маппить общие fail'ы frontier → классы
  `src/failure_taxonomy.yaml` продукта (входит ли покрытие). Это bridge в S3
  (coverage), не в S4.

## Связанные артефакты

- [`tb2-structure.md`](tb2-structure.md) — статичная структура TB-2.1.
- [`../public-report/`](../public-report/) — baseline-карточки (external + internal).
  - [`GLM-5.2-FP8_TB-2.1_mini-swe-agent.md`](../public-report/GLM-5.2-FP8_TB-2.1_mini-swe-agent.md) — 79.8%
  - [`vsm-baseline-0.0.1.md`](../public-report/vsm-baseline-0.0.1.md) — наш structural snapshot
- [`../state/bench_intel.json`](../state/bench_intel.json) — machine-readable кеш findings.
