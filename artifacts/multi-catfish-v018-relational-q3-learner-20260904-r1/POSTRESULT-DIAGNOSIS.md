# V0.18 relational-Q3 learner post-result diagnosis

Status: `VERIFIED_STOP__ROOT_CAUSE_REVIEW_IN_PROGRESS`.

Claim ceiling: opened TRAIN/VALIDATION learner diagnostics only. This document
does not authorize a retry, a new world, TEST access, episode training, a
physical EE claim, or a change to C1/C2.

## Verified result

- The source rectangle completed with `21/21` receipts and metadata closures.
- All three learners completed exactly 100 updates and reloaded bitwise.
- The independent gate closure returned `STOP_LEARNER_GATE`.
- Per-initialization validation skill was `-0.0785124`, `-0.0558140`, and
  `-0.0593407`; mean skill was `-0.0645557`.
- The three validation panels contained `484`, `430`, and `455` pivotal rows,
  but every learned Q3 produced zero action changes and zero positively
  supported changes.
- Learned Q3 validation surfaces had standard deviation between approximately
  `1.87e-10` and `6.57e-10`. Model MAE differed from the zero-Q3 MAE by less
  than `8e-10` in every initialization.

The STOP therefore identifies a learned-head failure. It is not evidence that
the exact or nominal physical C3 direction became EE-negative.

## Verified unit trace

The learner target is normalized once:

```text
t = target_surface_bits / kappa
```

The current head computes raw shared-scorer contributions, sums and centres
them, and then also divides its output by the same `kappa`:

```text
q = (sum(f_theta) - sum(f_theta)_reference) / kappa
```

Thus the mathematical optimum requires the ordinary neural scorer to emit
raw-bit contributions on the order of `kappa`, while the gradient reaching
that scorer contains a `1/kappa` factor. Here
`kappa = 0x1.2cea89d260f2ap+33`, approximately `1.01e10` bits. The trained
parameters moved only about `0.012`--`0.015` in maximum absolute difference
from initialization, while their returned Q3 surfaces stayed near `1e-9`.

## Current causal inference

The evidence is consistent with an ill-conditioned but algebraically correct
parameterization: the physical target and deployment units are normalized,
but the network is asked to learn an enormous latent raw-bit scale through a
gradient divided by that scale. A candidate repair is to let the shared scorer
predict normalized `bits/kappa` contributions directly and remove only the
final head division. That preserves the target, features, masks, relational
sum, reference centring, and unweighted Q1+Q2+Q3 deployment units.

This inference is awaiting independent Fable and Sol fresh-context review.
Any successor must use a new frozen contract and fresh validation worlds; the
opened V0.18 validation worlds cannot be reused for acceptance.
