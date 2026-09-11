# Declaration — two demonstration-utilisation arms, one demonstrator

> **PROVENANCE WARNING (added 2026-09-11 by the controller after CURATE):** this document contains at least one comparison between numbers produced under different conditions (physics/harness, estimand, host + TLE archive, or paired vs unpaired). Before citing any number from it, look it up in `.scratch/RESULTS-REGISTRY.md` (conditions per row, §2 lists the cross-condition comparisons) and check this document's status in `.scratch/DOCUMENT-STATUS.md`. Text below is unchanged.

Date: 2026-09-11. Pre-declared before any run. Authorises no run by itself.

## Owner instruction

Both the RIS paper's catfish mechanism and the published DQfD family are to be run and
compared, if they do not conflict. They do not: **they are two ways of using the same
demonstration data**, so they form a matched comparison rather than competing designs.

Owner also downgraded both source papers (MODQN handover, RIS/CDRL) to **reference-only**
— designs, code and mechanisms all suspect. The published family (DQfD, Hester et al.,
AAAI 2018, arXiv:1704.03732) is the primary reference. See
[[catfish-is-not-a-reward-route-2026-09-11]].

## Held fixed across arms (the demonstrator)

The demonstration source is **the same set of transitions in every arm**: the strongest
measured non-learned rule, `GAIN_IN_SET` (pooled EE 62.502712 Mbit/J, 1200/1200 served,
354/1200 attainment), versus the learned policy `a0` (q1-v1) at 41.28. Same episodes,
same seeds, same state encoding, same evaluation harness. **If the demonstration set
differs between arms the comparison is void.**

## Arms

| arm | what it is |
|---|---|
| **D0 / NONE** | no demonstrations. The control. |
| **D1 / CATFISH** | RIS paper as written: seeded catfish replay memory, EE-threshold buffer separation, asymmetric discounts, 70/30 periodic intervention, ACRM. |
| **D2 / DQFD** | published DQfD: pre-training phase on demos, demos never evicted, prioritized replay with demo priority bonus, loss = 1-step TD + n-step TD + large-margin supervised + L2. |

D0 is not optional. Without it neither arm has a reference and "catfish ON vs OFF" is
unanswerable.

## Pre-declared reading of the outcome

Declared **before** results, and not to be revised afterwards:

- **D2 > D1 > D0** — demonstrations help and the published mechanism is the better
  vehicle. The thesis reports catfish as the weaker variant of a known family.
- **D1 > D2 > D0** — the catfish mechanisms carry something DQfD does not. That is a
  genuine finding and must be attributed to a specific mechanism by ablation, not claimed
  wholesale.
- **D1 ~ D2 > D0** — the gain is *the demonstrations*, not either mechanism. This is the
  most likely outcome and must be reported as such, not dressed as a catfish result.
- **D0 >= both** — demonstration seeding does not help in this physics. Reported as the
  negative result; no further arms.

**No arm is re-run because its number was disliked. No threshold, discount, mixing ratio
or loss weight is changed after seeing an outcome.** D1's hyperparameters come from the
RIS paper, D2's from the DQfD paper; where either is unspecified, the value is declared
here before the run and recorded, not tuned.

## Gates that still stand before any of this runs

1. **CATFISHSURFACE** — whether the trainer has n-step, a supervised loss term,
   prioritized replay and a pre-training phase at all. If the delta is structural, cost
   goes to the owner first.
2. **SPECPROFILE** — whether `GAIN_IN_SET` violates a declared QoS/handover guard. This
   decides whether a **second** demonstrator exists; until it does, all three arms use
   **one**.
3. **C1VSGAIN** — whether exact C1 beats `GAIN_IN_SET`; the pre-declared rule in
   `V025-CONTROLLER-DECLARATION-TRAINING-PAUSE-2026-09-11.md` governs the 37 frozen
   trainings.
4. **DQFDGROUND** — the D2 specification and the honest mapping of the five catfish
   mechanisms onto published counterparts.

## Amendment 2026-09-11 (DQFDGROUND, `.scratch/dqfd-grounding/DQFD-FAMILY-GROUNDING-2026-09-11.md`)

Recorded **before** any run, because it changes what D1 can be claimed to be.

### D1 is the project's instantiation, not the published mechanism

The RIS paper specifies **exactly one runnable number** — the 70/30 mix. `EE_high`,
`gamma^M`, `gamma^CF`, the intervention period and ACRM `eta` are all **UNSPECIFIED**.
**Five of D1's six free numbers will be project choices.** Therefore **any D1 outcome is
an outcome for this project's instantiation of catfish, not for the published
mechanism**, and must be reported with that qualifier. The five values are declared here
before the run and not tuned afterwards.

Two further discrepancies found in the sibling's code, recorded now:
- it computes `r^C = r^CF + eta*(r^CF - r^M)`, substituting `r^CF` for the paper's `r`,
  which moves the fixed point;
