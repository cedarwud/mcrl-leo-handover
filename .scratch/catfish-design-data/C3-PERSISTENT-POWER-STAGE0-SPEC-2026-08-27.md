# Frozen C3 persistent-power Stage-0 role gate

Status: frozen before the dedicated runner, output, or evaluation seeds exist.
This is an isolated, non-training, legacy-geometry sensitivity probe. It does
not implement C3, alter reward/runtime/replay, route experience to Main, lift
G-6, or establish effectiveness.

Date: 2026-08-27

## Question and terminal nature of this gate

Does the action space contain enough three-interval, pre-outcome-certified
same-satellite relocations whose denominator relief survives an unseen
realised-mobility path and improves paired fading-off horizon EE without losing
service?

This is the last persistent-power hypothesis. Any failure drops C3; no new
median, rate, threshold, margin, horizon, or subgroup guard may be added after
seeing outcomes.

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
- `H3=3`, decision interval `Delta=30.08 s`, and power-identity tolerance
  `1e-10 W`.

Five disjoint seeds are revealed in a separate manifest only after this spec
and the companion C2 spec are hashed. No seed previously named in the repo may
be used. Census all 100 users at anchor steps `t in {0,...,7}`.

Seed reveal is additionally blocked until the dedicated runner and tests pass
and a closure manifest hashes both specs, all runner/test/helper files,
checkpoint, preregistration, reviewed analysis sources, Python/NumPy/PyTorch/
SGP4 versions, and every frozen TLE file. Any later code or dependency drift
invalidates the reveal; it cannot be repaired after viewing outcomes.

## Anchor and current-slot support

The frozen Main reference must serve the focal user on a continuing incumbent
source beam, with no current event. The source has at least two served users
and the focal user is its strict unique link-power maximum. Enumerate each
de-duplicated, valid, service-feasible different beam on the same satellite.
At `h=0`, the destination is already active and the focal candidate does not
raise its maximum. Unserved/no-op actions are excluded.

## Deterministic H3 twin-fork certificate

Before any realised future mobility/fading/outcome, derive the integer

```text
int.from_bytes(
  SHA256(UTF8(canonical_json([
    "SMC-ER-C3-H3-v1", checkpoint_sha256,
    evaluation_seed, step_index, focal_user
  ]))).digest()[0:16], "big"
)
```

where canonical JSON uses `sort_keys=True`, `separators=(",", ":")`, and no
ASCII escaping. The integer initializes `numpy.random.SeedSequence` and then
`numpy.random.PCG64`.

Reconstruct the current anchor into reference and candidate forecast forks,
disable fading, and replace future mobility with identical copies of this
forecast stream. The forecast stream neither reads nor copies actual future
environment mobility/fading RNG state; the runner records and asserts distinct
object/state hashes.

At each of `h=0,1,2`, the same frozen Main version independently generates
non-focal masked-greedy actions in both forecast forks. The reference focal
holds the source physical ID for all three intervals. The candidate focal
relocates to the destination at `h=0` and holds that physical ID thereafter.
Candidate indices are remapped from physical IDs after every table rebuild.

Reject the candidate before stochastic execution unless, at every interval:

1. all non-focal physical actions are identical between forks;
2. both focal holds remain valid and service-feasible;
3. served-user, active-beam, and active-satellite sets are identical;
4. the destination maximum is unchanged and source-bottleneck relief persists;
5. candidate system payload power is strictly below reference power;
6. the exact PA recurrence identity residual is at most `1e-10 W`; and
7. the candidate has exactly one additional `phi1` at `h=0`, no `phi2`, and no
   additional event at `h=1,2`.

The certificate may read current masks, association/segment state, geometry,
physical link powers, exact recurrence, and its independent forecast outcomes.
It may not read or copy actual future mobility/fading RNG state, realised
fading, stochastic rate, reward, EE, or a stochastic successor.

For every survivor compute

```text
G_P = Delta * sum_{h=0}^{2} (P_reference(h) - P_candidate(h)).
```

Select the largest `G_P`, then lexicographic destination physical ID. This
selection is final before the stochastic branches run. All rejected candidates
and reasons remain in the receipt.

At the same anchor, `C3-CERT-R` draws one destination uniformly from the
broader current-slot hard-safe same-satellite relocation set before H3
certification. Its RNG uses the identical canonical derivation above with
namespace `SMC-ER-C3-CERT-R-v1`. It follows the same physical-ID hold and
three-interval evaluation contract and is never discarded for a poor future
outcome. This control tests whether the H3 certificate is worth its complexity.

