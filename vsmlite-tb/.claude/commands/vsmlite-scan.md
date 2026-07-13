---
description: Только S4 — скан среды прикладного домена дочернего VSM. Weak signals, coverage gaps, drift, premises. = /vsmlite-cycle --s4, но как отдельная команда.
argument-hint: ""
allowed-tools: Read, Edit, Write, Agent
---

# /vsmlite-scan

Запускает только `s4-scout` (S4 vsmlite) — скан среды прикладного домена
дочернего VSM. Полезно между циклами, когда среда динамична.

## Что делаешь

1. Спавни `s4-scout` (см. [`systems/s4-scout/`](../../systems/s4-scout/)).
2. S4 читает `vsmlite.yaml → system_4.monitoring` + `../vsm/vsm.yaml → system_4`
   (tailored) + `../vsm/.intent.yaml`.
3. Скан: weak signals, coverage gaps, drift child-vs-seed, premises check.
4. Findings → `state/intel.json`.
5. Strategic shift → `VSM-NNN signal_type: gap` → S5 (но без полного cycle — просто
   запись; юзер увидит в следующем `/vsmlite-cycle`).
6. `python3 scripts/render_data.py` (обновить `intel[]` в телеметрии).

## Главное

- **S4 ≠ QA.** Не ищешь баги в коде дочернего VSM (это S3\*). Изучаешь
  эволюционную пригодность.
- Не мутируешь `../`.
- Не формируешь REPL-дайджест (это S5 в полном цикле). Только обновляешь `state/intel.json`.
