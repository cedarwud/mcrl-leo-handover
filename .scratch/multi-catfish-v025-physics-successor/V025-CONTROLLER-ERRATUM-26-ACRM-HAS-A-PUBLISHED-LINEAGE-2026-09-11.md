# Erratum 26 — ACRM has a published lineage, its citation resolves, and its implementation is faithful

> **PROVENANCE WARNING (added 2026-09-11 by the controller after CURATE):** this document contains at least one comparison between numbers produced under different conditions (physics/harness, estimand, host + TLE archive, or paired vs unpaired). Before citing any number from it, look it up in `.scratch/RESULTS-REGISTRY.md` (conditions per row, §2 lists the cross-condition comparisons) and check this document's status in `.scratch/DOCUMENT-STATUS.md`. Text below is unchanged.

Date: 2026-09-11. Owner challenged three conclusions I had reported. **All three were wrong.**
Source: `.scratch/acrm-provenance/ACRM-PROVENANCE-2026-09-11.md`.

## What I told the owner, three times

1. *"ACRM — no counterpart, and not potential-based so Ng/Harada/Russell policy invariance
   does not apply."*
2. *"The paper's 'SASR / Shen et al.' citation could not be matched to any paper."*
3. *"The code computes `r^C = r^CF + eta*(r^CF - r^M)`, substituting `r^CF` for the paper's
   `r`, which moves the fixed point."* and *"it ran net negative — `uid_win_rate = 0.339`,
   `d_signed_mean = -1.59e7`."*

## 1. A published equivalent exists, and it is a populated family

ACRM's structure — **an auxiliary learner receives a bonus proportional to the margin by
which it beats the main learner on the same transition** — is published:

| work | form | relation to ACRM |
|---|---|---|
| **CuSP** — Du, Abbeel & Grover, **ICLR 2022, arXiv:2202.10608** | goal-generator regret `R^A(g) − R^B(g)` | **exact form match** — linear, **unclipped**, two learners, same task |
| **Sukhbaatar et al., ICLR 2018, arXiv:1703.05407** | `R_A = gamma * max(0, t_B − t_A)` | the originating, **clipped** form |
| **Hughes et al., inequity aversion, NeurIPS 2018, arXiv:1803.08884** | Eq. 3 | ACRM is precisely the **`alpha = −beta`** case |
| **Minimax Exploiter, arXiv:2311.17190** | shapes only the auxiliary agent by a measure of the main agent's performance | closest **same-purpose** match — ACRM's exact containment |

**Difference rewards genuinely are not the equivalent** — but for the right reason:
`G(z) − G(z_{-i})` is system-with versus system-without, while ACRM is learner-A versus
learner-B. **Ruling out that one family and stopping was the error**, and it was my error:
I inherited the COMA comparison from an earlier agent and repeated it without checking
whether it was the right family to be ruling out.

## 2. The citation resolves — and the sibling repo had already resolved it twice

Reference **[24] = Ma, Luo, Vo, Sima & Leong, arXiv:2408.03029, ICLR 2025**, printed in the
source thesis's own bibliography. **There is no author named Shen**; the prose is a
mis-citation, repeated in the 6-page version.

**The sibling repo had recorded this resolution twice, in June and July 2026 — before
either web search ran.** Two agents went to the web first and missed a fact that was
already in the records they were told to read. The owner's instruction to look in the old
project's documentation was correct and I should have given it first.

## 3. The implementation is faithful

The source thesis's **Algorithm 1 writes `rC <- rCF + eta * rS` verbatim.** Eq. 4.8 leaves
`r` unqualified in prose; **the pseudocode resolves it.** So there is no spec/code
discrepancy and nothing moves the fixed point relative to spec.

Worse for my version: **under the reading I asserted, at the `eta = 1.0` every recorded run
used, the mechanism would be a literal no-op.** My claimed defect would have made the
mechanism vanish, which should have been the tell.

## 4. My "it ran net negative" was a misread of a rising curve

