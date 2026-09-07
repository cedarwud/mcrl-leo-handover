# Role

You are a fresh, read-only scientific reviewer. Use only file-view operations. Do not edit files, use shell, run simulations, train models, or access TEST. You have a limited action budget of 8 file reads; use them efficiently.

# Evidence

Read these absolute local paths:

1. `/home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-v013-zr-c3-fresh-confirmation-20260903-r1/POST-OUTCOME-VERIFICATION.md`
2. `/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-MCRL-V09-INTEGRATED-ORACLE-DISPOSITION-2026-09-02.md`
3. `/home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-v017-c3-softkl-gate-20260903-r1/contracts/MULTI-CATFISH-MCRL-V017-C3-SOFTKL-GATE-PREREG-2026-09-03.md`
4. `/home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-v017-c3-softkl-gate-20260903-r1/server-run-r1/learner-gate/result.json`
5. `/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_zero_marginal_c3.py`
6. `/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/ee_axis_v014_head.py`
7. `/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_v016_c3_origin_state.py`

Known facts: exact ZR oracle improved EE by +0.9383% across four fresh TRAIN worlds; projected PNFE previously gave -11.0636% C3 but its run was contract-invalid; V0.17 B402+Soft-KL failed all three initializations. The frozen V0.17 authority retires retries/tuning/B402 expansion. A separate fresh reviewer proposes keeping ZR and replacing the action-set MLP by one victim-relational Q3 that predicts candidate-to-victim effects, pools over victims, applies the fixed ZR algebra, and Main-centers its 28-action surface.

# Question

Based on the preceding information, try to falsify that proposal. Decide whether V0.17 primarily falsifies the ZR target, the available state, the action-set architecture, or only the loss. Compare victim-relational ZR against a context-gated scalar Q3, analytic Q3, new target, and structural stop. Recommend exactly one smallest fresh-TRAIN source-only gate before episode training. Preserve exactly three independent Q heads, one common mask, unweighted Q1+Q2+Q3, one final argmax, one executed action, and ratio-of-sums EE. No sign flip, route weights, coordinator, seed/rung shopping, weaker thresholds, or two-head fallback.

Label claims Fact, Inference, or Proposal. End with exactly one token: `GO_RELATIONAL_ZR_GATE`, `GO_CONTEXT_GATED_C3_GATE`, `GO_ANALYTIC_C3_GATE`, `GO_NEW_TARGET_C3_GATE`, or `STOP_THREE_HEAD_STRUCTURALLY`.
