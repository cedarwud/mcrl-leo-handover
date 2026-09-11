**Mostly (C) with a residual (B): the sibling's famous z-score win (146.6 → 357.1) is a comparison the sibling's own repo forbids citing as matched, its one width-matched headline was formally retracted on 2026-07-17, and its only clean matched contrast is +27.88 with a 95% CI of [−20.86, +76.63] — so the premise "z-score helped there" is not established at the size it is remembered at; a small matched effect does survive (+56.54, 6/6 seeds), it was never pooled EE, nothing in this project measures z-score as harmful to EE at all, and this repo's own writing rules already recorded the whole answer eight weeks ago — the belief being questioned traces to a 2026-07-20 user override that the same record flags as contrary to the evidence.**

# ZWHY — why z-score "helped there and hurts here" — 2026-09-11

Read-only audit across `/home/u24/papers/modqn-paper-reproduction` (sibling, reference-only) and
`/home/u24/papers/mcrl-leo-handover` (this project). No training, no server job, no artefact modified.

Everything below is tagged **[V]** verified by me reading the cited file at the cited line, or
**[R]** relayed from a report I read but did not re-derive, or **[D]** derived arithmetic, or
**[I]** inferred. The sibling is reference-only: its records are reported as *what they say*.

---

## Q0 — The question was already answered in this repository, and the answer was overridden

**[V]** `.scratch/chinese-word-r1-symbols-20260905-r1/input/thesis-mc/WRITING-RULES.md:270-290`
(identical copy at `.scratch/chinese-word-v023-lcsrs-20260905-r2/WRITING-RULES.md`) carries a
標題-level entry dated **2026-07-20 (晚)** headed **「USER OVERRIDE — 解崩敘事『還原回去』，與同日權威裁決
相反且現有數據不支持」**.

**[V]** It records the user instruction verbatim: 「baseline modqn 還是會崩，要靠 z-score 來崩〔解崩〕」
— *baseline MODQN still collapses, and z-score is what de-collapses it* — and states that the
controller reported the conflict in full, the user chose to override, and the entry exists
**precisely so this is traceable later**: 「本條存在的目的就是讓日後追溯得到——不要把它當成已證實的結論。」
(*do not treat this as an established conclusion*).

**[V]** The same entry then lists why the data do not support it (9000 ep, frozen argmax scorer,
Mbits/J):

- **L1 (raw MODQN, no z-score) = EE 428.60 · min_cov 0.586 · served 0.753**, labelled `healthy` by
  the authoritative document;
- what collapse actually looks like (`lr = 0.01`) = EE **145–150** · min_cov **0.167** · served
  **0.297**, three seeds bit-identical at 150.13 — a seed-independent degenerate attractor.
  **「L1 不在那個狀態。」** (*L1 is not in that state*);
- **「z-score 的實測作用＝`L2−L1 = +56.54`（6/6 種子）＝把健康的往上推，不是把崩掉的救回來。」**
  (*z-score's measured effect pushes a healthy baseline up; it does not rescue a collapsed one*);
- 「『z-score de-collapse』**已於 2026-07-17 撤回**」 (*retracted*), citing
  `ZSCORE-3WAY-FINDINGS-2026-07-17` and the +27.88 / CI-crosses-zero figure;
- **「z-score 有幫助但擋不住崩；lr 才是控制變數」** (*z-score helps but cannot prevent collapse; lr is
  the controlling variable*).

**[V]** It also records the framework rule that follows: 「z-score = substrate，不得宣稱為 MCRL 元件，
**因為它沒有 leave-one-out 對照臂**」 — *z-score is substrate; it may not be claimed as an MCRL
component, because it has no leave-one-out control arm* — and the unresolved viva risk that
`L6 − L1 = +180.85` is the bigger number but 「你怎麼隔離 z-score 的貢獻？」 is **無解** (unanswered).

**[D] Consequence for the owner's question.** The premise 「z-score 在舊的專案有效」 is, in this
repository's own authoritative record, **an overridden belief rather than a finding**. Everything I
verified independently below reproduces that record from the primary sources. The rest of this
document is therefore confirmation, not discovery — which is itself the most useful thing to report,
because it means no new experiment is needed to answer the question as asked.

---

## Q1 — What is "z-score" in each project? (check this first)

**They normalise the same quantity. This is not the answer, but a different distinction is.**

### Sibling

**[V]** A **state-feature** transform, not a reward transform. Per feature, standardised **across the
users present at that step**, and **concatenated to** the raw block:

- `src/modqn_paper_reproduction/modqn_faithful_ablation/encoding.py:62-85` — `cross_user_zscore`,
  `mean`/`std` over `axis=0` = the user axis, `eps = 1e-6`.
- `encoding.py:88-107` — `encode_population`: mode `concat` returns
  `np.concatenate((raw, z), axis=1)`; `112 -> 224`.
- `src/modqn_paper_reproduction/coordinator_dqfd_zscore/representation.py:132-169` — the
  corrected-r3 form, `140 -> 280`, `Z1` = `[raw ‖ z]`, `Z0` = `[raw ‖ raw]` width control.
- `docs/catfish-explainer-package/04-zscore.md:14-26` — the deployed training form:
  `shared_q_isolation/standardize.py:25-43`, `U = 100`, `F = 224`, network input `448`,
  **recomputed live every step**.

**[V]** The raw block is preserved and provably recoverable:
`representation.py:269-274` asserts `output[..., :140] == input.astype(float32)` and records
`raw_block_recoverable`. **[D]** So the absolute scale is *not* destroyed; it sits in the first half.

**[V]** Reward-side normalisation is a *separate, differently-named* mechanism in the sibling
(PopArt online target z-score, `src/modqn_paper_reproduction/runtime/popart_online.py:40,83,126`),
and it is recorded as **tried and failed** (`docs/failure-route-ledger.md:64-68`, relayed at
`.scratch/reviews/evidence-bundle-2026-09-11/reports/SIBLING-CONCEPT-TRANSFER-2026-09-10.md:31`).

### This project

**[V]** There is **no z-score in this repository's source at all**:
`grep -rniE "z[-_ ]?score|zscore" src/` returns **0 hits**. The only normalisation surface is
`src/mcrl/runtime/trainer_spec.py:107`, `reward_normalization_mode = "raw-unscaled"`, alongside
`reward_calibration_mode = "divide-by-fixed-scales"` (`:100`) — **fixed** scales, not per-batch.
`trainer_spec.py:113-117` records that the online reward-standardisation surface (4 fields) was
**deleted** under W-09 as having no consumer.

**[R]** The z view that *was* run lives in a server workspace, built by
`/home/sat/mcrl-v025-design-ws/build_zscore_corpus.py`, and is the **same construction**: raw
features plus a live cross-user population-z block appended to C1, C2 and the C3 member blocks —
Q1 `15 -> 30`, Q2 `22 -> 44`, C3 `296` with member width `66`
(`.scratch/reviews/evidence-bundle-2026-09-11/reports/Z-VIEW-SCORING-2026-09-10.md:53,137`;
`.../RAW-DUP-CONTROL-2026-09-10.md:18`). Schema id
`MCRL_V025_STAGEC_Q1_V2_Q2_V1_RAW_PLUS_LIVE_USER_Z`.

### The distinction that *does* matter

**[D]** Same quantity, same axis, same concatenation. What differs is **where it sits in the
pipeline**. In the sibling it is inside the **RL trainer's state encoder**, feeding a shared Q
network whose per-user argmax *is* the deployed policy. In this project it is a feature block on
**supervised route heads (C1/C2/C3)** whose scores are summed and fed to a downstream selector, and
the object being measured is a **route ablation marginal**, not a policy's EE. So "did z help" is
literally not the same question in the two projects, and the two answers are not comparable
endpoints. See Q4.

---

## Q2 — What is the sibling's actual recorded evidence that z-score helped?

Four distinct pieces of evidence exist. Three of them are dead or unusable, and the sibling's own
files say so.

### (a) The famous one — and it is flagged do-not-cite in the sibling's own repo

**[V]** `docs/catfish-explainer-package/04-zscore.md:56` presents the supporting measurement as
「實測支持：`argmax-EE` 從 raw 的 **146.6** 拉到 **357.1**（arm 平均；best-of-3 = 418.5）」.

**[V]** That exact pair is flagged **CROSS-CONDITION** in four places in the same repository:

- `configs/shared_q_isolation/v3/fulldqfd_OFF_raw.yaml:7` — *"the landmark raw≈146.6 vs concat≈357
  is CROSS-CONDITION and must NOT be cited as if it were matched"*.
- `configs/shared_q_isolation/v3/waveE_OFF_raw.yaml:13` — same sentence.
- `analysis/family-b-collapse-diagnosis/FULLDQFD-GROUPD-PREREG-2026-07-14.md:10`, and `:55` puts
  *"citing the cross-condition `146.6 vs 357` as if it were the [z-score effect]"* on the
  **FORBIDDEN** list.
- `analysis/family-b-collapse-diagnosis/catfish-v2/GROUPA-RESULT-2026-07-14.json:586` — provenance
  field: *"CROSS-CONDITION raw-MODQN landmark (NOT computed by this script; a different
  arm/condition). Cited for scale only."*

