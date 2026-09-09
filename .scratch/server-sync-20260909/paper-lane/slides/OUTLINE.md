# OUTLINE — V0.25 physics-successor deck skeleton

Markdown review copy of `v025-deck-skeleton.pptx`: **34 slides**, **18 native OfficeMath equations**, one speaker note per slide.

- **Generated file.** Produced by `make_outline.py` from the same `DECK` object the deck is built from, so the two cannot drift. Equations are quoted from `native-formulas-v025.json`, the manifest the OMML injector consumes.
- **Dispositions** refer to `STORYBOARD-DELTA.md`; V0.23 page numbers are those of `agy-pilot/STORYBOARD.md`.
- **No result numbers.** `⟨結果待填⟩` marks every slot where a result belongs.
- **Typography** is the V0.23 contract, unchanged: Times New Roman; 28 pt titles, 24 pt ordinary body text, 20 pt inside cards, boxes and badges; no other sizes.

---

## Slide 1 — Multi-Catfish MCRL V0.25

**Disposition:** REWRITE of V0.23 p.1 · **Layout:** title

*The physics successor: one terminal objective, a memoryless rate-target physics chain, and a two-layer decision structure that is evaluated rather than assumed.*

- Baseline: V0.25 successor declaration v1.0 with amendments v1.1–v1.9; stages 6–8 contract; design freeze and closure rule.
- Status: PAPER-LANE-A v2 DRAFT. Method description frozen, empirical surface empty. This deck states no efficacy.
- Every result slot reads ⟨結果待填⟩ until the formal matrix is run.

**Speaker note.** Open on the boundary: the method core is frozen, the claim surface is still empty.

---

## Slide 2 — What the Succession Invalidates

**Disposition:** NEW (states the delta) · **Badge:** `SUCCESSION` · **Layout:** table

*Four V0.23 teaching claims are retired; each has a named successor.*

| Retired | Successor | Why it matters |
|---|---|---|
| Segment-anchored power | Memoryless rate-target power control, re-solved every step | No segment, no entry power, no cross-step state |
| Shannon rate; mask-based service | ACM staircase, airtime TDM, decodability after the solve | Occupancy now reaches energy through required SINR |
| LC-SRS teacher C3 | Singleton increments plus a set-level interaction residual | The externality term is absorbed by C1, not deleted |
| One-pass three-head argmax | Per-user proposal, then a set-level selector over a catalogue | A coordinator now exists and is under evaluation |

> The set-level layer is a layer under evaluation, not a layer assumed effective.

**Speaker note.** This is the map of the delta; every later slide is downstream of one of these four rows.

---

## Slide 3 — LEO Context: Dynamics and Narrow Beams

**Disposition:** KEEP of p.2, plus the 10° rule · **Badge:** `CARRIED` · **Layout:** cards

*Unchanged background physics, plus one new declared visibility rule.*

**Fast geometry**

- Satellites move quickly past ground users.
- Slant range and off-axis angle drift within and across steps.
- Users must repeatedly re-select a serving beam.

**Narrow steerable beams**

- Transmit gain falls sharply off-axis.
- Geometry reaches power only through link gain times transmit gain.
- That product is the sole entrance of angle into energy.

**Minimum elevation**

- NEW: below 10° a satellite is not a candidate.
- Crossing the threshold mid-step stops radiating and decoding there.
- Bits and energy stop together; the rest of the step is unserved.

> The 10° threshold is a declared model choice and a registered deviation from the 0° legacy screen.

**Speaker note.** Short page: unchanged background plus one new declared threshold.

---

## Slide 4 — Why Multi-Objective Handover Fails

**Disposition:** KEEP of p.4 · **Badge:** `CARRIED` · **Layout:** cards

*The case for one canonical endpoint is untouched by the succession.*

**Conventional MODQN: heuristic scalarisation**

- Disparate metrics summed with hand-chosen weights.
- Bits per second, handover counts and user ratios cannot physically sum into an efficiency.
- Greedy link optimisation ignores shared activation cost and non-focal harm.
- Load balancing appears as a third reward that duplicates the first.

**V0.25: one canonical endpoint**

- A single terminal objective: pooled ratio-of-sums efficiency.
- QoS is reported as co-primary outcomes and acts as a non-inferiority condition, never as a weight.
- Occupancy is not a separate objective; it already enters energy through the required-SINR staircase.
- Decomposition assigns credit. It is never a vote.

**Speaker note.** Say plainly that the three-objective reward vector is gone, not re-weighted.

---

## Slide 5 — Coupled Resources Under Airtime TDM

**Disposition:** REWRITE of p.3 · **Badge:** `SUCCESSION` · **Layout:** cards

*Occupancy reaches energy twice: the rate denominator and required SINR.*

**Beam activation cost**

- Lighting a beam draws chain circuitry plus a declared processing increment.
- One beam maps to one switchable RF chain — declared, not surveyed.
- Emptying a beam is the only way to remove that cost.

**Equal-airtime TDM**

