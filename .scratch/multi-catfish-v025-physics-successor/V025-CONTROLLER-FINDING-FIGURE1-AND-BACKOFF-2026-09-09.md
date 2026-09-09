# Controller finding — figure 1 contradicts the sealed physics twice, and the second contradiction explains the engine's NO_MODE share
Recorded 2026-09-09, server clock about 08:20 UTC, from local analysis while the server was unreachable. Every number below was recomputed locally from `paper-lane-20260909/figures/figure1_compute.py` using that script's own constants and mode table.

## Finding 1 — the figure's ACM table is the QPSK subset, not the sealed table
VERIFIED. `ACM_TABLE` in the figure script contains **11 entries, all QPSK**. Its own comment names it "DVB-S2 / EN 302 307-1 QPSK ACM table". The strings `8PSK`, `16APSK` and `32APSK` appear **zero** times in the file.

| quantity | figure 1 | sealed priority declaration |
|---|---:|---:|
| modes | 11 | 28 |
| SE_max, bit/s/Hz | 1.4905 | 3.7109 |
| highest occupancy reaching r* = 50 Mbit/s | 4 | 12 |

The ratio of spectral-efficiency ceilings is 2.490. The stage-4h engine census independently reports 12 feasible and 13 infeasible, matching the declaration and not the figure.

The figure plots `OCCUPANCIES = (1, 2, 4)`. Four is exactly the last occupancy its own truncated table can serve, so the truncation is invisible in the rendered figure and the script raises `ValueError: rate target unreachable at occupancy 5` the moment anyone extends it. INFERENCE: the plotted occupancy set was chosen, deliberately or not, to sit inside the truncation.

## Finding 2 — the transmitted mode carries no wanted-link reserve
VERIFIED. The script computes `sinr = nextafter(power * h_hat, inf) / noise` and then `select_mode(sinr)`, whose docstring reads "highest-rate mode whose threshold the realised SINR clears". Its own comment concedes the problem: "the rate-target controller lands exactly on an ACM threshold, and this keeps the final divide/multiply round trip from deciding decodability".

Sealed v1.9 item 1 requires the selection view to predict `SINR_pred = q · h_nominal · p / (N0·W + I)` and to choose the transmitted mode from that, with power left at its nominal value. The figure uses `q = 1`.

Because the rate-target controller solves the power so that the nominal SINR lands **exactly** on the target mode's threshold, any `q < 1` strictly lowers the transmitted mode at every point on the figure. Credited bits as a fraction of what the figure reports, with energy unchanged so the same fraction applies to its energy-efficiency axis:

| occupancy | target mode | 1.0 dB | 1.7 dB | 3.0 dB | 5.0 dB |
|---:|---|---:|---:|---:|---:|
| 1 | QPSK 1/4 | 0.000 | 0.000 | 0.000 | 0.000 |
| 2 | QPSK 2/5 | 0.621 | 0.621 | 0.000 | 0.000 |
| 3 | QPSK 3/5 | 0.832 | 0.664 | 0.552 | 0.000 |
| 4 | QPSK 3/4 | 0.799 | 0.799 | 0.665 | 0.441 |

The exact reserve is the sealed 10th-percentile quantile of the fading product, which needs the engine's 200,000-draw procedure and could not be computed locally. The table is a sensitivity, not a substitute for it.

## Finding 3 — the structural corollary, which is the important one
INFERENCE, following directly from the two verified rules above.

Sealed v1.9 forbids re-solving the margin into transmit power, and requires the transmitted mode to be demoted instead. That is a **rate back-off** policy: reliability is bought with spectral efficiency, not with joules. Its corollary is unavoidable.

**A user whose target mode is already the lowest mode has nothing to back off to, so its transmitted mode is `NO_MODE` by construction, for any reserve at all.** The first row of the table above shows this: at occupancy 1 the target is QPSK 1/4, which is also the PHY floor, and a reserve of even 1.0 dB credits zero bits.

This predicts an observation nobody had explained. The corrected engine reports `m_tx = NO_MODE` for about **62 %** of transmissions and `rate_target_feasible = false` for **40.8 %** of user-steps, while beam occupancy averages only 2.44. Low occupancy means a low target mode, a low target mode means no back-off room, and no back-off room means no transmitted mode. The high `NO_MODE` share is not primarily a link-budget accident; it is what the sealed back-off rule does at low occupancy.

A `NO_MODE` user still transmits at its computed power, still contributes interference, still burns PA energy and still sits in the availability denominator. That is the mechanism behind availability falling from 0.791 to 0.453.

## Finding 4 — why this matters for C3, and it is favourable
INFERENCE. Under rate back-off, a user's transmitted mode depends on its occupancy, because occupancy sets the target mode. **Raising a beam's occupancy raises its target mode, which creates the back-off room the user needs to transmit at all.** That inverts the usual load intuition and it is a genuine coordination lever:

* moving a user onto a lightly loaded beam can push that beam's target mode up far enough that previously undecodable users become decodable;
* the benefit accrues to users other than the one that moved, and it can require two moves before any user crosses a threshold, which is exactly the shape of a super-additive interaction.

This is mechanism 2 of the constructive `Psi` witness test already commissioned, the airtime and occupancy cliff. That test is now the highest-value experiment queued, and this finding says where to aim it.

## What must be resolved before publication
1. Whether the figure's QPSK-only table contradicts the priority declaration, or whether the note it was computed from, `V025-ANGLE-POWER-EE-NOTE-2026-09-08.md`, declares a QPSK-only model. That note is on the server and was not readable during this analysis. If the note and the declaration disagree, the declaration governs.
2. Whether figure 1 should be recomputed under the sealed 28-mode table and the sealed reserve. On the evidence above it must be, and its energy-efficiency levels will fall substantially. The qualitative angle-to-power mechanism the figure exists to show is unaffected, because that mechanism lives in the antenna pattern and the path loss, not in the mode table.
3. Whether the back-off rule is intended to strand low-occupancy users. It is a defensible conservative choice, but the paper must state it as a choice with a named consequence rather than let it appear as a link-budget result.

## Standing
This document records a finding. It authorises no rerun and changes no sealed value, no threshold, no sign and no acceptance rule.
