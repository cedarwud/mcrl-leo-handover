**`raw_dup` (`[raw || raw]`, Q1 30 / Q2 44, FULL arm, 16 seeds at epoch 500) has pooled deployed-`Q1+Q2` user-row mean |off-diagonal Pearson| `0.4819`, `+0.2084` above the `0.2735` independence floor, and penultimate effective rank `0.621` (C1) / `0.470` (C2) of hidden width. That is statistically the non-z run (`0.4818`, `+0.2082`, `0.636` / `0.454`), while z beats both (`0.3604`, `+0.0869`, `0.815` / `0.903`), so the result falls in reading-table row 1: the z view's gain on these axes is cross-user normalisation, not capacity.**

# RAWDUP — the width-matched control for the z view — 2026-09-10

Design-phase representation diagnostic. **I computed no EE and read no loss value.** No evaluation-only claim date, evaluation shard or evaluation split was opened. Every row read is a `TRAIN` row of `V025_PROBE/world/1`. No sealed artefact was modified. Nothing was written outside `/home/sat/mcrl-v025-rawdup-ws`.

## Verdict

| question | answer |
|---|---|
| Which row of the fixed reading table? | **Row 1: `raw_dup` ≈ non-z, and z is better than both. The gain is cross-user normalisation.** |
| Does doubling input width and first-layer parameters, with no new information, move either axis? | **No.** Paired over the same 352 seed × anchor cells, `raw_dup − non-z` = `+0.00015` on pooled correlation (174/352 cells positive, 9/16 seeds positive). It is `−0.0153` on C1 rank fraction and `+0.0156` on C2 rank fraction. All three are indistinguishable from zero against a z effect of `−0.121` / `+0.179` / `+0.449`. |
| Is z better than `raw_dup` on a paired basis? | **Yes, on every seed.** `raw_dup − z` = `+0.1215` correlation (16/16 seeds, 341/352 cells) and `−0.433` C2 rank fraction (0/352 cells where `raw_dup` is higher). |
| Does this match the sibling's precedent? | Yes. The sibling's `width448` duplicate-raw control did not repair its pathology, and `raw_dup` does not repair anything here either. The difference is that this project's z view *does* repair something, and the control shows width is not the reason. |

## 1. What was built, and how it relates to the z view

**The view.** Each serialized row is `concatenate([raw, raw])`, and the second block is a value-for-value copy of the first. Q1 goes `15 -> 30`, Q2 `22 -> 44`, the same widths as the z view, so the first-layer parameter count is identical. Checkpoint input widths were read from the weights of both runs: C1 30, C2 44, C3 296 with member width 66, identical in `raw_dup` and z.

**The machinery is the z view's own code.** `/home/sat/mcrl-v025-design-ws/build_zscore_corpus.py` (SHA-256 `cd01b135…4f9f`) was imported unmodified and its `main()` was executed. The parent corpus is the same `q1v2` BUILD_NOT_CLAIM corpus the z view used. Only three module bindings were replaced, and the full unified diff is in [`MACHINERY-DELTA.diff`](/home/sat/mcrl-v025-rawdup-ws/MACHINERY-DELTA.diff):

- `zscore_rows -> rawdup_rows`: the z arithmetic (mean, sigma, divide) is replaced by `concatenate((raw, raw))` plus an equality assertion. Grouping, the duplicate-user check, the lineage hashing and the row rewrite are unchanged.
- `install_reader_adapter`: the second-block feature names change from `z__*` to `dup__*`, and units and scales are inherited from the source feature instead of "population standard deviation". Both digests are pinned in the launcher.
- `python_processes`: this is a resource-guard scope fix, not a view change. The original counts every python process on the shared box and would have aborted on other sessions' interpreters. The replacement counts only this job's own session.

The other 14 functions, `main()` included, have source identical to a pristine import (verified). The schema module [`rawdup_view.py`](/home/sat/mcrl-v025-rawdup-ws/rawdup_view.py) is an attribute-for-attribute twin of `zscore_view.py`.

