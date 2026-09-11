**MODQNZ never wrote a conclusion — its report does not exist, and no agent ever stated one — but its two completed arms do carry genuine pooled EE (a ratio of sums, `run_modqn_z_intervention.py:379`), and they say the cross-user z-score *lowers* MODQN's pooled EE by 3.511% (90,866,329.62 → 87,676,034.45 bit/J) while spreading the allocation (+3.38 active physical beams), which is row 4 of MODQNZ's own predeclared reading rule; and on the frozen MODQN checkpoint collapse is **UNDETERMINED, not absent** — I computed all four G-3 indicators and the two that were missing turn out to have no discriminative power on this decision surface, because an *untrained* network with 92.25% argmax agreement on 2.58 slots scores `q_margin` 0.1145 (79% of the frozen policy's 0.1447) and `q_entropy` 0.9992 (*higher* than the frozen policy's 0.9960).**

# ZCLOSE — MODQNZ retrieval and the G-3 four — 2026-09-11

Two jobs. Read-only plus one cheap diagnostic rollout (74.6 s wall, 0.89 GB peak RSS, 1 python
process, `nice -n 16`, all BLAS/OMP threads 1). No training. No new rollouts of anything that
did not already have a saved checkpoint. `/home/sat/mcrl-leo-handover` and its venv untouched;
the frozen checkpoint hashed `e6b063efea86…` before and after scoring and did not change.

Tags: **[V]** verified by me reading the cited file at the cited line or running the cited code;
**[D]** derived arithmetic over **[V]** numbers; **[I]** inferred, flagged in place.

Every number carries four fields: **reference point / information class / estimand / numerator**.

---

# JOB 1 — MODQNZ

## 1.1 The finding that comes before the numbers: there is no MODQNZ report

**[V]** `/home/sat/mcrl-v025-mqz-ws/MODQN-Z-INTERVENTION-2026-09-10.md` **does not exist.**
The whole workspace is four entries:

```
/home/sat/mcrl-v025-mqz-ws/
  run_modqn_z_intervention.py   21503 bytes
  test_modqn_z_intervention.py   1441 bytes
  artifacts/
  .git/                         (branch main, ZERO commits, everything untracked)
  __pycache__/
```

**[V]** `git -C /home/sat/mcrl-v025-mqz-ws log` → *"fatal: your current branch 'main' does not
have any commits yet"*; `git status --short` shows `run_modqn_z_intervention.py`,
`test_modqn_z_intervention.py`, `artifacts/`, `__pycache__/` all as `??`.

**[V]** The MODQNZ launch prompt did commission the report:
`.scratch/server-sync-20260909/audits/MODQNZ.codex.log:113` — *"Write to
`/home/sat/mcrl-v025-mqz-ws/MODQN-Z-INTERVENTION-2026-09-10.md`, first line one bolded sentence
giving `MODQN_RAW` and `MODQN_Z_INPLACE` pooled EE, the relative change, the change in
`modal_frac` and `active`, and which row of the reading rule the result falls in."*

**[V]** No such sentence was ever written, anywhere I can find. The codex session log
(48,211 lines) contains no conclusion: its highest progress line is `episode 300/9000`, and it
terminates mid-way through a diff of the unit-test file. `grep` for `decisive pair` in that log
returns only the prompt's own line 65 and one progress note at line 36939.

**[D] So the declared closure — `V025-CONTROLLER-DECLARATION-TRAINING-PAUSE-2026-09-11.md:11`,
*"MODQNZ (earlier) — decisive pair done; z line closed"* — rests on no written finding at all.**
The *runs* happened and their receipts are real; the *reading* of them was never recorded. What
follows is therefore my own reading of MODQNZ's artefacts against MODQNZ's own predeclared rule,
not a retrieval of a conclusion someone else reached.

Retrieved to `/home/u24/papers/mcrl-leo-handover/.scratch/zclose/modqnz/` (`.pt` weights excluded
deliberately — 4 files, ~1 MB each, not needed for any claim here and re-readable on the server):

```
run_modqn_z_intervention.py                     test_modqn_z_intervention.py
artifacts/MODQN_RAW/{progress,result}.json      artifacts/MODQN_Z_INPLACE/{progress,result}.json
artifacts/MODQN_Z_CONCAT/progress.json          artifacts/cost-probe-raw-100/{progress,result}.json
artifacts/resume-smoke/{progress,result}.json   artifacts/time-*.txt
```

## 1.2 Did the runs complete? Two of four did

**[V]** From the retrieved `progress.json` / `result.json` files:

| arm | episodes | `result.json` | final checkpoint | status |
|---|---:|---|---|---|
| `MODQN_RAW` | **9000 / 9000** | present | `modqn_raw-final-checkpoint.pt` | **complete** |
| `MODQN_Z_INPLACE` | **9000 / 9000** | present | `modqn_z_inplace-final-checkpoint.pt` | **complete** |
| `MODQN_Z_CONCAT` | **2300 / 9000** | **absent** | **absent** (only `resume-state.pt`) | **abandoned** |
| `MODQN_RAW_DUP` | — | — | — | **never started** (no directory) |

**[V] The 800/9000 in the local log is stale, not the run's endpoint.** The local
`MODQNZ.codex.log` snapshot stops even earlier than the brief said — its last progress line is
`episode 300/9000` — but the server artefacts show both decisive arms subsequently reached
9000/9000 (`MODQN_RAW` 17,620.68 s; `MODQN_Z_INPLACE` 17,705.94 s). **The conclusion below is
supported by two full 9,000-episode runs, not by 800 episodes.**

