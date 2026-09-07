# Multi-Catfish MCRL V0.3 E1 instrument-validity contract

Date: 2026-08-31  
Status: **binding design; run remains unsealed until source seeds and digests are frozen**  
Endpoint: **no EE endpoint is permitted in E1**

## 1. Decision

The first 10-episode matched ablation is retained as engineering evidence and
is void as evidence about C1, C2, C3, or EE efficacy. The next scientific run
is E1: a held-out test of whether the three route-local Q functions learn
state-conditioned pairwise EE surplus and can each affect the single deployed
action. E1 precedes every further EE ablation.

The omission of an explicit frozen-Main action from the 228-dimensional state
is not, by itself, a proven structural failure. Frozen Main is a deterministic
function of its input, mask, checkpoint, and weights; the pair loss also
observes both the reference and candidate actions. Structural non-observability
requires an observed input collision, not a failed inference from architecture
alone.

## 2. Evidence corrections

1. Agreement among A101, A110, and N000 on the audited source rows does not
   establish global policy identity. Their common-state agreement must be
   reported as corpus-local.
2. The sealed 41-trace C2 V0.3B artifact proves physical headroom only. Its
   preregistration requires any learnability pilot to use non-overlapping
   seeds, so those 41 traces cannot become E1 training rows.
3. The existing 54/2/54 corpus and the 27-versus-27 C1 cluster smoke are for
   metric plumbing and expected-fail diagnostics only. They do not have enough
   independent clusters or an adequate claim ceiling for E1.
4. Modal action share and number of selected actions are diagnostics, not
   primary gates. A valid policy may rationally prefer a small action subset.

## 3. Frozen split shape

Before outcomes are generated, seal:

- six fresh source seeds disjoint from all V0.3B and 10-episode seeds;
- seed/anchor-level split: three train, one validation, two test;
- at least 30 train, 10 validation, and 20 test
  `(world anchor, focal user)` **intervention clusters** for each route; these
  are coverage units and are not automatically iid inference units;
- full legal-alternative sibling groups for C1 and C3;
- pre-outcome sealed schedules for C2;
- retention of positive, zero, negative, all-dark, and censored rows;
- three Catfish initialization seeds;
- per-head update ladder `{10, 100, 1000, 10000}`.

Select one common rung by the lowest mean validation
`MAE_model / MAE_action-only`; ties select the smaller rung. Open the test
split once. EE, service outcome, or downstream ablation performance may not
choose a seed, rung, threshold, learning rate, or corpus row.

Failure to reach a minimum cluster count is `INSUFFICIENT_COVERAGE`, not a
route failure. It permits one predeclared supplement on new seeds.

Aggregate complete/censored counts and distinct-world-anchor counts are
authorized coverage metadata before rung selection. Censor reasons, target
values or signs, release outcomes, service outcomes, and test-model metrics
remain sealed until the test split opens once.
Retained C2 censor records live in the sealed generation-details receipt; a
censor is not converted into a synthetic pair target or learner row.

### 3.1 Inference units and claim ceiling

The focal-independent world anchor is the dependence block whenever multiple
focal interventions share one state, frozen-Main joint action, and physical
context. E1 therefore freezes two identities rather than calling every source
row independent:

- `intervention cluster = (source seed, world anchor, focal user)`; all legal
  action siblings stay inside this cluster;
- `inference anchor = (source seed, focal-independent world anchor)`.

For C1 and C3, every bootstrap resamples inference anchors. Opening geometry is
five world anchors times two focal users per seed, yielding minimum
train/validation/test inference-anchor counts `15/5/10` while retaining
intervention-cluster counts `30/10/20`.

For C2, the primary estimand is conditional on the sealed world anchors. Its
forecast RNG and common-random field are focal-keyed, so the primary bootstrap
resamples focal intervention clusters. Coverage still requires at least
`9/3/6` distinct train/validation/test world anchors, at most five focal users
per world anchor, and an anchor-balanced plus leave-one-world-anchor-out
sensitivity. A material point-gate or sign reversal under either sensitivity
is `INSUFFICIENT_COVERAGE`, not route success or failure.
Precisely, the anchor-balanced C2 point estimate must pass the same
preregistered point gate as the primary estimate, and every leave-one-world-
anchor-out estimate must both pass that point gate and retain the primary
effect direction. Any violation is `INSUFFICIENT_COVERAGE`; no exceptions may
be selected after observing test outcomes.

Accordingly, E1 supports instrument validity on the sealed trajectory family;
it does not claim population-wide generalization over arbitrary LEO world
anchors.

## 4. G0 -- provenance

