"""eval CLI: python3 -m eval [options] <command> [command-options].

Режимы (VSM-026): профиль задаёт источник данных + файл метрик.
  list, run, run-all, summary   # train (backward-compat, существующее поведение)
  eval-test [--sample N]        # TB-2.1 verified N сэмплов (seed=42)
  eval-dataset                  # TB-2.1 verified все 89 (финальный test)
  sanity                        # структурная проверка датасета (без агента)

Примеры:
  python -m eval list
  python -m eval list --profile eval-test
  python -m eval run --task acl-permissions-inheritance
  python -m eval eval-test --sample 5
  python -m eval eval-dataset
  python -m eval sanity --profile eval-test
  python -m eval summary --profile eval-test
"""
from __future__ import annotations

import argparse
import sys

from .config import DATASET_PROFILES, DEFAULT_PROFILE, EvalConfig


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
    """Собрать EvalConfig из глобальных опций + --filter/--dataset-dir."""
    profile = getattr(args, "profile", DEFAULT_PROFILE) or DEFAULT_PROFILE
    config = EvalConfig(
        profile=profile,
        harness_type=args.harness,
        harness_binary=args.harness_binary or "",
        limit=args.limit,
    )
    if args.filter:
        k, v = _parse_filter(args.filter)
        _apply_filter_to_config(config, k, v)
    if args.dataset_dir:
        config.dataset_dir = args.dataset_dir
    if getattr(args, "no_sanity", False):
        config.sanity_check = False
    return config


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="eval",
        description="Terminal-Bench eval-пайплайн: train / eval-test / eval-dataset",
    )
    parser.add_argument("--profile", "-P", default=DEFAULT_PROFILE,
                        choices=list(DATASET_PROFILES.keys()),
                        help=f"режим: {', '.join(DATASET_PROFILES)} (default: {DEFAULT_PROFILE})")
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
    parser.add_argument("--no-sanity", action="store_true",
                        help="отключить sanity-проверку перед агентом (default: вкл)")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="список задач в датасете профиля")
    sub.add_parser("summary", help="вывести pass-rate из файла метрик профиля")

    p_run = sub.add_parser("run", help="прогнать задачи (train по умолчанию)")
    p_run.add_argument("--task", default=None, action="append",
                       help="task_id (можно повторять); без --task — все по фильтру")

    sub.add_parser("run-all", help="прогнать все задачи по фильтру (train)")

    p_et = sub.add_parser("eval-test",
                          help="TB-2.1 verified: N сэмплов (seed=42) для оценки репрезентативности")
    p_et.add_argument("--sample", type=int, default=None,
                      help="размер выборки (default: 20, env EVAL_TEST_SAMPLE_SIZE)")

    sub.add_parser("eval-dataset",
                   help="TB-2.1 verified: все 89 задач (финальный test)")

    sub.add_parser("sanity",
                   help="структурная проверка датасета профиля (без агента)")

    args = parser.parse_args()
    config = _build_config(args)

    if args.command == "list":
        from .loader import list_tasks
        list_tasks(config)
    elif args.command == "summary":
        from .metrics import print_summary
        print_summary(config)
    elif args.command == "sanity":
        from .sanity import sanity_check_dataset, print_sanity_report
        summary = sanity_check_dataset(config)
        sys.exit(print_sanity_report(summary))
    elif args.command == "eval-test":
        from .modes import run_eval_test
        run_eval_test(config, sample_size=args.sample)
    elif args.command == "eval-dataset":
        from .modes import run_eval_dataset
        run_eval_dataset(config)
    elif args.command in ("run", "run-all"):
        # train: harbor batch (VSM-024 Phase 3). run/run-all делегируют в modes,
        # который идёт через harbor_run.run_trial (triad goose sub-agents).
        from .modes import run_train
        if args.command == "run" and args.task:
            config.filter_task_ids = args.task
        run_train(config)
    else:  # unreachable — argparse required=True
        parser.error(f"неизвестная команда: {args.command}")


if __name__ == "__main__":
    main()
