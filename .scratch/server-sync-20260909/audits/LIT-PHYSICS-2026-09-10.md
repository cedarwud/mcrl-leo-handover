Report written to `/home/sat/mcrl-v025-probe-ws/LIT-PHYSICS-CONVENTIONS-2026-09-10.md`. Full text:

---

# LIT-PHYSICS-CONVENTIONS-2026-09-10

`DIAGNOSTIC_NOT_CLAIM` — reading task, no code, no runs. Corpus: `/home/sat/litref-20260910/` (12 PDFs).

---

## Three one-line answers

**Q1 — Fade margin.** Not defensible: no paper in this corpus provisions power to a nominal (unfaded) threshold, every one of them puts the fade *inside* the quantity that must clear the threshold, and applying a fade quantile downstream of the power solve appears nowhere — the construction is an error of ordering, not a recognised design, and the 1.7 dB implementation margin is a different kind of quantity that cannot stand in for a fade margin.

**Q2 — Metric conventions.** Pooled energy efficiency is a real convention with, in the corpus's own words, "the strongest physical interpretation," but reporting *only* pooled is against convention — the two papers that care about heterogeneity report the summed-per-user form alongside it and criticise pooled for hiding per-link allocation; delivered capacity above the contracted rate is explicitly *not* credited (`min(capacity, demand)`); a per-chain fixed power cost is standard; a square-root amplifier law appears nowhere in this corpus.

**Q3 — Prior art.** Very little would be left as new: joint handover + occupancy-coupled power control under a pooled-EE objective in Ka-band multi-beam LEO is the explicit subject of Chen et al. 2024, occupancy-dependent rate sharing was settled by Ye et al. 2013 (and proved optimal), and the only element genuinely absent from this corpus is the discrete EN 302 307-1 mode table — which is standard industrial practice, not a research contribution.

---

## What I read, and what I used

**Read in full** (all seven required, plus two more that bear directly on the questions):

| Paper | Band / setting | Why it bears |
|---|---|---|
| Kim, Roberts, Iannucci & Andrews, GLOBECOM 2021 (`2023_09`) | S-band, 19-beam LEO | Outage-probability formalism; explicit lumped margin |
| Yu & Kim, APCC 2022 (`2022_11`) | S-band, earth-fixed beam | SINR computed *with* the shadow-fading realisation; serviceability threshold |
| Bian & Liu, *Sensors* 2022 (`2022_04`) | **Ka-band 25 GHz LEO** | The corpus's only explicit power-vs-outage-target design; EE = delivered bits / joules |
| Tervo, Tölli, Juntti & Tran, *IEEE TSP* 2017 (`2017_07`) | Terrestrial multicell MISO | NetEE vs WsumEE; PA-efficiency and per-chain power model |
| Chen, Shen, Feng, Yang & Wu, VTC-Spring 2024 (`2024_09`) | **Ka-band 28 GHz, 165 LEOs × 37 beams** | Joint handover + beam switching + power control, pooled EE — closest prior art |
| Abudureheman et al., *IEEE IoT-J* 2026 (`2026_01`) | Ka-band LEO, BH + freq. reuse | SFR, per-user rate floor, proportional-fair utility |
| Cai, Wang, Zhao, Xu & Wang, *IEEE IoT-J* 2025 (`2025_07`) | LEO uplink BH | GEE vs WSEE stated head-on; "shadowing margin" as a budget term |

**Also read and used** (from the skim of the rest of the directory):

- Ye, Rong, Chen, Shalash, Caramanis & Andrews, *IEEE TWC* 2013 (`2013_06`) — **used**. The origin of `R = c/K` (rate divided by beam occupancy) and the proof that equal resource sharing is optimal. Directly relevant to Q3's "occupancy-dependent" claim.
- Li et al., *IEEE TAES* 2026 (`2025_11`, distributed BH) — **used**. Contains the corpus's only explicit statement on crediting delivered capacity vs demand, and reports satisfaction rate separately from throughput.
- Zhang, Fu & Yang, *IEEE TVT* 2026 (`2026_03`, dual-agent handover + power) — **used**. Joint discrete-handover / continuous-power DRL; reports timed-out users separately from connectivity.
- Chen (CDRL RIS, `2025_07_CDRL`) — **used lightly**, for the power-consumption model only (per-RF-chain fixed cost, pooled EE ratio). Terrestrial RIS, otherwise off-topic.
- Holder, Jaques & Mesbahi, AAAI 2025 (`2025_02`, REDA) — **used lightly**, for the handover-switching-penalty and battery-state formulation. No physical layer at all; contributes nothing to Q1 or Q2.

---

## Q1 — Fade margin: is provisioning to the nominal threshold defensible?

### 1.1 What the field actually does

**No paper in this corpus provisions transmit power against an unfaded ("nominal", "clear-sky", "mean") SNR.** I searched the full text of all twelve for `nominal`, `clear sky`, `clear-sky`, `derate`, `average SNR … threshold` and `mean SNR`; there are zero hits in the relevant sense. The corpus splits into exactly two conventions, and the project matches neither.

**Convention A — evaluate the threshold on the faded quantity, and size power against that.**

