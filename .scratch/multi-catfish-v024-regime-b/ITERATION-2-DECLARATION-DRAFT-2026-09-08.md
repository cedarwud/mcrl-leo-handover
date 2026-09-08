# V0.24 Track-B iteration-2 declaration draft / v2 successor stub

Status: **DRAFT, UNSEALED, NO LAUNCH AUTHORITY.** Identity: `B2_RATE_TARGET_SUM_POWER`.
This versioned successor preserves v1 bytes and records that FD v2 was not pursued after
exposure to related E1 finite-demand diagnostics; the FD v2 map is incomplete and 5 Mbit/s
was untested. This is a priority decision, not an impossibility result.

## Exposure and claim boundary

At `2026-09-08T12:03:54Z`, before this draft, the designer had seen
`ORACLE-MARGINALS-2026-09-08`: finite-demand C3 marginals at 200/50/10 Mbit/s and the
associated service results. B-r2 G0 was also exposed; G1-G3 were not launched.
Track A results may be known before B2 launch. The controller records the actual exposure timestamp
again when sealing. B2 is outcome-informed, reuses E1 development anchors, is not independent
confirmation, leaves earlier failures/incomplete grids visible, and keeps TEST closed.

## One lever and fixed constants

- Lever: rate-derived per-user allocation with summed beam RF power; no sweep or fallback.
- `r*=50e6 bit/s`; provenance: Astra skeleton item 3, magnitude inherited from the memo and
  explicitly synthetic rather than field-calibrated demand.
- `W=500e6/3 Hz`; provenance: `src/mcrl/env/link_budget.py` bandwidth and FRF constants.
- `N0=k*Tsys`, `k=1.380649e-23 J/K`, `Tsys=242.294... K`; provenance: the same link budget.
- `Pbeam<=1.65 W`; provenance: inherited exact code value and Astra skeleton item 6.
- `5 dB` back-off, `xi_max=0.35`, derived saturation, `0.338 W` circuit and `0.200 W`
  baseband; provenance: inherited exact link-budget code values, never retyped for tuning.
- `interval=47*0.640 s`; provenance: canonical simulator clock, reported as 30.08 s.
- fixed-point residual `1e-10 W`, limit `4096`; provenance: Astra skeleton item 5.
- service margin `0.001`, target attainment `>=0.95`; provenance: Astra items 11-12.
- OPS-3 horizon `H<=3`; provenance: inherited OPS-3 and Astra item 8.
- set proposals `top-2` per user; provenance: memo section 3 and Astra item 10.
- `lambda_P`: overridden reference pooled EE, computed before candidate scoring.
- `kappa_P`: mean overridden reference bits per served-user interval, computed before scoring.

`TODO_CONTROLLER_DECLARE: NOMINAL_DECODER_CHANNEL_RULE` — Astra specifies a deployable
nominal decoder and forbids realised fading at selection, but does not choose its exact causal
channel/fading statistic. No value is invented. The runner and both authority builders refuse
to start or seal until a controller supplies it and the matching OPS-3/set adapter is bound.

## Physics and accounting

For scheduled eligible occupancy `n_b`, use uniformly interleaved OFDMA,
`W_u=W/n_b`, `gamma_u=2^(r*/W_u)-1`, and
`q_u=gamma_u*(N0*W_u+I_u)/g_u`. Co-channel interference uses beam-average PSD times
overlap `W_u/W`, excludes the serving beam, and uses ideal instantaneous CSI only inside PHY
power control. Iterate from zero with `P_b=min(1.65,sum(q_u))`; on a capped beam allocate
proportionally to `q_u`. No user removal, repacking, hidden cap relaxation, or convergence
epsilon. Nonconvergence is `INVALID_RUN`.

Retain achieved full-buffer Shannon bits and charge every transmitting beam. Record service,
partial delivery, and `R_u>=0.95*r*` separately. The original-physics control delegates to the
unchanged evaluator and must serialize byte-identically when the override is off.

## Panel, acquisition, and arms

Use every authenticated E1 TRAIN anchor: 4 worlds x 3 lineages x 10 steps. Freeze snapshots,
actions, masks, geometry and keyed fields. Evaluate B2 profiles on detached copies; advance
only the original reference continuation. This replaces the memo's fresh B-carrier panel for
this development screen.

The r2 finite-demand raw tapes are not reused: B2 changes feasibility, RF/interference, rates,
energy and OPS-3, so their scalar B/E rows are invalid. Regenerate per `WORLD:CARRIER` through
the E1 acquisition path and bind all E1/r2 input digests and snapshot-purity receipts.

Arms: `ORIGINAL_PHYSICS_CONTROL`, `REFERENCE`, exact `O1`, `O12`, additive LC-SRS `O123`, `SET_PRIVILEGED`,
`SET_DEPLOYABLE_NOMINAL`, literal `DROP_C1_O23`, `DROP_C2_O13`, `DROP_C3_O12`.
Also report `OTHERS_BIT_SUBSTITUTION_O123` separately; it is not LC-SRS and not a main arm.
Composition is one unweighted masked argmax with the inherited lowest-index tie rule.

Set arms share the proposal-derived catalog, guards and lexicographic ties: reference, each
user's top-2 unilateral proposals, and complete evacuations to a common proposal-member
destination. Set success cannot substitute for additive C3 success.

## Outputs, gates, and progression

Report pooled EE, bits, joules, service, rate-target guard, all three FULL-minus-DROP oracle
marginals, `U1`, `J1`, interaction, global-witness `J-U` direction in each world, certificates,
and every failure. Require all three oracle marginals strictly positive.

Map qualification is the conjunction: `J/reference-1>=5%`, `(J-U)/reference>=1%`, signed
interaction/reference bits `>=0.5%`, and global-witness `J-U>0` in at least 3/4 worlds.
Every arm must have service `>=reference-0.001`; rate-target attainment must be `>=95%` and
`>=reference-0.001`. Exact-rational Dinkelbach/service DP and independent certificates remain.

One valid completed probe supports only a conditional matched-anchor mechanism result. An
oracle pass does not establish learned efficacy. After qualification: obtain fresh B lineages,
recheck against trained M12, then evaluate learned FULL-versus-each-DROP under a separately
sealed campaign. Failure does not prove C3 impossible; invalid/incomplete runs have no
scientific verdict. At most two single-thread B workers may use genuinely spare compute and
must yield to Track A.
