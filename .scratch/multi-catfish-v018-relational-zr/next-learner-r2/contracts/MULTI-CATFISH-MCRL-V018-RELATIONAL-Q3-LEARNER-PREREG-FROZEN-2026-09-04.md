# Multi-Catfish MCRL V0.18 relational-Q3 learner gate

Status: `FROZEN_BEFORE_OUTCOME`.

Claim ceiling: fresh TRAIN/VALIDATION source-only learnability evidence. This
contract authorizes only the declared fresh source harvest and the
exactly-100-update source-only learner gate. It authorizes no TEST access,
episode-policy training, physical EE claim, or 9000-episode run.

## 1. Antecedent and single question

The sealed V0.18 analytic diagnostic returned
`PASS_ANALYTIC_DIAGNOSTIC`. Under the actual frozen learned-Q1+Q2 background,
the exact ZR arm improved pooled ratio-of-sums EE by `1.030617%` and the
parameter-free nominal relational arm by `1.102733%`; both were positive in
four of four worlds and three of three lineages with zero served-user-step
loss. These are TRAIN analytic facts, not learned-Q3 efficacy.

Fresh-context Sol Ultra, Fable Max, and Opus Max independently returned
`GO_FRESH_SOURCE_LEARNED_Q3_GATE`. Their GO decisions do not replace the
mechanical contract below.

This gate asks only:

> Can one victim-relational Q3 learn the unchanged exact ZR target from the
> already frozen deployable predecision representation on complete fresh
> worlds, and does its validation action effect remain positively supported?

C1/Q1, learned C2/Q2, canonical ratio-of-sums EE, ZR algebra, shared kappa,
native action mask, reference policy, and unweighted deployment sum are not
being redesigned here.

## 2. Fresh identities

Frozen identities, authenticated by the final pre-freeze census and manifest
closure:

- TRAIN worlds: `2026120501`, `2026120502`, `2026120503`, `2026120504`
- VALIDATION worlds: `2026120505`, `2026120506`, `2026120507`
- source lineages: `2026092101`, `2026092102`, `2026092103`
- Q3 initialization-to-lineage mapping:
  - `2026120511 -> 2026092101`
  - `2026120512 -> 2026092102`
  - `2026120513 -> 2026092103`

TRAIN and VALIDATION are separated by complete world. The already opened
V0.18 worlds `2026120401`--`2026120404` and every earlier V0.3--V0.17 world
are forbidden. No row-, user-, step-, or anchor-level split is permitted.

The final census is recorded in
`SEED-CENSUS-FROZEN-2026-09-04.md` and was repeated immediately before freeze
on both the local repository and the Ubuntu server.

## 3. Frozen background and source behaviour

Each source lineage uses its matching immutable checkpoints:

| lineage | Q1 rung-10 checkpoint SHA-256 | learned OPS-3 Q2 rung-3000 checkpoint SHA-256 |
|---|---|---|
| `2026092101` | `f26aab2fab6d31d6f3e4acd97782beeb0bba055ec94611dc9f3ed47038a231f0` | `d981232a9e56e6ce71c8e8b1fda789efc69852d4a6a22e918a2992ddc58a533d` |
| `2026092102` | `6930534d90840807c4dda1eda9c0ecf58793175053a37a43b75e38a7b6d310ba` | `9a45f5bc125d6ba453d7d74dbc640ec3d2e927fffb161518e383e6b3aabbe8ef` |
| `2026092103` | `507b871f2536097b400b099b9dcb666e8445e9aee921001d61e70ff6042646b2` | `8f9d2e5d1749515a0896137082b1430419ae1b8a794d28ea772a23c86648be81` |

At every decision step, the detached reference and executed source action are
the single native masked argmax

```text
a_ref = argmax_safe(Q1 + Q2_hat).
```

The source trajectory executes only `a_ref`. The exact ZR label never enters
the executed action. Each world uses one keyed common-random field. Each shard
contains ten physical steps and 100 focal-user rows per step, hence exactly
1000 rows; no sign, action-change, support, or target-magnitude filter is
allowed.

For every anchor the write order is fixed:

1. compute and detach `Q1`, learned `Q2`, native mask, and `a_ref`;
2. encode, copy, and authenticate the relational predecision tensors;
3. authenticate the evaluation-only `Q1+Q2_hat` background sidecar;
4. only then open the exact matched ZR measurement and attach the centred
   native-bit target;
5. prove the measurement did not mutate live environment or RNG state;
6. execute exactly `a_ref` once.

Q1 and Q2 parameter digests must be identical before and after every shard.

## 4. Learner input ruling

The learner input is exactly the V0.18 pre-outcome code-manifest schema:

```text
action_context:             (N, 28, 7)
victim_tokens:              (N, 28, V, 6)
action_mask:                (N, 28)
victim_mask:                (N, 28, V)
positive_credit_compatible: (N, 28)
reference_actions:          (N,)
```

The six-dimensional victim token is retained, including
`log1p_observed_candidate_sinr_at_reference_action`. This resolves, before
learner outcomes, the wording ambiguity in V0.18 Section 7:

- the field was already fixed in the V0.18 encoder schema and code manifest
  before the analytic outcomes;
- it is the current pre-action state gamma with provenance
  `theta-current-interference-previous-step`, also available to Q1;
- its keyed `observation` event is separate from the forbidden realised
  counterfactual `physics` event;
- it is neither an `ActionEvaluation`, a future value, a selected action, an
  exact target, nor a target-derived filter.

Retention is a pre-existing deployability ruling, not a claim that the
parameter-free nominal decoder internally consumes that scalar. A five-token
variant, alternative feature set, or second architecture is not authorized
after this gate opens.

