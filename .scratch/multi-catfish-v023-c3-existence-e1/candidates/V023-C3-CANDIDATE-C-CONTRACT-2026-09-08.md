**0. Status, disclosure and admission**

**C-C: exact-primary-tie network-energy selector. DRAFT_PRE_OUTCOME; UNSEALED; NO_LAUNCH.** This separate deployment contract prospectively fixes mechanism, interface, target, decoder, panel and falsifier before E1 outcomes.

Following STOP_PHYSICS_R7 and FAST_SCREEN_NO_SUPPORT, we prospectively declared this separate development experiment from physical principles and explicit exclusions; historical outcomes motivated reconsideration but did not select its formulas, deployment parameters, worlds, seeds, horizons, lambda or acceptance rules. Previous failures remain unchanged; reused checkpoints and exploratory evidence are disclosed; TEST remains closed.

Authority: the specified future-path memo, accepted E1 contract/controller review, sealed C1/C2 declaration, F1 package, and R7 balanced-successor/original observability contracts.

**Under-specification—family:** the memo does not map its tie-breaker to E1’s intervention classes. Plainest admissible reading chosen: **at most one user changes per anchor**, selected deterministically below. Unrestricted simultaneous tie-breaking is outside this contract.

Execution is eligible only in E1 §3 cells:

- `E1_UNILATERAL_HEADROOM` + `E1_JOINT_HEADROOM`;
- `E1_UNILATERAL_HEADROOM` + `E1_JOINT_CLOSED`.

Joint-only headroom, both CLOSED, INVALID_RUN or INCOMPLETE authorise no C-C execution. Even an eligible cell requires independent review, sealing and launch authority. Drafting now is unconditional; admission remains conditional. No efficacy, learner admission or TEST access follows.

**1. Mechanism**

The event is **physically distinct legal actions receiving exactly equal maximal float32 Q1+Q2 scores while inducing different total network energy**. C3 selects the lower-energy tied alternative without sacrificing the primary score.

Energy differences can arise through amplifier supply, beam activation and satellite baseband charges. Earlier designs already represented these physical costs; the novelty is their use inside a strictly preserved primary optimum, not discovery of new energy physics.

Required distinctions:

- PNFE `FAIL_ORACLE_GATE` and ZR `STOP_THREE_HEAD`: no independently selected simultaneous unilateral changes; other actions are binding commitments.
- Learned-context `REJECT_HYPOTHESIS`, V0.15-R `FAIL_REFERENCE_GATE`, V0.18 `STOP_LEARNER_GATE`, and V0.20 `REVISE_NOMINAL_Q3`: no centering repair or assertion that information/learning problems are solved.
- R7 `STOP_PHYSICS_R7`: no named two-player 00/10/01/11 game, equal allocation \(e_i+\Psi/2\), or additive residual deployment.
- F1 `FAST_SCREEN_NO_SUPPORT`: no D/F energy-share correction or additive score displacement.

**Under-specification—novelty:** the records support an untested decoder, not a claim that prior designs never encountered energy differences. That narrower claim governs.

**2. Interface**

The deployed central scheduler receives only:

\[
I_t=(S_1,S_2,q,M,b,f),
\]

where \(S_1\) is the authenticated roster of Q1 inputs, shape \(100\times228\); \(S_2\) is the authenticated feature-major OPS-3 Q2 input roster, \(100\times448\); \(q\) is the float32 Q1+Q2 surface, \(100\times28\); \(M\) is the Boolean native mask; \(b\) is the BASE action vector; and \(f\) is the selected focal user or NONE.

Existing encoders, field order, units and target-free projections are frozen by source hashes. Native action-to-physical-key tables support identity validation, not additional learned features.

**Under-specification—C3 carrier:** choose this explicit whole-roster interface; no existing successor C3 implementation is implied. A preflight field audit must verify availability before physics evaluation.

Compute BASE once. Select \(f\) from masks, physical identities and exact ties alone. Then irrevocably reserve every non-focal action to \(b_v\) **before** the focal C3 decision. Reservations are commands, not realised service outcomes; no physical advance occurs between reservations and selection.