**[D]** The explainer chapter that this project imported its picture of z-score from cites, as its
one empirical support, the exact number its own repository forbids citing that way.

### (b) The width-matched headline — **retracted**

**[V]** `CURRENT-STATE.md`'s 2026-07-15 banner claimed *"At matched width 448: `concat`(z) 0/6
collapsed @ EE 523.78 vs `width`(no-z) 5/6 collapsed @ EE 402.90 ⟹ the z-score effect is REAL"*
(quoted at `analysis/family-b-collapse-diagnosis/catfish-v2/ZSCORE-3WAY-FINDINGS-2026-07-17.md:17-22`).

**[V]** That document retracts it (`:24-26`): *"The `+120.88` is carried by a broken control.
Against the honest baseline the z-score is **not separated from zero at n=6**."* And `:60`:
*"⛔ **NOT** 'the z-score effect is REAL' — that cited the broken control."*
Reason (`:45-49`): `[raw ‖ raw]` is exactly collinear, so it is *"a pathological input in its own
right"*, costing `raw − width = +93.00` EE with no z-score involved on either side.

### (c) The one clean matched contrast — underpowered, crosses zero

**[V]** `ZSCORE-3WAY-FINDINGS-2026-07-17.md:28-42`. Three wave-E arms, **6 seeds**, 9000 episodes,
`run_metadata.json`-verified **single variable** `shared_q_isolation.form`, everything else
identical (lr `1e-3`, decode argmax, `k_c 1`, `k_cap 3`, r1 `angle_aware_ee`, injection OFF):

| arm | form | input | argmax-EE | min_cov | argmax_distinct |
|---|---|---|---:|---:|---:|
| `waveE_OFF` | `concat` | `[raw ‖ z]` 448 | **523.78** ±34.44 | 0.7920 | 11.163 |
| `waveE_OFF_raw` | *(absent)* | `raw` 224 | **495.89** ±21.30 | 0.6889 | 8.466 |
| `waveE_OFF_width` | `width` | `[raw ‖ raw]` 448 | **402.90** ±22.97 | 0.5924 | 7.359 |

| contrast | mean | 95% CI (n=6, t=2.5706) | sign |
|---|---:|---|---|
| `concat − width` | +120.88 | [+81.45, +160.31] | 6/6 |
| **`concat − raw`** | **+27.88** | **[−20.86, +76.63]** | **5/6 — crosses zero** |
| `raw − width` | +93.00 | [+59.00, +126.99] | 6/6 |

**[V]** The document is explicit in both directions (`:61-64`): it is *"⛔ NOT 'the z-score does
nothing' — `concat − raw` is **underpowered**, not null: paired sd 46.45 ⟹ MDE ≈ 55 EE at n=6, and
the observed +27.88 sits below it."*

**[V]** And it carries a **second, independent confound** (`:73-84`): the arms are **differentially
converged**. `concat` peaked at 58.6% of budget with 0/6 seeds still at peak in the last 10%;
`raw` peaked at 76.8% with 3/6 still at peak; `width` 78.5% with 2/6. *"9000 ep was enough for
`concat` and not enough for the other two ⟹ endpoint and sample-efficiency are not separable here,
and the confound points toward the project's preferred conclusion."*

