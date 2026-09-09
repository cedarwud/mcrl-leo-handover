# Per-beam transmit power in real multibeam satellite payloads

## Conclusion

**There is no architecture-independent positive per-beam power reserve.** A suitable payload can change RF output much faster than tens of seconds, but increasing one beam without reducing another requires both usable local amplifier headroom and slack in every relevant shared constraint. Adjustable output does not imply available additional power; a shared power budget does not imply that the budget is always fully used. Flight experiments with the Ka-band WINDS payload explicitly allocated additional downlink power from the available surplus of a multiport amplifier. [1–3]

Consequently, **fixed per-beam power plus adaptive coding and modulation (ACM) is a defensible operating abstraction, not a universal hardware law**. Conversely, an unrestricted satellite-wide pool from which every beam can draw is generally too permissive. The realistic middle ground is architecture-dependent, constrained flexibility. [2,4]

For current LEO broadband, the most representative architecture is an electronically steered array payload with solid-state RF front ends, rather than a classical GEO-style dedicated high-power tube behind every fixed terrestrial beam. The strongest public evidence concerns the array architecture; exact amplifier-to-beam mappings, independent boost ranges, and commercial control policies are usually not disclosed. Starlink's documented spacecraft architecture uses multiple Ku-band arrays and Ka/E-band antennas. Its established Ku user links must not be confused with its Ka-band gateway links when choosing a Ka user-downlink model. [5–7]

**The particular minimum-mode problem has two different interpretations:** loss of service after a sufficiently deep fade is an established operating regime; systematic rejection in nominal conditions because a controller first provisions zero margin and then demands positive margin is a feasibility or provisioning problem. The latter is not an inevitable consequence of satellite hardware. [8; analysis in Section 7]

## 1. What actually controls amplifier output?

### Travelling-wave tube amplifiers

A TWTA's output is determined by its RF input drive and nonlinear input–output characteristic, with its electronic power conditioner and tube operating settings determining the available amplification and saturation output. Operational control may act through a channel amplifier or attenuator, a commanded gain setting, an automatic-level-control target, or—in a flexible power module—selected tube/power-conditioner settings. A tube need not be operated at its saturation output merely because that output is its rating. [1,4]

Thus, neither “a TWTA is fixed at commissioning” nor “every beam has continuously independent power control” is generally correct. Gain or output targets can be telecommanded in orbit. Which settings can change, their quantization, and whether one command changes a single carrier or a group of beams are payload-specific. In a transparent transponder, changing uplink drive can also change downlink output over part of the transfer characteristic; it cannot produce output beyond the downlink amplifier's limit. [1,4]

**Output back-off needed for linearity is not automatically spare fade margin.** Moving a multicarrier amplifier closer to saturation can increase distortion and interference. The relevant ceiling is the output allowed for the actual waveform and quality requirements, not simply the catalogue saturated wattage. [4,8]

TESAT's 2019 ESA workshop presentation provides a concrete hardware example: a qualified 300 W **Ku-band** flexible power module with output configurable down to −3 dB by CAN telecommand. The presentation also identifies a 250 W Ka-band module, but the explicitly stated qualified 3 dB example is Ku-band. This establishes in-orbit adjustability, not a universal 3 dB reserve or a published end-to-end response time. [1]

### Solid-state power amplifiers

An SSPA similarly has controllable RF drive/gain and, in some designs, adjustable drain/bias settings. A 2023 Ka-band SSPA study by Giofrè and colleagues implements fixed-gain and automatic-level-control operation with commanded attenuation and bias flexibility. It reports measurements at approximately 25–100 W output, but this was a **TRL-5 development**, not evidence that a named commercial constellation uses that operating range. Its tested attenuation range must not be interpreted as an equal amount of upward power headroom. [9]

In an active phased array, “beam power” is additionally a beamforming quantity. Several logical beams can share element or subarray amplifiers. Changing beam amplitudes changes the RF loading of those amplifiers, so individually feasible beam powers may not be jointly feasible. A model with only one satellite-wide sum-power limit can miss per-element, per-panel, or per-RF-chain limits. [6,10]

### Realistic adjustment ranges and timescales

