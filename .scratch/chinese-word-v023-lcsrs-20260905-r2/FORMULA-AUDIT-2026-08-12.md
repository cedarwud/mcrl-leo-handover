# Formula consistency audit — 2026-08-12

Status: controller-verified handoff record from the current working tree. This
is a bounded source and build inspection, not an empirical-result declaration.

## Scope and exclusions

Inspected the current `CURRENT-STATE.md`, `docs/ADR-003-canonical-ee-closure.md`,
`src/modqn_paper_reproduction/runtime/angle_aware_ee.py`, the ZH/EN thesis
sources (`mc-modqn-base`, `ch4-method`, and the Chapter 5 settings sources),
`thesis-mc/notation-table.md`, the active v3 preregistration, and the current
`shared_q_isolation` trainer chain. The audit records equation-to-runtime
ownership and the converged semantic decisions listed below.

Explicitly excluded: the ten non-result figure assets and the frozen cover.
Result prose may be edited for readability, but no Chapter 5 result number,
ranking, comparison direction, interpretation boundary, or result claim is
changed or authorized by this record.

## Authority chain

1. `CURRENT-STATE.md` — current phase, gates, and claim ceiling.
2. `docs/ADR-003-canonical-ee-closure.md` — canonical EE semantics, model
   boundary, domains, and cross-project authority.
3. `src/modqn_paper_reproduction/runtime/angle_aware_ee.py` — executable
   angle-aware closure and ratio-of-sums implementation.
4. `thesis-mc/mc-modqn-base.md`, `thesis-mc/ch4-method.md`, their EN sources,
   and `thesis-mc/notation-table.md` — manuscript expression of the ADR.
5. `docs/research/env-foundation/retrain-prereg-family-b-system-ee-contribution-lr001-ep9000-2026-08-06.json`
   — active v3 protocol, calibration, and pre-RL claim boundary.
6. `shared_q_isolation` current trainer/runner and its inherited Family-B
   reward path — consumer wiring evidence; it cannot supersede the ADR or
   runtime.

## Grouped equation mapping

| Equation group | Current semantic mapping and ownership |
|---|---|
| Section 3.1.1 notation; (3.1)–(3.4) | `U,S,V`, binary realized connection `x`, active-beam gate `z`, per-satellite `v_max`, and post-decision actual load `U_{s,v}`. No empty beam transmits. The physical connection is completed by (4.5a), not by a second action definition. |
| (3.5)–(3.10) | Slant range/elevation, off-axis angle, Bessel transmit gain with continuous limit `G^T(0)=G_0` and full-HPBW/half-angle convention, free-space plus atmospheric loss, directional receive gain, and composite `h=G^T G^R G^{LS}g`. The same receive direction is used for wanted and interfering links. |
| (3.11)–(3.14a) | Previous-step intra/interference forms `I_hat`; target `gamma_req(U_{s,v})` uses actual post-decision load; `p_req` uses `h_div=max(h,epsilon_h)`; beam demand is the served-set maximum; `P^{DL}` is pre-satellite-cap; `tilde P^{DL}` is post-satellite-cap actual RF output. Only the actual output feeds signal, coupled interference, PA, power, reward, trace, and evaluation. |
| (3.15)–(3.23) | Piecewise PA efficiency/DC power, `P_0=P_beam,max 10^(BO/10)`, per-beam fixed/PA/event power, color assignment, current coupled intra/inter-satellite interference, realized SINR, TDMA rate using actual load, user throughput, and system throughput. All rates are bits/s and powers are watts. |
| (3.24)–(3.31) | P1/P2/P3, `P_sys=sum P_tot`, formal additive `r_{1,u}=R_u/P_sys` with explicit zero domains, handover cost, fixed 12-slot `F` load-balance reward, reward vector, and formal evaluation `sum_t Delta t_t sum_u R_u / sum_t Delta t_t P_sys`. Mean step EE and mean-user contribution are diagnostics, not the headline ratio. |
| (4.1)–(4.9) | Fixed 28-candidate domain `C`, pre-action state and mask, one-hot candidate action, execution-time mask `m^e`, joint action, congestion context, across-user normalization, and network input. Equation (4.7) applies the implemented fixed scales `n_pre/N_U`, `n_C/N_U`, and `rho/max(n_C-1,1)` before flattening. The physical identity is `x_{u,b_u(c,t)}=a_{u,c}m^e_{u,c}z_{b_u(c,t)}`; bare `x=az` is only the `m^e=1` branch. |
| (4.10)–(4.13) | Catfish transition-bundle stratification, asymmetric discounts, mixed intervention batch, and shared three-head scalarization. Stratification alone uses uncalibrated, unshaped `r_1`; replay and TD consume calibrated views with fixed positive `c_j`, and periodic intervention uses the unshaped calibrated view. Deployment remains per-user `argmax`. |
| (4.14) | Matched catfish/main counterfactuals use the same pre-action state and stochastic realization; both uncalibrated first objectives use (3.26), then form `r^S` and catfish-only `r^C` before both shaped and unshaped vectors are calibrated. Only the catfish critic consumes the shaped calibrated view. An out-of-domain rollout cannot produce a shaping difference. |
| (4.15)–(4.17) | **【2026-08-21 已移除】** 原式 (4.15)–(4.17) 為容量懲罰（penalty shaping）：主代理價值正規化、候選 softmax、偏好質量彙總與每衛星尾端懲罰項 $L_{\mathrm{cap}}$。該整節（原 ch4 §4.5 Penalty Shaping）連同圖 4-8 均已刪除。原式 (4.18)–(4.19) 改編號為 **(4.15)–(4.16)**，見下列。 |
| (4.15)–(4.16) *(原 4.18–4.19，2026-08-21 重編)* | Online Q scalarization selects the shared next action, target heads evaluate that action, terminal/non-terminal TD branches are explicit, and all heads consume `r_j/c_j` with one preregistered scale tuple. |