### (d) The one matched positive that survives

**[V]** `analysis/family-b-collapse-diagnosis/COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md:95` —
measured on the healthy `lr = 1e-3` substrate, **6 formal seeds**, same frozen argmax scorer:
**`L2 − L1` = +56.54 Mbits/J, 6/6 seeds**, described as the *"context-normalization increment on the
baseline"*; `min_cov` 0.586 → 0.732 across L1 → L2.

**[V]** I checked that this is genuinely a z-on/off pair.
`diff configs/shared_q_isolation/v3/abl9k_baseline_raw.yaml configs/shared_q_isolation/v3/abl9k_baseline.yaml`
shows the **only** substantive difference is the added block

```yaml
shared_q_isolation:
  form: concat
  zscore_eps: 1.0e-6
```

(the rest of the diff is the comment header and the arm name; `decode`, `state_aug`,
`gamma_per_objective: null`, `value_stratified`, `injection_rung1`, `r1_reward_mode:
system-ee-contribution`, `angle_aware_ee_contract_version` and `base_prereg` are identical).
**[V]** `abl9k_baseline_raw.yaml:1-4` states its own purpose: *"MODQN baseline on RAW state (NO
z-score / context normalization). The z-score ablation floor the ladder's L2 (concat-z baseline) is
measured against ... the width control is the documented pathological-collinearity one; not used."*

**[D]** So the sibling's honest matched z effect is **+56.54 on a ~430 base (≈ +13%)**, 6/6 seeds —
real, but roughly a **twentieth** of the 146.6 → 357.1 (≈ 2.4×) impression the explainer leaves.
**[I]** I did not audit whether the abl9k ladder suffers the same differential-convergence confound
that killed the wave-E contrast; that audit does not exist in the records I read.

### Was the metric pooled EE? **No.**

**[V]** The scorer is `analysis/family-b-collapse-diagnosis/catfish-v2/score_argmax_endpoint.py`.
Line `121`: `m["argmax_EE"] = m["r1"] / 1e6`. Line `105` accumulates
`acc["r1"].append(float(r1.mean()))` — the **mean over the 100 users** of the per-user term; line
`118` takes the **mean over the T steps of an episode**; line `120` takes the **mean over the 48
episodes**. The per-user term is `family_b_eta_r1` → `family_b_system_ee_contribution`
(`src/modqn_paper_reproduction/analysis/family_b_recalibration.py:120-143`), i.e.
`R_u / P_system`, whose **sum** over users is the instantaneous system EE.

**[D]** Therefore `argmax-EE` = a **triple arithmetic mean of instantaneous ratios**
(users → steps → episodes), scaled by `1/U`. It is **a mean of ratios, not a ratio of sums**.
Under this project's stated rule, **none of the sibling's z-score evidence is pooled-EE evidence.**
It is also not a loss and not a bare collapse diagnostic — it is an EE-flavoured endpoint scored
by a frozen 48-episode harness — so it is closer to EE evidence than a training curve, but it is
not the estimand this project judges by. The co-reported `min_cov` / `argmax_distinct` numbers *are*
collapse diagnostics and were reported alongside.

---

## Q3 — Was the sibling's z-score run confounded?

**Yes — three separate confounds, each recorded in the sibling's own files, and two of them were
found by the sibling *after* the z-score story had been written into `CURRENT-STATE.md`.**

### Confound 1 — the landmark moves the learning rate, not the z-score

This is the one the brief predicted ("fixing collapse (A) and fixing training (C) mask each other").
Its record is `analysis/family-b-collapse-diagnosis/COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md`.

**[V]** Verdict line 3-6: *"the collapse that this project has treated as a property of MODQN /
shared-Q / per-user-argmax is identified as an artifact of `lr = 0.01`. Flipping ONLY the learning
rate (0.01 → 0.001), with decode, episodes, state form, env and wave held fixed, doubles argmax EE
and lifts worst-user coverage from 0.312 to 0.698."*

**[V]** All cells scored by the **same** frozen harness, n = 3 seeds per cell (`:26-46`):

| decode | lr | ep | state form | argmax-EE | min_cov | |
|---|---|---|---|---:|---:|---|
| hybrid | 0.01 | 3000 | aug-224 | 145.47 | 0.167 | COLLAPSED |
| argmax | 0.01 | 3000 | **raw-224** | **150.13** | 0.167 | COLLAPSED |
| argmax | 0.01 | 3000 | **concat-448 (z)** | **235.53** | 0.312 | still far below healthy |
| argmax | **0.001** | 3000 | concat-448 (z) | **472.22** | 0.698 | HEALTHY — only lr flipped |
| argmax | **0.001** | 9000 | **raw-224** | **493.18** | 0.687 | healthy (waveE) |
| argmax | 0.001 | 9000 | raw-224 | 428.60 | 0.586 | healthy (abl9k L1) |

**[V]** `:36-38` — the lr isolation is single-variable: `fulldqfd_OFF` vs `fulldqfd_OFF_lr001` come
from the same wave and their `run_metadata` leaf-diff has *"exactly one substantive difference"*.

**[V]** `:70-72` — *"the concat/z state at bad lr reaches only 235.53 vs raw's 150.13 — z-score
**helps** but does not prevent the collapse; lr is the controlling variable"*, and the document
records that the project's own prior note already said 「z-score 不足以防崩，lr 才是」.

**[D]** So the 146.6 → 357.1 landmark straddles **at least** the learning rate (0.01 vs 0.001) as
well as the state form. Within one lr, z buys 150 → 236 while still collapsed; changing lr alone
buys 236 → 472. The overwhelming majority of the landmark gap is the learning rate.

**[V]** `:83-92` — the document then withdraws the premise, not just the number: *"MODQN / shared-Q
+ per-user-argmax collapses on this environment — as a general statement"* is **WITHDRAWN**, and
three further conclusions measured in the `lr = 0.01` era are marked **suspect, not re-measured**.

### Confound 2 — width

