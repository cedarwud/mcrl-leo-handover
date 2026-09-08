# Literature-Anchor and Realism-Check Report: Track B Constructed-Regime Pre-Registration (LEO Handover Simulator)

## TL;DR
- **The physics envelope is mostly defensible-but-stylised, with three clear problems to fix before freezing:** (i) the per-user demand grid conflates two incompatible unit readings (Mbit/s in file 01 vs Mbit/slot in file 02) and G1 = 200 Mbit/s sustained is a full-buffer-like extreme, not a demand; (ii) the static hardware constants (0.338 W/beam, 0.200 W/satellite) and the √ (class-B) efficiency curve are orders-of-magnitude-low and wrong-shaped for the cited Ka-band Doherty hardware; (iii) "max-over-users" per-beam power is internally consistent only under a TDM/constant-carrier reading, which sits uneasily with the equal-bandwidth split.
- **The constructed-regime methodology is accepted practice** (ML pre-registration, RL-evaluation rigor à la Henderson 2018 / Agarwal 2021, and multiverse/specification-curve reporting à la Steegen 2016 / Simonsohn 2020) *provided every claim is stated as conditional on the pre-declared regime with no external-validity claim*; the probe thresholds are conservative, but the G1→G2→G3 ordering, the λ_B/κ_B calibration panel, and the "each of C1/C2/C3 positive" criterion each need one explicit a-priori sentence to remove an outcome-driven appearance.
- **Several citations do not hold as used:** "Del Re et al., IEEE Aerospace 2020" and the "ESA LEO payload survey" (2–4.5 W per-beam) could not be verified and should be removed or re-sourced; TR 38.821 §6.1 and ITU-R M.2514 do **not** contain per-user 50–200 Mbit demand ranges; and TS 38.213/38.214 define a per-RE constant EPRE, not a beam sum-power rule. "You et al." is confirmed (IEEE Trans. Commun. 2022, mW-level component powers), while "Zhu et al." and "Ye et al." are conceptually sound but not uniquely traceable.

## Scope and stance
This report anchors and stress-tests the a-priori numbers and methodology of the Track B regime. Per the binding constraint, it makes **no** recommendation favouring any arm (C1/C2/C3, additive M123, or coordinator S0/S3) and never recommends a grid point or regime because it would help a method win. All observations concern realism, literature anchoring, internal consistency, and methodological acceptability only.

---

## 1. Per-user traffic demand for LEO broadband

**Speed-test medians (peak capability, not demand).** Ookla Speedtest Intelligence (June 2025) states verbatim that "users on Starlink's network experienced median download speeds nearly double from 53.95Mbps in Q3 2022 to 104.71Mbps in Q1 2025," with upload rising 7.50→14.84 Mbit/s and only 17.4% of US Starlink users meeting the FCC 100/20 Mbit/s minimum in Q1 2025; by 2H 2025 medians exceeded 100 Mbit/s in every US state but Alaska, and SpaceX's VP of Engineering claimed typical downloads over 200 Mbit/s. A mobile measurement study — Laniewski, Lanfer et al., "Starlink on the Road: A First Look at Mobile Starlink Performance in Central Europe" (IFIP TMA 2024; arXiv:2403.13497) — reports verbatim "download throughput medians of 284.68 Mbit/s and 303.85 Mbit/s for non-priority and priority, respectively." These are *attainable* per-session rates under test conditions, **not** sustained per-subscriber demand.

**Sustained/busy-hour per-subscriber demand (the correct anchor for d_u).** This is one to two orders of magnitude below speed-test medians. Osoro & Oughton (IEEE Access 9:141611–141625, 2021) state verbatim: "if there is 1 user per 10 km² we estimate a mean per user capacity of 24.94 Mbps, 1.01 Mbps and 10.30 Mbps for Starlink, OneWeb and Kuiper respectively in the busiest hour of the day" (busy-hour overbooking factor 20); at the denser 1 user/km² the mean per-user Starlink figure falls to **2.49 Mbps in the busiest hour**. Cartesian's RDOF assessment used a ~20.8 Mbit/s per-subscriber allocation target against a 20 Gbit/s single-satellite throughput. Sandvine's 2024 Global Internet Phenomena Report (March 2024) states verbatim "On-Demand Streaming is the type of Video that generates the most traffic, with per-subscriber volume of 7.9 GB per day (54% of total downstream volume)" (YouTube 1.9 GB/sub/day, Netflix 1.4 GB/sub/day; fixed-network downstream ~14.5 GB/sub/day), confirming heavy-tailed, video-dominated traffic where a minority of heavy users generate most bytes.

