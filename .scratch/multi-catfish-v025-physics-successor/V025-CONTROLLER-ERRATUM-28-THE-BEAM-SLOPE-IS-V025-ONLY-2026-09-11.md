# Erratum 28 — the −425,009.885 bit/J-per-beam slope belongs to the V0.25 panel, not the MODQN harness; and my ÷U inference was wrong

> **PROVENANCE WARNING (added 2026-09-11 by the controller after CURATE):** this document contains at least one comparison between numbers produced under different conditions (physics/harness, estimand, host + TLE archive, or paired vs unpaired). Before citing any number from it, look it up in `.scratch/RESULTS-REGISTRY.md` (conditions per row, §2 lists the cross-condition comparisons) and check this document's status in `.scratch/DOCUMENT-STATUS.md`. Text below is unchanged.

Date: 2026-09-11. Source: `.scratch/ee-magnitude/EE-MAGNITUDE-RECONCILIATION-2026-09-11.md`
(bridge script and output alongside).

## 1. The beam slope was applied to the wrong physics

I repeatedly used `d(EE)/d(active) = −425,009.885 bit/J` per added active beam as a property of
"this physics" in arguments about the **MODQN harness**: that CA-CPBR's assignment-entropy potential
has the wrong sign here; that a per-satellite beam cap could raise EE on its own (in the CAPPENALTY
brief); and in several statements to the owner ("每多開一個波束 EE 就掉 425,009 bit/J").

**That slope comes from the V0.25 a-r0 time-division path, not the MODQN harness.** On the MODQN
harness each beam carries the full band and costs roughly the same power whatever its load, so
**beam count cancels at first order**: `EE ≈ bandwidth × spectral efficiency ÷ power per beam`
predicts 93.6 against 93.1 measured for the trained checkpoint.

**What is withdrawn** (for the MODQN harness only):
- "spreading is EE-negative here" **as a consequence of that slope**;
- "CA-CPBR's entropy potential has the wrong sign here" — now **unsupported**, not refuted;
- "a beam cap could raise EE by removing fixed and PA power" — EEGAP finds the cap does not raise
  EE at first order on this harness.

**What stands**, because it came from the MODQN code itself (erratum 25): `R_beam = B · mean SE`
(occupancy reaches the numerator through mean spectral efficiency), and interference is
activation-gated and load-unweighted (lighting a beam costs every co-channel user SINR). Their net
sign on the MODQN harness is **not measured**.

### Correction to section 1, same day (CAPPENALTY, measured)

"A beam cap is not expected to raise EE at first order on the MODQN harness" is **half right**.
CAPPENALTY measured a per-satellite cap of 3 on this harness (96 evaluation episodes, one training
seed): **joules per beam-step flat within 0.7%** — the power half holds — but **interference per
served user falls 7-9x, so spectral efficiency and bits per beam rise 17-28%**. Pooled EE rises
**1.162x** (103,295,432.52 vs 88,894,962.36 bit/J), with **only 58% of user-steps served and
delivered bits at 0.48x**. The OFF weights alone, dropped into the capped environment, gain +27.5%.

So on the MODQN harness **fewer lit beams raise pooled EE through the interference term in the
numerator**, not through power. Consistent with FEASFRONT's `B1_NO_NEW_BEAM` (37.9 beams, served
0.9978, 103.47M vs the learner's 93.11M). **The interference channel of erratum 25 is now measured,
not just argued.** And it carries a warning the whole design must keep: **pooled EE without a service
floor rewards darkening beams and dropping users** — which is exactly what the declared C-S service
guard exists to block. Every EE figure is reported with served fraction beside it.

## 2. The ÷U reading was wrong for every cited sibling number

I told the owner the sibling's reported EE might be system EE ÷ U, making the true gap "hundreds of
times". **Wrong for every cited figure.** The ÷U form is in the sibling's code only since
2026-08-05 (commit `60807490`); every cited number (146-493, 609) dates from 2026-07-11 to 07-21, when
the formula was `eta_u = R_u / (P_beam / N_beam)` (rev `0082683d`). Users-per-beam cancels; the
estimand is ≈ served fraction × RF-only system EE — measured at 0.98x (trained) and 0.93x (random)
the RF-only ratio of sums.

## What actually separates the numbers

**The denominator.** The sibling's July EE divided by **radiated RF power only**; this project divides
by **consumed** power (PA supply, per-beam circuit, per-satellite baseband). On this project's own
runs, consumed is **7.60x** radiated.

**Bridge, measured** (placebo exact: random 53,060,175.56 reproduced): this project's trained
checkpoint scored with the sibling's July formula reads **693.87**; the random policy reads **373.61**.
Chain: 93.11 → x7.602 (radiated-only denominator) → 707.82 → x0.980 (per-user average) → 693.87.
**A formula comparison, not a project ranking** — the environments still differ (67.9 active beams at
1.48 users/beam here; 9-12 beams at ~8.5 users/beam in the sibling's healthy runs).

Same on both sides: 166.67 MHz per beam, U = 100, Shannon rate law, full buffer.

## The sibling's collapsed baseline

Correcting only the learning rate (0.01 → 0.001) lifts plain baseline MODQN to **428.60** (6 seeds)
and **493.18** (3 seeds). The best sibling methods reach **609-620** (~25-45% above); the
**catfish-argmax arm is 477, at the corrected baseline's level.** The "hundreds" came from the
estimand, the denominator and the learning rate; method gains are real but smaller, and the catfish
arm's gain was not among them. The collapse itself was mostly a served-fraction penalty.
