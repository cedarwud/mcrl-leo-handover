# V0.25 Physics-Successor — Design Brief (authority for the delta and the deck)

Compiled 2026-09-09 from the sealed successor set in
`/home/sat/mcrl-hub-copy/.scratch/multi-catfish-v025-physics-successor/`
and the v0.23 handoff in
`/home/sat/mcrl-hub-copy/.scratch/multi-catfish-v023-controller-handoff-20260907/`.
Source documents are read-only reference and were not modified.

**Sealed set in force** — `V025-DESIGN-FREEZE-AND-CLOSURE-RULE-2026-09-09.md` §1 "Freeze point":

> The successor design is **frozen when engine stage 4g passes its audit**. From that moment the sealed set is: declarations v1.0–v1.9 and their errata, the contingency ladder and its amendment, the stages 6–8 contract v1 with amendments v1.1–v1.2, and every controller decision record in force. No further scientific change is made before the a-r0 matrix.

**Precedence rule used throughout this brief:** later amendment overrides earlier; errata correct without changing design; controller decision records bind the engine passes they name. Where two documents disagree, the later sealed one is quoted and the superseded text is shown as "OLD".

---

## A. What the successor design IS

### A.0 Named identity of the system model

| Term (exact) | Meaning | Source |
|---|---|---|
| `V025-ANGLE-RATE-TPC-TDM-ACM` (**a-r**) | **Primary system model.** "memoryless angle-aware power control with a per-user nominal rate target r* = 50 000 000 bit/s … Equal-airtime full-band TDM." | `V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.1-AMENDMENT-2026-09-08.md` §Amendments 1 |
| `a-r0` | The single primary **setting** (treatment 0); the only setting that can produce the paper's primary result | v1.5 §1; v1.7 §4 |
| `V025-ANGLE-TPC-TDM-ACM` (**a-γ**) | v1.0's original primary (fixed-SINR target γ*), **demoted** by v1.1 to a sensitivity sibling and relabelled | v1.0 §Declaration; v1.1 §3 |
| `V025-FIXED-EIRP-ACM` (**b**) | "**Declared reference model** … fixed 1.65 W RF per active beam with ACM (astra round-3 §2). Reported in every table beside (a)." | v1.0 §Declaration |
| **a′-r / a′-γ** | FDM siblings: "same target with equal FDM sub-bands (per-user RF ceiling 1.65/n_b, beam RF = Σ p_u, sub-band-consistent noise/PSD/overlap)" | v1.0 §Declaration ("Architectural sensitivity: (a′)"); v1.1 §3 |

**Matrix size — authoritative count.** `V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.3-ERRATUM-2026-09-08.md` §Erratum:

> v1.2 §1 says "Total: 28 primary-eligible cells + diagnostic U cells". The explicit list in the same paragraph governs and yields **25 primary-eligible settings** (5 architecture baselines `a-r0, a′-r0, a-γ0, b0, a′-γ0` + S, H, SH, T for each of the five = 5 + 4 × 5) plus **6 diagnostic U settings** (`U-cap`, `U-margin` for `a-γ, b, a′-γ`; v1.2 §2), i.e. **31 settings in total**. The number 28 was a counting error.

**Sealed priority order** (v1.2 §1): `a-r0 > a′-r0 > a-γ0 > b0 > a′-γ0`, then S, then H, then SH, then T in the architecture order `a-r, a′-r, a-γ, b, a′-γ`; U cells diagnostic-only, never primary-eligible.

**Scope of the primary** — v1.5 §1 "Execution order and scope of the admission decision":

> The training-admission decision (PHYSICS-GO) is made on the primary setting `a-r0` alone, as sealed in v1.1. The other 30 settings are **exploratory sensitivities**: they execute after `a-r0` completes, in the sealed priority order, within the remaining budget, and **none of them can change the admission decision or the claim**.

v1.7 §4 resolves the precedence against the contingency ladder:

> v1.5 §1 governs the **primary claim**: only `a-r0` can produce the paper's primary result, and no sensitivity or regime cell can change it. The ladder's Rung 1 governs what happens **after a-r0 has been reported as failed**.

### A.1 The nine-stage spine

`END-TO-END-PIPELINE-MAP-2026-09-08.md` is the declared single source of truth for stage handoffs and their invariants.

- **Stage 0 — Data and splits.** Starlink TLE archive `~/demo/tle_data/starlink/tle/starlink_YYYYMMDD.tle` (373 daily files; one malformed record quarantined in 20260528); 100 users, 30 km/h mobility, ~14 km cell grid, earth-fixed beams. World = (TLE date, world seed); seed rule `int.from_bytes(sha256(domain).digest()[:8],'big') & ((1<<63)-1)`. TRAIN-only asserted at world construction.
- **Stage 1 — Geometry and time base.** Δt = 30.08 s = 47 × 0.640 s; **48 boundaries per step** at t + k·0.640 s, k = 0..47. Per boundary: satellite ECEF (sgp4), user ECEF, elevation, slant range, off-axis angle vs the earth-fixed cell centre, 10° visibility, D2 eligibility (entry elevations ≈ 19.7 / 23.4 / 27.7° at 426 / 485 / 550 km; TTT; margin), dwell phase (step mod 4; candidate identities and cell re-key only at phase 0). Invariant: "event ledger keyed by physical (NORAD, beam-chain) identity, not slot index".
- **Stage 2 — Channel.** Direct gain (transmit gain at off-axis angle × FSPL × receive gain), cross-satellite co-colour interference gains (S.465-6 receive pattern, θ_min = 2.0433° branch), keyed shadow/scintillation with common random numbers per world. Invariant: "nominal (no fading) vs realised (fading) separation".
- **Stage 3 — Power, service and energy (the physics model).** See §C.
- **Stage 4 — Endpoint and reward.** "Endpoint: pooled EE = ΣB/ΣE over the panel (ratio of sums, never sum of ratios); QoS co-primaries: availability, handover rate, Φ-priced handover cost. Reward core: R_t = B_t − η_ref·E_t (identity test); λ = η_ref from the nominal-greedy reference; κ = B_ref/(U·T_ref)."
- **Stage 5 — Targets (C1/C2/C3 labels).**
- **Stage 6 — Source tapes and training data.** **Stage 7 — Learner and deployment.** **Stage 8 — Evaluation and claim.** Governed by `V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md` with amendments v1.1 and v1.2.

Cross-cutting invariants named in the same map §"Cross-cutting invariants nobody owned until now": units/constants with `VERIFY_SOURCE` provenance in one table (`constants_v025.py`); identity keys `(NORAD, beam-chain)` from stage 1 to stage 8, never slot indices; one clock, one alignment rule, one integration rule; explicit λ/η/κ at every producer and consumer with a test that fails on any default; TRAIN-only and domain-derived seeds with CRN across arms; placebo and dry-run on every harness before any unit opens; "Sealed before outcome: priority order, constants, margins, catalogue, anchors, concurrency (operational) — amendments only pre-outcome."

### A.2 What observations flow in — the two declared information interfaces

`V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md` **§A. Information interfaces (declared, equalised across arms)**:

> **A1. I_heads** (per user i, per legal action): the completed Q1 and Q2 schemas of §B; observation access = current nominal geometry of user i's candidates, i's history, the previous committed served set excluding i (b⁻₋ᵢ) at decision time; derived features as frozen; model access = none (no joint physics); compute = one forward pass.

> **A2. I_coordinator** (per anchor): global nominal geometry with beam-specific cross gains, all users' legal sets, b⁻, the reference proposal a⁰, the bounded catalogue 𝒞 (decision 4/CB-2), the nominal model 𝓜 (no realised fading, no future TLE beyond the declared forecast horizon), and the outputs of 𝓜 for each profile in 𝒞 (joint load, coupled powers, interference, activation, service, bits, energy, continuation). Compute = the declared budget (§F).

> **A3. Two distinct references:** a⁰ (the reference proposal for the score decomposition; = the per-user argmax of Q1 + Q2, validated as a profile) and the previous committed association (the reference for handover/Φ/event accounting). **Never conflated.**

> **A4. Equalised between FULL and every DROP/comparator arm:** primitive access and timestamps, forecast method, physical identities, catalogue construction (authenticated identical catalogues at matched anchors), joint search, guards, tie-breaking, validation, deadline, fallback. Any learned pruning is part of the declared intervention. **An exact evaluator may never reinsert a removed score through ranking, pruning or a score-dependent guard.**

### A.3 Per-user structure and the heads

**Two heads only — Q1 and Q2. There is no third additive Q head in the successor.**

**Q1 schema** — contract v1 §B2:

> nominal rate-target SINR margin, required power / cap, mode SE, occupancy excluding focal, beam- and satellite-active bits before focal insertion, off-axis angle, remaining D2 time, remaining visibility time, refresh phase; history: previous served association one-hot, previous served load per candidate, previous beam/satellite activity, previous beam max RF / cap; `missing_incumbent`. **No recurrence power, entry-gain ratio or segment age.**