**How NTN/LEO simulation models finite demand.** 3GPP TR 38.821 (NTN, Rel-16) baseline calibration uses **full buffer** with **10 UEs per beam**; a finite-load **FTP model 3** option exists. ITU-R M.2514 (2022) defines the satellite eMBB-s methodology and specifies "user experienced data rate is the 5% point of the cumulative distribution function (CDF) of the user throughput"; the IMT-2020 user-experienced targets (100 Mbit/s DL / 50 Mbit/s UL) come from ITU-R M.2410-0. **Neither TR 38.821 §6.1 nor M.2514 specifies a per-user demand range like 50–200 Mbit** — they use rate targets and traffic models, not per-user Mbit volumes. LEO queue/arrival papers overwhelmingly use Poisson or bursty finite-buffer arrivals (the "finite-demand" motivation is standard and defensible).

**Assessment of the grid (G1 = 200, G2 = 50, G3 = 10 Mbit/s sustained).**
- **G3 = 10 Mbit/s sustained** is realistic as a busy-hour figure for a moderately heavy broadband subscriber and is consistent with capacity studies (Osoro/Oughton 10–25 Mbps busy-hour band; Cartesian ~20.8 Mbps target). Verdict: **realistic**.
- **G2 = 50 Mbit/s sustained** corresponds to a very heavy user or a small multi-user household aggregate — above typical sustained averages (which sit at a few Mbit/s per the 2.49 Mbps dense-cell figure) but within the envelope of speed-test-era expectations. Verdict: **stylised-but-conventional (high end)**.
- **G1 = 200 Mbit/s sustained per user** for 100 co-located users implies ~20 Gbit/s aggregate demand over the 200×90 km area — comparable to an *entire* Starlink satellite's downlink capacity concentrated on 100 users, and above even speed-test *peaks* held continuously. Verdict: **extreme**; it functions as an effectively-full-buffer stressor, not a demand scenario.

**Capacity cross-check (realism/physics only).** At B_w = 166.667 MHz and SINR 10 dB, Shannon gives ≈166.667 × log2(11) ≈ 577 Mbit/s per beam. With ~44–66 active beams for 100 users (~1.5–2.3 users/beam), the per-user share when a beam carries ~2 users is ~250–290 Mbit/s. Therefore:
- G1 (200 Mbit/s) is at or above the per-user Shannon share → **demand rarely binds → behaves like full buffer**.
- G2 (50 Mbit/s) and G3 (10 Mbit/s) are well below per-user capacity → **demand-limited** for most users.
This is a physics observation only, not a selection rule.

**Units discrepancy (must resolve before freeze).** File 01 uses Mbit/s (per 30.08 s interval: 6.016 Gbit, 1.504 Gbit, 300.8 Mbit). File 02 writes demand as Mbit *per slot* (50–200 Mbit/slot; grid 150/300 Mbit/slot ≈ 5 and 10 Mbit/s sustained). Read as Mbit/slot, the numbers collapse to ~1.7–10 Mbit/s sustained — all realistic but a much narrower low range. The two readings are irreconcilable, and the file-02 "citing TR 38.821 §6.1 and ITU-R M.2514" justification does **not** hold, because those documents contain no such per-user demand ranges.

**Recommended units/phrasing.** State demand as "sustained per-terminal offered demand over a 30.08 s decision interval, expressed in Mbit/s, a priori chosen and not calibrated to field traffic," and report both the Mbit/s value and the per-interval Gbit equivalent to eliminate the file-01/file-02 ambiguity. A literature-defensible ≤4-point set anchored to sustained busy-hour demand would be, e.g., ∞ (full-buffer control), ~25 Mbit/s (Starlink dense-cell heavy user), ~10 Mbit/s (Osoro/Oughton-class), ~2.5 Mbit/s (average dense-cell subscriber) — offered strictly as a realism observation, not a recommendation to select any point.

---

## 2. Ka/Ku-band satellite payload power models

