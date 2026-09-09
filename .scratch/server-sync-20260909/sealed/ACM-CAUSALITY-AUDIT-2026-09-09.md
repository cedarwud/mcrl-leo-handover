That notification was the leftover watcher job I had queued before the suite finished — it reports the same result already folded into the report: `tests/physics_v025` = 167 passed, exit 0. No new information, and no change to any finding.

The audit is complete and the full report was delivered in my previous message. Summary of what stands:

- **Q1 VERIFIED** — credited mode is selected from the **realised** post-fading SINR (`batch.py:333-361`, `resolution.py:123-128` → `acm.py:140`). No call site selects a mode from a nominal SINR.
- **Q2 VERIFIED** — `m_target` exists only to set power (`acm.py:77-118` → `architectures.py:684-694`); `m_tx` is re-derived post-hoc, so a fade of −3.03 dB at n=4 credits QPSK 1/2 against a QPSK 3/4 target, with no outage.
- **Q3 VERIFIED** — decode threshold and power target are the same `threshold_linear`; the 1.7 dB margin cancels. Success needs F ≥ 1: P = 0.287 / 0.432 / 0.470 at 10° / 30° / 50°.
- **Q4 VERIFIED** — infeasible users transmit at the 1.65 W cap, are permanently `rate_target_feasible=False`, still receive full genie-ACM bit credit, and remain in every availability denominator. Beam capacity 618.476 Mbit/s; feasible to n=12, infeasible for all at n=13.
- **Q5 VERIFIED** — Table 13 transcription correct and SHA-pinned; roll-off and margin each applied exactly once (`acm.py:32-33`).
- **Q6** — minimal fix is to materialise `m_tx` from the nominal SINR, decode against `threshold(m_tx)` alone, and add a separate declared fading reserve (~3.7 dB for 90 %). Expect `a-r`/`a′-r` bits and pooled EE to fall by roughly 2–3×; the `a-r` vs `b` ordering is not safe until re-run.

Nothing in either workspace was modified; all work was read-only plus scratch computation in a heredoc.

VERDICT: ACM_CAUSAL=NO | M_TARGET_VS_M_TX=SAME | DECODE_RESERVE=ZERO | INFEASIBLE_HANDLING=forced to full 1.65 W cap, permanently rate_target_feasible=False, still credited full genie-ACM bits and still counted in all availability denominators | BEAM_CAPACITY_MBPS=618.476 | MAX_USERS_AT_50MBPS=12 (n=13 infeasible for every user at any SINR) | FIX_REQUIRED=make m_tx an explicit object chosen from the nominal SINR, decode against threshold(m_tx) only, and add a separately declared fading reserve (~3.7 dB for 90%) since the 1.7 dB implementation margin cancels on both sides
