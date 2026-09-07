# V0.23 R7 final-verifier domain/import/pair-profile repair continuation

Status: `FROZEN_PRE_CORRECTED_OUTCOME_R3`

This is the versioned R3 continuation of the frozen R1/R2 array-domain and
import-closure repair. It authorizes one integrity-only re-verification of the
completed R7-I1 TRAIN-development shards. It does not authorize source
generation, learner fitting, composition replay, episode training, TEST
access, threshold changes, or scientific tuning.

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

## Authenticated R1 and R2 failure receipts

R1 froze and installed the array-domain dispatch, then stopped before it
loaded any source or composition NPZ. Its additive authority snapshot remains
at `repair-authority/`. The R1 manifest, pin, and log are immutable and are
authenticated by the following SHA-256 values:

- manifest: `e72b2cc566d0376c5c8d9bfafc3b28718fa757d4cab25f28f2b19703dd0b1f59`;
- frozen pin: `1ec0296abf541748f463411567264a7a1f25368aa4115f6f6747dd7bcf9022f8`;
- failure log: `fe5eebb609be38e8ca16fc734e8464f97a370aea65c291f4d50d564292dc0419`.

The authenticated R1 terminal signal was a zero dispatch count:
`{'source': 0, 'composition': 0}`. No corrected verification receipt or
repair receipt was written, no result was sealed, and no scientific outcome
was opened.

R2 retained the byte-identical frozen verifier and the R1 domain dispatch, and
added the scoped sibling import path. The server attempt reached the frozen
composition verifier and then failed closed because the original pair-profile
check compared arrays with shapes `(32, 4, U)` and `(1, 4, U)` using
`np.array_equal`, which never broadcasts. The R2 failure receipt is the
immutable server log `/home/sat/mcrl-v023-r7-domain-repair-20260907-r2.log`.
The R3 launcher authenticates that log as a failed R2 repair by requiring the
markers `V023_R7_DOMAIN_REPAIR_FAILED:` and
`NPZ domain dispatch count drifted:`. R2 left its manifest-authenticated
`repair-authority-r2/` snapshot in place, but produced no corrected
verification, repair receipt, result seal, or scientific token.
The R2 authority manifest and frozen pin are authenticated by SHA-256
`e6f433eeafbe8bcbf43c81e241a60a2f428a8fdd06275f95e3e4a6f0fdfd710b` and
`bdfca2665b26ff134da05326498d2e28cb7313e2dff0584ec4a935d82b40b216`,
respectively.

This R2 defect was diagnosed from a real composition shard: the stored
`pair_profile_actions` has shape `[96,32,4,100]`, and every pair is equal to
the four expected profiles after explicit broadcasting over the 32-draw axis.
The original verifier's equality call therefore rejects valid evidence before
the remaining checks for that shard can run.

## Sole authorized R3 correction

The R3 repair adapter shall retain the byte-identical frozen final verifier,
the R1 NPZ digest-domain dispatch, and the R2 scoped sibling import context.
It may change only the one pair-profile equality operand and the adapter's
postcondition ordering:

- source binding schema
  `multi-catfish-mcrl-v023-lcsrs-source-artifact-v1-arrays-v1` uses
  `source-array-v1`;
- composition bindings must explicitly declare
  `v023-composition-array-v1` and use that domain;
- the original `_validate_pair_arrays` function is transformed only at
  `np.array_equal(profile_actions[p], expected_profiles[None, :, :])` to use
  `np.broadcast_to(expected_profiles[None, :, :], profile_actions[p].shape)`;
- an original verifier result with `status == "INVALID_RUN"` must surface its
  `errors` before any dispatch-count postcondition is asserted;
- the expected successful dispatch counts remain exactly 8 source and 48
  composition NPZ loads, after all independent shard checks complete.

The pair-profile repair is installed only for the duration of the original
verifier call and the exact original `_validate_pair_arrays`, `_load_npz`,
`V023_ARRAY_DOMAIN`, and `sys.path` values are restored on success and
failure. The AST target must be unique; no broad `np.array_equal` override is
allowed.

All dtype, shape, C-order bytes, file hashes, sidecars, identities,
denominators, thresholds, predicates, decision order, and claim ceilings
remain those of the frozen verifier. Existing source, fit, composition,
authority, and invalid-verification files are read-only and may not be
rewritten.

## Deterministic proof requirements

The focused R3 tests must prove that:

1. `(32,4,U)` actions equal to `(1,4,U)` expected profiles pass only after
   explicit broadcasting;
2. one changed draw/action fails;
3. a shape-incompatible expected profile fails and the transformed validator
   retains the original count of independent `array_equal` checks;
4. the original pair validator, NPZ loader, domain value, and import path are
   restored;
5. an `INVALID_RUN` error is reported before dispatch-count assertions and
   writes no corrected output or repair receipt; and
6. write-once output behavior rejects existing regular files and symlinks.

The launcher must pass `bash -n`, local manifest verification, Python
byte-compilation, and `--dry-run` without starting a server or a tmux session.

## Additive same-root repair and terminal rule

Because R7-I1 has neither `MANIFEST.sha256` nor `COMPLETE`, the repair may add
one manifest-authenticated R3 repair-authority snapshot, one corrected final
verification receipt, and one repair receipt to the same run root. It may not
overwrite or delete the original invalid receipt or the retained R1/R2
failure evidence. The existing R7 result sealer may publish `result.json`,
`verification.json`, `MANIFEST.sha256`, and `COMPLETE` only when the corrected
receipt reports `PASS_FINAL_INTEGRITY` / `VERIFIED` and all original 8 source,
48 fit, and 48 composition shards pass independent re-verification.

If corrected verification is still invalid, the root remains unsealed and no
additional repair, rescue, alternate threshold, or new scientific token is
authorized by this contract.

Claim ceiling:
`TRAIN_DEVELOPMENT_INTEGRITY_ONLY_DOMAIN_AND_IMPORT_CLOSURE_REPAIR_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY`.
