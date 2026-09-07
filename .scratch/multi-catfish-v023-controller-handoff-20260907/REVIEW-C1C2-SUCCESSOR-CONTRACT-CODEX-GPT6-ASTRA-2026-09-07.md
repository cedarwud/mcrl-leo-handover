## VERIFIED

Read-only local review; no edits, network, SSH, or execution of learners.

- Recomputed `int(SHA256(domain)[:16],16) & ((1<<63)-1)`: TRAIN=`2927175120652069826`; predecessor WORLD=`2818138104890398344`; successor PLUMBING=`936547238915053535`. All correct.
- Three independent learners, source ablations, 100 epochs/200 updates, dimensions, normalization, and stage-A mechanical criteria match the decision/common brief.
- World numbering matches the September 6 contract. The runner requires explicit IDs: its default is `world-{seed}`.
- Both successor claim ceilings are present. The disclosure matches verbatim after Markdown line-wrap normalization.
- No explicit TEST opening or outcome-based checkpoint selection appears.

## DEFECTS

1. **Circular sealing (§1).** Change:

   > the two-route runner and model (`.scratch/multi-catfish-v023-two-route-source-training-runner/`, code manifest `<<BIND_AT_FREEZE:runner_manifest_sha256>>`) verify byte-for-byte against the launch manifest `<<BIND_AT_FREEZE:launch_manifest_sha256>>`, and this document verifies against `<<BIND_AT_FREEZE:contract_sha256>>`;

   Replacement:

   > Bind the runner code manifest here; seal the final contract’s file SHA-256 in an external launch manifest, then seal that manifest externally. Neither file embeds its own digest or creates a reciprocal file-hash dependency.

2. **Deployment rule incorrectly encompasses BASELINE (§2).** Change:

   > Deployment rule for all later stages: masked, unweighted `Q1+Q2` argmax over legal actions with the existing fixed tie handling of the current V0.23 carrier; no per-head weights.

   Replacement:

   > Learned arms deploy masked, unweighted `Q1+Q2`, choosing the lowest legal action index on ties; BASELINE deploys exclusively through its unchanged authenticated MODQN adapter.

3. **Incomplete, overlapping dispositions (§6).** Change:

   > Falsifiers and dispositions, evaluated at the `3000`-episode boundary (earlier rungs are reported, never used to stop early or reselect): if `FULL2 ≤ BASELINE` → `C1C2_DEVELOPMENT_PREDICTION_FALSIFIED` (no rescue; a later experiment needs its own declaration); if `FULL2 > BASELINE` but `DROP_C1 ≥ FULL2` → `C1_CONTRIBUTION_UNSUPPORTED`; likewise `DROP_C2 ≥ FULL2` → `C2_CONTRIBUTION_UNSUPPORTED`; if the service condition fails for an arm → `SERVICE_NONINFERIORITY_FAILED` for that arm; otherwise `C1C2_DEVELOPMENT_PREDICTION_HELD`.

   Replacement:

   > At 3000 complete matched episodes, emit exactly one overall result: HELD iff FULL2 exceeds both drops, every learned arm exceeds BASELINE, and every learned served fraction is at least BASELINE minus 0.001; otherwise FALSIFIED, using the existing full token names. Record all applicable nonexclusive reasons: FULL2≤BASELINE, each drop≤BASELINE, each drop≥FULL2, and each service failure. Invalid/incomplete receipts produce an integrity STOP, never a scientific result. Earlier rungs cannot select or stop scientifically; FALSIFIED ends continuation.

   Otherwise a drop below BASELINE can incorrectly receive HELD, and simultaneous contribution/service failures lack defined handling.

4. **Continuation conflicts with runner semantics (§6).** Change:

   > Ladder: cumulative `100 → 500 → 1500 → 3000` episodes per arm with a write-once receipt and checkpoint every `100` episodes; each rung continues the previous one (no restart, no reselection of policies or worlds).

   Replacement:

   > Freeze one 9000-world plan before computation; pause cumulatively at 100, 500, 1500 and 3000 using authenticated every-100 checkpoints, unchanged plan identity and write-once outputs. Intermediate boundaries do not publish terminal result.json. Continue beyond 3000 only after HELD and owner notification.

   The old runner rejects changed plan hashes and resuming an output containing `result.json`.

5. **Late execution freeze (§6).** Change:

   > Runner: a four-arm variant of `.scratch/multi-catfish-v023-physical/v023_physical_episode_runner.py` (currently `BASELINE`/`DROP_C3` only) — new code, manifest `<<BIND_AT_FREEZE:evaluation_runner_manifest_sha256>>`; the stage-C launch has its own preflight and is frozen after stage B passes, without looking at stage-B EE directions.

   Replacement:

   > Bind the new four-arm runner, verifier and complete scientific/execution configuration before any successor computation; after B, preflight only authenticates predetermined outputs and mechanical receipts, without changing the sealed contract.

   The referenced source-runner directory currently does not exist; implementation closure remains unverified.

6. **C3 admission incompletely incorporates governing restrictions (§0).** Change:

   > Nothing observed here selects, tunes or admits a C3.

   Replacement:

   > Neither R7 nor successor outcomes select or tune C3; R7 §7 forbids automatic CSE/EC promotion. Ladder §4 permits separately authorized F0/F1 after STOP_PHYSICS, retaining declared D-before-F priority and independent admission; this contract authorizes no C3 run or selection.

7. **Repair/termination conflict (§8).** Change:

   > A stop at any stage ends this experiment's schedule; it does not authorise another attempt under this document.

   Replacement:

   > A valid scientific stop ends the schedule; an INVALID_RUN permits only documented infrastructure repair and replay of the smallest invalid unit, preserving valid outcomes and scientific declarations.

## MISSING DECLARATIONS

Existing r8, factory, learner, runner, model and evaluation-manifest fields suffice **only with enumerated transitive coverage**. `r8_complete_line` is literal seal content, not another file digest. Remove circular fields as above.

Before sealing, additionally bind:

- Baseline checkpoint `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`, state dimension 112, 9000 episodes, status/authentication digest distinct from policy digest, adapter closure, and empty source routes.
- Initialization bytes; sampler/file order; formulas/objectives/optimizer defaults; launcher, diagnostics, policy adapters and independent verifier; predecessor authority digests.
- PREREG/TLE manifests, world-plan digest, keyed namespace `MCRL_V020_REPRICED_C3_GATE_V1`, RNG policy, environment and resource limits, absent diagnostic/evaluation roots.
- Physical aggregation from `last_outcome`, positive energy, pooled served/opportunity denominator, B’s 100 users, and explicit B/C integrity-failure dispositions.

## RECOMMENDATION

Freeze after these corrections and authenticated implementation closure; no additional scientific thresholds are needed.

ASTRA_CONTRACT_REVIEW=FREEZE_AFTER_FIXES