| Quantity | Evidence-supported interpretation |
|---|---|
| Additional usable output at an already binding amplifier or EIRP limit | **0 dB**, irrespective of how fast the control electronics are. |
| Output adjustment from an intentionally reduced operating point | Several dB can be available in particular designs; the qualified TESAT example spans 3 dB. This is product-specific. [1] |
| Large attenuation/control range | Demonstrates the ability to turn output down or accommodate input variation, not equivalent upward reserve. [9] |
| Array gain/phase updates | Analog Devices describes component updates on the order of microseconds. This is a component capability, not a commercial rain-control-loop guarantee. [6] |
| Beam hopping | The JoeySat launch announcement specified up to 1,000 location changes per second. This is an advertised hopping capability, not a measurement of closed-loop fade compensation latency. [11] |
| Ground-commanded or automated power allocation | The cited flight/component documents establish adjustability but do not disclose a universal command-to-settled-output latency. Feedback, authorization, scheduling, and bus control must be specified. [1–3] |

**Engineering inference:** tens of seconds is normally ample for suitable electronic actuation, but it is not proof that the deployed controller exposes that actuation every tens of seconds. Nor is tens of seconds necessarily fast enough to track every rain event. Component speed, supervisory reconfiguration time, and end-to-end channel-feedback time are different quantities. NICT's WINDS report derives a need for roughly 1 dB of compensation within about 2 seconds for the severe attenuation-change case it discusses; this is a response requirement, not a measured universal actuator latency. [3]

## 2. Is RF power a shared pool?

### Classical dedicated-amplifier payloads

When an amplifier feeds a dedicated beam, that beam cannot borrow another amplifier's unused RF capability through software alone. It can increase output within its own allowed operating envelope, subject to spacecraft electrical and thermal limits. Another beam's RF power need not decrease while those constraints retain slack. Conversely, surplus spacecraft electrical power does not overcome a saturated local RF amplifier. [2]

“Classical transponder” does not always mean one amplifier per beam. A single TWTA can carry several carriers or feed a defined subset of beams. Cocco and colleagues explicitly model these amplifier–beam groups and the corresponding coupled power changes. Independence must therefore be established from the RF routing, not inferred from the number of ground coverage cells. [4]

### Multiport amplifiers

An MPA combines a bank of amplifiers with input and output networks so that amplifier capacity can contribute to multiple output ports. This enables flexible redistribution **within the MPA group**, subject to total output, individual hardware limits, losses, calibration, and linearity. It does not create an unlimited spacecraft-wide RF pool. [2]

The Ka-band **WINDS** mission provides direct flight evidence, not just an optimization proposal. NICT's 2017 experiment report describes eight downlink ports, a total output limit of 280 W, and power redistribution using terminal reception-quality reports and available surplus. Its illustrative link-budget table assigns 210 W to one rainy location and 10 W to each of seven clear locations, totaling 280 W. That table demonstrates the intended allocation envelope; it is not a claim that this exact vector was a measured time-series event. [3]

The answer to “does raising one necessarily lower another?” is therefore **no when there is available surplus, yes when the relevant total-power limit is already binding**, unless some other resource or operating condition is changed.

### Active arrays and beam hopping

An array shares RF hardware through its beamforming network, but its feasible region can be more restrictive than a scalar sum-power bound. Beam hopping shares a limited set of simultaneously active beams or RF chains across a larger number of ground cells over time. These are different forms of sharing; neither should be reduced automatically to one independent amplifier per ground cell. [6,10,12]

An architecture-aware simplified model can impose

\[
0\le p_b\le \bar p_b,\qquad
\sum_{b\in G_g}p_b\le P_g,
\]

alongside

\[
\sum_j P_{\mathrm{DC},j}(\text{RF loading}_j,\text{bias}_j)
+P_{\mathrm{other}}\le P_{\mathrm{bus,available}}.
\]

Here the groups must correspond to real amplifier banks, panels, or RF chains. These equations are an analytical abstraction, not a universal payload specification. Electrical consumption is not identical to radiated RF power; efficiency and operating settings matter. Reducing RF output does not establish an equal reduction in spacecraft DC demand. [9; model synthesis]

## 3. What does a flexible or software-defined payload really change?

The terms describe multiple capabilities, not one standard hardware contract.

| Layer | Possible reconfiguration | What must not be inferred |
|---|---|---|
| Channelization and routing | Frequency slots, bandwidth, input-to-output connectivity | Every output has independently adjustable RF power. |
| Beamforming | Pointing, shape, amplitude weights, active beam selection | Arbitrary beam gains or arbitrary independent amplitudes. |
| Amplification | Gain, output target, operating profile, allocation within an MPA | Unlimited extra output or proportional DC savings. |
| Time scheduling | Illumination pattern, dwell time, burst allocation | More dwell necessarily improves burst SINR. |
| Regenerative processing | Onboard demodulation, switching, remodulation | Every software-defined payload is regenerative. |

