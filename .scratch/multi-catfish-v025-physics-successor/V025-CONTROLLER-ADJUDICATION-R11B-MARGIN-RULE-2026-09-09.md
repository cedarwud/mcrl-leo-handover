# Controller adjudication — the sealed margin rule is defective, and four of my own claims were wrong
Recorded 2026-09-09, after the round-11B outside review and its independent numerical audit. **No probe or matrix outcome exists.** Everything below is decided on mathematics and on deterministic recomputation from the figure's own declared constants, not on any observed result.

## 1. The finding: v1.9 item 1's rationale is mathematically wrong, and I was right to doubt it
Sealed v1.9 item 1 forbids re-solving the fade margin into transmit power, on the stated ground that setting `p = p_nominal / q` makes the link target the threshold again so that "the margin bought no reserve, only more power and more interference".

That reasoning does not hold. With `p = p0/q` where `p0 = Γ·D/h` and `q` is the 10th-percentile of the relative power-gain fading multiplier `G`:

* nominal SINR becomes `Γ/q`, which is **above** threshold, not at it;
* realised SINR is `Γ·G/q`, so decoding succeeds exactly when `G ≥ q`, which is probability **0.90** by the definition of `q`;
* the reserve is `−10·log10(q)` dB.

**The nominal link sits above threshold and the lower-decile faded link sits at threshold. That is the reserve, not its cancellation.** The construction has a direct primary source: Stojanovic, "Adaptive power and rate control for satellite communications in Ka band", IEEE ICC 2002, printed page 2968, immediately after equation (7), which derives `P_T = P_T0 / G_out` and names the reciprocal outage-gain factor as the required fixed fade margin.

Fixed-power ACM is also legitimate practice, and ETSI TR 102 376-1 §4.4.1 describes it with fixed beam power. The defect is not "margin through mode selection". The defect is **our particular composition**: solve power to leave exactly zero nominal headroom, then demand headroom while forbidding any power adjustment. Ordinary fixed-power ACM does not do that, because it never removes the headroom in the first place.

## 2. Three consequences of the current rule that must be named
1. **Controller-induced outage.** For an uncapped exact-target solution `SINR_nominal = Γ(m_r)`, any `q < 1` gives `q·SINR_nominal < Γ(m_r)`, so the intended mode is rejected **by construction**. When it was already the lowest mode, the feasible set is empty. This needs no rain, no bad realisation and no shortage of RF power.
2. **Back-off always misses the rate target.** If `m_r` is the least-threshold mode satisfying `B·η(m_r)/n ≥ r*`, then any strictly lower mode cannot satisfy the same requirement at the same airtime. So a backed-off user decodes but **never meets `r*`**. At occupancy 2 the backed-off mode delivers 34.04 Mbit/s against a 50 Mbit/s target.
3. **Zero-payload transmission at full power needs its own justification.** A transmission certain to deliver no bits still costs energy and creates interference. For a bits-minus-price-times-joules objective, muting it is preferable unless a signalling or synchronisation purpose is modelled.

## 3. Four of my own claims were wrong. Recorded plainly.
1. **The link budget I quoted belongs to a different geometry.** The engine report's 19.196747 dB and 9.851770 dB are the **550 km boresight** and **1,100 km half-power edge** cases. The mechanism figure is fixed at **2,000 km, 10 degrees**. Recomputed from the figure's own constants, C/N at the 1.65 W cap is **5.714 dB at boresight and 2.703 dB at the edge**. I quoted the first pair as though it described the second geometry.
2. **Lone-user starvation is not forced by the power cap.** With an illustrative 3 dB reserve, the lone-user power is 0.634 W at boresight and 1.268 W at the edge, both inside the 1.65 W cap. My finding said a lone user "is never served"; the correct statement is that it is never served **under the rate-back-off rule**, which is a policy artefact and not a physical limit.
3. **The QPSK truncation does not change this figure's numbers.** At 5.714 and 2.703 dB, no 8PSK, 16APSK or 32APSK mode is nominally feasible anyway; the best available are QPSK 4/5 and QPSK 1/2. The 11-mode table is a genuine specification mismatch that must be fixed, but my framing implied it suppressed reachable throughput at this geometry, and it does not.
4. **My reported figures are mutually inconsistent and I did not notice.** If every `NO_MODE` opportunity contributes zero availability under the same population and weights, then availability `<= 1 − NO_MODE fraction`. With 62 % that bound is 0.38, not 0.453; with the census figure of 76.56 % it is 0.234. This does not prove an error, because 0.453138 is a paired two-anchor smoke aggregate while the `NO_MODE` share is a separate census, but **the denominators must be reconciled before the two numbers appear in one sentence.** I also wrote that `NO_MODE` users transmit at "full power" while my own finding says "computed power"; those are different cases and I conflated them.

