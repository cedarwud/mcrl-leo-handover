# C3 intra-satellite bottleneck-relief shadow protocol

Status: frozen exploratory protocol before its dedicated runner or outputs
exist. Evaluation-only, legacy-narrow sensitivity; no reward, runtime,
preregistration, training, manuscript, or deployment authority.

Date: 2026-08-27

## Question

Does the live action space contain one-user, service-preserving transitions
that trade exactly one intra-satellite handover for a certified strict drop in
the current system power denominator?

This protocol follows the zero-support proof for the rejected same-handover-
class rule. It does not hide the R2 cost: the corrected C3 action deliberately
changes the focal handover class from `NONE` to `INTRA_SATELLITE`.

## Frozen reference and support

- Legacy checkpoint: completed 9,000-episode Main checkpoint already used by
  the Catfish diagnostic probes, with its existing SHA receipt.
- Geometry and reward authority: unchanged legacy-narrow environment only.
- Seed: `2026082701`.
- Episode: 100 users and all ten steps.
- Reference joint action: masked-greedy Q1-only Main action.
- Census unit: every user-step; no outcome-based resampling.

A focal row enters the candidate scan only if the Main reference:

1. serves the focal user on its continuing physical incumbent;
2. therefore has handover class `NONE`;
3. leaves at least two served users on the source beam; and
4. makes the focal user the strict unique source-beam link-power maximum.

For each de-duplicated valid focal action, an alternative is certified only if:

1. it selects a different cell on the same satellite, hence exactly one
   `INTRA_SATELLITE` event;
2. its destination beam is already active under the reference;
3. the exact training-only deterministic physics mask serves the focal user;
4. every user's served flag and the active beam/satellite sets equal the
   reference;
5. the candidate link power is no greater than the reference destination
   maximum; and
6. every non-focal physical action and link power is unchanged.

The scan may use masks, physical IDs, the association/segment ledger, and the
deterministic recurrence and service calculation. It may not use rate,
throughput, EE, reward, fading, or the successor to decide eligibility or
retention. Those quantities are read only after a candidate has been retained.

## Exact certificate

Let `p_src` be the focal reference power and `p_src_next` the maximum source
power after removing it. Let `S(p)` be the live PA supply-power function.
Because source and destination remain active, the destination maximum is
unchanged, and no satellite activation changes, every retained candidate must
satisfy

```text
Delta P_system
  = P_system(candidate) - P_system(reference)
  = S(p_src_next) - S(p_src)
  < 0.
```

The runner fails closed if the identity residual exceeds `1e-10 W`, if the
sign is not strict, or if any service/action/active-set invariant fails.

## Outputs and claim boundary

Report:

- counts of total user-steps, source-qualified rows, and certified candidate
  alternatives by step;
- source/destination keys, loads, powers, action IDs, and handover classes;
- predicted and realised power deltas and identity residuals;
- post-retention descriptive deltas in throughput and canonical EE;
- whether certificate inputs are available in the 112-dimensional Main state
  or only through the exact training-only mask.

There is no efficacy pass threshold. The classifications are:

- `ZERO_SUPPORT`: no certified candidate exists, so this C3 mechanism is
  rejected without training;
- `SUPPORT_PRESENT_SHADOW_ONLY`: at least one exists and every identity and
  invariant passes, permitting a state/representability design only;
- `CERTIFICATE_FAILURE`: any retained candidate violates the exact contract,
  so the mechanism is rejected.

Even `SUPPORT_PRESENT_SHADOW_ONLY` does not establish learnability, held-out EE
gain, causal Catfish benefit, or Multi-Catfish synergy.
