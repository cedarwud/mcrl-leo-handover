**C1/C2/C3 are not the catfish mechanism — they are a three-term decomposition of the scalar physics objective `F = B − η_ref·E − Φ` plus the source-selection rules that build training rows for it, sharing none of catfish's four mechanisms (EE-threshold stratification, asymmetric discounts, periodic 70/30 intervention, adaptive competitive reward) nor its Phase-1 solver seeding; and the authenticated pre-Catfish MODQN checkpoint `e6b063ef…1b09c28b` was trained *after* the throughput→EE switch — its own embedded `trainer_config` records `r1_reward_label = "system-energy-efficiency"` with provenance `"paper eq. (3.25): r1 = sum_{s,v} x * eta"`, and the hash-bound source tree that produced it already carries PATCH P-20, which deleted the throughput r1 mode entirely.**

Date: 2026-09-11. Fact-finding only; no training and no new experiment was run. Every file cited below I opened myself unless the line explicitly says otherwise. Evidence class is marked per claim: **[V]** verified by reading the source / running a hash or a read-only load, **[D]** derived on paper from quoted values, **[I]** inferred.

Two code trees are involved and are never mixed:

- **sibling** = `/home/u24/papers/modqn-paper-reproduction` (local).
- **current** = `/home/u24/papers/mcrl-leo-handover` (local) plus the server workspaces `/home/sat/mcrl-v025-*` and the byte-authenticated archive `/home/sat/mcrl-leo-handover-20260825-corrected`.

---

## 1. What the catfish mechanism is, precisely

Source: the sibling's explainer package, `/home/u24/papers/modqn-paper-reproduction/docs/catfish-explainer-package/`, which states it quotes `archive/catfish-route/catfish/thesis.pdf` page by page. I read `00-README-START-HERE.md`, `02-collapse-mechanism.md`, `07-true-catfish-formulas.md` and `99-open-questions-and-status.md` in full. **[V]** for what the package says; the thesis PDF itself I did not open, so every "the paper says" below is the package's quotation of it, at one remove.

### 1.1 Three phases

`07-true-catfish-formulas.md:15-23` gives the paper's own division (p33):

| Phase | Name | Content |
|---|---|---|
| §4.1 | Catfish-effect-based data preparation | external solver pre-generates high-EE samples ⟹ seeds the catfish replay memory |
| §4.2 | Catfish-effect-based DRL training | dual agent + three mechanisms + two training modes |
| §4.3 | Catfish-effect-based DRL optimization of EE | inference with the trained CDRL |

### 1.2 The three core mechanisms, verbatim

`07-true-catfish-formulas.md:25-28` quotes the paper (p13):

> *"all experiences are separated based on an **energy efficiency (EE) threshold**, the two DRL agents are assigned **different discount factors** to focus on distinct objectives, and the catfish agent is provided [with an adaptive competitive reward]"*

### 1.3 What the specialist produces and how it seeds replay (Phase-1)

`07-true-catfish-formulas.md:34-53`, quoting thesis p35, three steps:

