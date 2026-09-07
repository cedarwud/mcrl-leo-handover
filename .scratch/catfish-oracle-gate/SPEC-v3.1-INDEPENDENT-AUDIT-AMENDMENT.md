# V3.1 independent-audit amendment to the held-out R3 gate

Status: frozen after the engineering pilot but before the formal development
replay, collection of any new held-out outcome, or classifier fitting.

Date: 2026-08-26

This amendment is normative together with
`SPEC-v3-HELDOUT-STATE-LEARNABILITY.md`. It hardens that base specification in
response to a read-only independent audit; it does not use a held-out result.

## Strict topology label

For `r3_prev_inactive_split`, topology-positive now explicitly requires all of:

- the proposed physical beam is active in the alternative and absent from the
  Q1 reference active set;
- exactly one realised active beam is added;
- zero realised active beams are removed; and
- effective beam count increases by exactly one.

Positive load relief remains required. This explicit `removed = 0` condition
does not change any of the 184 v2 joint-positive rows, but closes a theoretical
receipt ambiguity before new data is collected.

## Stricter held-out pass conditions

Base-spec condition 3 is replaced by:

- ensemble held-out average precision must be at least all of `0.30`, held-out
  prevalence plus `0.05`, and `1.25` times held-out prevalence.

The following additional condition is required:

- at the frozen calibration-score threshold, at least 8 of 10 held-out seeds
  must each have joint precision at least `0.30`, joint recall at least `0.20`,
  and coverage between `0.05` and `0.50`.

All other base-spec pass conditions remain required. Proposal-SINR-only
performance remains a reported baseline; it is not a blocker because success
with a simpler strictly observable signal would still demonstrate state/action
separability.

## Head independence and reward boundary

The primary supervised model remains the actual Q-head input contract:
112-dimensional focal encoded state in, proposal-action output indexed. Q1
reference fields remain forbidden model inputs. The model is diagnostic only
and may not become a runtime gate.

If and only if the amended gate passes, the sole reward direction allowed into
the next shadow-reward design is an activation-regularised congestion reward:

```text
r3_u(t) = -[ U_bu(t) + lambda_on * I{N_bu(t-1) = 0} ]
```

The indicator uses the focal-observable previous beam demand, not another
user's simultaneous intent or a post-action `newly activated` oracle. The
activation price `lambda_on` must be fixed by a separate physical/contract
calibration and may not be tuned on the ten v2 confirmation seeds or the new
held-out labels. This formula is not authorized for runtime or RL training by
this amendment.