**PA efficiency vs back-off (GaN SSPA / Doherty).** Measured Ka-band GaN Doherty MMICs for the satellite downlink (17.3–20.3 GHz):
- Piacibello et al., "A 5-W GaN Doherty Amplifier for Ka-Band Satellite Downlink with 4-GHz Bandwidth and 17-dB NPR" (IEEE Microwave & Wireless Components Letters 32(8):964–967, 2022): 36.6–37.7 dBm output, 23–31% PAE at saturation, and **~20% PAE at 6 dB output back-off**; NPR > 17 dB.
- Colantonio & Giofrè, "A GaN-on-Si MMIC Power Amplifier with 10W Output Power and 35% Efficiency for Ka-Band Satellite Downlink" (EuMIC 2020, IEEE Xplore doc 9337363): **10 W output, 35% efficiency** (verbatim in the title); abstract corroborates >40 dBm (≈10 W), PAE peak >40%, 22 dB gain across 17.3–20.2 GHz.
- Doherty flattens efficiency over ~6 dB OBO; class-AB drops faster. 3–6 dB OBO for OFDM/DVB-S2X APSK is standard.

**Provenance of ξ_max = 0.35.** The 35% figure aligns precisely with the Colantonio/Giofrè Ka-band GaN headline efficiency — a defensible anchor for peak PA efficiency, though the simulator treats ξ_max as the maximum of a √-law curve reached only at saturation.

**(a) Is the √ (class-B) efficiency curve defensible at 5–8 dB back-off?** The class-B ideal η ∝ √(P_RF/P_sat) is a textbook approximation (Cripps). It captures the *direction* (efficiency falls with back-off) but **does not match measured Doherty behaviour**: Doherty PAs are specifically engineered to hold efficiency roughly flat across ~6 dB OBO (the second efficiency peak), whereas the √-law drops monotonically. At the simulator's operating region 0.825–1.65 W (5–8 dB below p_sat = 5.218 W), the √-law gives ξ ≈ 0.14–0.20; a real Ka-band Doherty would sit nearer its ~20% (6 dB OBO) value but *flatter*. Verdict: **stylised-but-conventional for a generic class-B/AB SSPA; pessimistic and wrong-shaped for a Doherty** — which the "Piacibello Ka-band Doherty" anchor invokes. A reviewer will ask why a class-B √-curve is used when the cited hardware is Doherty.

**(b) Are 0.338 W/beam circuit and 0.2 W/satellite baseband realistic?** **No — these are orders of magnitude low for a real phased-array LEO payload and are best understood as stylised per-beam/per-satellite accounting constants inherited from a terrestrial-style EE model (Björnson-type), not real hardware.** Real anchors: a modern flat-panel LEO satellite generates ~500–2000 W total (Starlink V2 Mini, per SpaceX Feb 2023 specs, carries "two massive 52.5-square-meter (565 sq ft) solar arrays" with a ~30 m wingspan and delivers ~4× the capacity of V1.5, up to ~60 Gbps); high-capacity beamforming can draw >800 W across hundreds of RF chains at 1–2 W each; You et al. (IEEE Trans. Commun. 70(8):5543–5557, 2022) model per-component powers of 20 mW (4-bit) / 10 mW (2-bit) phase shifters plus switches, LO, and baseband precoder — and a single beam aggregates thousands of such elements. The simulator's static fraction (~5%; PA share ≈94.8%) **inverts** the usual LEO breakdown, in which digital beamforming/baseband and fixed payload loads are a large, often dominant, share of the power budget. Verdict: **unrealistic as absolute hardware values; internally they make the model PA-dominated by construction.**

**(c) Is "max over served users" aggregation defensible?** It depends entirely on the multiplexing assumption:
- **TDM / single-carrier per beam (DVB-S2X style):** the PA transmits one carrier at (near) constant power and users share in time → per-beam power is a beam-level quantity independent of user count. This **supports max/constant-power** aggregation.
- **FDM / OFDMA with per-user subchannels and per-user power:** total PA output = Σ_u p_u (subject to saturation, PSD limits, PAPR back-off). Here **sum**, not max, is correct — and file 02's "sum-power per beam" is the right model under FDM.
- **MU-MIMO / SDMA precoding:** per-beam output = sum of stream powers.
- **3GPP TS 38.213 / 38.214:** downlink power is defined **per-RE via EPRE** (energy per resource element), which "the UE may assume … is constant across the … bandwidth." There is no "sum-power" instruction — the standard is PSD/per-RE-based, so citing 38.213/38.214 for a Σ_u p_u rule is a **mischaracterisation**; they prescribe neither sum-power nor max-power at the beam level.