*Disclosure:* the first `MACHINERY-DELTA.diff` written at build time captured only the `python_processes` hunk, because two of the rebinds happened before the diff was taken. The build itself was unaffected. The diff was then regenerated against a pristine import, and the file now holds all three hunks.

**Build verification (verified by running code):**

- The production reader failed closed on the unregistered schema (`StageCContractError`). It passed with the adapter registered (`PASS_WITH_IN_PROCESS_REGISTERED_SUCCESSOR`). The sealed runner and parent receipt were byte-identical before and after.
- An independent read-back covered all 22 source shards and all 21,532 rows. Every row's second block equals its first as hex strings.
- **The input adds zero rank.** The Q1 matrix has rank 14 at 30 columns, equal to its 15-column first block. Q2 has rank 20 at 44 columns, equal to its 22-column first block. The z corpus census reports ranks 24 and 36. The census correlation between each raw column and its second-block column is exactly `1.0`.
- Build peak RSS was 894,080 KiB (`/usr/bin/time -v`), wall time 36 s.

**Training.** The job used the unmodified runner `/home/sat/mcrl-v025-retrain-ws/scripts/run_stagec_training.py`, whose `runner_sha256` matches the z run. The launcher [`launch_rawdup_training.py`](/home/sat/mcrl-v025-rawdup-ws/launch_rawdup_training.py) is a structural twin of `launch_zscore_training.py`. Arguments were `--epochs 500 --checkpoint-cadence 100 --seeds 16`. The runner has no learning-rate schedule (constant Adam), so there was no step decay. The job compared the launch receipt with the z run's and found every field below identical:

- `epochs`
- `checkpoint_cadence`
- the 16-entry `seed_list`
- `head_literals` and `head_literals_sha256` (`201f6243…ebf0`)
- `runner_sha256`
- `arm_inventory`
- `source_map`
- the 22-anchor `anchor_list`
- source and coalition row counts (21,532 / 4,552)

The fixture gate returned PASS. The run produced 80 checkpoints: 16 seeds × epochs 100 to 500. Training took 9,002.8 s, and the runner's peak RSS was 847,757,312 bytes. The runner trains all five arms in one checkpoint and has no arm filter. This report reads **only `FULL`**, the same arm the prior report read.

- Output: `/home/sat/mcrl-v025-rawdup-ws/artifacts/firstrun-v2d-500ep-20260910T1900Z`
- Launch receipt file SHA-256 `e219f0d78b9c0d09c292217252f5482a30b844d4db4817c05a966d11a01818b4`
- Corpus digest `a3ae7fcd49124d1a591a849f1eaaf1dceceb52ff3d2c6c623d35ba1f0fcbb206`
- Feature-schema digest `592795cc…8205`
- Q1 / Q2 schema SHA-256 `22a1b6c4…5afb` / `3d5b074e…481b`

## 2. Method: identical to `Q-ROW-COLLINEARITY-2026-09-10.md`

- **Probe.** The probe is `/home/sat/mcrl-v025-qcollinear-ws/scripts/qcollinear_probe.py`, copied with two changes: the workspace path, and one appended `RUNS` entry for `raw_dup`. The instrument is the sibling module `ref/penalties.py`, SHA-256 `d1ca8dc89ffc71762369b361498e80b91dffe719916ef52556ac77243b486411`, the same bytes the prior report used.
- **Same surface.** Every `(user, action)` row goes through both deployed FULL heads, and the scores are summed. The score matrix has users as rows and local action slots as columns. The primary estimator is the complete `(U × 10)` block, run through `q_row_decorrelation_penalty`. The robustness estimator is pairwise-complete over all 100 users.
- **Same rank measure.** `srank_diagnostic(Phi, delta=0.01)` runs on mean-centered penultimate features, one anchor's full legal-row batch at a time. C1 hidden width is 8, C2 is 50.
- **Same scope.** 22 `TRAIN` development anchors, 16 of 16 seeds, epoch 500, giving 352 cells per run.
- **The comparison runs were re-measured in the same invocation, not transcribed.** Non-z and z both reproduced the prior report cell for cell: maximum |Δ correlation| `0.0` and maximum |Δ srank| `0` across all 352 cells of each, with identical checkpoint SHA-256s. So every comparison below is between numbers produced by one process on one instrument.
- **The floor is the prior report's measured Gaussian floor for a 10-slot row, `0.273525`** (from `MECHANISM-2026-09-10.json`, not remeasured). A fresh permutation null on `raw_dup`'s real matrices reproduces it (§4).

