# Amendment 1 to the three-catfish pilot declaration — pre-result

Date: 2026-09-11. Amends `V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md`.
**Written before any pilot training or evaluation result exists** (CF3PILOT had built only
`cf_sources.py`; nothing had run on `sat`). Prompted by an external review (`gpt3.md`, owner-supplied),
checked point by point; six of its eight points accepted, one refined, one recorded as caveat.

## Accepted

1. **`gamma = 1.0` for A1/A2/A3** (true terminal at the 10th step). The endpoint is an undiscounted
   10-step pooled ratio and `eta` is updated from undiscounted sums; the original "gamma as in the
   baseline, 0.9" optimised a discounted ratio instead — an internal inconsistency I introduced.
   ASK-1 had already recommended gamma = 1. **If the observation carries no step index, append a
   normalised remaining-steps feature for A1-A3 only** (finite-horizon values depend on time left);
   state which in the addendum. A0 keeps eq. (16) with gamma 0.9, unchanged.

2. **Common vector replay, not exclusive routing.** Every source transition carries the full
   `(B, E, H)` and **trains all three heads**. Exclusive routing (C1 → `Q_B` only, etc.) would have
   given each head a different state-action support, so `Q_B − eta Q_E − lambda Q_H` would combine
   components describing different action sets — the same incoherence as independently-optimal
   heads (DR-1). **Minibatch: 8/9 main replay + 1/27 each from C1, C2, C3** (total source fraction
   1/9; integerisation stated in the addendum). **The one-to-one C1↔`Q_B`, C2↔`Q_H`, C3↔`Q_E` is the
   objective each catfish specialises in, not a data restriction.** Per-catfish contribution is
   attributed later by drop-one arms. The 1/9 total is a Nair et al. reference, not a validated
   per-head value; recorded as a project choice.

3. **`eta` held at `eta_0` for the first 500 episodes**; first update at episode 500, after the
   declared learning check passes; then at 750. `lambda` dual ascent unchanged.

4. **Pinned-archive re-measurement of the sources before launch** (no training): `TRAINED`,
   `A m=2dB`, `A m=12dB`, `B1_NO_NEW_BEAM`, `RANDOM_MASKED` on the pinned archive `427e6a91…`,
   reporting pooled EE, `H_inter`, served, active beams, joules. FEASFRONT/CFSCREEN ran on the
   unpinned archive. **Reported before launch; it does not block launch** unless a source violates
   C-S or C-H on the pinned archive, in which case stop and report.

5. **C2 activation diagnostics, pre-declared.** Likely `lambda` stays 0 because every known policy is
   under 0.6016 inter-satellite. Report the `lambda` trajectory, the fraction of episodes with
   `lambda > 0`, and the fraction of evaluation decisions whose argmax changes when the `Q_H` term is
   removed. **If `lambda` is 0 throughout and removing `Q_H` changes < 1% of decisions, C2's head is
   classified INACTIVE in this pilot** — a reporting classification, not a gate; then an A2 win does
   not count as all three catfish being active. C-H stays at 0.6016 — **not lowered to make C2 bind.**
   (With common replay, C2's transitions still train `Q_B` and `Q_E`, so C2 still acts as a data
   source even if its head is inactive.)

6. **Isolated worktree**: branch `cf3/pilot-20260911`, worktree `/home/u24/papers/mcrl-leo-handover-cf3`,
   based on `363845e8`. The shared tree is read-only for CF3PILOT. `cf_sources.py` moves there.

## Refined

7. **`Q_E` credit — keep equal share tonight, and here is why the obvious fix is unsafe.**
   `E_u = P_sys*dt/U` gives every user the same energy label, so `Q_E` sees a team signal (the review
   is right; consistent with C3's weakest representability, 0.714). But the suggested beam-attributed
   split (beam energy shared among the beam's users) gives an **unserved user zero energy**, so an
   outage scores `0 − eta*0 = 0` while a served user on a poor beam can score `B − eta*E < 0` —
   **the outage free ride returns in a new form.** Equal share keeps outage costing `−eta*E_u`.
   Tonight: equal share, plus a **no-training diagnostic**: holding the other users fixed, switch user
   u from its incumbent to C3's action and record the distribution of `ΔE_sys`. If most local
   contrasts are near zero, a negative C3 result is **uninterpretable as "C3 fails"** and is reported
   so. Attribution with an explicit outage charge is next version.

## Recorded as caveat

8. **Naming.** This pilot is a **three-source catfish-inspired off-policy replay pilot**: scripted
   behaviour sources, raw rewards, uniform mixing, no imitation loss, no n-step, no PER, no ACRM, no
   EE-threshold stratification, no asymmetric discount, no 70/30 intervention. It tests whether three
   directed sources beat three random sources as replay data. **A positive result is not evidence
   for faithful RIS catfish, DQfD, or ACRM**; those are later comparison arms.

## Pre-launch tests added

Source parity with FEASFRONT (A m=2/12, B1); `sum_u B_u` and `sum_u E_u` equal the system totals;
the three heads share the same continuation action; source environments do not perturb the main
environment's RNG; A1 and A2 main rollouts bit-identical before the first source sample; NULL3 is
uniform over legal actions; source fractions exact and reproducible; checkpoint resume does not
repeat episodes; `eta`/`lambda` change only at declared boundaries. Plus a 100-episode diagnostic
(Q-scale per head, share of each term in the transformed Q, C2 activation, CF3 vs NULL3 batch
composition) before the full launch — a check, not a result.

## Unchanged

Arms A0/A1/A2/A3, 3 seeds, 1000 episodes, final checkpoint, per-episode reseeded evaluation if pure
harness (else unpaired), the ep-500 early-stop rule, C-H 0.6016, C-S −0.5 pp, and the declared reading.
