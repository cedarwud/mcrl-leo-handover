**Yes — ACRM has published equivalents: its linear unclipped two-learner margin is the same functional form as CuSP's regret objective `R^A(g) − R^B(g)` (Du, Abbeel & Grover, ICLR 2022, arXiv:2202.10608), the unclipped case of Sukhbaatar et al.'s asymmetric self-play reward `γ·max(0, t_B − t_A)` (ICLR 2018, arXiv:1703.05407), and the `α = −β` case of Hughes et al.'s inequity aversion (NeurIPS 2018, arXiv:1803.08884) — so the prior "no counterpart" conclusion was wrong, as was its claim that the "SASR / Shen et al." citation does not resolve (it is Ma et al., arXiv:2408.03029, printed in the source thesis's own bibliography) and its claim that the implementation substitutes `r^CF` for the paper's `r` (the source's own Algorithm 1 writes `rC ← rCF + ηrS`).**

---

# ACRM provenance — what it actually is, and what it descends from

Produced 2026-09-11 in response to ACRMSOURCE. Method: the sibling repo's own
records first and exhaustively, then the literature. That ordering is what found
the answer — the citation had already been resolved twice in-repo, and the
decisive piece of evidence on the implementation question is a line of pseudocode
in the source thesis that no prior pass had read.

---

## Part 1 — the sibling repo's own records

All file:line references below are in `/home/u24/papers/modqn-paper-reproduction`
unless marked otherwise. Everything in this section I read directly.

### 1.1 The source document

ACRM is Catfish Strategy 3 in:

> B.-H. Ke (柯博瀚), *CDRL: Catfish-Effect-Based Deep Reinforcement Learning for
> Energy-Efficient Joint Switching of RF Chains and Reflecting Elements in
> RIS-Aided 6G Networks*, MSc thesis, Dept. CSIE, National Taipei University,
> July 2025. Advisor: Yuh-Shyan Chen (陳裕賢).

Local copies: `paper-catalog/ref/2025_07_CDRL_Catfish-...pdf`,
`docs/web-agent-coordinator-catfish-integration-pack-2026-07-16/literature/CDRL-Catfish-thesis.pdf`.
Extracted text: `paper-catalog/txt_all/2025_07_CDRL_Catfish-...txt`.
Catalog record: `archive/thesis-route-c/thesis/references-text/13_PAP-2025-CDRL-CATFISH.json`.

It is **grey literature** — an institutional MSc thesis, not indexed on the open
web, no DOI, no arXiv id. It has no published venue.

### 1.2 The definition, verbatim from the source

`paper-catalog/txt_all/2025_07_CDRL_Catfish-...txt:2617-2650`:

> C. Catfish Strategy 3: Adaptive Competitive Reward Mechanism
> ... The ACRM is similar to the Self-Adaptive Success Rate Sampling (SASR)
> proposed by Shen et al. [24]. This thesis expresses the ACRM's augmented
> reward function as:
>
>     rC = r + ηrS            (4.8)
>
> Here, r denotes the original EE reward from the environment, rS represents the
> additional shaped reward, and η is the coefficient controlling the weight of
> this reward. When η approaches 0, the model degrades to the original reward
> model. As shown in Fig. 4.9, The additional shaped reward rS at time t is
> expressed as:
>
>     rtS = rtCF − rtM        (4.9)
>
> Here, rtM denotes the reward (energy efficiency) achieved by the main agent in
> the passive/active RIS communication system, while rtCF denotes the reward
> achieved by the catfish agent in the same system. **The greater the lead of the
> catfish agent over the main agent on the same task, the larger the additional
> reward received by the catfish agent.** Conversely, the catfish agent is
> penalized more when trailing behind, reinforcing the competitive dynamics.

Eq. (4.10) then puts `r^C` into the **catfish** agent's TD error with `γ^CF`.

**This settles the structure: `r^C` is the catfish agent's reward.** The main
agent's reward is never touched. The main agent benefits only through the
separate 70/30 periodic experience injection from the catfish replay buffer.

### 1.3 The source's own assessment of ACRM

`analysis/family-b-collapse-diagnosis/catfish-v2/CDRL-THESIS-ACRM-CITATION-CARD-2026-07-21.md`
locates §5.3, body pp. 51–52, verbatim:

> "Omitting the adaptive competitive reward mechanism **has the smallest effect**,
> implying that the baseline reward density already sufficiently drives CDRL
> training."

> "Using only the catfish agent without the Adaptive Competitive Reward Mechanism
> shows a smaller improvement, possibly because **the additional reward provides
> limited benefit**."

The source ranks its own three strategies: asymmetric discounting largest,
experience stratification moderate, **ACRM smallest**.

### 1.4 The implementation

Three computation sites. All three compute the same thing.

**(a)** `src/modqn_paper_reproduction/catfish_faithful_familyb/trainer.py:360-376`
— `_apply_acrm_shaping`:

```python
r_cf = float(reward_vec[0])
r_m = float(counterfactual_result.rewards[int(uid)].r1_system_ee_contribution)
r_s = r_cf - r_m
shaped = reward_vec.copy()
shaped[0] = r_cf + float(self.catfish_config.acrm_eta_weight) * r_s
```

**(b)** `src/modqn_paper_reproduction/shared_q_isolation/catfish_pack.py:364-372`
— the site the actual runs used:

```python
delta = r_cf - r_m                    # r^CF - r^M on same joint pre-state
shaped[0] = r_cf + eta_w * delta      # linear, tanh OFF, r1-axis only
```

**(c)** `src/modqn_paper_reproduction/modqn_faithful_ablation/trainer.py:871-880`
— `_shape_acrm`:

```python
main_r1 = float(counterfactual_result.rewards[int(uid)].r1_system_ee_contribution)
shaped[0] = float(shaped[0]) + (float(shaped[0]) - main_r1)
```

Presets: `catfish_faithful_familyb/presets.py:110` `acrm_full()` and `:139`
`acrm_annealed()`, both `acrm_enabled=True, acrm_eta_weight=1.0,
tanh_shaping_enabled=False`. Default is OFF: `config.py:118 acrm_enabled: bool = False`.
The route-B trainer refuses it outright: `route_b_factorial/trainer.py:61-64`
raises `NotImplementedError`.

**So the implemented formula is `r^C = r^CF + η·(r^CF − r^M)`.** The prior audit's
observation is factually correct at the character level.

