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

---

## C. Key formulas of the successor (LaTeX, exact symbol names)

All symbol names below are the ones used in the sealed documents. Numeric constants carry the provenance label the documents give them.

### C.1 Composed channel gain and the RF/power requirement

Nominal composed link gain (the "composed link budget" of the independent-oracle KAT):

$$\hat h_u \;=\; G^{T}(\theta_u)\cdot L_u \cdot G^{R}$$

**Primary architecture a-r (rate-target TDM)** — v1.1 §Amendments 1, per 30.08 s step, per simultaneous slot configuration:

$$\Gamma_r(n_b)\;=\;\min\bigl\{\gamma_m \;:\; W\cdot SE_m / n_b \;\ge\; r_*\bigr\},
\qquad r_* \;=\; 50\,000\,000\ \text{bit/s}$$

$$p_u\;=\;\min\!\left(1.65\ \mathrm{W},\;\; \Gamma_r(n_b)\,\frac{N_0W+\hat I_u}{\hat h_u}\right)$$

with $n_b$ = the number of assigned users of the beam (occupancy). "Angle drives power through $\hat h_u$; occupancy drives power through $\Gamma_r(n_b)$."

**Sensitivity sibling a-γ (fixed-SINR TDM)** — v1.0 §Declaration; round-3 §4 table:

$$p_u\;=\;\min\!\left(1.65,\;\; \gamma^{\star}\frac{N+\hat I_u}{\hat h_u}\right),
\qquad \gamma^{\star} \;=\; 5.660030272 \;\;(=7.528187540\ \mathrm{dB})$$

$\gamma^{\star}$ is "the 8PSK 2/3 threshold of EN 302 307-1 Table 13 with the 1.7 dB margin and roll-off 0.20 correction".

**Reference model b (fixed EIRP + ACM)** — round-3 §2 item 2: $P_b = 1.65$ W per active beam, constant regardless of occupancy; ACM alone carries geometry into bits.

**FDM siblings a′-r / a′-γ** — v1.0 §Declaration; round-3 §4 table: per-user RF ceiling $1.65/n_b$; beam RF $p_b=\sum_u p_u$; actual bandwidth $W/n_b$ and noise $N_0W/n_b$; "sub-band-consistent noise/PSD/overlap". Sub-band alignment (`…STAGE1-1B…` item 4): "sub-bands start at the low band edge, frozen ascending user-id order, aggressor uniform PSD × exact victim/aggressor frequency overlap."

### C.2 Noise, interference and the coupled fixed point

Thermal noise over the TDM slot uses the **full** band even though airtime is shared (round-4 §A: "$W/n_b$ is **effective airtime bandwidth**; slot noise remains $N_0W$"):

$$N \;=\; N_0 W \;=\; k\,T_{\rm sys}\,W,
\qquad T_{\rm sys}=150+290\bigl(10^{1.2/10}-1\bigr)\ \mathrm{K},
\qquad W=\tfrac{500}{3}\ \mathrm{MHz}$$

(round-3 §2 items 5, 6; KAT 24 checks $kT_{\rm sys}W \approx 5.5754\times10^{-13}$ W.)

Interference is the sum over **active co-colour physical beams**, excluding the serving beam, counted once (round-3 §2 item 5; `…PROVIDER…` items 1, 11 add the same-satellite per-chain term with the legacy P-10 peak-receive-gain override, eq. 3.12a):

$$\hat I_u \;=\; \sum_{b\,\in\,\text{active co-colour},\; b\neq b(u)} p_b \cdot g_{b\to u}$$

**Coupled capped fixed point** — `V025-CONTROLLER-DECISIONS-COUPLED-SOLVE-2026-09-08.md` item 1:

$$p \;\longleftarrow\; \min\!\bigl(\text{cap},\; \Gamma\,(N_0W + I(p))/\hat h\bigr)$$

> The capped rate-target map … with `force_cap` rows is a **standard interference function (monotone, scalable)**, so the iteration from $p = 0$ converges to the unique capped fixed point. Iteration budget raised from 4 096 to **65 536**; convergence when the max absolute change ≤ 1e-10 W **or** the max relative change ≤ 1e-9. Convergence is checked on the update, not on a separate residual that treats cap-bound rows differently.

Certificates: `CONVERGED` / `CONVERGED_SLOW` / `INVALID` (§A.8). Cap-bound users are flagged `rate_target_infeasible`.

**Mechanism identity (why occupancy is an energy lever at all)** — round-4 §A and §D, for equal channels and negligible interference:

$$P_{\rm RF}(n)=A\bigl(2^{\,n r_*/W}-1\bigr),
\qquad
P_{\rm PA}(n)\;\propto\;\sqrt{2^{\,n r_*/W}-1}$$

"$P_{\rm PA}(n)\propto\sqrt{2^{nr_*/W}-1}$ is concave below $n r_*/W = 1$, convex above. At 50 Mbit/s this boundary is $n = 3.33$; activation adds another consolidation incentive."

### C.3 The ACM / rate-target rule

From EN 302 307-1 V1.4.1 Table 13 entries $(e_m, g_m)$ — round-3 §2 item 8, with roll-off $\alpha = 0.20$ and implementation margin $M = 1.7$ dB (item 9):

$$SE_m \;=\; \frac{e_m}{1.20},
\qquad
\gamma_{m,\mathrm{dB}} \;=\; g_m + M - 10\log_{10}(1.20)$$

"Use all 28 entries … normal frames, no pilots; **select the eligible mode with greatest efficiency**. Freeze the transcribed table and its hash."

| Profile anchor | Table efficiency $e_m$ (bit/symbol) | Ideal threshold $g_m$ (dB) | Model $SE_m$ (bit/s/Hz) | Model $\gamma_{m,\mathrm{dB}}$ (dB) |
|---|---:|---:|---:|---:|
| Lowest: QPSK 1/4 | 0.490243 | −2.35 | 0.408535833 | −1.441812460 |
| a-γ power-control target: 8PSK 2/3 | 1.980636 | 6.62 | 1.650530000 | 7.528187540 |
| Ceiling: 32APSK 9/10 | 4.453027 | 16.05 | **3.710855833** | 16.958187540 |

**Service rule:**

$$\text{served}_{\rm PHY} \iff \mathrm{SINR}_u \;\ge\; \mathrm{SINR}_{\min},
\qquad
\mathrm{SINR}_{\min} = 10^{-1.441812460/10} = 0.7174947935$$

**Delivered rate (equal-airtime TDM):**

$$R_u \;=\; \frac{W}{n_b}\; SE\!\left(\mathrm{SINR}_u\right),
\qquad SE \le SE_{\max}=3.710855833\ \text{bit/s/Hz}$$

**Lowest-mode rounding** — `…STAGE1-1B…` item 16: "conservative max convention ($\Gamma_r(1)$ must clear **both** the derived QPSK 1/4 threshold **and** the frozen rounded `served_PHY` floor)."

**Infeasibility** — v1.1 §2: if no mode $m$ satisfies $W\,SE_m/n_b \ge r_*$ at the cap, set `rate_target_infeasible`, transmit at $1.65$ W, and keep the actual partial delivery, interference and energy. Bits credited are "achieved decodable ACM bits (full buffer)".

### C.4 Energy

Round-3 §2 item 12, over interval pieces $k$ of length $\delta_k$:

$$E=\sum_k\delta_k\Bigl\{\sum_{b\in\mathcal I_w}\bigl[z_{bk}\bigl(0.338+\max(P_{\rm idle},P_{\rm PA}(p_{bk}))\bigr)+(1-z_{bk})P_{\rm idle}\bigr]+0.200\,N_{\rm active\,sat,k}+P_{\rm bus}\Bigr\}$$

where $z_{bk}\in\{0,1\}$ is the beam-active indicator and $\mathcal I_w$ is the frozen physical inventory manifest. "An active satellite has at least one transmitting beam."

**PA law** — round-3 §2 item 3, renamed by v1.8 §1:

$$\mathrm{PA\_supply}(p)\;=\;P_{\rm PA}(p)\;=\;\frac{\sqrt{p\,p_{\rm sat}}}{\eta_{\max}},
\qquad p_{\rm sat}=5.217758139\ \mathrm{W},\quad \eta_{\max}=0.35,\quad P_{\rm PA}(0)=0$$

