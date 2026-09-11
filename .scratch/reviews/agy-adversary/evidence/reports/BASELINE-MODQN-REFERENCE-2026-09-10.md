**No runnable V0.25 external `BASELINE` exists: pooled EE and active-beam count are therefore unmeasured, and learned `a0` cannot be placed above or below it on this panel.**

# BASELINE / MODQN reference — design-phase determination

Date: 2026-09-10  
Scope: development anchors only; no evaluation-only claim dates read  
Status: Part 1 complete; Parts 2 and 3 intentionally not run under the requested stop rule

## Finding

The current V0.25 seal names an **“external BASELINE”** but does not bind an executable policy, checkpoint, training regime, or a mapping between V0.25 observations/actions and the predecessor MODQN interface. The predecessor seal does identify `BASELINE`: it is one particular frozen, authenticated pre-Catfish MODQN checkpoint. That checkpoint and its read-only adapter still load, but their complete runnable environment path is V0.23-era. No end-to-end path submits that policy's decisions to the current V0.25 `a-r0` `StepEvaluator`.

The current pilot's object called `BASELINE` is instead `carrier_base`, recorded as a **“fixed carrier proposal.”** It is a geometry control, not the authenticated MODQN policy. Its existing V0.25 outcome numbers cannot measure the owner's MODQN gate.

## 1. Exact identity and decision rule

### What the sealed declarations say

The current V0.25 contract's arm inventory contains only the words **“external BASELINE”**; it supplies no further identity in that contract ([V0.25 contract, C3](/home/sat/mcrl-v025-retrain-ws/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md:21)).

The predecessor scientific declaration is precise:

> “`BASELINE` is the unchanged, externally authenticated pre-Catfish MODQN policy admitted through `.scratch/multi-catfish-v023-baseline-adapter/baseline_adapter.py` source and is never a trained arm.”

([V0.23 scientific declaration](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md:103)) Its companion contract binds checkpoint SHA-256 `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`, state dimension 112, 9,000 training episodes, and empty learned routes ([V0.23 development contract](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-DEVELOPMENT-CONTRACT-2026-09-07.md:182)).

### Exact policy

`BASELINE` is a **specific frozen MODQN checkpoint using a shared set of three Q networks**. It is not learned `a0 = masked argmax(Q1+Q2)`, not a hand-written allocation rule, and not merely a training configuration.

For each user `u` and legacy action slot `j`, it computes

```text
score_u(j) = 0.5 Q1(s_u,j) + 0.3 Q2(s_u,j) + 0.2 Q3(s_u,j)

a_u = lowest-index argmax_j score_u(j), over legal j only
a_u = -1 (NO_OP), if no action is legal
```

The adapter itself states:

> “This is MODQN's original weighted masked argmax: invalid actions are -inf and numpy's argmax supplies the lowest-index tie break.”

([baseline adapter](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v023-baseline-adapter/baseline_adapter.py:720)) The bound dimensions, hidden layers, activation, weights, shared-policy mode, state transforms, and completed training configuration are fixed in the same file ([constants](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v023-baseline-adapter/baseline_adapter.py:34), [trainer configuration](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v023-baseline-adapter/baseline_adapter.py:68)). The checkpoint-selection rule is the final-episode policy; the bound checkpoint is episode index 8999, after 9,000 episodes. `select_actions` applies the weighted masked argmax independently to every user's row ([selection entry point](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v023-baseline-adapter/baseline_adapter.py:747)).

## 2. Runnable implementation status

### What exists

The read-only legacy policy implementation is:

- File: [baseline_adapter.py](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v023-baseline-adapter/baseline_adapter.py:1)
- Entry points: `BaselineAdapter.from_artifacts(...)` ([loader](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v023-baseline-adapter/baseline_adapter.py:561)) and `BaselineAdapter.select_actions(states, masks)` ([selector](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v023-baseline-adapter/baseline_adapter.py:747))
- Bound checkpoint: `/home/sat/mcrl-v025-retrain-ws/artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt`
- Legacy physical runner: [v023_c1c2_successor_physical_runner.py](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:667), through `load_baseline_policy(...)` and `FixedPolicyEpisodeAdapter.run_episode(...)` ([episode entry point](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:1189)).

This is runnable against the legacy/V0.23 state, action, and environment contract. A read-only smoke load authenticated the checkpoint and instantiated its three networks. That establishes artifact integrity and legacy executability only; it is not a V0.25 outcome measurement.

### What does not exist

There is no runnable V0.25 path that does all of the following:

1. constructs the baseline's authentic 112-dimensional observations and 28-slot masks from a V0.25 `ExogenousWorldTape` anchor;
2. calls the authenticated checkpoint;
3. maps the returned legacy slot indices to V0.25 physical identities and a joint `Configuration` under a sealed rule;
4. validates or repairs independently chosen actions under a sealed V0.25 joint-profile rule; and
5. includes that configuration in the required fresh dense `StepEvaluator.evaluate_many(...)` call.

The governing V0.25 code confirms the mismatch:

- `REPORTED_ARMS` includes `BASELINE`, but `PILOT_ARMS` contains learned arms only ([pilot inventory](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:82)).
- Training iterates only learned arms, while the manifest describes `BASELINE` as `external_policy: "fixed carrier proposal"` ([pilot training/manifest](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:1199), [exact manifest field](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:1220)).
- At evaluation, the code explicitly performs `selections[(seed, "BASELINE")] = carrier_base` ([pilot assignment](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:1732)).
- The newer Stage-C scorer declares only the five learned arms and describes itself as physics-free ([scorer](/home/sat/mcrl-v025-selector-ws/scripts/score_stagec_checkpoints.py:1), [arm tuple](/home/sat/mcrl-v025-selector-ws/scripts/score_stagec_checkpoints.py:40)). It has no `BASELINE` policy path.