## 4. A new defect to verify in the engine, which I had not seen
The figure selects the transmitted mode by scanning modes in threshold order and keeping the last one cleared. Within the 11 QPSK modes that is correct, and I verified locally that threshold order and efficiency order never disagree there.

**It stops being correct at 28 modes.** 16APSK 2/3 has both a lower reference threshold and a higher spectral efficiency than 8PSK 5/6, so threshold order is not throughput order. The correct rule is
`m_tx = argmax over { m : Γ_m <= SINR_safe } of η_m`, with explicit tie-breaking.

**The engine runs the full 28-mode table.** If its selection has the same shape as the figure's, it is silently choosing a lower-throughput mode in part of the range, which would suppress credited bits and therefore energy efficiency everywhere. This must be checked against `src/mcrl/physics_v025/acm.py` the moment the server returns. It is a verification task, not yet a finding.

## 5. Two normalisation checks required before the figure is re-derived
1. **Possible double-counted scintillation.** The figure already carries a deterministic 1.08 dB scintillation term inside the nominal gain, and v1.9 defines the fading-product quantile to include scintillation as well. Defining `G = h_realised / h_nominal` consistently would settle it. The evidence does not show that the engine double-counts; it shows that nothing rules it out.
2. **Geometry reconciliation.** The figure's fixed 2,000 km at 10 degrees and the link-closure ledger's 550 km and 1,100 km cases must be reconciled, or the paper will carry two link budgets that do not describe the same system.

## 6. Recommendation, and why it is made on correctness rather than on what helps C3
**Amend the rule.** Remove the prohibition on carrying reserve in power. Keep the causal correction exactly as it stands: choose the transmitted mode from information available before transmission, and credit bits only when the realised channel decodes it. The coherent construction for our rate-target controller is to test whether the target mode survives the declared reserve,

`q_i · h_ii · p_i  >=  Γ(m_r,i) · ( N_i + Σ_{j != i} h_ji · p_j )`,

subject to the RF cap and payload constraints, and then to distinguish three outcomes explicitly: lower-rate service, rate-target failure, and no data service.

Three qualifications travel with it, and none may be dropped. A **binding cap** removes the 90 % guarantee, so a cap-induced shortfall must surface as an explicit feasibility failure rather than a silent demotion. **Interference must be recomputed** when other beams change power: scaling every power by `1/q` gives `S_i/(q·N_i + I_i)`, not `SINR_i/q`, so the interference-limited component does not improve under uniform scaling. And **the quantile must match the actual uncertainty**: a wanted-link quantile with interference frozen at nominal is not automatically a 90 % guarantee when interference is random.

**The reason this recommendation must be made on correctness alone.** Amending the rule will probably **reduce** the headroom C3 is chasing. Fewer users will be stranded, availability will rise, contention will fall, and the coordination lever measured this morning will shrink. Keeping the defective rule would preserve a larger apparent opportunity for C3. That is precisely why the decision cannot be made on which option looks better for the result. A coordination gain measured inside a controller-induced outage is not a finding about satellites.

## 7. Cost, stated honestly
Amending the power rule changes the engine, so calibration must be recomputed under it, the mechanism figure must be re-derived, and both interaction probes are again measuring superseded physics and would restart. That is most of a day. The alternative is a paper whose headline availability is an artefact of a rule an outside reviewer has already shown to be mathematically misjustified.

## 8. Standing
This document records an adjudication and a recommendation. It does not itself amend the sealed declaration; a v1.10 amendment does that, and it is written only on the owner's decision because it changes the physical model the main run will measure. Nothing here authorises a run, changes a threshold, sign, seed, horizon, price or acceptance rule, or creates a gate.
