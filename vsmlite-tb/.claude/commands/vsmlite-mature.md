---
description: Продвинуть дочерний VSM к следующей фазе OSM. Проверяет emergence-критерии, запрашивает решение человека (phase_transition), исполняет через child-dispatcher.
argument-hint: "[--to <Phase N> | (next)]"
allowed-tools: Read, Edit, Write, Bash, Agent
---

# /vsmlite-mature

Продвигает `../vsm/` к следующей фазе созревания (Phase N → N+1) по OSM.

## Контекст

1. [`CLAUDE.md`](../../CLAUDE.md) → `decisions_requiring_human: phase_transition`.
2. [`synthesis/phases.yaml`](../../synthesis/phases.yaml) → `<phase>.emergence_criteria_to_next`.
3. [`state/maturation.json`](../../state/maturation.json) — текущая фаза.

## Что делаешь

1. Определи текущую фазу (`state/maturation.json → maturation_state`).
2. Прочитай `synthesis/phases.yaml → <current>.emergence_criteria_to_next`.
3. Спавни `s3-optimizer` — проверь, все ли критерии выполнены (objective measure).
4. Спавни `s3-star-auditor` — structural audit: готова ли структура child к новой
   фазе (файлы системы существуют и непротиворечивы).
5. Если оба green:
   - `phase_transition` требует человека → спавни `s5-guardian` с
     `VSM-NNN signal_type: policy, primitive: phase-transition, phase_from, phase_to,
     needs_human_decision: true`. **Жди ответа юзера.**
   - После accept → спавни `child-dispatcher` с task: `phase-transition` →
     активирует следующую фазу (проявляет файлы системы, обновляет
     `state/maturation.json → phase_activated`).
6. Если не green — доложи ближайший блокер (из S3 или S3\*).
7. `python3 scripts/autonomy.py` → обнови A(t).
8. `python3 scripts/render_data.py`.

## Аргументы

- (нет) — следующая фаза по `phases.yaml`.
- `--to Phase 4` — конкретная цель (проверит, что это next, не skip).

## Главное

- Никогда не skip'ай фазы (OSM: progressive acquisition of viability).
- Никогда не реверси фазу без явного решения человека (`reverse_phase_without_human`).
- Не переводи без green от S3 И S3\*.