1. **Enumerate** with a **DFT codebook**: RIS phase candidates `Φ̃_RIS = {φ̃_1,…,φ̃_2N}` and analog beamforming candidates `F̃^RF`.
2. **Solve**: for each candidate, compute the digital beamformer by **WMMSE** (paper's ref [22]).
3. **Select**: take the candidate with maximum EE —

   `(φ*, F^RF*, w^BB*) = argmax over (φ̃ ∈ Φ̃_RIS, F̃ ∈ F̃^RF) of EE(φ̃, F̃, w^BB_WMMSE(φ̃, F̃))`

The resulting "exemplary solution cases" are, verbatim (`07:50`):

> *"stored into the **catfish replay memory** … serving as **the INITIAL experience replay data for CDRL**."*

The package's own reading (`07:52-53`): *"catfish【有】外部專家，而且它是一個【求解器】（不是「另一個爛 agent」）"* and *"這是一個【枚舉 → 求解 → 取最大】的【搜尋】，不是一步貪婪規則"*. The external source is to be called **SPECIALIST**, never "teacher" (`00:26-28`).

### 1.4 M1 — separation by EE threshold

`07-true-catfish-formulas.md:73-83`, quoting the paper (Fig 4.7, p42-43):

> *"Experiences with **higher EE** are stored in the **catfish** replay memory, while those with **moderate EE** are stored in the **main** replay memory."*
> *"If `EE ≥ EE_high`, the dataset is stored in the catfish replay memory as **high-value data**."*

i.e. `(s,a,r,s') → D^CF if EE(s,a) ≥ EE_high, else D^M`.

### 1.5 M2 — the two agents' discount factors

`07:90-99`: `γ^M ≤ γ^CF`. The main agent gets the **small** γ and *"focuses on **short-term** demands to **accelerate convergence**"*; the catfish agent gets the **large** γ and *"emphasizes **long-term** objectives"*. Tied to M1: *"based on the prior experience stratification, **superior experiences are assigned a larger discount factor** for the catfish agent's tasks, while ordinary experiences receive a smaller discount factor."*

### 1.6 ACRM — the adaptive competitive reward

`07:103-118`, eqs (4.8)/(4.9):

```
r^C = r + η · r^S            (4.8)
r^S_t = r^CF_t − r^M_t       (4.9)
```

with `r` = *"the original EE reward from the environment"*, `η` = *"the coefficient controlling the weight of this reward. When **η → 0**, the model degrades to the original reward model."*, `r^M_t` / `r^CF_t` = what the main / catfish agent achieved **on the same task**. Semantics, verbatim:

> *"The **greater the lead** of the catfish agent over the main agent on the same task, **the larger the additional reward** received by the catfish agent. Conversely, the catfish agent is **penalized more when trailing behind**, reinforcing the **competitive dynamics**."*

The package notes the paper itself attributes ACRM to SASR (Shen et al. [24]) (`07:120-121`).

### 1.7 M3 — the two training modes

`07:132-148`, quoting Figs 4.5/4.6:

- **(a) ordinary training mode**: *"the main agent and catfish agent each have **independent** experience replay memories, discount factors, and reward mechanisms, **training independently**."*
- **(b) intervention training mode**: *"a portion of the **high EE experiences collected by the catfish agent** is sampled and **mixed into the main agent's training batches**."*
  Verbatim on the mix: *"In the mixed batch `S_mix = S^M ∪ S^CF`, **70% of the samples are drawn from the main replay memory `S^M`**, and **30% from the catfish replay memory `S^CF`**"*. The trigger is a **randomized** interval ("randomized periodic intervention").

`07:150-151` states the direction of the update plainly: *"更新的是【main agent】。catfish 只是「經驗的來源 + 過濾器」"* — the intervention updates the **main** agent; catfish is a source and filter.

### 1.8 What is deployed at inference

`00-README-START-HERE.md:32`: **"部署時沒有任何協調器"** — no coordinator at deployment; *"❌ **禁止** delegation（部署時不准有實體「替 user 選動作」）"*. Combined with §4.3 (`07:23`), deployment is the trained CDRL policy alone. In the sibling's discrete port, the deployed object is the pure per-user argmax over the shared Q (`00:99-104`, below).

### 1.9 Faithfulness of the sibling's own code (its disclosure, spot-checked by me)

`07:177-274` is the sibling's honest-disclosure table. I verified the load-bearing entries against its code:

- M1 is a **rolling quantile**, not the paper's absolute `EE_high`: `q_hi = float(np.quantile(window_arr, cfg.strat_threshold_quantile))` at `src/modqn_paper_reproduction/catfish_faithful_familyb/stratification.py:94`; the module docstring at `:11` states *"`to_catfish` iff `eta >= quantile(window, strat_threshold_quantile)`"*. **[V]**
- M2 is wired: `GAMMA_MAIN = 0.9` / `GAMMA_CATFISH = 0.99` at `catfish_faithful_familyb/presets.py:27-28`. **[V]** The package discloses it as structurally inert in that env (10-step episodes, no accumulating state ⟹ `γ·Q(s')` is action-independent), `07:205-217` — I did not re-verify the inertness claim.
- M3 is wired at the paper's ratio: `intervention_ratio_catfish=0.30` at `presets.py:39` and `:55`. **[V]**
- **Phase-1 does not exist.** `07:256-264` reports a three-surface grep with no hits. I re-ran it myself: `grep -rniE 'wmmse|dft_codebook|seed_buffer|phase1'` over `catfish_faithful_familyb/`, `route_b_factorial/faithful_catfish_trainer.py` and `runtime/catfish_replay.py` returns **0 hits**. **[V]**
- **Correction to the package.** `07:249` asserts ACRM is *"False（預設 OFF），而且全 repo 沒有任何 config 打開它"* — no config anywhere turns it on. That second half is **false as written**: `catfish_faithful_familyb/presets.py:110-120` defines `acrm_full()` with `acrm_enabled=True, acrm_eta_weight=1.0`, docstring *"COMPLETE 4-mechanism faithful catfish … This is the full canonical thesis algorithm"*, and `presets.py:138-150` defines `acrm_annealed()` likewise. **[V]** What I did **not** establish is whether any *run* ever used those presets; the default presets `faithful_full`-family do set `acrm_enabled=False` (`presets.py:42`, `:58`). **[V]** So the correct statement is "ACRM-enabling presets exist; whether they were ever executed is unestablished here", not "no config turns it on".

---

## 2. The declared endpoint for "catfish works"

**Confirmed, with one important addition the brief's one-liner omits.** `00-README-START-HERE.md:99-104` states it as the single number:

> ### **catfish ON vs catfish OFF ⟹ `argmax-EE` 有沒有上升？**
>
> `argmax-EE` = **純 per-user agent**：100 個 user 各自跑 `argmax_a Q_w(obs_u, a)`。
> **沒有 decode、沒有協調器。** 不動這個數字的任務就不是這條線的工作。

So the comparison is **ON vs OFF of catfish, same everything else**, and the metric is **`argmax-EE`**: closed-loop EE of the *pure per-user* policy — every one of 100 users independently takes `argmax_a Q_w(obs_u, a)`, **no decode, no coordinator**. The measurement harness is fixed (`99:81-84`): `SEED = 20260626`, `N_EP = 48`, `t0 = (ep/48)·86400 s`, `step_rng = 12345`, `EE = family_b_eta_r1 / 1e6` in Mbit/s/W. **[V]**

**The addition:** ON-vs-OFF alone is explicitly *not* sufficient for a claim of merit. `00:134-136` states the frozen adjudication rule:

> ### **凍結的裁決規則**：一支 arm **贏過地板**，**若且唯若它 PARETO-DOMINATE 同契約的 BC** —— **`argmax_EE ≥ BC_EE` 【且】 `min_cov ≥ BC_cov`。**

and `99:139` lists "taking catfish-OFF as the only control" under the motivated-reasoning red lines. The endpoint is therefore two-part: (i) **the mechanism question** is ON vs OFF on `argmax-EE`; (ii) **the merit question** additionally requires two-axis Pareto dominance over the same-contract zero-learning BC k-NN floor (live-z `475.26 @ min_cov 0.723`; raw `421.40 @ 0.527`; frozen-z `427.29 @ 0.481` — `99:72-74`, `99:96`), and cross-contract comparison is forbidden. **[V]**

---

## 3. The four confounds, and whether each is present in the current project

`99-open-questions-and-status.md:172-173` names them in one sentence:

> *"過去所有 negative 的 arm 都帶著 confound（**協調 decode · margin 尺度 · `γ₁=0.9` · 弱專家 pool**）"*

and `07:282-284` names the same four by the settings that removed them in the sibling's later wave (`decode: argmax` · `γ = [0.0, 0.9, 0.9]` · `scale_mode: qw_sd` or margin OFF · `F-mean` specialist pool). **[V]**

| # | Confound (sibling) | Present in the current project? |
|---|---|---|
| 1 | **Coordinated decode** — an auction/corrected decoder between Q and the joint action, which can manufacture spread out of bad Q values and hide the treatment | **Present by design, but as the object of study rather than a hidden nuisance.** The current project's deployed S3 *is* a coordinator optimising `C1 + C2 + Ψ̂` over a bounded catalogue (`V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md`, C2 line). The uncoordinated object is separately available and separately measured: `BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md` measures "the raw independent `a0`, before joint-conflict repair", citing `deployment.py:101`/`:112` for the per-user independent sum and `:125` for repair as "a later operation". I read `deployment.py:112-122` — `independent_two_head_profile` builds each user's score as `model.score("C1", q1) + model.score("C2", q2)` and takes `masked_argmax`, with no cross-user term. **[V]** So the current project can measure the pure per-user endpoint the sibling's endpoint demands; it does not have to run the coordinator to do it. |
| 2 | **Margin scale** — DQfD's large-margin supervised term dominating TD by orders of magnitude | **Absent.** There is no supervised margin term in the stage-C learner. Its update is stated in code as *"Pairwise fixed-target regression with a reference-zero gauge. No reward, next state, target network, discount, or bootstrap exists."* (`/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/learner.py:279-280`). **[V]** The contract wording matches: C1 says the heads are fitted "by pairwise zero-bootstrap regression … This estimates a supervised surrogate of the declared targets, **not a Bellman value**". **[V]** |
| 3 | **`γ₁ = 0.9`** — the first objective's discount set such that the mechanism could not act | **Cannot exist in stage C; fixed at 0.9 in the MODQN baseline.** Stage C has *no discount at all* (same `learner.py:279-280` quote). The frozen MODQN baseline has a single `discount_factor: 0.9` shared by all three heads (checkpoint `trainer_config`, §5 below; `src/mcrl/algorithms/modqn.py:550` uses `cfg.discount_factor` as the one γ). **[V]** Note the direction of this: the confound is gone because the mechanism it would confound (M2, asymmetric γ) has nothing to attach to. |
| 4 | **Weak specialist pool** — the demonstration source being a one-step greedy heuristic (`F-mean`) rather than the paper's enumerate→solve→argmax search | **A strong specialist exists in code but is not operationally available at the production budget.** `S_UNI` is defined in the contract (C2) as "iterated exact unilateral improvement to a local optimum … termination certificate reported", implemented at `/home/sat/mcrl-v025-coalgen-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:1831`, with only `NO_IMPROVING_LEGAL_UNILATERAL` counting as a certificate (`:1921`) and a 10-second production budget after which it returns BASE as `DEADLINE_FALLBACK_BASE` (`:162`, `:1873`). The BASE-COLLAPSE diagnosis reports that with **600 seconds** allowed — 60× production — and exact batch widths 256/128/64/16/8, *"even anchor 0 did not reach the certificate"*, so no S_UNI panel exists. **[V, as that report's verified-by-running-code section; I did not re-run it, per the no-new-experiment constraint.]** An exact `S0` (the same selector with exact `Ψ_A` substituted for the learned `Ψ̂`) is also declared (contract C2). **[V]** |

