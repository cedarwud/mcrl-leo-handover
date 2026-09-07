# Multi-Catfish MCRL V0.3 E1 Masked Mean/Max Fallback Contract

Date: 2026-09-01  
Scope: one validation-only fallback before the bounded 500-source-epoch
TRAIN-partition screen.

## 1. Trigger and one-shot boundary

This contract is admissible only when the sealed V3 action-shared validation
result has status `EVALUATE_MASKED_MEANMAX_ONCE`. The trigger must retain all
of the following properties:

- C1 route gate passes;
- C2 route gate passes, including the anchor-balanced and every
  leave-one-world-anchor-out estimand;
- C3 route gate fails;
- collision, action-main-effect, and C2 sensitivity gates pass;
- V3 authority, authority seal, result, result seal, and pre-outcome
  authority/seal match their predeclared SHA-256 digests.

This is the single and final fallback. The fallback may produce only
`GO_500EP_SCREEN_ONLY` or `STOP_MASKED_MEANMAX_VALIDATION`. If it does not
pass the complete existing Section 5 gate, execution stops. No second scorer,
DeepSets variant, new seed pool, beta/LR search, test opening, EE evaluation,
or outcome-selected retry is authorized.

The V3 trigger receipt currently supplied for the server run is:

| File | SHA-256 |
|---|---|
| `authority.json` | `b8a27bcae00de2571cf9f01696f014f10040373fd6edde825c3bf15fd6d044fa` |
| `authority-seal.json` | `acf6f6da0afdba03eff4b08610a94c6f3a1406fb448a821974a7c80380f5c4a3` |
| `result.json` | `92923bdb15d52b851b5bd4a8308e7ac0e4a15b2992446400007ecd19c355c09f` |
| `result-seal.json` | `08e68cf7dcbc235f837eadd2f54aa1e443e7ad7b09ce59caccd2e647784c45bf` |

The digest table is an input receipt, not permission to bypass any structural
or code-manifest check.

## 2. Frozen source and learner choices

The fallback consumes exactly the formal V3 source chain:

1. the independently verified 4/3/0 base source;
2. the formal expanded C2 TRAIN datasets;
3. the unchanged C1 and C3 TRAIN datasets;
4. the unchanged three-seed validation partition.

The expansion is appended only to TRAIN/C2. Validation objects and bytes are
not changed. All source, expansion, pre-outcome, and V3 authority/seal
digests are checked before metrics.

The fallback changes only the scorer surface. It copies the primary learner's
state dimension, action dimension, hidden widths, activation, kappa, beta,
loss weights, initialization seeds, and update rungs. In particular:

- learning rate remains `0.001`;
- beta remains `0.1`;
- hidden widths remain `(100, 50, 50)`;
- no `0.01` learning-rate arm is mixed into this run.

The legal mask is the explicit `EEAxisPairBatch.action_masks` / deployment
mask. It is never inferred from the state access feature.

## 3. Masked mean/max scorer

For each action (a), let (x_a\in\mathbb{R}^{8}) be the existing
action-aligned state features and let (g\in\mathbb{R}^{4}) be the existing
temporal global block. With explicit legal mask (m_a\in\{0,1\}), the
fallback forms, featurewise,

\[
\bar{x}_{m}=
\frac{\sum_a m_a x_a}{\max(1,\sum_a m_a)},
\qquad
 x^{\max}_{m,f}=\max_{a:m_a=1}x_{a,f}.
\]

The per-action scorer receives

\[
q_j(s,a)=f_{\theta_j}\!left([x_a,\,g,\,\bar{x}_m,\,x^{\max}_m]\right),
\qquad j\in\{1,2,3\}.
\]

Each (f_{\theta_j}) is one scalar MLP shared over action slots within its
own Q head. Parameters remain independent across C1, C2, and C3. The
deployment rule remains one masked argmax of (Q_1+Q_2+Q_3); the fallback
does not add an agent, coordinator, auction, vote, or post-training override.

## 4. Validation and evidence boundary

The runner reuses the frozen null/generalization definitions and gate:

- route model-to-strongest-null ratios and skills;
- deterministic common-rung selection over the existing rungs;
- observability collision census;
- train-to-validation action-main-effect ceiling;
- C2 anchor-balanced and leave-one-anchor-out sensitivity.

Every initialization/rung checkpoint is saved and reloaded. The reloaded
trainer must reproduce the exact route metrics before the next rung is
accepted. Checkpoint bytes, result bytes, and seals are recorded. The runner
also closes over a SHA-256 manifest of the new runner/scorer and all frozen
source, metric, dataset, and contract dependencies.

The authority and authority seal are written before any validation dataset
bytes are opened or any validation metric is computed. The result is
TRAIN/validation diagnostic evidence only:

```text
test_dataset_paths_opened = []
test_split_opened = false
held_out_ee_evaluated = false
```

Passing this fallback authorizes the next bounded 500-source-epoch screen; it
does not establish EE efficacy, Chapter 5 evidence, or permission for a
1500/3000/9000-epoch run.

## 5. Files

- runner: `.scratch/ee-axis-redesign/run_v03_e1_masked_meanmax_fallback.py`
- scorer: `src/mcrl/algorithms/ee_axis_action_shared_meanmax.py`
- tests: `tests/test_w74_ee_axis_action_shared_meanmax.py`
- primary 500EP consumer remains separately fail-closed until this runner
  returns `GO_500EP_SCREEN_ONLY`.