- Chen et al. 2024 (`2024_09`), §II-A eq. (1): total path loss is `L = L_fs + L_g + L_sc + L_sf`, i.e. free space **plus** atmospheric absorption **plus** tropospheric scintillation **plus** log-normal shadow fading. The channel gain `H = 10^(−L/10)` in eq. (4) therefore *contains the fade realisation*, and the SINR `γ_n,m,k` in eq. (4) is a faded SINR. The power-control law, §IV-B eq. (30), then reads: the per-beam power step is forced positive — power is increased — `if ∃k ∈ K : γ_n,m,k < γ_thr`, with `γ_thr = 10 dB` (Table I). Power is driven up until the *realised, faded* SINR clears the threshold. The paper states the purpose in one sentence: "This approach avoids the situation in which there is insufficient beam power to provide acceptable service quality" (§IV-B, after eq. (30)).
- Yu & Kim 2022 (`2022_11`), §II eq. (1): `PL = FSPL(d,f_c) + SF + CL(α,f_c)` where `SF ∼ N(0, σ²_SF)` is drawn per realisation (σ_SF up to 11.52 dB NLOS, Table I). The service test in §III is applied to that realised SINR: "As stated in the specification of [3GPP TS 36.300], the received SINR should be over the −8 dB. Then, when f_c is 2 GHz, an elevation angle over 50° is the serviceable signal quality."
- Zhang, Fu & Yang 2026 (`2026_03`), §II-B eqs. (3)–(7): channel gain includes LoS/NLoS probability-weighted excess loss, rain attenuation (ITU-R) and cloud attenuation (ITU-R P.676). Constraint (12c) `h^m_n,i(t) ≥ h_min` is applied to *that* gain — with `h_min = 2.2×10⁻⁸` (§IV) — as an admission condition on the faded channel.

**Convention B — provision against an outage probability, i.e. a threshold evaluated at a percentile.**

- Bian & Liu 2022 (`2022_04`) is the corpus's Ka-band LEO reference (25 GHz, EIRP 40 dBW, G/T 20 dB/K, §2.1) and it is unambiguous. §2.2.1 eq. (21) and §2.2.2 eq. (25): the EE-maximising power (or power sequence) is chosen **subject to `e_L ≤ e_0`**, where §3.2 defines `e_0` as "the maximum outage probability allowed by the communication system." The whole of §3.1 exists to compute that outage probability accurately (the NI-FFT method), precisely because approximating it "will mean that either the system cannot meet the reliability requirements or the energy efficiency of the system is decreased" (§3.1). And §4.2 reports the empirical fact that the constraint binds: "when the energy efficiency reaches the maximum, the outage probability satisfies `e_L = e_0`." Power is sized *at the outage percentile*, and the optimum sits exactly on it.
- Kim et al. (`2023_09`) supplies the analytic machinery for the same idea: §IV eq. (30), `P(SNR ≤ γ) = F̃_Y(γ · SNR̄⁻¹)`, computed from the Squared-Shadowed-Rician CDF. The instantaneous SNR is `SNR = SNR̄ · |h|²` (eq. (14)); the mean multiplier is `E[|h|²] = 2b + Ω` (Corollary 2.1). Outage is defined against the *distribution*, never against `SNR̄` alone.

**Convention C — carry the fade as a deterministic dB budget in the link equation.** This is the third and most common industrial form, and it appears twice:

- Kim et al. (`2023_09`), §V: "In addition to free space path loss, **5.3 dB of path loss including scintillation loss, atmospheric loss, and shadowing margin is considered.**" This is a fixed budget added *before* any performance is computed.
- Cai et al. 2025 (`2025_07`), §II-A eq. (1): the channel gain divides by `L_loss`, and the text defines it as "sum of other losses (e.g., atmospheric path loss, **shadowing margin**, scintillation loss)."

Note what Convention C shows: **the field budgets a shadowing margin as a term in the link equation, alongside — and distinct from — deterministic hardware and atmospheric losses.** It is a subtraction applied *before* the power solve, not after it.

### 1.2 What availability / outage probability is conventional for Ka-band LEO, and what dB does it buy?

**This corpus does not answer the availability question in the ITU form, and I will not generalise past it.** No paper states a percentage availability (99.5 %, 99.9 %, etc.), and no paper states a Ka-band fade-margin figure in dB tied to one. What the corpus does give:

- **Bian & Liu (`2022_04`), Ka-band 25 GHz LEO**: `e_0` is swept over `10⁻⁶ … 10⁻¹` (Figs. 6, 13), with the headline results reported at `e_0 = 10⁻⁵` and `10⁻⁶`. This is a *post-HARQ, per-packet* residual outage after up to `L` incremental-redundancy rounds — **not** a link-availability figure and not directly comparable to a single-shot fade margin. The paper's Fig. 13 makes the distinction concrete: at `e_0 = 10⁻⁵`, "the scheme without HARQ cannot satisfy the requirements of reliability during the whole communication window," and even IR-HARQ-EP and IR-HARQ-VPA "cannot satisfy the requirements of reliability in the early stages" at low elevation. The reliability is bought with retransmission diversity, not with a static margin.
- **Kim et al. (`2023_09`)**: 5.3 dB, lumped, at 2 GHz. This is the only explicit margin number in the corpus. It is not Ka-band.
- **Chen et al. (`2024_09`)**, Ka-band 28 GHz: `γ_thr = 10 dB` on the faded SINR, with no separate margin — the margin is implicit in the closed loop.

The corpus points at where the answer lives without containing it. Bian & Liu cite ITU-R P.676 (gases), P.840 (clouds/fog), P.838 (rain specific attenuation) and P.618 (earth-space design) as refs [25]–[28] — P.618 is the recommendation that maps an availability percentage to a rain-fade depth — and cite Ekerete, Awoseyila & Evans, "Robust adaptive margin for ACM in satellite links at EHF bands," *IEEE Commun. Lett.* 2020 (ref [4]) for the margin question directly. **Neither is in this directory.** If the availability convention needs to be pinned to a number, those are the sources, and they must be read rather than inferred.

