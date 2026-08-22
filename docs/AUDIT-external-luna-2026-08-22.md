## (1) Divergences I found independently

I derived this list from mc-modqn-base.md, ch4-method.md, ch5-experimental-result.md, and the simplified symbol table before reading CONTROLLER-QUESTIONS-2026-08-22.md. “Not wired” means that a helper or configuration exists but no StepEnvironment producer consumes it; modqn.py calls env.reset()/env.step() but no StepEnvironment definition or env/step.py exists in src/mcrl/.

Implementation citations below are relative to mcrl-leo-handover/src/mcrl; paper citations are relative to modqn-paper-reproduction.

| ID | Paper equation(s) | Paper says | Code does | Quantity/effect |
|---|---|---|---|---|
| D-01 | (3.1)–(3.4) | x is the binary physical connection, U=sum x, and z=1{U>0} with no per-satellite beam-count cap (mc-modqn-base.md:99-136). | ServiceResolution counts post-execution served users and derives activation from that count (service.py:52-124), but there is no runtime x tensor or connected environment. The code also inserts execution gate m^e (service.py:23-29,127-198). | Algebraic helper coverage is partial; end-to-end x/U/z and all downstream physical quantities are not computable. Code U is the post-m^e count, not the paper's two-gate x unless the unresolved authority conflict is settled. |
| D-02 | (3.5)–(3.9) | Geometry feeds one transmit pattern through theta; the active symbol table specifies theta in radians (simplified-ee-symbol-table.md:48-59,77-92). | The closed-form slant range and satellite-vertex angle helpers exist (pointing.py:40-73), and the Bessel pattern is algebraically faithful (antenna.py:42-99). However, candidate_geometry emits off_axis_deg (pointing.py:151-169), while UserState/the encoder contract says theta is raw radians (step_types.py:536-542; state_encoding.py:37-65). | The pattern helper itself is numerically equivalent after its explicit degree conversion. The unconnected producer/consumer seam has a possible 180/pi=57.2957795 angle error; I cannot claim that it occurs in a live rollout because no environment connects the seam. |
| D-03 | (3.10), (3.10a)–(3.10c) | H=10^(-L/10)GR, L=Lf+Lg+Lc+Ls, then wanted power is p H GT (mc-modqn-base.md:194-231). | FS gain, an alternative atmospheric loss, and receive gain are separate helpers (link_budget.py:84-126; antenna.py:146-170); no function assembles H, and no Lc, Ls, or Rician realization is implemented. The paper atmosphere row is 3 d chi/(10 h) (ch5-experimental-result.md:31-42), while code uses chi*10/sin(elevation) (link_budget.py:93-119). | At zenith d=h, paper loss is 3*0.05/10=0.015 dB; code loss is 0.05*10=0.500 dB: +0.485 dB, a linear gain multiplier 10^(-0.485/10)=0.8943345 (10.5665% lower). Effects of missing Lc, Ls, and KR=20 dB cannot be computed because the paper gives no executable realization for them. |
| D-04 | (3.11), (3.12) | Within one served physical-link segment, p(t)=p(t-1)GT(theta(t-1))/GT(theta(t)); each segment starts at p0; no target-SINR inversion, cap, clamp, or projection (mc-modqn-base.md:237-268). | The concrete power function is p=0.25+0.35*sqrt(load) for positive load (link_budget.py:134-151); at load 1 it is 0.60 W, not the paper p0=2 W (ch5-experimental-result.md:49-60). The “single-sinr-previous-step” label is only a configuration name (step_types.py:35-56); no recurrence implementation is present. | Power is a different function of state: load-driven instead of angle/segment-driven. The absolute discrepancy at a one-user segment start is 0.60 versus 2.00 W; at other loads no common paper/code state exists for a more meaningful numeric comparison. |
| D-05 | Text immediately before (3.12a), then (3.12a)–(3.12b) | One active beam has one RF power, p_s,v=max over served users of p_u,s,v, independent of user count (mc-modqn-base.md:270-290). | No max-over-served-users aggregation exists. beam_transmit_power_w derives one value from a load count (link_budget.py:134-151). | Beam power is not determined by the paper rule; the difference depends on per-user powers and cannot be computed from the present code. |
| D-06 | (3.12a), (3.12b), (3.13) | Sum all active same-colour intra/inter-satellite beams, then use the unique physical gamma=(p H GT)/(I+sigma2) (mc-modqn-base.md:270-307). | Colour and angle-side helper data exist, but no interference sums or physical SINR producer exist. shannon_rate_bps accepts a caller-supplied SINR (link_budget.py:195-202); the optional intra-interference configuration is only a sidecar declaration (step_types.py:221-230). | No numerical I or gamma can be audited. A supplied SNR/SINR is not an implementation of (3.13). |
| D-07 | (3.14) | R=(B^w/U_s,v) log2(1+gamma) (mc-modqn-base.md:309-319). | shannon_rate_bps returns B^w log2(1+sinr) with no load divisor (link_budget.py:195-202). | For the same gamma and positive load U, code rate is exactly U times the paper rate. For U=4 it is 4x; for U=1 it agrees. |
| D-08 | (3.15), (3.15a) | Pp=p/xi, with xi=min(xi_max, xi_max*sqrt(p_s,v/p_sat)) (mc-modqn-base.md:321-340). | consumed_power_w sums radiated beam watts only (link_budget.py:182-192). The available per-link EE helper instead computes a legacy R/(kappa P_tot+P0) (energy_efficiency.py:226-329); there is no xi/Pp implementation. | Code omits the PA conversion factor and undercounts the paper PA term by 1/xi; the numerical factor is indeterminate because code has neither the paper p_s,v nor p_sat/xi constants. |
| D-09 | (3.16a), (3.16), (3.17), (3.25) | Add fixed/circuit Pf, aggregate PN, then use the common denominator for every link and r1 (mc-modqn-base.md:342-374,397-413). | No producer computes Pf or PN. additive_system_ee accepts an already supplied system power (energy_efficiency.py:114-184), and StepResult exposes radiated beam power only (step_types.py:637-669). The default trainer selects throughput for r1 (trainer_spec.py:78-90; objective_math.py:53-90). | With one active beam on one satellite, paper legacy values alone add 0.338+0.200=0.538 W to Pf; code adds zero fixed watts. Default learned r1 is bits/s, not the paper bit/J common-denominator contribution. |
| D-10 | (3.24), (3.27)–(3.29) | Optimize EE, handover, and sum U squared; r1 is EE, r2=-Psi, r3=-U_bu, and the reward is their three-vector (mc-modqn-base.md:380-450). | Handover classification matches the three served-association branches but adds unserved/re-entry rules (action_contract.py:392-450). r3_counting returns -U (service.py:201-214), while RewardComponents still documents the old “negative gap / num_users” semantics (step_types.py:592-634). No live producer supplies the paper r1/reward vector because the environment is absent. | r3 is exact only through the particular helper and served population; the stale typed contract is semantically inconsistent. The handover extension changes unserved/re-entry rewards, which are not fully specified by the displayed (3.27) cases. |
| D-11 | (4.1) | State is exactly four C-length blocks: prior connection x(t-1), actual SINR gamma, theta, and prior demand N(t-1) (ch4-method.md:13-30). With C=28, paper says 112 dimensions (ch5-experimental-result.md:23-25). | access_vector is documented as current assignment, channel_quality as linear SNR, and beam_loads as global ungated demand (step_types.py:530-555). The encoder applies log1p(SNR) and divides loads by num_users, then appends a 13-dimensional contract block (state_encoding.py:20-116). | State width is 125 versus 112 (+13, 11.607%); observation values are also transformed and SNR is not the paper unique SINR. The 13 fields are incumbent, D2 TTT, radial rate, and dwell phase (action_contract.py:518-547), none of which appear in (4.1). |
| D-12 | (4.2)–(4.6), especially (4.5a) | Masked scalar action is one valid candidate per user; paper connection is x=a z, with link infeasibility handled after connection (ch4-method.md:32-78). | Masked scalar selection and joint action array exist (modqn.py:274-369), but empty masks emit NO_OP_ACTION=-1 (action_contract.py:71-88; modqn.py:299-336), and service accounting uses x=a m^e z (service.py:23-29). Candidate masks explicitly omit link-feasibility filtering (candidates.py:15-24). | No-op is outside a in A and violates the unconditional sum a=1 wording; it creates an unserved/drop-replay path absent from the displayed equations. The three-gate connection also differs from the two-gate equation in ch4-method.md. |
| D-13 | (4.7)–(4.13) | Two MODQN agents, EE routing, asymmetric discounts, intervention batches, competitive reward, two TD-update families, and fixed c_j calibration (ch4-method.md:108-180,182-249). | MODQNTrainer creates one set of three Q networks and one replay buffer (modqn.py:123-145), uses one discount (trainer_spec.py:37-57), and has no catfish/routing/intervention/competitive path. Calibration is disabled by default with scales (1,1,1) (trainer_spec.py:78-90; objective_math.py:32-50). | This is not MCRL parity. beta_F=.99, q1=.50, q2=.80, W=5000, rho_I=.30, [T1,T2]=[4,16], eta_w=1, and the paper c_j values are not implemented. With paper values, effective raw-unit weights are (4.265579694e-9, 1.044309168e-3, 1.202568614e-9), not uncalibrated (0.5,0.3,0.2). |

