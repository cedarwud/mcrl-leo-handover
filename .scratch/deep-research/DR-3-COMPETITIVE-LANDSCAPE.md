# DR-3 — What does the field actually report, what would a referee expect, and is there a contribution left?

*Paste `00-EVIDENCE-LEDGER.md` above this.*

This project has never checked itself against the field. Its declared win gate is an
internal one (its own MODQN baseline), which is legitimate for a controlled ablation but
tells us nothing about whether the numbers, the baselines or the claim would survive
review.

## 1. What do published LEO/NTN beam-handover and resource-allocation papers report?

- **Energy efficiency values**: what magnitudes appear, in what units, and how is EE
  defined in each — a ratio of sums, a mean of per-user ratios, bits/Joule, bits/Hz/Joule?
  **Is the ratio-of-sums vs mean-of-ratios distinction respected in that literature, or
  routinely elided?** This matters because two definitions here differ by only 0.06% on
  one panel but are conceptually different estimands.
- **Baselines**: what do those papers compare against? How often is the comparator a
  trivial rule (max-SINR / max-RSRP / nearest-satellite / greedy), and **how often does the
  trivial rule win**? A referee will ask why a learned policy is needed if `MAX_NOMINAL_GAIN`
  beats it by 19.8% on the declared metric — find out whether that embarrassment is common
  in the field or unusual.
- **Handover rates and service metrics**: what is reported, and at what operating points?
- **Multi-objective handling**: is fixed linear scalarisation (`w1*r1 + w2*r2 + w3*r3`) the
  norm? Does anyone report that their scalarisation is **anti-aligned** with their own
  declared endpoint? Is there published criticism of fixed scalarisation for
  energy-efficiency objectives specifically?

## 2. Demonstration-guided RL in wireless / satellite resource allocation

- Has anyone applied **DQfD or its family** (offline RL, advantage-weighted regression,
  guide-policy bootstrapping, constrained RL) to wireless resource allocation, beam
  management or handover? What was the demonstrator, and what did it buy?
- Specifically: any case where the **demonstrator is an optimisation solver or a heuristic
  rule** rather than a human or a prior policy. What is that called in this literature, and
  what are the reported gains?
- Any case where the demonstrator is **expert on one objective and violates a constraint** —
  which is this project's exact situation.

## 3. The "catfish" line

- The source is an RIS/CDRL paper describing a training-time experience-stimulation
  mechanism under the name "catfish" (solver-seeded replay memory, EE-threshold buffer
  separation, asymmetric discounts, periodic 70/30 batch intervention, a competitive
  reward `r^C = r + eta(r^CF − r^M)`). **Does this line have any independent replication,
  citation or follow-up at all** — by other groups, in other domains, or in later work by
  the same authors?
- Its competitive-reward term cites "SASR / Shen et al."; that citation could not be
  matched to any paper. **Find out what it refers to, or establish that it does not
  resolve.**
- Is "catfish effect" used as a mechanism name anywhere else in the RL literature, and does
  it mean the same thing?

## 4. Novelty — answer honestly, including "no"

Multiple heterogeneous demonstrators, Q-filtering of imitation losses, imperfect-
demonstration filtering, demonstration-guided multi-objective RL, and constrained MORL are
**all published**. Given that:

- **Is there a defensible contribution here?** State it in one sentence if there is.
- If the honest answer is that the contribution is **the integration and the measurement**
  rather than any new mechanism, say so, and say what a paper of that shape needs to carry
  to be publishable — how many baselines, what ablations, what statistical treatment, what
  venue.
- A second candidate contribution is the **negative result itself**: that a trivial rule
  beats a trained multi-objective policy by 19.8-22.2% on the declared energy-efficiency
  endpoint because the training scalarisation prices a handover that costs zero joules.
  **Is a result of that shape publishable in this field, and where?** Find precedents for
  negative or diagnostic results in wireless RL.

## 5. What would a referee kill this on?

List the objections a reviewer of a good venue would raise, ranked, given everything in
the ledger — the simulator's zero-joule handover, the 30 s decision interval, the
`max`-over-users beam power, the single-simulator evaluation, the seed counts, the fact
that two of three reward heads have premises that fail inside the model. **For each, say
whether it is fatal, fixable, or answerable in text.**

## Output

Cite everything. Be concrete about numbers so the project can see where it sits in the
distribution. Where the field's practice is weaker than this project's own standards, say
that too — it is relevant to how the results should be framed.
