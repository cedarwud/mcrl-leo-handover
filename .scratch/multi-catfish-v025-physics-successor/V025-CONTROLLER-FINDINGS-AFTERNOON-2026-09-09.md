# Controller findings — three results that change the picture, recorded 2026-09-09 afternoon
`DIAGNOSTIC_NOT_CLAIM` throughout. Nothing here may enter the paper or support a claim.

## 1. The coordination headroom is robust to the disputed circuit constant
A rescoring of the already-selected oracle configurations across 18 combinations of the per-chain and per-satellite circuit terms. Assignments, bits, decode outcomes and served counts are fixed at every point; only the energy accounting changes.

| per-chain W | per-satellite W | ORACLE over UNILATERAL |
|---:|---:|---:|
| **0.000** | **0.200** | **+6.514881 %** |
| 0.338 (declared) | 0.200 | +6.359000 % |
| 3.000 | 0.200 | +5.666631 % |
| 15.000 | 2.000 | +4.844512 % (worst of 18) |

**All eighteen combinations are positive**, spanning +4.84 % to +6.59 %.

The `0.0 W` case is the architecture an outside hardware review raised as fatal: beams share element amplifiers, so emptying one saves nothing. At that point the headroom is **larger**, not smaller. The declared per-chain accounting **dilutes** the relative gain by 0.156 percentage points rather than creating it.

Served counts hold at 1,957 for the oracle against 1,939 for unilateral at every sweep point, so no variant buys efficiency by serving fewer users.

This retires my afternoon worry that the result rested on the disputed constant. It does not retire the constant's semantic problem, which is now a **paper wording obligation**: the value must be presented as a declared assumption with its source's narrower meaning stated. The sweep is a rescoring, so it does not say which coalitions a selector using different accounting would choose.

## 2. Constant provenance: mostly sourced, one real attribution error
A systematic audit of every declared constant against its cited source found **four** adverse or unavailable verdicts, and the largest is not the one I expected.

**The real defect is the beamwidth.** `TX_FULL_HPBW_DEG = 3.32°` is commented as retaining a HOBS full half-power beamwidth convention. The source's own equation uses `sin(theta_3dB)` with `theta_3dB = 0.058 rad` as an **off-axis angle**, not half of one. The engine registers a full span and halves it. The geometry is reproducible but **the HOBS attribution is unsupported**, and unlike the other cases the code still asserts it. Sensitivity is large: at 2° off-axis, halving or doubling the declared width moves the mechanism figure's endpoint from 9.17 Mbit/J to **zero** or to **13.08 Mbit/J**.

**The circuit constants are honestly declared, and that matters.** The audit confirms `338 mW` decomposes in its source as DAC 300 + mixer 19 + low-pass filter 14 + baseband amplifier 5 mW with the amplifier supply separate, and `200 mW` is a digital baseband precoder. But sealed amendment v1.8 **already** calls `0.35` a saturation efficiency, the satellite term a processing increment, and `50 Mbit/s` a power-control setpoint, and limits the energy boundary to named partial-payload components. So these are declared modelling assumptions, not physical claims dressed up as measurements. That is methodologically defensible provided the paper says so.

The two interruption constants are `UNVERIFIABLE_HERE`: their 3GPP annex could not be retrieved, and the audit correctly distinguishes inaccessible evidence from absent evidence. Under the primary interruption-off setting their effect is zero.

The ~20 s operational reserve is `UNSOURCED` as an empirical timing attribution only; the reserve itself is declared and has no direct physical-layer effect.

## 3. The unilateral comparator is degenerate, and both adjudications agree
Two independent reviews, one per model family, reached the same verified number: the comparator selected a BASE configuration at **90 of 90 anchors**, not the 79 of 90 I reported. The eleven that certified successfully certified BASE with zero accepted updates; of the 79 that fell back, 37 had made tentative updates and discarded them.

So `FULL > S_UNI` is arithmetically the same test as `FULL > BASELINE`, which the figure already plots as its own curve. **The C4 conjunct cannot fail for any reason connected to coordination.**

The structural cause: each iteration re-evaluates every single-user deviation, about 2,748 exact solves per sweep at 6 to 11 seconds, then commits **one** move. An anchor therefore certifies within budget **only if the first sweep finds no improving move**, that is only if the answer is already the anchor. Uncensored iteration counts are bimodal at `{0, 46, 50, 80, 86, 86}` with nothing between 1 and 45, so no realistic budget increase converts any anchor.

The root cause I had not named: on abort the solver **discards** a fully validated, jointly legal profile that has already passed the service guard, and returns the anchor. The arm is non-anytime by construction, mandated by the contract's own "atomic commit of the final profile only".

**The path forward is narrower than I thought, and better.** Contract v1.2 item 6 **already** calls the budget-limited arm an operational comparator, already requires a completed-neighbourhood certificate for a beyond-unilateral claim, and already permits an offline certified diagnostic. So the two-arm split is **implementing a distinction the contract requires**, not amending it.

One correction to my own framing that both reviews made: an unlimited-compute fixed point reached by one greedy path is an arbitrary local optimum, **not a ceiling** on unilateral reasoning. `FULL > S_UNI(unlimited)` licenses only "not reproducible by this greedy path".

Also recorded: acceptance test T2 carries a second vacuous clause. Its requirement that the additive placebo yield a near-zero interaction and matching decisions passes **vacuously** when both arms return the anchor, so the gate cannot detect the condition just measured.

## Standing
No threshold, sign, seed, horizon, price, service guard, acceptance rule or claim condition changes. No run is authorised.