### 1.5 But it is NOT a substitution error — it is the correct reading

The prior audit read the source's `r` as the main agent's reward and concluded the
code substituted `r^CF` for it. That reading is wrong, and two independent
arguments from the source's own text refute it.

**Argument 1 — the η→0 clause.** The source says "When η approaches 0, the model
degrades to the original reward model." Under the implemented reading, η→0 gives
`r^C → r^CF`, the catfish's own unshaped environment reward. Correct. Under the
prior audit's reading, η→0 gives `r^C → r^M`, the *main* agent's reward — which is
not "the original reward model" for the agent being updated. The prior reading
contradicts the source's own degeneracy clause.

**Argument 2 — the η=1 no-op.** Under the prior audit's reading,
`r^C = r^M + η(r^CF − r^M) = (1−η)r^M + η·r^CF`. At **η = 1** — the value every
preset and every run in the repo uses — this collapses to `r^C = r^CF` exactly.
The mechanism would be a literal no-op, bit-identical to no ACRM at all. The
telemetry shows it is not (nonzero `delta_abs_mean`, a measured arm difference).
The prior reading cannot be what the source means.

**Argument 3 — and this one is conclusive: the source's own Algorithm 1 spells it
out.** `paper-catalog/txt_all/2025_07_CDRL_Catfish-...txt:2704-2705`, verbatim:

```
// Catfish updates with ACRM
rS ← rCF − rM ; set rC ← rCF + ηrS .
```

and the TD error immediately below it (:2707-2712) is
`δ^CF_t = r^CF_t + η·r^S_t + γ^CF·Q^CF_{Φ^CF}(s_{t+1}, π_{θ^CF}(s_{t+1})) − Q^CF_{Φ^CF}(s_t,a_t)`.

**The source thesis itself writes `r^C ← r^CF + η·r^S`.** Eq. (4.8) leaves `r`
unqualified in prose; Algorithm 1 resolves it. The implementation reproduces the
source's pseudocode character for character.

Add the sentence "the larger the additional reward **received by the catfish
agent**" and Eq. (4.10) putting `r^C` in the catfish's TD error, and the reading
is settled beyond dispute: **`r` in Eq. (4.8) is the catfish's own environment
reward.**

**The prior audit's finding is refuted.** There is no substitution, no
discrepancy, and therefore nothing that moves the fixed point relative to the
specification. (ACRM *does* move the fixed point relative to the *unshaped*
objective — see §1.11 — but that is the mechanism working as designed, not an
implementation defect.)

**Two independent corroborations in the project's own specifications:**

- `/home/u24/papers/mcrl-leo-handover/docs/decisions/ADR-001-proposed-ris-lineage-r1-catfish.md:97`:
  `r1_cat_acrm,u = r1_cat,u + eta_A * (r1_cat,u - r1_main_cf,u)`
- `thesis-mc/ch4-method.md:194-198` (Eq. 4.11), the live thesis:
  `r^C_{1,u} = r^F_{1,u} + η_w · r^S_{1,u}` where `r^S = r^F − r^{M|F}`, with the
  explicit clause "當 $\eta_w=0$ 時，$r_{1,u}^{C}=r_{1,u}^{F}$".

**Verdict on "does the implementation match the specification":** yes. It matches
the project's own frozen specification exactly, and it matches the only
self-consistent reading of the source. There is no fixed-point discrepancy to
assess, because there is no discrepancy.

### 1.6 One real implementation defect (minor, latent)

`modqn_faithful_ablation/trainer.py:871-880` **hardcodes η = 1.0**. It never reads
`acrm_eta_weight`, unlike the other two sites. Currently benign — every preset sets
η=1.0 and `shared_q_isolation/runner_acrm_fresh_replication.py:376` asserts
`acrm_eta_weight == 1.0` — but it is a silent divergence if η is ever swept.

### 1.7 Did the sibling project question the citation?

Yes, and it resolved it, twice, before either prior agent looked.

- **Doubt recorded:** `analysis/family-b-collapse-diagnosis/CATFISH-DQFD-BOUNDARY-DISCUSSION-OUTPUT-2026-07-14.md:145`
  marks "ACRM 的祖先 SASR (Shen et al. [24]，`thesis-cited, verify`)" — flagged for
  verification.
- **Resolution 1 (2026-06-24):** `analysis/family-b-collapse-diagnosis/catfish-ca-cpbr-litcheck-findings-2026-06-24.md:42`
  records "SASR, arxiv 2408.03029".
- **Resolution 2:** `archive/thesis-route-c/thesis-narrative/05-provenance.md:110`
  records "**[SASR]** Ma et al., 'Highly Efficient Self-Adaptive Reward Shaping for
  RL,' *ICLR* 2025 (github.com/mahaozhe/SASR)."

The verbatim confirmation of Eq. 4.8/4.9 and the SASR sentence is at
`analysis/family-b-collapse-diagnosis/CATFISH-DQFD-BOUNDARY-APPENDIX-2026-07-14.md:22`,
marked "✔ CONFIRMED verbatim".

### 1.8 The recorded run

`artifacts/diag-winrate-2026-07-20/abl9k_strategy3_acrm/seed-{42,137,271}/run_metadata.json`.
Arm config `configs/shared_q_isolation/v3/abl9k_strategy3_acrm.yaml`, preset
`acrm-annealed`, trainer `ConcatAcrmCatfishE5Trainer`. Verified at source:

| field | seed 42 | seed 137 | seed 271 |
|---|---|---|---|
| `acrm_on` | true | true | true |
| `acrm_eta_weight` | 1.0 | 1.0 | 1.0 |
| `episodes` | 2000 | 2000 | 2000 |
| `uid_win_rate` | 0.338858 | 0.3570135 | 0.340898 |
| `d_signed_mean` | −1.5887727e7 | +1.489472e6 | −1.0685753e7 |
| `delta_abs_mean` | 3.1795e8 | 3.2221e8 | 3.1750e8 |
| `r_cf_mean` | 2.6340e8 | 2.7902e8 | 2.6309e8 |
| `bundle_win_rate` | 0.41075 | 0.4875 | 0.43365 |
| `bundle_feasible_win_rate` | 0.2 | 0.2769 | 0.2267 |
| `uid_comparisons` | 2,000,000 | 2,000,000 | 2,000,000 |
| `clone_count` | 2000 | 2000 | 2000 |