**Internal-consistency question.** The simulator computes per-user link powers p_u from an angle recurrence with an *equal bandwidth split* (R_u uses B_w/n_b), then radiates max_u p_u per beam. This is consistent **only under a TDM/constant-power beam reading**, where the single carrier's power is set by the worst-case (highest-required) user and SINR is computed on the full allocated sub-band. Under a genuine FDM equal-split, each user occupies B_w/n_b and carries its own p_u, so beam output should be Σ_u p_u and each user's SINR should derive from that user's share — making "max power + equal split + per-link SINR" internally inconsistent. A reviewer will ask: "Is a beam one TDM carrier (then why an equal *bandwidth* split and per-user powers?) or FDM sub-bands (then why max instead of sum)?" The current combination should be labelled explicitly as a stylised TDM-carrier abstraction.

---

## 3. Centralized multi-beam coordination in LEO

**Beam hopping (illumination optimisation; DVB-S2X Annex E).** DRL/MARL beam-hopping papers report throughput, delay, and energy gains over greedy/genetic baselines: e.g., a MAPPO beam-hopping scheme achieving ~8 Mbit/s throughput gain over a genetic-algorithm baseline (GABH) with real-time adaptation to time-varying traffic; a digital-twin + DRL scheme (BRIDGE) reporting superior energy efficiency, throughput, and fairness. Most assume a centralised scheduler and known/telemetered traffic demand; traffic is typically finite/bursty (queue-driven), not full buffer.

**Load-aware / load-balancing user association in LEO.** Game-theoretic and optimisation approaches: Spatial Adaptive Play (SAP) and Concurrent-SAP for handover-minimising, load-balanced association (arXiv:2607.04829); potential-game handover (Wu et al., IEEE Access 2019); joint power+association MICP reporting ~40% user-rate improvement and a ~58% gain from jointly optimising association and power vs a closest-satellite baseline (arXiv:2511.19745); MAPPO+TarMAC multi-orbit association reaching 92% of greedy-SNR throughput with >4× fewer handovers. The canonical *terrestrial* load-aware baseline is Q. Ye et al., "User Association for Load Balancing in HetNets" (IEEE Trans. Wireless Commun. 2013) — the likely conceptual origin of the "Ye et al." bandwidth-sharing anchor.

**Joint power/beam/bandwidth scheduling & MARL coordination.** Multidimensional DRL resource allocation (spectral + energy efficiency + blocking); GNN-over-bipartite-graph handover (Lee et al., ICT Express 2025); cell-free / CoMP-style LEO coordination. Reported gains are relative to max-SNR/nearest or independent-greedy association.

**Mapping to the arms.**
- **S0/S3 (catalogue of joint edits — reference, top-2 unilateral edits, whole-beam evacuations — scored by a learned complete-configuration predictor + atomic decoder)** corresponds to **centralised set-level / coordination-graph and joint beam-illumination optimisation** families: the decoder over a candidate joint-configuration catalogue is a factored/DCOP-style coordinated selection, and the learned complete-configuration predictor (B_N, E_N, C_served, C_demand) plays the role of a centralised critic / value predictor over joint actions.
- **M123 (independent per-user unweighted masked argmax over Q1+Q2+Q3)** corresponds to **independent learners (IQL-style)** with per-agent value heads.

**Why independent additive argmax fails to realise joint gains.** This is the multi-agent credit-assignment problem: with a shared/global reward, independent per-agent argmax cannot see its own contribution and suffers herding/collision on shared resources and non-additive set-value functions. COMA (Foerster et al., AAAI 2018) and difference rewards (Wolpert & Tumer) address this via a counterfactual baseline; QMIX (Rashid et al.) / VDN (Sunehag et al.) via monotonic value factorisation; Shapley-value counterfactual credit assignment (Li et al.) explicitly splits joint value using cooperative-game Shapley shares. The Track B Ψ/2 pairwise-interaction split (Q3* = E[e_i + Ψ/2 | I_t]/κ_B) is a Shapley-style two-player surplus split — a recognised device to inject non-additive joint value into an otherwise additive head. The LICA paper (NeurIPS 2020) shows a 1-step game with multiple optima defeats naive difference-reward/independent methods, supporting the design's premise that additive argmax under-realises coordinated gains. These families use both full-buffer and finite-demand traffic; the coordination gains are consistently reported *relative to independent/greedy baselines*, which is exactly the M123-vs-S0/S3 contrast.

---

## 4. Methodology: is a constructed-regime study accepted practice?

**Yes — the design pattern (declare the regime a priori, run every grid point, select by a pre-declared rule, disclose everything, keep the negative primary result) is aligned with accepted rigor practices, provided its claims are conditioned on the pre-declared regime.**