No current realised fading, candidate rates, candidate energy, service resolution, future observations, or uncommitted same-slot actions enter deployed C3. Historical measurements already legitimately present in the authenticated inputs retain their original timing.

**3. Formula**

For focal user \(u=f\), legal tied action \(a\), and reserved background \(b_{-u}\), let \(x^{u,a}=(a,b_{-u})\). Define:

\[
z_u(a;\omega)=-E_t(x^{u,a};\omega)
=-\Delta t\,P_{\rm system}(x^{u,a};\omega).
\]

Here \(t\) is the anchor; \(\omega\) is the matched physical field; \(E_t\) is total network interval energy in joules; \(P_{\rm system}\) is canonical network power in watts; and \(\Delta t=30.08\) seconds. Higher \(z\) means lower energy.

The oracle substitutes exact tape-derived \(z\). A later learner would estimate \(Q_{3u}(I_t,a)\approx\mathbb E[z_u(a;\omega)\mid I_t]\), in joules.

**Under-specification—target:** choose total network energy, not a cost share, externality, residual or surplus. No division by \(\kappa\) applies to this secondary joule score. Frozen \(\kappa=10097071012.757404\) bits and \(\lambda=118424222.8550065\) bits/J continue authenticating Q1/Q2; neither modifies \(z\).

Toy example: legal scores are \((0.5,0.5,0.4999999701976776)\), with energies \((10,9,1)\) J. BASE chooses slot 0. Scores \(z=(-10,-9,-1)\) select slot 1 among the two exact maximisers. Slot 2 remains excluded despite its lower energy. Service and delivered bits still require screening.

**4. Deployment rule**

Compute exactly:

\[
q=\operatorname{float32}
(\operatorname{float32}(Q_1)+\operatorname{float32}(Q_2)),
\quad
T_u=\{a:M_{ua},\ q_{ua}=\max_{j:M_{uj}}q_{uj}\}.
\]

Use exact float32 numerical equality, including equality of signed zeros; \(\epsilon=0\). No approximate comparison, rounding or score perturbation.

BASE \(b_u=\min T_u\). Choose \(f\) as the lowest native user index whose \(T_u\) contains at least two distinct physical actions. If none exists, return BASE.

For \(u=f\), choose the highest C3 score within \(T_u\), resolving secondary ties by lowest native action index. Everyone else retains BASE. Thus every selected action remains a masked Q1+Q2 maximiser.

**Under-specification—scheduler:** fixed lowest-index selection prevents outcome-dependent focal ranking and confines deployment to E1’s unilateral class.

All-false masks emit `NO_OP_ACTION=-1`; NOOP is never an extra competitor. Reject duplicate legal physical aliases as F1 does. Missing/non-finite required scores or malformed masks invalidate the run. There is no additive `Q1+Q2+z/κ` composition.

**5. Two-step matched oracle kill screen**

Use all four E1 worlds, in declared order:

`861587764845384088 / 3943897440191533562 / 5747196377242098234 / 4004348767321774260`.

Cross with authenticated rung-003000 Q1/Q2 lineages `2026092101–03`, including their original authorities and Q2 initialisations `2026108101–03`. These are reused reference lineages, not the three successor ablation arms.

Use fresh environments, TRAIN only, 100 users, canonical steps 0 and 1: **12 units, 24 anchors, 2,400 service opportunities**. Bind E1’s TLE, PREREG, environment/mobility RNGs and keyed-field component `MCRL_V023_LCSRS_C3_OBSERVABILITY_V1`.

At each anchor evaluate BASE and every focal tied candidate against identical state/field. Substitute exact \(z\) for the learner, execute the declared selector and authenticate its complete physical profile. Counterfactual evaluation must preserve state/RNG. Commit only BASE between anchors.

**Under-specification—freshness:** these worlds are fresh relative to historical experiments but shared prospectively with E1. Reacquisition does not make C-C independent confirmation.

Pool additive bits \(B=\Delta t\sum_uR_u\), network joules and served counts across all 24 anchors:

\[
\eta_A=\frac{\sum B_A}{\sum E_A},\qquad
s_A=\frac{\sum C_A}{2400}.
\]

Use losslessly serialized binary64 accounting scalars as exact rationals for decisions, following accepted E1 arithmetic. Require positive energy and corrected F0 canonical-power/conservation checks.

**Under-specification—pooling:** choose one global comparison; world/lineage breakdowns are descriptive, with no direction-vote gate.

Emit `C_C_FAST_SCREEN_SUPPORT` iff integrity passes, at least one legal physical action changes, \(\eta_C>\eta_{\rm BASE}\), and \(s_C\ge s_{\rm BASE}-0.001\). Otherwise a complete valid panel emits `C_C_FAST_SCREEN_NO_SUPPORT`, which **closes C-C**.

Record all applicable reasons: `NO_EXACT_TIE_EXPOSURE`, `NO_LEGAL_CHANGE`, `EE_NOT_ABOVE_BASE`, `SERVICE_NONINFERIORITY_FAILED`. Integrity failure yields global `INVALID_RUN`, never scientific support/closure. Interrupted valid acquisition is `INCOMPLETE`. Infrastructure repairs preserve scientific choices and replay only affected invalid units; valid unfavourable outcomes cannot be rerun selectively.

**6. Later learner screen: declared, not authorised**

It would require frozen implementations of §2, explicit reservation receipts, and matched labels \(-E_t(x^{u,a})\) for every eligible tied action, including BASE, without sign filtering.

Gate requirements: target-free deterministic inference; held-out-world prediction against an equal-budget neutral control; unchanged exact-tie deployment; and positive pooled EE with the same service margin and legal-change requirement.

Architecture, learner seeds, training budget, neutral construction, held-out panel and predictive thresholds are **under-specified**. They require a separate prospective contract before learner outcomes. This draft authorises none.

**7. Forbidden moves**

No clipping, gating or rescaling revival of D/F; residual ranking; favourable-world selection; tuning against any E1 world or `2026121721`; changing signs, targets, masks, scheduler or acceptance rules; widening \(\epsilon\); changing \(\kappa,\lambda\), or inherited OPS-3 \(H=3\). The target is one canonical interval; two BASE anchors are not adaptive trajectories. No automatic F2/F3 reopening or simultaneous-roster extension.

**8. Cost**

F1 scaling: \(383\times4\times3=4596\) seconds, approximately **76.6 serial minutes / 1.28 worker-hours**, plus implementation and verification. Tie-only acquisition may be cheaper; no speedup is assumed. Parallel time, capacity and resource cap are under-specified execution bindings, never grounds for dropping units.

**9. Freeze checklist**

Resolve all placeholders; each artifact requires path and SHA-256:

- `<<BIND_AT_FREEZE:PRE_E1_DRAFT_TIMESTAMP_CONTRACT_SEAL_REVIEW>>`
- `<<BIND_AT_FREEZE:MEMO_E1_REVIEW_R7_C1C2_F1_AUTHORITY_MANIFEST>>`
- `<<BIND_AT_FREEZE:ELIGIBLE_E1_CERTIFIED_CELL_AND_LAUNCH_AUTHORITY>>`
- `<<BIND_AT_FREEZE:THREE_CHECKPOINTS_AUTHORITIES_ENCODERS_PARAMETER_HASHES>>`
- `<<BIND_AT_FREEZE:PANEL_EXCLUSIONS_PREREG_TLE_RNG_FIELD_MANIFEST>>`
- `<<BIND_AT_FREEZE:INTERFACE_RESERVATION_DECODER_ACCOUNTING_CODE_TESTS_VERIFIER>>`
- `<<BIND_AT_FREEZE:ENVIRONMENT_THREADS_RESOURCE_CAP_ROOTS_WRITE_ONCE_RECEIPTS>>`

Review must accept every stated interpretation. Execution bindings cannot defer or alter scientific choices.

ASTRA_CANDIDATE_C=DRAFTED