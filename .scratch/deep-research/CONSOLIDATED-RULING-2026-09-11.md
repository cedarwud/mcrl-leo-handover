# Consolidated ruling on the three Deep Research reports

Date: 2026-09-11. Sources: `dr1.md`, `dr2.md`, `dr3.md`. **Every claim below is the DR
report's, to be verified against the primary source before entering a declaration.**

## 1. The architecture recommendation is withdrawn — two critics is folklore

**The full combination `(Q_B, Q_E)` + Dinkelbach outer loop + replay + masked discrete
argmax: no primary source found** (dr1 §"證據缺口", explicit). Three independent parties —
the controller, the agy review, and the gpt2 proposal — converged on it, and **none of them
had a citation, because there isn't one.**

Worse, the specific form is contradicted:

- **`argmax_a Q_B/Q_E` from two independently-optimal heads has no support and must not be
  derived from existing theory.** Jin's fractional decomposition `Q_γ = N_γ − γ D_γ`
  requires both components to be defined **under the same γ-optimal continuation policy**,
  which is not two heads each maximising its own objective (dr1, Jin AAAI 2024,
  arXiv:2312.10418).
- **This is the same mathematical error as the per-head bootstrap defect already found in
  `modqn.py:536-552`** — combining independently-optimal value functions as though their
  weighted combination were a value function. Two independent routes to the same error.
  The B0 fix (bootstrap every head from the argmax of the scalarised sum) is therefore
  **more strongly supported than when it was dispatched**.

### What IS supported, strongly

`B − η E` as the ratio-consistent additive Bellman signal, with `η` updated in an outer
loop from realised sums. Dinkelbach 1967 (DOI 10.1287/mnsc.13.7.492); Suttle et al. CARVI,
ICML 2021 (tabular two-timescale convergence, discrete, value-based); Jin et al. AAAI 2024
(replay-based D3QN inside a fractional framework).

**Decision: build a single scalarised `B − η E` signal with `η` in an outer loop. Do not
build two critics.**

### The replay problem, and the one design choice we must own

`B − η E` changes when `η` changes, so every stored target computed under an old `η` is
stale. **Jin's published implementation stores the already-transformed scalar and does not
handle this**; its convergence theorem does not analyse it (dr1, explicit). So the field
has not solved it.

**Storing raw `(B, E)` and recomputing `B − η E` at sample time is algebraically exact but
has no published protocol.** That is our design choice, it must be **declared as new and
ablated**, not presented as standard practice. Buffer-flush-on-η-update: also no source.
Two-timescale arguments do **not** cover finite replay of stale transformed rewards —
CARVI's theorem is online stochastic approximation, not replay.

### Demonstrator advantage under a ratio — the definition exists, the use does not

Grounded: `m_η(s, a_D, a_L) = [Q_B(a_D) − Q_B(a_L)] − η[Q_E(a_D) − Q_E(a_L)]`, and the
policy-gradient form `A_B − ρ A_E` (Suttle CAAC). **But no fractional-RL paper uses either
to gate an imitation or large-margin loss.** Using it that way is a **new combination** and
must be labelled as ours, not as replication.

Corollary that matters: a DQfD-style fixed margin on a scalar `Q` has clear semantics
**only if that scalar `Q` is the `B − ηE` fractional subproblem's `Q`**. On an arbitrary
weighted multi-objective reward it carries no fractional-programming guarantee.

### Pooled EE: measurable, not directly trainable

The pooled ratio `Σ B_i / Σ E_i` **is** the natural sample estimator of `E[B]/E[E]` and is
therefore the right **evaluation** statistic. **No published method back-propagates a
finite-batch pooled quotient as a replay loss.** What is trainable is `B − η E` TD or a
reward-rate differential TD. **So the endpoint stays as the endpoint; the training signal
is `B − η E`.** That resolves the open question cleanly and in our favour.

### Ratio vs constrained: not equivalent

