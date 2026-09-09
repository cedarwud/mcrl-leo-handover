# ACM causality and decoding-margin audit (Claude Opus 5, read-only, HIGH PRIORITY)

You are auditing one specific question that can invalidate the whole comparison. Work read-only on the snapshot `/home/sat/mcrl-v025-stage4d-snapshot-20260909` (engine at stage 4d) and, for the provider, `/home/sat/mcrl-v025-provider-fix2-snapshot-20260908`. Python for inspection: `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. You may run the test suite. Do not modify the live workspaces.

Background (an outside reviewer's finding, to be verified or refuted): three objects must be distinct in an ACM system —
* `m_target`: the MODCOD used to compute the required transmit power for the rate target;
* `m_tx`: the MODCOD actually transmitted, selected from **causally available** channel information (nominal/predicted, not the realised draw);
* decoding success and credited bits: determined by whether the **realised** SINR clears the threshold of `m_tx`.
The reviewer observed that in the angle→power→EE note, four users at the beam edge target QPSK 3/4 but are credited QPSK 1/2 bits, which is only legitimate if a causal ACM controller had already selected QPSK 1/2. Selecting the best feasible mode from the same realised SINR that is then used to credit bits is a genie/ideal-ACM bound and can systematically favour whichever policy's realised SINR distribution sits nearer a threshold.

Answer each with file:line evidence and a VERIFIED / REFUTED / UNKNOWN label:
1. In the successor engine, exactly which SINR selects the mode that determines credited bits: the nominal (or margin-adjusted nominal) SINR available before transmission, or the realised SINR after fading? Trace it from the resolution/ACM code to the integration/endpoint code.
2. Are `m_target` and `m_tx` distinct objects in the code, or the same value reused? If the same, what is credited when the realised SINR falls below the target mode's threshold but above a lower mode's threshold?
3. Is the decoding threshold used for the service decision the same quantity as the SINR target used to compute power? If yes, show that success requires the realised fading factor ≥ 1 (i.e. the declared 1.7 dB implementation margin creates no fading reserve), and quantify: what fraction of the fading distribution at a typical elevation satisfies F ≥ 1 under the declared shadow/scintillation model?
4. What happens when no mode meets the rate target (`rate_target_infeasible`): which mode is transmitted, what bits are credited, and is the user counted in availability denominators? Also: with the declared bandwidth and the highest Table-13 efficiency, what is the beam's maximum aggregate rate, and at what user count does the 50 Mbit/s equal-airtime target become infeasible for every user even at unlimited SINR? Report the number.
5. Does the ACM mode table used for bits come from EN 302 307-1 (DVB-S2) Table 13 as declared, and are the roll-off and margin applied exactly once each?
6. If any of 1–3 shows an ideal/genie ACM or a zero-reserve threshold, state precisely what the minimal correct implementation is and which arms' numbers would change.
Deliverable: your final message, ≤ 150 lines, ending with `VERDICT: ACM_CAUSAL={YES|NO} | M_TARGET_VS_M_TX={DISTINCT|SAME} | DECODE_RESERVE={PRESENT|ZERO} | INFEASIBLE_HANDLING=<one line> | BEAM_CAPACITY_MBPS=<x> | MAX_USERS_AT_50MBPS=<n> | FIX_REQUIRED=<none|one line>`.