### 3.1 The masking claim, and what the collapse measurements do to it

`02-collapse-mechanism.md:196-203` lists three repairs — **(A) fix decode** (joint optimiser/auction), **(B) fix inputs** (z-score), **(C) fix training** (catfish/DQfD injection) — and closes with:

> ⚠ **(A) 與 (C) 會互相遮蔽** —— 這正是為什麼過去測不出 catfish 的效果。

The mechanism story that makes (C) worth running is in `02:127-137`: collapse is a **Nash fixed point** that ε-greedy cannot escape, because escaping requires a coordinated simultaneous move by many users (`k_cap` is a *ranking* cut, so a lone defector loses the demand ranking and gets `r1 = 0`); catfish injection is supposed to make the value of the good fixed point *visible* to TD. **[V]** The package tags this as `hypothesis`, not established (`02:138`, `99:37`).

**The current project has measured that the premise does not hold here.** Two development-only diagnoses, both read by me in full:

- `/home/sat/mcrl-v025-probe-ws/BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md`, headline: *"Across 11 epoch-500 v2 seeds × 22 TRAIN anchors, learned `a0` has mean `modal_frac=0.05236`, `active=49.07 beams / 5.79 satellites`, and `argmax_distinct=0.49070`; the zero-learning myopic control has `0.05500`, `51.68 / 5.18`, and `0.51682`"*, against the sibling's collapsed regime of `argmax_distinct = 0.01`, one active action, `modal_frac ≈ 1`. That report is careful: *"I do not turn that comparison into a binary 'collapsed/not collapsed' label"*, and it flags a separate concentration symptom (up to 74 of 100 users selecting null at one anchor). **[V]**
- `/home/sat/mcrl-v025-mqcollapse-ws/MODQN-COLLAPSE-2026-09-10.md`, headline: *"MODQN is not physically collapsed … `modal_frac=0.04170`, `active=68.70` physical beams / `7.47` satellites … versus the zero-learning myopic control's `0.05010`, `63.32 / 6.47`"*, and in the body: *"**this authenticated MODQN policy is not in the sibling project's physical shared-Q + argmax collapsed regime**"*. Its qualification is that MODQN is concentrated in **local action-slot indices** (slots 7 and 21 hold 69.18% of selections) while being physically spread, because a slot is user-relative. **[V]** That run used the same frozen checkpoint as §5 and recorded identical before/after SHA-256 `e6b063ef…`. **[V]**

