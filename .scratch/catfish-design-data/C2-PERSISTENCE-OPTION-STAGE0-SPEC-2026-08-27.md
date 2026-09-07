# Frozen C2 persistence-option Stage-0 role gate

Status: frozen before the dedicated runner, output, or evaluation seeds exist.
This is an isolated, non-training, legacy-geometry sensitivity probe. It does
not implement a Catfish learner, alter reward/runtime/replay, route experience
to Main, lift G-6, or establish effectiveness.

Date: 2026-08-27

## Question and one permitted interpretation

Does a three-interval physical-association persistence option expose a
pre-outcome-selectable opportunity that reduces the focal user's cumulative
canonical R2 penalty relative to both a uniform-safe option and
stay-if-possible, including the first post-release interval and the rest of the
episode?

A pass means only that the option class has support that a future specialist
might learn. It does not mean `Q2` learns it or that EE improves.

## Frozen authority and inputs

- Method contract:
  `docs/MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md`, SHA-256
  `25318fcea4acca6c8692c454751b3af35e7d4151195d200821077c208672e63f`.
- Corrected Main checkpoint:
  `artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt`, episode
  8999, SHA-256
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`.
- Frozen preregistration:
  `artifacts/PREREG-FROZEN-2026-08-25-R2.json`, SHA-256
  `8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543`.
- Reviewed analysis source hash:
  `4cfc7e3043453994fc0686c3bbfa14d9a95156aeabc578b26decb2f210603a2e`.
- Legacy-narrow corrected environment, 100 users, ten intervals per episode.
- Main behavior is frozen masked-greedy Q1-only. No optimizer or replay update.

Five disjoint seeds are revealed in a separate manifest only after this spec
and the companion C3 spec are hashed. No seed previously named in the repo may
be used. For each seed and each anchor step `t in {0,...,5}`, choose five focal
users without replacement using one sequential
`numpy.random.default_rng(seed + 220003)` permutation stream. The focal
schedule is fixed before any environment outcome.

Seed reveal is additionally blocked until the dedicated runner and tests pass
and a closure manifest hashes both specs, all runner/test/helper files,
checkpoint, preregistration, reviewed analysis sources, Python/NumPy/PyTorch/
SGP4 versions, and every frozen TLE file. Any later code or dependency drift
invalidates the reveal; it cannot be repaired after viewing outcomes.

## Current-safe opportunity support

At an anchor, the focal reference must be served on a continuing physical
incumbent. Enumerate de-duplicated served satellite/beam physical IDs whose
current action is valid and service-feasible under deterministic fading-off
physics. The incumbent must be in this set and the set must contain at least
two IDs. Unserved and no-op actions are excluded.

Candidate-table positions are never persistent identities. Every later action
remaps the bound satellite/beam ID into the current table. Disappearance,
invalidity, or deterministic service failure explicitly terminates that
option; it is not silently reindexed or counted as a no-op success.

## Pre-outcome C2-PRE selector

Before any stochastic outcome at the anchor, build a deterministic fading-off
Main-reference forecast through `h=3`. The forecast mobility generator uses
the integer

```text
int.from_bytes(
  SHA256(UTF8(canonical_json([
    "SMC-ER-C2-PRE-v1", checkpoint_sha256,
    evaluation_seed, step_index, focal_user
  ]))).digest()[0:16], "big"
)
```

where canonical JSON uses `sort_keys=True`, `separators=(",", ":")`, and no
ASCII escaping. The integer initializes `numpy.random.SeedSequence` and then
`numpy.random.PCG64`. The forecast begins from the current anchor state, is
copied identically across every reference/candidate forecast fork, and neither
reads nor copies the actual environment mobility/fading RNG state. The runner
records and asserts distinct object/state hashes.

Store the reference forecast branch's non-focal physical action script. For
every currently safe focal candidate, reconstruct the current anchor, replace
future mobility with the sealed forecast stream, and execute:

```text
h=0,1,2: choose candidate at h=0 and then hold the same physical ID
h=3:     release the focal user to frozen masked-greedy Q1 Main
```

At every interval, replay the same reference non-focal physical actions. Reject
a candidate if any common non-focal physical action cannot be remapped and
executed in its branch. Early focal invalidity is an explicit termination;
after termination the frozen Main fallback acts for the focal user.

`C2-PRE` chooses the candidate with the largest focal

```text
S2_pre = sum_{h=0}^{3} r2_focal(h)
```

(the least canonical R2 penalty), then the larger worst-interval deterministic
link margin, then lexicographic physical ID. Actual future mobility RNG,
realised fading, stochastic rate, EE, stochastic reward, and stochastic
successor are unavailable to selection.
`C2-PRE` is used only for this opportunity-existence gate and never supplies a
training label.

## Frozen controls

- `C2-RANDOM`: one uniform draw from the same current-safe physical-ID set,
  using the identical canonical derivation above with namespace
  `SMC-ER-C2-RANDOM-v1`, then the identical hold/release/termination contract.
- `C2-STAY`: bind the qualifying incumbent, which is guaranteed to be in the
  current-safe set, then the identical hold/release/termination contract.

There is no unspecified fallback: if a bound action terminates, frozen
masked-greedy Q1 Main acts for that focal user from the next interval.

## Paired post-selection evaluation

After all three initial choices have been frozen, reconstruct `C2-PRE`,
`C2-RANDOM`, and `C2-STAY` twins from episode reset by replaying the identical
frozen Main physical-action prefix under freshly recreated evaluation RNGs.
The runner must prove equal full anchor fingerprints before branching; no
private snapshot API is assumed. From the anchor onward, every evaluation
branch sets `fading_enabled=False`; the held-out realised-mobility stream
remains the untouched evaluation stream and was unavailable to the forecast.
This Stage-0 result therefore has no actual-fading robustness claim.

Use common initial realised-mobility RNG states. On each branch and interval,
the same frozen Main version independently generates every non-focal action on
that branch's own observation. The anchor fails the causal contract if any
non-focal physical action differs across branches. Each focal branch follows
its own frozen three-hold option, releases at `h=3`, and thereafter follows
frozen Main to episode end. All pass statistics use only these post-selection
fading-off branches. All outcomes, including negative R2, early termination,
and outage, are retained.

Record separately for the option horizon, first post-release interval, and
full anchor-to-episode-end window:

- focal and system `sum(r2)`, `phi1/phi2` incidence, reversal/ping-pong count;
- served-user and focal-service indicators;
- canonical EE, useful bits, payload energy, and power;
- physical action IDs, remapping, option termination, masks, RNG hashes,
  preview/commit parity, and non-focal action equality.

The only improvement sign is

```text
Delta_R2(control) = sum(r2_focal,C2-PRE) - sum(r2_focal,control).
```

Positive means a smaller canonical R2 penalty.

Each eligible anchor has weight one. A seed mean averages its eligible anchors
equally; the pooled mean averages all eligible anchors equally. Direction
counts give each of the five seed means one vote. No episode, step, user, or
seed is reweighted after support is observed.

The full anchor fingerprint hashes canonical serialization of epoch and step;
user positions/headings; dwell anchors; D2 tracker state; association ledgers
and segments; previous radiating, demand, and association maps; candidate
tables; pending ages; environment, mobility, and age RNG states; and frozen TLE
records/NORAD order. All reconstructed twins must match field-by-field and by
SHA-256 before branching.

## Frozen pass/fail rule

Return `C2_STAGE0_PASS_TO_FIXTURES_ONLY` only if all hold:

1. every engineering/hash/clone/remapping/preview/non-focal equality check
   passes;
2. every one of the five seeds has at least one eligible anchor and total
   support is at least 20 paired anchors;
3. against **each** control, full-episode `Delta_R2` has a positive pooled
   mean and a positive seed mean in at least four of five seeds;
4. condition 3 also holds through the first post-release interval, so a
   deferred event cannot escape scoring; and
5. no C2-PRE focal branch changes served to unserved, aggregate served-user
   fraction declines by at most 0.5 percentage points versus each control, and
   no zero-power or identity guard fails.

Return `C2_STAGE0_CERTIFICATE_FAILURE` for an engineering or outcome-timing
leak. Otherwise return `C2_STAGE0_FAIL_DROP_ROLE`. No coefficient, horizon,
support definition, selector, subgroup, or seed may be revised after outcomes
to rescue C2.

EE is a preregistered secondary interaction endpoint. A positive EE result is
reported as Stage-0 paired sensitivity evidence only; a neutral or negative EE
result cannot be hidden behind an R2 pass.