v1.8 §1: "$\eta_{\max}$ is the **saturation** efficiency, so the realised RF-to-DC efficiency is ≈ **19.7 %** at the 1.65 W cap and ≈ **8.6 %** at 0.32 W. The declaration and the paper say '**saturation efficiency**', never '35 % efficiency'." Round-3 §2 item 3: at $P_b$, supply is **8.383317219 W**, efficiency **0.196819**; "**Back-off is already encoded; never subtract it again from emitted RF.**"

**Constants and their status** (round-3 §2 items 12–14; `…PIPELINE-AUDITS-CD…` item 11):

- circuit **0.338 W** per active beam/chain; baseband **0.200 W** per active satellite;
- $P_{\rm idle}=0$ **primary**, "with ideal boundary switching";
- standby sensitivity $P_{\rm idle}=f\,P_{\rm PA}(1.65)$, $f = 35/420 = 1/12$ → **0.698609768 W/chain**, with a 12-RF-chain census per satellite and idle chains $=12-\text{active beams}\ (\ge 0)$; "The active-floor clamp prevents 'turn on at tiny RF to evade standby.'";
- $P_{\rm bus}=0$ "**denotes exclusion** of bus, terminal, gateway and controller energy".

**TDM PA averaging** (round-3 §3 KAT 12): the PA supply is averaged over slots, not evaluated at the mean power — "equal 0.825/1.65-W slots give mean PA supply **7.155608836 W**, not $P_{\rm PA}(1.2375)=7.260165679$ W".

**Handover energy:** none. Round-3 §2 item 15: "**No event-joule term.**"

### C.5 Pooled energy efficiency (the endpoint) and the decision margin

$$\eta \;=\; \frac{\sum_t\sum_u \mathrm{bits}_u(t)}{\sum_t P_{\rm payload}(t)\,\Delta t}\;=\;\frac{\Sigma B}{\Sigma E}$$

"a ratio of sums over the whole panel (**never a mean of per-episode ratios**)" — `CONTROLLER-REFERENCE-DESIGN…` §3; pipeline map Stage 4; contract v1 §D2.

**Decision margin** — v1.4 §1:

$$\delta:\qquad \frac{\mathrm{EE}_{\rm FULL}}{\mathrm{EE}_{\rm DROP}}-1 \;\ge\; +0.5\,\%,
\qquad\text{with the 95 \% lower bound of that relative gain above } +0.5\,\%$$

**Interval convention** — v1.4 §2: "All bootstrap intervals are **central 95 % percentile intervals** (2.5th/97.5th percentiles, linear interpolation as implemented by `numpy.quantile` default); the one-sided decision uses the corresponding endpoint (**2.5th for gains and availability, 97.5th for handover rate and Φ-priced cost**), which is conservative relative to a 5 % one-sided bound and is retained as declared."

**QoS non-inferiority margins** — `…STAGE2…` item 6 (**CHANGE**, numeric, prospective):

> FULL is QoS non-inferior to a DROP arm when the 95 % cluster-bootstrap interval of (FULL − DROP) lies above **−0.5 pp** for complete-service availability, and the interval of the relative change lies below **+5 %** for both the handover rate and the Φ-priced handover cost per user-step.