`max B/E` and `max B s.t. E <= c` generally give different policies (dr1 gives a two-policy
counterexample). The ratio optimum **is** optimal for the budget it itself induces, but an
arbitrarily chosen `c` does not recover it. **So adopting a constrained endpoint is a
change of decision preference, not a reformulation** — which sharpens what the owner is
being asked to decide. By contrast `B − ηE` **is** an exact parametric reformulation of the
ratio.

## 2. Physics — two of our load-bearing facts are weaker than claimed

### 2a. The 62/142 ms interruption constants are NOT verified as normative

dr2: *"我沒有從符合本題來源門檻的可驗證 primary-source extract 中，驗證出「62 ms = 同衛星
換 beam、142 ms = 換衛星」這一對數字是 Release-17 NTN 的通用規範常數"*. 62 ms appears in
**a** Rel-17 test configuration; **142 ms was not located at all**.

**This directly conflicts with the adversarial reviewer**, who reported them "confirmed
against 3GPP TS 38.133 Annex A.14.2". **Two sources disagree and neither has been checked
by the controller against the actual spec.** Until one is, the constants are **test-case /
implementation parameters, not standard handover costs**. Flagged, unresolved.

*(This does not change the arithmetic that killed the numerator proposal — that argument
only needed the constants to be small, and a smaller or unverified value makes it stronger,
not weaker.)*

### 2b. `max`-over-users beam power is **not** the standard model — and this undercuts our own r3 argument

dr2, explicit: the standard multiuser payload model takes a beam's transmit power as the
**sum of its users' precoder powers** (Ha et al., GLOBECOM 2022, §II-B eq. 3), plus a fixed
per-illuminated-beam hardware term, summed over beams. `max` over users was **not found as
a mainstream convention**.

**Consequence: our finding that "adding a user to an active beam costs exactly 0 W" is a
property of a non-standard power model, not of satellite physics.** Under the standard
additive model it would cost something. So:

- the r3-premise-fails argument is **model-dependent**, and its basis is now a simulator
  choice a referee will question;
- the sealed V0.25 successor's occupancy → required-power change is **the standard-aligned
  direction**, which strengthens the earlier adversarial objection that we were about to
  overturn a sealed decision;
- **this is the highest-ranked defensibility problem in the simulator** and it should go to
  the owner as such.

### 2c. The handover-rate envelope — one of our reviewers overstated

Published operating points at 550-600 km: **0.10/min** (elevation-threshold),
**0.167/min** (graph-planned), **~0.998/min** (600 km dense Walker, 60.12 s mean
inter-satellite interval), with an explicit study-imposed cap at **~1.2/min**
(`H̄ = 0.004` per 0.2 s epoch).

Converting ours at `dt = 30.08 s`:

| | per user-step | per minute | vs published envelope |
|---|---:|---:|---|
| trained learner | 0.2796 | **0.558** | **inside** |
| `MAX_NOMINAL_GAIN` | 0.7117 | **1.420** | **above the highest published cap (1.2), not absurd** |

**The agy review's "70% churn per 30 s is operationally absurd, RACH flooding, control-plane
collapse" is too strong.** It is 1.42 handovers per minute, roughly 18% above the highest
cap any surveyed paper imposed on itself. That is a real constraint violation and a real
argument for a cap — **but not the qualitative absurdity the review asserted**, and the
correction must be carried.

**There is no 3GPP handovers-per-minute ceiling.** The only concrete ceilings in the
literature are study-specific stipulations. So a constraint threshold here is honestly a
**declared design parameter with a cited precedent for the practice**, not a derived bound.
`H̄ = 0.004` is the citable precedent for *declaring* one.

### 2d. No standard joules-per-handover — confirmed

dr2 finds no 3GPP or literature basis for a per-handover energy tariff; costs are
interruption ms, signalling messages, failure probability. **Our r2-prices-a-zero-joule-event
finding is consistent with the field**, and moving handover cost into an energy term has no
external support. Unchanged.

## 3. Landscape — the negative result has no precedent, and multiple sources have a basis

### 3a. Nobody publishes "the simple rule won"