### 1.3 Does the project's construction appear anywhere?

**No. Plainly: applying a fade quantile at mode selection while provisioning power at the nominal value appears nowhere in this corpus, and I found nothing structurally similar.**

Let me state the construction as given and then say what it does. Power `P` is solved so that `SNR_nom(P) = threshold(m_req)` exactly, where `m_req` is the mode whose spectral efficiency meets the beam's requirement `n × 50 Mbit/s / 166.67 MHz`. Then the transmitted mode `m_tx` is selected from `SNR_nom × 0.51`.

`10·log₁₀(0.51) = −2.92 dB`. So `m_tx` is selected at an SNR 2.92 dB below the SNR the power solve was sized to deliver. In EN 302 307-1 the Es/N₀ thresholds are spaced roughly 0.5–1.5 dB apart over the spectral-efficiency range this system operates in (`n × 0.30 bit/s/Hz`, so ≈1.2 bit/s/Hz at n=4 up to ≈3.0 bit/s/Hz at n=10) — *this spacing is from the standard, not from the corpus*. A 2.92 dB shortfall is therefore typically **two to five MODCOD steps**.

The consequence, stated as a logical implication of the construction rather than as an audit finding: **`m_tx` is systematically below `m_req`, so the beam's users systematically fail to receive their contracted 50 Mbit/s, while the satellite pays the power bill sized for `m_req`.** Both the numerator and the denominator of an energy-efficiency ratio move the wrong way. Under-delivery is not signalled as an outage — it is silent degradation, and if the metric is pooled bits over pooled joules it shows up only as a level shift, which is exactly the failure mode a pooled metric is bad at surfacing (see Q2).

There is a second reading of the sentence, in which the power solve and the mode selection are fixed-pointed so that the mode whose threshold is matched *is* the mode transmitted at the tenth percentile. **That reading is Convention B, and it is defensible** — it is exactly "provision at an outage percentile," matching Bian & Liu's `e_L ≤ e_0` structure with `e_0 ≈ 0.10`. Whether the project is in this reading or the first is a question of the *ordering* of two operations, and the description says the derate happens "after" the power solve, which puts it in the first. **If so, this is a one-line ordering fix, not a redesign.** I would not describe 90 % availability as generous for Ka-band, but it is a defensible research-model choice and it is at least the right *shape*.

One further note on the 10th percentile itself: 0.51 as a p10 multiplier at 30° elevation is a **−2.92 dB** fade depth. Kim et al.'s Fig. 3(b) and Fig. 5, under "average" Shadowed-Rician shadowing, show a distribution in which "extremely poor SINR levels — on the order of −20 dB or more — are not unlikely" and "very deep fades that are not practical for communication" occur even near cell centre (§V). A −2.9 dB tenth percentile is a substantially milder channel than the corpus's own average-shadowing case. That is a modelling choice, and it may be right for the project's environment, but it should be stated as a choice rather than absorbed.

### 1.4 Is 1.7 dB implementation margin the same kind of quantity as a fade margin?

**No. Different kind, and it cannot substitute.**

The corpus does not discuss receiver implementation margin — I searched all twelve for `implementation loss`, `implementation margin`, `1.7 dB`, `quasi-error`, `QEF` and found nothing. So I answer from the structure the corpus does exhibit, and say so.

- An **implementation margin** is a deterministic, time-invariant hardware penalty: the gap between the demodulator's ideal Es/N₀ threshold and what the real receiver needs (phase noise, quantisation, synchronisation loss, filter ripple). It is *always* present, in every symbol. Folding it into the threshold table — as the project does — is the correct treatment, and it is the treatment EN 302 307-1 users conventionally apply. It has already been spent.
- A **fade margin** is a stochastic reserve: extra power held back so the link survives a *time-varying* depletion that is absent most of the time and deep occasionally. It is sized by choosing an exceedance probability. It is spent only during fades.

They cannot substitute because they are drawn against different budgets. Folding 1.7 dB into the threshold correctly raises the bar the *unfaded* link must clear; it does nothing about the 2.92 dB the fade removes from that same link. The corpus's own bookkeeping demonstrates the separation: Cai et al. eq. (1) lists "shadowing margin" as one term in `L_loss` alongside atmospheric and scintillation losses — a fade reserve budgeted *in the link equation as its own line item*, not merged into the modem threshold. Kim et al.'s 5.3 dB is likewise a propagation budget, added to path loss, not to the decoding threshold.

### 1.5 Verdict on Q1

**Error, not an unusual design.** Evidence, in order of weight:

1. Chen et al. 2024 (`2024_09`) §II-A eq. (1) + §IV-B eq. (30) — Ka-band LEO, the closest system in the corpus, drives power up until the *faded* SINR clears threshold. The project drives power up until the *unfaded* SINR clears threshold and then discovers the fade afterwards.
2. Bian & Liu 2022 (`2022_04`) §2.2.2 eq. (25) + §4.2 — Ka-band LEO, power is constrained by `e_L ≤ e_0` and the optimum binds at `e_L = e_0`. Provisioning at the nominal value is the `e_0 ≈ 0.5`-ish corner of that sweep, which the paper never operates in.
3. Kim et al. (`2023_09`) §IV eq. (30), §V — outage is defined against the fading distribution and a 5.3 dB budget is charged *before* performance is computed.
4. Zero occurrences of nominal-threshold provisioning across twelve papers.

The failure is one of *ordering*, and it is repairable by moving the tenth-percentile multiplier upstream of the power solve. That change converts the construction into Convention B at ~90 % availability, which is defensible.

