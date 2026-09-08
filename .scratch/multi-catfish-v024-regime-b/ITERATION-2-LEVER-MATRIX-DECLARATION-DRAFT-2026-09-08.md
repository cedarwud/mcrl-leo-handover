# V0.24 Track-B iteration-2 parallel lever-matrix declaration draft

Status: **DRAFT, UNSEALED, NO LAUNCH AUTHORITY, NO COMPUTE PERFORMED**.
Matrix identity: `B2_LEVER_MATRIX_L1_L12_L2_L4`. Split: TRAIN only; TEST stays closed.

## Scope, panel, and exposure

This successor uses all B-r2 development anchors: 4 worlds × 3 fixed reference
carriers × 10 anchors, 100 users. The carriers are `nearest-eligible` (first legal
satellite-major/beam-minor action), `stay-if-possible`, and `random-masked`; they
are fixed rules, not trained lineages. No Track A checkpoint enters the panel.

Freeze masks, physical action keys, references, TLE/geometry, carrier seeds, and
keyed fading. Original physics advances the reference trajectory; overrides run
on detached evaluations. Keyed fading retains event `physics`. Include the
byte-identical `ALL_NEUTRAL_CONTROL`; it is never relabelled `BASELINE`.

Known before this draft: finite-demand C3 marginals −1.3866%, −0.7524%, and zero
at 200/50/10 Mbit/s; S0 +1.8126% one-step evidence; and B-r2 G0 results (J₁
+6.5501%, U₁ +6.4346%, J−U only 0.1155% of reference EE, interaction −1.5777%).
G1–G3 were not launched. FD v2 was not pursued after related E1 exposure; its map
is incomplete and 5 Mbit/s is untested. This is outcome-informed development,
not independent confirmation or an impossibility result. The sealing team must
append hashes/access times for any Track A closed-loop results known before seal.

## Common constants and estimands

Every constant is code-bound and has provenance; no outcome-selected values exist.

| Constant | Value/formula | Provenance |
|---|---|---|
| carrier frequency | 20 GHz | inherited link budget; TR 38.821 scenario |
| beam bandwidth | `500e6/3` Hz | inherited frequency-reuse/link-budget code |
| Boltzmann constant | `1.380649e-23` J/K | inherited link-budget code |
| system temperature | `150+290*(10^(1.2/10)-1)` K | inherited TR 38.821 link budget |
| legal RF cap | 1.65 W | inherited scenario/code value |
| PA saturation | `1.65*10^(5/10)` W | inherited 5 dB back-off formula |
| original max efficiency | 0.35 | inherited scenario/model assumption |
| circuit power | 0.338 W/active beam | inherited You et al. mapping assumption |
| baseband power | 0.200 W/active satellite | inherited You et al. assumption |
| interval | native `47*0.64` s representation | inherited simulator clock |
| service margin | 0.001 | Astra common qualification Q |
| OPS-3 horizon | `min(3,T-1-t)` | inherited OPS-3 definition |
| set proposals | top 2 O12 proposals/user | Astra common set catalog |

For each lever, compute `lambda=sum(B_ref)/sum(E_ref)` and
`kappa=sum(B_ref)/N_served,ref` before candidate scoring. C1 is
`(delta focal bits-lambda*delta network joules)/kappa`. C2 keeps frozen
background, absorbing service loss, offset averaging and reference centering;
its imported normalized values receive no second division. C3 keeps the R7 pair
selector and LC-SRS target `(e_i+Psi_ij/2)/kappa`, where
`V(S)=delta B_N-lambda*delta E_N` and `Psi=V(ij)-V(i)-V(j)`.

## Declared levers and provenance

Priority is **L1 → L12 → L2 → L4**. Every lever receives every probe; priority
does not permit hiding or skipping unfavorable results.

### L1 — `B2_L1_RATE_TARGET_SUM_POWER`

Use independent uniformly interleaved subchannels. Before power feasibility,
`n_b` counts scheduled eligible users; `W_u=W/n_b`, synthetic
`r*=50e6 bit/s`, and `gamma=2^(r*/W_u)-1`. The target magnitude is inherited
from the memo/Astra declaration and is not calibrated traffic.

Use `q_u=gamma*(k*Tsys*W_u+I_u)/g_u`, with co-colour beam-average-PSD
interference scaled by `W_u/W`, excluding the serving beam. Iterate from zero:
`P_b=min(1.65,sum_u q_u)`. Allocate capped power proportionally to `q_u`.
Residual tolerance `1e-10 W` and limit 4096 are Astra L1 numerical declarations.
No dropping, admission ceiling, repacking, or cap relaxation. Nonconvergence is
`INVALID_RUN`. Retain achieved Shannon bits and original PA/fixed energy; record
partial delivery, cap hits, residuals, power conservation, and 95% target
attainment separately from service.

R2 RF/rate rows are invalid for L1. Authenticate the r2 tapes as anchor/control
provenance, replay the same exogenous states, and regenerate RF, interference,
rates, energy, profiles and OPS-3. `--estimate` must say `REGEN_REQUIRED`.

### L12 — `B2_L12_RATE_TARGET_DEVICE_PA`

Run exactly L1 through RF allocation/rates/service, then exactly L2's DC curve.
For the same complete action, L1/L12 RF powers, SINR, bits, and service must be
identical; only energy and energy-dependent targets/selections may differ. Share
new RF primitives, not receipts or decisions. R2 physics needs regeneration and
`--estimate` says `REGEN_REQUIRED`. No PA distortion/allocation feedback is added.