- the catfish buffer is a FIFO deque, i.e. it **evicts** — the opposite of DQfD's
  never-evict guarantee.

### Published standing of the five catfish mechanisms

| mechanism | published counterpart | standing |
|---|---|---|
| (i) solver-seeded replay | RBS (Lipton 2016); class = DQfD/DDPGfD/R2D3/ADET | class supported, **but this exact parameterisation is DQfD's own NEGATIVE arm**: "naively adding … does not provide similar benefit and can sometimes be detrimental" |
| (ii) EE-threshold two buffers | split by *source* well supported (R2D3, Nair); split by *value* only as SIL's `(R - V_theta(s))_+`, relative to the learner's own value | **PARTIAL** — absolute-threshold split not found as a reproduced mechanism |
| (iii) asymmetric `gamma`, two agents | multi-gamma as auxiliary heads exists (Fedus, arXiv:1902.06865); two agents, one seeding the other | **NO COUNTERPART** |
| (iv) periodic 70/30 mix | = HER (Hosu & Rebedea 2016) | **exists, evidence points the other way**: HER is one of DQfD Fig. 2's two worst arms; R2D3 swept 120 agents, optimum ratio **1/256 ~ 0.39%**, ~77x below 30%. The *randomised period* has no counterpart |
| (v) ACRM | not difference rewards (COMA's counterfactual is a PG baseline, zero expected gradient contribution); **not potential-based**, so Ng/Harada/Russell (ICML 1999) policy-invariance does not apply | **NO COUNTERPART + published theoretical warning**. The paper's "SASR / Shen et al." citation could not be matched to any paper |

**(iii), (v) and the randomised-period half of (iv) are the three the thesis cannot lean
on.**

### Count — settled by the literature, not by me

**One demonstration stream.** No DQfD-family paper runs more than one demo buffer with an
ablation behind it. **R2D3 had three human experts and pooled them into one buffer.** No
published work sweeps the *number* of demonstrators, so "N demonstrators help up to K" is
**unclaimable**. This supersedes the earlier reasoning that a second measured
non-dominated specialist would justify a second catfish: a second specialist justifies
**more demonstration data**, not a second buffer.

Separation by **source** from the agent's own data is supported (R2D3, Nair `R_D`/`R`);
DQfD achieves the same in one buffer via never-evict plus `eps_d = 1.0` vs
`eps_a = 0.001`.

### Where it attaches — the strongest transferable finding

The only two published papers with a genuinely **one-objective demonstrator**
(arXiv:2404.04857, arXiv:1809.08343) both **confine the demonstration signal to its own
reward component**, and neither lets it write a supervised action-matching loss over the
joint policy. Two unrelated papers converging is the strongest evidence in the report.

`GAIN_IN_SET` is an **r1-only (EE) specialist**. Therefore the demonstration signal
attaches to the **r1 head**, not to the joint policy. This is a structural answer to
"where does the new catfish attach", and it is multi-head-specific.

### Loss terms

Uncontested: 1-step TD + n-step (n=10, `lambda_1 = 1.0`) + L2 (1e-5).
**Contested: the margin loss `J_E`** (`lambda_2 = 1.0`, margin 0.8) — it must be a
**declared arm, not a default**. If used, gate it with Nair's **Q-filter** evaluated on
the scalarised multi-head objective; that extension is **not published** and must be
labelled as ours. DDPGfD is the published zero-assumption alternative: no imitation loss
at all, still beat its demonstrations 2-4x.

**Demo fraction is not fixed at 30%.** DQfD does not fix it (it measures it); R2D3's
swept optimum is 0.39%; Nair's is 11.1%.

### The largest declared risk

`J_E` is **unconditional**: it fires on every demo transition, forces the specialist's
action 0.8 above all alternatives, and DQfD makes that permanent (never evicted) and
privileged (1000x priority floor). **With an r1-only specialist, every state where the
EE-best action is handover- or occupancy-costly is a state where `J_E` teaches the wrong
action.** POfD names this failure ("performance decline when only imperfect demo data are
given"; anchored baselines "converge to the imperfect demonstration data" — Walker2d:
demo 1701.13, POfD 7687.47). ZPD Table 2 adds that the single *best* demonstrator won
**0/9** Atari games against moderate teachers: **being better on the measured axis is not
evidence of being the right thing to imitate.**

### D2 specification completeness

15 values specified by the DQfD paper; **4 UNSPECIFIED** — learning rate, optimizer,
mini-batch size, replay capacity (plus the beta annealing schedule, deferred to Schaul et
al.). Runnable as published up to four engineering constants.

## Cost note

Three arms x seeds is a real training bill. The episode budget and seed count are not set
here; they are set once CATFISHSURFACE returns the measured per-episode cost, and the
owner is notified before any 9000-episode continuation.
