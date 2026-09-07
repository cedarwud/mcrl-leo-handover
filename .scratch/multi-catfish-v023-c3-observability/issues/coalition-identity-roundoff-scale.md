# V0.23 coalition identity roundoff-scale failure

Status: `FIX_VERIFIED__R4_FULL_GATE_RUNNING`  
Date: 2026-09-06

## Checkable completion criterion

The fix is complete only when all of the following hold:

1. the deterministic physical-scale cancellation regression passes;
2. a material forged component still fails closed;
3. the directly affected V0.23 LC-SRS W190--W205 tests pass;
4. the isolated replay of TRAIN world `2026121706` completes with the same
   scientific inputs that failed R3; and
5. the preflight manifest is resealed before any full Gate relaunch.

Passing items 1--3 alone does not authorize or establish a Gate result.

## Observed symptom

The R3 Gate completed source world `2026121705` and then stopped in world
`2026121706` at `CoalitionResidualC3Result.verify()` with
`CoalitionResidualC3Error: coalition C3 identity failed`.  No C3 learner or
later composition stage ran.

## Ranked hypotheses and discriminating predictions

1. **Final-value scale is the wrong floating guard.**  If this is the cause,
   a deterministic case with large delta-domain operands and a small valid
   joint surplus will fail under the old guard and pass when the guard uses
   the arithmetic work scale, without changing any formula value.
2. **The coalition algebra is wrong.**  If this is the cause, recomputing the
   identity from the same exact delta-domain values will leave a material
   residual that remains outside a forward-error-scale bound.
3. **A source profile or coalition member is mismatched.**  If this is the
   cause, a minimal pure-formula reproduction with no simulator/source
   adapter will not reproduce the failure class.
4. **Serialization truncated a formula input.**  If this is the cause, the
   in-memory pure-formula path will pass while a serialized replay fails.

The deterministic pure-formula regression falsifies hypotheses 3 and 4 for
the reproduced failure class and supports hypothesis 1.  The formula fields
are still compared to independently recomputed components before the identity
roundoff check, so a material component mutation remains a hard failure.

## Minimal reproduction

`tests/test_w181_ee_axis_coalition_residual_c3.py::test_physical_scale_cancellation_is_not_misclassified_as_identity_corruption`
uses two coalition users with per-user bit totals of order `1e11`,
delta-domain terms of order `1e7`, and a final joint surplus of order `1e4`.
The old guard produced a valid identity residual of
`1.1175870895385742e-08` bits but a tolerance of only
`6.490267655208165e-09` bits because it scaled solely from the final sides.

## Scoped fix

The target, multiplier, coalition, equal interaction share, sparse Q3
surface, source selection, worlds, draws, learner, and acceptance criteria are
unchanged.  Only the identity verification tolerance scale changes: it is
computed from the absolute delta-domain and energy-priced intermediate terms
that actually participate in the arithmetic.  The common reference totals
are excluded because they cancel before the identity is formed.

The coefficient remains `1024 * eps`; the change is the mathematically
relevant magnitude supplied to that existing coefficient.  This is an
integrity correction, not an outcome-dependent scientific adjustment.

## Evidence so far

- W181 cancellation regression: red under the old guard, green after the fix.
- W181 material `combined_bits` corruption: still fail-closed.
- 10,000 deterministic physical-scale randomized cases: zero false failures;
  maximum valid absolute identity residual `8.940696716308594e-08` bits.
- W190--W205 directly affected test groups: passed after the fix.
- Real-world isolated replay of the unchanged failing code reproduced the
  failure at `lhs=0x1.d4cafd2191000p+22`,
  `rhs=0x1.d4cafd2192000p+22`, and
  `residual=-0x1.0000000000000p-18` bits
  (`-3.814697265625e-06` bits).  The old final-value-scaled tolerance was
  `0x1.d4cafd2192000p-20`, about 2.2 times smaller than this roundoff.
- Real-world replay with the scoped fix passed the sealed source-artifact
  loader.  It produced index SHA-256
  `05b88696220678b27dcf6f89f62978ba1b1d5bc4396b77de0176499149a97c33`
  and sidecar SHA-256
  `55a01d95f7955f157813dbd8cd87823dff650b13b7d60eb4ee585c3386a927ea`.
  The reopened artifact reports 9 records, 86 pairs, 172 supported rows, and
  167 placebo-eligible rows for world `2026121706` under preflight SHA-256
  `8ce6c78ebfa0ef75192e139c0163064ccfb4ca796a76495df80daf17a377b4e6`.

## R4 replay receipt and full-Gate handoff

- R4 preflight manifest SHA-256:
  `8ce6c78ebfa0ef75192e139c0163064ccfb4ca796a76495df80daf17a377b4e6`.
- Local and Ubuntu-server focused W181--W205 suites passed against those
  bytes (293 tests in the complete focused selection).
- Independent Agy Gemini 3.8 Flash High numerical review returned
  `PASS_SCOPED_NUMERIC_FIX`; its claim boundary is numerical integrity only.
- Fresh isolated server root:
  `/home/sat/mcrl-v023-lcsrs-debug-20260906-r4-1706`.
- Completed tmux handle:
  `mcrl-v023-lcsrs-debug-20260906-r4-1706`.
- Frozen world: `2026121706`; output:
  `replay/world-2026121706.json`.
- The one-shot auto-promotion worker independently reopened the artifact and
  emitted `PASS_R4_WORLD_1706_REPLAY`; all five completion criteria above are
  now satisfied.
- After replay verification, the same worker reran the sealed focused suite
  successfully and launched the full R4 Gate at
  `/home/sat/mcrl-v023-lcsrs-gate-20260906-r4`, tmux
  `mcrl-v023-lcsrs-gate-20260906-r4`.
- At 2026-09-06 01:30 Asia/Taipei, two source workers for worlds
  `2026121705` and `2026121706` were live at approximately one CPU core each.
  This is execution evidence only; no V0.23 scientific decision exists yet.