`C3-RANK-R` draws uniformly from the surviving H3-certified destinations using
namespace `SMC-ER-C3-RANK-R-v1`. It separates the certificate from the
largest-`G_P` ranking rule. A one-element certified mask is retained and makes
`C3-RANK-R` equal the top-`G_P` choice; it is not resampled.

## Paired post-selection H3 evaluation

For each selected proposal, reconstruct reference, top-`G_P`, `C3-RANK-R`, and
`C3-CERT-R` twins from episode reset by replaying the identical frozen Main
physical-action prefix under freshly recreated evaluation RNGs. Prove equal
full anchor fingerprints before branching; no private snapshot API is assumed.
From the anchor onward, every branch sets `fading_enabled=False`; the held-out
realised-mobility stream remains the untouched evaluation stream and was
unavailable to the forecast. This Stage-0 result therefore has no actual-fading
robustness claim.

At each interval, the same frozen Main version independently generates every
non-focal masked-greedy action on each branch's own observation. Reject the
causal contract if any non-focal physical action differs across the four
branches. The reference focal holds its source; the three relocation branches
relocate once and hold their frozen destinations. Run exactly three intervals
with common initial realised-mobility RNG states. All pass statistics use only
these post-selection fading-off branches. Retain every outcome; never filter
on power, rate, reward, or EE.

Record interval and horizon totals for useful bits, payload energy, canonical
EE, system power, focal marginal power, service, active sets, `phi1/phi2`,
physical actions, remapping, RNG hashes, and preview/commit parity. The primary
paired effects are

```text
Delta_E_payload_ref  = E_payload,reference - E_payload,top-GP
Delta_EE_ref         = EE_top-GP - EE_reference
Delta_E_payload_cert = E_payload,C3-CERT-R - E_payload,C3-RANK-R
Delta_EE_cert        = EE_C3-RANK-R - EE_C3-CERT-R
Delta_E_payload_rank = E_payload,C3-RANK-R - E_payload,top-GP
Delta_EE_rank        = EE_top-GP - EE_C3-RANK-R.
```

Positive is favourable for both. No handover energy or time value is invented;
the canonical environment's current EE is used unchanged and event counts are
reported separately.

Each eligible anchor has weight one. A seed mean averages its eligible anchors
equally; the pooled mean averages all eligible anchors equally. The seed-t95 is

```text
mean(seed_means) - 2.776445105 * sample_sd(seed_means) / sqrt(5).
```

Direction counts give each seed mean one vote. No seed with zero support is
imputed and no episode, step, user, or seed is reweighted after observation.

The full anchor fingerprint hashes canonical serialization of epoch and step;
user positions/headings; dwell anchors; D2 tracker state; association ledgers
and segments; previous radiating, demand, and association maps; candidate
tables; pending ages; environment, mobility, and age RNG states; and frozen TLE
records/NORAD order. All reconstructed twins must match field-by-field and by
SHA-256 before branching.

## Frozen pass/fail rule

Return `C3_STAGE0_PASS_TO_IMPLEMENTATION_RULING_ONLY` only if all hold:

1. every engineering/hash/clone/remapping/preview/non-focal equality and PA
   identity check passes;
2. all five seeds have selected support and there are at least 20 selected
   proposals total; no zero-support seed mean is imputed;
3. post-selection `Delta_E_payload_ref` and `Delta_E_payload_cert` each have a
   positive pooled mean, positive seed mean in at least four of five seeds, and
   seed-mean t95 lower endpoint above zero using
   `t_0.975,4 = 2.776445105`;
4. post-selection `Delta_EE_ref` and `Delta_EE_cert` independently satisfy the same
   pooled, four-of-five, and seed-t95 rule;
5. at every interval all four branches have identical served-user, active-beam,
   and active-satellite sets; no relocation loses focal service; the top-`G_P`
   horizon useful bits are not below reference and `C3-RANK-R` useful bits are
   not below `C3-CERT-R`; and each relocation has exactly one expected initial
   `phi1`, no `phi2`, and no later additional event; and
6. every selected deterministic certificate has strictly positive `G_P`.

`Delta_E_payload_rank` and `Delta_EE_rank` are reported but do not gate
Stage-0; learning whether `Q3` can outperform uniform ranking belongs to a
later pilot.

Return `C3_STAGE0_CERTIFICATE_FAILURE` for an engineering or outcome-timing
leak. Otherwise return `C3_STAGE0_FAIL_DROP_ROLE`. A pass is conditional
paired Stage-0 evidence only and still requires an explicit C3 implementation
ruling plus deterministic fixtures. It does not authorize a learner, replay
transfer, carrier smoke, training, or an effectiveness/novelty claim.
