
LEO handover regime B: literature anchors and realism review
Pre-freeze research report | 8 September 2026
Audience: Multi-Catfish investigators and scientific reviewers. Scope: traffic, payload power, deployable coordination and evaluation methodology. Evidence cutoff: 8 September 2026; principally 2019–2026 primary sources.
1. Executive assessment
A constructed regime is scientifically legitimate, but this package is not ready to claim a realistic commercial LEO workload or payload model. The most defensible minimal study is a declared finite-demand, reserved-service abstraction. Its claims must remain conditional on that abstraction and on any development-stage regime selection.
For a residential-terminal interpretation, my preferred four-point set is {full buffer, 5, 10, 50 Mbit/s}. The 5 Mbit/s point supplies an externally motivated household-load anchor; 10 represents sustained active use; 50 represents heavy active use. Retain 200 only if the study is explicitly about very high active-terminal or aggregated enterprise demand. These are scenario choices, not measured LEO percentiles, and this recommendation uses no C3 outcome. Broadband measurements distinguish a few Mbit/s of subscriber-average busy-hour load from much higher achievable transfer speeds. Preseem, subscriber usage (2024); ACCC, Starlink measurements (2025).
The PA numbers describe a plausible small-amplifier scale and a transparent class-B-style approximation. They do not identify a Starlink/OneWeb/Kuiper beam. The circuit and baseband numbers have a traceable simulation source, but its component boundaries differ from the package’s labels. A larger fixed cost cannot be justified merely by calling it realistic DBF power. You et al., hybrid precoding (2022); Piacibello et al., 5-W Doherty PA (2022).
Set-level control is a credible deployment architecture. Whether learned prediction adds value over a physically informed coordinator remains an empirical question: recent LEO work finds an interference-aware greedy scheduler close to exhaustive optimization. Its large power savings exploit beam duty cycling, which this package excludes. Fastenbauer et al. (2025).
The most consequential pre-registration issue is file 03’s all-positive oracle-marginal screen. It selects on the proposed mechanisms’ performance. Declaring that rule beforehand makes it prospective selection; it does not make selection independent of outcomes or purely a realism check. This distinction must survive into the paper.
Package interpretation and evidence boundary
I read 00 first, then 01, 02, 03, 04 and 09–11, and consulted the relevant accounting clauses in 05. Package citations below use those numbered filenames and section/function names. Historical results in 04 are supplied project evidence, not independently reproduced measurements. No simulator, learner or TEST split was run or opened; no attachment was modified.
File
Controlling fact or conflict
01, §§2–4
Finite demand in Mbit/s; no micro-sleep; all grid points probed; first qualifying point selected; five main deployment arms.
02, §§1–4
Different Mbit/slot grid, sleep, 2.5 W circuit power and sum-power proposals; several unverified numerical forecasts and incorrect physical deductions.
03, steps 1–3
Restates 01’s minimal physics, but adds all-positive oracle marginals, DROP arms and a fast-iteration framework.
09–11
Confirm 30.08 s, angle-based link power, max aggregation and square-root efficiency. They are excerpts, not the complete executable rate/energy pipeline.
Treat 01/03 as the proposed minimal regime for this review. Before sealing, resolve their selection-rule differences and explicitly mark the incompatible parts of 02 as superseded. Some supplied constants, including 0.338/0.200 W, are not declared in the provided code excerpts; their package values are taken from the question/design text, and their literature provenance is checked separately.
2. Traffic demand: magnitude, units and workload realism
What public measurements establish
Define “user” as a subscriber terminal serving a household or small site, unless a different population is expressly intended. One person, one household router, one enterprise terminal and one cell aggregate have different demand distributions. A rate measured during a speed test is achievable service under an induced transfer, not the terminal’s ordinary offered traffic.
OpenVault’s 1Q25 measurements report 616.2 GB/month average downstream consumption and a residential peak-hour average of 1.544 GB/hour per subscriber. Using decimal units, these correspond to approximately 1.90 Mbit/s over a declared 30-day month and 3.43 Mbit/s during the peak hour. This is broadband-provider data, without a separately identified LEO cohort. Its hourly aggregation does not reveal 30-second demand. OpenVault, 1Q25, pp. 6 and 9–10.
Preseem independently reports most sampled ISPs at 3–4 Mbit/s downstream busy-hour load per subscriber, explicitly including inactive subscribers in the denominator. Thus a 3–5 Mbit/s busy-hour household proxy is defensible; an exact 5 Mbit/s workload is a rounded analyst choice. Neither source estimates the distribution conditional on a terminal being actively downloading. Preseem (2024).
System evidence
What the number means
What it cannot justify
Starlink: ACCC reports 170.2 Mbit/s average busy-hour download speed, March 2025
Regulator speed tests during busy network hours; release dated 27 June 2025
170–200 Mbit/s average offered demand from every subscriber
Kuiper: 2023 terminal announcement gives up to 100, 400 and 1,000 Mbit/s for different terminal classes
Historical equipment capability targets
Measured traffic, concurrency, busy-hour means or a demand CDF
OneWeb: TMA 2025 measurement study
Evidence about connectivity/performance exists
No verified per-terminal offered-load distribution was obtained in this review
Sources: ACCC; Amazon’s original terminal announcement; OneWeb measurement authors’ publication page. The OneWeb full paper could not be retrieved reliably; indexed SLA numbers are therefore not used as numerical anchors.
Assessment of the existing grid
For d in Mbit/s, the offered batch is D = 30.08d Mbit. The following are arithmetic conversions, not simulation outcomes.
Point
Per terminal per interval
Aggregate offer for 100 terminals
Realism judgment
G0: full buffer
Unlimited backlog
Capacity-limited
Standard saturation control; no finite-demand population interpretation
G1: 200 Mbit/s
6,016 Mbit = 752 MB
20 Gbit/s
Possible large transfer for a capable terminal; extreme as simultaneous sustained demand from every household
G2: 50 Mbit/s
1,504 Mbit = 188 MB
5 Gbit/s
Plausible heavy active transfer or site aggregate; high as subscriber-average busy-hour demand
G3: 10 Mbit/s
300.8 Mbit = 37.6 MB
1 Gbit/s
Plausible sustained active household load; still above the measured subscriber-average proxies
Magnitude anchors: ACCC; Preseem. Classification is this review’s inference, not an operator traffic classification.
If sustained continuously for 30 days, 200/50/10 Mbit/s would imply 64.8/16.2/3.24 TB per terminal. This illustrates intensity only: the package’s ten-step episode lasts 300.8 s, not a month. Its 95%-of-demand guard at 200 Mbit/s requires roughly 190 Mbit/s for nearly every counted terminal; that is a demanding synchronized service experiment.
Critical unit correction: file 02’s 50–200 Mbit/slot equals only 1.66–6.65 Mbit/s at 30.08 s. Its 150 and 300 Mbit/slot points equal 4.99 and 9.97 Mbit/s. Those proposals cannot be cited as if they support the same numerical values in Mbit/s.
Recommended traffic and timing values
The recommended set has four points including the control. It replaces the 200 Mbit/s stress point with 5 Mbit/s; it does not add a fifth point. Freeze new labels and any priority order explicitly rather than silently reusing G1’s old meaning.
Parameter
Recommended value/range
A priori justification and qualification
Full-buffer control
∞
Retain; standardized system-evaluation convention, not representative offered traffic. ITU-R M.2514
Residential load anchor
5 Mbit/s; proxy range 3–5
150.4 Mbit per interval. Rounded household busy-hour scenario, not a measured LEO mean. Preseem
Sustained active use
10 Mbit/s
Retain as a heavier active-use scenario; finite-demand LEO studies also use 10 Mbit/s. Fastenbauer et al., §V
Heavy active use
50 Mbit/s
Retain as a heavy-transfer scenario within demonstrated access capability, not as ordinary mean demand. ACCC
Optional substitute stress case
200 Mbit/s
Keep only if high active/aggregated demand is the declared scientific population; it should replace a point, not be chosen after results. Amazon, 2023 capabilities
Decision interval
30.08 s, explicitly self-chosen
47 × 0.640 s from file 09. No literature-derived exact value. It is an association clock, not a validated beam-hopping slot.
Demand expiry
30.08 s only as declared deadline service
No generic broadband anchor for this deadline. Ordinary queues need carryover/retry semantics. Zhu et al., §II
Demand distribution
Deterministic for this minimal study; no fitted tail exponent
Retain only with a synthetic-workload label. No LEO-specific 30-second Pareto/lognormal parameters were established.
Finite demand is not one traffic model
Model
What it represents
Mapping to the package
Full buffer
A persistent saturated backlog; tests available service capacity
G0. Valid control; does not approximate an average household.
Deterministic expiring batch
D bits available at the interval start; delivered bits capped; residual expires
Exactly 01’s minimal proposal. No stochastic arrivals or persistent queue.
Finite-arrival FTP traffic
Files/packets arrive with a prescribed size and arrival process
TR 38.821 Table 6.1.1.1-7 specifies FTP3 and 0.5 Mbyte packets; it does not specify 50–200 Mbit/slot.
Persistent arrival queue
New arrivals join unserved work: Q(next) = max(Q − service, 0) + arrivals
Zhu et al. use equal-size Poisson arrivals per cell and gateway queues; their aggregate is not a terminal demand calibration.
Sources: 3GPP TR 38.821 V16.0.0, p. 45; Zhu et al. (2024). ITU-R M.2514 uses full-buffer configurations, including its VSAT example, and explicitly distinguishes evaluation settings from deployment requirements. It does not establish file 02’s packet-demand range. ITU-R M.2514, §8.2.3 and Annex 2.
A useful standards-aligned simulation example compares full-buffer and limited-load operation using FTP3, 60 kB downlink files and 100 ms mean interarrivals: a derived mean offer of 4.8 Mbit/s per terminal. This is a GEO simulation assumption, not LEO field measurement, but it demonstrates that finite-arrival satellite evaluations need not use tens or hundreds of Mbit/s per terminal. Sormunen et al. (2025), Table I.
Heterogeneity and heavy tails
OpenVault reports 4.88% of subscribers above 2 TB/month and 0.16% above 5 TB/month in 1Q25. This establishes a substantial high-usage tail at monthly resolution; it does not establish a power-law exponent, a 30-second distribution, or a LEO-specific law. OpenVault, p. 3.
A representative future workload would need terminal activity, conditional active-transfer intensity, burst duration, temporal correlation and geographic correlation. A distribution family and all its parameters should come from an external trace or an expressly synthetic construction fixed before outcomes. Do not infer a Pareto shape from speed-test CDFs or monthly threshold counts. For the current minimal study, homogeneous demand is acceptable as a controlled simplification, but the paper should not claim that it captures statistical traffic multiplexing.
The existing combination of expiring demand, no unused-share reallocation and interval-long carrier operation is a reserved-service model. Clipping counted bits alone does not model a work-conserving broadband scheduler or packet-level sleep. This choice may create avoidable energy expenditure relative to a more adaptive scheduler; it is a substantive limit on external validity.
3. Payload power: defensible anchors and reference planes
What the present PA model actually does
From file 11, below saturation:
η(p) = 0.35 √(p / 5.218), and P_DC(p) = √(5.218p) / 0.35.
Output back-off is OBO = 10 log10(p_sat / p), using the same RF reference plane and average-power convention. The values below are direct calculations from the supplied model.
Operating point
RF output
OBO
Model efficiency
PA DC draw
Segment start
0.825 W
8.01 dB
13.92%
5.93 W
Maximum admitted link/beam output
1.650 W
5.00 dB
19.68%
8.38 W
Hypothetical saturation, outside legal range
5.218 W
0 dB
35.00%
14.91 W
Thus 35% is not the achieved operating efficiency in the allowed range. The segment-start and maximum draws correspond to approximately 178.3 and 252.2 J of PA energy per 30.08 s. The stated 0.338 W beam circuit term adds 10.17 J; 0.200 W adds 6.016 J per charged satellite interval.
The second derivative of P_DC is negative for positive p. Therefore file 02’s proposed convex-cost/Jensen argument is backwards for this model: splitting a fixed RF total among otherwise identical active amplifiers increases the sum of square roots. Channel gains, interference, service constraints and activation costs can change the complete system comparison, so this algebra is not a theorem that consolidation always wins either. Nor does increasing transmit power universally worsen EE at every SNR; the package’s blanket monotonic statement lacks the necessary conditions.
The square-root law is a legitimate published analytical approximation. It is not a measured universal Doherty curve, and it omits a separate quiescent PA term as p approaches zero. Whether that omission matters depends on the operating range and shutdown semantics. You et al., Eq. (12).
Measured hardware anchors
Primary source
Reported operating evidence
Permitted inference
Piacibello et al., 2022, Ka-band GaN Doherty
16.3–20.3 GHz; 36.6–37.7 dBm saturation = 4.57–5.89 W; 23–31% PAE at saturation; about 20% PAE at 6 dB OBO
A roughly 5 W amplifier is credible at the chip/module plane. This does not establish a complete beam’s power.
Piacibello et al., 2024, high-gain Ka-band Doherty
17.3–20.3 GHz; above 36 dBm saturation; CW PAE 23–30%, relatively flat over 5–6 dB OBO
Back-off efficiency can have a plateau. Process was not space-qualified at design; wider/high-PAPR signal validation was still needed.
ESA, 2023 tested Doherty project
20 W saturation/10 W operating and 10 W saturation/5 W operating targets; tested PAE above 34% across 17.3–20.2 GHz
Approximately 3 dB OBO is another device-specific example; not a universal commercial payload setting.
Sources: Piacibello 2022 accepted manuscript; Piacibello 2024 published paper; ESA project report.
PAE and drain efficiency must remain distinct: PAE = (P_out − P_in)/P_DC, whereas η_D = P_out/P_DC. With power gain G, η_D = PAE/(1 − 1/G). Do not insert measured PAE directly into a drain-efficiency denominator without the conversion and matching measurement boundaries. Similarly, input back-off and output back-off are different quantities. The Sormunen simulation uses 5 dB IBO but 0.8 dB OBO for one downlink configuration, illustrating why waveform and amplifier assumptions must accompany a number. Sormunen et al., Table I.
Recommended power and resource parameter treatment
These are evidence ranges and accounting recommendations, not a new multi-parameter outcome-search grid. The literature does not identify a universally realistic beam or satellite wattage.
Parameter
Defensible range/value
Required label or action before freeze
RF cap
Retain 1.65 W as this model’s feasibility cap
Equals about 5 dB OBO relative to 5.218 W. No source establishes it as a commercial-beam or regulatory limit. Package 01/11; Piacibello anchors below.
PA saturation
4.57–5.89 W for the specific 2022 measured design; broader selected devices reach 10–20 W
Retaining 5.218 W is plausible for a module abstraction, not field calibration. Identify chip, element, subarray or beam reference plane. Piacibello 2022; ESA 2023
Operating OBO
Selected examples support 3–6 dB; lower outputs can be further backed off
Freeze device, waveform, temperature, distortion criterion and average/peak convention. Do not independently mix range endpoints. Piacibello 2024; ESA 2023
Efficiency law / 0.35 scale
Retain the analytical model; measurements include ~20% PAE at 6 dB OBO, 23–31% at saturation, and >34% in ESA tests
0.35 is an assumed saturation scale, not verified deployed efficiency; use a complete measured curve if changing hardware. You 2022; measured sources above
RF-chain circuit
0.338 W as a published simulation coefficient
Not a verified complete-beam static budget. You 2022, Eq. (15), §V
Digital precoder block
0.200 W as a published simulation coefficient
Not a whole-satellite baseband budget. No defensible universal satellite-total range found. You 2022
Array/DBF additions
Source model separately uses 10/20 mW per phase shifter, 1 mW per switch and 5 mW oscillator
Count actual components and shared resources; no validated 2–4.5 W per formed beam range. You 2022
Beam bandwidth
Retain 500 MHz / 3 = 166.667 MHz as a declared allocation
Plausible order of magnitude, not an operator-calibrated allocation. Publish reuse/PSD/noise assumptions. A comparison study uses a 200 MHz TDM carrier. Sormunen 2025
Beam/satellite activation cost
No universal zero-to-active wattage or switching delay established
Specify what physically shuts down, idle draw, transition cost and shared power. Do not assert zero whole-satellite power when its last modelled beam empties.
In You et al., the 338 mW RF chain comprises a DAC, mixer, low-pass filter and baseband amplifier; the 200 mW term is a digital precoder. PAs are counted per antenna element, and RF chains, phase shifters and antennas have distinct counts. The source therefore does not establish one beam = one chain = one amplifier. Its parameters are model assumptions, not flight measurements. You et al., Eqs. (12), (15), §V.
Accordingly, call the present denominator energy of the modelled communication subsystem. Whole-network or whole-spacecraft energy would also require a defined accounting treatment for shared processing, conversion losses, persistent payload functions and any included gateway/terminal resources. Omitted fixed energy does not automatically cancel in an EE comparison when delivered bits differ.
Is max over users defensible?
Yes, under an explicit shared-carrier provisioning interpretation; no, if each existing p_u is claimed to be an independently radiated simultaneous user allocation. The decisive issue is what p_u measures and how users are multiplexed.
Multiplexing interpretation
Correct power/energy relationship
Consequence for the current implementation
TDM, fixed common carrier power
Choose P_b = max required full-band user power; each user obtains airtime fraction α_u. E_PA = Δt P_DC(P_b).
Max can be conservative and coherent. Desired signals must use the common actual P_b. Equal airtime can yield the W/n rate form.
TDM, power adapted per user
E_PA = Σ τ_u P_DC(p_u), with Σ τ_u ≤ Δt, plus idle/transition terms
Neither an unweighted sum nor max generally gives average consumption.
FDMA/OFDMA independent allocations
P_b = Σ q_u, where q_u is actual RF power over W_u; noise = N₀W_u
Sum is appropriate. Recompute allocation, interference overlap and feasibility; do not sum unchanged full-band requirements.
OFDMA, common uniform PSD
q_u = P_b W_u/W; total P_b can remain fixed as shares change
A load-independent beam total is possible. Signal, noise and overlapping interference must scale consistently.
Spatial streams / shared active array
Average stream powers combine through precoder weights at each antenna; DC cost applies at physical PAs
Independent per-beam costs require a dedicated-hardware or explicit equivalent abstraction.
These relationships are engineering consistency deductions. For waveform precedent, the primary comparison paper explicitly contrasts a DVB-S2X TDM carrier with NR resource-block scheduling; it does not identify Starlink’s waveform or prescribe a max rule. Sormunen et al. (2025).
Multicast can also be governed by a worst-user requirement, but a common codeword is not equivalent to independent unicast broadband goodput. The current recurrence compensates antenna angle, not a target rate/SINR. Its p_u should therefore not be relabelled a QoS-required OFDMA allocation without redesign.
Pre-freeze consistency requirement: demonstrate one accounting identity linking actual radiated power, desired received signal, user bandwidth/airtime, noise, cochannel interference and PA energy. The supplied excerpts expose the max aggregation but omit the complete signal/rate call site. This review cannot certify that identity or diagnose a definite signal-power bug from the excerpts alone.
4. Set-level coordination: deployment architectures and reported gains
Architectures that have a credible information path
Starlink measurements from four terminals in the US and Europe show synchronized 15-second scheduling signatures. The authors infer a global association scheduler and finer onboard MAC scheduling; the proprietary decision algorithm and its full inputs are not observed. This is evidence that centralized association is plausible, not validation of the package’s 30.08-second carrier assumption. Tanveer et al., CoNEXT Companion 2023.
A ground gateway/controller can use demand or queue reports, predicted geometry, previous associations and delayed link telemetry to issue a future schedule. Zhu et al. explicitly motivate queue/geometry-based epoch decisions because collecting instantaneous global CSI, optimizing and uploading a schedule take time. Their model uses 120 ms epochs and a slower 72 s serving-satellite update. This supports separating association from radio scheduling clocks. Zhu et al., §§I–II, V.
Coordination graphs offer another information architecture: joint values retain pairwise payoffs and max-plus messages participate in action selection. This differs from learning an interaction signal and then making independent unary argmax decisions. Convergence guarantees for max-plus depend on graph structure; the Deep Coordination Graphs demonstrations are not satellite experiments. Böhmer, Kurin and Whiteson, ICML 2020.
Package arm/mechanism
Corresponding literature category
Claim it can support
S0: nominal physics; fixed proposals, catalog and decoder
Model-based centralized configuration selection
Value of deployable joint control with an explicit physical predictor
S3: learned full-configuration outcomes, same decoder
Learned-surrogate configuration selection
Added predictive value over S0; total coordinator effect relative to M12
Whole source-beam evacuation
Joint association/consolidation move
Restricted simultaneous edits; not beam hopping unless illumination timing changes
M123: independent Q1+Q2+Q3 argmax
Independent execution of unary scores
Tests the specified additive target/interface; not max-plus or centralized scheduling
Exact privileged teacher
Offline catalog oracle
Finite-panel headroom with realized information; no deployment-efficacy claim
This mapping is an interpretation of file 01 §3, not a claim that the package reproduces any cited implementation.
Quantitative evidence with the actual comparator retained
Study
Reported gain / comparison
Scope and applicability
Fastenbauer et al., 2025, peer reviewed
Almost 90% modelled power reduction versus full illumination for 19 beams and 25 users at 10 Mbit/s, high elevation; greedy closely matches exhaustive optimization in the seven-beam low-demand case
Uses 1 ms beam-hopping slots. Strong reason to include S0; not a forecast for no-DTX, 30.08 s association control.
Lyu and Qi, 2023, peer reviewed
At 200 users, about 1.02% more scheduling slots than CVX, with 0.0138 versus 19.8143 s runtime
Shows a strong low-complexity scheduler. Comparator is optimization, not independent user association; slots and runtime are not EE.
Zhao et al., 2024 preprint
Throughput +96.7% versus random BH/equal power, +46.2% versus random BH/demand-based power, +10.2% versus coordinated BH/equal power, +5.6% versus discrete-power baseline; load disparity improves 75.95% versus Greedy BH
A3C coordination plus MADDPG power allocation, 12 satellites and 2 ms slots. Different metrics and action space; no C3 or pooled-EE marginal.
Jayarajan et al., June 2026 preprint
Paper-wide ranges of 20–30% more demand satisfaction and 15–25% more coverage than baseline approaches
Joint cell–satellite–gateway orchestration. Baselines include nearest assignment and demand-ordered load-aware selection; cell aggregates, not independent terminals. Ranges are not a single matched greedy-association effect.
Sources: Fastenbauer et al., Figs. 12 and 15; Lyu and Qi, §V.B; Zhao et al., §V.C; Jayarajan et al., NEO-GNN.
There is no defensible single percentage for “gain over per-user greedy association” transferable to this experiment. Greedy beam hopping already makes set decisions; nearest-cell assignment, load-aware association and M12 are different comparators. Throughput, delay, coverage and power savings must not be relabelled pooled EE improvements. The newer preprints are useful architecture examples, with weaker publication status than the peer-reviewed anchors.
What must be fixed for S0/S3 to count as deployable
The observation contract should identify where the controller runs, who knows current demand, report timestamps and maximum age, proposal message sizes, controller runtime and the time needed to distribute assignments. Execution should mean a common scheduled epoch, with existing handover interruption/service accounting applied to every changed user. Excluding realized fading is necessary but does not alone establish deployability.
S0 and S3 need the same catalog, input availability, decision timing, constraints and tie rules. Freeze what “nominal physics” means under stochastic fading: evaluating at mean fading is generally different from computing expected delivered bits. If S3 receives richer information or a better uncertainty treatment, S3/S0 measures more than learning alone.
Predicted service constraints are not guarantees; actual violations must be counted without oracle repair. The learned objective is also a surrogate: the ΔB − λ_BΔE term plus a Q2 contribution is not automatically an exact optimizer of pooled EE. Keeping λ_B and κ_B calculation rules fixed is appropriate, but the result still requires prospective evaluation. Failure of the top-2/evacuation catalog rejects that tested architecture, not every centralized coordinator.
5. Constructed regimes and pre-registration
Accepted precedent, with a bounded claim
Yes: controlled synthetic regimes are accepted tools for mechanism evaluation. This is not the same as a blanket guarantee that any constructed regime will satisfy a networking reviewer. The evidence supports three related practices:
Networking test scenarios: IETF RFC 8867 specifies controlled congestion-control cases with motivation, expected behavior, metrics, topology, traffic and timing. It even explains why a scalable controlled rate range can be preferable to treating one deployment rate as universal. It is an Informational RFC, not a LEO validation standard. RFC 8867, §§3–5.
RL mechanism benchmarks: bsuite deliberately varies difficulty in small tasks designed to isolate exploration, memory, credit assignment and other capabilities. This supports a mechanism-focused regime map, not claims of field representativeness. Osband et al., ICLR 2020.
Prospective evaluation: the NeurIPS pre-registration workshop accepted experiment plans before results, including a constructed real-time RL setting in which the environment evolves during computation. The venue explicitly welcomes negative results and separates exploratory observations from confirmation. Thodoroff et al., PMLR 181 (2022); workshop protocol.
No reviewed source endorses the package’s exact combination of headroom thresholds, first-qualifying selection and all-positive oracle marginals. Its legitimacy is a methodological inference from these precedents, conditional on transparent selection and independent confirmation.
Three decisions that must not be conflated
Choosing the workload values: use external magnitude, service semantics and hardware accounting before Track B outcomes. That is the realism task addressed here.
Choosing a regime after a fixed development probe: file 01’s first-qualifying rule uses measured oracle headroom. It is an adaptive selection procedure whose rule is pre-specified; the selected value itself is not fixed beforehand. Its campaign can answer a conditional question on fresh worlds, but cannot estimate average effectiveness across real LEO workloads.
Requiring positive C1/C2/C3 oracle marginals: file 03 adds method-performance enrichment. This may be disclosed as an engineering triage procedure, but it cannot be described as selecting only for physical realism. In particular, any reported positive oracle marginals after that screen are selection criteria, not independent confirmation.
For a study explicitly intended to establish realistic value ranges, remove the all-positive-marginal requirement from the realism-selection rule. It can remain a reported diagnostic. If retained as a training-budget gate, freeze whether the first point is selected before this gate, whether a gate failure terminates the campaign, and whether the next grid point is ever considered. The present 01/03 text does not make that sequence fully unambiguous. This recommendation concerns inferential clarity, not which point helps C3.
Statistical and procedural commitments still needed
Freeze every threshold and its role: 5% joint headroom, 1% J−U margin, 0.5% interaction surplus, three-of-four world direction, ≥1% deployment improvement, service slack and demand guards are investigator choices. Literature does not supply these exact cutoffs.
J and U are non-nested catalogs. A positive J−U gap demonstrates that the J catalog achieves more than U on that panel; it is not generally a nested “adding joint actions” effect. Use a predeclared union if that nested estimand is intended, or retain the restricted-comparison wording.
Specify whether FULL-versus-DROP means masking a trained head or retraining without its mechanism. These estimate different contributions. Fix which architecture’s FULL is used and how oracle Q2’s multi-step target is constructed in the “one-step” oracle-marginal probe.
Define one success test, including uncertainty, for the conjunction that all three marginals are positive. Separate per-head intervals or later claims need an explicit multiplicity policy; pre-registration alone supplies no error control.
Resample matched worlds jointly across arms and recompute each ratio of summed bits to summed joules. Do not bootstrap per-user opportunities as independent or replace pooled EE with a mean of ratios. With only three trained lineages, a world-only interval is conditional on those policies and does not capture broad training-seed variability.
Freeze calibration completion, stopping rules, failed-run handling and which development/validation information may change anything. A later fresh namespace or sealed iteration does not erase outcome-informed redesign across iterations. Report the complete sequence, including NONE and INCOMPLETE outcomes.
Time-stamp and archive the exact protocol, code/configuration hashes and permitted repairs before generating the relevant outcomes. Keeping TEST closed is useful, but confirmation depends on the actual independence of all information used, not on a split’s filename.
These are design-specific deductions. The statistical caution is supported by empirical RL work showing that few-run point estimates and changed evaluation protocols can reverse conclusions; reproducibility reporting should expose experimental choices. This does not justify changing the project’s pooled-EE estimand to another aggregate. Agarwal et al., NeurIPS 2021; Pineau et al., JMLR 2021.
Suggested disclosure language
“Track B is a prospectively specified, constructed workload study motivated by the previously reported Track A failures. Its finite-demand levels are externally motivated service scenarios, not a fit to commercial LEO traffic traces. All declared grid points and screening outcomes are reported. The campaign regime is selected by the published development-stage rule, and deployment comparisons use independent, previously unused confirmation worlds. Conclusions apply to the selected workload, stated communication-subsystem power model, observation contract and action catalog. Track A’s negative findings remain unchanged.”
If file 03’s extra filter remains, add: “Progression to training additionally requires positive oracle marginals for all three mechanisms. This is method-dependent development selection. Those selected oracle results are not counted as confirmatory evidence, and deployment claims remain conditional on this enrichment procedure.”
6. Explicit reviewer objections and required disposition
The following list separates errors needing correction from abstractions that can be retained with limited claims.
Unit error / conflicting authority: file 02’s Mbit/slot values differ by a factor of 30.08 from identical numbers in Mbit/s. Resolve before sealing; do not merge the two grids or citations.
Unsupported standards attribution: TR 38.821 and ITU-R M.2514 do not establish 50–200 Mbit/slot broadband demand. Replace that attribution with their actual traffic configurations.
Unverified hardware claims: the abbreviated “Del Re et al., IEEE Aero. 2020” and “ESA LEO Payload Survey” references could not be uniquely verified. The asserted 2–4.5 W/beam range and 2.5 W replacement remain unsupported, not proved nonexistent.
Incorrect convexity argument: square-root DC power is concave. File 02’s sum-power/Jensen explanation and universal EE-monotonicity claim require correction, not a footnote.
Unsupported effect-size forecasts: file 02’s 15–20% RF savings, 25–40% energy savings, 30–50% EE gain and 30–50% spectral-efficiency collapse are not verified expectations for this model. Remove them from numerical justification.
Historical contradiction: file 02’s statement that regime A has ≤1.2% oracle headroom conflicts with file 04’s supplied U1 +1.992% and J1 +2.222% record. Preserve the latter with its finite-panel, privileged-information qualification.
Undefined terminal population: 100 mobile “users” under real TLEs are not automatically 100 representative residential terminals. A household, vehicle or enterprise interpretation must be explicit.
Unrealistic homogeneity if generalized: identical positive demand for everyone at every interval omits idle periods, burstiness and spatially correlated demand. Acceptable controlled workload; insufficient population model.
Nonstandard expiry and idle operation: hard 30.08 s deletion, no retries, unused reserved shares and continuous carrier operation are substantive service assumptions. Do not label them generic broadband, statistical multiplexing or DTX.
Clock chosen for project behavior: file 09 says the historical 30 s choice sought nondegenerate objectives, later quantized to 30.08 s. This is disclosed project design history, not a standard-derived physical time scale. Its suitability needs a limited slow-control claim.
Power-reference mismatch: one PA module is not automatically one formed beam; 0.338 W is not a complete DBF beam budget and 0.200 W is not a satellite total. Define component counts and shared costs.
Incomplete max-power justification: max is plausible only with coherent multiplexing and received-signal accounting. Changing it to sum alone is not a low-risk correction.
Incomplete physical realism evidence: the excerpted instantaneous link accounting does not demonstrate interval integration of evolving channel/geometry or a complete weather/fade-availability model. Do not infer their absence from excerpts, but do not claim they were validated here.
Scheduler baseline weakness: nearest/stay/random carriers are useful probes; headroom above them need not survive retrained M0/M12. Keep the comparator-strength falsifier and a serious S0 baseline.
Outcome-dependent selection: first-qualifying oracle screening is adaptive, and all-positive oracle marginals are method-dependent enrichment. A fixed priority order reduces discretion but does not remove selection.
Repeated-iteration selection: sealing each new attempt after learning earlier outcomes does not make the entire research program outcome-independent. Preserve all attempts and limit later confirmation claims.
Architecture/claim mismatch: S3’s centralized decoder changes execution relative to M123. A positive S3 does not establish success of the original independent three-head argmax, and a failed catalog is not a universal impossibility result.
Unspecified marginal inference: DROP semantics, oracle horizon, per-head uncertainty and only three training lineages can materially change the meaning of “each head improves EE.” Freeze those meanings before reporting significance.
7. Evidence limits and source notes
No public, verified 30-second offered-load trace for representative Starlink, OneWeb or Kuiper subscribers was obtained. No complete commercial payload component-and-power budget was obtained. Consequently, this report provides proxy-based traffic magnitudes and device/component anchors, not a field-calibrated replacement simulator. Missing evidence is not a negative experimental result.
The search used primary standards, regulator/provider measurements, original engineering papers, institutional author manuscripts and methodological venue records. Independent traffic, power and coordination reviews were reconciled; consequential numbers and claims were checked against original documents. Search refinement targeted demand-versus-speed denominators, standards units, hardware reference planes, realistic controller information and strong greedy counterexamples. Searching stopped once those claims were supported or their gaps bounded; additional generic sources would not supply the missing proprietary distributions or payload budget.
Source details
OpenVault. Broadband Insights Report 1Q25. May 2025. Primary measurement report; pp. 3, 6, 9–10. Report.
Preseem. Subscriber Data Usage Metrics and Trends. 21 March 2024. Primary provider measurement analysis. Article.
Australian Competition and Consumer Commission. Wireless networks provide high speed alternatives to remote and regional households. 27 June 2025. Measurement release.
Amazon. Here’s your first look at Project Kuiper’s low-cost customer terminals. March 2023. Historical first-party capability announcement. Article.
Zhao, J.; Perrin, O.; Ahangarpour, A.; Pan, J. Measuring the OneWeb Satellite Network. IEEE/IFIP TMA 2025. Publication identity verified; full-paper numerical claims not used. Authors’ project page.
3GPP. TR 38.821 V16.0.0: Solutions for NR to support non-terrestrial networks. December 2019. Table 6.1.1.1-7. ATIS copy.
ITU-R. Report M.2514-0: Vision, requirements and evaluation guidelines for satellite radio interface(s) of IMT-2020. September 2022. Report.
Sormunen, L., et al. Simulative Comparison of DVB-S2X/RCS2 and 3GPP 5G NR NTN Technologies in a Geostationary Satellite Scenario. 2025 author manuscript, arXiv:2502.13704. Paper.
You, L., et al. Massive MIMO Hybrid Precoding for LEO Satellite Communications With Twin-Resolution Phase Shifters and Nonlinear Power Amplifiers. 2022 author manuscript, arXiv:2206.04250. Paper.
Piacibello, A., et al. A 5-W GaN Doherty Amplifier for Ka-Band Satellite Downlink With 4-GHz Bandwidth and 17-dB NPR. IEEE MWCL 32(8), 964–967, 2022. DOI.
Piacibello, A., et al. High-Gain and High-Linearity MMIC GaN Doherty Power Amplifier With 3-GHz Bandwidth for Ka-Band Satellite Communications. IEEE MWTL 34(6), 765–768, 2024. DOI.
European Space Agency. Design, Manufacture & Test of a Single-chip Ka-band Doherty Power Amplifier. 16 January 2023. Engineering report.
Tanveer, H. B., et al. Making Sense of Constellations: Methodologies for Understanding Starlink’s Scheduling Algorithms. CoNEXT Companion 2023, 37–43. DOI; author text.
Zhu, J.; Sun, Y.; Peng, M. Beam Management in Low Earth Orbit Satellite Networks with Random Traffic Arrival and Time-varying Topology. 2024 author manuscript, arXiv:2404.08959v1. Paper.
Fastenbauer, A., et al. LEO Satellite Beam Hopping for Power Consumption Minimization at Different Elevation Angles. IEEE OJCOMS 6, 6930–6952, 2025. DOI.
Lyu, L.; Qi, C. Beam Position and Beam Hopping Design for LEO Satellite Communications. China Communications 20(7), 29–42, 2023. Author-hosted paper.
Zhao, R., et al. Demand-Aware Beam Hopping and Power Allocation for Load Balancing in Digital Twin empowered LEO Satellite Networks. 2024 preprint, arXiv:2411.08896v1. Paper.
Jayarajan, A.; Matson, N. C.; Sundaresan, K. LEO Satellite Network Orchestration with Heterogeneous Graph Neural Networks. June 2026 preprint, arXiv:2606.31950v1. Paper.
Böhmer, W.; Kurin, V.; Whiteson, S. Deep Coordination Graphs. ICML 2020, PMLR 119, 980–991. Proceedings.
Sarker, Z., et al. RFC 8867: Test Cases for Evaluating Congestion Control for Interactive Real-Time Media. IETF, January 2021, Informational. RFC.
Osband, I., et al. Behaviour Suite for Reinforcement Learning. ICLR 2020; 2019 author manuscript. Paper.
Thodoroff, P.; Li, W.; Lawrence, N. D. Benchmarking Real-Time Reinforcement Learning. NeurIPS 2021 Pre-registration Workshop, PMLR 181, 26–41, published 2022. Proceedings.
NeurIPS 2021 Workshop on Pre-registration in Machine Learning. Experiment-plan and results-stage policy. Venue protocol.
Agarwal, R., et al. Deep Reinforcement Learning at the Edge of the Statistical Precipice. NeurIPS 2021. Proceedings.
Pineau, J., et al. Improving Reproducibility in Machine Learning Research (A Report from the NeurIPS 2019 Reproducibility Program). JMLR 22(164), 1–20, 2021. Paper.
Project input: multi-catfish-track-b-chatgpt-review-package-20260908-r1.zip, the uploaded attachment in this conversation. It was consulted as supplied evidence and is not embedded in this report.
All linked sources were accessed on 8 September 2026. Publication status is labelled where author manuscripts or preprints are used.