These distinctions are supported by hardware-aware flexible-payload models, satellite front-end documentation, and DVB-S2X beam-hopping implementation guidance. A digital transparent processor can provide flexible channelization without onboard user-data decoding; software cannot remove output-stage constraints. [4,6,12]

**Flown commercial capability:** SES-17, a Ka-band satellite commercially operational since June 2022, has roughly 200 beams and an operator-described ability to vary power and frequency allocations through its flexible payload and Adaptive Resource Control system. This establishes commercial flexibility. The public material does not establish a universal dB boost, independent control for every beam under every loading condition, or a measured sub-second reconfiguration guarantee. [13,14]

**Flown demonstrator:** JoeySat launched in 2023 with digital beam steering and beam hopping; ESA reported in-orbit tests in 2023 and further demonstrations in 2025. This is stronger than a simulation, but it does not establish that the same feature set was present across the first-generation OneWeb fleet. [15,16]

**Component-level research:** the 2023 Ka-band SSPA measurements establish a technically credible flexibility mechanism and its efficiency/linearity trade-offs. They do not establish flight deployment. [9]

**Algorithmic research:** papers optimizing jointly over beam activation and continuous power demonstrate performance inside an assumed feasible set. Their simulations do not prove that a particular operator's payload exposes those variables. [17]

### Which architecture is most common in current LEO broadband?

The strongest public-evidence answer is **electronically steered array payloads, generally implemented with distributed solid-state RF front ends**, with Starlink providing the dominant deployed example. The conclusion is stronger about array architecture than about the exact unpublished amplifier inventory. Starlink's documented spacecraft design includes five Ku-band arrays and three Ka/E-band antennas; this should not be extrapolated into a claim that every generation or constellation has identical hardware. [5,6]

There is also a crucial band distinction: the familiar Starlink user downlink is Ku-band, whereas Ka-band has been used for gateway downlinks. A Ka user-link constellation should be evaluated on its own payload, rather than borrowing a generic “LEO/Starlink” amplifier model. [7]

SpaceX's original technical filing already described varying both Ku- and Ka-band transmit power as beams steer, to maintain the specified ground power-flux density. That is direct documentary evidence against physical immutability of beam power. It is a historical design filing, not disclosure of present-day fade-control headroom. [18]

**Unresolved in public evidence:** a defensible fleet-wide numerical split between detailed amplifier topologies, and a current operator-specific independent-boost range over 10–60 seconds. Those cannot be established merely from the labels “LEO,” “Ka-band,” or “software-defined.”

## 4. Beam hopping: instantaneous power is not average power

A common beam-hopping abstraction gives an illuminated beam a fixed on-burst power and varies its duty factor. For beam \(b\), neglecting overhead,

\[
\overline P_b=d_bP_{b,\mathrm{on}},\qquad
\overline R_b\approx d_b B_b\eta\!\left(\gamma_{b,\mathrm{on}}\right).
\]

These are time-averaging identities. The decoding decision uses **on-burst SINR**, not RF power averaged over intervals when the beam is off.

Thus, “increase a beam's power” may mean raising burst amplitude, increasing the fraction of time illuminated, or reallocating array/chain resources. Those operations are not equivalent. Increasing duty factor alone delivers more bits or energy over a frame but does not raise the received symbol SINR of an otherwise unchanged burst. More time can compensate for the throughput reduction caused by a more robust code; it cannot make an undecodable unchanged waveform decodable. [12; analytical interpretation]

Fixed on-burst power is **common but not definitional**. A 2023 China Communications LEO beam-hopping paper divides total power uniformly across the active hopping beams. A 2024 IEEE Transactions on Wireless Communications paper instead jointly optimizes beam scheduling and power. Both are legitimate research formulations of different control assumptions. [17,19]

For fixed-power beam hopping, the appropriate fade model is to calculate burst SINR, select a supported robust MODCOD, and then allocate sufficient dwell time if capacity permits. If the lowest supported mode still cannot decode, more dwell alone is insufficient. Lower symbol rate, repetition, interference reduction, or a different route can help only when those additional mechanisms actually exist in the model and hardware. [8,12,20]

