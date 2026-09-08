# V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md

## 0. Status, provenance and disclosure

**DRAFT; unsealed; no execution authorised by this document alone.** Controller destination: `.scratch/multi-catfish-v023-c3-existence-e1/`; no `docs/` update.

Basis: `.scratch/multi-catfish-v023-controller-handoff-20260907/ADJUDICATION-C3-FUTURE-PATH-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md`: `PURSUE_NOW_PARALLEL`, `EXISTENCE_TEST=REQUIRED_FIRST`.

Following STOP_PHYSICS_R7 and FAST_SCREEN_NO_SUPPORT, we prospectively declared this separate development experiment from physical principles and explicit exclusions; historical outcomes motivated reconsideration but did not select its formulas, deployment parameters, worlds, seeds, horizons, lambda or acceptance rules. Previous failures remain unchanged; reused checkpoints and exploratory evidence are disclosed; TEST remains closed.

E1 is an existence screen for **ONE intervention class plus ONE joint catalog**, not an admission gate, not efficacy. TEST remains closed. This draft used read-only local inspection; no edits, network, SSH or experiment.

## 1. Claim scope

E1 measures finite-panel physical headroom at matched BASE anchors, using realised information unavailable to a deployable policy.

U₁ bounds only interventions changing at most one user per anchor under the conventions below. J₁ is exact within its catalog and a lower bound on unrestricted joint potential.

Neither establishes deployable information, learnability, additive composition, adaptive trajectory improvement, generalisation or efficacy. Neither closes arbitrary simultaneous C3. Reused lineages are not fresh trained lineages; worlds are the physical clusters.

## 2. Estimands and certification

Let \(P\) contain all 120 anchors. For complete physical profile \(x\) at anchor \(p\), define interval bits \(B_{px}\), network joules \(E_{px}\), and served-user count \(C_{px}\). Let \(b_p\) be BASE, \(N=12000\), and

\[
\eta_{\rm BASE}=\frac{\sum_pB_{pb_p}}{\sum_pE_{pb_p}},
\qquad
s_{\rm BASE}=\frac{\sum_pC_{pb_p}}N.
\]

For either finite choice family \(\mathcal X_p\), define

\[
V(\mathcal X)=
\max_{\substack{y_{px}\in\{0,1\}\\
\sum_{x\in\mathcal X_p}y_{px}=1\;\forall p}}
\frac{\sum_{p,x}B_{px}y_{px}}{\sum_{p,x}E_{px}y_{px}}
\quad\text{subject to}\quad
\sum_{p,x}C_{px}y_{px}\ge
N(s_{\rm BASE}-0.001).
\]

All profiles require positive energy. BASE supplies a feasible solution.

**Unilateral:** \(U_1=V(\mathcal U)\), where \(\mathcal U_p\) contains BASE and every F1-legal, non-NOOP unilateral physical change, everyone else remaining at BASE.

**Joint:** \(J_1=V(\mathcal J)\). Each \(\mathcal J_p\) contains BASE and the following exhaustive catalog: for each occupied BASE origin beam, propose moving every BASE user of that beam to each distinct destination physically identified by `(NORAD, cell)` that is mask-legal for every member. Other users retain BASE actions. Evaluate every resulting complete action vector physically; never sum unilateral effects.

**Underspecified catalog interpretation chosen:** origin membership means BASE’s realised served occupancy. Unserved users are not origin members. Include singleton origins and empty destinations. Native resolution may prevent intended evacuation; retain the realised profile without a favourable-success filter. Sort origins/destinations lexicographically; record exact duplicate profiles as aliases. An empty catalog leaves BASE alone.

**Certified procedure:** use Dinkelbach iterations. At trial ratio \(q\), solve

\[
\max_y\sum_{p,x}(B_{px}-qE_{px})y_{px}
\]

exactly by dynamic programming over anchor index and integer cumulative served count \(0,\ldots,N\). Retain only terminal counts satisfying the service constraint; update \(q\) to the selected feasible ratio. Terminate only when the exact maximum residual is zero.

Deliver **both** a reconstructable primal selection and a certificate: complete choice-set census, coefficients, final \(q\), DP recurrence values/backpointers, feasible terminal maximum zero, and independently verified totals. A positive witness without optimality certification is insufficient for a completed E1 result.

**Underspecified arithmetic chosen:** generate per-profile binary64 B/E scalars using F1’s accounting, serialize losslessly, then treat them as exact rationals for optimisation and pooled comparisons. Thus “exact” concerns the frozen simulator tape, not ideal real-number physics. No optimisation epsilon or rounded-ratio comparison is allowed. Resolve equal optima lexicographically, BASE first.

## 3. Pre-declared decisions

Freeze \(\delta=0\).

- `E1_UNILATERAL_HEADROOM` iff certified \(U_1>\eta_{\rm BASE}\), with service feasible; otherwise `E1_UNILATERAL_CLOSED`.
- `E1_JOINT_HEADROOM` iff certified, service-constrained \(J_1>\eta_{\rm BASE}\); otherwise `E1_JOINT_CLOSED`.