**The catfish win rate rises 27.5% → 44-46% in all three seeds.** The `0.339` I reported is
a **pooled average over a rising curve, from one seed of three**, and `d_signed_mean`'s sign
**is not stable across seeds**. This is the four-fields failure again — I reported a number
without its estimand, and the estimand was "mean over a trajectory that was still moving".

## 5. The real, citable defect — and it is a better finding than "no counterpart"

**The conference version bounds the term and the thesis dropped it.**

`catfish-route/catfish/6pages.pdf` (logged in-repo as **unread**) uses
**`tanh(r^cat − r^actor)`**, justified as *"preventing training instability caused by large
differences."* **The final thesis removed the `tanh`.**

And the magnitude says why that matters: **the margin's mean magnitude is 1.15-1.21x the
catfish's own mean reward, max ~6x, across all three seeds. The comparison term dominates
the reward signal.**

**Six independent works bound the cross-learner term** — by clipping, binarising,
thresholding, regressing to a target, shifting to <= 0, or symmetrising. **ACRM uses none.**

ACRM is indeed **not potential-based**, so Ng-1999's necessity clause applies — but **two
published remedies exist**: Devlin 2014's Counterfactual-as-Potential, and
Harutyunyan 2015.

## What this changes for the design

**The reward-shaping leg is alive, and it is now the best-documented of the three.**

Under the three-shaping narrative (experience / reward / penalty), reward shaping was the
weak leg because I had reported it as unsupported, uncited and measured-negative. **All
three of those were wrong.** It now has: an exact-form published match (CuSP), an
originating clipped form (Sukhbaatar), a special-case identification (Hughes), a
same-purpose match (Minimax Exploiter), a resolved source citation, a faithful
implementation, a **measured** defect (unbounded margin dominating the reward by 1.15-1.21x),
the **author's own earlier bounded version** that was dropped, and **two published remedies**.

That is a stronger position than either of the other two legs, and it converts the arm from
"reproduce a mechanism with no counterpart" into: **restore the bound the authors
themselves used, and measure what it buys.** No new mechanism is claimed; the contribution
is identification, measurement and repair.

## The method failure, recorded because it will recur

The agent ran **two literature searches with different framings**. Both converged on Hughes
independently. **The credit-assignment / potential-based-shaping framing concluded "no
counterpart beyond inequity aversion"; the self-play / curriculum framing found CuSP.**

**CuSP is essentially unreachable from a difference-reward framing.** That is precisely how
the earlier audit went wrong, reproduced under controlled conditions in the same report.

**Lesson: a negative literature result is only as good as the framing that searched for it,
and one framing is not a search.** See `[[framing-determines-the-negative-result]]`.

## Addendum — the shaping is NOT contained to the catfish agent; it reaches the deployed main agent

Owner asked whether ACRM corresponds to PBRS. Checked in the sibling code, **controller-verified**:

- `catfish_faithful_familyb/trainer.py:544-555` — the ACRM-shaped reward vector is what is
  **pushed into `catfish_replay`**.
- `trainer.py:462-479` (`_maybe_intervene`) — at each intervention, `n_cf = 0.3 * batch`
  transitions are **sampled from `catfish_replay` and used to update the MAIN agent's
  `q_nets`**, carrying that shaped reward.
- `trainer.py:567-575` — under `strat_hard_discard`, the shaped reward is also pushed into the
  **main** replay.

**So the shaped reward reaches the deployed agent.** Two statements are withdrawn:
1. this erratum's "Minimax Exploiter — exactly ACRM's containment" — **the containment does
   not hold in the implementation**; it holds only in the notation `r^C`;
2. the controller's own statement to the owner that "the main agent's reward is untouched" —
   **false in effect**: 30% of every intervention batch trains the main agent on `r^C`.

(Whether the thesis intends the catfish buffer to store `r` or `r^C` is not verified here;
this is a statement about the sibling implementation.)

### ACRM is not PBRS

PBRS (Ng, Harada & Russell, ICML 1999) is `F(s,a,s') = gamma*Phi(s') - Phi(s)` — a difference
of a **state potential**, which telescopes along any trajectory and therefore cannot change
the optimal policy. ACRM's `eta*(r^CF - r^M)` is a difference of **two learners' rewards on
the same transition**; it depends on both agents' actions, is not a potential difference,
and does not telescope. **PBRS is not ACRM's lineage — it is the theory ACRM fails.**
Ng 1999's necessity result: non-potential shaping can change the optimal policy in some MDP.

