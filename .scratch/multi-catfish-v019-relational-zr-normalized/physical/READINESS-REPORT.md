# V0.19 five-arm short-screen readiness report

**Scope:** isolated preparation under this V0.19 physical-screen lane only.  
**Status:** `READY_FOR_POST_PASS_BINDING__NOT_RUN`  
**Claim ceiling:** `TRAIN_DEVELOPMENT_EE_RECEIPTS_ONLY_NO_TEST_EFFICACY_CLAIM`

## What was prepared

The isolated evaluator in `v019_five_arm_screen.py` supplies:

- literal `FULL`, `DROP_C1`, `DROP_C2`, and `DROP_C3` score-head ablations;
- an independent `MAIN` callback boundary;
- one native Boolean mask and one masked argmax for every route;
- additive ratio-of-sums EE aggregation;
- per-lineage marginal summaries and the pre-registered partial ordering;
- 100-episode checkpoint names and receipt summaries;
- strict TRAIN-only, no-learner-update flags;
- provenance checks for the three Q1/Q2/learned-Q3 lineage bindings;
- paired keyed-field checks across all five arms; and
- an explicit Q3 input/reference-drift check; and
- an explicit `normalized_bits_per_kappa` binding for every learned-Q3
  route receipt and checkpoint panel.

The module is runnable once a post-gate caller supplies the physical episode
callbacks.  It does not contain a default simulator launcher.  This is
intentional: the learned-Q3 gate has not yet produced the checkpoint panel,
and this worker was instructed not to open fresh worlds or start training.

## Frozen semantics audited before implementation

The current V0.19 source path uses the native Q1 surface from
`encode_ee_axis_state`, builds the Q2 carrier through the detached OPS-3
anchor/projection helpers, and evaluates learned Q2 on the V0.14 Q2 state
surface.  The learned V0.19 Q3 source contract trains against the detached
reference

\[
r_{12}=\arg\max_{a\in\mathcal A_{\rm safe}}(Q_1+Q_2).
\]

The physical screen therefore keeps `r12` fixed for all active-Q3 arms:

| Arm | Final score | Q3 state/reference | Q3 call |
|---|---|---|---|
| `FULL` | `Q1 + Q2 + Q3` | fixed V0.19 relational state from `r12` | yes |
| `DROP_C1` | `Q2 + Q3` | the same state from the same `r12` | yes |
| `DROP_C2` | `Q1 + Q3` | the same state from the same `r12` | yes |
| `DROP_C3` | `Q1 + Q2` | not constructed for this route | no |
| `MAIN` | independent frozen baseline | not applicable | no |

V0.19 changes the learned Q3 scorer's output parameterisation only: the
scorer returns normalized bits-per-κ, and the route sum consumes that value
without a second division.  The structured relational input/state schema is
unchanged from V0.18 and remains bound as
`multi-catfish-mcrl-v018-relational-zr-c3-v1`.

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

The canonical callback seam is now implemented in
`v019_physical_adapter.py`.  `V019PhysicalAdapter.route_episode_runner` uses
the existing frozen Q1/Q2 carrier helpers, the V0.19 relational encoder, and
the normalized learned-Q3 checkpoint; `main_episode_runner` uses a separately
injected frozen MAIN policy.  `run_v019_five_arm_screen_server.py` provides
`assemble_post_pass_runtime(...)` and an explicit `run(output_dir=...)`
boundary.  This is setup/implementation only: no simulator, fresh world,
outcome, or learner was opened in this lane.

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
4. **Q3 state/output:** bind the exact current relational-ZR state encoder
   and its unchanged schema/config, together with the V0.19 checkpoint
   `output_unit_mode=normalized_bits_per_kappa`.  For every active route
   episode, build the state once
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

The launcher additionally requires the explicit mapping from each Q3
initialization seed to its source lineage.  The current V0.19 learner
checkpoint stores the source-panel digest but intentionally does not repeat a
lineage field, so the mapping is a post-gate input rather than a guessed
directory convention.

The physical adapter folds all ten anchor-level relational state/reference
digests into the episode receipt.  Therefore the pure loop's active-arm
equality check covers the whole episode rather than only its final anchor.

## Forward-only runtime estimate (not measured in this lane)

This lane deliberately did not open a simulator or a fresh world, so the
following is a planning estimate rather than a server receipt.  The closest
existing physical reference is the V0.4 five-arm run: 390 ten-step episodes
with 100 users in `890.9166037801187 s` (about `2.28 s/episode`).  V0.19 has
`100 * 3 * 4 + 100 = 1,300` physical episodes (four route arms for each of
three lineages plus one MAIN episode per world).  At that observed rate this
projects to about `2,970 s`, or **49.5 minutes**, on comparable hardware.

A one-world, three-lineage server smoke would contain 13 episodes (12 route
episodes plus one MAIN episode), projecting to about **30 seconds** at the
same rate.  Allow **1--3 minutes** for process start, checkpoint loading,
TLE/archive linking, and receipt flushes.  The full 100-world screen should
be planned as **50--90 minutes serially** until the first permitted smoke
calibrates this estimate; safe world-level sharding may reduce wall time but
must preserve the common field and write-once receipt closure.

The remaining integration work after a valid `PASS_LEARNER_GATE` is supplied
is binding the three Q3 checkpoint paths/hashes/init-to-lineage mapping,
selecting the pre-registered 100 TRAIN worlds/field component and frozen
archive, then running the non-scientific smoke.  No outcome from this estimate
authorizes a physical run or changes the frozen acceptance criteria.

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
are pure/mock tests in `tests/test_v019_five_arm_screen.py` plus adapter/launcher
contract tests.  A server smoke has not been run here; its runtime estimate
must be measured only after PASS and explicit bindings are supplied.