Because BASE belongs to both sets, valid CLOSED optima equal BASE.

| Unilateral | Joint | Sole next-step authorisation |
|---|---|---|
| HEADROOM | HEADROOM | Declare a candidate’s kill screen within either demonstrated family. |
| HEADROOM | CLOSED | Declare a unilateral-class candidate’s kill screen only. |
| CLOSED | HEADROOM | Declare a catalog-based joint candidate’s kill screen only. |
| CLOSED | CLOSED | Neither family authorises a candidate kill screen. |

No outcome itself authorises launching that screen, training, admission or efficacy evaluation.

Malformed/inconsistent physics, provenance or certificates yield global `INVALID_RUN`; no sibling result escapes invalidation. Repair only demonstrated infrastructure defects, preserving formulas, panel and decisions. Document evidence and changed bindings; replay the smallest affected unit. Preserve original receipts. Never rerun a valid unfavourable outcome.

**Underspecified interruption policy chosen:** budget exhaustion or interruption is `INCOMPLETE`, without HEADROOM/CLOSED adjudication; it is not evidence of closure.

## 4. Panel and anchor conventions

Use four ASCII domains, without newline:

- `C3_EXISTENCE_E1/world/1`
- `C3_EXISTENCE_E1/world/2`
- `C3_EXISTENCE_E1/world/3`
- `C3_EXISTENCE_E1/world/4`

For each, derive

`int.from_bytes(SHA256(domain.encode("ascii")).digest()[:8], "big") & ((1 << 63) - 1)`.

This matches `.scratch/multi-catfish-v023-c3-contingency-f3/f3_common.py`. The controller computes numbers and verifies mutual disjointness and absence from previously used/allocated world inventories before freeze. Collision handling is unspecified: stop before outcomes; do not silently substitute domains.

Cross all worlds with lineages `2026092101`, `2026092102`, `2026092103`: twelve units, ten canonical steps `0..9`, 100 users each. No favourable-regime selection; retain every world, lineage and anchor.

BASE is native masked argmax of float32 Q1+Q2, with NumPy first-index ties. Masks have 28 slots. All-false masks emit `NO_OP_ACTION=-1` and no unilateral candidate. Enumerate unilateral changes by user then action; omit BASE-equivalent physical keys; reject duplicate legal physical aliases as F1 does.

Bind `KeyedFadingField.from_components("MCRL_V023_LCSRS_C3_OBSERVABILITY_V1", world)` before reset. Lineage and catalog do not enter the field key. Reuse F1/F2 environment/mobility RNG construction.

At every anchor, evaluate all profiles against identical predecision state and field. Verify counterfactual evaluation leaves continuation state/RNG unchanged. Commit BASE afterward and verify `last_outcome` matches evaluated BASE; advance only BASE.

**Underspecified pooling chosen:** one global ratio and service constraint over all 120 anchors. World/lineage breakdowns are descriptive; F2’s direction-vote gates are not inherited.

## 5. Physics and accounting

Bind the canonical interval \(30.08\) s, \(47\times0.640\), from `src/mcrl/env/constants.py`; require runtime agreement. Apply F1’s convention:

\[
B=\Delta t\sum_u R_u,\qquad E=\Delta t\,P_{\rm system}.
\]

Read rates, served identities, link powers, active beams, beam radiated powers, fixed/system power from `ActionEvaluation`; authenticate BASE against committed `last_outcome`. D2 substeps are tracking updates, not independently measured energy integrals.

Apply corrected F0 `PhysicalProfile.verify_canonical_power()` and `compute_cost_shares()` to every profile. Check occupancy/service consistency, unserved zero rates/shares, canonical PA supply, beam circuit and active-satellite baseband charges, and conservation of total shares in watts and joules. Never substitute summed link power for network power.

Retain F0’s existing roundoff checks, including
\(\max(10^{-12},1024\epsilon_{64}\max(1,|\text{values}|))\).
These do not relax EE/service decisions.

Bind:

- \(\lambda=118424222.8550065\) bits/J, hex `0x1.c3c0a7b6b86d3p+26`, from each lineage’s `authority.json` and `.scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md`.
- \(\kappa=10097071012.757404\) bits, hex `0x1.2cea89d260f2ap+33`, from those authorities and `.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-MODEL-CONFIG.json`.

These authenticate inherited heads/accounting; neither is a tunable E1 objective coefficient. `Q1+Q2+z/κ` is not used.

## 6. Inherited exclusions

STOP_PHYSICS_R7 and FAST_SCREEN_NO_SUPPORT remain unchanged. Do not revive D/F variants, clipping, gating, sign filtering or rescaling. Do not rank formulas using opened residuals or tune against world `2026121721`.

No world, lineage, threshold, horizon, λ, κ, deployment or acceptance-rule search. Historical F1 rows are disclosed historical diagnostics only. F2/F3 admission is not reopened. A changed intervention family requires a separate prospective contract.

## 7. Bindings, outputs and resumability

