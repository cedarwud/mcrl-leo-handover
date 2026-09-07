# V0.4 C3 fresh-source runner work order

Date: 2026-09-01  
Status: implementation work order; no source outcome or training claim

## Classification and route

The prepare scan is non-training but uses the real TLE/checkpoint.  The
materialization phase evaluates up to 1,862 matched branch pairs and may take
roughly 15--40 minutes.  Run both in the isolated Ubuntu snapshot
`/home/sat/mcrl-leo-handover-v04-c3-20260901`, not in local WSL.  The server
already has the Python environment and frozen TLE view.

## Frozen inputs

- checkpoint: the authenticated Main checkpoint from
  `artifacts/training-2026-08-25-rerun01/main`;
- frozen PREREG file SHA-256
  `8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543`,
  record digest `3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4`,
  and ephemeris file-set SHA-256
  `427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`;
- frozen Main status/log/checkpoint file SHA-256 values
  `3e980bc8c47087ff313c5f5589dab053e0f52440fff692d0c88153af4cce7fa1`,
  `635e375fe04e890d22aed41eebd40c808b41635a2f15bdadfc4e85b5580769f0`,
  and `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`;
- source seeds: TRAIN `2026092301`--`2026092304`, validation
  `2026092305`--`2026092307`, TEST none;
- learner initialization seeds: `2026092101`--`2026092103`;
- `kappa_bits_hex = 0x1.2cea89d260f2ap+33`;
- `lambda_bits_per_j_hex = 0x1.443a8f481639ap+26`;
- maximum source steps per seed: 10;
- contexts/rows: 263 / at most 1,052 TRAIN, 203 / at most 810 validation;
- at most four siblings per focal-state context and eight selected contexts
  per physical anchor;
- no C1, C2, TEST, learner update, EE evaluation, or architecture fallback.

## Two-phase boundary

### Prepare

Load the frozen Main checkpoint read-only.  For each fresh source seed, bind a
new keyed fading field, replay the Main trajectory for at most 10 steps, encode
the V0.4 C3 state, rank focal users by absolute beam contrast then beam victim
pressure, use satellite contrast/pressure only as tie-breaks, and collect only
`C3V04ContextCandidate` metadata.
Persist reference and candidate physical keys, enforce the per-anchor context
cap, and build and atomically publish the schedule.  Seal the schedule and a
transitively closed source manifest before any candidate or reference branch
evaluation.  The receipt must state
`counterfactual_outcomes_evaluated=false` and prove Main networks/replay are
unchanged.

### Generate

Authenticate the prepared schedule, replay each seed, recompute and match the
scheduled anchor/state/reference/focal/action metadata and all physical keys,
then materialize every scheduled row through
`produce_v04_c3_opening_comparison`.  Persist one V0.4 C3-only dataset per
seed.  No scheduled row may be dropped because of target sign or magnitude.
Fail if any scheduled row is missing, any unscheduled row is emitted, any
physical key or digest drifts, or Main networks/replay mutate.

Before the production prepare seal, run one separate development-seed real-TLE
smoke outside the frozen TRAIN/validation pools.  It must include at least one
non-opening anchor, materialize every comparison in its small smoke schedule,
verify keyed fading and state immutability, and publish only a smoke receipt.
The target-bearing round-trip dataset must remain ephemeral; the published
directory contains only the source manifest, non-outcome mini-schedule and
their sealed receipt files.  Production `prepare` must authenticate and bind
the smoke receipt and seal before scanning any source seed.  It may not
publish learning data, inspect TEST/EE, or modify the production schedule.

## Checkable completion criterion

The runner slice is complete only when:

1. a unit/synthetic prepare proves no call to `evaluate_actions`;
2. prepare output has exactly the frozen 66/66/66/65 and 68/68/67 context
   balance, no more than eight contexts per physical anchor, a connected
   28-action TRAIN graph, and TRAIN-supported validation pairs;
3. a bounded real-TLE smoke replays at least one non-opening anchor and
   materializes every scheduled comparison without state mutation;
4. dataset round-trip, physical-key lineage, transitive manifest closure, and
   independent receipt verification pass;
5. published metadata says TEST absent/unopened, held-out EE absent, training
   false, and no target-sign filter.

Passing this slice authorizes the fresh C3 source run only.  It does not
authorize the learnability GO claim, 500EP, or 9000EP.

Engineering receipt (2026-09-01): the disjoint real-TLE smoke at
`artifacts/multi-catfish-v04-c3-real-tle-smoke-20260901-r3` passed with a
non-opening anchor and 2/2 materialized rows.  Receipt SHA-256:
`26b56cb8326f84736d36c5c0f338d237332c29bc190a2177c4459685d1743196`.
It published the five authority files only and no target-bearing dataset.
The first fail-closed smoke attempt also exposed a verifier-only numerical
bug: the target constructor subtracted matched per-user rates before summing,
while the verifier subtracted two large system sums.  W77 now locks the same
subtraction-before-summation rule at both seams; no tolerance was relaxed.

Production prepare receipt (2026-09-01):
`artifacts/multi-catfish-v04-c3-source-20260901` sealed the outcome-blind
schedule in 46.31 s with TRAIN balance `66/66/66/65`, validation balance
`68/68/67`, 466 non-opening contexts, schedule SHA-256
`c9465e60afb2533b59f10106756fdab2b176a90b288f8e6222da9b34fcd8c1d2`,
and `counterfactual_outcomes_evaluated=false`.  Source materialization and
learnability remain pending at this receipt boundary.
