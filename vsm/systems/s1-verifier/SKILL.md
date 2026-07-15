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
   - artifacts_coherent: the artifacts diff is meaningful (expected files were created).
   - no_error_keywords: no error/traceback/failed in the post-checkpoint trace.
3. All checks passed → `{passed: true}`.
4. Any check failed → `{passed: false}` with a specific reason.
5. Return JSON: passed + reason + checks.

## Communication
- verifier → solver: via the final verdict (passed → task_resolved).
- Does not communicate with S2/S3/S3*/S4/S5 — internal S1 role.