dr3 found **no peer-reviewed LEO paper whose primary contribution is that a learned method
fails to beat a simple rule**. The closest published diagnostics are weaker: a simple rule
winning one *component* (Lee et al., IEEE TWC 2024, Table VII — random competitive on
collision); online RL losing to rule baselines **when undertrained** (Yang et al., Asilomar
2023, Fig. 1); and a declared system endpoint that **cannot be decomposed into a per-step
reward**, forcing a surrogate (Yang et al.).

**So our result — a converged, authenticated checkpoint beaten by a one-line rule by
19.8-22.2% on the paper's own declared endpoint, traced to reward misspecification — has no
equal precedent.** That is simultaneously the novelty and the referee risk.

### 3b. Simple-rule baselines are standard practice — our baseline work is defensible

Of the 13 papers whose comparators dr3 could identify, **10 include at least one of random /
single-criterion / greedy / max-signal / max-service-time / exhaustive**. A de facto family
exists: random, max-link-quality, longest-remaining-service, load/capacity-aware, and a
greedy matched to the objective. **We have measured all of these or their analogues.**

### 3c. A published basis for MULTIPLE sources that we did not have

**Yang et al., Asilomar 2023, Fig. 4**: several *individually poor* behaviour policies,
mixed (50% main BP / 20% greedy / 20% TDM / 10% random), produce a **better** offline
dataset than any one of them — and the mechanism is **coverage, not expertise**. Fig. 3:
a single low-quality behaviour policy **limits** the learner.

**This is the multi-catfish justification, and it is different from the one we had.** The
argument is not "a second specialist is better at something"; it is **"a second source
covers states the first does not"**. That is also exactly the JSRL coverage sweep's
question, now with a published precedent behind it.

It also reframes the naming: in wireless offline RL, a heuristic or solver data source is
called a **behaviour policy**, not an expert demonstrator — because the algorithms that use
it care about coverage and distribution shift, not about imitating it.

### 3d. The catfish lineage does not resolve

dr3 **could not independently resolve the RIS/CDRL catfish paper's bibliographic identity
at all** — so citation count and replication status are **unverifiable, and must not be
reported as zero**. "SASR / Shen et al." remains **unresolved** (the only SASR found is an
unrelated 2025 LLM fine-tuning paper by Chen et al.). "Catfish effect" exists elsewhere —
swarm-optimisation population diversity, meta-learning "catfish pruning", a 2025 multi-agent
LLM "Catfish Agent" injecting dissent — **and none of them is solver-seeded replay.**

**No DQfD deployment found in satellite beam management or handover. No
advantage-weighted-regression-from-demonstrations either.**

## 4. What changes, concretely

| | before | after |
|---|---|---|
| training signal | two critics `Q_B`, `Q_E` | **single `B − ηE`, `η` in an outer loop** — the only supported form |
| replay | (unspecified) | **store raw `(B, E)`, recompute `B − ηE` at sample time; declare as new, ablate it** |
| per-head bootstrap fix | a defect fix | **independently confirmed by fractional-RL theory; keep, and it is now load-bearing** |
| demonstrator advantage | scalar Q-margin | **`m_η` difference form; using it to gate imitation is new and must be labelled ours** |
| pooled EE | endpoint, possibly untrainable | **endpoint stays; it is an evaluation statistic and that is correct practice** |
| multi-source justification | "a second non-dominated specialist" | **coverage (Yang Fig. 4), not expertise** |
| 0.7117 handover rate | "operationally absurd" | **1.42/min, ~18% above the highest published self-imposed cap** |
| `max`-over-users beam power | assumed | **non-standard; the r3 argument is model-dependent — highest defensibility risk** |
| 62/142 ms constants | "confirmed against TS 38.133" | **unverified; two sources conflict; controller has checked neither** |

## 5. What the owner must decide, now narrower

Not "should the endpoint change" in the abstract, but: **the ratio and the constrained
problem are genuinely different preferences (dr1 proves non-equivalence), and there is no
external ceiling to derive — only a citable precedent for declaring one.** So the question
is whether the thesis claims *maximum efficiency* or *maximum efficiency at a declared
operating limit*. Both are defensible; they are different papers.
