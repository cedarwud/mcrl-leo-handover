# V0.18 five-arm short-screen readiness report

**Scope:** isolated preparation under `five-arm-screen-draft/` only.  
**Status:** `READY_FOR_POST_PASS_BINDING__NOT_RUN`  
**Claim ceiling:** `TRAIN_DEVELOPMENT_EE_RECEIPTS_ONLY_NO_TEST_EFFICACY_CLAIM`

## What was prepared

The isolated evaluator in `v018_five_arm_screen.py` supplies:

- literal `FULL`, `DROP_C1`, `DROP_C2`, and `DROP_C3` score-head ablations;
- an independent `MAIN` callback boundary;
- one native Boolean mask and one masked argmax for every route;
- additive ratio-of-sums EE aggregation;
- per-lineage marginal summaries and the pre-registered partial ordering;
- 100-episode checkpoint names and receipt summaries;
- strict TRAIN-only, no-learner-update flags;
- provenance checks for the three Q1/Q2/learned-Q3 lineage bindings;
- paired keyed-field checks across all five arms; and
- an explicit Q3 input/reference-drift check.

The module is runnable once a post-gate caller supplies the physical episode
callbacks.  It does not contain a default simulator launcher.  This is
intentional: the learned-Q3 gate has not yet produced the checkpoint panel,
and this worker was instructed not to open fresh worlds or start training.

## Frozen semantics audited before implementation

The current V0.18 source path uses the native Q1 surface from
`encode_ee_axis_state`, builds the Q2 carrier through the detached OPS-3
anchor/projection helpers, and evaluates learned Q2 on the V0.14 Q2 state
surface.  The learned V0.18 Q3 source contract trains against the detached
reference

\[
r_{12}=\arg\max_{a\in\mathcal A_{\rm safe}}(Q_1+Q_2).
\]

The physical screen therefore keeps `r12` fixed for all active-Q3 arms:

| Arm | Final score | Q3 state/reference | Q3 call |
|---|---|---|---|
| `FULL` | `Q1 + Q2 + Q3` | fixed V0.18 relational state from `r12` | yes |
| `DROP_C1` | `Q2 + Q3` | the same state from the same `r12` | yes |
| `DROP_C2` | `Q1 + Q3` | the same state from the same `r12` | yes |
| `DROP_C3` | `Q1 + Q2` | not constructed for this route | no |
| `MAIN` | independent frozen baseline | not applicable | no |

This answers the potentially ambiguous ablation question: Q3 *can* be
evaluated in `DROP_C1` and `DROP_C2`, but only as a score-head ablation.  The
evaluator must not replace `r12` with `argmax(Q2)` or `argmax(Q1)` for those
arms.  Doing so would change the learned Q3 input/reference definition and
would confound the claimed C1/C2 marginal with a second state-definition
experiment.  The runner records hashes of the reference vector and complete
Q3 input state and rejects any active-arm mismatch.  `DROP_C3` is the only
route that does not evaluate Q3.

The source/learner and physical layers remain separate: the Q3 checkpoint is
loaded frozen after the learner gate, all three heads are queried in eval/no
gradient mode, and no checkpoint is changed by the screen.

## Exact remaining bindings after `PASS_LEARNER_GATE`

Nothing below is currently opened or selected by this draft.  A later owner
must fill every item in a new post-outcome binding record before invoking
`run_five_arm_screen`.

1. **Gate authority:** authenticated learner-gate summary path and SHA-256;
   the summary must state `PASS_LEARNER_GATE`, `test_split_opened=false`,
   `episode_training=false`, and `learner_update=false`.  Also bind the
   independent verification and the learner contract/code-manifest digests.
2. **Three route lineages:** for each initialization/source lineage, bind the
   exact frozen Q1, Q2, and learned-Q3 checkpoint paths and SHA-256 values.
   Validate every checkpoint payload's schema, contract, source-panel, code
   manifest, update count, and frozen/no-TEST flags before the first physical
   episode.  The three records become `LineageBinding` instances.
3. **Q1/Q2 loading:** bind the existing frozen Q1/Q2 loader roots and verify
   the parameter digests against their receipts.  Preserve the current Q1
   native-state and Q2 OPS-3-carrier semantics; do not substitute an old
   archived route or a new Q2 state.
4. **Q3 state:** bind the exact current V0.18 relational-ZR state encoder and
   its schema/config.  For every active route episode, build the state once
   from `r12 = argmax(Q1+Q2)` and pass the same state/reference receipt to
   `FULL`, `DROP_C1`, and `DROP_C2`.
5. **Fresh physical panel:** select exactly 100 previously unopened TRAIN
   world seeds, a canonical TLE/archive root, the field component, and one
   keyed-fading root digest per world.  The roots must be new identities and
   must be common across all five arms for a given world.
6. **MAIN baseline:** bind the frozen legacy MAIN policy path/receipt and its
   policy SHA-256.  Its callback must not use route Q1/Q2/Q3 surfaces and must
   return one paired receipt per world index.
7. **Runtime factories:** bind the canonical environment factory, RNG reset
   factory, and field factory.  Each route lineage/world pair must start from
   the same deterministic world identity and field root; no arm, action,
   target, or outcome may enter the field key.
8. **Output identity:** create a new empty server output directory for the
   short screen.  The evaluator will write one `episode-000100` progress
   checkpoint per arm after all route lineages and the matched MAIN receipt for
   world index 100 are complete.

## Acceptance to be computed, not tuned

The screen computes the following exact endpoint checks from raw additive
receipts:

```text
FULL > DROP_C1
FULL > DROP_C2
FULL > DROP_C3
DROP_C1 > MAIN
DROP_C2 > MAIN
DROP_C3 > MAIN
FULL served user-steps >= each comparator
each FULL-minus-drop marginal is positive in at least 2 of 3 lineages
```

There is no required order among the three drop arms.  Mean episode EE is
diagnostic only; the endpoint is pooled delivered bits divided by pooled
positive energy.  A passing short screen remains TRAIN development evidence
and does not by itself authorize a long 1500/3000/9000-episode run.

## Boundary statement

No simulator, fresh world, source outcome, TEST split, learner update, or
training process was opened by this preparation.  The only executed checks
are pure/mock tests in `tests/test_v018_five_arm_screen.py`.
