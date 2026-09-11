# Plan — three catfish on three Q-heads, with physics-corrected targets

Date: 2026-09-11. Controller recommendation to the owner. Authorises no run by itself;
each stage is gated on the one before.

## The choice

Neither "return to the old project's design" nor "continue C1/C2/C3 as developed".

- **Keep the C1/C2/C3 picture**: three catfish, each attached to one Q-network. This is also
  the old project's CA-CPBR structure (N = 3, one per MODQN head).
- **Correct what each head means**, from this project's measurements:

| name | originally | corrected to | Q-head | catfish (experience source) |
|---|---|---|---|---|
| **C1** | EE | EE numerator | `Q_B` expected bits | bits specialist — `MAX_NOMINAL_GAIN` (1.146x the learner's bits) |
| **C2** | handover | handover as a **constraint** | `Q_H` expected handover cost | handover guard — hysteresis rule |
| **C3** | load balance | load's physical channel is **energy** | `Q_E` expected joules | energy specialist — beam consolidation |

  Deployment: `argmax_a [Q_B − η Q_E]` subject to `Q_H` within a declared cap; `η` by
  Dinkelbach outer iteration. All three heads bootstrap from the **same** continuation action
  (the B0 per-head-bootstrap fix is what makes this coherent).
- **Borrow the machinery** from the old project and the literature: experience seeding
  (DQfD family), competitive shaping (CER / CuSP lineage; ACRM with containment, tanh bound, or
  PBRS — the old CA-CPBR skeleton), stagnation-triggered intervention (Catfish PSO / CA-CPBR,
  re-keyed on the EE gap). The representation penalty stays an orthogonal factor.

**Dead and not revived**: the stage-C C1/C2/C3 that decompose `F` into
unilateral/continuation/interaction and serve as supervised labels (C1VSGAIN, row 3).

## Amendment after FEASFRONT and HARVEST (same day)

The three catfish now have **measured sources, distinguished by information set** (HARVEST's
framing, independently matching this plan):

| catfish | source | information set | measured |
|---|---|---|---|
| **C1** C-gain | `MAX_NOMINAL_GAIN` / `A m=2dB` | gain only (block 2) | frontier, highest EE |
| **C2** C-hold | `A m=9dB` / `A m=12dB` | gain + incumbent memory (blocks 1-2) | frontier; dominates the learner on EE, handover and its own objective |
| **C3** C-consolidate | `B1_NO_NEW_BEAM` / `B2` | previous-step loads (block 4) | dominated on the frontier, but the **only** source reaching few-beam, low-joule states (37.9 beams, 0.57x joules) — its case is coverage (Yang, Asilomar 2023), not expertise |

C1 and C2 are claimed mutually non-dominated and differing by information set; CFSCREEN measures
whether that holds on actions and states, and representability of each from the learner's own
observation. **Diagnostics, not gates.**

Also from HARVEST: several old catfish negatives are contaminated in ways absent here — lr = 0.01;
the per-satellite hard cap; a mean-of-ratios estimand; **"best checkpoint" selected on the
uncalibrated `0.5 * r1` scalar, often very early (the faithful catfish was scored at episode 99 in
all three seeds)**. The penalty with a large recorded sibling effect was the **capacity penalty**
(+89 to +135, 6/6 seeds), which acts on users bumped by the hard cap; decorrelation/srank never ran
there. ACRM for C-learner arms computes `r^CF − r^M` on `B − eta E`, not on `r1`.

## Stages

| stage | what | gate to pass | status |
|---|---|---|---|
| **0** | B0 defect fixes; FEASFRONT (room for a learner; does an energy specialist exist); CAPPENALTY; HARVEST | B0 clean; learner on or near the frontier | **in flight** |
| **1** | single-head `Q_eta` Dinkelbach learner on B0, **no catfish** | trains stably; report whether fixing the objective alone closes the 22% gap | next |
| **2** | three heads + three catfish, each with its own null control; drop-one ablation | each catfish separates from its null on pooled EE | after 1 |

**Stage 1 is the honest reference.** If the corrected objective alone closes most of the gap,
the catfish's job shrinks to sample efficiency — still a publishable secondary contribution
(ASK-3), but it must be reported as such.

## Owner decisions this plan needs

1. **Endpoint**: pooled EE **subject to** a handover cap. Required for C2 to have a job. The cap
   must be declared, not derived (no 3GPP ceiling exists); citable precedent for declaring one:
   `H̄ = 0.004` per 0.2 s epoch → 0.6016 per 30.08 s step.
2. **Names**: keep C1/C2/C3 with a stated redefinition, or rename to CF-B / CF-H / CF-E.
3. **Kill the 44 SIGSTOPped current-design trainings** (row 3, awaiting permission).

## What can still kill it

- FEASFRONT shows a simple rule with memory already dominates the learner → no job for any catfish.
- No energy specialist distinct from `MAX_NOMINAL_GAIN` exists → C3 collapses into C1; two catfish, not three.
- Stage 1 closes the gap → catfish reduced to sample-efficiency.
