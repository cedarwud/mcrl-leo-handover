# V0.12 independent freeze audit

Date: 2026-09-03 UTC  
Scope: pre-outcome implementation and authority checks only  
Pre-outcome decisions: `GO_FREEZE`, `GO_PACKAGE`, then `GO_LAUNCH`  
Post-result verifier decision: `GO_VERIFIER`

## Findings closed before freeze

1. Merge now recomputes current contract, runner, direct runtime, prereg, TLE,
   and Q1 authorities instead of accepting mutually consistent stale shards.
2. Both the formula builder and immutable surface reject
   `compatibility=True` outside the native legal mask.
3. The live-evaluator purity test snapshots `_pending_segment_age` in addition
   to the other mutable environment state and RNG state.

## Package hardening checked after freeze

The runner additionally seals every non-symlink Python file under
`src/mcrl/**/*.py`, `.scratch/c3-v04/*.py`, and `scripts/**/*.py`.  Each shard
records the sorted file-set digest, and merge recomputes it from the current
isolated checkout.
This is receipt and merge hardening only; it does not change either C3
formula, action selection, seeds, candidate order, or acceptance gates.

## Verification evidence

- V0.12 focused suite: 29 passed, 0 failed.
- Related C1/OPS3-C2/V0.11/V0.12 suite: 93 passed, 0 failed.
- The isolated server copy passed the V0.12 focused suite: 29 passed, 0
  failed, with the same contract and Python source file-set digests.
- A static and literal-dynamic import trace covered 62 reachable local
  modules; none fell outside the three sealed Python roots.
- Independent final verdict: `GO_LAUNCH`.

Claim ceiling: pre-outcome code/package readiness only.  This audit is not an
oracle result, learner result, TEST result, or efficacy claim.

## Post-result verification addendum

After the clean 18-shard second attempt, the independent verifier was hardened
to recompute non-joint mechanics, joint-support truth, production root
authorities, the V0.3 authority seal, and both checkpoint-file and Q1-parameter
digests. The final independent audit returned `GO_VERIFIER`.

- Final V0.12 focused suite: 42 passed, 0 failed.
- Final related C1/OPS3-C2/V0.11/V0.12 suite: 106 passed, 0 failed.
- Standalone verifier suite: 12 passed, 0 failed.
- Both the server-side and local independent verifier reports authenticate the
  clean result and reproduce `STOP_C3_ORACLE_REDESIGN_REVIEW_SEAM`.

This addendum verifies receipt integrity and the frozen decision. It does not
change the original pre-outcome gate or elevate TRAIN-world oracle evidence to
learned-policy efficacy.
