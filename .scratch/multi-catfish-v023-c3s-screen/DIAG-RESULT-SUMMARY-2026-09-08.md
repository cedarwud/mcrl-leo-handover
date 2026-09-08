# diag2 result summary — attribution of the C3-S v1 gain (controller, 2026-09-08, server clock ≈ 16:40 UTC)

Source: 27 immutable unit receipts under `diag2-run-{main-none,main-ablate_anchor,null-none}/units/*/receipt.json` (4 TRAIN worlds × 3 lineages × 30 steps, 100 users; all units EXIT=0), aggregated independently by `/home/sat/diag2_summary2.py` (pooled ΣB/ΣE per arm vs the unit-paired BASE; the runner's own merge reports are produced separately by the chain).

## Numbers (pooled EE vs BASE; units with positive paired gain / 12)
| arm | physics `none` (anchored, as in v1) | physics `ablate_anchor` (p⁰ reset removed) |
|---|---|---|
| LITE (deployable set-level decoder) | **+2.922 %** (12/12); bits +1.55 %, joules −1.33 %, lit beams 40.6 vs 41.2, ≈ 2.0 users changed vs BASE per step | **+2.894 %** (12/12); bits +1.68 %, joules −1.18 %, lit beams 40.7 vs 41.2 |
| BASE_FORCED_RENEW_4 (renew every association aged ≥ 4) | +0.494 % (11/12); bits −0.36 %, joules −0.85 % | **+0.000 % — bit-identical to BASE** (3 027 renewals executed) |
| RANDOM_RENEW (one random re-association per step) | −1.117 % (0/12) | −1.253 % (0/12) |
| NULL (full C3-S code path committing BASE's choice; 3 units) | **90/90 steps bit-exact with BASE → harness OK** | — |

LITE's advantage by dwell-refresh phase (step mod 4): anchored 0:+1.36 %, 1:+1.70 %, 2:+3.86 %, 3:+9.84 %; ablated 0:+1.36 %, 1:+1.73 %, 2:+4.00 %, 3:+9.03 %.

## Verified facts
1. The renewal premium exists and is entirely the segment-anchor artefact: forced renewal gains +0.49 % under the anchored physics and exactly nothing once the p⁰ reset is removed.
2. LITE's gain is **not** the renewal premium and not churn: it is unchanged (+2.92 % → +2.89 %) without the anchor, random re-association is negative in both settings, and LITE executes zero explicit renewals.
3. LITE's gain is selective consolidation with more delivered bits: ≈ 2 % of user decisions per step differ from BASE, fewer beams are lit, bits rise, served users are identical.
4. The harness placebo holds (NULL ≡ BASE bit-exact), so the C3-S code path itself adds nothing.
5. The phase-monotone slope is not an anchoring effect (it persists under ablation). The cadence audit (`C3S-CADENCE-AUDIT-2026-09-08`) verified that BASE and LITE both decide at every step under the same candidate constraints; the remaining difference is information/computation: LITE evaluates complete configurations with exact current-slot nominal joint physics, BASE applies learned per-user Q surfaces with lagged/frozen-background interaction features.

## Inference (not yet verified)
The gain is either (b) genuine set-level multi-user coordination, (d) exact current-slot rescoring of single-user alternatives (an exact evaluator beating the learned heads), or a mixture. The v1 selection census (305 evacuation-labelled vs 55 unilateral-labelled LITE profiles) leans towards (b) but does not measure causal share. diag3 (`DIAG3-MECHANISM-SEPARATION-DECLARATION-2026-09-08.md`, running) separates them with the already-implemented `LITE_UNILATERAL_ONLY` / `LITE_EVACUATION_ONLY` arms under both physics settings; reading rules were declared before launch.

## Status of the v1 claim
C3-S v1 (+2.88 % FULL / +2.92 % LITE, TRAIN panel, development evidence) is now attributed away from the two artefact hypotheses (renewal premium, churn) and from a harness defect; it is not yet attributed between coordination and exact rescoring. It remains development evidence in the legacy physics; the V025 successor matrix decides the regime for the real claim.

## Addendum (17:10 UTC) — astra adjudication and runner cross-check
- Astra independently decoded all 27 receipts and reproduced the table (LITE +2.921776 % / +2.893833 %; forced renewal +0.494376 % / exactly 0; random −1.116708 % / −1.252791 %; NULL 90/90). Its corrections are accepted: the result shows anchor-independence, not blanket artefact exclusion; under ablation LITE's energy advantage is exactly its 177 fewer beam-slots at 6.266 W each (activation is the only energy lever of the legacy model); the diag3 ⅔/⅓ reading is withdrawn (see the diag3 declaration addendum) and mechanism attribution moves to the V025 runner (singleton/interaction decomposition, Δ_joint, `S_UNI` comparator, deadline rule).
- The runner's own NULL merge reports `C3S_DIAGNOSTIC_INCOMPLETE missing_units=9` because the merge authority expects 12 units while the NULL check was declared on 3; the placebo verdict rests on the per-unit `--assert-null-equals-base` (all EXIT=0) and the independent per-step comparison (90/90).
- Astra priors before diag3: mixed 45 %, exact rescoring 40 %, multi-user coordination 15 %.

## diag3 interim (physics `none`, 12/12 units; `ablate_anchor` half still running; 18:36 UTC) — catalogue sufficiency only (reading declared before any unit was read)
| arm (catalogue) | pooled EE vs BASE | bits | joules | changed users / step | fraction of LITE's +2.922 % |
|---|---|---|---|---|---|
| `LITE_EVACUATION_ONLY` (BASE + evacuation rows, incl. singleton evacuations with broad destination search) | **+2.950 %** (12/12) | +1.45 % | −1.45 % | 2.05 | 1.01 |
| `LITE_UNILATERAL_ONLY` (BASE + one Q-ranked alternative per user) | **+2.100 %** (12/12) | +0.46 % | −1.60 % | 1.00 | 0.72 |
Phase slopes: evacuation-only 0:+1.32 → 3:+10.05 % (same as LITE); unilateral-only 0:+1.20 → 3:+5.87 %. Harness: diag3 BASE ≡ diag2 BASE, 360/360 steps bit-exact.
**Reading (sufficiency, not mechanism):** the evacuation catalogue alone is sufficient for the whole LITE gain; exact rescoring of a single Q-ranked alternative per user already retains ≈ 72 % of it with one changed user per step. Because evacuation rows include broader single-user search, the ≈ 28 % remainder is an upper bound on what multi-user moves could add in this catalogue, not a measured coordination share. Consistent with astra's priors (exact-rescoring-dominant or mixed); the successor's matched-anchor singleton/interaction decomposition is the instrument that separates them.

## diag3 final (24/24 units; both physics; 20:34 UTC) — catalogue sufficiency
| arm | `none` pooled EE vs BASE (share of LITE's +2.922 %) | `ablate_anchor` (share of +2.894 %) |
|---|---|---|
| `LITE_EVACUATION_ONLY` | +2.950 % (1.01), 12/12 | +2.873 % (0.99), 12/12 |
| `LITE_UNILATERAL_ONLY` | +2.100 % (0.72), 12/12 | +2.046 % (0.71), 12/12 |
Phase slopes unchanged in shape (evacuation-only ≈ LITE's; unilateral-only about half the phase-3 gain). Harness: diag3 BASE ≡ diag2 BASE 360/360 steps in both physics. Reading: the evacuation catalogue is sufficient for the whole LITE gain in both physics; one exactly re-scored alternative per user retains ≈ 71–72 %; no mechanism share is claimed (see the diag3 declaration addendum). Legacy diagnostics end here.
