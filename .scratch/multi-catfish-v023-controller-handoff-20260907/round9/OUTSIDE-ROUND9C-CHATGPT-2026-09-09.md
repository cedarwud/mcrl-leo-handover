# Round 9C — Publication defensibility of the successor energy model

**Judgment: conditional.** The successor is defensible as a model of **forward-downlink partial-payload energy efficiency under a specified power-control and scheduling architecture**. The supplied material does not establish whole-constellation energy efficiency, a calibrated commercial Ka-band operating point, or guaranteed 50 Mbit/s service. The most serious unresolved issue is the consistency between the transmitted MODCOD, the realised-bit calculation, and the definition of service.

Evidence status: all implementation descriptions and development measurements below are **supplied and unverified against executable code or raw receipts**. Calculations explicitly marked “recomputed” use the supplied equations; they establish internal consistency, not physical calibration. External references are primary standards, original research, or engineering accounts. The review is current to 9 September 2026.

The ZIP contains five Markdown files. File citations use these aliases:

| Alias | Uploaded file and relevant location | Evidentiary limit |
|---|---|---|
| **[A]** | `V025-ANGLE-POWER-EE-NOTE-2026-09-08.md`, introduction, “Exact equations,” “Numbers” | Deterministic single-beam example; explicitly calls its denominator partial-payload energy. |
| **[P]** | `V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-2026-09-08.md`, “Declaration,” especially “Service definition” | Earlier fixed-SINR declaration; does not itself document the subsequent 50 Mbit/s amendment. |
| **[R]** | `VERTICAL-SLICE-REGIMES-SMOKE-2026-09-08.md`, “Cross-regime numbers,” “All-arm pooled realised diagnostics,” “Decision items not honoured” | TRAIN-only development, one world and ten anchors, explicitly `SMOKE_NOT_MATRIX`. |
| **[S]** | `V025-SYNTHETIC-MAP-R1-REPORT-SUPERSEDED-B2-2026-09-08.md`, “Declared fields by grid cell × setting,” “DEFECTS” | Synthetic mechanism report; filename explicitly marks it superseded. Corrected B2 report and referenced raw receipt are absent. |
| **[Q]** | `01-QA-PROMPT.md` | Question/context, including median SINR ≈6.6 dB; no supporting SINR distribution is present in the other files. |

**1. Which elements are standard, simplified, or wrong?**

| Element | Assessment | Publication condition |
|---|---|---|
| Geometry-dependent received power, thermal noise, cochannel interference | Established link-budget structure | Declare antenna-reference planes, power versus amplitude gains, receiver G/T, and bandwidth convention. |
| Lowest discrete MODCOD meeting a rate target under equal-airtime TDM | Defensible controller/scheduler design | It is one chosen operating policy, not a DVB-mandated scheduling rule. Define what happens when no MODCOD meets the target. |
| Coupled capped power-control fixed point | Defensible numerical abstraction | Resolve powers and interference for the same simultaneous transmissions; certify both numerical residual and target feasibility separately. |
| Square-root PA DC law | Recognised analytical approximation | Identify saturation efficiency and physical PA architecture; do not describe it as a universal measured satellite law. |
| Per-slot PA DC followed by airtime integration | Correct under independent TDM beam chains | Apply the nonlinear DC law before averaging; do not charge every user's slot power for the full beam interval. |
| Circuit cost per active beam | Conditional | The beam must map to a genuinely switchable hardware chain. |
| Common cost per active satellite | Conditional | Identify the switched processing block. Satellite bus operation does not cease when its last traffic beam goes dark. |
| Zero standby or a fixed standby fraction | Engineering sensitivity assumption | Define off, ready-idle and transmitting states and which hardware remains powered. The fraction is not a standard constant. |
| 47 × 0.640 s integration | Defensible time discretisation | Geometry integration does not by itself resolve symbol errors, rain dynamics, or ACM feedback delay. |
| A failed user radiates at cap and contributes interference | Physically consistent if actually scheduled | Charge its airtime and DC energy; define whether it fails decoding, the rate target, or both. |
| Feeder/ISL omitted | Acceptable for a declared downlink subsystem | State nonbinding feeder capacity and the assumed payload architecture; do not claim end-to-end performance. |

**PA interpretation.** Writing the supplied law as

