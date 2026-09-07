# V0.16 B402 -> 100EP five-arm preparation audit

Status: **PREP ONLY**.  This note is an isolated implementation plan; it is
not a preregistration, does not change shared authority, and no simulator,
episode training, or TEST split was opened while preparing it.

## 1. Boundary and current gate state

The frozen V0.16 contract is
`artifacts/multi-catfish-v016-c3-origin-gate-20260903-r1/contracts/MULTI-CATFISH-MCRL-V016-C3-ORIGIN-GATE-PREREG-2026-09-03.md`
with SHA-256
`4dfeb9154983ee12ec6690e61c92a19e6893b27c811b0b84352a5d52c28b6784` (the
adjacent `prereg.sha256` check passed).  It is a source-only learnability
gate.  A PASS authorizes only a **separately preregistered** 100-episode
TRAIN-world five-arm trajectory screen; it does not authorize 500/1500/3000/
9000 episodes or episode training.  The B402 gate result is not present in the
local checkout at the time of this audit, so no physical screen is authorized
yet.

The phrase “100-episode” is not fully parameterized by the frozen contract.
The prior V0.14 physical protocol means 100 paired evaluation worlds/episode
indices, with four route arms evaluated for each of three frozen lineages and
one independent MAIN row per world.  That convention must be stated and
sealed in the next physical preregistration; no old V0.4/V0.15 world may be
silently reused.

## 2. Reusable seams

The following existing files are suitable read-only dependencies:

| Need | Reuse | Required treatment |
| --- | --- | --- |
| One common-mask route semantics | `.scratch/multi-catfish-v015-c3-reference-gate/run_v015_reference_physical_five_arm.py`, `V015ReferenceAnchorDecoder` | Reuse the logic as a V0.16-namespaced adapter. Do not import its V0.15 authentication/state constants unchanged. |
| Physical environment plumbing | `.scratch/multi-catfish-v014-learner/run_v014_physical_five_arm.py` helpers `_set_fading_field`, `_reset_environment`, `_last_outcome`, `_observation_after_step`, and action-trace helper | These are import-time side-effect-free helpers. Keep one fresh environment per route row and the same keyed field per world. |
| Ratio-of-sums and receipt aggregation | `.scratch/multi-catfish-v014-learner/run_v014_five_arm_evaluation.py` (`V014EpisodeReceipt`, `aggregate_arm`, `aggregate_five_arm`, `ratio_of_sums`) | Import read-only or wrap under a V0.16 schema. Never use the mean of per-episode EE as the endpoint. |
| Paired five-arm persistence/checkpoints | `.scratch/multi-catfish-v014-learner/run_v014_physical_five_arm.py` | Reuse its prepare/run/verify pattern, but create V0.16 output/schema names and add explicit B402 provenance. |
| Frozen Q1/Q2 loaders | `.scratch/multi-catfish-v015-c3-learned-context/run_v015_c3_learned_context_oracle.py` (`load_frozen_q1`, `load_frozen_q2`) | Keep the authenticated V0.3 Q1 and V0.14 Q2 bytes exactly. Record that Q2 is a frozen inference input even though its historical V0.14 learner-gate status is `STOP_LEARNABILITY_GATE`. |
| V0.16 state | `src/mcrl/runtime/ee_axis_v016_c3_origin_state.py` | Use `encode_ee_axis_v016_c3_origin_state`; require 402-D/14-local/10-global and the V0.16 schema digest. |
| B402 C3 gate | `.scratch/multi-catfish-v016-c3-origin-gate/run_v016_origin_gate.py` | Add a V0.16-specific read-only gate-selection/authentication helper after PASS. V0.15 `PASS_REFERENCE_GATE` authentication is not valid for B402. |

The pure V0.14 evaluator already writes a checkpoint only when the configured
episode index reaches the cadence, and its checkpoint is explicitly a progress
receipt, not a model checkpoint.  That is the right basis for this frozen-head
screen.

## 3. Frozen model panel and state/loading changes

### Frozen Q1/C1

Use the exact V0.3 Q1 files (rung-10 outer checkpoint) for lineages
`2026092101`, `2026092102`, and `2026092103`:

* `artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1/checkpoints/init-2026092101-rung-000010.pt`
  — `f26aab2fab6d31d6f3e4acd97782beeb0bba055ec94611dc9f3ed47038a231f0`
* `.../init-2026092102-rung-000010.pt`
  — `6930534d90840807c4dda1eda9c0ecf58793175053a37a43b75e38a7b6d310ba`
* `.../init-2026092103-rung-000010.pt`
  — `507b871f2536097b400b099b9dcb666e8445e9aee921001d61e70ff6042646b2`

The canonical V0.13/V0.15 loader must authenticate the V0.3 authority/result
receipts and parameter digest.  These are C1/Q1 inference inputs, not a new
training run.

### Frozen Q2/C2

