# Declaration — two demonstration-utilisation arms, one demonstrator

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

## Cost note

Three arms x seeds is a real training bill. The episode budget and seed count are not set
here; they are set once CATFISHSURFACE returns the measured per-episode cost, and the
owner is notified before any 9000-episode continuation.
