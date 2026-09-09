# STORYBOARD-DELTA: V0.23 teaching deck (38 pages) → V0.25 physics successor

- **Annotated source:** `multi-catfish-teaching-deck-v023-20260905-r1/agy-pilot/STORYBOARD.md`
  (38 pages, the V0.23 content authority), with `PILOT-SLIDE-SPEC.md`,
  `SCIENCE-CLAIM-MAP.md`, `MATH-TOKEN-INVENTORY.json`, `CORE-FLOW-DRAFT.svg`.
- **Successor authority:** `.scratch/multi-catfish-v025-physics-successor/`
  (declaration v1.0 + amendments v1.1–v1.9, contingency ladder + R7 amendment,
  stages 6–8 contract v1/v1.1/v1.2, all controller decisions, design freeze and
  closure rule, pilot-track declaration).
- **Wording authority (so the deck and the thesis agree):** `../DELTA-MAP.md`,
  `../SEC-SYSTEM-MODEL-REWRITE.md`, `../SEC-METHOD-REWRITE.md`,
  `../SYMBOL-ADDITIONS.md`, plus `active-symbol-table-v023-20260905.md` and its
  collision / single-letter audit. Where the paper lane has already fixed a
  phrasing, this file and the deck reuse it rather than re-inventing one.
- **Disposition codes:** **KEEP** (usable as written, terminology touch-ups at
  most) / **REWRITE** (same teaching slot, replaced content) / **DELETE**
  (removed from the successor arc; nothing on the page survives, and it may
  reappear only as labelled history) / **NEW** (page with no V0.23 ancestor).
- **No result numbers.** Every V0.23 page whose teaching payload was a measured
  number is DELETE-d on that ground alone, and its successor slot carries
  `⟨結果待填⟩`.
- **Output boundary:** this file, `OUTLINE.md`, `BUILD-NOTES.md` and the build
  artefacts are the only things written; `docs/` and everything under
  `/home/sat/mcrl-paper-sources/` is untouched.

> **Parallel lane.** A second, independently derived delta exists at
> `../_work/STORYBOARD-DELTA-opus5-lane.md`, written against
> `../_work/SUCCESSOR-BRIEF.md`. It reaches a 47-page arc and differs from this
> file on four verdicts; §5 below reconciles them. Neither file was derived from
> the other, and the `_work` copy is untouched.

---

## 0. The four invalidations, named

These are the physics-succession facts that do the demolition. Every DELETE and
most REWRITEs below cite one of them. They are the deck-side statement of
`DELTA-MAP.md` Δ1, Δ2/Δ3, Δ4 and Δ5.

