# Role

Act as a fresh-context principal scientific reviewer. Audit the current Multi-Catfish C3 evidence before any Q3 learner gate or episode training. Your task is adjudication, not implementation.

# Required outcome

Determine whether the evidence supports a bounded revision of the nominal/learnable Q3 representation, requires redesigning the R3/C3 target itself, or exposes a more fundamental defect in the repriced Q1+Q2+C3 design. Identify any deep blind spot that could make the current positive oracle result a false green.

# Read first

- `artifacts/multi-catfish-c3-fable-cleanroom-20260904-r1/FABLE-C3-SOURCE-AUDIT.md`
- `.scratch/multi-catfish-v020-c3-source-audit/REPRICED-C3-LAMBDA-CONFOUND-GATE-CONTRACT-2026-09-04.md`
- `.scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md`
- `.scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-REPRICED-SUPERVISED-EXECUTION-CONTRACT-2026-09-04.md`
- `.scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/merged/result.json`
- `artifacts/multi-catfish-v020-repriced-c3-gate-20260904-r1/server-run/result/result.json`
- `artifacts/multi-catfish-v020-repriced-c3-gate-20260904-r1/server-run/independent-verification.json`
- `artifacts/multi-catfish-v020-repriced-c3-gate-20260904-r1/server-run/RESULTS.sha256`
- `.scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate.py`
- `.scratch/multi-catfish-v020-c3-source-audit/verify_v020_repriced_c3_gate.py`
- `src/mcrl/runtime/ee_axis_relational_zr_c3.py`
- `src/mcrl/runtime/ee_axis_zero_marginal_c3.py`
- `src/mcrl/runtime/ee_axis_zero_marginal_c3_live.py`
- `src/mcrl/runtime/ee_axis_v018_gate.py`
- `src/mcrl/algorithms/ee_axis_relational_zr_c3_head.py`
- `src/mcrl/algorithms/ee_axis_relational_zr_c3_head_v019.py`

Inspect individual shard receipts only as needed to authenticate or challenge an aggregate claim.

# Facts that must be independently checked, not merely repeated

- Repriced BASE pooled EE is about 114.906 Mbit/J.
- EXACT_ZR is about +0.985% pooled, positive in 3/3 lineages and 4/4 worlds, with unchanged served fraction.
- NOMINAL_ZR is about +0.424% pooled but positive in only 2/3 lineages and 3/4 worlds, so it fails the frozen stability gate.
- The Q1 and Q2 repricing exercise establishes source reconstruction/learnability only; it does not establish episode-level EE efficacy.

# Questions to adjudicate

1. Is the repriced comparison scientifically valid for the stated causal question, including the fixed-lambda/Dinkelbach sign argument, matched worlds, common keyed fading, action construction, aggregation, service guard, and absence of TEST leakage?
2. Does EXACT_ZR's positive result establish a distinct and defensible C3 physical mechanism, or can it still be explained by an artifact of joint action enumeration, compatibility gating, beam shutdown, or oracle access unavailable to Q3 at deployment?
3. Does NOMINAL_ZR's mixed stability isolate a representation/selection problem, or is there evidence that the R3/C3 target or Catfish mechanism itself remains wrong?
4. Examine cross-head identifiability and double counting. Can Q1, Q2, and C3 plausibly remain three distinct training-time views whose summed deployment score improves final ratio-of-sums EE, or is C3 stealing/relabeling energy effects already priced by Q1/Q2?
5. Identify false-green risks: weak or source-only Q1/Q2 backgrounds, oracle-to-policy gap, seed/world count, reuse or selection of development worlds, normalization/calibration, action-set mismatch, hidden post-selection, per-world instability, and any contract/implementation discrepancy.
6. Decide the smallest high-information next gate. Do not prescribe long episode training unless the evidence already supports it.

# Boundaries

- Read-only. Do not edit files, run simulation, train learners, use the TEST split, tune parameters, or create new authority.
- Treat all present numbers as development evidence, never efficacy or held-out proof.
- Do not reward complexity. Prefer the simplest next gate that distinguishes representation failure from target failure.
- Preserve the user's invariant: exactly three Q networks and three Catfish training mechanisms, all aimed at final EE; no deployment auction, coordinator, or extra agent.
- Separate verified fact, inference, and proposal. If evidence is insufficient, say exactly what is missing.

# Output

Lead with a direct verdict. Then provide:

1. authenticated evidence and any discrepancy;
2. the strongest interpretation that survives the audit;
3. the three most serious remaining blind spots, ranked;
4. one bounded next gate with a pre-outcome acceptance contract, explicit arms/contrasts, minimum evidence needed, and compute class;
5. what must not yet be claimed in the paper.

End with exactly one token:

`GO_NOMINAL_Q3_REVISION_GATE`

`REDESIGN_R3_TARGET`

`REOPEN_Q1_Q2_BACKGROUND`

`INVALIDATE_REPRICED_GATE`

`STOP_THREE_CATFISH_STRUCTURALLY`
