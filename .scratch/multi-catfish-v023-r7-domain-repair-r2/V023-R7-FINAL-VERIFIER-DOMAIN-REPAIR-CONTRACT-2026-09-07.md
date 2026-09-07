# V0.23 R7 final-verifier array-domain/import-closure repair continuation

Status: `FROZEN_PRE_CORRECTED_OUTCOME`

This is the versioned R2 continuation of the frozen R1 array-domain repair.
It authorizes one integrity-only re-verification of the completed R7-I1
TRAIN-development shards. It does not authorize source generation, learner
fitting, composition replay, episode training, TEST access, threshold changes,
or scientific tuning.

## Trigger and authenticated invalid attempt

- Run root: `/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1`
- Original final verifier SHA-256:
  `3cc573717f010d8b67ede027d05ef79f4c69497e9654d6766df50e88e9aa4717`
- Invalid verification receipt SHA-256:
  `2b14fb95b9599b1c6abd50a63ab7adaaf61e31a8bbf448ada625b4242fd6a64f`
- Required invalid status: `INVALID_RUN`, integrity `INVALID`, no scientific
  claim, no TEST, no episode training, and exactly one error:
  `source 2026121801 array anchor_phase digest disagrees`.

The source writer hashes every source NPZ array with domain
`source-array-v1`. The frozen final verifier incorrectly applies
`v023-composition-array-v1` to both source and composition NPZ arrays. The
first source member therefore fails before any R7 scientific token is opened.

## Authenticated R1 entry-point failure

R1 froze and installed the array-domain dispatch, then stopped before it loaded
any source or composition NPZ. Its additive authority snapshot remains at
`repair-authority/`; the R1 log SHA-256 is
`fe5eebb609be38e8ca16fc734e8464f97a370aea65c291f4d50d564292dc0419`.
The exact terminal signal was a zero dispatch count:
`{'source': 0, 'composition': 0}`. No corrected verification receipt or repair
receipt was written, no result was sealed, and no scientific outcome was
opened.

The zero count was caused by an entry-point-only import-context defect. The
frozen verifier is loaded from a different directory, while its preflight
module performs an ordinary sibling import of
`r7_balanced_successor_gate`. R1 did not expose the frozen verifier's sibling
directory on `sys.path`, so verification returned before array-domain dispatch.
This is not a failed scientific re-verification and did not exercise the R1
terminal rule for a corrected 8/48/48 result.

## Sole authorized correction

The R2 repair adapter shall retain the byte-identical frozen final verifier and
the R1 NPZ digest-domain dispatch, and add only a scoped import context for the
duration of the original verifier call:

- prepend the frozen verifier's own directory to `sys.path` immediately before
  calling it;
- restore the exact prior `sys.path` immediately after the call, including on
  failure;
- do not replace, copy, or edit the sibling module.

The retained R1 digest-domain dispatch is:

- source binding schema
  `multi-catfish-mcrl-v023-lcsrs-source-artifact-v1-arrays-v1` uses
  `source-array-v1`;
- composition bindings must explicitly declare
  `v023-composition-array-v1` and use that domain;
- any other schema/domain combination fails closed.

All dtype, shape, C-order bytes, file hashes, sidecars, identities,
denominators, thresholds, predicates, decision order, and claim ceilings
remain those of the frozen verifier. Existing source, fit, composition,
authority, and invalid-verification files are read-only and may not be
rewritten.

## Additive same-root repair and terminal rule

Because R7-I1 has neither `MANIFEST.sha256` nor `COMPLETE`, the repair may add
one manifest-authenticated repair-authority snapshot, one corrected final
verification receipt, and one repair receipt to the same run root. It may not
overwrite or delete the original invalid receipt. The existing R7 result
sealer may publish `result.json`, `verification.json`, `MANIFEST.sha256`, and
`COMPLETE` only when the corrected receipt reports
`PASS_FINAL_INTEGRITY` / `VERIFIED` and all original 8 source, 48 fit, and 48
composition shards pass independent re-verification.

If corrected verification is still invalid, the root remains unsealed and no
additional repair, rescue, alternate threshold, or new scientific token is
authorized by this contract.

The existing R1 repair authority and failure log are immutable authenticated
inputs. R2 writes only `repair-authority-r2/`,
`final-verification-domain-repair-r2.json`, and
`domain-repair-r2-receipt.json` before the unchanged sealer is permitted to
publish the normal result closure.

Claim ceiling:
`TRAIN_DEVELOPMENT_INTEGRITY_ONLY_DOMAIN_AND_IMPORT_CLOSURE_REPAIR_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY`.