**Pre-registration / registered reports in ML.** NeurIPS ran Pre-registration in Machine Learning workshops (2020, PMLR 148; 2021, PMLR 181), explicitly to reward sound protocol and *negative* results over "beating SOTA." The Center for Open Science notes that pre-registration's central aim is to **distinguish confirmatory from exploratory** analyses and preserve inferential validity, and that deviations do not invalidate but must be disclosed. Expected reviewer language: "conditional on the pre-declared regime," "exploratory vs confirmatory," "no claims of external validity," "all pre-specified conditions reported."

**RL evaluation rigor.** Henderson et al., "Deep RL That Matters" (AAAI 2018): non-determinism, seeds, hyperparameters, and codebase differences make point-estimate comparisons unreliable. Agarwal et al., "Deep RL at the Edge of the Statistical Precipice" (NeurIPS 2021): report interval estimates, performance profiles, and interquartile mean rather than point estimates (rliable). These support the design's world-cluster paired 95% CI lower bound > 0 threshold, fixed training endpoint, and no best-checkpoint selection.

**Multiverse / specification-curve analysis** (Steegen, Tuerlinckx, Gelman & Vanpaemel, Perspectives on Psychological Science 2016; Simonsohn, Simmons & Nelson, Nature Human Behaviour 4:1208–1214, 2020) is the accepted way to "run every grid point and report all," and the garden-of-forking-paths (Gelman & Loken 2013) / researcher-degrees-of-freedom (Simmons et al. 2011) literature is the vocabulary reviewers use to flag outcome-driven flexibility. Networking artifact evaluation (SIGCOMM/IMC/NSDI/CoNEXT badging) and 3GPP calibration campaigns are the reproducibility analogues; wireless-simulation-credibility work (Kurkowski; Pawlikowski; Andel & Yasinsac) warns against uncalibrated, non-reproducible simulation.

**Assessment of the probe thresholds and first-qualifying-point rule.**
- The four regime-map probes (J₁/η_ref − 1 ≥ 5%; (J₁−U₁)/η_ref ≥ 1%; non-additive interaction surplus ≥ 0.5%; ≥3/4 worlds positive + demand guard) plus an oracle-marginal pre-screen are **conservative and interpretable**: they are declared before training, and a point that fails the oracle-marginal screen is reported but not trained. This is good practice.
- **First-qualifying-point-in-fixed-order (G1→G2→G3)** is defensible *only if the order is justified independently of coordination headroom.* If the order was chosen after observing the direction in which headroom grows, it is a garden-of-forking-paths / HARKing risk.

**Elements a reviewer would call outcome-driven, with the defusing sentence for each (each change makes the study more conservative or more interpretable):**
1. **G1→G2→G3 ordering.** Risk: order chosen knowing headroom grows toward full buffer. Defuse: *"The selection order G1→G2→G3 is fixed a priori by decreasing demand stringency (most-constrained first) for reasons independent of any arm's expected advantage; it was frozen before any oracle or training result was observed."*
2. **λ_B/κ_B from a calibration panel that may overlap training.** Risk: information leakage. Defuse: *"λ_B and κ_B are computed on a pre-declared calibration panel that is disjoint from the training and test splits; both constants are frozen before training and never re-tuned."*
3. **Multiple thresholds (four probes).** Risk: multiple comparisons / selective declaration. Defuse: *"The four probes form an a-priori conjunction (all must pass); they gate reporting, not selection, and no threshold was adjusted after seeing results."*
4. **"Each of C1, C2, C3 positive" success criterion vs the coordinator-vs-additive claim.** Risk: the per-head criterion is a different hypothesis from the coordinator-beats-additive claim. Defuse: *"The confirmatory hypothesis is the pre-declared coordinator-vs-M12 comparison; the per-head (C1/C2/C3-positive) DROP diagnostics are exploratory and reported as such, with no confirmatory claim attached."*
5. **Hardware numbers not increased to force a positive result.** Defuse (keep file-01 warning verbatim): *"Static hardware constants are stylised accounting values, not measured hardware, frozen a priori, and never adjusted to change the sign of any result."*
6. **Retaining the negative regime-A C3 result.** This is a strength; keep the sentence: *"Regime A's negative C3 result remains in the paper; the TEST split is opened once, after freezing."*

---

## (A) Parameter realism table