The prior audit's quoted `uid_win_rate = 0.339` and `d_signed_mean = -1.59e7`
are seed 42's numbers, correctly transcribed. **But they are one seed of three,
and the sign is not stable across seeds** — seed 137's `d_signed_mean` is
*positive*. Quoting seed 42 alone as "the" result overstates a negative.

Additional structure the run recorded that the prior audit did not report: the
catfish's win rate **rises monotonically over training** in all three seeds
(per-100-episode `win_blocks`; e.g. seed 42 `uid_feas_wins` goes 27,647 at block 0
to 44,691 at block 19), and `d_signed_sum` crosses from negative to positive in
the later blocks. The catfish starts behind the main agent and overtakes it. This
is the mechanism working as designed, not a null.

**Outcome as the project recorded it:**
`analysis/family-b-collapse-diagnosis/catfish-v2/EP2K-RESULT-2026-07-20.md:86` —
ACRM in-stack (L6−L8) "not credited". The citation card at
`CDRL-THESIS-ACRM-CITATION-CARD-2026-07-21.md:36` reports `L6−L8 = −6.10`
(2/6 seeds, exploratory) and `L4−L3 = +7.07` with CI crossing zero, and argues this
**agrees with the source thesis's own §5.3 ablation** where ACRM was the weakest
of the three strategies.

### 1.9 The handover repo's inherited notes

`/home/u24/papers/mcrl-leo-handover/docs/decisions/ADR-001-proposed-ris-lineage-r1-catfish.md`
§3 "Keep ACRM Catfish-only" (:92-130) is the live design record: the formula at :97,
the matched-comparator protocol, and the explicit containment rule that Main
receives the **ACRM-unshaped** calibrated reward vector on transfer (:116).

`/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md:153-166`
records that V0.3 **retired the additive form**: "The superseded formula that
added an ACRM reward directly to a Bellman target is not used: it would make Q1
incomparable with Q2 and Q3." ACRM survives there only as "the reference-anchored
candidate-versus-Main comparison inside the C1 pairwise advantage ... a unit-safe
adaptation of competitive learning, **not an additive shaped reward**."

### 1.10 The sibling repo had already done most of Part 2

Three prior literature efforts in the sibling repo bear directly on the question,
and all three predate the two prior agents' web searches.

**(a) `analysis/family-b-collapse-diagnosis/catfish-ca-cpbr-litcheck-findings-2026-06-24.md`**
— an 11-query / 4-fetch sweep whose §2 table (:34-46) is a precedent map. Line 40:

> | **Difference / relative reward ↔ PBRS** | Devlin/Yliniemi/Kudenko/Tumer 2014;
> Wolpert-Tumer 1999; Wiewiora 2003 (JAIR) | ⇒ competitive `(r^CF−r^M)`-as-PBRS is
> **precedented** — not our novelty |

and line 46:

> | Competitive **second agent** pushing main off local optima | Minimax Exploiter
> 2311.17190; AlphaStar league (Vinyals 2019) | ⇒ "catfish competition" =
> **exploiter/league** → **NOT novel** |

Its §3 (:49-50) lists what must **not** be claimed as novel: "per-objective PBRS ·
difference-reward-as-PBRS · adaptive coefficient · competitive-second-agent ·
diversity-as-reward."

**(b) `docs/research/phase-c-forward/deep-research-B2-challenger-boundary-2026-07-02.md`**
— ~30 primary sources on when a challenger/auxiliary learner helps. Its headline
(:18-26) maps three regimes where challengers help (opponent-is-environment /
league; PBT as hyperparameter selection; selective small-quota experience
injection at 1–10%) and records: "**No published case was found of a
catfish/challenger-style auxiliary competitor improving a single-team
wireless/satellite resource-allocation learner.**" Note this doc is about
*whether challengers work*, **not** about ACRM's reward form — it does not
address the functional-form question at all.

**(c) `analysis/family-b-collapse-diagnosis/track-b-mechanism-sdd-dr-modqn-v1.md`**
— the repo built a *real* difference reward, separately, for a different purpose
(:125-141):

> `D_i(a) = G(a) − G(a_{−i})` with `a_{−i}` = the joint assignment with **user i
> removed** from the system ... (Wolpert–Tumer WLU / Agogino–Tumer QUICR class;
> mechanism-prior-art, application-novel)

and disclosed (:194-196) "**D_i is NOT policy-invariant.** A team-sum difference
reward changes the per-user r1 target and can shift the optimum ... it is a
credit-assignment surrogate, not potential-based shaping."

**This is the sharpest thing in the repo for settling the Wolpert-Tumer question**,
and it settles it *against* equivalence — see Part 2.

### 1.11 Is ACRM potential-based? (my own derivation, checked against the repo)

Rewrite the implemented form:

```
r^C(s,a) = (1+η)·r^CF(s,a) − η·r^M(s)
```

where `r^M(s)` is the reward the main comparator's greedy action earns at the same
pre-action state under common random numbers — with a **frozen** comparator (which
is what ADR-001 mandates) this is a function of `s` alone.

- The `(1+η)` factor is a positive scaling of the agent's own reward. Applied
  uniformly at every step it **preserves** the optimal policy; it changes TD
  magnitudes and effective step size, not the fixed point.
- The `−η·r^M(s)` term is a **bare state function added to the reward**. It is not
  of the form `γΦ(s') − Φ(s)` — it is the `Φ(s)` half with no `γΦ(s')` companion.
  By Ng, Harada & Russell (ICML 1999), potential-based form is what buys policy
  invariance; a bare `b(s)` added to reward is the canonical non-potential
  counterexample class. Over a trajectory it contributes `−η·Σ_t γ^t r^M(s_t)`,
  which depends on state visitation and therefore **on the policy**.

**So ACRM is not potential-based and policy invariance does not hold.** Concretely,
the `−η·r^M(s)` term pays the catfish for *reaching states where the main agent
does badly*, independent of the catfish's own energy efficiency. At η=1 that
incentive carries half the weight of the catfish's own reward
(`r^C = 2·r^CF − r^M`).

