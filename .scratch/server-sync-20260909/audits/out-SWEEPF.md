Written to `/home/sat/mcrl-v025-strategic-fable-ws/SWEEP-fable-2026-09-10.md`. Nothing was modified elsewhere; one `nice -n 15` Python process was used for JSON reads and arithmetic only. Full text follows.

---

**The number now standing in for the owner's bar, FULLSPAN's `+17.03%`, is the ceiling of a realised-future oracle over a purpose-built catalogue measured from the raw carrier incumbent, on anchors where a non-learned unilateral search gains about `+400%` from that same incumbent and where the panel harness's own all-neutral arm gains `+409%`; its "C1/C2/C3" are not the contract's three routes (its C2 is an ACM-rung control term, not the persistence forecast), so training gate G1 is about to be evaluated on a decomposition of the wrong system, against a reference the controller's own arm-set record forbids as a stand-in, and would pass.**

# SWEEP — fable — 2026-09-10

Read-only. One `nice -n 15` Python process was used, for JSON reads and arithmetic only; no measurement was run; nothing under `/home/sat/mcrl-leo-handover` was touched. I did not read the astra workspace or any parallel sweep.

Evidence classes: **[V]** verified by me against code or a receipt I opened; **[P]** derived on paper from numbers in receipts; **[I]** inferred. No loss value is used as EE evidence anywhere.

## 0. What I opened

Controller records: all 90. Worker receipts: ORACLE-RESIDUAL-TOGGLE, ORACLE-FULL-SPAN, ORACLE-FACTORIAL (landed 08:41, after the last state record), C3-ARGMAX-REACHABILITY (+ `results.json`), MULTISTART-CEILING, MULTISTART-DEMAND-CAPPED, MODE-SELECTION-GAP, MODE-CAUSAL-REACHABILITY, CONTROL-LAW-CEILING, FAST-LOOK-*, RESEEDED-SPAN, ANYTIME-UNILATERAL, FINAL-BEAMWIDTH-CURVE, CEILING30-MARGIN, LADDER-FLOOR, OCCUPANCY-FLOOR, EVALPATH (+ `comparisons.json`), C3-PANEL-HARNESS (+ r8 `smoke.json`), PANEL-AUDIT-FABLE, MATCHED-ANCHOR-TIER, PILOT-MIN-REPORT, PREFLIGHT-DATA-CENSUS, EXACT-ROW-PATH-COST, C1C2-TARGET-DESIGN, CONTROL-CEILING-FRAMING, contract v1/v1.1/v1.2, declarations v1.6–v1.9, the five running jobs' specs, and the OBJMISMATCH dispatch prompt (recovered from the process table). Code: `run_oracle_residual_toggle.py`, `run_oracle_factorial.py`, `run_v025_pilot_c3.py:1495-1580`, SIGNFORK `run.py`, C3REACH `measure.py`.

Running at 08:44 UTC: OBJMISMATCH (4 h 40 m), CTRLCAP, C1REAL, SIGNFORK, EXACTGEN. None has written a report.

## 1. Q1 — numbers treated as evidence that are not, ranked by damage

### 1.1 `FULLSPAN` `+17.03%` whole-system span and its `+10.80%` additive component — most damaging

What it measures [V]: on 8 anchors (worlds 1–2, steps 0–3), the best row of a purpose-built 8,192-row catalogue (2,700 association singletons, ±1 ACM-rung control singletons, occupant bundles of size 2–4, beam evacuations, beam-wide and joint mode controls), chosen with a common exact-Fraction Dinkelbach price, where every candidate's score is its **realised 48-boundary outcome** (`run_oracle_residual_toggle.py:379-384`: `field="realised"`, `boundary_indices=BOUNDARIES` = 0..47), relative to the **raw carrier incumbent**.

What it is being used for: "FULL − BASELINE, against that bar" (STATE 07:45; REQUIREMENT-CHANGE).

Why that is a confusion, four independent ways:

