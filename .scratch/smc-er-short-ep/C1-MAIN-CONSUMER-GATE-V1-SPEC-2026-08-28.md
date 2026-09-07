# C1 post-gate four-episode efficacy micro-screen V1

Date: 2026-08-28  
Status: candidate before efficacy-screen seed reveal and execution  
Legacy filename: retained only to avoid breaking prior review links

## Question and claim ceiling

This screen asks one narrow question: after the deterministic C1 pre-transfer
representation/atomic gate has independently passed, when the current scalarized Main consumes
one complete C1 bundle as an equal source unit beside each complete Main
bundle, does the C1-informed source produce a better fresh-seed Main-only EE
policy than a matched neutral C1 source?

A pass means only `CONTINUE_10EP`; a fail means `STOP_AND_REDESIGN_C1`.  This
outcome-bearing screen is not a consumer/representation gate and never grants
routing authority.  It is not Chapter 5 evidence, a convergence claim, or
evidence for C2/C3.

## Frozen prerequisites

- C1 Source Gate A must be a sealed `PASS_TO_C1_CONSUMER_GATE` result.
- Its independent verifier receipt must be an exact replay under the currently
  bound Source Gate runner, method, and specification, including regeneration
  of all 50 paired raw rows from the ordered five-seed manifest; a stale,
  reordered, or merely self-attested `PASS` is not sufficient.
- The frozen canonical-TLE corrective-replay addendum and its independent
  verification must bind the build specification's historical `9eca...`
  predecessor, the current canonical `254636...` Source result, all three
  same-seed build-manifest generations, the exact 373-file TLE set, and the
  retained corpus bytes.  The correction is authority-only, uses no new seed
  or sample, and cannot be outcome-conditioned.
- The Source Gate seed-provenance correction explicitly supersedes the seed
  manifest's false statement that all five frozen values were consecutive
  32-bit words from the specification hash.  It must bind the unchanged five
  seeds, the mechanically exact hash windows, the unchanged Source result and
  canonical TLE authority, and attest that no new seed, outcome, sample, or
  outcome-conditioned selection was introduced.  The historical generation
  command is unavailable and must not be reconstructed as contemporaneous
  evidence.
- The C1 EXP corpus and its independent verification must pass byte-, shape-,
  lineage-, and predecessor-hash checks.
- The deterministic C1 pre-transfer representation/atomic Gate 2 receipt must
  pass its independent validator for the exact `run_short_ep.py` revision.
- The current scalarized Main method, routing core, role implementation,
  short-EP runner, sweep evaluator, exact-parity checker, the complete
  `src/mcrl/**/*.py` implementation tree, canonical sealed preregistration,
  exact TLE archive file set, screen runner, validator, tests, and this
  specification, corrective addendum, corrective verifier, and corrective
  verifier test, plus the Source Gate seed-provenance correction and its
  enforcing verifier, are hash-bound by the seed manifest and result receipt.
- All training, environment, mobility, corpus-build, source-gate, and fresh
  evaluation seeds are pairwise disjoint.  The corrected Main checkpoint's
  embedded train/environment/mobility seeds are forbidden explicitly.
- The closure test receipt, repository-wide pre-reveal numeric inventory,
  collision-search trace, fixed campaign ledger, and fixed execution ledger
  must authenticate a single freeze and a single outcome-bearing execution.

## Matched branches

Use one new training seed, environment seed, and mobility seed for both
branches, 100 training users, four episodes, epsilon decay over three episodes,
target synchronization every two episodes, learning rate 0.001, and ACRM
coefficient 1.0.

- **C1-informed:** `F111` behavior carrier, local-SNR high/mid corpus prefill,
  C1 informed behavior plus C1-private ACRM, and gate ledger
  `(C1=route,C2=shadow,C3=shadow)`.
- **C1-neutral:** `A011` carrier, matched-uniform high/mid corpus prefill,
  uniform C1 behavior without ACRM advantage, and the identical gate ledger.

C2 and C3 execute only in independent shadow trajectories and never enter
Main.  Both branches must use exactly 31 prefill bundles drawn from the exact
shared `(source_seed, step)` intersection (17 high-stratum and 14 mid-stratum
contexts), the same Main source
schedule, the same one-unit C1 quota, natural unshaped `U x 3` rewards, the
same shortage denominator, and Main-only deployment checkpoints.  No action
fusion, auction, or post-training coordination is permitted.

Before either branch is run, two independently constructed Main trainers with
the two descriptive arm configurations must be exactly equal after removal of
descriptive metadata across networks, targets, optimizers, replay, RNGs,
masking diagnostics, and persistent environment state.

Every one of the 40 logical-step receipts per branch is checked.  Every step
admits one unique C1 bundle to the durable at-most-once ledger.  The canonical
replay warmup is the complete prefix for which
`main_replay_size_before_update < batch_size (128)`; those steps consume no
optimizer sample and apply no C1 unit.  Every later optimizer update must
contain exactly one complete Main unit and its already-admitted complete C1
unit, no C2/C3 unit, no shortage, and the frozen-Main comparator hash for its
collection block.  The two branches must have identical warmup and applied
update indices.

## Fresh-seed developmental evaluation and pass rule

Evaluate each saved Main-only checkpoint on five new paired evaluation seeds
at 100 users.  These seeds are new and disjoint, but the sampler remains the
canonical `TRAIN` partition; this is not a held-out test split.  Construct a
fresh environment and trainer for every `(checkpoint, seed)` point.  The
independent validator reruns all ten points from the bound checkpoints and
requires exact payload agreement.  Report ratio-of-sums system EE and served
fraction.

The screen passes only if all structural guards pass and all of the following
hold:

1. exactly five paired fresh-seed rows are present;
2. mean paired `EE_informed - EE_neutral` is strictly positive;
3. the paired EE difference is positive on at least four of five seeds;
4. aggregate ratio-of-sums EE is strictly higher for C1-informed;
5. aggregate served fraction of C1-informed is no more than 0.005 below
   C1-neutral;
6. both checkpoints, all raw totals, and all recomputed metrics are finite and
   every branch ran exactly four episodes with only C1 routed.

Every paired row stores its explicit `delta_ee_bits_per_j`, which must equal the
independently recomputed informed-minus-neutral value.

This is a directional continuation rule, not a significance test.  In
particular, the `>=4/5` sign component alone has null probability
`(C(5,4)+C(5,5))/2^5 = 6/32 = 18.75%`; no alpha-level inference is claimed.

Any missing file, hash drift, seed overlap, denominator change, evaluation
state reuse, non-finite value, or failed guard yields `STOP_AND_REDESIGN_C1`;
no partial pass or threshold adjustment after result reveal is allowed.  A
stop does not revoke the separate mechanical Gate 2 result.
