window.VSM_DATA = {
  "generated": "2026-07-13T23:57:40",
  "project": "vsmlite-template",
  "operational_mode": "normal",
  "systems": {
    "S1": {
      "name": "synthesis-operator",
      "summary": "",
      "current_task": "",
      "health": "unknown"
    },
    "S2": {
      "name": "s2-coordinator",
      "summary": "",
      "current_task": "",
      "health": "unknown"
    },
    "S3": {
      "name": "s3-optimizer",
      "summary": "",
      "current_task": "",
      "health": "unknown"
    },
    "S3*": {
      "name": "s3-star-auditor",
      "summary": "",
      "current_task": "",
      "health": "unknown"
    },
    "S4": {
      "name": "s4-scout",
      "summary": "",
      "current_task": "",
      "health": "unknown"
    },
    "S5": {
      "name": "s5-guardian",
      "summary": "",
      "current_task": "",
      "health": "unknown"
    }
  },
  "units": [],
  "metrics": {
    "autonomy_score": 0.1,
    "maturation_phase": "Phase 1",
    "coverage_ratio": 0.0,
    "validate_pass_rate": null,
    "drift_score": 0.0,
    "token_spend_estimate": 0,
    "triple_index": {
      "actuality": "",
      "capability": "",
      "potentiality": "",
      "measurement": ""
    },
    "balance_s3_s4": {
      "ratio": null,
      "status": "unknown",
      "alert": false
    },
    "s5_intervention_count": 0,
    "s5_intervention_cycles": 0,
    "intervention_share": 0.0
  },
  "maturation": {
    "state": "Phase 1",
    "phase_activated": [
      "S1"
    ],
    "autonomy_verdict": "DEPENDENT",
    "autonomy_target": 1.0,
    "autonomy_signs": {
      "s5_sign": {
        "value": null,
        "from": "issues",
        "meets": false
      },
      "s4_sign": {
        "value": null,
        "from": "intel",
        "meets": false
      },
      "s3_sign": {
        "value": null,
        "from": "units",
        "meets": false
      },
      "s1_sign": {
        "value": null,
        "from": "activity",
        "meets": false
      }
    },
    "last_primitive": "Create",
    "last_transition": "Initial State → Phase 1",
    "child_initialized": true,
    "child_path": "../vsm",
    "cycle_count": 0,
    "updated": "2026-07-13"
  },
  "audit": [],
  "audit_caveats": [],
  "intel": [],
  "intel_coverage": {
    "domain_environment": [],
    "vsmforge_roadmap": [],
    "osm_evolution": []
  },
  "heartbeat": {
    "S2": {
      "cadence": "on_demand",
      "last_run": null
    },
    "S3": {
      "cadence": "on_demand",
      "last_run": null
    },
    "S3*": {
      "cadence": "on_demand",
      "last_run": null
    },
    "S4": {
      "cadence": "on_demand",
      "last_run": null
    },
    "S5": {
      "cadence": "on_demand",
      "last_run": null
    }
  },
  "issues": [
    {
      "id": "VSM-001",
      "source_system": "S5",
      "signal_type": "policy",
      "severity": "S2",
      "target_unit": "child",
      "title": "Runtime membrane: solver/S2-S4 blind to benchmark identity; S4 internet + transduction",
      "summary": "Два архитектурных решения от человека (сессия init Terminal Bench 2.1):\n(1) Полная изоляция рантайма — знание «это Terminal Bench» остаётся только в\ndesign-time/S5-слое (.intent.yaml, vsm.yaml identity, CLAUDE.md, VSM-NNN).\nРешающий агент (S1-solver) и runtime-функции S2–S4 работают benchmark-agnostic:\nсолвер получает задачи как generic agentic tasks, TB-фрейминг снимается на\nтранедукционной границе VSM. Это blinded-eval инвариант: мера качества честна,\nпока решающий агент не знает, что его оценивают.\n(2) S4-scout получает открытый доступ в интернет в runtime для поиска\nbenchmark-agnostic Skill DB (scope unchanged, never_do unchanged). Всё, что S4\nнаходит, проходит через мембрану — очистка от любых TB-следов — перед\nсохранением в Skill DB и передачей в рантайм.\n",
      "evidence": [
        "../vsm/.intent.yaml → runtime_membrane (design-time truth)",
        "../vsm/vsm.yaml → identity.never_do: runtime_aware_of_benchmark",
        "../vsm/vsm.yaml → identity.runtime_membrane",
        "../vsm/vsm.yaml → system_4.runtime_internet_access",
        "../vsm/systems/s4-scout/{SOUL,SKILL}.md",
        "../vsm/CLAUDE.md → Identity + NEVER DO"
      ],
      "proposal": "Зафиксировать runtime membrane как архитектурный инвариант дочернего VSM и\nрасширить capability S4 интернет-доступом с обязательной трансдукцией.\nDesign-time/S5 сохраняет знание о TB для coverage/pass_rate/grading; runtime\n(S1-solver + S2–S4 в их runtime-функциях) — benchmark-agnostic.\n",
      "acceptance": [
        "../vsm/vsm.yaml → identity.never_do содержит runtime_aware_of_benchmark",
        "../vsm/vsm.yaml → identity.runtime_membrane секция описывает границу design-time/runtime",
        "../vsm/vsm.yaml → system_4.runtime_internet_access: open + transduction_via_membrane",
        "../vsm/.intent.yaml → runtime_membrane секция зафиксирована",
        "../vsm/systems/s4-scout/{SOUL,SKILL}.md описывают интернет + мембрану",
        "../vsm/CLAUDE.md NEVER DO включает runtime_aware_of_benchmark"
      ],
      "needs_human_decision": true,
      "policy_question": "Зафиксировать runtime membrane (полная изоляция рантайма) + открытый интернет S4 с трансдукцией через мембрану как архитектурные инварианты дочернего VSM?\n",
      "options": [
        {
          "id": "accept",
          "label": "Принять оба решения",
          "hint": "Полная изоляция рантайма + S4 интернет с трансдукцией (Recommended)"
        },
        {
          "id": "relax",
          "label": "Ослабить: контроль-плейн знает",
          "hint": "S2-S4 runtime знают, но солвер нет — менее строго"
        },
        {
          "id": "defer",
          "label": "Отложить",
          "hint": "Оставить как есть, вернуться позже"
        }
      ],
      "status": "accepted",
      "decision": "accept — оба решения утверждены человеком в init-сессии (полная изоляция рантайма + S4 открытый интернет с трансдукцией через мембрану)",
      "selected_options": [
        "accept"
      ],
      "created": "2026-07-13",
      "updated": "2026-07-13"
    },
    {
      "id": "VSM-002",
      "source_system": "S5",
      "signal_type": "policy",
      "severity": "S1",
      "target_unit": "child",
      "title": "Продукт = benchmark-agnostic failure-aware coding harness; TB уезжает в родитель-оценщик",
      "summary": "Концептуальный поворот, зафиксированный в сессии после обсуждения архитектуры\n«VSM ↔ harness ↔ солвер». Истинный продукт проекта — НЕ «VSM, решающий Terminal\nBench». Истинный продукт = failure-aware coding harness для long-horizon\nагентов (с failure taxonomy → recovery policy → retry как первичной онтологией).\nTerminal Bench — калибровочный стенд (один из возможных: мог быть SWE-bench или\nреальный поток тикетов), живёт ТОЛЬКО в родительском vsmlite-tb (оценщик) +\nкорневой README. Продукт (vsm/ + src/) полностью benchmark-agnostic — не знает\nо TB ни в design-time, ни в runtime, ни в S5. Мембрана VSM-001 переформулируется:\nраньше была design-time/runtime внутри продукта, теперь — граница\nproduct↔evaluation (родитель↔дочерний).\n\nДополнительное решение: failure-aware runtime (Failure Classifier → Recovery\nPolicy → Retry) — первичная онтология в src/, benchmark-agnostic по природе.\nКлассы сбоев: ToolNotFound→InstallTool, DependencyConflict→CreateFreshVenv,\nGitConflict→ResetAndReplay, и т.д. Ложится на VSM: S1 выполняет действия, S2\nкоординирует восстановление (anti-repetition одинаковых неудач), S3 классифицирует\nсбои и выбирает политику восстановления, S3* аудирует recovery, S4 ищет coding\npatterns / новые recovery policies.\n",
      "evidence": [
        "сессия 2026-07-13: обсуждение «VSM ↔ TB harness ↔ солвер», выбран вариант 2 (VSM=harness)",
        "решение: продукт полностью benchmark-agnostic (S5 тоже), blind даже к факту оценки",
        "архитектура: VSM сам и есть harness; солвер = S1; harness-функции = S2/S3-слой",
        "src/ роли: failure taxonomy (первичная онтология), кэш прогонов, skill DB, session sync",
        "KPI продукта: recovery rate / retry efficiency / policy effectiveness (НЕ pass_rate по TB)",
        "VSM-001 переформулируется: мембрана = product↔evaluation, не design-time/runtime",
        "история: новые коммиты поверх (видимая эволюция, remote нет)"
      ],
      "proposal": "Рефакторинг продукта (vsm/ + src/) в полностью benchmark-agnostic форму:\n(1) vsm.yaml → name/purpose/mission = coding harness; KPI = recovery/retry/policy;\n    never_do = product-level (убрать train_on_eval/harbor_tb2/change_target_tb_version);\n    system_1 = солвер (не harness); удалить runtime_membrane из identity продукта.\n(2) .intent.yaml → миссия = coding harness; TB упоминается только в parent: vsmlite-tb.\n(3) CLAUDE.md → S5-конституция продукта, agnostic.\n(4) systems/{s2,s3,s4} SOUL/SKILL → failure-aware roles.\n(5) src/README.md + src/failure_taxonomy.yaml — skeleton первичной онтологии.\n(6) vsm/state/* дочернего — вычистить TB-маркеры.\nРодитель vsmlite-tb/vsmlite.yaml → identity оценщика продукта.\nКорневой README → обновить картинку product↔evaluator.\n",
      "acceptance": [
        "ни одного упоминания Terminal Bench/TB/benchmark/бенчмарк/harbor в vsm/ и src/",
        "vsm/vsm.yaml → name ≠ Terminal Bench; purpose = coding harness (не решение TB)",
        "vsm/vsm.yaml → system_3.kpi_list = recovery/retry/policy KPI (НЕ pass_rate по TB)",
        "vsm/vsm.yaml → identity.never_do НЕ содержит train_on_eval/harbor_tb2/change_target_tb_version",
        "vsm/vsm.yaml → identity.runtime_membrane удалена (мембрана уезжает на границу parent↔child)",
        "vsm/.intent.yaml → mission = coding harness; 'Terminal Bench' встречается только в parent-комментарии",
        "vsm/CLAUDE.md — S5 agnostic, не упоминает TB как домен",
        "vsm/systems/s4-scout/{SOUL,SKILL}.md — S4 scope = coding patterns/recovery policies (не benchmark-agnostic Skill DB)",
        "src/failure_taxonomy.yaml существует, содержит skeleton классов сбоев + recovery policies",
        "vsmlite-tb/vsmlite.yaml → identity purpose явно: оценить coding-harness продукт через TB",
        "validate.sh GREEN"
      ],
      "needs_human_decision": true,
      "policy_question": "Рефакторинг продукта (vsm/ + src/) в полностью benchmark-agnostic failure-aware coding harness, TB уезжает только в родитель-оценщик?\n",
      "options": [
        {
          "id": "accept",
          "label": "Принять рефакторинг",
          "hint": "Полный benchmark-agnostic продукт + failure taxonomy (Recommended)"
        },
        {
          "id": "partial",
          "label": "Частично",
          "hint": "Только identity/mission, без failure taxonomy сейчас"
        },
        {
          "id": "defer",
          "label": "Отложить",
          "hint": "Оставить как есть, вернуться позже"
        }
      ],
      "status": "accepted",
      "decision": "accept — полный рефакторинг продукта в benchmark-agnostic failure-aware coding harness; история: новые коммиты поверх",
      "selected_options": [
        "accept"
      ],
      "created": "2026-07-13",
      "updated": "2026-07-13"
    },
    {
      "id": "VSM-003",
      "source_system": "S5",
      "signal_type": "policy",
      "severity": "S2",
      "target_unit": "child",
      "title": "S1 retry feedback-channel: спектр R0/R1/R2, R1 baseline, launch-time argument от человека",
      "summary": "Архитектурное решение для S1-контракта продукта (workstream T2), зафиксированное\nв сессии. Решило открытый вопрос «stateful-vs-stateless retry» (WORKSTREAM.md:188)\nчерез рефрейминг: состояние окружения и память S1 о прошлой попытке — две РАЗНЫЕ\nоси, и retry характеризуется только второй.\n\nОСЬ 1 — State axis (env, fs, git): управляется recovery policy ВНЕ S1. InstallTool\nустановил пакет, ResetAndReplay откатил git — это делает recovery executor (T3),\nне солвер. В этом смысле retry всегда «stateful» на уровне environment, но это\nне дело S1.\n\nОСЬ 2 — Memory axis (что S1 знает о прошлой попытке): ЭТО И ЕСТЬ R0/R1/R2.\nS1 как агент стартует fresh-per-invocation; режим определяет, какая часть\nпрошлой попытки доносится в input как `prior_attempt`. Спектр:\n\n  R0 — Blind:              prior_attempt = null. S1 не знает, что это retry.\n                            Use case: env-recovery (InstallTool, CreateFreshVenv).\n  R1 — Feedback-agnostic:  prior_attempt = {failure_class, cost, explored_paths[]}.\n                            Базовый режим. S1 знает класс прошлой ошибки и\n                            исследованные paths, но НЕ trace/artifacts.\n  R2 — Feedback-aware:     prior_attempt = {full_trace, verdict, artifacts_diff,\n                            failure_observations}. S1 видит всю прошлую попытку.\n                            Use case: long-horizon, GitConflict replay.\n\nРешения (зафиксированы человеком в сессии):\n(1) R1 — baseline/дефолт, когда recovery directive не указывает явно.\n(2) Режим выбирает ЧЕЛОВЕК при запуске harness как launch-time argument. Это\n    НЕ решение S3 (T3) и НЕ атрибут failure class (T1 taxonomy) — режим глобален\n    для всех invocations одного harness-run.\n(3) Один режим на retry: никаких progressive disclosure (R0→R1→R2 по попыткам).\n    Проще аудит (S3* видит один режим + одну policy на retry).\n(4) Feedback во всех режимах — product-internal (failure class, cost, paths,\n    trace). Никогда не benchmark-level. Сохраняет never_do: optimize_for_specific_evaluator.\n\nЛожится на VSM-архитектуру: S3-classifier (T3) получает failure_observations\nиз output S1; S2-coordinator координирует retry; S3 выбирает recovery policy;\nrecovery executor меняет environment; s1-dispatcher (T2 CONTRACT) запускает S1\nснова с prior_attempt согласно feedback_mode.\n",
      "evidence": [
        "сессия 2026-07-13: workstream T2, вопрос stateful-vs-stateless retry",
        "рефрейминг: разделение на state-axis (env, вне S1) и memory-axis (R0/R1/R2, input S1)",
        "решение человека: режим = launch-time argument, R1 дефолт, один режим на retry",
        "обоснование R1 как baseline: баланс general-purpose discipline и эффективности; недостаточно контекста для overfit, достаточно чтобы не повторять ошибку",
        "инвариант сохранён: feedback product-internal, не нарушает optimize_for_specific_evaluator"
      ],
      "proposal": "Зафиксировать R0/R1/R2 как retry feedback-channel в S1-контракте продукта:\n(1) vsm/systems/s1-dispatcher/CONTRACT.md → разделы \"Input contract\" (feedback_mode)\n    и \"Feedback modes\" (R0/R1/R2 спецификация).\n(2) prior_attempt формат определён per-mode в CONTRACT.\n(3) failure_observations формат (что S3 парсит) — mode-agnostic, всегда полный\n    в output (S3 всегда видит всё для классификации; режим ограничивает только\n    что доносится НАЗАД в S1 при retry).\n(4) vsmlite-tb/vsmlite.yaml → runtime_policy.child_mutation_scope: init_only →\n    workstream (T2 = tailor: s1_design формально вне init; расширение по VSM-003).\n",
      "acceptance": [
        "CONTRACT.md (T2) содержит раздел Feedback modes с R0/R1/R2 спецификацией",
        "CONTRACT.md явно фиксирует R1 как baseline и launch-time argument как механизм выбора",
        "CONTRACT.md явно фиксирует один режим на retry (no progressive disclosure)",
        "runtime_policy.child_mutation_scope = workstream в vsmlite.yaml",
        "validate.sh GREEN",
        "ни одного упоминания Terminal Bench/benchmark/eval в vsm/ и src/"
      ],
      "needs_human_decision": false,
      "policy_question": "Зафиксировать R0/R1/R2 как retry feedback-channel спектр (R1 baseline, launch-time argument, один режим на retry) в S1-контракте продукта?\n",
      "options": [
        {
          "id": "r1_baseline",
          "label": "R1 как baseline + R0/R1/R2 спектр",
          "hint": "Balanced default; режим = launch-аргумент человека; один режим на retry (Recommended)"
        },
        {
          "id": "r0_strict",
          "label": "R0 (Blind) как baseline",
          "hint": "Максимум general-purpose чистоты; дороже на long-horizon"
        },
        {
          "id": "r2_full",
          "label": "R2 (Feedback-aware) как baseline",
          "hint": "Максимум эффективности; больше поверхность для product-internal overfit"
        }
      ],
      "status": "superseded",
      "decision": "superseded — человек передумал в той же сессии: R0/R1/R2 вычищены из s1-dispatcher; stateful-vs-stateless решён как S1 stateless (fresh-per-invocation), retry доносит только recovery_directive. VSM-003 остаётся в истории (monotonic id).",
      "selected_options": [],
      "superseded_by": "VSM-004 (pending) — простой stateless retry вместо R0/R1/R2 спектра",
      "superseded_reason": "Человек передумал: не усложнять. R0/R1/R2 спектр вычищен из s1-dispatcher\n(5 файлов переписаны). Вместо режимов — простое решение: S1 stateless,\nfresh-per-invocation; retry доносит только recovery_directive (какой класс\nожидается, что изменилось в env). T2-контракт сохранён (input/output/lifecycle,\nfailure_observations format). VSM-003 accepted→superseded в той же сессии.\n",
      "created": "2026-07-13",
      "updated": "2026-07-13"
    },
    {
      "id": "VSM-004",
      "source_system": "S5",
      "signal_type": "policy",
      "severity": "S1",
      "target_unit": "meta",
      "title": "Dev Set как метрика автономности + general-purpose self-modification продукта (не training)",
      "summary": "Концептуальный поворот от человека (сессия 2026-07-13, после отката R0/R1/R2).\nПереформулировка того, КАК vsmlite выращивает продукт до автономии.\n\nКЛЮЧЕВОЕ РАЗЛИЧЕНИЕ (от человека): «продукт не тренируют, его СТРОЯТ до\nавтономности с учётом метрики проходимости этого dev-бенча». Это синтез (OSM),\nне ML-тренировка.\n\nИдея: vsmlite (родитель, знает про Terminal Bench) использует Terminal-Bench Dev\nSet v2 как ИНДИКАТОР роста автономности A(t) продукта. Dev Set задачи подаются\nв продукт как generic coding tasks (мембрана снимает TB-фрейминг). Продукт\nразвивает general-purpose self-adaptation (новые recovery policies, skill DB\nentries, структурные изменения через OSM-примитивы), НЕ зная про TB. Затем\nпродукт слепо оценивается на Eval Set.\n\nSelf-modification продукта — это OSM-синтез (vsmlite применяет примитивы\nSplit/Merge/Reconfigure через child-dispatcher на основе метрик), НЕ\nweight-update / fine-tuning. Продукт «изменяет себя» в том смысле, что его\nструктура (taxonomy, skill DB, system definitions) эволюционирует — но\nизменяет её vsmlite как оператор синтеза, на основе general-purpose метрик\nпродукта + pass-метрики Dev Set (которую видит только родитель).\n\nКонтраст с тем что было: раньше vsmlite выращивал продукт «в общем» (OSM-фазы\nпо emergence-критериям). Теперь emergence-критерии ДОПОЛНЯЮТСЯ pass-метрикой\nDev Set как внешним индикатором: «продукт достаточно автономен, когда\nсправляется с Dev Set без вмешательства». Это не меняет never_do — напротив,\nуточняет границу product↔evaluation.\n",
      "evidence": [
        "сессия 2026-07-13: человек — «продукт не тренируют, его строят до автономности с учетом метрики проходимости dev-бенча»",
        "контраст: R0/R1/R2 откатаны (VSM-003 superseded) — не усложнять; self-modification = OSM-синтез, не режимы retry",
        "vsmlite.yaml → identity.product_evaluation: product_knows=false, membrane на стороне родителя — сохраняется",
        "vsm/vsm.yaml → never_do: optimize_for_specific_evaluator — продукт не знает про TB, адаптация general-purpose",
        "vsmlite.yaml → never_do: train_on_eval — НЕТ ML-тренировки на eval-разметке; pass-метрика = индикатор для OSM, не gradient",
        "OSM §7: vsmlite = dedicated operational unit parent, mission = organizational synthesis — self-modification продукта = синтез"
      ],
      "proposal": "Зафиксировать концептуальный поворот как уточнение роли vsmlite + membrane:\n\n(1) Dev Set = индикатор автономности (НЕ training data). vsmlite подаёт Dev Set\n    задачи в продукт как generic coding tasks (мембрана). Pass-метрика Dev Set\n    видна ТОЛЬКО родителю; продукт её не видит. vsmlite использует pass-метрику\n    как один из emergence-сигналов для OSM-синтеза (наряду с A(t), 4 знаками).\n\n(2) Self-modification продукта = OSM-синтез (НЕ training/fine-tuning). vsmlite\n    применяет примитивы Split/Merge/Reconfigure к дочернему VSM через\n    child-dispatcher, когда метрики (включая Dev Set pass-rate) показывают что\n    текущая структура недостаточна. Продукт «изменяет себя» в смысле эволюции\n    своей структуры (taxonomy, skill DB, system definitions), но изменяет её\n    vsmlite — продукт не модифицирует собственную identity сам (basta:\n    identity/values change — решение человека).\n\n(3) Разделение Dev Set / Eval Set. Dev Set = для развития (vsmlite видит\n    pass-метрику, итеративно синтезирует). Eval Set = для финальной слепой\n    оценки (продукт никогда не видел, vsmlite не использует для синтеза —\n    только для вердикта готовности). Оба живут в родителе; продукт не знает\n    ни про один.\n\n(4) Инварианты СОХРАНЯЮТСЯ (не нарушаются):\n    - train_on_eval: НЕТ — нет ML-тренировки; pass-метрика = сигнал для OSM.\n    - optimize_for_specific_evaluator: НЕТ — продукт не знает про TB;\n      адаптация general-purpose (recovery policies применимы к любым tasks).\n    - leak_evaluation_context_to_product: НЕТ — мембрана транслирует;\n      продукт видит generic coding tasks.\n    - blinded_evaluation: сохраняется — Eval Set слепой; Dev Set не протекает\n      в product identity.\n\n(5) Метрика Dev Set — ВНУТРЕННЯЯ для vsmlite, не протекает в продукт. Продукт\n    продолжает измерять свои product KPI (recovery_rate, retry_efficiency,\n    policy_effectiveness — из vsm/vsm.yaml system_3.kpi_list). Dev Set\n    pass-rate — метрика РОДИТЕЛЯ, живёт в vsmlite-tb/state/ + telemetry.\n",
      "acceptance": [
        "vsmlite.yaml → identity.product_evaluation дополнена: dev_set role = autonomy indicator (не training data), eval_set = blind final",
        "vsmlite.yaml → never_do: train_on_eval формулировка уточнена — «ML-тренировка на eval-разметке запрещена; pass-метрика Dev Set = сигнал для OSM-синтеза, не gradient»",
        "vsm/vsm.yaml — БЕЗ ИЗМЕНЕНИЙ (продукт не знает про Dev Set / Eval Set / TB)",
        "src/failure_taxonomy.yaml — БЕЗ ИЗМЕНЕНИЙ (taxonomy general-purpose, не привязана к Dev Set)",
        "ни одного упоминания Terminal Bench / benchmark / eval в vsm/ и src/ (сохраняется)",
        "validate.sh GREEN",
        "vsmlite-tb/state/ — метрика Dev Set pass-rate живёт здесь (не в product state/)"
      ],
      "needs_human_decision": true,
      "policy_question": "Зафиксировать концептуальный поворот: Terminal-Bench Dev Set v2 = индикатор автономности (не training data), self-modification продукта = OSM-синтез через vsmlite (не fine-tuning), при сохранении всех never_do и мембраны?\n",
      "options": [
        {
          "id": "accept",
          "label": "Принять поворот",
          "hint": "Dev Set = autonomy indicator, self-modification = OSM-синтез, never_do сохранены (Recommended)"
        },
        {
          "id": "partial",
          "label": "Только Dev Set role",
          "hint": "Зафиксировать Dev Set как индикатор, self-modification оставить как есть (общий OSM)"
        },
        {
          "id": "defer",
          "label": "Отложить",
          "hint": "Вернуться к концепции позже; сейчас продолжить workstream T1-T5 как есть"
        }
      ],
      "status": "superseded",
      "decision": "superseded — Dev Set pass-rate вошёл в VSM-005 как ВХОДНОЙ индикатор автономности (в паре с S5 intervention count как ОБРАТНЫЙ). VSM-005 переформулирует: S5 = архитектор (не divine will), intervention metric = публичный индикатор в dashboard. VSM-004 остаётся в истории (monotonic id).",
      "selected_options": [],
      "superseded_by": "VSM-005 — S5 архитектор + intervention metric (объединяет Dev Set pass-rate как входной индикатор + S5 intervention как обратный)",
      "superseded_reason": "Человек переформулировал в той же сессии. VSM-004 ставил Dev Set pass-rate\nкак индикатор автономности + self-modification = OSM-синтез. VSM-005\nсохраняет обе идеи, но переформулирует: S5 = архитектор (вмешивается при\nалгедонике), intervention metric = обратный индикатор (чем меньше S5\nвмешивается, тем автономнее). Dev Set pass-rate = входной индикатор.\nВместе (pass-rate ↑ + interventions ↓) = автономность растёт. VSM-004\nsuperseded, его содержание вошло в VSM-005.\n",
      "notes": [
        "Это prepare_only (basta_constraint: prepare_only) — человек постановляет.",
        "VSM-003 (R0/R1/R2) superseded в той же сессии; VSM-004 — следующее концептуальное решение (monotonic id).",
        "Если accept: vsmlite-tb/vsmlite.yaml правится (identity.product_evaluation + never_do формулировка); vsm/ и src/ НЕ трогаются.",
        "Открытый подвопрос (для человека): где физически живёт Dev Set pass-rate метрика — vsmlite-tb/state/dev_metrics.json? Решается при имплементации."
      ],
      "created": "2026-07-13",
      "updated": "2026-07-13"
    },
    {
      "id": "VSM-005",
      "source_system": "S5",
      "signal_type": "policy",
      "severity": "S1",
      "target_unit": "meta",
      "title": "S5 = architect (intervenes on algedonic only) + intervention metric + parent isolation + env-type awareness + MCP restriction + uncertainty handling (S2/S3/S3*/S4)",
      "summary": "Концептуальный поворот (сессия 2026-07-13), развивающий VSM-001/VSM-002.\nЗаменяет ранее предложенный в этой же сессии «divine will» framing (откатан,\nне применялся к файлам) и объединяет VSM-004 (Dev Set pass-rate как индикатор\nавтономности) — VSM-004 superseded, вошёл сюда. Дополнения от человека:\nparent isolation (vsm/ не знает про vsmlite-tb) + S3* в uncertainty handling.\n\n─────────────────────────────────────────────────────────────────────────\n(1) S5 = АРХИТЕКТОР (не divine will, не routine director)\n─────────────────────────────────────────────────────────────────────────\nS5 родительского vsmlite — структурный архитектор VSM, не «направляющая воля».\nРутинно НЕ вмешивается: S1-S4 работают автономно в своих горизонтах. S5\nвмешивается ТОЛЬКО когда алгедонический канал сигнализирует, что S3 (control),\nS3* (audit) или S4 (intelligence) не справляются самостоятельно.\n\nВмешательство S5 = структурное изменение VSM на ходу (OSM-примитивы:\nSplit/Merge/Reconfigure; изменение system definitions; перераспределение\nbudget). НЕ микроуправление операциями S1, НЕ указание «какую recovery policy\nвыбрать» — это S3. S5 меняет СТРУКТУРУ, когда routine control/audit/\nintelligence не могут погасить проблему.\n\nКаждое вмешательство S5 = +1 к intervention metric (см. §2) = сигнал что VSM\nещё недостаточно автономен. Цель VSM = минимизировать вмешательства S5.\nРост A(t) = уменьшение частоты S5-вмешательств.\n\nАлгедонический канал — триггер S5:\n- S3 → не справляется с отклонением (deviation beyond threshold, не погасилось).\n- S3* → нашёл структурный брак (viability breach).\n- S4 → стратегический gap, не закрытый разведкой.\nЛюбой → S5 как архитектор оценивает и применяет структурное изменение.\n\n─────────────────────────────────────────────────────────────────────────\n(2) INTERVENTION METRIC + PARENT ISOLATION\n─────────────────────────────────────────────────────────────────────────\n«Вмешательство» = случаи когда автономии VSM не хватило и потребовалось\nвмешательство S5 (архитектора). Чем больше вмешательств — тем менее\nжизнеспособен VSM в автономии.\n\nScope metric (решение человека): только S5-вмешательства. Человек (basta-\nрешения) — отдельная категория, НЕ intervention metric (человек по определению\nвне автономии VSM; basta = области где VSM не должен решать сам).\n\nMetric показывается на публику через vsmlite dashboards (monitor/data.js,\ntelemetry для vsmforge) — НЕ через S5. S5 не «владеет» метрикой, он источник\nодного из потоков. Публика видит: A(t), pass-rate (Dev Set), intervention\ncount — вместе дают картину автономности.\n\nОбъединение с VSM-004: pass-rate Dev Set растёт + S5 interventions падают =\nавтономность растёт. Две стороны одной медали:\n- pass-rate (Dev Set) — ВХОДНОЙ индикатор (продукт справляется с задачами).\n- intervention count — ОБРАТНЫЙ индикатор (продукт не нуждается во внешнем).\n\nPARENT ISOLATION (дополнение от человека):\nЦепочка взаимодействия: human → vsmlite → vsm. VSM НЕ знает, что vsmlite\nс ним работает — параллель с eval-blindness (продукт не знает, что его\nоценивают; продукт не знает, что его растит родитель). S5 (в vsmlite)\nвмешивается в vsm, но vsm переживает это как внутреннее изменение, не как\n«родитель вмешался».\n\nСтруктурная изоляция (folder-level, design-time):\n- `vsm/` и `src/` НЕ ссылаются на `../../vsmlite-tb/` (родитель) — ни в путях,\n  ни в конфигах, ни в README. VSM не имеет структурного пути к родителю.\n- Intervention metric живёт в `vsmlite-tb/state/` (родитель), НЕ в\n  `vsm/state/` (продукт). VSM не видит intervention count — не знает про\n  вмешательства в себя.\n- Параллель с MCP restriction (§4): мембрана = отсутствие пути, не фильтр.\n  Как S1 не имеет eval-access tool, так vsm/ не имеет пути к родителю.\n- S5 вмешивается через child-dispatcher (единственный boundary), который\n  пишет в `vsm/` — но для vsm это выглядит как локальная мутация, не как\n  внешний акт. VSM не различает «своё изменение» и «вмешательство S5».\n\nПроверяется (validate.sh expansion): grep по `vsm/` и `src/` на упоминания\n`../../vsmlite` или `vsmlite-tb` (кроме README продукта, где есть одна\nструктурная ссылка на родителя как на директорию — она легитимна для\nнавигации, но не раскрывает роль vsmlite как оператора).\n\n─────────────────────────────────────────────────────────────────────────\n(3) ENVIRONMENT-TYPE AWARENESS (S5 знает уровень, не конкретику)\n─────────────────────────────────────────────────────────────────────────\nS5 (архитектор) знает о существовании типов сред, в которых работает VSM:\n  Environment types:\n    - Production     — реальная эксплуатация\n    - Simulation     — симуляция\n    - Benchmark      — оценочная среда\n    - Sandbox        — изолированная пробная среда\n    - Training       — среда развития/обучения (не ML; OSM-синтез)\n\nS5 знает, что этот VSM используется в т.ч. для Benchmark environment. Но S5\nНЕ знает конкретики: не «Terminal Bench 2.1», не «harbor-framework», не\n«SWE-bench». S5 знает только: «есть специальный тип среды — Benchmark —\nпродукт в ней оценивается». Это структурное знание архитектора (нужно для\nпроектирования: продукт не должен optimise под Benchmark), не eval-context\n(конкретный бенчмарк, задачи, разметка).\n\nСистемы ниже S5 (S1-S4 родителя + дочерний VSM) — НЕ знают даже про\nenvironment types. Для них есть только generic coding tasks (мембрана снимает\nframing). S5 — единственный, кто знает про env-type categorisation.\n\nПрактическое следствие:\n- S5 при проектировании гарантирует: product never_do `optimize_for_specific\n  _evaluator` структурно обеспечен (продукт не знает про Benchmark env-type).\n- Конкретный бенчмарк (TB 2.1) — знание ТОЛЬКО человека + vsmlite.yaml\n  identity (не S5-агент, а модель). S5-агент знает «Benchmark env-type\n  существует», не «Terminal Bench».\n\n─────────────────────────────────────────────────────────────────────────\n(4) MCP ACCESS RESTRICTION (structural, для T4) — сохранено из draft\n─────────────────────────────────────────────────────────────────────────\nMCP tools-server (T4) продукта структурно НЕ предоставляет доступ к eval-\nresources. Продукт не знает о restriction: tool surface просто не включает\neval-access. Это не runtime-policy (которую можно обойти), а design-time\nструктурное ограничение tool surface. S1 не может обратиться к eval-данным,\nпотому что такого tool нет в MCP-сервере. Мембрана = отсутствие инструмента,\nне фильтр.\n\n─────────────────────────────────────────────────────────────────────────\n(5) UNCERTAINTY HANDLING — S2/S3/S3*/S4 (продукт) — сохранено из draft\n─────────────────────────────────────────────────────────────────────────\nS4 продукта расширяет knowledge (coding patterns, recovery techniques) когда\nесть НЕУВЕРЕННОСТЬ в решаемости поданной задачи. Не по расписанию, а по\nтриггеру: «задача выглядит непривычно / нет готового pattern / high failure-\nrisk». S4 ищет расширения именно для этого случая. Уточняет role S4: не\nтолько ambient scan, но и demand-driven knowledge expansion при неуверенности.\n\nS2 (продукт): при неуверенности проводит эксперименты (probing) — маленькие\nизолированные пробы, чтобы уточнить характер задачи. Не полноценный solve,\nа reconnaissance.\nS3 (продукт): на основе S2-experiments + S4-findings проводит оптимизации\n(перераспределение ресурсов, выбор policy, структурные сигналы через OSM).\n\nS3* (продукт, независимый аудит) — НЕ rubber-stamp S2/S3/S4 response на\nнеуверенность. S3* независимо проверяет:\n- жизнеспособность выбранной реакции (достаточен ли S2-probing? не избыточен\n  ли? S3-optimization обоснован или premature? S4-expansion релевантен?);\n- не является ли «неуверенность» симптомом структурного брака (напр.\n  classifier даёт Unknown слишком часто — это не «неуверенность», это\n  taxonomy gap, structurally → new_failure_class_introduction);\n- cross-provider независимость: S3* на другом провайдере, ловит коррелированные\n  галлюцинации S3 в оценке неуверенности.\nЕсли S3* находит что reaction на неуверенность нежизнеспособна → алгедоник\n→ S5 (архитектор) вмешательство (см. §1, intervention metric +1).\n",
      "evidence": [
        "сессия 2026-07-13: человек — «метрика вмешательства будет показывать насколько VSM нежизнеспособен в состоянии автономности. Чем меньше вмешательства, тем лучше»",
        "сессия 2026-07-13: человек — «передать при прохождении terminal bench на публику через vsmlite дашборды, а не S5»",
        "сессия 2026-07-13: человек — «S5 это архитектор VSM, который может на ходу изменять что-то если по алгедоническому каналу S3 S3* и S4 не справляются»",
        "сессия 2026-07-13: человек — intervention = только S5; «Архитектору доступны доп. знания вроде того, что этот VSM используется в т.ч. для Eval Env, но не говорится что Terminal Bench»",
        "сессия 2026-07-13: человек — environment types: Production/Simulation/Benchmark/Sandbox/Training",
        "сессия 2026-07-13: человек — VSM-004 объединить; MCP restriction + S4 uncertainty сохранить",
        "VSM-001 → runtime membrane; VSM-005: S5 = архитектор (не divine will), intervention metric",
        "VSM-002 → product_evaluation; VSM-005: env-type awareness S5, MCP structural restriction",
        "VSM-004 → superseded (объединён в VSM-005: pass-rate + intervention = автономность)"
      ],
      "proposal": "Зафиксировать концептуальный поворот (VSM-005, объединяет VSM-004):\n\n(1) S5 = АРХИТЕКТОР:\n    - vsmlite-tb/CLAUDE.md → S5 role: архитектор, вмешивается при алгедонике\n      от S3/S3*/S4; рутинно бездействует; вмешательство = структурное изменение\n      (OSM-примитивы), не микроуправление.\n    - vsmlite-tb/systems/s5-guardian/{SOUL,SKILL}.md → role = architect.\n    - vsmlite-tb/vsmlite.yaml → identity: S5 role уточнена.\n\n(2) INTERVENTION METRIC:\n    - vsmlite-tb/vsmlite.yaml → system_3.kpi_list: + s5_intervention_count\n      (count S5-вмешательств за цикл; lower = better).\n    - vsmlite-tb/vsmlite.yaml → autonomy.signs: S5-sign уточнён: «доля\n      циклов без S5-вмешательств» (не «доля открытых issues с needs_human»).\n    - vsmlite-tb/monitor/ + scripts/render_data.py → intervention metric в\n      dashboard (публичная трассировка автономности).\n    - scripts/autonomy.py → A(t) учитывает intervention frequency.\n\n(3) ENVIRONMENT-TYPE AWARENESS:\n    - vsmlite-tb/vsmlite.yaml → identity.product_evaluation: env_type_known_to_s5\n      = [Production, Simulation, Benchmark, Sandbox, Training] (S5 знает\n      типы); concrete_benchmark_known_to = [human, model] (конкретика — только\n      человек + модель identity, не S5-агент).\n    - S5-агент (SOUL/SKILL) знает «Benchmark env-type существует», не «TB 2.1».\n\n(4) MCP ACCESS RESTRICTION (для T4):\n    - WORKSTREAM.md → T4 spec: + MCP structural restriction (tool surface не\n      включает eval-access; мембрана = отсутствие инструмента).\n\n(5) UNCERTAINTY HANDLING (продукт, S2/S3/S3*/S4):\n    - vsm/vsm.yaml (через child-dispatcher) → system_4: + uncertainty_driven\n      _expansion trigger.\n    - vsm/vsm.yaml → system_2.coordination_rules: + uncertainty probing.\n    - vsm/vsm.yaml → system_3: + uncertainty optimization on S2+S4 data.\n    - vsm/vsm.yaml → system_3_star: + audit of uncertainty-reaction viability\n      (S3* не rubber-stamp; independently checks S2/S3/S4 response; structural\n      defect detection; cross-provider).\n\n(6) PARENT ISOLATION (structural, vsm/ не знает про vsmlite-tb):\n    - vsm/ и src/ НЕ ссылаются на ../../vsmlite-tb/ (ни в путях, ни в конфигах).\n    - intervention metric живёт в vsmlite-tb/state/ (родитель), НЕ в vsm/state/.\n    - validate.sh expansion: grep по vsm/ и src/ на упоминания vsmlite-tb/\n      (кроме одной структурной ссылки в vsm/CLAUDE.md для навигации — не\n      раскрывает роль vsmlite как оператора, только директорию).\n    - VSM переживает S5-вмешательство (через child-dispatcher) как локальную\n      мутацию, не как внешний акт.\n\n(7) VSM-004 → SUPERSEDED: Dev Set pass-rate вошёл в VSM-005 как входной\n    индикатор автономности (в паре с intervention count как обратный).\n",
      "acceptance": [
        "vsmlite-tb/CLAUDE.md → S5 role = архитектор (вмешивается при алгедонике, рутинно бездействует)",
        "vsmlite-tb/systems/s5-guardian/{SOUL,SKILL}.md → role = architect",
        "vsmlite-tb/vsmlite.yaml → system_3.kpi_list: + s5_intervention_count",
        "vsmlite-tb/vsmlite.yaml → autonomy.signs.s5_sign: доля циклов без S5-вмешательств",
        "vsmlite-tb/vsmlite.yaml → identity.product_evaluation.env_type_known_to_s5 (5 типов)",
        "vsmlite-tb/vsmlite.yaml → identity.product_evaluation.concrete_benchmark_known_to = [human, model]",
        "vsmlite-tb/monitor/ + render_data.py → intervention metric в dashboard",
        "scripts/autonomy.py → A(t) учитывает intervention frequency",
        "vsm/vsm.yaml → system_2 +uncertainty probing; system_3 +uncertainty optimization; system_3_star +uncertainty-reaction audit; system_4 +uncertainty_driven_expansion (через child-dispatcher)",
        "vsm/ и src/ не ссылаются на ../../vsmlite-tb/ (parent isolation; grep проверка)",
        "WORKSTREAM.md → T4: + MCP structural access restriction",
        "VSM-004 → status: superseded (объединён в VSM-005)",
        "ни одного упоминания Terminal Bench/benchmark/eval/harbor в vsm/ и src/ (продукт не знает)",
        "S5-агент файлы (SOUL/SKILL) не содержат 'Terminal Bench' — только env-type 'Benchmark'",
        "validate.sh GREEN (с expansion: parent-isolation grep)"
      ],
      "needs_human_decision": true,
      "policy_question": "Зафиксировать: S5 = архитектор (вмешивается при алгедонике от S3/S3*/S4, рутинно бездействует) + intervention metric (публичный индикатор в dashboard, только S5) + parent isolation (vsm/ не знает про vsmlite-tb) + env-type awareness (S5 знает 5 типов сред включая Benchmark, не знает конкретику TB) + MCP structural restriction (T4) + uncertainty handling S2/S3/S3*/S4 (продукт)? VSM-004 объединить (superseded).\n",
      "options": [
        {
          "id": "accept",
          "label": "Принять VSM-005",
          "hint": "S5 архитектор + intervention + isolation + env-type + MCP + uncertainty (S2/S3/S3*/S4); VSM-004 superseded (Recommended)"
        },
        {
          "id": "partial",
          "label": "Только S5 + intervention",
          "hint": "S5 архитектор + intervention metric; isolation/env-type/MCP/uncertainty отложить"
        },
        {
          "id": "defer",
          "label": "Отложить",
          "hint": "Вернуться позже; сейчас Sync 1 / T3 / T4"
        }
      ],
      "notes": [
        "Это prepare_only (basta_constraint: prepare_only) — человек постановляет.",
        "VSM-001 НЕ закрывается — VSM-005 уточняет S5 role (divine will framing откатан в этой же сессии).",
        "VSM-004 → superseded: Dev Set pass-rate вошёл как входной индикатор; intervention = обратный.",
        "S5-агент знает env-type 'Benchmark', не 'Terminal Bench' — конкретика только в vsmlite.yaml identity (модель) + human.",
        "Правки vsm/vsm.yaml (продукт) — через child-dispatcher; S4 uncertainty-driven не раскрывает eval-context."
      ],
      "created": "2026-07-13",
      "updated": "2026-07-13",
      "status": "triage"
    },
    {
      "id": "VSM-006",
      "source_system": "S5",
      "signal_type": "policy",
      "severity": "S1",
      "target_unit": "child",
      "title": "Autonomous S5 продукта: issues self-resolved, no human escalation (наблюдение через vsmlite dashboards)",
      "summary": "Концептуальный поворот identity продукта (сессия 2026-07-13). Строим автономный\nVSM — значит S5 продукта сам резолвит issues. Требование `needs_human_decision`\nу product issues убирается. Человек наблюдает за всеми product issues через\ndev-проходы (vsmlite dashboards) и поднимает issues уже на уровне родителя\n(`vsmlite-tb/issues/`), если хочет вмешаться.\n\nРаньше (VSM-002, seed): product S5 = `basta_constraint: prepare_only` — готовит\nрешения, не принимает. Это унаследовано от родительского vsmlite (где basta\nуместен: vsmlite — оператор, человек его направляет). Для продукта basta\nпротиворечит цели автономии: если S5 продукта всегда эскалирует к human,\nпродукт никогда не станет автономным.\n\nТеперь (VSM-006):\n- Product S5 = **автономный архитектор** (развивает VSM-005). Резолвит issues\n  продукта сам: triage → decision → execution (через s1-dispatcher для ../src/,\n  через self-reconfigure для vsm/). Не эскалирует к human.\n- Product issues НЕ имеют `needs_human_decision`. Поле убирается из schema и\n  template продукта. S0/S1/algedonic в продукке → S5 реагирует сам (структурное\n  изменение), не ждёт human.\n- Человек наблюдает: vsmlite-tb dashboards (monitor/data.js, intervention metric\n  из VSM-005) показывают product issues, их resolution, S5 interventions. Человек\n  видит всё, но НЕ в цикле product issue-resolution.\n- Если человек хочет вмешаться → поднимает issue на уровне РОДИТЕЛЯ\n  (`vsmlite-tb/issues/VSM-NNN`), не продукта. Родительский vsmlite через\n  child-dispatcher может применить изменения к `../vsm/`. Это intervention\n  (S5 родителя, +1 к metric), не product issue.\n\nКонтраст product S5 vs parent S5:\n- Product S5: autonomous architect, self-resolves, no human escalation.\n- Parent S5 (vsmlite-tb): architect, intervenes on algedonic (VSM-005), bastas\n  остаются (submit_or_publish_results, change_target_tb_version, ...) — родитель\n  управляется человеком, продукт — нет.\n",
      "evidence": [
        "сессия 2026-07-13: человек — «убери у issues в vsm требование human decision. Так как мы строим автономную, мы хотим чтобы S5 сам резолвил»",
        "сессия 2026-07-13: человек — «мы наблюдаем за всеми ними при dev проходе и делаем issues уже на уровне vsmlite»",
        "VSM-002 → product basta_constraint: prepare_only (унаследован от родителя) — VSM-006 снимает для продукта",
        "VSM-005 → S5 = архитектор (вмешивается при алгедонике) — VSM-006 уточняет: product S5 автономен, не эскалирует",
        "vsm/issues/vsm-issue.schema.json → allOf: severity S0/S1 ⇒ needs_human_decision: true — противоречит автономии",
        "vsm/issues/template.yaml → needs_human_decision: false (default) — поле убирается"
      ],
      "proposal": "Убрать `needs_human_decision` и связанные конструкции из продукта:\n\n(1) PRODUCT ISSUE SCHEMA + TEMPLATE:\n    - vsm/issues/vsm-issue.schema.json → убрать `needs_human_decision` из\n      required + properties; убрать allOf rules (S0/S1 ⇒ true, algedonic ⇒ true).\n    - vsm/issues/template.yaml → убрать `needs_human_decision: false` строку.\n    - seed/child/issues/ — те же правки (seed = template для будущих VSM).\n\n(2) PRODUCT IDENTITY (vsm/vsm.yaml):\n    - identity.basta_constraint → убрать (продукт автономен, не prepare_only).\n    - identity.decisions_requiring_human → убрать (продукт не эскалирует).\n    - identity.never_do → убрать `s5_decides_for_human` (S5 продукта МОЖЕТ\n      решать — это его роль теперь).\n    - + identity.never_do: `escalate_to_human` (новый — продукт не эскалирует).\n\n(3) PRODUCT CLAUDE.md (vsm/CLAUDE.md + seed/child/CLAUDE.md):\n    - S5 = autonomous architect, не prepare_only.\n    - NEVER DO: убрать «не давать S5 принимать решения за человека»; добавить\n      `escalate_to_human`.\n    - Basta: убрать (продукт не имеет basta_constraint).\n    - + примечание: «человек наблюдает через родительский vsmlite dashboards;\n      вмешательство — через родительский issue, не product issue».\n\n(4) PRODUCT S5-GUARDIAN (vsm/systems/s5-guardian/ + seed):\n    - SOUL.md: S5 = autonomous architect (резолвит сам, не готовит для human).\n    - SKILL.md: triage → decision → execution (через s1-dispatcher); убрать\n      «needs_human_decision → policy_question + options».\n    - + ссылка: S5-вмешательство логируется для родительского intervention metric.\n\n(5) PRODUCT .intent.yaml (vsm/.intent.yaml):\n    - authority.basta_constraint → переформулировать: product S5 автономен;\n      basta остаются только для identity/values change (S5 не меняет own\n      identity без родительского решения — но это родительский basta, не product).\n    - + autonomy.autonomous_means: S5-sign = «доля issues, резолвленных без\n      эскалации к human» (было «доля issues без needs_human_decision»).\n\n(6) РОДИТЕЛЬ (vsmlite-tb/) — БЕЗ ИЗМЕНЕНИЙ:\n    - Родительский S5 остаётся prepare_only (basta_constraint: prepare_only).\n    - Родительские issues сохраняют needs_human_decision (человек управляет\n      родителем, родитель управляет продуктом).\n    - validate.sh: проверить что product schema не требует needs_human_decision.\n",
      "acceptance": [
        "vsm/issues/vsm-issue.schema.json: нет needs_human_decision в required/properties; нет allOf S0/S1⇒true",
        "vsm/issues/template.yaml: нет needs_human_decision",
        "seed/child/issues/{schema,template}: те же правки",
        "vsm/vsm.yaml → identity: нет basta_constraint; нет decisions_requiring_human; never_do нет s5_decides_for_human; never_do есть escalate_to_human",
        "vsm/CLAUDE.md + seed/child/CLAUDE.md: S5 = autonomous architect; нет basta prepare_only; never_do есть escalate_to_human",
        "vsm/systems/s5-guardian/{SOUL,SKILL}.md + seed: S5 резолвит сам, не готовит для human",
        "vsm/.intent.yaml: basta переформулирован (product S5 автономен); autonomy S5-sign updated",
        "vsmlite-tb/ (родитель) — БЕЗ ИЗМЕНЕНИЙ (basta сохранён на родителе)",
        "ни одного упоминания Terminal Bench/benchmark/eval/harbor в vsm/ и src/",
        "validate.sh GREEN"
      ],
      "needs_human_decision": true,
      "policy_question": "Убрать needs_human_decision из product issues, сделать product S5 автономным архитектором (self-resolves, не эскалирует к human)? Человек наблюдает через vsmlite dashboards; вмешательство — через родительский issue.\n",
      "options": [
        {
          "id": "accept",
          "label": "Принять VSM-006",
          "hint": "Product S5 autonomous; needs_human_decision убран; родитель без изменений (Recommended)"
        },
        {
          "id": "partial",
          "label": "Только schema/template",
          "hint": "Убрать поле из issues, но bastа в identity оставить (гибрид)"
        },
        {
          "id": "defer",
          "label": "Отложить",
          "hint": "Вернуться позже; сейчас продолжить VSM-005/Sync 1"
        }
      ],
      "notes": [
        "Это prepare_only (basta_constraint РОДИТЕЛЯ: prepare_only) — человек постановляет.",
        "VSM-005 (S5 = архитектор) совместим: VSM-005 описывает родительский S5; VSM-006 — product S5.",
        "Правки vsm/ + seed/child/ — через child-dispatcher (главный инвариант).",
        "Родительский vsmlite-tb/issues/ сохраняет needs_human_decision — человек управляет родителем."
      ],
      "created": "2026-07-13",
      "updated": "2026-07-13",
      "status": "triage"
    }
  ],
  "history": [
    {
      "date": "2026-07-13",
      "autonomy_score": 0.1,
      "maturation_phase": "Phase 1",
      "coverage_ratio": 0.0,
      "validate_pass_rate": null,
      "drift_score": 0.0,
      "triple_index": {
        "actuality": "",
        "capability": "",
        "potentiality": "",
        "measurement": ""
      },
      "balance_s3_s4": {
        "ratio": null,
        "status": "unknown",
        "alert": false
      },
      "s5_intervention_count": 0,
      "s5_intervention_cycles": 0,
      "intervention_share": 0.0
    }
  ],
  "activity": [],
  "interventions": []
};