`positive_credit_compatible` is a causal predecision side-channel computed
from opening service, physical beam identities, recurrence power, and network
activation compatibility. It may gate positive contributions but cannot
replace or narrow the native action mask. The exact target surface is a label
only and may never enter the forward inputs.

## 5. Exact target and network

The label is the unchanged ZR centred bit surface for the `Q1+Q2_hat`
reference. It is exactly zero at the reference action and outside the native
mask. Its normalization is fixed to

```text
kappa = 0x1.2cea89d260f2ap+33 bits.
```

The only learned module is `RelationalZRC3QNetwork`. It applies one shared
victim scorer, preserves victim permutation invariance, keeps all negative
victim contributions, admits a positive victim contribution only when the
predecision compatibility bit is true, sums over victims, centres at the
detached reference, divides by kappa, and finally applies the native mask.

Frozen learner configuration:

- action dimension: `28`
- action-context width: `7`
- victim-token width: `6`
- shared victim-scorer hidden layers: `(100, 50, 50)`
- activation: `tanh`
- optimizer: Adam
- learning rate: `0.001`
- batch size: `512`
- gauge coefficient: `0.0` because centring is structural
- updates: exactly `100`
- execution: deterministic CPU, one independent optimizer per initialization

The loss is the legal non-reference pairwise MSE between the learned and exact
centred surfaces, both on the `bits / kappa` scale. Loss is training plumbing,
not the binding validation decision.

The exact 100-batch row-index schedule for each initialization must be emitted
in the frozen run config before source outcomes are opened. It cycles equally
over the four TRAIN worlds and contains no validation identity.

## 6. Decision-level validation metrics and nulls

All metrics are computed independently for each initialization on its matching
three complete VALIDATION worlds, then pooled only by additive counts.

The evaluation-only background is `B = Q1 + Q2_hat`. Define:

```text
a_base    = argmax_safe(B)
a_teacher = argmax_safe(B + Z3_exact / kappa)
a_student = argmax_safe(B + Q3_hat)
```

Two state-independent nulls are fit or fixed without using learner outcomes:

1. `ZERO`: the all-zero Q3 surface, identical to `a_base`;
2. `ACTION_ONLY`: a 28-action potential fit by least squares from TRAIN-only
   exact legal reference/candidate differences, centred at each validation
   reference.

The strongest null is the one with the higher validation teacher-action
agreement on pivotal rows, ties to `ZERO`. This conservative comparator choice
does not alter a learner, seed, threshold, or architecture.

A pivotal row is one where `a_teacher != a_base`. For each initialization:

```text
validation_skill =
    P(a_student = a_teacher | pivotal)
  - max_null P(a_null = a_teacher | pivotal).
```

Also report all-anchor teacher agreement, stable preservation, pivotal
exposure and recovery, student change exposure, and every null score. MSE and
training loss are diagnostics only and cannot substitute for the decision
metric.

A student change is positively supported only when
`a_student != a_base`, the selected action has
`positive_credit_compatible = true`, and its exact centred target is strictly
positive. The supported-change rate is the supported student-change count
divided by student-change exposure.

## 7. Frozen acceptance rule

The final implementation must assert exactly three initializations and exactly
three validation worlds; no `min(panel_size, threshold)` relaxation is allowed.

`PASS_LEARNER_GATE` requires all of:

1. mean `validation_skill` is strictly positive;
2. at least two of three initialization skills are strictly positive;
3. pooled student-change exposure is positive and at least two of three
   initializations have positive exposure;
4. pooled supported-change rate is strictly greater than `0.50` and at least
   two of three initialization rates are strictly greater than `0.50`;
5. source, split, checkpoint, kappa, mask, finiteness, digest, reload, and
   Q1/Q2 immutability checks all pass.

No world unanimity, pairwise Catfish synergy, physical EE improvement, or
throughput floor is a condition of this source-only gate. Those belong to the
separately sealed physical five-arm screen.

Failure returns `STOP_LEARNER_GATE` and does not authorize a second seed set,
architecture, feature set, threshold, target, scale, or 100-update retry
against these outcomes. Pass only authorizes preparation of a separate
fresh-TRAIN short-episode physical screen.

## 8. Required receipts before freeze

The frozen closure must include and authenticate:

- this contract and a strict external run config;
- repeated local and Ubuntu-server seed censuses;
- one complete code manifest covering source harvester, relational encoder,
  exact ZR target, bridge/schema, background sidecar, learner/head, validation
  reporter, adjudicator, independent verifier, and focused tests;
- 21 write-once source closures: seven worlds by three lineages;
- source NPZ, metadata, array digests, predecision-capture digests, keyed-field
  roots, exact-target digests, background-sidecar digests, and shard receipts;
- three checkpoints, parameter digests, exact update counts, raw validation
  predictions, bitwise reload receipts, and Q1/Q2 checkpoint bindings;
- raw per-initialization validation counts, gate result, result seal, server
  preflight log, and artifact manifest;
- explicit `test_split_opened=false` and `episode_training=false` throughout.

## 9. Stop boundary and next step

This gate is one source harvest plus one exactly-100-update learner panel. It
never opens TEST and never runs an episode-policy learner.

If and only if it returns `PASS_LEARNER_GATE`, the next step is a separately
preregistered TRAIN-development physical screen with exactly five arms:

```text
FULL     = Q1 + Q2 + Q3
DROP_C1  = Q2 + Q3
DROP_C2  = Q1 + Q3
DROP_C3  = Q1 + Q2
MAIN     = frozen legacy baseline
```

That later block must checkpoint every 100 episodes. The user must be notified
again before any 9000-episode training. Neither a source-only pass nor a short
episode sign is a final efficacy claim.
