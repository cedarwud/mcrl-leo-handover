# Multi-Catfish MCRL V0.2 — 1500/3000EP intermediate trend plan

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: plan
- Origin Date: 2026-08-28
- Verification Status: UNVERIFIED
- Version Label: `multi_catfish_v02_intermediate_trend_v1`

## Experiment overview

- **Objective:** determine whether the full three-Catfish carrier and each
  Catfish's marginal contribution show a credible Main-only EE direction before
  any 9000EP experiment.
- **Hypotheses:** `F111 > B000` and, for `j=1,2,3`,
  `F111 > Full-minus-Cj` in held-out Main-only system EE.
- **Type:** PyTorch training plus fixed TEST-partition simulation sweep.
- **Evidence ceiling:** one training seed, intermediate trend only; not Chapter
  5, not formal efficacy, not statistical generalization, and not 9000EP
  authorization.

## Frozen design

### Training factors

| Factor | Frozen values |
|---|---|
| Arms | `B000`, `F111`, `A011` (Full-C1), `A101` (Full-C2), `A110` (Full-C3) |
| Stage 1 episodes | `1500` |
| Stage 1 learning rates | `0.001`, `0.01` |
| Stage 2 episodes | `3000`, fresh from initialization rather than resumed from 1500 |
| Stage 2 learning rate | selected by the frozen rule below |
| Users during training | `100` |
| Training seed | `2026082901` |
| Environment seed | `2026082902` |
| Mobility seed | `2026082903` |
| Epsilon schedule | `1.0 -> 0.01`, decay over `2000` episodes |
| Target synchronization | every `50` episodes |
| Trend checkpoint cadence | every `100` episodes for every arm |
| Specialist bundle replay | FIFO capacity `2000` complete bundles per specialist |
| Donor beta | `0.25`, no borrowing |
| C1 ACRM eta | `1.0` |
| TLE file-set SHA-256 | `427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9` |

The learning rate applies to the matched Main and specialist learners in a
given matrix. Arms at different learning rates are separate matrices; the
baseline is retrained at each learning rate.

The 1500EP LR screen intentionally retains the canonical 2000EP epsilon decay,
so its final training episode still has nonzero exploration.  The frozen
assumption is that Main-only greedy held-out evaluation can provide an early
LR direction before the fresh 3000EP run reaches the fully annealed regime;
this is a screen limitation, not evidence that the regimes are equivalent.

### Evaluation

- Policy: final checkpoint, Main only, masked greedy; all Catfish doses are
  zero and no specialist chooses deployment actions.
- Partition: canonical held-out `TEST`.
- User sweep: `60, 80, 100, 120, 140`.
- Evaluation seeds: `2026082904` through `2026082908`.
- Primary endpoint: system EE in bits/J, computed as ratio of total useful bits
  to total system energy within each training-seed/load cell.
- Safeguards: served fraction, zero-power intervals, zero-service intervals,
  finite losses/parameters, complete episode count, and exact authority hashes.
- Secondary diagnostics: canonical `r1/r2/r3` sums, realized C2/C3 trigger
  exposure, routed dose count, throughput, power, and handover totals. None may
  replace the primary EE endpoint after results are seen.

Every arm retains a loadable Main-only policy snapshot at episodes
`100, 200, ...` through the declared endpoint.  A rolling latest full
training/carrier state is replaced at the same cadence for recovery without
duplicating the large replay state at every checkpoint.  Each periodic Main
snapshot is evaluated Main-only at `100` users with the same five fixed TEST
seeds to produce an EE learning curve.  The final snapshot alone receives the
full `60/80/100/120/140` user sweep used for the primary contrasts.
The 100EP curve is diagnostic only: it cannot select an episode count,
checkpoint, arm, or replacement endpoint, and it cannot replace the declared
final-episode checkpoint in any contrast.

The five evaluation seeds estimate environment variation for one trained
policy. They are not five independent training replications and must not be
used to claim training stability or conventional inferential significance.

## Stage 0 — server smoke

Before 1500EP, run the same five arms for 10EP under the bounded development
route through `run_intermediate_trend_matrix.py --smoke` and complete the
identical TEST EE sweep.  The launcher still validates the selected 1500EP
authority and canonical inputs first, but labels all 10EP output with the
separate engineering-smoke claim ceiling. This smoke may catch an arm,
output, or evaluator failure but cannot select a learning rate or establish an
EE trend. Any authority, isolation, checkpoint-load, or sweep failure blocks
Stage 1.

## Stage 1 — 1500EP learning-rate screen

Run all five arms at both learning rates. This yields ten matched training
runs and 250 held-out evaluation episodes.

For each learning rate and load `n`, let `E_X(n)` be the ratio-of-sums EE for
arm `X`, pooled over the five fixed evaluation seeds. Define percentage
contrasts:

