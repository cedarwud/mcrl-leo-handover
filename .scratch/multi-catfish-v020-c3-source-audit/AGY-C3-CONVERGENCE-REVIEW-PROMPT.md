# Role

You are an independent fresh-context scientific reviewer. Perform a read-only convergence review of the current Multi-Catfish C3 branch. Do not implement anything.

# Evidence

Read these files from `/home/u24/papers/mcrl-leo-handover`:

- `artifacts/multi-catfish-c3-fable-cleanroom-20260904-r1/FABLE-C3-SOURCE-AUDIT.md`
- `.scratch/multi-catfish-v020-c3-source-audit/REPRICED-C3-LAMBDA-CONFOUND-GATE-CONTRACT-2026-09-04.md`
- `.scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/merged/result.json`
- `artifacts/multi-catfish-v020-repriced-c3-gate-20260904-r1/server-run/result/result.json`
- `artifacts/multi-catfish-v020-repriced-c3-gate-20260904-r1/server-run/independent-verification.json`
- `src/mcrl/runtime/ee_axis_zero_marginal_c3.py`
- `src/mcrl/runtime/ee_axis_relational_zr_c3.py`
- `src/mcrl/algorithms/ee_axis_relational_zr_c3_head_v019.py`

The authenticated development result is: EXACT_ZR versus repriced Q1+Q2 BASE is +0.985% pooled EE, positive in 3/3 lineages and 4/4 worlds; NOMINAL_ZR is +0.424% pooled but positive in only 2/3 lineages and 3/4 worlds. No Q3 learner, episode training, TEST, or held-out efficacy exists. Fable recommends exactly one additional EXPECTED_ZR deployable-information oracle ceiling gate before a Q3 learner gate.

# Question

Based on the preceding evidence, decide whether:

1. the C3 physical target/mechanism is stable enough for the paper while only its deployable estimator remains open;
2. Fable's EXPECTED_ZR gate is necessary and high-information, or an over-cautious detour that can be replaced by a simpler source-and-learner gate;
3. the positive EXACT_ZR result could still be a false green caused by oracle information, compatibility gating, joint beam shutdown, double counting with Q1/Q2, or weak source-only Q1/Q2 backgrounds;
4. paper work can safely freeze the high-level C3 role now, and exactly which formula/pseudocode claims must remain provisional.

Use no more than 18 file-view/search actions. Do not use web search, shell execution, simulation, training, TEST, tuning, or file edits. Separate verified fact, inference, and recommendation. Do not equate development evidence with efficacy.

# Output

Return a concise review with:

- direct verdict;
- strongest surviving interpretation;
- top three blind spots;
- one smallest next gate, including pass/fail rule and whether it is heavy or non-heavy;
- paper-stable versus paper-provisional boundary.

End with exactly one token:

`RUN_EXPECTED_ZR_GATE`

`GO_DIRECTLY_TO_Q3_LEARNER_GATE`

`REDESIGN_C3_TARGET`

`REOPEN_Q1_Q2_FIRST`
