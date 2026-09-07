# Draft C3 reward-aligned Stage-0 role gate v2

Status: bounded pure semantic core implemented for engineering review; **not
frozen, not operationally executable, and no seed reveal is authorized**.
This file supersedes the power-primary C3 Stage-0 specification only after the
method gate, operational runner, tests, and a new closure manifest all pass.

Date: 2026-08-27

## Question and permitted interpretation

Does the action space contain enough pre-outcome-certified, same-satellite
one-user relocations for which the simple maximum-load-gap policy improves the
system's cumulative unchanged canonical R3 relative to both uniform certified
selection and the unchanged Main reference, through the first post-release
interval and to episode end, without breaking the power, service, identity, or
causal guards?

A pass means only that the C3 option class and non-learning ranking rule have
support worth carrying to an explicit implementation ruling. It does not mean
that `Q_3^F` learns the rule, that Main can consume its bundles, or that EE
improves.

## Authority and fixed inputs

- Recorded method-review authority (currently stale and not a closure):
  `docs/MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md`, SHA-256
  `d0768cf721cd24e4e78fa2cc519c8244786f1486e90ab6a1d78f2286bcbb2228`.
- Corrected Main checkpoint:
  `artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt`, episode
  8999, SHA-256
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`.
- Frozen preregistration:
  `artifacts/PREREG-FROZEN-2026-08-25-R2.json`, SHA-256
  `8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543`.
- Legacy-narrow corrected environment, 100 users, ten intervals per episode.
- Main behavior is frozen masked-greedy Q1-only. No optimizer or replay update.
- The option holds for `H_3=3` intervals, `h=0,1,2`; `h=3` is the first
  post-release interval. The decision interval remains `30.08 s`.
- Power equality tolerance is `1e-10 W`; reward/load identities are exact
  integer checks before any float comparison.

The final freeze must replace the method hash above if the reviewed bytes
change and must add the reviewed-analysis source hash. No output may be
interpreted under a stale authority hash.

At this bounded implementation checkpoint, the live method bytes hash to
`a42a66be367247d96a54091034f7cada89796b34e47660a225400310f26a49fd`,
which does not match the recorded hash above. The `authority_hashes` guard is
therefore externally open and must remain false. This spec edit does not
choose which method snapshot is authoritative, update a closure manifest, or
permit an operational runner or seed reveal.

Five wholly new evaluation seeds are revealed in a separate manifest only
after this spec, the replacement runner/tests/helpers, the companion C2
dependencies, checkpoint, preregistration, dependency versions, and every
frozen TLE file are closed by SHA-256. The seeds must be disjoint from every
previously named C2, C3, training, evaluation, pilot, and probe seed in the
repository. No old C3 seed or outcome may be reused.

For every revealed seed, census all 100 focal users at anchor steps
`t in {0,...,6}`. This leaves the three forced intervals plus `h=3` inside the
ten-interval episode. No outcome-dependent focal subsampling is permitted.

### Fail-closed machine input contract

- A physical ID is exactly a two-item Python tuple `(satellite_id, beam_id)`;
  both components are nonnegative exact integers. Booleans, floats, strings,
  lists, truncation, and implicit casts are invalid.
- A C3 destination is distinct from the source and has the same satellite ID.
- Every forecast and realised branch interval retains a complete map from all
  99 non-focal user IDs to either one strict physical ID or explicit `None`.
  The focal ID is excluded and no non-focal user may be omitted.
- Event fields use only the closed classes `none`, `phi1`, `phi2`, `reentry`,
  and `reversal`. During certification, the reference event is `none` at all
  three intervals; the candidate event is `phi1` at `h=0` and `none` at
  `h=1,2`.
- Loads, R3 totals, powers, service fractions, seed/step/user IDs, booleans,
  sets, and traces are type-checked without coercion. A missing, malformed,
  duplicate, non-finite, or inconsistent field cannot enter support or a
  positive gate; receipt-level malformed input returns certificate failure.

## Canonical C3 quantity and construction identity

The runner reads the natural, unscaled canonical reward emitted by the
environment:

```text
r_{3,u}(t) = -U_{s,v}(t)
```

for a served user `u` on physical beam `(s,v)`. Unserved users contribute the
environment-defined zero. The system total must satisfy the existing runtime
identity

```text
sum_u r_{3,u}(t) = -sum_{s,v} U_{s,v}(t)^2.
```

For a reference/candidate fork that differs only by moving the focal user from
`(s,v)` to `(s,v')`, take both loads from the post-feasibility reference
resolution. The source count includes the focal user and the destination count
excludes it. The runner must assert

```text
Delta sum_u r_{3,u}(h)
  = sum_u r_{3,u}^{candidate}(h) - sum_u r_{3,u}^{reference}(h)
  = 2 * (U_{s,v}^{reference}(h) - U_{s,v'}^{reference}(h) - 1).
```

The exact strict-improvement condition is therefore

```text
U_{s,v}^{reference}(h) >= U_{s,v'}^{reference}(h) + 2.
```

Every assertion uses `eligible_load_by_beam`. The lagged
`demand_by_beam` quantity is logged only for the later Main-consumer
representability test and may never substitute for eligible load.

For each fork, `sum_b U_b` must equal the size of that fork's served-user set,
and the positive load keys must equal its active-beam keys. Reconstruct the
load map independently from served non-focal physical actions, then add the
served focal user to the reference source or candidate destination exactly
once. Both reconstructed maps must equal the logged eligible-load maps before
the squared-load identity or one-user delta is accepted.

## Sealed deterministic forecast

At each anchor, derive the forecast seed as

```text
int.from_bytes(
  SHA256(UTF8(canonical_json([
    "SMC-ER-C3-FORECAST-v2", checkpoint_sha256,
    evaluation_seed, step_index, focal_user
  ]))).digest()[0:16], "big"
)
```

where canonical JSON uses `sort_keys=True`, `separators=(",", ":")`, and no
ASCII escaping. Initialize `numpy.random.SeedSequence`, then
`numpy.random.PCG64`. The forecast stream must be independent by object and
state from the eventual environment mobility/fading stream and shared exactly
between every reference/candidate forecast pair.

The held-out realised stream uses a distinct
`SMC-ER-C3-REALISED-v2` domain. Each derivation creates a fresh `SeedSequence`,
`PCG64`, and `Generator`; neither forecast construction nor arm selection may
accept, copy, advance, or return an environment RNG object.

Reconstruct the anchor separately for each fork, disable fading, and advance
geometry and candidate tables normally. At every `h in {0,1,2}`, the same
frozen Main version independently generates non-focal masked-greedy physical
actions in both forks. The reference focal user holds source physical ID
`(s,v)`. The candidate moves to destination physical ID `(s,v')` at `h=0` and
holds it at `h=1,2`. Every step remaps the physical ID after candidate-table
rebuild; table indices are never treated as persistent identities.

The certificate may read masks, association and segment state, eligible loads,
exact recurrence, physical link powers, and its independent deterministic
forecast outcomes. It may not read or copy actual future mobility/fading RNG
state, realised fading, stochastic reward, EE, rate, or a stochastic
successor.

## Four nested support layers

The census records every candidate in a waterfall. A candidate can enter a
later layer only after passing every earlier layer.

1. **Hard-safe support.** The reference focal user is served on a continuing
   incumbent with no current event. The destination is a de-duplicated,
   different, already-active beam on the same satellite. At every forecast
   interval, both focal holds are mask-valid and service-feasible, non-focal
   physical actions are identical, served-user/active-beam/active-satellite
   sets are identical, and only the declared initial `phi1` occurs.
2. **Strict-load support.** At every forecast interval, the reference eligible
   loads meet the integer `+2` condition; candidate/reference load maps differ
   only by source `-1` and destination `+1`; and the exact total-R3 identity
   above holds.
3. **Persistent-power support.** At every forecast interval,
   `P_ref^N(h)-P_cand^N(h) >= 0`, with a strict difference beyond tolerance at
   least once. The existing PA recurrence identity residual is at most
   `1e-10 W`.
4. **Joint certificate.** Hard-safe, strict-load, and persistent-power support
   all pass, with no hidden fallback, extra event, or service failure.

Log hard-safe, load-only, power-only, joint-pass, and load/power
sign-disagreement counts separately. Load and power have different units: the
runner must never add them, normalize them into a joint score, or expose them
as a shaped learning reward.

The three power intervals are exactly `h=0,1,2`; this is not a caller-selected
horizon. For each fork and interval, the runner supplies the per-radiating-beam
PA supply map and the radiating-beam count by satellite. The semantic core
recomputes, using the frozen runtime constants,

```text
P^f = 0.338 * number_of_radiating_beams
      + 0.200 * number_of_satellites_with_a_radiating_beam
P^N = P^f + sum_{radiating beams} P^p_{s,v}.
```

The beam keys must reproduce the per-satellite counts exactly. Logged
`fixed_power_w` and `system_power_w` are parity assertions only and are never
trusted as the power comparison. Non-finite or negative components, a changed
constant, a zero supply value on a declared radiating beam, a count/key
mismatch, a reported-total mismatch, or a PA recurrence residual beyond
tolerance fails the power layer.

For each joint candidate record separately

```text
G_U = sum_{h=0}^{2}
        (U_{s,v}^{reference}(h) - U_{s,v'}^{reference}(h))

G_P = 30.08 * sum_{h=0}^{2}
        (P_ref^N(h) - P_cand^N(h)).
```

`G_U` ranks load gap. `G_P` is only a power-certificate diagnostic and
tie-breaker. They are never summed.

## Frozen non-learning arms

- `reference`: bind the continuing source physical ID for `h=0,1,2`.
- `C3-SAFE-R`: draw uniformly from persistent hard-safe support.
- `C3-LOAD-R`: draw uniformly from persistent strict-load support before the
  power safeguard.
- `C3-CERT-R`: draw uniformly from the joint certificate.
- `C3-GAP`: maximize `G_U` inside the joint certificate, then larger `G_P`,
  then lexicographic destination physical ID.

The earlier method phrase `C3-PRE` refers to the Stage-0 use of the same
non-learning `C3-GAP` rule; receipts and code use `C3-GAP` as the sole arm
identifier. `C3-I` is excluded because Stage-0 contains no learner.

Each random arm uses a domain-separated v2 namespace of the form
`SMC-ER-C3-<ARM>-v2`, with the same checkpoint/seed/step/user tuple as the
forecast. A one-element set is retained. No arm is redrawn or discarded after
its outcome is observed.

All relocation arms use identical option semantics. Move once at `h=0`, hold
the selected physical association for `h=1,2`, release at `h=3`, and use
frozen Main for the focal user thereafter. Invalidity, deterministic service
failure, episode end, or horizon exhaustion terminates the option explicitly;
frozen Main begins on the next interval. There is no hidden substitute action.

The executable seam is an explicit sequential state machine. `forced` emits
the selected destination at `h=0,1,2`; `h=0` records `phi1`. At `h=3` it emits
no option action, changes to `released`, and marks frozen Main as controller.
Invalid hold, deterministic service failure, or episode end emits no substitute
action and changes to `terminated`; Main becomes controller only on the next
interval. Out-of-order interval advancement is malformed input.

## Paired held-out evaluation

An anchor is primary-gate eligible only when joint support is non-empty, so
both `C3-CERT-R` and `C3-GAP` are defined. Freeze all arm choices before
evaluation. Then reconstruct five twins from episode reset by replaying the
identical frozen-Main physical-action prefix under freshly recreated
evaluation RNGs. Prove equal full anchor fingerprints before branching; no
private snapshot API is assumed.

From the anchor onward, set `fading_enabled=False`. Use common initial
held-out realised-mobility RNG states that were unavailable to the forecast.
This Stage-0 result therefore makes no actual-fading robustness claim. On each
branch and interval, frozen Main independently generates all non-focal actions
from that branch's own canonical observation. The causal contract fails if
any non-focal physical action differs across branches through episode end.

The focal user follows its frozen option through `h=2`, releases to frozen
Main at `h=3`, and follows Main to episode end. Keep every branch outcome,
including an R3 loss, realised power increase, extra event, early option
termination, or outage. Such an outcome may fail a gate but is never filtered
out.

For each arm, record separately over `(a)` the forced option window `h=0..2`,
`(b)` the extended window `h=0..3`, and `(c)` anchor to episode end:

- natural system `sum_u r_{3,u}`, plus the per-beam squared-load identity;
- eligible loads and lagged ungated demand by physical beam;
- focal/system service, useful bits, system energy, system total power, and
  ratio-of-sums canonical EE;
- `phi1`, `phi2`, re-entry, reversal, and later event counts;
- physical actions, remapping, option state/termination, masks, RNG hashes,
  preview/commit parity, and anchor fingerprints.

The primary paired effects for window `W` are

```text
Delta_R3_ref(W)  = R3_C3-GAP(W) - R3_reference(W)
Delta_R3_cert(W) = R3_C3-GAP(W) - R3_C3-CERT-R(W).
```

Positive is favourable. The gate uses `W=extended` and `W=episode`. The
within-certificate window is a construction check only and receives no
statistical test. Also report, without making them rescue endpoints,
`C3-LOAD-R - C3-SAFE-R`, `C3-CERT-R - C3-LOAD-R`, and every EE/power/useful-bit
contrast needed to separate load support, the power safeguard, and ranking.

Each eligible anchor has weight one. A seed mean averages its eligible anchors
equally; the pooled mean averages all eligible anchors equally. Direction
counts give each seed mean one vote. No zero-support seed is imputed, and no
episode, step, user, anchor, or seed is reweighted after outcomes are seen.

The full anchor fingerprint hashes canonical serialization of epoch and step;
user positions/headings; dwell anchors; D2 tracker state; association ledgers
and segments; previous radiating, demand, and association maps; candidate
tables; pending ages; environment, mobility, and age RNG states; and frozen
TLE records/NORAD order. All reconstructed twins must match field-by-field and
by SHA-256 before branching.

## Frozen directional pass/fail rule

After this draft is formally closed, return
`C3_STAGE0_PASS_TO_IMPLEMENTATION_RULING_ONLY` only if all hold:

1. every hash, clone, replay, remapping, preview/commit, RNG-independence,
   non-focal-action, reward/load, PA recurrence, and outcome-timing check
   passes;
2. every one of five new seeds has at least one joint-certified eligible
   anchor and total paired support is at least 20 anchors;
3. for **each** of `Delta_R3_ref` and `Delta_R3_cert`, the full-episode pooled
   mean is positive and the seed mean is positive in at least four of five
   seeds;
4. condition 3 independently holds through the first post-release interval;
5. every selected `C3-GAP` forecast certificate satisfies the strict-load and
   power conditions, and on held-out realised branches the reference-minus-
   `C3-GAP` system-power difference is nonnegative at each forced interval and
   strictly positive at least once;
6. no `C3-GAP` focal branch changes served to unserved, aggregate served-user
   fraction declines by at most `0.5` percentage points versus each primary
   control, and no zero-power, physical-identity, or event guard fails; and
7. the receipt contains the complete support waterfall, all retained negative
   outcomes, and the required extended/episode direct and supporting
   contrasts.

Every retained anchor receipt has the exact branch-key set
`{reference, C3-SAFE-R, C3-LOAD-R, C3-CERT-R, C3-GAP}` plus evaluation seed,
step, focal user, full anchor fingerprint, and the eight named waterfall
counts. Each branch retains finite extended/episode R3, three full power
snapshots, focal service through at least `h=3`, served fraction, and the full
non-focal action and event-class traces through episode end. Missing or
additional arms fail the receipt. The forced-window event trace is `none` for
the reference and `phi1, none, none` for each relocation arm; later events are
retained rather than filtered.

The receipt guard ledger names at least `authority_hashes`,
`clone_fingerprints`, `prefix_replay`, `physical_remapping`,
`preview_commit_parity`, `rng_independence`, `reward_load_identity`,
`pa_recurrence_identity`, `outcome_timing`, `five_arm_receipt`,
`anchor_fingerprints`, `support_waterfalls`, `aggregate_recomputed`, and
`nonfocal_causality`, `event_timing`, `focal_service_guard`,
`realised_power_guard`, and `service_fraction_guard`. Missing, non-Boolean, or
false engineering guards return certificate failure. Realised service or power
outcomes remain retained
scientific outcomes and, when otherwise well-formed, lead to drop-role rather
than being relabelled as engineering errors.

All pooled means, seed means, direction counts, and support counts are
recomputed internally from retained per-anchor rows. An externally supplied
aggregate is accepted only as a byte-for-byte-equivalent check value; any
difference from internal recomputation is certificate failure.

Return `C3_STAGE0_CERTIFICATE_FAILURE` for an engineering, identity,
construction, or pre-outcome/held-out leakage failure. Otherwise return
`C3_STAGE0_FAIL_DROP_ROLE`. No horizon, support layer, selector, control,
threshold, endpoint, subgroup, or seed may be revised after outcomes to rescue
C3 under the current gate budget.

An R3 pass with neutral or negative EE is reported as load-balancing evidence,
not EE improvement. An EE or power gain without both primary R3 comparisons
does not rescue C3.

## Main-consumer boundary

This Stage-0 gate never routes a bundle. Current Main observes previous-step
ungated demand, whereas C3 constructs its support from current-step
post-feasibility eligible load. A Stage-0 pass therefore still leaves C3
shadow-only until a separate observational-alias and atomic-bundle consumer
gate proves that Main can use the exact executed canonical reward vector.

Only an explicit post-Stage-0 implementation ruling may authorize isolated
fixtures. Neither this draft nor a later Stage-0 pass authorizes Catfish code
under `src/mcrl`, carrier smoke, training, replay transfer, a novelty claim, or
an effectiveness claim.

Passing the pure-core tests establishes only engineering behavior at these
seams. Tests are not Stage-0 observations, do not establish support or effect
direction, and provide no scientific effectiveness evidence.
