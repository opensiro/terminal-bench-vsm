window.VSM_DATA = {
  "generated": "2026-07-13T20:48:13",
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
    }
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
      }
    }
  ],
  "activity": []
};