Use the exact V0.14 Q2 rung-3000 files through the existing lineage mapping:

| Q1/Q2 source lineage | Q2 checkpoint initialization | SHA-256 |
| --- | --- | --- |
| 2026092101 | 2026108101 | `d981232a9e56e6ce71c8e8b1fda789efc69852d4a6a22e918a2992ddc58a533d` |
| 2026092102 | 2026108102 | `9a45f5bc125d6ba453d7d74dbc640ec3d2e927fffb161518e383e6b3aabbe8ef` |
| 2026092103 | 2026108103 | `8f9d2e5d1749515a0896137082b1430419ae1b8a794d28ea772a23c86648be81` |

The current loader validates the V0.14 result/authority/seal and the exact
rung-3000 nested Q2 state.  The historical result is a learnability STOP, so
the provenance must not call it a passed Q2 gate; it is simply the frozen Q2
head required by the V0.16 source/route design.

### B402 C3

After and only after a B402 `PASS_ORIGIN_GATE`, authenticate:

* result: the B402 `learner-gate/result.json`;
* receipt: the B402 `learner-gate/receipt.json`;
* three explicit checkpoints:
  `checkpoints/init-2026111101-rung-003000.pt`,
  `...1102...`, and `...1103...`.

The final result/receipt/checkpoint digests are unknown until the gate runs and
must be pinned into the later physical preparation receipt.  Each C3
initialization is paired by index with Q1/Q2 source lineages:

`2026111101 -> 2026092101`, `2026111102 -> 2026092102`,
`2026111103 -> 2026092103`.

This is the key semantic difference from V0.14/V0.15: the C3 initialization
seed and the Q1/Q2 source-lineage ID are no longer the same integer.  The new
receipt should therefore carry both fields (the old `initialization_seed`
field may denote the C3 seed, while `source_lineage` explicitly denotes the
Q1/Q2 pair).

The adapter must require the B402 config exactly: 28 actions, 14 local
features, 10 globals, hidden `(100, 50, 50)`, `tanh`, learning rate `0.001`,
the frozen `kappa`, `beta=0.1`, and zero-initialized final layer.  It must
reject V0.15's 371-D/13-local/7-global schema and its
`PASS_REFERENCE_GATE` decision.

## 4. Route/arm semantics to preserve literally

At every decision use one native legal mask and one masked argmax:

* `FULL`: compute detached `c^12 = argmax(Q1+Q2)`, encode B402 C3 state with
  that reference, select `argmax(Q1+Q2+Q3(s^12))`;
* `DROP_C1`: compute detached `c^2 = argmax(Q2)`, encode the context-2 B402
  state, select `argmax(Q2+Q3(s^2))`;
* `DROP_C2`: compute detached `c^1 = argmax(Q1)`, encode the context-1 B402
  state, select `argmax(Q1+Q3(s^1))`;
* `DROP_C3`: select `argmax(Q1+Q2)` and **do not call Q3 or construct a zero
  Q3 surface**;
* `MAIN`: an independently supplied canonical frozen Main baseline.  It is
  not a route with missing heads and must not be formed by composing Q1/Q2/Q3.

The `V015ReferencePhysicalAdapter` already implements this context/reference
ordering and the no-Q3 `DROP_C3` branch.  The V0.16 fork must replace only the
state/gate/panel seam and retain the one-action deployment contract.  It must
not introduce a second decoder, normalization, action override, coordinator,
auction, or learner update.

For each evaluation world, create one canonical `KeyedFadingField` from the
frozen field component and world seed, and pass that same field to all four
route arms and MAIN.  Use a fresh environment/reset for every route-lineage
row so one policy cannot carry state into another.  World identity is paired
by evaluation seed, start record/digest, and field-root digest.

## 5. Proposed 100EP data layout and endpoint

This is a proposal for the later physical contract, not a frozen result rule.
Following the existing V0.14 convention, use 100 previously unopened TRAIN
world seeds in a fixed order.  Each world produces:

* 4 route arms × 3 C3/Q1-Q2 lineage pairs = 12 route episodes;
* 1 independent MAIN episode;
* 13 episodes/world, 1,300 ten-step episodes total;
* 13,000 simulator steps and 130,000 user-step decisions when the canonical
  100-user × 10-step episode is retained.

Do not reuse the old V0.4 evaluation seeds (`2026109001..2026109100`) or any
previously opened V0.15 worlds.  The next physical preregistration must list
the new seeds, TLE/record digest, field component, users, steps, and exact
five-arm row cardinality before outcomes are opened.

For each episode, record finite nonnegative delivered bits, positive system
energy, decision count, served user steps, arm, episode index, evaluation seed,
C3 initialization seed, Q1/Q2 source lineage, field digest, and action-trace
digest.  Compute the arm endpoint only after pooling additive totals:

```text
B_A = fsum(total_bits_e)
E_A = fsum(total_energy_j_e)
eta_A = B_A / E_A
service_A = sum(served_user_steps_e) / sum(decision_count_e)
```