---

## Q2 — Metric conventions

### 2.1 Pooled EE vs per-user EE

**Pooled is a genuine convention. Reporting only pooled is not.** Both forms appear, the corpus names them, and the two papers that examine the difference conclude that pooled alone is insufficient.

Pooled (summed bits over summed joules) — four instances:

- Tervo et al. 2017 (`2017_07`) §II-C eq. (10a), "network energy efficiency maximization" (NetEEmax): `Σ_b R̃_b(w) / (g(w) + P_RD Σ_b δ(r_b))`.
- Chen et al. 2024 (`2024_09`) §II-B eq. (13): `E_eff(t) = R_tot(t) / Σ_n Σ_m P_n,m(t)`. Note the denominator is **transmit power only** — no circuit, no chain, no fixed satellite cost. This matters: it is not the same pooled quantity as the project's.
- CDRL (`2025_07_CDRL`) §3.2 eq. (3.12a): `Σ_k R_k / P_Tot`.
- Bian & Liu (`2022_04`) §2.2 eq. (11): `η_EE = K / E`, correctly-decoded bits over consumed joules — degenerate (single link), but the same form.

Per-user / per-cell summed — three instances:

- Tervo et al. §II-C eq. (11a), "weighted sum energy efficiency" (WsumEEmax): `Σ_b ω_b · R̃_b(w) / (g_b(w̃_b) + P_RD δ(R̃_b(w)))` — a sum of *ratios*, not a ratio of sums.
- Cai et al. 2025 (`2025_07`) §II-C eq. (6)–(7): per-terminal `E_j,l,t = C_j,l,t / (P_t^l + P_sys)`, then `E_total^t = Σ λ_l E_j,l,t`.
- Chen et al. 2024 §IV-B eq. (29): a per-beam EE `E_n,m^eff = Σ_k R_n,m,k / P_n,m` used *internally* to drive the power-control loop, with the pooled figure reported.

**What the papers say about the difference — explicitly:**

- Cai et al. §I-A, in full: "Although GEE can represent the efficiency of the entire network with the strongest physical interpretation, **it limits the tuning resources of individual links based on their EES.**" The paper's entire contribution is built on this: it adopts WSEE precisely because GEE cannot express that some terminals (battery-powered IoT) need EE more than others (grid-powered fixed sites). It then measures the cost of using the wrong one: JPFA "can significantly improve the WSEE by 34 % for the uplink LEO satellite system when compared with the case of ignoring the EES scheme" (§IV-D), and its MaxGEE benchmark [23] "neglects the differences among terminals in the optimization process, resulting in WSEE not being optimized" (§IV-D).
- Tervo et al. §VII, Fig. 7, quantifies the trade in the other direction: "when equal weights are used for all the BSs, the **WsumEEmax clearly balances the energy efficiencies and rates between the cells with only small performance degradation in the network EE.** As far as fair resource allocation is concerned, the WsumEEmax design criterion proves to be a good choice." Fig. 7 plots per-BS EE and per-BS sum rate side by side for both objectives — the paper does not ask the reader to take the pooled number on faith.

**Reading for the project.** Pooled EE is defensible as *a* headline. Reporting it *alone* is against the practice of the two corpus papers that studied the question, and it is the metric least able to surface the Q1 defect: systematic under-delivery of 2–5 MODCOD steps across all users appears in a pooled ratio as a smooth level shift with no structural signature. Both Tervo and Cai report the disaggregated form alongside; that is the convention worth matching.

### 2.2 When a discrete mode delivers more than the contracted rate, is the surplus credited?

**No. The one explicit statement in the corpus says credit `min(capacity, demand)`, and says why.**

Li et al. 2026 (`2025_11`), §III-B, verbatim:

> "**To avoid overestimating throughput, we account for both capacity and demand** by defining the realized per-cell RT throughput as `λ_j^rt = Σ_{t=1}^{N_t} min(C_j,t, D_j,t)`, where `C_j,t` is the beam capacity (from the Shannon's formula under the current BHP/SINR) and `D_j,t` is the requested RT demand of cell `j` on slot `t`."

The phrase "to avoid overestimating throughput" is the field's judgement in four words. Crediting unrequested capacity is treated as an inflation of the metric.

Supporting, less direct:

- Abudureheman et al. 2026 (`2026_01`) §II-E: the system utility is `Σ_u log(R_u)` (eq. (13)), chosen because log "balances throughput among users with varying channel conditions and demands" — a concave utility that, by construction, saturates the reward for delivering above what a user already has. Delivered surplus is worth progressively less, never linearly credited.
- Cai et al. (`2025_07`) constraint C1: `C_j,l,t ≥ C_l_min_need,t`. The demand enters as a *floor*, not as a target to overshoot; §IV-E notes that when demand rises past the WSEE stationary point "the capacity is boosted by changing the spectrum allocation as well as the power control … This leads to a reduction in the WSEE" — capacity beyond need is a cost, not a credit.

**Reading for the project.** This is the sub-question with the most direct bite. With a discrete EN 302 307-1 table and a per-user contract of 50 Mbit/s, a lightly-loaded beam (small `n`, low required SE) will be served by a mode that delivers well above `n × 0.30 bit/s/Hz` — because the table's floor mode already exceeds it. Crediting that surplus as delivered bits in a pooled EE numerator would inflate the metric in exactly the way Li et al. names. The corpus convention is `min(mode capacity, n × 50 Mbit/s)`.

### 2.3 How is a user that cannot meet its rate target treated?

