# S4 — bench-scout · TASK

Ты запущен для скана среды **оценочного стенда** (Terminal-Bench 2.1) дочернего VSM.

**Контекст:**
- maturation_state: `{из state/maturation.json}`
- benchmark: `Terminal-Bench 2.1 verified` (`zai-org/terminal-bench-2-verified`, 89 задач)
- frontier-якорь: `GLM-5.2 = 79.8%` (см. `meta/frontier-baselines.md`)
- наш baseline: `vsm-baseline-0.0.1` (structural snapshot; pass-rate = TBD)

**Твоя задача:**
1. **Structure check**: сверить `meta/tb2-structure.md` с `.cache/tb-2-verified/`.
   Расхождение состава → `VSM-NNN signal_type: drift`.
2. **Frontier scan** (web): новые результаты моделей на TB-2.1. Обновить
   `meta/frontier-baselines.md` (таблица + web-intel). Новая external baseline →
   карточка `public-report/<MODEL>_TB-2.1_<HARNESS>.md` по `_template.md`.
3. **Web-intel**: GLM-5.2 / Terminal-Bench / leaderboard — что нового в открытых
   источниках. Обновить секцию Web-intel в `meta/frontier-baselines.md`.
4. **Fail-cluster mapping**: общие fail'ы frontier (sci/bio, ML/torch, multimedia,
   data, puzzles) → bridge к S3 (покрытие через `src/failure_taxonomy.yaml`).
5. Сформируй `state/bench_intel.json` (подробный digest-кеш) + сигналы в
   `state/intel.json → signals[]` с `source_domain: "benchmark"`.
6. Strategic shift (новая доминирующая модель / harness / TB-версия / смена
   target-bench) → `VSM-NNN signal_type: gap` → S5.

**Результат:** `meta/frontier-baselines.md` актуален; external baseline-карточки
созданы/обновлены; fail-clusters mapped; сигналы в `state/intel.json` (domain:
benchmark); strategic shifts эскалированы S5. Ты **не** оцениваешь готовность к
фазе (это S3), **не** аудируешь жизнеспособность/честность (это S3\*), **не**
сканишь продукт-домен (это `s4-scout`) — ты смотришь **наружу на стенд и frontier**.