The current paper has no equation tags (3.18)–(3.23) or (3.26); those numbers are not omissions from Python.

## (2) Findings not represented as C-1..C-14

- The direct (3.14) load-divisor error is not in the controller list; its “matches” row is contradicted by link_budget.py:195-202.
- The angle unit seam is not in the list: paper/symbol table theta is radians, candidate_geometry returns degrees, and the state seam requires radians (simplified-ee-symbol-table.md:48-55; pointing.py:151-169; step_types.py:536-542).
- The list does not count the complete absence of a live physical chain: no StepEnvironment, no x producer, no H, no interference/SINR producer, and no PN producer. The controller notes the missing environment at CONTROLLER-QUESTIONS-2026-08-22.md:12-16, but does not include it as a divergence.
- The whole (4.7)–(4.13) MCRL gap is absent as a divergence. The list discusses state, learning rate, and no-op, but not the missing catfish agent, routing, intervention, competitive reward, beta_F, or calibration contract.
- The state-semantic mismatches beyond width—current assignment versus prior x, SNR versus actual gamma, log1p, and load normalization—are not covered by C-1’s dimension question.
- The typed reward seam is internally stale: service.r3_counting is raw -U, but RewardComponents still describes normalized gap semantics (service.py:201-214; step_types.py:592-634). This is not merely the open scale question.
- The code’s concrete rate, power, and EE helpers are not connected to one another. The controller’s “formula exists” statements do not establish implementation parity; the absent connection changes whether any reported physical quantity is real or only caller-supplied metadata.

