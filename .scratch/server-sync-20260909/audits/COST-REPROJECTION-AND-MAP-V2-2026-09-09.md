# Addendum to the map — three items from the audit index, one of them decisive

The audit-report survey returned after I published. It corroborated most of the map, but it carried **one finding I did not have and which outranks everything in my ranked list**. I verified it against the stage-4d snapshot before writing this. The map above stands except as amended here.

## New: VERIFIED V74 — the credited ACM mode is selected from the *realised* post-fading SINR

`ACM-CAUSALITY-AUDIT-2026-09-09.md` returns `ACM_CAUSAL=NO | M_TARGET_VS_M_TX=SAME | DECODE_RESERVE=ZERO`. I re-derived it in `mcrl-v025-stage4d-snapshot-20260909` and it holds:

- `physics_v025/acm.py:135-141` ✓ — `ACMRate.rate_bps(sinr_linear, …)` calls `select_mode(sinr_linear)` and credits `bandwidth_hz * mode.spectral_efficiency`. The credited mode is whatever the SINR it is *handed* supports.
- `physics_v025/resolution.py:123-128` ✓ — what it is handed is `transmission.sinr`, the resolved SINR after realised fading. The comment at `:129-130` confirms the design intent ("an unsuccessful attempt continues to interfere and consume exactly the energy already scheduled") — but there is no unsuccessful *decode*, because the mode adapts to the outcome.
- `physics_v025/batch.py:354-361` ✓ — the vectorised path does the same: `eligible_modes = sinr[:,:,None] >= thresholds`, `argmax` over efficiencies, `chosen_efficiency * BEAM_BANDWIDTH_HZ`.

**There is no transmitted-mode object anywhere in the credited-rate path.** `m_target` sizes the power; the credited `m_tx` is re-derived post-hoc from the realised SINR, so a fade never produces an outage — it produces a lower-order mode with full credit. Combined with `acm.py:33` / `:72`, which build the threshold with `+ IMPLEMENTATION_MARGIN_DB` and test against `threshold_db − IMPLEMENTATION_MARGIN_DB`, the 1.7 dB margin cancels on both sides and the decode reserve is exactly zero.

The audit further reports that target-infeasible users transmit at the 1.65 W cap, are permanently `rate_target_feasible=False`, and **still receive full genie-ACM bit credit while remaining in every availability denominator**; beam capacity 618.476 Mbit/s, feasible to n = 12, infeasible for all users at n = 13. I did not independently re-derive those four numbers.

**Consequence, in the audit's own words: bits and pooled EE fall by roughly 2–3× under the fix, and the `a-r` vs `b` ordering is not safe until re-run.** That is a sign-changing defect on the primary endpoint — it satisfies every clause of the design-freeze admissibility test `[FZ 2]` and must be acted on before the matrix.

**This is the same hole as O24, seen from the other side.** The ACM audit's prescribed fix is "add a separately declared fading reserve (~3.7 dB for 90 %)". Declaration v1.9 §1–§3's α = 0.10 quantile *is* a 90 % reserve on the wanted link — and I verified it has no implementation in any snapshot. So the sealed scientific rule and the measured engine defect are pointing at one missing object: **a predicted-reception reserve that is distinct from the power-sizing target.** Closing O24 correctly closes O33; closing either one badly leaves the endpoint genie-optimistic.

## New OPEN items

- **O33 — ACM is non-causal; the endpoint credits genie mode selection.** Owner: engine stage 4e/4f + controller (it changes a sealed physical quantity, so it is not an engineering fix). Guard: materialise `m_tx` from the nominal SINR, decode against `threshold(m_tx)` alone, add the v1.9 reserve as the *only* margin in the predicted-reception path, and re-run the `a-r` vs `b` ordering. **blocking-matrix**
- **O34 — audit-closure integrity.** `STAGE4D-AUDIT` rebuts the stage-4d report's own closure claims for rows 17, 20–23, 25, 27, 29, 31, 36, and the tautological-KAT count moves 15 → 2 only by removing 15 and substituting 2 self-fulfilling replacements. `[FZ 1]` freezes the design when 4g "passes its audit", so the meaning of *passes* is now load-bearing. Owner: controller. Guard: 4g's audit reports closure per row with the discriminating test named, and the controller adjudicates rebutted rows explicitly rather than by count. **blocking-matrix**
- **O35 — a real formal outcome was opened on `V025_PROBE/world/1` before the declared seals.** Pipeline audit C records it from a provider log: bits `138034644600.74075`, joules `6255.138642826578`, served `100`. The pilot-track declaration acknowledges this obliquely ("world 1 was opened before sealing") and quarantines it, but no record adjudicates the lost freshness. Owner: controller/seal assembler. Guard: the allocation manifest names world 1 as consumed and the claim panel demonstrably excludes it. **blocking-matrix**

## Corrections to the map above

- **R37 softened — cause identified, finding retained.** The audit index shows five distinct source trees in circulation (`stage2-snapshot`, `codex-ws-engine`, `codex-ws-provider`, `codex-ws-stagec`, `stage4d-snapshot`), with the same logical file at different line numbers in each — e.g. the S3 authentication defect moves `deployment.py:525` → `:675` between stage-C build 2 and build 3. So `[D-CO 1(a)]`'s `learner.py:1027,:1034` is **tree drift, not a fabricated citation**. It remains a defect of the record — those lines resolve to unrelated code in the only snapshot supplied, and a reader cannot check the decision — but the correct disposition is an erratum binding the citation to a named tree and digest, not a retraction. This strengthens the case for O28.
- **The map's method note was, if anything, understated.** No citation in this corpus is safe without its tree. Any future map should carry `tree@digest:file:line`, not `file:line`.

## What this does not change

**Task 1 stands unaltered.** The ACM defect changes the *value* of bits and pooled EE, not the *cost* of computing them: the catalogue size, the coordinator call count, the epoch budget, the batch rows and the fork accounting are all untouched. If anything it adds work — the prescribed fix introduces a second mode selection and the v1.9 quantile lookup into the per-decision path, which pushes the mean solve time *t* up, in the direction that already dominates the evaluation projection.

**Revised counts.** Three new OPENs, all blocking-matrix; one new VERIFIED; R37 reworded, not withdrawn.

MAP: VERIFIED=53 REFUTED=41 DECIDED=55 OPEN=28 BLOCKING_MATRIX=12 BLOCKING_TRAINING=8

**Revised top of the ranked list.** O33 displaces O24 at rank 1 — not because O24 is less important, but because O33 supplies the failing measurement that makes O24 actionable under `[FZ 2]`, and it names the certificate whose sign is at risk: the S0-realised-gain-over-BASE ≥ +1 % condition in `ADMIT_FULL`, which a 2–3× shift in pooled EE can invert.