Frozen normalisation scales — `V025-CONTROLLER-DECISIONS-STAGEC-SPEC-2026-09-08.md` item 1 (`Q1-SCALES`, ACCEPT): "margin / 20 dB, SE / 4 bit/s/Hz, occupancy / 10 users, angle / 1 rad, times / 120 s, phase / 3"; "they are scales, not thresholds; sealed with the Q1 schema SHA in spec v1."

**Q2 schema** — contract v1 §B3: "the frozen 21 fields + `missing_incumbent`; background = b⁻₋ᵢ projected to the decision instant; occupancy excludes focal; activation before focal insertion." Stage-C spec item 2 completes it: "**Q2-SCHEMA-SEAL** — the 22-field schema gets its own SHA in spec v1; the 21-field SHA 54ab6a82… is retired and never stamped again. **Q2-INCUMBENT-MARGIN** — each candidate row carries its **own candidate-current margin**; the incumbent's margin is a per-user context field broadcast once per row (both present, distinct names)."

**Learner form** — contract v1 §C1:

> **Heads:** Q1, Q2 by pairwise zero-bootstrap regression on typed deterministic aggregate batches (legacy heterogeneous design); the deployed two-head action is the per-user masked argmax of the normalised Q1 + Q2, validated as a jointly legal profile (deterministic repair rule for conflicts, KAT with a jointly infeasible pair). This estimates a **supervised surrogate of the declared targets, not a Bellman value**; the claim is worded accordingly.

Architecture and optimiser are copied, not re-tuned — Stage-C spec item 5 (`FORMAL-LEARNER`): "heads identical to the V0.23 heterogeneous Catfish trainer's configuration (architecture, optimiser and settings, batch construction, epoch budget and stopping rule), with input dimensions changed to the sealed schemas; the literal configuration values are copied from the legacy trainer's frozen config into spec v1 at seal time (no re-tuning). The set head uses the same optimiser settings." Contract v0 item 6 adds: "**no Bellman replay in the successor**."

### A.4 What a per-user proposal is

The per-user proposal is the **masked argmax of the normalised Q1 + Q2**, validated as a jointly legal profile; the validated profile is **a⁰**, also called **BASE**.

- Contract v0 item 9: "per-user masked argmax of the normalised Q1 + Q2 sum (bits / κ) for the two-head policy".
- Contract v0 item 10 (**Joint feasibility**): "the committed action is one jointly legal profile; independent per-user argmax outputs are validated as a profile before commit (KAT: two users whose individually legal picks are jointly infeasible)."
- Contract v1 §A3: a⁰ "= the per-user argmax of Q1 + Q2, validated as a profile".
- Contract v1 §F2: "BASE (a⁰) is computed, validated and repaired **before** the coordinator starts".

**Per-user action catalogue — exact cardinality and structure.** Astra round-3 §2 item 19, retained by v1.0 ("actions" is among items 5–31 carried unchanged):

> Retain **28 association actions, four cached satellite identities, seven local cells** and four-decision refresh; these are candidate restrictions, not minimum residence. **NO_OP remains legal exactly for an empty mask.** Joint SINR is not an independently guaranteeable per-user legality mask; outage does not authorize hidden rescue.

So the per-user action surface is 4 satellites × 7 cells = **28 slots**, plus NO_OP (`= -1` in the legacy interface, `DRAFT-C3S-SET-LEVEL-COORDINATOR-CONTRACT-CODEX-GPT6-ASTRA-2026-09-08.md` §2: "28 slots，空 mask 回傳 `NOOP=-1`"). Roster U = 100 users (`V025-CONTROLLER-DECISIONS-STAGE2-2026-09-08.md` item 1: "user count (100)").

"N = 4 is named a **candidate-refresh period, not a dwell**" (v1.2 §7); confirmed by `V025-CONTROLLER-DECISIONS-PIPELINE-AUDIT-A-2026-09-08.md` item 8: "N = 4 refresh cadence only: confirmed (cadence audit + audit A); documented in the system model."

### A.5 The set-level layer (C3)

**C3 is a set-level coordinator over complete profiles, not a head that is summed into the per-user score.** Three named selectors — contract v1 §C2:

| Name | Definition (verbatim from contract v1 §C2 unless noted) |
|---|---|
| **S3** | "a **set-conditioned scalar interaction head** Ψ̂_θ(Z_t, a⁰, A, a_A): permutation-invariant over A, anchored Ψ̂(∅) = Ψ̂({u}) = 0, trained on the residual Ψ_A / κ over the coalition support of the bounded catalogue; deployed S3 optimises the **complete** score C1 + C2 + Ψ̂ over 𝒞 with the sealed service guard, budget and fallback." |
| **S0** | "the same selector with the **exact Ψ_A** in place of Ψ̂." |
| **S_UNI** | "iterated exact unilateral improvement to a local optimum (every legal unilateral alternative evaluated with the same nominal joint physics at each iterate, deterministic improving move, atomic commit of the final profile only, **termination certificate reported**)." |

S_UNI is further pinned by `V025-CONTROLLER-DECISIONS-4C-AUDIT-ROWS-2026-09-08.md` item 2:

> S_UNI is the iterated exact **unilateral** best response using the **same nominal evaluator, snapshot, guards and objective as the coordinator** (k = 0 selection view) — "exact" refers to the exhaustive unilateral search, not to 48-boundary integration. Its unilateral option set is the **full legal set** (not the top-8 shortlist), so it is never weaker than the coordinator's unilateral options; it has its own compute budget (comparator arm, not the deployable policy), reported per anchor with its iteration count and termination certificate. Its committed profile is evaluated at 48 boundaries like every arm.

Deployed mode — Stage-C spec item 7 (`COORDINATOR-MODE`): "S3 (learned set head over the bounded catalogue) is the deployed C3 layer; S0 and S_UNI are always evaluated beside it (contract v1 §C2, §C4); the information claim per §A."

**Set-head input representation** — Stage-C spec item 4 (`C3-SET-REPRESENTATION`):

> set head input = permutation-invariant pooling (sum and max) over the changed users' per-user vectors (their Q1 row for the selected action, their incumbent row, `missing_incumbent`), concatenated with global resource context per affected beam (occupancy before/after, activation change, interference summary, cap margin), padded to |A| ≤ 4 with masks; a two-layer MLP on the pooled vector; anchored zeros by construction (output × 𝟙[|A| ≥ 2]). Shapley for reporting: exact over subsets for |A| ≤ 4.

**Amended — the interference summary is insufficient.** Contract v1.2 §2 (`§C2 — feature sufficiency for the set-conditioned head`):

> The encoder's input must contain, for the changed-user set and its affected beams: proposed and incumbent associations by physical identity, background occupancy and activation before and after insertion, the shared-resource relations among the affected beams, and the **pairwise cross-gain terms among the affected beams** (not only a scalar interference summary — a summary can hide exactly the difference that flips a coupled fixed point). Acceptance test T2 is extended: the information-twin pair must be separable with the full context and provably ambiguous when the cross-gain block is removed.

**C3 training rows** — contract v1 §B5 as corrected by contract v1.2 §1 and v1.7 §3: rows "carry the complete coalition context: anchor, a⁰, the changed-user set A, their selected actions a_A, the global resource context (occupancy, activation, shared capacity, interference summary per affected beam), and the label Ψ_A / κ"; Ψ_A "is computed for every coalition regardless of size"; "Only the exact per-user Shapley attribution remains capped at |A| ≤ 4 and is reporting-only … with `credit_split = NOT_COMPUTED_LARGE_SET` above the cap"; "**Per-user Shapley credit is reporting only … never a training target**."

### A.6 The bounded action catalogue 𝒞 (CB-2) — exact size and structure

Two generations exist. The **sealed deployable one** is the selection-time shortlist.

**Original union catalogue** — `V025-CONTROLLER-DECISIONS-STAGE2-2026-09-08.md` item 4 (**CHANGE** for real worlds):

> the complete Cartesian product of legal assignments is used only when it has ≤ 4 096 configurations (synthetic worlds). Otherwise the union catalogue is the bounded set: (i) every unilateral move of every user to every legal option; (ii) the S0 deployable proposals (top-two per user) and all frozen beam evacuations; (iii) all pairwise joint moves among the top-K = 10 users ranked by nominal unilateral surplus, over all their legal option pairs; (iv) per-active-beam evacuation sets (every user of the beam to its best legal alternative). **J1 = the best changed-user-count > 1 configuration in this catalogue; U1 = the best in (i).**

**Sealed deployable shortlist** — `V025-CONTROLLER-DECISIONS-SELECTION-TIME-APPROXIMATIONS-2026-09-08.md` item 1:

> **Catalogue shortlist (replaces the "all legal options" unilateral set):** per user, the **top-8 legal options** by nominal single-link decoding margin at the decision instant (deployable shortlist) → **≤ 800 unilateral rows**; pairwise among the **top-10 users** by exact nominal unilateral surplus × their **top-2 options** (**≤ 180**); per-active-beam evacuations (**≈ 40**); S0 top-two + evacuations (**≤ 200**). **Catalogue ≈ 1 200 rows.** The stage-3 item-10 diagnostic reports, per anchor, how many legal options fall outside the shortlist and the best excluded option's margin.