## (3) Existing items I dispute or find overstated

- The “✓” claims for (3.12a)/(3.12b) and (3.14) at CONTROLLER-QUESTIONS-2026-08-22.md:31-33 are wrong as implementation claims. The interference sums are absent; the rate helper omits /U.
- The “✓” claims for (3.1)–(3.4) and (3.27)–(3.29) at CONTROLLER-QUESTIONS-2026-08-22.md:24-35 are only structural/helper-level matches. There is no physical x tensor or environment, (3.27) has extra unserved/re-entry behavior, and the typed r3 contract is stale.
- C-3’s statement that “V=39 沒有問題” (CONTROLLER-QUESTIONS-2026-08-22.md:78-95) is overstated. The paper says 39, but the current code has no V=39 constant; an independent probe of build_cell_grid(altitude_km=483) returned 81 lattice cells, 47 marked service-area cells. The claimed 39-cell coverage result cannot be reproduced from the implementation as written.
- C-8/C-9 correctly identify absent channel terms, but their request for exact Lc, Ls, and Rician realization values is not answerable from the supplied paper: (3.10b) names the terms, while §5.1 supplies only KR=20 dB, not a stochastic model or numeric Lc/Ls parameters (mc-modqn-base.md:203-214; ch5-experimental-result.md:34-43). The audit result is “unimplemented/undetermined,” not a guessed model.
- C-11’s statement that “the paper now is two gates” is too absolute. ch4-method.md:63-71 is two-gate x=a z, but the supplied active symbol table explicitly records the revised environment accounting as three-gate x=a m^e z (simplified-ee-symbol-table.md:285-298). This is an unresolved paper/SDD authority conflict, not a settled code-only error.
- C-12’s inference that the legacy rows therefore must be active is overstated. The paper explicitly labels the rows “Legacy execution settings” and says the active contract does not put the legacy cap/PA reference curve into the active EE main formula (ch5-experimental-result.md:45-60). It is still a real execution-parity gap for (3.15a)/(3.16a), because those formulas have no separately traceable active values; the label does not justify silently treating legacy values as active.
- C-14 is not a physical or algorithmic divergence. G0=2000 agrees numerically (antenna.py:45-48; ch5-experimental-result.md:36-42); only the provenance comment says “HOBS boresight gain,” which is documentation drift.
- The controller document says there are 14 items but contains C-1 through C-14 plus a separately numbered C-15 (CONTROLLER-QUESTIONS-2026-08-22.md:47-215). That is a counting/label issue, not a model result.

