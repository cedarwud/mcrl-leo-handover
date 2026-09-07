# C2 persistence-option Stage-0 candidate — scalarized Main V2

Status: frozen candidate specification for a new, non-training C2 role gate.
This document is not a result, does not supersede the sealed legacy C2
time-only evidence, and does not authorize a carrier, specialist training, or
Main replay routing.

Date: 2026-08-28

## Purpose and authority

The earlier C2 Stage-0 runner was bound to a Q1-only Main reference and to a
stale method digest. That is not the current SMC-ER authority. This V2
candidate evaluates exactly the persistence option described in
`docs/MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md`, with the corrected
Main policy kept intact:

```text
Q_M^sc(s,a) = 0.5 Q_1^M(s,a) + 0.3 Q_2^M(s,a) + 0.2 Q_3^M(s,a)
```

Main action selection is masked-greedy on this scalarized surface. There is no
Q1-only selection, private C2 reward shaping, time-only EE ledger, optimizer
update, replay update, action vote, auction, coordinator, or post-training
override in this gate.

The byte authorities frozen for this candidate are:

| Input | Path | SHA-256 |
|---|---|---|
| method contract | `docs/MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md` | `0e67e6aa570158dd1433afe98d4992ed278db1cb5d586f6aff6680e0c7696d2e` |
| corrected preregistration | `artifacts/PREREG-FROZEN-2026-08-25-R2.json` | `8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543` |
| corrected Main checkpoint | `artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt` | `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b` |
| current analysis source bundle | repository MODQN/runtime code digest | `4cfc7e3043453994fc0686c3bbfa14d9a95156aeabc578b26decb2f210603a2e` |

The earlier C2 specification and its sealed outputs remain historical
evidence. The legacy runner is retained only as a pinned physical-environment
adapter for this V2 implementation; its repaired causal guards are included
in the exact closure and are not authority for the V2 policy choice. No
historical result is re-hashed, reused, or relabelled as V2 evidence.

## Scientific question

At a pre-outcome boundary where the focal user has a continuing served
physical incumbent and at least two current-safe physical associations, does a
three-interval persistence option reduce the focal user's canonical continuity
penalty relative to both a matched uniform-safe option and stay-if-possible?

The direct endpoint is the unchanged canonical event reward

```text
r_{2,u}(t) = -Psi_u(t) in {0, -varphi_1, -varphi_2}.
```

The gate is an opportunity-existence test for a future `F_2` specialist. A pass
does not establish that `Q_2^F` learns the option, that Main benefits from its
experience, or that EE improves. EE, useful bits, power, and service are
supporting interaction endpoints only.

## Frozen Main and causal protocol

At every anchor, all reference and candidate forecasts use the same corrected
checkpoint and the same scalarized, masked-greedy Main version. The policy is
read-only and deterministic at inference. The focal user is the only user
whose option is changed; non-focal users follow Main independently on each
branch. A branch is invalid if non-focal physical actions differ across the
paired branches, because that would confound a focal persistence intervention
with a changed joint policy trajectory.

The anchor is reconstructed from reset by replaying the frozen Main physical
action prefix. The full anchor fingerprint includes the mutable environment
state, candidate tables, association and dwell ledgers, previous maps, pending
ages, environment/mobility RNG states, and the observation masks/state. Every
twin must match field-by-field and by SHA-256 before branching. Every forecast
replay and every realised branch replay must then match this original
`_anchor_row()` fingerprint exactly; any mutable, physical, observation, or RNG
drift fails closed. A forecast RNG
is derived from a domain-separated namespace, checkpoint digest, evaluation
seed, anchor step, and focal user. It is a newly constructed generator and may
not read or copy the eventual mobility/fading RNG. Forecast environment and
forecast mobility use separate domain-separated generators; both are separate
objects from the realised streams, and fading is explicitly disabled before
any forecast draw.

The no-option Main forecast and every candidate option forecast are generated
as separate branch-local scripts. A candidate script applies its own focal
physical-ID option while computing the other users' frozen-Main actions. Its
non-focal physical-ID signature must match the independently generated
no-option signature at every forecast interval; otherwise that candidate is
invalid and cannot be selected. The script is never shared between candidate
branches.

From the anchor onward, paired realised evaluation branches disable fading but
keep their common realised mobility stream. Each branch uses the same frozen
Main policy for every non-focal user. The treatment binds a physical
satellite/beam ID for three executed intervals, remapping that ID through each
new candidate table. It releases the focal user to scalarized Main at the
fourth interval and thereafter. Invalidity, disappearance, service failure,
episode end, or option expiry terminates the option explicitly; a candidate
table index is never treated as a persistent identity and no bad outcome is
discarded. The interval that observes a service failure or other termination
is retained in the forecast/receipt; when the episode continues, scalarized
Main takes the next forecast interval, so recoverable Main fallback is not
itself a candidate invalidity. A fixed four-interval forecast is required
unless the episode ends before that horizon.

## Candidate and controls

