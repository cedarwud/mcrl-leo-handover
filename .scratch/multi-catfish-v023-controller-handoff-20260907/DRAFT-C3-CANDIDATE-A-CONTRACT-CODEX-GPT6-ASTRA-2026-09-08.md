**0. Status, disclosure and admission**

**C-A: OPS-3 action-set coalition value with fixed allocation. DRAFT_PRE_OUTCOME; UNSEALED; NO_LAUNCH.** Declared before any E1 outcome. No files changed, network accessed, SSH used, or experiment executed.

Following STOP_PHYSICS_R7 and FAST_SCREEN_NO_SUPPORT, we prospectively declared this separate development experiment from physical principles and explicit exclusions; historical outcomes motivated reconsideration but did not select its formulas, deployment parameters, worlds, seeds, horizons, lambda or acceptance rules. Previous failures remain unchanged; reused checkpoints and exploratory evidence are disclosed; TEST remains closed.

Under E1 §3, C-A may be executed only after:

- `E1_UNILATERAL_HEADROOM` + `E1_JOINT_HEADROOM`; or
- `E1_UNILATERAL_CLOSED` + `E1_JOINT_HEADROOM`.

Joint CLOSED, `INVALID_RUN`, or `INCOMPLETE` authorises no C-A screen. Even an eligible cell requires this contract’s seal, implementation review, resolved bindings, and separate launch authority. E1 authorises the family; it does not establish C-A’s observability, composition, or efficacy.

**1. Mechanism**

A complete origin-beam evacuation can remove circuit charges, potentially remove an active satellite’s baseband charge, and alter destination beam maxima, amplifier supply, interference and bandwidth sharing. With three or more members, shutdown can require higher-order joint adoption that no two-player game represents.

R7 already tested last-pair shutdown through four profiles and \(z_i=e_i+\Psi/2\); “coalition” and “shutdown” alone are not novel. C-A instead enumerates every subset of each named evacuation set, uses its full characteristic function, and subtracts an explicitly declared C1/C2 overlap.

This differs from PNFE’s stopped held-background unilateral target, ZR’s unilateral externalities, V0.14–V0.20 information/learner variants, and F1’s stopped D/F accounting targets. OPS-3 projections are not a new adaptive trajectory mechanism; PNFE already included future offsets.

**Under-specification chosen:** require at least one catalogue proposal with three members to expose the claimed higher-order mechanism. Absence closes this candidate’s screen without revising the requirement.

**2. Interface**

Freeze one immutable predecision packet before scoring:

- Native Q1 state: 228 values; native Q2 OPS-3 state: 448 values, unchanged.
- All users’ legal 28-slot masks, physical `(NORAD, cell)` identities, detached frozen Q1/Q2 scores and BASE reference actions.
- Committed previous associations, service, beam/satellite occupancy, link powers, segment ages and dwell/D2 state.
- Current geometry, archived TLE identities, and deterministic median/no-fading OPS-3 projections.
- Explicit named proposal membership, origin, destination and each member’s proposed action.

BASE actions and proposals are reference messages fixed before focal scoring, **not others’ committed same-slot actions**. No final same-slot C-A choices, realised fading, counterfactual rates, service outcomes, energies or labels enter deployed inputs.

**Under-specification chosen:** proposal construction uses detached BASE action-key occupancy. E1 instead uses BASE’s realised served occupancy. These cannot silently be equated. The oracle records both catalogues; any membership/catalogue discrepancy blocks support as `INTERFACE_CATALOG_MISMATCH`. Realised membership must never repair the deployed packet.

For each origin, enumerate every distinct commonly legal destination; include singletons and empty destinations, exclude unserved reference users, sort physical keys lexicographically, retain duplicate-profile aliases and every unfavourable proposal.

**3. Formula**

Let \(p\) denote an anchor, \(b\) its BASE vector, \(C\) one named proposal, \(M_C\) its members, and \(m=|M_C|\). For \(S\subseteq M_C\), \(x_S\) replaces precisely those members’ BASE actions by their proposed actions; everyone else retains BASE.

**Under-specification chosen:** extend OPS-3 to complete joint profiles, retaining its projected-persistence convention rather than summing unilateral power deltas.

Use \(H_p=\min(3,T-1-t)\), native interval \(\Delta=47\times0.640\) seconds, fixed action identities, frozen user positions, cloned D2 projection, median/no-fading channels and absorbing service loss. Recompute joint bandwidth, interference and canonical network power at each offset; no future policy or adaptive branch is introduced.

