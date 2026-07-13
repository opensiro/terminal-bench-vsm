// monitor/assets/hints.js — описания метрик vsmlite-tb для тултипов.
// Адаптировано из opensiro-arctic под maturation/OSM-домен (не benchmarks/leaves).
"use strict";
window.VSM_HINTS = {
  // ── A(t) / maturation (главное для vsmlite) ──
  autonomy_score:  "A(t) ∈ [0,1] — автономность дочернего VSM (DEPENDENT → SEMI-AUTONOMOUS → AUTONOMOUS). Считается scripts/autonomy.py из 4 знаков.",
  maturation_phase:"Текущая фаза OSM: Initial State → Phase 0 (Intent) → Phase 1 (S1) → ... → Phase 6 (S5) → Autonomous. Phase N+1 — по emergence-критериям.",
  autonomy_verdict:"Вердикт A(t): DEPENDENT (0 знаков), SEMI-AUTONOMOUS (1–3 знака), AUTONOMOUS (все 4).",

  // ── 4 знака A(t) (forward-совместимо с vsmforge) ──
  s5_sign: "S5-sign ← issues[]: низкая доля открытых issues с needs_human_decision. Эскалаций < 0.5 → meets.",
  s4_sign: "S4-sign ← intel[]: есть self-closed сигналы (разведка закрывает сама). ≥1 → meets.",
  s3_sign: "S3-sign ← units[]: ≥2 operational units с низким pressure → meets.",
  s1_sign: "S1-sign ← activity[]: ≥3 активных git-дней в ../vsm/ → meets.",

  // ── KPI домена TB-2.1 (из ../vsm/vsm.yaml → system_3.kpi_list, tailored) ──
  coverage_ratio:       "coverage_ratio (домен TB): доля категорий задач Terminal Bench, по которым есть attempted прогоны.",
  pass_rate:            "pass_rate: доля решённых задач (по грейдеру) среди attempted.",
  trace_observability:  "trace_observability: доля прогонов с полной наблюдаемой трассой (для S3/S3*-анализа).",
  token_spend_per_task: "token_spend_per_task: медианные токен-затраты на задачу (efficiency).",
  skill_db_reuse_ratio: "skill_db_reuse_ratio: доля задач, где переиспользованы skills из benchmark-agnostic Skill DB.",
  validate_pass_rate:   "validate_pass_rate: /vsmlite-check проходит (invariant-grep + структура).",
  drift_score:          "drift_score: расхождение child vs seed/child/ (0 — нет дрейфа).",
  token_spend_estimate: "token_spend_estimate: оценка затрат токенов за цикл (часто неизмерима).",

  // ── Triple index (S3) ──
  triple_actuality:    "Actuality (S3): что есть сейчас — текущее покрытие категорий TB + pass_rate.",
  triple_capability:   "Capability (S3): что дочерний VSM способен сделать по фазе.",
  triple_potentiality: "Potentiality (S4): что могло бы быть — новые benchmark-agnostic skills расширяют capability.",

  // ── Баланс S3↔S4 (S5) ──
  balance_s3_share: "Доля S3 (control/optimization) в работе цикла.",
  balance_s4_share: "Доля S4 (intelligence) в работе цикла.",
  balance_status:   "Баланс S3↔S4: в tolerance, иначе drift-сигнал (одна сторона >75% активности 2 цикла).",

  // ── Счётчики ──
  open_issues:    "Открытые запросы корректировки VSM-NNN (не done/wontfix).",
  audit_findings: "Находки независимого аудита S3* (F-NNN).",
  intel_signals:  "Сигналы разведки S4 в state/intel.json.",
};
