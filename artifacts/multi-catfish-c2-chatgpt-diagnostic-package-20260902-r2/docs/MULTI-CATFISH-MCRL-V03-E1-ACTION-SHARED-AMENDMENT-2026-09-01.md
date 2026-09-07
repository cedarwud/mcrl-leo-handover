# Multi-Catfish MCRL V0.3 E1 action-shared amendment

Date: 2026-09-01  
Status: **binding pre-outcome amendment; fresh source generation in progress**  
Claim ceiling: **instrument screen only; no test or EE efficacy**

## 1. Scope

This amendment supersedes only the learner surface, null baseline, validation
split, and bounded-pilot authorization rules in the 2026-08-31 E1 contract.
It does not change the canonical ratio-of-sums EE, the physical C1/C2/C3
counterfactuals, `z_1 + z_2 + z_3`, source selection, common-random physics,
three independent heads, or the deployment sum.

The old E1 train/validation rows are `DESIGN_ONLY` because they were used to
diagnose and select the architecture. The old two-seed test files remain
sealed and unopened.

## 2. Frozen learner

For route `j` and legal action `a`, use

`Q_j(s,a) = f_{theta_j}(x_a, g)`.

- `x_a`: eight action-aligned features from the 228-dimensional causal state;
- `g`: four temporal global features;
- scalar scorer: `12 -> 100 -> 50 -> 50 -> 1`, tanh;
- three independent parameter sets `theta_1`, `theta_2`, and `theta_3`;
- learning rate `0.001`, `beta = 0.1`, and the existing shared `kappa`;
- pair target, route-diagonal update, and deployment sum unchanged.

The same scorer weights apply to every action slot within one head. A
consistent permutation of all eight action-aligned blocks must permute the Q
surface identically. This property is a tested structural requirement.

No beta, learning-rate, hidden-width, DeepSets, or extra-head search is
permitted on the fresh validation outcomes.

## 3. Fresh design split

Before reading outcomes, seal seven new source seeds:

- four train seeds;
- three validation seeds;
- no new test outcomes.

Per seed retain the existing five opening anchors times two focal users and at
least ten complete C2 intervention clusters across at least three world
anchors. Therefore minimum aggregate coverage is:

| Route | Train intervention clusters | Validation intervention clusters | Train world anchors | Validation world anchors |
|:---:|---:|---:|---:|---:|
| C1 | 40 | 30 | 20 | 15 |
| C2 | 40 | 30 | 12 | 9 |
| C3 | 40 | 30 | 20 | 15 |

All siblings, negative/zero/positive targets, and censors are retained. C2
fresh validation must cover both `horizon` and `support_expired` on at least
three distinct world anchors each. Failure is `INSUFFICIENT_COVERAGE`, not an
outcome-selected row replacement.

## 4. Strong state-independent baseline

For each route, fit or declare on training data only:

1. action-only pair differences;
2. the parameter-free zero predictor;
3. a constant equal to the training-target median.

On validation, the null MAE is the lowest held-out MAE among this predeclared
family. Define

`skill_j = 1 - MAE_model,j / MAE_null,j`.

The old action-only denominator remains reportable but cannot authorize the
learner when it is weaker than zero or the train-median predictor.

## 5. Common-rung selection and gates

Evaluate the sealed rungs `{3, 10, 30, 100, 300}` for three initialization
seeds. Select one common rung by the lowest mean `MAE_model / MAE_null` across
all routes and initializations; ties select the smaller rung.

The local action-shared learner obtains `GO_500EP_SCREEN_ONLY` when all of the
following hold on the one fresh validation split:

- provenance, masks, digests, finiteness, and train/validation isolation pass;
- no persistent conflicting exact-input collision is observed;
- absolute action-main-effect fraction is at most `0.80` for the deployed sum;
- every route has mean `skill_j > 0` at the common rung;
- every route has positive skill in at least two of three initializations;
- for C2, recompute the strongest predeclared null separately under the
  anchor-balanced estimand and under every leave-one-world-anchor-out
  estimand; each estimand must have mean skill greater than zero and positive
  skill in at least two of three initializations. A failure is a validation
  stop, not permission to select another null, anchor, or seed after seeing
  the outcome.

Bootstrap intervals and the earlier `skill >= 0.20` threshold remain reported
diagnostics, but they are not required to authorize one bounded 500-episode
screen. Requiring a 20% prediction gain before an exploratory matched EE run
would conflate effect magnitude with the narrower question of whether the
instrument resolves state-conditioned action differences.

This authorization is deliberately narrower than `GO_E2`: it permits one
matched 500-source-training-epoch route-ablation screen, with immutable
learner checkpoints and fresh matched-EE evaluation every 100 source-training
epochs, and no efficacy claim. Here one source-training epoch is one complete
`C1 -> C2 -> C3` batch-update cycle; it is not one simulator episode. Formal
test opening, 1500/3000/9000-epoch promotion, equal-budget neutral-source
ablation, and paper efficacy claims require a separate post-500 decision. The
user must be notified before any 9000-epoch run.

## 6. Single bounded fallback

If local action-shared passes C1 and C2 but fails C3, evaluate exactly one
predeclared masked mean/max context scorer on the same frozen source and rung
set. It must pass the complete Section 5 gate for all routes. Otherwise stop;
do not try DeepSets, additional context families, outcome-selected seeds, or
the test split.

## 7. Current evidence boundary

The design-only beta screen ran on train/old-validation data only. At rung 30,
`beta = 0.1` produced stronger-null skills about `0.271`, `0.100`, and `0.025`
for C1, C2, and C3. Every route was positive in every initialization. This
supports the bounded repair but does not satisfy the fresh gate, validate EE,
or prove that any Catfish improves deployment performance.
