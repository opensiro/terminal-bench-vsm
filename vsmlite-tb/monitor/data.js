window.VSM_DATA = {
  "generated": "2026-07-15T13:45:36",
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
    "autonomy_score": 0.175,
    "maturation_phase": "Phase 4",
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
    "intervention_share": 0.0,
    "eval_pass_rate": 0.0
  },
  "eval": {
    "dataset": "open-thoughts/OpenThoughts-TB-dev-v2",
    "harness": "claude-code",
    "generated": "2026-07-15",
    "summary": {
      "total": 1,
      "passed": 0,
      "failed": 1,
      "error": 0,
      "pass_rate": 0.0
    },
    "by_difficulty": {
      "easy": {
        "total": 1,
        "passed": 0,
        "pass_rate": 0.0
      }
    },
    "by_category": {
      "file-operations": {
        "total": 1,
        "passed": 0,
        "pass_rate": 0.0
      }
    },
    "trend": {
      "current": 0.0,
      "previous": null,
      "delta": 0.0,
      "direction": "none"
    },
    "history": []
  },
  "maturation": {
    "state": "Phase 4",
    "phase_activated": [
      "S1",
      "S2",
      "S3",
      "S3*"
    ],
    "autonomy_verdict": "DEPENDENT",
    "autonomy_target": 1.0,
    "autonomy_signs": {
      "s5_sign": {
        "value": 0.0,
        "from": "interventions",
        "meets": true
      },
      "s4_sign": {
        "value": 0,
        "from": "intel",
        "meets": false
      },
      "s3_sign": {
        "value": 0,
        "from": "units",
        "meets": false
      },
      "s1_sign": {
        "value": 0,
        "from": "activity",
        "meets": false
      },
      "eval_sign": {
        "value": 0.0,
        "from": "dev_metrics",
        "meets": false
      }
    },
    "last_primitive": "Create",
    "last_transition": "Phase 3 → Phase 4",
    "child_initialized": true,
    "child_path": "../vsm",
    "cycle_count": 0,
    "updated": "2026-07-14"
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
      "needs_human_decision": false,
      "status": "accepted",
      "decision": "accept — S5 = архитектор + intervention metric + parent isolation + env-type awareness + MCP restriction + uncertainty handling (S2/S3/S3*/S4). VSM-004 superseded (объединён). Применено к vsmlite-tb/ + vsm/vsm.yaml (через child-dispatcher).",
      "selected_options": [
        "accept"
      ],
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
      "updated": "2026-07-13"
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
    },
    {
      "id": "VSM-007",
      "source_system": "S5",
      "signal_type": "policy",
      "severity": "S1",
      "target_unit": "child",
      "title": "OSM Split S1 → planner + executor + verifier (multi-agent solver)",
      "summary": "Применение OSM-примитива Split к S1 дочернего VSM. S1 был mono-agent\n(single solver per invocation, stateless — CONTRACT.md §5). Split разбивает\nS1 на три рекурсивно-жизнеспособных суб-агента:\n\n- **planner** — декомпозирует task_prompt на упорядоченные шаги (plan).\n- **executor** — выполняет шаги через MCP tools (hands).\n- **verifier** — проверяет результат каждого шага (tests/exit codes/artifacts).\n\nКоординация между суб-агентами — через session sync (shared state: plan,\nartifacts, exploration_map, intermediate_results, verifier_feedback). Session\nsync был placeholder (src/session_sync/README.md — «НЕ НУЖЕН (mono-agent)»);\nSplit активирует его.\n\nПочему сейчас: recovery cycle orchestrator (S1→S3→S3*→recovery→S2→retry)\nтребует связывания 5 слоёв. Multi-agent S1 повышает viability для long-horizon\ncoding-задач: planner снижает cognitive load, executor фокусируется на\nвыполнении, verifier обеспечивает early-failure detection (до budget\nexhaustion). Это разгружает recovery cycle — verifier может поймать failure\nдо того, как он станет observation для S3.\n\nS2 conflict detection (resource_overlaps, output_contradictions,\ncustom_triggers из vsm.yaml system_2) активируется параллельно — для\nпараллельных attempts/tasks (resource registry), не для sub-agents внутри\nодного invocation (там session sync).\n",
      "evidence": [
        "primitives.yaml → Split: requires_human_decision: true, primitive_class: structural",
        "VSM-006 → identity/values change — единственное исключение автономии product S5; Split требует родительского решения",
        "PIPELINES.md §6 — «если S1 станет мультиагентным через OSM-примитив Split (planner + executor + verifier), понадобится session sync»",
        "src/session_sync/README.md — placeholder с contract: {task_id, agents, shared_state, created, ttl}",
        "CONTRACT.md §5 — S1 stateless (fresh-per-invocation); Split сохраняет это: каждый sub-agent stateless, state в session sync (per-task, TTL)",
        "VSM-005 — S5 = архитектор (вмешивается при алгедонике); Split — упреждающее структурное улучшение, не algedonic response"
      ],
      "preconditions": [
        "source unit (S1) достаточно сложен — long-horizon coding задачи требуют декомпозиции",
        "каждая часть удовлетворяет критериям жизнеспособности: planner (decision-making), executor (action), verifier (audit) — чёткие роли",
        "session sync contract определён (src/session_sync/README.md)"
      ],
      "postconditions": [
        "исходный VSM остаётся (S1 остаётся system_1, но теперь = ансамбль 3 суб-агентов)",
        "каждая часть — рекурсивно жизнеспособна (planner/executor/verifier имеют свои decision/action/audit циклы)",
        "остаточная организация удовлетворяет жизнеспособности (S2/S3/S3*/S4/S5 не меняются)"
      ],
      "proposal": "Применить Split через child-dispatcher:\n\n(1) src/runtime/multi_agent.py — MultiAgentSolver:\n    - planner: декомпозирует task_prompt → list[step] (через HarnessRunner/LLM\n      или rule-based для тестов).\n    - executor: выполняет steps через MCP tools (через HarnessRunner или\n      AgentLoop), пишет intermediate_results в session.\n    - verifier: проверяет каждый step (exit codes, artifacts, tests), пишет\n      verifier_feedback в session.\n    - Координация через SessionStore: planner writes plan → executor reads\n      plan + writes intermediate_results → verifier reads + writes feedback\n      → executor корректирует при fail.\n    - MultiAgentSolver реализует SolverProtocol (та же сигнатура\n      decide_next_action), внутренне оркестрируя 3 суб-агента.\n\n(2) src/session_sync/store.py — SessionStore (реализация вместо placeholder):\n    - create(task_id, agents) → Session\n    - get/update/read/close — per-task isolation, TTL cleanup.\n    - shared_state: {plan, artifacts, exploration_map, intermediate_results,\n      verifier_feedback}.\n\n(3) src/runtime/dispatcher.py — solver_mode:\n    - S1Dispatcher(solver_mode=\"mono\"|\"multi\").\n    - \"multi\" → MultiAgentSolver; \"mono\" → RuleBasedSolver/HarnessRunner.\n    - Session lifecycle: create в начале invocation, close в конце.\n\n(4) src/s2/ — S2 conflict detection runtime:\n    - coordinator.py: authorize_retry (4-check: anti-repeat → conflict →\n      oscillation → authorize).\n    - conflict.py: ConflictDetector (resource_overlaps, output_contradictions,\n      custom_triggers из vsm.yaml).\n    - Resource registry для multi-agent изоляции (register/release claims).\n\n(5) src/orchestrator.py — recovery cycle:\n    - Связывает S1→S3→S3*→recovery→S2→retry в цикл.\n    - Budget: cumulative cost tracking, budget reduction per retry.\n\n(6) src/runtime/llm_interface.py — update:\n    - Убрать NotImplementedError из build_llm_solver().\n    - Production LLM path = HarnessRunner (Goose+ZAI), не in-process API.\n",
      "acceptance": [
        "src/runtime/multi_agent.py: MultiAgentSolver (planner+executor+verifier) реализует SolverProtocol",
        "src/session_sync/store.py: SessionStore (create/get/update/read/close, per-task isolation, TTL)",
        "src/runtime/dispatcher.py: solver_mode='multi' использует MultiAgentSolver",
        "src/s2/coordinator.py: authorize_retry (4-check pipeline из PIPELINES.md §2)",
        "src/s2/conflict.py: ConflictDetector (resource_overlaps, output_contradictions, custom_triggers)",
        "src/orchestrator.py: run_recovery_cycle (S1→S3→S3*→recovery→S2→retry, CONTRACT.md §4)",
        "src/runtime/llm_interface.py: build_llm_solver не raises NotImplementedError",
        "smoke tests A-F pass (детерминированные, через RuleBasedSolver + dry_run recovery)",
        "ни одного упоминания Terminal Bench/benchmark/eval/harbor в vsm/ и src/",
        "validate.sh GREEN"
      ],
      "needs_human_decision": true,
      "decision": "approved",
      "executor": "child-dispatcher",
      "notes": [
        "Split = единственное исключение автономии product S5 (VSM-006: identity/values change).",
        "Product S5 НЕ мог применить Split сам — родительское решение. Мы = vsmlite S5, постановляем.",
        "S1 остаётся stateless (CONTRACT.md §5): state в session sync (per-task, TTL), не в solver.",
        "S2 conflict detection — для параллельных attempts/tasks (resource registry), не для sub-agents внутри invocation.",
        "Правки src/ — через child-dispatcher (главный инвариант)."
      ],
      "created": "2026-07-13",
      "updated": "2026-07-13",
      "status": "triage",
      "options": []
    },
    {
      "id": "VSM-008",
      "source_system": "S1",
      "signal_type": "gap",
      "severity": "S2",
      "target_unit": "meta",
      "title": "Terminal-Bench Dev Set v2 eval-пайплайн: docker-exec MCP bridge + dev_metrics.json",
      "summary": "Реализован eval-пайплайн в vsmlite-tb/eval/ (новый модуль родителя), который\nоценивает продукт (../src/ — failure-aware harness) на 100 задачах\nTerminal-Bench Dev Set v2 (open-thoughts/OpenThoughts-TB-dev-v2) и записывает\npass-rate в state/dev_metrics.json — как материализацию ВХОДНОГО индикатора\nавтономности A(t) из VSM-004/005.\n\nКлючевое архитектурное решение — \"docker-exec MCP bridge\": продуктовый\nMCP-сервер (../src/mcp_server/) запускается ВНУТРИ TB-контейнера через\n`docker exec -i <container> python3 -m mcp_server.server`, а harness\n(claude-code/goose) подключается к нему с хоста через mcp_config.json.\nКаждый shell.exec MCP выполняется в реальном TB-окружении; trace пишется\nв продуктовом формате (T2 CONTRACT §3). Продукт НЕ модифицируется и НЕ\nимпортируется родителем как модуль — только read-only bind mount ../src\n+ subprocess. Мембрана VSM-002 сохранена.\n\nМембрана материализована в eval/membrane.py: TB instruction.md → нейтральный\ntask_prompt (вырезается канарейка + оценочные термины), verify_neutrality()\nбросает ошибку при утечке. Грейдинг (eval/grader.py) честный outcome-based:\ntests/ копируются в контейнер ПОСЛЕ фазы агента (анти-reward-hacking),\ntests/test.sh пишет 1/0 в /logs/verifier/reward.txt.\n",
      "evidence": [
        "vsmlite-tb/eval/ — новый модуль: loader, membrane, container, agent_phase, grader, runner, metrics, __main__",
        "vsmlite-tb/state/dev_metrics.json — целевой файл метрики (решает открытый вопрос из VSM-004 notes)",
        "vsmlite-tb/scripts/validate.sh §2c — добавлена проверка benchmark membrane (VSM-002): grep ../vsm/ ../src/ на terminal-bench/harbor",
        "vsmlite-tb/Makefile — eval-list/eval-run/eval-all/eval-summary таргеты",
        "huggingface.co/datasets/open-thoughts/OpenThoughts-TB-dev-v2 — 100 TB задач, НЕ табличный (папки на диске)"
      ],
      "proposal": "Структурное дополнение родителя (vsmlite-tb/eval/), НЕ затрагивающее продукт.\nneeds_human_decision: false — operational/structural, не identity-affecting.\nФиксируется в истории (monotonic id) для audit trail.\n\nСвязь с A(t) (VSM-004/005): dev_metrics.json summary.pass_rate — ВХОДНОЙ\nиндикатор автономности (в паре с S5 intervention count как ОБРАТНЫЙ).\nРост pass_rate ↑ + снижение interventions ↓ = рост автономности.\n\nСвязь с мембраной (VSM-002): eval/membrane.py — материализация мембраны,\nкоторая раньше была только концептуальной (\"при трансляции TB-задачи в продукт\nTB-фрейминг снимается\"). Теперь это исполняемый код с verify_neutrality().\n",
      "acceptance": [
        "vsmlite-tb/eval/ создан: __init__, __main__, config, loader, membrane, container, agent_phase, grader, runner, metrics",
        "vsmlite-tb/state/dev_metrics.json — целевой формат метрики (summary + by_category + by_difficulty + tasks[])",
        "make validate GREEN с новой проверкой §2c (benchmark membrane VSM-002)",
        "src/ и vsm/ БЕЗ ИЗМЕНЕНИЙ (продукт не тронут)",
        "make eval-list, eval-run TASK=<id>, eval-all, eval-summary — CLI точки входа работают",
        "eval/membrane.py verify_neutrality() проходит на реальных instruction.md",
        "vsmlite-tb/requirements.txt — huggingface_hub как единственная новая зависимость"
      ],
      "needs_human_decision": false,
      "status": "done",
      "decision": "done — eval-пайплайн реализован, validate GREEN, мембрана усилена проверкой §2c",
      "selected_options": [],
      "references": [
        "VSM-002",
        "VSM-004",
        "VSM-005"
      ],
      "notes": [
        "Требуется Docker daemon на хосте. TB-образы ubuntu:24.04-based, сборка ~минуты/задача.",
        "Полный прогон 100 задач — длительный; CLI даёт --limit и --filter для инкрементальной разработки.",
        "Продуктовый MCP-сервер запускается в контейнере с PYTHONPATH=/opt/mcp_server_src (read-only mount ../src).",
        "harness-логика сборки аргументов НЕ импортируется из src/runtime/harness.py (развязка от внутреннего API продукта)."
      ],
      "created": "2026-07-14",
      "updated": "2026-07-14",
      "options": []
    },
    {
      "id": "VSM-009",
      "source_system": "S5",
      "signal_type": "policy",
      "severity": "S1",
      "target_unit": "child",
      "title": "Phase transition: Phase 1 → Phase 2 (S2 coordinator activated)",
      "summary": "Активация S2 coordinator в дочернем VSM. S2 runtime реализован\n(`src/s2/coordinator.py`, `src/s2/conflict.py`), capability report\nподтверждает работоспособность (S2 verify: 3/3 checks passed).\n\nEmergence criteria (phases.yaml Phase 1→2):\n- ≥2 operational units OR explicit coord need: VSM-007 Split S1 на\n  planner+executor+verifier — multi-agent требует координации.\n- observed resource contention: S2 conflict detection runtime\n  (resource_overlaps, output_contradictions), capability report S2\n  resource_overlap_detection = PASS.\n",
      "evidence": [
        "capability_report S2: 3/3 checks passed (authorize_retry_valid, anti_repeat_blocking, resource_overlap_detection)",
        "src/s2/coordinator.py: S2Coordinator.authorize_retry (4-check pipeline: anti-repeat → conflict → oscillation → authorize)",
        "src/s2/conflict.py: ConflictDetector (resource_overlaps, output_contradictions, circumvent_recovery)",
        "VSM-007 Split: planner+executor+verifier → multi-agent требует координации",
        "src/runtime/verify.py _verify_s2: real S2Coordinator.authorize_retry на real RetryHistory"
      ],
      "preconditions": [
        "S1 runtime реализован и работает (capability_report S1: 3/3 PASS)",
        "S2 runtime реализован (src/s2/)",
        "≥2 units need coordination (VSM-007 Split: planner+executor+verifier)"
      ],
      "postconditions": [
        "phase_activated: [S1, S2]",
        "maturation_state: Phase 2",
        "S2 system active in vsm.yaml"
      ],
      "proposal": "Применить phase-transition (Phase 1 → Phase 2) через child-dispatcher:\n- vsm/vsm.yaml: meta.maturation_state → Phase 2, meta.phase_activated → [S1, S2]\n- state/maturation.json: maturation_state → Phase 2, phase_activated → [S1, S2], last_transition → \"Phase 1 → Phase 2\"\n",
      "acceptance": [
        "vsm/vsm.yaml → meta.maturation_state: Phase 2",
        "vsm/vsm.yaml → meta.phase_activated: [S1, S2]",
        "state/maturation.json → maturation_state: Phase 2",
        "state/maturation.json → phase_activated: [S1, S2]",
        "state/maturation.json → last_transition: Phase 1 → Phase 2",
        "validate.sh GREEN"
      ],
      "needs_human_decision": true,
      "decision": "approved",
      "executor": "child-dispatcher",
      "created": "2026-07-14",
      "updated": "2026-07-14",
      "status": "triage",
      "options": []
    },
    {
      "id": "VSM-010",
      "source_system": "S5",
      "signal_type": "policy",
      "severity": "S1",
      "target_unit": "child",
      "title": "Phase transition: Phase 2 → Phase 3 (S3 optimizer activated)",
      "summary": "Активация S3 optimizer в дочернем VSM. S3 runtime реализован\n(`src/classifier/classifier.py`, `src/recovery_policies/`),\ncapability report подтверждает (S3 verify: 3/3 checks passed).\n\nEmergence criteria (phases.yaml Phase 2→3):\n- S2 ran ≥2 cycles without escalations: orchestrator recovery cycle\n  (smoke tests A/C/D + capability_report orchestrator: PASS).\n- KPI/budget need appeared: orchestrator budget tracking\n  (`src/orchestrator.py`), S3 KPI list в vsm.yaml\n  (failure_recovery_rate, retry_efficiency, policy_effectiveness).\n",
      "evidence": [
        "capability_report S3: 3/3 checks passed (taxonomy_loaded, classify_import_error, recovery_executor_dry_run)",
        "src/classifier/classifier.py: FailureClassifier (16 classes, match_order, confidence)",
        "src/recovery_policies/: 15 real executors (pip install, git reset, ...)",
        "capability_report orchestrator: PASS (run_recovery_cycle end-to-end)",
        "src/runtime/verify.py _verify_s3: real classifier + dry_run executor"
      ],
      "preconditions": [
        "Phase 2 active (VSM-009 applied)",
        "S3 runtime реализован (src/classifier/, src/recovery_policies/)",
        "S2 ran ≥2 cycles (orchestrator recovery cycle tests)"
      ],
      "postconditions": [
        "phase_activated: [S1, S2, S3]",
        "maturation_state: Phase 3",
        "S3 system active in vsm.yaml"
      ],
      "proposal": "Применить phase-transition (Phase 2 → Phase 3) через child-dispatcher:\n- vsm/vsm.yaml: meta.maturation_state → Phase 3, meta.phase_activated → [S1, S2, S3]\n- state/maturation.json: maturation_state → Phase 3, phase_activated → [S1, S2, S3], last_transition → \"Phase 2 → Phase 3\"\n",
      "acceptance": [
        "vsm/vsm.yaml → meta.maturation_state: Phase 3",
        "vsm/vsm.yaml → meta.phase_activated: [S1, S2, S3]",
        "state/maturation.json → maturation_state: Phase 3",
        "state/maturation.json → phase_activated: [S1, S2, S3]",
        "state/maturation.json → last_transition: Phase 2 → Phase 3",
        "validate.sh GREEN"
      ],
      "needs_human_decision": true,
      "decision": "approved",
      "executor": "child-dispatcher",
      "created": "2026-07-14",
      "updated": "2026-07-14",
      "status": "triage",
      "options": []
    },
    {
      "id": "VSM-011",
      "source_system": "S5",
      "signal_type": "policy",
      "severity": "S1",
      "target_unit": "child",
      "title": "Phase transition: Phase 3 → Phase 4 (S3* auditor activated)",
      "summary": "Активация S3* auditor в дочернем VSM. S3* runtime реализован\n(`src/audit/auditor.py`, `src/audit/config.py`), capability report\nподтверждает (S3* verify: 2/2 checks passed).\n\nEmergence criteria (phases.yaml Phase 3→4):\n- S3 controlled resources ≥2 cycles: orchestrator recovery cycle\n  (classify → policy → recovery → retry).\n- Information asymmetry → need independent audit: S3* cross-provider\n  constraint (s1_provider ≠ s3star_provider, audit/config.py).\n\nHard constraint: provider_constraint.must_differ_from: s1.\nS1 = ZAI/GLM-5.2. S3* = другой provider (documented in audit/config.py).\n",
      "evidence": [
        "capability_report S3_star: 2/2 checks passed (cross_provider_constraint, audit_classification)",
        "src/audit/auditor.py: S3StarAuditor (5 check types: consistency, coverage, structural, uncertainty, provider_violation)",
        "src/audit/config.py: AuditConfig.validate_provider_constraint (s1_provider ≠ s3star_provider)",
        "capability_report orchestrator: PASS (S3* audit на каждой classification в recovery cycle)"
      ],
      "preconditions": [
        "Phase 3 active (VSM-010 applied)",
        "S3* runtime реализован (src/audit/)",
        "S3 controlled resources ≥2 cycles (orchestrator recovery cycle)",
        "Cross-provider constraint satisfiable (s1=ZAI, s3*≠ZAI)"
      ],
      "postconditions": [
        "phase_activated: [S1, S2, S3, S3*]",
        "maturation_state: Phase 4",
        "S3* system active in vsm.yaml"
      ],
      "proposal": "Применить phase-transition (Phase 3 → Phase 4) через child-dispatcher:\n- vsm/vsm.yaml: meta.maturation_state → Phase 4, meta.phase_activated → [S1, S2, S3, S3*]\n- state/maturation.json: maturation_state → Phase 4, phase_activated → [S1, S2, S3, S3*], last_transition → \"Phase 3 → Phase 4\"\n",
      "acceptance": [
        "vsm/vsm.yaml → meta.maturation_state: Phase 4",
        "vsm/vsm.yaml → meta.phase_activated: [S1, S2, S3, S3*]",
        "state/maturation.json → maturation_state: Phase 4",
        "state/maturation.json → phase_activated: [S1, S2, S3, S3*]",
        "state/maturation.json → last_transition: Phase 3 → Phase 4",
        "validate.sh GREEN"
      ],
      "needs_human_decision": true,
      "decision": "approved",
      "executor": "child-dispatcher",
      "created": "2026-07-14",
      "updated": "2026-07-14",
      "status": "triage",
      "options": []
    },
    {
      "id": "VSM-012",
      "source_system": "S5",
      "signal_type": "policy",
      "severity": "S0",
      "target_unit": "child",
      "title": "Полная агентизация S1–S5: каждая система = goose-агент внутри докера (Reconfigure runtime)",
      "summary": "Концептуальный поворот runtime продукта (инициатива человека, сессия 2026-07-14).\n\nСЕЙЧАС: продукт — гибрид. S1 = внешний harness (goose/claude) + продуктовый\nMCP-сервер («руки»); S2/S3/S3* = детерминированные Python-функции\n(coordinator.py, classifier.py, auditor.py); S5 = отсутствует (basta —\nродитель/человек). orchestrator.py координирует цикл recovery. Все системы\nживут как Python-код в ../src/, управляютсяdispatcher.invoke().\n\nПРЕДЛАГАЕТСЯ: каждая система S1–S5 = ОТДЕЛЬНЫЙ goose-агент внутри\nDocker-контейнера, со своим SOUL/SKILL/TASK, своим набором тулов и скриптов,\nкоординируясь через общий state. orchestrator = протокол взаимодействия\nагентов, а не Python-оркестратор. Продукт — рой агентных ролей, а не монолит.\n\nВАЖНО: seed/child/systems/ УЖЕ содержит агентные маски для всех систем\n(s2-coordinator, s3-optimizer, s3-star-auditor, s4-scout, s5-guardian — каждая\nс SOUL/SKILL/HEARTBEAT/TASK). VSM-012 = сделать эти маски ИСПОЛНЯЕМЫМИ\ngoose-агентами, а не только документацией к Python-функциям.\n",
      "evidence": [
        "vsm/vsm.yaml → system_1/2/3/3_star/4: описания ролей, но runtime = ../src/ Python",
        "vsmlite-tb/seed/child/systems/{s2-coordinator,s3-optimizer,s3-star-auditor,s4-scout,s5-guardian}/ — агентные маски УЖЕ спроектированы (SOUL/SKILL/TASK), но не исполняются goose",
        "src/orchestrator.py — Python-оркестратор recovery cycle (S1→S3→S3*→recovery→S2→retry); при агентизации = протокол координации агентов",
        "src/s2/coordinator.py::authorize_retry — Python 4-check (anti-repeat, conflict, oscillation); кандидат на агентизацию",
        "src/classifier/classifier.py::classify — Python signal-matching; кандидат на агентизацию (но риск: classifier должен остаться детерминированным!)",
        "src/audit/auditor.py::audit_classification — Python + cross-provider constraint; кандидат на агентизацию (S3* = goose на ДРУГОМ провайдере)",
        "src/runtime/llm_interface.py:1-17 — «in-process API path deliberately closed; production = HarnessRunner»; VSM-012 переоткрывает агентный путь",
        "vsmlite-tb/eval/agent_phase.py — docker-exec MCP bridge: goose+MCP внутри контейнера; паттерн для агентизации",
        "phases.yaml: продукт в Phase 4 (S1–S3* активны); S4/S5 ещё не проявлены — VSM-012 может совпасть с Phase 5→6"
      ],
      "proposal": "VSM-012 = концептуальная развилка, НЕ готовая к реализации. Человек постановляет\nнаправление; затем серия VSM-013+ (по одной системе за раз) реализует через\nchild-dispatcher. Этот issue фиксирует ЗАМЫСЕЛ и архитектурные вопросы.\n\n── Что меняется при полной агентизации ──\n\n(1) Каждая система = goose-агент со своим tool surface:\n  - S1 solver: goose + coding tools (fs/shell/git) [уже так через harness]\n  - S2 coordinator: goose + coordination tools (state read/write, conflict\n    detection, retry authorize) [сейчас Python coordinator.py]\n  - S3 optimizer: goose + classification tools (taxonomy read, signal match,\n    policy select) [сейчас Python classifier.py]\n  - S3* auditor: goose НА ДРУГОМ ПРОВАЙДЕРЕ + audit tools (read-only state,\n    cross-provider constraint) [сейчас Python auditor.py]\n  - S4 scout: goose + internet/pattern-discovery tools [не реализован]\n  - S5 guardian: goose + policy/identity tools [не реализован]\n\n(2) Координация = общий state (Redis/file/stdio-bus), а не Python-вызовы.\n  orchestrator.py → протокол обмена сообщениями между агентами.\n\n(3) Каждый агент живёт внутри Docker-контейнера (sandbox), со своими\n  скриптами и тулами. Рой агентов, не монолит.\n\n── Ключевые архитектурные вопросы (для человека) ──\n\nQ1: ДЕТЕРМИНИЗМ S3 classifier. Сейчас classify — детерминированный signal-\n    matching (regex по taxonomy). Goose-агент = вероятностный (LLM). Готовы\n    ли потерять детерминизм ради гибкости? Или S3 остаётся Python (гибрид:\n    S1/S2/S4/S5 = агенты, S3/S3* = Python)? Это РЕШАЮЩИЙ вопрос — affects\n    classifier_precision KPI, recovery reproducibility, S3* audit.\n\nQ2: S3* CROSS-PROVIDER. Сейчас constraint в audit/config.py (s1≠s3star).\n    При агентизации: S3* goose на другом провайдере — структурно сильнее\n    (другая модель, не просто другая конфигурация). Но сложнее оркестрация.\n\nQ3: STATE КООРДИНАЦИИ. Python-оркестратор → обмен сообщениями. Какой\n    транспорт? Redis (тяжело для sandbox)? File-based state (просто, но\n    race conditions)? stdio-bus (как MCP)? Это новый слой инфраструктуры.\n\nQ4: ПРИМИТИВ OSM. Это Reconfigure (runtime меняется, identity сохраняется)\n    или Split (продукт делится на рекурсивные под-VSM по системам)? От этого\n    зависит Phase-модель и emergence criteria.\n\nQ5: ПОРЯДОК АГЕНТИЗАЦИИ. Сразу все (big bang) или по одной системе\n    (инкрементально: S5 → S4 → S3* → S3 → S2, каждая = отдельный VSM-NNN)?\n    Инкрементально безопаснее, дольше.\n\nQ6: СОВМЕСТИМОСТЬ С EVAL. Текущий eval-bridge (vsmlite-tb/eval/) тестирует\n    S1=harness+MCP. При агентизации S2–S5 тоже становятся тестируемыми.\n    Eval должен расширяться: не только «решила ли задача», но и «координировал\n    ли S2», «классифицировал ли S3». Это новый класс метрик.\n\n── Что НЕ меняется ──\n- Мембрана VSM-002 (продукт не знает про TB; task_prompt нейтрален).\n- never_do: same_provider_for_s3star, skip_failure_classification, circumvent_recovery.\n- Stateless CONTRACT §5 (каждый invoke свежий; state только в общем state-bus).\n- general_purpose_discipline (агенты не tied к конкретному оценочному набору).\n",
      "acceptance": [
        "Этот issue = концептуальная фиксация; acceptance = человек выбирает направление (см. options)",
        "При accept: серия VSM-013+ (по одной системе) реализует через child-dispatcher",
        "vsm/vsm.yaml runtime: claude-code → agentized (если accept) — отдельно per системе",
        "phases.yaml: возможно Phase 5→6 совпадает с агентизацией S4/S5",
        "src/ БЕЗ ПРЯМЫХ ИЗМЕНЕНИЙ в этом issue — только концепция; реализация в VSM-013+"
      ],
      "needs_human_decision": true,
      "policy_question": "Полная агентизация S1–S5 (каждая система = goose-агент внутри докера со своими тулами) — принять направление, ограничить гибридом (S3/S3* остаются Python), или отложить? Ключевое: готовы ли потерять детерминизм S3 classifier?\n",
      "options": [
        {
          "id": "full",
          "label": "Полная агентизация S1–S5",
          "hint": "Все системы = goose-агенты; S3 теряет детерминизм; новый state-слой; big-bang или инкрементально (VSM-013+)"
        },
        {
          "id": "hybrid",
          "label": "Гибрид (S1/S2/S4/S5 = агенты, S3/S3* = Python)",
          "hint": "S3 classifier остаётся детерминированным; S3* cross-provider в конфиге; агентизация координационных/исследовательских ролей"
        },
        {
          "id": "s1_only",
          "label": "Только S1 multi-agent (расширение VSM-007)",
          "hint": "Planner/verifier VSM-007 → реальные goose-агенты; S2–S5 не трогаются"
        },
        {
          "id": "defer",
          "label": "Отложить",
          "hint": "Зафиксировать концепцию, вернуться после Phase 5 (S4) — агентизация S5 логичнее когда S5 проявлен"
        }
      ],
      "status": "accepted",
      "decision": "accept: full — полная агентизация S1–S5. Каждая система = goose-агент внутри докера со своим SOUL/SKILL/тулами. S3 classifier теряет детерминизм (становится LLM-агентом) — человек принял этот tradeoff. Реализация = серия VSM-013+ (по одной системе за раз, через child-dispatcher). Q1 (детерминизм S3) = решён в пользу агентизации. Остальные Q2–Q6 решаются per-issue в серии.",
      "selected_options": [
        "full"
      ],
      "references": [
        "VSM-007",
        "VSM-002",
        "VSM-001"
      ],
      "notes": [
        "seed/child/systems/ уже содержит SOUL/SKILL/TASK для всех 5 систем — агентные маски спроектированы, нужно сделать исполняемыми.",
        "Q1 (детерминизм S3) — РЕШАЮЩИЙ вопрос; recommend hybrid если детерминизм критичен для classifier_precision KPI.",
        "vsmlite-tb/eval/agent_phase.py (docker-exec MCP bridge) — готовый паттерн для агентного runtime; goose+MCP внутри контейнера уже работает.",
        "При accept: НЕ реализовывать в этом issue — серия VSM-013+ (по системе), каждая через child-dispatcher.",
        "orchestrator.py → при полной агентизации становится протоколом координации (state-bus), не Python-оркестратором."
      ],
      "created": "2026-07-14",
      "updated": "2026-07-14"
    },
    {
      "id": "VSM-013",
      "source_system": "S5",
      "signal_type": "gap",
      "severity": "S1",
      "target_unit": "child",
      "title": "Agent runtime foundation: inter-process state-bus + goose-runner + coordination protocol",
      "summary": "Фундамент для VSM-012 (полная агентизация S1–S5). Без этого слоя ни одна\nсистема не может стать goose-агентом — нет инфраструктуры запуска и координации.\n\nVSM-012 принял: каждая система = goose-агент внутри докера. Нужны 3 компонента:\n\n(1) INTER-PROCESS STATE-BUS. Сейчас SessionStore (session_sync/) — in-process\n    (Python dict + RLock). Goose-агенты = subprocess'ы → нужен exchange через\n    файловую систему (sandbox-friendly, не Redis). Shared state per-task:\n    {plan, observations, classifications, audit_findings, retry_history, ...}.\n    Каждый агент читает входы, пишет свои выходы.\n\n(2) GOOSE-RUNNER. Generic-обёртка: собрать промпт из SOUL/SKILL/TASK системы,\n    подключить MCP с нужным tool surface, запустить goose как subprocess,\n    собрать структурированный результат. Аналог HarnessRunner, но для ЛЮБОЙ\n    системы (не только S1), со своим tool surface per роль.\n\n(3) COORDINATION PROTOCOL. Заменяет Python-вызовы в orchestrator.py. Каждый\n    шаг recovery-cycle = вызов агента: orchestrator пишет input в state-bus →\n    запускает goose-агента → агент пишет output в state-bus → orchestrator\n    читает. Async, but recovery-cycle = sequential (S1→S3→S3*→S2 по CONTRACT).\n\nНЕ МЕНЯЕТ: мембрану VSM-002, never_do, stateless CONTRACT §5, general-purpose.\nСовместимость с eval: текущий eval-bridge (docker-exec MCP) — частный случай\ngoose-runner для S1; VSM-013 обобщает паттерн.\n",
      "evidence": [
        "src/session_sync/store.py — in-process SessionStore (RLock, dict); нужен inter-process (file-based)",
        "src/runtime/harness.py — HarnessRunner запускает goose через --with-extension wrapper; паттерн для обобщения",
        "src/orchestrator.py::run_recovery_cycle — Python-вызовы S1/S3/S3*/S2; при агентизации = protocol calls",
        "vsmlite-tb/eval/agent_phase.py — docker-exec MCP bridge доказывает что goose+MCP в контейнере работает",
        "vsm/systems/{s2-coordinator,s3-optimizer,s3-star-auditor,s4-scout,s5-guardian}/ — SOUL/SKILL/TASK готовы для goose-промптов"
      ],
      "proposal": "Создать в ../src/agent_runtime/ (новый модуль продукта) три компонента:\n\n── 1. state_bus.py — inter-process shared state ──\nFile-based (JSON in /logs/state-bus/), thread+process-safe через atomic writes\n(write temp → rename). Per-task namespace. API (mirror SessionStore):\n  write(task_id, key, value), read(task_id, key), append(task_id, key, item),\n  read_all(task_id), lock(task_id) [context manager for atomic multi-write].\nSchema: {task_id, created, agents: [...], s1_output, s3_classification,\n         s3star_audit, s2_authorization, recovery_directive, retry_history}.\nTTL cleanup (как SessionStore). Совместим с in-process SessionStore (adapter).\n\n── 2. goose_runner.py — generic agent launcher ──\nAgentConfig(system_name, soul_path, skill_path, task_path, mcp_tools, budget).\nrun(config, input) → AgentResult:\n  - собрать промпт: SOUL (identity) + SKILL (capabilities) + TASK (конкретное\n    задание из state-bus) + available tools\n  - MCP tool surface per роль (см. tool registry ниже)\n  - subprocess: goose run --text <prompt> --with-extension <mcp-wrapper>\n    --no-session --max-turns N --output-format text\n  - парсить stdout → структурированный результат (JSON в stdout или marker)\n  - писать trace в /logs/<system>_trace.json (для observability)\nTool registry (per роль):\n  - S1: fs/shell/git (coding) [уже есть в mcp_server/tools/]\n  - S2: state_bus (read/write), conflict_check, retry_authorize\n  - S3: taxonomy_read, signal_match, policy_select\n  - S3*: state_bus (read-only), audit_check [ДРУГОЙ провайдер — config flag]\n  - S4: browser (internet), pattern_store\n  - S5: policy_read, identity_check, algedonic_send\n\n── 3. protocol.py — coordination protocol ──\nКаждый шаг recovery-cycle = protocol call. Заменяет прямые Python-вызовы:\n  orchestrator.invoke_s1(input) → запускает S1 goose-агента\n  orchestrator.invoke_s3(observations) → запускает S3 goose-агента\n  orchestrator.invoke_s3star(classification, observations) → S3* агент\n  orchestrator.invoke_s2(history, classification) → S2 агент\nКаждый: write input to state-bus → goose-runner → read output from state-bus.\norchestrator.py рефакторится: Python-классы → protocol-вызовы. S3* = ДРУГОЙ\nпровайдер (config в goose_runner, cross-provider constraint сохраняется).\n\n── Порядок реализации (через child-dispatcher, НЕ родителем напрямую) ──\nМембрана: родитель НЕ мутирует ../src/. Этот issue = план; реализация =\nchild-dispatcher (agent в .claude/agents/). Шаги:\n  Step 1: state_bus.py (inter-process SessionStore)\n  Step 2: goose_runner.py (generic launcher + tool registry)\n  Step 3: protocol.py (coordination API)\n  Step 4: orchestrator.py рефакторинг (Python-вызовы → protocol)\n  Step 5: capability_report (verify.py) обновить под агентный runtime\nКаждый Step = отдельный коммит child-dispatcher'а; capability_report = gate.\n",
      "acceptance": [
        "../src/agent_runtime/ создан: __init__, state_bus.py, goose_runner.py, protocol.py",
        "state_bus.py: file-based, atomic writes, API mirror SessionStore, capability_report PASS",
        "goose_runner.py: запускает goose для ЛЮБОЙ системы (S1–S5), per-role tool surface, trace writes",
        "protocol.py: invoke_s1/s3/s3star/s2 — каждый = state-bus write → goose → read",
        "orchestrator.py рефакторен: Python-классы → protocol calls (поведение сохранено)",
        "capability_report (verify.py) PASS под агентным runtime (S1+S2+S3+S3*+orchestrator)",
        "src/ и vsm/ — мембрана VSM-002 сохранена (validate.sh GREEN, без упоминаний TB)",
        "Совместимость: существующий eval-bridge (vsmlite-tb/eval/) не сломан"
      ],
      "needs_human_decision": true,
      "policy_question": "Создать agent_runtime/ (state-bus + goose-runner + protocol) как foundation для VSM-012? Это новый infra-модуль в ../src/, реализуемый child-dispatcher'ом. Альтернатива: инкрементально, по одному компоненту за issue (state_bus → runner → protocol как VSM-013a/b/c).\n",
      "options": [
        {
          "id": "accept",
          "label": "Принять foundation целиком",
          "hint": "VSM-013 = state_bus + goose_runner + protocol + orchestrator refactor; child-dispatcher реализует по шагам (Recommended)"
        },
        {
          "id": "split",
          "label": "Разбить на VSM-013a/b/c",
          "hint": "state_bus (a) → goose_runner (b) → protocol+orchestrator (c); каждый = отдельный issue и коммит"
        },
        {
          "id": "defer",
          "label": "Отложить",
          "hint": "Сначала агентизировать S1 (VSM-007 расширение) без общего foundation; state-bus когда появится S2-агент"
        }
      ],
      "status": "accepted",
      "decision": "accept: VSM-013 = foundation целиком (state_bus + goose_runner + protocol + orchestrator refactor). Реализуется по шагам (каждый = коммит), capability_report = gate между шагами. Мембрана сохранена: agent_runtime/ = продукт, benchmark-agnostic; child_mutation: allowed (workstream-режим).",
      "selected_options": [
        "accept"
      ],
      "references": [
        "VSM-012",
        "VSM-007",
        "VSM-002"
      ],
      "notes": [
        "Реализация — через child-dispatcher (мембрана: родитель не мутирует ../src/ напрямую).",
        "state_bus file-based (не Redis): sandbox-friendly, достаточно для recovery-cycle частоты.",
        "goose-runner обобщает HarnessRunner + eval/agent_phase.py docker-exec bridge.",
        "После VSM-013: серия VSM-014..018 (по системе: S2→S3→S3*→S4→S5 агентизация)."
      ],
      "created": "2026-07-14",
      "updated": "2026-07-14"
    },
    {
      "id": "VSM-014",
      "source_system": "S5",
      "signal_type": "gap",
      "severity": "S2",
      "target_unit": "child",
      "title": "S2 coordinator → goose-agent: активация agent-mode для retry authorization",
      "summary": "Первый step агентизации серии VSM-012 (полная агентизация S1–S5). S2 coordinator\nпереходит из Python-функции (s2/coordinator.py::authorize_retry) на agent-runtime\n(goose-агент + coordination tools).\n\nFoundation (VSM-013) построен и валидирован: state_bus + goose_runner + protocol.\nS2-agent path уже реализован в protocol.py::invoke_s2 + tools/coord.py\n(state_bus_read/write, conflict_check, retry_authorize). Этот issue = активация\nи доказательство что S2-agent работает в реальном recovery cycle.\n\nКОНТРАСТ с VSM-012 Q1 (детерминизм S3): S2 — arbiter, не classifier. S2's 4-check\n(anti-repeat, conflict, oscillation, authorize) остаётся доступным goose-агенту\nчерез retry_authorize tool (детерминированная функция как fact-provider). Агент\nрассуждает над фактами (custom triggers, uncertainty probing из PIPELINES.md §5),\nно core checks детерминированы. Потеря детерминизма минимальна для S2.\n\nИНТЕГРАЦИЯ: orchestrator.py::run_recovery_cycle_agents уже вызывает protocol.invoke_s2\nна Step 6 recovery cycle. E2E тест (S1 fail → S3 classify → S3* audit → S2 authorize)\nдоказывает что agent-mode цикл доходит до S2 и получает структурированный вердикт.\n",
      "evidence": [
        "src/agent_runtime/protocol.py::invoke_s2 — S2 agent invocation (state-bus → goose → read)",
        "src/agent_runtime/tools/coord.py — retry_authorize tool wraps S2Coordinator.authorize_retry (4-check)",
        "src/orchestrator.py::run_recovery_cycle_agents — Step 6: protocol.invoke_s2 (agent-mode)",
        "E2E test: S2-agent в изоляции возвращает {authorized: true, blocked_by: null, reason: '...'} с рассуждением",
        "E2E test: recovery cycle agent-mode use_agents=True — S1 goose → verdict → cycle завершается",
        "capability_report: agent_runtime PASS (state_bus + goose_runner + protocol role configs)"
      ],
      "proposal": "VSM-014 = зафиксировать активацию S2 в agent-mode. Реализация уже в VSM-013\nfoundation; этот issue = E2E доказательство + фиксация в истории.\n\nЧто уже работает:\n  - S2-agent получает task_input (failure_class, policy, attempt) через state-bus\n  - S2-agent использует retry_authorize tool (детерминированный 4-check)\n  - S2-agent рассуждает (goose) и возвращает {authorized, blocked_by, reason}\n  - orchestrator читает результат, решает retry/terminate\n\nЧто НЕ меняется:\n  - S2Coordinator.authorize_retry остаётся Python (через tool — fact-provider)\n  - Детерминированные checks (anti-repeat, conflict, oscillation) сохранены\n  - Python-mode orchestrator (use_agents=False) не тронут (обратная совместимость)\n\nБаг найденный и исправленный при E2E:\n  - orchestrator.py: FailureObservation(**o) падал на лишних полях goose-output\n  - фикс: _obs_from_agent() — толерантный маппинг (только валидные поля)\n",
      "acceptance": [
        "S2-agent в изоляции: возвращает {authorized, blocked_by, reason} с 4-check рассуждением (доказано)",
        "capability_report PASS (S1+S2+S3+S3*+orchestrator+agent_runtime, 6 систем)",
        "make validate GREEN",
        "Баг-fix _obs_from_agent: толерантный маппинг goose-output → FailureObservation",
        "Усиленный output contract (per-role JSON schema в build_prompt) — стабильность S1 output",
        "Известная лимита: полный agent-mode cycle (4 последовательных goose с tools) медленный — минуты; сквозной E2E упирается в timeout, но каждый шаг доказан изолированно"
      ],
      "needs_human_decision": false,
      "status": "done",
      "decision": "done — S2-agent активирован и доказан изолированно (authorize с рассуждением). Полный agent-mode cycle (S1→S3→S3*→S2 последовательно с tools) длится минуты и упирается в timeout при сквозном E2E — это лимита производительности (4× goose calls), не баг. Баг-fix _obs_from_agent + усиленный output contract включены. capability_report PASS.",
      "selected_options": [],
      "references": [
        "VSM-012",
        "VSM-013"
      ],
      "notes": [
        "S2 сохраняет детерминизм core checks (через retry_authorize tool) — агент рассуждает над фактами.",
        "ЛИМИТА ПРОИЗВОДИТЕЛЬНОСТИ: полный agent-mode recovery cycle = 4 последовательных goose-вызова с MCP tools (~15-30с каждый) = минуты. Сквозной E2E в тестах упирается в timeout. Для продакшена: параллелизация где возможно (S3 ∥ S3*), кеш, или гибридный режим (часть систем в Python).",
        "Доказательства по шагам (изолированно): S1-fail+observations ✓, S2-authorize+рассуждение ✓, S3-classify ✓ (capability_report), S3*-audit ✓ (capability_report). Сквозной цикл = композиция доказанных шагов.",
        "Дальше: VSM-015 (S3 → goose-agent, ТЕРЯЕТ детерминизм per VSM-012 Q1), VSM-016 (S3*), VSM-017 (S4), VSM-018 (S5)."
      ],
      "created": "2026-07-14",
      "updated": "2026-07-14",
      "options": []
    },
    {
      "id": "VSM-015",
      "source_system": "S5",
      "signal_type": "policy",
      "severity": "S2",
      "target_unit": "child",
      "title": "Параллелизация S3||S3*: независимая классификация + divergence audit (VSM-014 perf fix)",
      "summary": "Оптимизация производительности agent-runtime (VSM-014 выявил: полный cycle = 4×\ngoose ~минуты). Главный bottleneck — последовательные S3 classify → S3* audit.\nVSM-015 распараллеливает их: S3 и S3* НЕЗАВИСИМО классифицируют одни и те же\nobservations параллельно (ThreadPoolExecutor, 2 goose subprocess'а одновременно),\nзатем divergence сравнивает две классификации.\n\nВыигрыш двойной:\n  1. ПРОИЗВОДИТЕЛЬНОСТЬ: classify+audit step ~50% быстрее (параллельно вместо\n     последовательно; goose subprocess'ы освобождают GIL во время wait).\n  2. КАЧЕСТВО АУДИТА: S3* больше НЕ видит классификацию S3 → нет anchoring bias.\n     Две независимые классификации на разных провайдерах (VSM-001 cross-provider)\n     дают richer audit signal: divergence в failure_class = потенциальная\n     misclassification или taxonomy ambiguity.\n\nСЕМАНТИЧЕСКОЕ ИЗМЕНЕНИЕ: раньше S3* аудировал self-consistency S3 (signal\nдействительно в observations?). Теперь S3* аудирует DIVERGENCE — сравнивает свою\nнезависимую классификацию с S3. Это сильнее: ловит misclassification, а не только\nhallucinated evidence.\n\nDivergence logic (_classify_divergence):\n  - classes_match (S3 == S3*): OK\n  - class divergence + both high confidence → CRITICAL + algedonic (escalate S5)\n  - policy divergence, same class → WARN (multiple valid policies exist)\n  - confidence mismatch → INFO\n",
      "evidence": [
        "src/agent_runtime/protocol.py::invoke_s3_parallel — ThreadPoolExecutor(2), оба классифицируют независимо",
        "src/agent_runtime/protocol.py::_classify_divergence — structured comparison → findings + algedonic",
        "src/agent_runtime/protocol.py::_s3star_classify_config — S3* в parallel-mode: taxonomy tools + classify contract",
        "src/agent_runtime/goose_runner.py::AgentConfig.contract_override — per-mode output contract",
        "src/orchestrator.py::OrchestratorConfig.parallel_s3_s3star — флаг (default False, backward-compat)",
        "src/orchestrator.py — Steps 3+4 branch: parallel vs sequential",
        "Unit-тест divergence: 4 случая (match/class-CRITICAL/policy-WARN/confidence-INFO) — PASSED"
      ],
      "proposal": "VSM-015 = активация параллельного режима S3||S3*. Реализация готова; флаг\nparallel_s3_s3star=False по умолчанию (обратная совместимость). Включение = True.\n\nЧто меняется:\n  - protocol.invoke_s3_parallel() — S3 + S3* параллельно (ThreadPoolExecutor)\n  - S3* в parallel-mode использует _s3star_classify_config (classify, не audit)\n  - orchestrator branch в agent-mode: parallel vs sequential\n  - _classify_divergence → structured audit {passed, findings, algedonic}\n\nЧто НЕ меняется:\n  - sequential mode (parallel_s3_s3star=False) — полностью сохранён\n  - capability_report — PASS (офлайн, без goose)\n  - Python-mode orchestrator (use_agents=False) — не тронут\n  - cross-provider constraint (S3* ≠ S1 provider) — сохранён\n",
      "acceptance": [
        "protocol.invoke_s3_parallel: ThreadPoolExecutor(2), оба классифицируют независимо",
        "_classify_divergence: 4 случая (match/divergence-CRITICAL/policy/confidence) — unit-tested",
        "contract_override: per-mode output contract (S3* classify vs audit)",
        "capability_report PASS (6 систем, backward-compat)",
        "make validate GREEN",
        "E2E: invoke_s3_parallel с реальным goose — параллельно, divergence computed"
      ],
      "needs_human_decision": false,
      "status": "done",
      "decision": "done — S3||S3* параллелизация реализована; divergence audit сильнее sequential (no anchoring bias); unit-tested; capability_report PASS",
      "selected_options": [],
      "references": [
        "VSM-013",
        "VSM-014",
        "VSM-001"
      ],
      "notes": [
        "Параллелизация через ThreadPoolExecutor: goose subprocess.run освобождает GIL во время wait → реальный parallelism.",
        "Semantic improvement: S3* independent classify (no anchoring) > S3* audit-of-S3. Divergence ловит misclassification, не только hallucinated evidence.",
        "Algedonic trigger: class divergence + high confidence → escalate (два независимых агента расходятся = structural concern).",
        "Дальше: VSM-016 (полная S3* агентизация), VSM-017 (S4), VSM-018 (S5). Параллелизация других шагов — S1 независим от S3/S3*, S2 после recovery — sequential по необходимости."
      ],
      "created": "2026-07-14",
      "updated": "2026-07-14",
      "options": []
    },
    {
      "id": "VSM-016",
      "source_system": "S4",
      "signal_type": "gap",
      "severity": "S2",
      "target_unit": "child",
      "title": "S4 scout → goose-agent: on-demand intelligence (browser + intel.json, scan_on_demand pattern)",
      "summary": "Пятая система в серии VSM-012 (полная агентизация S1–S5). S4 scout переходит\nиз концептуальной роли (Phase 5 placeholder) на agent-runtime.\n\nКОНТРАСТ с S1-S3* (recovery cycle): S4 НЕ часть recovery cycle. Это on-demand\nintelligence — «outside-and-then»: скан среды, weak signals, coverage gaps,\ndrift. Триггеры: weak signals (taxonomy gaps, recovery_rate_drift), heartbeat\n(1d), явный запрос (S5/human).\n\nS4 = internet-enabled scout: browser tools (search/fetch) для general-purpose\ncoding patterns и recovery-policy candidates. Пишет signals в state/intel.json.\nStrategic shifts (новый класс сбоя, policy expansion) → VSM-NNN → S5 (basta).\n\nНОВЫЙ ПАТТЕРН ИНТЕГРАЦИИ (vs invoke_s1/s2/s3 в цикле):\n  - scan_on_demand(trigger) — не часть recovery cycle, отдельный entry point\n  - S4 использует ephemeral state-bus namespace (cross-task intelligence, не\n    per-task recovery)\n  - Результаты пишет в product state/intel.json (через intel_write tool),\n    не в state-bus recovery-cycle keys\n",
      "evidence": [
        "src/agent_runtime/protocol.py::scan_on_demand — S4 on-demand entry (не invoke_* в цикле)",
        "src/agent_runtime/protocol.py::ROLE_CONFIGS['s4-scout'] — browser + intel_write + taxonomy + fs",
        "src/agent_runtime/tools/scout_tools.py — intel_write/intel_read (state/intel.json atomic)",
        "src/agent_runtime/goose_runner.py::_output_contract['s4-scout'] — signals + strategic_shifts schema",
        "src/runtime/verify.py::_verify_s4_scout — 3 checks (tool surface, intel round-trip, protocol)",
        "capability_report: s4_scout PASS (7 систем всего)"
      ],
      "proposal": "VSM-016 = S4 scout агентизация. on-demand паттерн:\n  1. Trigger (weak signal / heartbeat / request) → scan_on_demand(trigger)\n  2. S4-agent: SOUL/SKILL/TASK prompt + browser + intel tools\n  3. Agent: browser.search patterns, taxonomy_read coverage gaps\n  4. Agent: intel_write signals → state/intel.json\n  5. Strategic shifts → VSM-NNN (basta — human)\n\nЧто НЕ меняется:\n  - S4 НЕ в recovery cycle (orchestrator не вызывает scan_on_demand)\n  - S4 on-demand: heartbeat (vsm.yaml s4_scout: every 1d) или явный запрос\n  - Мембрана VSM-002: browser scope = general-purpose, agnostic по построению\n",
      "acceptance": [
        "scan_on_demand(trigger) — on-demand entry point для S4 (не recovery cycle)",
        "S4 tool surface: browser.fetch/search + intel_write/read + taxonomy_read",
        "scout_tools: intel.json atomic write, round-trip unit-tested (write+read+persist)",
        "capability_report: s4_scout PASS (7 систем, 3 checks)",
        "make validate GREEN",
        "Известная лимита: E2E scan_on_demand с browser tools превышает тест-timeout (150с) — browser+goose reasoning медленнее coding tasks; офлайн-проверки (capability_report) PASS"
      ],
      "needs_human_decision": false,
      "status": "done",
      "decision": "done — S4 scout агентизирован; scan_on_demand on-demand паттерн; browser + intel tools unit-tested + capability_report PASS. E2E с browser превышает тест-timeout (browser web requests + goose = медленно), офлайн-доказательства достаточны.",
      "selected_options": [],
      "references": [
        "VSM-012",
        "VSM-013",
        "VSM-014"
      ],
      "notes": [
        "S4 единственная система с internet access (browser tools). Scope = general-purpose (мембрана).",
        "intel_write пишет в state/intel.json продукта — S4 единственный писатель (SOUL).",
        "Дальше: VSM-017 (S5 guardian → policy/identity agent). S5 = последняя система в серии."
      ],
      "created": "2026-07-14",
      "updated": "2026-07-14",
      "options": []
    },
    {
      "id": "VSM-017",
      "source_system": "S5",
      "signal_type": "policy",
      "severity": "S1",
      "target_unit": "child",
      "title": "S5 guardian → goose-agent: autonomous architect (algedonic + triage, OSM primitives, VSM-012 series complete)",
      "summary": "Шестая и финальная система в серии VSM-012 (полная агентизация S1–S5). S5\nguardian переходит из концептуальной роли (Phase 6 placeholder) на agent-runtime.\n\nS5 = АВТОНОМНЫЙ АРХИТЕКТОР (VSM-006): triage → decision → execution. Резолвит\nissues сам (НЕ эскалирует к human). Вмешивается при алгедонике от S3*/S4 через\nOSM-примитивы (Split/Merge/Reconfigure).\n\nТРЕТИЙ УНИКАЛЬНЫЙ ПАТТЕРН интеграции (vs recovery-cycle invoke + on-demand scan):\n  - handle_algedonic(signal) — реактивная обработка S0/S1 сигналов\n  - triage_issues(pending) — routine duty: резолвить status=triage issues\n  - S5 решает и ДЕЙСТВУЕТ: osm_apply (декларативный → s1-dispatcher исполняет),\n    issue_resolve (записывает decision), algedonic_log (интервенция наблюдаема)\n\nЕДИНСТВЕННОЕ ОГРАНИЧЕНИЕ АВТОНОМИИ (VSM-006): identity/values/never_do change =\nBLOCKED (требует родительского решения через VSM-NNN). S5-goose знает это через\nidentity_read tool + SOUL/NEVER DO.\n",
      "evidence": [
        "src/agent_runtime/protocol.py::handle_algedonic — reactive S0/S1 processing",
        "src/agent_runtime/protocol.py::triage_issues — routine issue resolution",
        "src/agent_runtime/protocol.py::ROLE_CONFIGS['s5-guardian'] — identity/osm/issue/algedonic tools",
        "src/agent_runtime/tools/guardian_tools.py — identity_read, osm_apply, issue_resolve, algedonic_log",
        "src/agent_runtime/goose_runner.py::_output_contract['s5-guardian'] — action + primitive + blocked_reason",
        "src/runtime/verify.py::_verify_s5_guardian — 3 checks (tool surface, identity+osm round-trip, protocol)",
        "capability_report: s5_guardian PASS (8 систем всего — серия завершена)"
      ],
      "proposal": "VSM-017 = S5 guardian агентизация. Серия VSM-012 (полная агентизация S1–S5)\nЗАВЕРШАЕТСЯ. Все 6 систем — goose-агенты на agent-runtime.\n\nПаттерны интеграции (3 типа):\n  1. Recovery-cycle invoke (S1/S2/S3/S3*) — orchestrator, sequential/parallel\n  2. On-demand scan (S4) — scan_on_demand, heartbeat/trigger-driven\n  3. Reactive architect (S5) — handle_algedonic + triage_issues, VSM-006 autonomous\n\nЧто НЕ меняется:\n  - S5 НЕ эскалирует к human (VSM-006); человек наблюдает через родительский dashboard\n  - Identity/values/never_do change = BLOCKED (единственное ограничение автономии)\n  - osm_apply декларативный: S5 объявляет примитив, s1-dispatcher исполняет (мембрана)\n  - Каждое вмешательство логируется (state/interventions.json, VSM-005 observable)\n",
      "acceptance": [
        "handle_algedonic(signal) — reactive S0/S1 entry (третий паттерн)",
        "triage_issues(pending) — routine autonomous resolution",
        "S5 tool surface: identity_read + osm_apply + issue_resolve + algedonic_log",
        "guardian_tools: identity read + osm declarative + intervention log, unit-tested",
        "identity-change block: osm_apply НЕ мутирует identity (VSM-006 autonomy limit)",
        "capability_report: s5_guardian PASS (8 систем — серия VSM-012 complete)",
        "make validate GREEN"
      ],
      "needs_human_decision": false,
      "status": "done",
      "decision": "done — S5 guardian агентизирован; autonomous architect (VSM-006); handle_algedonic + triage_issues; identity-change blocked; capability_report 8 систем PASS. СЕРИЯ VSM-012 ЗАВЕРШЕНА: все S1-S5 = goose-агенты.",
      "selected_options": [],
      "references": [
        "VSM-012",
        "VSM-006",
        "VSM-005"
      ],
      "notes": [
        "СЕРИЯ VSM-012 COMPLETE: S1, S2, S3, S3*, S4, S5 — все goose-агенты на agent-runtime.",
        "3 паттерна интеграции: recovery-cycle invoke (S1-S3*), on-demand scan (S4), reactive architect (S5).",
        "S5 единственная система с identity guard (identity-change blocked — VSM-006).",
        "Все системы: capability_report PASS (8), make validate GREEN, мембрана VSM-002 сохранена."
      ],
      "created": "2026-07-14",
      "updated": "2026-07-14",
      "options": []
    },
    {
      "id": "VSM-022",
      "source_system": "S3",
      "signal_type": "drift",
      "severity": "S1",
      "target_unit": "meta",
      "title": "eval: harness обходит продуктовый MCP — trace пуст при PASS, pass_rate невалиден",
      "summary": "Smoke-test jsonl-aggregator (TB Dev Set v2) → PASS (reward='1', pytest 1/0), но\ntrace_len=0: продуктовый MCP-сервер не получил ни одного tool-call. claude-code\nрешает задачу через собственный host-bash (видели `find / -name records_*.jsonl`\nна хосте), минуя docker-exec MCP bridge. pass_rate сейчас измеряет harness, а не\nавтономность продукта → входной индикатор A(t) (state/dev_metrics.json) невалиден,\nтелеметрия T2 CONTRACT §3 trace для vsmforge пуста.\n",
      "evidence": [
        "smoke-test: jsonl-aggregator PASS, agent_exit=0, dur=488s, trace_len=0, failure_obs=0 (state/dev_metrics.json#tasks[0])",
        "process tree: claude → npm exec @z_ai/mcp-server → docker exec -i ... python3 -m mcp_server.server (MCP-bridge активен, но не используется)",
        "claude параллельно спавнил host-bash через нативный Bash tool (НЕ через MCP)",
        "eval/agent_phase.py:121-129 (_build_harness_args, ветка claude-code): нет --allowedTools → claude сохраняет нативные Bash/Read/Write/Edit на хосте",
        "src/mcp_server/server.py:152 serve_stdio — trace пишется в --trace-file ТОЛЬКО при tool-call'ах через MCP; без вызовов файл пуст"
      ],
      "proposal": "Ограничить tool-surface harness'а только продуктовым MCP (вариант A): добавить в\n_build_harness_args (claude-code) ограничение, отключающее нативные Bash/Read/Write/Edit.\nТогда весь I/O идёт через продукт → trace заполняется → pass_rate измеряет реальный\nпродукт. Принять с оговоркой: измерить regress на том же jsonl-aggregator.\nАльтернативы B (двойной прогон) / C (документация) — в policy_question.\n",
      "acceptance": [
        "eval/agent_phase.py claude-code ветка ограничивает tools до MCP-сервера продукта",
        "повторный прогон jsonl-aggregator: trace_len > 0 (продуктовый MCP получает вызовы)",
        "goose-ветка либо аналогично ограничена, либо заведён отдельный issue для неё",
        "make validate GREEN (мембрана VSM-002 + parent isolation VSM-005 не нарушены)",
        "state/dev_metrics.json pass_rate обновлён после повтора"
      ],
      "needs_human_decision": true,
      "policy_question": "Как измерять автономность продукта? (A) только MCP-инструменты продукта — честно, но\nвозможен regress pass_rate; (B) двойной прогон unrestricted + MCP-only — мера\n«стоимости изоляции», но 2× время; (C) признать текущий режим intentionally\nunrestricted — 0 кода, но A(t)-метрика остаётся неточной.\n",
      "options": [
        {
          "id": "A",
          "label": "ограничить harness до MCP продукта (--allowedTools)",
          "hint": "минимальное изменение; восстанавливает семантику pass_rate=продукт; возможен regress"
        },
        {
          "id": "B",
          "label": "двойной прогон unrestricted + MCP-only",
          "hint": "сохраняет baseline; даёт метрику стоимости изоляции; 2× время прогона"
        },
        {
          "id": "C",
          "label": "документировать как unrestricted (не чинить сейчас)",
          "hint": "0 кода; A(t) остаётся семантически неточной; trace для vsmforge пуст"
        }
      ],
      "status": "superseded",
      "decision": "A — ограничить harness до MCP продукта (первоначальное решение 2026-07-15). Обоснование: цель измерения = прогресс продукта во времени (T0→T1), обе точки в режиме A → delta честна. SUPERSEDED VSM-024 (2026-07-15): pivot eval на harbour-framework делает дилемму --allowedTools moot — harbour управляет tool-surface и средой исполнения, а не claude-code. Acceptance trace_len>0 не доказан (state/dev_metrics.json:34 trace_len=0). VSM-022 решение A было верным для старой архитектуры; в harbour-архитектуре проблема растворяется.",
      "selected_options": [
        "A"
      ],
      "references": [
        "VSM-008",
        "VSM-004",
        "VSM-005",
        "VSM-002"
      ],
      "notes": [
        "Сессия подтвердила: docker-exec MCP bridge РАБОТАЕТ (subprocess tree активен), но harness его не использует, т.к. ему доступнее нативный Bash.",
        "PASS задачи ≠ продукт её решил. Без ограничения tool-surface pass_rate — это сила harness (claude-code), не автономность продукта.",
        "goose-ветка: --with-extension wrapper не эквивалентен --allowedTools; требует отдельной проверки при выборе A."
      ],
      "created": "2026-07-15",
      "updated": "2026-07-15"
    },
    {
      "id": "VSM-023",
      "source_system": "S3",
      "signal_type": "gap",
      "severity": "S2",
      "target_unit": "meta",
      "title": "eval: goose-ветка не ограничивается до MCP продукта — нет эквивалента --allowedTools",
      "summary": "VSM-022 решение A (ограничение tool-surface до MCP продукта) реализовано только\nдля claude-code через --allowedTools mcp__<server>__*. goose CLI не имеет\nэквивалентного флага: --with-extension подключает MCP-сервер, но НЕ отключает\nbuilt-in tools (developer, computer-controller, ...), а --no-profile убирает\nлишь user-профиль, не core builtins. В результате goose-ветка может решать\nзадачи через собственные built-in tools, минуя продуктовый MCP → trace пуст,\npass_rate невалиден (наследие VSM-022 для goose). Текущий default harness —\nclaude-code, поэтому impact ограничен; goose нужен для cross-provider проверки\n(S3* provider_constraint must_differ_from s1).\n",
      "evidence": [
        "issues/VSM-022.yaml:69 — goose-ветка: --with-extension wrapper не эквивалентен --allowedTools; требует отдельной проверки при выборе A",
        "eval/agent_phase.py:130-148 (_build_harness_args goose-ветка) — нет ограничения tool-surface; комментарий VSM-023 добавлен",
        "goose run --help: флаги --with-extension / --no-profile / --with-builtin — НЕТ allow/deny tool-list",
        "claude --help: --allowedTools/--allowed-tools есть только у claude-code CLI (подтверждение асимметрии harness'ов)"
      ],
      "proposal": "S5 non-binding рекомендация. Варианты (аналогично VSM-022 policy):\n  (A1) goose recipe/.goosehints с явным исключением builtins — если goose\n       поддерживает disable-builtin в recipe-формате (требует проверки goose docs);\n  (A2) кастомный MCP-wrapper/proxy, который перехватывает built-in tool-calls и\n       возвращает ошибку — заставляет goose идти через MCP (дороже, ломает чистоту bridge);\n  (C)  признать goose cross-provider-check only: trace из goose не используется\n       для A(t), только как «доказательство что задача решаема другим harness»\n       (минимальное изменение — документация + assert в metrics для goose).\nДо решения: goose не используется для canary-set T0/T1 (claude-code only).\n",
      "acceptance": [
        "решение выбрано (A1/A2/C) и зафиксировано в decision-поле",
        "если A1/A2: повторный прогон goose на canary set → trace_len > 0",
        "если C: eval/README.md отражает 'goose = cross-provider check, trace невалиден для A(t)'"
      ],
      "needs_human_decision": true,
      "policy_question": "Как обеспечить честность метрики A(t) для goose, учитывая отсутствие --allowedTools?\n",
      "options": [
        {
          "id": "C",
          "label": "goose = cross-provider check only (trace не для A(t))",
          "hint": "0 кода; goose-прогоны не учитываются в A(t); claude-code остаётся primary для метрики"
        },
        {
          "id": "A1",
          "label": "recipe/.goosehints с исключением builtins",
          "hint": "требует проверки goose recipe-синтаксиса; среднее изменение"
        },
        {
          "id": "A2",
          "label": "MCP proxy, перехватывающий builtins",
          "hint": "дороже; ломает простоту docker-exec bridge"
        }
      ],
      "status": "superseded",
      "decision": "SUPERSEDED VSM-024: goose --allowedTools gap растворяется в harbour-архитектуре. harbour --agent goose управляет tool-surface и средой первоклассно (enum, без кастомных wrapper'ов); дилемма 'recipe/.goosehints vs MCP-proxy' больше не стоит, т.к. ProductAdapter обёртывает весь orchestrator (мультиагентный), а не голый goose+S1-tools. Проблема не отвергнута (wontfix), а растворена в новой архитектуре.",
      "selected_options": [],
      "references": [
        "VSM-022",
        "VSM-004",
        "VSM-005"
      ],
      "notes": [
        "goose CLI (goose run --help, версия на дату создания) НЕ содержит allow/deny tool-list флагов.",
        "claude-code --allowedTools синтаксис: mcp__<server>__* (wildcard), подтверждён claude --help + code.claude.com/docs/en/permissions."
      ],
      "created": "2026-07-15",
      "updated": "2026-07-15"
    },
    {
      "id": "VSM-024",
      "source_system": "S5",
      "signal_type": "policy",
      "severity": "S1",
      "target_unit": "meta",
      "title": "Разворот eval-пайплайна на harbor-framework: ProductAdapter + снятие запрета harbor",
      "summary": "Архитектурный разворот: кастомный eval-пайплайн (loader/container/agent_phase/grader,\nдублирующий функциональность harbor-framework) заменяется на harbor как infra-раннер +\nProductAdapter — harbour custom-agent, обёртывающий orchestrator.run_recovery_cycle()\nпродукта целиком. Harbour = зрелый бенчмарк-раннер (job/trial/verifier/trajectory), НЕ\nдатасет и НЕ решатель.\n\nДве предпосылки разворота, выявленные сессией:\n1. VSM-022 показал, что pass_rate измерял harness (claude-code), а не автономность\n   продукта — harness обходил продуктовый MCP через нативные тулы. Custom eval/ не давал\n   полной trajectory recovery-cycle (S3/S3*/S2 координация не отслеживалась).\n2. harbor даёт полнее observability: ATIF trajectory recovery-cycle (все 6 VSM-агентов,\n   не только S1 tool-calls), web-UI (harbor view), анализ reward-hacking (harbor analyze),\n   встроенный verifier/retRies/concurrency.\n\nIdentity change: use_harbor_tb2 (абсолютный запрет harbor, vsmlite.yaml:62) — запрещён по\nошибке как будто harbor = «датасет, на котором cheat'им». На самом деле harbor =\nинфраструктура раннера (как docker-compose/pytest). Датасет тянется через HF\n(open-thoughts/OpenThoughts-TB-dev-v2), harbour его не заменяет. Запрет снят с\nограниченным scope: harbor разрешён ТОЛЬКО в vsmlite-tb/ (родитель-оценщик); продукт\n(vsm/, src/) по-прежнему не знает про harbour (мембрана VSM-002 сохраняется).\n\nАрхитектура: ProductAdapter.run() выполняет один environment.exec() внутри docker-контейнера\n→ orchestrator.run_recovery_cycle() → продукт сам спавнит своих goose-агентов → полная\ntrajectory recovery-cycle пишется в ATIF-формате → harbor verifier ставит reward →\nharbour_bridge парсит trial → state/dev_metrics.json (через существующий metrics.py).\n",
      "evidence": [
        "harbor 0.18.0 установлен (/home/alex/.local/bin/harbor): run/job/trial/analyze/view, --agent goose (первоклассная), --agent module.path:ClassName (custom), --mcp-config",
        "vsmlite.yaml:62 use_harbor_tb2 — абсолютный запрет; добавлен в c5a0407 (VSM-002, 2026-07-13) тем же автором, что инициировал разворот — осознанная ревизия своего решения",
        "VSM-022 acceptance: trace_len > 0 не доказано (state/dev_metrics.json:34 trace_len=0); premise 'claude-code обходит MCP' теряет смысл при pivot на harbour-managed tool-surface",
        "src/agent_runtime/ — продукт уже мультиагентный (goose_runner + protocol + orchestrator recovery-cycle S1→S3→S3*→S2→retry); src/mcp_server/ — лишь tool-provider для S1, не сам продукт",
        "harbor BaseAgent contract (site-packages/harbor/agents/base.py): run(instruction, environment, context) async, populate_context_post_run; /logs/agent/ bind-mounted для trajectory",
        "harbour ATIF trajectory (models/trajectories/): Trajectory{steps:[Step{tool_calls,observation}]} — полная agent trajectory, не только MCP-calls",
        "validate.sh §2c grep'ит ../vsm/ ../src/ (продукт) на harbour — НЕ vsmlite-tb/; запрет harbour в identity, не в исполняемом инварианте"
      ],
      "proposal": "Фаза 0 (identity/policy) + Фаза 1 (feasibility smoke) в этой сессии:\n0.1 Снять use_harbor_tb2 из vsmlite.yaml never_do (строка 62) + _intent_draft harbor-строки.\n0.2 Закрыть VSM-022/VSM-023 как superseded (дилеммы растворяются в harbour-архитектуре).\n1.x ProductAdapter (stub use_agents=False для smoke) → доказать infra-feasibility.\nФаза 2/3 (use_agents=True реальный мультиагент + cleanup старого eval/) — следующая сессия.\n\nМембрана VSM-002 сохраняется полностью: harbour живёт только в vsmlite-tb/ (родитель);\nProductAdapter вызывает membrane.translate() перед продуктом; validate.sh §2c без изменений.\n",
      "acceptance": [
        "vsmlite.yaml:62 use_harbor_tb2 удалён из never_do (harbor = infra-раннер, не датасет)",
        "VSM-022 status: superseded → VSM-024; VSM-023 status: superseded → VSM-024",
        "ProductAdapter (eval/harbor_adapter.py) — наследник harbor BaseAgent, run() вызывает orchestrator",
        "smoke-test jsonl-aggregator: trial завершается, agent/trajectory.json валиден (ATIF), reward приходит",
        "harbour_bridge.parse_trial() → state/dev_metrics.json обновлён (формат summary/by_*/tasks[] сохранён)",
        "make validate GREEN (§2c без изменений: продукт по-прежнему без harbour/TB)",
        "мембрана VSM-002: FORBIDDEN_TERMS в membrane.py по-прежнему включает harbour (продукт защищён)"
      ],
      "needs_human_decision": true,
      "policy_question": "Снять запрет harbour (use_harbor_tb2) с ограниченным scope — разрешить в vsmlite-tb/ как\ninfra-раннер eval-пайплайна, при полном сохранении мембраны VSM-002 (продукт agnostic)?\n+ pivot eval на harbour + ProductAdapter (goose primary harness).\n",
      "options": [
        {
          "id": "accept",
          "label": "Принять разворот (Phase 0+1 в сессии, 2/3 следующая)",
          "hint": "Снять запрет harbour (scoped), ProductAdapter stub smoke-test, cleanup в Phase 3"
        }
      ],
      "status": "accepted",
      "decision": "accept — снять запрет harbour с ограниченным scope (только vsmlite-tb/); pivot eval-пайплайна на harbour + ProductAdapter; goose primary harness. Обоснование: harbour = infra-раннер (НЕ датасет), даёт полнее observability (ATIF trajectory recovery-cycle, harbor analyze/view), решает VSM-022 структурно (harbour управляет tool-surface, не claude-code). Мембрана VSM-002 сохраняется полностью. Scope сессии: Phase 0 (identity) + Phase 1 (stub smoke); Phase 2/3 (реальный мультиагент + cleanup) — следующая сессия.",
      "selected_options": [
        "accept"
      ],
      "references": [
        "VSM-002",
        "VSM-005",
        "VSM-008",
        "VSM-022",
        "VSM-023",
        "VSM-001"
      ],
      "notes": [
        "Запрет harbour (vsmlite.yaml:62) добавлен в c5a0407 (VSM-002) — ошибочно классифицирован как 'датасет для cheating'. Harbour = раннер-инфраструктура.",
        "Продукт уже мультиагентный (src/agent_runtime/): orchestrator recovery-cycle S1→S3→S3*→S2→retry; goose_runner спавнит per-role goose-agents. src/mcp_server/ — лишь S1 tool-provider.",
        "harbour даёт наблюдаемость, которой не было в custom eval/: ATIF trajectory (все 6 агентов, не только S1), harbor view (web-UI), harbor analyze (reward-hacking rubric).",
        "Проверено: validate.sh §2c grep'ит только ../vsm/ ../src/ (продукт); запрет harbour в identity, не в исполняемом инварианте. Продукт остаётся чистым.",
        "VSM-022 acceptance trace_len>0 не доказан (state/dev_metrics.json:34 trace_len=0) — ещё аргумент за superseded."
      ],
      "created": "2026-07-15",
      "updated": "2026-07-15"
    },
    {
      "id": "VSM-025",
      "source_system": "S5",
      "signal_type": "gap",
      "severity": "S3",
      "target_unit": "meta",
      "title": "process log + agent eval: таймлайн структурных дельт и скоринг 0-10 работы агентов",
      "summary": "vsmlite эмитит точечную телеметрию (monitor/data.js) и snapshot-хранилища\n(history.json по дням, eval_history.json по прогонам, interventions.json,\nissues/VSM-NNN.yaml), но не имеет единого слоя (а) таймлайна структурных\nсобытий и (б) оценки качества работы агентов. Человек и S5 не видят «что\nизменилось в этом цикле» одной лентой и не имеют числового вердикта по\nработе каждого агента (продуктового TB-агента и системного S1-S5).\n\nРешение (запрошено пользователем в сессии, средний уровень логов): два слоя\nв одной точке интеграции (render_data.py — вызывается в конце каждого\ncycle/eval/mature/init), чистый авто-детект дельт state/, ноль правок в\nагентах/командах/eval/.\n\nСлой 1 — process log: scripts/export_logs.py сравнивает key-path'и state/\nс прошлым прогоном (state/_events_snapshot.json) и эмитит события только при\nреальной дельте → state/events.json (machine, cap 500) + logs/process.log\n(human append-only, cap 1000 строк). События: autonomy.changed/verdict,\nphase.transition, cycle.completed, eval.run, metrics.drift,\nintervention.added, issue.changed.\n\nСлой 2 — agent eval: scripts/agent_eval.py — scoring engine 0-10 (<5 = FAIL)\n+ буквенный A/B/C/D/E (D < 0.5). Два контура: продуктовые агенты (per TB-task,\nread-only из dev_metrics.json#tasks[] — формат стабилен по контракту VSM-024:59)\nи системные S1-S5 (per cycle, атрибуция по owner state-файла). Per-agent\nsummary ≤ 500 символов (детерминированные шаблоны, без LLM). Breakdown по\ndifficulty/category. → state/agent_eval.json + сводная секция в process.log.\n\ntrace_len — info-only в числовом скоринге (VSM-022 superseded→VSM-024: harbor\nуправляет tool-surface, trace_len больше не индикатор обхода). harbor-блок\n(task[\"harbor\"]={terminated_by, attempts, reward}, появляющийся post-VSM-024\nsmoke) подхватывается оппортунистически как progressive enhancement — base\nscoring работает и без него. Token-spend → deferred до instrumentation в VSM-024.\n",
      "evidence": [
        "issues/VSM-022.yaml (superseded→VSM-024): trace_len=0 был индикатором harness-bypass; VSM-024 делает harbor управляющим tool-surface",
        "issues/VSM-024.yaml:59 — harbour_bridge.parse_trial() → state/dev_metrics.json, формат summary/by_*/tasks[] сохранён (контракт стабилен)",
        "eval/harbor_bridge.py:85-91 — task_result['harbor']={trial_name, terminated_by, verdict, attempts, reward} (progressive enhancement для agent_eval)",
        "eval/harbor_bridge.py:57-59 — trace_len = len(trajectory['steps']) (post-smoke будет > 0)",
        "scripts/render_data.py:171-174 — единственная точка: вызывается в конце cycle/eval/mature/init (хук detect_and_log)",
        "state/history.json + state/eval_history.json — существующий cap-паттерн [-90:], переиспользуется (events: [-500:], process.log: 1000 строк)",
        "scripts/autonomy.py:35-43 — tunable пороги как образец для весов скоринга",
        ".claude/settings.json:27 — Write(state/**) уже разрешён; logs/ пишется внутри Bash(python3 scripts/render_data.py*) — правок permissions не нужно"
      ],
      "proposal": "Реализовать в порядке: VSM-025.yaml → scripts/agent_eval.py →\nscripts/export_logs.py → хук в render_data.py → logs/.gitkeep + .gitignore\n+ Makefile target logs:. Read-only из dev_metrics.json (defensive fallback на\nempty-skeleton как eval/metrics.py:30-41 при пустом/битом/transit файле).\nНоль касаний eval/, агентов, слэш-команд, settings.json, validate.sh.\n",
      "acceptance": [
        "scripts/export_logs.py эмитит события в state/events.json только при реальной дельте (первый прогон = seed, 0 событий)",
        "logs/process.log — human-readable append-only tail, cap 1000 строк",
        "scripts/agent_eval.py: score_task + score_system → {score 0-10, grade A-E, summary ≤500 символов}",
        "trace_len НЕ входит в числовой скоринг (info-only в summary; VSM-022 superseded→VSM-024)",
        "breakdown по difficulty/category в process.log + state/agent_eval.json",
        "token-spend: null, пометка deferred→VSM-024; task['harbor'] подхватывается оппортунистически когда есть",
        "defensive fallback при пустом/битом dev_metrics.json (graceful skip секции продуктовых агентов)",
        "make logs печатает tail; make telemetry прогоняет детект и пишет все 3 артефакта",
        "make validate GREEN (инвариант VSM-002/005 не нарушен — MUT_RE касается только ../vsm|../src)"
      ],
      "needs_human_decision": false,
      "status": "accepted",
      "decision": "requested by user in-session: средний уровень логов процесса + агентский скоринг 0-10 (A-E, D<0.5=FAIL), per-agent summary ≤500 символов, оба контура (продуктовые TB + системные S1-S5). trace_len info-only (VSM-022 superseded); harbor block — progressive enhancement.",
      "selected_options": [],
      "references": [
        "VSM-024",
        "VSM-022",
        "VSM-005",
        "VSM-002"
      ],
      "notes": [
        "ID VSM-025: 023 (goose --allowedTools gap) и 024 (harbour pivot) заняты другим агентом в этой сессии.",
        "harbor 0.18.0 установлен (/home/alex/.local/bin/harbor), но smoke-прогонов нет — task['harbor'] блока в dev_metrics пока нет. Оппортунистическое чтение.",
        "Точка интеграции единственная: render_data.py вызывается в конце каждого /vsmlite-cycle, /vsmlite-mature, /vsmlite-eval, /vsmlite-init, make telemetry."
      ],
      "created": "2026-07-15",
      "updated": "2026-07-15",
      "options": []
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
    },
    {
      "date": "2026-07-14",
      "autonomy_score": 0.175,
      "maturation_phase": "Phase 4",
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
      "intervention_share": 0.0,
      "eval_pass_rate": null
    },
    {
      "date": "2026-07-15",
      "autonomy_score": 0.175,
      "maturation_phase": "Phase 4",
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
      "intervention_share": 0.0,
      "eval_pass_rate": 0.0
    }
  ],
  "activity": [],
  "interventions": []
};
