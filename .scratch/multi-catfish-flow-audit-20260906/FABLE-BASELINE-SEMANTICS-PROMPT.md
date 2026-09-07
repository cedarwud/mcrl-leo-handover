# Role and goal

Act as a fresh-context scientific-method adjudicator for one bounded Multi-Catfish V0.23 interface question: what `BASELINE` must mean across source training and the later five-arm physical EE evaluation. Read the actual repository evidence, identify the causal estimand of each option, and choose the smallest scientifically defensible correction. This is a read-only review; the user cannot answer mid-task.

# Evidence to inspect

Work in `/home/u24/papers/mcrl-leo-handover`. Inspect at least:

- `.scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py`
- `.scratch/multi-catfish-v023-five-arm-learner-orchestrator/v023_five_arm_learner_orchestrator.py`
- `.scratch/multi-catfish-v023-ablation-prep/v023_source_binding_plan.py`
- `.scratch/multi-catfish-v023-five-arm-evaluation/v023_five_arm_eval_binding.py`
- `.scratch/multi-catfish-v023-episode-screen/v023_real_five_arm_episode_runner.py`
- `.scratch/multi-catfish-v023-c1c2-neutral-adapters/README.md`
- `.scratch/multi-catfish-v023-c3-source-schedule/README.md`
- `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md`
- `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-R7-LAUNCH-DECISION-2026-09-06.md`
- `docs/MULTI-CATFISH-MCRL-CONDITIONAL-EXECUTION-AUTHORIZATION-2026-09-06.md`

Relevant observed conflict to authenticate rather than assume:

- The source-training runner currently calls the all-neutral source map `BASELINE`: C1 neutral, C2 neutral, C3 neutral. It trains and exports that fifth current model with the same update budget as FULL and the three DROP arms.
- The source-binding/evaluation layer instead requires `BASELINE` to be an explicit authenticated pre-Catfish MODQN policy carrying no C1/C2/C3 route sources.
- The intended primary physical plot has exactly five curves: `BASELINE`, `FULL`, `DROP_C1`, `DROP_C2`, `DROP_C3`. The scientific objective is ratio-of-sums EE. The desired sign must never be used to choose a definition.
- A DROP arm changes only one route from informed to its equal-budget neutral source; it does not remove a Q head at deployment.

# Boundaries

- Do not edit any file, run tests, launch SSH, open TEST, run a simulator, train a learner, or inspect current Gate outcomes.
- Do not redesign C1, C2, C3, LC-SRS, formulas, thresholds, seeds, worlds, or checkpoints.
- Do not propose a new scientific Gate. This is terminology, arm identity, and causal-identification adjudication only.
- Preserve exactly five curves in the primary physical EE evaluation. You may distinguish an implementation-only source-training control from those five evaluation policies, but do not casually turn the primary result into six arms.
- Separate verified fact, inference, and proposal. Cite exact paths and line numbers.

# Questions

1. What does `FULL - DROP_Cj` estimate under the equal-budget neutral-source design, and does it require an all-neutral policy to be one of the five primary physical arms?
2. What does `FULL - pre-Catfish MODQN` estimate, and is it the appropriate `BASELINE` for the user's primary five-curve Chapter-5 comparison?
3. Is it scientifically valid for the source-training lifecycle to train an all-neutral fifth model while the physical five-arm evaluator instead uses an external pre-Catfish baseline? If yes, what must that trained control be named and what claim ceiling applies? If no, identify the exact inconsistency.
4. Choose one canonical arm vocabulary and mapping for:
   - source-training models;
   - primary physical evaluation policies;
   - checkpoint/export manifests.
5. Give the surgical implementation/documentation changes needed before the 100-epoch learner screen can be frozen. Mark which changes are mandatory and which are optional; do not add unrelated tests or authority.

# Output and stop

Start with a concise verdict. Then provide one compact table with the source-training and physical-evaluation mappings, followed by `Mandatory correction`, `Claim interpretation`, and `No-change items`. Keep the answer under about 1,500 words while retaining exact evidence.

End with exactly one of these tokens on its own final line:

- `BASELINE_ALL_NEUTRAL_PRIMARY`
- `BASELINE_PRECAT_PRIMARY`
- `RENAME_NEUTRAL_CONTROL_KEEP_PRECAT_BASELINE`
- `CURRENT_FIVE_ARM_DESIGN_INVALID`

Stop after the adjudication; do not perform any implementation.