| # | Invalidated V0.23 teaching claim | What replaces it | Pages killed or rewritten |
|---|---|---|---|
| **I-1 — segment-anchored power** | Power recurses inside an uninterrupted served physical-link segment from an entry power `p⁰`, carrying segment-age and continuity semantics (V0.23 eq. 3.11–3.12). | **Memoryless per-user rate-target power control.** Every 30.08 s step and every simultaneously radiating slot configuration is solved independently: required power is the required-SINR staircase times noise-plus-interference, over composite link gain times transmit pattern gain, capped at `p⁺`. No segment, no `τ`, no `p⁰`, no cross-step state. Interference makes it a **coupled fixed point** — a standard interference function iterated from zero — carrying a `CONVERGED` / `CONVERGED_SLOW` / `INVALID` certificate. | REWRITE 3; NEW power-control, coupled-solve and energy pages |
| **I-2 — the old service rule** | Served = an action that passes the mask and whose required power fits under the cap; rate is the continuous Shannon expression with the bandwidth share `Bʷ/U_{s,v}`. | **Discrete ACM staircase with equal-airtime TDM**, and **service = post-joint-solve PHY decodability** at the frozen threshold. A user that cannot meet the rate target under the cap is flagged `rate_target_infeasible`, **transmits at the cap**, and keeps its partial delivery, interference and energy — no pruning, no repacking. "Unserved" and "missed the rate target" become two separately reported fields; availability splits three ways. | REWRITE 3, 5, 20, 34; NEW ACM, service, MODCOD-pair pages |
| **I-3 — the LC-SRS teacher C3** | A two-user coalition exception evaluated over four matched current-slot profiles (00, 10, 01, 11) under 32 keyed fading draws, with a local own-surplus term `ℓᵢ`, a non-focal externality `eᵢ`, bit and energy interactions, and the target `z₃,ᵢ = eᵢ + Ψ/2`. | **Interaction residual on a bounded catalogue.** C1 becomes the **whole-network** singleton increment on the configuration residual, so the externality is **already inside C1**; the successor's C3 target is therefore the interaction residual **alone** — carrying `eᵢ` as well would be double counting. The residual is computed for a **selected coalition of any size** at cost K+2 evaluations; only the exact per-user Shapley split is report-only and stops at K ≤ 4. | DELETE 22, 23, 24, 26, 31; REWRITE 11, 25, 28, 29 |
| **I-4 — the genie-ACM basis and the one-pass argmax** | The deployment surface is the unweighted sum `Q₁+Q₂+Q₃` under a single native masked argmax, with a runtime prohibition list that forbids any coordinator; the credited mode follows from the achieved SINR. | **Two layers, and a target/transmit MODCOD pair.** Layer one is the per-user proposal `a⁰` (two heads with frozen schemas, masked argmax, verified jointly legal, deterministic repair). Layer two is a **set-level selector** over a bounded catalogue with a 10 s per-anchor budget, an executor-enforced deadline and a verified fallback. The transmit mode is chosen **before** transmission from the causally available margin-adjusted nominal view, and bits credit only if the realised SINR clears **that** mode — a failed higher-order frame is never re-decoded lower. | DELETE 32, 35, 36, 37; REWRITE 8, 27, 33; NEW selection-view, catalogue, sort-key, comparator pages |

Two symbol consequences travel with the above and are load-bearing for reading
any old slide: the per-user handover cost `Ψ_u` is **renamed `Φ_u`** so that `Ψ`
can be reserved for the interaction residual, and the configuration surplus `G`
is **renamed `Ω`** (a superscripted `G` would collide with the antenna-gain
family; `Ω` is released because weighted scalarisation retires).

---

## 1. Page-by-page disposition (all 38)

### Part I — Motivation and objective (1–6)

| # | V0.23 page | Disposition | Reason |
|---|---|---|---|
| 1 | Teaching Deck Overview | **REWRITE** | Its core-concept line is "three independent Q surfaces and one native masked argmax", which I-4 retires; baseline and status must move to the V0.25 declaration and PAPER-LANE-A v2. |
| 2 | LEO Satellite Network Context | **KEEP** | Orbital dynamics and narrow beams are untouched, and the angle→power path is *stronger* in the successor; add only the new 10° minimum-elevation candidacy rule. |
| 3 | Coupled Satellite Resources | **REWRITE** | I-1 and I-2: the bandwidth-share sentence becomes equal-airtime full-band TDM, the max-over-users beam aggregation retires, and interference becomes a fixed point of the power vector. |
| 4 | Limits of Conventional Multi-Objective Handover | **KEEP** | The MODQN scalarisation critique is independent of the physics and is now stronger, since load balancing is retired as an objective rather than re-weighted. |
| 5 | The Canonical Endpoint (ratio-of-sums EE) | **REWRITE** | "Ratio of sums, never a mean of ratios" is retained verbatim, but "delivered bits" becomes *successfully decoded* bits, the verbatim metric-boundary sentence becomes mandatory, and QoS co-primary outcomes must sit beside the ratio. |
| 6 | Linear Surplus and the Frozen Multiplier | **REWRITE** | `G(x) = ΣB − λE` becomes `Ω(a) = B(a) − λE(a) − Φ(a)` with `Φ` charged once; the rule `λ = η_ref` frozen at calibration survives but the objective-gap disclosure must be stated in place — a higher residual does not imply a higher realised ratio. |

### Part II — Causal decomposition (7–11)