This reproduces the sibling repo's own recorded verdict:
`catfish-development-direction-2026-06-24.md:16` — "**non-potential → Ng-1999-UNSOUND,
can shift the optimum**"; also `archive/thesis-route-c/thesis-narrative/05-provenance.md:74`
and `13_PAP-2025-CDRL-CATFISH.json:168` ("this additive agent-vs-agent lead is
NON-potential-based (can alter the optimum)").

Containment note: in both the sibling implementation and ADR-001 the shaped value
updates **only the catfish's `Q_1`**; Main always receives the unshaped calibrated
vector on transfer. So the distortion is confined to the catfish's fixed point —
the main agent's optimum is untouched. That containment is a project addition, not
something the source thesis specifies.

### 1.12 Did the catfish actually compete? (a finding the prior audit missed)

The per-100-episode `win_blocks` telemetry shows the catfish **starting behind the
main agent and overtaking it**, consistently across all three seeds:

| seed | `uid_wins` block 0 | `uid_wins` block 19 | `d_signed_sum` b0 → b19 | blocks with `d_signed_sum` > 0 |
|---|---|---|---|---|
| 42 | 27,647 / 100,000 | 44,691 / 100,000 | −2.769e12 → +3.944e12 | 5/20 |
| 137 | 27,559 / 100,000 | 46,049 / 100,000 | −2.776e12 → +1.848e12 | 7/20 |
| 271 | 27,356 / 100,000 | 44,094 / 100,000 | −2.737e12 → +2.413e12 | 5/20 |

The mechanism ran and did what it was designed to do. The pooled
`uid_win_rate ≈ 0.34` that the prior audit quoted is an **average over a rising
curve**, not a steady state, and the pooled `d_signed_mean` is negative only
because the early blocks dominate. Reporting 0.339 alone understates this.

### 1.13 ★ The authors' own earlier version HAD a saturating margin, and dropped it

`catfish-route/catfish/6pages.pdf` is a 6-page conference-format version of the
same work. The sibling repo knew this file existed but recorded it as unread —
`CATFISH-CONCEPT-FIDELITY-BRIEF-2026-07-10.md:34` says "6pages.pdf not read = out
of scope". **I read it.** It changes the picture.

In that version the mechanism is called **CRF (competitive reward function)**, not
ACRM, and the margin is passed through a **tanh**, verbatim:

> The third component, the additional reward mechanism, is a competitive reward
> function (CRF), similar to the Self-Adaptive Success Rate Sampling (SASR)
> proposed by Shen et al. [15]. The enhanced reward function of the CRF in this
> thesis is expressed as: `rCR = r + ηrS`. ... The shaped reward `rS` at time t is
> expressed as: `r^S_{0,t} = tanh(r^catfish_{0,t} − r^actor_{0,t})`;
> `r^S_{1,t} = tanh(r^catfish_{1,t} − r^actor_{1,t})`. Here, tanh(·) denotes the
> hyperbolic tangent function used to **normalize the difference, preventing
> training instability caused by large differences.**

Two consequences.

**(a) The squashing was load-bearing, by the authors' own stated reason, and the
final thesis dropped it.** The final thesis's Eq. (4.9) is the bare linear
`r^S_t = r^CF_t − r^M_t`. So the unbounded margin in ACRM is not an oversight by
the reimplementation — it is a regression **in the source**, against a fix the same
authors had already written down.

**(b) In this project's environment the unbounded margin is quantitatively
dominant.** From the run metadata (§1.8), at η=1 the shaping term's magnitude
relative to the catfish's own reward:

| seed | `delta_abs_mean / r_cf_mean` | `delta_abs_max / r_cf_mean` |
|---|---|---|
| 42 | 1.21 | 6.27 |
| 137 | 1.15 | 5.99 |
| 271 | 1.21 | 6.23 |

**The competitive term's mean magnitude exceeds the base reward's mean by 15–21%,
and its maximum is ~6× the base reward.** The shaped reward is dominated by the
comparison term, not by energy efficiency. This is exactly the "training
instability caused by large differences" the 6-page tanh existed to prevent.

The repo's implementation retains `tanh_shaping_enabled` but ships it OFF and
fails closed if set (`catfish_faithful_familyb/config.py:121-124`), which is
faithful to the final thesis and therefore inherits the regression.

**(c) The mis-citation is systematic.** The 6-page version's reference list
(`6pages.txt:452`) reads "`[15] MA, Haozhe, et al. Highly efficient self-adaptive
reward shaping for ...`" while its prose again says "proposed by Shen et al. [15]".
Both versions of the authors' work carry the same prose error against a correct
bibliography entry.

---

## Part 2 — published analogues

### 2.0 What ACRM's structure actually is

```
r^C = r^CF + η·(r^CF − r^M)
```

An **auxiliary learner receives a bonus proportional to the margin by which it
outperforms the main learner on the same transition.** One-sided (the main
agent's reward is untouched), linear, unbounded, unclipped, unsymmetrized.

That is the shape to search on. It is **not** the shape of a difference reward.

### 2.1 The answer: yes, and here is the closest exact-form match

**Du, Abbeel & Grover, "It Takes Four to Tango: Multiagent Self-Play for Automatic
Curriculum Generation", ICLR 2022, arXiv:2202.10608.**

Its goal generators are optimized on a **regret objective**, verbatim from §3 of
the paper:

> "The goal generators are optimized to maximize the regret of their corresponding
> agent: `R^{G_A} = R^A(g) − R^B(g)` and `R^{G_B} = −R^{G_A} = R^B(g) − R^A(g)`."

where `R^A(g)` and `R^B(g)` are two goal-conditioned learners' discounted returns
**on the same goal**. Linear, no `max(0,·)`, no clipping — **the same functional
form as ACRM's `r^S_t = r^CF_t − r^M_t`.**

- Same functional form? **Yes** — a linear unclipped margin between two learners
  evaluated on the same task.
- Same purpose? **Partly.** CuSP uses it to generate an automatic curriculum;
  ACRM uses it to breed an "elite challenger" whose experience is then injected.
  Both are "use a second learner's relative performance as a training signal".

**And CuSP explicitly analyses the pathology of the unbounded form** — this is the
citable defect, verbatim:

> "**Symmetrization.** The regret objective `R^A − R^B` helps `G_A` propose goals
> that are challenging for Bob while still being feasible for Alice. **However,
> this can be detrimental when Alice and Bob's performance diverge too quickly.**
> To address this, we propose symmetrizing the multi-agent system by introducing a
> corresponding goal generator `G_B` whose regret objective is `R^B − R^A`,
> essentially pitting it in a zero-sum game against `G_A`."

and:

> "**Without the corresponding `G_B`, if Alice performs worse at a goal, the regret
> `R^A − R^B` decreases and `g_A` is less likely to repropose it unless Bob's
> performance decreases even further. This can potentially lead to neglecting to
> propose these challenging goals for Bob.**"

ACRM has neither clipping nor symmetrization. It is the one-sided unbounded
variant that CuSP identified as detrimental and fixed.

### 2.2 The originating precedent (clipped)

**Sukhbaatar, Lin, Kostrikov, Synnaeve, Szlam & Fergus, "Intrinsic Motivation and
Automatic Curricula via Asymmetric Self-Play", ICLR 2018, arXiv:1703.05407.**

Eq. (2), verbatim: `R_A = γ · max(0, t_B − t_A)`, with `R_B = −γ·t_B` (Eq. 1).
`t_A` is Alice's time to STOP, `t_B` Bob's time to complete; on Bob's failure
`t_B = t_Max − t_A`.

- Same functional form? **Yes, modulo the clip** — auxiliary learner's reward ∝
  its margin over the main learner on the same task.
- Same purpose? Automatic curriculum / intrinsic motivation for exploration;
  the bonus goes to the *task-setter*, and Bob (the deployed agent) learns
  directly from the self-play episodes rather than via replay injection. Different
  purpose — **still a citable precedent**.
- The scaling coefficient γ is small and explicitly justified as balancing the
  internal reward "to be of the same scale as external rewards from the target
  task": 0.033 (Long Hallway), 0.1 (Mazebase), 0.01 (Mountain Car, SwimmerGather,
  StarCraft). **ACRM uses η = 1.0 with a margin already larger than the base
  reward (§1.13) — the opposite of this discipline.**

**On the clipping.** The paper never explicitly analyses or defends `max(0,·)`.
But it is implicitly load-bearing: the paper's only theoretical guarantee (§2.2,
"if π_A and π_B are in equilibrium then π_B is a fast policy") is argued from
"**Alice will always get zero reward in equilibrium**", which the zero floor
pins. Without the clip that proof by contradiction does not go through. *This is
an inference from verified text, not the paper's own claim, and must be worded
that way.*

⚠ **Do not claim** that Sukhbaatar et al. warn that removing the clip rewards
Alice for failing. That sentence is not in the paper — it was hallucinated by a
summarization step during research and caught on re-reading the PDF.

### 2.3 The strict generalization — inequity aversion

**Hughes, Leibo, Phillips, Tuyls, Dueñez-Guzman, García Castañeda, Dunning, Zhu,
McKee, Koster, Roff & Graepel, "Inequity aversion improves cooperation in
intertemporal social dilemmas", NeurIPS 2018, pp. 3330–3340, arXiv:1803.08884.**

Eq. (3):

```
u_i = r_i − (α_i/(N−1))·Σ_{j≠i} max(e_j − e_i, 0) − (β_i/(N−1))·Σ_{j≠i} max(e_i − e_j, 0)
```

with temporally-smoothed returns `e^t_j = γλ·e^{t−1}_j + r^t_j` (Eq. 4). α is
aversion to *disadvantageous* inequity, β to *advantageous* inequity.

**ACRM is exactly this at N=2 with α = η, β = −η**, since
`η(r^CF − r^M) = η·max(r^CF − r^M, 0) − η·max(r^M − r^CF, 0)`.

- Same functional form? **Yes** — ACRM is the `α = −β` special case.
- Same purpose? **No** — Hughes seeks cooperation; ACRM seeks competition.
  Still a citable precedent.
- **The sharp point:** Hughes assumes `α, β ≥ 0` throughout (both sides are
  *penalties*). ACRM's `β = −η < 0` — rewarding the agent for being ahead — is a
  configuration that literature never treats as stable. So the defect is not
  "missing a `max(0,·)`" per se; it is the loss of the **boundedness and sign
  constraints that every precedent imposes**.

### 2.4 The same-purpose match — Minimax Exploiter

**Bairamian, Marcotte, Romoff, Robert & Nowrouzezahrai, "Minimax Exploiter: A Data
Efficient Approach for Competitive Self-Play", arXiv:2311.17190 (2023).**

Eq. (3): `R^i_minimax(s_t,a_t) = R^i(s_t,a_t) − α·γ·(1−d)·max_a Q^j(s_{t+1},a)`,
α ∈ [0,1], where `j` is the Main Agent and `i` the Exploiter. The paper states the
modified reward "is only used on Exploiter Agents… and **not on the Main Agent**"
— **structurally identical to ACRM's catfish-only containment.**

- Same functional form? **Yes** (auxiliary reward = env reward + coefficient ×
  a measure of the main agent's performance; Q-value here vs realized reward in ACRM).
- Same purpose? **Yes** (the auxiliary exists to make the main agent stronger).

Two directly citable warnings, verbatim:

> "We note that the choice in α is important, since **setting it too high will
> potentially result in the agent focusing too much on the opponents value
> function**, which in our case is only an approximation."

> "Moreover, **to reduce the potential for reward hacking via finding a cycle of
> infinite positive rewards, we ensure that the additional reward term based on the
> opponents value function, provided only at non-terminal states, is at most
> zero.**"

ACRM constrains neither η nor the range of `r^CF − r^M`.

### 2.5 Difference rewards — NOT an equivalent, and here is why precisely

**Wolpert & Tumer**, "Optimal payoff functions for members of collectives",
*Advances in Complex Systems* 4(2–3):265–279, 2001 (COIN); **Agogino & Tumer**
(QUICR/WLU); **Devlin, Yliniemi, Kudenko & Tumer**, "Potential-based difference
rewards for multiagent reinforcement learning", AAMAS 2014.

Difference utility: `D_i = G(z) − G(z_{−i})` — the **system objective with agent i
present** minus the **same system with agent i removed or replaced by a default**.
It is a counterfactual over *the same agent's own participation*, computed to solve
**credit assignment** in a shared team objective.

ACRM: `r^CF(s, a_CF) − r^M(s, a_M)` — **two different learners' realized rewards
under two different actions in the same system state.** No agent is removed; the
system is intact in both branches.

**These are different objects.** One is system-with vs system-without; the other is
learner-A vs learner-B. The sibling repo demonstrates the distinction by having
built both, separately, for different reasons — `track-b-mechanism-sdd-dr-modqn-v1.md:129`
implements the real `D_i = G(a) − G(a_{−i})` on the r1 head for marginal-congestion
credit, entirely independently of ACRM.

**Verdict: same algebraic silhouette (a subtraction), different semantics, different
purpose. It is form-adjacent prior art worth one line in related work, not the
equivalent.**

*(On COMA — Foerster, Farquhar, Afouras, Nardelli & Whiteson, "Counterfactual
Multi-Agent Policy Gradients", AAAI 2018: its counterfactual is a policy-gradient
**baseline**, which leaves the reward and hence the fixed point untouched, whereas
ACRM changes the reward itself. Different objects; the prior audit's use of COMA to
dismiss the difference-reward family was a category error. Noted and moved past.)*

### 2.6 The family's convergent design principle — and what ACRM omits

Six independent works in this space all **bound the cross-learner term**, by six
different mechanisms:

| Work | Citation | Bounding mechanism |
|---|---|---|
| Asymmetric self-play | Sukhbaatar et al., ICLR 2018, arXiv:1703.05407 | `max(0,·)` clip to zero; γ ∈ [0.01, 0.1] |
| OpenAI asymmetric self-play | Plappert et al., arXiv:2101.04882 (2021) | replaced the margin entirely with bounded binary {0, 5} |
| AMIGo | Campero et al., ICLR 2021, arXiv:2006.12122 | thresholded two-sided `{+α, −β}` |
| Setter-Solver | Racanière et al., ICLR 2020, arXiv:1909.12892 | difficulty **regressed to a sampled target**, not maximized |
| Minimax Exploiter | Bairamian et al., arXiv:2311.17190 | shifted so the cross term is `≤ 0`; α ∈ [0,1] |
| CuSP | Du, Abbeel & Grover, ICLR 2022, arXiv:2202.10608 | symmetrized into a zero-sum pair |

**ACRM uses none of them.** Note especially that OpenAI's own direct successor to
Sukhbaatar's method *abandoned the margin form* in favour of a bounded binary
reward — and that the CDRL authors' own 6-page version (§1.13) had a tanh, which
the final thesis dropped. The convergence is strong: unbounded two-learner margins
are a known hazard, and ACRM sits at the unprotected point of the design space.

### 2.7 Families checked that are NOT equivalents

| Family | Citation | Verdict |
|---|---|---|
| Population-Based Training | Jaderberg et al., arXiv:1711.09846 (2017) | **Neither.** Inter-learner comparison drives `exploit()` (weight/hyperparameter copying) and deliberately never enters the reward. A useful design contrast for ACRM. |
| League training / exploiters | Vinyals et al., *Nature* 575:350–354, 2019, doi:10.1038/s41586-019-1724-z | **Same purpose, different form.** Exploiters exist to expose the main agent's flaws, but relativity lives in *opponent sampling* (PFSP), not in a reward term. *(Reward definition not verified at source — do not assert "AlphaStar has no margin reward" without checking the Nature appendix.)* |
| Competitive coevolution / relative fitness | Rosin & Belew, *Evolutionary Computation* 5(1):1–29, 1997, doi:10.1162/evco.1997.5.1.1 | **Unresolved.** Competitive fitness sharing appears to be a shared-credit scheme (`1/N_j` credit for beating opponent j), not a per-individual score difference — but all three sources returned 403 and **the formula was not verified.** Open item. |
| Ensemble-disagreement intrinsic reward | Pathak et al., "Self-supervised exploration via disagreement", ICML 2019 | **Neither.** Disagreement is variance across an *ensemble of dynamics models*, not a performance margin between two policy learners. |
| SASR | Ma et al., ICLR 2025, arXiv:2408.03029 | **Neither** (see Part 3). Shares only the generic additive-shaping template. |
| Potential-based shaping | Ng, Harada & Russell, ICML 1999 | **Not applicable** — ACRM is not of the form `γΦ(s') − Φ(s)`; see §1.11 and §2.8. Policy invariance does not hold. |
| Competitive Experience Replay | Liu, Trott, Socher & Xiong, ICLR 2019, arXiv:1902.00528 | **Different form, adjacent purpose.** A pair of agents in an exploration race; it *does* relabel rewards (A penalized on states B visited, B rewarded), but keyed on **state visitation comparison**, not a return margin. |
| Social influence intrinsic motivation | Jaques et al., ICML 2019, arXiv:1810.08647 | **Shell only.** Counterfactual-derived bonus added to env reward; the counterfactual is over *the agent's own* action's causal effect on others. Purpose is coordination. |
| Difference-reward policy gradients (Dr.Reinforce) | Castellini, Devlin, Oliehoek & Savani, AAMAS 2021 / *Neural Comput. Appl.* 2022, DOI 10.1007/s00521-022-07960-5, arXiv:2012.11258 | **Advantage-as-reward, but** the subtracted term is a counterfactual default action, not a second learner. |
| "Catfish effect" in metaheuristics | Chuang, Tsai & Yang, *Expert Systems with Applications* 38(10), 2011, DOI 10.1016/j.eswa.2011.04.057 (catfish-PSO); also DOI 10.1155/2018/6906295, DOI 10.1007/s10462-025-11291-x | **Metaphor precedent only.** The catfish metaphor entered computational optimization a decade before CDRL — worth one line, as it shows the naming is borrowed, not coined. |

### 2.8 Why ACRM is not potential-based — the theorem, verbatim

**Ng, Harada & Russell, "Policy Invariance Under Reward Transformations: Theory and
Application to Reward Shaping", ICML 1999**, Theorem 1 (verified against the
original PDF):

> Let any S, A, γ, and any shaping reward function F : S × A × S ↦ ℝ be given. We
> say F is a **potential-based** shaping function if there exists a real-valued
> function Φ : S ↦ ℝ such that for all s ∈ S − {s₀}, a ∈ A, s′ ∈ S,
> **F(s,a,s′) = γΦ(s′) − Φ(s)** (2).
> Then, that F is a potential-based shaping function is a **necessary and
> sufficient** condition for it to guarantee consistency with the optimal
> policy … (Necessity) If F is not a potential-based shaping function … then there
> exist (proper) transition functions T and a reward function R such that no
> optimal policy in M′ is optimal in M.

Corollary 2: `Q*_{M′}(s,a) = Q*_M(s,a) − Φ(s)`.

`η(r^CF − r^M)` fails (2) on three counts: it is action-dependent in general; it
does not telescope (no `γΦ(s')` companion — see §1.11); and with a concurrently
learning main agent it drifts with the comparator's policy. Dynamic PBRS
(**Devlin & Kudenko**, "Dynamic Potential-Based Reward Shaping", AAMAS 2012,
pp. 433–440) permits a time-varying Φ but still requires the form
`F = γΦ(s′,t′) − Φ(s,t)` with the potential evaluated on state entry; ACRM does
not meet that either.

Devlin's thesis (*Potential-Based Reward Shaping for Knowledge-Based, Multi-Agent
Reinforcement Learning*, Univ. of York) states the analogous point for difference
rewards directly: "**as the counterfactual term does not depend on previous states,
difference rewards and PBRS are not equivalent**." The same argument applies to
`r^CF`.