**[V]** `concat`(448) vs `raw`(224) differ in the z-score **and** the input dimension. The sibling
built `waveE_OFF_width` to close it
(`analysis/family-b-collapse-diagnosis/WAVE-E-AMENDMENT-width-and-insurance-2026-07-14.md:30,67`,
committed data-blind at 09:29 UTC before either checkpoint landed, per
`ZSCORE-3WAY-FINDINGS-2026-07-17.md:52-56`). **[V]** It failed as a control: *"It fixed the width
confound by introducing a collinearity confound. Neither `concat − width` nor `concat − raw`
isolates the z-score cleanly"* (`:56-57`).

### Confound 3 — differential convergence, pointing the preferred way

Quoted under Q2(c) above. **[V]** `ZSCORE-3WAY-FINDINGS-2026-07-17.md:82-84` notes it is *"the same
episode-budget confound the USER caught on the fulldqfd wave on 2026-07-14"* — i.e. caught twice.

### What was never done

**[V]** `ZSCORE-3WAY-FINDINGS-2026-07-17.md:100-106` — the settling run (*"`concat` vs `raw`, with
(a) a budget that converges **all** arms, and (b) enough seeds to clear the ~55 EE MDE"*) was
explicitly **deferred**, and then made moot: *"the corrected-r3 seam ... changes the encoder base
from 224 to 140, **which invalidates every z-score arm**."*

**[V]** The matched replacement arm `fulldqfd_OFF_raw` was preregistered as **D-1**, *"the MATCHED
replacement for the cross-condition 146.6-vs-357 claim"*
(`FULLDQFD-GROUPD-PREREG-2026-07-14.md:38`), with the stated stakes: *"NULL ⟹ the z-score is NOT
what lifts MODQN and the whole 'de-saturation' narrative needs re-writing."* Its own config header
is marked `READINESS-ONLY` (`fulldqfd_OFF_raw.yaml:11`), and the aggregate note records that even
D-1 is *"⚠ CONFLATED BY DESIGN: this moves the TRAINING substrate and the INFERENCE-time
normalization together"*
(`analysis/family-b-collapse-diagnosis/catfish-v2/fulldqfd-aggregate-2026-07-14/FULLDQFD-READ-2026-07-14.json:2136`).

**[D] Q3 answer: the sibling's z-score runs were confounded by lr, by width, and by convergence
budget; the cleanest surviving contrast is underpowered and its remaining confound favours z. This
is what decides between (B) and (C), and it decides for (C).**

---

## Q4 — This project's evidence that z-score is harmful or unnecessary

**"Harmful" is *not* an EE measurement here. What is measured is that z shrinks one route's
ablation marginal. Separately — and in the opposite direction — z is measured to *repair* a real
representation pathology in this project.**

### The predeclared reading rule (written before any number existed)

**[V]** `.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-PREDECLARATION-ZSCORE-AND-HORIZON-2026-09-10.md:1-5,28-45`
fixes four readings in advance, and names the two controls: `raw_dup` (`[raw‖raw]`, same width, zero
new information) and `z_perm` (same normalisation, statistics over a permuted grouping).
**`z_perm` was never run** — no report for it exists anywhere in `.scratch/` or `docs/` (grep for
`z_perm|zperm` returns only the predeclaration, the ZSCORE amendment and a chain log).

### The measured "harm": one route marginal, 16/16 seeds

**[V]** `.scratch/reviews/evidence-bundle-2026-09-11/reports/Z-VIEW-SCORING-2026-09-10.md`.
16 learner seeds × 20 development anchors, **epoch 500**, three runs each scored on **its own**
schema-digest-matched panel, unmodified scorer, all 48 checkpoint sidecars verified.

| marginal | z view | Q1 v2 (like-for-like base) |
|---|---|---|
| `FULL − DROP_C1` | +1.353181 Mbit/J (+3.4513%), 14/16 + — **sign flips** | **+12.691200 (+42.9183%), 16/16 +** |
| `FULL − DROP_C2` | +0.762113 (+1.9149%), 13/16 + — sign flips | −1.148719 (−2.6462%), 15/16 − |
| `FULL − DROP_C3` | −2.251681 (−5.2593%), 15/16 − | −1.200528 (−2.7622%), 14/16 − |

**[V]** Paired within-panel, seed by seed (`:126-135`): `Δ(z − Q1v2)` on `FULL − DROP_C1` is
**−11.379188 Mbit/J, smaller at 0/16 larger — i.e. 16 of 16 seeds**. C2, C3 and
`FULL − ALL_NEUTRAL` are **indistinguishable** (paired signs flip).

**[V]** The controller ruling that followed:
`.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-NOTE-C1-C2-COMPETE-2026-09-11.md:18-20`
— *"**z view: closed at this budget.** It reduces the C1 marginal at 16/16 paired seeds (mean
−11.34 Mbit/J) and does not detectably change C2 or C3."*

**[V]** Crucially, `Z-VIEW-SCORING:122,269` forbids the EE-level reading: *"I do not compare EE
levels across panels ... **No cross-panel comparison.** Each EE level belongs to its own panel."*
**[D] So there is no measurement in this project that the z view lowers pooled EE.** Its FULL arm
sits at 40.561 Mbit/J on its own panel against Q1 v2's 42.262 on a different panel, and reading
that difference is explicitly disallowed.

### The measured *benefit* in this project — with the width control run

**[V]** `.scratch/reviews/evidence-bundle-2026-09-11/reports/RAW-DUP-CONTROL-2026-09-10.md`.
`raw_dup` = `[raw‖raw]`, Q1 30 / Q2 44 — identical widths and first-layer parameter count to the z
view; same corpus, same runner SHA, launch receipt field-for-field equal to the z run's (epochs,
cadence, 16-seed list, head literals + digest, runner sha, arm inventory, source map, anchor list,
row counts). 16 seeds × 22 TRAIN anchors, epoch 500, FULL arm.

| run | deployed `Q1+Q2` mean \|off-diag Pearson\| (floor 0.2735) | C1 srank / 8 | C2 srank / 50 |
|---|---:|---:|---:|
| v2 non-z | 0.481769 (+0.2082) | 0.6364 | 0.4544 |
| `raw_dup` | 0.481920 (+0.2084) | 0.6211 | 0.4700 |
| **z view** | **0.360429 (+0.0869)** | **0.8153** | **0.9034** |