| # | V0.23 page | Disposition | Reason |
|---|---|---|---|
| 7 | The Causal Attribution Dilemma | **REWRITE** | The three questions survive but two change object: the focal question becomes whole-network, and the spatial question becomes a set-level interaction rather than a per-user externality. |
| 8 | Three Independent Q Networks | **REWRITE** | There are still exactly three fitted heads, but only two are per-user Q surfaces; the third is a set-conditioned scalar interaction head, so "three parallel per-user networks with independent optimisers" is no longer an accurate picture. |
| 9 | Route-Local Zero-Bootstrap Training | **KEEP** | Zero-bootstrap pairwise regression with no target networks survives for the two per-user heads; add the successor's wording that this is a supervised proxy estimate of a declared target, not a Bellman value. |
| 10 | Unilateral Counterfactual: the C1 Opening Intervention | **REWRITE** | The matched-branch protocol survives, but the intervention is evaluated against the reference proposal `a⁰` on the whole-network residual, not as an opening-step focal branch pair. |
| 11 | The Coalition Exception: Why C3 Breaks Unilateral Symmetry | **REWRITE** | I-3: there is no longer an *exception*. The interaction residual is defined for a changed-user set of any size, so the page becomes "why an additive score is not enough", not "why two users are special". |

### Part III — Route C1 (12–15)

| # | V0.23 page | Disposition | Reason |
|---|---|---|---|
| 12 | C1 Role: Focal Opening Net Surplus | **DELETE** | Its whole payload is the focal / opening-step framing with the entire opening power difference assigned to the mover; the successor's C1 is a whole-network differential residual with no opening-step privilege. |
| 13 | C1 Target Formulation `ζ₁,ᵤ` | **DELETE** | The equation, its `k = 0` energy-assignment bookkeeping and its "not duplicated in C3" caveat are all artefacts of the focal formulation. **Replaced by** the new singleton-increment page. |
| 14 | C1 Lineage: RIS EXP/ACRM Provenance | **REWRITE** | ACRM's candidate-versus-reference evaluation and the unit-safety argument for pairwise regression survive, but EXP stratified frontier sampling does not: the successor fits from typed deterministic aggregated batches. |
| 15 | C1 Historical Evidence: V0.4 Frozen-Policy Margin | **DELETE** | A measured margin from the old physics under the old `Q₂` context; excluded from claims by the deviation register, and this deck carries no result numbers. Successor slot: `⟨結果待填⟩`. |

### Part IV — Route C2 (16–19)

| # | V0.23 page | Disposition | Reason |
|---|---|---|---|
| 16 | C2 Role: Evaluating Temporal Persistence | **REWRITE** | The persistence motivation and the ping-pong argument survive, but C2 becomes a declared continuation value over three prediction offsets on nominal geometry and nominal interference, with each absorbed offset charged at the common scale. |
| 17 | C2 Evolution: Temporal-Fork → First-Successor k1 | **DELETE** | The page exists to justify `ζ₂,ᵤ` at offset `k = 1`; the three-offset continuation has no use for that lineage, and the retired-horizon history no longer explains the current design. |
| 18 | C2 Diagnostic Failures (V0.6 screen, V0.7 R14 audit) | **DELETE** | Measured negative results for a retired C2 learner under the retired physics; no result numbers, and the successor's C2 is a different estimand. |
| 19 | Current C2 Status: Present but Unqualified | **REWRITE** | C2 is no longer merely "present but unvalidated": it shapes the proposal, and in set-level selection it acts as tie-break only — with the by-construction consequence that the set-level C2 margin can be exactly zero, an accepted outcome rather than a defect. Its matrix certificate is prediction validity, not a selection margin. |

### Part V — Route C3 / LC-SRS (20–29)