| Parameter | Simulator value | Literature range / anchor | Verdict |
|---|---|---|---|
| Per-user demand d_u | 200 / 50 / 10 Mbit/s (+∞) | Sustained busy-hour ~2.5–25 Mbps (Osoro/Oughton 24.94 Mbps @0.1/km², 2.49 Mbps @1/km²; Cartesian ~20.8 Mbps); speed-test medians ~104 Mbps (Ookla), 285–304 Mbps (Laniewski 2024) | G3 realistic; G2 high-but-conventional; G1 extreme (full-buffer-like) |
| Demand distribution / tail | single value per point | Heavy-tailed, video-dominated; on-demand 7.9 GB/day/sub (Sandvine 2024); heavy-hitter minority | Stylised (no distribution modelled) |
| Interval Δt = 30.08 s | 47×0.640 s | Decision-epoch length is a design choice; TTT/D2 from TS 38.331 | Realistic (conventional) |
| Per-beam BW 166.667 MHz (500/FRF 3) | 166.667 MHz | 250–500 MHz Ka user channels, FRF 3–4 typical | Realistic |
| Equal bandwidth split | R_u = (B_w/n_b)·log2(1+SINR) | Proportional/load-aware sharing (Q. Ye et al. 2013) | Stylised-but-conventional |
| No admission/occupancy cap | none | Real systems apply admission control | Stylised (optimistic) |
| p⁰ = 0.825 W (p_max/2) | 0.825 W | Ka SSPA per-carrier 1–10 W (Piacibello) | Realistic order of magnitude |
| p_max = 1.65 W | 1.65 W | within 1–10 W Ka downlink range | Realistic |
| p_sat = 5.218 W | 5.218 W | Piacibello 5 W / Colantonio 10 W Ka GaN MMIC | Realistic |
| ξ_max = 0.35 | 0.35 | Colantonio 35% Ka GaN; Piacibello 23–31% sat, ~20% @6 dB OBO | Realistic as peak; see curve caveat |
| √ (class-B) efficiency curve | η ∝ √(P/P_sat) | Cripps class-B ideal; Doherty flat over 6 dB OBO | Stylised; wrong shape for Doherty |
| Operating back-off (5–8 dB) | ξ≈0.14–0.20 @0.825–1.65 W | 3–6 dB OBO standard for APSK/OFDM | Operating point plausible; efficiency pessimistic/mis-shaped |
| Circuit 0.338 W/beam | 0.338 W | Real DBF/RF chains 1–2 W each × many elements; payload 500–2000 W total | Unrealistic (orders low); stylised constant |
| Baseband 0.200 W/satellite | 0.200 W | Onboard DBF/baseband is a large share of kW-class bus | Unrealistic (orders low); stylised constant |
| Max-vs-sum aggregation | max_u p_u | TDM→beam-level (max ok); FDM→Σp_u; MU-MIMO→Σ stream | Defensible only under TDM reading |
| No DTX/micro-sleep | carrier active whole interval | DTX claims 25–40% savings (file 02, unverified) | Conservative (no savings claimed) |
| No cross-slot queueing | demand expires at interval end | Real buffers queue across slots | Stylised (conservative for demand) |
| 100 users / 4 sats / 200×90 km | as stated | MODQN Table I; user density ~0.0056/km² | Stylised scenario (low density) |
| Service guard: 95% users ≥95% demand | as stated | 5th-pct user-experienced rate (M.2514) | Reasonable, interpretable |

## (B) Unrealistic / outcome-driven elements and the defusing pre-registration sentence

1. **G1 = 200 Mbit/s sustained per user** — Unrealistic as demand. Defuse: *"G1 is an intentionally full-buffer-like upper stressor, not a field-calibrated demand; it is labelled a control-adjacent extreme, not a realistic subscriber load."*
2. **Static hardware constants (0.338 W/beam, 0.2 W/sat) and √-efficiency** — Unrealistic hardware. Defuse: *"All PA/circuit/baseband constants are stylised accounting values inherited from the MODQN base model, frozen a priori, explicitly not claimed as real hardware, and never adjusted to change any result's sign."*
3. **max-over-users per-beam power with equal bandwidth split** — Internally inconsistent unless TDM. Defuse: *"A beam is modelled as a single TDM/constant-power carrier whose power is set by the most-demanding served user; the equal-bandwidth term is a rate-sharing abstraction, and no FDM per-subchannel power claim is made."*
4. **G1→G2→G3 first-qualifying-point rule** — potential HARKing. Defuse: §4 item 1.
5. **λ_B/κ_B calibration-panel overlap** — leakage risk. Defuse: §4 item 2.
6. **"C1,C2,C3 each positive" vs coordinator-vs-additive** — hypothesis mismatch. Defuse: §4 item 4.
7. **File-02 "sum-power per beam citing TS 38.213/38.214"** — mischaracterises the standard. Defuse: *"TS 38.213/38.214 define a per-RE constant EPRE, not a beam sum-power rule; the sum-power model is our modelling choice under an FDM assumption, not a standards requirement."*

