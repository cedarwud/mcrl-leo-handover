# ACRMSOURCE progress — COMPLETE 2026-09-11

Report: `ACRM-PROVENANCE-2026-09-11.md` (same directory).

- [x] Part 1: sibling repo documentation sweep
- [x] Part 1.4: implementation formula at all three computation sites
- [x] Part 1.5: recorded ACRM run, numbers recomputed at source, 3 seeds
- [x] Part 2: published analogue families
- [x] Part 3: "SASR / Shen et al." resolved
- [x] Report written

## Answer

**A published equivalent exists.** All three of the prior audit's conclusions were wrong.

1. **Citation resolves.** Source thesis reference [24] = Ma, Luo, Vo, Sima, Leong,
   "Highly Efficient Self-Adaptive Reward Shaping for RL", arXiv:2408.03029, ICLR 2025.
   No author named Shen. The prose "Shen et al." is a mis-citation internal to the
   source (repeated in its 6-page version); both bibliographies say Ma.
   The sibling repo had already resolved this twice (2026-06-24 and in 05-provenance.md).

2. **Published equivalents exist**, in the two-learner-margin family:
   - CuSP regret `R^A(g) - R^B(g)` — Du/Abbeel/Grover, ICLR 2022, arXiv:2202.10608.
     Exact form: linear, unclipped, two learners, same task. CLOSEST MATCH.
   - Sukhbaatar et al. `R_A = gamma*max(0, t_B - t_A)` — ICLR 2018, arXiv:1703.05407.
     Originating form, clipped.
   - Hughes et al. inequity aversion — NeurIPS 2018, arXiv:1803.08884. ACRM is the
     alpha = -beta case.
   - Minimax Exploiter — arXiv:2311.17190. Closest SAME-PURPOSE match.
   Difference rewards (Wolpert-Tumer) are NOT the equivalent: G(z) - G(z_-i) is
   system-with vs system-without; ACRM is learner-A vs learner-B.

3. **Implementation is faithful.** Source thesis Algorithm 1 literally writes
   `rC <- rCF + eta*rS`. The prior "substitutes r^CF for r" reading would make the
   mechanism a no-op at the eta=1.0 every run used.

## New findings not in either prior audit

- `catfish-route/catfish/6pages.pdf` (recorded in-repo as unread): the conference
  version uses `r^S = tanh(r^cat - r^actor)` "preventing training instability caused
  by large differences". The final thesis dropped the tanh.
- Measured: margin mean magnitude = 1.15-1.21x the catfish's own mean reward,
  max ~6x. The unbounded margin dominates the reward signal.
- Six independent works in the family all bound the cross-learner term; ACRM uses none.
- The recorded run's catfish win rate RISES 27.5% -> 44-46% across all three seeds;
  the prior audit's quoted 0.339 is a pooled average over a rising curve, one seed
  of three, and the sign of d_signed_mean is not stable across seeds.
- ACRM is not potential-based (Ng-1999 necessity clause); two published remedies
  exist (Devlin 2014 CaP; Harutyunyan 2015).

## Method note worth keeping

Two literature searches with different framings converged on Hughes but diverged on
the headline: the credit-assignment/PBRS framing concluded "no counterpart beyond
inequity aversion"; the self-play/curriculum framing found CuSP. **This precedent is
unreachable from a difference-reward framing.** That is exactly how the prior audit
went wrong.

## Open items (stated as unverified in the report)

- AlphaStar exploiter reward definition (Nature appendix unread).
- Rosin & Belew competitive fitness sharing formula (three sources returned 403).
- Held/Florensa "inherently unstable" analysis (only Sukhbaatar's footnote paraphrase found).
- Whether 6pages.pdf corresponds to any published venue.