| # | V0.23 page | Disposition | Reason |
|---|---|---|---|
| 20 | The Spatial Externality Problem | **REWRITE** | The contention story is right but the mechanism changed: sharing now costs through equal-airtime TDM and the required-SINR staircase, and interference is a coupled fixed point rather than a lagged term. |
| 21 | The Beam Extinction Blindspot | **KEEP** | Still exactly the motivating physics for a non-additive term; only the name changes from LC-SRS to the interaction residual. |
| 22 | The Two-User Cooperative Game: Four Matched Profiles | **DELETE** | I-3: the 00/10/01/11 profile basis is gone. **Replaced by** the reference proposal plus the bounded catalogue, and by the K+2 evaluation count for a coalition of any size. |
| 23 | Exact Two-Player LC-SRS Teacher Formulation | **DELETE** | Every symbol on the page — `ℓᵢ`, `eᵢ`, `Ψ_B`, `Ψ_E` — has left the active surface. **Replaced by** the new singleton-increment / interaction-residual page. This was also the pilot slide, so `native-formulas.json` is superseded wholesale. |
| 24 | Super-Additive Interaction Surplus and the Shapley Target | **DELETE** | `z₃,ᵢ = eᵢ + Ψ/2` double-counts under the successor's whole-network C1, and the equal split is now report-only and capped at K ≤ 4. |
| 25 | Construction-Level Exact Identity | **REWRITE** | Conservation survives, still construction-level exact and KAT-verified, but on the changed-set form `Σdᵢ + Ψ_K = Ω(a_K) − Ω(a⁰)`, plus a second `Φ`-free physical identity as a separate KAT. |
| 26 | The Teacher Anchor Surface (Supported / Reference / Control) | **DELETE** | The tri-class per-user anchor-cell surface exists only to label a per-user `Q₃`; successor labels are set-level rows on the catalogue's coalition support. |
| 27 | Deployment C3View: Committed vs Detached Context | **REWRITE** | The information-boundary teaching survives, but the object is now the **two-layer information interface** — per-user head interface versus set-level interface — and the set-level side must carry pairwise cross-gain blocks between affected beams. |
| 28 | Relational Token Architecture (67-64-64-1) | **REWRITE** | The shared token scorer survives as the base, but the architecture becomes permutation-invariant pooling over changed users plus affected-beam context through a two-layer MLP; the fixed dimensions and the relation mask are gone. |
| 29 | Reference-Centering: the Structural Zero | **REWRITE** | The structural zero survives as an anchoring condition — `Ψᶠ` is zero on the empty set and on every singleton — but is enforced by a `K ≥ 2` gate rather than by subtracting a reference score. |

### Part VI — Learning and deployment (30–33)

| # | V0.23 page | Disposition | Reason |
|---|---|---|---|
| 30 | Pairwise Advantage Learning: Zero-Bootstrap Loss | **KEEP** | The loss shape, the gauge regulariser and unity deployment weights survive for the two per-user heads; only the route target symbol changes. |
| 31 | Class-Balanced Tri-Partite Loss for LC-SRS | **DELETE** | S/R/C class balancing exists only to protect sparse supported cells on the retired per-user anchor surface. |
| 32 | One-Pass Deployment: Native Masked Argmax | **DELETE** | I-4: the unweighted three-head sum under one argmax is no longer the deployment surface, and the page's own symbol `Φ_u` now means the priced handover cost. **Replaced by** the new two-layer deployment page. |
| 33 | Runtime Invariants: Prohibited Coordination | **REWRITE** | The successor **does** add a set-level coordinator, so the blanket prohibition is withdrawn; what survives is the narrower list — no auction, no voting, no second argmax, no retry, no post-selection repair, no user-to-user messaging — plus budget, deadline and verified fallback. |

### Part VII — Rigor and evaluation (34–38)

| # | V0.23 page | Disposition | Reason |
|---|---|---|---|
| 34 | Method Safeguards: Native Masks and Propensity Strata | **REWRITE** | The native mask survives unchanged; service non-inferiority becomes the QoS co-primary bounds, and matched-placebo strata become neutral sources sealed before generation. |
| 35 | Development Gate: Four Evaluation Arms | **DELETE** | `INFORMED` / `MATCHED_PLACEBO` / `ZERO_SURFACE` / `TEACHER_ORACLE` are arms of the retired LC-SRS observability gate. **Replaced by** the four named experiments and the FULL / DROP / ALL_NEUTRAL arm set. |
| 36 | Development Gate: Pre-Registered Passing Criteria | **DELETE** | Its predicates are numeric criteria of that retired gate. **Replaced by** the `δ = +0.5 %` relative-margin conjunction, the QoS non-inferiority bounds and the admission trichotomy. |
| 37 | Historical vs Future Multi-Arm Matrix | **DELETE** | The `M0` / `N000` / `A011` / `A101` / `A110` / `F111` labelling belongs to the V0.4 ensemble and to a future full-policy protocol that the successor replaced with the four named experiments. |
| 38 | Scientific Claim Ceiling | **REWRITE** | The ceiling idea survives and is promoted: claim ladder Level A/B/C, the admission trichotomy, the intersection-union conjunction, regime-conditional wording, and the rule that missing the margin means the benefit is *not established* rather than the effect being non-positive. |

