# V0.23 baseline namespace adjudication

Date: 2026-09-06

Status: `IMPLEMENTATION_NAMESPACE_CORRECTED / NO_SCIENTIFIC_OUTCOME`

## Decision

The primary physical-evaluation label `BASELINE` remains the explicitly
authenticated pre-Catfish MODQN policy.  The separately trained three-route
control whose C1, C2, and C3 sources are all neutral is named
`ALL_NEUTRAL_CONTROL`.  It is an implementation/source-training diagnostic and
is not one of the five primary Chapter-5 physical curves.

The canonical mappings are therefore:

| Layer | Arms |
|---|---|
| Source training | `ALL_NEUTRAL_CONTROL`, `FULL`, `DROP_C1`, `DROP_C2`, `DROP_C3` |
| Primary physical evaluation | `BASELINE`, `FULL`, `DROP_C1`, `DROP_C2`, `DROP_C3` |

`FULL - DROP_Cj` is a controlled informed-versus-equal-budget-neutral source
replacement contrast for route Cj.  It does not require the all-neutral
control.  `FULL - BASELINE` is the whole current Multi-Catfish policy-family
contrast against the authenticated pre-Catfish MODQN policy; it is not a
route-isolated contrast.

## Implemented correction

Only the source-training namespaces were changed:

- `.scratch/multi-catfish-v023-five-arm-training-runner/`
- `.scratch/multi-catfish-v023-five-arm-learner-orchestrator/`
- `.scratch/multi-catfish-v023-real-one-world-plumbing/`

The serialized identities were advanced from runner schema v1 to v2 and from
orchestrator schema v2 to v3.  A subsequent repository-wide caller audit found
that the implementation-only real-one-world diagnostic still gave the
all-neutral current model the old `BASELINE` label.  That diagnostic was also
renamed to `ALL_NEUTRAL_CONTROL`, and its schema/domain were advanced from v1
to v2.  A temporary test-only translation back to `BASELINE` was removed.
The source-binding and primary physical-evaluation layers were deliberately
left unchanged.

## Independent verification

The controller re-ran the four focused suites together after the correction:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -p no:cacheprovider \
  .scratch/multi-catfish-v023-five-arm-learner-orchestrator/test_v023_five_arm_learner_orchestrator.py \
  .scratch/multi-catfish-v023-five-arm-training-runner/test_v023_five_arm_source_training_runner.py \
  .scratch/multi-catfish-v023-ablation-prep/test_v023_source_binding_plan.py \
  .scratch/multi-catfish-v023-five-arm-evaluation/test_v023_five_arm_eval_binding.py
```

Result: `37 passed`.

The affected real-one-world/source-runner suites were then re-run after the
caller correction and exited successfully.  A dedicated cross-layer invariant
was added and separately passed: source training contains
`ALL_NEUTRAL_CONTROL` and excludes `BASELINE`, while primary physical
evaluation contains the authenticated `BASELINE` and excludes
`ALL_NEUTRAL_CONTROL`.  The source-runner suite now has `4 passed`; the provider
bridge (`9 passed`) and real five-arm episode-runner seam (`6 passed`) also
remained green.  A repository-wide search found no remaining executable or
current documentation mapping that assigns all-neutral route sources to
`BASELINE`; the only remaining text is the pre-correction review prompt kept
as provenance.

The physical source-binding and evaluation code still require `BASELINE` to
carry `EXPLICIT_AUTHENTICATED_PRE_CATFISH_POLICY` and no route sources.  No
simulator, learner training, TEST split, formula, Gate predicate, seed,
threshold, or paper claim was changed by this correction.

## Claim ceiling

This receipt establishes only namespace and cross-layer implementation
consistency.  It is not evidence that C1, C2, C3, FULL, or Multi-Catfish
improves energy efficiency.

`RENAME_NEUTRAL_CONTROL_KEEP_PRECAT_BASELINE`
