# S1 — test-controller (child) · SKILL

## Tool scope
- **shell.exec**: run tests (pytest), if none have been run yet.
- **git.reset_hard**: revert to the checkpoint ref (CONTRACT §5.1, VSM-019).
- **git.status / git.diff**: inspect the workspace state.
- **fs.read**: read test output or artifacts.
- **Do not mutate**: anything other than a revert (reset --hard) — this is an
  in-invocation operational action, not a persistent env change.

## Contract
- Input: plan, trace (since the last checkpoint), checkpoint ref,
  revert_count, max_reverts.
- Output: JSON `{verdict, test_output, revert_performed, reason}` (see output contract).

## Protocol
1. Find the latest test run in the trace (shell.exec pytest or equivalent).
   If there is none — run it (shell.exec).
2. Evaluate the result: are there error keywords / nonzero exit / failed assertions?
3. PASS → return `{verdict: "pass", ...}`.
4. FAIL:
   - If checkpoint.ref == "none" or no checkpoint → `fail_no_checkpoint`.
   - If revert_count >= max_reverts → `fail_revert_limit`.
   - Otherwise: perform `git.reset_hard(checkpoint.ref)` → `fail_reverted`,
     revert_performed=true. The solver will re-solve.
5. Return JSON with test_output (brief) and reason.

## Communication
- test-controller → solver: via verdict (fail_reverted triggers re-solve).
- test-controller → verifier: via phase transition (pass / fail_limit → verify).
- Does not communicate with S2/S3/S3*/S4/S5 — internal S1 role.

## Anti-oscillation
Respect `max_reverts` (default 2). If revert_count is at the limit — do NOT revert,
hand off to the verifier (`fail_revert_limit`). This prevents an infinite
solve→fail→revert loop.