## 5. The academic modelling convention is a split, not a single standard

A percentage split would require a defined corpus and systematic coding. The evidence supports the following **qualitative division**, with representative papers rather than claimed publication shares.

| Literature family | Typical abstraction | Representative venue and year |
|---|---|---|
| Link engineering and ACM implementation | Prescribed EIRP/power operating point; adapt MODCOD to channel quality | ETSI DVB-S2 implementation guidance, 2015; DVB-S2X guidance, 2021. [8,12] |
| Queue-aware networking | Power and scheduling/routing decisions under varying channel conditions | Neely, Modiano and Rohrs, IEEE/ACM Transactions on Networking, 2003. [21] |
| Flexible multibeam capacity allocation | Adjustable time, frequency and/or beam power | Lei and Vázquez-Castro, Journal of Communications and Networks, 2011; Aravanis et al., IEEE Transactions on Wireless Communications, 2015. [22,23] |
| Hardware-aware payload optimization | Amplifier groups, quantized power profiles/back-off, bandwidth, actual MODCOD mapping | Cocco et al., IEEE Transactions on Broadcasting, 2018. [4] |
| Energy-efficient allocation | Variable beam powers, radiated-power cost, service-demand trade-offs | Efrem and Panagopoulos, IEEE Wireless Communications Letters, 2020. [24] |
| Beam-hopping/placement scheduling | Often fixed or equal on-burst power; optimize activation and dwell | Lyu et al., China Communications, 2023. [19] |
| Joint beam hopping and power | Both illumination and power are variables | Chen et al., IEEE Transactions on Wireless Communications, 2024. [17] |

The trend is not “old papers fixed power; new papers variable power.” Both assumptions coexist, and power adaptation appears in networking research at least as early as 2003. Signal-processing work adds another important distinction: per-antenna constraints can matter even where a resource-allocation paper assumes only total power. [10,21]

“Shared-pool power allocation” and “joint power/rate optimization” are not mutually exclusive categories. Rate can be a derived function of SINR, an explicit discrete MODCOD choice, or a constrained demand served by scheduling. **For the minimum-mode question, whether the rate model has a finite decoding floor matters at least as much as whether power is optimized.** A smooth Shannon-rate model does not reproduce a finite implemented MODCOD floor without an additional constraint. [4,19; model comparison]

## 6. Fixed-power fade margin and the meaning of an unserved user

### Fixed power can contain substantial fade margin

Fade reserve does not require increasing power after rain begins. A design can provide enough fixed EIRP and receiver performance for a robust baseline mode under a chosen attenuation percentile. In clear weather, ACM exploits the additional received quality with a higher-rate mode; during rain it relinquishes that rate. ITU-R S.1061 covers multiple fade-mitigation strategies, and ITU-R P.618 supplies Earth–space propagation prediction methods for availability-dependent planning. [20,25]

A useful design inequality is

\[
\Gamma_{\mathrm{clear}}(P_{\mathrm{fixed}})
\ge \theta_{\mathrm{minimum\ service}}
+A_{\mathrm{design}}+M_{\mathrm{implementation}},
\]

with quantities in compatible dB units. This is a simplified link-budget statement; interference and changing receiver noise may require a fuller calculation.

As a concrete example rather than a generic Ka-band number, a DVB-S2X guideline link budget separately includes **5.1 dB of rain attenuation for its 99.9% availability case** and at least **1 dB of remaining link margin**. It does not first size the lowest service mode exactly at clear-sky threshold and only afterward attempt to create rain reserve. [26]

Do not merge three different reserves: long-term fade/availability allowance, short-term ACM safety allowance for imperfect or delayed estimates, and traffic capacity reserved for users operating at lower rates. A mode downgrade can preserve decoding while failing the user's throughput target. The latter requires extra time/bandwidth or an explicit service degradation. [8,12,20]

### When the robust mode no longer closes

**Service loss below the supported decoding range is established behavior.** The DVB-S2 implementation guideline contains a laboratory fade experiment that steps down to QPSK 1/4, subsequently loses lock in a deeper fade, and recovers afterward. It explicitly places this region outside the illustrated 99.9% availability domain. This is strong evidence for the recognized outage regime, not a claim about Starlink's proprietary waveform. [8]

