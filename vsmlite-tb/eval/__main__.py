"""eval CLI: python3 -m eval {list,run,run-all,summary} [options].

Примеры:
  python3 -m eval list
  python3 -m eval list --filter difficulty=medium
  python3 -m eval run --task acl-permissions-inheritance
  python3 -m eval run --filter difficulty=easy --limit 5
  python3 -m eval run-all --filter category=system-administration
  python3 -m eval summary
"""
from __future__ import annotations

import argparse
import sys

from .config import EvalConfig


def _parse_filter(value: str | None) -> tuple[str | None, str | None]:
    """Распарсить 'key=value' фильтр. Возвращает (key, value) или (None, None)."""
    if not value:
        return None, None
    if "=" not in value:
        print(f"некорректный фильтр (нужно key=value): {value}", file=sys.stderr)
        sys.exit(2)
    k, v = value.split("=", 1)
    return k.strip(), v.strip()


def _apply_filter_to_config(config: EvalConfig, key: str | None, val: str | None) -> None:
    if key is None:
        return
    if key == "difficulty":
        config.filter_difficulty = val
    elif key == "category":
        config.filter_category = val
    else:
        print(f"неизвестный фильтр: {key} (доступны: difficulty, category)", file=sys.stderr)
        sys.exit(2)


def _build_config(args: argparse.Namespace) -> EvalConfig:
    config = EvalConfig(
        harness_type=args.harness,
        harness_binary=args.harness_binary or "",
        limit=args.limit,
    )
    if args.filter:
        k, v = _parse_filter(args.filter)
        _apply_filter_to_config(config, k, v)
    if args.dataset_dir:
        config.dataset_dir = args.dataset_dir
    return config


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="eval",
        description="Terminal-Bench Dev Set v2 пайплайн оценки продукта",
    )
    parser.add_argument("--harness", default="claude-code",
                        help="harness: claude-code | goose | custom (default: claude-code)")
    parser.add_argument("--harness-binary", default="",
                        help="путь к бинарнику harness (авто-детект если пусто)")
    parser.add_argument("--filter", default=None,
                        help="фильтр задач: difficulty=<easy|medium|hard> | category=<name>")
    parser.add_argument("--limit", type=int, default=None,
                        help="максимум задач в батче")
    parser.add_argument("--dataset-dir", default=None,
                        help="путь к локальной копии датасета (override EVAL_DATASET_DIR)")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="список задач в датасете")
    sub.add_parser("summary", help="вывести pass-rate из state/dev_metrics.json")

    p_run = sub.add_parser("run", help="прогнать задачи")
    p_run.add_argument("--task", default=None, action="append",
                       help="task_id (можно повторять); без --task — все по фильтру")

    sub.add_parser("run-all", help="прогнать все задачи (по фильтру)")

    args = parser.parse_args()
    config = _build_config(args)

    if args.command == "list":
        from .loader import list_tasks
        list_tasks(config)
    elif args.command == "summary":
        from .metrics import print_summary
        print_summary(config)
    elif args.command in ("run", "run-all"):
        from .runner import run_single, run_all
        if args.command == "run" and args.task:
            config.filter_task_ids = args.task
            for tid in args.task:
                run_single(tid, config)
            # run --task (батч) не идёт через run_all, поэтому eval_history.json
            # (trend для S4/autonomy) не пишется. Фиксируем снэпшот явно — это
            # нужно для canary-set прогонов (T0/T1), которые идут через --task.
            from .metrics import record_run, compute_trend
            snapshot = record_run(config)
            trend = compute_trend(config)
            import sys as _sys
            print(f"batch snapshot: pass_rate={snapshot['pass_rate']:.1%} "
                  f"({snapshot['passed']}/{snapshot['total']})  "
                  f"trend: {trend['direction']} ({trend['delta']:+.1%})",
                  file=_sys.stderr)
        elif args.command == "run" and not args.task:
            run_all(config)
        else:
            run_all(config)
    else:  # unreachable — argparse required=True
        parser.error(f"неизвестная команда: {args.command}")


if __name__ == "__main__":
    main()
