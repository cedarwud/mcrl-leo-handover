## VERIFIED

Read-only local inspection; no edits, network, SSH, or physics runs. The declaration’s SHA-256 matches its sidecar (`f27d0500…`); rederiving the world plan produced `866d28e05b04a361041f829e424a2417f49987239b7771ee94f43022d35e01bb`.

The [contract §6](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-DEVELOPMENT-CONTRACT-2026-09-07.md) fixes four arms, TRAIN only, 100 users × 10 steps, cumulative pauses, and the pooled estimand. Computing beyond 3000 requires `C1C2_DEVELOPMENT_PREDICTION_HELD` and owner notification. The 9000-world plan does **not** authorize speculative 9000-episode execution.

The [runner](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py) currently loops episodes, then all four arms, sequentially. Its adapter and launch admission require learned exports and predecessor PASS receipts; neither proposal is presently an available launch mode.

**Episodes are not seed-only independent.** `_rngs(seed)` creates fresh environment/mobility generators through `SeedSequence(seed).spawn(2)`. However, `run_episode()` restores `environment_training_state` from the preceding episode. [StepEnvironment](/home/u24/papers/mcrl-leo-handover/src/mcrl/env/step.py) preserves `_age_rng`: episode 1 spawns it from the environment generator; each reset draws 100 warm-start ages using `integers(0,10,size=100)`. Physics state resets; this stream persists. Its consumption is outcome-independent and occurs only at reset.

An in-memory RNG probe confirmed that fresh episode-101 initialization changes ages; restoring the sequential episode-100 boundary reproduced all age draws for episodes 101–200. This was **not** the required physical equivalence test.

`aggregate_last_outcomes()` accumulates ten steps; `pool_receipts()` applies `math.fsum` to individual episode totals. Summing chunk totals would change the reduction.

Two launch code-manifest files changed during inspection. The inspected runner remained SHA-256 `54e5d2475e36bac76206788de85a09e024f89facba450e588b31d7fcfd913386`; this memo does not certify the concurrent fix pass.

## INFERRED

BASELINE has no scientific dependency on stage-A exports: its authenticated MODQN adapter is frozen, exposes `contract_fields_excluded`, and carries `routes=[]`. Chronological separation can preserve matched evaluation.

Chunk parallelism can preserve results **with exact age-stream boundary states**. Those states can be generated cheaply by replaying the original RNG draws, without evaluating policies or physics. Equal world seeds and keyed-field roots alone are insufficient.

The measured predecessor cost implies **43.13 core-hours** for 4 × 3000 episodes. With 16 available workers, the ideal floor is **2.70 hours**; 100-episode chunks require approximately **2.88 hours** without rung barriers, or **3.23 hours** respecting 100/500/1500/3000 barriers, plus startup, verification, contention, and pauses. Budget approximately **3.3–4 hours**, provisionally: the measurement covers predecessor DROP_C3, not all successor arms.

Server occupancy is owner-supplied, unverified here. With 16 of 20 cores occupied and two reserved, only **two additional single-thread workers** fit.

## RULING

**A — Allow BASELINE 1–3000 conditionally.** Before execution, seal an explicit execution-only scheduling addendum permitting early baseline materialization and later authenticated import. Preserve the scientific declaration. Resolve the existing whole-contract admission requirements explicitly; freezing only baseline inputs does not silently waive unresolved bindings.

Bind the complete stage-C runner, independent verifier, configuration, plan, RNG/boundary policy, baseline checkpoint/status/adapter closure, and scheduling change **before any successor computation, including stage-A’s one-epoch diagnostic**. Later learned-export binding must only authenticate predetermined stage-A outputs. If computation already started, do not backdate or silently reseal.

Early baseline outputs remain per-arm evidence. Publish four-arm rung receipts only after stage-A integrity, stage-B plumbing, and complete matched coverage pass. Preserve actual execution dates and per-arm provenance; claim numerical equivalence, not simultaneous execution. No reselection or tuning from early outcomes. **Early BASELINE 9000 is disallowed.**

Stage-A training may start only after its existing r8 and diagnostic gates. Learned-arm physical evaluation still requires stage B. This ruling does not authorize splitting sequential learner updates.

**B — Allow only boundary-state-preserving chunking after equivalence passes.** Fresh-start chunks as proposed are not equivalent. Preserve the existing age stream; do not introduce per-episode age reseeding.

No episode reordering, per-chunk scientific stopping, outcome-selected chunks, altered policies, or TEST. Enforce cumulative barriers and total workers ≤ cores−2, with every worker’s numerical threads set to one.

## IMPLEMENTATION SPEC (for codex gpt-5.6-sol)

**Non-heavy implementation; remain local.** After the current fix pass lands, reread and hash affected files; preserve unrelated WIP.

1. In `v023_c1c2_successor_physical_runner.py`, add `build_chunk_boundary_states`, `run_arm_chunk`, and `merge_arm_chunks`. Retain existing sequential execution as the reference. Reproduce episode-1 RNG initialization and actual age draws to prepare states at 0/100/200/…; never substitute arithmetic `advance(100)`. Authenticate start states; verify end states against the boundary table.

2. Freeze contiguous 100-aligned ranges. Give each chunk an exclusive write-once root, episode records, and cadence checkpoints. Resume only authenticated completed boundaries; preserve valid prefixes and require existing repair authority after integrity STOP.

3. Receipts must bind arm/range/chunk ID, plan and schedule digests, policy/status/adapter provenance, authority/code/configuration/TLE/PREREG hashes, RNG algorithm/version, boundary-state hashes, threads/runtime, parent checkpoint, ordered episode-record digest, timestamps, and forbidden-boundary flags.

4. Merge records by episode index and frozen arm order. Reapply unchanged per-episode aggregation and `math.fsum` over individual episode totals at each cumulative boundary. Emit matched receipts and checkpoints write-once; only the complete 3000 boundary adjudicates.

5. Update stage-C binder, preflight, controller, `stagec_common.py`, verifier, manifest builder, sync script/list, and README; update stage-A freeze bindings to pin the resulting closure prospectively. Separate early-baseline admission from later four-arm admission without fabricated exports or PASS receipts.

6. Extend `test_cadence_resume.py` and launch tests. Independently recompute plan/field identities, boundary streams, coverage, provenance, ordered pools, checkpoints, and disposition. Require bitwise float comparisons, not the verifier’s current tolerance. **Mandatory server acceptance:** sequential 200 episodes versus 2×100 chunks for every arm, identical episode/pool/rung values, state boundaries, and receipts modulo explicitly enumerated provenance fields. Test interruption/resume, duplicate/missing chunks, wrong states, and forbidden continuation. Report unrun acceptance as pending; do not launch automatically.

ASTRA_BASELINE_DECOUPLING=ALLOWED_WITH_CONDITIONS
ASTRA_EPISODE_CHUNKING=EQUIVALENT_WITH_CONDITIONS