**All three treatments appear. The corpus's dominant convention is a hard constraint plus a separately-reported violation count — never silent degradation.**

- **Hard constraint (most common).** Chen et al. 2024 §III eq. (14b): `R_n,m,k(t) ≥ R_th ∀n,m,k`. Cai et al. §II-C C1: `C_j,l,t ≥ C_l_min_need,t ∀l,t,j`. Abudureheman et al. §II-E C5: `R_u ≥ R_min,u ∀u`, "derived from user-specific service level agreement requirements." Tervo et al., footnote 4: "The proposed algorithms can be straightforwardly extended to include data rate constraints, i.e. `r_b ≥ R_b^target` or `r_k ≥ R_k^target`." CDRL §3.2 C1: `R_k^pas ≥ R_min`. Under this treatment an infeasible user makes the *problem* infeasible; it is not quietly served at a lower rate.
- **Admission / connectivity gate.** Zhang, Fu & Yang 2026 §II-C constraint (12c): `h^m_n,i(t) ≥ h_min` — a user may only connect to a satellite whose channel gain clears a floor. Constraint (12e), `t̃^m_n,i ≥ t_min`, additionally blocks connection to satellites with insufficient remaining service time. Chen et al. 2024 defines beam-training failure as `γ < γ_thr` (§II-B) and tracks it as an alignment-accuracy statistic (eq. (10)), constrained in (14c)–(14d).
- **Degraded and counted, but counted *visibly*.** Li et al. 2026's `min(C, D)` (§III-B) is degradation-with-service, and it is paired with an explicitly reported satisfaction rate (below).

**What does not appear anywhere: serving a user below its target, counting its bits toward a pooled numerator, and reporting no separate signal that the target was missed.** That is the failure mode the Q1 construction produces.

### 2.4 Is rate-target attainment reported separately from "has a connection"?

**Yes, in three papers, with three different names for the same idea.** This is a firm convention.

- **Li et al. 2026 (`2025_11`)**, §V: reports four panels per experiment — RT throughput, total throughput, **RT traffic satisfaction rate**, and **overall traffic satisfaction rate** (Figs. 7(a)–(d), 8(a)–(d)). Satisfaction rate is delivered-over-demanded, entirely separate from throughput. Concretely, §V: "at 640-Mbps demand, DLBIA-BH maintains the highest RT traffic satisfaction rate of 96 % … while other methods show significantly lower performance ranging from 54.8 %–92.3 %," and "DLBIA-BH's overall traffic satisfaction rate of 82.5 % … compared to other methods ranging from 53 %–75.2 %." Note the spread: 96 % RT satisfaction against 82.5 % overall from the *same* run. A pooled throughput number cannot express that.
- **Zhang, Fu & Yang 2026 (`2026_03`)**, §II-C eq. (11): `ξ(t) = Σ_m 1(t_total^m > T_max)` — the count of **timed-out users**, users who are connected but failed to finish their 2.5 GB transfer within 450 s (§IV). It enters the objective as a separate term (eq. (12a): `max { R_ave(t), −ξ(t) }`), enters the reward as a distinct penalty factor `Ψ(t) = e^(−ξ(t)/b)` (eq. (13)), and is reported as its own figure (Fig. 5, timed-out users vs user count). The paper's stated reason is exactly the pooled-metric hazard: the penalty "prevents bias toward users with excellent channels and improve QoS" and stops the system "from favoring only excellent-channel users" (§II-C, §III-3). Headline result: "boosting average throughput by 13 % **and reducing timed-out users by 30 %**" — two numbers, reported separately.
- **Chen et al. 2024 (`2024_09`)**, §II-B eq. (10) and Table II: **beam alignment accuracy** `Q_n,m,k(t) = (1/S) Σ 1(γ_n,m,k(τ) ≥ γ_thr)` — the fraction of the recent window in which the user's SINR cleared threshold. Tabulated per sweeping scheme and per frame size (Table II, values 0.774–0.930), constrained separately in (14c)–(14d), and reported alongside EE and throughput rather than folded into them.

Also relevant: Zhang, Fu & Yang's headline rate metric is *not* pooled. §II-C eq. (10): `R_ave(t) = Σ R^m_n,i(t) / Σ u^m_n,i(t)` — sum of rates divided by the **number of connected users**, a per-user average. Combined with `ξ(t)`, the pair distinguishes "how well are served users doing" from "how many users are failing."

**Reading for the project.** A pooled bits-over-joules figure alone reports neither. The corpus's minimum reporting set is: the efficiency ratio, *plus* a rate-target attainment fraction, *plus* a count of users failing the target. All three papers above pay for that separation with figure space, which is the strongest evidence that they consider it necessary.

### 2.5 Amplifier supply power: square-root law? Fixed per-chain cost?

**Square-root law: absent from this corpus.** I searched all twelve for `saturat*`, `back-off`, `backoff`, `OBO`, `IBO`, `amplifier efficien*`, `PA efficiency`, `sqrt`, `square root`. The only PA-efficiency model in the corpus is **linear**:

- Tervo et al. §II-B eq. (5): `P_tot,b = (1/η) Σ_k ||w_k||² + P_CP,b + P_RD δ(r_b)`, with "`η ∈ [0,1]` is the power amplifier efficiency at the BS." Constant efficiency, DC power proportional to RF power.
- CDRL §3.2 eq. (3.9): `P^BS = ||C^RF||_0 P^RF + Σ_k ||F^RF C^RF w_k^BB||²` — transmit power enters linearly.
- Cai et al. §II-C eq. (6): denominator `P_t^l + P_sys`, linear.
- Chen et al. 2024 eq. (13): denominator is raw `Σ P_n,m`, no efficiency term whatsoever.