## 3. Verified by running code: the collinearity axis

Estimand: the equal-weighted mean over 352 seed × anchor cells of the within-cell mean |off-diagonal Pearson| between user rows. Within a cell, the numerator is the sum of |ρ| over `U(U−1)/2` user pairs, with `U ∈ [47, 95]` complete-block users. Brackets give the minimum and maximum cell value. Information class: frozen-checkpoint replay on frozen development anchors. Reference: the `0.2735` floor, and the same-instrument non-z and z runs.

| run (FULL, epoch 500, 16 seeds) | `Q1+Q2` deployed | excess over floor | `Q1` alone | `Q2` alone |
|---|---:|---:|---:|---:|
| v2 non-z (`firstrun-v2-500ep-20260910T1425Z`) | 0.481769 [0.296, 0.770] | +0.208244 | 0.591860 | 0.427892 |
| **raw_dup (`firstrun-v2d-500ep-20260910T1900Z`)** | **0.481920** [0.290, 0.791] | **+0.208395** | **0.597571** | **0.425656** |
| v2z (`firstrun-v2z-500ep-20260910T1512Z`) | 0.360429 [0.267, 0.545] | +0.086904 | 0.334835 | 0.359434 |

Per-head excess over the same floor for `raw_dup`: Q1 `+0.324046`, Q2 `+0.152131`. Non-z: `+0.318335` and `+0.154367`. z: `+0.061311` and `+0.085910`.

- **Signed mean off-diagonal Pearson, `Q1+Q2`.** `raw_dup` `0.424787`, non-z `0.425050`, z `0.256588`.
- **All-100-user pairwise-complete estimator, `Q1+Q2`.** `raw_dup` `0.436998`, non-z `0.436671`, z `0.348642`. No pair was dropped in any cell.
- **Tail counts over 352 cells, `Q1+Q2`.**

  | run | `> 0.7` | `> 0.9` | `< 0.30` | median |
  |---|---:|---:|---:|---:|
  | non-z | 21 | 0 | 3 | 0.473273 |
  | raw_dup | 30 | 0 | 2 | 0.466659 |
  | z | 0 | 0 | 136 | 0.363074 |

- **Per-seed pooled means for `raw_dup`** span `0.4609`–`0.5026`, overlapping non-z's `0.4686`–`0.5075` and entirely above z's `0.3484`–`0.3671`. No `nan` cell occurred in any run.
- **Which head carries it.** Under `raw_dup`, C1 still dominates (Q1 `0.598` vs Q2 `0.426`), the same pattern as non-z. Under z, the two heads converge near the floor. Width does not change which head is collinear; the z transform does.

## 4. The floor at this width, re-checked on `raw_dup`

Permutation null at representative seed `6407676579069309528`, epoch 500, all 22 anchors, 64 within-row shuffles per anchor. The script is the prior `null_floor.py` with workspace paths and a run filter changed.

- `raw_dup` checkpoint SHA-256 `3778383032a7dc0e…`
- z checkpoint SHA-256 `77d2661bbb5efd8e…`

| run | observed | permutation null | excess [min, max over anchors] |
|---|---:|---:|---:|
| raw_dup | 0.484647 | 0.273331 | **+0.211316** [+0.0351, +0.4571] |
| v2z (re-run) | 0.365805 | 0.273179 | +0.092627 [+0.0042, +0.2517] |
| v2 non-z (prior report, transcribed) | 0.473490 | 0.273526 | +0.199964 |

