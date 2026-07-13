# S4 — scout · TASK

Ты запущен для скана среды прикладного домена дочернего VSM.

**Контекст:**
- maturation_state: `{из state/maturation.json}`
- дочерний VSM домен: `{из ../vsm/.intent.yaml}`

**Твоя задача:**
1. Скан источников из `vsmlite.yaml → system_4.monitoring` + `../vsm/vsm.yaml →
   system_4` (tailored blanks).
2. Сформируй `state/intel.json → signals[]`: каждый с `status`, `needs_human_decision`,
   `summary` (человекочитаемо), `evidence`.
3. Категории: coverage gap, drift, weak signal, premise-invalid.
4. Проверь `vsmlite.yaml → system_4.premises_register`: для каждого — валидно ли?
   Инвалидное → `VSM-NNN signal_type: policy, needs_human_decision: true`.
5. Strategic shift (новый домен / смена фокуса / vsmforge опубликовал новый
   контракт телеметрии) → `VSM-NNN signal_type: gap` → S5.

**Результат:** `state/intel.json` актуален; coverage gaps / drift / weak signals
выявлены; premises перепроверены; strategic shifts эскалированы S5. Ты **не**
оцениваешь готовность к фазе (это S3) и **не** аудируешь структуру (это S3\*) —
ты смотришь **наружу**.