A scheduler may stop allocating futile data bursts, buffer traffic, drop packets under queue/deadline constraints, or attempt reacquisition or rerouting. The exact policy is implementation-dependent; the physical fact is that no supported mode closes the current link. Such outage is compatible with a specified availability target, but excessive outage relative to the promised service is a design or operational failure. [8,21; engineering interpretation]

The minimum mode is implementation-specific. DVB-S2X includes very-low-SNR modes beyond the original DVB-S2 set; a model should not treat the oldest DVB-S2 minimum as a universal hardware limit. [12]

Other remedies can include supported rate reduction, repetition, diversity, changes in antenna gain, and interference avoidance. But the causal path matters: gateway diversity mitigates a feeder-link problem, not automatically the rain attenuation on an unchanged user downlink. Increasing uplink power does not overcome a saturated downlink stage. [20; engineering interpretation]

## 7. The exact nominal-threshold-then-margin rule

Let \(\Gamma_0\) be nominal received SINR in dB, \(\theta_m\) the decoding threshold of mode \(m\), and \(F>0\) the additional required margin. Suppose the power-setting rule produces

\[
\Gamma_0=\theta_{m_0}.
\]

The subsequent eligibility test is

\[
\Gamma_0\ge\theta_m+F.
\]

The originally selected mode fails by construction. A lower-threshold mode works only if its threshold reduction is at least \(F\). If \(m_0\) is already the minimum supported mode, the feasible set is empty. **This conclusion follows from the two rules; it does not establish an amplifier limitation.**

Three cases must be kept separate:

| Case | What has happened | Appropriate interpretation |
|---|---|---|
| Actual faded SINR is below every supported decoding threshold | No supported waveform can currently close the link | **Physical outage / link unavailability.** Recognized operation outside the designed availability envelope. [8] |
| Actual SINR clears the minimum threshold but not the extra safety requirement | The link could decode now, but does not satisfy the selected reliability policy | **Reliability/admission blocking.** A defensible policy, but not evidence of current physical non-decodability. This classification is an analytical distinction. |
| Nominal power is repeatedly set exactly at the minimum threshold, followed by a positive mandatory margin | The controller makes its own nominal feasible set empty | **Zero-margin provisioning or incompatible design constraints.** It can describe an intentionally best-effort or under-provisioned system, but it is not unavoidable payload behavior. This is an analytical diagnosis. |

No special standardized name for this precise two-stage rule was established in the reviewed sources. “Insufficient fade margin,” “link-budget infeasibility,” and “outage below the minimum supported MODCOD” describe its different aspects; “minimum-MODCOD floor” is a useful description, not a unique named syndrome.

The claim that a more robust mode is the **only** alternative is correct only when power, bandwidth/symbol rate, antenna gain, interference, repetition, and available paths are all fixed. Under that restricted model, a minimum-mode user indeed has no physical-layer fallback. Broadening the available controls changes the feasible set, but must be justified by the actual architecture rather than added solely to avoid an inconvenient result. [12,20; analysis]

**Adjudication:** leaving users unserved during sufficiently deep fades is neither exotic nor intrinsically a modelling artifact. Leaving minimum-mode users unserved even at the nominal reference condition can also represent a real, weakly provisioned system—but it cannot simultaneously be presented as a design that meets a positive fade-margin requirement for those users at that condition.

## 8. Consequence for the model

A fixed-power model is supportable when it represents a fixed on-burst operating point, a local amplifier already at its allowable ceiling, or a controller without permission or resources to vary power over the decision horizon. A variable-power model is supportable when the payload exposes that control and includes local/group limits, DC consumption, and relevant operating constraints. An unconstrained independent boost is not supported merely because the payload is flexible. [1–4,9,12]

For the outage rule, record separately whether a user is physically undecodable, excluded by a reliability policy, or decodable but unable to meet its throughput target. Incorporate the intended service availability into the original link budget—or explicitly accept the resulting outages—rather than declaring a post hoc positive margin requirement automatically compatible with a zero-margin nominal power setting.

**Established practice:** adjustable amplifier settings; topology-dependent power sharing; fixed-power ACM; finite decoding-range outages. **Research or product-specific capability:** particular bias-flexibility schemes, joint hopping/power optimizers, and precise reconfiguration ranges. **Not established publicly:** a universal current-LEO per-beam boost allowance or control latency. **Analytical conclusion:** exact nominal-threshold operation at the lowest mode and a strictly positive mandatory margin are incompatible unless some other resource changes.

