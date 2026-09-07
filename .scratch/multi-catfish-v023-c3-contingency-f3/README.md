# V0.23 C3 contingency F3 learner screen

Status: `IMPLEMENTED_PRE_OUTCOME / NOT_LAUNCHED / TRAIN_DEVELOPMENT_ONLY`

This package implements F3 for the single F2 survivor `X in {D,F}`.  It has
not opened an F1/F2 outcome, a TEST split, a simulator run, or a learner run.
The only candidate-dependent launch input is the exact `survivor` field in a
separately sealed launch authority.  D remains prior to F at F2; a D failure
at F3 never opens F.

## Binding inputs

- `SUCCESSOR-BRIEF-COMMON-2026-09-07.md`: owned-directory, no-TEST,
  write-once, producer-derived-fixture, and claim boundaries.
- `V023-C3-RAPID-CONTINGENCY-LADDER-PREOUTCOME-2026-09-06.md` section 3:
  F3 is INFORMED versus equal-budget NEUTRAL, at source-update checkpoints
  `0,100,...,2000`, for three fixed seeds.
- `DESIGN-F3-LEARNER-SCREEN-PREOUTCOME-R2-CODEX-GPT6-ASTRA-2026-09-07.md`:
  F2 panel reuse, noninitial anchors 1--9, dense D/F targets, fold-local
  neutral labels, Q3-only MSE, four LOWO folds, and mandatory composition veto.
- R7 successor contract sections 4--6 and R7 code: sign eligibility 0.02,
  balanced accuracy 0.60, informed-minus-neutral 0.05, Spearman 0.20,
  24 rows per sign, service margin 0.01, and native lowest-index masked argmax.
- F2's `verify_unit_tape` and `target_surfaces_from_step`: shared-tape
  authentication and F0 `compute_c3_targets` reuse.  Targets are retained as
  raw bits and divided exactly once by
  `kappa=10097071012.757404` (`0x1.2cea89d260f2ap+33`).
- The imported R7 `capture_lcsrs_c3_predecision` and structured
  `LCSRSC3QNetwork`: the `C3View`, 28/29/38 widths, 67-64-64-1 ReLU scorer,
  token aggregation, reference gauge, Adam settings, and output unit are not
  copied or altered.

Claim ceilings are exactly:

- source: `TRAIN_DEVELOPMENT_C3_CONTINGENCY_F3_SOURCE_NO_EFFICACY_NO_TEST`
- learner: `TRAIN_DEVELOPMENT_C3_CONTINGENCY_F3_LEARNER_SCREEN_NO_EFFICACY_NO_TEST`

Every source, startup, checkpoint/heartbeat, job, and terminal receipt says:
`F3 passing is observability, not efficacy`.

## Plainest readings recorded

1. C1 uses `c1-cluster-profile-matched-randomized-predecision-v2` and C2 uses
   `c2-equal-budget-uniform-predecision-v1`; both select sources before physical
   targets exist.  They do not define C3 label replacement.  F3 instead uses
   the distinct fold-local, training-only matched label permutation
   `MCRL_V023_C3_F3_NEUTRAL_V1`.  Within each R2 stratum it sorts cells by
   `(world,lineage,step,user,action)` and applies R7's frozen nonzero hash shift.
   Singletons remain unchanged, held-out labels never move, and every seed
   shares the same mapping.  `build_f3_source_artifact.py` imports this sole
   implementation.
2. Step 0 advances the BASE trajectory but is not a source record.  The
   artifact has `4 worlds x 3 lineages x 9 anchors = 108` records.
3. “Every legal action” means every native-mask legal cell is present in the
   dense target surface.  F2's authenticated reader supplies F0 values for
   distinct unilateral physical changes, exact zero for each reference, and
   its already-declared zero for a legal slot that is not a distinct physical
   mutation.  No new counterfactual is invented.
4. NEUTRAL is materialized once per LOWO fold from training worlds only.
   Held-out labels are never permuted.  Singleton strata retain their labels,
   are counted as ineligible, and the fold fails below 80% coverage.
5. The decimal threshold `informed - neutral >= 0.05` is inclusive.  A
   `1e-12` absolute equality tolerance is used only to prevent binary
   representation of `0.60 - 0.55` from rejecting the stated boundary; it
   does not relax a genuinely smaller gap.
6. The mandatory composition veto is supplied by the contingency ladder and
   specified by R2 as an outcome-blind interface sanity check before F4.
   `ORACLE` is survivor X; `INFORMED` and `NEUTRAL` use native one-pass
   `Q1+Q2+Q3`.  The runner pools bits and joules and uses inherited tolerance
   and ratio-of-sums direction checks.  For D/F, the decisive predicates are:
   teacher and INFORMED EE above BASE both pooled and in at least 2/4 worlds,
   plus INFORMED service at least `BASE - 0.01` in every world.  D/F are
   unilateral continuous corrections, not closure pairs.  Literal-11,
   harmful-partial, topology, pair-count, and action-exposure diagnostics are
   nondecisive; zero selected-11 cannot veto D/F, and no added closure
   simulation is required.

## Numerical provenance labels