**Tally over the 38 V0.23 pages — KEEP 5 · REWRITE 19 · DELETE 14.**

- KEEP {2, 4, 9, 21, 30}
- REWRITE {1, 3, 5, 6, 7, 8, 10, 11, 14, 16, 19, 20, 25, 27, 28, 29, 33, 34, 38}
- DELETE {12, 13, 15, 17, 18, 22, 23, 24, 26, 31, 32, 35, 36, 37}

---

## 2. NEW pages the successor requires

Each has no V0.23 ancestor; each is cited to the paper-lane section that
supplies its wording.

| New page | Why it must exist | Wording source |
|---|---|---|
| What the succession invalidates | The audience has seen the V0.23 deck; the delta must be stated before anything is re-taught. | `DELTA-MAP.md` §0 |
| Memoryless rate-target power control | I-1; also carries the in-place deviation statement. | `SEC-SYSTEM-MODEL-REWRITE.md` 3.1.3.1, 3.1.3.4 |
| ACM staircase and equal-airtime TDM | I-2; the rate and the required-SINR staircase. | 3.1.3.2, 3.1.3.3 |
| The coupled solve and its certificates | Standard interference function, unique capped fixed point, three certificates. | 3.1.3.4 |
| Service is decodability after the solve | I-2's service half, plus `rate_target_infeasible`. | 3.1.3.5 |
| Energy: saturated efficiency and terms | The "35 % efficiency" misreading must be corrected explicitly; idle states and slot integration. | 3.1.4.1, 3.1.4.2 |
| The metric boundary, verbatim | The declaration requires the English sentence verbatim in the text and in every receipt header, with the non-cancellation argument. | 3.1.4.3 |
| Handover and QoS pricing `Φ` | The rename, the once-only charging rule, and the two-references rule. | 3.2.2 |
| Singleton increment and interaction residual | I-3's replacement, and the load-bearing page of the deck. | `SEC-METHOD-REWRITE.md` 4.3 |
| Why C3 carries no externality term | Without it the audience mis-reads every surviving C3 slide. | 4.3 |
| The margin-adjusted selection view | Δ9; the quantile rule with its two construction constraints and its withdrawn phrasing. | 4.4.1, 4.4.2 |
| Two decompositions never mixed | Selection-time versus outcome view; every reported quantity must name its view. | 4.4.4 |
| Target / transmit MODCOD pair | Three objects that must never be conflated. | 4.4.3 |
| Bounded catalogue and two-stage scoring | Δ5's machinery, the 10 s budget, the deadline and the fallback. | 4.5 |
| Per-arm sort keys | No arm may rank by a score it has had removed; carries the C2 tie-break consequence. | 4.4.5 |
| Two-layer deployment | Δ5's replacement for the one-pass argmax. | 4.2, 4.8 |
| Comparators | `a⁰`, `a¹`, `a^d`, `a^ψ`, bounds and controls, and the termination-certificate distinction. | 4.7.1 |
| Net collision-avoidance value | Δ10; the mechanism certificate with both untruncated components and the re-anchoring. | 4.7.2 |
| Named experiments and neutral sources | Four experiments that are never presented as one another; the permitted zero result. | 4.8 |
| Claim ladder and admission trichotomy | Δ8; Level A/B/C, `ADMIT_FULL` / `ADMIT_C1C2` / `NOT_ADMITTED`, fixed wording. | 4.9.1–4.9.4 |
| Declared idealisations | Four idealisations stated where the model is defined. | `SEC-SYSTEM-MODEL-REWRITE.md` 3.3 |
| Symbol succession | Readers carry V0.23 letters in their heads; `Ψ` and `G` have changed meaning. | `SYMBOL-ADDITIONS.md` R-1, R-2, §3 |

