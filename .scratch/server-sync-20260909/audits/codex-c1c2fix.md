You are auditing and repairing a feature-encoder defect in the MCRL LEO handover project. Workspace: /home/sat/mcrl-v025-c1c2suff-ws (a clone; the sealed clone /home/sat/mcrl-leo-handover must never be modified, but its interpreter /home/sat/mcrl-leo-handover/.venv/bin/python is the one to use, with PYTHONPATH=src and `nice -n 15`).

## What is already established (do not re-derive)
A prior diagnostic in this same workspace produced C1C2-SUFFICIENCY-2026-09-09.md. Read it first. Its findings:
1. Two admissible network states have byte-identical 16-scalar Q1 and 22-scalar Q2 rows but exact C1 targets 11/10 vs -33/10.
2. A REAL legacy-tape witness (V025_PROBE/world/1, step 0, user 6, action (65028,44), anchors 0 and 1) has byte-identical Q1/Q2 but exact C2 targets 5.4095145 vs 19.3466970. In that witness the exact projection has survives=0 at offset 1 for state A and survives=1 for state B, yet the stored 22-scalar Q2 says valid and surviving at all three offsets in BOTH rows. There are 62 such exact C2 collision groups among just those two anchors.
3. Held-out k-NN on the current encoders: C1 explained variance -0.3355 (worse than the mean), C2 0.2107. Given the discarded target-defining terms, an OLS readout reaches EV = 1.0 with coefficients +/-1.

## The trap you must not fall into
Finding 3's EV = 1.0 is TAUTOLOGICAL. The C1 target is defined as ((B_cand - B_def) - eta*(E_cand - E_def))/kappa + (Phi_cand - Phi_def). Regressing it on B_cand, E_cand, Phi_cand, B_def, E_def, Phi_def recovers its own definition. Those quantities are the OUTPUT of the expensive coupled evaluation of the candidate action; the head exists precisely to predict them cheaply BEFORE that evaluation is run. Adding them to the encoder would be leakage, not a repair, and would make the learner useless at deployment.

So the governing constraint for every feature you propose is:

**ADMISSIBILITY: a feature is admissible only if it is computable from the pre-decision network state and the focal candidate action alone, without evaluating the candidate configuration's coupled power fixed point or its whole-network outcome, and without any label, oracle, or future information.**

State this constraint at the top of your report and justify EVERY proposed feature against it individually, in a table, naming the function that computes it and its inputs.

## Tasks

### Task A — is the C2 survival flag an encoder bug rather than a sufficiency gap?
Determine precisely why the stored Q2 says surviving at all three offsets while the exact projection says survives=0 at offset 1 for state A. Read the encoder in src/mcrl/stagec_v025/state.py and the projection code that the exact target uses. Answer, with code citations and a minimal reproduction:
- Does the encoder compute a DIFFERENT survival predicate than the target's, or does it compute the same predicate on different inputs, or does it overwrite/default the flag?
- Is the absorbing rule (once survives=0, later offsets are losses) applied in the target but not in the encoded row?
- Classify the result as ENCODER_BUG (the encoded row misreports a quantity it already has) or SUFFICIENCY_GAP (the quantity is genuinely absent) or BOTH, and give the count of affected rows over the two anchors you can reach cheaply.
If it is an ENCODER_BUG, that is the single most important sentence in your report; lead with it.

### Task B — the minimal admissible feature set
For C1 and for C2 separately, propose the SMALLEST set of admissible features (as defined above) that breaks the published collision witnesses, i.e. makes the two colliding states encode to different rows. For each:
- give the exact definition and the production function that supplies it;
- verify against the admissibility constraint;
- state whether it breaks witness 1 (C1 constructed), witness 2 (C2 real), or both, and show the two now-different encoded values.
The C1 witness differed in background association topology, focal cross gains, and background coupled powers. Those are pre-decision state and are therefore candidates. Do not propose more than you need; a large encoder is not the goal, identifiability is.

### Task C — does the repair actually buy predictive power?
Re-run the held-out diagnostic (scripts/diagnose_v025_c1c2_sufficiency.py, seed 20260909, same by-physical-step split: train 1,2,4,6,7,8,9; validation 5; test 0,3) with the encoder extended by your Task B features ONLY. Report the same table: Q-only held-out EV and RMSE for C1 and C2, before and after. Also report a LEAKY upper reference row computed with the tautological target-defining terms, clearly labelled `LEAKY_REFERENCE_NOT_DEPLOYABLE`, so the reader can see where the admissible repair sits between the current encoder and the ceiling.
If the admissible repair moves EV very little, say so plainly. A negative result here is more valuable than an optimistic one, because it would mean the target is genuinely unpredictable from pre-decision information and the whole per-user head design is in question. Do not tune features to improve the number; propose the set once on identifiability grounds, measure it, and report what you get. If you want to measure a second variant, declare both variants BEFORE measuring either, and report both.

### Task D — consequences
State, in at most 200 words each:
- whether C1 and C2 can be expected to raise pooled energy efficiency with the current encoder;
- what the minimum change to the training pipeline would be to adopt your Task B features, listing files and whether any sealed artefact or frozen manifest would need to change (if any would, say so and STOP there; do not modify it).

## Rules
- `DIAGNOSTIC_NOT_CLAIM`. No training run is authorised. No production run is authorised.
- Never modify /home/sat/mcrl-leo-handover or its venv.
- Do not change any threshold, sign, seed, horizon, price, service guard or acceptance rule. Do not touch PILOT_PRIMITIVE_SOURCE_FALLBACK (leave it True).
- Use exact Fraction arithmetic where the existing target code does.
- If a task is infeasible in the time you have, do the earlier tasks fully and say plainly which you did not reach. Partial and honest beats complete and guessed.
- Write C1C2-ENCODER-REPAIR-2026-09-10.md in the workspace root AND print it as your final message. Lead with one line: whether the C2 defect is an encoder bug, and whether an admissible repair exists for C1.
