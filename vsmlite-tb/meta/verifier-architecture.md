# Verifier Architecture — как reward течёт от TB test.sh до A(t)

> Зафиксировано при планировании VSM-037 (true-verifier). ASCII-схема
> verifier-фазы: кто кого вызывает, где reward возникает, куда вставлен
> true-verifier (post-trial attribution).

## Полная цепочка

```
┌─ HOST (vsmlite-tb) ──────────────────────────────────────────────────┐
│                                                                       │
│  eval/harbor_run.py:run_trial                                         │
│    1. _prepare_overlay_task → overlay Dockerfile (goose+uv+pip+deps)  │
│       └─ VSM-035: COPY --from=vsm-tools:<profile> (zero network)      │
│       └─ VSM-036: mkdir /app + WORKSPACE-probe                        │
│    2. render harbor_config_template.yaml (нет [verifier] секции)      │
│    3. subprocess: `harbor trial start --path <overlay> --config <yml>`│
│         │                                                             │
│         ▼                                                             │
└─────────│─────────────────────────────────────────────────────────────┘
          │  vsmlite НЕ запускает test.sh — это работа harbour
          ▼
┌─ HARBOUR (внешний eval framework, host process) ─────────────────────┐
│                                                                       │
│  Trial._prepare → docker build (overlay image) → docker run          │
│         │                                                             │
│         ▼                                                             │
│  ┌─ CONTAINER (overlay image: task-base + goose/uv/pip/wheels) ────┐ │
│  │                                                                  │ │
│  │  bind-mount: host trial_dir/agent/    → /logs/agent/             │ │
│  │  bind-mount: host trial_dir/verifier/ → /logs/verifier/          │ │
│  │  bind-mount: host src/  → /opt/vsm_src  (read-only)              │ │
│  │  bind-mount: host vsm/  → /opt/vsm      (read-only)              │ │
│  │  bind-mount: host eval/ → /opt/eval_shim(read-only)              │ │
│  │                                                                  │ │
│  │  ═══ ФАЗА 1: AGENT (продукт работает) ═══                        │ │
│  │  harbour → ProductAdapter.run(instruction, env, context)         │ │
│  │    membrane.translate(instruction) → task_prompt.txt             │ │
│  │    env.exec("python3 orchestrator_runner.py --workspace $WS")    │ │
│  │       │                                                          │ │
│  │       ▼  ПРОДУКТ (../src recovery cycle, goose sub-agents)       │ │
│  │       модифицирует /app: создаёт файлы, запускает команды        │ │
│  │       пишет product-trace.json → /logs/agent/                    │ │
│  │         └ s1_trace, s1_verify, s1_control.verdict, s1_artifacts  │ │
│  │                                                                  │ │
│  │  ═══ ФАЗА 2: VERIFIER (ТОТ ЖЕ контейнер, НЕ restart) ═══         │ │
│  │  harbour Verifier.verify():                                      │ │
│  │    upload tests/ → /tests/  (TB test.sh + test_outputs.py)       │ │
│  │    chmod +x /tests/test.sh                                       │ │
│  │    env.exec("bash /tests/test.sh")                               │ │
│  │       │                                                          │ │
│  │       ▼  test.sh ВНУТРИ контейнера                               │ │
│  │       видит: overlay-deps (pip!) + продукт-модификации /app      │ │
│  │       pytest /tests/test_outputs.py → pass/fail                  │ │
│  │       echo 1|0 > /logs/verifier/reward.txt  ─────────┐           │ │
│  │                                                       │           │ │
│  └───────────────────────────────────────────────────────│───────────┘ │
│                                                          │             │
│  harbour читает reward.txt → result.json.verifier_result │             │
│         │                                                │             │
└─────────│────────────────────────────────────────────────│─────────────┘
          ▼                                                ▼
┌─ HOST (vsmlite-tb, post-hoc) ─────────────────────────────────────────┐
│                                                                       │
│  eval/harbor_bridge.py:parse_trial:                                   │
│    _parse_reward: reward.txt (или result.json fallback) → reward      │
│    task_result["harbor"] = {reward, terminated_by, verdict, ...}      │
│    metrics.record → dev_metrics.json (TB pass-rate)                   │
│                                                                       │
│  ═══ TRUE-VERIFIER (VSM-037, ЗДЕСЬ) ═══                               │
│  scripts/true_verifier.py:verify_trial(trial_dir):                    │
│    читает result.json + product-trace.json                            │
│    если reward==1.0 + s1_control==fail_no_checkpoint                  │
│           + terminated_by==no_observations + s1_artifacts==[]         │
│       → strict_verdict = "false_positive" (overlay-collision)         │
│    иначе если reward==1.0 + есть work-signals                         │
│       → strict_verdict = "genuine_pass"                               │
│    иначе → "fail" / "unknown"                                         │
│    НЕ затирает TB reward — добавляет strict_verdict рядом              │
│                                                                       │
│  task_result["harbor"]["strict_verdict"]  (genuine_pass/false_pos/..) │
│  task_result["harbor"]["strict_reward"]   (1.0 только genuine_pass)   │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

## Ключевые принципы

1. **TB `tests/test.sh` = ground truth**, детерминистический. LLM-judge НЕ нужен
   (0% задач требуют — все проверяются pytest/grader скриптами).

2. **Verifier работает в ТОМ ЖЕ контейнере** где работал продукт (harbour default
   `environment_mode: shared`). Видит overlay-deps + продукт-модификации /app.

3. **Проблема = overlay-collision** (VSM-037): overlay ставит deps (pip, ...),
   test.sh проверяет их как «продукт решил» → reward=1.0 без действий продукта.
   broken-python: overlay-pip → test `import pip` → false-positive PASS.

4. **True-verifier = post-trial attribution** (детерминистический, no LLM):
   reward=1.0 от продукта или от overlay? Сигнатура false-positive:
   `s1_control=fail_no_checkpoint + no_observations + s1_artifacts=[]`.

5. **Inner-verifier** (в продукте, `../src/`) — отдельная сущность, не трогаем.
   Продукт сам judge'ит себя в recovery-cycle (s1_verify, s1_control).

## Слои верификации

| Слой | Где | Что проверяет | Vertra |
|---|---|---|---|
| **TB test.sh** | harbour, контейнер | ground truth: задача решена? | 1.0/0.0 reward |
| **inner-verifier** | продукт `../src/` (s1_control) | продукт judge'ит себя: я решил? | verdict (pass/fail_no_checkpoint/..) |
| **true-verifier** | vsmlite scripts/ (post-trial) | атрибуция: reward от продукта или overlay? | strict_verdict (genuine/false_positive) |

## Артефакты trial'а (источники сигналов для true-verifier)

```
state/harbor-trials/<trial>/
├── result.json                    # reward (TB), terminated_by, verdict, timing
├── agent/
│   ├── trajectory.json            # ATIF steps, tool_calls, final_metrics
│   ├── product-trace.json         # s1_trace, s1_control.verdict, s1_artifacts ← КЛЮЧ
│   ├── task_prompt.txt            # neutralized instruction (membrane applied)
│   └── product-stdout.log         # raw product output
└── verifier/
    ├── reward.txt                 # 1 или 0 (TB ground truth)
    └── test-stdout.txt            # test.sh output (pytest results)
```

## Команды true-verifier

```bash
python3 scripts/true_verifier.py <trial_dir>            # один trial
python3 scripts/true_verifier.py --batch <summary.json> # PASS в батче
python3 scripts/true_verifier.py --all [--write-registry]  # все → registry
python3 scripts/true_verifier.py --all --json           # machine-readable
```