**[V]** What did *not* complete is the **width-controlled pair**. MODQNZ's own prompt
(`MODQNZ.codex.log:57-67`) declares arm 3 `MODQN_Z_CONCAT` = `[raw ‖ z]` (224 wide, the
sibling's construction) and arm 4 `MODQN_RAW_DUP` = `[raw ‖ raw]` (224 wide, *"the capacity
control for arm 3"*). Arm 3 died at 2300 episodes; arm 4 never ran. So **the width-controlled
form of this test does not exist**, and the reading-rule row that depends on it — *"concat beats
in-place, but not `raw_dup` ⟹ the gain is capacity, not normalisation"* — is unreachable.

**[V]** The prompt does say the in-place arm is the primary one and is *better* than the
width-matched pair for this purpose: arm 2 is *"the primary z arm because it has **no capacity
confound at all** — same parameter count, same width"* (`:52-54`), and *"Arms 1 and 2 are the
decisive pair"* (`:65`). So the surviving pair is the one the design named as decisive. It is
still the case that the sibling-matched construction was not reproduced.

## 1.3 THE CRITICAL CHECK — pooled EE or mean of ratios?

### **Pooled EE. A genuine ratio of sums. [V]**

**[V]** `/home/u24/papers/mcrl-leo-handover/.scratch/zclose/modqnz/run_modqn_z_intervention.py`:

- `:324-325` — per decision step:
  `step_bits = outcome.energy.system_throughput_bps * DECISION_STEP_S` and
  `step_joules = outcome.energy.system_consumed_power_w * DECISION_STEP_S`.
  Both are **system-level** quantities read off `outcome.energy`, not per-user terms.
- `:326-327` — `row_bits += float(step_bits)` / `row_joules += float(step_joules)`
  (accumulated over the 10 steps of a scenario).
- `:340-341` — `pooled_bits += row_bits` / `pooled_joules += row_joules`
  (accumulated over the 10 scenarios).
- **`:379` — `"pooled_ee_bits_per_j": pooled_bits / pooled_joules`.**

**[D]** One division, performed once, at the end, on two independently accumulated totals. There
is **no** `mean` anywhere on the EE path — the only `np.mean` calls in the file are `:262-265`,
which build the learning-curve endpoint summary that the prompt itself forbids as EE evidence
(`MODQNZ.codex.log:88` — *"the learning curve endpoints as convergence diagnostics only —
**never as EE evidence**"*).

**[D] This is the opposite of the sibling's `argmax_EE`.** ZWHY established that the sibling's
`score_argmax_endpoint.py:105,118,120-121` takes a mean over users of `R_u/P_system`, then a mean
over steps, then a mean over episodes — a triple mean of ratios. MODQNZ takes Σbits / Σjoules.
**MODQNZ's closure does rest on EE evidence in this project's declared estimand.** That is the
answer to the critical check, and it comes out the way the closure needs it to.

Two honest qualifications on that, neither of which changes the estimand:

- **[V]** The per-scenario field `ee_bits_per_j` (`:356`, `row_bits / row_joules`) is also a
  ratio of sums within its scenario. The 10 scenario values are reported but are **never averaged
  into the headline** — the headline recomputes from the totals. **[D]** So no mean-of-ratios
  enters even by the back door.
- **[V]** `:381` `served_fraction` and `:384` `modal_frac` *are* ratios of counts over the whole
  panel, i.e. also pooled. They are collapse/service diagnostics, not the EE estimand.

## 1.4 What the two completed arms actually say

**[V]** From `.scratch/zclose/modqnz/artifacts/{MODQN_RAW,MODQN_Z_INPLACE}/result.json`,
`evaluation` block.

**Four fields for every EE number in this table.**
**Reference point:** `MODQN_RAW` — the same runner, same 10 frozen P6 development seeds
(`2026082401`–`2026082410`), same 10 steps × 100 users, same architecture, same
hyperparameters, same training/env/mobility seeds (42 / 1337 / 7); the *only* difference is the
observation transform (`run_modqn_z_intervention.py:139-153`).
**Information class:** greedy (`eps=0.0`, `:304`) rollout of a checkpoint trained from scratch
for 9,000 episodes under the byte-matched 2026-08-25 legacy stack, on the **TRAIN/development**
split (`:372`) — development evidence, not held-out.
**Estimand:** pooled EE, Σbits / Σjoules over the whole 100-decision-step panel.
**Numerator:** Σ (`system_throughput_bps` × `DECISION_STEP_S`) over all 100 decision steps.

| quantity | `MODQN_RAW` | `MODQN_Z_INPLACE` | Δ (Z − RAW) |
|---|---:|---:|---:|
| **pooled EE (bit/J)** | **90,866,329.62** | **87,676,034.45** | **−3,190,295.18** (**−3.511%**) |
| pooled bits | 1.2285089233×10¹⁴ | 1.2582221867×10¹⁴ | +2.9713263348×10¹² |
| pooled joules | 1,351,995.76 | 1,435,081.09 | +83,085.33 (**+6.145%**) |
| served / 10,000 | 9,926 (0.9926) | 9,993 (0.9993) | +67 (+0.0067) |
| `modal_frac` | 0.0367 | 0.0378 | +0.0011 |
| mean active **physical** beams | 72.24 | 75.62 | **+3.38** |
| mean active satellites | 7.74 | 8.51 | +0.77 |
| mean `argmax_distinct` (local slots) | 9.11 | 6.51 | **−2.60** |

**[D]** The mechanism is legible in the two totals: z-in-place **raised throughput** (+2.42%
bits) but **raised power more** (+6.15% joules), and the ratio therefore fell. It served 67 more
users out of 10,000 and lit 3.38 more physical beams to do it.

**[D] Paired per-scenario (the 10 seeds are matched across arms):** Z − RAW is negative in
**7 of 10** scenarios; mean −3,116,131 bit/J, sd 2,858,652 bit/J. Per-scenario deltas
(bit/J): +374,378 / +620,663 / +293,919 / −7,534,835 / −4,344,915 / −3,517,734 / −2,699,652 /
−2,828,264 / −5,366,827 / −6,158,041. **[D]** At n=10 with that sd the paired mean is about
3.4 standard errors from zero, but **[I]** I would not lean on that: these ten are evaluation
scenarios inside **one** training seed per arm, not ten independent replications of the
intervention, so they estimate panel variation and not training-seed variation. **The intervention
itself has n = 1 seed per arm** (`run_modqn_z_intervention.py:56-58`, `TRAIN_SEED = 42`,
`ENV_SEED = 1337`, `MOBILITY_SEED = 7`).

### Which row of MODQNZ's own predeclared reading rule

**[V]** The rule, fixed before any number existed, at `MODQNZ.codex.log:95-103`:

| observed | reading |
|---|---|
| z raises EE **substantially** and spreads | MODQN **was** collapsed, by the documented mechanism |
| z raises EE **without** spreading | z helps for a different reason |
| z changes EE **little or not at all** | **MODQN was not collapsed.** The hypothesis closes. |
| **z lowers EE** | **consistent with this project's own physics finding that spreading is expensive (`d(EE)/d(active) < 0`, no sign flip)** |
| concat beats in-place but not `raw_dup` | the gain is capacity, not normalisation |

**[D] The result is row 4.** z lowered pooled EE by 3.511% and spread the physical allocation
(+3.38 active beams, +0.77 satellites). Row 1 is excluded (EE fell). Row 3 is not the match
either — a −3.5% pooled-EE move with a coherent power mechanism is not "little or not at all".
Row 5 is unreachable because arms 3 and 4 do not exist.

**[D] Consistency check against this project's own measured slope.** `CROWDING-COST-2026-09-10.md:1`
gives `d(EE)/d(active) = −425,009.885 bit/J` per added mean-active beam. Applied to Δactive =
+3.38, that predicts ΔEE ≈ **−1,436,533 bit/J**. Observed: **−3,190,295 bit/J**. Same sign,
observed magnitude ≈ 2.22× the slope prediction. **[I]** So spreading accounts for the direction
and roughly half the size; the remainder is not attributed by anything I read.

**[D] What this does and does not close.** It closes the "z-score rescues a collapsed MODQN"
hypothesis on this project's own physics in this project's own EE estimand: the intervention that
is supposed to repair collapse instead *costs* EE here, in the direction the project's crowding
slope already predicted. It does **not** establish that MODQN is uncollapsed — a −3.5% result is
evidence that z has nothing to repair *by the documented mechanism*, which is weaker than a
measurement of MODQN's own state. Job 2 addresses that directly, and does not reach "absent".

### Two structural caveats the closure has to carry

**[V] 1. `MODQN_RAW` is not the frozen checkpoint.** The frozen checkpoint is used *only* as a
tamper anchor: `run_modqn_z_intervention.py:31-37` names it, `:102-106` hashes it before the run,
`:511-513` re-hashes it after and aborts on any change. **It is never loaded.** There is no
`torch.load(FROZEN_CHECKPOINT)` in the file. Both arms are **trained from scratch** — same
initial network for both (`initial_network_sha256` = `62a2ef5450837f…` for RAW and Z_INPLACE
alike), diverging only through the transform.

**[V]** And it is not even a numerical reproduction of the frozen run. On the identical P6 panel
(Job 2's rollout, §2.3), `FROZEN_MODQN` scores `active_beam_count` 7.470 / `argmax_agreement`
0.4871 while `MODQNZ_MODQN_RAW` scores 9.110 / 0.3875. Same seeds, same config, same code
digest (`544fcf078f7e…`, asserted at `:107-109`), different policy. **[D]** So the intervention is
internally valid — RAW and Z_INPLACE are matched to each other — but the claim "this tests
z-score on the project's frozen MODQN checkpoint" is **not what the code does**. The frozen
checkpoint was never an arm.

**[V] 2. The z-score is applied to all four observation blocks undifferentiated.**
`:139-153` `transform_encoded` z-scores the whole `(U, 112)` matrix. `:537-542` records the block
layout: `access_vector[0:28]`, `log1p(channel_quality)[28:56]`,
`beam_offsets_raw_radians[56:84]`, `beam_loads_divide_by_num_users[84:112]`. **[D]** MODQNZ's own
prompt demanded the opposite treatment (`MODQNZ.codex.log:74-77`: *"State exactly which fields
the z-score is applied to and which are left alone … **Normalising a field that is already a
ratio is not the same operation as normalising a raw power**; say what you did per block and
why."*). The code normalises the already-normalised load block and the binary access vector on
the same footing as the log-SNR block, and — the report being absent — nothing states or defends
that choice.

---

# JOB 2 — the four G-3 indicators

## 2.1 The four, and their declared criterion

**[V]** `/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/collapse_metrics.py`.

| # | indicator | definition (file:line) | computation (file:line) |
|---|---|---|---|
| 1 | `active_beam_count` | `:54-59` — *"Distinct relative action slots selected (legacy frozen field name). … it is not a physical `(norad_id, cell_id)` beam identity, so this field must never be presented as a count of physically lit beams."* | `:157-158` `np.unique(actions[served]).size` |
| 2 | `argmax_agreement` | `:61-62` — *"Fraction of users choosing the single most popular action."* | `:160-165` `counts.max() / count_nonzero(served)` |
| 3 | `q_margin` | `:64-65` — *"Top-1 minus top-2, **normalised by the Q range**. Dimensionless."* | `:179-192`, aggregated `:205-207` — **mean over users** of `(top1−top2)/(top1−min)` per user |
| 4 | `q_entropy` | `:70-71` — *"Entropy of the softmax over the masked scalarised row, normalised to [0, 1]."* | `:196-201`, aggregated `:208` — softmax over the valid actions, entropy ÷ `log(n_valid)`, meaned over users |

### **The declared pass/fail criterion is completeness, not a value. There is no threshold — for any of the four.**

**[V]** `collapse_metrics.py:46`, verbatim: **"All four, always. G-3 fails on a missing one, not
on a bad value."**

**[V]** `:3-5` states G-3 itself: 任何『是否崩潰』的判定,必須同時報告 `active_beam_count`、
`argmax_agreement`、`q_margin`、`q_entropy`,且 `q_margin` **必須以 Q 值域正規化後**呈現。
**缺任一項即不通過** — *any collapse verdict must simultaneously report all four, `q_margin`
normalised by the Q range; missing any one fails*.

**[V]** `assert_g3_complete` (`:108-130`) enforces exactly two conditions and no others:
`:114-120` raises `MCRLContractError` if any of `REQUIRED_G3_FIELDS` (`:40-45`) is absent;
`:121-129` raises if any of the four is non-finite. **There is no comparison against any number.**

**[V]** I searched for a numeric criterion and there is none. `grep -rn "q_margin"` over `src/`
and `docs/` returns definitions, the normalisation mandate, and the wiring — never a cut-off.
The nearest thing to a value judgement anywhere in the repo is a *disclosure* obligation, not a
gate: `docs/DEVIATION-REGISTER.md:118` records that dropping lr to 0.001 in the source project
bought `q_margin` falling 10× and that this must be written down alongside the deviation.
Corroborating: `docs/IMPLEMENTATION-PROMPT.md:56` (缺任一項即不通過),
`docs/PREREG-DRAFT.md:330-331`, `docs/PATCH-LEDGER.md:276`,
`src/mcrl/runtime/prereg.py:553-565`, `src/mcrl/runtime/trainer_spec.py:236-247`
(`collapse_report` raises rather than return zeros for a missing sample).

**[D] This matters for what Job 2 can conclude.** As written, G-3 licenses no verdict by itself:
completing the four lifts a *procedural* refusal, it does not supply a decision rule. A verdict
therefore has to come from comparison against a reference policy — which is exactly what §2.4
turns out to break.

**[V] Wiring:** the four are computed at both ends of every training episode, from the **greedy**
argmax (not the executed epsilon-greedy one) — `src/mcrl/algorithms/modqn.py:1169-1215`, with the
rationale at `src/mcrl/runtime/trainer_spec.py:139-155`.

**[V] One definitional fork you need to know about.** The 2026-08-25 frozen legacy tree
(`/home/sat/mcrl-leo-handover-20260825-corrected/src/mcrl/runtime/collapse_metrics.py`,
sha `2245562b6ee1…`) computes `q_margin` as `mean(top1−top2) / mean(top1−min)` — a **ratio of
means**. The current repo file (sha `fb053e68ef44…`) computes the **mean of per-user ratios**,
with the reason in-line at `:185-189`. I report the **current** definition as primary because the
mandate names that file, and I carry the legacy value in every table beside it. The two never
differ by more than ~4% in anything below.

## 2.2 What I computed, and on what

**[V]** Script: `/home/sat/zclose-g3/score_g3.py` (a copy is at
`/tmp/claude-1000/…/scratchpad/score_g3.py`); raw output retrieved to
`/home/u24/papers/mcrl-leo-handover/.scratch/zclose/g3-indicators.json`.

Design, matched deliberately to `MODQN-COLLAPSE-2026-09-10.md` so the numbers are comparable:
native legacy/V0.23 stack at `/home/sat/mcrl-leo-handover-20260825-corrected`; **TRAIN split**;
the 10 frozen P6 development seeds from `probe_p6.P6_EVALUATION_SEEDS`; 10 steps × 100 users =
**100 profiles**, 10,000 selections per checkpoint; greedy masked argmax at `eps = 0` with
lowest-index tie-break, weights `(0.5, 0.3, 0.2)`, via the legacy trainer's own
`_scalarize_q_values` / `_select_unconstrained_actions`. No training. No optimizer state loaded.

**[V] Reproduction check.** My `FROZEN_MODQN` `active_beam_count` = **7.470** distinct slots per
100 users. `MODQN-COLLAPSE-2026-09-10.md` reports `argmax_distinct` = **0.07470** for the same
checkpoint on the same panel — the identical quantity divided by 100 users. My rollout
reproduces the earlier one exactly, so the four indicators below sit on the same measurement as
the existing collapse report rather than beside it.

Four checkpoints. The third and fourth are MODQNZ's completed arms — free to score, same
architecture, and they carry the z contrast onto the same four indicators.

**[V]** `UNTRAINED_INIT_SEED42` is **not** a trained checkpoint: it is the legacy trainer's own
initialisation at `train_seed = 42`, scored without a single gradient step. It is here because
§2.1 established there are no thresholds, so `q_margin` and `q_entropy` are uninterpretable
without a reference for what a **non-discriminative** Q looks like on this exact action space.
It costs one extra rollout and no training.

## 2.3 The four values, per checkpoint

**Four fields for every indicator number below.**
**Reference point:** each other, and specifically `UNTRAINED_INIT_SEED42` for indicators 3 and 4;
there is no declared threshold to compare against (§2.1).
**Information class:** greedy argmax over the scalarised Q surface of a **saved checkpoint**,
computed offline, TRAIN/development split, no training and no learning signal in the loop.
**Estimand:** the per-profile indicator as defined at `collapse_metrics.py:157-208`, then the
arithmetic mean over the 100 profiles.
**Numerator:** #1 distinct selected action slots; #2 users on the single most popular slot;
#3 Σ per-user `(top1−top2)/(top1−min)`; #4 Σ per-user softmax entropy ÷ `log(n_valid)`.

### Pooled over all 100 profiles

| checkpoint | `active_beam_count` [min,max] | `argmax_agreement` [min,max] | `q_margin` [min,max] | `q_entropy` [min,max] |
|---|---:|---:|---:|---:|
| **FROZEN_MODQN** `e6b063ef…1b09c28b` | **7.470** [2, 13] | **0.4871** [0.220, 0.800] | **0.144691** [0.0484, 0.2547] | **0.996027** [0.99382, 0.99746] |
| **UNTRAINED_INIT_SEED42** (0 gradient steps) | 2.580 [1, 5] | **0.9225** [0.770, **1.000**] | 0.114468 [0.0642, 0.1761] | **0.999150** [0.99902, 0.99933] |
| MODQNZ `MODQN_RAW` `cdce028e…` | 9.110 [6, 13] | 0.3875 [0.250, 0.640] | 0.157988 [0.0366, 0.2887] | 0.996287 [0.99379, 0.99725] |
| MODQNZ `MODQN_Z_INPLACE` `ddc8e4ff…` | 6.510 [4, 12] | 0.4435 [0.330, 0.660] | 0.167438 [0.0531, 0.2747] | 0.995020 [0.99327, 0.99623] |

Supporting scale fields (the module requires `q_margin` normalised, and carries these so the
scale is auditable — `collapse_metrics.py:67-74`), plus the legacy aggregation:

| checkpoint | `q_margin_raw` | `q_range` | `q_margin` (legacy ratio-of-means) | no-op users |
|---|---:|---:|---:|---:|
| FROZEN_MODQN | 0.107623 | 0.684916 | 0.150635 | 0 |
| UNTRAINED_INIT_SEED42 | 0.037832 | 0.314517 | 0.118464 | 0 |
| MODQNZ `MODQN_RAW` | 0.103883 | 0.622161 | 0.161922 | 0 |
| MODQNZ `MODQN_Z_INPLACE` | 0.144345 | 0.808445 | 0.173625 | 0 |

### Both sampling points, as G-3 requires (`trainer_spec.py:207-221` — the drift *is* the signal)

| checkpoint | point | `active_beam_count` | `argmax_agreement` | `q_margin` | `q_entropy` |
|---|---|---:|---:|---:|---:|
| FROZEN_MODQN | step 0 | 3.300 | 0.5330 | 0.063974 | 0.996400 |
| FROZEN_MODQN | step 9 | 10.100 | 0.4370 | 0.137493 | 0.995176 |
| FROZEN_MODQN | **drift** | **+6.800** | **−0.0960** | **+0.073519** | **−0.001224** |
| UNTRAINED_INIT | step 0 | 3.200 | 0.8910 | 0.083400 | 0.999148 |
| UNTRAINED_INIT | step 9 | 2.800 | 0.9290 | 0.115367 | 0.999100 |
| UNTRAINED_INIT | **drift** | **−0.400** | **+0.0380** | **+0.031967** | **−0.000049** |
| `MODQN_RAW` | step 0 | 6.400 | 0.4300 | 0.049281 | 0.996215 |
| `MODQN_RAW` | step 9 | 10.300 | 0.3800 | 0.193679 | 0.995688 |
| `MODQN_RAW` | **drift** | **+3.900** | **−0.0500** | **+0.144397** | **−0.000527** |
| `MODQN_Z_INPLACE` | step 0 | 4.000 | 0.4590 | 0.092368 | 0.994380 |
| `MODQN_Z_INPLACE` | step 9 | 9.200 | 0.4020 | 0.185449 | 0.995020* |
| `MODQN_Z_INPLACE` | **drift** | **+5.200** | **−0.0570** | **+0.093081** | **+0.000094** |

\* step-9 `q_entropy` for `MODQN_Z_INPLACE` is 0.994474; the 0.995020 in the pooled table is the
all-steps mean. Drift is computed from the step-wise means.

**[V] Corroboration from an independent artefact.** The frozen run's own receipt,
`/home/sat/mcrl-leo-handover-20260825-corrected/artifacts/training-2026-08-25-rerun01/main/status.json`,
carries a `collapse_summary` — the same four, meaned over the last 100 **training** episodes:
first `active_beam_count` 3.07 / `argmax_agreement` 0.637 / `q_margin` 0.059617 /
`q_entropy` 0.996120; last 9.48 / 0.448 / 0.217325 / 0.995490. **[D]** Same shape as my step-0 and
step-9 rows (3.300 / 0.5330 / 0.063974 / 0.996400 and 10.100 / 0.4370 / 0.137493 / 0.995176) —
different panel (training distribution vs the P6 development seeds), consistent readings.
**[D] Note this means the frozen checkpoint has had all four G-3 indicators on disk since
2026-08-25**; the two collapse reports simply did not read them.

## 2.4 The finding: the two missing indicators cannot do the job the gate assigns them

The reason the gate mandates indicators 3 and 4 is stated in the module's own docstring
(**[V]** `collapse_metrics.py:7-21`): the first two alone can read a *flattened* Q as a
de-collapsed policy, because *"escape is argmax-dispersion under near-flat Q, not a
discriminative Q"*. So `q_margin` and `q_entropy` are supposed to be the pair that tells "the
policy chose" from "the policy is picking between indistinguishable options."

**On this project's decision surface, they do not separate those two states. [V], computed.**

**[V] The untrained network is the demonstration.** `UNTRAINED_INIT_SEED42` has had zero
gradient steps. By indicators 1 and 2 it is severely degenerate: **92.25% of users on one slot**,
using **2.58 of 28** slots, and in at least one profile **100% agreement** (`argmax_agreement`
max = 1.000). It is as close to the sibling's one-beam attractor as anything in this project.
Yet:

| | untrained (0 steps) | FROZEN_MODQN (9,000 eps) | ratio frozen/untrained |
|---|---:|---:|---:|
| `active_beam_count` | 2.580 | 7.470 | 2.895 |
| `argmax_agreement` | 0.9225 | 0.4871 | 0.528 |
| **`q_margin`** | **0.114468** | **0.144691** | **1.264** |
| **`q_entropy`** | **0.999150** | **0.996027** | **0.997** |

**[D]** The untrained network's `q_margin` is **79.1%** of the trained policy's, and its
`q_entropy` is **higher** — i.e. by indicator 4 the untrained network looks *less* concentrated
than the trained one. **A policy that has learned nothing scores essentially the same on both
of the indicators that were supposed to catch exactly that.**

**[V] `q_entropy` has no dynamic range here at all.** Across all **400 profiles** (four
checkpoints × 100), `q_entropy` spans **[0.993270, 0.999329]** — a total span of
**6.06 × 10⁻³** on a [0, 1] scale, covering everything from an untrained network to three
9,000-episode policies.

**[V] And it is very nearly a restatement of `q_range`.** Pearson correlation over those 400
profiles: **`q_entropy` vs `q_range` = −0.9520**. (For contrast: `q_entropy` vs `q_margin`
= −0.4248; `q_margin` vs `argmax_agreement` = −0.3376; `q_margin` vs `active_beam_count`
= +0.2675.)

**[D] The mechanism is structural, not a fluke of these checkpoints.** `q_entropy` is the entropy
of `softmax(row)` over ~28 raw scalarised Q values (`collapse_metrics.py:196-201`) — and unlike
`q_margin`, it is **normalised only by `log(n_valid)`, never by the Q range**. With `q_range`
≈ 0.68 the softmax weights differ by at most a factor `e^0.68 ≈ 1.97`, which is nearly uniform,
so the normalised entropy pins near 1. **This is precisely the defect the module's own docstring
warns about for `q_margin`** (`:18-21`: an unnormalised quantity *"shrinks whenever the Q scale
does, for reasons that have nothing to do with discrimination"*) — the fix was applied to
`q_margin` and not to `q_entropy`, and on this Q scale it saturates indicator 4.

**[I]** `q_margin`'s weakness is a different one and I am less certain of its mechanism: the
per-user normaliser `(top1 − min)` is itself inflated by whatever spreads the Q row, so an
untrained network with a small absolute spread (`q_margin_raw` 0.0378, `q_range` 0.3145) lands at
almost the same *ratio* as a trained one with 2.8× the raw margin over 2.2× the range. The raw
fields do separate the two (`q_margin_raw` 0.1076 vs 0.0378, a factor 2.845) — but the raw margin
is exactly what G-3 forbids reading as the indicator, for reasons the docstring gives and I am
not disputing.

## 2.5 The z contrast on the four, since it was free

**[D]** `MODQN_Z_INPLACE` vs `MODQN_RAW`, same panel, same four fields as §2.3:
`active_beam_count` 6.510 vs 9.110 (**−2.600**), `argmax_agreement` 0.4435 vs 0.3875 (**+0.0560**),
`q_margin` 0.167438 vs 0.157988 (+0.009450), `q_entropy` 0.995020 vs 0.996287 (−0.001267).

**[D]** So on **local action slots** the z arm is *more* concentrated than the raw arm, while on
**physical beams** (§1.4) it is *more* spread — 75.62 vs 72.24. That is not a contradiction; it
is the slot-versus-physical distinction `MODQN-COLLAPSE-2026-09-10.md` insists on, appearing here
as opposite signs on the same intervention. **[D]** It also means the G-3 four, whose indicator 1
is explicitly *not* a physical beam count (`collapse_metrics.py:54-59`), would have read the z
intervention as *increasing* concentration while the physical measurement read it as decreasing —
a further reason the four alone do not settle a verdict here.

## 2.6 What could not be computed, and why

**[V] The zero-learning myopic control has no Q function, so two of the four are undefined for
it.** The reference policy that `MODQN-COLLAPSE-2026-09-10.md` compares MODQN against is
*"independently for each user, select the lowest-index legal argmax of the native linear
`channel_quality`"*, described in that report as having *"no fitted parameters, look-ahead, load
coordination, or learning."* It emits actions; it has no scalarised `(U, A)` value surface.
`compute_collapse_metrics` requires one (`collapse_metrics.py:133-152`, `scalarized_q` is a
mandatory `(U, A)` argument). **[D]** So `q_margin` and `q_entropy` **cannot be computed for the
control at all** — not by proxy, not by substitution. `UNTRAINED_INIT_SEED42` is offered as a
*different* reference (a real Q function that has learned nothing), not as a stand-in for the
myopic rule.

**[D] This is the deeper reason §2.1 bites.** With no threshold and no control value for two of
the four, "does the frozen checkpoint pass?" has no defined answer for indicators 3 and 4 —
there is nothing to pass *against*.

**[V] `MODQN_Z_CONCAT` and `MODQN_RAW_DUP` could not be scored** — the former has no final
checkpoint (only a 2300-episode `resume-state.pt`, and scoring a mid-training resume bundle
would not be the object either report refers to); the latter does not exist.

## 2.7 This project's current learner checkpoints — 2 of 4 recoverable, 2 structurally absent

**[V] The learner checkpoints exist.** Epoch-0500 stage-C checkpoints are on the server, e.g.
`/home/sat/mcrl-v025-arch-ws/artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/checkpoints/`
(per-seed, per-arm `…-epoch-0500.json` with `.sha256` sidecars), and the q1-v2 `a0` panels used
by `BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md` are cached at
`/home/sat/mcrl-v025-design-ws/artifacts/a0-panel-q1v2-nonz-{,selections-}20260910.json`
(schema `mcrl-v025-learned-a0-fixed-selection-cache-v1`, label `Q1-v2-non-z`, 16 checkpoint
receipts, 192 profiles).

**[V] Indicators 1 and 2 are recoverable from that cache, and I computed them.**
Same four fields as §2.3, except — **reference point:** the q1-v2 non-z learner's own selection
cache, with `BASE-COLLAPSE-DIAGNOSIS`'s myopic and geometric controls as the standing comparators;
**information class:** cached learned `a0` = masked `argmax(Q1+Q2)` per user *before joint repair*
(`/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/deployment.py:101,112`; repair is later, at
`:125`), TRAIN anchors, 500 unconverged epochs on **surrogate labels**.

| indicator | learned `a0`, q1-v2 non-z (192 profiles) |
|---|---:|
| `active_beam_count` (distinct action slots) | **7.7344** [4, 10] |
| `argmax_agreement` | **0.4185** [0.19, 0.78] |
| `q_margin` | **NOT COMPUTABLE** |
| `q_entropy` | **NOT COMPUTABLE** |

**[V] Why the other two are not computable from anything that exists.** Each cached selection
carries exactly `['concentration', 'global_anchor_index', 'indices', 'mapping', 'seed']` — the
**selected index per user** and its `(NORAD, cell)` mapping. **The per-user, per-action score row
was never persisted.** `q_margin` and `q_entropy` both require the full `(U, A)` scalarised
surface (`collapse_metrics.py:133-152`, `:179-201`); a vector of argmaxes cannot yield a top-1
minus top-2 gap or a softmax entropy. Recovering them would mean re-running the 16 stage-C head
checkpoints over every action row of every anchor — a new scoring pass over the corpus, which is
outside "no training, no new rollouts, existing checkpoints only". **I did not substitute a
proxy.**

**[I] And two reasons the numbers would not be comparable even if produced.** First, `Q1+Q2` are
**supervised route-head scores on surrogate labels**, not the Q-values of a value-learning agent
— `q_entropy`'s softmax and `q_margin`'s range normaliser would be operating on a different
object at a different scale from the MODQN Q surface. Second, the learner's candidate set per
user is the stage-C coalition action set, not MODQN's fixed 28 slots, so `q_entropy`'s `log(n)`
normaliser and indicator 1's ceiling differ per profile. **[D]** Given §2.4 — that the pair
carries no discriminating information even on the MODQN surface where it is well-defined — I
would not expect producing them here to change the verdict; but that is an expectation, not a
measurement, and I am not claiming it as one.

**[D] So the learner is at 2 of 4, exactly where `BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md` left it.**
The G-3 completeness gate is **not** cleared for this project's current learner, and cannot be
cleared from existing artefacts. That report's own refusal to issue a binary label
(`:5` — *"I do not turn that comparison into a binary 'collapsed/not collapsed' label"*) remains
the correct posture, and it is now the correct posture for a stated reason: the inputs the other
two indicators need were not saved.

---

# THE ANSWER

## Is collapse absent, present, or undetermined here?

## **UNDETERMINED.**

Not "absent". Absent was never available, and completing the four did not make it available.

**[D] Why not absent.** "Absent" was supposed to rest on all four indicators passing. Two things
block that, and only one of them is the one the mandate anticipated:

1. **There is no "passing".** G-3 as written (`collapse_metrics.py:46`) has **no value criterion
   for any of the four** — it is a completeness gate. Completing the four removes a procedural
   refusal; it does not supply a verdict. So "all four passing" is not a state this codebase
   defines.
2. **Even read comparatively, the two newly added indicators discriminate nothing here.** An
   untrained network — 92.25% argmax agreement, 2.58 of 28 slots, one profile at 100% — posts
   `q_margin` 0.1145 (79.1% of the frozen policy's 0.1447) and `q_entropy` 0.9992 (*above* the
   frozen policy's 0.9960). `q_entropy` spans 6.06 × 10⁻³ across all 400 profiles and correlates
   −0.952 with `q_range`. **The pair that exists to catch "argmax dispersion under near-flat Q"
   does not distinguish a 9,000-episode policy from a randomly initialised one on this decision
   surface.**

**[D] Why not present either.** Indicators 1 and 2 on the frozen checkpoint —
`active_beam_count` 7.470 of 28 slots, `argmax_agreement` 0.4871, drifting from 3.300/0.5330 at
step 0 to 10.100/0.4370 at step 9 — are nowhere near a degenerate attractor, and they are joined
by the physical-beam measurements already on record (68.70 physical beams, `modal_frac` 0.04170,
`MODQN-COLLAPSE-2026-09-10.md`). Nothing I computed moves toward "collapsed". The reason I cannot
say "absent" is instrumental, not adverse.

**[D] And for the current learner it is undetermined for the older, cruder reason:** the four are
still **2 of 4** there (`active_beam_count` 7.7344, `argmax_agreement` 0.4185; §2.7), and the
missing two cannot be computed from any existing artefact because the per-action score rows were
never persisted. The G-3 completeness gate is cleared for the frozen MODQN checkpoint as of this
document, and is **not** cleared for the learner.

**[D] So the precise statement is:** on this project's frozen MODQN checkpoint, all four G-3
indicators are now reported (§2.3), which clears the completeness gate that both existing
collapse reports failed. The verdict the gate was built to enable still cannot be issued, because
the two indicators it added carry no discriminating information on this action space and this Q
scale. **ZWHY's Q6 said "no binary collapse verdict is currently licensed here in either
direction" for want of the two missing indicators. Having computed them, that conclusion does not
change — the reason for it does.** It is no longer "the numbers were not measured"; it is "the
numbers were measured and they do not separate the hypotheses."

## And the z line

**[D]** MODQNZ's closure **does** rest on EE evidence in this project's declared estimand —
pooled EE, a ratio of sums, `run_modqn_z_intervention.py:379`. That is the one thing that came
out in the closure's favour, and it is a real difference from the sibling, whose entire z-score
case was a mean of ratios.

**[D]** What the closure does *not* have: a written conclusion (none exists), the width-controlled
arm pair (never completed), more than one training seed per arm (n = 1), and any contact with the
frozen MODQN checkpoint (never loaded). And the direction is the reverse of the belief that
prompted the line — z-in-place **lowered** pooled EE by 3.511% while spreading the allocation,
landing on row 4 of MODQNZ's own predeclared rule, consistent in sign with this project's measured
`d(EE)/d(active) = −425,009.885 bit/J`.

---

# Evidence classification

**[V] Verified — I read the cited file at the cited line, or ran the code and read its output:**
the absence of `/home/sat/mcrl-v025-mqz-ws/MODQN-Z-INTERVENTION-2026-09-10.md` and the empty git
history of that workspace; the entire contents of `run_modqn_z_intervention.py` (arms `:49-54`,
transform `:139-153`, frozen-checkpoint anchoring `:31-37,102-106,511-513`, seeds `:56-59`,
evaluation `:276-393`, pooled EE `:377-379`, block layout `:537-542`); every number in the
`MODQN_RAW` / `MODQN_Z_INPLACE` / `MODQN_Z_CONCAT` `result.json` and `progress.json` files
retrieved to `.scratch/zclose/modqnz/`; `MODQNZ.codex.log` lines 40-125 (the predeclared design
and reading rule) and its terminal state; `src/mcrl/runtime/collapse_metrics.py` in full;
`src/mcrl/runtime/trainer_spec.py:139-260`; `src/mcrl/algorithms/modqn.py:1169-1215`;
the negative grep for any numeric G-3 threshold in `src/` and `docs/`; the sha256 difference
between the current and 2026-08-25 `collapse_metrics.py` and the exact diff between them; the
frozen run's `status.json` `collapse_summary`; and every indicator value in §2.3-2.5, produced by
`/home/sat/zclose-g3/score_g3.py` with raw output at `.scratch/zclose/g3-indicators.json`.

**[D] Derived by me** from those verified numbers: all deltas, ratios, percentages, the paired
per-scenario sign count, the crowding-slope consistency check, the reading-rule row assignment,
the Pearson correlations, and the two "why not absent / why not present" arguments.

**[I] Inferred and flagged in place:** the `q_margin` normaliser mechanism (§2.4), the portion of
the EE drop not accounted for by the crowding slope (§1.4), and the caution about reading the
n=10 scenario spread as a test of an n=1 intervention (§1.4).

**Relayed, not re-derived:** `CROWDING-COST-2026-09-10.md:1`'s slope and
`MODQN-COLLAPSE-2026-09-10.md`'s physical-beam figures and myopic-control description — I read
those reports, and I independently reproduced the one number that overlaps my own rollout
(`argmax_distinct` 0.07470 = my `active_beam_count` 7.470), but I did not re-derive the rest.

**Not done, by design:** no training, no new arm, no re-analysis of ZWHY's sibling work, no
modification to `/home/sat/mcrl-leo-handover` or its venv, no scoring of the abandoned
`MODQN_Z_CONCAT` resume bundle, and no proposed fix — the design decision is the owner's.

**Interruption note.** The controlling session hit a usage limit partway through. The one
detached server computation (`score_g3.py`) had already completed before the interruption — its
output was retrieved to `.scratch/zclose/g3-indicators.json` and every §2.3-2.5 number is read
from that single file. **Nothing was re-run, and no result in this document was recomputed after
the interruption.** The only work done after resuming was §2.7, which had been delegated to a
parallel search that died on the same rate limit; I did it directly, and it consists of two
read-only `ssh` listings plus one arithmetic pass over an existing cached artefact.