- `r7_copy`: sign eligibility `0.02`, INFORMED mean Spearman `0.20`, balanced
  accuracy `0.60`, INFORMED-minus-NEUTRAL balanced accuracy `0.05`, at least
  `24` positive and `24` negative eligible rows, neutral permutation coverage
  `0.80`, and INFORMED per-world service margin `0.01`.
- `panel_adaptation`: four-world INFORMED-over-NEUTRAL mean-seed Spearman wins
  at least `3/4` (from `6/8`), each seed nonnegative in at least `3/4` worlds
  (from `5/8`), and teacher/INFORMED EE above BASE in at least `2/4` worlds
  (from `4/8`).
- `panel_adaptation`: the newly specified loss is mean squared error over legal
  nonreference cells.  It is not an R7 loss copy.

## Source and learner workflow

`build_f3_source_artifact.py` authenticates the sealed F2 terminal receipt and
all twelve write-once F2 tape bundles.  It replays only BASE to reconstruct the
imported R7 view and requires exact stored state, float32 Q12, native mask,
reference actions, and action physical identities.  An empty-mask anchor is
`F3_INTERFACE_UNSUPPORTED`; rows/users are never dropped.  Numeric records,
four fold-local neutral mappings, manifest, receipt, and COMPLETE seal are
write-once.

`run_v023_c3_contingency_f3_learner_screen.py --job WORLD:SEED` runs one paired
LOWO job (two independent models/optimizers).  Paired arms have identical
initial bytes and consume the same PCG64 row schedule.  Checkpoints contain
both model/optimizer states, RNG state, loss cursors, and a chained consumed-
schedule digest.  Existing complete checkpoints authenticate and resume;
partial or gapped checkpoints fail closed.  Only checkpoint 2000 is decisive.
Real jobs also require the inherited deterministic environment exactly:
`OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, and
`NUMEXPR_NUM_THREADS=1`.

`--merge` requires all 12 paired job receipts and one sealed composition input.
Outcomes are exactly `F3_PASS`, `F3_STOP_OBSERVABILITY`,
`F3_STOP_COMPOSITION`, or `INVALID_RUN`.

The three SHA-256-derived seeds (first eight bytes, big-endian, sign bit
cleared) are:

```text
MCRL_V023_C3_F3_LEARNER_SEED_1_V1 -> 9024197307195252515
MCRL_V023_C3_F3_LEARNER_SEED_2_V1 -> 6671349318246123539
MCRL_V023_C3_F3_LEARNER_SEED_3_V1 -> 6946862304711082547
```

## Freeze before reading any F1/F2 outcome

Freeze the F3 preflight bytes and sidecar; every code/import digest; the F2
panel/anchor reuse; target/kappa convention; Q3 config; seed domains and
derived numbers; optimizer, MSE, batch, schedule, checkpoints; neutral key,
strata, singleton and 80% rules; LOWO construction; every R7-copy learner
threshold and every labelled panel adaptation; composition-input profile
construction; deterministic process environment; output roots; launch-
authority schema; receipt schemas; failure precedence; and the independent
verification command.  After F2, only the launch authority's `survivor` value
and mechanical F2 terminal path/digest may be filled in.

The launch authority has strict top-level and nested key equality:

```json
{
  "schema": "multi-catfish-mcrl-v023-c3-contingency-f3-v1-launch-authority",
  "status": "FROZEN_LAUNCH_AUTHORITY",
  "claim_ceiling": "TRAIN_DEVELOPMENT_C3_F3_SOURCE_LEARNER_COMPOSITION_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY",
  "preflight_manifest": {"path": ".scratch/multi-catfish-v023-c3-contingency-f3/F3-PREFLIGHT-MANIFEST.json", "sha256": "<sha256>"},
  "f2_terminal_receipt": {"path": "<absolute sealed terminal-receipt.json>", "sha256": "<sha256>"},
  "survivor": "D",
  "test_split_opened": false,
  "episode_training": false,
  "efficacy_claim": false
}
```

## Dry run and tests

```bash
./.venv/bin/python .scratch/multi-catfish-v023-c3-contingency-f3/build_f3_source_artifact.py --dry-run
./.venv/bin/python .scratch/multi-catfish-v023-c3-contingency-f3/run_v023_c3_contingency_f3_learner_screen.py --dry-run
./.venv/bin/python -m pytest -q .scratch/multi-catfish-v023-c3-contingency-f3
```

Dry-run validates the frozen preflight and is simulator/learner inert.  Adding
`--launch-authority` also validates the sealed F2 survivor binding.

## Cost boundary

There are `4 x 3 x 2 x 2000 = 48,000` source updates.  The design estimate is
5.3--12 serial hours using the supplied Q1/Q2 proxy and excludes view replay,
checkpoint I/O, held-out scoring, and composition evaluation.  Before any
learner launch, measure actual structured-Q3 updates/second, peak memory,
source/view loading, replay/token construction, checkpoint I/O, and
composition cost with a nondecisive throughput fixture.  Do not infer Q3 cost
from the Q1/Q2 proxy.

## Remaining launch-time question

The package deliberately does not nominate an F2 result or a production
composition-input path pre-outcome.  The controller must bind a sealed input
that implements the ladder/R2 EE-and-service scope before launch; it may not
create or revise that input after learner metrics are opened.  F4 remains
separate and unauthorized.
