### 1. Physics & NTN Practice: Recurrence Reset vs. Forward Link Reality

Holding the segment-start received power level via the recurrence $p(t) = p_0 \cdot \frac{G^T(\theta(\tau))}{G^T(\theta(t))}$ ([Excerpt 1, lines 225–239](file:///home/u24/src/mcrl/env/link_budget.py#L225-L239)) is **not a defensible abstraction** of NTN forward links; it manufactures an **artificial renewal premium**.

* **The Cancellation & Drift Mechanism**: In [Excerpt 2, lines 95–104](file:///home/u24/src/mcrl/env/step.py#L95-L104), received power is $P_{\text{rx}}(t) \propto p(t) \cdot G^T(\theta(t)) = p_0 \cdot G^T(\theta(\tau))$. The instantaneous antenna gain $G^T(\theta(t))$ cancels completely. As the LEO satellite moves over a 30.08 s step, $\theta(t)$ drifts away from the dwell anchor, driving $G^T(\theta(t))$ down and forcing $p(t)$ to ramp up monotonically by up to 3.01 dB ([Excerpt 1, lines 165–175, 445–455](file:///home/u24/src/mcrl/env/link_budget.py#L165-L175)).
* **The Artificial Renewal Premium**: When a handover occurs, $\tau$ resets to $t$, collapsing $p(t)$ back down to $p_0 = 0.825\text{ W}$ ([Excerpt 1, line 155](file:///home/u24/src/mcrl/env/link_budget.py#L155); [Excerpt 2, lines 25–45](file:///home/u24/src/mcrl/env/step.py#L25-L45)). In the energy accounting, handovers cost **zero Joules** ([Excerpt 1, line 375](file:///home/u24/src/mcrl/env/link_budget.py#L375); [Excerpt 2, line 120](file:///home/u24/src/mcrl/env/step.py#L120)), whereas training rewards penalize handovers via $r_2 = -\text{HANDOVER\_COST}$ ([Excerpt 2, line 145](file:///home/u24/src/mcrl/env/step.py#L145)). A model-based coordinator optimizing pure physical $EE = \text{bits}/\text{Joules}$ ignores $r_2$ and aggressively triggers handovers to reset transmit power to $p_0$, dodging the late-dwell power penalty. This explains why the coordinator's EE advantage expands from $+1.35\%$ at phase 0 to $+9.26\%$ at phase 3 ([Excerpt 3, lines 75–85](file:///home/u24/src/mcrl/env/dwell.py#L75-L85)).
* **Real Forward Link Operation**:
  1. *Fixed EIRP + ACM*: Operational LEO forward links (DVB-S2X, 3GPP Rel-17/18 NTN) operate at fixed, backed-off per-carrier/per-beam RF power. Channel variation and beam-edge rolloff are handled by Adaptive Coding and Modulation (ACM), adjusting spectral efficiency (MODCOD/MCS) according to terminal CQI reports rather than pumping transmitter power.
  2. *Power Control Cadence*: Fast closed-loop transmit power control (TPC) exists almost exclusively on the **return link** (uplink) to handle terminal battery conservation and near-far multi-access dynamics at sub-second cadences. Forward links do not run closed-loop gain-inversion across 30-second orbital drift steps.

---

### 2. Comprehensive Audit: Energy & Bits Model Terms

#### 1. Per-beam RF Power Aggregation (`beam_power_w = max over users`)
* **Mechanism**: Radiated beam RF power is $p_{s,v} = \max_{u \in \text{served}} p_{u,s,v}$ ([Excerpt 1, lines 265–290](file:///home/u24/src/mcrl/env/link_budget.py#L265-L290); [Excerpt 2, line 60](file:///home/u24/src/mcrl/env/step.py#L60)), rather than the sum $\sum_u p_u$.
* **Who Exploits**: Any policy packing multiple users onto a single beam gets subsequent users served with **zero marginal RF power**.
* **Rough Magnitude**: Deflates beam RF energy by the mean occupancy factor $U_{s,v}$ ($2.28\times \approx 3.6\text{ dB}$ for 100 users; [Excerpt 1, lines 385–395](file:///home/u24/src/mcrl/env/link_budget.py#L385-L395)).
* **Action**: **FIX**. Real orthogonal downlink multiplexing (TDM/FDM) requires summing user sub-band powers (FDM) or time-averaging slot powers (TDM).

#### 2. PA Efficiency, Back-off, and Saturation (`pa_efficiency`, `supply_power_w`)
* **Mechanism**: $\xi = \min(\xi_{\max}, \xi_{\max}\sqrt{p/p_{\text{sat}}})$ with $\xi_{\max}=0.35$, $p_{\max}=1.65\text{ W}$, $BO=5\text{ dB}$, and $p_{\text{sat}}=5.218\text{ W}$ ([Excerpt 1, lines 180–195, 295–320](file:///home/u24/src/mcrl/env/link_budget.py#L180-L195)). Because $p \le p_{\max}$, maximum achievable efficiency is $\xi_{\max}\sqrt{1.65/5.218} \approx 0.197$. Supply power scales as $P_{\text{supply}} = p/\xi \propto \sqrt{p \cdot p_{\text{sat}}}$ ([Excerpt 1, lines 325–345](file:///home/u24/src/mcrl/env/link_budget.py#L325-L345)).
* **Who Exploits**: Policies concentrating power into fewer beams benefit from higher efficiency ($\sqrt{p}$ sub-linear DC scaling), while low-power beams suffer steep penalties ($\xi \to 0$ as $p \to 0$).
* **Rough Magnitude**: Efficiency ceiling is capped at $19.7\%$ rather than $35\%$; DC draw is inflated by $1.78\times$ relative to peak specs.
* **Action**: **DECLARE**. The sub-linear Class-B efficiency curve is standard; clarify that $\xi_{\max}=0.35$ is unreachable due to the mandatory $5\text{ dB}$ back-off.

#### 3. Active Beam & Satellite Fixed Power (`fixed_power_w`)
* **Mechanism**: $P^f = \sum_s (N^{\text{act}}_s P_{\text{cir}} + \mathbf{1}_{\{N^{\text{act}}_s > 0\}} P_{\text{BB}})$ with $P_{\text{cir}}=0.338\text{ W}$ and $P_{\text{BB}}=0.200\text{ W}$ ([Excerpt 1, lines 200–210, 350–370](file:///home/u24/src/mcrl/env/link_budget.py#L200-L210)). A beam or satellite with zero served users draws exactly $0.0\text{ W}$ instantly.
* **Who Exploits**: Coordinators that aggressively turn off beams/satellites step-by-step achieve instantaneous power collapse with no cooldown/warm-up latency or transition energy penalty.
* **Rough Magnitude**: 39 beams draw $39 \times 0.338 = 13.18\text{ W}$ circuit power. Deactivating 10 idle beams saves $3.38\text{ W}$ (comparable to total network RF power of $\sim 10\text{–}20\text{ W}$).
* **Action**: **SENSITIVITY**. Sweep an unswitched quiescent standby power floor on active orbiters (e.g., $20\%\text{–}50\%$ of $P_{\text{cir}}$).

#### 4. Omission of Spacecraft Bus / Quiescent Idle Floor (`system_power_w`)
* **Mechanism**: Total system power $P^N$ sums only active RF supply and fixed circuit/baseband power ([Excerpt 1, lines 375–410](file:///home/u24/src/mcrl/env/link_budget.py#L375-L410)). If all beams are dark, power is $0.0\text{ W}$ ([Doc Excerpt §7](file:///home/u24/docs/LINK-BUDGET-NOTES.md#7-w-06p-7-零功率-ee-fail-closed)). Spacecraft bus power (ADCS, OBDH, thermal, solar tracking, telemetry) is omitted.
* **Who Exploits**: Policies that deliberately under-serve or sparse-schedule traffic produce inflated $EE = \text{bits}/\text{marginal Joules}$, because no baseline satellite operating cost is amortized.
* **Rough Magnitude**: Actual LEO comms payloads draw hundreds of watts quiescently ($50\text{–}500\text{ W}$). Model power ($\sim 5\text{–}25\text{ W}$) is an order of magnitude too low for platform-level EE.
* **Action**: **DECLARE**. Explicitly define the metric as *marginal RF/payload subsystem efficiency*, not full spacecraft EE.

#### 5. Handover and Beam Re-steering Energy
* **Mechanism**: Handover has an RL reward penalty $r_2$ ([Excerpt 2, line 145](file:///home/u24/src/mcrl/env/step.py#L145)) but costs $0.0\text{ J}$ in physical energy ([Excerpt 1, line 375](file:///home/u24/src/mcrl/env/link_budget.py#L375)). Phased array re-steering and RRC signaling consume no energy.
* **Who Exploits**: Model-based policies evaluating physical EE can trigger unlimited handovers with zero energy consequence, evading RL training constraints.
* **Rough Magnitude**: Direct cause of the $+2.9\%$ coordinator gain (escalating to $+9.26\%$ at late dwell phase).
* **Action**: **FIX**. Either introduce a physical handover switching cost ($E_{\text{HO}} = P_{\text{reconfig}} \cdot \Delta t_{\text{HO}}$) or enforce a signaling latency gap ($\Delta t_{\text{HO}} \approx 100\text{–}500\text{ ms}$) where delivered bits are zero.

#### 6. Equal Bandwidth Partitioning (`shannon_rate_bps`)
* **Mechanism**: Beam bandwidth is divided equally among served users: $B_u = B^w / U_{s,v}$ ([Excerpt 1, lines 415–435](file:///home/u24/src/mcrl/env/link_budget.py#L415-L435)).
* **Who Exploits**: Policies allocating single users to dedicated beams award them the entire $166.67\text{ MHz}$, whereas multi-user beams heavily penalize edge users with equal time slices regardless of channel quality.
* **Rough Magnitude**: Omitting opportunistic scheduling (Proportional Fair / Water-filling) biases capacity comparisons by $20\%\text{–}40\%$.
* **Action**: **DECLARE**. Tractable standard for high-level MAC network simulations.

#### 7. Co-channel Interference and Antenna Modelling
* **Mechanism**: FRF = 3 ([Excerpt 1, lines 20–28](file:///home/u24/src/mcrl/env/link_budget.py#L20-L28)), co-channel interference keyed on matched cell colors ([Excerpt 2, lines 75–90](file:///home/u24/src/mcrl/env/step.py#L75-L90)), terminal side-lobes follow ITU-R S.465-6 with a $35\text{ dBi}$ override for co-satellite beams ([Doc Excerpt §3, §4](file:///home/u24/docs/LINK-BUDGET-NOTES.md#3-w-06gr-與度弧度g-7)).
* **Who Exploits**: Policies segregating users across distinct satellites avoid the $35\text{ dBi}$ intra-satellite interference penalty.
* **Rough Magnitude**: SINR dynamic range spans $>25\text{ dB}$ (isolated) down to $<0\text{ dB}$ (co-channel loaded).
* **Action**: **DECLARE**. Verified against 3GPP/ITU-R standards and numerical guards ([Doc Excerpt §1](file:///home/u24/docs/LINK-BUDGET-NOTES.md#1-w-15貝索數值域p-1--g-10)).

#### 8. Full-Buffer Unconstrained Shannon Rate
* **Mechanism**: Rates are computed as $R = B_u \log_2(1 + \text{SINR})$ ([Excerpt 1, lines 415–435](file:///home/u24/src/mcrl/env/link_budget.py#L415-L435)) without MCS tables, code rate ceilings, or packet overhead.
* **Who Exploits**: Policies driving high SINR on beam-center users gain unphysical spectral efficiencies ($>6\text{ bps/Hz}$), unachievable in DVB-S2X / 3GPP NTN.
* **Rough Magnitude**: Overestimates throughput by $1.5\text{–}3.0\text{ dB}$ implementation margin and $25\%\text{–}45\%$ at high SINR by ignoring MODCOD saturation.
* **Action**: **FIX**. Clamp spectral efficiency at the maximum standard MODCOD ceiling (e.g., $5.4\text{ bps/Hz}$ for 64-APSK/256-QAM) and apply a $1.5\text{ dB}$ implementation gap.

#### 9. Service Feasibility Outside Recurrence (`p > p_max` Outage)
* **Mechanism**: Users whose recurrence power exceeds $p_{\max} = 1.65\text{ W}$ are declared infeasible and dropped to outage ([Excerpt 1, lines 245–260](file:///home/u24/src/mcrl/env/link_budget.py#L245-L260); [Excerpt 4, lines 60–75](file:///home/u24/src/mcrl/env/service.py#L60-L75)). Once dropped, they do not enter eligible load $U_{s,v}$ ([Excerpt 4, lines 20–35](file:///home/u24/src/mcrl/env/service.py#L20-L35)).
* **Who Exploits**: A policy can shed power-hungry edge users; surviving users get more bandwidth ($B^w / (U-1)$) and lower beam power, artificially boosting EE ($bits/J$).
* **Rough Magnitude**: Dropping one marginal user saves up to $1.65\text{ W}$ and doubles remaining bandwidth on a 2-user beam.
* **Action**: **DECLARE** with mandatory service rate reporting (enforced by Gate G-8, [Doc Excerpt §9](file:///home/u24/docs/LINK-BUDGET-NOTES.md#9-w-06g-8-服務率必附)).

---

### 3. Top 5 Ranking & The Single Decisive Cheap Test

#### Top 5 Artifacts Ranked by Impact on Policy EE Comparisons:
1. **Recurrence Power Drift & Reset at Handover (with Zero Energy Cost)**: Directly manufactures the coordinator's $+2.9\%$ to $+9.26\%$ EE advantage by subsidizing handovers to evade aging link power penalties.
2. **Per-Beam RF Power Max Aggregation ($p_{s,v} = \max_u p_u$)**: Biases network load balancing by up to $3.6\text{ dB}$ ($2.28\times$), granting multi-user multiplexing free RF energy.
3. **Absence of Spacecraft Bus / Quiescent Idle Power Floor**: Distorts relative EE differences by $10\times\text{–}100\times$, artificially favoring policies with sporadic or sparse beam activation.
4. **Full-Buffer Shannon Capacity without MODCOD/MCS Saturation**: Disproportionately rewards high-power concentration policies by crediting unphysical spectral efficiencies.
5. **Instantaneous On/Off Beam Circuit & Baseband Power**: Provides an unphysical free option for dynamic satellite beam hopping without standby energy or transition delays.

#### The Single Most Decisive Cheap Test:
**Ablate the gain drift memory**: in `src/mcrl/env/step.py` ([Excerpt 2, line 10](file:///home/u24/src/mcrl/env/step.py#L10)), force `start_gain = float(transmit_gain[uid])` at every step (or equivalently set $p(t) \equiv p_0 = 0.825\text{ W}$ in `recurrence_power_w`).
* **Expected Decisive Outcome**: Disabling drift compensation fixes transmit power to $p_0$ across all steps. If the coordinator's $+2.9\%$ advantage and its $+1.35\% \to +9.26\%$ phase-dependent escalation collapse to near zero, the entire performance gain is definitively proven to be an artifact of the recurrence reset.