**Implication for testability here [I, but tightly bounded by the two quotes above]:** the pathology catfish was designed to remove — all users collapsing onto one beam at a bad Nash fixed point — is **not the current project's failure mode**, on either the learned V0.25 proposal or the authenticated V0.23 MODQN baseline. Two consequences follow.

1. The (A)/(C) masking problem is **moot here, for the wrong reason**: (A) and (C) mask each other only when there is a collapse for both to repair. There isn't one, so removing the coordinator would not reveal a suppressed catfish effect; it would reveal a policy that is already spread.
2. An ON/OFF catfish test in the current project would therefore **not be a test of the sibling's declared endpoint question**. The sibling's `argmax-EE` endpoint is sharp precisely because the OFF arm sits at `argmax_distinct = 0.01` and the headroom to the specialist is enormous (146.6 → 636.05, `00:106-117`). Here the OFF arm is already at `argmax_distinct ≈ 0.49` (V0.25) / physically spread with `modal_frac ≈ 0.042` (MODQN), and the zero-learning myopic control does **not** uniformly dominate it (MODQN report: myopic is *more* diverse in local slots but *more* concentrated by physical modal fraction and uses fewer beams). Whatever a catfish arm here would measure, it would not be "does injection escape collapse"; the effect size argument that motivated the mechanism does not transfer, and a new endpoint would have to be declared from this project's own physics. Note also the measured concentration statistics are **development-panel** quantities, explicitly not EE claims — neither report extracted any EE (MODQN report, "Explicit exclusions").

---

## 4. Are C1/C2/C3 the catfish mechanism?

**No. They are a different mechanism carrying an adjacent name — and not even a superset: the intersection with catfish's mechanism set is empty.** Stated plainly, as requested.

### 4.1 What C1/C2/C3 actually are

From `/home/sat/mcrl-v025-retrain-ws/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md`, item **B4**, verbatim:

> **B4. F and Φ:** F(a) = B(a) − η_ref·E(a) − Φ(a), with Φ the signed handover/QoS preference in κ units charged exactly once inside F. Unilateral increments dᵢ = F(aᵢ, a⁰₋ᵢ) − F(a⁰); interaction residual Ψ_A = F(a_A, a⁰₋A) − F(a⁰) − Σᵢ∈A dᵢ. **C1(config) = Σᵢ∈A dᵢ; C3(config) = Ψ_A; identity C1 + C3 = F(a_A) − F(a⁰) exactly** (KAT) … C2 = declared continuation value excluding the immediate term (three offsets, −κ per absorbing lost offset).

So:

- **C1** = the sum of **unilateral increments** of a scalar physics objective under single-user deviations from the reference profile `a⁰`.
- **C2** = the **continuation value** of that same score over a declared forecast horizon.
- **C3** = the **interaction residual** `Ψ_A` — exactly the part of a coalition's joint effect that the additive C1 decomposition cannot express.

These are **terms of an algebraic decomposition of one objective**, tied by an exact identity `C1 + C3 = F(a_A) − F(a⁰)`. They are then also the names of three **heads** (C1, C2, C3) and of three **source-construction rules** that pick which rows the heads train on. The deployed use is a selection score: `deployment.py:112-122` sums `model.score("C1", q1) + model.score("C2", q2)` per user, and contract C2 says the coordinator `S3` "optimises the **complete** score C1 + C2 + Ψ̂ over 𝒞". **[V]**

The current project's own code says the same in its module headers. `src/mcrl/runtime/ee_axis_source_selectors.py:3-7`:

> *"The C3 Catfish is a **source construction** rule. It chooses a sealed anchor, focal user, and physical alternatives from information that was committed in the previous slot; it does not evaluate a candidate branch and it does not look at a target."*

and `:19-20`: *"selecting an action because its `zeta_3` is large would make the source an outcome filter rather than a Catfish."* `src/mcrl/runtime/ee_axis_c1_selector.py:3-8` similarly: *"The C1 Catfish has two deliberately separate pieces of lineage: EXP supplies **where to look** … ACRM supplies **how to compare** …"*, and `:57-58` defines `C1_ACRM_PAIR_RULE` with the comment **"ACRM is pair construction, not an additive reward or selector score."** **[V]**

That last line is the whole answer in miniature: the current project has kept catfish's vocabulary (`multi-catfish-mcrl-…` schema strings appear 185 times under `src/`, "Catfish", "ACRM") and **redefined every term**. ACRM in the paper is `r^C = r + η(r^CF − r^M)`, an additive shaped reward for a second learning agent. ACRM here is a rule for *pairing* a candidate action against a frozen reference action when constructing a training row, with an explicit disclaimer that it is not a reward.

### 4.2 Mechanism-by-mechanism comparison

| Catfish component (§1) | Present in the current project's stage-C routes? |
|---|---|
| **Phase-1**: DFT enumeration + WMMSE solve + argmax-EE, seeding the catfish replay memory | **No.** No replay memory exists in stage C at all; `learner.py:279-280` states there is no reward, next state, target network, discount, or bootstrap. There is an exact selector (`S_UNI`) and an exact residual oracle (`S0`), but neither seeds any buffer — they are *comparators/labels*, not a data-preparation phase feeding a learner's replay. |
| **M1**: separate experiences by an EE threshold into two memories | **No.** There are no two memories. The analogous object — which rows get built — is governed by *source-selection rules* explicitly forbidden from looking at any outcome field (`ee_axis_source_selectors.py:18-20`), which is the **opposite** of routing by realised EE. |
| **M2**: two agents with `γ^M ≤ γ^CF` | **No.** One learner, no discount (`learner.py:279-280`). The MODQN baseline: one `discount_factor = 0.9` for all three heads. |
| **M3**: randomized periodic intervention, `S_mix` 70% main / 30% catfish | **No.** No intervention path, no second buffer to draw the 30% from. |
| **ACRM**: `r^C = r + η(r^CF − r^M)` | **No** — the name is reused for pair construction and the code says so (`ee_axis_c1_selector.py:58`). |
| **Dual-agent rollout** (a *learning* catfish agent) | **No.** Contract C1/C2 describe one model with three heads. |

Nor is it a superset: the catfish side has no analogue of C1/C2/C3 either — catfish never decomposes its objective into unilateral + continuation + interaction terms; its `r` is the undecomposed system EE (`07:65`, reward (4.3) `r_t = Σ_k R_k`).

### 4.3 What they have in common, stated honestly

Two things, and they are shallow. **[I]**

- **Both concern the same physical failure family** — many users, shared beams, a joint assignment where individual greedy choice is not jointly good. The sibling formalises it as a congestion game with a `k_cap` ranking cut (`02:97-108`); the current project formalises it as a nonzero interaction residual `Ψ_A` (contract B4).
- **Both have a notion of "an external, better-than-the-learner source"** — catfish's Phase-1 solver and learning catfish agent; the current project's `S_UNI` / exact `S0`. But their *roles* are opposite in kind: catfish's source **feeds the learner's replay buffer** so TD can discover the value of an unreachable region; the current project's exact solvers are **comparator arms and label generators** that the learner is measured against, never mixed into its training stream.

