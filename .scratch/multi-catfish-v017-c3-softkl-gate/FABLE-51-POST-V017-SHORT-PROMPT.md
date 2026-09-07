<role>
Act as a fresh, read-only scientific adjudicator. Do not edit, run simulation, train, or open TEST. The user cannot answer mid-task; finish the requested judgment autonomously.
</role>

<evidence>
Read only these local authorities:
- `docs/MULTI-CATFISH-MCRL-V09-INTEGRATED-ORACLE-DISPOSITION-2026-09-02.md`
- `artifacts/multi-catfish-v013-zr-c3-fresh-confirmation-20260903-r1/POST-OUTCOME-VERIFICATION.md`
- `artifacts/multi-catfish-v017-c3-softkl-gate-20260903-r1/contracts/MULTI-CATFISH-MCRL-V017-C3-SOFTKL-GATE-PREREG-2026-09-03.md`
- `artifacts/multi-catfish-v017-c3-softkl-gate-20260903-r1/server-run-r1/learner-gate/result.json`
- `src/mcrl/runtime/ee_axis_zero_marginal_c3.py`
- `src/mcrl/runtime/ee_axis_v016_c3_origin_state.py`
- `src/mcrl/runtime/ee_axis_b402_c3_softkl.py`
- `src/mcrl/algorithms/ee_axis_v014_head.py`
</evidence>

<facts>
V0.13 exact ZR oracle with Q1+exact O2 gave FULL-minus-DROP-C3 +0.9383% EE on four fresh TRAIN worlds; all worlds positive, service equal, bits -5.70%, energy -6.57%. V0.9 projected non-focal insertion externality gave -11.06% C3 and moved bits -5.40%, energy +6.37%, though its gate was later invalidated by two contract defects. V0.17 kept ZR but tried B402 plus full-action Soft-KL. All three initializations failed: pivotal agreement .149/.217/.429, stable preservation .978/.974/.894, supported changes .782/.743/.577. Frozen authority stops Soft-KL retry, tuning, and further B402 expansion. B402 aggregates over actions, while ZR sums candidate-specific effects over non-focal victims and conditions positive credits on an exact physical-compatibility indicator.
</facts>

<task>
Decide whether the next route should be: (A) a victim-relational/set Q3 that predicts per-victim action effects then applies the fixed ZR algebra; (B) a context-gated scalar Q3; (C) analytic decision-time Q3; (D) a new C3 target; or (E) structural stop. Explain whether V0.17 falsified ZR or only its B402 learner. Explain whether PNFE should be retried or is already adequately disfavored. Specify exactly one smallest fresh-TRAIN, source-only/no-episode pre-outcome gate, including frozen inputs, metrics, hard stops, and compute class. Keep exactly three independent Q heads, one common mask, unweighted Q1+Q2+Q3, one final argmax and one executed action. No sign flip, route weights, coordinator, second executed decoder, favorable seed/rung, threshold relaxation, or two-head fallback. Keep C1 and learned C2 frozen unless you identify a concrete causal defect.
</task>

<output>
Use clear headings and a compact route-ranking table. Label decisive claims Fact, Inference, or Proposal. End with exactly one token: `GO_RELATIONAL_ZR_GATE`, `GO_CONTEXT_GATED_C3_GATE`, `GO_ANALYTIC_C3_GATE`, `GO_NEW_TARGET_C3_GATE`, or `STOP_THREE_HEAD_STRUCTURALLY`.
</output>