Because the shaping reaches the main agent (above), **that failure applies to the deployed
policy, not just to an auxiliary one.**

### Three repairs, now distinguishable

| repair | source | what it does |
|---|---|---|
| **bound** | the authors' own conference version, `tanh(r^cat - r^actor)` | caps the term's magnitude (measured 1.15-1.21x the catfish's own reward) |
| **potential-based advice** | Harutyunyan et al., AAAI 2015 (arbitrary reward → PBA via a learned potential); Devlin et al., AAMAS 2014 (counterfactual-as-potential) — per ACRMSOURCE, not re-read by the controller | restores policy invariance |
| **containment** | the Minimax-Exploiter structure | store **unshaped** `r` for any transition that reaches the main agent; keep `r^C` only for the catfish's own update |

**Containment is the cheapest and makes the PBRS objection moot for the deployed agent**:
if the main agent never trains on `r^C`, a non-potential term can only change what the
catfish explores, which is exactly its intended role. The three are separable arms.

## Addendum — Competitive Experience Replay is the closest ARCHITECTURAL precedent (owner pointer)

**CER — Liu, Trott, Socher & Xiong, ICLR 2019, arXiv:1902.00528.** Controller-verified in the
sibling's own records: `round1-deepresearch-synthesis-2026-06-20.md:28` names it *"Closest prior
art … the sharpest threat"*; `artifacts/_codex-logs/round3-adjudication-G6-20260622T100400.md:1697`
calls it *"the closest 'competition stimulates a main agent' RL precedent"* and records a
corrected author list.

**ACRMSOURCE did find CER** (`ACRM-PROVENANCE-2026-09-11.md:623`, "different form, adjacent
purpose") **but ranked it by functional form and left it out of its summary; the controller
relayed the summary and dropped it.** At the level the thesis actually makes its claim — the
catfish *architecture* — CER is closer than any functional-form match:

| | catfish | CER |
|---|---|---|
| two learners, same task | yes | yes |
| asymmetric competitive reward | yes (`r^CF − r^M` margin) | yes (visitation-based relabelling) |
| acts through replay | yes (70/30 injection) | yes (relabels minibatches) |
| only one agent evaluated / deployed | yes (main) | yes (agent A) |

**Lineage of the reward-shaping leg, by level:**
- **architecture** (two learners, competition, replay, deploy one): **CER, ICLR 2019**;
- **functional form** (linear unclipped learner-vs-learner margin): **CuSP, ICLR 2022**; clipped
  origin Sukhbaatar ICLR 2018; Hughes NeurIPS 2018 `alpha = −beta`;
- **same containment purpose**: Minimax Exploiter;
- **the original authors' own stated analogue**: SASR (Ma et al., ICLR 2025) — structurally
  loose (Beta-posterior success-rate shaping, not two-agent);
- **theory it fails, and the repairs**: PBRS (Ng 1999); Harutyunyan 2015; Devlin 2014.
- Difference rewards / COMA remain **not** the lineage (they subtract a counterfactual
  default or system-without-i, not a second learner).

**Two design consequences:**
1. **CER relabels the evaluated agent A's own rewards.** So competition-shaped reward reaching
   the deployed agent is a **published, working design** — containment (above) is an option,
   not a requirement. Both "contained" and "uncontained" arms are now defensible by citation.
2. **CER's competition is over state coverage**, which lines up with Yang et al. (Asilomar 2023,
   coverage-not-expertise) and with the JSRL coverage sweep in flight. It suggests a
   distinct, citable catfish identity — **a coverage catfish rewarded for reaching states the
   main does not visit** — alongside the return-margin catfish. **Premise check:** CER was built
   for **sparse-reward** goal tasks (DDPG + HER); this project's reward is dense, and no
   discrete masked-DQN instance exists. Whether a coverage deficit exists here is exactly what
   the coverage sweep measures; until it returns this stays a candidate.

**Name origin, also in the sibling records** (`round3-adjudication…:1713`): "catfish effect" is a
named mechanism only in metaheuristics — Chuang, Tsai & Yang, *Catfish Particle Swarm
Optimization*, IEEE SIS 2008 — where catfish particles re-initialise the search from extreme
points **when the global best stagnates**. That is a stagnation-triggered intervention — the
same control-loop shape as CA-CPBR's collapse-adaptive coefficient and the EE-gap-adaptive
variant proposed today.

## Prior art in the sibling repo — it already built a PBRS replacement for ACRM (owner pointer)

Controller-read: `modqn-paper-reproduction/analysis/family-b-collapse-diagnosis/catfish-ca-cpbr-design-note-2026-06-24.md`,
`catfish-ca-cpbr-litcheck-findings-2026-06-24.md`, `catfish-6arm-VERDICT-G6-2026-06-25.md`;
code `archive/src-eras/demo_guided_catfish/ca_cpbr.py` (400 lines; tests archived).

**CA-CPBR = Collapse-Adaptive Competitive Potential-Based Reward**, explicitly written as
"the minimal fix" for ACRM being non-potential (§4: *"a non-potential persistent term …
= the exact ACRM flaw we are fixing"*):

- `Phi_k(s,t) = eta_k(t) * Psi_k(s)`, `Psi_k` **strictly state-only** and bounded
  (assignment entropy / occupancy spread / tail coverage);
- `F_k = gamma_CF * Phi_k(s',t') - Phi_k(s,t)`, terminal `Phi = 0`; `eta_k(t)` an exogenous
  per-round schedule so Devlin-Kudenko 2012 dynamic-potential invariance holds;
- shaping added to the **catfish's reward only**, and **§5: injected experiences carry only
  the original env reward — the shaping is STRIPPED** — i.e. the **containment** repair
  identified above, reached independently in June;
- 3-model G6 review (FIX-FIRST, folded); shaping core built with 11 unit tests, B1
  invariance validated on tabular VI **with a non-vacuous negative control**.
- Its lit-check already listed Harutyunyan 2015, Devlin 2014, Minimax Exploiter, and SASR as
  arXiv:2408.03029 — further confirming erratum 26.

**It ran once** (route-C 6-arm, 2026-06-25, family_b J_w/coverage, not clean EE): catfish
**DECORATIVE**; CA-CPBR **STRUCTURALLY INERT** — `realized_eta` identical `0.123839` across
arms 4/5/6 because the main's collapse level was constant over 4 distill rounds, so the
adaptive coupling never moved. Recorded verdict: *"grounded no-benefit; mechanism NOT
refuted (never exercised)."*

### What transfers and what does not

| part | transfers? | why |
|---|---|---|
| PBRS skeleton, exogenous schedule, invariance argument, tested code | **yes** | domain-independent, already reviewed and tested |
| **containment** (strip shaping before injection) | **yes** | exactly what the implementation audit above says is missing |
| `Psi^A` assignment entropy as the potential | **NO — wrong sign here** | rewards spreading; this physics measures `d(EE)/d(active) = -425,009.885 bit/J`, and erratum 25 found spreading EE-negative. Imported diagnostic, flipped direction. |
| collapse-adaptive `eta_k(t)` | **no, for now** | keyed on collapse, which is UNDETERMINED here (erratum 24), and it was inert when it last ran |

**Honest limit, stated in its own §4**: PBRS preserves the catfish's optimum, so the benefit
is **transient steering of what the catfish explores**, not a moved optimum. It is a weaker
lever than raw ACRM, by construction. That is the price of soundness and must be stated.

### Consequence for the reward-shaping leg

Four separable arms: **ACRM as published** / **ACRM-tanh** (authors' conference bound) /
**ACRM-contained** (unshaped `r` to main) / **PBRS** (CA-CPBR skeleton, containment kept,
`Psi` replaced by an **EE-relevant state-only potential**, no collapse coupling).

## Open, flagged unverified in the source report

AlphaStar's exploiter reward definition; Rosin & Belew's fitness-sharing formula (three
sources returned 403); Held/Florensa's "inherently unstable" analysis.