- **Reference.** BASELINE is the geometry-only carrier assignment. Its per-anchor EE equals ANYTIME's MARGIN_Q base to four decimals at w1/s0, w1/s1 and w2/s1, and to 0.03% at w2/s0 [P]. From that same incumbent the non-learned first-improvement unilateral search reaches `+438%`, `+360%`, `+511%`, `+368%` on those anchors; FULLSPAN's entire ladder captures `3.1–5.0%` of that prize [P]. The ARM-SET record says neither the all-neutral control nor the geometry-only baseline "may silently stand in for the fixed point". FULLSPAN does exactly that.
- **The bar is vacuous at this reference.** In the r8 panel smoke, FULL − BASELINE is `+401.7%` and FULL − ALL_NEUTRAL_CONTROL is `−1.75%` [V, `smoke.json` `screen_by_provisioning_rule`]. The panel auditor traced the mechanism: `repair_reference` picks the exact-surplus whole-profile row (`s0-top-two`) for every arm, so all eight learned arms, including all-neutral, share one seed. "FULL − BASELINE substantial" is satisfied by a system with every head neutral-trained. The requirement as restated tests nothing about the routes.
- **Information.** The contract's coordinator sees the nominal model with no realised fading (§A2). FULLSPAN's selector sees the realised 48-boundary outcome of every candidate. That is the class the controller's own RESIDUAL-READING predeclaration excludes ("any oracle-only gain … that uses the realised fading draw"). The `+10.80%` "additive" is not the ceiling of an admissible C1 head; it is the ceiling of a clairvoyant single-move selector on this catalogue.
- **Catalogue.** No deployed arm uses this catalogue. The pilot's `_catalogue_with_census` (base, all unilaterals, two whole-profile proposals, ≤180 pairs, evacuations) and the matrix probe's `build_joint_candidates` (subsets ≤4, cap 4,096) are different objects with very different one-shot ceilings (see P2).

What survives: `+17.03%` is a true upper bound on any selector confined to this catalogue in a one-shot-from-carrier design. Nothing more.

### 1.2 `FACTORIAL`'s `C1_ONLY +10.80% / C2_ONLY +0.45% / C3_ONLY −0.06%` — reported 08:41; G1 will misread it

[V] `run_oracle_factorial.py:6,735`: C1 = atomic **association** deltas, C2 = atomic **adjacent-mode/control** deltas, C3 = residual. Contract §B4/§C2: C2 is the **persistence forecast** (`c2_persistence_forecast`, three future offsets). The factorial's C2 has no counterpart in the contract; the contract's C2 has no term in the factorial. Declaration v1.9 §5 already states the set-level C2 oracle marginal is zero by construction and that C2's certificate is forecast validity, not a selection marginal. `C2_ONLY +0.45%` is a number about ACM-rung controls; `FULL − DROP_C2 = 0.00%` says nothing about route 2.

[V/P] Every eligible row is association-only or control-only (factorial, "Exact construction"). Each arm's argmax is therefore the max over two disjoint row families, not a sum of contributions: `DROP_C3 = C1_ONLY`, `DROP_C1 = C3_ONLY`, `FULL = DROP_C2`, all byte-identical. The "route interaction" table is arithmetic over mutually exclusive families and cannot be read as synergy.

[P] `FULL − DROP_C1 = +17.10%` is a degeneracy artefact by the controller's own erratum-13 logic: `DROP_C1 − BASELINE = −0.06%`, so the reference arm fell below the incumbent (it ranks rows by residual alone). `C3_ONLY` negative means "ranking by residual alone is ill-posed", not "route 3 alone is harmful".

Consequence: G1 as written ("joint span substantial, and the report states which single-route marginals are positive") passes on this report. Training would be proposed on a factorial of the wrong routes, at a vacuous reference, with clairvoyant terms.

### 1.3 `C3REACH`'s `30.82 → 12.30 Mbit/J` (`−60%`) — the other half of the "contradiction"