\[
P_{\mathrm{PA,DC}}(p)=\frac{\sqrt{pP_{\mathrm{sat}}}}{\eta_{\mathrm{sat}}},
\qquad \eta(p)=\eta_{\mathrm{sat}}\sqrt{p/P_{\mathrm{sat}}}
\]

makes its meaning clear. This is the traditional-PA model used, for example, by Cui et al., §III-B, equations (1)–(4); their treatment distinguishes peak/saturation output from maximum average output. That is a modelling precedent, not satellite hardware calibration. [1]

Recomputed from [A], \(P_{\mathrm{sat}}=5.217758\) W and \(\eta_{\mathrm{sat}}=0.35\) imply **8.383 W PA DC and 19.68% RF/DC efficiency at the 1.65 W cap**. At the one-user boresight power, 0.317638 W, efficiency is about 8.64%. Thus 35% means saturation efficiency. If its original hardware source instead specified 35% at the allowed average output, adding another 5 dB penalty would be an error.

Real PA curves depend on device, bias, waveform, linearisation and architecture. A measured Ka-band GaN Doherty design reports about 20% power-added efficiency at 6 dB output back-off; that illustrates why the square-root shape is not universal. Power-added efficiency is also not automatically the complete amplifier's RF/DC efficiency. The cited device does not validate the supplied coefficients. [2]

For a single-carrier beam chain, the appropriate average is \(\sum_u\tau_uP_{\mathrm{PA,DC}}(p_u)\), not \(P_{\mathrm{PA,DC}}(\sum_u\tau_up_u)\). Because square root is concave, these differ. In a shared amplifier or array, apply the DC model to physical amplifier outputs, including the aggregate waveform. ESA engineers Angeletti and Lisi illustrate both per-beam HPAs and multiport architectures in which multiple HPAs contribute to each beam. Removing one software beam then need not switch off one amplifier. [3]

The **0.338 W/beam and 0.200 W/satellite coefficients are uncalibrated in this package**. Their magnitudes alone do not prove an error. Calling 0.200 W the entire satellite's baseband or platform consumption would, however, be unsupported. For a transparent payload, much baseband processing resides on the ground; for a regenerative payload, onboard processing must be represented. State exactly which block the common term represents.

The proposed idle fraction is also consequential: one twelfth of the cap PA supply is **0.699 W**, over twice the stated active-beam circuit term. Specify whether this is per installed PA, per idle chain, or a shared block, and distinguish steady standby from wake-up energy. Zero standby is defensible as ideal deep power-gating of the scoped block; it is not a credible statement that the entire unused satellite consumes zero.

**ACM and service need a correction in the specification.** EN 302 307-1 Table 13 is **DVB-S2**, not DVB-S2X. Its efficiencies and AWGN thresholds have stated frame/pilot and ideal-receiver assumptions. The supplied divisions by \(1+\alpha\), including the negative dB correction to \(E_s/N_0\), are consistent when \(W=R_s(1+\alpha)\). Do not divide again if bandwidth already denotes symbol-rate-equivalent bandwidth. S2X has a separate Part 2 and performance tables. [4,5]

The following three objects must be distinct:

- \(m_{\mathrm{target}}\): the MODCOD used to determine power for the controller's 50 Mbit/s setpoint.
- \(m_{\mathrm{tx}}\): the MODCOD selected before transmission, using the declared available channel information.
- Actual decoding and useful bits: assessed after realisation for \(m_{\mathrm{tx}}\).

In [A], four users at the beam edge target QPSK 3/4 but receive credited QPSK 1/2 bits. This is legitimate if an actual ACM controller first selected QPSK 1/2. A failed QPSK 3/4 frame cannot retrospectively decode as QPSK 1/2. Selecting the best mode from the very same realised SINR being evaluated is an ideal-ACM bound unless a sufficiently fast, causally specified controller is included. DVB-S2 implementation guidance explicitly treats feedback delay and shifted selection thresholds. [6]

For a hard decoding-cliff abstraction, credit bits using the actual transmitted mode and its success indicator. Maintain separate diagnostics for minimum-mode link availability, decoding success of the transmitted mode, and achieved average rate ≥50 Mbit/s. [P] explicitly chooses PHY decodability and denies a guaranteed-rate endpoint. That differs from reading “unserved” as “missed the rate target.”