Report the descriptive mean of per-episode ratios separately, but never use it
as the EE endpoint.  Report `FULL / DROP-Ci - 1` for each i, pooled and by
lineage, plus per-world paired contrasts.  Route arms have equal row
multiplicity, whereas MAIN has one row/world; compare MAIN by service fraction
and pooled ratio-of-sums, and label raw served-count comparisons as multiplicity
diagnostics only.

The physical contract must freeze its service rule before outcome inspection.
At minimum report pooled service fractions, per-world service differences, and
the number of nonnegative lineage contrasts.  Do not invent or tune a strict
service/noninferiority threshold after seeing the 100EP result.  The current
B402 source contract does not supply an efficacy decision rule.

## 6. Checkpoint and receipt semantics

Because the B402 heads are frozen inference models, the episode-100 files are
**evaluation progress receipts**, not learner/model checkpoints.  For each arm
write once:

`checkpoints/full-episode-000100.json`,
`drop_c1-episode-000100.json`,
`drop_c2-episode-000100.json`,
`drop_c3-episode-000100.json`, and
`main-episode-000100.json`.

Each checkpoint should contain the arm, episode index 100, configured episode
count, row count, pooled bits/energy/EE/service summary through that boundary,
contract/gate/checkpoint digests, `evaluation_split=TRAIN`, and explicit
`test_split_opened=false`, `held_out_ee_evaluated=false`,
`episode_training=false`.  The output should also contain write-once
`prepare.json`, `episode-receipts.json`, `episode-provenance.json`, `run.json`,
and `verify.json`.

If a later user decision authorizes actual episode/learner training, that is a
different contract.  It must write model/optimizer/replay state every 100
episodes; the B402 gate and this screen do not authorize it.

## 7. Fastest safe implementation path

The lowest-risk path is one new V0.16 physical adapter/runner that imports
the two V0.14 pure receipt seams and the V0.14 physical reset helpers, and
copies only the V0.15 route decoder/policy loop into a V0.16 namespace.  A
second new test module can exercise synthetic receipts, B402 panel
authentication, 402-D state shape, four route contexts, `DROP_C3` no-call, one
common mask, paired field identity, and checkpoint cadence without opening a
simulator.

For shorter server wall time without changing scientific semantics, shard by
**world**, not by arm: one shard process constructs one field and evaluates all
five arms and all three route lineages for that world, then a deterministic
receipt-only merge checks the rectangular world/arm/lineage closure.  Never
run arms independently with different fields.  Serial execution is simpler;
world sharding up to the server's bounded CPU budget is safe once the physical
contract freezes the merge order and digest rules.

Minimum later file set:

1. `.scratch/multi-catfish-v016-c3-origin-gate/run_v016_origin_physical_five_arm.py`
   (new V0.16 auth, adapter, and either serial loop or shard entry point);
2. `tests/test_w169_ee_axis_v016_origin_physical_five_arm.py` (synthetic-only
   seam/receipt tests);
3. a separately frozen physical 100EP preregistration/receipt set (not to be
   created by this prep task);
4. optional world-shard controller/merge scripts if parallel execution is
   selected.

Do not edit V0.14/V0.15 runners or shared authority merely to parameterize
V0.16.  The V0.16 code manifest must include every imported source seam and
the physical runner's exact bytes.

## 8. Wall-time estimate (server)

An existing measured reference is
`artifacts/multi-catfish-v04-five-arm-ablation-20260901-r1/result.json`:
390 ten-step episodes, 100 users, elapsed `890.9166037801187 s` (about
2.28 s/episode).  Scaling the proposed 1,300 episodes gives about
`2,969.7 s` or **49.5 minutes** on comparable hardware.  The V0.16 402-D
state and provenance checks may add overhead, so a reasonable serial-server
planning range is **roughly 50–90 minutes**, not a guaranteed runtime.  The
older oracle screens were more expensive (`1149.4 s / 132` episodes and
`969.5 s / 72` episodes) because they performed additional counterfactual
work; they are an upper-bound warning, not a direct physical-run benchmark.

With safe world-level sharding, elapsed wall time could be lower, but only if
the server has spare CPU and the merge retains the same paired field and
write-once receipts.  This estimate excludes the B402 source gate itself and
the time needed to write/freeze the separate physical contract.

## 9. Decision dependency

The sequence is therefore:

1. finish the frozen B402 source gate;
2. if and only if all three initializations pass, authenticate its result,
   receipt, and r3000 C3 checkpoints;
3. freeze a new physical 100EP TRAIN-only contract with new world seeds,
   field, service reporting, row multiplicity, and checkpoint semantics;
4. run the inference-only five-arm screen and verify its receipts;
5. treat the output as development trajectory evidence, not proof of final
   EE efficacy, until a later pre-registered confirmatory decision authorizes
   that claim.

