# Multi-Catfish C3 Astra Pro clean-room review package

Package date: 2026-09-05 (Asia/Taipei)  
Scope: current three-head feasibility, C3 deployable-estimator fork, and the minimum path to short episode training  
Evidence ceiling: TRAIN/development only; no efficacy claim, no held-out TEST, no learned Q3

## Read first

This is the pass-2 synthesis file. A genuinely fresh reviewer must begin with `PASS1-READ-FIRST.md` and record its provisional account before reading this file.

The project requires exactly three Q networks and exactly three training-time Catfish mechanisms. All three serve one final objective: Main-only ratio-of-sums energy efficiency (EE). Deployment performs one native masked argmax of `Q1 + Q2 + Q3`. There is no Catfish deployment agent, auction, vote, coordinator, joint decoder, or post-training override. Legacy `r2/r3` metrics need not improve.

The desired empirical ordering is ultimately:

`FULL > DROP-C1, DROP-C2, DROP-C3 > BASELINE`

with sensible pairwise/two-head behavior and a service guard. That ordering is a research target, not a fact or mathematical guarantee.

## Current verified picture

| Route | What is currently supported | What is not yet supported |
|---|---|---|
| C1/Q1 | Repriced source-fit skill is positive in 3/3 initializations; route is focal current-slot own-rate plus marginal-energy surplus | Positive learned physical EE marginality |
| C2/Q2 | H-A/OPS-3 projected-persistence oracle family has strong positive C2 direction in Stage 1b; latest source-fit skill is positive in 3/3 initializations | Learned Q2 physical EE marginality; held-out efficacy; service guard was not perfectly clean in Stage 1b |
| C3/Q3 | After coherent Q1/Q2 repricing, pathwise EXACT_ZR improves development EE by +0.985325%, positive in 3/3 lineages and 4/4 worlds with unchanged service | NOMINAL_ZR failed V0.20 stability; conditional EXPECTED_ZR then failed the frozen V0.21 fast screen; no deployable or learned Q3 is validated |

V0.20 pooled values are 114.906263 Mbit/J for BASE, 116.038463 for EXACT_ZR, and 115.393571 for NOMINAL_ZR. EXACT loses 5.32% delivered bits while saving 6.24% energy. The defensible mechanism description is therefore a spatial resource-sharing / joint beam-consolidation opportunity dominated by denominator-side savings, not proven interference relief.

The old V0.3 documents in `contracts/00-*` and `contracts/01-*` are historical formula context. Their old C3 formula and exact three-route bookkeeping identity are not current proof and must not override the newer evidence.

The packaged C2 report also records that historical source-closure rechecking failed and was not required for that receipt-level screen. Therefore C2 claims in this upload are receipt-level development directions, not a fresh source-closure proof.

## V0.21 resolved fork

V0.21 asked whether the conditional expectation of the complete nonlinear exact ZR label, computed only from deployable predecision information and independent integration fading fields, retains useful action-specific value under independent evaluation fields.

The bounded fast screen uses one fresh TRAIN world, one lineage, one initial anchor, K=8 integration draws, and L=8 evaluation draws with arms:

- B: Q1+Q2 background;
- N: existing nominal-ZR approximation;
- E: privileged pathwise exact-ZR diagnostic;
- R: conditional-expected ZR;
- P: score-permutation action-specificity control.

The independently verified frozen decision is `STOP_EXPECTED_ZR_FAST`:

- B = 129.793009 Mbit/J;
- privileged pathwise E = 129.911956 Mbit/J, or +0.091643% versus B;
- deterministic N = 128.837148 Mbit/J, or -0.736451%;
- conditional-expected R = 129.272913 Mbit/J, or -0.400712%;
- permuted control P = 128.554178 Mbit/J, or -0.954467%.

R changed 8 of 100 actions, beat B on only 2/8 independent evaluation fields, and failed `R > B`; all mechanics and the service guard passed. All five arms had identical pooled energy at this anchor, so the ordering came entirely from delivered bits. K=4 and K=8 actions agreed for 95% of users, which argues against simple Monte Carlo instability as the whole explanation.

This one-anchor TRAIN result is rejection-oriented triage, not efficacy and not proof that every spatial C3 is impossible. Under the frozen contract it terminates the current NOMINAL/EXPECTED-ZR estimator family and reopens the R3 target/identifiability question. It does not authorize another tuned ZR variant on the same outcome.

## Known blind spots the reviewer must not merely repeat

1. EXACT sees pathwise execution fading; deployable observations do not.
2. Unilateral positive rate credit can produce simultaneous beam shutdown and energy saving even though that shared saving is absent from the individual label.
3. Common units and reference centering make score addition legal but do not prove additivity, calibration, or monotonic marginal benefit.
4. Q1/Q2 source prediction is not learned physical EE evidence.
5. Existing relational Q3 heads gate positive contribution before reference centering; without a final support clamp, an incompatible action can become positive after centering. V0.21 mechanics adds that clamp, but no learner has yet adopted or passed it.
6. Four worlds are four world clusters, not twelve independent worlds just because three lineages are crossed with them.

The requested fresh review should go beyond this list and actively identify missing questions, mistaken abstractions, invalid stop rules, or a simpler causal route that the current team has overlooked.

## Recommended reading order

To preserve fresh-context value, begin with `PASS1-READ-FIRST.md` and use two passes.

Pass 1 — independent reconstruction:

1. `PASS1-READ-FIRST.md`
2. `EVIDENCE-MAP.md`
3. `evidence/03-v020-independent-verification.json`
4. `evidence/02-v020-repriced-c3-result.json`
5. `evidence/04-repriced-q1-q2-source-fit.json`
6. `evidence/05-c2-stage1b-report.md`
7. `contracts/02-v020-repriced-c3-contract.md`
8. `contracts/03-v021-expected-zr-fast-contract.md`
9. `evidence/09-v021-fast-screen-result.json`
10. `evidence/09b-v021-fast-screen-independent-verification.json`
11. Source files when checking a concrete causal or leakage claim

Pass 2 — cross-model challenge:

12. `START-HERE.md`
13. `CROSS-MODEL-STATE.md`
14. Reviewer files `evidence/01-*`, `evidence/08-*`, `evidence/10-*`, and `evidence/11-*`

Record the pass-1 provisional verdict before pass 2. Prior reviews are not authority.

Use exactly one of the two prompts at package root. The ordinary Q&A prompt is package-only adjudication. The Deep Research prompt adds primary external literature and must keep project facts separate from literature-based inference.
