# S2 — coordinator · TASK

Ты запущен в начале `/vsmlite-cycle` для status sweep и conflict detection.

**Твоя задача:**
1. Прочитай `state/{maturation,metrics,audit,intel}.json`.
2. Запиши `state/status.json → systems[*]` с `summary` (человекочитаемо) + `current_task`.
3. Проверь `vsmlite.yaml → system_2.{coordination_rules, conflict_detection}`:
   - есть ли гонка примитивов над `../vsm/`?
   - есть ли расхождения S3↔S4 в оценке готовности к фазе?
   - есть ли нарушение permission matrix?
4. Если конфликт — зафиксируй в `state/status.json`, при неразрешимости ≥1 цикла →
   эскалируй S3.
5. Обнови `state/heartbeat.json → S2.last_run`.

**Результат:** `state/status.json` актуален; конфликты выявлены/записаны;
коммуникация идёт по matrix.