The ZH and EN sources currently expose the same equation-tag sets by a
read-only tag extraction check (36 Chapter 3 tags in each source and 22
Chapter 4 tags in each source). This is only a source-shape check; it is not a
semantic, DOCX, visual, or runtime validation pass.

## Completed convergence notes

- **Actual load:** `U_{s,v}(t)` and runtime `beam_load_b` are the realized
  serving counts. `gamma_req` cannot use a separate pre-action load; the
  closure checks the load against `serving_beam_u`.
- **Receive gain:** `G^R_{u,s}` is evaluated relative to each user's serving
  direction and applies to both desired and co-channel links. Raw non-negative
  `h` drives received signal, interference, and rate; `h_div` is only the
  `p_req` division floor (`epsilon_h=1e-12`).
- **`P_0` and `Delta t`:** `P_0=P_beam,max 10^(BO/10)` is the single-PA
  saturation reference. `P_tot` includes active RF-chain power, satellite-
  shared baseband allocation, PA DC power, and event energies divided by the
  positive frame duration. Current scenario event energy is `0 J`; this is a
  project assumption, not a measurement.
- **Zero domains:** zero RF output maps to zero PA power; positive RF output
  with non-positive efficiency is invalid. Non-finite or negative rate/power
  is invalid. `throughput>0` with `P_sys=0` is invalid; `throughput=0` and
  `P_sys=0` is explicit zero and flagged. Empty/all-dark transitions close to
  zero. `h=0` may yield finite `p_req` through the division floor but cannot
  create positive received signal or throughput.
- **Execution mask:** movement is followed by fresh execution feasibility
  `m^e`; only `a*m^e*z` produces a realized connection. This records existing
  admission semantics and does not introduce another action space.
  > ⚑ **2026-08-21 狀態更新**：執行遮罩 $m^e$ 保留為環境端帳務，但不再列為塑形策略的貢獻，不得出現在「三種塑形策略」或「現行貢獻」的列舉中。
- **Candidate `q`/`kappa` proxy removed from formal use:** legacy `q` and
  `kappa` allocation remain descriptive diagnostics only. They are excluded
  from formal reward, replay, action selection, checkpoint ranking, and the
  Chapter 5 headline. The `q_{s,v}` hex-grid coordinate in (3.16a) is a
  separate notation and remains valid.
- **Current calibration:** active v3 preregistration freezes
  `(c_1,c_2,c_3)=(117217362.20189127, 287.27125, 166310676.7672135)` from
  non-learning, data-blind calibration. The prior load-only scales and all
  prior EE checkpoints/results remain historical-invalid.

## Current trainer consumer boundary

`family_b_system_ee_contribution()` returns the environment-produced
`result.rewards[uid].r1_system_ee_contribution`; it does not reconstruct a
denominator, antenna gain, `q`, or `kappa`. The current
`shared_q_isolation` runner uses the `ConcatE5Trainer`/`ConcatInjectionRung1Trainer`
chain, whose active override is the 28-action raw/context encoding (196 raw,
392 concatenated dimensions); the reward, decode, replay, TD, and EE guards are
inherited from the Family-B/Route-B path. The E5 probe is read-only telemetry.
This inspection records the consumer route only; it does not authorize a
training run or claim that a run has completed.

## Figure and Chapter 5 boundary

The ten non-result method assets — Figures 2-1, 3-1, and 4-1 through 4-8 — are
unchanged in this scope and remain queued for full redraw, followed by render,
collision/overflow inspection, and human visual acceptance. The cover is
unchanged. Result prose may be naturalized, but its numbers, ranking,
comparison direction, and interpretation boundary remain fixed. No figure-sync
or DOCX build is treated as visual acceptance here.

> ⚑ **2026-08-21 狀態更新**：圖 4-8（容量懲罰梯度步）已隨 §4.5 Penalty Shaping 整節一同移除。現行非結果方法圖為圖 2-1、圖 3-1、圖 4-1 至圖 4-7，共九張。「三個塑形策略」已改為「兩個塑形策略」（經驗塑形與獎勵塑形）；$v_{max}$（每衛星同時啟用波束上限，舊稱 k_cap）已自貢獻機制中刪除，改為場景參數（Table I 的 V=7）。

## Claim ceiling and verification status

This record supports formula/notation ownership and deterministic-readiness
handoff. It does not claim a current RL empirical result, convergence outcome,
baseline comparison, method win, or Chapter 5 result. Calibration is frozen but
no new RL episode/result is authorized by this audit.

The controller rebuilt all three DOCX files from source set
`f131e82a68a3ab08804b230f561eb38c819cb75824f8cdfa6343fc54de2f2e73`.
DOCX structural parity passed with 10 drawings, 58 display equations, 34
headings, and 29 references; the 16 focused manuscript-semantics tests,
state-staleness check, and `git diff --check` also passed. The frozen cover hash
remained `28db3106c98f2beb0ff7a82d8320e50586ff7663c0c0db5b9264d5281c65e0c4`,
and all 428 files under `thesis-mc/figures/` matched their pre-edit hashes.
Figure-sync reported only caption-text notes and passed without resetting its
baseline. Figure redraw, rendered-page visual acceptance, fresh-process prereg
validation, and Ubuntu RL execution remain outside this verification.