Therefore the current V0.25 `carrier_base` results, and the older roughly 3.72 Mbit/J V0.23 results, are both unusable as the requested V0.25 external-MODQN comparator: the former is the wrong policy and the latter is the wrong physics.

## 3. Decision-time information and comparison class

For every user, the authenticated checkpoint consumes four arrays of 28 entries, plus a Boolean legal-action mask over the same 28 slots:

1. `access_vector`: current access, one-hot or empty;
2. `channel_quality`: linear candidate-beam SNR, encoded as `log1p(SNR)`;
3. `beam_offsets`: candidate-beam off-axis angle in raw radians;
4. `beam_loads`: global pre-admission load for each physical beam, divided by the number of users; and
5. the legal-action mask.

The adapter validates those four arrays and deliberately strips every contract extension ([input validation and native surface](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v023-baseline-adapter/baseline_adapter.py:394)). Thus `112 = 4 × 28`; the mask restricts selection but is not part of the 112 numeric features.

Its comparison class is a shared per-user policy: all users use the same three networks, each user observes its own access/SNR/angle vectors plus the globally shared beam-load vector, and each action is selected independently subject to its mask. It does not consume the V0.25 coordinator's joint cross-gain matrix, bounded catalogue, joint-physics outputs, reference proposal, or future horizon ([V0.25 information interfaces](/home/sat/mcrl-v025-retrain-ws/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md:5)).

## 4. V0.25 training/configuration declaration

**The V0.25 sealed declaration is silent.** It does not say whether V0.25 must:

- replay the exact V0.23 checkpoint;
- retrain MODQN against V0.25 physics;
- use some other MODQN checkpoint; or
- use the pilot's fixed carrier proposal.

It also does not bind the V0.25-to-legacy observation/action projection or a deterministic invalid-joint-profile rule. The legacy adapter's embedded training configuration precisely authenticates the already-completed V0.23 checkpoint; it is not an instruction to retrain that configuration on V0.25.

Choosing among those possibilities would redefine the comparator. This is a scientific-owner gap, not an implementation choice that may be filled here.

## 5. Smallest work that would make the gate measurable

The irreducible first step is an owner-sealed comparator binding. It must name checkpoint reuse versus retraining and bind the checkpoint/implementation digests, the 4×7 candidate-slot roster, every V0.25-to-legacy input field, physical-identity round trip, and the joint invalidity fallback/repair behavior.

Once that decision exists, the smallest code work is a thin, read-only V0.25 policy bridge with known-answer tests for input identity, masks, slot mapping, lowest-index ties, empty masks, joint invalidity, and unchanged checkpoint bytes. The bridge then needs to be wired into one development-panel measurement entry point.

That entry point must assert the evaluator rule requested here, per anchor:

- selection: create **one fresh dense** `StepEvaluator(boundary_indices=(0,))`, then include `BASE` and every candidate in its first `evaluate_many(...)` call; no scalar `evaluate(...)` and no foreign cache may precede it;
- endpoints: create **one separate fresh realised dense full-48** evaluator, then include `BASE` and all endpoints in one `evaluate_many(...)` call; and
- assert fresh caches, evaluator identity separation, boundary sets, and membership of `BASE` in both relevant batch calls.

Only after those bindings, tests, and assertions exist can pooled EE, bits, joules, served PHY, rate-target attainment, `modal_frac`, active beams/satellites, and `argmax_distinct` be scientifically computed.

## Parts 2 and 3 — not run

The user's stop condition applies because Part 1 found no runnable V0.25 implementation of the declared MODQN comparator.

- No 20-anchor V025_PROBE_R2 outcome evaluation was run.
- `BASELINE` pooled EE, bits, joules, served PHY, attainment, `modal_frac`, active beams/satellites, and `argmax_distinct` are **unmeasured**, not zero.
- Learned `a0` was not evaluated or selected from the completed v1 checkpoints, so no checkpoint/seed/epoch is reported and no above/below comparison is made.
- `BASELINE` concentration versus spread is unknown. The supplied negative `d(EE)/d(active)` result therefore cannot diagnose this missing comparator. Calling the fixed carrier proposal's active count the MODQN active count would be a category error.
- No loss value was used as evidence about EE.

## Evidence classification and resource receipt

### Verified by running code

A single read-only Python process used exactly `/home/sat/mcrl-leo-handover/.venv/bin/python`, under `nice -n 15`, with `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS`, and `BLIS_NUM_THREADS` all set to `1`. It authenticated and loaded the legacy adapter/checkpoint, asserted the 112-state/28-action binding and the 5 GB cap, and did not invoke physics or inspect a panel anchor.

```text
anchor 0/20
peak RSS: 524275712 bytes (499.99 MiB)
python processes used: 1 (hard cap: 3)
nice: 15
BLAS/thread pins: all 1
```

### Verified by primary-source inspection

The current seal's bare arm wording; the predecessor checkpoint binding; exact adapter rule and inputs; legacy runner entry points; current V0.25 pilot substitution; and current scorer omission. The checkpoint file's SHA-256 matched `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`.

### Derived on paper

The displayed scalarization formula, `112 = 4 × 28`, and the classification of the mask as a selection constraint rather than a numeric state block follow directly from the executable constants and encoding path.

### Inferred

An owner decision is required before a V0.25 bridge can be scientific, because no sealed V0.25 text resolves checkpoint identity, input projection, action mapping, or invalid joint behavior. No efficacy or V0.25 EE inference is made.
