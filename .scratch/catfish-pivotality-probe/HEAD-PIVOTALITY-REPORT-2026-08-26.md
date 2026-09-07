# Q2/Q3 Head Pivotality and One-Step EE Mediation

Date: 2026-08-26  
Status: evaluation-only checkpoint audit; no training performed

## Decision

The present three-head design is **not ready to freeze as three EE-helpful
Catfish roles**.

- Q2 is highly action-pivotal and strongly reduces inter-satellite handovers,
  so it is not an inactive head. Its paired EE effect is mixed and does not
  exclude zero with ten seeds. Keep the continuity role open, but do not claim
  that the present identity-only handover penalty improves EE.
- Q3 is action-pivotal less often but reliably performs its stated load-
  balancing job. That job currently opens more beams and raises power enough
  to reduce EE. The present `r3 = -U_b` direction should not survive the next
  design freeze unchanged.

The next design should keep three distinct physical roles but align all three
with one EE improvement criterion:

1. R1: direct link/system-EE exploitation.
2. R2: temporal continuity EE, with physical handover lost-time and energy
   cost represented in the system numerator/denominator.
3. R3: spatial activation-aware EE, balancing load only when its throughput
   and interference benefit exceeds the marginal beam-power cost.

## Estimand and safeguards

For each frozen evaluation seed and pre-decision state, the deployed greedy
joint action was compared with two renormalized ablations:

- without Q2: `(0.5, 0.0, 0.2) / 0.7`;
- without Q3: `(0.5, 0.3, 0.0) / 0.8`.

`full - ablated` is the reported head effect. Positive `Delta EE` therefore
means that including the head helped immediate system EE.

All alternatives used an identical copy of the pre-step environment RNG and
the same environment state. Alternatives produced only current-slot physics;
they did not build a next observation or advance a trajectory. Only the full
policy action advanced the episode. At all 100 evaluated steps, the full
preview exactly matched the subsequently committed step for reward, link
power, SINR, rate, radiating beam identity/power, interference, handover class,
and system EE.

Artifact under test:

- checkpoint episode: 8999;
- checkpoint SHA-256:
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`;
- evaluation seeds: `2026082401` through `2026082410`;
- 100 users, 10 steps per seed, 10,000 user-decisions total;
- result receipt:
  `main-final-seeds-10-v1.json`;
- result SHA-256:
  `f98e2d01212b79a9e09d39ced9a205644d3bca47951a3508a419d213037f8124`.

## Results

Mean deployed-policy EE was **90.524 Mbit/J**, matching the prior 90.52
Mbit/J replay result.

| Quantity | Q2 included vs removed | Q3 included vs removed |
|---|---:|---:|
| Physical action pivotality | 60.25% (6,025 / 10,000) | 7.72% (772 / 10,000) |
| Mean `Delta EE` | -2.156 Mbit/J | -0.765 Mbit/J |
| Percent of deployed EE | -2.38% | -0.85% |
| Seed-level 95% t-CI | [-5.415, +1.103] Mbit/J | [-1.265, -0.265] Mbit/J |
| Seeds with negative `Delta EE` | 7 / 10 | 8 / 10 |
| Mean `Delta throughput` | +2.776 Gbit/s | +0.810 Gbit/s |
| Mean `Delta system power` | +39.921 W | +10.028 W |
| Mean `Delta active beams` | +7.52 | +1.70 |
| Mean `Delta sum(load^2)` | -36.74 | -7.11 |

The confidence intervals treat the ten matched seeds as the independent
paired units; the 100 time steps are not incorrectly counted as 100
independent replicates.

### Q2 mediation

Including Q2 reduced inter-satellite handovers by 50.72 per step on average,
increased service fraction by 0.86 percentage points, reduced load
concentration, and raised throughput. It also activated 7.52 more beams and
used 39.92 W more. The resulting EE direction varied by seed. This is strong
evidence that Q2 controls actions and continuity, but not evidence that the
current handover reward is an EE-improving Catfish.

### Q3 mediation

Including Q3 reduced `sum(load^2)` in every seed and increased active beams,
throughput, and power in every seed. It therefore does what `-U_b` asks:
spread users over less-loaded beams. The failure is objective alignment, not
head inactivity. In this power model, activating extra beams incurs fixed and
PA supply cost; the throughput gain was insufficient, giving a paired EE
loss whose 95% interval excludes zero.

## Next formula gate

The coherent three-Catfish candidate is a common marginal-EE test over three
physical axes. A useful screening quantity is the fractional-programming
improvement score

`g_eta = Delta R_system - eta_ref * Delta P_system`,

where `eta_ref` is frozen or lagged rather than fitted after observing the
same candidate outcome. `g_eta > 0` is the local condition that the candidate
can improve EE around the reference operating point.

- R2 candidate reward: apply `g_eta` to the physical throughput lost during
  handover interruption and the signaling/access energy added by a handover.
  Those terms must also enter the system EE numerator/denominator; otherwise
  R2 remains only an identity preference with no direct EE mechanism.
- R3 candidate reward: apply `g_eta` to load/interference throughput gain and
  the **marginal** beam cost. Reusing an already-active beam pays only its
  incremental max-power cost; opening a new beam pays activation, fixed, and
  PA supply cost. This prevents unconditional beam proliferation.

This is a design direction, not yet a frozen formula. Before implementation
or training it still needs defensible `T_HO`/`E_HO` parameters, a decision on
`eta_ref`, a state-sufficiency check for the temporal terms, and a data-blind
action-level falsifier. No new long training should start before those four
items close.

## Claim ceiling

The analysis code hash differs from the code hash recorded at training time
because this post-run probe adds a non-mutating evaluation seam and because
the working tree contains later audit changes. The checkpoint, weights,
reward configuration, frozen TLE contract, and baseline replay are verified,
and the committed baseline step matched its preview at every comparison.
These results support a current-source checkpoint design decision; they are
not a byte-identical replay of the original launched source tree.