**[V]** Paired (`:139-141`): `raw_dup − non-z` = **+0.000151** correlation (9/16 seeds), i.e. flat;
`z − non-z` = **−0.121340** (0/16 seeds worse) and **+0.449034** on C2 rank fraction (352/352 cells,
16/16 seeds). **[V]** `:122-131` — z is the **only** view that lifts the step-3 / step-7 C2 rank
collapse at the four group-departure anchors (C2 srank ≈ 11–13 for non-z and `raw_dup`, ≈ 37 for z).
**[V]** Its verdict row (`:14`): *"the sibling's `width448` duplicate-raw control did not repair its
pathology, and `raw_dup` does not repair anything here either. The difference is that **this
project's z view *does* repair something**, and the control shows width is not the reason."*
**[V]** `:186` — *"Anything about EE. No EE was computed."*

### The one pooled-EE-labelled comparison, and it goes the other way

**[V]** `.scratch/server-sync-20260909/audits/out-ZSCORE.md:7-11` — the ZSCORE agent's own
completion summary (the full report lives at `/home/sat/mcrl-v025-design-ws/ZSCORE-VIEW-AND-TRAINING-2026-09-10.md`,
outside this filesystem, so this is **[R]**, a summary line I read but whose derivation I could not
check):

- Z view **29.948640 Mbit/J**, `modal_frac` 0.067240
- Q1-v2 non-z **29.176924 Mbit/J**, `modal_frac` 0.055469
- **Z versus Q1-v2: +0.771716 Mbit/J**; active beams, satellites and distinct argmax indices all
  increased, but modal share increased too. Weak-static floor 11.027760 Mbit/J.

**[D]** So the only place in this project where a z-vs-non-z **EE level** was written down at all,
z is **higher**, not lower. Note this is a different evaluation surface from `Z-VIEW-SCORING`'s
20-anchor panels (whose FULL levels are 40.561 vs 42.262), and it is exactly the kind of cross-view
level comparison that `Z-VIEW-SCORING:122,269` later ruled inadmissible. **Neither number supports
"z-score is harmful to EE here."**

### The physics reason the sibling's mechanism should not be expected to help here

**[V]** `.scratch/reviews/evidence-bundle-2026-09-11/reports/CROWDING-COST-2026-09-10.md:1` —
*"On this development panel, opening beams lowers EE: **`d(EE)/d(active) = −425,009.885 bit/J` per
added mean-active beam** over 8.00–98.25 beams (no panel-level sign flip); the controlled two-user
case is the low-load exception, where spreading 1→2 beams raises EE 60.805%; therefore the sibling
project's 'collapsed means broken' diagnosis does not transfer to this physics as a general
diagnosis."*

**[V]** `:134` — *"On this panel an explicit load-balancing term would be **actively harmful to EE**
because it would reward movement in the direction whose measured EE slope is negative."*
**[V]** `:140`, and the report tags this itself as **Inferred**, not measured: *"The sibling
project's cross-user z-score result cannot be imported as a collapse diagnosis without showing an EE
gain under this project's current TDM, target-SINR, clipping, and energy model. On the measured
development panel, the imported diagnosis points in the wrong direction."*

**[D]** This is the strongest *mechanistic* support for (B) anywhere in the record: the sibling's
z-score is valued there because it **spreads**, and spreading is measured to be **EE-negative** in
this project's physics over the whole non-degenerate range. It is a measured slope about spreading,
one inferential step away from z-score — the report says so — but it is a real physical reason, not
an absence-of-symptom argument.

### The test built to settle this — dispatched, declared closed, result not in this repo

**[V]** `.scratch/AGENT-REGISTRY.md:55` lists **MODQNZ** among completed agents:
*"MODQNZ (codex, stopped after decisive pair)"*.
**[V]** `.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECLARATION-TRAINING-PAUSE-2026-09-11.md:11`
— *"**MODQNZ** (earlier) — decisive pair done; **z line closed**."*
**[R]** Per the record-search, MODQNZ was the interventional arm set on the **frozen MODQN
checkpoint** (SHA-256 `e6b063ef…1b09c28b`): `MODQN_RAW` vs `MODQN_Z_INPLACE` (no capacity confound)
vs `MODQN_Z_CONCAT` / `MODQN_RAW_DUP` (sibling-matched with the capacity control), 9,000 episodes.
**[V]** The log in this repo (`.scratch/server-sync-20260909/audits/MODQNZ.codex.log`) stops at
episode 800/9000, and **no result file, no numbers, and no report are present on this filesystem**;
the named report path is `/home/sat/mcrl-v025-mqz-ws/MODQN-Z-INTERVENTION-2026-09-10.md`.

**[D] So the sentence "z line closed" currently rests on a result that cannot be read here.** That
is the single most consequential gap in this audit: MODQNZ is the one experiment designed to answer
the owner's question *directly*, on this project's own frozen MODQN checkpoint, with both the
in-place (no width change) and the sibling-matched (width-controlled) forms.

### Is "harmful" measured, or is "no longer needed" inferred?

**[D] Neither cleanly.** Three distinct statements are being run together in the project record:

1. **"Unnecessary" — inferred, not measured.** The rejection ledger entry
   `.scratch/reviews/evidence-bundle-2026-09-11/reports/SIBLING-CONCEPT-TRANSFER-2026-09-10.md:183`
   reads: *"**Live cross-user z-score:** solved a sibling common-mode collapse absent under F3 and
   introduces an avoidable cross-user dependency."* Its inventory row (`:54`) adds: *"none: current
   F3 says physical choices already diversify; **no fact reports input common-mode saturation**"*.
   This is an **absence-of-symptom inference**. The common-mode ratio the sibling actually measures
   for this purpose (its screen `R`, `04-zscore.md:140-157`, value `0.33632`) has **no counterpart
   measured in this project**.
2. **"Harmful" — measured, but to a decomposition, not to EE.** The 16/16-seed C1-marginal
   reduction above. That is a real paired measurement. It is harm to *"three Catfish, each raising
   EE"*, which the predeclaration named in advance as the outcome it would be most tempted to
   reframe (`PREDECLARATION:46-62`).