**By the necessity clause, there exist transition/reward functions for which no
optimal policy of the ACRM-shaped problem is optimal for the original.** So any
measured ACRM gain has to be carried by evidence, not by theory, and "the optimum
was moved" must be excluded as an explanation.

**Two published routes to a version that *does* preserve the optimum**, if the
mechanism is to be kept:

1. **Counterfactual-as-Potential (CaP)** — Devlin, Yliniemi, Kudenko & Tumer,
   "Potential-Based Difference Rewards for Multiagent Reinforcement Learning",
   AAMAS 2014, pp. 165–172. Their Eq. (7) puts the counterfactual *inside* the
   potential: `r = G`, `F = γΦ(s′) − Φ(s)` with `Φ(s) = G(s_{−i})` — "guaranteed to
   have the same Nash equilibria as G alone". The ACRM analogue is to set
   `Φ(s) = r^M(s)` and shape with `γ·r^M(s') − r^M(s)` instead of adding `−η·r^M(s)`.
   *(This is the same move the sibling repo's own CA-CPBR proposal made —
   `catfish-ca-cpbr-design-note-2026-06-24.md` — arrived at independently.)*
2. **Arbitrary reward as potential-based advice** — Harutyunyan, Devlin, Vrancx &
   Nowé, "Expressing Arbitrary Reward Functions as Potential-Based Advice",
   AAAI 2015. Learn a secondary value function Φ on reward `−R†` in parallel, then
   shape with `F = γΦ_t(s′,a′) − Φ_t(s,a)`; this captures `R†` in expectation while
   preserving policy invariance.

