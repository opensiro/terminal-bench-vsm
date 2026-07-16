# Стандарт запуска eval-цикла (playbook)

> Сформирован по итогам сессии 2026-07-16: 4 infra-фикса (VSM-035 offline,
> VSM-036 WORKDIR, python3-apt, py312-wheels) + OOM-mitigation. Это canonical
> процедура для запуска eval-батча на train (tb-dev-v2) с учётом всех ограничений.

## Предусловия (выполнять в порядке)

### 1. Сеть: host-сеть работает, harbour-build — нет
WSL2 + VPN-TUN: DNS резолвится на host (172.22.160.1), но **docker build network
в harbour ненадёжна** (timeout на pypi.org/ghcr.io/github.com). Поэтому ВСЕ
сетевые операции выносятся на host; в build — только COPY из локального.

### 2. vsm-tools образы (offline deps layer) — строить ОДИН РАЗ, ДО батча
```bash
python3 scripts/build_tools_images.py core sci    # покрывает 100% train (77 core + 23 sci)
# опц: --all включает ml/web (torch ~2GB, для train не нужно)
python3 scripts/build_tools_images.py --list       # проверить статус
```
Каждый vsm-tools:<profile> содержит: goose, uv, get-pip.py, wheels для
**python 3.11 + 3.12 + 3.13** (task-образы разные). Overlay получает через
`COPY --from=vsm-tools:<profile>` — zero network в build.

**ВАЖНО:** дождаться полного завершения rebuild ПЕРЕД стартом батча (race-condition:
батч стартует со stale tools → первые задачи падают на yaml). Проверить:
`docker run --rm --entrypoint sh vsm-tools:core -c "ls /opt/wheels/ | grep -c cp312"`
должно быть ≥1.

### 3. Pre-pull base-images на host (до батча)
```bash
# Сканировать все task-Dockerfile'ы, pull отсутствующих на host:
python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'scripts')
from pathlib import Path
import subprocess
ds = Path('.cache/tb-dev-v2')
seen = set()
for d in sorted(p for p in ds.iterdir() if p.is_dir()):
    df = d/'environment'/'Dockerfile'
    if not df.exists(): continue
    base = next((l.split()[1] for l in df.read_text(errors='replace').splitlines()
                 if l.strip().upper().startswith('FROM ')), None)
    if base and base not in seen:
        seen.add(base)
        r = subprocess.run(['docker','image','inspect',base],capture_output=True)
        if r.returncode != 0:
            print(f'pull: {base}'); subprocess.run(['docker','pull',base])
        else: print(f'cached: {base}')
"
```
Без этого harbour-build падает на `FROM <image>` pull через ненадёжную сеть.

## Запуск батча

### Workers: 1 (безопасно) или 2 (компромисс)
**OOM-лимит WSL2 7.8GB RAM.** Каждый overlay-env-image ~1-1.5GB; 3 workers × build
+ containers = гарантированный OOM (умер на v4). Стратегия:
- **workers=1**: пик ~2-3GB, никогда не OOM. ~3мин/задача → 100 задач ≈ 5ч.
- **workers=2**: пик ~4-5GB, рискованно но swap (16GB) страхует. ~2.5ч.
- **workers=3+**: ОПАСНО на 7.8GB — только на более мощной машине.

### Команды
```bash
# Финальный прогон (детерминированный sample, воспроизводимо):
python3 -m eval --workers 1 run-all --sample 10 --seed 44

# Полный датасет (100 задач, ~5ч на workers=1):
python3 -m eval --workers 1 run-all

# Разные батчи (расширение выборки обучения):
python3 -m eval --workers 1 run-all --sample 15 --seed 45   # batch 2
python3 -m eval --workers 1 run-all --sample 15 --seed 46   # batch 3
```
**ВАЖНО:** `--workers N` — глобальная опция, идёт ДО подкоманды (`--workers 1 run-all`).

### Между прогонами: чистить docker cache
```bash
docker builder prune -f        # build cache растёт (47GB за сессию)
docker container prune -f      # мёртвые env-main контейнеры
docker system df               # мониторинг
```

## Что делает батч автоматически (не вмешиваться)

1. Каждый trial: `_prepare_overlay_task` → COPY --from=vsm-tools (offline) →
   product recovery cycle → verifier.
2. `mkdir /app` в overlay (VSM-036) — обеспечивает harbour default cwd.
3. WORKSPACE-probe в harbor_adapter (VSM-036) — product запускается в task's
   own WORKDIR (/app, /workdir, /workspace).
4. После батча: auto-cycle (run_cycle.py) — observe/decide/A(t)/cycle_count/render_data.

## Мониторинг во время батча

```bash
# прогресс + infra-аномалии:
grep -oE "\[[0-9]+/[0-9]+\]" state/logs/<batch>.log | tail -1
grep -rl "chdir to cwd.*failed" state/harbor-trials/*/agent/product-stdout.log | wc -l  # должно быть 0
grep -rl "No module named yaml" state/harbor-trials/*/agent/product-stdout.log | wc -l  # должно быть 0
docker ps --format "{{.Names}}" | grep -c env-main   # активные контейнеры
```

## Известные продуктовые паттерны (не infra — НЕ чинить)

- **VSM-034 empty-workspace surrender**: продукт делает `fs.list(".")+pytest` →
  стоп (2 tool_calls, no_observations). Системный продуктовый баг, не infra.
- **broken-python ложный PASS**: overlay чинит pip (get-pip bootstrap) → verifier
  проходит, но продукт не решал. Маска, не реальный успех.
- **AgentTimeoutError 360s**: продукт работал долго, не успел. Productive fail.
- **VerifierTimeoutError**: продукт task_resolved, но verifier тяжёлый/медленный.

## Коммит после батча

```bash
python3 scripts/run_cycle.py        # финальный cycle (observe aggregate)
python3 scripts/cycle_digest.py     # REPL-дайджест для S5
make validate                       # GREEN обязательно
git add state/ monitor/data.js meta/<analysis>.md
git commit -m "feat(eval): <batch> — <pass-rate>, <findings>"
```

## Чеклист «перед выходом на мощную машину»

- [ ] vsm-tools:core+sci built с cp311/312/313 wheels (`--list` проверка)
- [ ] Все base-images pre-pulled (скрипт выше)
- [ ] docker cache почищен (`builder prune`)
- [ ] workers=1 (или 2 если RAM > 16GB)
- [ ] `--sample N --seed S` для воспроизводимости
- [ ] Мониторинг: chdir=0, yaml=0, DNS=0 (infra устранена)
- [ ] `make validate` GREEN перед коммитом

## История фиксации (для контекста)
- VSM-034: продуктовый empty-workspace surrender (не чинить, продуктовая проблема)
- VSM-035: offline vsm-tools layer (снял DNS-build-fail для product-runtime deps)
- VSM-036: WORKDIR-probe + mkdir /app (снял chdir-fail для 48% датасета без /app)
- py312-wheels: 3-я builder stage в tools-image (ubuntu-apt=3.12, был только 3.11/3.13)
- python3-apt: restore `apt-get install python3` в offline overlay (ubuntu-base задачи)