3. **Contradicted on its own stated mechanism.** On the representation axes the sibling's mechanism
   is claimed to act on, **z works here too**, and the width control confirms it is not capacity.

**[V]** Standing caveat on all of (2) and (3): **500 unconverged constant-rate gradient steps on
surrogate labels**. `PREDECLARATION:9-14` records that `LR-CONVERGENCE-SWEEP-2026-09-10.md` found
**21 of 21 route × learning-rate cells fail a convergence rule fixed before the sweep**, and that
none of the three current lr literals is admissible. Surrogate-label argmax disagreement with exact
labels: C1 51.68%, C2 55.27%, C3 81.82% (`Z-VIEW-SCORING:268`).

**[D] This is the same class of defect as the sibling's confound 1 — a mis-tuned/under-run
optimiser underneath the z comparison — except that here it is *known and un-fixed at measurement
time*, whereas in the sibling it was found afterwards.** That single fact is what rules out the
"(A): fixed here, so no longer needed" story.

---

## Q5 — The mechanism hypothesis

> *z-scoring a reward head per batch destroys the head's absolute scale, so the agent optimises
> rank-within-batch rather than the physical quantity; where the objective is a ratio of sums
> (pooled EE), that scale is exactly what carries the objective.*

**Verdict: CONTRADICTED by the code in both projects, on three independent counts. Do not use it.**

**[V] It is not a reward head.** Both projects z-score the **state/observation** features
(`encoding.py:62-107`, `representation.py:132-169`, `04-zscore.md:14-26`; and here, the Q1/Q2/C3
member feature blocks). Neither the sibling's `concat` form nor this project's z view touches r1,
r2, r3, the TD target, or the Q values. The sibling's *reward*-side normaliser is PopArt, a
separately named and separately failed mechanism (`popart_online.py:40-129`), and this project has
no such surface at all (`trainer_spec.py:107,113-117`).

**[V] It is not per batch.** The population is **the users co-present at one step**
(`encoding.py:79-81`, `representation.py:135-137,166`; `04-zscore.md:24` 「`μ`、`σ` 沿 `axis=0` =
user 軸 reduce。每一步重算」). A batch statistic and a same-step cross-user statistic are different
objects; the latter is why the sibling flags it as *smuggled coordination*
(`04-zscore.md:106-130`), which is the real live caveat and is not the caveat the hypothesis names.

**[V] The absolute scale is not destroyed.** Both are `[raw ‖ z]` concatenations, not replacements.
The sibling proves raw-block recoverability byte-for-byte (`representation.py:269-274`); this
project's z view likewise appends (`Z-VIEW-SCORING:53,137`, Q1 `15 -> 30`). The unnormalised
physical magnitudes remain in the first half of every input vector.

**[D] And the objective link does not hold either.** The sibling's endpoint is *itself* a mean of
ratios (Q2), so "the objective is a ratio of sums" is false of the sibling's measurement; and in
this project the z block feeds supervised heads whose targets are surrogate route labels, not a
pooled-EE gradient.

**[I]** A *weaker* claim is testable and untested: whether appending a per-step cross-user
standardised block shifts the heads toward *within-population relative* structure at the expense of
*absolute-level* structure. `Z-VIEW-SCORING:148` offers exactly that as a candidate reading of where
the C1 reduction comes from and immediately labels it un-tested: *"I did not test this; no
head-attribution experiment was run."* `RAW-DUP-CONTROL:182` names the arm that would separate the
two readings (a z-only view at original width, or a random-projection block of matched rank) and
records: **"That arm was not run and is not claimed."**

---

## Q6 — Is collapse actually absent here? (measured, not assumed)

**Yes, measured, for both the current learner and the frozen MODQN checkpoint. Both sit next to
their zero-learning controls, not next to the sibling's one-beam pathology.**

**[V] Frozen MODQN checkpoint** —
`.scratch/reviews/evidence-bundle-2026-09-11/reports/MODQN-COLLAPSE-2026-09-10.md:1`. Authenticated
112-state / 28-action three-Q-network checkpoint, weights `(0.5, 0.3, 0.2)`, lowest-index masked
argmax; native V0.23 TRAIN split, 10 frozen P6 scenarios × 10 steps × 100 users = 100 physical
profiles, 10,000 selections:

| | MODQN | zero-learning myopic control |
|---|---:|---:|
| `modal_frac` (largest beam occupancy / 100) | **0.04170** | 0.05010 |
| active physical beams / satellites | **68.70 / 7.47** | 63.32 / 6.47 |
| `argmax_distinct` (local slots) | 0.07470 | 0.13920 |

**[V]** `:7-9` — worst observed largest-beam occupancy **7 of 100**; every profile selected **56–82
distinct physical beams**; no profile had a no-op selection. Conclusion as written: *"this
authenticated MODQN policy is **not** in the sibling project's physical shared-Q + argmax collapsed
regime."* The qualification is recorded honestly: on *local slot numbers* it does concentrate
(2–13 of 28 slots; slots 7 and 21 take 69.18% of selections), but a slot is user-relative and maps
per-user to a different physical `(NORAD, cell)`.

**[V] Current learner** —
`.scratch/reviews/evidence-bundle-2026-09-11/reports/BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md:1` and
its table. 11 epoch-500 q1-v2 seeds × 22 TRAIN anchors, learned `a0` = masked `argmax(Q1+Q2)` per
user before joint repair, 242 profiles:

| profile | `modal_frac` [range] | active beams [range] | active sats |
|---|---:|---:|---:|
| Learned `a0`, q1-v2 | **0.05236** [0.02, 0.13] | **49.07** [24, 66] | 5.79 |
| Zero-learning myopic | 0.05500 [0.03, 0.08] | 51.68 [38, 73] | 5.18 |
| Geometric nearest-eligible | 0.05000 | 43.77 | 3.36 |
| Learned `a0`, q1-v1 (sensitivity) | 0.06864 [0.01, 0.13] | 41.28 [1, 60] | 5.57 |

**[D]** Both diagnostics are **physical-beam** diagnostics and both land on top of a zero-learning
control. Compare the sibling's collapse signature (`COLLAPSE-ROOT-CAUSE-IS-LR:75-79`): at `lr=0.01`
the sibling produced `min_cov = 0.167` / `served = 0.297` **bit-identical across seeds and across a
decode flip**, and identical EE `150.13` on all three seeds — *"structural homogenization, not noisy
divergence."* Nothing of that shape appears in either table above.

