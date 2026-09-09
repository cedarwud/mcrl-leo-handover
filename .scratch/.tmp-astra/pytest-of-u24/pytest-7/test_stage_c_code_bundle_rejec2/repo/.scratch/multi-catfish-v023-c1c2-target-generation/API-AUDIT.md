# V0.23 C1/C2 source-to-target API audit

Status: `IMPLEMENTED_SEAM__NOT_RUN`

This audit was performed before any new target-generation run.  The current
predecision capture/materialization is intentionally outcome blind; it does
not contain rate, power, target, or forecast-trace payloads.  Therefore the
missing seam is a deterministic physical replay, not a missing formula.

## Reused production APIs

| Route | Existing producer | Required live inputs | Typed output |
| --- | --- | --- | --- |
| C1 | `mcrl.runtime.ee_axis_opening_runner.materialize_opening_opportunity` | current `StepEnvironment`, `StepObservation`, `EEAxisStateObservation`, sealed `C1UnilateralOpportunity`, keyed field, RNG, lambda, interval | `EEAxisOpeningSourceResult` |
| C1 | `mcrl.runtime.ee_axis_opening_dataset.EEAxisOpeningDataset.from_results` and `write_opening_dataset` | complete opening source results with one field root per shard | current `D^o` dataset |
| C2 | `.scratch/c2-v03/c2_temporal_fork_trainer_backend.py` `C2TemporalForkTrainerBackend.prepare_one_candidate` + `PreparedC2Fork.run_forecast` | current wrapped environment/legacy states/masks, frozen Main trainer, declared focal/candidate physical key, keyed forecast mode | complete matched forecast traces |
| C2 | `mcrl.runtime.ee_axis_temporal_capture.capture_temporal_anchor` then `materialize_temporal_pair` | same prepared fork, schedule digest, lambda, interval | `EEAxisTemporalPair` |
| C2 | `mcrl.runtime.ee_axis_temporal_dataset.EEAxisTemporalDataset.from_pairs` and `write_temporal_dataset` | complete verified pairs | current `D^t` dataset |

The new entry point only coordinates these calls.  It does not calculate
`zeta_1`, `zeta_2`, opening energy/rate differences, downstream surplus, or
release behavior itself.

## Replay-field audit

### C1

The sealed capture stores the exact fields needed to authenticate a replayed
anchor: `source_seed`, `step_index`, `state_sha256`, frozen Main
`reference_actions`, and all current `slot_tables`.  The materialized
opportunity adds focal/candidate action vectors and the physical candidate.
The runner reconstructs each world with the current Q1+Q2 source adapter,
checks the state and canonical C1 anchor digest, then calls the opening
producer.  It advances the source trajectory with the captured Main background
actions, matching `v023_c1c2_predecision_capture.capture_world`.

### C2

The sealed authenticated anchor stores `world_id`, `source_seed`, step/focal
identity, state/observation digests, reference and incumbent physical keys,
candidate SINR, slot table, legal alternatives, horizon, and release grammar.
The materialized opportunity stores the informed or neutral candidate.  The
runner rebuilds the current anchor and compares its canonical anchor digest
before constructing the existing C2 backend; it refuses an anchor whose
declared `world_id` and `source_seed` disagree.  It then invokes the strict
capture -> detached forecast -> temporal-pair order.  Future rates, powers,
served flags, release offset, and `zeta_2` remain backend-produced fields;
none are inferred from the source JSON.

### Important fail-closed check

The predecision bridge's Q1+Q2 background is compared with the C2 backend's
own Main action vector.  If those two current authorities disagree, the seam
stops instead of silently generating targets under a different behavior
policy.  This protects the state/action provenance boundary exposed by the
source capture.

## Data that is deliberately absent

The old source-only files do not provide physical branch outcomes or temporal
traces.  They cannot be converted into targets by adding a scalar or by
relabeling an old V0.20/V0.14 artifact.  The new seam regenerates those values
only by replaying the declared TRAIN world/anchor through the current
production primitives.  It never opens TEST and never selects a seed,
threshold, horizon, lambda, or candidate after an outcome.

## Remaining work

No local simulator run was performed for this task.  A fresh Ubuntu-server
run is still required after Gate GO and after a fresh capture/materialization
pair is available.  Its output is development source/target plumbing only;
learner fitting, checkpointed 100/500/1500/3000 development evaluation, and
any conditional 9000-episode launch remain separate authorized steps.
