"""orchestrator_runner — thin shim that runs the product's recovery cycle inside a container.

VSM-024: launched by ProductAdapter (harbor_adapter.py) via `environment.exec()`.
Runs INSIDE the docker sandbox where the product (../src/) is mounted at
/opt/vsm_src (PYTHONPATH). Writes a structured summary to <trace-file> for the
adapter to parse into an ATIF trajectory.

This file lives in the PARENT (vsmlite-tb/eval/), not the product. It knows about
the eval pipeline; the product (src/) stays benchmark-agnostic (membrane VSM-002).

Phase 1 (smoke): use_agents=False — deterministic stub, no LLM. Proves infra
feasibility (import + invoke + write trace). Phase 2 will set use_agents=True for
the real multi-agent recovery cycle (needs goose binary + API keys in container).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Product src/ is mounted at /opt/vsm_src (PYTHONPATH set by ProductAdapter).
# This must happen before importing orchestrator (absolute imports rooted at src/).
_SRC = "/opt/vsm_src"
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the product's recovery cycle.")
    parser.add_argument("--instruction-file", required=True,
                        help="path to neutralized task prompt (membrane already applied)")
    parser.add_argument("--workspace", required=True,
                        help="task workspace path (where the agent operates)")
    parser.add_argument("--trace-file", required=True,
                        help="where to write the structured recovery-cycle summary (JSON)")
    parser.add_argument("--time-budget", type=int, default=900,
                        help="time budget seconds (default: 900)")
    args = parser.parse_args()

    task_prompt = Path(args.instruction_file).read_text(encoding="utf-8")
    workspace = Path(args.workspace)

    # Lazy imports (after sys.path is set). These are product-internal; the product
    # is benchmark-agnostic and has no knowledge of the eval harness invoking it.
    from orchestrator import run_recovery_cycle, OrchestratorConfig
    from runtime.types import S1Input, Budget
    from runtime.dispatcher import S1Dispatcher
    from classifier.classifier import FailureClassifier
    from audit.auditor import S3StarAuditor
    from audit.config import AuditConfig
    from s2.coordinator import S2Coordinator

    taxonomy = f"{_SRC}/failure_taxonomy.yaml"
    classifier = FailureClassifier(taxonomy)
    auditor = S3StarAuditor(AuditConfig(s1_provider="zai", s3star_provider="anthropic"))
    s2 = S2Coordinator(get_anti_repeat_limit=classifier.get_anti_repeat_limit)
    # Phase 1 smoke: "mono" = RuleBasedSolver (deterministic stub, no LLM).
    # Phase 2 will wire the triad (make_triad_with_goose) via use_agents=True.
    dispatcher = S1Dispatcher(solver_mode="mono")

    inp = S1Input(
        task_prompt=task_prompt,
        workspace=workspace,
        budget=Budget(time_seconds=args.time_budget, tokens=100000, actions=50),
    )

    config = OrchestratorConfig(
        max_retries=3,
        taxonomy_path=taxonomy,
        s1_provider="zai",
        s3star_provider="anthropic",
        use_agents=False,  # Phase 1 smoke: deterministic stub, no LLM. Phase 2: True.
    )

    result = run_recovery_cycle(
        input=inp,
        dispatcher=dispatcher,
        classifier=classifier,
        auditor=auditor,
        s2=s2,
        config=config,
    )

    # Structured summary for ProductAdapter → ATIF trajectory conversion.
    verdict = getattr(result.final_output, "verdict", None)
    verdict_str = getattr(verdict, "value", str(verdict)) if verdict else "unknown"
    summary = {
        "terminated_by": result.terminated_by or "unknown",
        "total_attempts": result.total_attempts,
        "verdict": verdict_str,
        "classifications": result.classifications,
        "audit_results": result.audit_results,
        "s2_authorizations": result.s2_authorizations,
        "recovery_results": result.recovery_results,
    }

    trace_path = Path(args.trace_file)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    # Stdout summary for the harbor trial log (human-readable).
    print(f"recovery-cycle: terminated_by={summary['terminated_by']} "
          f"attempts={summary['total_attempts']} verdict={verdict_str}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