### ⚠ Both measurements fail this project's own collapse-reporting gate

**[V]** This project implements the four-indicator rule in source:
`src/mcrl/runtime/collapse_metrics.py:1-6` — *"G-3: 任何『是否崩潰』的判定，必須同時報告
`active_beam_count`、`argmax_agreement`、`q_margin`、`q_entropy`，且 `q_margin` 必須以 Q 值域正規化後
呈現。**缺任一項即不通過**"* (*any collapse verdict must report all four; `q_margin` must be
normalised by the Q range; **missing any one fails**). `REQUIRED_G3_FIELDS` at `:40-45`;
`assert_g3_complete` refuses a partial report. It is wired into training at
`src/mcrl/algorithms/modqn.py:1199-1215`.

**[V]** The module's docstring (`collapse_metrics.py:7-20`) states exactly why, using the sibling's
own ablation: dropping lr `0.01 → 0.001` moved active beams `1.00 → 4.39` and argmax agreement
`1.000 → 0.484` — *"which reads as 'the collapse was fixed'"* — while `q_margin` fell
`0.0057 → 0.00055`. Headline quoted verbatim in the source: **"escape is argmax-dispersion under
near-flat Q, not a discriminative Q."** And: *"the first two indicators alone say 'not collapsed'
about a policy whose Q values are nearly tied."*

**[V] Neither of the two reports above contains `q_margin` or `q_entropy`** — grep over
`MODQN-COLLAPSE-2026-09-10.md` and `BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md` returns **0 hits** for
either field, and neither mentions G-3.

**[D]** So the Q6 answer must be stated precisely: **physical-allocation collapse is measured absent
on two of the four indicators this project's own gate requires**, and the two that are missing are
exactly the pair the gate exists to catch — the pair that distinguishes "the policy chose" from "the
policy is picking between indistinguishable options". `BASE-COLLAPSE-DIAGNOSIS:5` is itself careful
about this: *"I do not turn that comparison into a binary 'collapsed/not collapsed' label."*
By this project's own rule, **no binary collapse verdict is currently licensed here in either
direction.** This does not overturn the measurements — the physical-beam numbers are real and are
nowhere near the sibling's one-beam attractor — but it does mean "collapse is absent here" is a
two-of-four report, not a passed gate.

**[I] And "collapse" is not one thing — the narrow version is *not* absent.** The C2 effective
rank at the four group-departure anchors is 11–13 of 50 hidden units without z and 37 with it
(`RAW-DUP-CONTROL:122-131`), and the deployed-head row collinearity sits 0.208 above its measured
Gaussian floor without z. That is a real, measured degeneracy in this project of the same *family*
the sibling's z-score was aimed at — at the head-representation level rather than the
physical-allocation level. **Physical collapse is measured absent. Representation degeneracy is
measured present.**

---

## Verdict

**Primarily (C), with a genuine but small residual of (B). (A) is false as posed.**

**(C) — the premise is largely false at the size it is believed.** The evidence that z-score
"helped" in the sibling is, in the sibling's own records:

- the 146.6 → 357.1 landmark — flagged **CROSS-CONDITION and forbidden to cite as matched** in four
  places in that repo, and later attributed overwhelmingly to `lr = 0.01`
  (`fulldqfd_OFF_raw.yaml:7`; `COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md:26-46,70-72`);
- the `concat − width` = +120.88 headline — **formally retracted**, broken control
  (`ZSCORE-3WAY-FINDINGS-2026-07-17.md:17-26,60`);
- the only clean matched contrast, `concat − raw` = **+27.88, 95% CI [−20.86, +76.63]**, 5/6, below
  its own MDE ≈ 55, and differentially converged in the preferred direction (`:36-42,61-64,73-84`).

**And it was never pooled-EE evidence.** `argmax_EE` is a mean over episodes of a mean over steps of
a mean over users of `R_u/P_system` (`score_argmax_endpoint.py:105,118,120-121`;
`family_b_recalibration.py:120-132`) — a mean of ratios, which this project's rules do not accept as
EE evidence.

**(B) — a real, regime-conditional residual survives, and it has a measured physical reason.** One
matched, single-variable, healthy-lr, 6-seed, 6/6-sign z-on/off contrast does stand: **`L2 − L1` =
+56.54 Mbits/J** (`COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md:95`, config pair verified by diff) — and
this repo's own writing rules already characterise it correctly: it *pushes a healthy baseline up;
it does not rescue a collapsed one* (`WRITING-RULES.md:283`). The regime is measurably different in
the two projects: the sibling's physical one-beam signature (`min_cov 0.167` / `served 0.297`,
seed-identical EE 150.13) has **no counterpart here** (Q6), and — the strongest part — this
project's physics measures **`d(EE)/d(active) = −425,009.885 bit/J` per added mean-active beam**
with no sign flip over 8.00–98.25 beams (`CROWDING-COST-2026-09-10.md:1`). The sibling's z-score is
valued there *because it spreads*; spreading is EE-negative here. So (B) is right about direction
and mechanism — it is just far smaller than the 2.4× headline suggests, and the sibling's collapse
itself turned out to be a learning-rate artifact rather than a property of the architecture.

**(A) — rejected as posed.** The sibling *did* have a defect that z-score partially masked, but the
defect was **`lr = 0.01`**, not a physics, mask or reward bug — and it is **not fixed here**. This
project's own pre-sweep rule found **21 of 21 route × learning-rate cells inadmissible** and all
three current lr literals non-admissible, and every z number here is from **500 unconverged
gradient steps on surrogate labels with 52–82% argmax disagreement**
(`PREDECLARATION:9-14`; `Z-VIEW-SCORING:268`). The "we repaired it, so we no longer need z" branch
of (A) has no support; if anything this project is currently *in* the sibling's confounded regime,
not out of it.