### 2.9 The "catfish effect" name has no RL precedent

Exhaustive arXiv API search: `abs:"catfish" AND abs:"reinforcement learning"` →
**0 results**. `all:"catfish effect"` → **2 results**, neither relevant to reward
shaping:

- Liu, Ruan & Liu, "Catfish Effect Between Internal and External Attackers: Being
  Semi-honest is Helpful", arXiv:1907.03720 (2019) — cryptocurrency mining.
- Wang, Yan, Xing, Liu, He, Fu, Hu & Heng, "Silence is Not Consensus: Disrupting
  Agreement Bias in Multi-Agent LLMs via Catfish Agent for Clinical Decision
  Making", arXiv:2505.21503 (2025) — **same metaphor, same role** (a deliberately
  contrarian auxiliary agent stimulating the main group), but LLM prompting with
  **no reward function at all**.

So the *name* is essentially novel in RL — and that is precisely why it cannot be
used to distinguish ACRM from prior art. The precedent lives in the **form**, and
the form is well populated.

---

## Part 3 — the citation, resolved

**"SASR / Shen et al." resolves. The source thesis's own bibliography answers it.**

`paper-catalog/txt_all/2025_07_CDRL_Catfish-...txt:3342-3343`, verbatim:

```
[24] Ma, H., Luo, Z., Vo, T. V., Sima, K., and Leong, T. Y., "Highly efficient self-adaptive
     reward shaping for reinforcement learning," arXiv preprint arXiv:2408.03029, 2024.
```

