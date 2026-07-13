# `src/recovery_policies/` — executors для recovery policies (T3)

> Каждая recovery policy из [`../failure_taxonomy.yaml`](../failure_taxonomy.yaml)
> имеет executor здесь. Executor применяет policy к environment ВНЕ S1 —
> меняет env/state перед retry. S3-classifier выбирает policy; S2 координирует
> применение; executor исполняет.

## Принцип

Recovery executor — изолированный компонент: получает policy id + context,
меняет environment, возвращает `env_changes[]` (что изменилось — для
`recovery_directive`). Не классифицирует (это S3), не запускает retry (это S2),
не знает про оценочные наборы.

## Структура (future runtime)

Каждая policy — отдельный модуль/файл:
```
src/recovery_policies/
├── README.md              ← этот файл
├── install_tool.py        ← InstallTool (ToolNotFound)
├── install_dependency.py  ← InstallDependency (ImportError)
├── create_fresh_venv.py   ← CreateFreshVenv (DependencyConflict)
├── fix_build_config.py    ← FixBuildConfig (CompilationError)
├── fix_syntax.py          ← FixSyntax (SyntaxError)
├── diagnose_and_patch.py  ← DiagnoseAndPatch (TestFailure)
├── relocalize.py          ← RelocalizeAndReplay (FileLocalizationError)
├── reset_and_replay.py    ← ResetAndReplay (GitConflict)
├── use_alternate_auth.py  ← UseAlternateAuth (GitAuthFailure)
├── retry_smaller_scope.py ← RetryWithSmallerScope (TimeoutExpired)
├── kill_and_restart.py    ← KillAndRestart (HangDetected)
├── reduce_footprint.py    ← ReduceFootprint (ResourceLimit)
├── fix_permissions.py     ← FixPermissions (PermissionDenied)
├── retry_with_backoff.py  ← RetryWithBackoff (NetworkError)
├── clarify_spec.py        ← ClarifySpec (AmbiguousSpec)
└── escalate_to_s3.py      ← EscalateToS3 (Unknown)
```

_Сейчас — декларация (README). Реализация (python modules) — на runtime-фазе._

## Executor interface (contract)

```
input: {
  policy_id: <string>,
  failure_class: <id>,
  context: {
    workspace: <path>,
    failure_observations: [<from S1 output>],
    policy_attempt: <int>
  }
}
output: {
  applied: true|false,
  env_changes: [<string>],     # что изменилось (для recovery_directive)
  blocked: null|"<reason>"     # если не смог применить
}
```

## Hard constraints (NEVER)

- **`skip_failure_classification`** — executor не запускается без классификации
  (S3-classifier должен определить class первым).
- **`circumvent_recovery`** — executor не применяется если policy_attempt
  превышает limit (anti-repeat из taxonomy).
- **`optimize_for_specific_evaluator`** — executor general-purpose, не привязан
  к конкретному оценочному набору.