- Users on a beam take turns over the whole beam bandwidth.
- Each gets a 1/occupancy airtime share, aligned by user index.
- So beam RF power is that one user's power; max-over-users aggregation retires.

**Interference is a fixed point**

- Same-colour interference is a function of the whole power vector.
- Cross gains are keyed by satellite and beam chain, not folded to satellite level.
- Colour belongs to the chain; a user inherits its serving chain's colour.

**Speaker note.** The pivot: occupancy is no longer a fairness concern, it is a power-consumption mechanism.

---

## Slide 6 — Memoryless Rate-Target Power Control

**Disposition:** NEW (Δ1) · **Badge:** `SUCCESSION` · **Layout:** math

*Power is re-solved every step; nothing at all is carried across steps.*

**Native OMML — `power`** (label “Power”, SEC-SYSTEM-MODEL-REWRITE.md eq. (3.11))

```latex
p_{u,s,v}(t)=\min\left\{p^{+},\frac{\Gamma_{r}\left(U_{s,v}(t)\right)\left[\sigma^{2}+I_{u,s,v}\left(t;\mathbf{p}\right)\right]}{H_{u,s,v}(t)\,G^{T}\left(\theta_{u,s,v}(t),\theta_{3}\right)}\right\}
```

**What replaced the recursion**

- No segment, no entry power, no segment age, no cross-step state. Power follows this step's rate target and this step's geometry and interference.
- Geometry enters only through composite link gain times transmit pattern gain — the denominator above. The cap is a physical ceiling, not a feasibility screen.
- In-place deviation statement: a history-recursive rule was replaced during simulator development, and the register discloses that timing.

> The right-hand side is a standard interference function, so iterating from zero converges to the unique capped fixed point.

**Speaker note.** Stress that this one equation is the whole power model; there is no second historical branch.

---

## Slide 7 — The Discrete ACM Staircase

**Disposition:** NEW (Δ2) · **Badge:** `SUCCESSION` · **Layout:** math

*Rate is a staircase of frozen modes divided by beam occupancy.*

**Native OMML — `acm`** (label “Rate”, SEC-SYSTEM-MODEL-REWRITE.md eq. (3.14))

```latex
R_{u,s,v}(t)=\frac{B^{w}\,\nu_{m}}{U_{s,v}(t)}
```

**Native OMML — `modcod`** (label “Mode”, SEC-SYSTEM-MODEL-REWRITE.md eq. (3.14a))

```latex
m^{r}_{u,s,v}(t)=\min\left\{m\in\mathcal{M}:\frac{B^{w}\nu_{m}}{U_{s,v}(t)}\ge R^{\star}\right\}
```

**Native OMML — `gammar`** (label “SINR”, SEC-SYSTEM-MODEL-REWRITE.md eq. (3.14a))

```latex
\Gamma_{r}\left(U_{s,v}(t)\right)=\gamma_{m^{r}}
```

**Reading the staircase**

- Modes come row by row from EN 302 307-1 Table 13, with a 1.7 dB implementation margin and a 0.20 roll-off conversion; no DVB-S2X performance is claimed.
- The rate target is a synthetic operating point that fixes the power set-point only. Occupancy sits in the rate denominator and in the required-SINR argument.

**Speaker note.** Point at both places occupancy appears; that coupling retires load balancing as its own objective.

---

## Slide 8 — The Coupled Solve and Its Certificates

**Disposition:** NEW (Δ1, coupled solve) · **Badge:** `SUCCESSION` · **Layout:** cards

*Every simultaneously radiating configuration is solved as one system.*

**Why it is coupled**

- Each link's required power depends on the interference it sees.
- That interference depends on every other link's power.
- So the per-link rule is a system, not a closed form.
- Iteration starts from the all-zero vector.

**Convergence rule**

- Judged on the update itself, not on a residual that special-cases capped rows.
- Max absolute change 1e-10 W, or max relative change 1e-9.
- Iteration budget 65 536.

**Three certificates**

- CONVERGED — tolerance reached.
- CONVERGED_SLOW — budget spent, last iterations monotone and small.
- INVALID — non-finite or non-monotone; an implementation fault, and the unit halts.
- Infeasible or slow states are legal physics, not errors.

> Share of CONVERGED_SLOW configurations: ⟨結果待填⟩ — a physical finding to discuss, never a reason to change the model.

**Speaker note.** The certificate vocabulary is the honesty device: slow convergence is reported, not engineered away.

---

## Slide 9 — Service Is Decodability After the Solve

**Disposition:** NEW (Δ3) · **Badge:** `SUCCESSION` · **Layout:** math

*The mask says what may be chosen; decodability says what becomes a link.*

**Native OMML — `service`** (label “Serve”, SEC-SYSTEM-MODEL-REWRITE.md eq. (3.13a))

```latex
\gamma_{u,s,v}(t)\ \ge\ \gamma^{-},\qquad\gamma^{-}=-1.4418\ \mathrm{dB}
```

**What changed**