## (C) Citations that could not be verified or do not support the claim as used

- **"Del Re et al., IEEE Aerospace 2020" (per-beam DBF/RF-chain 2.0–4.5 W): NOT FOUND / appears to be a misattribution.** Enrico Del Re is a genuine satellite-comms author but retired in 2017; no 2020 IEEE Aerospace paper on LEO payload DBF power with 2–4.5 W per-beam figures was located. **Remove or re-source; do not call these real hardware values** (file 01 already warns of this).
- **"ESA LEO payload survey" (per-beam static 2–4.5 W): unverified.** No identifiable ESA survey with these figures was found. Treat as unsourced.
- **TR 38.821 §6.1 and ITU-R M.2514 "demand ranges 50–200 Mbit" (file 02): NOT SUPPORTED.** TR 38.821 §6.1 baseline is full buffer, 10 UEs/beam (FTP model 3 optional); M.2514 defines user-experienced rate as the 5th-percentile of the throughput CDF and inherits 100/50 Mbit/s DL/UL targets from M.2410. Neither contains per-user Mbit demand volumes; the file-02 justification is invalid.
- **TS 38.213/38.214 "sum-power per beam": mischaracterised.** These define a per-RE EPRE assumed constant across bandwidth; they neither prescribe Σ_u p_u nor max-power at beam level.
- **"Zhu et al." LEO traffic/queue model: NOT uniquely identifiable.** The finite-buffer/Poisson-arrival motivation is standard and defensible, but no single canonical "Zhu et al." paper was confirmed (closest candidates involve beam-hopping/traffic-demand contexts, not a clean arrival-process paper). Request exact year/venue from the authors.
- **"Ye et al." load-aware bandwidth-sharing: concept traces to Q. Ye et al. (IEEE TWC 2013, terrestrial HetNet), not a confirmed LEO-specific Ye paper.** Clarify which Ye (Jianhua vs Neng vs Qiaoyang).
- **"You et al." RF-chain power: CONFIRMED as You et al., IEEE Trans. Commun. 70(8):5543–5557, 2022** ("Massive MIMO Hybrid Precoding for LEO … With Twin-Resolution Phase Shifters and Nonlinear Power Amplifiers," DOI 10.1109/TCOMM.2022.3182757), giving 20 mW (4-bit) / 10 mW (2-bit) phase-shifter component powers — **not** whole-watt-per-RF-chain values; any W-per-chain figure is a derivation. The 2020 JSAC You paper ("Massive MIMO Transmission for LEO Satellite Communications," DOI 10.1109/JSAC.2020.3000803) does not contain component power figures.
- **VERIFIED anchors:** Colantonio & Giofrè (EuMIC 2020, 10 W/35% Ka GaN, verbatim in title); Piacibello et al. (IEEE MWCL 32(8), 2022, 5 W, ~20% PAE at 6 dB OBO); Björnson et al. (IEEE TWC 2015; arXiv:1403.4851) circuit-power model; Foerster COMA (AAAI 2018); Agarwal et al. (NeurIPS 2021); Henderson et al. (AAAI 2018); Steegen et al. (2016); Simonsohn et al. (2020); ITU-R M.2514 (2022); 3GPP TR 38.821 (Rel-16); Osoro & Oughton (IEEE Access 2021); Laniewski et al. (TMA 2024); Sandvine GIPR 2024.

## (D) Verified facts vs inferences; where literature is silent

**Verified (with source):** Ookla Starlink medians (53.95 Mbps Q3 2022 → 104.71 Mbps Q1 2025; >100 in all states but Alaska 2H2025; 17.4% meeting FCC 100/20 in Q1 2025); Laniewski et al. mobile medians 284.68/303.85 Mbps; Osoro/Oughton busy-hour per-user 24.94 Mbps @0.1 users/km² and 2.49 Mbps @1 user/km²; Sandvine on-demand streaming 7.9 GB/sub/day; TR 38.821 full-buffer/10-UE baseline; M.2514 5th-pct user-experienced-rate definition; Piacibello 5 W / ~20% at 6 dB OBO; Colantonio 10 W/35%; You et al. 2022 phase-shifter powers (20/10 mW); Starlink V2 Mini two 52.5 m² arrays and ~500–2000 W flat-panel LEO bus class; TS 38.214 constant-EPRE downlink power; COMA/QMIX/VDN/Shapley credit-assignment results; RL-evaluation and multiverse methodology papers.