**Zero/undefined handling** — contract v1 §D3: $B=0$ with $E>0$ gives $\mathrm{EE}=0$ (defined); a draw is undefined only when a denominator ($E$, or the comparator's EE in a relative contrast) is $0$ — "recorded and counted, never substituted".

**Non-cancellation of omitted common energy** — v1.8 §4:

$$\operatorname{sign}\!\left(\frac{B_1}{E_1+E_0}-\frac{B_2}{E_2+E_0}\right)
=\operatorname{sign}\!\bigl(B_1E_2-B_2E_1+E_0(B_1-B_2)\bigr)$$

> so a partial-payload EE gain does not transfer to constellation scope whenever the policies deliver different bits. **Every EE claim names its boundary; no result is restated at a wider scope.**

**Energy boundary sentence** — v1.8 §3, "verbatim in the paper and in every receipt header":

> "Pooled successfully decoded forward-downlink information bits per joule of modelled partial-payload DC energy, comprising user-link PA supply, the declared per-beam chain circuitry and a declared common processing increment, with explicitly stated idle states; spacecraft bus, unmodelled payload functions, feeder and inter-satellite links, and ground/terminal energy are outside this metric."

### C.6 The interval / receipt used for evaluation (the 48 boundary)

$$\Delta t \;=\; 47\times 0.640\ \mathrm{s}\;=\;30.08\ \mathrm{s},
\qquad t_k \;=\; t + k\cdot 0.640\ \mathrm{s},\quad k=0,1,\dots,47$$

Treatment 0 (primary) integrates $[t,\,t+30.08]$ by trapezoid over the 48 samples, i.e. **47 sub-intervals**:

$$X \;=\; \sum_{k=0}^{46} \frac{X(t_k)+X(t_{k+1})}{2}\,\delta,
\qquad \delta = 0.640\ \mathrm{s}$$

KAT (round-3 §3 item 17): $R(t)=t$ over 30.08 s integrates to **452.4032**; a terminal snapshot gives **904.8064**. Treatment T is the **left-endpoint** legacy snapshot (`…STAGE1-1B…` item 3), whose corrected KAT is "$R(t) = 2 + t$ over 2 s → true integral 6, left snapshot 4".

Selection-time grids (never the endpoint): stage 1 at $k = 0$; stage 2 at $k \in \{0,12,24,36,47\}$ with trapezoid weights; escalation may reduce stage 2 to one boundary per offset (§A.7).

Receipt fields: hex floats for bits/joules and energy components, additive opportunities and served counts over the full roster, prior/current physical identities, event type, Φ numerator/denominator, provider/code digests (`…PIPELINE-AUDITS-CD…` item 5); plus the solver certificate, `m_target`/`m_tx`/realised outcome per user-step, the per-boundary `rate_target_attained` series, and the deadline-miss fraction.

### C.7 Reward core, calibration constants and Φ

**Reward core** — round-3 §2 item 22; pipeline map Stage 4:

$$R_t \;=\; B_t - \eta_{\rm ref}\,E_t$$

> using exactly the endpoint's bits and energy, including the setting's interruption/standby treatment. Retain and sum this core independently of normalization, credit assignment and QoS shaping.

Identity KAT (round-3 §3 item 8): $\sum_t R_t \;=\; \sum_t B_t - \eta_{\rm ref}\sum_t E_t$.

**Selector objective with QoS** — contract v1 §B4:

$$F(a) \;=\; B(a) - \eta_{\rm ref}\,E(a) - \Phi(a)$$

"with $\Phi$ the signed handover/QoS preference in $\kappa$ units **charged exactly once inside $F$**." (A second KAT "states the physical identity without Φ".)

**Calibration** — round-3 §2 item 21, with the unit fix of stage-4 item 24:

$$\eta_{\rm ref}=\frac{B_{\rm ref}}{E_{\rm ref}},
\qquad \lambda=\eta_{\rm ref},
\qquad \kappa=\frac{B_{\rm ref}}{U\cdot N_{\rm ref}}$$

$N_{\rm ref}$ = "number of decision steps in the calibration reference (**a count, not seconds**)"; every normalised target is bits/$\kappa$ (dimensionless). The reference policy is a "deterministic **nominal-greedy** reference policy" on "disjoint TRAIN calibration worlds", frozen before probes, with "positive calibration totals; freeze once". Nominal-greedy is lexicographic (`…STAGE2…` item 7): "served users, then bits, then lower energy, then configuration id; **no price**."

`…STAGEC-SPEC…` item 3 (`KAPPA-BIT-SCALE`): "the sealed quantity is κ in **bits per user-step** … If the engine exposes bits per user-second, the conversion is exactly × 30.08 s (KAT); Stage C consumes only `kappa_normalization_bits`."

**Φ prices** — `…STAGEC-SPEC…` item 10 (`EVENT-QOS`):

$$\Phi_1 = 0.5\,\kappa \ \text{(same-satellite beam change)},
\qquad \Phi_2 = 1.0\,\kappa \ \text{(satellite change)}$$

> re-entry after outage is priced as a satellite change if the satellite differs from the pre-outage incumbent, else as a beam change; a cell re-key at a dwell boundary without a beam change is **not a handover** (priced 0, counted separately).

Φ semantics — v1.2 §5: "Because interruption (treatment H) already removes useful time, Φ₁/Φ₂ are declared to price ***signalling/QoS preference* (not time, not joules)**; they are reported alongside the handover rate as **co-primary QoS outcomes**, and the reward/coordinator use the same event ledger and coefficients."

**Objective-gap caveat** — v1.6 §5: "$\eta_{\rm ref}$ is frozen at calibration, so a positive surplus $B - \eta_{\rm ref}E$ does not by itself imply a higher realised pooled ratio than an arbitrary comparator (**Dinkelbach updates the multiplier; this design does not**). Every claim and certificate is therefore stated on realised pooled ΣB/ΣE, as already sealed."

### C.8 The C1 / C2 / C3 target definitions and the conservation identity

Contract v1 §B4 (identical in v1.5 §2), for a configuration with changed-user set $A$ relative to the anchor reference $a^0$:

**Unilateral increments:**
$$d_i \;=\; F\!\left(a_i,\,a^{0}_{-i}\right) - F\!\left(a^{0}\right)$$

**Interaction residual:**
$$\Psi_A \;=\; F\!\left(a_A,\,a^{0}_{-A}\right) - F\!\left(a^{0}\right) - \sum_{i\in A} d_i$$

**Targets:**
$$C1(\mathrm{config}) \;=\; \sum_{i\in A} d_i,
\qquad
C3(\mathrm{config}) \;=\; \Psi_A$$

**Exact conservation identity (KAT):**
$$C1 + C3 \;=\; F\!\left(a_A\right) - F\!\left(a^{0}\right)$$

**C2:** "the declared continuation value excluding the immediate term (three offsets, $-\kappa$ per absorbing lost offset)".

**Per-user credit (reporting only):**
$$z_{3,i} \;=\; \Psi/2 \ \text{for pairs};
\qquad z_{3,i} \;=\; \text{the Shapley allocation of the interaction game for larger sets}$$

capped at $|A| \le 4$, `credit_split = NOT_COMPUTED_LARGE_SET` above it, and **never a training target** (contract v1 §B5; v1.7 §3; contract v1.2 §1).

**Pairwise special case** (pipeline map Stage 5): $\Psi = F_{11} - F_{10} - F_{01} + F_{00}$ on $F = B - \eta_{\rm ref}E$, per regime.

**Cost of a label:** $|A| + 2$ evaluations (baseline, $|A|$ singletons, one joint) — v1.7 §3.

**Factor arms** — v1.5 §2:
$$\text{FULL}=C1+C2+C3,\quad
\text{DROP\_C1}=C2+C3,\quad
\text{DROP\_C2}=C1+C3,\quad
\text{DROP\_C3}=C1+C2$$

### C.9 Selection-time margin scoring (v1.6 §1 as corrected by v1.9 §§1–3)

**Declared channel** (v1.9 §3):
$$G \;=\; R\cdot 10^{-\left(X + L_c(e)\right)/10}$$
with $R$ = Rician power fading, $X$ = Gaussian shadow loss (dB), $L_c(e)$ = deterministic scintillation at elevation $e$; $K = 20$ dB (round-3 §2 item 6).

**The quantile** $q_\alpha$ is "computed by the sealed procedure: **200 000 draws** of the declared product at the link's actual elevation with a fixed derivation seed from the domain rule, **cached per (elevation bin of 0.5°, α)**; the KAT checks the cached quantile against a direct evaluation to 1e-3 relative." Primary $\alpha = 0.10$, i.e. $q_{10}$; "**α = 0.10 stays primary regardless of the sweep's outcome**" (v1.9 §7).

**Corrected construction** — power from nominal gains, quantile on the wanted link only (v1.9 §§1–2):

$$p \;=\; p_N\!\left(\hat h_{\rm nominal}\right),
\qquad
\mathrm{SINR}_{\rm pred} \;=\; \frac{q\cdot \hat h_{\rm nominal}\cdot p}{N_0W + \hat I}$$

"so a link is predicted to decode only if it clears its mode threshold **with the reserve $q$**." Interference terms keep nominal values.

**Margin-adjusted selection score:**
$$F_m(a) \;=\; B_m(a) - \eta_{\rm ref}E_m(a) - \Phi(a)$$
with "service, ACM mode, required power, bits and energy all recomputed under" the margin-adjusted prediction (v1.6 §1).

**Two decompositions, never mixed** — v1.7 §2: selection-time statistics ($d_i^m$, $\Psi_A^m$, $V_{CA}$, reversal frequency) come from $F_m$; outcome statistics (C1/C2/C3 labels, credit split, all certificates) come from the realised 48-boundary $F$.

**Net collision-avoidance value** — v1.6 §3, at matched anchors with $D(a)=\sum_i d_i(a)$, $a_D$ the additive-selection profile and $a_C$ the interaction-aware profile:

$$V_{CA} \;=\; \frac{F(a_C)-F(a_D)}{\kappa}$$

reported "together with both components (interaction loss avoided, singleton value sacrificed), **unclipped**, plus the frequency of reversals where $D(a_D) > 0$ and $D(a_D) + \Psi(a_D) < 0$". Reported **twice**: anchored at the carrier $a^0$, and re-anchored at the certified S_UNI local optimum $u$, "where $d_i^u \le 0$ by construction, so any improving joint escape must have $\Psi_A^u > 0$."

### C.10 The estimator / interval

Contract v1 §D2, as amended by v1.4 §2, v1.5 §3 and contract v1.1 §3:

$$\widehat{\eta}_{\text{arm}} \;=\; \frac{\Sigma B_{\text{arm}}}{\Sigma E_{\text{arm}}}
\qquad\text{recomputed within every bootstrap draw}$$

- **Primary interval:** two-way pigeonhole bootstrap over clusters $=$ (TLE date $\times$ learner seed), **arms paired within each resample**, ratio recomputed per draw, central 95 % percentile.
- **Learner-free physics matrix:** one-way bootstrap over TLE dates (v1.5 §3).
- **Pooling:** "worlds sharing a cluster are **pooled** (ΣB, ΣE, QoS numerators) before resampling, never rejected as duplicates" (`…PIPELINE-AUDITS-CD…` item 3).
- **Supplementary:** one-way cluster bootstrap; delta method; seedwise paired effects; paired per-world log-EE intervals — "supplementary and … **never substituted** for the pooled-ratio interval" (v1.2 §3).
- **Claim form** — v1.2 §4, conditional intersection–union: "with the other two components enabled, each of the three FULL − DROP pooled-EE contrasts exceeds its prespecified margin δ = +0.5 pp [read as +0.5 % relative, v1.4 §1] with the 95 % lower bound above it, and FULL is QoS non-inferior to each DROP".
- **Disclosure fields on every interval** — v1.7 §6: "its contrast, endpoint, units, decision margin, method, sidedness, nominal level, whether coverage is marginal or simultaneous, the number of dates and learner seeds, the panel scope, and the **measured calibration coverage with its Monte-Carlo uncertainty**."

---

## D. The information boundary

### D.1 What each component may and may not see

| Component | **May see** | **May NOT see** | Source |
|---|---|---|---|
| **Q1 / Q2 heads** (`I_heads`) | the completed Q1 and Q2 schemas; "current nominal geometry of user i's candidates, i's history, the previous committed served set excluding i (b⁻₋ᵢ) at decision time; derived features as frozen" | "**model access = none (no joint physics)**"; compute = "one forward pass" | contract v1 §A1 |
| **Coordinator** (`I_coordinator`) | "global nominal geometry with beam-specific cross gains, all users' legal sets, b⁻, the reference proposal a⁰, the bounded catalogue 𝒞 …, the nominal model 𝓜 …, and the outputs of 𝓜 for each profile in 𝒞 (joint load, coupled powers, interference, activation, service, bits, energy, continuation)" | "**no realised fading, no future TLE beyond the declared forecast horizon**"; compute = the declared budget | contract v1 §A2 |
| **Set head encoder (S3)** | additionally: "proposed and incumbent associations by physical identity, background occupancy and activation before and after insertion, the shared-resource relations among the affected beams, and the **pairwise cross-gain terms among the affected beams**" | a scalar interference summary alone is insufficient and is a test failure | contract v1.2 §2 |
| **C2 forecasts** | "nominal geometry and nominal interference only"; "survival is the **focal user's**"; "the uncapped required-power margin is reported even when negative" | "no realised fading"; "an INVALID solve makes the forecast INVALID (**no surrogate**)" | `…PIPELINE-AUDITS-CD…` item 9 |
| **Any deployment selector** | "current nominal geometry, D2 state and explicitly timestamped **lagged** telemetry" | "**Realized fading stays hidden from deployment selectors**; forecasts use ephemeris/current motion assumptions, **not future random realizations**." Also removed: "independent 'current CSI' noise and the false elevation fallback" | round-3 §2 item 20 |
| **Nominal channel convention** | "unit Rician gain、zero-dB shadowing" (OPS-3 median/no-fading convention) | — | `DRAFT-C3S-…` §2 |
| **Coordinator interface (C3-S, the model for the successor's)** | "當前 pre-decision state、已 committed association／occupancy／tracking state、當前 geometry、合法 masks 與 Q1+Q2 proposals" | "禁止輸入本步 realised fading、realised candidate scores、oracle winners、未來 state、另一臂 trajectory 或 screen running EE" (this step's realised fading, realised candidate scores, oracle winners, future state, another arm's trajectory, the running EE). "環境 RNG、keyed field 與其 seed 不暴露給 coordinator." | `DRAFT-C3S-…` §2, §4 |
| **Realised endpoint** | read by an independent scoring path **after commit** only ("Realised endpoint 僅由獨立評分端在 commit 後讀取") | — | `DRAFT-C3S-…` §2 |
| **Physics powers** | "controller powers solved from **nominal current geometry and nominal interference only**; realised fading enters received fields only" | — | `…STAGE1-1B…` item 8 |

**Equalisation across arms** — contract v1 §A4 (verbatim):

> Equalised between FULL and every DROP/comparator arm: primitive access and timestamps, forecast method, physical identities, catalogue construction (authenticated identical catalogues at matched anchors), joint search, guards, tie-breaking, validation, deadline, fallback. Any learned pruning is part of the declared intervention. **An exact evaluator may never reinsert a removed score through ranking, pruning or a score-dependent guard.**

Reinforced by the per-arm ranking-key rule (v1.9 §4): "no arm may rank, prune or reject using a score it has had removed."

**Dependency allowlist (the test that enforces the boundary)** — stage-4 item 25, carried into contract v1 §B1:

> two decision instants with identical visible primitives, masks, keyed fading and declared state but **different hidden legacy reset internals** (pending segment ages, warm D2 history beyond the encoded remaining time) must produce identical C1/C2/C3 targets and identical legality; the successor's opening state at step 0 is declared (carrier opening associations, D2 state from the seeded legacy history, **no hidden ages**).

Acceptance test T2 exercises it end to end (contract v1 §G2): "poisoned post-decision outcomes, realised future fading and hidden legacy reset state leave current features and actions unchanged; physical-identity relabelling invariance".

**Causality: availability, not epoch** — v1.8 §7:

> an element set is causally usable only if its **receipt/publication time** precedes the decision instant; a future epoch alone is not leakage and a past epoch alone is not causal availability. The benchmark keeps the nearest-epoch rule for all arms and labels it **retrospective**; an operational claim requires availability-filtered replay.

The TLE convention itself (v1.5 §5): "The legacy nearest-epoch rule (per NORAD, files date−1/date/date+1, |age| ≤ 24 h at episode start, **future epochs allowed**) is retained as an accuracy-first benchmark convention shared by all arms (`VERIFY_SOURCE`); it is documented as **non-causal**."

**Benchmark vs operational** — contract v1 §F1: "decision at t from information at t, applied from t (legacy convention, kept for the scientific comparison); TLE nearest-epoch rule labelled retrospective (v1.5 §5). **Operational claim** (if made): a causal-input variant (ephemeris available by decision time, causal forecasts) and an explicit action-effective-time convention."

**Deployment-capability manifest** — stage-4 item 26, required in the seal package:

> for every set-level arm (S0, S_UNI, FULL/DROP coordinators) list the information it consumes (authenticated current geometry of all users, legal option sets, nominal joint-physics model, no realised fading, no future TLE beyond the declared forecast horizon), its catalogue, service guard, computation budget/deadline and fallback; **this manifest is part of the system model statement.**

Fields — contract v1 §F3: "telemetry sources and ages, roster and cross-gain coverage, model assumptions and calibration source, worker hardware/count, catalogue bounds, solver limits, memory, missing-data handling, measured end-to-end latency distribution."

**Information contract was a named blocker** — v1.5 §6 ("Information contract for C3 (residual risk 0.90)"): "Before any successor training, the stages 6–8 contract v1 must state exactly what the learned heads observe and what the coordinator computes (candidate identities, load, shared capacity and interference, activation state, other users' proposed actions or a joint search), with the deployment-capability manifest; **retrained ablations are the scientific claim, checkpoint knockouts are reported separately.**"

### D.2 The deadline and the fallback path

**Normative statement** — contract v1 §F2 (verbatim):

> **Timing budget:** the coordinator's compute budget is **10 s wall on the declared worker count** (the rest of the 30.08 s interval reserved for sensing/transport/validation/commit); **BASE (a⁰) is computed, validated and repaired *before* the coordinator starts**; **the runner enforces the timer (cancel), not the solver**; **a miss executes the validated a⁰**; **misses are a co-reported QoS field and their B/E enter the endpoint.**

Element by element:

| Question | Answer | Source |
|---|---|---|
| **Budget** | 10 s wall (superseding the earlier 30.08 s of stage-4 item 12 and contract v0 item 9) | contract v1 §F2 |
| **On what hardware** | "wall clock (**monotonic**) on `sat`; coordinator worker count = **4 processes**; **no warm caches** for decision timing (cold per anchor); the timing evidence is the per-phase table of stage 4c" | `…STAGEC-SPEC…` item 8 (`DEADLINE-CLOCK`) |
| **What is computed before the clock starts** | BASE / a⁰ — "computed, validated and **repaired** before the coordinator starts" | contract v1 §F2 |
| **What the timer covers** | "catalogue → selection → validation" (`…4C-AUDIT-ROWS…` item 3); more fully "proposal generation, forecasts, catalogue evaluation, selection, validation and fallback; the cost estimate counts actual provider/power calls; **cached lookups are not decision time**" | `…PIPELINE-AUDITS-CD…` item 12 |
| **Who enforces it** | "the **runner** enforces the timer (**cancel**), not the solver" | contract v1 §F2 |
| **What happens on a miss** | "a miss executes the **validated a⁰**"; "the runner timer … executes the validated BASE on a miss **for every set arm, including large coalitions (no exception path)**" | contract v1 §F2; `…4C-AUDIT-ROWS…` item 3 |
| **What gets counted** | "misses are a **co-reported QoS field** and their **B/E enter the endpoint**"; load-bearing certificate (iv) is "realised availability/QoS, physics validity and **deadline behaviour with timeout/fallback outcomes counted in B and E**" | contract v1 §F2; v1.6 §4 |
| **Where it is reported** | terminal report must carry "the full **decision-latency distribution** including feature construction, catalogue generation, physics-call count, **timeout frequency and fallback-inclusive outcomes**" | contract v1.2 §5 |
| **Comparability rule** | "**Learned value (S3 vs matched S0)** … realised closed-loop pooled EE under **equal computation budget including timeouts**" | contract v1 §C4 |
| **Test that the path is real** | T2: "**an injected timeout exercises the real fallback**"; "the deadline-fallback test is made true by implementing stage-4 item 12" | contract v1 §G2; `…ENGINE-AUDIT…` item 5 |
| **Planning statistic** | "The decisive planning number is the coordinator's **mean** solve time, not the 10 s deadline … the stage-4g real-anchor measurement therefore reports the **mean and the p95** per decision, not only the worst case" | `V025-CONTROLLER-DECISIONS-STAGEC-COST-2026-09-09.md` item 4 |
| **S_UNI exemption** | S_UNI "has its **own compute budget** (comparator arm, not the deployable policy), reported per anchor with its iteration count and termination certificate" | `…4C-AUDIT-ROWS…` item 2 |

**Current measured status (not yet passing).** `V025-CONTROLLER-DECISIONS-4D-GATE-2026-09-09.md` preamble: "catalogue 1 004 rows (PASS ≤ 1 500); complete 14-arm anchor 34.4 s (PASS ≤ 60 s); provider + anchor 55.9 s (PASS); **coordinator selection path 24.7 s (FAIL vs 10 s)**, dominated by the five-boundary stage-2 forecasts at 18.3 s." The pre-declared escalation (parallelism → one boundary per offset → M = 48) is binding and ordered; "**No further step without a controller decision**", and "labels, committed-profile evaluation and the endpoint remain at 48 boundaries throughout (KAT)."

**Hard gate** — `…4C-GATE…` item 6: "if the real anchor still misses the 10 s selection budget after items 1–3, **stop and report the dominating phase; no further approximation without a controller decision**."

**Atomicity is an idealisation, and its failure mode is declared** — v1.8 §6:

> No Rel-17/18 mechanism provides all-or-nothing multi-UE commitment; conditional handover prepares alternatives per UE, and group signalling is not atomic application. The study therefore evaluates a candidate supervisory coordinator under **ideal simultaneous profile application**, and states as a limitation that **partial completion can change the sign of a planned beam evacuation** (a beam switched off while one user remains causes outage; an evacuation that half-executes saves no activation energy). Any execution-aware variant is a separately declared arm applied symmetrically.

---

## E. Everything explicitly forbidden

### E.1 Claims that must not be made

1. **"Coordination" for a Level-B-only result.** `V025-CONTINGENCY-LADDER-PREOUTCOME-2026-09-08.md` Rung 0: "Wording is fixed now: a Level-B-only result is described as '**exact/learned joint re-evaluation layer**', **never as 'coordination'**."
2. **Wider-scope EE.** v1.8 §4: "**Every EE claim names its boundary; no result is restated at a wider scope.**" Round-3 §2 item 13: "**Do not claim spacecraft EE or physically zero procedure energy.**"
3. **"35 % efficiency."** v1.8 §1: "The declaration and the paper say '**saturation efficiency**', **never '35 % efficiency**', and cite the traditional square-root PA abstraction as a **modelling convention, not satellite hardware calibration** (`VERIFY_SOURCE`)."
4. **Hardware mapping as fact.** v1.8 §2: "One beam ↔ one switchable RF chain, and the per-satellite common term is a named processing increment, **not the spacecraft's total baseband or platform load**. Multiport/shared-amplifier payloads would break the one-to-one mapping, so **consolidation savings are conditional on this declared architecture**."
5. **Non-positivity inferred from a failed margin.** v1.7 §6: "Failure to clear +0.5 % means the benefit was **not established**, not that the effect is non-positive; the stronger statement requires a calibrated upper bound at or below zero."
6. **Skipped reported as negative.** v1.7 §6: "A regime that was not executed is reported as *skipped*, **never as negative** (R2: the provider fixes the user count at 100)." Round-3 §4: "INCOMPLETE/INVALID cells are **not zero effects** and cannot support the across-settings negative conclusion."
7. **A regime result presented as the primary claim.** v1.7 §4: regimes may be reported "**only as an explicitly regime-conditional statement carrying the words 'in regime R_k'**, never as the primary claim, and always with a-r0's failed status reported first and in full."
8. **Main effects without the full factorial.** v1.2 §4: "**main effects across all backgrounds are not claimed without the full 2³ factorial.**"
9. **Component-wise discovery.** Contract v1 §D4: "components are reported with their own intervals but **no component-wise discovery is claimed**; all other cells exploratory."
10. **Bellman/value semantics for the heads.** Contract v1 §C1: "This estimates a supervised surrogate of the declared targets, **not a Bellman value**; the claim is worded accordingly."
11. **Additive reconstruction of the global objective.** Round-3 §2 item 25: "**Do not claim that summing user difference rewards reconstructs the global core.**" `DRAFT-C3S-…` §3: "不得相加 unilateral effects 重建 joint physics" (unilateral effects may not be summed to reconstruct joint physics).
12. **Design innocence.** `DRAFT-C3S-…` §8: "此新架構由既有失敗、global views、E1 與 S0 development evidence 啟發；**不得宣稱設計未受已知 diagnostics 影響**" (it may not be claimed that the design was uninfluenced by known diagnostics). Compare v1.6 preamble: "**Disclosure: these changes followed inspection of development SMOKE numbers**".
13. **A universal availability convention behind q₁₀.** v1.7 §1: "a per-link 10th-percentile channel-gain quantile does not establish 90 % network availability, and **no such universal convention is claimed**."
14. **Demand, throughput or fairness claims.** v1.8 §5: the rate target is "a **power-control setpoint, not a demand model**"; "**Finite demand or queues would be a versioned model amendment with affected comparisons re-run, never a relabelling.**" Round-3 §2 item 10: "**this is not a minimum-throughput guarantee**." v1.0 §Service definition: "A guaranteed-rate service endpoint is **not declared**." `DRAFT-C3S-…` §5: "Served fraction 不是 demand satisfaction 或公平性."
15. **Efficacy from a screen.** `DRAFT-C3S-…` §7: SUPPORT "**不是 efficacy，也不直接授權執行**" (is not efficacy and does not itself authorise execution).
16. **Operational deployability.** The paper sentence is fixed by v1.8 §7: "We evaluate a candidate ground-based supervisory association coordinator using retrospective orbital reconstruction, a nominal joint-resource model and idealised simultaneous profile application; **operation with causally available telemetry and delayed, partially successful execution remains unvalidated**."
17. **The Route-C disclosure sentence is mandatory.** `ADJUDICATION-SUCCESSOR-ROUTE-…` §DECISION 2: "Following the pre-registered STOP_PHYSICS_R7, we closed the LC-SRS successor and prospectively declared a separate C1/C2-only development experiment with unchanged C1/C2 definitions; **this outcome-informed scope change does not rescue R7 or establish three-Catfish efficacy**, and R7 residuals and successor outcomes are not used to select formulas, signs, thresholds, seeds, horizons, lambda, budgets, or acceptance rules."
18. **Old artefacts as successor evidence.** Round-3 §2 item 31: "Preserve old BASE/Q1/Q2/Q3 checkpoints, λ/κ, recurrence state/OPS-3 schemas, source corpora, attempt-4 bindings, R7, F1, E1, S0, C3-S v1/FULL/LITE, old Stage-C ladders, anchor/churn diagnostics and nine-arm matrices unchanged. **None becomes successor evidence by relabelling.**" §4.6: "**Do not reuse old positive/negative outcomes as successor gates.**"
19. **Learned superiority over an exactly evaluated catalogue.** Contract v1.2 §3: "**S3 cannot exceed S0's maximum of the same score**"; only three named axes are admissible, and "A learned escape proposer over a wider neighbourhood is **not** part of this study."
20. **"Beyond exhaustive unilateral improvement" without a certificate.** Contract v1.2 §6: "**only** a S_UNI with a completed-neighbourhood termination certificate supports the … claim"; a budget-limited S_UNI "is an operational comparator and is labelled as such."

### E.2 Numbers and results that must not be shown or used

| Category | Prohibition (verbatim) | Source |
|---|---|---|
| **Pilot** | "pilot numbers **may never enter the paper**, may never select a configuration, a regime, a margin, a seed count or any sealed rule, and **may never be cited as evidence for or against C1, C2 or C3**. Their only admissible uses are (i) finding integration and engineering defects, (ii) measuring cost, (iii) deciding *engineering* priorities. **The pilot cannot trigger PHYSICS-GO and cannot substitute for the a-r0 matrix.**" Label `PILOT_NOT_CLAIM` on every artefact. | `V025-PILOT-TRACK-DECLARATION-2026-09-09.md` |
| **Synthetic mechanism map** | "**Synthetic results support no claim, admit no training**, and may not change any sealed constant, order, margin or rule of the real-world plan." Permitted effects only: engine bug fixes with a KAT, and a pre-filed written expectation. Label `SYNTHETIC_MECHANISM_MAP`. | `V025-SYNTHETIC-MECHANISM-MAP-DECLARATION-2026-09-08.md` |
| **Synthetic map R2** | "Per the declaration, **E1–E4 are NOT SCORED on a partial grid**"; score only on the complete 36-world grid, and only after `AR0-DONE`; "The map is mechanism/engineering evidence and **never enters admission or claims**." | `V025-SYNTHETIC-MAP-R2-COMPLETION-DECISION-2026-09-09.md` |
| **Stage-2 sweep** | labelled `SUPERSEDED_B2` (it "inherits B2 (zero factor marginals by construction)") | `…ENGINE-AUDIT…` item 7 |
| **SMOKE / vertical slice** | "the vertical slice numbers (SMOKE) **never substitute for the matrix**" | ladder Rung 4 |
| **Cost rehearsal** | "**Every number here is an engineering measurement on synthetic fixtures; none of it enters any scientific claim, and none of it may change a sealed scientific rule.**" And: "the numbers in the rehearsal **must not be quoted as the plan**." | `…STAGEC-COST…` items 5, 3 |
| **Cell count 28** | "the launcher **may reject the number 28**" | `…STAGE2…` item 2; v1.3 erratum |
| **"+0.5 pp"** | "**pooled EE has no percentage-point scale**" | v1.4 §1 |
| **Contract v1 §E power figures** | "The analytic estimate of v1 §E is **withdrawn**." | contract v1.1 §2 |
| **Q2 21-field SHA `54ab6a82…`** | "**retired and never stamped again**" | `…STAGEC-SPEC…` item 2 |
| **Old-physics prices** | λ = 118 424 222.8550065 bits/J and η_ref = 124 075 740.54723135 bits/J do not transfer; "**synthetic dry-run values are inadmissible**" for calibration | `DRAFT-C3S-…` §2, §3; `…STAGE2…` item 10 |
| **U cells** | "U cells (uncapped Shannon) are **diagnostic only and ineligible as primary**"; "U does not 'pass' by claiming an SE cap it intentionally lacks." | v1.0 §Declaration; round-3 §4 |
| **q₀₅ / q₂₅ rescoring** | "**Diagnostic only (never decision-bearing)**" | v1.6 §1 |
| **α sweep** | "It is a robustness report, **never a selector of the primary α**; α = 0.10 stays primary regardless of the sweep's outcome." | v1.9 §7 |
| **Non-certificates** | "**Informative but not decisive:** J1 − U_all … **Diagnostics only:** cap-hit, plateau share, ACM distribution, lit beams." | v1.6 §4 |
| **Per-boundary attainment series** | persisted "for QoS reporting (cheap; **no decision use**)" | `…STAGE1-1B…` item 15 |
| **Post-hoc interval widening** | "**no post-hoc widening is applied**" despite measured under-coverage | contract v1.1 §3 |

### E.3 Deprecated terminology

| Retired term | Replacement / status | Source |
|---|---|---|
| `recurrence_power_w`, `previous_recurrence_power`, `current_to_segment_start_gain_ratio` (entry-gain ratio), `segment_age` | incumbent nominal decoding margin; forecast SE trend; remaining D2 / visibility time. Contract v1 §B2: "**No** recurrence power, entry-gain ratio or segment age." | contract v1 §B2; contract v0 item 2; round-3 §2 item 26 |
| "segment", "segment-entry gain", "reset target", "private-power/beam-max hybrid" | "**No segment-entry gain, recurrence, reset target or private-power/beam-max hybrid survives.**" v1.0: "**no segment memory**". | round-3 §2 item 4; v1.0 §Declaration |
| "**dwell**" for N = 4 | "N = 4 is named a **candidate-refresh period, not a dwell**"; "candidate restrictions, **not minimum residence**" | v1.2 §7; round-3 §2 item 19; `…PIPELINE-AUDIT-A…` item 8 |
| "**load balancing**" as an EE lever | "'**Load balancing' is not an EE lever**: spreading users lights more beams; EE wants consolidation subject to QoS (rate, fairness, handover rate)." | `CONTROLLER-REFERENCE-DESIGN…` §3 |
| "C3 = load balancing / observability"; additive per-user Q3 | set-level coordinator; $C3 = \Psi_A$; "**Two weeks of ≤ 0 oracle marginals were structural**" | `CONTROLLER-REFERENCE-DESIGN…` §6 row 7 |
| LC-SRS $e_i$ in the C3 target | "the historical LC-SRS e_i (defined for an own-bits-only C1) **is not transferred**" | `…STAGE2…` item 5 |
| "the standard 90 %-availability link-budget convention" | "a **pre-specified tenth-percentile channel-gain scoring rule**" | v1.7 §1 |
| "shadow + scintillation" (for the quantile) | "the **complete fading product**" $G = R\cdot 10^{-(X+L_c(e))/10}$ | v1.9 §3 |
| "uniformly stricter" (of v1.6) | "**withdrawn**" | v1.9 preamble |
| "g_I ≠ 0" | "**withdrawn**" | contract v1 §C4 |
| Shapley "wired into selection" | "**withdrawn** as a requirement" | `…4C-AUDIT-ROWS…` item 4 |
| "per-anchor provider target of 1 s" | "**withdrawn** in favour of 'once per world'" | `…SELECTION-TIME…` item 5 |
| slot indices as identity keys | "**Identity keys:** (NORAD, beam-chain) everywhere from stage 1 to stage 8; **never slot indices**" | pipeline map §Cross-cutting invariants |
| "twelve learner seeds" | "**sixteen**" | `…STAGEC-SPEC-ERRATUM-1…` |
| "coordinator deadline = 30.08 s" | "**10 s** compute budget" (30.08 s is the *interval*) | contract v1 §F2 |
| "served = masked action ∧ p ≤ p_max" | "`served_PHY ⇔ SINR ≥ SINR_min`" | round-3 §2 item 10 |

### E.4 TRAIN-only, no-TEST, and quarantine rules

- **No TEST split at all.** Contract v1 §D1: "allocation manifest sealed with role-wise date disjointness …; **no TEST**." Contract v0 item 11: "cluster = TLE date × learner seed; **no TEST split**." Pipeline map Stage 8: "no TEST split".
- **TEST is never read, and the assertion must be able to fail.** `…PIPELINE-AUDIT-A…` item 4: "**TEST never read**: a shared world factory is the **only** production entry point for successor runners; every realised start date and opened TLE file is recorded and checked against the split." `…PROVIDER…` item 8 (T12): "the assertion **must be able to fail**: KAT constructs a provider on a known TEST date and expects the raise; the split source (file and hash) is recorded in the manifest."
- **TRAIN asserted at construction.** Contract v1 §B1: "TRAIN asserted at construction". Stage-C spec / provider: "no hardcoded `TRAIN`" — "split identity, start UTC, TLE hashes, split-rule digest, provider digest are **protocol outputs**" (`…PIPELINE-AUDIT-A…` item 3).
- **TRAIN-only wording enforced mechanically.** Contract v1 §D4: "**TRAIN-only wording enforced by the report schema**."
- **Claim dates must be role-wise fresh.** v1.5 §4: "The successor's confirmation panel uses TRAIN dates that were **never used by any successor development activity** (probe, calibration, rehearsal, KAT, synthetic-real); the allocation manifest asserts this role-wise disjointness; overlap with legacy (old-physics) development dates is **recorded, not forbidden**, and the claim wording says so."
- **Opened worlds are quarantined.** `…PIPELINE-AUDITS-CD…` item 4: "`V025_PROBE/world/1` was opened by the provider rehearsal before sealing (real bits/joules printed in the provider log). It is **quarantined** for development, rehearsal and KATs together with worlds 2–4 of that namespace. The formal matrix uses fresh domains `V025_PROBE_R2/world/{1..4}` and `V025_CAL_R2/world/{1..2}`".
- **No acceptance peeking.** `…PIPELINE-AUDITS-CD…` item 14: "acceptance/equivalence runs use disjoint worlds (role `rehearsal`) or blinded hashes; **no claim-panel world is executed before the formal root starts**."
- **No outcome-selected reruns.** Pipeline map Stage 8 invariants: "receipts write-once with sha256; … **no rerun selected by outcome**." `DRAFT-C3S-…` §8: "有效 NO_SUPPORT **不重跑**；僅可修復有證據的 infrastructure defect，保留原結果及 repair provenance."

### E.5 Procedural prohibitions

- **No post-outcome design change.** v1.0 §Rules: "**No target, standby, margin, service or priority change after outcomes are opened. Any defect found later is repaired and re-run, never demoted by outcome.**" And: "A positive C3 under (b) with a non-positive C3 under (a) is a **reported finding, not grounds to swap the primary after the fact**."
- **Primary identity is outcome-independent.** v1.1 §5: "**the primary's identity cannot change with outcome signs**."
- **No feature/catalogue redesign after a negative.** Contract v1 §C6: "neither permits **changing features, catalogues, sources or regimes until C3 becomes positive**." Ladder Rung 2: "**No redesign of features or catalogues after seeing S3 fail.**"
- **Thinning is pre-ordered and outcome-blind.** `…COMPUTE-BUDGET…` item 3: "(apply the smallest step that fits; record every applied step in the seal; **never chosen by outcome**)"; item 4: "**What is never thinned:** the 12 + 1 arms per setting (the arms are the science), the 48-boundary integration, the calibration procedure, the placebo and dry-run."
- **Fail closed, never fabricate.** `…PROVIDER…` item 7 (T9): "the provider must **fail closed (raise)** on any non-finite primitive; **never emit NaN**." `…STAGE1-1B…` item 9: "4096 iterations or a failed residual → INVALID, **never a synthetic zero-effect outcome**." `…PROVIDER…` item 5 (T14): "a same-day rule is **not introduced**."
- **Prices must be explicit.** `…STAGE1-1B…` item 18: "every C1/C2/C3 generator and endpoint consumer passes through the explicit λ/η/κ assertion; **a test fails if any producer can fall back to a default**."
- **Freeze admissibility (all four must hold)** — `V025-DESIGN-FREEZE-AND-CLOSURE-RULE-2026-09-09.md` §2: a post-freeze finding is acted on only if (1) "it can change the **sign** of a load-bearing certificate or the **branch** of the admission trichotomy"; (2) "it names a **test that fails now and passes after the change**, executable in under an hour"; (3) "it is confirmed by a source **independent** of the one that raised it"; (4) "the change does not require re-running work already completed under the freeze, or … the re-run fits in one overnight window." Otherwise it goes to `LIMITATIONS-AND-FUTURE-WORK-REGISTER.md` — "**This is not a way to hide problems: the register is published with the work.**"
- **Standard of evidence for "defect"** — same file §4: "Every item recorded as a defect carries: the failing test or the changed number, the independent confirmation, and what it would have done to a certificate. An item with none of these is labelled **precautionary, not a defect, and is not used to justify delay.**"
- **Deadline discipline** — §5: "If stage 4g's audit does not return READY within two further engine passes, the controller **stops adding scope**, runs the matrix on the last audited configuration, and reports every unresolved item in the register as a declared limitation."
- **Receipt claim ceiling** (legacy convention carried): `TRAIN_DEVELOPMENT_C3S_CLOSED_LOOP_KILL_SCREEN_NO_LEARNER_NO_EFFICACY_NO_TEST` (`DRAFT-C3S-…` §8).

---

## F. Storyboard-impact list (v0.23 teaching-deck concepts vs the successor)

Verdicts: **KEEP** = survives unchanged in role and wording; **REWRITE** = the concept survives but the slide's content/numbers/name must change; **DELETE** = removed from the successor and may only appear as labelled history.

| # | v0.23 deck concept | Verdict | Reason (one sentence) |
|---|---|---|---|
| 1 | **Three independent Q surfaces Q1 + Q2 + Q3** | **DELETE** | The successor has exactly two heads and no third additive Q surface — "沒有第三個 additive Q head、第三頭訓練或個人化 surplus 分配" (`DRAFT-C3S-…` §1) — because "additive per-user surpluses **cannot represent the joint gain of emptying a beam**" (`CONTROLLER-REFERENCE-DESIGN…` §4.2). |
| 2 | **Unweighted three-head sum** | **REWRITE** | The unweighted sum survives only as the **two-head** proposal "per-user masked argmax of the **normalised Q1 + Q2**" (contract v1 §C1); the third summand is gone, and the set-level score is a different object (C1 + C2 + Ψ̂ over whole profiles). |
| 3 | **One-pass masked argmax with no coordinator** | **REWRITE** | The masked argmax survives but is demoted to the *proposal* stage a⁰, which must then be "validated as a jointly legal profile (deterministic repair rule for conflicts)" and is followed by a set-level coordinator over the bounded catalogue (contract v1 §§A3, C1, C2). |
| 4 | **Runtime prohibition list** ("NO runtime coordinator, auction, bidding, tokens; NO voting/consensus; NO post-selection repair or fallback") | **DELETE** | Three of its clauses are now mandatory features: the successor *is* a runtime coordinator (S3/S0 with `I_coordinator`, contract v1 §A2), it *requires* a deterministic post-selection repair rule (§C1) and a *mandatory* deadline fallback to the validated a⁰ (§F2) — only "no auction/bidding/voting/consensus" survives, and it survives as a description (the coordinator is a centralised model-based selector, not a market), not as a prohibition worth a slide. |
| 5 | **Route C1 — focal opening surplus** | **REWRITE** | C1 survives as a route but its label is redefined: "Replace focal-bit-only opening labels with **full-network difference surplus** against the declared default action, plus the same explicit QoS difference" (round-3 §2 item 25), formally $C1=\sum_{i\in A}d_i$ (contract v1 §B4), and under the rate target "its positive marginal is expected through **energy and service, not surplus bits** — accepted" (v1.1 §4). |
| 6 | **Route C2 — OPS-3 diagnostic head** | **REWRITE** | C2 survives as a route and a head, but its entire temporal state is replaced (recurrence power → incumbent decoding margin, entry-gain ratio → forecast SE trend, segment age → remaining D2/visibility time; round-3 §2 item 26), its target is the three-offset continuation with −κ per absorbing lost offset (contract v1 §B4), and at set level it is **tie-break only** whose matrix certificate is "**forecast validity, not a selection marginal**" (v1.6 §2; v1.9 §5). |
| 7 | **Route C3 — two-user LC-SRS coalition teacher, four matched profiles 00/10/01/11** | **REWRITE** | The 2×2 construction survives only as the $|A|=2$ special case $\Psi = F_{11}-F_{10}-F_{01}+F_{00}$ (pipeline map Stage 5); the successor generalises to arbitrary coalitions at $|A|+2$ evaluations — "Ψ_A is therefore computed for **every selected coalition regardless of size**" (v1.7 §3; contract v1.2 §1) — and computes it on $F=B-\eta_{\rm ref}E-\Phi$ under successor physics, not on the LC-SRS objective. |
| 8 | **The Shapley target $z_{3,i} = e_i + \Psi/2$** | **REWRITE** | The $e_i$ term is struck — "the successor C3 target carries **no e_i term**: $z_{3,i} = \Psi/2$ for pairs and the equal-share (Shapley) split … for larger sets" because "the unilateral externality e_i is inside C1" (`…STAGE2…` item 5) — and what remains is **reporting only, capped at $|A|\le 4$, and never a training target** (contract v1 §B5). |
| 9 | **Exact conservation identity $\sum_i(\ell_i + z_{3,i}) = G(x^c) - G(x^0)$** | **REWRITE** | The structural role (an exact, KAT-checked conservation between per-user and joint credit) is kept, but the symbols and anchor change to "**C1 + C3 = F(a_A) − F(a⁰) exactly** (KAT)" with $C1=\sum_i d_i$, $C3=\Psi_A$, $F = B - \eta_{\rm ref}E - \Phi$ and Φ charged exactly once (contract v1 §B4; v1.5 §2), plus "a second KAT [that] states the physical identity without Φ". |
| 10 | **The C3View committed/detached context** | **REWRITE** | The committed/detached idea survives as the successor's two non-conflatable references — a⁰ (score-decomposition reference) vs the previous committed association (handover/Φ reference), "**Never conflated**" (contract v1 §A3) — but the feature object itself is replaced by `I_coordinator` (§A2) plus the set-head context, which now **must** carry "the **pairwise cross-gain terms among the affected beams**" (contract v1.2 §2). |
| 11 | **The 67-64-64-1 relational token scorer** (Q3 head, dims 28/29/38, token aggregation, reference gauge) | **DELETE** | The successor's C3 architecture is a different object: "permutation-invariant pooling (sum and max) over the changed users' per-user vectors … concatenated with global resource context per affected beam …; **a two-layer MLP on the pooled vector**" (`…STAGEC-SPEC…` item 4) — only the Q1/Q2 trainer configuration is copied verbatim from the legacy Catfish trainer (item 5), not the Q3 scorer. |
| 12 | **Reference-centering $Q_{3,i}(a_i^0)\equiv 0$** | **KEEP** (re-expressed at set level) | The gauge survives exactly in spirit: the set head is "anchored $\hat\Psi(\emptyset)=\hat\Psi(\{u\})=0$" (contract v1 §C2) with "anchored zeros by construction (output × 𝟙[|A| ≥ 2])" (`…STAGEC-SPEC…` item 4) — i.e. no interaction credit at the reference or for any singleton. |
| 13 | **The (U, 28) action surface cardinality** | **KEEP** | Retained verbatim: "Retain **28 association actions, four cached satellite identities, seven local cells** and four-decision refresh" (round-3 §2 item 19, carried by v1.0) with U = 100 users (`…STAGE2…` item 1), and NO_OP still "legal exactly for an empty mask". |
| 14 | **The native safe mask $\mathcal A_u^{+}(t)$** | **REWRITE** | Per-user legality masks remain first-class (both `I_heads` and `I_coordinator` consume "legal sets"), but the semantics change on four points: the 10° floor is now "the successor's declared minimum operating elevation" (`…PROVIDER…` item 2), legality can lapse **mid-step** at boundary k (`…PIPELINE-AUDITS-CD…` item 8), an empty mask yields the null/NO_OP action with a receipt counter (`…ENGINE-AUDIT…` item 4), and "**joint SINR is not an independently guaranteeable per-user legality mask; outage does not authorize hidden rescue**" (round-3 §2 item 19). |
| 15 | **The service non-inferiority guard** | **REWRITE** | It splits into two distinct objects with new numbers: a *deployable* guard inside the selector — "**no served-count decrease versus the BASE proposal**", which now "score[s] and report[s]" rather than excluding configurations — and a *statistical* QoS non-inferiority rule with prospective margins "above **−0.5 pp** for complete-service availability … below **+5 %** for both the handover rate and the Φ-priced handover cost per user-step" (`…STAGE2…` item 6), plus the `FAIL_UNDEFINED_DENOMINATOR` rule (`…STAGEC-SPEC…` item 11). |
| 16 | **Canonical ratio-of-sums EE $\eta^{N}$** | **KEEP** | Unchanged in form and status — "pooled EE = ΣB/ΣE over the panel (**ratio of sums, never sum of ratios**)" (pipeline map Stage 4; contract v1 §D2) — though its *value* is recomputed under successor physics and every statement of it must now carry the v1.8 §3 energy-boundary sentence. |
| 17 | **The frozen multiplier λ** | **REWRITE** | The rule survives ("$\lambda=\eta_{\rm ref}$", frozen once at calibration from a nominal-greedy reference, round-3 §2 item 21) but the value does not: the old 118 424 222.855 bits/J "carries the artifact" and must be re-derived (`CONTROLLER-REFERENCE-DESIGN…` §6 row 8), 31 per-setting values are sealed in one immutable file (`…STAGE2…` item 10), and the slide must add v1.6 §5's caveat that a frozen multiplier does not by itself imply a better realised ratio. |
| 18 | **V0.23 four-arm observability gate** (INFORMED / MATCHED_PLACEBO / ZERO_SURFACE / TEACHER_ORACLE) | **DELETE** | The observability framing died with the additive head ("'C3 = load balancing / **observability**' framing … Two weeks of ≤ 0 oracle marginals were structural", `CONTROLLER-REFERENCE-DESIGN…` §6 row 7), and the successor replaces it with a different taxonomy — "**four named experiments, never conflated**" (learned neutral-source; oracle factor-score removal; checkpoint knockout; architecture removal — named, not run; contract v1 §C3) over the 6-arm panel FULL / DROP_C1 / DROP_C2 / DROP_C3 / ALL_NEUTRAL_CONTROL / external BASELINE. *(Note: of these four labels only `MATCHED_PLACEBO` appears anywhere in the handoff corpus, in `R7-STOP-PHYSICS-RESULT-2026-09-07.md`; none appears in the sealed successor set.)* |
| 19 | **V0.4 five-arm matrix** (M0 / N000 / A011 / A101 / A110 / F111) | **DELETE** | None of these arm labels appears anywhere in the sealed successor set; the successor's arm nomenclature is the 6-arm learned panel above plus, in the physics matrix, "**the 12 + 1 arms per setting** (the arms are the science)" including NULL ≡ BASE, random-feasible, nominal-greedy, UNI, S0, S_UNI and the U1/J1 ceiling arms (`…COMPUTE-BUDGET…` item 4; `…ENGINE-AUDIT…` item 2; `…SYNTHETIC-MECHANISM-MAP…`), and the 2³ factorial reading it implies is explicitly barred without the full factorial (v1.2 §4). |

### F.1 New slides the successor requires that v0.23 had no equivalent for

1. **The 48-boundary invariant** — selection may be approximated, the endpoint may not (§A.9).
2. **The bounded catalogue 𝒞 / CB-2** with its exact row budget (≈ 1 200; measured 1 004; guard ≤ 1 500) (§A.6).
3. **The 10 s deadline and the BASE fallback**, with misses counted in B and E (§D.2).
4. **The three selectors S3 / S0 / S_UNI** and the certified-comparator rule (§A.5).
5. **The margin-adjusted selection view** $q_{10}$ on the wanted link only, with the v1.9 corrections (§C.9).
6. **The admission trichotomy** `ADMIT_FULL` / `ADMIT_C1C2` / `NOT_ADMITTED` (§A.12).
7. **The claim ladder Level A / B / C** and the "never 'coordination'" wording rule (§A.12, §E.1).
8. **The energy-boundary sentence** and the non-cancellation identity (§C.5).
9. **Track F vs Track S** and the `PILOT_NOT_CLAIM` label (§A.13).
10. **The design freeze and its four-part admissibility test** (§E.5).

---

## G. Residual ambiguities and open items at the freeze

1. **Deadline figure.** Stage-4 item 12 (engine prompt) says "30.08 s wall per decision"; contract v1 §F2 says **10 s** with the remainder of the interval reserved. Contract v1 is later and sealed — **10 s governs** — but the engine-prompt text was never edited. Treat 30.08 s as the *interval*, 10 s as the *compute budget*.
2. **v1.8 §8 is `PENDING`.** The ACM-causality disposition is declared but the audit (`ACM-CAUSALITY-AUDIT-2026-09-09.md`) is not in the sealed directory; the link-closure ledger of §9 is "required before the seal".
3. **Seal-time `CONTROLLER_DECIDE` items still open** (contract v1.1 §4): "coalition feature scales, neutral-source seals, **catalogue CB-2 construction**, formal allocation manifest, operational capability values, causal operational variant".
4. **The 10 s budget is not currently met.** Stage 4d measured 24.7 s on the selection path; the escalation ladder is pre-declared and binding but no sealed measurement shows the budget achieved.
5. **`ADMIT_C1C2` is not "C3 failed".** Training is admitted with C3 "carried as an evaluated layer", and the learned FULL vs DROP_C3 test still runs — "since a learned coordinator and an oracle removal are **different estimands**" (v1.6 §4) — but the resulting statement is explicitly weaker.
6. **Interval under-coverage is known and unpatched** (0.89–0.92 measured vs 0.95 nominal at 16 seeds); every interval must print its measured coverage.
7. **Provider status is `READY_WITH_CONDITIONS`** (`V025-CONTROLLER-DECISION-PROVIDER-READINESS-2026-09-08.md`), conditional on the assembler's allocation manifest and the 4c audit's merge-pooling confirmation.

---

*End of brief. Sources are read-only; nothing in the sealed successor set or the v0.23 handoff was modified.*