- OUT: served meant a mask-passing action whose required power fitted under the cap. IN: the realised SINR clears the frozen threshold, judged after the joint solve.
- A user who cannot reach the rate target under the cap is flagged rate_target_infeasible, transmits at the cap, and keeps its partial delivery, interference and energy.
- Unserved means below the decodability threshold. It does not mean the rate target was missed; those are two separate reported fields.

> Availability splits three ways — decode, useful, fully-served user-steps — beside a separate rate-attainment rate. No guaranteed-rate endpoint is claimed.

**Speaker note.** The sentence to land: this work claims no guaranteed-rate endpoint anywhere.

---

## Slide 10 — Energy: Saturated Efficiency and Terms

**Disposition:** NEW (energy model) · **Badge:** `SUCCESSION` · **Layout:** math

*The amplifier law applies per slot, then integrates by airtime.*

**Native OMML — `pnet`** (label “Power”, SEC-SYSTEM-MODEL-REWRITE.md 3.1.4 (eq. 3.16, 3.16a retained))

```latex
P^{N}(t)=\sum_{s\in\mathcal{S}}\left[\sum_{v}P^{p}_{s,v}(t)+N^{a}_{s}(t)\,P^{c}+\mathbb{1}\left\{N^{a}_{s}(t)>0\right\}P^{b}\right]
```

**Native OMML — `energy`** (label “Sum”, SEC-SYSTEM-MODEL-REWRITE.md 3.1.3.6 + 3.1.4.3 (48 boundaries, 47 sub-intervals))

```latex
E(a)=\sum_{t}\sum_{k=0}^{46}P^{N}\left(t,k\right)\,\Delta t_{k}
```

**Reading the energy chain**

- The square-root amplifier law is unchanged in shape; only its reading is corrected. The 0.35 figure is the saturated efficiency, not the operating-point efficiency.
- The realised efficiency at the cap, and again near the single-user pivot, is far lower. The text says saturated efficiency everywhere and never says 35% efficiency.
- Idle states are explicit: zero idle power in the primary setting, a declared 12-chain census in the sensitivity setting. Integration uses 48 boundaries per 30.08 s step.

> One beam to one switchable chain, and a named common processing increment: both are declared conditions, not measurements.

**Speaker note.** Say the efficiency correction out loud; it is the most quotable error the successor fixes.

---

## Slide 11 — The Metric Boundary, Stated Verbatim

**Disposition:** NEW (metric boundary) · **Badge:** `FROZEN` · **Layout:** quote

*This sentence appears verbatim in the text and in every receipt header.*

> "Pooled successfully decoded forward-downlink information bits per joule of modelled partial-payload DC energy, comprising user-link PA supply, the declared per-beam chain circuitry and a declared common processing increment, with explicitly stated idle states; spacecraft bus, unmodelled payload functions, feeder and inter-satellite links, and ground/terminal energy are outside this metric."

**Omitted common energy does not cancel between policies**

- Add a policy-independent energy term to both denominators: the sign of the difference of the two ratios then depends on delivered bits as well as on energy. So whenever two policies deliver different bit totals, a partial-payload-scale gain does not transfer to constellation scale.
- Every efficiency claim must therefore name its boundary, and no result may be restated at a wider scale.

**Speaker note.** Read the boundary sentence aloud once; it is the shortest defence against the commonest misreading.

---

## Slide 12 — The Single Terminal Objective

**Disposition:** REWRITE of p.5 · **Badge:** `FROZEN` · **Layout:** math

*Pooled ratio-of-sums efficiency, with QoS beside it as co-primary.*

**Native OMML — `eta`** (label “Ratio”, SEC-SYSTEM-MODEL-REWRITE.md eq. (3.24))

```latex
\eta^{N}=\frac{\sum B}{\sum E}
```

**Rules that travel with the ratio**

- Total successfully decoded bits over total network energy inside the declared boundary, across the whole claim panel.
- It may not be rewritten as a mean of per-row efficiencies, and it may not be read as a weighted sum of reward components.
- Co-primary outcomes: fully-served availability, handover rate, priced per-user-step handover cost, and rate-target attainment.
- These are non-inferiority conditions. A contrast that passes on efficiency but fails a QoS bound does not stand.

> The three-objective long-run formulation of the previous version is withdrawn, not re-weighted.

**Speaker note.** Anchor here: everything downstream is a device for improving this one ratio.

---

## Slide 13 — Handover and QoS Pricing

**Disposition:** NEW (Φ pricing) · **Badge:** `SUCCESSION` · **Layout:** math

*The per-user handover cost is renamed, re-priced, and charged once.*

**Native OMML — `phi`** (label “Price”, SEC-SYSTEM-MODEL-REWRITE.md eq. (3.27); SYMBOL-ADDITIONS.md R-1)

```latex
\Phi(a)=\sum_{u\in\mathcal{U}}\Phi_{u}(t),\qquad\varphi_{1}=0.5\,\kappa,\qquad\varphi_{2}=1.0\,\kappa
```

