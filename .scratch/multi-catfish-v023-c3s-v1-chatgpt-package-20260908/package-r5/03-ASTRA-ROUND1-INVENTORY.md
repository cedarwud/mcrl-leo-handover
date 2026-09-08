# Power and EE adjudication — 2026-09-08

**The segment anchor is declared, and it creates a real renewal option inside this model. The evidence does not establish that renewal explains the entire C3-S advantage. Several independent assumptions can produce similar advantages, and one further source error was confirmed in the receive-antenna model.**

**Recommendation: adopt option (iii), a versioned successor whose power target is independent of segment entry, and hold stage-A attempt #4 until that choice is frozen.** Preserve all sealed results as results under their original model.

This was a read-only audit of checkout `a9702a08be09772549c461c7084ce9229fa08889`. I inspected the implementation, rulings, thesis text and evidence copies, and executed small deterministic calculations without writing files. Receipt statistics below are attributed to the supplied audits; I did not independently reproduce the full trajectories. The harness audit also establishes that the available C3-S source files differ from the receipt-producing versions, which must be recovered before an authenticated replay. [EVIDENCE-02:8](/home/sat/mcrl-v023-astra-physics/EVIDENCE-02-HARNESS-AUDIT-OPUS.md:8)

## A. Anchored power: fact, status, physics