The only mention of saturation anywhere is Abudureheman et al. §II-E, constraint C4, and it is a *cap*, not a law: total power must stay below `P_max`, "preventing amplifier saturation and ensuring energy-efficient operation."

I will state this without softening and also without over-reading it. **The corpus does not support `P_supply = √(P_rad · P_sat)/0.35`, and it also does not refute it — the question is simply not addressed here.** The square-root form is the standard Class-AB / back-off-dependent DC-power model (`P_DC ∝ √(P_out · P_sat) / η_max`), well established in the terrestrial base-station power-modelling literature. Its absence from this directory is a gap in the directory, not evidence against the model. But it does mean: **the project cannot cite anything in this corpus for it**, and if the model is load-bearing for the results, a source outside this directory is required.

**Fixed per-chain cost: yes, standard.** Three independent instances, all structurally identical to the project's 0.338 W per radiating chain:

- Tervo et al. §II-B eq. (7): `P_TC,b = N_b P_BS + P_SYN + K_b P_UE`, where "`P_BS` is the power per RF chain at each antenna." Linear in the number of active chains.
- CDRL §3.2 eq. (3.9): `||C^RF||_0 P^RF`, where "`P^RF` indicates the fixed power consumption per RF chain" and the L0 norm counts *active* chains. The paper's entire contribution is switching chains off to save this cost.
- Cai et al. §II-C eq. (6): `P_sys`, "the power to maintain normal operation of the ground user, such as power supply and circuit blocks" — a per-device fixed cost.

The project's per-satellite 0.200 W has an analogue too: Tervo's `P_FIX`, "a fixed power consumption required for site-cooling, control signaling, and the load-independent power of backhaul infrastructure and baseband processors" (§II-B eq. (6)).

---

## Q3 — The closest prior art

The required list contains **four** papers whose stated objective is energy efficiency (`2022_04`, `2017_07`, `2024_09`, `2025_07`). I cover all four rather than guess which three were meant.

### Bian & Liu 2022 — "Reliable and Energy-Efficient LEO Satellite Communication with IR-HARQ via Power Allocation" (`2022_04`)

- **Setting.** Single Ka-band (25 GHz) LEO-to-ground link over one communication window. Large-scale fading from ITU-R models (gases P.676, cloud/fog P.840, rain P.838/P.618) driven by STK-simulated geometry; small-scale Rician block fading, i.i.d. across HARQ rounds. §2.1.
- **Decision variables.** The per-round transmit power sequence `(P_1, …, P_L)` for a truncated incremental-redundancy HARQ protocol with at most `L` rounds. §2.2.2 eq. (25).
- **Objective.** `max η_EE = K/E` — correctly-decoded information bits over expected total consumed energy — subject to `e_L ≤ e_0` and `0 < P_i ≤ P_max`. §3.2, Problem 2.
- **Method.** NI-FFT for exact outage probability (§3.1), genetic algorithm for the power sequence (§3.2, Algorithm 1).
- **Baselines.** IR-HARQ-EP (equal power, same `L`); VPA-Approximation (the KKT/approximation method of Shi et al. [24]); no-HARQ.
- **Gains.** vs IR-HARQ-EP: 63.6 % at `L=3, e_0=10⁻⁶`; 2.6× at `e_0=10⁻⁵, L=3`; 44.4 % at `R=1, L=2`; 37.1 % at `K=1`; "more than twice … during most of the communication window" (§4.2, Fig. 14). vs VPA-Approximation: 15.4 % at `e_0=10⁻³`, 26.6 % at `e_0=10⁻²` (Fig. 11).

### Tervo, Tölli, Juntti & Tran 2017 — "Energy-Efficient Beam Coordination Strategies With Rate-Dependent Processing Power" (`2017_07`)

- **Setting.** **Terrestrial**, not satellite. Downlink multicell multiuser MISO, `B` cells, `N_b` antennas per BS, single-antenna users, TDD with pilot overhead and pilot contamination modelled. §II-A.
- **Decision variables.** Beamforming vectors `{w_k}` (jointly direction and power); additionally, uplink pilot allocation via a heuristic (§VI, Algorithm 4).
- **Objective.** Two, contrasted: NetEEmax (pooled, §II-C eq. (10)) and WsumEEmax (sum of per-cell ratios, eq. (11)). The novelty is the denominator: `P_RD δ(r_b)` with `δ` convex increasing in the sum rate, capturing coding/decoding/backhaul power that grows super-linearly with rate — plus per-chain, per-user, oscillator, channel-estimation and beamformer-computation terms (§II-B eqs. (5)–(9)).
- **Method.** Successive convex approximation; Charnes–Cooper transform for NetEE; SOCP for WsumEE; decentralised closed-form KKT variants.
- **Baselines.** DB-WMMSE [17] and "Parametric" [19] (both EE designs that omit rate-dependent power); uncoordinated; orthogonal access (bandwidth split 7 ways); multicell MMSE precoding; single-cell MMSE.
- **Gains.** "up to 60 % gain in the considered setting" over methods ignoring rate-dependent power (§VII, Fig. 3). Explicitly: with `m = 1` (linear rate-dependent power) the term does not change the NetEEmax solution at all (Remark 2) — the gain exists only for `m > 1`.

### Chen, Shen, Feng, Yang & Wu 2024 — "Energy-Efficient Joint Handover and Beam Switching Scheme for Multi-LEO Networks" (`2024_09`)

