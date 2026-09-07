# C2 boundary-persistence evidence re-adjudication

Status: read-only re-adjudication of an already-frozen state-only receipt. No
new experiment, reward, runtime, replay, training, or manuscript authority.

Date: 2026-08-27

## Receipts

- Frozen v2 state-only spec SHA-256:
  `9a0a70dac4f8f892a29a5162692b0464406899d7deb6b8ea6327a17ac369a760`
- Confirmation receipt SHA-256:
  `cd88d8c5b17d163a957d8c2e56c2995080c4bb1636cbcc93fae13b234ba50658`
- Derived analysis SHA-256:
  `742837883aec098c766fa5504e51ff5e3e9eb5bdee09de818059eeb1071e3cab`
- Ten evaluation seeds: `2026082401` through `2026082410`.
- Legacy-narrow checkpoint/geometry only.

## Mechanism correspondence

The frozen family `r2_access_exact_stay` is the state-observable core of the
ADR-003 C2 mechanism:

- the focal access vector exposes one valid continuing incumbent;
- the Q1-only Main reference chooses a different physical association;
- the challenger changes only that focal action back to the incumbent;
- the proposal is fixed before the current outcome; and
- the full counterfactual is evaluated with every other action fixed.

It is not a trained C2 policy and does not test replay transfer. It establishes
that the intended boundary-persistence support is already measurable from the
live focal observation.

## Existing result

From 1,000 sampled focal user-steps:

| Quantity | Result |
|---|---:|
| exact-stay eligible | 758 |
| lower handover class/cost | 758 / 758 |
| immediate EE positive and service-safe | 393 / 758 (51.84697%) |
| seeds with at least one joint-positive row | 10 / 10 |
| seed-clustered joint-positive rate t95 | 48.32681% to 55.19968% |
| service-unsafe alternatives | 1 / 758 |

Across all 758 evaluated alternatives:

- mean immediate `Delta EE = +0.0366775 Mbit/J`;
- median immediate `Delta EE = +0.0351402 Mbit/J`;
- mean throughput change `= +0.333029 Gbit/s`;
- mean payload-power change `= +3.436371 W`.

Thus persistence is not a power-saving rule: it commonly pays more recurrence
power. Its plausible EE pathway is avoiding a handover while often preserving
or increasing useful rate enough to offset that power. This is physically
distinct from C3's denominator-relief pathway.

The original frozen decision was
`ADVANCE_TO_PHYSICAL_HANDOVER_PARAMETER_GATE_ONLY`. That decision remains the
claim ceiling.

## What is and is not closed

Closed at diagnostic level:

- abundant, cross-seed state-observable support;
- exactly one focal intervention with no action fusion;
- a direct avoided-event pathway distinct from C1 and C3; and
- immediate EE-positive opportunities in every seed.

Open:

- accepted `T_HO/E_HO` and re-entry boundary;
- a total C2 reward over all event classes;
- deterministic service-feasibility admission (one unsafe row existed);
- specialist learnability versus same-support random control;
- full transition/replay parity and Main transfer;
- primary geometry and held-out temporal-ledger effect.

Because a persistence branch removes an event, any non-negative incremental
event energy would favour it relative to the handover reference. This monotone
direction does **not** supply a value for `E_HO`, and it cannot rescue a branch
whose rate/power trade-off fails the eventual temporal ledger. A future shadow
should report symbolic or break-even event-energy quantities rather than
inventing joules.

## Claim ceiling

The defensible statement is:

> C2 boundary persistence already has abundant state-observable one-focal
> support and a non-trivial immediate-EE-positive subset under legacy
> sensitivity physics, so it is a credible new Catfish hypothesis; physical
> timing/energy closure and learning/transfer evidence are still absent.

Do not call C2 effective, implemented, trained, or a proved temporal-EE
improvement.