1. **DECLARED.** The thesis explicitly says: “這是本研究自行定義的角度感知功率規則，不是原始 MODQN 的公式。” It then declares preservation of transmit power times transmit gain within a continuous service segment. [Thesis:246](/home/sat/mcrl-leo-handover-e1/.scratch/chinese-word-v023-lcsrs-20260905-r2/mc-modqn-base.md:246)
2. The implementation is \(p_u(t)=0.825\,G_u^T(\tau)/G_u^T(t)\). Thus the wanted signal contains \(0.825\,G_u^T(\tau)\), multiplied by **current** path loss, fading and receive gain. Full received power, SINR and throughput are not frozen. [link_budget.py:385](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:385), [step.py:943](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/step.py:943)
3. Association changes **and service breaks** end continuity; subsequent service re-anchors power. A dwell boundary alone does not reset a continuing physical `(NORAD, cell)` link. [step.py:783](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/step.py:783), [step.py:824](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/step.py:824)
4. Power can decrease: gains \(1\rightarrow2\) give \(0.4125\) W; gains \(1\rightarrow0.5\) give \(1.65\) W. Comments saying recurrence “only ever raises” power are false as general statements. [link_budget.py:216](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:216)
5. **Physics judgment:** gain compensation is defensible; choosing its target from an arbitrary entry angle and renewing that target through association changes is a bespoke control abstraction. It creates history-dependent opportunities without a demonstrated physical justification for their renewal terms.
6. NR power control does not establish this law. PUSCH power-control adjustments operate around transmission occasions and TPC commands; NTN introduces feedback/timing considerations. These are principally **UE uplink** procedures, not validation of this satellite downlink formula. There is no universal “30-second, handover-reset” cadence. [TS 38.213 §7](https://www.etsi.org/deliver/etsi_ts/138200_138299/138213/18.04.00_60/ts_138213v180400p.pdf), [TR 38.821 §6.2.2](https://atisorg.s3.amazonaws.com/archive/3gpp-documents/Rel16/ATIS.3GPP.38.821.V1600.pdf)
7. DVB ACM adapts modulation/coding using link feedback, potentially frame by frame; adaptation is quantized and delayed. A fixed-RF/fixed-boresight-EIRP forward link instead lets current geometry change received power without an entry-history target. Both offer clearer reference models. [DVB implementation guide](https://dvb.org/wp-content/uploads/2019/12/a171-1_s2_guide.pdf), [ITU-R S.2174 §3.2](https://www.itu.int/dms_pub/itu-r/opb/rep/R-REP-S.2174-2010-PDF-E.pdf)
8. **Verdict:** declared simplification with a manufactured renewal option; neither an undocumented coding accident nor proof that every renewal improves EE. Re-anchoring can change both bits and joules in either direction.

## B. Full inventory, ranked by impact

**Ranking:** HIGH means a mechanism can materially affect the approximately 2.9% comparison, undermine its attribution, or change what the endpoint means. It does not mean a measured contribution has been established. MEDIUM denotes substantial model or comparison sensitivity. LOW denotes smaller direct effects or accounting paths that currently appear correct.

**Exploiters:** “All” means C1/C2 through their training targets, C3-S through nominal search, and an oracle through direct optimization. Their ability to discover an option differs; the environment offers it to all.

**Magnitude reference.** The supplied receipts give:

| Quantity | BASE | FULL |
|---|---:|---:|
| Pooled EE | 117.4194 Mbit/J | 120.8048 Mbit/J |
| Mean power | 260.528 W | 257.302 W |
| Mean aggregate rate | 30.591 Gbit/s | 31.083 Gbit/s |
| Relative change | — | EE +2.883167%; bits +1.6092%; joules −1.2383% |

LITE gives +2.921776% EE. These are model endpoints, not measured satellite efficiencies. [EVIDENCE-02:37](/home/sat/mcrl-v023-astra-physics/EVIDENCE-02-HARNESS-AUDIT-OPUS.md:37)

At BASE’s denominator, 1 W is approximately 0.384% of power. Effects below overlap and must not be added as independent explanations.

### HIGH

**B01 — Segment anchoring and reset admission.**  
**Mechanism:** identical current geometry can produce different power, wanted signal and feasibility solely because entry histories differ. A new segment starts at 0.825 W for any positive transmit gain; an old segment at the same geometry can exceed 1.65 W and drop out. An outage then clears the history. **Exploiters:** all, including through legal association changes; deliberate NO_OP is unavailable when legal actions exist. **Magnitude:** potentially substantial for both pooled EE and the contrast; unmeasured here. Phase-specific EE gains of 1.348/1.748/3.921/9.262% support investigation, not attribution: dwell phase is not measured segment age. **Status:** DECLARED mechanism; causal contribution unestablished. **Handle: FIX in a successor; SENSITIVITY and disclosure for sealed results.** [step.py:770](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/step.py:770), [action_contract.py:574](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/action_contract.py:574), [EVIDENCE-01:52](/home/sat/mcrl-v023-astra-physics/EVIDENCE-01-REDTEAM-OPUS.md:52)

**B02 — Wanted power and radiated beam power describe different transmissions.**  
**Mechanism:** energy and interference use \(p_b=\max_u p_u\), while user \(u\)’s wanted signal uses \(p_u\). For a beam actually transmitting at one constant power, a nonmaximum user receives more wanted RF than credited. For TDMA with varying user power, energy should instead integrate slot power and interference should follow the schedule or an explicitly named approximation. **Exploiters:** all; changing beam membership changes this discrepancy. **Magnitude:** absolute SINR is underestimated relative to the literal constant-power interpretation; relative policy bias has no fixed sign. It is zero for equal powers and potentially material for heterogeneous powers. **Status:** DECLARED explicitly, including its pointwise conservative direction; that does not make policy comparisons conservative. **Handle: FIX the transmission interpretation in the successor.** [interference.py:402](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/interference.py:402), [link_budget.py:439](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:439)

**B03 — Maximum aggregation creates zero marginal RF cost and discrete consolidation savings.**  
**Mechanism:** adding a user below an existing beam maximum adds no PA or circuit power; removing the maximum user can reduce power abruptly; removing the last user deletes the beam’s entire draw. These are powerful association incentives. Bandwidth sharing supplies a countervailing cost, so consolidation is not automatically beneficial. **Exploiters:** all, especially C3-S’s evacuation catalog and joint oracles. **Magnitude:** at 0.825 W, PA plus circuit draw is **6.26590 W/beam**. Half an equivalent beam is **3.13295 W**, close to the reported 3.226 W saving. But “0.50 fewer beams” is an inference, not a recorded count. **Status:** DECLARED equations. **Handle: DECLARE and SENSITIVITY; resolve B02 before hardware interpretation.** [link_budget.py:442](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:442), [EVIDENCE-02:129](/home/sat/mcrl-v023-astra-physics/EVIDENCE-02-HARNESS-AUDIT-OPUS.md:129)

**B04 — Instant power gating, no idle floor, and an action-dependent accounting boundary.**  
**Mechanism:** an empty beam costs zero; an emptied satellite contributes zero. There is no retained PA bias, idle payload draw, minimum on-time or wake-up transient. The model therefore grants immediately realizable savings whenever resources become empty. Real savings depend on what can actually be powered down and for how long. **Exploiters:** all; evacuation search directly targets this discontinuity. **Magnitude:** potentially large for absolute EE and its energy-saving component. For fixed trajectories, adding a common **total** floor of 40/100/400 W reduces the reported FULL contrast to approximately 2.712/2.527/2.108%; an arbitrarily large common floor leaves the +1.6092% bits contrast. These are sensitivities, not hardware estimates. Four candidate slots per user do not establish four physical satellites. **Status:** partial boundary DECLARED; instant switching follows from the equations. **Handle: SENSITIVITY and explicit hardware boundary.** [link_budget.py:527](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:527), [EVIDENCE-01:138](/home/sat/mcrl-v023-astra-physics/EVIDENCE-01-REDTEAM-OPUS.md:138)

**B05 — Handover, re-steering and signalling have no endpoint transition cost.**  
**Mechanism:** a changed association receives a full step’s steady-state bits immediately, with no interruption, overlap transmission, acquisition or switching energy. A reward penalty does not debit this endpoint. **Exploiters:** all current EE-surplus learners, C3-S and oracles; legacy reward users may face a separate preference penalty. **Magnitude:** unknown without event counts and physical calibration. At 30.08 s, the ADR’s *conditional, unapproved* 62/142 ms interruption examples remove only 0.206/0.472% of an affected user’s step bits; network impact also depends on the fraction of users moving. They cannot be enlarged to make an effect visible. **Status:** procedure-energy exclusion DECLARED; full-step immediate service IMPLIED by implementation. **Handle: DECLARE boundary, calibrate time/energy independently, then SENSITIVITY or versioned FIX.** [step.py:965](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/step.py:965), [ADR-004:78](/home/sat/mcrl-leo-handover-e1/docs/decisions/ADR-004-payload-boundary-time-only-c2.md:78), [ADR-004:118](/home/sat/mcrl-leo-handover-e1/docs/decisions/ADR-004-payload-boundary-time-only-c2.md:118)

**B06 — “Served” is admission, not useful service or QoS.**  
**Mechanism:** a selected legal link within its recurrence-power limit is served regardless of realized SINR, minimum rate, decoding success or delivered packets. Concentration can preserve 100/100 service while worsening individual throughput. C3-S guards nominal served count against the **same-state BASE proposal**, not against the separate BASE trajectory. **Exploiters:** all; C3-S’s guard permits rate redistribution that preserves this Boolean. **Magnitude:** service was identical at 35,971/36,000 opportunities; 352/360 BASE steps already served everyone. Thus the service clause supplied almost no independent discrimination in this panel. This does not prove service invariance in other worlds. **Status:** DECLARED implementation; saturation established in receipts. **Handle: DECLARE “admitted user-step”; add QoS/delivery SENSITIVITY before service claims.** [service.py:185](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/service.py:185), [c3s_policy.py:275](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/c3s_policy.py:275), [EVIDENCE-02:91](/home/sat/mcrl-v023-astra-physics/EVIDENCE-02-HARNESS-AUDIT-OPUS.md:91)

**B07 — Coarse integration and synchronized candidate refresh.**  
**Mechanism:** rates and power evaluated at a decision snapshot are multiplied by 30.08 s. D2’s 47 measurements do not constitute 47 throughput integrations. Dwell \(N=4\) freezes candidate identities for 120.32 s; eligibility can disappear inside a dwell, while newly eligible satellites wait for its boundary. This creates phase-dependent opportunities independent of anchoring. **Exploiters:** all; predictive C2 and nominal search can exploit snapshot timing and candidate availability. **Magnitude:** unknown physical integration bias; the reported phase contrast is large enough to make this a serious competing explanation. Changing only the common time multiplier leaves EE unchanged, but changing the physical action/integration cadence does not. **Status:** DECLARED clocks and candidate rules; numerical integration approximation IMPLIED. **Handle: SENSITIVITY with physical-time-matched trajectories and phase-offset starts.** [constants.py:73](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/constants.py:73), [candidates.py:271](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/candidates.py:271), [run_v023_c3s_screen.py:793](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_screen.py:793)

**B08 — Warm starts and evaluation horizon alter the physical initial distribution.**  
**Mechanism:** `uniform-episode-length` draws initial ages from \(0,\ldots,H-1\). A 30-step run therefore initializes different segment histories from a 10-step run. Historical gain back-propagates the satellite while holding the user at its current location, without proving continuous historical service. Segment-age features also normalize by episode length; OPS3’s future horizon contracts near termination. **Exploiters:** all, especially renewal and temporal policies. **Magnitude:** potentially material; all 29 BASE outages occur at step zero. Reported prefix contrasts—2.425% at 10 steps, 3.071% at 28—are not equivalent to fresh runs configured with those horizons. **Status:** DECLARED construction; the claim of a representative stationary age distribution is not established. **Handle: FIX horizon-dependent initialization in the successor; SENSITIVITY using fixed initial states, burn-in and complete cycles.** [step.py:1391](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/step.py:1391), [ee_axis_state.py:314](/home/sat/mcrl-leo-handover-e1/src/mcrl/runtime/ee_axis_state.py:314), [EVIDENCE-01:163](/home/sat/mcrl-v023-astra-physics/EVIDENCE-01-REDTEAM-OPUS.md:163)

**B09 — The actual C1/C2 objectives differ from whole-trajectory pooled EE.**  
**Mechanism:** current C1 targets focal \(\Delta B_u-\lambda\Delta E_{\text{network}}\), omitting contemporaneous nonfocal bit changes by design. Current C2 averages up to three projected future marginal surpluses against a frozen background and applies \(-\kappa\) after projected service loss. Persistence is absorbing within that projection, although the live environment can reconnect. Their sum is not an identity for realized pooled EE. **Exploiters:** C3-S/oracles can improve the global endpoint by correcting these surrogate limitations; C1/C2 can learn renewal incentives present in their teachers. **Magnitude:** unmeasured contrast contribution. Active \(\kappa=10.0971\) Gbit gives a normalized loss of one per lost projected offset; \(\kappa/\lambda\approx85.26\) J is an objective-equivalent scale, not physical handover energy. **Status:** DECLARED across source contracts and OPS3. **Handle: DECLARE the actual comparison; matched objective/information SENSITIVITY.** [Repricing contract:54](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md:54), [ee_axis_ops3.py:724](/home/sat/mcrl-leo-handover-e1/src/mcrl/runtime/ee_axis_ops3.py:724), [ee_axis_ops3.py:780](/home/sat/mcrl-leo-handover-e1/src/mcrl/runtime/ee_axis_ops3.py:780)

### MEDIUM

**B10 — Idealized PA efficiency and back-off strongly set the denominator.**  
**Mechanism:** throughout the feasible range,
\[
P_{\rm supply}(p)=\frac{\sqrt{p\,p_{\rm sat}}}{0.35},
\quad p_{\rm sat}=1.65\,10^{5/10}=5.21776\ {\rm W}.
\]
There is no measured quiescent term or waveform-dependent efficiency curve. **Exploiters:** all; concavity favors sharing a PA and creates different incentives from constant efficiency. **Magnitude:** at 0.825 W, efficiency is 13.917% and supply is 5.92790 W; at 1.65 W, efficiency is only about 19.68%, not 35%. A 1% RF reduction produces approximately 0.5% PA reduction. Five additional dB of back-off, holding RF output fixed, multiplies this supply expression by 1.778. Relative effects depend on beam-power distributions. **Status:** DECLARED engineering idealization and scenario parameters. **Handle: SENSITIVITY to independently specified PA curves; do not apply back-off twice.** [link_budget.py:254](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:254), [link_budget.py:468](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:468)

**B11 — The 1.65 W cap and 0.825 W start are internally consistent choices, not uniquely sourced hardware values.**  
**Mechanism:** B4 retains an inherited cap after checking \(39\times1.65\le100\) W. That inequality does not derive 1.65 W. Likewise, choosing a factor-of-two headroom derives a 3.010 dB **relative** loss budget, not an absolute cell-edge admission test. **Exploiters:** all; cold-start feasibility and renewal thresholds depend on this choice. **Magnitude:** changing RF scale changes noise-limited rates and PA draw; changing the cap/start ratio changes outage and renewal behavior. C3-S sensitivity is unknown. The older 0.718 dB measured excursion is not a universal bound on the 30-step warm-start panel. **Status:** DECLARED, with overstated “not a free parameter” and geometric-derivation prose. **Handle: FIX provenance wording; SENSITIVITY with coupled parameter changes.** [link_budget.py:175](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:175), [link_budget.py:242](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:242), [link_budget.py:737](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:737)

**B12 — Full-buffer capacity is counted as useful bits without a demand constraint.**  
**Mechanism:** every served rate contributes continuously, regardless of queued traffic, demand satisfaction or whether additional capacity has application value. There is no finite-workload completion or idle-traffic accounting. **Exploiters:** all; policies can favor users with high capacity even when a finite-demand system would have nothing left to send. **Magnitude:** absolute delivered-bit EE can differ substantially. FULL’s +1.6092% capacity-bit gain could shrink, vanish or change under demand limits; the receipts cannot quantify it. **Status:** IMPLIED by unconditional rate integration. **Handle: DECLARE full-buffer capacity EE; SENSITIVITY with fixed offered traffic if claiming useful delivery.** [step.py:964](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/step.py:964), [run_v023_c3s_screen.py:793](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_screen.py:793)

**B13 — Shannon rates give immediate, smooth rewards for arbitrarily small SINR improvements.**  
**Mechanism:** \(R_u=(166.667\ {\rm MHz}/U_b)\log_2(1+\gamma_u)\), using realized post-action wanted signal and interference. There is no finite MODCOD set, coding gap, BLER, spectral-efficiency ceiling, pilot/header overhead or retransmission charge. **Exploiters:** all; nominal search can rank gains too small to change an actual MODCOD. **Magnitude:** a common fixed overhead factor scales absolute EE but cancels the percentage contrast for unchanged actions. Thresholds, ceilings and action-dependent overhead do not cancel and could materially alter the +1.6092% bits contribution. **Status:** DECLARED Shannon model; omitted implementation losses follow from it. **Handle: DECLARE capacity interpretation; SENSITIVITY to a frozen link-to-system mapping.** [link_budget.py:590](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:590), [step.py:958](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/step.py:958)

**B14 — Equal sharing is TDMA; treating it as FDMA would create a new inconsistency.**  
**Mechanism:** the declared interpretation is equal airtime over the full beam bandwidth. Therefore full-band \(kTB\) noise during a user’s slot and the \(1/U_b\) average-rate factor are compatible. Replacing noise by \(kT(B/U_b)\) without changing RF and interference allocation would manufacture extra SINR. **Exploiters:** all can exploit the fixed sharing policy, but there is no demonstrated missing divisor today. **Magnitude:** omitting the load divisor inflates each user’s rate by \(U_b\). Under the actual formula, merging two identical singleton beams halves total rate; my fixture gives **1.55% lower EE** after merging because the shared baseband cost is amortized differently. Contrast sign is therefore not predetermined. **Status:** DECLARED. **Handle: DECLARE and preserve the resource interpretation; resolve B02 consistently.** [link_budget.py:367](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:367), [link_budget.py:598](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:598)

**B15 — Interference is a closed, simultaneously radiating, three-colour model.**  
**Mechanism:** interference includes every active co-colour beam in the simulated population, using beam-maximum RF power. Other colours are perfectly orthogonal; the serving beam is excluded; same-satellite beams receive full terminal gain because they arrive from the same direction. There is no external traffic field, imperfect orthogonality or independently scheduled beam activity. **Exploiters:** all, especially coordinated beam evacuation and colour-aware moves. **Magnitude:** both pooled EE and the contrast are sensitive to the interference field. An older probe found approximately 97.9% intra-satellite interference, but that is not the current panel’s decomposition. Removing a beam can therefore yield both PA savings and nonfocal rate gains. **Status:** DECLARED. **Handle: DECLARE scope; SENSITIVITY to scheduling and an independently specified background field.** [interference.py:277](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/interference.py:277), [interference.py:349](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/interference.py:349), [LINK-BUDGET-NOTES.md:227](/home/sat/mcrl-leo-handover-e1/docs/LINK-BUDGET-NOTES.md:227)

**B16 — Propagation and transmit-pattern assumptions shape every apparent energy saving.**  
**Mechanism:** free-space loss, atmospheric/scintillation loss, LOS shadowing, a fixed Bessel pattern and ideal steering determine rates without changing required power except through transmit-angle recurrence. There is no weather-driven power adaptation, blockage state or scan-dependent hardware draw. Positive but weak off-axis links can start at 0.825 W. **Exploiters:** all; geometry search can exploit weak-link admission and ideal steering. **Magnitude:** large potential absolute effect; contrast unknown. The cap-based reference link budget is 3.010 dB above a new segment’s 0.825 W RF level and must not be presented as its actual received level. **Status:** DECLARED equations and scenario substitutions; no validation of an operational payload. **Handle: DECLARE; SENSITIVITY to propagation/steering assumptions, preserving consistent gain and loss units.** [link_budget.py:50](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:50), [antenna.py:43](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/antenna.py:43), [LINK-BUDGET-NOTES.md:129](/home/sat/mcrl-leo-handover-e1/docs/LINK-BUDGET-NOTES.md:129)

**B17 — Confirmed receive-pattern source error, plus an unsupported near-axis extrapolation.**  
**Mechanism:** with \(D=0.6\) m and 20 GHz, \(D/\lambda=40.0277<50\). S.465-6 therefore uses
\[
\theta_{\min}=\max(2^\circ,114(D/\lambda)^{-1.09})=2.04330^\circ,
\]
not the code’s large-dish expression giving 2.49827°. Separately, the code extrapolates \(32-25\log_{10}\theta\) below the valid envelope: it returns 32 dBi at 1° and 24.474 dBi at 2°, contradicting the docstring’s claim of a 35 dBi plateau throughout that region. The thesis correctly calls the extrapolation a simplification. **Exploiters:** all can benefit from the assumed rejection of nearby satellites. **Magnitude:** fixing the diagnostic threshold alone changes **no endpoint power or bits**; changing the near-axis pattern can change inter-satellite interference materially, with unknown C3-S impact. **Status:** DECLARED extrapolation; incorrect source derivation and contradictory prose. **Handle: FIX the threshold/prose; SENSITIVITY or versioned FIX for the physical pattern.** [antenna.py:172](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/antenna.py:172), [antenna.py:197](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/antenna.py:197), [Thesis:229](/home/sat/mcrl-leo-handover-e1/.scratch/chinese-word-v023-lcsrs-20260905-r2/mc-modqn-base.md:229), [ITU-R S.465-6, recommends 2](https://www.itu.int/dms_pubrec/itu-r/rec/s/R-REC-S.465-6-201001-I!!PDF-E.pdf)

**B18 — Fading keys prevent rerolling, but channel statistics still favor particular comparisons.**  
**Mechanism:** keyed fading depends on world, event, step and physical NORAD, with a user vector; it does not depend on arm, action slot or renewal count. Same-satellite beams share the user-satellite fading realization. Observation and physics events differ. Shadowing is zero-mean in dB, not unit-mean in linear power; nominal shadow zero is a median-channel evaluation, not expected throughput. **Exploiters:** all respond to these statistics; a realized-channel oracle has additional information. There is no same-satellite renewal reroll under this keyed field. **Magnitude:** at 3 dB shadow standard deviation, mean linear gain is 1.26945; that is not a 26.9% rate uplift because of the logarithm and interference. Relative EE impact is unknown. **Status:** DECLARED. **Handle: DECLARE correlation/normalization; SENSITIVITY to physical temporal correlation and delayed CSI.** [keyed_fading.py:114](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/keyed_fading.py:114), [keyed_fading.py:137](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/keyed_fading.py:137), [link_budget.py:151](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:151)

**B19 — Nominal search has exact energy knowledge and richer joint context.**  
**Mechanism:** C3-S evaluates the environment’s deterministic power formula using copied segment/association state and joint actions, with unit Rician gain and zero shadow for nominal rates. It can price beam opening/closing exactly. This is stronger than a learned local approximation. However, current C1 state already contains previous power, gain ratio and segment age; current C2 already uses projected geometry. “BASE is blind to the anchor” and “only C3 uses physics” are incorrect. **Exploiters:** C3-S and oracles most directly. **Magnitude:** nominal energy matched realized energy in 720/720 decisions; nominal rate errors remain. Its share of the +2.883% advantage is unmeasured. **Status:** DECLARED across implementation, insufficiently captured by a generic “nominal” label. **Handle: DECLARE information access; compare against matched nonlearned controls.** [c3s_policy.py:490](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/c3s_policy.py:490), [ee_axis_state.py:3](/home/sat/mcrl-leo-handover-e1/src/mcrl/runtime/ee_axis_state.py:3), [EVIDENCE-01:173](/home/sat/mcrl-v023-astra-physics/EVIDENCE-01-REDTEAM-OPUS.md:173)

**B20 — Different frozen energy prices do not optimize an identical ratio objective.**  
**Mechanism:** current learner sources use \(\lambda=118.424223\) Mbit/J; C3-S uses \(\eta_{\rm ref}=124.075741\) Mbit/J in \(B-\eta_{\rm ref}E\). A fixed surplus ranking is not generally the same as maximizing finite-trajectory \(B/E\). A higher price favors lower energy; it is **not necessarily conservative for the EE contrast**. **Exploiters:** all optimize their respective prices; search can exploit differences between them. **Magnitude:** C3-S’s price is 5.67% above this panel’s realized BASE ratio. The resulting action and EE sensitivity is unknown; percentage price mismatch is not percentage EE bias. **Status:** DECLARED, prospectively frozen. **Handle: DECLARE; permitted frozen-grid sensitivity only, with no outcome-driven repricing.** [Repricing contract:17](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md:17), [c3s_config.json:3](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/c3s_config.json:3), [c3s_policy.py:230](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/c3s_policy.py:230)

**B21 — Hardware resource limits are largely absent.**  
**Mechanism:** there is no live aggregate satellite power allocator, RF-chain ceiling, per-beam capacity ceiling, feeder-link bottleneck or processing-throughput constraint. Available geometric pointings and eligible users determine activity. **Exploiters:** all; search/oracles can rearrange traffic without these coupled constraints. **Magnitude:** potentially material outside the frozen scenario; no demonstrated 100 W RF-budget violation here because 39 beams at 1.65 W total only 64.35 W per satellite. The 260.5 W network **supply** figure must not be compared directly with a per-satellite RF limit. Current contrast contribution is unknown. **Status:** DECLARED exclusions and compatibility check. **Handle: DECLARE scope; SENSITIVITY to a specified payload architecture rather than inventing limits.** [link_budget.py:188](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:188), [link_budget.py:425](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:425), [link_budget.py:276](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:276)

**B22 — Computation and decision latency are free in the physical endpoint.**  
**Mechanism:** search consumes computation but no modeled controller energy; actions are applied without wall-clock-induced staleness or deadline misses. This permits expensive optimization within the same simulated decision snapshot. **Exploiters:** C3-S and oracles disproportionately. **Magnitude:** energy impact is unmeasured and may lie outside the payload boundary. The supplied audit reports comparable mean decision times of BASE 1.885 s, FULL 32.497 s and LITE 14.882 s; FULL exceeds the 30.08 s interval on its mean, while LITE’s mean does not. Deadline tails and deployment hardware remain unresolved. **Status:** endpoint exclusion IMPLIED; timing instrumentation mismatch established separately. **Handle: DECLARE compute boundary; FIX latency reporting and test deadline-aware execution.** [EVIDENCE-02:199](/home/sat/mcrl-v023-astra-physics/EVIDENCE-02-HARNESS-AUDIT-OPUS.md:199)

**B23 — Legacy reward penalties and scales must not be attributed to the current heads.**  
**Mechanism:** legacy rewards include \(r_1=R_u/P^N\), \(r_2=-\Phi\), and \(r_3=-U_b\), with normalization, weights and temporal accumulation. Summed \(r_3=-\sum_b U_b^2\) favors spreading, while the energy model can favor consolidation. Summing or discounting per-step EE also differs from pooled EE. **Exploiters:** legacy learners face these trade-offs; endpoint search does not. **Magnitude:** potentially substantial for genuinely legacy-trained comparisons, but **the Φ-trained-BASE explanation is unsupported for C3-S’s authenticated repriced Q1/Q2 heads**. Their active objectives are B09. **Status:** DECLARED legacy terms; checkpoint attribution must be corrected. **Handle: FIX the explanatory record; DECLARE the objective separately for every sealed experiment.** [step.py:1051](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/step.py:1051), [service.py:264](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/service.py:264), [authority.json:11](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/authority.json:11), [EVIDENCE-02:70](/home/sat/mcrl-v023-astra-physics/EVIDENCE-02-HARNESS-AUDIT-OPUS.md:70)

### LOW direct contribution or currently correct accounting

**B24 — Per-active-beam circuit power imports a hardware mapping the source does not establish.**  
**Mechanism:** 0.338 W is correctly summed from DAC/mixer/LPF/baseband-amplifier entries, then assigned to each active beam. You et al.’s architecture separately includes RF-chain, phase-shifter and oscillator terms; its simulation uses 2 GHz and 20 MHz. Those typical component values do not validate a 20 GHz satellite beam’s complete circuitry. **Exploiters:** all through beam extinction. **Magnitude:** approximately 40 beams imply 13.52 W, about 5.2% of BASE power. Half a beam saves only 0.169 W in this term—about **0.065%** of BASE power—so the cited half-beam explanation is mainly PA supply, not circuit power. **Status:** DECLARED number and unsourced beam-to-chain mapping. **Handle: DECLARE; architecture SENSITIVITY.** [link_budget.py:270](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:270), [You et al., §II-C and Tables I–II](https://arxiv.org/pdf/2201.06281)

**B25 — Baseband power is small, shared and switched off with the last beam.**  
**Mechanism:** 0.200 W is charged once per satellite with any radiating beam; neither throughput nor beam count changes that satellite’s baseband charge thereafter. **Exploiters:** all through sharing or emptying a satellite. **Magnitude:** one satellite’s extinction saves 0.200 W, approximately **0.077%** of BASE power. This coefficient alone is unlikely to explain a 2.9% contrast without many changed active-satellite counts; those counts are absent. Real bus/baseband floors belong to B04, not an invented rescaling of this number. **Status:** DECLARED. **Handle: DECLARE and SENSITIVITY; preserve once-per-satellite charging.** [link_budget.py:273](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:273), [link_budget.py:521](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:521)

**B26 — Pooled ratio-of-sums is correct, but boundary and zero-energy handling matter.**  
**Mechanism:** the endpoint is \(\sum B/\sum E\), giving joule-weighted step efficiencies. Mean-of-ratios answers a different question. The core permits a dark zero-bit/zero-energy step, whereas the C3-S metric rejects nonpositive power; silent removal of such steps would select the sample. **Exploiters:** no demonstrated pooling exploit in these receipts; a different harness could introduce one. **Magnitude:** mean-of-unit-ratios gives +2.885448% rather than +2.883167%, so current pooling choice does not explain the headline. Zero-energy rejection has no demonstrated effect in this panel. **Status:** DECLARED estimand; incompatible dark-step treatment is visible in code. **Handle: retain pooling; FIX/declare dark-step semantics without dropping observations.** [run_v023_c3s_screen.py:1036](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_screen.py:1036), [energy_efficiency.py:146](/home/sat/mcrl-leo-handover-e1/src/mcrl/runtime/energy_efficiency.py:146), [EVIDENCE-02:51](/home/sat/mcrl-v023-astra-physics/EVIDENCE-02-HARNESS-AUDIT-OPUS.md:51)

**B27 — Beam deduplication, common denominators and dimensional guards currently avoid known historical artifacts.**  
**Mechanism:** PA supply is charged once per physical beam; baseband once per active physical satellite; each user’s additive EE contribution uses the same network denominator. The old private-power-share \(\kappa\) closure was withdrawn. It is unrelated to active OPS3 \(\kappa_{\rm bits}\). Beam-count consistency is checked, but a matching total alone cannot prove correct physical satellite grouping. **Exploiters:** none through the inspected correct path; reintroducing per-user PA charges penalizes occupancy artificially. **Magnitude:** historical per-user charging caused order-two denominator inflation; no such current defect was found. No extra factor of \(\Delta t\), transmit gain or fixed power is evident in the inspected endpoint path. **Status:** DECLARED corrections. **Handle: retain and independently test; no model change warranted.** [link_budget.py:549](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/link_budget.py:549), [step.py:985](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/step.py:985), [energy_efficiency.py:218](/home/sat/mcrl-leo-handover-e1/src/mcrl/runtime/energy_efficiency.py:218)

**B28 — Bessel branch error can create small artificial angular preferences.**  
**Mechanism:** the antenna implementation retains an ascending-series branch through \(|\mu|=34\), switching to Miller above it. The source acknowledges residual error near the boundary. I reproduced \(J_1(34)=0.1332130747\) on the routed branch versus \(0.1329711811\) with Miller. **Exploiters:** all; sufficiently detailed geometry search can rank numerical discrepancies. **Magnitude:** the notes estimate about 0.07 dB pattern error near this region; no pooled or C3-S contribution is established. The catastrophic large-argument failure is already guarded against. **Status:** DECLARED residual, not a newly discovered catastrophic runtime failure. **Handle: independent precision test; versioned numerical FIX if retained accuracy is inadequate.** [bessel.py:47](/home/sat/mcrl-leo-handover-e1/src/mcrl/runtime/bessel.py:47), [bessel.py:139](/home/sat/mcrl-leo-handover-e1/src/mcrl/runtime/bessel.py:139), [LINK-BUDGET-NOTES.md:49](/home/sat/mcrl-leo-handover-e1/docs/LINK-BUDGET-NOTES.md:49)

## C. Options for anchored power

### (i) Keep the declared model, disclose it, and complete churn-null attribution

This is defensible **as a deliberately defined simulation benchmark**. It does not establish operational NTN energy savings.

- **Sealed BASE/C1/C2, R7, stage C, E1, S0 and C3-S v1:** retain their numbers and seals. Correct the explanations of their training objectives and restrict conclusions to the declared model. The existing 2.883%/2.922% results remain numerically meaningful under that model.
- **Attempt #4:** can use existing physics and source lineage if the owner explicitly chooses this benchmark scope.
- **Paper:** identify entry-history power control, partial payload energy, full-buffer Shannon bits, admitted-user service, and model-based search privilege. Avoid attributing the gain to learned coordination or physically realizable renewal savings without controls.
- **Cost:** the owner’s approximately **2–3 worker-hours** for the developing control panel is a reasonable stated budget for that panel, not a guarantee for every proposed sensitivity.

The requested arms are useful, with these declarations:

| Arm | Required interpretation |
|---|---|
| BASE | Authenticated frozen heads and native state evolution. |
| LITE | Frozen coordinator configuration and candidate construction. |
| NULL | Same machinery as LITE, but commits BASE’s actions; must reproduce BASE’s complete trace. |
| RANDOM_RENEW | A prospectively fixed legal renewal rule and independent random stream; no realized-rate selection. |
| BASE_FORCED_RENEW_4 | Specify whether it forces a legal association change or resets the power anchor without changing association. The latter is a mechanism intervention, not a deployable handover policy. |

Record physical handovers, forced anchor resets, beam/satellite activation transitions, actual segment ages and gains, and the full power decomposition. More handovers alone do not prove anchor causation; a coordinator can obtain better renewal opportunities with fewer handovers.

**RANDOM_RENEW beating BASE is an admissible diagnostic result, not a failed harness test.** NULL equality is the invariance requirement. The current evidence lacks the necessary counters. [EVIDENCE-01:72](/home/sat/mcrl-v023-astra-physics/EVIDENCE-01-REDTEAM-OPUS.md:72)

### (ii) Add handover energy consistently

Define physical event energies \(\epsilon_1,\epsilon_2\) and an explicit boundary:
\[
E'=\sum_t\Delta t\,P_t+\epsilon_1 H_1+\epsilon_2 H_2+E_{\rm other\ transitions}.
\]

**Do not equate \(\Phi_1=0.5,\Phi_2=1\) with joules.** The code labels them scenario preference coefficients and only sources their ordering. Their 1:2 ratio is not itself a hardware-energy measurement. [action_contract.py:408](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/action_contract.py:408)

Outcome-independent calibration requires:

1. A component boundary: satellite payload only, or an explicitly extended satellite/terminal/gateway system.
2. Event definitions covering successful handover, re-entry, failed acquisition, beam wake-up and overlap.
3. Measured or independently sourced incremental power integrated over event duration, subtracting already-counted baseline power.
4. Frozen estimates or sensitivity bounds before opening the new outcomes.

The repository already records that no boundary-compatible handover-energy source had been established. That is a reason to keep coefficients symbolic or use labeled bounds, not to infer them from the desired EE result. [ADR-004:21](/home/sat/mcrl-leo-handover-e1/docs/decisions/ADR-004-payload-boundary-time-only-c2.md:21)

For scale only, FULL saves approximately **97.04 J per decision** in modeled steady-state energy. Using the rounded receipt bit ratio, its overall EE advantage disappears when
\[
E_{\rm event,FULL}-1.016092\,E_{\rm event,BASE}
\gtrsim223.15\ {\rm J/decision}.
\]
This is a **break-even diagnostic, never a calibration target**.

- **Sealed results:** unchanged as original endpoints. Additional event-adjusted scores can be reported for fixed traces if events are recoverable.
- **Attempt #4:** adding event energy to the claimed optimization objective requires corresponding teacher/target changes; merely rescoring old heads is a transfer evaluation.
- **Paper:** an extended endpoint does not repair arbitrary entry targets or B02’s RF inconsistency.
- **Cost:** event collection/replay and calibration first; retraining is additional. No defensible hardware-calibration time estimate is available from this checkout.

### (iii) Use a versioned, history-independent physical successor — recommended

**Changing the cadence is insufficient: the current recurrence already recomputes power each 30.08 s step. The entry-dependent target must change.**

The smallest clear forward-link successor is:

\[
p_b(t)=p_\star\quad\text{for an active beam},
\qquad
S_u(t)=p_b(t)G^T_u(t)L_u(t)F_u(t)G^R_u(t).
\]

Use that **same beam RF power** in wanted signal, interference and PA accounting. Rates adapt to current geometry at each decision step. This is fixed RF/boresight EIRP with rate adaptation; it should not be called NR closed-loop power control. Taking \(p_\star=0.825\) W preserves the existing starting RF scale as a declared benchmark choice without fitting a new number.

If adjustable power is scientifically essential, use a target prescribed independently of segment entry and specify its update, feedback and saturation behavior. A fixed gain-compensation target is another model; it does not make received power track off-axis gain in the same way as fixed RF.

**Consequences:**

- Preserve all old sealed records; do not overwrite or retroactively reinterpret them.
- Regenerate C1/C2 teacher quantities, OPS3 power projections and physics-dependent source caches. Reusing old targets would train on the old objective.
- Train successor BASE/C1/C2 before making learned-performance claims in the successor.
- Repeat the stage-C comparisons and any E1, S0 and C3-S evidence used to support the successor’s claims.
- Repeat R7 if its negative/positive finding is claimed to hold under the successor. Otherwise retain it explicitly as historical old-model evidence.
- Frozen old heads evaluated under new physics are useful transfer controls, not substitutes for retrained successor results.
- Re-evaluation must use a declared development/validation protocol; a physics change is not permission to reopen and select on sealed TEST outcomes.

**Cost:** provisionally one to several engineering days for the coherent implementation, independent fixtures, source-pipeline updates and small validation runs, **plus the required source-generation and training budgets**. This is an engineering estimate, not a measured runtime. Changing only `recurrence_power_w` is not the complete job: B02, initialization, OPS3 and lineage all depend on it. [ee_axis_ops3.py:717](/home/sat/mcrl-leo-handover-e1/src/mcrl/runtime/ee_axis_ops3.py:717), [step.py:783](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/step.py:783)

### (iv) Build a scheduled transmitter and transition model

A more complete successor can explicitly allocate user airtime \(d_u\), transmit at user-slot power \(p_u\), and integrate
\[
\overline P_{\rm PA,b}=\sum_{u\in b}d_u\,P_{\rm supply}(p_u),
\]
with schedule-consistent interference, useful-time interruptions and payload sleep/wake states.

This resolves the ambiguity behind “one beam, one power” and makes real consolidation trade-offs assessable. It also introduces scheduling, hardware-state and calibration choices that the present evidence does not settle.

Its sealed-result and retraining implications are at least those of (iii), with greater implementation/calibration cost. I would not make this larger model a prerequisite for a clearly scoped fixed-RF successor.

### Exact declaration recommended before successor outcomes

> **Physics successor declaration.** All existing sealed results remain attached to their original code, targets and endpoint. The successor removes segment-entry history from RF power selection. Each active beam transmits at the prospectively fixed value 0.825 W; the same beam RF power is used for wanted signal, interference and PA supply. Current geometry determines link gain at each decision step. No power target is renewed by handover, outage, re-entry or dwell boundary.  
>  
> Initial physical state generation is independent of the scored horizon. The primary endpoint remains pooled full-buffer Shannon bits divided by the explicitly named partial payload energy; admitted-user service is reported separately from delivered-rate/QoS sensitivities. Omitted event energy is an accounting exclusion, not a claim that physical handover energy is zero.  
>  
> C1/C2 targets and all physics-dependent projections are regenerated under the successor. Parameter values, source splits, control arms, sensitivity definitions and acceptance tests are frozen before opening successor outcomes. No coefficient or model variant is selected to preserve, remove or enlarge the previous C3-S advantage. Previous heads are labeled transfer controls; successor claims use successor-trained comparators.

This declaration preserves a tractable benchmark while removing the specific renewal target and RF inconsistency. It does **not** claim to solve every realism limitation in B.

## D. Stage-A ordering

**HOLD attempt #4 at the launch boundary until the owner chooses the physics and claim scope.**

The reason is concrete: its source targets and temporal projections depend on the disputed law. If the paper needs physical EE claims and adopts the recommended successor, launching now creates an avoidable old-physics training run. The existence of many sealed old-physics results does not make additional training under that model necessary.

During the hold, complete the already-authorized churn controls, recover/authenticate the receipt-producing source, and execute the analytic audit below. None requires new formal training or reopening sealed TEST results.

If the owner instead chooses option (i) and accepts its narrower benchmark claims, release attempt #4 under the existing physics immediately after its ordinary launch gates; there is no need to wait for every possible hardware sensitivity. **The fastest path is one explicit model decision followed by consistent training, rather than starting formal training while that decision remains unresolved.**

## E. One-pass audit execution plan

Use an independent scalar reference calculation and small synthetic worlds. Tests that call the production formula twice establish parity, not correctness. Keep **legacy characterization expectations** separate from **successor acceptance expectations**.

First recover the receipt-producing tree and authenticate code, checkpoints, source targets, world keys and configuration. Verify that every arm starts from the same complete state and that detached evaluations leave segment state, previous associations, candidate state and RNG state unchanged. This is required because current local C3-S files are newer than the receipt bindings. [EVIDENCE-02:8](/home/sat/mcrl-v023-astra-physics/EVIDENCE-02-HARNESS-AUDIT-OPUS.md:8)

### Known-answer fixtures for every inventory item

| Item | Fixture and required known answer |
|---|---|
| **B01 Anchor** | One link: \(G_\tau=1\), current gains \(0.5,2\) produce \(1.65,0.4125\) W and \(pG=0.825\) in legacy physics. Renewing at the same current geometry changes the legacy target. In the successor, identical current physical states give identical RF, bits and joules regardless of segment history. Test association change, outage/re-entry and unchanged association across a dwell boundary separately. |
| **B02 RF consistency** | Two users on one beam request 0.825 and 1.65 W. With identical channel factors, legacy wanted powers differ by two while both are charged/interfere through 1.65 W. The selected successor interpretation must yield either one common transmitted RF power or explicitly integrated user slots; assert consistency at the received-field level. |
| **B03 Maximum/consolidation** | Two identical users, no mutual interference, synthetic \(B_b=8\) Hz and SINR 3. Two singleton beams give 32 bit/s; one shared beam gives 16 bit/s. With default 0.825 W PA parameters and one satellite, power changes from 12.7318009 to 6.46590045 W. Merging reduces EE by about 1.5466%. Also test adding/removing a nonmaximum versus maximum user. |
| **B04 Idle/switching** | One beam active for one interval then empty. Legacy draw changes from 6.46590045 W to zero. A declared retained-idle fixture must instead retain exactly its configured floor; a wake-up fixture adds exactly one event charge. Apply a common total floor equally to all arms and verify the analytic ratio transformation. |
| **B05 Handover cost** | Two otherwise identical traces with different event counts have identical legacy bits/joules when anchor effects are held fixed. Under an extension, the difference is exactly \(\epsilon_1\Delta H_1+\epsilon_2\Delta H_2\). For interruption \(T\), subtract \(RT\) once. Distinguish episode start, failed service, re-entry and successful physical handover. |
| **B06 Service** | Two legal, power-feasible users with SINR zero remain two “served” users but produce zero Shannon bits. One infeasible user must be excluded from served load and beam maximum. Separately demonstrate that a same-state nominal service floor does not guarantee equality to another arm’s future trajectory. |
| **B07 Time/dwell** | For \(R(t)=2+t\) over two seconds, true integrated bits are 6; a left snapshot gives 4. Verify which estimand is implemented. At constant rates/power, 47 × 0.640 s is applied exactly once. A newly D2-eligible satellite must wait until the next four-step identity refresh; crossing that boundary must not itself reset a continuing segment. |
| **B08 Initialization/horizon** | Fix physical initial state and RNG root, then change only scored horizon from 10 to 30. The successor’s initial state and common trajectory prefix must remain identical. Legacy `uniform-episode-length` should expose its differing age range. Validate any claimed warm segment against historical visibility/service, and test terminal OPS3 horizon explicitly. |
| **B09 Current targets/κ** | With \(\Delta t=1,\Delta R_u=10,\Delta P=2,\lambda=3\), C1 target is 4 bits. With two future offsets, active surplus 4 then service loss and \(\kappa=8\), uncentered C2 target is \((4-8)/2=-2\). A service-loss/recovery sequence must show legacy OPS3’s absorbing persistence; distinguish this from live re-entry. |
| **B10 PA** | Independently calculate \(\xi(0.825)=0.1391723775\), supply \(=5.9279004542\) W, and \(\xi(1.65)\approx0.19682\). Zero RF gives zero legacy PA draw. Positive RF with zero efficiency must fail. Check the square-root elasticity and that back-off is not also subtracted from emitted RF a second time. |
| **B11 Cap/headroom** | Exactly 1.65 W is feasible; the next representable larger value is infeasible. A factor-two relative gain drop reaches the boundary regardless of the absolute start gain. Independently verify \(39\times1.65=64.35\) W; do not treat that identity as deriving 1.65 W. |
| **B12 Demand** | A user has 5 queued bits but 10-bit interval capacity. Legacy capacity accounting reports 10; a delivery-based sensitivity reports 5 and never serves nonexistent payload. Keep the two endpoints distinctly named. |
| **B13 Shannon** | At SINR 3 and \(B_b=8\) Hz, one user obtains 16 bit/s; SINR zero gives zero. Add a frozen MODCOD fixture where two nearby SINRs map to the same rate and verify that the apparent Shannon improvement vanishes. Fixed 10% overhead must reduce absolute EE by 10% while leaving a fixed-action relative contrast unchanged. |
| **B14 TDMA/noise** | Two equal users each occupy half the time but see full-band noise during their slot. Their average rates are 8 bit/s each in the preceding fixture. An FDMA alternative must explicitly divide bandwidth, RF allocation and interference consistently; reject a fixture that divides noise alone. |
| **B15 Interference** | Give wanted beam, same-satellite co-colour beam, different-colour beam and different-satellite same-cell co-colour beam known received powers. Expected interference excludes only the wanted and different-colour terms. Same cell ID on a different satellite must still interfere. Remove one physical beam and verify its contribution disappears exactly once. |
| **B16 Propagation/transmit gain** | Double distance: free-space received power quarters. Add 10 dB loss: power divides by ten. Verify \(G_T(0)=2000\), \(G_T(1.66^\circ)\approx1000\), degree/radian handling and exactly one transmit-gain factor. Separate ideal steering from any declared scan-loss sensitivity. |
| **B17 Receive pattern** | Independently compute \(D/\lambda=40.02769\) and S.465-6’s applicable \(\theta_{\min}=2.04330^\circ\). Characterize existing receive gains as 35, 32 and 24.47425 dBi at 0°, 1°, 2°. Correcting only the diagnostic threshold must leave trajectories unchanged. Any new near-axis pattern needs separate frozen expected values. |
| **B18 Fading** | Reorder candidate/beam enumeration and renew an association: keyed user–NORAD–step physics fading must remain identical. Different event labels must use their own fields. Check unit-mean Rician power statistically and zero-mean-dB shadow analytically; at \(\sigma=3\) dB, mean linear shadow factor is 1.269452, not one. |
| **B19 Information/purity** | Evaluate candidates in forward and reverse order and with duplicates: nominal metrics and committed BASE state remain identical. Alter the previous segment anchor: current expanded state must expose the relevant change. For fixed actions, nominal versus realized power must match; nominal versus realized bits need not. |
| **B20 Pricing** | BASE \(B=10,E=10\); candidate \(B=7,E=8\), equal service. At \(\eta_{\rm ref}=2\), surplus selects the candidate even though EE falls from 1 to 0.875. At the BASE ratio 1, it rejects it. Authenticate learner λ and coordinator η independently; never infer one from the other’s configuration. |
| **B21 Capacity limits** | Light every physical pointing at cap and independently sum RF per satellite. Verify the declared 39-beam reference gives 64.35 W. Any extended aggregate RF, chain, feeder or processing constraint must bind in a fixture specifically exceeding it and remain distinct from DC supply power. |
| **B22 Compute/deadlines** | Inject known selector delays above and below 30.08 s. An instantaneous simulator retains legacy outcomes; a deadline-aware variant must apply its declared stale-action/hold rule. Measure inference/search separately from audit fingerprints and report deadline quantiles, not only means. |
| **B23 Legacy rewards** | Same satellite/new cell gives \(\Phi_1=0.5\); different satellite gives \(\Phi_2=1\), never 1.5; re-entry follows its declared ledger rule. Two users on one beam give summed \(r_3=-4\); two singleton beams give −2. Authenticate whether each evaluated checkpoint actually trained on these terms. |
| **B24 Circuit** | Independently sum \((300+19+14+5)\) mW = 0.338 W. Adding a second user to an active beam adds zero circuit draw; activating a second beam adds exactly 0.338 W before baseband effects. An architecture sensitivity must account for its declared RF-chain and phase-shifter multiplicities separately. |
| **B25 Baseband** | Two active beams on one satellite have fixed draw \(2(0.338)+0.2=0.876\) W. One beam on each of two satellites gives 1.076 W. Adding an empty satellite changes neither under legacy physics. |
| **B26 Pooling/zero** | Steps \((B,E)=(10,1),(10,9)\) give pooled EE 2, whereas mean step EE is \(5.555\ldots\). Duplicate the dataset: EE stays 2. A zero-bit/zero-energy step remains in service opportunities and contributes zero to sums; positive bits at zero energy fail. An all-dark episode needs an explicit disposition, never silent exclusion. |
| **B27 Accounting/units** | Two users on one physical beam must incur one PA draw. With rates 4 and 6 and network power 5, additive contributions are 0.8 and 1.2 and sum to EE 2. A mismatched beam tally must fail. At 30.08 s, the one-beam default fixture consumes **194.4942857 J**. Verify physical `(NORAD, cell)` identity, not action-slot identity, controls deduplication. |
| **B28 Numerics** | Compare the antenna/Bessel computation against an independent high-precision implementation over the live domain, especially around \(\mu=34\) and pattern nulls. Use both absolute power error and relative error away from nulls; scalar/vector parity alone is insufficient. |

The recurrence, cap boundary, beam maximum, PA calculation, shared-baseband examples, TDMA rate example, zero-power accounting and mismatched-count rejection were exercised in this audit. The receive-pattern discrepancy and applicable S.465-6 branch were also independently checked. **The full environment/replay checklist remains execution work; it has not been reported as passed.**

### Required replay receipt and acceptance gates

Each step should expose enough raw quantities to reconstruct both endpoints independently:

- Physical associations; handover classes; forced-reset indicators; segment start/current gain and age.
- Per-user feasibility, served indicator, rate, wanted power, noise and intra/inter interference.
- Per-beam membership, maximum RF power, PA efficiency/supply, circuit draw and activation transitions.
- Per-satellite active-beam count and baseband draw; any separately modeled idle/event components.
- Interval, raw total bits and joules, nominal metrics, model/checkpoint hashes and fading-field key.

Recompute pooled outcomes without importing the runner’s aggregation helper. Test deliberate mutations: doubled bits, duplicated PA charges, per-beam baseband charges, incorrect pooling, changed physical identifiers, stale segment state and action-dependent fading keys. NULL must reproduce **actions, state and raw component traces**, not merely the same final EE scalar.

Run the five declared arms on the fixed development panel. Report actual segment-age strata alongside dwell phase, event counts, beam changes and power-component changes. Keep world clustering explicit; 36,000 user opportunities are not 36,000 independent experimental worlds. Attribute renewal only through a specified intervention or controlled comparison, and retain results in which random renewal helps—the possibility of that outcome is precisely what this audit is testing.

ASTRA_PHYSICS_AUDIT: ANCHORED_POWER=DECLARED | HANDLE=iii | STAGEA=HOLD | ITEMS=9