Require all of the following:

- all schemas, digests, checkpoints, and keyed random fields verify;
- every stored reference action equals frozen-Main recomputation;
- no policy-digest mixture, invalid decision mask, non-finite target, or seal
  violation;
- deterministic same-record replay has normalized target error at most
  `1e-6`.

Any G0 failure yields `STOP_INSTRUMENT`.

## 5. G-O -- observability

For normalized target `y = zeta / kappa`, define the exact input key as:

`(route, float32 state bytes, mask, reference action, candidate action, policy digest)`.

A persistent collision contains at least two records with `y >= 0.05` and at
least two records with `y <= -0.05` under one exact key. E1 requires zero
persistent collisions. A collision failure is structural; add the missing
reference-policy context or reject the affected route before generating more
training data.

As a sample-burden diagnostic, train an offline-only masked classifier with
architecture `228-100-50-50-28` to predict the frozen-Main action. It is
discarded after E1 and is not a fourth Q function. Against the train-set
state-independent legal-action prior, require on held-out clusters:

- top-1 accuracy at least `0.80`;
- relative error reduction at least `0.50`;
- route-specific bootstrap under Section 3.1 has a 95% lower bound above
  `0.25`;
- passage in at least two of three probe initializations.

Probe-only failure is a coverage/capacity result, not proof of structural
non-observability.

## 6. G-S -- state-independent action-slot bias

For each held-out state and legal action, center the deployed score within the
state's legal action set:

`X(s,a) = Phi(s,a) - mean_b Phi(s,b)`.

Give every state total weight one and each legal action weight
`1 / |A(s)|`. Fit one action-only effect per slot on validation clusters and
score it once on test clusters:

`G_S = 1 - weighted_SSE_test / weighted_centered_SS_test`.

Require for deployed `Phi`:

- `G_S <= 0.80`;
- at least `0.05` below matched untrained common initialization;
- route-specific bootstrap under Section 3.1 has a 95% upper bound for
  `G_S(trained) - G_S(initialized) < 0`.

Report the three heads separately as diagnostics. G-Gen is the head-level
learning gate.

## 7. G-Gen -- held-out state-conditioned pair learning

Fit on train clusters the action-only difference baseline:

`y_bias(a_M,a_C) = b(a_C) - b(a_M)`.

For each route, evaluate on the unopened test clusters:

`skill_j = 1 - MAE_model,j / MAE_bias,j`.

Require for C1, C2, and C3:

- `skill_j >= 0.20`;
- one-sided route-specific bootstrap 95% lower bound above zero;
- passage in at least two of three Catfish initializations.

The held-out action contrast must lie in a connected component of the training
comparison graph; otherwise the result is `INSUFFICIENT_COVERAGE`.

## 8. G-D -- route pivotality at deployment

On at least 1,000 fixed decisions from the two test seeds, compare the masked
action selected by all three heads with the action selected after removing
each head in turn. Every route must satisfy:

- at least 50 changed decisions;
- changed fraction at least `0.05`;
- route-specific bootstrap 95% lower bound above `0.01`;
- its corresponding G-Gen gate passes.

This prevents a random fixed bias from being counted as useful pivotality.
Action diversity and modal share remain reported diagnostics only.

## 9. Stop/go and bounded repairs

- All G0, G-O, G-S, G-Gen, and G-D pass: `GO_E2`.
- G0 or persistent G-O collision fails: redesign before more data.
- No collision but probe, G-S, G-Gen, or G-D fails: one sealed corpus
  expansion with unchanged thresholds and no EE endpoint.
- Failure after that expansion: redesign.

Failure-mode-specific minimal repairs preserve exactly three trainable Q
functions:

- hidden reference-policy collision: append a read-only one-hot frozen-Main
  action observation and bind its policy digest;
- action-slot bias without collision: first remove or zero-initialize the 28
  output biases; if needed, replace free slot outputs with an action-shared
  candidate scorer;
- coverage-only failure: perform the one bounded fresh-seed expansion.

Do not add a fourth `Q_Main` term. It has incompatible units and violates the
current three-Q deployment formula. Action-centering alone is not a repair:
subtracting one state-only constant cannot change an argmax or remove free
slot biases.

## 10. Execution routing

Metric implementation, tests, and expected-fail diagnostics are non-heavy and
run locally. Fresh source generation and the full E1 ladder are heavy,
non-GUI work and must run on the Ubuntu server after repo/artifact sync,
environment verification, and preregistration sealing. Estimated E1 wall time
is 1--2 hours after the fresh corpus exists; source generation time is reported
separately rather than hidden inside an episode estimate.