The observed v2z value reproduces the prior report's `0.365805` exactly. Its null differs in the fourth decimal (`0.273179` vs `0.273218`) only because the RNG stream is consumed in a different run order.

The action-row width is unchanged by the view: complete-block shapes are `(47–95) × 10` in every run, because the view widens the *input*, not the action row. **The floor is therefore `0.2735` for all three runs, so raw values compare directly.** The excess-over-floor column is the honest comparison, and it shows `raw_dup` 2.4× further above the floor than z.

An i.i.d. Gaussian `Phi` at `raw_dup`'s exact shapes gives srank `8/8` and `50/50` at all 22 anchors.

## 5. Verified by running code: the rank axis

Estimand: the equal-weighted mean over 352 cells of `srank_diagnostic(delta=0.01)` on mean-centered `Phi`, divided by hidden width. Numerator within a cell: the count of leading singular values reaching 99% of the singular-value sum.

| run | C1 srank / 8 | fraction | C2 srank / 50 | fraction |
|---|---:|---:|---:|---:|
| v2 non-z | 5.090909 [2, 7] | 0.636364 | 22.718750 [9, 35] | 0.454375 |
| **raw_dup** | **4.968750 [2, 7]** | **0.621094** | **23.500000 [9, 35]** | **0.470000** |
| v2z | 6.522727 [3, 8] | 0.815341 | 45.170455 [34, 48] | 0.903409 |

The raw Kumar penalty `σmax² − σmin²` on un-centered `Phi`, `raw_dup`: C1 `6320.69`, C2 `19112.27`. As in the prior report, it is unnormalised and does not track the diagnostic, so it is not used as rank evidence.

**The step-3 and step-7 C2 collapse survives the width control.** At the four group-departure anchors, C2 srank is:

| anchor | non-z | raw_dup | z |
|---|---:|---:|---:|
| `3\|nearest-eligible` | 12.88 | 12.69 | 37.56 |
| `3\|random-masked` | 11.25 | 11.12 | 37.12 |
| `3\|stay-if-possible` | 11.69 | 11.38 | 36.94 |
| `7\|nearest-eligible` | 11.12 | 10.94 | 37.44 |

Only the z view lifts them.

## 6. Paired comparisons (same seed, same anchor, same instrument)

Each difference is taken within a cell, i.e. the same learner seed and the same development anchor, then averaged over 352 cells. "Seeds > 0" counts the 16 per-seed mean differences.

| contrast | pooled `Q1+Q2` corr | C1 rank frac | C2 rank frac |
|---|---|---|---|
| raw_dup − non-z | **+0.000151** (174/352 cells > 0; seeds > 0: 9/16; seed range −0.023 to +0.028) | −0.015270 (9/16) | +0.015625 (11/16; seed range −0.018 to +0.080) |
| raw_dup − z | **+0.121491** (341/352; **16/16**) | −0.194247 (1/16) | **−0.433409** (0/352; **0/16**) |
| z − non-z (re-measured) | −0.121340 (20/352; 0/16) | +0.178977 (14/16) | +0.449034 (352/352; 16/16) |

**Mapping to the reading table.** `raw_dup` sits within `0.0002` of non-z on correlation and within `0.016` on both rank fractions. As fractions of the corresponding z effect, the gaps are 0.1% (correlation), 8.5% (C1) and 3.5% (C2), and none has a consistent sign across seeds. Z is better than `raw_dup` on every seed for correlation and C2 rank. This is row 1. It is not row 2 (`raw_dup` ≈ z), not row 3 (`raw_dup` better than z), and not row 4 (all three equal).

Per head: `raw_dup − non-z` is `+0.0057` on Q1 alone and `−0.0022` on Q2 alone. `raw_dup − z` is `+0.2627` on Q1 (352/352 cells) and `+0.0662` on Q2.

The C1 rank per-seed range is wide (`−0.34` to `+0.22` for `raw_dup − non-z`). C1 has only 8 hidden units, so one unit is `0.125` of width and seed noise is coarse. The pooled mean is still near zero, and z's `+0.179` is a different size.