The current-safe support contains only de-duplicated physical IDs whose action
is valid and deterministically service-feasible with fading disabled. The
incumbent must be in the support and the support must contain at least two IDs.

For the opportunity gate, `C2-PRE` uses an independent deterministic forecast
to score every current-safe ID by the focal cumulative canonical `r2` over the
three hold intervals plus the first release interval. It chooses the largest
score (least penalty), then larger worst-interval deterministic link margin,
then lexicographic physical ID. The selector cannot read realised rewards,
future realised RNG, fading, EE, or a stochastic successor. It supplies no
training label.

Controls use the identical support, forecast/evaluation RNG derivation,
physical-ID remapping, horizon, termination, fallback, and branch accounting:

```text
C2-RANDOM    uniform current-safe physical ID
C2-STAY      qualifying incumbent physical ID
```

`C2-STAY` therefore has no trigger-time redraw: the incumbent is already
required to be in the current-safe support. If its persistence option later
terminates, the focal user uses the same frozen scalarized-Main fallback as
`C2-PRE` and `C2-RANDOM` on the next forecast/evaluation interval; no control
silently samples a replacement association.

The branch retains all canonical reward vectors and all service/outage/event
outcomes. Only the focal option differs by construction.

A forecast with no served interval has no deterministic link-margin tie-break
and is ineligible; it must fail closed rather than emit a null margin into the
candidate ranking.

## Frozen support, seed, and pass rule

Before revealing any evaluation seed, the candidate spec, V2 runner, tests,
legacy environment adapter, current MODQN/runtime source digest, checkpoint,
preregistration, dependency versions, and frozen TLE inventory must be sealed
in a V2 closure manifest. The closure manifest is exact-file hashed and binds
the later seed manifest. A seed manifest must:

1. contain exactly five unique integer C2 seeds;
2. identify namespace `C2-SCALARIZED-STAGE0-V2`;
3. attest repository-wide pre-reveal disjointness and bind a sealed search
   receipt;
4. list any prior formal C2/C3/validation seed values and be disjoint from
   them; and
5. bind the closure-manifest SHA-256.

The runner rejects missing, malformed, duplicate, reused, or closure-unbound
seeds before constructing an environment. No seed values are committed to
this candidate document; they may remain in the separately sealed seed
manifest until the closure and tests are independently accepted.

The closure is accepted only after both the scalarized-V2 and legacy C2
semantic suites pass. Each test receipt carries its exact argument vector,
working directory, raw-output digest, and duration-normalised output digest;
the verifier re-runs the recorded commands before accepting the closure. The
disjointness receipt is likewise re-read and its candidate decisions and
repository search are recomputed, with only the exact post-reveal receipt
files excluded on a later load. Those ignored paths are exactly the canonical
closure manifest, disjointness receipt, and seed manifest in one freeze output
directory; that directory must be outside the repository, and no additional
path is permitted even if it shares the directory.

The formal gate requires at least one eligible anchor in each of the five
seeds and at least 20 paired eligible anchors in total. For **each** control,
both of these windows must pass:

```text
Delta_R2(control) = sum(r2_focal,C2-PRE) - sum(r2_focal,control)
```

- positive pooled mean; and
- positive seed mean in at least four of five seeds.

The windows are the first post-release interval and the complete
anchor-to-episode-end trajectory. No service safeguard may fail: treatment may
not turn a control-served focal outcome into unserved, and the aggregate served
fraction may not decline by more than 0.005 versus either control. All
preview/commit identities, RNG independence, anchor/twin hashes, physical-ID
remapping, non-focal equality, positive-power EE identities, and branch-length
guards must pass. Otherwise the result is either a certificate failure (for an
engineering/causal violation) or `C2_STAGE0_FAIL_DROP_ROLE`.

An R2 pass with neutral or negative EE is reported only as a continuity result.
It cannot be relabelled as an EE improvement. A failure cannot be rescued by
retuning the horizon, support threshold, selector, weights, seed set, or
service tolerance after outcomes are inspected.

## Receipt contract and claim boundary

The V2 result receipt must include the exact input hashes, scalarized weight
row, policy-selection mode, closure and seed-manifest hashes, runtime
versions, per-seed focal schedule, anchor eligibility/support, forecast and
realised RNG hashes, branch fingerprints, physical-ID scripts, all option
termination reasons, canonical R2 windows, service/event counts, throughput,
power, ratio-of-sums EE, and engineering failures. Aggregation gives every
eligible anchor unit weight, every seed one directional vote, and never imputes
zero support.

The only allowed positive scientific statement from a successful receipt is
that the scalarized-Main persistence option has Stage-0 paired support for the
canonical R2 objective under fading-off evaluation. The result cannot authorize
specialist training or Main routing until the separately specified C2
Main-consumer/atomic-bundle gate passes.

The V2 runner performs no training and must refuse to overwrite an existing
output. It is suitable for a bounded five-seed role gate; no long carrier run
is part of this candidate.