[V] Selection at boundary 0 with the pilot's engine; exact Ψ from `_exact_interactions`. [V, EVALPATH] That function subtracts a scalar-path base from dense-path candidates; the base offset ε at 8 sampled anchors is −17.3 to +28.7 κ. [P] Ψ_A then carries `(|A|−1)·ε`; at |A| = 100 that is −1,700 to +2,800 κ. C3REACH's exact-Ψ full ranges are 128–5,421 κ; SELECTOR-DIAGNOSIS's Ψ at k = 100 is −440. Both sit inside the artefact envelope. Also UNDETERMINED [V: `results.json` carries no rule field; PANEL-AUDIT D5: the pilot-side physics lacks the fading-quantile margin]: which provisioning rule C3REACH ran under. The contradiction record lists worlds, catalogues, objective and residual object as candidate causes and omits both path mixing and physics version.

### 1.4 `RESIDTOGGLE`'s `+5.62%`

Same construction as 1.1: realised-future selector, purpose-built catalogue, 8 anchors, carrier reference. It is being read against the 10% and 5% screens as "the ceiling on what any C3 head can be worth inside the deployed selector". It is the ceiling of a clairvoyant residual on a catalogue no arm deploys. The 8/8 "selectors differ" is reachability of that construction, not of the contract's Ψ in the deployed catalogue.

### 1.5 `9.8698% / 3.5590%` multi-start headroom

[V] `9.87%` is under the SEALED (defective) rule; `3.56%` under MARGIN_Q. Both are per-anchor **best-of-8 random restarts plus one swap**, pooled: an order statistic. [V] Pooled same-index starts under MARGIN_Q: start 0 (nearest-eligible) is the best pooled column, 47.12 against at most 47.03 Mbit/J. A random restart is on average no better than the nearest start; only the per-anchor maximum is. This is the width of the local-optimum distribution, not headroom a policy can target. Quoting `9.87%` as "assignment headroom" imports the defective rule.

### 1.6 `+78.02%` causal mode selection

[V] One world, four anchors, the **carrier assignment** (`BASE:nearest-eligible`, 3.89 Mbit/J, 78.5% NO_MODE records). R2's decode failure conditional on selecting a mode is 44.3%. Relative gains on a 3.9 Mbit/J base do not transfer to the 43 Mbit/J fixed point where most NO_MODE records are gone; nothing was measured there. It also introduces a feedback channel (one-boundary-stale realised SINR) absent from §A2. "Identical joules to the bit" is true and irrelevant: the joules are those of the worst configuration.

### 1.7 `+119% / +134%` control-law best-known, and its predecessor `+113% → +0.273%`

[V] CONTROL-LAW-CEILING is a non-causal joint power/mode search with realised information, best-known and not a bound. Its STRICT gain is `+117.9%` bits with `−0.6%` energy, on anchors where 548 of 800 user-anchors already attain: the same shape that deflated `+113.4%` to `+0.273%` under the demand cap on two anchors. CTRLCAP is rescoring it now (prediction in §5).

### 1.8 Numbers that are being read correctly and should stay as they are

Reseeded span `+1.29%` (20 anchors) and `+0.899%` (8 anchors, strict, paired). The 30-date interval `[+0.436%, +0.997%]` is old-pairing and must not be cited as the corrected span's interval. Occupancy-floor `−7.66×` and ladder-floor `+6.36% → +0.51%` are clean negatives. The 128/128 two-swap result is scoped to one-boundary F.

## 2. Q2 — premises standing without verification, load-bearing first

**P1. "The deployed selector" is one object.** [V] It is at least four: (a) pilot `_select_for_anchor`, a catalogue argmax **from the carrier**, whose catalogue includes whole-profile `s0-top-two` rows; (b) `ProfileSelector.select` S3, an argmax over a supplied catalogue, where `repair_reference` has no production caller (MATCHED-ANCHOR-TIER); (c) the panel harness, first-improvement over single-user neighbours **from the repaired proposal** (PANEL-AUDIT D2/D3); (d) the matrix-probe joint selector, a bounded catalogue **seeded from the unilateral fixed point**. Records cite properties of each as "the system does X": the "about one per cent working range" (d), the `12–26 / 29–69 / 0` proposal changes (b, via a function only the panel harness calls), argmax reachability (a), and the degeneracy screen (assumes d). Erratum 15 corrected one instance; the pattern is general.