## 7. Per-anchor structure (mean over 16 seeds)

| anchor | non-z `Q1+Q2` | **raw_dup** | z | C1 srank n / **d** / z | C2 srank n / **d** / z |
|---|---:|---:|---:|---|---|
| `0\|nearest-eligible` | 0.6002 | **0.6094** | 0.4065 | 5.12 / **4.94** / 6.56 | 23.62 / **25.62** / 46.12 |
| `0\|random-masked` | 0.3792 | **0.4027** | 0.3727 | 5.00 / **4.88** / 6.44 | 24.06 / **25.88** / 46.44 |
| `0\|stay-if-possible` | 0.4936 | **0.4930** | 0.4520 | 5.12 / **4.94** / 6.56 | 29.50 / **30.25** / 48.00 |
| `1\|nearest-eligible` | 0.7210 | **0.7132** | 0.4464 | 5.12 / **5.06** / 6.62 | 27.69 / **27.19** / 47.94 |
| `1\|random-masked` | 0.4376 | **0.4525** | 0.3579 | 5.25 / **5.06** / 6.69 | 19.38 / **21.25** / 47.12 |
| `1\|stay-if-possible` | 0.3703 | **0.3722** | 0.3723 | 5.12 / **5.12** / 6.69 | 25.75 / **25.75** / 48.00 |
| `2\|nearest-eligible` | 0.5048 | **0.4480** | 0.2889 | 5.25 / **5.06** / 6.88 | 23.69 / **23.69** / 46.75 |
| `2\|random-masked` | 0.3925 | **0.3846** | 0.3059 | 5.25 / **5.12** / 6.75 | 22.88 / **24.62** / 46.69 |
| `2\|stay-if-possible` | 0.3198 | **0.3197** | 0.2903 | 5.25 / **5.12** / 6.69 | 23.44 / **23.69** / 47.00 |
| `3\|nearest-eligible` | 0.3383 | **0.3387** | 0.2844 | 5.25 / **5.06** / 6.62 | 12.88 / **12.69** / 37.56 |
| `3\|random-masked` | 0.6588 | **0.6906** | 0.2891 | 5.06 / **4.81** / 6.56 | 11.25 / **11.12** / 37.12 |
| `3\|stay-if-possible` | 0.3383 | **0.3387** | 0.2801 | 5.19 / **4.94** / 6.69 | 11.69 / **11.38** / 36.94 |
| `4\|nearest-eligible` | 0.6933 | **0.6950** | 0.4888 | 4.44 / **4.75** / 5.94 | 26.19 / **27.56** / 45.69 |
| `4\|random-masked` | 0.5516 | **0.5486** | 0.3818 | 4.56 / **4.88** / 6.25 | 25.81 / **27.12** / 45.62 |
| `4\|stay-if-possible` | 0.6002 | **0.6005** | 0.4816 | 4.44 / **4.75** / 5.94 | 32.56 / **33.00** / 47.88 |
| `5\|nearest-eligible` | 0.6705 | **0.6742** | 0.5164 | 5.25 / **4.94** / 6.69 | 24.38 / **25.00** / 47.44 |
| `5\|random-masked` | 0.5214 | **0.5360** | 0.3819 | 5.12 / **4.88** / 6.38 | 25.56 / **27.19** / 46.81 |
| `5\|stay-if-possible` | 0.5328 | **0.5326** | 0.3948 | 5.06 / **4.88** / 6.12 | 27.50 / **28.56** / 47.94 |
| `6\|nearest-eligible` | 0.4585 | **0.4569** | 0.2970 | 5.19 / **4.94** / 6.56 | 20.25 / **21.31** / 46.12 |
| `6\|random-masked` | 0.3911 | **0.3695** | 0.2893 | 5.44 / **5.06** / 6.56 | 27.38 / **29.06** / 46.31 |
| `6\|stay-if-possible` | 0.3176 | **0.3200** | 0.2776 | 5.19 / **5.06** / 6.69 | 23.25 / **24.12** / 46.81 |
| `7\|nearest-eligible` | 0.3075 | **0.3058** | 0.2736 | 5.31 / **5.06** / 6.62 | 11.12 / **10.94** / 37.44 |

