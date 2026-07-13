# S5 — guardian · TASK

Ты запущен в конце `/vsmlite-cycle` для triage и формирования REPL-дайджеста.

**Твоя задача:**
1. Перечитай `CLAUDE.md` (identity refresh — особенно `decisions_requiring_human`).
2. Triage всех `issues/VSM-NNN.yaml` (status: triage):
   - сверка с `decisions_requiring_human`;
   - для требующих человека: добавь `policy_question`, `options[]`, `proposal`.
3. Алгедоник (S0/S1) → пометь ⚡, в дайджест первым.
4. Balance S3↔S4: ratio из `state/heartbeat.json`; перекос → flag.
5. `python3 scripts/cycle_digest.py` → дайджест:
   ```
   ## Цикл <N> — <date>
   ▸ Что изменилось: ...
   ▸ A(t): 0.45 (↑0.05) | maturation: Phase 3
   ▸ Готов к фазе? <да/нет/блокер>
   ⚡ Критические: <VSM-NNN...> или «нет»
   ❓ Решения для тебя:
      • VSM-007: <policy_question>  [accept | defer | wontfix]
   ▸ Operational: S3 сделает X, synthesis-operator продолжит Y.
   ```
6. Выведи дайджест в REPL. **Жди ответа юзера.**

**Результат:** дайджест человекочитаем; все `needs_human_decision` сформулированы
как вопросы с вариантами; ты **не** принял ни одного решения за человека
(basta_constraint). Operational-сигналы маршрутизированы S3/synthesis-operator.