The honest one-sentence framing for a paper: **the current project's C1/C2/C3 answer "which part of a joint-assignment objective is additive and which is interaction, and can a learned head predict the interaction term fast enough to be deployable"; catfish answers "can an external high-EE experience source, injected into a second agent's replay and mixed into the main agent's batches, pull a collapsed policy out of a bad fixed point". These are different questions, and the current project's code says so in its own comments.**

---

## 5. What this project's MODQN optimises as r1 — resolved, in code and in the frozen artefact

**Answer: EE, in the frozen checkpoint.** The checkpoint was trained **after** the throughput→EE switch. Nothing here rests on the current tree's default.

### 5.1 The record in the checkpoint itself

The checkpoint stores its own `trainer_config`. I loaded it read-only with the mandated interpreter (`/home/sat/mcrl-leo-handover/.venv/bin/python`, one process, `torch.load(..., map_location="cpu")`) from
`/home/sat/mcrl-leo-handover-20260825-corrected/artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt`,
whose SHA-256 I computed as **`e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`** — the artefact named in the brief. **[V]**

Its `trainer_config` records, verbatim:

```
"r1_reward_label": "system-energy-efficiency",
"r1_reward_provenance": "paper eq. (3.25): r1 = sum_{s,v} x * eta",
"reward_calibration_enabled": true,
"reward_calibration_mode": "divide-by-fixed-scales",
"reward_calibration_source": "probe-P3-and-analytic-bound",
"reward_calibration_scales": [2029238.4328742754, 1.0, 6.0],
"objective_weights": [0.5, 0.3, 0.2],
"discount_factor": 0.9,
"learning_rate": 0.001,
"episodes": 9000,
"method_family": "MODQN-baseline",
"phase": "baseline"
```

**There is no `r1_reward_mode` key at all.** **[V]** That is the positive signature of the post-switch build: the mode key existed only while the five-way `R1_REWARD_MODE_*` selector existed, and PATCH P-20 deleted both.

Corroborating, from the same load, `last_episode_log` at episode 8999: `r1_mean = 9,635,190.20`, `r1_mean_calibrated = 4.7482`, `r2_mean = −2.48`, `r3_mean = −21.29`. **[V]** `9.64e6` is bit/J in the order of magnitude the V0.25 physics uses for `η_ref` (`1.0943e7 bits/J`, BASE-COLLAPSE report) — consistent with EE, though I treat this as corroboration, not proof **[D]**.

### 5.2 The record in the hash-bound source tree

`status.json` for that run records `run_fingerprint.code_sha256 = 544fcf078f7e0d74c38e79288081c60357bc64b59540120dbe4e30bffe014ec4` and the same `checkpoint_sha256`. **[V]** The MODQN-COLLAPSE report states it recomputed the producer's full source-closure algorithm over `/home/sat/mcrl-leo-handover-20260825-corrected` and got the same `544fcf…14ec4`, covering every `src/mcrl/**/*.py`, the launcher and `pyproject.toml` — so that tree **is** the code that trained this checkpoint. **[V, as that report's verified-by-running-code claim; I did not re-run the closure.]**

In that tree:

- `src/mcrl/runtime/trainer_spec.py:8-15` already carries **PATCH P-20**: *"the five ``R1_REWARD_MODE_*`` constants are gone. (3.25) defines r1 as one thing — ``Σ x·η`` — so there was nothing for a mode to select between … the fifth ("throughput") pointed at a field the environment had started filling with bits/J."* **[V]**
- `src/mcrl/runtime/objective_math.py:46-55`: *"``select_r1_reward_value`` is removed … The trainer now reads ``RewardComponents.r1_system_ee_contribution`` directly. There is nothing left to select."* **[V]**
- `src/mcrl/env/step_types.py:168-172` fixes the units and settles which field is r1: *"``r1_system_ee_contribution``: bit/J, ``R_u/P^N`` — **this is r1**."* and *"``r1_throughput``: bit/s, ``R_u`` — the numerator, reported beside it … **Not r1.**"* **[V]**
- `src/mcrl/algorithms/modqn.py:604-620` builds the reward vector as `np.array([rw.r1_system_ee_contribution, rw.r2_handover, rw.r3_load_balance])`, with an in-code note that *"The old default pointed at ``r1_throughput``, which the environment had begun filling with bits/J — a field whose name disagreed with its contents."* **[V]**

### 5.3 Reconciliation with the D-09 audit line

