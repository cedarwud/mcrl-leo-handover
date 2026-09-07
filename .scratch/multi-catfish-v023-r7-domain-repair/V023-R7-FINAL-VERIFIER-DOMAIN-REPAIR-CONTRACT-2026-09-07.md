# V0.23 R7 final-verifier array-domain repair contract

Status: `FROZEN_PRE_CORRECTED_OUTCOME`

This contract authorizes one integrity-only re-verification of the completed
R7-I1 TRAIN-development shards. It does not authorize source generation,
learner fitting, composition replay, episode training, TEST access, threshold
changes, or scientific tuning.

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

## Sole authorized correction

The repair adapter shall retain the byte-identical frozen final verifier and
change only its NPZ digest-domain dispatch:

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

Claim ceiling:
`TRAIN_DEVELOPMENT_INTEGRITY_ONLY_DOMAIN_REPAIR_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY`.