Similarly, if the 1.7 dB allowance is included in both the assumed decoder threshold and the nominal power target, it supplies **no additional fading reserve**. For an uncapped, noise-limited link with realised power gain \(h=F\hat h\), targeting \(\Gamma\) gives \(\mathrm{SINR}=F\Gamma\). When that same \(\Gamma\) is the decoding threshold, success requires \(F\ge1\). A positive implementation allowance has not changed that condition. A robustness allowance must create separation between selection and decoding thresholds; ETSI's guidance makes that distinction. [6]

At fixed cap, continued transmission by an infeasible user is physically possible, especially before updated feedback arrives. It is a scheduler assumption, not a necessary property of capped power control. Prolonged knowingly useless transmissions should be justified against admission control, deferral or a feasible lower MODCOD. A converged capped fixed point can contain failed users: convergence is not a certificate that every SINR target was met. Also specify the empty target-mode case: with the highest Table-13 efficiency and the stated bandwidth, beam capacity is about 618.5 Mbit/s, so thirteen equal-airtime users cannot each receive 50 Mbit/s even at unlimited SINR under this mode catalogue. [A; calculation using 4]

**2. What energy boundary is defensible?**

There is no single denominator that can be inferred merely from the words “LEO energy efficiency.” A published LEO optimisation example, Khan et al., §II, equation (11), uses transmit power plus a circuit term. That establishes precedent for a communications-level ratio, not a complete spacecraft energy inventory. [7]

ETSI TR 103 352 illustrates the boundary dependence: §5.1 describes satellite payload/platform, gateways and terminals, while §7.4's simplified operational assessment uses gateway and terminal consumption. Sections 5.2–5.3 require exclusions to suit the assessment's purpose. Its GEO-oriented approximation is not a universal LEO accounting rule. [8]

For this paper, I would require the following scope-to-inventory mapping. These are engineering recommendations for making the claim interpretable, not a claimed normative minimum imposed by a single standard.

| Claimed metric | Required inventory at that scope |
|---|---|
| **The supplied partial-payload EE** | Modeled user-link PA DC, named beam-chain circuitry, named common processing increment, and all modeled idle/transition states. |
| **Complete communications-payload DC EE** | All onboard communications electronics: PA, drivers/RF conversion, beamforming, processing, feeder receiver/transmitter hardware, ISL terminals if used, standby, switching and relevant distribution losses. |
| **Space-segment/constellation operational EE** | Complete payload inventory plus the participating fleet's bus, ADCS, command/data handling, thermal-control electrical loads and other operational spacecraft loads over the same interval. Satellites remain in the inventory when traffic beams are off. |
| **End-to-end satellite-service EE** | Space segment plus allocated gateway, feeder-ground equipment, control/compute, terrestrial transport and terminal energy; declare the delivery endpoint and allocation of shared infrastructure. |

NASA's spacecraft-platform description identifies the bus services that remain necessary beyond the communications payload, including power/storage, thermal control, ADCS, navigation, communications and command/data handling. It does not calibrate their wattages for this constellation. [9]

Avoid double counting. PA supply power already contains the radiated RF energy and amplifier losses; do not add RF power or dissipated heat again. Thermal power means electrical heaters, pumps or controllers, where present. Specify the electrical measurement plane so power-conversion losses are charged once. Operational EE does not require manufacturing/launch energy unless a life-cycle claim is made. Solar energy being available does not make consumed electrical joules disappear from an onboard energy-resource metric.

Omitting feeder or ISL energy does not automatically permit omitting their effects on throughput. For a transparent repeater, feeder noise can contribute to end-to-end link quality; for regeneration, feeder capacity and delivery availability still constrain the traffic supplied to the downlink. Declare these nonbinding or model them. A constellation without ISLs legitimately has no ISL term.

I recommend the following boundary sentence:

“We report pooled successfully decoded forward-downlink information bits per joule of modeled partial-payload DC energy, comprising user-link PA supply, specified beam-chain circuitry and a common processing increment, with explicitly stated idle states; spacecraft bus, unmodeled payload functions, feeder/ISL and ground/terminal energy are outside this metric.”

Only call the numerator application goodput after explicitly accounting for offered data, applicable framing/protocol overhead and delivery success. Full-buffer traffic can also carry application data; the present equations do not establish that accounting.