**P2. "The bounded catalogue" is one object.** Three, with one-shot-from-carrier ceilings of `+17%` (RESIDTOGGLE's), `+21.6%` (matrix probe's, PREFIX-ABLATION) and `+401%` (pilot's, because of its whole-profile rows; r8 smoke under SEALED physics, against `+664%` for the converged search). PREFIX-IS-THE-VALUE ("the raw geometric state does not expose a large one-catalogue learning band") is true of one catalogue and false of the one the pilot deploys. Both are receipts; the record generalises one of them.

**P3. "Exact terms" are the contract's targets.** [V] FULLSPAN/FACTORIAL terms are realised 48-boundary; the contract's C1 target and the pilot's selection are nominal boundary-0. Different objects; neither ceiling bounds the other.

**P4. FACTORIAL's C2 is route 2.** [V] False (1.2). The training-gate record cites `C2_ONLY` as a route marginal.

**P5. "The conditioning finding is untouched: +480.113 − 440.079 = +40.034, 22.99×."** [V EVALPATH] Produced by `diagnose_v025_selector.py`, which EVALPATH names as carrying the mixed boundary-policy error. The (|A|−1)·ε envelope at k = 100 (±1,700–2,800 κ) exceeds all three numbers. UNDETERMINED whether the cancellation is physics or path. The DECOMP bake-off's metric 1 uses 22.99× as its comparison scale, and my own DECOMP round 2 built on the same table.

**P6. "The learned interaction head is badly scaled" (2,518–11,205 against 107–264).** The head was trained on coalition rows that EVALPATH shows are path-mixed ("ψ additionally mixes scalar singletons with a dense joint"). Its scale may be a learned artefact. UNDETERMINED.

**P7. Three references in three records, all dated today.** "BASELINE is the committed nearest-eligible incumbent" (REQUIREMENT-CHANGE); "neither outer reference may stand in for the fixed point" (ARM-SET); "the reference is the certified unilateral fixed point" (DEGENERACY-SCREEN). The panel as built is seeded from the carrier and sits `+401%` above it; under a fixed-point reference every arm is "below reference", under the carrier the screen never bites (PANEL-AUDIT D1). The pre-declared screen cannot be applied to the pre-declared panel.

**P8. "C3 is reachable — settled by two independent routes."** RESIDTOGGLE's 8/8 is reachability of a clairvoyant residual in a catalogue with bundles and mode controls; C3REACH's 14/20 uses a path-mixed Ψ. Reachability of the contract's Ψ, path-consistent, in the deployed catalogue, under the nominal objective, has not been measured.

**P9. "The learned layer's entire working range is about one per cent."** True for (d); false for (a) and (c), where the per-user heads form the proposal and the working range is the whole unilateral prize. TERMINOLOGY and C1-IS-SEARCH-GUIDANCE describe different systems in consecutive paragraphs.

**P10. Erratum 13 ("+15.6% is a degeneracy signal because a ranker can add at most the span above the fixed point").** Valid only for arms seeded at the fixed point. The pilot's arms were seeded at the carrier; the `+15.6%` / `+45.6%` was a warm-up artefact for a different reason (THREE-LEARNER-DEFECTS). The erratum's logic, now embedded in the degeneracy screen, does not apply to the panel as built.

**P11. "No further gate of mine stands in front of the screen" (ACCOUNTABILITY) against G1/G2 (TRAINING-GATE, written later the same morning).** Two gates were added after that sentence.

**P12. ANYTIME's "88% of the prize at 30 s" is cited as closing the deadline route.** The pilot's whole-profile proposal row obtains roughly 60% of the SEALED prize in one evaluation pass (r8: `+401%` against `+664%`). The deadline question for a learned proposer was never posed against that comparator.

**P13. EXACTGEN's two cost measurements (57.79× and 132×) remain unreconciled.** The panel cost carried in records (29 h) is the low one; the harness's own projection is 185 worker-hours.

## 3. Q3 — is the three-route decomposition the right object?

Stepping outside the framing, the receipts describe layers of very different size, and the three routes do not map onto them.

| layer | measured size | produced by | route that owns it |
|---|---:|---|---|
| carrier → one-shot per-user best response (whole-profile row) | ≈ `+400%` [V r8, SEALED] | exact nominal surplus argmax, head-independent | none; C1/C2 heads can at best imitate it |
| one-shot → converged unilateral fixed point | remainder to `+664%` SEALED / `+451%` MARGIN_Q [V ANYTIME] | 45–65 s of search | none |
| fixed point → bounded joint optimum | `+0.9%` to `+1.3%` [V RESEEDED, FINAL-BEAMWIDTH] | exact set evaluation | C3's natural home |
| assignment-fixed control law (power/mode) | `+119%` capacity, best-known, non-causal; demand-capped unknown [V CTRLCEIL] | not in any route | none |
| route 2 (persistence) | never measured on EE; declared zero at set level by construction (v1.9 §5) | — | C2 |

So: the substantial EE lives in the per-user best-response step and in the control law, neither of which is a learned route; C3's physics-supported territory is about one per cent, consistent with the price-of-anarchy literature the controller cited; C2 has no EE measurement of any kind and the contract already predicts a zero selection marginal; C1's demonstrated value is as a proposal surrogate, where the exact nominal surplus already exists and is cheap enough to compute once per anchor.

Answer: the three-route conjunction is not the object the physics supports. It is the object the contract's ablation design supports, and the two have been conflated all day. The honest claims available today: (a) the exact ladder with intervals, correctly paired; (b) a per-user learned surrogate as **acceleration** of the unilateral search, with the comparator being the one-shot exact proposal row and the 10-s anytime incumbent (contract v1.2 item 3(ii)); (c) a set-level correction of about one per cent, reported as such; (d) the control law as the diagnosed location of the large headroom, with a demand-capped number once CTRLCAP reports. What cannot be claimed today: that any route raises EE relative to neutral-source training. That contrast has still never been run.

## 4. Q4 — predicted next overturnings, ranked, with checks under an hour and no new compute

1. **G1 passes on FACTORIAL and training is proposed.** Mechanism: 1.2. Check: diff the route definitions at `run_oracle_factorial.py:735` against `targets.py:251` and v1.9 §5; re-word G1 to name the estimand and the reference before reading. Done above.
2. **The owner's restated bar is met by ALL_NEUTRAL_CONTROL.** Mechanism: repair picks the exact whole-profile row for every arm. Check: r8 `smoke.json`, FULL − ALL_NEUTRAL `−1.75%`, FULL − BASELINE `+401.7%`. Already in hand. The bar must be restated relative to the all-neutral control or the head-independent proposal, or it measures nothing.
3. **+480 / −440 / +40 and the 22.99× cancellation are path artefacts.** Mechanism: 1.3, P5. Check: for one SELECTOR-DIAGNOSIS anchor, take ε from EVALPATH's `comparisons.json` (serialised for 8 anchors), multiply by 99, compare to Ψ(k = 100). Ten minutes. If |99ε| is of the order of |Ψ|, the DECOMP bake-off scale and erratum 15's "untouched" clause fall.
4. **SIGNFORK is read as "objective mismatch, repairable".** Mechanism [V `run.py:218-248`]: its "pooled EE" column is `field="realised"`, 48 boundaries, Dinkelbach; its "pilot" column is nominal boundary-0, fixed price. Price, horizon and field move together. A positive residual only in the realised column means "C3 helps a clairvoyant selector", the unfavourable reading. A nominal-field 48-boundary Dinkelbach column would be needed to separate price from foresight; the spec has none.
5. **The degeneracy screen disqualifies every arm or none.** Mechanism: P7. Check: the r8 receipt with reference = carrier (no arm below); the same receipt against U (SEALED `+664%`) puts all nine below. Arithmetic. Either the reference must match the arms' seed or the arms must be reseeded from the fixed point.
6. **CTRLCAP deflates the control-law headroom the way FAST-LOOK did.** Mechanism: STRICT gain is 99% bits, 1% energy; 68% of user-anchors already attain. Prediction: STRICT demand-capped gain in the low single digits or less; SEALED larger because 0/800 attained. Do not quote `+119%` before it reports.
7. **The multi-start 3.56% is quoted as learner headroom.** Check: the same-index pooled column, already in the receipt. Order statistic, not policy headroom.
8. **The 30-date interval is quoted for the corrected span.** It is old-pairing; the correctly paired corrected span has no interval. Check: CEILING30-MARGIN method section. Fix: re-pair on existing receipts if endpoints were stored, else about ten core-hours.
9. **EXACTGEN's reconciliation lands near 132×.** Consequence: panel cost is about 185 worker-hours plus training, not 29. Check: EXACTGEN's Part 1 reconciliation, which its spec requires printed before generation.
10. **C3REACH ran on pre-margin physics.** Check: `measure.py` imports `pilot.ENGINE._setting("a-r0")`; compare the pilot engine's `acm.py` and `batch.py` digests against the sealed copies (PANEL-AUDIT D5 lists the diff). Fifteen minutes.

## 5. Pre-declared readings for the running measurements

**OBJMISMATCH** (O1–O4, 20 anchors, both rules).

- If a single-user move improves the reported objective at most endpoints: the fixed point is a local optimum of the proxy, not of the reported objective. Read O3's span as the room available to a **realised-future** search. Do not read it as room for a causal head, do not add it to `1.29%` or `17.03%`, do not call it "the association layer's room". [V dispatch prompt: O1–O3 evaluate the reported objective, i.e. realised 48 boundaries.]
- O4 attributes the discrepancy to price or horizon. "Horizon" in the prompt means 48 realised boundaries; if horizon carries it, the mismatch is foresight and is not repairable by re-pricing. Only a price-carried discrepancy is repairable causally (a Dinkelbach price on the nominal model). Ask which field O4's 48-boundary arm uses before reading it.
- If endpoints are already local optima: confirms about one per cent for the association layer on the matrix-probe design. It does not confirm RESIDTOGGLE, which has a different catalogue and reference.
- Mistake to avoid: reading O2 ("the selector's choice is not the catalogue's best under the reported objective") as evidence about C3. It is evidence about the objective.

**C1REAL** (declared C1 target, exact path, LOAO/LOWO, widened and high-capacity heads, 16 slots).

- Read ranking metrics (within-anchor ordering, top-1 agreement), not R². LOWO is the metric that matters for a date/world panel.
- High-capacity ordering below about 0.70 on LOWO: informational ceiling; G2 fails; the route as a surplus predictor is not learnable from these 16 slots. High-capacity clearly above linear: architectural.
- Mistake 1: reading G2-fail as "route 1 is dead". C1's demonstrated value is the proposal, where the exact nominal surplus is computable; a poor surplus predictor can still be an adequate proposal ranker. Mistake 2: reading any C1REAL number against FULLSPAN's `+10.80%`, a realised-outcome ceiling of a different quantity. Mistake 3: treating two worlds as an interval.

**EXACTGEN** (exact-path corpus, cost reconciliation, C1 gauge, decomposition, correlation, argmax disagreement).

- The cost reconciliation is the deliverable that changes decisions; read it first and re-cost the panel from the harness's own formula.
- Argmax disagreement between surrogate and exact labels: small disagreement does not rehabilitate the surrogate corpus (a small label change can flip a per-user argmax over 27 options); large disagreement does not show the exact target is better for EE.
- Mistake: treating an exact-path corpus as the panel's physics. PANEL-AUDIT D5: the source-side physics differs from the sealed realised evaluator in nine files and the tapes have different digests. The corpus is exact on one physics and will be evaluated on another until that is unified.
- A partial prefix of the 180-anchor order is usable only as a prefix; fit nothing to it.

**SIGNFORK** (world 3, 8 anchors, pilot catalogue, corrected provisioning, exact additive terms, 2×2 price × gate).

- It reproduces neither RESIDTOGGLE (catalogue) nor C3REACH (learned additive scores, pilot physics, path-mixed Ψ). Read it as a third measurement, not an adjudication.
- Residual positive in the realised-Dinkelbach column and negative or null in the nominal-boundary-0 column: the residual helps only with foresight. This is the reading that makes the work harder and must be reported as such, not as "objective misalignment, repairable without touching the routes".
- Both columns positive: the C3REACH sign came from its own construction (learned additive scores, physics version, or the path artefact); the discriminating follow-up is a path-consistent Ψ on C3REACH's anchors, not another world.
- Both columns negative: the exact residual hurts on the deployed catalogue under both objectives; RESIDTOGGLE's `+5.62%` is then a property of its catalogue's bundles and mode controls.
- Gate factor: on this catalogue contexts exist for every |A| ≥ 2 row [V `run_v025_pilot_c3.py:1508-1512`] and the residual is identically zero on singletons, so gated and ungated should coincide [P]. A non-null gate effect is a finding about the gate's implementation, not about C3. A null gate effect must not be read as "C3 reaches everything".
- A second-world cell is permitted by the spec only for a world-dependent disagreement; do not select it on outcome.

**FACTORIAL** (reported 08:41). Reading rules in 1.2. Report it as "association-move / mode-control / residual factorial on RESIDTOGGLE's catalogue, realised-outcome oracle, carrier reference"; never as C1/C2/C3; never as G1 input for route 2; `FULL − DROP_C1` is a below-reference artefact.

**CTRLCAP** (not among the brief's five, but running). Read the demand-capped STRICT gain only, with served and attainment beside it; do not carry the capacity `+119%`.

## 6. UNDETERMINED, with the evidence that would settle each

- Whether Ψ(k = 100) = −440 and the 22.99× ratio are physics or the (|A|−1)·ε path artefact: one anchor, base re-evaluated through `evaluate_many`, Σd and Ψ recomputed.
- Which physics and provisioning C3REACH ran under: digest comparison of the pilot engine's `acm.py` and `batch.py` against the sealed copies.
- Whether the learned Ψ head's 10–100× scale is learned from path-mixed labels: one seed retrained on path-consistent coalition rows (compute; not urgent until the first item is settled).
- The deployed catalogue's one-shot ceiling under corrected physics with a path-consistent exact Ψ: SIGNFORK's nominal column partially answers it.
- FULL − ALL_NEUTRAL_CONTROL at convergence and at panel scale: the §C3 contrast, never run.
- Whether the corrected span has an interval: 30-date re-pairing.

## 7. Ledger

**[V]** FULLSPAN/FACTORIAL evaluator field and boundaries; factorial route definitions and row-family exclusivity; SIGNFORK column fields; pilot selector argmax from the carrier and its context gate; r8 smoke contrasts; C3REACH selection and committed boundary sets and the absence of a rule field; EVALPATH's base-offset range; ANYTIME, RESEEDED and FULLSPAN per-anchor baseline identity; MULTISTART same-index pooled columns; MODE-CAUSAL's base configuration and failure rates; the three references named in three records.

**[P]** FULL as a fraction of the unilateral prize per anchor; the (|A|−1)·ε envelope; the family-argmax explanation of the byte-identical factorial arms; gate-factor nullity on the pilot catalogue.

**[I]** That the r8 seed-collapse mechanism persists at convergence and at scale; the CTRLCAP prediction; that the learned head's scale is an artefact.