Verified independently by fetching the paper:

| Field | Value |
|---|---|
| Title | Highly Efficient Self-Adaptive Reward Shaping for Reinforcement Learning |
| Authors | Haozhe Ma, Zhengding Luo, Thanh Vinh Vo, Kuankuan Sima, Tze-Yun Leong |
| Affiliations | National University of Singapore; Nanyang Technological University |
| Venue | **ICLR 2025** (poster); OpenReview `QOfWubPhdS` |
| arXiv | **2408.03029** (v1 2024-08-06, v4 2025-02-28) |
| DOI | 10.48550/arXiv.2408.03029 |
| Code | github.com/mahaozhe/SASR |

**Two errors in the source thesis's prose, both confined to the prose:**

1. **"Shen et al." is wrong.** There is no author named Shen on arXiv:2408.03029.
   The five-author list was confirmed on the arXiv abstract page, the ICLR virtual
   poster page, and the GitHub README. The only "Shen" string anywhere in the
   thesis is "Shenyang, China" in reference **[23]**, immediately above [24] — the
   likely source of the slip.
2. **"Self-Adaptive Success Rate Sampling" is wrong.** The paper defines SASR as
   "Self-Adaptive Success Rate-based reward shaping mechanism". The expansion with
   "Sampling" is the thesis's own invention.

The reference-list entry itself is correct. This was a prose slip, not a phantom
citation. **The prior conclusion that the citation "does not resolve to any paper"
is wrong** — it resolves cleanly, and the sibling repo had already resolved it
twice (§1.7).

**Is SASR actually an analogue of ACRM?** Barely. SASR's shaped reward is
`R^S(s_i) = f(N_S(s_i)/(N_S(s_i)+N_F(s_i)))` sampled from `Beta(N_S+1, N_F+1)`,
with KDE/Random-Fourier-Feature count estimation for continuous states — a
per-state success-rate statistic from the agent's own history, whose whole point
is the Beta posterior's variance annealing ("self-adaptive"). ACRM's `r^S` is an
instantaneous inter-agent performance difference with no history, no distribution,
no annealing. The only shared structure is the generic additive template
`r_total = r_env + coefficient × r_shaped`, which is common to the whole
reward-shaping literature. **The source's "similar to SASR" claim overstates the
relationship, and SASR is not ACRM's real precedent.**

**Negative results (auditable):** no other "SASR" in RL by an author named Shen was
found across four search formulations (`"Self-Adaptive Success Rate Sampling" RL
Shen`; `Shen "SASR" RL reward shaping state-action self-adaptive sampling`; `Shen
"self-adaptive" reward shaping RL sampling success rate IEEE`; `Shen RL "success
rate" reward shaping RIS energy efficiency`). No Shen-authored RIS / reward-shaping
/ satellite-wireless RL paper surfaced that could be an alternative [24]. This is
moot regardless — the bibliography settles [24] directly.

