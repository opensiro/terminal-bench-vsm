#!/usr/bin/env python3
"""verify_child.py — automation bridge: run child S1 capability report.

Vsmlite automation: requests S1 capability report from the child VSM
(via subprocess into ../src/) and returns structured evidence. Used by
/vsmlite-mature command as the S3-verify step for phase transitions.

The capability report is S1's internal self-verification (recursive
viability): it runs solver → MCP → trace → recovery cycle end-to-end
and reports which systems work.

Usage:
  python3 scripts/verify_child.py              # human-readable summary
  python3 scripts/verify_child.py --json       # JSON for programmatic use
  python3 scripts/verify_child.py --check      # exit code only (0=pass, 1=fail)

Exit codes:
  0 — all systems passed (capability_report.all_passed)
  1 — one or more systems failed
  2 — capability report could not be run (error)
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
VSMROOT = SCRIPT_DIR.parent                    # vsmlite-tb/
CHILD_SRC = VSMROOT.parent / "src"             # ../src/

CAPABILITY_REPORT_MODULE = "runtime.verify"


def run_capability_report(json_output: bool = True) -> dict | None:
    """Run the child's S1 capability report via subprocess.

    Returns parsed JSON dict, or None if the report could not be run.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", CAPABILITY_REPORT_MODULE, "--report", "--json"],
            cwd=str(CHILD_SRC),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode not in (0, 1):
            # 0 = all passed, 1 = some failed — both produce valid JSON
            print(f"capability report exited with {result.returncode}", file=sys.stderr)
            if result.stderr:
                print(result.stderr[:500], file=sys.stderr)
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print("capability report timed out (120s)", file=sys.stderr)
        return None
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"capability report JSON parse error: {exc}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"capability report error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None


def format_human_report(report: dict) -> str:
    """Format capability report as human-readable text."""
    lines = []
    lines.append(f"═══ Child S1 Capability Report ═══")
    lines.append(f"Generated: {report.get('generated_at', '?')}")
    lines.append(f"Overall: {report.get('overall', '?')}")
    lines.append(f"Passed systems: {report.get('passed_systems', [])}")
    failed = report.get('failed_systems', [])
    if failed:
        lines.append(f"Failed systems: {failed}")
    lines.append("")

    systems = report.get('systems', {})
    for name in ['S1', 'S2', 'S3', 'S3_star', 'orchestrator']:
        status = systems.get(name, {})
        passed = status.get('passed', False)
        mark = "✓ PASS" if passed else "✗ FAIL"
        lines.append(f"{mark}  {name}")
        for check in status.get('checks', []):
            cmark = "✓" if check.get('passed') else "✗"
            lines.append(f"     {cmark} {check.get('name', '?')}: {check.get('detail', '')}")
        evidence = status.get('evidence', {})
        if evidence:
            lines.append(f"     evidence: {json.dumps(evidence)}")
        lines.append("")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run child S1 capability report")
    parser.add_argument("--json", action="store_true", help="output as JSON")
    parser.add_argument("--check", action="store_true", help="exit code only (no output except errors)")
    args = parser.parse_args()

    report = run_capability_report(json_output=True)

    if report is None:
        print("ERROR: capability report could not be run", file=sys.stderr)
        sys.exit(2)

    all_passed = report.get('all_passed', False)

    if args.check:
        sys.exit(0 if all_passed else 1)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_human_report(report))

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