```text
d_full(n) = 100 * [E_F111(n) - E_B000(n)] / E_B000(n)
d_C1(n)   = 100 * [E_F111(n) - E_A011(n)] / E_A011(n)
d_C2(n)   = 100 * [E_F111(n) - E_A101(n)] / E_A101(n)
d_C3(n)   = 100 * [E_F111(n) - E_A110(n)] / E_A110(n)
```

For each contrast, its screen value is the equal-weight mean across the five
user loads. Evaluation seeds are pooled inside each load before these
contrasts; they are not treated as extra training samples.

### Fail-closed eligibility

A learning rate is ineligible for 3000EP if any arm is incomplete, any
checkpoint/receipt is missing or hash-drifted, a finite-value guard fails, a
zero-power guard fails, or the full arm loses more than `2.0` percentage points
of served fraction against baseline at any load. There is no silent retry and
no post-hoc replacement seed.

### LR selection

For each eligible learning rate, define:

```text
S(lr) = min(mean(d_C1), mean(d_C2), mean(d_C3))
```

Select the eligible learning rate with the larger `S(lr)`, because the stated
goal is three individually EE-helpful Catfish roles rather than only a large
full-arm average. If the two scores differ by at most `0.25` percentage point,
select `0.001` as the lower-variance/lower-step default. If only one learning
rate is eligible, select it. If neither is eligible, stop; do not run 3000EP.

The signs of `d_full`, `d_C1`, `d_C2`, and `d_C3` must all be reported even
when they are unfavorable. This rule selects a learning rate for a longer
trend check; it does not declare a successful mechanism.

## Stage 2 — selected-LR 3000EP ablation

Run a fresh five-arm matrix at the selected learning rate with the same seeds,
schedule, evaluator, and load sweep. A 3000EP result receives the label
`ALL_THREE_DIRECTIONALLY_EE_POSITIVE` only when:

1. mean `d_full`, `d_C1`, `d_C2`, and `d_C3` are all strictly positive;
2. each of the four contrasts is positive at at least four of five user loads;
3. the full arm loses no more than `0.5` percentage point of served fraction
   against baseline at every load; and
4. no finite, identity, zero-power, checkpoint, or authority guard fails.

The four-of-five-load rule is only a correlated load-consistency check on one
trained policy, not four independent successes or an inferential test.

Any other outcome is reported literally: which role is negative, mixed by
load, or inconclusive. A mixed result may motivate a parameter or role-rule
revision, but it cannot be relabelled as EE improvement.

## 9000EP boundary

No result in this plan authorizes 9000EP. Before a long Chapter-5 candidate
run, freeze multiple independent training seeds, a formal comparison and
statistical analysis plan, final role gates, resource budget, and stopping
rules. The user must be explicitly notified before any 9000EP process starts.

## Setup and execution location

This is heavy compute without a GUI and must run on the Ubuntu training server,
not local WSL. Rough estimates per treatment arm are `3–4 h` at 1500EP and
`6–8 h` at 3000EP; actual matrix wall time depends on verified two-way
parallelism, memory growth, checkpoint serialization, and evaluation time.

1. SSH to the Ubuntu server.
2. Sync the repository plus the frozen preregistration, C1 corpus, current
   support/parity receipts, and exact 373-file TLE view.
3. Confirm `/home/sat/mcrl-leo-handover/.venv` and
   `/home/sat/mcrl-runtime/tle-frozen-20260820` reproduce local hashes.
4. Open a Codex worker session in the synced checkout and run preflight/tests.
5. Launch under `tmux` with at most two arms concurrently and no silent retry.

## Expected outputs

| Output | Format | Success criterion |
|---|---|---|
| Per-arm status/log/checkpoint | JSON, text, PT | exact episode count, zero exit, finite guards, hashes present |
| 100EP checkpoint trajectory | PT, JSON, CSV, PNG | every declared episode present/loadable; Main-only fixed-seed EE probe complete |
| Matrix receipt | JSON | five fixed arms and authority reproduced; elapsed/RSS/log hashes recorded |
| Held-out sweep | JSON, CSV | all 5 arms x 5 loads x 5 eval seeds complete |
| EE-vs-users plot | PNG | measured values only; labelled intermediate trend, not Chapter 5 |
| LR decision receipt | JSON/Markdown | frozen contrasts and selection rule applied without override |

## Monitoring

- Monitor process-alive state, per-arm log growth, completed episode count,
  disk use, and maximum RSS.
- Do not kill a healthy slow arm merely for missing an ETA. A hard resource or
  finite-value failure stops new arm launches; already running matched work is
  allowed to finish and is reported.
- Do not auto-retry, change a seed, lower user count, switch TLE data, or alter
  a trigger after observing an outcome.