**This is the closest prior art to the project by a wide margin.**

- **Setting.** Ka-band 28 GHz, 165 LEOs at 550 km, 37 beams each, 100 MHz system bandwidth, 50 dBm max satellite power, 500 km serving radius. Path loss `L = L_fs + L_g + L_sc + L_sf`. Both intra-LEO (inter-beam) and inter-LEO interference modelled (§II-A eqs. (5)–(6)). Table I.
- **Decision variables.** Three, jointly: per-beam transmit power `P`, the user–beam–satellite association / handover indicator `a`, and the beam training set `Φ`. §III.
- **Objective.** `max E_eff(t) = R_tot(t) / Σ_n Σ_m P_n,m(t)` — **pooled energy efficiency** — subject to a per-user rate floor `R_n,m,k ≥ R_th` (14b), per-user and system beam-alignment accuracy (14c)–(14d), training-latency caps (14e)–(14f), and per-beam / per-satellite power caps (14g)–(14h). §III eq. (14).
- **Also present, and material to the project's claims.** (i) **Bandwidth shared equally among the users of a beam**: `R_n,m,k = (1 − C_n/T_f)(W_n,m / U_n,m) log₂(1 + γ)`, §II-B eq. (9), "We allocate the bandwidth equally among the users served by the same beam to ensure fairness" — this makes the achievable rate an explicit function of beam occupancy `U_n,m`. (ii) **Occupancy-coupled power control**: the DPC loop (§IV-B eqs. (27)–(31)) steps per-beam power up or down by observing per-beam EE, and eq. (30) forces the step positive whenever any user in the beam falls below `γ_thr`. Since the per-user SINR requirement rises with `U_n,m` through eq. (9), the loop is occupancy-driven. (iii) **Handover**: intra-LEO beam switching plus inter-LEO handover gated by a 3GPP-A3-style pair of conditions — SINR offset `γ_n*,m*,k − γ_os > γ_n,m,k` with `γ_os = 6 dB` (eq. (24)) and a time-to-trigger `T^trig ≥ T_thr` (eq. (25)) — Algorithm 2.
- **Baselines.** EBS (exhaustive beam search, optimal SINR at unaffordable overhead); HOBS-F (proposed search with full/fixed power control); three beam-sweeping schemes crossed with power control (SCBS/SSBS/ABS × F/P).
- **Gains.** Throughput "approximately 1.2 times to twice higher … compared to EBS" (§V, Fig. 5(a)); HOBS-P achieves the highest EE among all combinations across frame sizes 2–7 s (Fig. 6, Fig. of §V); beam alignment accuracy 0.774–0.930 (Table II); SINR "asymptotic … to that of EBS while minimizing latency" (Fig. 4).

### Cai, Wang, Zhao, Xu & Wang 2025 — "Energy-Efficiency-Based Joint Uplink Resources Allocation for LEO Satellite Beam-Hopping System" (`2025_07`)

- **Setting.** LEO **uplink**, beam hopping, `J` cells, `K` beams active per slot, 400 MHz total divided into 8 sub-bands, full frequency reuse across beams, FDMA within a beam, 576 terminals under one satellite, 3GPP TR 38.811 antenna pattern. §II, §IV-A.
- **Decision variables.** Beam-hopping patterns `A`, frequency (sub-band) allocation `F`, and per-terminal power-control coefficients `w`. §II-C P0.
- **Objective.** `max Σ_t E_total^t` where `E_total^t = Σ Σ λ_l · C_j,l,t/(P_t^l + P_sys)` — **weighted sum EE**, deliberately not pooled — subject to `C_j,l,t ≥ C_l_min_need,t` and power/bandwidth/beam constraints. §II-C eqs. (6)–(8).
- **Method.** Many-to-one matching with peer effects over a "friendship" graph built from EE-sensitivity and spatial isolation (BBHMA-1 greedy, BBHMA-2 with simulated annealing); then penalty-function relaxation of the binary frequency variables + quadratic transform + minorize–maximization (JPFA). §III.
- **Baselines.** For BH design: R-BH (random), P-BH (periodic), SP-BH-2-D and SP-BH-3-D (spatial isolation at 2× and 3× beam diameter), DRL-BH [20]. For resource allocation: FA (fixed frequency allocation), MaxGEE [23] (the pooled-EE design), MaxCC [7] (max capacity), and a genie UP-bound with perfect inter-beam SIC.
- **Gains.** WSEE "+34 % … compared with the case of ignoring the EES scheme" (§IV-D); BH design "outperform the conventional method by at least 15 % in terms of the C.D.F" (§IV-B); DRL-BH beats SP-BH-3-D by only 2 % at the tolerance point, while BBHMA beats both.

### So what would be left as new?

Project as described: joint handover decisions + occupancy-dependent power control + a discrete mode table + pooled EE reporting, Ka-band multi-beam LEO, frequency reuse 3.

**Already covered, element by element:**