**Event accounting**

- Events are classified by physical identity: hold, intra-satellite beam change, inter-satellite handover, re-entry, and dwell-boundary cell re-key.
- Re-entry prices as inter-satellite if the satellite differs from the pre-outage incumbent, otherwise as a beam change. A re-key with no beam change is not a handover.
- The 'before' state is always the incumbent association carried from the previous step — never the same-step reference proposal.
- Prices stand for signalling and QoS preference only. They are not time and they are not joules.

> Symbol succession: the per-user handover cost moves to Φ so that Ψ can be reserved for the interaction residual.

**Speaker note.** Flag the rename early; the audience will otherwise read Ψ with its V0.23 meaning.

---

## Slide 14 — The Residual and the Objective Gap

**Disposition:** REWRITE of p.6 · **Badge:** `FROZEN` · **Layout:** math

*Selection and learning share one residual; the ratio is what is claimed.*

**Native OMML — `omega`** (label “Score”, SEC-SYSTEM-MODEL-REWRITE.md eq. (3.25) = SEC-METHOD-REWRITE.md eq. (4.6))

```latex
\Omega(a)=B(a)-\lambda\,E(a)-\Phi(a)
```

**Definition and its honest caveat**

- Whole-network delivered bits, minus the frozen bits-per-joule multiplier times whole-network energy, minus the priced handover term counted exactly once.
- The multiplier is the reference efficiency frozen at calibration, never replaced by a post-outcome price. The residual is normalised before use in learning.
- Objective gap, stated once: a higher residual does not imply a higher realised pooled ratio. Dinkelbach methods update the multiplier; this design does not.
- So every claim is stated on the realised pooled ratio, and the residual stays a target-consistent but non-equivalent proxy for selection and training.

**Speaker note.** The objective gap is a concession, not a footnote — state it before anyone asks.

---

## Slide 15 — The Attribution Question, Restated

**Disposition:** REWRITE of p.7 merged with p.11 · **Badge:** `SUCCESSION` · **Layout:** cards

*Three causal channels survive; two now attach to different objects.*

**What one move is worth**

- V0.23: focal opening-step surplus, with the whole opening power difference on the mover.
- V0.25: the change in the whole-network residual when only that user moves.
- Every other user's effect is already inside this term.

**What it is worth later**

- V0.23: a first-successor one-step accounting term.
- V0.25: a declared continuation value over three prediction offsets.
- Nominal geometry and nominal interference only; an offset lost to absorption is charged at the common scale.

**What a set is worth**

- V0.23: a two-user coalition exception with an equal split.
- V0.25: the interaction residual of any changed-user set, at K+2 evaluations.
- Per-user credit splitting is report-only and stops at four members.

> A single scalar reward still hides all three; the decomposition is what makes them separately learnable.

**Speaker note.** Frame it as continuity of question with discontinuity of answer.

---

## Slide 16 — Singleton Increment and Interaction

**Disposition:** NEW — replaces DELETE p.13, 22, 23, 24 · **Badge:** `FROZEN` · **Layout:** math

*Two definitions on the reference proposal replace the whole teacher.*

**Native OMML — `singleton`** (label “Solo”, SEC-METHOD-REWRITE.md eq. (4.7); SYMBOL-ADDITIONS.md A-3)

```latex
d_{i}=\Omega\left(a_{i},a^{0}_{-i}\right)-\Omega\left(a^{0}\right),\qquad D(a)=\sum_{i\in\mathcal{K}}d_{i}
```

**Native OMML — `interaction`** (label “Set”, SEC-METHOD-REWRITE.md eq. (4.8); SYMBOL-ADDITIONS.md A-4)

```latex
\Psi_{\mathcal{K}}=\Omega\left(a_{\mathcal{K}},a^{0}_{-\mathcal{K}}\right)-\Omega\left(a^{0}\right)-\sum_{i\in\mathcal{K}}d_{i}
```

**What each term is**

- The singleton increment moves exactly one user off the reference proposal and reads the whole-network residual change; the additive value of a set is their sum.
- The interaction residual is what the set achieves together beyond that sum. It costs one baseline, K singletons and one joint evaluation.
- So it is computed for a selected coalition of any size. Only the exact per-user Shapley split stops at four members; beyond that the receipt records it as not computed.

> The changed-user set carries a script subscript; its cardinality is the upright capital. The two are never interchanged.

**Speaker note.** This slide is the load-bearing replacement for the retired LC-SRS teacher pages.

---

## Slide 17 — The Exact Identity

**Disposition:** REWRITE of p.25 · **Badge:** `FROZEN` · **Layout:** math

*Conservation survives — on a set of any size, on the configuration residual.*

**Native OMML — `identity`** (label “Sum”, SEC-METHOD-REWRITE.md eq. (4.9); SYMBOL-ADDITIONS.md A-4)

```latex
\sum_{i\in\mathcal{K}}d_{i}+\Psi_{\mathcal{K}}=\Omega\left(a_{\mathcal{K}}\right)-\Omega\left(a^{0}\right)
```

