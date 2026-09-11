# Erratum 26 — ACRM has a published lineage, its citation resolves, and its implementation is faithful

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

## Open, flagged unverified in the source report

AlphaStar's exploiter reward definition; Rosin & Belew's fitness-sharing formula (three
sources returned 403); Held/Florensa's "inherently unstable" analysis.