`raw_dup` tracks non-z anchor by anchor on both axes. The largest per-anchor correlation gap is `0.057`, at `2|nearest-eligible`. Z is lower than both at 21 of 22 anchors. The exception is `1|stay-if-possible`, where all three coincide at `0.37`.

## 8. What this control settles, and what it does not

**Settles.** It settles the confound the brief named: doubled input width and doubled first-layer parameter count. `raw_dup` has both and moves neither axis. The z view's advantage is therefore not bought by the extra parameters. Row 1 holds.

**Derived, and it sharpens what "capacity" means here.** A verbatim duplicate spans the same input subspace as the raw block (rank 14 / 20 either way). A first layer `W_a·x + W_b·x` computes the same function class as a single `(W_a + W_b)·x`. So `raw_dup` adds parameters but no function-class capacity, and at initialisation it mainly changes the effective first-layer scale and the Adam dynamics. That is exactly why it is the correct control for "is it the parameters?". It also means the control cannot separate two readings of the z block. The z block brings 10 (Q1) and 16 (Q2) new input directions (ranks 24 / 36 vs 14 / 20), and those directions are the cross-user standardised information itself. In this view "cross-user normalisation" and "new cross-user input directions" are one object, and the table's row 1 names it correctly. Separating standardisation *per se* from the added cross-user directions would need a different arm, for example a z-only view at the original width or a random-projection block of matched rank. **That arm was not run and is not claimed.**

**Does not settle.**

- Anything about EE. No EE was computed.
- Converged behaviour. See §10.
- Whether the representation gain matters to deployed decisions.

## 9. Route marginals: no matching panel exists, so this stops at the representation axes

- The only five-arm route-marginal scorer on the box is `/home/sat/mcrl-v025-selector-ws/scripts/score_stagec_checkpoints.py`. It needs a per-view scoring panel.
- Panels exist for Q1-v1 and Q1-v2 (`mcrl-v025-panelfix-ws`) and for the z view (`mcrl-v025-panelz-ws/artifacts/panel-q1v2z.json`). **No `raw_dup` panel exists, so no route marginal was computed for `raw_dup`.** Building one would mean adapting the PANELZ builder to a new view, which is the improvisation the brief rules out.
- **The silent-failure hazard is real for this exact pair (verified).** `raw_dup` checkpoints have input widths C1 30, C2 44, C3 296, member width 66, identical to the z checkpoints the z panel was accepted against. The scorer takes widths from `len(weights[0])` and checks panel states only against those widths. Pointed at `panel-q1v2z.json`, it would therefore accept `raw_dup` checkpoints without error. It would then feed z-transformed states to heads trained on duplicated raw states, producing numbers that look well-formed but are meaningless. **This was not run**, and nobody should run it.
- A FULL-arm-only development evaluator also exists: `evaluate_a0_panel.py` over the frozen PANELCEIL panel. It builds states from the corpus passed to it, so it has no semantics hazard, but it produces pooled EE and concentration, not route marginals. It was not run, following the brief's instruction to stop at the representation axes. It is available as a cheap follow-up (the z run's evaluate phase took about 4 minutes).

## 10. Standing caveats on every number

- **500 unconverged constant-rate updates on surrogate labels, in every run.** Per the brief, not re-verified by me, C1's label argmax disagrees with exact on 51.68% of rows, C2 on 55.27% and C3 on 81.82%. The three runs share corpus rows, seeds, literals and budget, so **the paired comparison is valid. No statement here is about converged behaviour or exact-label behaviour.**
- **Every number is FULL arm, epoch 500, over the 16 seeds listed in §12.** The §4 permutation null uses seed `6407676579069309528` alone.

## 11. Evidence classification