**Status of the identity**

- Exact by the definitions of the singleton increment and the interaction residual. Nothing here is estimated.
- Verified by a known-answer test, not by appeal to simulator traces. A second test checks the same identity on the physical terms with the priced term removed.
- The V0.23 identity summed a local term and a half-interaction target over exactly two members. That statement retires with its terms.
- Numerical residual of the identity check: ⟨結果待填⟩.

> Construction-level exactness is a mathematical property. It is not evidence that coordination helps.

**Speaker note.** Draw the line: an exact identity is a bookkeeping guarantee, never a performance claim.

---

## Slide 18 — Three Routes, Restated

**Disposition:** REWRITE of p.8 · **Badge:** `SUCCESSION` · **Layout:** math

*Three surfaces remain; each names a different object than in V0.23.*

**Native OMML — `routes`** (label “Roles”, SEC-METHOD-REWRITE.md 4.3 (route roles))

```latex
C_{1}(a)=D(a),\qquad C_{3}(a)=\Psi_{\mathcal{K}}(a)
```

**Route roles**

- C1 is the additive singleton value of the changed set on the whole-network residual. C3 is the interaction residual — the part that is not additive.
- C2 is the declared continuation value and carries no current-step term. Its predictions use nominal geometry and nominal interference only.
- C2 judges survival at the focal user and is invalid whenever the solve is invalid, never filled with a surrogate. Unclipped power margin is reported even when negative.

> Three surfaces, three questions, one commitment. This is still not three agents, and still not a vote.

**Speaker note.** Reuse the V0.23 line that this is not a vote — still true, still the commonest misreading.

---

## Slide 19 — Why C3 Carries No Externality Term

**Disposition:** NEW (the e_i absorption) · **Badge:** `SUCCESSION` · **Layout:** cards

*The most consequential arithmetic change between the two versions.*

**V0.23: the externality was separate**

- C1 measured the focal user's own surplus against full network energy.
- A separate externality term measured the unilateral bit impact on everyone else.
- The C3 target was that externality plus half the two-user interaction.
- Coherent only because C1 was focal rather than network-wide.

**V0.25: the externality sits inside C1**

- The singleton increment is defined on the whole-network residual.
- It therefore already contains every non-focal user's bit and joule change.
- Carrying an externality term into C3 as well would be double counting.
- So the successor's C3 target is the interaction residual alone.

> Same three routes, different arithmetic: read any V0.23 C3 slide with this correction in hand.

**Speaker note.** One equation to take home: the externality term is absorbed, not deleted.

---

## Slide 20 — The Margin-Adjusted Selection View

**Disposition:** NEW (Δ9) · **Badge:** `SUCCESSION` · **Layout:** math

*Selection runs on causal information, and nominal gains carry no reserve.*

**Native OMML — `gammaq`** (label “Score”, SEC-METHOD-REWRITE.md eq. (4.10); SYMBOL-ADDITIONS.md A-1)

```latex
\gamma^{q}_{u,s,v}(t)=\frac{q^{\alpha}_{u,s,v}(t)\,H_{u,s,v}(t)\,G^{T}\left(\theta_{u,s,v},\theta_{3}\right)\,p_{u,s,v}(t)}{\sigma^{2}+I_{u,s,v}\left(t;\mathbf{p}\right)}
```

**Two construction constraints**

- The implementation margin cannot serve twice: counted into both the assumed threshold and the nominal set-point, it provides no fading reserve at all.
- First, the quantile never back-solves transmit power. Power stays nominal and the quantile enters only the wanted link's predicted receive side.
- Otherwise the link lands back on its threshold, and the margin buys only more power and more interference. Second, the quantile applies to the wanted link only.
- Applied to interference it would merely rescale noise. Name it exactly: a pre-specified tenth-percentile channel-gain scoring rule.

> Not a standard 90% availability convention — that phrasing is withdrawn. Level 0.10 is frozen; the sweep never selects it. Agreement: ⟨結果待填⟩.

**Speaker note.** The withdrawn availability phrasing is a disclosed correction; say it rather than let a reviewer find it.

---

## Slide 21 — Two Decompositions, Never Mixed

**Disposition:** NEW (two views) · **Badge:** `FROZEN` · **Layout:** cards

*Every reported quantity must name which of the two residuals it came from.*

**Selection-time view**

- Evaluated at the decision instant on the margin-adjusted nominal view.
- Power, interference and energy stay nominal; only the wanted link's predicted receive side is scaled.
- Service, mode, bits and energy are recomputed internally consistently in that view.
- Produces mechanism statistics only: selection-time increments and residuals, net collision-avoidance value, reversal frequency.

**Outcome view**

- Evaluated on the realised 48 boundaries.
- Produces labels, certificates and endpoints.
- The learned set-level head must state in writing which residual it estimates.
- Without that, replacing the exact residual with a learned estimate silently changes both the approximation and the target.

> No statistic may straddle the two views, and no reported number may leave its view unnamed.