## Sources

Public-source assessment checked on 9 September 2026. Historical hardware and experiment dates are retained deliberately; no undisclosed operator control policy is assumed.

1. Freese, J., et al. TESAT. *Equipment with CAN-TM/TC Interface for Flexible Payloads on Modern Telecom Satellites*. ESA CAN in Space workshop, 12 June 2019. Especially pp. 4–8 and 16–17. [Manufacturer presentation](https://indico.esa.int/event/276/contributions/4532/attachments/3474/4571/Tesat_Equipment_with_CAN_2019-06_Upload_Issue_A.pdf).
2. Angeletti, P., and Lisi, M. *Multiport Power Amplifiers for Flexible Satellite Antennas and Payloads*. Microwave Journal, 1 May 2010. Original technical article by ESA engineers. [Article](https://www.microwavejournal.com/articles/9430-multiport-power-amplifiers-for-flexible-satellite-antennas-and-payloads).
3. Asai, T., Takahashi, T., and Katayama, N. *Experiment Report for Rain Attenuation Compensation*. Journal of NICT 64(2), 2017, pp. 77–86. Especially downlink section and Table 2, printed pp. 81–82. [Flight experiment report](https://www.nict.go.jp/publication/shuppan/kihou-journal/journal-vol64no2/J2017W-03-02.pdf).
4. Cocco, G., de Cola, T., Angelone, M., Katona, Z., and Erl, S. *Radio Resource Management Optimization of Flexible Satellite Payloads for DVB-S2 Systems*. IEEE Transactions on Broadcasting 64(2), 266–280, 2018; online 2017. DOI: 10.1109/TBC.2017.2755263. [Original article, author-uploaded full text](https://www.researchgate.net/publication/319907303_Radio_Resource_Management_Optimization_of_Flexible_Satellite_Payloads_for_DVB-S2_Systems).
5. SpaceX/Starlink. *Progress 2024 Report*. Spacecraft array/antenna description. [Operator report](https://www.starlink.com/public-files/starlinkProgressReport_2024.pdf). The antenna description was available in indexed operator text; the complete large PDF was not available for full-text inspection in this review.
6. Ryan, J. Analog Devices. *How to Select Antenna Front-End Components for Non-GEO Space Applications*. 16 January 2023. [Manufacturer technical article](https://www.analog.com/en/resources/analog-dialogue/articles/how-to-select-antenna-front-end-components-for-non-geo-space-applications.html).
7. mmTron. *MMIC Power Amplifier for LEO Satellite Downlinks*. Microwave Journal, 13 February 2024. [Manufacturer technical article](https://www.microwavejournal.com/articles/41454-mmic-power-amplifier-for-leo-satellite-downlinks). Band allocation and component example, not proof of installation on a particular operator's spacecraft.
8. ETSI. *TR 102 376-1 V1.2.1: DVB-S2 Implementation Guidelines*, November 2015. Particularly Annex E, printed pp. 103–104. [Standard implementation report](https://www.etsi.org/deliver/etsi_tr/102300_102399/10237601/01.02.01_60/tr_10237601v010201p.pdf).
9. Giofrè, R., et al. *An Efficient and Linear SSPA With Embedded Power Flexibility for Ka-Band Downlink SatCom Applications*. IEEE Transactions on Microwave Theory and Techniques, 2023. [Original paper, university repository](https://art.torvergata.it/bitstream/2108/341923/1/An_Efficient_and_Linear_SSPA_With_Embedded_Power_Flexibility_for_Ka_-Band_Downlink_SatCom_Applications.pdf).
10. Spano, D., et al. *Per-antenna Power Minimization in Symbol-level Precoding for the Multibeam Satellite Downlink*. International Journal of Satellite Communications and Networking, 2018. [University publication record](https://orbilu.uni.lu/handle/10993/35363).
11. UK Space Agency. *Beam-hopping OneWeb satellite soars into space*. 20 May 2023. [Mission announcement](https://www.gov.uk/government/news/beam-hopping-oneweb-satellite-soars-into-space).
12. ETSI. *TR 102 376-2 V1.2.1: DVB-S2X Implementation Guidelines*, January 2021. Very-low-SNR modes and Annex C beam-hopping guidance. [Standard implementation report](https://www.etsi.org/deliver/etsi_tr/102300_102399/10237602/01.02.01_60/tr_10237602v010201p.pdf).
13. SES. *SES-17: Experience Endless Connectivity*. 7 February 2022. [Operator technical overview](https://www.ses.com/newsroom/ses-17-experience-endless-connectivity).
14. SES. *Fully Operational SES-17 Starts Delivering Connectivity Services Across Americas*. 16 June 2022. [Operational announcement](https://www.ses.com/press-release/fully-operational-ses-17-starts-delivering-connectivity-services-across-americas).
15. ESA. *Beam-hopping JoeySat passes in-orbit tests*. 30 July 2023. [Mission test report](https://www.esa.int/Applications/Connectivity_and_Secure_Communications/Beam-hopping_JoeySat_passes_in-orbit_tests).
16. ESA. *Beam-hopping JoeySat marks two years in orbit*. 21 May 2025. [Mission progress report](https://www.esa.int/Applications/Connectivity_and_Secure_Communications/Beam-hopping_JoeySat_marks_two_years_in_orbit).
17. Chen, L., et al. *Joint Power Allocation and Beam Scheduling in Beam-Hopping Satellites: A Two-Stage Framework With a Probabilistic Perspective*. IEEE Transactions on Wireless Communications 23(10), 14685–14701, 2024. DOI: 10.1109/TWC.2024.3417707. [University publication record and abstract](https://scholar.xjtu.edu.cn/en/publications/joint-power-allocation-and-beam-scheduling-in-beam-hopping-satell/).
18. SpaceX. Original NGSO technical attachment, filed 2016; copy included with its 2018 New Zealand spectrum consultation submission. Sections on Ku- and Ka-band beam steering/power-flux density. [Government-hosted filing](https://www.rsm.govt.nz/assets/Uploads/documents/consultations/2018-preparing-for-5g/c4c9f26604/300.3-spacex-submission-preparing-for-5g.pdf).
19. Lyu, L., et al. *Beam Position and Beam Hopping Design for LEO Satellite Communications*. China Communications, July 2023. System model, printed p. 32. [Original paper, university repository](https://signal.seu.edu.cn/_upload/tpl/0a/67/2663/template2663/JournalFiles/ChinaCom2023LeyiLv.pdf).
20. ITU-R. *Recommendation S.1061-1: Utilization of fade mitigation strategies and techniques in the fixed-satellite service*, January 2007. [Recommendation](https://www.itu.int/dms_pubrec/itu-r/rec/s/R-REC-S.1061-1-200701-I!!PDF-E.pdf).
21. Neely, M. J., Modiano, E., and Rohrs, C. E. *Power Allocation and Routing in Multibeam Satellites with Time-Varying Channels*. IEEE/ACM Transactions on Networking 11(1), 138–152, 2003. DOI: 10.1109/TNET.2002.808401. [Publisher record](https://dl.acm.org/doi/abs/10.1109/TNET.2002.808401).
22. Lei, L., and Vázquez-Castro, M. A. *Multibeam Satellite Frequency/Time Duality Study and Capacity Optimization*. Journal of Communications and Networks 13(5), 472–480, 2011. [Original preprint](https://arxiv.org/pdf/1103.3866).
23. Aravanis, A. I., et al. *Power Allocation in Multibeam Satellite Systems: A Two-Stage Multi-Objective Optimization*. IEEE Transactions on Wireless Communications 14(6), 3171–3182, 2015. DOI: 10.1109/TWC.2015.2402682. [University record](https://orbilu.uni.lu/handle/10993/20797). Record-level evidence used; no detailed claim about its inaccessible full text.
24. Efrem, C. N., and Panagopoulos, A. D. *Dynamic Energy-Efficient Power Allocation in Multibeam Satellite Systems*. IEEE Wireless Communications Letters 9(2), 228–231, 2020. [Original preprint](https://arxiv.org/abs/1912.00920).
25. ITU-R. *Recommendation P.618-14: Propagation data and prediction methods required for the design of Earth-space telecommunication systems*, August 2023, listed in force when checked. [Recommendation record](https://www.itu.int/rec/R-REC-P.618-14-202308-I/en).
26. ETSI. *TR 102 376-2 V1.1.1: DVB-S2X Implementation Guidelines*, March 2015. Table 27, printed p. 90. Historical illustrative link-budget example; not the latest version of the guideline. [Report](https://www.etsi.org/deliver/etsi_tr/102300_102399/10237602/01.01.01_60/tr_10237602v010101p.pdf).
