# V0.18 R2 full-cache equivalence check

Status: `FROZEN_BEFORE_CHECK`

Date: 2026-09-04 (Asia/Taipei)

## Purpose

Verify that the R2 anchor-local cache is numerically equivalent to the sealed
R1 branch-by-branch implementation before R2 executes any V0.18 shard.  This
is an implementation check, not an efficacy experiment and not a source of
algorithm choices.

## Frozen check surface

- Split: previously opened TRAIN only; TEST remains unopened.
- World: V0.13 world `2026104901`.
- TLE input: the same frozen TLE source authenticated by
  `artifacts/PREREG-FROZEN-2026-08-25-R2.json`; its environment-local absolute
  root must be supplied explicitly and persisted in the receipt.
- Frozen Q1/Q2 lineage: `2026092101`.
- Users: `100`.
- Step: initial predecision anchor only; no environment action is executed.
- Contexts: `h=12` (`Q1+learned Q2`), `h=1` (`Q1`), and `h=2`
  (`learned Q2`).
- Candidate coverage: every native legal focal-user/action branch in each
  context; no branch sampling or mask reduction.
- Parallel workers: at most `18`; parallelism changes wall time only.
- Exact teacher, realised outcome, learner, episode training, and TEST: none.

## Compared values

For every context and legal focal branch, reconstruct R1 full-network nominal
rates and interference.  Compare every non-focal reference victim with the R2
cached branch; the focal value is outside C3 by definition and the cached
primitive intentionally does not reconstruct it.  Then compare the resulting
complete nominal `delta` and centred `q3` surfaces.  Also compare the complete
public action-context and victim-token tensors (including the sixth victim
entry, which carries the transformed reference/candidate interference
relation).
For each of the three frozen background score surfaces, compare the final
native masked argmax selected with R1 versus R2 and report the maximum score
deviation and minimum top-two legal-action margin.

The independent sealed R1 source file must hash to
`6a3d61940175f0e4e422fa4ac9818fd64652dd4f6e699408f6189cec164425a2`.

The frozen check implementation identities are:

- equivalence runner:
  `bdafa3c8c8f135b105ccda947852b3b937e0b04fad5572f1f68d483947624aca`;
- R2 cached runtime:
  `e66f61d7ad8833115eb0542ca2b4ea6718a23ecc26aa0729f5cf879c64cf6166`.

The runner and R2 runtime bytes must match these values when the check starts.

No equivalence outcome or environment action had been opened when this
pre-execution revision was made.  The revision only replaced an implicit
workstation-dependent TLE path with an explicit recorded frozen-data root; it
did not change any world, lineage, context, branch, tolerance, or acceptance
condition.

## Fixed acceptance

The check passes only if all of the following hold:

1. rates: `rtol=1e-12`, `atol=1e-9`;
2. interference: `rtol=1e-12`, `atol=1e-18`;
3. complete `delta` and `q3`: `rtol=1e-12`, `atol=1e-9`;
4. complete action-context and victim-token tensors: `rtol=1e-12`,
   `atol=1e-12`; their byte-exact content-digest equality is reported as a
   diagnostic, not required after a floating-point algebraic reordering;
5. the frozen preregistration hash and preregistered TLE file-set identity are
   verified and recorded;
6. R1 and R2 masked argmax actions are exactly identical for all 100 users in
   all three contexts;
7. the interleaved-anchor no-stale-state unit test and the full 57-test focused
   cross-module set pass; and
8. all source/code/contract/output hashes and the no-action/no-TEST boundary
   are present in a write-once receipt.

Any mismatch returns `STOP_R2_CACHE_EQUIVALENCE`; it cannot be repaired by
changing tolerances, selecting another world/context/action subset, or using
the observed discrepancy to tune the formula.  A pass returns
`PASS_R2_CACHE_EQUIVALENCE` and authorizes only freezing the separate R2
performance addendum and code manifest.