**Speaker note.** This discipline is what keeps mechanism evidence from being read as performance evidence.

---

## Slide 22 — The Target / Transmit MODCOD Pair

**Disposition:** NEW (Δ2 accounting) · **Badge:** `SUCCESSION` · **Layout:** cards

*Three objects, reported separately for every user-step.*

**Target mode**

- The lowest mode meeting the rate target at the current occupancy.
- Its required SINR fixes the power set-point.
- It does not decide what is transmitted.

**Transmit mode**

- Chosen before transmission from the causally available margin-adjusted view.
- The quantile rule exists to give this choice the decoding reserve the implementation margin does not provide.

**Realised outcome**

- Bits credit at the transmit mode, and only if the realised SINR clears that mode's threshold. Otherwise zero.
- A failed higher-order frame is never re-decoded at a lower mode.
- Crediting a mode chosen from realised information is a defect to fix before the formal matrix.

**Speaker note.** Three objects, three receipt columns; conflating any two is the failure this page prevents.

---

## Slide 23 — Bounded Catalogue, Two-Stage Scoring

**Disposition:** NEW (Δ5 catalogue) · **Badge:** `SUCCESSION` · **Layout:** cards

*Selection approximates; the physics and the endpoints do not.*

**The catalogue**

- Full legal products are used only on synthetic worlds.
- Real worlds take a bounded union: per-user shortlist moves; pairwise joint moves over top-ranked users; a per-lit-beam evacuation set; and set-level proposals.
- A user with no legal candidate takes the null action and leaves the product; the catalogue never silently collapses to the reference proposal.
- Truncated coverage is reported: silence must never read as full coverage.
- Shortlist coverage and the best excluded margin: ⟨結果待填⟩.

**Two stages and a deadline**

- Stage one scores every row at the decision instant with that arm's own key.
- Stage two adds continuation values for the surviving rows, the proposal, the incumbent and every set-level proposal.
- Selection is an argmax within that set; commitment and endpoints are evaluated on the 48 boundaries.
- Budget is 10 s per anchor, cancelled by the executor, not the solver.
- On timeout the verified proposal executes; timeouts are a reported QoS field and their bits and energy still count.

**Speaker note.** The honest sentence: the approximation lives in selection only, never in the physics or the endpoints.

---

## Slide 24 — Per-Arm Sort Keys

**Disposition:** NEW (per-arm keys) · **Badge:** `FROZEN` · **Layout:** table

*Ranking every arm by the full score would restore the removed contribution.*

| Arm | Primary current-step key | Secondary key |
|---|---|---|
| FULL | Additive value plus interaction residual | Continuation value |
| DROP_C1 | Interaction residual only | Continuation value |
| DROP_C2 | Additive value plus interaction residual | Fixed deterministic rule |
| DROP_C3 | Additive value only | Continuation value |

> Pruning, feasibility guards and tie handling all use that same arm-specific key. Tie frequency: ⟨結果待填⟩.

**Speaker note.** One rule: no arm may rank, prune or veto using the score it has had removed.

---

## Slide 25 — Two-Layer Deployment

**Disposition:** REWRITE of p.27 — replaces DELETE p.32 · **Badge:** `SUCCESSION` · **Layout:** cards

*Per-user proposal, one set-level re-evaluation, exactly one commitment.*

**Layer one: proposal**

- Candidate table and native safe mask unchanged.
- Two per-user heads with frozen schemas give a masked per-user argmax.
- Neither schema holds recursive power, entry gain ratio or segment age.
- The proposal is then verified jointly legal; conflicts go to a declared repair rule.

**Layer two: selection**

- Sees global nominal geometry with per-beam cross gains, all legal sets, the incumbent, the proposal and the catalogue.
- Reads no realised fading, no future actions, no post-hoc state, no labels.
- Scores the catalogue and selects one configuration.
- The whole path is timed; on timeout the verified proposal executes.

**Commitment**

- One configuration is committed.
- Afterwards only that same action vector's physical receipt is recorded.
- No second argmax, no auction, no retry, no post-selection repair.
- The two references — proposal and incumbent — are never mixed.

**Speaker note.** The concession to state plainly: a coordinator now exists; what is preserved is single commitment.

---

## Slide 26 — Runtime Invariants, Restated Honestly

**Disposition:** REWRITE of p.33 · **Badge:** `SUCCESSION` · **Layout:** cards

*The V0.23 prohibition list claimed more than the successor can claim.*

**Withdrawn from the prohibition list**

- 'No coordinator of any kind.' The successor introduces a set-level layer, and that layer is under evaluation.
- 'No joint scoring of the roster.' The roster is exactly what the set-level layer scores.
- The V0.23 related-work sentence promising no additional coordinator retires with it.

**Still prohibited, and still load-bearing**

- No auction, bidding, token or negotiation round.
- No voting or consensus: the three routes are summed as evidence, never polled.
- No second argmax after commitment; no retry; no post-selection repair or heuristic override.
- No message passing between users at runtime.
- Set-level reasoning is bounded by a declared budget and a deadline with a verified fallback.