**Verified by running code, by me, on `sat`:**

- the `raw_dup` corpus build, its read-back and its rank census
- the reader fail-closed / pass behaviour
- the equality of the training launch receipt with the z run's
- training completion (80 checkpoints, 16 × epoch 500, exit 0)
- every value in §3–§7, including the same-process re-measurement of non-z and z and its cell-for-cell agreement with the prior report
- the permutation null and Gaussian srank references for `raw_dup`
- the checkpoint-width identity behind §9's hazard

**Derived:**

- excess over floor, as a subtraction of two measured quantities
- the paired differences
- the gap-as-fraction-of-z-effect ratios (0.1% / 8.5% / 3.5%)
- the argument in §8 that duplicated inputs add parameters but no function class, which follows from linear algebra on the first layer

**Transcribed, not re-measured:**

- the `0.273525` 10-slot Gaussian floor (`MECHANISM-2026-09-10.json`)
- non-z's representative-seed permutation null `0.273526` / excess `+0.199964` (`NULL-FLOOR-2026-09-10.json`)
- the z corpus ranks 24 / 36 (the z build receipt)
- the sibling's `width448` outcome (quoted from the prior report)
- the surrogate-label disagreement rates (from the brief)

**Inferred, not established:**

- that the z block's gain is about the *standardisation* rather than about the added cross-user directions it carries (§8 explains why this control cannot separate them)
- any bearing on EE or on the deployed a0 decisions

## 12. Provenance and resources

| item | value |
|---|---|
| workspace | `/home/sat/mcrl-v025-rawdup-ws` (git) |
| corpus | `artifacts/v025-stagec-c3-coalition-q1v2d-20260910-BUILD_NOT_CLAIM/corpus`, digest `a3ae7fcd…b206` |
| build receipt | `artifacts/…/BUILD_NOT_CLAIM-rawdup-view-verification.json`; read-back `rawdup-readback.json` |
| training run | `artifacts/firstrun-v2d-500ep-20260910T1900Z` |
| machine receipts | `Q-ROW-COLLINEARITY-RAWDUP-2026-09-10.json` (all 1,056 cells: `raw_dup`, non-z, z) and `NULL-FLOOR-RAWDUP-2026-09-10.json` |
| scripts | `build_rawdup_corpus.py`, `rawdup_view.py`, `launch_rawdup_training.py`, `scripts/qcollinear_probe.py`, `scripts/null_floor.py`, `ref/penalties.py` (`d1ca8dc8…6411`) |
| delta vs z machinery | `MACHINERY-DELTA.diff` |
| logs | `build.log`, `train.log`, `probe.log`, `nullfloor.log` |

Seeds, all at epoch 500: `389903013832883586`, `925030429265975792`, `1437152739566466432`, `2106858948530091040`, `2306713132836500212`, `2539879246662512149`, `2914121027624601215`, `2947922203589416513`, `3155344545377116990`, `5166716249291843642`, `5683607794651051129`, `6114226365011333154`, `6407676579069309528`, `7234013715671416945`, `7291913070596938501`, `9087876568043732533`. Per-cell checkpoint SHA-256s are in the machine receipt.

Resources:

- **Interpreter.** `/home/sat/mcrl-leo-handover/.venv/bin/python` only; that checkout and its `.venv` were untouched.
- **Priority and threads.** `nice -n 16`. All six BLAS/OMP thread variables were set to `1`.
- **Concurrency.** At most 2 python processes of this job at once (probe + null floor; cap 3).
- **Peak RSS** (`/usr/bin/time -v`):

  | step | peak RSS (KiB) | wall |
  |---|---:|---:|
  | build | 894,080 | 0:36 |
  | training | 827,888 | 2:30:52 |
  | probe | 675,928 | 1:45 |
  | null floor | 679,488 | 0:04.5 |

  All are under 5 GB.
- **Timeline.** Training finished around 21:27Z. The controlling session was interrupted around 19:00Z, and the measurement ran on resume around 23:45Z; no finished step was redone.
