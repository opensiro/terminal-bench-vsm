# S1 — verifier (child) · SKILL

## Tool scope
- **fs.read**: read final artifacts, test output.
- **shell.exec**: if needed, re-run tests for the final check.
- **Do not mutate**: anything. Verifier = read-only final check.

## Contract
- Input: plan, trace (post-checkpoint), artifacts diff (since the checkpoint).
- Output: JSON `{passed, reason, checks}` (see output contract).

## Protocol
1. Evaluate the trace **only since the last checkpoint** (reverted attempts do not count).
2. Checks:
   - tests_pass: the latest pytest run passed.
   - non_empty_collection (VSM-034 TERTIARY-2): the latest pytest run actually
     collected tests — "collected 0 items", "no tests ran", exit code 5
     (NO_TESTS_COLLECTED), or an empty artifacts diff means the solver
     produced nothing testable → check fails.
   - artifacts_coherent: the artifacts diff is meaningful (expected files were created).
   - no_error_keywords: no error/traceback/failed in the post-checkpoint trace.
3. **Empty-collection check** (VSM-034 TERTIARY-2): scan the trace for pytest
   output. If any test run reported "collected 0 items", "no tests ran", exit
   code 5, or the artifacts diff is empty → `passed: false`. A pass requires
   actual tests to have run against actual solution artifacts.
4. All checks passed → `{passed: true}`.
5. Any check failed → `{passed: false}` with a specific reason.
6. Return JSON: passed + reason + checks.

## Communication
- verifier → solver: via the final verdict (passed → task_resolved).
- Does not communicate with S2/S3/S3*/S4/S5 — internal S1 role.
