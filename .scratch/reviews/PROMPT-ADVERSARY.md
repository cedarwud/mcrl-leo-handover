You are a hostile but fair peer reviewer with no prior involvement in this project. You have one
directory of evidence, `./evidence/` (read `./evidence/README.md` first). Your job is to argue
AGAINST a proposed paper narrative, using that evidence.

# ADVERSARY — attack the proposed narrative

## The proposed narrative

A learned handover / beam-assignment method for multi-beam LEO satellites targets **system energy
efficiency (EE = pooled decoded bits / pooled system joules)**. It has three learned routes.

1. Each route ("Catfish") optimises its **own reward**; each reward is directed toward raising EE via
   a different mechanism. One proposed decomposition: a **bits side** (per-user link quality), an
   **energy side** (beam concentration — how many beams the population opens), and a **time side**
   (persistence / avoiding handover).
2. **Necessity condition**: each route on its own must raise EE (under a service guard); a route that
   cannot is not a meaningful component.
3. Because objectives conflict, **combining routes involves trade-offs**, and the trade-off is between
   **EE and service quality** (served users, rate-target attainment), not EE against EE; the method's
   value is reaching Pareto points no single route reaches. Offered example: an energy-side
   configuration at 46.11 Mbit/J with 2.5% rate-target attainment versus a link-side configuration at
   41.62 Mbit/J with 24.75% attainment, both serving all users — a non-dominated pair.
4. The combination rule must be ratio-consistent (Dinkelbach-style), not a fixed linear weighting,
   because a measured result shows no single linear price orders configurations by EE.

Acknowledged by the proposers: the narrative was developed in an extended conversation, turn by turn,
and may have been shaped by that process; the decomposition in (1) was proposed partly because it maps
onto measurements already in hand. The baseline is a multi-objective DQN whose reward already has three
components: **r1 = EE** (per-link, summing to system EE), **r2 = -Psi** (handover), **r3 = -U**
(negative beam occupancy, load balance).

## Argue against it, as specifically as you can

- **Circularity / outcome-fitting**: is the decomposition chosen because it makes the necessity
  condition pass? Is redefining a route's job (e.g. calling the interaction route an "energy side"
  route) justified independently of its effect?
- **Consistency with the evidence**: does the evidence show each route alone raising EE? Genuine
  trade-off rather than redundancy between routes? Is the offered Pareto pair evidence about *routes*,
  or only about two non-learned configurations?
- **The single-judge problem**: if EE is the sole primary metric, when is "a combination worse than
  its best constituent" a legitimate trade-off rather than a loss?
- **Relation to the baseline**: the baseline already has EE, handover and load objectives. Is the
  method distinguishable from the baseline's own multi-objective structure? Does r3 (a spreading term)
  conflict with EE in this physics, and what follows?
- **What a reviewer would demand** before accepting it, and **what it must not claim**.
- If some version survives your attack, say which and why — but do not soften the attack to get there.

## Standards

Separate what the evidence **establishes**, **suggests**, and **your inference**. Distinguish
learner-free from trained-model results and in-sample from out-of-sample. Mark literature you cannot
verify. Run no experiments.

Write to `./ADVERSARY-REVIEW.md`, first line one bolded sentence giving your verdict (reject / major
revision / minor revision) and the single most damaging flaw; then your full review.
