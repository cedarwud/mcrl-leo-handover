# Repriced C3 lambda-confound gate contract

Date: 2026-09-04 (Asia/Taipei)

Status: **FROZEN BEFORE ANY REPRICED C3 TRAJECTORY**

## Question and ceiling

This one matched development gate asks whether the existing zero-marginal
spatial C3 family still increases canonical ratio-of-sums EE after Q1 and Q2
have both been refit at the corrected development price

\[
\lambda'=118{,}424{,}222.8550065\ \mathrm{bit/J}.
\]

It is the predeclared falsification requested by the 2026-09-04 Fable source
audit.  It is not episode training, does not open TEST, and cannot establish
held-out efficacy.  C3 is an oracle/analytic surface in this gate; a passing
result still requires a separate Q3 source-and-learner gate.

## Frozen Q1/Q2 input

- merged source-only decision:
  `.scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/merged/result.json`
- merged file SHA-256:
  `4657a1f758fa83c92deb631231431abf6bae586c050abfffc9f7e06963d9029a`
- merged status: `GO_MATCHED_C3_GATE`
- Q1 rung: 10; Q2 rung: 3000.
- lineages and combined checkpoint SHA-256 values:
  - `2026092101`: `d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc`
  - `2026092102`: `bb45bed30465f8be0ea9a1463c3b6e958d8f8b90cf11b4cd8e5d56a71f4b7057`
  - `2026092103`: `32b5accfa1595ff19ddc11779402b5c86e115b883d04c6c5cbf90434ee32d44c`

No checkpoint, multiplier, normalization, or Q-head scale may change after
opening this gate.

## Frozen matched panel

- development TRAIN worlds: `2026121501`, `2026121502`, `2026121503`,
  `2026121504`;
- these four seeds were globally unused by prior text-visible C3 source,
  learner, oracle, or trajectory receipts at freeze time.  This was checked
  before outcome access with a hidden-inclusive repository census; binary
  model/array payloads were excluded from the text census;
- lineages: `2026092101`, `2026092102`, `2026092103`;
- users: 100; physical steps per trajectory: 10;
- arms: `BASE`, `EXACT_ZR`, `NOMINAL_ZR`;
- one fresh environment per arm;
- one common initial world and keyed fading field for all arms/lineages of a
  world, using field component `MCRL_V020_REPRICED_C3_GATE_V1`;
- canonical endpoint: total delivered bits divided by total network energy;
- masks, simulator physics, TLE authority, and action tie-breaking remain
  unchanged.

`BASE` executes one native masked argmax of `Q1 + Q2`.  `EXACT_ZR` adds the
existing exact unilateral zero-marginal teacher.  `NOMINAL_ZR` adds the
existing parameter-free relational nominal surface.  No Q3 rescaling,
threshold change, coordination, auction, vote, or post-action override is
permitted.

## Frozen checks and decision

Every row must pass state/RNG non-mutation, common-mask, finite-surface,
compatibility-reconstruction, and native-action mechanics.  Every treatment
must expose at least one action change in the pooled panel.

For each C3 arm versus `BASE`, define a directional pass as all of:

1. pooled ratio-of-sums EE is strictly greater than `BASE`;
2. relative EE is positive in all three lineages;
3. relative EE is positive in at least three of four worlds;
4. pooled served fraction is no more than `0.001` below `BASE`.

The gate emits exactly one decision:

- `GO_Q3_SOURCE_AND_LEARNER` if both `EXACT_ZR` and `NOMINAL_ZR` pass;
- `REVISE_NOMINAL_Q3` if only `EXACT_ZR` passes;
- `REDESIGN_R3_TARGET` if `EXACT_ZR` fails, irrespective of the nominal arm.

Observed signs may not trigger a new seed, scale, lambda, compatibility rule,
or acceptance threshold inside this gate.  A failing decision stops the
current C3 family and is reported before any replacement is designed.