For offset \(h\), let \(R_{vh}(S)\) be delivered rate, \(\chi_{vh}(S)\) the OPS-3 opening-and-persistence indicator, and \(P_h(S)\) total canonical system power. Define

\[
A(S)=\frac1{H_p}\sum_{h=1}^{H_p}
\left[\Delta\sum_vR_{vh}(S)-\kappa\sum_v(1-\chi_{vh}(S))\right],
\quad
E(S)=\frac{\Delta}{H_p}\sum_hP_h(S),
\]

\[
V_C(S)=A(S)-A(\varnothing)-\lambda[E(S)-E(\varnothing)].
\]

Here \(A,V\) have units bits; \(A\) includes the inherited OPS-3 service-risk penalty and is **not delivered bits**. \(E\) is joules. For \(H_p=0\), set \(V_C(S)=0\). Preserve uncapped recurrence and native feasibility predicates.

\[
\lambda=118424222.8550065\ {\rm bits/J},\qquad
\kappa=10097071012.757404\ {\rm bits}.
\]

The prospectively fixed allocation is exact Shapley:

\[
\phi_u(V_C)=
\sum_{S\subseteq M_C\setminus\{u\}}
\frac{|S|!(m-|S|-1)!}{m!}
[V_C(S\cup\{u\})-V_C(S)].
\]

**Overlap is under-specified in the memo. Chosen accounting definition:**

\[
d_{12,u}=
[B_u(x_{\{u\}})-B_u(b)]
-\lambda[E^0(x_{\{u\}})-E^0(b)]
+\kappa[y_{2,u}(a_C)-y_{2,u}(b_u)],
\]

where \(B_u,E^0\) are current-interval delivered bits and total network joules; \(y_2\) is the unchanged repriced OPS-3 normalised C2 target, evaluated with its authenticated reference convention.

\[
\boxed{z_u(p,a_C;C)=\phi_u(V_C)-d_{12,u}}
\]

This declares analytic overlap, not \(\kappa(Q_1+Q_2)\); predicted heads need not equal it. Positive \(z\) adds score; negative \(z\) subtracts score. No sign filtering.

Toy example: three members have \(V(\varnothing)=0\), every nonempty proper subset worth \(-3\) bits, and \(V(M_C)=12\) bits. Symmetry gives each \(\phi=4\) bits. If \(d_{12}=(1,2,3)\), then \(z=(3,2,1)\) bits and \(\sum_u(d_{12,u}+z_u)=12\). Partial adoption need not realise that allocation.

**4. Deployment**

Populate each member’s corresponding action row with its proposal-conditioned \(z\). The origin/destination construction makes the row’s proposal unique. BASE and legal noncatalogue rows receive zero; illegal rows are unselectable.

Apply exactly

\[
a_u^\star=\operatorname{masked\,argmax}_a
[Q_{1u}(a)+Q_{2u}(a)+z_u(a)/\kappa].
\]

Use F1 arithmetic: frozen float32 Q1+Q2 surface promoted to float64 for composition. Exact ties choose the lowest legal action index. An all-false mask emits `NO_OP_ACTION=-1`. Reject duplicate legal physical aliases as F1 does.

No joint decoder, adoption negotiation, retry or repair follows. Evaluate the resulting complete vector physically. Simultaneous mixed proposals and partial adoption may invalidate the allocation’s usefulness; that is tested, not assumed away.

**5. Matched oracle kill screen**

Reacquire fresh tapes on E1 worlds:

`861587764845384088`, `3943897440191533562`,  
`5747196377242098234`, `4004348767321774260`.

Cross all four with authenticated rung-003000 lineages `2026092101–03`; 100 users; exactly steps 0 and 1: 12 units, 24 anchors, 2,400 service opportunities. Worlds are reused from E1, not independent confirmation after E1; checkpoint lineages are also reused.

BASE is each lineage’s masked `argmax(Q1+Q2)`. Substitute exact \(z\) for the learner. Evaluate BASE, all requisite subset profiles/projections, full proposals and composed C-A actions from identical snapshots and keyed fields. Commit only BASE between anchors. Verify state/RNG immutability and committed-BASE agreement.