One particularly consequential mathematical point: **common omitted energy does not generally cancel between policies**. For a common \(E_0\),

\[
\operatorname{sign}\!\left(\frac{B_1}{E_1+E_0}-\frac{B_2}{E_2+E_0}\right)
=\operatorname{sign}\!\left[B_1E_2-B_2E_1+E_0(B_1-B_2)\right].
\]

Thus even policy-independent bus energy can change a ranking when policies deliver different amounts of traffic. Equal delivered bits preserve energy ordering, although the relative EE gain changes. Reporting a partial-payload gain does not establish the same gain at constellation scope.

**3. Are the operating points plausible? What single check resolves the concern?**

**The median SINR is plausible in isolation; the service operating point is suspect pending independent link closure.** Low cap power alone is not proof of an implausible link: antenna gains, occupied bandwidth, range and interference determine received quality. Conversely, a median cannot validate the lower tail responsible for outages.

The following values were recomputed directly from [A], independently of the printed EE column:

| Quantity | Recomputed value |
|---|---:|
| Receiver system temperature | 242.294 K |
| Receiver G/T | 11.157 dB/K |
| Boresight EIRP at RF cap | 35.185 dBW |
| Noise in 166.667 MHz | −122.537 dBW |
| Cap C/N at 2,000 km, boresight | 5.714 dB |
| Cap C/N at the half-power edge | 2.703 dB |
| Four-user target-mode threshold | 4.938 dB |
| Four-user edge deficit against target | 2.235 dB |
| Four-user edge rate with QPSK 1/2 | 34.335 Mbit/s/user |

This is internally coherent: the deterministic example already fails the four-user 50 Mbit/s target at the edge, while permitting a lower-rate decodable mode. It is evidence of intentional or accidental over-demand relative to that link, not an arithmetic contradiction. Whether this is representative of the intended system still needs an external hardware and propagation anchor.

The diagnostics do not support a single combined outage interpretation. In [R], a-r0 FULL has availability 0.744 and cap share 0.146, whereas NULL has 0.587 and 0.403. In [S], LOW-SPARSE-WEAK a-r0 reports availability 0.418, UNSERVED share 0.40 and cap share 0.000. These supplied quantities cannot simply be treated as complements with one denominator. A b0 cap share of one is its fixed-power definition, not evidence that it cannot close the link. The superseded synthetic report is not a validation source for current performance.

**The single decisive check is an independently calculated link-closure ledger, covering both the cap-power envelope and the actual controlled powers, reconciled to the simulator's flags.** For actual occupancy and representative/edge geometry, compute EIRP, path and pointing losses, receiver G/T, occupied bandwidth, C/I and implementation losses. Compare the resulting SINR separately with the actual transmitted-mode threshold, the rate-target mode and the minimum-mode threshold. Include the specified weather percentile if claiming service availability, then explain the observed failures from those margins. The cap envelope tests physical target feasibility; actual controlled powers explain failures caused by threshold targeting without sufficient reserve.

This check separates a units/bandwidth/gain mistake from genuine overload, interference, geometry exclusion and lack of fade reserve. A site-independent elevation-loss expression cannot establish Ka-band annual rain availability; ITU-R P.618-14 is the applicable primary propagation-design reference. [10] Do not interpret ten development anchors or synthetic occupancy worlds as an annual service-availability measurement.

**4. Is a fixed per-user target the right load model?**

It is a valid **power-controller setpoint**, but it is not by itself a traffic model. Choosing the smallest qualifying mode does not limit useful demand to 50 Mbit/s, specify queues, or guarantee the realised rate.

The distinction is visible without new simulation. [A] credits 2,048.126 Mbit in the one-user boresight step, equivalent to 68.089 Mbit/s. A finite 50 Mbit/s arrival over 30.08 s would provide only **1,504 Mbit**, absent initial backlog. The table's fixed-RF comparator credits 6,630.952 Mbit. Those additional bits are legitimate under backlogged traffic, but cannot all be delivered offered traffic if every user has only 1,504 Mbit available. This choice directly affects policy comparisons.