Freeze corrected F1/F2 tape code and dependencies, F0, canonical physics, E1 enumerator/solver/verifier, tests, environment and exact launch arguments.

Authenticate each lineage under `.scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-{lineage}/`: exactly one rung-003000 checkpoint, authority file and recomputed body seal; Q2 initialisations `2026108101–03`; expected source-contract, update and no-TEST semantics; Q1/Q2 parameter hashes before/after.

Bind TLE root `/home/sat/mcrl-runtime/tle-frozen-20260820`, its complete archive manifest, and `artifacts/PREREG-FROZEN-2026-08-25-R2.json`, both file and semantic record digest.

Freeze absolute checkout/output roots before launch. Publish `units/<world>-<lineage>/` atomically with write-once tapes, manifests and receipts, mode `0444`, reopened and hash-verified. Resume authenticates/skips complete units; incomplete staging is not evidence. Twelve complete units precede pooled solving and write-once terminal publication. No cumulative release barrier is required.

Every receipt carries:

`TRAIN_DEVELOPMENT_C3_EXISTENCE_SCREEN_E1_NO_LEARNER_NO_EFFICACY_NO_TEST`

## 8. Cost, budget and resources

F1’s run report records 383 s for one world×lineage×two steps. Scaling gives \(383\times5\times12=22980\) s, approximately **6.4 serial hours** for unilateral acquisition. Reserve another **6.4 worker-hours** for joint profiles; actual cost depends on prospectively determined catalog counts.

**Underspecified cap chosen:** 16 worker-hours total: 12.8 acquisition plus 3.2 solver/verifier reserve. Exhaustion yields INCOMPLETE, never catalog truncation or a relaxed certificate. Any extension requires a logged resource-only amendment.

Worker count is at most `min(12, usable cores−2)`, reduced for concurrent workloads and memory; one thread per process, including BLAS/OpenMP/Torch/solver. Launch none if insufficient capacity. Parallel wall time is provisional, not guaranteed; record time, profile counts and peak RSS per unit.

## 9. Permitted paper statements

**Both HEADROOM:** “The declared finite TRAIN panel contained service-feasible physical headroom in both the unilateral class and joint catalog. These oracle findings motivate prospective candidate kill-screen declarations and establish no learner or efficacy result.”

**Unilateral only:** “The declared unilateral class contained physical headroom, while the fixed joint catalog did not improve upon BASE under pooled service. Only unilateral candidate-screen declaration is supported; arbitrary joint potential remains unresolved.”

**Joint only:** “The exact unilateral ceiling equalled BASE, while the fixed joint catalog contained service-feasible headroom. This supports a catalog-based candidate-screen declaration, without establishing deployability or efficacy.”

**Both CLOSED:** “Neither the restricted unilateral class nor the fixed joint catalog improved upon BASE under pooled service on this panel. These closures do not establish universal C3 impossibility.”

**INVALID_RUN or INCOMPLETE:** “E1 did not produce a valid complete certified result. No headroom or closure conclusion is drawn.”

## 10. Freeze checklist

Resolve every placeholder before outcomes; **each manifest entry must contain its own path and SHA-256**.

- Contract body/seal: `<<BIND_AT_FREEZE:CONTRACT_BODY_SHA256>>`; freeze timestamp/reviewer: `<<BIND_AT_FREEZE:REVIEW_AND_TIME>>`.
- Memo, R7/ladder, F1 ruling/results: `<<BIND_AT_FREEZE:PROVENANCE_DIGEST_MANIFEST>>`.
- F1/F2 code/preflights/dependencies: `<<BIND_AT_FREEZE:F1_F2_DIGEST_MANIFEST>>`.
- Corrected F0: `<<BIND_AT_FREEZE:F0_SHA256>>`.
- Three checkpoints, authority files/body seals, source contracts, parameters, λ/κ configuration: `<<BIND_AT_FREEZE:LINEAGE_DIGEST_MANIFEST>>`.
- PREREG file/record: `<<BIND_AT_FREEZE:PREREG_FILE_AND_RECORD_DIGESTS>>`.
- TLE archive/files: `<<BIND_AT_FREEZE:TLE_DIGEST_MANIFEST>>`.
- Derived worlds, exclusion inventory, RNG implementation, field roots: `<<BIND_AT_FREEZE:PANEL_DIGEST_MANIFEST>>`.
- E1 code, coefficient serialization, solver, independent verifier, synthetic certificate tests: `<<BIND_AT_FREEZE:E1_CODE_AND_VALIDATION_DIGEST_MANIFEST>>`.
- Checkout, interpreter, libraries, hardware/thread environment and launch arguments: `<<BIND_AT_FREEZE:PROCESS_ENVIRONMENT_DIGEST_MANIFEST>>`.
- Absolute output roots: `<<BIND_AT_FREEZE:OUTPUT_ROOTS>>`; preflight/launch-authority seals: `<<BIND_AT_FREEZE:E1_LAUNCH_DIGESTS>>`.

Controller review must expressly accept every identified interpretation before sealing.

ASTRA_E1_CONTRACT=DRAFTED