## (4) Existing items I independently confirm

- C-1: confirmed as a real paper/code contract conflict. The paper’s (4.1)/§5.1 state is 112 (ch4-method.md:13-26; ch5-experimental-result.md:23-25); code requires 125 (state_encoding.py:83-116). The symbol table records the competing 13-field extension, so the audit cannot choose a freeze version.
- C-2: confirmed exactly. Paper recurrence/segment start is at mc-modqn-base.md:237-268; code’s concrete load-concave power is at link_budget.py:134-151.
- C-3: confirmed only as “39 is not implemented and its selection rule is missing.” The code’s J_w=7/C=28 contract explicitly says it is not V (action_contract.py:40-69), and the dynamic grid has no 39-cell freeze.
- C-4: confirmed; paper and code formulas and the 0.015 versus 0.5 dB zenith calculation are explicit (ch5-experimental-result.md:31-35; link_budget.py:93-119).
- C-5: confirmed; no xi or Pp layer exists, while code sums radiated power (mc-modqn-base.md:321-335; link_budget.py:182-192).
- C-6: confirmed; no Pf calculation or P_cir/P_BB constants exist (mc-modqn-base.md:342-360; link_budget.py:182-192).
- C-7: confirmed; the legacy kappa closure is distinct from the paper shared PN denominator (energy_efficiency.py:226-329; mc-modqn-base.md:363-374), and the default trainer still selects throughput.
- C-8: confirmed as an explicit-model gap: no Lc/Ls implementation was found.
- C-9: confirmed: KR=20 dB is in Table 5-2 (ch5-experimental-result.md:39-43), but no Rician path is in the target code.
- C-10: confirmed: no max aggregation over served users; only load-derived beam power exists.
- C-11: confirmed as the stated-paper-versus-code/SDD conflict, with the authority qualification in section (3).
- C-12: confirmed as missing traceable active numeric values, but not as proof that the paper’s legacy rows are active.
- C-13: confirmed numerically: paper 0.001 (ch5-experimental-result.md:64-70) versus code default 0.01 (trainer_spec.py:37-42).
- C-15: confirmed as a real equation/edge-case gap: (4.4)/(4.5) require a in A and sum a=1 even when the mask is empty (ch4-method.md:32-60), while code introduces NO_OP=-1 (action_contract.py:71-88).
- C-14 is independently confirmed only as a provenance/comment update, not as a divergence.

## (5) Equations with no corresponding code

Strictly, the following have no active implementation of the displayed equation in the target tree:

- (3.10a): component helpers exist, but no H=10^(-L/10)GR assembler.
- (3.11) and (3.12): no previous-step angle recurrence or segment-start p0 state.
- (3.12a), (3.12b), and (3.13): no intra/inter interference sums or physical SINR producer.
- (3.15) and (3.15a): no PA efficiency or Pp=p/xi.
- (3.16a) and (3.16): no fixed-power or system-power producer.
- (3.17) and (3.25): additive_system_ee can calculate a ratio only after a caller supplies system power; no active environment produces the paper PN or r1.
- (4.7), (4.8) for the F agent, (4.9), and (4.11): no routing/stratification, separate F discount, intervention, or competitive reward.
- (4.12) for the F agent and (4.13) as an active training contract: only one-agent vanilla TD exists and calibration defaults off.

Partial rather than absent:

- (3.1)–(3.4) have post-mask service/count helpers, but no physical x tensor or connected environment.
- (3.5)–(3.9) have faithful standalone geometry/pattern helpers.
- (3.10c) has a faithful receive-envelope helper, but it is not assembled into H.
- (3.14) has a rate helper with the exact U divisor missing.
- (3.24), (3.27)–(3.29) have Q/reward/classification pieces, but not the paper live EE objective path.
- (4.1)–(4.6) have state/action seams, with the semantic, dimension, no-op, and three-gate deviations above.
- (4.8), (4.10), and (4.12) have only the single MODQN side: one discount, one three-network set, and one vanilla TD update.

The current mc-modqn-base.md has no displayed equations numbered (3.18)–(3.23) or (3.26), so those equation numbers have no paper contract to implement.

## (6) Code with no equation in §3.1/§4

