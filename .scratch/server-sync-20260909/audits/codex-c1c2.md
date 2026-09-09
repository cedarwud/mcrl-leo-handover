# Audit C1 and C2 with the rigour that was applied to C3 today

`DIAGNOSTIC_NOT_CLAIM`. Budget 2 hours. Read-only analysis plus small deterministic checks; run no training.

## Why
The whole day has been spent auditing the coordination component. The two per-user components have never had the same treatment, and there is already direct evidence of a defect in them that was noticed and not pursued.

**The evidence.** A selector diagnosis concluded the size-100 selection symptom is "principally a learned-score failure in the singleton/additive path", which is C1 and C2, not C3. Zeroing the interaction head left the symptom unchanged at 10 of 10 decisions. On the panel average the **learned** singleton sum was `106.501`, while the exact score shows large singleton and interaction terms that cancel, and the report states the learned path does **not** reproduce that cancellation.

**Why their passing gates means less than it did.** The stage-C acceptance test named to enforce the pairwise-coupling requirement contained zero mentions of its subject and asserted that the head predicts synergy on a fixture the test itself labelled synergy. It could not fail for the reason it existed. The physics and stage-C baselines are also not green: six failing tests and one that does not complete. About thirty tests validate a file loaded from `.scratch` by path rather than the package under test.

## What to audit
1. **The learned versus exact singleton contrast.** Quantify the error in the learned C1 and C2 scores against exact evaluator singletons, by anchor and by coalition size. Is it bias, scale, or a failure to reproduce the cancellation? Report the sign and magnitude, not only a fit statistic.
2. **Their acceptance tests, one by one.** For each test that gates C1 or C2, state the obligation it names and then answer: **which specific wrong implementation would this test reject?** Where the answer is "none", say so. Apply the same standard used against the interaction test: a fixture the test labels and then asserts is not evidence.
3. **Feature sufficiency.** The interaction encoder was found summing pairwise terms into a forbidden scalar. Check the C1 and C2 encoders for the same class of defect: is any structured quantity reduced to an aggregate before the head sees it, and can two physically distinct states with different correct answers map to the same encoded input? Construct a collision if one exists.
4. **Estimator matching across arms.** A known failure class in this project: if the factor arms are scored with the exact objective, every DROP arm coincides with FULL and the marginals are identically zero. Verify that DROP_C1 and DROP_C2 differ from FULL by the intended mechanism, that each ablation changes what it is supposed to change and nothing else, and that a fixture exists which would make them disagree. If no such fixture exists, the ablation is untested.
5. **Corpus coverage.** The interaction corpus was 180 rows from two worlds. The per-user corpus is 176,223 rows, but from the **same two worlds**. Report the diversity actually present: how many distinct anchors, worlds, dates, and how much of the per-user input space is covered. Volume is not diversity.
6. **The 664 per cent figure.** A perfect-knowledge diagnostic measured iterated unilateral optimisation improving pooled energy efficiency by about 664 per cent over the carrier baseline. That is large enough to warrant asking whether the baseline is unreasonably poor rather than the optimisation unreasonably good. Check what the baseline assignment actually is and whether it is a fair comparator or a straw man.

## Output
`C1C2-AUDIT-2026-09-09.md` in the workspace root, printed as your final message. Lead with the single most consequential defect found, or with a clear statement that none was found, which is an equally useful answer. Then the six sections. For each finding give the file and the lines.

Mark every claim as verified by reading, verified by executing, or inference.

## Constraints
Workspace `/home/sat/mcrl-v025-c1c2-ws`: `cp -a /home/sat/mcrl-v025-pilot-ws /home/sat/mcrl-v025-c1c2-ws`, then `rm -rf .git`, `git init`, commit. Never modify any other workspace; several jobs are editing them. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, or `/home/sat/mcrl-v025-codex-ws-engine`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Large files under `/home/sat/bigtmp`, never `/tmp`, a RAM-backed tmpfs here. Two processes maximum, `nice -n 15`.

Change no threshold, sign, seed, horizon, price, service guard or acceptance rule.