Size guard and measurement: `V025-CONTROLLER-DECISIONS-4C-GATE-2026-09-08.md` item 3 — "with the top-8 shortlist it must be ≈ 1 200 (≤ 1 500); if the count is ≈ 3 000 the shortlist was not applied — fix before timing." Measured at the stage-4d gate: "catalogue **1 004 rows** (PASS ≤ 1 500)" (`V025-CONTROLLER-DECISIONS-4D-GATE-2026-09-09.md` preamble).

An earlier size cap (`V025-CONTROLLER-DECISIONS-COMPUTE-BUDGET-2026-09-08.md` item 2) gave "Catalogue ≤ ≈ 3 200 rows per anchor"; the selection-time shortlist supersedes it for the deployable coordinator.

CB-2's formal construction is still a named seal-time item: contract v1.1 §4 lists "catalogue CB-2 construction" among "Remaining `CONTROLLER_DECIDE` from build 3 … seal-time items resolved with the launch package and the stage-C spec v1 seal."

### A.7 Selection procedure — two-stage, budgeted, arm-specific

`V025-CONTROLLER-DECISIONS-SELECTION-TIME-APPROXIMATIONS-2026-09-08.md` preamble states the invariant that makes this legitimate:

> A complete anchor is far beyond the coordinator's own decision budget, so the exact-everything selector is not a deployable object either. **The physics, labels and endpoint stay exact at 48 boundaries; selection-time scoring gets the approximations a real controller would use.** All values below are sealed before any outcome; none may be changed after.

1. **Stage 1** — immediate score (C1 + Ψ interaction) for **all catalogue rows**. Grid: originally 5 boundaries k ∈ {0, 12, 24, 36, 47} with trapezoid weights (item 2); tightened by `V025-CONTROLLER-DECISIONS-4C-GATE-2026-09-08.md` item 2 to "**the decision instant only (k = 0; the deployable controller's own view)**".
2. **Stage 2** — C2 continuation (three offsets, **batched**: "one shared batch call per anchor (configuration × offset × boundary)") for the **top-M = 64** rows "plus BASE, the incumbents and every S0 proposal" at the 5-boundary grid. "M is sealed."
3. **Selection** — "the selected profile is the argmax of the complete score within that set."
4. **Provider amortisation** — "the world tape (33 steps × 48 boundaries) is constructed once per world and reused by all arms and settings … the per-anchor provider target of 1 s is **withdrawn** in favour of 'once per world'."
5. **Escalation if over budget** — `V025-CONTROLLER-DECISIONS-4D-GATE-2026-09-09.md`, binding order 1 → 2 → 3: (1) "**Declared parallelism first (not an approximation)** … 4-worker parallel evaluation of stage 1 and stage 2 (configuration-level sharding; deterministic reduction; identical results to the serial path — KAT)"; (2) "stage-2 forecasts evaluated at **one boundary per offset** step … keeping three offsets and M = 64"; (3) "**M = 64 → 48**. No further step without a controller decision." Item 4: "labels, committed-profile evaluation and the endpoint remain at 48 boundaries throughout (KAT)."

**Per-arm ranking keys (defect fix)** — v1.9 §4:

> Using the full F_m for every arm would restore the removed contribution. The immediate ranking key is the arm's own score: FULL → C1_m + C3_m (secondary C2); DROP_C1 → C3_m (secondary C2); DROP_C2 → C1_m + C3_m (secondary: a fixed deterministic rule); DROP_C3 → C1_m (secondary C2). Top-M pruning, any feasibility guard and any tie-break use the same arm-specific key; **no arm may rank, prune or reject using a score it has had removed.**

**C2's role in the set selector** — v1.6 §2:

> The set-level continuation term ranks only among the maximisers of the immediate margin-adjusted score (deterministic tie-break; ties defined by a declared 1e-9 relative tolerance). Q2's separate role in forming the per-user proposal a⁰ is unchanged.

Consequence, declared in advance — v1.9 §5: "With a unique immediate maximiser, a tie-break-only continuation cannot change the selected profile, so FULL and DROP_C2 coincide. The engine reports the tie frequency; a zero set-level C2 marginal is reported as such and never patched … **C2's certificate in the physics matrix is therefore forecast validity, not a selection marginal**."

### A.8 Validation, guards and execution

- **Joint legality validation** with a deterministic repair rule (contract v1 §C1; contract v0 item 10).
- **Service guard** — `V025-CONTROLLER-DECISIONS-STAGE2-2026-09-08.md` item 6: "Catalogue/service exclusion thresholds do not exclude configurations; they score and report (the service guard used by the deployable decoder is the sealed one from C3-S: **no served-count decrease versus the BASE proposal**)."
- **Coupled capped power solve** — `V025-CONTROLLER-DECISIONS-COUPLED-SOLVE-2026-09-08.md`: "The capped rate-target map p ← min(cap, Γ·(N₀W + I(p))/ĥ) with `force_cap` rows is a standard interference function (monotone, scalable), so the iteration from p = 0 converges to the unique capped fixed point. Iteration budget raised from 4 096 to **65 536**; convergence when the max absolute change ≤ 1e-10 W **or** the max relative change ≤ 1e-9." Certificates: "`CONVERGED` (tolerance met); `CONVERGED_SLOW` (budget reached, all changes over the last 1 000 iterations monotone and below 1e-6 W — recorded with the final change); `INVALID` only for non-finite values or a violated monotonicity check (a genuine implementation fault, which stops the unit). Cap-bound users are flagged `rate_target_infeasible`, transmit at cap, and are served iff their SINR after joint resolution ≥ SINR_min. **A BASE with infeasible users is evaluated like any other profile.**" Reporting: "Every receipt records the certificate per profile and the share of `CONVERGED_SLOW`; a high share is a physics finding to discuss, not a reason to change the model."
- **Null action** — `V025-CONTROLLER-DECISIONS-ENGINE-AUDIT-2026-09-08.md` item 4: "a user with zero legal candidates receives the null action (unserved) and is excluded from the product — **the catalogue never silently collapses to {BASE}**; KAT: … a receipt field counts null-action users."
- **Live legality within the step** — `V025-CONTROLLER-DECISIONS-PIPELINE-AUDITS-CD-2026-09-08.md` item 8: "a link that crosses below 10° or loses D2 eligibility at boundary k stops radiating and decoding from boundary k onward (energy and bits stop; the user is unserved for the remainder); KAT with D2 release and 10° crossing at boundary 17."
- **Execution** — one **atomic commit** of the complete profile (round-3 §2 item 29: "commits atomically"; C3-S §3: "完整 x_t^* 一次 atomic commit，不拆成連續單人採納"). Declared as an idealisation — see §E.
- **Deadline and fallback** — see §D.2.

### A.9 The evaluation endpoint — and what "the 48 boundary" is

**Definition.** Each 30.08 s decision step is sampled at **48 boundaries**, t + k·0.640 s for k = 0..47 (30.08 = 47 × 0.640 s). Those 48 samples define **47 trapezoidal sub-intervals** over [t, t + 30.08]. Astra round-3 §2 item 17 ("Clock"):

> Decisions remain every 47 × 0.640 = 30.08 s … Primary integration covers [t, t+30.08]: the value at t plus the next 47 D2 boundary samples define **47 trapezoidal intervals**; handle known event discontinuities explicitly. **Never apply the new action to pre-t samples.**

Treatment 0 is therefore "47-subinterval integration" (v1.0 §Declaration, priority-order paragraph).

**The 48 boundary is the invariant endpoint of the study.** It is restated as a hard rule in five sealed places:

- v1.6 §1: "**Executed physics, labels, the committed profile's evaluation and the endpoint remain unchanged at 48 boundaries with realised fading.**"
- v1.7 §2(ii): "The **outcome decomposition** uses the realised **48-boundary endpoint F**: C1, C2, C3 labels, the credit split and every certificate reported against the endpoint are computed from F. A statistic never mixes the two, and each reported quantity names which F it came from."
- `…SELECTION-TIME-APPROXIMATIONS…` item 2: "the committed profile, every label (C1/C2/C3) and the endpoint use all 48 boundaries."
- `…4C-GATE…` item 2 / `…4D-GATE…` item 4: "the committed profile and all labels/endpoint at 48 boundaries (unchanged)"; "KAT: the endpoint of a committed profile is bit-identical before/after."
- `…COMPUTE-BUDGET…` item 4 ("What is never thinned"): "the 12 + 1 arms per setting (the arms are the science), **the 48-boundary integration**, the calibration procedure, the placebo and dry-run."
- v1.9 §8 requires "power/interference/**48-boundary invariance KATs** (executed power identical with and without the margin; interference unchanged; committed-profile endpoint bit-identical)".

**In one sentence:** selection may be approximated (k = 0, or 5 boundaries, margin-adjusted, top-M pruned); the *endpoint* may not — every committed profile, every label and every certificate is recomputed on all 48 boundaries with realised fading. That is "the 48 boundary".