**On "harmful here":** not measured as EE harm at all. What is measured is that the z view **shrinks
the `FULL − DROP_C1` marginal at 16/16 paired seeds** and leaves C2/C3 indistinguishable
(`Z-VIEW-SCORING:126-144`), which closed it (`V025-CONTROLLER-NOTE-C1-C2-COMPETE-2026-09-11.md:18`).
Cross-panel EE-level comparison is explicitly disallowed by the same report. In the opposite
direction, the z view is measured to **repair** row collinearity (0.482 → 0.360 against a 0.2735
floor) and C2 effective rank (0.454 → 0.903 of width), with a width-matched `raw_dup` control that
moves neither axis (`RAW-DUP-CONTROL:70-74,114-118,139-141`). **z is not harmful here; it is
inconvenient here** — it removes the ablation contrast the three-Catfish claim rests on, which is
the outcome the controller named in advance as the most tempting one to reframe
(`PREDECLARATION:46-62`).

### The single sentence that decides it

`ZSCORE-3WAY-FINDINGS-2026-07-17.md:24-26` — the sibling's own retraction of its own headline:
*"The `+120.88` is carried by a broken control. Against the honest baseline the z-score is **not
separated from zero at n=6**."*

And the sentence that shows this project already knew it, in
`WRITING-RULES.md:288`: **「z-score 有幫助但擋不住崩；lr 才是控制變數」.**

### Named missing measurements

0. **MODQNZ's numbers are not on this filesystem.** The one experiment designed to answer this
   question directly — z in-place and z-concat vs raw and raw_dup on this project's own frozen
   MODQN checkpoint — is declared *"decisive pair done; z line closed"*
   (`V025-CONTROLLER-DECLARATION-TRAINING-PAUSE-2026-09-11.md:11`) while its log here stops at
   episode 800/9000 and its report (`/home/sat/mcrl-v025-mqz-ws/MODQN-Z-INTERVENTION-2026-09-10.md`)
   is off-machine. **Retrieve this before treating the z line as closed** — it may already
   answer the owner's question outright, or may not support the closure.
1. **`z_perm` was never run** in this project — the one predeclared control that separates
   "cross-user coupling" from "having a normalised block at all"
   (`PREDECLARATION:28-45`; grep confirms no report exists).
2. **No `raw_dup` scoring panel exists**, so the width control has **no route marginal** here
   (`RAW-DUP-CONTROL:190-195`) — and the report warns the scorer would silently accept `raw_dup`
   checkpoints against the z panel and emit meaningless numbers.
3. **No converged comparison exists in either project.** The sibling's settling run (all arms
   converged + n to clear MDE ≈ 55) was deferred and then invalidated by the r3 encoder change
   (`ZSCORE-3WAY-FINDINGS:100-106`). This project's z comparison is at 500 steps with 21/21 lr cells
   inadmissible.
4. **This project has never measured the sibling's own trigger statistic** — the common-mode screen
   `R` (`04-zscore.md:140-157`; sibling value `0.33632`, itself "IN BETWEEN"). The claim that the
   common-mode regime is absent here rests on F3's absence-of-symptom, not on `R`.
5. **The abl9k `L2 − L1` = +56.54 pair was not audited for the differential-convergence confound**
   that killed the wave-E contrast. It is currently the sibling's only surviving matched positive,
   and its one known vulnerability is unchecked.
6. **The head-attribution experiment** that would say whether the C1-marginal reduction is z moving
   signal from C1 into C2/C3 inputs, or z destroying it, was not run
   (`Z-VIEW-SCORING:148`; `RAW-DUP-CONTROL:182`).
7. **`q_margin` and `q_entropy` are absent from both collapse diagnostics**, so this project's own
   G-3 gate (`src/mcrl/runtime/collapse_metrics.py:1-6,40-45`) is not passed in either direction.
   These are cheap to add on existing checkpoints and are the two indicators that distinguish
   "not collapsed" from "argmax dispersion under near-flat Q".

### Evidence classification

- **[V] Verified by me, reading the cited file at the cited line:** every sibling code and config
  citation (encoding.py, representation.py, popart_online.py, score_argmax_endpoint.py,
  family_b_recalibration.py, the four CROSS-CONDITION flags, the `abl9k_baseline*` diff), every
  sibling document quotation (04-zscore.md, ZSCORE-3WAY-FINDINGS, COLLAPSE-ROOT-CAUSE-IS-LR,
  FULLDQFD-GROUPD-PREREG, WAVE-E-AMENDMENT), this project's `grep` for z-score in `src/` (0 hits)
  and `trainer_spec.py`, and every number quoted from Z-VIEW-SCORING, RAW-DUP-CONTROL,
  MODQN-COLLAPSE, BASE-COLLAPSE-DIAGNOSIS, SIBLING-CONCEPT-TRANSFER, the predeclaration and the
  C1-C2-COMPETE note.
  Also verified by me: `WRITING-RULES.md:270-290` (the user override and its five bullets),
  `src/mcrl/runtime/collapse_metrics.py:1-45`, the 0-hit grep for `q_margin`/`q_entropy` in both
  collapse reports, `CROWDING-COST-2026-09-10.md:1,134,140`,
  `.scratch/server-sync-20260909/audits/out-ZSCORE.md:7-11`, `AGENT-REGISTRY.md:55`, and
  `V025-CONTROLLER-DECLARATION-TRAINING-PAUSE-2026-09-11.md:11`.
- **[R] Relayed, not re-derived:** the contents of the server workspaces those four reports were
  produced in (`/home/sat/mcrl-v025-*-ws`) — I read the reports, not the artefacts. Their internal
  claims of scorer digests, sidecar verification and receipt equality are taken as written. Also
  relayed: the MODQNZ arm design (I verified only that the declaration and registry say it ran and
  that its numbers are absent here), and the `out-ZSCORE.md` EE levels, which are a completion
  summary of an off-machine report.
- **Search coverage note:** two independent record searches (one per repo) were run in parallel with
  my own reading. Every claim either side surfaced that I judged load-bearing was re-verified by me
  against the primary file before being written above; nothing is included on a search agent's
  say-so alone.
- **[D] Derived:** the arithmetic and the reading of what the confounds imply.
- **[I] Inferred, flagged in place:** the abl9k convergence question, the "relative vs absolute
  structure" weak mechanism, and the reading that physical collapse and representation degeneracy
  are different things.