Retain full-adoption and partial-adoption receipts; never reconstruct joint physics from unilateral rows. Catalogue EE headroom does not guarantee composed-policy headroom.

**Under-specified pooling chosen:** one global ratio-of-sums and service fraction, without lineage votes:

\[
\eta_X=\frac{\sum_pB_{pX}}{\sum_pE_{pX}},\qquad
s_X=\frac{\sum_p n^{served}_{pX}}{2400}.
\]

Physical \(B=\Delta\sum R\); physical \(E=\Delta P_{\rm system}\). Use corrected F0 power/share checks and E1’s lossless binary64-to-rational comparisons.

Emit `C_A_FAST_SCREEN_SUPPORT` only with complete valid receipts, catalogue/interface agreement, higher-order exposure, at least one legal physical action change, \(\eta_A>\eta_{\rm BASE}\), and \(s_A\ge s_{\rm BASE}-0.001\).

Otherwise valid completion emits `C_A_FAST_SCREEN_NO_SUPPORT`, permanently closing C-A. Record every applicable reason: `EE_NOT_IMPROVED`, `SERVICE_FAILED`, `NO_ACTION_CHANGE`, `NO_HIGHER_ORDER_EXPOSURE`, `INTERFACE_CATALOG_MISMATCH`. Partial-adoption losses are additionally reported, without an invented threshold.

Malformed physics, leakage, provenance or replay yields global `INVALID_RUN`; interrupted acquisition yields `INCOMPLETE`. Repair only evidenced infrastructure defects; preserve valid outcomes.

**6. Later learner screen: declared, unauthorised**

Require the exact §2 encoder shared by source and inference, proposal membership/action tokens, all subset labels, \(d_{12}\), allocation-conservation checks and immutable provenance. Oracle-only fields remain label-side.

A later separately frozen gate must establish accessible-information prediction against matched placebo on held-out worlds, literal learned composition, physical EE/service support and independent C1/C2 context checks. Architecture, training budget, fresh worlds/seeds and predictive thresholds are presently unspecified; bind them prospectively under separate authority. No training or F2/F3 reopening is authorised here.

**7. Forbidden moves**

No clipping, gating, sign filtering or rescaling revival of D/F; residual-based formula ranking; favourable-world selection; tuning against `2026121721` or any E1 world; changing \(H,\epsilon,\kappa,\lambda\), signs, margins or acceptance rules. No approximate/sample Shapley substitution, coalition-size truncation, selective reruns, automatic admission or TEST opening. No tie band is used; \(\epsilon=0\).

**8. Cost**

F1 scaling is \(383\times12=4596\) seconds: **1.28 serial hours before joint/OPS-3 overhead**. Exact allocation requires up to \(2^m\) subset profiles per proposal and three offsets; this can greatly exceed F1.

Under-specified budget chosen: 16 worker-hours acquisition/verification; exhaustion means `INCOMPLETE`, never truncation. Profile-count estimates precede launch; resource-only extensions require logged authority.

**9. Freeze checklist**

Bind and review every interpretation before outcomes; placeholders cannot conceal scientific choices:

- `<<BIND_AT_FREEZE:BODY_SHA256_TIMESTAMP_REVIEW>>`
- `<<BIND_AT_FREEZE:MEMO_E1_REVIEW_R7_LADDER_F1_AUTHORITY_DIGESTS>>`
- `<<BIND_AT_FREEZE:ELIGIBLE_E1_CERTIFIED_CELL_AND_LAUNCH_AUTHORITY>>`
- `<<BIND_AT_FREEZE:THREE_CHECKPOINTS_AUTHORITIES_LAMBDA_KAPPA>>`
- `<<BIND_AT_FREEZE:ENCODER_CATALOGUE_OPS3_OVERLAP_FORMULA_VERIFIER_DIGESTS>>`
- `<<BIND_AT_FREEZE:WORLD_FIELD_RNG_TLE_PREREG_MANIFESTS>>`
- `<<BIND_AT_FREEZE:EXACT_ALLOCATION_POWER_REPLAY_VALIDATION>>`
- `<<BIND_AT_FREEZE:CODE_ENVIRONMENT_PROFILE_COUNTS_BUDGET_OUTPUT_ROOTS>>`

Each artifact binding requires path and SHA-256. Claim ceiling: TRAIN development oracle screen; no learner admission, generalisation or efficacy claim.

ASTRA_CANDIDATE_A=DRAFTED