> Offline complexity, online single commitment: the slogan survives; the no-coordinator claim does not.

**Speaker note.** Correcting an over-claim in public is cheaper than having it corrected for you.

---

## Slide 27 — The Learned Interaction Head

**Disposition:** REWRITE of p.28 and p.29 · **Badge:** `SUCCESSION` · **Layout:** math

*C3 deploys as one permutation-invariant scalar head over the changed set.*

**Native OMML — `anchor`** (label “Zero”, SEC-METHOD-REWRITE.md 4.6; SYMBOL-ADDITIONS.md §2 (no hat, superscript f))

```latex
\Psi^{f}_{\varnothing}=\Psi^{f}_{\left\{u\right\}}=0
```

**Shape and feature sufficiency**

- Permutation-invariant pooling over the changed users' per-user vectors, concatenated with per-affected-beam global resource context, through a two-layer perceptron.
- The output is gated so that the empty set and every singleton score exactly zero by construction. No pair head, no allocation head, no positive-credit head.
- Feature sufficiency is not optional: the encoder must see pairwise cross-gain blocks between affected beams.
- A scalar interference summary is insufficient — it can hide precisely the difference that flips the coupled fixed point.

> Acceptance tightens accordingly: information twins must be separable in full context and provably inseparable without the cross-gain block.

**Speaker note.** V0.23's reference-centring is gone; the structural zero is now a gate, not a subtraction.

---

## Slide 28 — Learning and What C3 May Claim

**Disposition:** KEEP of p.9, p.30; REWRITE of p.14 · **Badge:** `FROZEN` · **Layout:** cards

*Three heads, three sources, one prohibition on gradient leakage.*

**How the heads are fitted**

- The two per-user heads are fitted by pairwise zero-bootstrap regression on typed deterministic batches.
- No target networks, no Polyak averaging, no recursive temporal estimates.
- The set-level head learns only from the residual target at the common scale.
- This is a supervised proxy estimate of a declared target, not a Bellman value, and the claim wording follows.
- No C3 loss updates the per-user heads, the native state, the mask, the topology or the simulator.

**What a learned C3 may claim**

- On the same exactly evaluated catalogue a learned selector cannot beat the exact selector on the same score.
- So three claims are admissible, each named before training.
- One: better realised closed-loop efficiency under model mismatch.
- Two: comparable decision quality at much lower measured computation.
- Three: a measurable residual task, such as reduced evaluation count.
- A learned escape over a wider neighbourhood is out of scope.

**Speaker note.** State the ceiling before the ambition: a learner cannot beat the exact optimiser it approximates.

---

## Slide 29 — Comparators

**Disposition:** NEW (comparators) · **Badge:** `FROZEN` · **Layout:** cards

*Configuration-level arms, and what each is allowed to certify.*

**Reference and exact**

- Reference proposal: per-user argmax of the two heads, verified jointly legal.
- It is the decomposition reference and the timeout fallback.
- Exact set selector: optimises the full score with the exact interaction residual over the catalogue.
- That is the exact upper form of C3.

**Learned and certified**

- Learned set selector: same guards, budget and fallback, with the learned residual. This is the deployable C3 layer.
- Certified unilateral optimum: exact best responses over the full legal set until no improving move remains.
- Without a full-neighbourhood termination certificate it is only a budget-limited comparator, and its contrast carries nothing.

**Mechanism, bounds, controls**

- Additive and interaction-aware picks share anchor, catalogue and rules, differ only in the score, and serve mechanism statistics only.
- Upper-bound arms: best single-user and best multi-user configurations under the exact residual.
- Controls: null, random feasible, nominal greedy, external baseline. Never factor arms.

**Speaker note.** The certificate distinction separates a Level A claim from a merely suggestive one.

---

## Slide 30 — Net Collision-Avoidance Value

**Disposition:** NEW (Δ10) · **Badge:** `RESULTS_PENDING` · **Layout:** math

*A mechanism certificate, reported with both untruncated components.*

**Native OMML — `upsilon`** (label “Value”, SEC-METHOD-REWRITE.md eq. (4.11); SYMBOL-ADDITIONS.md A-5)

```latex
\Upsilon=\frac{\Omega\left(a^{\psi}\right)-\Omega\left(a^{d}\right)}{\kappa}
```

**Native OMML — `upsilon2`** (label “Split”, SEC-METHOD-REWRITE.md eq. (4.12))

```latex
\kappa\,\Upsilon=\left[\Psi\left(a^{\psi}\right)-\Psi\left(a^{d}\right)\right]-\left[D\left(a^{d}\right)-D\left(a^{\psi}\right)\right]
```

**How to read it**

- Matched anchors, same catalogue and rules; only the score differs. A selector can avoid a large interaction loss while sacrificing more additive value, so both components are reported.
- Also reported: the reversal frequency, where additive value is positive but the corrected score is negative, and whether the layer prevented those reversals.
- The decomposition is reported twice — at the carrier proposal, and re-anchored at the certified unilateral optimum.