**Panel, estimator and claim** — contract v1 §D as amended:

- **§D1 Panel**, superseded by contract v1.1 §1: "Panel: 6 arms × **16** seeds × 2 worlds per date over ≈ 160 claim dates (≈ 320 worlds per arm-seed); training cost 96 arm-seed lineages." Seeds "derived from `V025_LEARNER/seed/{1..16}`". ≈ 30 steps per world; "allocation manifest sealed with role-wise date disjointness (claim dates unused by any successor development activity; legacy overlap recorded); **no TEST**."
- **§D2 Estimator:** "pooled ΣB/ΣE; primary interval = **two-way pigeonhole bootstrap** over dates × learner seeds with arms paired within resamples and the ratio recomputed per draw (central 95 % percentile); one-way cluster bootstrap and delta-method supplementary; seedwise paired effects reported; δ = **+0.5 % relative** with the 2.5th-percentile lower bound (v1.4); QoS margins with additive numerators/denominators inside draws."
- **§D3 Zero outcomes:** "B = 0 with E > 0 is EE = 0 (defined); a draw is undefined only when a denominator (E or the comparator's EE) is 0 — recorded and counted, never substituted."
- **§D4 Multiplicity and claim:** "the conditional intersection–union conjunction for `a-r0` is the **single primary claim**; components are reported with their own intervals but no component-wise discovery is claimed; all other cells exploratory; TRAIN-only wording enforced by the report schema."
- **§D5 Harness:** "attempt registry (STARTED before outcomes), canonical per-step receipts, merge re-aggregation from rows, conformance suite (NULL ≡ BASE per step, real-step dry-run of every arm, write-once sha256 receipts, authority manifest), same physics/endpoint digest as training, one terminal adjudication."

**Measured calibration of the estimator** — contract v1.1 preamble and table (stage C build 3: "200 Monte-Carlo replications per cell, 160 dates, two unequal-energy worlds per date × learner-seed cell, planning alternative +2 %, claim margin +0.5 %, 49 two-way bootstrap draws per replication, 7.3 M authenticated receipts"):

| date SD | seed SD | learner seeds | interval coverage | three-contrast conjunction power |
|---:|---:|---:|---:|---:|
| 5 % | 1 % | 5 | 0.863 ± 0.028 | 0.380 ± 0.067 |
| 5 % | 1 % | 12 | 0.878 ± 0.026 | 0.495 ± 0.069 |
| 5 % | 1 % | 16 | 0.893 ± 0.025 | 0.675 ± 0.065 |
| 5 % | 1 % | 24 | 0.908 ± 0.023 | 0.675 ± 0.065 |
| 3 % | 1 % | 12 | 0.893 ± 0.025 | 0.920 ± 0.038 |
| 3 % | 1 % | 16 | 0.920 ± 0.022 | 0.980 ± 0.019 |

Contract v1.1 §1: "**learner seeds: 16** (from 12). Beyond 16 the conjunction power does not improve at a 5 % date SD (the date component caps precision)." §3 (coverage disclosure): "The two-way pigeonhole percentile interval **under-covers** at these seed counts (0.89–0.92 measured against 0.95 nominal). The sealed decision rule is unchanged (declared before any outcome), and the report states the measured coverage next to every interval; **no post-hoc widening is applied**."

Contract v1.2 §4 adds: acceptance test T3 "additionally reports the **one-sided** coverage of the bound actually used for the decision (not only the two-sided interval coverage), at 5 / 12 / 16 / 24 seeds and for the 3 %, 5 % and 10 % date-SD scenarios, each with its Monte-Carlo uncertainty."

### A.10 Per-step receipt schema

`V025-CONTROLLER-DECISIONS-PIPELINE-AUDITS-CD-2026-09-08.md` item 5 (Merge re-aggregation):

> merge rebuilds every summary from the canonical per-step rows and refuses on disagreement; per-step schema = **hex floats** for bits/joules and energy components, additive opportunities and served counts over the **full roster**, prior/current physical identities, event type, Φ numerator/denominator, provider/code digests. Independent bit-for-bit re-aggregation is a test.

Additional mandatory receipt content: the energy boundary sentence verbatim in every receipt header (v1.8 §3); the power-solve certificate per profile and the `CONVERGED_SLOW` share (`…COUPLED-SOLVE…` item 4); `m_target`, `m_tx` and the realised outcome separately per user-step (v1.8 §8); the per-boundary `rate_target_attained` series (`…STAGE1-1B…` item 15: "additionally persist the per-boundary attainment series in the receipts for QoS reporting (cheap; **no decision use**)"); deadline-miss fraction as a co-reported QoS field (contract v1 §F2).

**Attempt registry** — `…PIPELINE-AUDITS-CD…` item 2: "an append-only, hash-chained registry `ATTEMPT-REGISTRY-2026-09.jsonl` in the repository (hub) receives a `STARTED` record — experiment, panel, cell, unit, code/provider/world/calibration digests, UTC — **before any outcome-producing call**; `DONE`/`ABANDONED` follow; merge loads the registry and rejects units without a matching STARTED, duplicates, or unadjudicated abandoned attempts."

### A.11 Arms, experiments and estimands

**Four named experiments, never conflated** — contract v1 §C3:

> (i) *learned neutral-source experiment* (primary for the C1/C2/C3 claims): FULL, DROP_C1, DROP_C2, DROP_C3 by neutral-source substitution of the named route with all routes retained, updated and deployed; ALL_NEUTRAL_CONTROL; external BASELINE; claim wording: "informative source training for route x improved pooled EE relative to the specified neutral source training, with the other routes informative and all heads retained"; (ii) *oracle factor-score removal* (physics regime map, stage-4 item 18); (iii) *checkpoint knockout* (secondary: zero the deployed contribution, machinery fixed; measures reliance and exposes hidden score restoration); (iv) *architecture removal* — **named, not run**.

**Oracle factor arms in the physics matrix** — `V025-CONTROLLER-DECISIONS-ENGINE-AUDIT-2026-09-08.md` item 2 (B2, design **CHANGE**):

> the set decoder's score for FULL/DROP arms is the **sum of the declared targets**, not the exact realised objective: S(config) = C1(config) + C2(config) + C3(config) … DROP_Cx removes exactly one term inside the **same selector class and the same catalogue**; `DROP_C3` = no interaction term (joint search kept); an additional `UNI` arm = unilateral-only search with all three terms is reported separately (**search value ≠ interaction value**); `S_UNI` … is the iterated exact-unilateral comparator. The exact-F oracle is a **ceiling arm** (U1/J1/union certificates), **never a factor arm**. **Marginals are measured on the realised pooled endpoint ΣB/ΣE, never on nominal scores.**

Factor-arm composition — v1.5 §2: "FULL = C1 + C2 + C3; DROP_C1 = C2 + C3; DROP_C2 = C1 + C3; DROP_C3 = C1 + C2 (additive), all in the same selector class and catalogue."

**Coordination attribution** — contract v1 §C4:

> FULL (S3) > DROP_C3 **and** FULL > the S_UNI-equipped comparator on held-out realised pooled EE, QoS margins met, plus decision-relevant nonadditivity (the selected profile differs from the additive/unilateral optimum at a reported fraction of anchors, including rejected harmful joint moves) — **the requirement "g_I ≠ 0" is withdrawn**. **Learned value (S3 vs matched S0)** is one predeclared axis: realised closed-loop pooled EE under equal computation budget including timeouts; matching S0 at lower compute is an acceptance claim, reported separately.

**Admissible learned claims are bounded** — contract v1.2 §3:

> Over one catalogue that is exactly evaluated, **S3 cannot exceed S0's maximum of the same score**; therefore the only admissible learned claims are (i) better realised closed-loop pooled EE under model mismatch, (ii) equal decision quality at materially lower measured end-to-end computation, or (iii) a measured residual task (search allocation, evaluation-count reduction). The claim axis is named before training.

**Zero results are allowed** — contract v1 §C6: "a zero C3 source marginal ends the positive C3 claim under this scope; an interval excluding the practical margin supports 'no practically relevant benefit'; a lower-bound failure alone is inconclusive; **neither permits changing features, catalogues, sources or regimes until C3 becomes positive**."

### A.12 Admission trichotomy (the endpoint of the physics matrix)

v1.9 §6 (superseding v1.6 §4), stated so that it is monotone:

> `ADMIT_FULL`: all load-bearing certificates pass — S0 realised gain over BASE ≥ +1 %, S0 > certified S_UNI beyond the certified numerical error, C1's oracle marginal positive beyond numerical error, C3's interaction term decision-relevant (the coordinator's choice differs from the additive selection at a reported non-trivial fraction of anchors and the realised contrast is positive), C2's forecast validity established, QoS/validity/deadline pass. `ADMIT_C1C2`: identical except that the C3 conditions are not met; training is admitted, C3 is carried as an evaluated layer, and the resulting learned C3 statement is explicitly labelled as lacking an oracle certificate and is therefore a weaker claim than under `ADMIT_FULL`. `NOT_ADMITTED`: C1's oracle marginal or the QoS/validity/deadline conditions fail → contingency ladder rung 1. **No branch weakens a condition another branch imposes on the same factor.**

Load-bearing vs informative vs diagnostic — v1.6 §4:

> Load-bearing for the a-r0 admission decision: (i) S0's **realised** pooled-EE gain reported beside its nominal prediction; (ii) S0 vs **certified** S_UNI (matched information, objective, budget and fallback accounting; termination certificate present, else the comparator is labelled budget-limited and the contrast is not load-bearing); (iii) the corrected factor-oracle marginals under the final C2 rule; (iv) realised availability/QoS, physics validity and deadline behaviour with timeout/fallback outcomes counted in B and E. **Informative but not decisive:** J1 − U_all (two purely additive good moves can exceed the best single move). **Diagnostics only:** cap-hit, plateau share, ACM distribution, lit beams.

**Claim ladder for C3** — `V025-CONTINGENCY-LADDER-PREOUTCOME-2026-09-08.md` Rung 0:

> **Level B (the owner's requirement, primary):** the C3 layer raises realised pooled EE over the C1 + C2 policy under the same deployable information, catalogue and 10 s compute budget: FULL(S3 or S0) vs DROP_C3, relative gain lower bound > +0.5 %, QoS margins met. **Level A (secondary, stricter):** in addition, FULL > the information-matched S_UNI comparator with decision-relevant nonadditivity. **Level C (tertiary):** learned S3 matches S0 at lower compute (acceleration), reported only if A/B hold for S0.

### A.13 Two tracks

`V025-PILOT-TRACK-DECLARATION-2026-09-09.md`:

- **Track F — pilot (starts immediately).** "prove the whole stages 6–8 path runs end to end on real successor physics, and obtain a first *learned* C3 signal in hours rather than days." Scope: "quarantined development worlds only (`V025_PROBE/world/{1,2}` for training rows, `world/{3,4}` for evaluation), the engine as it stands at the stage-4d/4f snapshot with the fixed provider, 30 anchors per world per carrier, the sealed catalogue and arms, **4 learner seeds** and the sealed learner configuration, 6 arms." Label on every artefact: `PILOT_NOT_CLAIM`.
- **Track S — sealed confirmatory path (unchanged).** "Stage 4g → its audit → seal package → a-r0 matrix → admission trichotomy → PHYSICS-GO → confirmatory source generation and training on the claim panel with 16 seeds. Nothing in Track F alters this sequence, its worlds, its seeds or its rules."

### A.14 Mandatory synthetic acceptance gate before any real source generation

Contract v1 §G — "**mandatory gate before any real source generation**":

- **T1 Exhaustive decomposition and intervention:** "hand-computed 3-user, 2-action, 3-step fixture with additive / synergistic (F = 0, −1, −1, 2) / antagonistic (0, −1, −1, −4) cases, a dummy user (credit 0), nonzero Φ charged once, a future outage; production target builder and selectors; exact reconstruction of both identities; oracle DROP behaviour as hand-predicted; neutral-source DROP retains and trains the route; knockout removes the deployed contribution."
- **T2 Information twins / interaction reversal / additive placebo through the production path:** "paired contexts with identical per-user rows but opposite joint interactions; S3 must separate them using declared coalition context and **fail when it is removed**; poisoned post-decision outcomes, realised future fading and hidden legacy reset state leave current features and actions unchanged; physical-identity relabelling invariance; jointly infeasible individual proposals repaired; **an injected timeout exercises the real fallback**; the additive placebo yields Ψ̂ ≈ 0 and S3 = S_UNI decisions."
- **T3 Crossed-cluster inference through the real merger:** synthetic raw receipts with controlled date/seed/world effects, "unequal energies (pooled ≠ mean EE), identical arms, zero-bit and undefined-denominator cells, injected alternatives, **least-favourable conjunction null** (one component at the +0.5 % boundary); verify pairing, interval calibration, conjunction power and QoS rejection."

**Order of operations** — contract v1 §H: "Build 1 (running) → build 2 applies this v1 and implements T1–T3 → fresh-context audit of the build → controller seal of spec v1 → **real source generation only after the calibration freeze and PHYSICS-GO (a-r0 admission)**; training in the pipeline session with checkpoints every 100 source epochs; the owner is notified before any long continuation."

---

## B. What the physics succession INVALIDATES from v0.23

### B.1 Segment-anchored power → memoryless rate-target TPC

**OLD** — `CONTROLLER-POSITION-PHYSICS-SUCCESSOR-2026-09-08.md` §1 "What the code does today (verified by the red-team; I checked the cited lines)":

> `recurrence_power_w` (`src/mcrl/env/link_budget.py:379`): p(t) = p⁰ · G^T(θ(τ)) / G^T(θ(t)); p⁰ = 0.825 W (ruling F-1) at every segment start τ; the in-segment budget is 3.010 dB, beyond which the link is infeasible (service rule).
> Wanted signal (`step.py:946-957`): P_rx ∝ p(t)·G^T(θ(t)) = p⁰·G^T(θ(τ)) — the received level is *held* at the segment-start value; bits therefore do not follow geometry within a segment; energy rises as the user drifts.
> Any association change resets τ and p⁰ (`step.py:829-861`); handover costs no joules (`system_power_w`, `link_budget.py:549`) but the training reward charges Φ₁ = 0.5 / Φ₂ = 1.0.
> Per-beam RF power = max over the beam's users; PA supply from `pa_efficiency` with 5 dB back-off (saturation 5.218 W, cap 1.65 W); circuit 0.338 W per active beam, baseband 0.200 W per active satellite; nothing for inactive beams; bits = full-buffer Shannon over an equal bandwidth split.

Precision from the same file, §Addendum 13:30 UTC (after `PHYSICS-AUDIT-SEGMENT-ANCHORED-POWER-CLAUDE-OPUS-2026-09-08.md`):

> power is recomputed every step; what is frozen is the reference gain G^T(θ(τ)); the in-segment invariant is the product p·G^T (received level). Path loss, fading, interference and the beam max are current. The only in-segment change is the p > p_max feasibility test → outage → forced re-anchor. … Verdict (ii): declared ≠ standard; **no power-control reference updates only at handover**.

**NEW** — `V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.1-AMENDMENT-2026-09-08.md` §Amendments 1:

> **Primary architecture: (a-r) `V025-ANGLE-RATE-TPC-TDM-ACM`** — memoryless angle-aware power control with a per-user nominal rate target r* = 50 000 000 bit/s (inherited as a synthetic operating point from Track B lever L1; explicitly not calibrated demand). Equal-airtime full-band TDM. Required SINR from the frozen ACM profile: Γ_r(n_b) = min{γ_m : W·SE_m/n_b ≥ r*}; slot power p_u = min(1.65 W, Γ_r(n_b)·(N₀W + Î_u)/ĥ_u), ĥ_u = G^T(θ_u)·L_u·G^R; history-independent coupled solving; slot-integrated PA accounting. **Angle drives power through ĥ_u; occupancy drives power through Γ_r(n_b).**

**CHANGED BY:**
- `CONTROLLER-POSITION-PHYSICS-SUCCESSOR-2026-09-08.md` §2 (my reading of the physics): "The gain-inversion recurrence is a *return-link* (uplink) power-control idea transplanted to the forward link. Operational LEO forward links run each carrier/beam at a fixed, backed-off RF power and let ACM change the MODCOD as the terminal's SNR drifts; the transmitter does not ramp power to freeze the received level across a 30 s orbital drift."
- `CONTROLLER-REFERENCE-DESIGN-NORMAL-POWER-EE-2026-09-08.md` §6 row 1: current "Per-user power recurrence p(t) = p⁰·G^T(θ(τ))/G^T(θ(t)), p⁰ reset at every handover; received level frozen at segment start" → normal "Fixed P_b per beam; rate follows geometry" → consequence "Energy rises with segment age for no bits; churn is free for the endpoint → renewal premium; training signal contradicts physics" → handling **FIX (successor physics)**.
- Astra round-3 §2 item 4 ("Transmission"), bound by v1.0: "**No segment-entry gain, recurrence, reset target or private-power/beam-max hybrid survives.**"
- Sealed in `V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-2026-09-08.md` §Declaration (a-γ form, "no segment memory") and finalised in **v1.1 §1** (a-r form).

**The renewal premium is the specific artefact removed** — `CONTROLLER-POSITION…` §2.2:

> (a) staying on a beam is charged rising energy for *no* extra bits; (b) re-anchoring is free in the endpoint but penalised in the reward; (c) a coordinator that evaluates the endpoint directly harvests the renewal premium (v1's advantage grows +1.35 → +9.26 % with segment age). So the +2.9 % is, until the ablation says otherwise, largely a property of the model, and the learned heads were trained against an inconsistent objective.

§Addendum: "renewal raises EE whenever SE > 2.52 bit/s/Hz (panel SE ≈ 3.67–4.59); a single beam re-anchored at 0.744 dB staleness yields exactly the observed **+2.883 %**; the receipts cannot exclude that **100 % of the energy-side gain is renewal**." Confirmed independently in the pipeline map Stage 3: "`!` renewal premium; confirmed by diag2: forced renewal +0.49 % → exactly 0 under ablation".

**Riders that die with it:**

| Old statement | New statement | Document + section |
|---|---|---|
| Per-beam RF power = **max over the beam's users** | Retired; under fixed P_b "the question disappears", under a-r each user's slot power is solved individually and the PA is **slot-averaged** | `CONTROLLER-REFERENCE-DESIGN…` §6 row 5 ("Retire with (1)"); round-3 §2 item 4; pipeline map Stage 3 invariants: "PA averaged per slot (not PA(max), not PA(Σ))" |
| Handover costs no joules in the endpoint but Φ in the reward (endpoint paid a *negative* handover cost via the p⁰ reset) | "**No event-joule term.**" Φ is QoS only; "the physics must contain **no** hidden incentive that contradicts Φ" | round-3 §2 item 15; `CONTROLLER-REFERENCE-DESIGN…` §1.6 and §6 row 2 ("FIX (reward = endpoint function; Φ stays as QoS + reported)"); pipeline map Stage 4 |
| ZOH energy (≈ +2.27 % undercharge, segment-age dependent) | 47-subinterval trapezoid integration (treatment 0); the ZOH snapshot survives only as **treatment T**, and "T therefore uses the **left endpoint** sample at t, not the terminal t + 30.08 s sample" | pipeline map Stage 3; `V025-CONTROLLER-DECISIONS-STAGE1-1B-2026-09-08.md` item 3 (**CHANGE**), which also corrects the KAT: "the correct KAT is the round-1 one: R(t) = 2 + t over 2 s → true integral 6, left snapshot 4" |
| C2 temporal state = `previous_recurrence_power`, `current_to_segment_start_gain_ratio` (= p⁰/p), `segment_age`, `missing_incumbent` | "Replace `previous_recurrence_power` with **incumbent nominal decoding margin**; gain-to-entry ratio with **forecast SE trend**; `segment_age` with **remaining D2/visibility time**. Retain `missing_incumbent` as a service-state flag; add **refresh phase**." | round-3 §2 item 26; flagged in `CONTROLLER-POSITION…` §Addendum: "under per-step physics three of them become constants. Therefore the successor must redefine C2's persistence/service-risk state from geometry and rate forecasts … **This is a design change to C2, not only to the physics**" |
| λ = 118 424 222.8550065 bits/J derived under the old physics (and C3-S's η_ref = 124 075 740.54723135 bits/J, hex `0x1.d94fb72305d6ap+26`) | "η_ref from a reference run of the successor physics … Re-derive by the same rule"; per setting, "all **31** exact η_ref = λ and κ values are sealed in one immutable file required by every unit; **synthetic dry-run values are inadmissible**" | `CONTROLLER-REFERENCE-DESIGN…` §6 row 8; round-3 §2 item 21; `V025-CONTROLLER-DECISIONS-STAGE2-2026-09-08.md` item 10 |
| Legacy `Segment.continues` keyed on `cell_id` → ≈ 9.6 % uncommanded renewals | "event ledger keyed by **physical (NORAD, beam-chain) identity**, not slot index"; cross gains keyed by `(NORAD, beam-chain)` so co-colour beams of the same satellite are representable | pipeline map Stage 1; `V025-CONTROLLER-DECISIONS-PROVIDER-2026-09-08.md` items 1, 11 |

### B.2 The LC-SRS teacher / C3 — status: **closed at oracle level, replaced by a set-level coordinator, then re-specified as an interaction residual**

Three successive demotions, in order.

**(1) The additive third head is closed by outcome (v0.23).** `DRAFT-C3S-SET-LEVEL-COORDINATOR-CONTRACT-CODEX-GPT6-ASTRA-2026-09-08.md` §1:

> [Oracle marginals] 中，exact others' delivered-bit externality 經 `argmax(Q1+Q2+z/κ)` 合成後，C3 marginal 在 G0–G3 均 ≤0；該 additive third-head 路線在已測目標與 regimes 上 **closed at the oracle level**。

("After composing the exact others'-delivered-bit externality through `argmax(Q1+Q2+z/κ)`, the C3 marginal was ≤ 0 in G0–G3; that additive third-head route is closed at the oracle level for the tested targets and regimes.")

Route decision — `ADJUDICATION-SUCCESSOR-ROUTE-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md` §DECISION 1: "**Adopt Route C.** Close R7 and its conditional five-arm launch permanently. Establish the independent C1/C2 successor; keep C3 outside its critical path. Exercise the delegated authority without asking the owner." (`ASTRA_SUCCESSOR_ROUTE=C`.) Its §DECISION 6 also requires "successor-specific negatives **proving Q3 absence** and baseline separation."

Structural diagnosis — `CONTROLLER-REFERENCE-DESIGN-NORMAL-POWER-EE-2026-09-08.md` §6 row 7: current "'C3 = load balancing / observability' framing; additive per-user Q3" → normal "Coordinator for consolidation; per-user heads for surplus and persistence" → consequence "**Two weeks of ≤ 0 oracle marginals were structural**" → handling "Reframe (C3-S shape is the normal one)". The same file §4.2 gives the reason: "Additive per-user surpluses **cannot represent the joint gain of emptying a beam** (the saving appears only when the last user leaves): that gain must be given to a coordinator or a shaped joint term, **not hidden in per-user Q-heads**."

**(2) The architectural replacement is the set-level coordinator (C3-S).** `DRAFT-C3S-…` §1:

> C3-S 將第三 Catfish 定義為兩個 learned heads 之上的 **set-level coordinator**：Q1/Q2 提出 BASE complete profile，deployable model-based decision layer 評估完整候選配置，選定後 atomic execution。**沒有第三個 additive Q head、第三頭訓練或個人化 surplus 分配。**

("C3-S defines the third Catfish as a set-level coordinator above the two learned heads: Q1/Q2 propose the BASE complete profile, a deployable model-based decision layer evaluates complete candidate configurations, and the selection is executed atomically. There is **no third additive Q head, no third-head training and no individualised surplus allocation**.")

Sealed into the successor by round-3 §2 item 29 (bound by v1.0's "items 1, 3, 5–31 unchanged"):

> A set-level consolidation coordinator operates on complete proposals, scores whole configurations with the same system objective/QoS terms, and commits atomically. BASE is always present and wins ties. Include unilateral proposals and genuine multi-user evacuations; count actual changed users, not catalogue labels. S0 uses deployable nominal physics; **learned S3 must additionally beat matched S0**.

v1.1 §4 extends its action repertoire: "C3 = set-level coordinator scoring whole configurations, with **coordinated load transfers / swaps included alongside evacuations**, one prospectively frozen catalogue across matched arms."

**(3) The LC-SRS *target* (the unilateral externality e_i) is explicitly not transferred.** `V025-CONTROLLER-DECISIONS-STAGE2-2026-09-08.md` item 5 (**CHANGE**):

> **LC-SRS e_i binding** — **CHANGE**: under the sealed whole-network C1 (which already contains every unilateral bit and joule change of the network), the unilateral externality e_i is inside C1, so the successor C3 target carries **no e_i term**: z₃,ᵢ = Ψ/2 for pairs and the equal-share (Shapley) split of the set interaction for larger sets, with Ψ computed on F = B − η_ref·E per regime (per-cell re-optimisation). This is the round-6 no-double-counting rule; **the historical LC-SRS e_i (defined for an own-bits-only C1) is not transferred.**

Corroborated by the pipeline map Stage 5: "**C3:** interaction share only (stage-2 decision 5: z₃ = Ψ/2, Ψ = F₁₁ − F₁₀ − F₀₁ + F₀₀ on F = B − η_ref·E, per regime) — `!` **legacy executed C3 ≠ declared LC-SRS Ψ; J reused across regimes**."

**Current definition.** `C3(config) = Ψ_A`, the interaction residual (contract v1 §B4; v1.5 §2), learned by the set-conditioned scalar interaction head Ψ̂_θ (contract v1 §C2), deployed as S3 over the bounded catalogue.

**Subsequent corrections to C3's own specification (all post-v1.5):**

| Old statement | New statement | Document + section |
|---|---|---|
| Coalition label computation capped at \|A\| ≤ 4 ("2^\|A\| subset evaluations bounded"), contract v1 §B5 | "Computing Ψ_A needs the baseline, the \|A\| singletons and one joint evaluation, i.e. **\|A\| + 2 evaluations**. Ψ_A is therefore computed for **every selected coalition regardless of size**; only the exact per-user Shapley attribution stays capped at \|A\| ≤ 4 (reporting only), with `credit_split = NOT_COMPUTED_LARGE_SET` above it. This restates the 4c-gate decision item 1 and **overrides any narrower reading of contract v1 §B5**." | **v1.7 §3**; applied to the contract as **contract v1.2 §1** |
| Exact Shapley validation over subsets was implemented in the runner | "the a-r0 FULL selector on the quarantined world chose a **100-user coalition**; the runner then tried an exact Shapley validation over **2^100 subsets** and failed closed … **The 2^\|A\| validation is removed.**" "**No selection or validation step may depend on a per-user split.**" | `V025-CONTROLLER-DECISIONS-4C-GATE-2026-09-08.md` preamble + item 1 |
| Shapley credit "wired into selection" | "Shapley credit is reporting only (\|A\| ≤ 4); selection uses Ψ_A at set level; '**wired into selection**' is **withdrawn** as a requirement." | `V025-CONTROLLER-DECISIONS-4C-AUDIT-ROWS-2026-09-08.md` item 4 |
| Coordination attribution requires "g_I ≠ 0" | "**the requirement 'g_I ≠ 0' is withdrawn**"; replaced by decision-relevant nonadditivity at a reported fraction of anchors | contract v1 §C4 |
| Scalar interference summary suffices for the set head | "the **pairwise cross-gain terms among the affected beams** (not only a scalar interference summary — a summary can hide exactly the difference that flips a coupled fixed point)" | contract **v1.2 §2** |
| A learned S3 may claim general superiority | "Over one catalogue that is exactly evaluated, **S3 cannot exceed S0's maximum of the same score**"; three named admissible axes only | contract **v1.2 §3** |
| Any S_UNI is a valid comparator | "A **budget-limited** S_UNI is an operational comparator and is labelled as such; **only** a S_UNI with a completed-neighbourhood **termination certificate** supports the 'beyond exhaustive unilateral improvement' claim" | contract **v1.2 §6**; v1.6 §4(ii) |

**Vocabulary ceiling fixed in advance** — ladder Rung 0: "Wording is fixed now: **a Level-B-only result is described as 'exact/learned joint re-evaluation layer', never as 'coordination'.**"

### B.3 The old service rule → PHY decodability

**OLD.** `CONTROLLER-REFERENCE-DESIGN-NORMAL-POWER-EE-2026-09-08.md` §6 row 3: current "Service = power feasibility within the 3.01 dB in-segment budget (p ≤ p_max)" → normal "Served ⇔ SINR ≥ SINR_min" → consequence "**Service saturates by construction; guards vacuous**" → handling "FIX with the physics". Pipeline map Stage 3 (legacy): "served = masked action ∧ p ≤ p_max (`!` **feasibility, not decodability**)".

**WHY IT IS DEAD.** It is a property of the deleted recurrence, not of the link. `CONTROLLER-REFERENCE-DESIGN…` §1.5:

> **Service.** A user is served iff SINR_u ≥ SINR_min (and, if modelled, a minimum-rate guarantee). "**Served" is a function of the current link, not of a power-feasibility recurrence.**

Once the in-segment 3.010 dB budget is removed there is no p > p_max event to define outage, and the old test would either never bind or bind arbitrarily; the successor also removes the "forced re-anchor" that the test produced.

**NEW.** Astra round-3 §2 item 10 ("Service"), bound by v1.0:

> For an allocated transmission, `served_PHY ⇔ SINR ≥ SINR_min`, with SINR_min = 10^(−1.441812460/10) = 0.7174947935. Below it: zero decodable bits. NULL is unserved. Report time-weighted decoding availability and complete-service user-steps separately; **this is not a minimum-throughput guarantee.**

Sealed wording — v1.0 §Declaration: "served ⇔ SINR ≥ −1.4418 dB **after joint resolution**". And v1.0 §Service definition:

> **Service definition:** PHY decodability with QoS co-primaries (astra §2 item 10, 23). **A guaranteed-rate service endpoint is not declared**; if the owner later requires one it is a separate, additional endpoint.

**Resolution order that makes it well-defined** — round-3 §2 item 11: "Fix assignments/airtime → radiate and compute joint interference → decode. **Failed attempts retain RF energy/interference and their scheduled share; no retrospective pruning or bandwidth redistribution.** Association legality is checked before execution; instantaneous decoding is checked afterward."

**CHANGED BY:** `CONTROLLER-REFERENCE-DESIGN-NORMAL-POWER-EE-2026-09-08.md` §1.5 and §6 row 3; astra round-3 §2 items 10 and 11; sealed in `V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-2026-09-08.md` §Declaration and §Service definition.

**Critical corollary — the rate target is NOT a service rule, and rate attainment is not service.**

- v1.1 §2 (**Infeasibility / accounting**): "if no MODCOD meets the rate at the cap, **mark the target infeasible and transmit at the RF cap**; keep actual partial delivery, interference and energy; **no pruning or repacking. PHY service (decodability) is unchanged; rate-target attainment is reported separately.** Bits = achieved decodable ACM bits (full buffer)."
- `V025-CONTROLLER-DECISIONS-STAGE1-1B-2026-09-08.md` item 6 (**Availability naming**): "decoding availability (PHY threshold, interruption-independent), useful availability (minus H blackout), complete-service user-step, and — **distinct** — `rate_target_attained`." Item 15 keeps `rate_target_feasible` (nominal feasibility at every integrated boundary) and `rate_target_attained` (realised decodable bits ≥ r* per user-step) as separate fields, with "no decision use" for the per-boundary series.
- v1.8 §5 (**Traffic model declared explicitly**): "The numerator is saturated (full-buffer) decodable throughput under a per-user rate-target power controller; the rate target is a **power-control setpoint, not a demand model**, and realised per-user rates may exceed it. Reported alongside every claim: rate attainment, availability and the coverage/outage distribution. **Finite demand or queues would be a versioned model amendment with affected comparisons re-run, never a relabelling.**"
- `V025-CONTROLLER-DECISIONS-STAGE1-1B-2026-09-08.md` item 19: "r* = 50 Mbit/s is a synthetic operating point (`VERIFY_SOURCE`); **no demand or hardware claim**."

### B.4 Other invalidated concepts (complete ledger)

| # | Old statement | New statement | Document + section |
|---|---|---|---|
| 1 | Full-buffer Shannon over an equal bandwidth split, no SE cap | ACM from EN 302 307-1 V1.4.1 Table 13 (all 28 entries, normal frames, no pilots), roll-off α = 0.20, margin M = 1.7 dB, SE_max = 3.710855833 bit/s/Hz; "**Rewards concentration with unphysical SE**" is the consequence being removed | round-3 §2 items 8, 9; `CONTROLLER-REFERENCE-DESIGN…` §6 row 4 (**FIX (cap + margin, cited)**) |
| 2 | No standby / bus floor; instant on/off | P_idle = 0 **primary** with declared sensitivity f = 35/420 = 1/12 → 0.698609768 W/chain; P_bus = 0 **denotes exclusion**, not a physical zero | round-3 §2 items 13, 14; `CONTROLLER-REFERENCE-DESIGN…` §6 row 6 (**DECLARE + SENSITIVITY**) |
| 3 | Standby inventory derived from the realisable-cell count | "each satellite carries a declared **12-RF-chain census** (`VERIFY_SOURCE`; matches the f = 1/12 sensitivity); idle chains = 12 − active beams (≥ 0); the primary P_idle = 0 is unaffected; **standby no longer depends on the realisable-cell count**" | `V025-CONTROLLER-DECISIONS-PIPELINE-AUDITS-CD-2026-09-08.md` item 11 |
| 4 | Legacy shadow drawn at a fixed 10° elevation; receive-pattern floor never applied | shadow at the **actual elevation**; S.465 θ_min = 2.043298703° branch applied in the receive pattern and in interference | pipeline map Stage 2 (`!` items); `…STAGE1-1B…` §Carry-over |
| 5 | Interference keyed per satellite; colour not bound to beam identity | per-chain cross gains keyed `(NORAD, beam-chain)`; "Colour is a property of the beam-chain (cell colour in the reuse-3 plan); a user inherits the colour of its serving chain; invariant enforced at tape construction; KAT: the reuse mask is **reciprocal**" | `V025-CONTROLLER-DECISIONS-ENGINE-AUDIT-2026-09-08.md` item 3 (B3); `…PROVIDER…` items 1, 11 |
| 6 | Legacy 0° screening | "**10° visibility floor** … stands as the successor's declared minimum operating elevation (`VERIFY_SOURCE`; a model choice, documented as a deviation from the legacy 0° screening)" | `V025-CONTROLLER-DECISIONS-PROVIDER-2026-09-08.md` item 2 |
| 7 | Q1 state 228-D, Q2 state 448-D (hetero) | sealed successor Q1 schema; **22-field** Q2 with its own SHA; the 21-field SHA `54ab6a82…` "**retired and never stamped again**" | pipeline map Stage 6; contract v1 §B2/§B3; Stage-C spec item 2 |
| 8 | Replay buffer / Bellman replay | "pairwise zero-bootstrap regression on typed deterministic aggregate batches … **no Bellman replay in the successor**"; deterministic aggregate epochs with sealed row counts/order/digests | contract v0 item 6; contract v1 §C1, §C7 |
| 9 | "three independent initializations" (round 3 §4.1) → "five learner seeds" (contract v0 item 8; pipeline map Stage 7) → "**12 learner seeds**" (contract v1 §C7; Stage-C spec item 6) | "**learner seeds: 16**"; "the learner-seed count is **16**, derived from the domains `V025_LEARNER/seed/{1..16}` … Item 6 of the stage-C spec decisions is superseded to that extent" | contract **v1.1 §1**; `V025-CONTROLLER-DECISIONS-STAGEC-SPEC-ERRATUM-1-2026-09-09.md` |
| 10 | δ = "+0.5 **pp**" (v1.2 §4; contract v0 item 12) | "The success margin is a **relative** pooled-EE gain: EE_FULL / EE_DROP − 1 ≥ +0.5 % (the phrase '+0.5 pp' in v1.2 §4 meant this relative percentage; **pooled EE has no percentage-point scale**). The 95 % lower bound of that relative gain must exceed +0.5 %." | **v1.4 §1** |
| 11 | One-way cluster bootstrap as primary (v1.2 §3) | "Because dates and learner seeds are **crossed** (audit A), the primary interval for every contrast is a **two-way pigeonhole bootstrap** over TLE dates × learner seeds with arms paired within each resample and ΣB/ΣE recomputed per draw; the one-way cluster bootstrap of v1.2 §3 and the delta-method interval become supplementary. For the learner-free physics matrix the primary is the one-way bootstrap over TLE dates." | **v1.5 §3**; `…PIPELINE-AUDIT-A…` item 2 |
| 12 | Round-3 priority `b0 > a0 > a′0 > …` | `a-r0 > a′-r0 > a-γ0 > b0 > a′-γ0`, then S/H/SH/T; "Launcher and admission artefacts **reject the round-3 order**" | v1.1 §3; v1.2 §1; `…STAGE1-1B…` item 1 |
| 13 | "Total: 28 primary-eligible cells" | **25 + 6 = 31 settings**; "the launcher **may reject the number 28**" | **v1.3 erratum**; `…STAGE2…` item 2 |
| 14 | v1.6 §1 margin scoring re-solved required power from the attenuated gain (p_m = p_N/q) | "**executed and predicted transmit power are computed from the nominal gains** (unchanged); the quantile enters **only the predicted reception of the wanted link**" — otherwise "the margin bought no reserve, only more power and more interference, and it changed feasibility at the cap" | **v1.9 §1** (named a **defect**) |
| 15 | v1.6 §1 applied the quantile to every link | "The quantile applies to the **wanted link only** … a uniform application is not conservative and distorts interference-limited cases. **Interference terms keep their nominal values in the selection view.**" | **v1.9 §2** (named a **defect**) |
| 16 | v1.6 §1 called it the quantile of "shadow + scintillation" | "The quantile is of the **complete fading product**": G = R · 10^(−(X + L_c(e))/10) with Rician power fading R, Gaussian shadow loss X and deterministic scintillation L_c(e) | **v1.9 §3** |
| 17 | v1.6 §1 justified q₁₀ as "the standard 90 %-availability link-budget convention" | "**That is withdrawn**: a per-link 10th-percentile channel-gain quantile does not establish 90 % network availability, and no such universal convention is claimed. The rule is named exactly what it is: a **pre-specified tenth-percentile channel-gain scoring rule**, applied identically to every arm, with the level fixed before any formal outcome and **disclosed as having followed development inspection**." | **v1.7 §1** |
| 18 | Every arm ranks by the full F_m | arm-specific ranking keys; "**no arm may rank, prune or reject using a score it has had removed**" | **v1.9 §4** (named a **defect**) |
| 19 | v1.6 §4 admission trichotomy | restated monotone in **v1.9 §6**; and "The controller's earlier claim that v1.6 was '**uniformly stricter**' is **withdrawn**." | v1.9 preamble + §6 |
| 20 | C2 expected to produce a set-level selection marginal | "**C2's certificate in the physics matrix is therefore forecast validity, not a selection marginal** … C2's decision value is tested in the learned stage, where Q2 shapes the proposal." A zero set-level C2 marginal "is reported as such and **never patched** by substituting Q2's separate effect on the proposal." | **v1.9 §5** |
| 21 | Coordinator deadline 30.08 s (stage-4 item 12; contract v0 item 9) | "the coordinator's compute budget is **10 s wall** on the declared worker count (the rest of the 30.08 s interval reserved for sensing/transport/validation/commit)" | contract **v1 §F2** |
| 22 | "per-anchor provider target of 1 s" | "**withdrawn** in favour of 'once per world'" | `…SELECTION-TIME-APPROXIMATIONS…` item 5 |
| 23 | Factor arms scored on the exact realised objective | "the set decoder's score for FULL/DROP arms is the **sum of the declared targets**"; "**Marginals are measured on the realised pooled endpoint ΣB/ΣE, never on nominal scores.**" | `…ENGINE-AUDIT…` item 2 (**B2**, design **CHANGE**) |
| 24 | Treatment H/SH implemented | "**B1 — treatment H/SH is a no-op.** The runner never constructs `InterruptionEvent`s, so `useful_availability ≡ decoding_availability` and 10 of 31 settings are bit-identical duplicates." FIX: interruption events built from the common event ledger; "the setting-duplicate test asserts all 31 receipts are pairwise distinct" | `…ENGINE-AUDIT…` item 1 |
| 25 | Synthetic mechanism map results from the stage-2 sweep | "its sweep is **re-run on the stage-4 code** before any expectation E1–E4 is scored. Results from the stage-2 sweep are labelled `SUPERSEDED_B2`." R2 to be completed only after `AR0-DONE`; "E1–E4 are **NOT SCORED** on a partial grid" | `…ENGINE-AUDIT…` item 7; `V025-SYNTHETIC-MAP-R2-COMPLETION-DECISION-2026-09-09.md` |
| 26 | "before" state of an arm at a matched anchor = the same-step BASE proposal | "at a matched anchor the '**before**' state of every arm is **the anchor's incumbent association** (the carrier's committed physical assignment at t − 1), never the same-step BASE proposal; events are classified by physical identity (stay / beam change / satellite change / re-entry / cell re-key from the dwell boundary)" | `…PIPELINE-AUDITS-CD…` item 1 |
| 27 | Probe world 1 usable for the formal matrix | "`V025_PROBE/world/1` was opened by the provider rehearsal before sealing (real bits/joules printed in the provider log). It is **quarantined** … The formal matrix uses fresh domains `V025_PROBE_R2/world/{1..4}` and `V025_CAL_R2/world/{1..2}`" | `…PIPELINE-AUDITS-CD…` item 4 |
| 28 | Solver failure at 4 096 iterations = INVALID; certificate failure stops the run | budget 65 536; `CONVERGED_SLOW` introduced; "An infeasible or slowly converging BASE is a **legitimate physical state, not an error**; the runner must never stop on it." | `…COUPLED-SOLVE…` preamble + items 1–2 |
| 29 | v1.6's top-1 agreement diagnostic sufficient for robustness | "a paired **closed-loop quantile sweep** over α ∈ {0.05, 0.10, 0.25} plus the unchanged nominal selector … The top-1 agreement diagnostic of v1.6 is retained but is **explicitly insufficient on its own**." | **v1.9 §7** |
| 30 | Contract v1 §E analytic power statement (per-contrast power ≈ 0.86; conjunction ≈ 0.64) | "**The analytic estimate of v1 §E is withdrawn**"; replaced by the measured table (16 seeds → 0.675 ± 0.065 conjunction power at 5 % date SD) | contract **v1.1 §2** |

### B.5 A pending correctness item that is declared but not closed at the freeze

v1.8 §8 — **PENDING — ACM causality and decoding reserve**:

> Round 9C observes that the credited MODCOD may be selected from the same realised SINR used to credit bits (an ideal/genie ACM bound) and that, if the power-target SINR equals the decoding threshold, the declared 1.7 dB implementation margin creates **no fading reserve** (success would require realised fading ≥ 1). An audit (`ACM-CAUSALITY-AUDIT-2026-09-09.md`, started 02:00 UTC) is verifying this in the engine. Disposition, declared now and not conditioned on any outcome: **if the transmitted mode is selected from realised information, that is a defect and is corrected before the formal matrix** — the transmitted mode is chosen from the same causally available (margin-adjusted nominal) view used for selection, and credited bits are those of the transmitted mode when the realised SINR clears its threshold, zero otherwise. The v1.6 tenth-percentile rule is thereby the mechanism that creates the decode reserve that the implementation margin does not, and the fix applies identically to every arm. Whatever the audit finds, the engine reports `m_target`, `m_tx` and the realised outcome separately per user-step.

v1.8 §9 adds a blocking validity certificate: "**Link-closure ledger** (round 9C's decisive check) **is required before the seal**: an independent computation of EIRP, path and pointing losses, receiver G/T, occupied bandwidth, C/I and implementation losses at representative and edge geometry, compared separately against the transmitted-mode threshold, the rate-target mode and the lowest mode, and reconciled with the simulator's own flags. It is a **validity certificate, not a performance result**."

<!--PART3-->