### L2 — `B2_L2_PIACIBELLO_SURROGATE`

Keep original max-user beam RF physics, rates, service, activations and fixed
power. For `q=p/P_sat`, `q6=10^(-6/10)`, `G=100`, use
`e(q)=0.20*sqrt(q/q6)` below the knee and
`e(q)=0.20+0.07*(q-q6)/(1-q6)` above it. DC power is zero at zero and otherwise
`max(1.32 W,p*(1-1/G)/e(q))`. Reject out-of-domain power.

0.20/0.27 are declared midpoints of cited 6 dB/saturation PAE ranges; `G=100`
is a 20 dB midpoint approximation; the low branch is the chosen Cripps
approximation. `1.32=11(0.050)[2(0.8+0.3)+0.2] W` is a derived bias proxy.
Reprice each active beam from stored per-user RF/physical keys; never globally
scale old energy. R2 RF/rate rows remain read-only valid inputs; missing
OPS-3/LC-SRS/composed profiles still require authenticated supplements.

### L4 — `B2_L4_CONTROL_EVENT_ENERGY_PROXY`

Keep payload physics unchanged. Count each non-NOOP physical association change
from the authenticated predecision `(NORAD,cell)` key, including failed service;
count each distinct destination beam once for shared setup. Never compare action
indices. Initial state must be replay-authenticated.

Use `t_b=500 us`, `t_fb=t_ack=50 us` from the cited HOBS timing proxy.
`P_tx=sqrt(Pmax*Psat)/0.35+0.338 W`; `P_rx=0.338 W`.
`e_b=P_tx*t_b`, `e_u=P_rx*t_fb+P_tx*t_ack`, unrounded. Add
`e_b*N_setup+e_u*N_HO` once at the anchor; do not repeat it over OPS-3 offsets
unless that projection actually contains a new event. These are constructed
power×timing joules, not measured handover energy. R2 payload rows remain
read-only inputs; event/OPS-3/composed supplements are authenticated separately.

## TODO_CONTROLLER_DECLARE (launch blockers)

- L2 and L12: verify actual gain/PAE curves, bias-floor interpretation and
  omitted currents, low-power behavior, temperature/interpolation to 20 GHz,
  amplifier-to-beam mapping, and CW-to-multicarrier back-off/distortion scope.
- L4: verify the incremental resource boundary, event applicability, and actual
  subsystem event-energy measurements.

The overrides are implemented, but the runner and per-lever authority builder
refuse these levers until the controller resolves the corresponding source-model
declarations. No post-outcome refit is allowed.

## Arms, set decoder, reports, and gates

Evaluate `REFERENCE`, O1, O2, O12, additive O123, literal DROP_C1/O23,
DROP_C2/O13, DROP_C3/O12, `SET_PRIVILEGED`, `SET_NOMINAL`, and
`ALL_NEUTRAL_CONTROL`. Named subsets use only named exact heads. Composition is
one simultaneous unweighted masked argmax with lowest-index ties and existing
empty-mask NOOP.

Both set decoders use the same proposal-membership catalog and service rule:
reference, each user's top-2 O12 proposals, and permitted complete evacuations.
Score `delta B-lambda*delta E+kappa*sum(delta q2)`. Privileged selection may use
realized profiles; nominal selection must use causal nominal scores/predicted
service. Ties are lexicographic. Set success cannot qualify additive C3.

Report every arm's bits, joules, pooled EE, service and applicable attainment,
globally, in all four worlds, and by carrier as a non-selective diagnostic.
Report all three `eta_123-eta_DROP` marginals in bit/J and DROP-relative percent,
U1/J1 exact certificates, signed interaction, the two global witnesses'
per-world J−U direction, and every guard.

Map gates are: `J/reference-1>=5%`, `(J-U)/reference>=1%`, signed
interaction/reference bits `>=0.5%`, and global-witness J−U positive in at least
3/4 worlds. Service is at least reference−0.001. L1/L12 also require attainment
at least 0.95 and reference−0.001. All three additive marginals must be strictly
positive with applicable guards.

For each FULL−DROP report delta bits, delta joules, and
`delta bits-eta_DROP*delta joules`; identify bits/energy movement. Decompose
interaction into bits, PA, fixed-circuit, event and other energy. Include each
lever's mechanism ledger, intended versus realized composition surplus, changed
users, disagreements, service losses, and set-versus-additive conversion.

Use `NO_SUPPORT` only after complete valid evidence. Keep `REGEN_REQUIRED`,
`INCOMPLETE`, `INVALID_RUN`, and unresolved source limitations distinct.

## Multiplicity and progression

This is one outcome-informed parallel matrix whose priority and selection
function are fixed before matrix outcomes. Every lever gets map plus oracle
marginals even if its map fails. After complete adjudication, the first lever in
priority order satisfying map, three-positive-oracle, and guards proceeds. Do
not select by largest gain, runtime, favorable world, or revised parameter. An
unresolved higher-priority lever cannot be silently skipped. Later M12/campaign
failure does not authorize fallback. A future matrix is a disclosed successor.

This supersedes the earlier sequential map-point-first rule. It fixes the
selection function, not outcome independence. At most two single-thread Track-B
workers may use genuinely spare capacity and must yield to Track A. Confirmation
requires fresh B policies/worlds, strong-M12 requalification, learned FULL/DROP
guards and declared paired confidence intervals; no oracle result is efficacy.
The three-head conjunction within a selected campaign does not establish
familywise significance across this lever search.
