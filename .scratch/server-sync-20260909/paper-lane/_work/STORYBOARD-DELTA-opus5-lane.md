# STORYBOARD-DELTA — the 38-page v0.23 teaching deck against the V0.25 successor

**Scope.** One verdict and one reason for each of the 38 pages of
`agy-pilot/STORYBOARD.md`, judged against the sealed successor set in
`.scratch/multi-catfish-v025-physics-successor/`. Authority for every successor
claim is `_work/SUCCESSOR-BRIEF.md` (§A architecture, §B invalidations,
§C formulas, §D boundaries, §E prohibitions, §F concept verdicts).

**Verdicts.** `KEEP` = survives in role and wording. `REWRITE` = the page's
question survives but its content, symbols or numbers must change. `DELETE` =
removed from the arc; may appear only as labelled history. `NEW` = the successor
needs a page the v0.23 deck has no equivalent for.

**Tally.** 9 KEEP · 18 REWRITE · 11 DELETE · 10 NEW → a 47-page successor arc.

Source artefacts are read-only; nothing under `mcrl-paper-sources/` or `docs/`
was modified.

---

## 1. Page-by-page verdicts

### Part I — Motivation and objective (1–6)

| # | Title | Verdict | Reason |
|---|---|---|---|
| 1 | Multi-Catfish MCRL: Teaching Deck Overview | **REWRITE** | Its core-concept line ("three independent Q surfaces, and one native masked argmax") is false under the successor, which has two heads and a set-level coordinator (brief §F.1, §A.3). |
| 2 | LEO Satellite Network Context: Orbital Dynamics & Narrow Beams | **KEEP** | Slant range $d_{u,s,v}(t)$ and off-axis angle $\theta_{u,s,v}(t)$ still drive the whole model — the successor makes the angle→power link *stronger*, not weaker (brief §C.1). |
| 3 | Coupled Satellite Resources: Beam Power & Ground Interference | **REWRITE** | Three of its statements die with the power model: per-beam RF is no longer the max over the beam's users, the PA is slot-averaged, and users no longer "divide total bandwidth $B^w/U_{s,v}$" — the successor uses equal-airtime **full-band TDM** (brief §B.1 riders, §A.0). |
| 4 | Limits of Conventional Multi-Objective Handover: The MODQN Dilemma | **KEEP** | The scalarisation critique is independent of the physics and still motivates the canonical objective. |
| 5 | The Canonical Endpoint: Network Ratio-of-Sums EE | **KEEP** (+ addendum) | "Ratio of sums, never sum of ratios" is retained verbatim (brief §F#16); add the mandatory v1.8 §3 energy-boundary sentence that every statement of it must now carry. |
| 6 | Linear Surplus Formulation and the Frozen Multiplier | **REWRITE** | The *rule* $\lambda=\eta_{\rm ref}$ survives but the *value* does not — the old multiplier "carries the artifact" and is re-derived per setting; add v1.6 §5's caveat that a frozen multiplier alone does not imply a better realised ratio (brief §F#17). |

### Part II — Causal decomposition (7–11)

| # | Title | Verdict | Reason |
|---|---|---|---|
| 7 | The Causal Attribution Dilemma in Multi-User Handover | **REWRITE** | The three questions survive, but the answer structure changes: questions 1–2 collapse into the whole-network C1 and question 3 becomes C2 *forecast validity*, not a third additive surface (brief §F#5, §F#6). |
| 8 | Architecture Invariant: Three Independent Q Networks | **DELETE** | The successor instantiates exactly two heads; "沒有第三個 additive Q head" is explicit, because additive per-user surpluses cannot represent the joint gain of emptying a beam (brief §F#1, §B.2). |
| 9 | Architecture Invariant: Route-Local Zero-Bootstrap Training | **KEEP** | Pairwise zero-bootstrap regression with no target networks is retained verbatim, and "no Bellman replay in the successor" reinforces it (brief §A.3). |
| 10 | Unilateral Counterfactual Evaluation: The C1 Opening Intervention | **REWRITE** | The matched-branch protocol survives, but the C1 label is redefined from focal-bits-only to a **full-network difference surplus** against the declared default action (brief §F#5). |
| 11 | The Coalition Exception: Why C3 Breaks Unilateral Symmetry | **REWRITE** | The argument is right and now load-bearing, but its conclusion changes: the exception is answered by a **set-level coordinator over whole profiles**, not by a fourth-profile route inside a per-user head (brief §B.2). |

### Part III — Route C1 (12–15)

| # | Title | Verdict | Reason |
|---|---|---|---|
| 12 | Route C1 Role: Focal Opening Net Surplus | **REWRITE** | "Assigns the entire opening-step system power difference to the focal mover" is superseded by the whole-network surplus, and C1's positive marginal is now expected "through energy and service, not surplus bits" (brief §F#5). |
| 13 | Route C1 Target Formulation: Assigning Opening Energy | **REWRITE** | $\zeta_{1,u}$ is replaced by $C1=\sum_{i\in A} d_i$ evaluated on $F = B - \eta_{\rm ref}E - \Phi$ with $\Phi$ charged exactly once (brief §C, §F#9). |
| 14 | Route C1 Lineage: The RIS EXP/ACRM Lineage | **DELETE** | EXP stratified frontier sampling is replaced by typed deterministic aggregate batches; only the legacy trainer's *configuration* is copied, not its sampling machinery (brief §A.3). |
| 15 | Route C1 Historical Evidence: V0.4 Frozen-Policy Margin | **DELETE** | A +254.596 % pooled-EE margin measured under the retired physics, in an old-Q2 frozen-policy context — brief §E bars re-showing it as evidence for the successor. |

### Part IV — Route C2 (16–19)

| # | Title | Verdict | Reason |
|---|---|---|---|
| 16 | Route C2 Role: Evaluating Temporal Persistence | **KEEP** | The persistence question and the ping-pong argument survive intact as C2's reason to exist. |
| 17 | Route C2 Evolution: From Temporal-Fork to First-Successor k1 | **REWRITE** | The $k=1$ single-offset target is replaced by a three-offset continuation with $-\kappa$ charged per absorbing lost offset (brief §C, §F#6). |
| 18 | Route C2 Diagnostic Failures: V0.6 Screen and V0.7 R14 Audit | **DELETE** | −28.575 %, 0/3 lineages and the 76.07 % flip rate are old-physics outcomes for a retired C2 learner; the successor's C2 is a different object with a different state. |
| 19 | Current C2 Status: Present but Unqualified OPS-3 Diagnostic | **REWRITE** | C2 is no longer a parked diagnostic: its entire temporal state is redefined from geometry and rate forecasts, and its matrix certificate is **forecast validity, not a selection marginal** (brief §F#6, §A.7). |

### Part V — Route C3 / LC-SRS (20–29)

| # | Title | Verdict | Reason |
|---|---|---|---|
| 20 | The Spatial Externality Problem: Shared Beam Coupling | **KEEP** | Contention and cross-tier interference are unchanged physical motivation, and the successor adds beam-specific cross gains that make the coupling explicit. |
| 21 | The Beam Extinction Blindspot in Unilateral Exploration | **KEEP** (promote) | This is now the successor's central structural argument — "the saving appears only when the last user leaves … that gain must be given to a coordinator" — so it should be strengthened, not cut (brief §B.2). |
| 22 | The Two-User Cooperative Game: Four Matched Profiles | **REWRITE** | The 2×2 grid survives only as the $|A|=2$ special case $\Psi=F_{11}-F_{10}-F_{01}+F_{00}$; the successor computes $\Psi_A$ for **every** coalition regardless of size at $|A|+2$ evaluations (brief §F#7). |
| 23 | Exact Two-Player LC-SRS Teacher Formulation *(the pilot slide)* | **REWRITE** | $\ell_i$, $e_i$ and $\Psi=\Psi_B-\lambda\Psi_E$ are replaced by $d_i$ and $\Psi_A$ on $F=B-\eta_{\rm ref}E-\Phi$; the externality term is struck entirely (brief §B.2(3)). |
| 24 | Super-Additive Interaction Surplus and the Shapley Target | **REWRITE** | $z_{3,i}=e_i+\Psi/2$ becomes $z_{3,i}=\Psi/2$ — "the historical LC-SRS $e_i$ … is not transferred" — and the per-user Shapley split is now **reporting only, capped at $|A|\le4$, never a training target** (brief §F#8). |
| 25 | Construction-Level Exact Identity: Surplus Conservation | **REWRITE** | The structural role is kept but the identity is restated as **$C1 + C3 = F(a_A) - F(a^0)$ exactly (KAT)**, with a second KAT for the physical identity without $\Phi$ (brief §F#9). |
| 26 | The Teacher Anchor Surface: Supported, Reference, Control | **DELETE** | $S_h/R_h/C_h$ is the label surface of the additive per-user Q3 head; the successor trains $\hat\Psi_\theta$ on the coalition support of the bounded catalogue instead (brief §A.5). |
| 27 | Deployment C3View: Committed vs. Detached Context | **REWRITE** | The committed/detached idea survives as the two never-conflated references ($a^0$ vs the previous committed association), but the feature object becomes `I_coordinator` plus a set-head context that **must** carry pairwise cross-gains among affected beams (brief §F#10). |
| 28 | Relational Token Architecture: Shared 67-64-64-1 Scorer | **DELETE** | The successor's C3 encoder is a different object — permutation-invariant sum/max pooling over changed users feeding a two-layer MLP (brief §F#11). |
| 29 | Reference-Centering: Enforcing the Structural Zero Invariant | **KEEP** (re-expressed) | The gauge survives exactly in spirit as the set-level anchor $\hat\Psi(\emptyset)=\hat\Psi(\{u\})=0$, "anchored zeros by construction" (brief §F#12). |

### Part VI — Learning and deployment (30–33)

| # | Title | Verdict | Reason |
|---|---|---|---|
| 30 | Pairwise Advantage Learning: Zero-Bootstrap Loss | **KEEP** | This is still exactly the Q1/Q2 training form, with the legacy trainer's configuration copied rather than re-tuned (brief §A.3). |
| 31 | Class-Balanced Tri-Partite Loss for LC-SRS | **DELETE** | The tri-partite $S/R/C$ loss exists only to protect sparse Supported cells on the additive Q3 surface, which no longer exists. |
| 32 | One-Pass Deployment: Native Masked Argmax | **REWRITE** | The masked argmax survives but is **demoted to the proposal stage $a^0$**, which must then be validated into a jointly legal profile and passed to the coordinator (brief §F#3). |
| 33 | Runtime Invariants: Prohibited Coordination Mechanisms | **DELETE** | Three of its four prohibitions are now mandatory features — a runtime coordinator, a deterministic post-selection repair rule, and a deadline fallback; only "no auction/bidding/voting" survives, as description rather than red line (brief §F#4). |

### Part VII — Rigor and evaluation (34–38)

| # | Title | Verdict | Reason |
|---|---|---|---|
| 34 | Method Safeguards: Native Masks and Propensity Strata | **REWRITE** | Masks stay first-class but legality can now lapse **mid-step** at boundary $k$, an empty mask yields NO_OP with a receipt counter, and "joint SINR is not an independently guaranteeable per-user legality mask" (brief §F#14). |
| 35 | Active V0.23 Development Gate: Four Evaluation Arms | **DELETE** | The observability framing died with the additive head; the successor's taxonomy is four never-conflated experiments over a 6-arm panel (brief §F#18). |
| 36 | Active V0.23 Development Gate: Pre-Registered Passing Criteria | **DELETE** | Its predicates (Spearman ≥ 0.20, literal-11 adoption ≥ 25 %, the `GO_FIXED_LEARNER_SCREEN_CONTRACT` token) are defined over a surface that no longer exists; the successor gate is the admission trichotomy plus the Level A/B/C ladder. |
| 37 | Historical vs. Future Evaluation: The Multi-Arm Matrix | **DELETE** | None of `M0/N000/A011/A101/A110/F111` appears in the sealed successor set, and the 2³ factorial reading it implies is explicitly barred without the full factorial (brief §F#19). |
| 38 | Scientific Claim Ceiling: Development Gate Boundary | **REWRITE** | The *device* is essential and must stay, but every clause changes: the new ceiling is TRAIN-only with no TEST, `PILOT_NOT_CLAIM` on all Track F artefacts, the admission trichotomy, and the "never 'coordination'" wording rule (brief §E). |

### NEW pages the successor requires

| # | Working title | Why it is needed |
|---|---|---|
| N1 | The 48-Boundary Invariant | The study's defining rule — selection may be approximated ($k=0$, top-$M$ pruning, margin adjustment); the endpoint may not (brief §A.9). |
| N2 | The Bounded Catalogue 𝒞 | The coordinator is only deployable because the search space is bounded to ≈ 1 200 rows with a ≤ 1 500 guard (brief §A.6). |
| N3 | The 10 s Deadline and the BASE Fallback | A deployability constraint with scientific consequences: misses fall back to the pre-validated $a^0$ and are counted in $B$ and $E$ (brief §D.2). |
| N4 | Three Selectors: S3 / S0 / S_UNI | The learned layer, its exact twin, and the certified comparator that bounds what a learned claim can mean (brief §A.5). |
| N5 | The Margin-Adjusted Selection View | The $q_{10}$ quantile on the wanted link only, with the v1.9 corrections (brief §C.9). |
| N6 | The Coupled Capped Power Solve | The fixed point that makes occupancy and angle interact, with its `CONVERGED` / `CONVERGED_SLOW` certificates (brief §A.8). |
| N7 | The Admission Trichotomy | `ADMIT_FULL` / `ADMIT_C1C2` / `NOT_ADMITTED` is the actual endpoint of the physics matrix (brief §A.12). |
| N8 | The Claim Ladder A / B / C | What a C3 result is permitted to say, and the bounded set of admissible learned claims (brief §A.12, §E). |
| N9 | Track F vs Track S | The pilot exists and must be visibly fenced off from the claim path (brief §A.13). |
| N10 | The Design Freeze and Closure Rule | The four-part admissibility test that governs any further change (brief §E). |

---

## 2. Pages invalidated by the physics succession

The task named three succession events. Below is exactly which pages each one
invalidates and what replaces the invalidated content.

### 2.1 Segment-anchored power → memoryless rate-target TPC

**What died.** `p(t) = p^{0}\,G^T(\theta(\tau))/G^T(\theta(t))` with
$p^{0}=0.825$ W reset at every segment start, holding the *received level*
constant within a segment, plus the 3.010 dB in-segment budget. Sealed out by
round-3 §2 item 4: "**No segment-entry gain, recurrence, reset target or
private-power/beam-max hybrid survives.**"

**What replaces it.** The memoryless capped rate-target map
$p_u = \min\!\left(1.65\ \mathrm{W},\ \Gamma_r(n_b)\,(N_0W+\hat I_u)/\hat h_u\right)$
solved as a coupled capped fixed point — "**angle drives power through $\hat h_u$;
occupancy drives power through $\Gamma_r(n_b)$**" (v1.1 §Amendments 1).

**Pages invalidated:** **3** (per-beam max power, bandwidth split), **12–13**
(opening-step energy assignment rests on the reset), **17** (C2's temporal state
was `previous_recurrence_power`, gain-to-entry ratio and `segment_age` — under
per-step physics three of these become constants), **19**, **6** (λ was derived
under the retired physics), **34** (power over-allocation as a mask criterion).

**The specific artefact removed** is the **renewal premium**: staying on a beam
was charged rising energy for no extra bits while re-anchoring was free in the
endpoint, so a coordinator could harvest it. A single beam re-anchored at
0.744 dB staleness reproduces the whole observed +2.883 %; the receipts cannot
exclude that 100 % of the energy-side gain was renewal. Every v0.23 EE number in
the deck sits on top of this artefact — which is the deeper reason pages 15, 18
and 37 are DELETE rather than REWRITE.

### 2.2 The LC-SRS teacher C3 → set-level coordinator → interaction residual

**What died, in three steps.** (1) The additive third head was **closed at the
oracle level** — the C3 marginal was ≤ 0 across G0–G3 once the exact
others'-delivered-bit externality was composed through `argmax(Q1+Q2+z/κ)`, and
"two weeks of ≤ 0 oracle marginals were structural". (2) It was architecturally
replaced by a set-level coordinator: "**no third additive Q head, no third-head
training and no individualised surplus allocation**." (3) The LC-SRS *target*
itself was struck: because the whole-network C1 already contains every unilateral
bit and joule change, "the historical LC-SRS $e_i$ … **is not transferred**".

**What replaces it.** `C3(config) = Ψ_A`, the interaction residual, learned by a
set-conditioned scalar head $\hat\Psi_\theta$ and deployed as S3 over the bounded
catalogue, with per-user Shapley attribution demoted to reporting only.

**Pages invalidated:** **8** (three surfaces), **22–26** (the four-profile
teacher, $\ell_i/e_i/\Psi$, $z_{3,i}=e_i+\Psi/2$, the conservation identity, the
anchor surface), **27–29** (C3View, the token scorer, the centering gauge as a
*per-user* device), **31** (the tri-partite loss), **35–36** (the observability
gate built to test that surface).

### 2.3 The old service rule → an SINR threshold after joint resolution

**What died.** Service as **power feasibility**: a link was infeasible once
$p_{\rm req} > p^{+}$ within the 3.010 dB in-segment budget, which forced an
outage and a re-anchor. Note this rule was *inseparable* from segment-anchored
power — it tested a quantity that only existed because the received level was
being held.

**What replaces it.** A physical threshold applied after the coupled solve:
cap-bound users are flagged `rate_target_infeasible`, transmit at the cap, and
are **served iff their SINR after joint resolution ≥ SINR_min** (−1.4418 dB, the
sealed PHY floor). Legality can additionally lapse mid-step: a link crossing
below 10° or losing D2 eligibility at boundary $k$ stops radiating and decoding
from that boundary onward.

**Pages invalidated:** **34** (the service non-inferiority guard, which now
splits into a deployable "no served-count decrease versus BASE" guard that
*scores and reports* rather than excluding, plus a statistical QoS rule with new
margins), **32** (the "service-safe mask" framing), **3**, **36**.

### 2.4 One consequence worth stating separately

Pages **32** and **33** are invalidated not by the physics but by what the physics
forced: once the joint gain of emptying a beam must be represented at set level,
a runtime coordinator becomes mandatory. The v0.23 deck's proudest architectural
claim — "offline complexity, online simplicity", no coordinator, no repair, no
fallback — is precisely inverted. The successor deck must make that reversal
explicit rather than quietly dropping the slide, because the reversal *is* the
scientific content: it is the price of representing a saving that no per-user
surplus can express.

---

## 3. Evidence-quality flags

Two DELETE verdicts rest on weaker evidence than the rest and are marked here so
they are not mistaken for sealed decisions:

- **Page 35** (four-arm gate) — of `INFORMED` / `MATCHED_PLACEBO` /
  `ZERO_SURFACE` / `TEACHER_ORACLE`, only `MATCHED_PLACEBO` appears anywhere in
  the handoff corpus, and none appears in the sealed successor set. The verdict
  rests on absence-from-corpus plus a positively-cited replacement taxonomy, not
  on a document that names and retires these arms.
- **Page 37** (five-arm matrix) — same basis: no successor document names
  `M0/N000/A011/A101/A110/F111` in order to retire them.

Both should be confirmed against the seal package when it lands.

A third item is a live contradiction rather than a weak inference: the engine
prompt says "30.08 s wall per decision" while contract v1 §F2 says **10 s**.
Contract v1 is later and sealed, so 10 s governs the compute budget and 30.08 s
is the decision interval — but the engine text was never edited, and slide N3
must use the contract figure.

---

## 4. Resulting arc

```
I    Motivation and objective          1  2  3  4  5  6
II   Attribution and architecture      7     9 10 11              (8 cut)
III  Route C1                         12 13                       (14 15 cut)
IV   Route C2                         16 17    19                 (18 cut)
V    The joint-gain problem           20 21 22 23 24 25    27  29 (26 28 cut)
VI   Learning and deployment          30    32                    (31 33 cut)
VII  Successor mechanism              N1 N2 N6 N4 N5
VIII Evaluation and claim             34 N7 N8 N9 N10 38          (35 36 37 cut)
```

27 surviving pages + 10 new = **47**. The centre of gravity moves from
"three routes and a teacher" to "one bounded search under a deadline, with an
endpoint that is never approximated".