> Values, components and reversal frequency: ⟨結果待填⟩. A negative interaction total near the carrier is a loss absorbed there, not evidence against coordination.

**Speaker note.** A mechanism certificate; the operational certificate is realised efficiency against the certified comparator.

---

## Slide 31 — Named Experiments and Neutral Sources

**Disposition:** NEW — replaces DELETE p.35, 37 · **Badge:** `RESULTS_PENDING` · **Layout:** cards

*Four named experiments that are never presented as one another.*

**The four experiments**

- Learned neutral-source experiment — primary for all three route claims. Each arm replaces one route's source with a neutral source; every head is retained, updated and deployed.
- An all-neutral control and an external baseline sit alongside it.
- Oracle experiment with factorial score removal — the physical regime map.
- Checkpoint ablation — secondary; zeroes a deployed contribution.
- Architectural removal — named but not executed.

**Sealing and the zero result**

- Neutral sources are sealed before generation: generator, labels, support, strata, overlap, row weights, optimisation dose.
- 'Same batches across arms' means same within a route and source identity, nothing wider.
- Every drop checkpoint keeps all heads, and a neutrally trained head must differ from initialisation and actually deploy.
- A zero source margin is permitted and informative: it ends the positive claim for that route within this scope.
- Arm outcomes: ⟨結果待填⟩.

**Speaker note.** The pre-commitment that matters: a null result is an outcome, not a reason to re-open the design.

---

## Slide 32 — Claim Ladder and Admission

**Disposition:** REWRITE of p.38 — replaces DELETE p.36 · **Badge:** `RESULTS_PENDING` · **Layout:** cards

*One conditional intersection-union conjunction on the primary setting.*

**Claim ladder**

- Level B, primary: higher realised pooled efficiency for the set-level layer against the two-route policy, at equal information and budget.
- Describe it as a joint re-evaluation layer, never as coordination.
- Level A, secondary: also better than the certified comparator, with decision-relevant non-additivity. A learned Level B positive cannot establish Level A without certified evidence.
- Level C: the learned selector reaching the exact standard at lower computation.

**Admission trichotomy**

- ADMIT_FULL: all load-bearing certificates pass, including a decision-relevant interaction term.
- ADMIT_C1C2: as above but the C3 condition is unmet. Training is admitted; C3 enters as an evaluated layer lacking an oracle certificate.
- NOT_ADMITTED: the C1 oracle margin, or a QoS, validity or deadline condition, fails.
- Admission outcome: ⟨結果待填⟩.

> Missing the pre-specified margin means the benefit is not established — which is not the same as the effect being non-positive.

**Speaker note.** Read the footer verbatim; it is the distinction reviewers most often collapse.

---

## Slide 33 — Declared Idealisations of the Model

**Disposition:** NEW (declared idealisations) · **Badge:** `FROZEN` · **Layout:** cards

*Stated where the model is defined, not deferred to a footnote.*

**Application and orbits**

- Idealised atomic application: the chosen configuration is assumed to apply simultaneously and all-or-nothing.
- Standard mechanisms offer no such transaction, and partial completion can flip the sign of a planned evacuation.
- Retrospective reconstruction: element sets follow the nearest-epoch rule, future epochs permitted.
- Causal availability turns on receipt time, not on epoch sign; the rule is shared by all arms and labelled retrospective.

**Boundary and traffic**

- Partial-payload boundary: see the verbatim sentence and the non-cancellation argument.
- Not full payload DC efficiency, not space-segment efficiency, not end-to-end service efficiency.
- Full-buffer traffic: the numerator is saturated decodable throughput under rate-target power control.
- The rate target is a set-point, not a demand model, and realised rates may exceed it.
- Introducing finite demand later is a versioned model revision, never a relabelling.

> Each idealisation bounds how far a positive result could travel; none of them is a footnote.

**Speaker note.** Four idealisations, stated in place, each bounding the reach of any positive result.

---

## Slide 34 — Symbol Succession

**Disposition:** NEW (symbol succession) · **Badge:** `FROZEN` · **Layout:** table

*Read every V0.23 slide with this table in hand.*

| V0.23 symbol | Status | Successor and reason |
|---|---|---|
| Segment age, entry power | Retired | Memoryless power control keeps no cross-step state |
| Per-link efficiency display | Retired | Only the pooled ratio exists; per-row displays invite averaging errors |
| Local term, externality term | Retired | Replaced by the singleton increment on the whole-network residual |
| Interaction pair, C3 target, student label | Retired | Replaced by the set-level interaction residual and its normalised target |
| Per-user handover cost Ψ | Renamed Φ | Ψ is reserved for the interaction residual and always carries a script set subscript |
| Configuration surplus G | Renamed Ω | A superscripted G would collide with the gain family; Ω is freed by dropping scalarisation |

**Speaker note.** Close on the symbol table: the fastest way for a reader to re-date any slide they have seen before.

---