---

## 3. Consequences for the pilot artefacts

- **`PILOT-SLIDE-SPEC.md` is superseded in full.** It specifies V0.23 slide 23,
  which is DELETE. Its typography contract — Times New Roman; 28 / 24 / 20 pt
  only; atomic single-letter or single-digit sub- and superscripts — is retained
  verbatim and is enforced by the new build.
- **`native-formulas.json` is superseded in full.** All four of its formulas
  (`ℓᵢ`, `eᵢ`, `z₃,ᵢ`, the two-member identity) are retired symbols. The
  replacement manifest is `native-formulas-v025.json`, in the same schema.
- **`MATH-TOKEN-INVENTORY.json`** needs re-deriving against
  `SYMBOL-ADDITIONS.md`: the retired-symbol list is long enough that a
  token-by-token re-audit is cheaper than a diff. Not produced in this delivery.
- **`CORE-FLOW-DRAFT.svg`** shows the one-pass three-head seam and therefore
  contradicts I-4. It needs a two-layer redraw with the catalogue, the deadline
  and the fallback path. Not produced in this delivery.
- **`SCIENCE-CLAIM-MAP.md`** maps claims to the retired gate contract; its
  successor is the claim ladder plus the admission trichotomy. Not produced in
  this delivery.

---

## 4. The resulting arc, as built

The skeleton deck (`v025-deck-skeleton.pptx`, `OUTLINE.md`) consolidates the 24
surviving V0.23 slots and the 22 NEW pages into **34 slides** — several
surviving pages are merged into one successor slide where the successor removed
the distinction that separated them.

```
I    Motivation and endpoint      1  2  3  4  5
II   Successor physics            6  7  8  9 10 11
III  Objective and decomposition 12 13 14 15 16 17 18 19
IV   Selection machinery         20 21 22 23 24
V    Deployment and learning     25 26 27 28
VI   Comparators and claims      29 30 31 32 33 34
```

Notable consolidations: V0.23 pages 7 and 11 merge into deck slide 15; pages 27
and 28/29 merge into deck slides 25 and 27; pages 9, 14 and 30 merge into deck
slide 28; pages 34 and 38 fold into deck slides 31–33.

---

## 5. Reconciliation with the parallel lane

`../_work/STORYBOARD-DELTA-opus5-lane.md` was derived from
`../_work/SUCCESSOR-BRIEF.md`; this file was derived from the paper-lane
rewrites, because the deck is required to reuse the thesis wording. The two
agree on 34 of 38 pages. The four differences:

| # | This file | Parallel lane | Assessment |
|---|---|---|---|
| 5 | REWRITE | KEEP + addendum | Same content change, different label. The verbatim boundary sentence and "successfully decoded" are content edits, so REWRITE is the safer instruction to a slide author. |
| 8 | REWRITE | DELETE | Both are right about the physics: there is no third *additive per-user* Q surface. But `SEC-METHOD-REWRITE.md` 4.8 step 6 fits **three heads** (two per-user, one set-level) and every DROP arm retains all three, so the slide's slot survives with corrected content. |
| 14 | REWRITE | DELETE | Adopted from the parallel lane in part: EXP stratified sampling is indeed replaced by typed deterministic aggregated batches. ACRM's candidate-versus-reference framing and the unit-safety argument survive, so this file downgrades its own earlier KEEP to REWRITE rather than to DELETE. |
| 16 | REWRITE | KEEP | The persistence motivation survives, but the object becomes a three-offset nominal continuation whose certificate is prediction validity; that is a content change. |

Both files independently flag the same live contradiction in the source set: an
engine-side "30.08 s per decision" against contract v1 §F2's **10 s** compute
budget. Contract v1 is later and sealed, so 10 s is the budget and 30.08 s is
the decision interval; the deck uses the contract figure.
