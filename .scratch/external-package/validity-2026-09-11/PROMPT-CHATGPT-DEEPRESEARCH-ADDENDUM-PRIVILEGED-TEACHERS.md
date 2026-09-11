# Deep Research addendum — can demonstration mechanisms (DQfD, the "catfish" line) be kept as a way to distil privileged teachers into a per-user policy?

Paste into the same ChatGPT Deep Research conversation after the first report, or into a new one with the package attached
(read `README.md` for the setting).

## Context (new since the first prompt)

- The 12-run pilot showed that three rule-based demonstration sources mixed into replay (static pools, 15 of 128 minibatch
  rows, no imitation loss) helped no more than random-policy pools of the same size: directed vs random +0.78 % pooled EE
  (noise at 3 seeds); any off-policy pool +2.6 % over no pool; every learned arm 5–8 % below a one-line hysteresis rule on
  the same episodes.
- Physics: consumed joules are nearly constant per lit beam, so pooled EE ≈ bits delivered per lit beam. Whether a user's
  choice lights a new beam, or lowers a shared beam's mean spectral efficiency, depends on other users' same-step choices,
  which a per-user policy cannot see; an equal-share energy label cannot credit it.
- A centralised search (joint decisions, realised counterfactuals — privileged information the deployable per-user policy
  does not have) is being measured as a lower bound on the one-step optimum. If it finds room above the rule, the next design
  treats such searches, and intermediate "oracles" (a simultaneous best response with an exact difference reward; a
  sequential sweep where later users see earlier users' choices), as **teachers**, and the deployable per-user policy as the
  **student**. The demonstration mechanism (DQfD-style large-margin loss, or the competitive "catfish" replay) would then be
  the distillation channel, and the student's credit would be a difference reward.

## Questions (for each: citations with authors / venue / year / DOI or arXiv id, the relevant number, and what you could not verify; two independent search framings per question, listed)

1. **Distilling privileged teachers into students with less information.** Teacher–student learning where the teacher sees
   privileged state (e.g. "Learning by Cheating" — Chen et al., CoRL 2019; asymmetric actor-critic — Pinto et al. 2017;
   learning using privileged information — Vapnik; DAgger — Ross et al. 2011; the "imitation gap" and ADVISOR — Weihs et al.
   2021; teacher-guided RL). Verify each. What does the literature report about the **imitation gap** when the teacher's
   decisions depend on information the student lacks, how much of the teacher's performance students retain, and which
   methods close the gap (DAgger with a privileged expert, adaptive insubordination, TD fine-tuning after imitation)?
2. **DQfD-style margins toward a teacher that is better than the learner but privileged.** Known failure modes (the margin
   anchors the student to actions it cannot justify from its own observation; imperfect demonstrations), and remedies
   (Q-filter — Nair et al. 2018; advantage-gated or annealed margins; POfD — Kang et al. 2018; normalized actor-critic).
   Is DQfD + a centralised teacher + decentralised student reported anywhere?
3. **Centralised expert → decentralised policies in multi-agent systems.** Imitation of a centralised planner/solver by
   per-agent policies (MARL, CTDE-with-imitation, "centralised teacher, decentralised execution"), including wireless
   examples (user association, beam management, power control distilled from optimisation solvers). What fraction of the
   solver's objective do the distilled per-agent policies reach?
4. **Difference rewards / counterfactual credit in wireless resource allocation** (user association, beam selection,
   power control): papers, measured gains over equal-share or global rewards, and the cost of computing the counterfactual.
5. **The "catfish effect" in RL**: peer-reviewed papers (beyond a master's thesis) on a competitive "catfish" agent that
   injects experience into a main learner; what exactly was measured, in which reward regimes; any dense-reward results.
6. **Multiple teachers.** Multi-teacher policy distillation (e.g. policy distillation — Rusu et al. 2016; Actor-Mimic —
   Parisotto et al. 2016; mixtures of experts). Is there a principled criterion for **how many teachers** to keep (Pareto
   non-dominance, behavioural diversity on shared states, marginal value in ablation), and evidence that redundant teachers
   hurt?
7. **Beam sleep and power control as EE levers in multi-beam LEO**: reported EE gains at full service versus assignment-only
   policies (this decides the fallback if the centralised search finds no room).

## Deliverable

A structured report (English, with a Traditional Chinese executive summary), one table per question (paper, year, venue,
setting, what was measured, number, condition), and a final section: (a) is "privileged teachers distilled via a
demonstration margin into a per-user student with a difference-reward credit" a recognised pattern, and under what name;
(b) what retention fraction is realistic; (c) which of DQfD / catfish competitive replay / DAgger-style correction fits a
dense-reward, 10-step, 28-action problem best; (d) what a referee would demand.