`docs/AUDIT-external-luna-2026-08-22.md`, item D-09, says: *"The default trainer selects throughput for r1 (trainer_spec.py:78-90; objective_math.py:53-90) … Default learned r1 is bits/s, not the paper bit/J common-denominator contribution."* **[V, quoted from the file.]** That audit is dated **2026-08-22**; the checkpoint's run started **2026-08-25T15:41:49Z** and finished **2026-08-25T19:39:51Z** (`status.json`). **[V]** PATCH P-20 is present in the 2026-08-25 tree. **[D]** So D-09 describes the pre-switch state and does **not** describe this checkpoint.

**Plain statement, since the brief asked for one either way: the frozen baseline was *not* trained on throughput. It optimised the EE contribution `R_u/P^N` in bit/J as r1, as the current design intends. The concern that "the baseline everything is compared against does not optimise the target metric" does not apply to this artefact.**

### 5.4 r2 and r3 against their declarations

- **r2 = −Ψ handover: as declared.** `step_types.py:177` — *"``r2_handover``: dimensionless penalty (0, −φ1, or −φ2)"*, i.e. the three-branch signed handover penalty. **[V]** Caveat, quoted from the audit and not re-verified by me: D-10 records that the handover classification *"matches the three served-association branches but adds unserved/re-entry rules (action_contract.py:392-450)"* — an extension beyond the displayed (3.27) cases. **[V, as the audit's claim.]**
- **r3 = −U beam occupancy: as declared *now*, after a correction.** `step_types.py:178-180` — *"``r3_load_balance``: PATCH P-13 (B13) — the count-based ``−U_{b_u}``, in whole users. The original line described the superseded form, 'a dimensionless ratio (negative gap / num_users)', which is a different quantity in different units."* **[V]** The audit's D-10 complaint (*"RewardComponents still documents the old 'negative gap / num_users' semantics"*) is therefore also **resolved in the tree that trained this checkpoint** — PATCH P-13 fixed the typed contract. The checkpoint's `r3_mean = −21.29` in whole users is consistent with the count form and not with a ratio in `[−1, 0]`. **[D]**
- One thing the frozen record does **not** say: nothing in `status.json` or `trainer_config` names the *environment* r1 producer; the r1 semantics are established by the hash-bound source tree, not by a standalone field in the receipt. I flag this rather than pretend the receipt is self-contained. **[V]**

---

## 6. What a faithful catfish would need from this project that does not exist yet

Component by component. "current" and "sibling" as defined at the top.

| Component | Current project | Sibling | Gap |
|---|---|---|---|
| **Specialist / solver interface** — an object that, given an anchor, returns a high-EE joint profile | **Partly exists.** `S_UNI` exact iterated unilateral improvement with a termination certificate (`run_v025_matrix_probe.py:1831`, certificate at `:1921`, 10 s budget and `DEADLINE_FALLBACK_BASE` at `:162`/`:1873`); exact `S0` with true `Ψ_A` (contract C2). **But**: no certificate was obtained on even one anchor at 60× the production budget (BASE-COLLAPSE report), so as a *data source* it is currently unusable at scale. | `F-mean` EE-aware greedy-auction heuristic and an ORACLE local search (per the package; not re-verified in code by me). Neither is the paper's DFT+WMMSE. | Need either (a) a cheap-enough specialist with a declared quality, or (b) a wall-clock story for S_UNI. Nothing DFT+WMMSE-shaped exists in either project; that is the paper's Phase-1 and it is absent everywhere. |
| **Replay seeding path** — write specialist transitions into a buffer before or during learning | **Does not exist.** Stage C has no replay at all (`learner.py:279-280`). The MODQN trainer has exactly one buffer, `self.replay = ReplayBuffer(config.replay_capacity)` at `src/mcrl/algorithms/modqn.py:143`, with no seeding entry point. **[V]** | **Does not exist** either: `07:256-273` reports the catfish buffer's only write is the catfish agent's own rollout, and my grep for Phase-1 terms returned 0 hits. | **Missing in both.** This is the single largest gap, and it is the same gap the sibling identifies as *"最大的 code-vs-paper 缺口"*. |
| **Dual-agent trainer** — two agents, two buffers, two discounts | **Does not exist.** `modqn.py:120-145`: three Q-networks (one per objective), three target nets, three optimizers, **one** replay buffer, **one** `discount_factor` used at `:550`. Stage C: one model, three heads, no bootstrap. **[V]** | **Exists**: `catfish_faithful_familyb/trainer.py` (`CatfishFaithfulFamilyBMODQN`) and `route_b_factorial/faithful_catfish_trainer.py` (`RouteBFaithfulCatfishMODQN`). **[V — files present]** | Would have to be built here, or the sibling's ported. Note the sibling's own disclosure that M2 is structurally inert in its 10-step no-accumulation env (`07:205-217`) — porting it without re-checking that would port a known dead weight. |
| **EE-threshold separation (M1)** | **Does not exist**, and the nearest analogue is deliberately the opposite: source selectors are forbidden from reading outcome fields (`ee_axis_source_selectors.py:18-20`). | **Exists** as a rolling quantile, `stratification.py:94`, `strat_threshold_quantile` default 0.80. | Buildable here in principle, but it needs a per-transition EE to threshold on, which stage C does not compute (it computes `F`, `Ψ_A`, `d_i` — not a per-step realised EE reward). A design decision, not a port. |
| **Competitive reward (ACRM)** | **Does not exist as a reward.** The identifier `ACRM` is bound to pair construction with an explicit disclaimer (`ee_axis_c1_selector.py:57-58`). More fundamentally there is no reward channel to add `η·(r^CF − r^M)` to: `learner.py:279-280`. | **Exists**: `catfish_faithful_familyb/trainer.py:385-404` implements `r_s = r_cf − r_m; shaped[0] = r_cf + η·r_s`, with `acrm_full()` / `acrm_annealed()` presets enabling it (`presets.py:110-120`, `:138-150`). Default presets have it off (`presets.py:42`, `:58`). | Needs a counterfactual "what the main agent would have done at this catfish state" evaluator. The sibling has one (`counterfactual_eta`, per `07:243`); the current project has nothing of the kind. |
| **ON/OFF harness** | **Exists in form, but toggles the wrong thing.** Contract C3 defines six arms (FULL, DROP_C1, DROP_C2, DROP_C3, ALL_NEUTRAL_CONTROL, external BASELINE) with neutral-source substitution, C5 sealing, C7's 12 learner seeds, D2's paired two-way pigeonhole bootstrap, and D5's attempt registry / write-once receipts. That machinery would carry a catfish ON/OFF unchanged — but what it currently toggles is **source informativeness for a score route**, not a training mechanism. | Three-arm paired design `OFF` / `ON` / `ONnm` over 6 seeds (`00:163-171`). | **The reusable asset.** The statistical and provenance harness is the one piece a faithful catfish here would *not* have to build. |
| **A declared endpoint** | **Does not exist for catfish.** The sibling's `argmax-EE` endpoint presupposes a collapsed OFF arm; §3.1 shows this project's OFF arm is not collapsed. The current project's endpoint is pooled `ΣB/ΣE` with `δ = +0.5 %` relative (contract D2). | `argmax-EE` on the frozen 48-episode harness, plus two-axis Pareto dominance over the BC k-NN floor. | A catfish claim here would need its own pre-declared endpoint and its own zero-learning floor, derived from this project's physics. The sibling's numbers are not transferable (different environment, different action catalogue — the MODQN-COLLAPSE report makes exactly this point about cross-project comparison: *"comparable in kind but not in physics"*). |

**Summary of the gap [I]:** of the six ingredients, the current project has **one and a half**: the experiment/statistics harness (fully), and a specialist (in code, but without a wall-clock certificate). The replay seeding path — the component the sibling calls the largest code-vs-paper gap — is missing in **both** projects. And the current stage-C learner is not a reinforcement learner at all (no reward, no next state, no target network, no discount, no bootstrap), so four of catfish's five mechanisms have **no surface to attach to**: they would require first introducing a TD learner into stage C, which is a larger change than the catfish mechanism itself.

---

## Evidence classification summary

**Verified by reading the source / running a hash or read-only load (by me, this session):** all quotations from the four sibling explainer files; the sibling code facts at `stratification.py:11,94`, `presets.py:27-28,39,42,55,58,110-120,138-150`, and the 0-hit Phase-1 grep; the full text of `V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md`; `learner.py:270-290`, `deployment.py:101-122`, `targets.py:125-135` on the server; `ee_axis_c1_selector.py:1-60`, `ee_axis_source_selectors.py:1-60`, `modqn.py:120-160,550`, `trainer_spec.py`, `objective_math.py` in the local current tree and their counterparts in the archived tree; the SHA-256 of `final-checkpoint.pt`; the checkpoint's embedded `trainer_config`, `checkpoint_rule` and `last_episode_log`; `status.json` fields; the D-09/D-10/D-13 audit text.

**Derived on paper:** the date ordering of the 2026-08-22 audit versus the 2026-08-25 run; the order-of-magnitude consistency of `r1_mean = 9.64e6` with `η_ref = 1.0943e7` bit/J; `r3_mean = −21.29` being a count rather than a ratio; PATCH P-20 being present in the tree that produced the checkpoint.

**Inferred (reasoning, not measurement):** the implication in §3.1 that a catfish ON/OFF test here would not answer the sibling's endpoint question; the "shallow commonality" framing in §4.3; the summary gap count in §6. Both server collapse reports' own numbers are taken as their verified-by-running-code sections state them — I did not re-run either probe, per the no-new-experiment constraint.

**Not established here:** whether any sibling *run* ever used the ACRM-enabling presets; the sibling's claim that M2 is structurally inert in its env; whether the source-closure recomputation in the MODQN-COLLAPSE report is itself correct (I relied on it); anything about the thesis PDF beyond what the explainer package quotes.