**Also negative:** the CDRL catfish thesis itself is not on the open web. Searches
for `"catfish" "reconfigurable intelligent surface" competitive DRL reward`,
`"adaptive competitive reward mechanism" "catfish"`, and `"catfish effect" CDRL
wireless` returned nothing. It must be cited as an institutional thesis.
**`arXiv:2409.18718` is a dead end** — the PDF of that name in the sibling repo is
Hassan et al., *Enhancing Spectrum Efficiency in 6G Satellite Networks: A
GAIL-Powered Policy Learning via Asynchronous Federated Inverse RL*, unrelated to
RIS, CDRL, catfish, or ACRM.

---

## Verdict

**A published equivalent exists.** The prior "no counterpart" conclusion is wrong
on every one of its three components:

1. **"The citation does not resolve."** Wrong. Reference [24] is Ma et al.,
   arXiv:2408.03029, ICLR 2025 — printed in the source thesis's own bibliography,
   and already resolved twice in the sibling repo's records before either web
   search began. The "Shen et al." in the prose is a mis-citation internal to the
   source (and repeated in its 6-page version), not a phantom reference.

2. **"No published counterpart."** Wrong. The closest exact-form match is **CuSP's
   regret objective `R^A(g) − R^B(g)`** (Du, Abbeel & Grover, ICLR 2022,
   arXiv:2202.10608) — a linear, unclipped, two-learner margin on the same task.
   The clipped originating form is **Sukhbaatar et al.'s `R_A = γ·max(0, t_B − t_A)`**
   (ICLR 2018, arXiv:1703.05407). The strict generalization is **Hughes et al.'s
   inequity aversion** (NeurIPS 2018, arXiv:1803.08884), of which ACRM is the
   `α = −β` case. The closest *same-purpose* match is the **Minimax Exploiter**
   (arXiv:2311.17190), which shapes only the auxiliary agent by a measure of the
   main agent's performance, exactly as ACRM does.

3. **"The code substitutes r^CF for the paper's r."** Wrong. The source thesis's
   own Algorithm 1 writes `rC ← rCF + ηrS` verbatim. The implementation is
   faithful; the prior reading would make the mechanism a literal no-op at the
   η = 1.0 every run used.

**The dismissal of difference rewards was right for the wrong reason.** Difference
rewards genuinely are not ACRM's equivalent — but because `G(z) − G(z_{−i})` is
system-with vs system-without while ACRM is learner-A vs learner-B, not because of
anything about COMA. Ruling out that one family and stopping was the error; the
two-learner-margin family was never searched.

**ACRM as implemented matches ACRM as specified**, in the source's pseudocode, in
the project's ADR-001, and in the live thesis's Eq. (4.11). There is no
implementation/specification discrepancy and nothing moves the fixed point relative
to spec.

**ACRM does move the fixed point relative to the unshaped objective**, and that is
inherent to the mechanism, not to the implementation: `r^C = (1+η)r^CF(s,a) −
η·r^M(s)` adds a bare state-dependent term, which is not potential-based, so Ng-1999
invariance fails. Containment to the catfish's `Q_1` limits the damage to the
catfish's own optimum.

**The genuine, citable defect is the unbounded margin.** Every precedent in the
family bounds the cross-learner term (§2.6); the CDRL authors' own 6-page version
bounded it with a tanh and the final thesis dropped that; and in this project's
environment the margin's mean magnitude is 1.15–1.21× the base reward and its
maximum ~6× (§1.13). CuSP and Minimax Exploiter both analyse this failure mode in
print. That is a specific, sourced finding — not a vague "no counterpart".

### What to do with this

- Cite **Ke 2025 [source]** → **Ma et al. arXiv:2408.03029 / ICLR 2025 [the
  source's own ancestor claim]**, and correct "Shen et al." to "Ma et al." wherever
  it is repeated. Note that the SASR resemblance is weak and say so.
- Position ACRM in the **two-learner-margin family**: Sukhbaatar 2018 (clipped) →
  CuSP 2022 (linear, symmetrized) / Hughes 2018 (two-sided, both-penalty) /
  Minimax Exploiter 2023 (bounded ≤ 0, main-agent-only). Do **not** claim the form
  is novel.
- If ACRM is kept, **bound the margin** — the 6-page tanh, a clip, or an η scaled
  to the base reward as Sukhbaatar's γ is. The measured 1.2×/6× ratios are the
  evidence that this is not hypothetical.

### Evidence status

**Verified by reading (repo):** every file:line in Part 1, the source thesis text
and Algorithm 1, the 6-page PDF's CRF section and reference list, all three
`run_metadata.json` files (numbers recomputed, not transcribed).
**Verified by fetching (literature):** SASR's authors/title/venue (arXiv, ICLR
virtual, GitHub); Sukhbaatar Eqs. 1–2, §2.2, Table 1, Algorithm 1, footnote 2;
CuSP's regret objective and Symmetrization paragraph; Hughes Eqs. 3–4; Minimax
Exploiter Eqs. 3–4 and both α/hacking quotes; OpenAI 2021 §3.1; AMIGo teacher
reward; Setter-Solver losses; PBT exploit/explore; the arXiv "catfish" searches.
**On search reliability.** Two independent literature searches ran on this
question with different framings. They **converged** on Hughes et al.'s inequity
aversion as the most literal match without knowing of each other. They
**diverged** on the headline: the one framed on difference rewards and PBRS
concluded "apart from inequity aversion, I found no published method that
subtracts another *learning* agent's return and uses it as a reward" — a negative
that the one framed on two-learner margins refuted by finding CuSP. That is the
same failure the prior audit made, reproduced under controlled conditions: **this
precedent is reachable from a curriculum-learning / self-play framing and
essentially unreachable from a credit-assignment / shaping framing.** Treat any
future negative on this question as framing-dependent until searched from the
self-play side.

**Not verified — do not assert:** AlphaStar's exploiter reward definition
(Nature appendix unread); Rosin & Belew's competitive fitness sharing formula
(three sources 403); Held/Florensa's "inherently unstable" analysis (found only
Sukhbaatar's footnote paraphrase, not the original); the 6-page PDF's relationship
to any published venue.