- D2 thresholds, hysteresis, TTT, latching, and altitude floor (env/d2.py:1-39,76-103).
- Earth-fixed dwell/re-keying, candidate dwell sweep, and dwell_phase (env/dwell.py:1-29,41-68).
- Dynamic rectangular-cropped hex lattice, guard rings, coverage marking, and greedy coverage accounting (env/cells.py:125-208).
- Execution-time m^e, decision/execution drift accounting, no-op sentinel, replay dropping, and the outage/semi-MDP gate (env/service.py:23-29,127-198; env/action_contract.py:71-88; runtime/outage_gate.py:1-29,49-141).
- The 13-field contract state—incumbent, D2 timer, radial rate, dwell phase—added to the observation (env/action_contract.py:518-547).
- Load-concave PA, per-link power admission, gamma_req(U) QoS inversion, power codebooks, DPC sidecar, continuous-power sidecar, and configurable power budgets/caps (env/link_budget.py:63-80,134-179; env/service.py:226-250; env/step_types.py:197-315).
- The alternative atmospheric slab model and same-satellite receive-gain override (env/link_budget.py:93-119; env/antenna.py:173-203).
- Random-wandering reflection and the exact turn-law/heading choices (env/mobility.py:1-24,36-52,116-145), plus TLE archive selection/SGP4/WGS-72 and freeze-manifest machinery (env/tle.py:1-29,254-298; env/ephemeris.py:467-500,692-740).
- Legacy/diagnostic EE surfaces (runtime/energy_efficiency.py:226-329), finiteness guards, collapse metrics, preregistration/freezer logic, and reward-calibration switches. These are governance or alternative-runtime behavior, not equations in the supplied §3.1/§4.

## (7) §5.1 value mismatches and traceability

### Table 5-1

| Paper value | Code trace | Result |
|---|---|---|
| Real Starlink, 373 daily files, 2025-07-27..2026-08-20, inclination about 53° | The TLE module repeats 373/date text in a docstring (env/tle.py:1-5), but TleArchive accepts whatever matching files are present and has no inclination constant/check (env/tle.py:254-283). | Not a frozen code constant; numeric agreement cannot be established from code alone. |
| Altitude median 483.0 km, range 470.7–539.7 km | Altitude is computed from each propagated ECEF state (env/ephemeris.py:595-618); no median/range constant is stored. | Cannot determine agreement without the external TLE corpus and a specified aggregation. |
| L_w=4 | NUM_SATELLITE_SLOTS=4 (env/action_contract.py:40-42). | Exact numeric match. |
| U=100 | StepConfig.num_users=100 and MobilityConfig.num_users=100 (env/step_types.py:87-103; env/mobility.py:43-52). | Exact numeric match, though no environment consumes it. |
| V=39 | No V=39 constant. build_cell_grid dynamically creates the lattice (env/cells.py:125-208); probe at 483 km returned 81 total/47 service-area cells. | Mismatch/not traceable. |
| J_w=7 | NUM_BEAM_SLOTS=7 (env/action_contract.py:43-65). | Exact numeric match; code correctly says this is not V. |
| C=L_w J_w=28 | NUM_ACTIONS=4*7=28 (env/action_contract.py:68-69). | Exact numeric match. |
| L_w V=156 | No per-satellite V; code has only the 28-action local candidate domain. | Not represented; cannot trace 156. |
| Delta t=1 s, H=10 | TIME_STEP_S=1, STEPS_PER_EPISODE=10 (env/constants.py:57-63), and StepConfig uses 1 s/10 s (env/step_types.py:96-99). | Exact numeric match. |

### Table 5-2