| Load assumption | Meaning of the bits/J result | Additional reporting needed |
|---|---|---|
| Full buffer | Decodable saturated throughput per modeled joule | Fairness, coverage/outage and rate distributions; explicitly unlimited offered data. |
| Backlogged users with a fixed power-control rate setpoint | Throughput EE under that controller; realised rates may be above or below the setpoint | Actual rate attainment, not merely minimum-mode availability. This is the closest description of [A]. |
| Finite demand without persistent queues | Delivered requested data per joule within a stated delivery window | Clip delivery to available data; define what happens to unused airtime and undelivered demand. |
| Finite arrivals with queues | Operational traffic delivery per joule under delay/reliability constraints | Queue evolution, deadlines, drops, retransmissions and end-of-horizon backlog; account for energy throughout the observation window. |

Referees can accept each of these for the appropriate question. For association under saturated traffic, a full-buffer abstraction can isolate radio-resource mechanisms. For claims about saving energy by consolidating load or sleeping equipment at realistic utilisation, finite demand with explicit airtime and idle behavior is more informative. Queueing is needed when deferral, deadlines and temporal load variation are central; a finite-demand-per-window model can suffice for a narrower study. Traffic-aware payload switch-off is an established LEO research direction, as illustrated by Gupta et al. (2025); that precedent does not validate 50 Mbit/s as a measured typical demand. [11]

For the existing design, retain the frozen setpoint as a controlled operating assumption and describe the numerator honestly. If finite offered demand is introduced, declare it as a versioned model amendment and rerun affected comparisons; do not silently relabel existing results. Demand clipping alone is insufficient if the radio keeps radiating padded or unnecessary frames: specify whether excess scheduled airtime is released, reassigned or consumed.

**5. The three issues most likely to change pooled policy comparisons**

The ranking below is an engineering judgment about policy sensitivity, not a measured effect size. The supplied reports do not identify counterfactual effects of these corrections.

| Rank | Issue | Why policy ordering can change | Minimum resolution |
|---|---|---|---|
| **1** | **Unresolved transmitted-MODCOD/realised-bit consistency and missing separation of decode and selection thresholds** | Policies change occupancy and proximity to discrete thresholds. Retrospective mode selection or zero robustness reserve can disproportionately reward one policy's SINR distribution. | Specify causal ACM and its information/timing; evaluate the mode actually transmitted; distinguish PHY decode, rate attainment and outage denominators. |
| **2** | **Unvalidated physical activation and DC-power model** | Consolidation gains depend on real switchable chains, PA operating efficiency, standby and always-on processing. A software-beam count can overstate shutdown savings; shared satellite RF/DC/thermal limits can also exclude seemingly legal profiles. | Map beams to physical hardware; source/calibrate the PA curve and switchable/always-on terms; document satellite aggregate limits and transition costs. |
| **3** | **Unspecified offered traffic and credit for excess capacity** | Discrete modes and good channels produce traffic above the controller setpoint; different policies can receive unequal credit for bits that would not exist under finite demand. | Declare full buffer, or introduce finite demand/queues with consistent delivered-bit and airtime accounting; retain a QoS constraint that prevents sacrificing users for EE. |

Weather, feeder limitations and spacecraft overhead are also significant. They are not automatically more influential on a short-horizon policy ranking than the three issues above. If policy actions change feeder routing, satellite processing, or ISL usage, those terms become policy-dependent and must move into the corresponding energy/performance model. No current supplied result establishes that any omitted term leaves the ranking unchanged.

The publication path is therefore a bounded one: reconcile the service/MODCOD specification, establish one independent link closure, and either calibrate the switchable DC inventory or label it as an abstract partial-payload model. The supplied load–angle–power example supports a mechanism claim. It does not yet support commercial availability or whole-constellation efficiency claims.

**Primary references and exact evidentiary roles**

