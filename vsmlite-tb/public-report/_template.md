<!--
  Шаблон baseline-карточки (VSM-028).
  Скопируй в <MODEL>_<BENCH>_<HARNESS>.md, заполни поля в <угловых скобках>.
  Все поля обязательны; если значение неизвестно — пиши `unknown` и добавь
  объяснение в caveats. Числа проверяй на арифметическую консистентность.
  Назначение: frontier-якорь для A(t), read-only reference (НЕ наша метрика).
-->

# Baseline card — <MODEL> · <BENCHMARK> · <HARNESS>

> **<PASS_RATE> %** (<PASSED> / <TOTAL> passed) — <community reproduction | official | reproduced-in-this-repo> via `<harness>` harness.
> <одна строка про конфигурацию: квантизация / notable flag>. <примечание про errored, если есть>.

---

## Metadata

| Field | Value |
|---|---|
| Model | **<MODEL>** (<open-weights / proprietary>) |
| Quantization | **<quantization, напр. FP8 weights + FP8 KV cache / BF16 / …>** |
| Harness | **<harness, напр. mini-swe-agent / Terminus-2 / SWE-agent / claude-code>** |
| Benchmark | **<BENCHMARK>** — <dataset ref, напр. `zai-org/terminal-bench-2-verified` (folder-based Harbor format, N tasks)> |
| Split | <full dataset (N tasks) / N-sample (seed=…)> |
| Pass rate | **<PASSED> / <TOTAL> = <PASS_RATE> %** |
| Date | <YYYY-MM-DD / unknown> |
| Source | [<link>](<url>) |
| Reproducibility | <self-reported by community / official datasheet / verified in this repo> |

---

## Headline result

```
TOTAL:   <TOTAL>
PASSED:  <PASSED>   (<PASS_RATE> %)
FAILED:  <FAILED>
ERRORED: <ERRORED>   <если 0 — удалить строку; если есть — пометить (timed out / …)>
```

---

## Token budget

<!-- Заполни, если доступны. Проверь: input − cache = new; cache/total = hit rate. -->

| Metric | Tokens |
|---|---:|
| Input (total) | <input_total> |
| └ cache hit | <cache_tokens> |
| └ new input | <new_input> |
| Output | <output_tokens> |
| **Cache hit rate** | **<hit_rate> %** |

Sanity: `input − cache = new` → <арифметика> ✓
Cache hit = <cache> / <input> = <hit_rate> % ✓

---

## Sampling / runtime config

<!-- Если значение не из источника — отметь `unknown` и объясни в caveats. -->

| Field | Value |
|---|---|
| Temperature | <value / unknown> |
| top_p | <value / unknown> |
| max_turns / step budget | <value / unknown> |
| per-task timeout | <value / unknown> |
| Inference engine | <vLLM / SGLang / … / unknown> |
| Hardware | <GPU count / type / unknown> |
| Context length | <value / unknown> |

---

## FAILED — <N> (completed, wrong answer)

```
<task_id_1>
<task_id_2>
...
```

<!-- Опц.: кластеризация по типам (sci/bio, ML/torch, multimedia, data, puzzles). -->

## ERRORED — <N>

<!-- Если 0 errored — удали секцию целиком. -->

```
<task_id>   [<ErrorType — re-run status>]
```

---

## Caveats

1. **<caveat 1>** — <пояснение>.
2. **<caveat 2>** — <пояснение>.
3. ...

---

<!--
  Карточка = external reference (read-only). НЕ пишется в state/dev_metrics.json
  и НЕ смешивается с A(t). См. public-report/README.md → invariant.
-->
