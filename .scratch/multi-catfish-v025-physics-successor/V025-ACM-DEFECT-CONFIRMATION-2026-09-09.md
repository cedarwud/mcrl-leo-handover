# V025 — ACM causality defect confirmed (controller, 2026-09-09 ≈ 02:55 UTC)

The disposition was pre-declared in v1.8 §8 before the audit ran; this note records the confirmation only. **No new decision is taken here.**

Audit (`ACM-CAUSALITY-AUDIT-2026-09-09.md`, Claude Opus 5, read-only on the stage-4d snapshot; the concern was raised independently by the round-9C outside review):
`ACM_CAUSAL=NO | M_TARGET_VS_M_TX=SAME | DECODE_RESERVE=ZERO | BEAM_CAPACITY_MBPS=618.476 | MAX_USERS_AT_50MBPS=12`

1. **Genie ACM confirmed.** The credited mode is selected from the **realised, post-fading** SINR (`batch.py:333-361`, `resolution.py:123-128` → `acm.py:140`); no call site selects a mode from a nominal SINR. `m_target` exists only to set power; `m_tx` is re-derived after the fact, so a −3.03 dB fade at n_b = 4 is credited QPSK 1/2 against a QPSK 3/4 target instead of failing.
2. **Zero decode reserve confirmed.** The decode threshold and the power target are the same `threshold_linear`, so the declared 1.7 dB implementation margin cancels exactly and success requires a realised fading factor F ≥ 1, whose probability is only **0.287 / 0.432 / 0.470 at 10° / 30° / 50°**. This is the mechanism behind the 30–40 % unserved share seen in development.
3. **Infeasible users** transmit at the 1.65 W cap, stay permanently `rate_target_feasible=False`, are still credited full genie bits and remain in every availability denominator.
4. **Beam capacity** is 618.476 Mbit/s, so at most 12 users per beam can each receive 50 Mbit/s under equal airtime; at 13 the target is infeasible for every user at any SINR.
5. **Table 13 transcription is correct** and SHA-pinned; roll-off and margin are each applied exactly once.

**Consequences, stated now so no later number is misread.** Every energy-efficiency figure produced so far — the vertical slice, the regime slice, the synthetic map, and the pilot now running on the stage-4d snapshot — is on a **genie-ACM basis with no decode reserve**. Delivered bits will fall and availability will move once the fix lands; those numbers are development evidence and none of them is a claim. The pilot's purpose is unaffected because its decisive comparison (carrier-anchored versus unilateral-optimum-anchored catalogue) is a *relative* comparison made under one and the same ACM basis; its absolute numbers are not used.

**Fix (as pre-declared in v1.8 §8, implemented in stage 4g):** `m_target`, `m_tx` and the realised outcome become three distinct objects; `m_tx` is chosen from the causally available margin-adjusted nominal view; credited bits are those of `m_tx` when the realised SINR clears **threshold(m_tx)**, and zero otherwise; the v1.9 tenth-percentile rule supplies the decode reserve that the implementation margin does not. The engine emits all three per user-step, and reports availability and pooled EE before and after the change on the quarantined world, labelled SMOKE.