1. Cui, Q., Zhang, Y., Ni, W., Valkama, M., and Jäntti, R. (2018 manuscript). [Energy Efficiency Maximization of Full-Duplex Two-Way Relay with Non-ideal Power Amplifiers and Non-negligible Circuit Power](https://arxiv.org/html/1801.01709v1), §III-B, equations (1)–(4). Supports the traditional square-root PA abstraction and peak-versus-average distinction; does not calibrate a satellite PA.
2. Piacibello, A., et al. (2022). [A 5-W GaN Doherty Amplifier for Ka-Band Satellite Downlink With 4-GHz Bandwidth and 17-dB NPR](https://doi.org/10.1109/LMWC.2022.3160227). Measured back-off behavior demonstrates architecture dependence. Related measured hardware: Piacibello et al. (2024), [High-gain and high-linearity MMIC GaN Doherty Power Amplifier with 3-GHz bandwidth for Ka-band satellite communications](https://orca.cardiff.ac.uk/id/eprint/167888/). Neither validates the supplied 0.35 or 5 dB.
3. Angeletti, P., and Lisi, M., European Space Agency (2010). [Multiport Power Amplifiers for Flexible Satellite Antennas and Payloads](https://www.microwavejournal.com/articles/9430-multiport-power-amplifiers-for-flexible-satellite-antennas-and-payloads), Figures 1–2 and “MPA Satellite Transponders.” Supports the distinction between beam-assigned HPAs and shared amplifier pools.
4. ETSI (2014). [EN 302 307-1 V1.4.1](https://www.etsi.org/deliver/etsi_en/302300_302399/30230701/01.04.01_60/en_30230701v010401p.pdf), §6, Table 13; Annex D.5. Source of the supplied DVB-S2 mode performance assumptions and ACM feedback framework.
5. ETSI (2024). [EN 302 307-2 V1.4.1](https://www.etsi.org/deliver/etsi_en/302300_302399/30230702/01.04.01_60/en_30230702v010401p.pdf), §6, including Table 20a. Distinguishes DVB-S2X from the Part-1 table used here; no assertion that changing to S2X is required for publication.
6. ETSI (2015). [TR 102 376-1 V1.2.1](https://www.etsi.org/deliver/etsi_tr/102300_102399/10237601/01.02.01_60/tr_10237601v010201p.pdf), §4.4.1 and Annex E.2. Supports feedback-delay treatment, shifted selection thresholds and hysteresis; does not establish a universal 1.7 dB margin.
7. Khan, W. U., Lagunas, E., Mahmood, A., Chatzinotas, S., and Ottersten, B. [RIS-Assisted Energy-Efficient LEO Satellite Communications with NOMA](https://arxiv.org/pdf/2306.10422), author manuscript, §II, equation (11); published in IEEE Transactions on Green Communications and Networking 8(2), 2024. Documents transmit-plus-circuit EE convention; not authority for a complete spacecraft inventory.
8. ETSI (2016). [TR 103 352 V1.1.1 — Energy efficiency of satellite broadband network](https://www.etsi.org/deliver/etsi_tr/103300_103399/103352/01.01.01_60/tr_103352v010101p.pdf), §§5.1–5.3, 6, 7.4. Supports explicit boundaries, useful-output/energy metrics and qualified exclusions. Its simplified gateway/terminal assessment must not be misrepresented as a universal LEO requirement.
9. NASA. [State-of-the-Art Small Spacecraft Technology: Complete Spacecraft Platforms](https://www.nasa.gov/smallsat-institute/sst-soa/platforms/), introductory bus-services description. Identifies spacecraft functions beyond payload electronics; supplies no project-specific power budget.
10. ITU-R (2023). [Recommendation P.618-14 — Propagation data and prediction methods required for the design of Earth-space telecommunication systems](https://www.itu.int/rec/R-REC-P.618-14-202308-I/en). Primary reference for Earth-space propagation/availability design, not support for the supplied fixed elevation loss as an annual rain model.
11. Gupta, V. K., Al-Hraishawi, H., Lagunas, E., and Chatzinotas, S. (2025). [Energy efficient LEO satellite communications: Traffic-aware payload switch-off techniques](https://orbilu.uni.lu/handle/10993/64490), Computer Communications 236, 108122, DOI 10.1016/j.comcom.2025.108122. Publisher/repository abstract supports traffic-aware payload operation as a research precedent; no detailed hardware coefficient is adopted from it.

VERDICT: MODEL_DEFENSIBLE=conditional | BOUNDARY=Successfully decoded forward-downlink information bits per modeled partial-payload DC joule, with spacecraft bus, unmodeled payload, feeder/ISL and ground/terminal energy excluded. | OPERATING_POINT=suspect+check | TOP_MISSING=causal ACM and service consistency; physical activation and PA/DC calibration; offered-traffic and useful-bit accounting
