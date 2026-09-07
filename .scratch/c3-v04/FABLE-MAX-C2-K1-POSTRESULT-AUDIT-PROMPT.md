<role>
Act as a fresh-context scientific algorithm reviewer for a Multi-Catfish MCRL
research project. Do not inherit the controller's prior optimism or pessimism.
This is a read-only diagnosis and redesign review. Be concise but decisive.
</role>

<documents>
Read the following local authorities and receipts before answering:

1. `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md`
2. `docs/MULTI-CATFISH-MCRL-V06-C2-K1-T1-PREREG-2026-09-01.md`
3. `docs/MULTI-CATFISH-MCRL-V06-C2-K1-BOUNDED-LEARNER-PREREG-2026-09-02.md`
4. `docs/MULTI-CATFISH-MCRL-V06-C2-K1-PAPER-FIGURE-DELTA-2026-09-02.md`
5. `docs/MULTI-CATFISH-MCRL-V05-C2-CONTROLLED-TAPE-DISPOSITION-2026-09-01.md`
6. `docs/MULTI-CATFISH-MCRL-V04-C2-FAILURE-FORENSICS-2026-09-01.md`
7. `artifacts/multi-catfish-v06-c2-k1-bounded-screen-20260902-r1/freeze/formal-verdict/formal-verdict.json`
8. `artifacts/multi-catfish-v06-c2-k1-bounded-screen-20260902-r1/freeze/train-q13-a/train-result.json`
9. `artifacts/multi-catfish-v06-c2-k1-bounded-screen-20260902-r1/freeze/train-q13-b/train-result.json`
10. `artifacts/multi-catfish-v06-c2-k1-bounded-screen-20260902-r1/freeze/train-q13-c/train-result.json`
11. `artifacts/multi-catfish-v06-c2-k1-bounded-screen-20260902-r1/freeze/design-eval/evaluation-result.json`
12. `artifacts/multi-catfish-v06-c2-k1-bounded-screen-20260902-r1/freeze/design-eval/evaluation-seal.json`
13. `.scratch/c3-v04/run_v06_c2_k1_bounded_learner.py`
14. `src/mcrl/runtime/ee_axis_v06_c2_k1_learner.py`
15. `src/mcrl/algorithms/ee_axis_v06_c2_k1.py`

The merged source file is about 172 MB. Do not read it wholesale. If a source
statistic is necessary, use a narrowly targeted read-only script against
`artifacts/multi-catfish-v06-c2-k1-t1-source-gate-20260902-r1/merged/source.json`.
</documents>

<verified_result>
The sealed receipt has already been independently reauthenticated:

- T1 source gate disposition:
  `AUTHORIZE_ONE_BOUNDED_C2_K1_LEARNER_SCREEN`.
- Three independent Q2 lineages completed exactly 100 updates, 336 rows each.
- DESIGN-EVAL: 10 matched worlds x 3 lineages x FULL/DROP_C2, 60 rows.
- FULL pooled EE: 75,438,916.32270679 bit/J.
- DROP_C2 pooled EE: 105,620,395.14331958 bit/J.
- FULL minus DROP_C2: -28.57542691414722%.
- Positive lineages: 0/3; positive worlds: 0/10.
- Service noninferiority: failed; nonnegative service lineages: 2/3.
- G-L passed; G-E and G-S failed.
- Mean action-flip rate: 0.7607.
- Median absolute Q2-to-(Q1+Q3) surface magnitude: 4.023230155521755.
- No TEST split, episode training, retry, replacement, or 9000-episode run.
- Formal disposition: `C2_K1_LEARNER_NOT_CONFIRMED`.

This is a genuine negative learned-deployment result, not a launch failure.
</verified_result>

<invariants>
The final scientific objective is the unchanged canonical network
ratio-of-sums energy efficiency. The intended method must retain exactly three
Catfish training mechanisms, exactly three Q surfaces, and one final safe
argmax that executes one Main action. C1 and C3 are currently frozen positive
candidates. C2 remains mandatory; deleting it or silently keeping a harmful Q2
is not acceptable. There is no post-training auction, coordinator, vote, or
second agent. Apart from the EE definition, the C2 target, causal view, state,
source, learner calibration, and principled pre-argmax composition may be
redesigned if scientifically justified. Clearly flag any recommendation that
requires relaxing the current direct unweighted `Q1+Q2+Q3` sum.
</invariants>

<task>
Explain why C2 has remained unresolved across several designs despite repeated
claims of physical opportunity. Distinguish these possibilities using the
receipts and code rather than intuition:

1. Q2 scale dominance or output-unit miscalibration;
2. first-successor surrogate reversal against 10-step ratio-of-sums EE;
3. insufficient C2 state/source support for deployment action ranking;
4. 100-update overfit or loss/gauge behavior;
5. a FULL/DROP_C2 implementation error;
6. a deeper incompatibility between an independently learned temporal head and
   direct additive three-Q deployment.

Decide whether the evidence still supports a realistically achievable C2 that
improves EE, rather than merely saying it is theoretically possible. If yes,
give the simplest next C2 design precisely enough to implement: public target
formula, causal state/view, source pairs, loss/calibration, and how it enters
the one argmax. Prefer a mechanism that remains a genuine third Catfish, not a
hidden coordinator or a renamed C1/C3 duplicate. If no current design is
credible, say so and state the falsification boundary.

Also determine whether a post-hoc scalar sweep on the already opened 10 worlds
would be invalid outcome tuning. If scaling is worth testing, specify a new
pre-registered fresh-world experiment that avoids that bias.
</task>

<output>
Return these sections only:

1. `Bottom line` -- what happened and why C2 has taken so long.
2. `Cause ranking` -- ranked causes with direct file/receipt evidence and a
   falsifiable prediction for each.
3. `Is a useful C2 still realistic?` -- calibrated probability range and what
   evidence supports it.
4. `Recommended C2 vNext` -- one primary design and at most one fallback,
   including equations and deployment composition.
5. `Minimal next evidence` -- smallest pre-registered diagnostics/pilots, their
   wall-time class, and exact pass/fail gates before any 1500/3000/9000 EP run.
6. `Retain versus invalidate` -- which V0.6 assets remain valid and what must be
   archived as a falsified candidate.

Support consequential claims with file paths and line numbers or exact receipt
fields. Do not edit files, launch training, or create new outcome artifacts.
When you have enough information to decide, decide.
</output>
