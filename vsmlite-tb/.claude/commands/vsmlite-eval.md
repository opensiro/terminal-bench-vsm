---
description: Прогон Terminal-Bench Dev Set v2 eval-пайплайна. Обновляет state/dev_metrics.json (pass-rate), eval_history.json (trend), влияет на A(t) через eval_sign. Ручной триггер; каркас heartbeat в vsmlite.yaml (пока disabled).
argument-hint: "[--task <id> | --filter difficulty=medium | --limit N | --summary]"
allowed-tools: Read, Bash, Edit, Write
---

# /vsmlite-eval

Запускает eval-пайплайн (`eval/`) — оценку продукта на Terminal-Bench Dev Set v2.
Обновляет `state/dev_metrics.json` (pass-rate), `state/eval_history.json` (trend),
косвенно `state/maturation.json` (A(t) через eval_sign при следующем цикле).

## Контекст (прочитай первым)

1. [`eval/README.md`](../../eval/README.md) — архитектура docker-exec MCP bridge.
2. [`issues/VSM-008.yaml`](../../issues/VSM-008.yaml) — фиксация решения.
3. [`vsmlite.yaml`](../../vsmlite.yaml) → `heartbeats.eval_run` — каркас авто-триггера.

## Предусловия

- Docker daemon запущен (`docker info`).
- `huggingface_hub` установлен (`pip install -r requirements.txt`).
- Harness binary доступен (`claude` для claude-code, `goose` для goose).
- HF_TOKEN опционален (датасет публичный).

Если предусловие не выполнено — сообщи юзеру и остановись, не запускай прогон.

## Что делает команда

Ты **не** решаешь TB-задачи сам — eval-пайплайн (`python3 -m eval ...`) делает всё:
скачивает датасет, для каждой задачи строит Docker-песочницу, запускает harness +
продуктовый MCP-сервер внутри контейнера, грейдит. Твоя роль — запустить и
прокомментировать результат.

### Режимы (аргументы)

- (без аргумента) — все 100 задач (`python3 -m eval run-all`).
- `--task <id>` — одна задача (`--task` можно повторять).
- `--filter difficulty=<easy|medium|hard>` — подмножество.
- `--filter category=<name>` — по категории.
- `--limit N` — максимум N задач.
- `--summary` — только вывести текущий pass-rate без прогона (`python3 -m eval summary`).
- `--harness goose` — переопределить harness (default: claude-code, env EVAL_HARNESS).

### Шаги

1. Проверь предусловия. Если что-то не так — сообщи и остановись.
2. Запусти `make eval-list` (если юзер не указал конкретный task/filter) — покажи список.
3. Запусти прогон:
   ```bash
   python3 -m eval run-all [--filter ...] [--limit N] [--harness ...]
   ```
   Прогон долгий (минуты/задача × N). Вывод прогресса — в stderr.
4. После прогона обнови метрики:
   ```bash
   python3 scripts/autonomy.py   # A(t) с учётом eval_sign
   python3 scripts/render_data.py # monitor/data.js с секцией eval
   ```
5. Выведи дайджест:
   ```bash
   python3 scripts/cycle_digest.py
   ```
6. `scripts/validate.sh` — green.

## Вывод в REPL

```
## eval run — <date>
▸ Прогон: <N> задач (<filter>), harness: <type>
▸ Результат: <passed>/<total> = <pass_rate>% (trend: <↑/↓/→> <delta>)
▸ A(t) обновлён: <old> → <new> (eval_sign: <meets/!meets>)
▸ Записано: state/dev_metrics.json, state/eval_history.json
▸ Operational: eval_sign вошёл в A(t); trend виден в дашборде.
```

## Примечания

- Eval дорогой: Docker build + harness API-токены. Для инкрементальной разработки
  используй `--limit 5` или `--filter difficulty=easy`.
- Каркас heartbeat (`vsmlite.yaml → heartbeats.eval_run`) пока закомментирован —
  автоматический прогон добавляется раскомментированием + выбором cadence.
- Мембрана (VSM-002) сохранена: продукт не модифицируется, task_prompt
  нейтрализуется в `eval/membrane.py` перед пересечением границы.
