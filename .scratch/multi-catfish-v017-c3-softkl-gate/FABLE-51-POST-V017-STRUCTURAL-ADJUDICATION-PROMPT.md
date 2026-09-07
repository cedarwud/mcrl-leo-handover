<role>
You are the independent clean-room scientific adjudicator for one narrow design decision in a Multi-Catfish MCRL research codebase. The user is not watching and cannot answer mid-task. Work autonomously to the requested deliverable, but remain read-only: do not edit files, run a simulator, generate sources, train a learner, open TEST data, or launch a background process.
</role>

<goal>
Determine the single best next C3 design route after the completed V0.17 gate, without repeating a retired mechanism under a new name. Separate target/estimand failure, observation insufficiency, learner-architecture mismatch, loss mismatch, and interaction with Q1+learned-Q2. Recommend exactly one smallest pre-outcome falsification gate; do not authorize episode training.
</goal>

<authority_and_evidence>
Read these local files before judging. Treat contracts and result JSON as project evidence, not efficacy claims.

1. `artifacts/multi-catfish-v017-c3-softkl-gate-20260903-r1/contracts/MULTI-CATFISH-MCRL-V017-C3-SOFTKL-GATE-PREREG-2026-09-03.md`
2. `artifacts/multi-catfish-v017-c3-softkl-gate-20260903-r1/server-run-r1/learner-gate/result.json`
3. `.scratch/multi-catfish-v017-c3-softkl-gate/monitor/final-verification.json`
4. `docs/MULTI-CATFISH-MCRL-V09-INTEGRATED-ORACLE-DISPOSITION-2026-09-02.md`
5. `docs/MULTI-CATFISH-MCRL-V09-INTEGRATED-ORACLE-PREREG-2026-09-02.md`
6. `docs/MULTI-CATFISH-MCRL-V012-ZERO-ENERGY-C3-ORACLE-PREREG-2026-09-03.md`
7. `docs/MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md`
8. `artifacts/multi-catfish-v013-zr-c3-fresh-confirmation-20260903-r1/server-run/merged/result.json`
9. `src/mcrl/runtime/ee_axis_zero_marginal_c3.py`
10. `src/mcrl/runtime/ee_axis_v014_q3_state.py`
11. `src/mcrl/runtime/ee_axis_v015_c3_state.py`
12. `src/mcrl/runtime/ee_axis_v015_c3_reference_state.py`
13. `src/mcrl/runtime/ee_axis_v016_c3_origin_state.py`
14. `src/mcrl/runtime/ee_axis_b402_c3_softkl.py`
15. `src/mcrl/algorithms/ee_axis_v014_head.py`
16. `gpt-dr.md`, especially lines 454-684.

Also inspect V0.14-V0.16 result JSON files only as needed to distinguish the repeated failure mode:
- `artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/result.json`
- `artifacts/multi-catfish-v015-c3-reference-gate-20260903-r1/server-run-r3/learner-gate/result.json`
- `artifacts/multi-catfish-v016-c3-origin-gate-20260903-r1/server-run-r1/learner-gate/result.json`
</authority_and_evidence>

<verified_starting_facts>
- V0.13 unchanged ZR oracle beat DROP-C3 by +0.938285% pooled over four fresh TRAIN worlds, with positive world directions in 4/4, 11/12 lineage directions positive, equal service, total bits lower by about 5.70%, and total energy lower by about 6.57%. This is oracle-development evidence only.
- V0.9 projected non-focal externality (PNFE) produced FULL-minus-DROP-C3 = -11.0636%, reduced bits by 5.3951%, and increased energy by 6.3736%. The run was formally invalidated by a diagnostic-action mismatch and a t=0 warm-start opening-service mismatch; it remains a strong diagnostic against blindly rerunning the same PNFE formula.
- V0.14-V0.17 all kept the V0.12/V0.13 ZR physical teacher while trying successively different state context and/or objectives. V0.17 retained B402 and used masked full-action Soft-KL.
- V0.17 completed and independently verified. At 3000 updates all three initializations failed. Full-context pivotal agreement was 0.1490, 0.2173, 0.4289 (required >=0.50); stable preservation was 0.9779, 0.9743, 0.8941 (required >=0.95); supported changes were 0.7820, 0.7425, 0.5769 (required >=0.80). The frozen decision is `FAIL_SOFTKL_GATE` and next authority `STOP_C3_B402_ACTION_SHARED_STRUCTURALLY`.
- V0.17 forbids Soft-KL retry, seed/rung selection, threshold relaxation, rescaling, clipping, support masking, and further B402 feature expansion. A genuinely different target or architecture remains admissible only under a new pre-outcome contract.
- B402 scores each action with a shared local MLP using that action's 14 features, 10 globals, and legal-set featurewise mean/max. It has no victim-set encoder and no explicit pairwise candidate-to-victim interaction representation.
</verified_starting_facts>

<questions>
1. Is the evidence strongest for (A) ZR target is sound but not representable by B402/action-shared MLP, (B) ZR target is itself too context-dependent/nondeployable, (C) the loss family is still the primary issue, or (D) the three-head requirement is structurally implausible? Rank these with evidence.
2. Is the PNFER/PNFE proposal in `gpt-dr.md` scientifically distinct enough from V0.9 to justify another oracle gate? Identify exact differences. If its core causal intervention is already falsified by V0.9, say so.
3. Compare these structural routes: victim-set encoder/DeepSets or attention Q3; a context-conditioned two-stage residual/gating Q3; an analytically computed decision-time Q3 rather than a learned Q-network; a redesigned current-slot target; projected PNFE retry; or another route you can derive from the EE physics. Respect the user's invariant of exactly three independent Q heads, one common mask, unweighted Q1+Q2+Q3, one argmax, one executed action, and final ratio-of-sums EE.
4. Recommend exactly one next gate that is cheaper than episode training and can falsify the chosen structural route. Freeze its inputs, fresh TRAIN split, metrics, thresholds, hard stops, and expected compute class. Do not tune against V0.17 outcomes.
5. State whether C1 and learned C2 should remain frozen during this gate and why.
</questions>

<constraints>
- The only final objective is canonical ratio-of-sums EE. C3 need not improve a legacy r3 metric.
- Do not weaken the requirement that FULL must beat each drop arm eventually; do not propose two-head retirement.
- Do not propose sign reversal, route weights, coordinator, auction, veto, second deployment decoder, post-training correction, favorable seed/rung selection, or reuse of TEST.
- A target may be negative in raw value; the issue is action ordering and positive EE marginal after Main-centering and integration.
- Label every important statement as verified fact, inference, or proposal.
- Distinguish oracle viability, source learnability, short-episode direction, and held-out efficacy.
</constraints>

<output>
Return a concise but technically complete adjudication with:
1. verdict on why V0.17 failed;
2. a table ranking at most four live structural routes;
3. exact comparison of PNFE V0.9 versus any proposed projected route;
4. one selected next route and one pre-outcome gate;
5. an explicit list of retired actions;
6. one final decision token chosen from `GO_VICTIM_SET_C3_GATE`, `GO_CONTEXT_GATED_C3_GATE`, `GO_ANALYTIC_C3_GATE`, `GO_NEW_TARGET_C3_GATE`, `STOP_THREE_HEAD_STRUCTURALLY`.

Do not use mannered prose or repeat the evidence table verbatim. Cite local paths and JSON field names for decisive claims.
</output>