| Element | Covered by | Where |
|---|---|---|
| Handover decisions jointly with power control, Ka-band LEO, **EE objective** | Chen et al. 2024 | §III eq. (14), Algorithm 2, §IV-B |
| Handover jointly with power, LEO, DRL, discrete+continuous action split | Zhang, Fu & Yang 2026 | §II-C eq. (12), §III |
| Handover / reassignment with a switching cost, at constellation scale | Holder et al. 2025 (REDA) | Constellation experiment, 324 sats / 450 tasks |
| Rate divided by beam occupancy (`R = c/K`), **and proved optimal** for log utility | Ye et al. 2013 | Definition 1, Proposition 1, eq. (8) |
| Equal airtime/bandwidth share within a beam, satellite multi-beam | Chen et al. 2024 | §II-B eq. (9) |
| Occupancy-coupled power stepping to hold a per-user SINR threshold | Chen et al. 2024 | §IV-B eqs. (27)–(31) |
| Demand-proportional per-beam power | Abudureheman et al. 2026 | §III-A eq. (27) |
| Pooled EE as the reported objective, Ka-band multi-beam LEO | Chen et al. 2024 | §II-B eq. (13) |
| Pooled EE with per-chain + fixed platform power in the denominator | Tervo et al. 2017; CDRL | §II-B eqs. (5)–(7); §3.2 eq. (3.9) |
| Multi-beam LEO with explicit frequency reuse / SFR and reuse-induced interference | Abudureheman et al. 2026 | §II-A, §III-B eqs. (30)–(31) |
| Beam-level vs system-level EE trade-off | Tervo et al. 2017; Cai et al. 2025 | §VII Fig. 7; §I-A, §IV-D |

**Not covered by anything in this corpus:**

- **The discrete EN 302 307-1 mode table.** Every rate expression in all twelve papers is Shannon `log₂(1 + SINR)` — I verified this mechanically across the whole directory. Bian & Liu cite EN 302 307-1 (their ref [33]) but only for the claim that DVB-S2 ACM supports a 1 s channel-state update; they use a *fixed* rate `R = N_b/N_s` per HARQ round, not a table. Li et al. 2026 cite EN 302 307-2 (DVB-S2X, their ref [8]) only as motivation for beam hopping, and then use Shannon. **So a discrete-MODCOD link budget inside an EE/handover loop is genuinely absent from this corpus.**
- The specific square-root PA supply-power law (see §2.5 — absent, not refuted).

**The honest verdict: very little is left as new, and what is left is not the kind of thing that carries a paper.**

Chen et al. 2024 already does joint handover + beam switching + occupancy-coupled power control in Ka-band multi-beam LEO, optimising and reporting pooled energy efficiency, with per-user rate floors, inter-beam and inter-satellite interference, and shadow fading and scintillation in the path loss. That is the project's contribution list, in a 2024 VTC paper. The occupancy→rate dependence has been settled since Ye et al. 2013, where equal sharing is not merely assumed but *proved optimal* for logarithmic utility (Proposition 1) — so adopting it is adopting a known-correct default, not a modelling advance.

That leaves the discrete mode table. Replacing Shannon with EN 302 307-1 thresholds plus a 1.7 dB implementation margin is a **realism upgrade** — it is a strictly better link model than Shannon, and it changes results in ways worth reporting (quantisation makes rate a step function of SINR, which changes the shape of every power-control loop that assumes smoothness, and it creates the "delivered exceeds contracted" case discussed in §2.2). But adaptive coding and modulation against a standard MODCOD table is what deployed Ka-band systems do; using it is closing a gap between the literature and practice, not opening a new question. As a framing, "we redid a known joint-handover-and-power-control problem with a standards-compliant PHY" is defensible and useful. As a novelty claim, it is thin.

And the pooled-EE reporting choice moves the project *behind* the two papers that examined the metric question: Tervo et al. and Cai et al. both report the disaggregated form alongside the pooled one, and Cai et al. state in §I-A why the pooled form alone is inadequate. Reporting only pooled EE is not a contribution; it is the weaker of two available conventions.

Finally, the Q1 defect subtracts rather than adds. Under the construction as described, users are served 2–5 MODCOD steps below contract while the power bill is sized for the contracted mode. That is not a novel physics choice to be defended — it is a bug in the ordering of two operations, and the pooled metric is the reporting choice least likely to reveal it.

**If the project needs a defensible novelty claim from this corpus's vantage point, the candidates are narrow and should be stated narrowly:** (i) what MODCOD quantisation does to an occupancy-driven power-control loop that prior work modelled as smooth; (ii) the interaction between frequency-reuse-3 (nobody in this corpus uses FR3 — Kim et al. use reuse 1, Yu & Kim use FRF option 1, Cai et al. use full reuse, Abudureheman et al. use adaptive SFR) and a discrete rate table. Both are real. Neither is "joint handover with power control and pooled EE."

---

## Where this corpus does not answer the question

Stated so these are not mistaken for findings:

1. **No availability percentage for Ka-band LEO, and no dB fade margin tied to one.** The corpus gives Bian & Liu's post-HARQ outage sweep (`10⁻⁶ … 10⁻¹`, Ka-band) and Kim et al.'s 5.3 dB lumped budget (S-band). Neither is an ITU-style availability-to-margin mapping. That answer lives in ITU-R P.618 and in Ekerete, Awoseyila & Evans (*IEEE Commun. Lett.* 2020), both cited by Bian & Liu and **neither present in this directory**.
2. **No discussion of receiver implementation margin.** Zero hits across twelve papers. My answer in §1.4 reasons from the corpus's *structure* (Cai eq. (1), Kim §V) rather than from any statement in it, and I have flagged it as such.
3. **No square-root amplifier supply-power law.** Absent, not contradicted. §2.5.
4. **No discrete MODCOD rate model.** Absent. All twelve use Shannon. This means the corpus cannot tell you how the field handles quantisation effects — because in this corpus, the field does not model them.
5. **EN 302 307-1 threshold spacing.** The "0.5–1.5 dB apart" figure in §1.3 is from the standard, not from any paper in this directory.
6. **Tervo et al. Table I (simulation parameters) did not survive PDF text extraction**, so no numeric parameter values from that table are cited here.
