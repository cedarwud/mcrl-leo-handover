# Controller check of the agy blind audit (`VALIDITY-AUDIT-AGY-BLIND-2026-09-11.md`)

Date: 2026-09-11 ~12:40 UTC. The agy run (Gemini 3.8 Flash (High)) took ~10 minutes and produced a 380-line
report with verdict **DEAD-PATH**. Before relaying it, the controller checked its numbers and citations against the
artefacts it claims to have verified. Result: **the structural arguments are the ones already written in the
controller's pre-result forecast (blind spots A/B/C), and the quantitative support labelled [V] is in several places
wrong or cross-archive.** The report is retained as a list of hypotheses for the Fable audit and for phase 2; it is
not evidence on its own.

## Verified discrepancies (each checked by the controller against the named artefact)

| # | agy claim (tagged [V]) | artefact says | source checked |
|---:|---|---|---|
| 1 | Pinned-archive table: `A m=2dB` active beams 71.16, `MAX_NOMINAL_GAIN` 72.10, `A m=12dB` 61.64, RANDOM served 93.6 % / beams 63.20 / `H_inter` 0.8695 | `A m=2dB` 62.98 beams; `MAX_NOMINAL_GAIN` 62.98; `A m=12dB` 71.55; RANDOM beams 76.43, `H_inter` 0.6896, served 0.93683 | `.scratch/cf3-pilot/PROGRESS.md` lines 55-61 (pinned premeasure) |
| 2 | Bits/joules relative to TRAINED: `A m=2dB` 1.050× / 0.878×; `B1` 0.638× / 0.575× | From the same block (bits = EE × joules): `A m=2dB` bits 3.2454e14 = **1.152×**, joules 2.8926e6 = **0.964×**; `B1` bits 1.8616e14 = **0.661×**, joules 1.7867e6 = **0.595×** (TRAINED bits 2.8181e14, joules 3.0011e6). The 0.575× is FEASFRONT's unpinned figure. | same block; `.scratch/feasible-frontier/…:19` |
| 3 | `MAX_NOMINAL_GAIN` handover 0.7117 in the pinned table | 0.7117/0.7120 is FEASFRONT's **total** handover on the **unpinned** archive; pinned `H_inter` is 0.6546 | FEASFRONT §3; PROGRESS line 60 |
| 4 | r2 penalties "inter −2.0, intra −1.0" | `r2 = −φ1 = −0.5` same-satellite, `−φ2 = −1.0` satellite change | FEASFRONT §2 "Handover split" |
| 5 | Citation `V025-CONTROLLER-AMENDMENT-1-CALIBRATION-AND-LEARNING-CHECK-2026-09-11.md` | No such file; Amendment 1 is `…-AMENDMENT-1-THREE-CATFISH-PILOT-2026-09-11.md` | `ls .scratch/multi-catfish-v025-physics-successor/` |
| 6 | Section J describes Q4 as "catfish attachment / scaling", Q6 as "SRANK / decorrelation penalties", Q7 as "baseline retraining" | HANDOFF §6b: Q4 = energy credit with outage charge; Q5 = full-length runs + drop-one arms; Q6 = demonstration-utilisation arms; Q7 = engineering speed-ups | `.scratch/HANDOFF-2026-09-11.md` §6b |
| 7 | "A0 EE 85.98–93.90" | 93.90 is the frozen 9000-episode checkpoint on the pinned archive; 85.98 is not in any in-force artefact the controller could find (unverified) | registry grep |
| 8 | PA = 94.3 % of system power; `P_fixed ≈ 10 W + 0.338 W × beams`; 5.93 W PA per beam | Not checked by the controller; plausible in magnitude (the project's own dE_sys diagnostic gives ≈ 6.267 W per beam) but the split must be read from `link_budget.py` constants before use | `.scratch/cf3-pilot/PROGRESS.md` lines 72-77 |

Items 1-4 are the registry's "condition trap" (numbers from two archives in one table) plus arithmetic errors. Items 5-6
show the reviewer did not read the files it cites.

## What in the agy report is independently useful (as hypotheses)

- The credit argument: equal-share `E_u` makes the `eta·Q_E` term almost action-independent (project's own 0/240 probe;
  forecast blind spot B). Not new, but stated sharply with an order-of-magnitude derivation whose inputs are guessed.
- "Two `eta` updates in 1000 episodes is not Dinkelbach" — a fair conceptual objection to calling the schedule
  Dinkelbach; the declaration already calls it "our adaptation".
- "Beating A0 by dropping `r2` is an objective change, not a learning result" — forecast blind spot C, verbatim.
- Demonstration methods target sparse reward; static 11.7 % replay mixing without a margin loss is not DQfD — forecast
  blind spot A and Amendment 1 item 8, verbatim. The R2D3 demo-ratio figure (≈0.39 %) is [R] and worth verifying.
- The pivot options (negative-result/benchmark paper; centralised beam-sleep master + per-user worker; bursty traffic;
  power control) are reasonable candidates for the "better-posed problem" question.

## Controller arithmetic the agy report did not do (pinned archive, 24 calibration episodes, per-episode reseeded, consumed `max` power, sat; [D] from PROGRESS lines 55-61)

| rule | bits (×1e14) | joules (×1e6) | lit beams | joules per beam (kJ) | bits per beam (×1e12) | EE (Mbit/J) |
|---|---:|---:|---:|---:|---:|---:|
| `A m=2dB` | 3.2454 | 2.8926 | 62.98 | 45.9 | 5.15 | 112.20 |
| `MAX_NOMINAL_GAIN` | 3.1990 | 2.8948 | 62.98 | 46.0 | 5.08 | 110.51 |
| `A m=12dB` | 3.3008 | 3.2685 | 71.55 | 45.7 | 4.61 | 100.99 |
| `B1_NO_NEW_BEAM` | 1.8616 | 1.7867 | 38.57 | 46.3 | 4.83 | 104.19 |
| TRAINED `e6b063ef` | 2.8181 | 3.0011 | 66.63 | 45.0 | 4.23 | 93.90 |
| RANDOM_MASKED | 1.7984 | 3.4673 | 76.43 | 45.4 | 2.35 | 51.87 |

- Joules are ≈ 45–46 kJ per lit beam for every policy: **the denominator is proportional to the number of lit beams**
  (per-beam consumed power is nearly policy-independent).
- Therefore pooled EE ≈ bits per lit beam ÷ joules per lit beam: **EE is set by how many bits each lit beam delivers**
  (airtime-weighted spectral efficiency of the lit beams), not by the beam count itself.
- Marginal EE of the ≈24 beams that separate `B1_NO_NEW_BEAM` from `A m=2dB`: (3.2454−1.8616)e14 / (2.8926−1.7867)e6
  = **125 Mbit/J**, above either rule's average. Lighting those beams *raises* EE. So "fewer beams" is not the lever in
  this physics once assignments are gain-greedy; consolidation lowers EE unless it removes low-efficiency beams.
- The frozen learner sits at 4.23e12 bits per beam against 5.15e12 for the hysteresis rule with a similar beam count:
  the learner's gap is **bits per lit beam (assignment quality)**, not joules.
- Open question for the ceiling measurement: how much bits-per-beam a centralised, interference-aware assignment
  adds above the gain-greedy rules, at full service.

This arithmetic is not shown to the Fable reviewer (to avoid anchoring); it is checked against the Fable report in
phase 2.

## Disposition

- agy blind verdict: recorded, **not weighted as an independent derivation** (errors above).
- Next use of agy: an adversarial cross-model check of the **Fable** report (read the artefact, attack its claims),
  which is the standing cross-model rule, rather than a second blind run.
