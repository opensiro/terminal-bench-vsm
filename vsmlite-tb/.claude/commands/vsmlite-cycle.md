---
description: REPL-цикл созревания дочернего VSM. S2→S3→S3*→S4→S5: статус, A(t), аудит, разведка, дайджест решений для юзера. Юзер = инициатор: запускает, получает дайджест изменений, решает когда нужно.
argument-hint: "[--s2 | --s3 | --s4 | (full)]"
allowed-tools: Read, Edit, Write, Bash, Agent
---

# /vsmlite-cycle

Запускает цикл созревания `../vsm/`. По умолчанию — полный; с флагом — отдельная
фаза (для heartbeats / partial runs).

## Контекст (прочитай первым)

1. [`CLAUDE.md`](../../CLAUDE.md) — S5-конституция + главный инвариант.
2. [`vsmlite.yaml`](../../vsmlite.yaml) — модель.
3. [`state/maturation.json`](../../state/maturation.json) — текущая фаза, A(t).
4. [`systems/README.md`](../../systems/README.md) — permission matrix + карта цикла.
5. [`cycle`](../../systems/README.md#карта-цикла-что-делает-каждый) — фазы.

## Полный цикл (без аргумента)

```
┌─ S2 (s2-coordinator) ─── status sweep + conflict detection → state/status.json
│
├─ S3 (s3-optimizer) ───── A(t) + KPI + emergence-проверка → state/metrics.json
│   (параллельно с S4 где возможно)
├─ S4 (s4-scout) ──────── скан среды домена → state/intel.json
│
├─ S3* (s3-star-auditor) ─ независимый structural audit child → state/audit.json
│
└─ S5 (s5-guardian) ────── triage VSM-NNN + REPL-дайджест → ждёт ответ юзера
```

Каждая фаза — **отдельный субагент** (Agent tool). S3 ∥ S4 concurrently; S3\*
независимо; S5 — после остальных.

## Что делает оркестратор (ты)

Ты **только** спавнишь субагентов, читаешь `state/`, пишешь `issues/` +
`monitor/data.js`. **Не мутируешь** `../vsm/`, `../src/` (главный инвариант).

1. Прочитай `state/maturation.json` (maturation_state, A(t)).
2. Спавни `s2-coordinator` (status sweep).
3. Параллельно: `s3-optimizer` + `s4-scout`.
4. `s3-star-auditor` (cross-provider).
5. `s5-guardian` (triage + дайджест).
6. После S5 — `python3 scripts/render_data.py` (эмит `monitor/data.js`).
7. `scripts/validate.sh` — green.
8. Инкремент `state/maturation.json → cycle_count`.

## Дайджест S5 (центр UX)

S5 выводит в REPL:

```
## Цикл <N> — <date>
▸ Что изменилось: <delta с прошлого цикла>
▸ A(t): <val> (<trend>) | maturation: <Phase>
▸ Готов к фазе? <да/нет/блокер>
⚡ Критические: <VSM-NNN...> или «нет»
❓ Решения для тебя:
   • VSM-NNN: <policy_question>  [accept | defer | wontfix]
▸ Operational: S3 сделает X, synthesis-operator продолжит Y.
```

**Жди ответа юзера.** Не действуй без решения по `needs_human_decision: true`.

## Partial runs (аргументы)

- `--s2` — только S2 (status sweep).
- `--s3` — только S3 (A(t) + KPI).
- `--s4` — только S4 (скан среды; = `/vsmlite-scan`).
- (нет S3\* partial — он через `/vsmlite-check --audit`).

Partial не формирует REPL-дайджест (только обновляет `state/`).

## После цикла

- `monitor/data.js` актуален для forward-контракта vsmforge.
- Принятые юзером `VSM-NNN` (status: accepted) → synthesis-operator планирует
  primitive/phase → child-dispatcher исполняет (в следующем ходе или том же).
