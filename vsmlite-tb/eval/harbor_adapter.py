"""harbor_adapter — ProductAdapter: harbor custom-agent wrapping the product.

VSM-024: bridges harbor-framework (the eval runner) and the product (../src/ — a
multi-agent VSM whose entry point is orchestrator.run_recovery_cycle). Harbor
manages the docker sandbox + trial lifecycle + verifier; the ProductAdapter is
the single glue layer that launches the product inside the container and converts
its recovery-cycle output into an ATIF trajectory.

Architecture (all execution happens inside the docker container):
  ProductAdapter.run(instruction, environment, context)
    1. membrane.translate_from_text(instruction) → neutralized prompt (VSM-002)
    2. write neutralized prompt into the container
    3. environment.exec("python3 /opt/eval_shim/orchestrator_runner.py ...")
       → the shim imports the product (PYTHONPATH=/opt/vsm_src) and invokes
         run_recovery_cycle(S1Input, dispatcher, classifier, auditor, s2, config)
       → product is stateless (CONTRACT §5): one fresh process per trial
    4. read the recovery-cycle summary from /logs/agent/product-trace.json
    5. convert to ATIF Trajectory → write self.logs_dir/trajectory.json
    6. populate context.metadata (terminated_by, attempts, verdict)

This file lives in the PARENT (vsmlite-tb/eval/). The product stays
benchmark-agnostic (membrane VSM-002): the instruction is neutralized before any
product process sees it.

Phase 1 (smoke): orchestrator_runner runs with use_agents=False (deterministic
stub, no LLM). This proves infra feasibility — import chain, exec, trace write.
Phase 2 will switch to use_agents=True for the real multi-agent recovery cycle.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.trajectories import (
    Agent,
    FinalMetrics,
    Observation,
    ObservationResult,
    Step,
    ToolCall,
    Trajectory,
)

# eval/ is a package; membrane is a sibling module. ProductAdapter is imported
# by harbor as "eval.harbor_adapter:ProductAdapter" (see harbor-config.yaml), so
# the package context is available.
from . import membrane

# Container-side paths (harbor EnvironmentPaths convention). The eval shim is
# mounted at /opt/eval_shim (read-only), the product at /opt/vsm_src.
_CONTAINER_TASK_PROMPT = "/logs/agent/task_prompt.txt"
_CONTAINER_PRODUCT_TRACE = "/logs/agent/product-trace.json"
_SHIM_PATH = "/opt/eval_shim/orchestrator_runner.py"
_TRAJECTORY_FILENAME = "trajectory.json"

logger = logging.getLogger(__name__)


class ProductAdapter(BaseAgent):
    """Harbor custom-agent that runs the product's recovery cycle.

    Subclass of harbor BaseAgent; launched via `--agent eval.harbor_adapter:ProductAdapter`.
    Emits an ATIF trajectory from the product's recovery-cycle summary so that
    `harbor analyze` / `harbor view` / `harbor traces export` work on full
    multi-agent runs, not just S1 tool-calls.
    """

    SUPPORTS_ATIF: bool = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def name() -> str:
        return "vsm-product"

    def version(self) -> str | None:
        return "0.1.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        """No-op. All deps (python3, pyyaml, goose) are baked into the Docker image
        by the overlay Dockerfile that harbor_run generates (FROM <task-image> +
        RUN apt+pip+goose). The image is content-addressed and cached by harbor, so
        deps install happens once at build time, not per-trial at runtime.
        """
        return None

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        """Run the product's recovery cycle inside the container; emit ATIF trajectory.

        Args:
            instruction: raw task instruction (harbor passes instruction.md content).
            environment: docker sandbox; product + shim are mounted read-only.
            context: harbor AgentContext to populate (metadata, tokens).
        """
        # 1. Membrane VSM-002: neutralize the instruction BEFORE the product sees it.
        #    Harbor loads instruction.md (which may contain the TB canary + framing);
        #    the membrane strips it so the product stays benchmark-agnostic.
        task_prompt = membrane.translate_from_text(instruction)
        membrane.verify_neutrality(task_prompt)

        # 2. Write the neutralized prompt into the container (heredoc avoids quoting).
        await environment.exec(
            command=f"cat > {_CONTAINER_TASK_PROMPT} << 'PROMPT_EOF'\n{task_prompt}\nPROMPT_EOF",
            timeout_sec=15,
        )

        # 3. Launch orchestrator_runner inside the container. All deps (python3,
        #    pyyaml, goose) are baked into the image by the overlay Dockerfile —
        #    no runtime install needed. PYTHONPATH makes the product importable.
        #
        # VSM-036: WORKSPACE detection. The adapter previously hardcoded /app,
        # but 48% of train tasks have WORKDIR=/workdir or /workspace (not /app).
        # For those, `chdir /app` fails → OCI exec error → infra_error, attempts=0
        # (product never starts). Fix: detect the task WORKSPACE at runtime by
        # probing candidate dirs in priority order (task's own WORKDIR wins), then
        # run the product there. The probe runs as a shell prefix that exports
        # WORKSPACE and cds into it.
        workspace_probe = (
            "WORKSPACE=$(for d in /app /workdir /workspace /root; do "
            "[ -d \"$d\" ] && echo \"$d\" && break; done); "
            "WORKSPACE=${WORKSPACE:-/}"
        )
        # VSM-034 A': bind-mount a diag dir for goose sub-agent observability
        # (planner_source = goose vs default fallback, network_retry events).
        # Read by _diag_goose() in ../src/runtime/triad_solver.py.
        diag_dir = "/logs/agent/diag"
        command = (
            f'{workspace_probe} && '
            f"mkdir -p {diag_dir} && "
            f"PYTHONPATH=/opt/vsm_src WORKSPACE_ROOT=$WORKSPACE "
            f"VSM_DIAG_DIR={diag_dir} "
            f"python3 {_SHIM_PATH}"
            f" --instruction-file {_CONTAINER_TASK_PROMPT}"
            f" --workspace $WORKSPACE"
            f" --trace-file {_CONTAINER_PRODUCT_TRACE}"
        )
        # cwd=None → harbor uses the container's default WORKDIR (task-defined),
        # which is the right place for task data. We no longer force /app.
        exec_result = await environment.exec(command=command, cwd=None)

        # Record raw exec output for debugging (visible in harbor view / trial logs).
        if exec_result.stdout:
            (self.logs_dir / "product-stdout.log").write_text(
                exec_result.stdout, encoding="utf-8"
            )
        if exec_result.stderr:
            (self.logs_dir / "product-stderr.log").write_text(
                exec_result.stderr, encoding="utf-8"
            )

        # 4. Read the recovery-cycle summary (written by orchestrator_runner).
        #    If the product failed to write it (infra error), synthesize a minimal
        #    summary so the trial still produces a valid trajectory.
        summary = self._load_product_trace()
        if summary is None:
            summary = {
                "terminated_by": "infra_error",
                "total_attempts": 0,
                "verdict": "unknown",
                "classifications": [],
                "audit_results": [],
                "s2_authorizations": [],
                "recovery_results": [],
                "exec_return_code": exec_result.return_code,
                "exec_stderr_tail": (exec_result.stderr or "")[-500:],
            }

        # 5. Convert to ATIF trajectory and write to self.logs_dir/trajectory.json.
        #    self.logs_dir is bind-mounted to trial_dir/agent/ on the host, so the
        #    trajectory is immediately available to harbor analyze/view/export.
        trajectory = self._build_trajectory(summary, task_prompt)
        traj_path = self.logs_dir / _TRAJECTORY_FILENAME
        traj_path.write_text(
            json.dumps(trajectory.to_json_dict(), indent=2) + "\n",
            encoding="utf-8",
        )

        # 6. Populate harbor context metadata (tokens left None in Phase 1 stub).
        context.metadata = {
            "terminated_by": summary.get("terminated_by", "unknown"),
            "total_attempts": summary.get("total_attempts", 0),
            "verdict": summary.get("verdict", "unknown"),
            "classifications_count": len(summary.get("classifications", [])),
            "audit_results_count": len(summary.get("audit_results", [])),
            "adapter": self.name(),
            "adapter_version": self.version(),
        }

    def populate_context_post_run(self, context: AgentContext) -> None:
        """Backfill context if run() didn't (e.g. timeout). Default no-op:
        run() always populates metadata; tokens stay None for the Phase 1 stub.
        """
        if context.metadata is None:
            context.metadata = {"terminated_by": "post_run_backfill", "total_attempts": 0}

    # ── helpers ──

    def _load_product_trace(self) -> dict | None:
        """Read the recovery-cycle summary written by orchestrator_runner.

        Returns None if the file is absent or invalid (treated as infra error).
        """
        # /logs/agent/ in the container == self.logs_dir on the host (bind-mounted).
        host_trace = self.logs_dir / "product-trace.json"
        if not host_trace.exists():
            return None
        try:
            return json.loads(host_trace.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _build_trajectory(self, summary: dict, task_prompt: str) -> Trajectory:
        """Build an ATIF Trajectory from the recovery-cycle summary.

        Rich mode (when s1_trace is present): one agent Step per tool-call the
        executor made — tool name, args, observation. This is the real trajectory:
        visible in `harbor view`, analyzable by `harbor analyze`, and readable
        from product-trace.json for planner tuning.

        Fallback (no s1_trace — stub, no_observations, or infra error): the old
        2-step format (user prompt + verdict summary).
        """
        terminated_by = summary.get("terminated_by", "unknown")
        attempts = summary.get("total_attempts", 0)
        verdict = summary.get("verdict", "unknown")
        s1_trace = summary.get("s1_trace") or []

        # Step 1 is always the user task prompt.
        steps = [
            Step(
                step_id=1,
                source="user",
                message=task_prompt[:2000],
            ),
        ]

        if s1_trace:
            # Rich mode: one agent step per tool-call. Each step carries the
            # tool_call (function_name + arguments) and the observation (what the
            # tool returned). This makes the trajectory a faithful record of what
            # the agent did, not just the final verdict.
            for i, entry in enumerate(s1_trace):
                tool = entry.get("tool", "unknown")
                args = entry.get("args", {})
                obs = entry.get("observation", "")
                steps.append(Step(
                    step_id=i + 2,  # step_id starts at 1; user is 1
                    source="agent",
                    message=f"{tool}({json.dumps(args, default=str)[:200]})",
                    tool_calls=[ToolCall(
                        tool_call_id=f"call-{i}",
                        function_name=tool,
                        arguments=args if isinstance(args, dict) else {"raw": str(args)},
                    )],
                    observation=Observation(results=[
                        ObservationResult(
                            source_call_id=f"call-{i}",
                            content=obs[:4000],
                        )
                    ]),
                ))
        else:
            # Fallback: single agent step with the verdict summary.
            steps.append(Step(
                step_id=2,
                source="agent",
                message=(
                    f"recovery-cycle complete: terminated_by={terminated_by}, "
                    f"attempts={attempts}, verdict={verdict}"
                ),
                observation=Observation(results=[
                    ObservationResult(content=json.dumps(summary, default=str)[:4000])
                ]),
            ))

        return Trajectory(
            schema_version="ATIF-v1.7",
            agent=Agent(
                name=self.name(),
                version=self.version() or "unknown",
                model_name="glm-5.2",
            ),
            steps=steps,
            final_metrics=FinalMetrics(
                total_steps=len(steps),
                extra={
                    "terminated_by": terminated_by,
                    "total_attempts": attempts,
                    "tool_calls": len(s1_trace),
                },
            ),
        )
