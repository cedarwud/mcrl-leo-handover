You are a fresh-context reviewer from a different model family. Read the ACTUAL code and files below yourself — do not rely on any summary. Your job is to find defects that would make a multi-hour training batch produce a wrong or uninterpretable result. Do not edit anything.

Repository worktree: /home/u24/papers/mcrl-leo-handover-cf3 (branch cf3/pilot-20260911). Diff to review: `git -C /home/u24/papers/mcrl-leo-handover-cf3 diff 363845e8..HEAD`. Main files: src/mcrl/algorithms/cf_ratio.py, src/mcrl/algorithms/cf_sources.py, scripts/run_cf3_pilot.py (and any launch/eval scripts), tests/test_cf_ratio.py.

The design it must implement (read all):
- /home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md
- /home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-AMENDMENT-1-THREE-CATFISH-PILOT-2026-09-11.md
- /home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-AMENDMENT-2-EE-ONLY-2026-09-11.md
- /home/u24/papers/mcrl-leo-handover/.scratch/cf3-pilot/DECLARATION-ADDENDUM.md (if present) and PROGRESS.md

Summary of intent: four arms — A0 baseline MODQN (published eq.16 per-head max, rewards r1/r2/r3 weights 0.5/0.3/0.2, gamma 0.9); A1 a new learner with three Q-heads (bits B, energy E, handover H), shared continuation bootstrap, action argmax[Q_B − eta*Q_E] (lambda fixed 0), gamma 1 with true terminal at step 10, eta by Dinkelbach from calibration rollouts; A2 = A1 plus three scripted "catfish" sources (hysteresis 2 dB, hysteresis 12 dB, no-new-beam) whose transitions make up 1/27 each of every minibatch and train all three heads; A3 = A2 with random-legal-action sources. Evaluation: greedy final checkpoint, pooled bits / pooled joules, per-episode reseeded so arms share start states.

Look in particular for: (1) anything that makes the arms unfair (different number of gradient updates per environment step, different learning rate or target-update schedule, A2/A3 getting more updates because of extra environments); (2) TD-target errors (masking missing on target net, wrong terminal handling, stale eta in stored rewards, heads not sharing the continuation action); (3) reward sums not matching the evaluator's pooled bits and joules; (4) any outage case where an unserved user scores better than a served one; (5) evaluation leakage (training or calibration seeds overlapping evaluation seeds, exploration not off); (6) silent exception handling or fallbacks that would hide a failure; (7) anything in the tests that passes without actually testing the claimed property.

Output: a list of findings, each with severity (INVALIDATES / BIASES / COSMETIC), a concrete failure scenario, and file:line. Say clearly what you verified by reading versus inferred. If you find nothing material, say so. First line: one bold sentence with the count of INVALIDATES and BIASES findings.

Write your review to /home/u24/papers/mcrl-leo-handover/.scratch/reviews/cf3-agy/CF3-AGY-REVIEW.md