| Paper value/row | Code trace | Result |
|---|---|---|
| f_c=20 GHz, B_sys=500 MHz | CARRIER_FREQ_HZ=20e9, BANDWIDTH_HZ=500e6 (env/link_budget.py:18-22). | Exact numeric match. |
| chi=0.05 | CHI_DB_PER_KM=0.05 (env/link_budget.py:48-54). | Constant matches; atmospheric formula does not. |
| L_atm=3d chi/(10h) | Code uses chi*10/sin(elevation) (env/link_budget.py:93-119). | Mismatch: 0.015 dB paper versus 0.500 dB code at zenith, +0.485 dB. |
| Three-colour reuse, B^w=166.667 MHz | Reuse factor 3 and derived bandwidth (env/link_budget.py:24-29); cell colour (q-r)%3 (env/cells.py:198-205). | Numeric/rule match, but it is not connected to interference computation. |
| theta_3dB=3.32°, R_b=13.998 km at 483 km | THETA_3DB_DEG=3.32; h*tan(theta/2) (env/cells.py:49-59). Code value at 483 km is 13.9976176468 km. | Exact to the table’s 3 decimals. |
| G0=2000 | G0_LINEAR=2000 (env/antenna.py:42-48). | Exact numeric match; provenance comment is stale only. |
| G_R,max=35 dBi, G_R,min=-10 dBi; A_R=32, B_R=25 | Constants/envelope (env/antenna.py:121-166). | Exact numeric match in the standalone helper; no H assembly. |
| epsilon_mu=1e-10 | Hard-coded limit in the Bessel pattern (env/antenna.py:88-99). | Exact numeric behavior, though not a named constant. |
| K_R=20 dB | No K_R constant or Rician draw. | Missing; numerical channel effect cannot be determined. |
| T_a=150 K, T_0=290 K, NF=1.2 dB, T_sys=242.294 K | link_budget.py:35-46. | Exact numeric match; noise helper is standalone. |
| Pf(t) fixed-power aggregate | No Pf implementation. consumed_power_w is RF-only (env/link_budget.py:182-192). | Missing. Legacy P_cir=.338 W and P_BB=.200 W rows are also not constants. |

Legacy rows in the same §5.1 source are all untraceable except P_beam,max=1.65 W:

| Legacy value | Code result |
|---|---|
| R^m=1 Mbit/s | No default/constant; required_sinr accepts a caller-supplied rate (env/service.py:226-250). |
| P_beam,max=1.65 W | Numeric constant exists as BEAM_POWER_MAX_W=1.65 (env/link_budget.py:61-76), but code treats it as an active per-link admission ceiling (env/link_budget.py:154-179) while paper labels it legacy and excludes caps from active main formula (ch5-experimental-result.md:45-60). |
| p0=2 W | No constant and no recurrence. |
| P0=5.218 W | No constant. Do not confuse it with PA_BASE_W=.25. |
| P_sat,max=19.953 W | No constant; sidecar field dpc_p_sat_max_w defaults to None (env/step_types.py:247-261). |
| xi_max=.35, BO=5 dB | Neither value is present as the paper PA parameter. PA_SCALE_W=.35 is a load-power coefficient, not xi_max (env/link_budget.py:78-81). |
| P_cir=.338 W, P_BB=.200 W | No constants or fixed-power computation. |
| eta0=.35 | No constant. |

### Table 5-3

| Paper value | Code trace | Result |
|---|---|---|
| Omega=(.5,.3,.2) | TrainerConfig.objective_weights (runtime/trainer_spec.py:37-45). | Exact numeric match, used by one MODQN only. |
| phi1=.5, phi2=1.0 | action_contract.py:402-412 and StepConfig (env/step_types.py:101-103). | Exact numeric match. |
| Hidden layers 100,50,50 | trainer_spec.py:37-40; one MODQNTrainer network set (algorithms/modqn.py:123-145). | Widths match; paper requires separate M and F sets, which are absent. |
| Learning rate .001 | TrainerConfig.learning_rate=.01 (runtime/trainer_spec.py:37-42). | Numeric mismatch: code default is 10x the table value; no .001 constant was found. |
| Batch B=128 | trainer_spec.py:40-43. | Exact numeric match. |
| Epsilon 1 to .01 over 2000 episodes; target sync 50 | trainer_spec.py:46-57; epsilon and sync are used by modqn.py:936-1033. | Exact numeric match for the single trainer. |
| E=9000, H=10 | trainer_spec.py:41-44; constants.py:59-63. | Exact numeric match for the single trainer. |
| beta_M=.90, beta_F=.99 | One discount_factor=.9 (trainer_spec.py:40-42; modqn.py:526-533). | beta_M matches; beta_F=.99 is absent. |
| q1=.50, q2=.80, W=5000 | No routing quantiles/window in src/mcrl/algorithms or trainer config. | All missing. |
| rho_I=.30, intervention interval [4,16] | No intervention scheduler or mixed-batch path. | Missing. |
| eta_w=1.0 | No competitive-reward parameter or (4.11) path. | Missing. |
| c=(117217362.202,287.27125,166310676.767) | Calibration is disabled; default scales are (1,1,1) (trainer_spec.py:87-90), and calibration returns raw rewards when disabled (objective_math.py:32-50). | Missing/mismatch. Paper effective weights are (4.265579694e-9, 1.044309168e-3, 1.202568614e-9); code default uses raw (.5,.3,.2). |