**Inferences (mine):** the per-user Shannon share (~250–290 Mbit/s at 2 users/beam) is my computation from the stated B_w and SINR; the "G1 behaves full-buffer-like / G2,G3 demand-limited" mapping follows from that computation; the identification of ξ_max = 0.35 with Colantonio is a plausible provenance inference, not a stated fact in the design files.

**Literature silent / non-public:** Exact Starlink/Kuiper/OneWeb **per-beam RF power, per-beam DBF power, and onboard baseband power are not public** (SpaceX explicitly withholds V3 array output and battery capacity). The specific values 5.218 W / 0.35 / 0.338 W / 0.200 W therefore cannot be confirmed against real hardware; they are best treated as stylised constants (most plausibly inherited from the MODQN base paper and terrestrial Björnson-type EE models). Where these numbers are not public, this report does not guess real values.

## (E) No arm/regime recommendation
This report makes no recommendation of any grid point or regime on the basis of which arm (C1/C2/C3, additive, or coordinator) would benefit. All verdicts concern realism, literature anchoring, internal consistency, and methodological acceptability only.

---

## Recommendations (methodological / realism, staged)

**Before freezing (mandatory):**
1. **Resolve the demand units.** Adopt a single convention — "sustained per-terminal offered demand over the 30.08 s interval, in Mbit/s, with the per-interval Gbit equivalent stated alongside" — and delete the file-02 Mbit/slot reading (or convert it). *Threshold to change this recommendation:* none; the file-01/file-02 conflict is disqualifying if left unresolved.
2. **Re-label G1 as a full-buffer-like control stressor**, not a demand scenario, since at ~2 users/beam it sits at/above the per-user Shannon share (~250–290 Mbps). Keep it only if explicitly framed as an extreme. *Threshold:* if a defensible source for ≥200 Mbps *sustained* per-subscriber demand emerges, re-classify; none exists in the current literature.
3. **Remove or re-source the "Del Re et al. 2020" and "ESA LEO payload survey" citations** and the "TR 38.821 §6.1 / M.2514 demand range" and "TS 38.213/38.214 sum-power" claims; replace with the verified anchors (Björnson 2015 for circuit power; You et al. 2022 for component power; EPRE definition for downlink power semantics).
4. **State the beam multiplexing model explicitly** (TDM constant-carrier) so that "max power + equal bandwidth split + per-link SINR" is internally consistent; otherwise switch to Σ_u p_u under FDM.

**Before training:**
5. **Add the six defusing sentences** in §4/(B) verbatim to the pre-registration (ordering justification, calibration-panel disjointness, probe conjunction, confirmatory-vs-exploratory split, hardware-constant freeze, negative-result retention).
6. **Adopt Agarwal-style interval reporting** (IQM + stratified bootstrap CIs, performance profiles) for all arms relative to M0, consistent with the existing paired-CI threshold.

**In the paper:**
7. **Frame the whole grid as a pre-registered multiverse / specification curve** (Steegen 2016; Simonsohn 2020): report every grid point and arm, present the negative regime-A C3 result, and state all claims as "conditional on the pre-declared regime, with no claim of external validity." *Threshold that would change this:* none — this framing is the accepted way to run-every-point-and-report-all and is the study's main methodological safeguard.

## Caveats
- Several key hardware numbers (per-beam/baseband power for real constellations) are **not public**; realism verdicts on 5.218 W / 0.35 / 0.338 W / 0.200 W rest on comparison with published academic component/PA figures and total-bus-power figures, not on operator disclosures.
- Speed-test figures (Ookla, Laniewski) and some payload figures were partly corroborated via secondary aggregators; the underlying primary sources (Ookla Speedtest Intelligence, SpaceX FCC filings) are quoted where the enricher confirmed verbatim text but were not all independently fetched in full.
- "Zhu et al." and "Ye et al." remain unresolved to a single primary source; the conceptual claims they support are standard, but the exact citations should be confirmed with the authors.
- This report deliberately abstains from any statement about which regime or grid point would advantage any arm; readers seeking such guidance will not find it here by design.