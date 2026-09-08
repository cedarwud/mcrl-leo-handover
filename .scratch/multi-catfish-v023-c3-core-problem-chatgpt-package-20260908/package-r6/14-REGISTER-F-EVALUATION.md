# Slice F audit — evaluation, estimands, statistics, splits, and ladders

All paths are relative to `/home/sat/mcrl-leo-handover-e1`. This is a read-only audit; no repository state was changed.

## Executive finding

The harness supports narrowly defined, finite-TRAIN development comparisons. It does **not** presently support the broader claim that each component independently and generally improves EE.

The largest problems are:

- Stage-C’s first 100 “new” worlds exactly reuse an opened earlier evaluation panel.
- `HELD/FALSIFIED` is a deterministic inequality gate, not a statistical or sequential test.
- The three learned arms identify only conditional C1/C2 effects under one training seed; there is no all-neutral factorial cell.
- Pooled bits/joules is legitimate fleet accounting, but alone can conceal opposite per-world conclusions, uncertainty, fairness, and whether gains came from bits or reduced energy.
- The finite horizon and cold resets interact directly with the supplied renewal-premium energy model.

## Ranked summary

| Rank | Assumption | Implementation evidence | Documentation | Standard practice / literature | Likely distortion | Magnitude | Verdict |
|---:|---|---|---|---|---|---|---|
| 1 | A pooled ratio alone proves “each component improves EE” | [physical_runner.py:878–951](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:878) | [scientific declaration:112–129](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md:112) | Ratio-of-totals is valid for aggregate throughput/J, but component claims normally also need paired cluster effects and uncertainty | Can reverse every per-episode ordering; hides numerator/denominator, heterogeneity, and fairness | Potentially unbounded | **FIX** |
| 2 | Stage-C worlds are fresh and independent | [world plan:18–23,87–119](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/build_v023_c1c2_successor_stage_c_world_plan.py:18); [age RNG:491–536](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/step.py:491) | [old evaluation contract:20–41](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-physical/V023-DROPC3-DEVELOPMENT-EVALUATION-CONTRACT-2026-09-06.md:20); [successor declaration:107–109](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md:107) | A validation panel should be unopened, standalone-reproducible, and inventoried against training/development use | First-rung selection bias; ambiguous experimental unit | First 100: 100% reused; rung 500: 20%; rung 1500: 6.7%; rung 3000: 3.3% | **FIX** |
| 3 | `HELD/FALSIFIED` are sound sequential tests | [gate:907–951](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:907); [merge barriers:2405–2482](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:2405) | [declaration:120–129](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md:120); [R2:73–97](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-08-R2.md:73) | Sequential inference requires declared nulls, error control and boundaries; a fixed-panel gate may instead make only finite-panel claims | Arbitrarily tiny differences become “HELD”; no sampling or training-seed uncertainty | High | **FIX** |
| 4 | DROP arms establish fair, independent C1/C2 contributions | [arm mapping:448–523](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:448); [baseline:526–568](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:526) | [development contract:59–86](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-DEVELOPMENT-CONTRACT-2026-09-07.md:59); [neutral adapters:16–39](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-neutral-adapters/README.md:16) | A two-component attribution normally uses all four factorial cells and multiple training seeds | Interaction and training stochasticity can be mislabelled as component effects | High; unidentified from current cells | **DECLARE** |
| 5 | TRAIN evaluation adequately represents generalization | [split:183–299](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/ephemeris.py:183); [sampler:381–441](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/ephemeris.py:381) | Same TRAIN split is explicit in [declaration:101–109](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md:101) | Blocked temporal validation requires an embargo justified by measured correlation length; deployment claims prefer forward-time holdout | Same-corpus temporal/ephemeris dependence; no future-period evidence | Unknown | **DECLARE** |
| 6 | A `0.001` service allowance is substantively justified | [Stage-C constants:79–90](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:79); [service definition:96–129](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/service.py:96) | [C3-S contract:83–105](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/V023-C3S-SET-LEVEL-COORDINATOR-KILL-SCREEN-CONTRACT-2026-09-08.md:83) | A noninferiority margin should come from an operationally meaningful outage/demand loss, not convenience | Can accept concentrated outages while reporting near-identical aggregate service | 3,000 Stage-C or 36 C3-S user-steps | **FIX** |
| 7 | Ten-/30-step reset episodes estimate continuing-system policy value | [Stage-C horizon:86–88](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:86); [C3-S horizon:62,821–878](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_screen.py:62); [reset:491–544](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/step.py:491) | [C3-S contract:58–62](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/V023-C3S-SET-LEVEL-COORDINATOR-KILL-SCREEN-CONTRACT-2026-09-08.md:58) | Continuing-task evaluation needs horizon/burn-in/terminal-value robustness | Strong interaction with last-step handovers and renewal premium | Direction uncertain; potentially dominant | **SENSITIVITY** |
| 8 | The verifier is scientifically independent | [verifier:193–311](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/verify_v023_c1c2_successor_stagec.py:193); [age replay:715–749](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/verify_v023_c1c2_successor_stagec.py:715) | [declaration:131–133](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md:131) | Independent replication recomputes physical observables from raw inputs, not merely receipt arithmetic | Shared physics/accounting bugs pass both runner and verifier | Unknown | **DECLARE** |
| 9 | E1 → S0 → C3-S is confirmatory evidence | [C3-S runner:451–555,999–1082](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_screen.py:451) | [E1 contract:13–20](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3-existence-e1/V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md:13); [C3-S contract:128–156](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/V023-C3S-SET-LEVEL-COORDINATOR-KILL-SCREEN-CONTRACT-2026-09-08.md:128) | Adaptive development evidence must be separated from prospective confirmation | Architecture selected using E1/S0; C3-S has only four physical-world clusters | High for generalization; legitimate as development | **DECLARE** |

## Detailed findings and known-answer tests

### F1. Pooled EE is a valid aggregate estimand, but not sufficient attribution evidence — **FIX**

The implementation computes
\[
\hat\eta_a=\frac{\sum_i B_{ai}}{\sum_i E_{ai}},
\]
which is the right answer to “how many total delivered bits did this arm produce per total joule over this finite panel?” It is not the mean world-level treatment effect, the probability of improvement, or evidence that every component or world improved.

It hides:

- separate changes in delivered bits and energy;
- between-world and between-lineage dispersion;
- the number or fraction of worlds that improved;
- optimizer/training-seed variation;
- per-user service concentration and outage runs;
- policy-mediated trajectory differences after the common initial state;
- interaction with the supplied reset-induced energy benefit.

**KAT:** Two matched episodes:

| Arm | Episode 1 `(bits,J,EE)` | Episode 2 `(bits,J,EE)` | Mean episode EE | Pooled EE |
|---|---|---|---:|---:|
| A | `(10,1,10)` | `(100,100,1)` | `5.5` | `110/101 = 1.089` |
| B | `(900,100,9)` | `(0.9,1,0.9)` | `4.95` | `900.9/101 = 8.920` |

A has higher EE in **both** matched episodes, yet B has much higher pooled EE because each arm induces different energy weights. Keep pooled EE as the declared fleet estimand, but report paired world-cluster contrasts, numerator/denominator changes, sign counts, and prespecified uncertainty alongside it.

### F2. The ladder is not a sequential statistical test — **FIX**

The 100/500/1500 rungs cannot stop or emit a scientific disposition; only 3000 emits `HELD/FALSIFIED`, and 9000 is continuation-only. That is good protection against optional stopping, but it means the design is a fixed-panel deterministic gate—not a sequential test.

There is no null hypothesis, sampling model, confidence interval, minimum meaningful EE effect, Monte Carlo error estimate, or treatment of the single training seed. “FALSIFIED” therefore means only “one finite-panel inequality failed.”

**KAT:** Let `ε=10⁻¹²`, `ηBASE=100`, both DROP EEs be `100+ε`, FULL be `100+2ε`, and all service fractions equal. Every coded inequality passes and the result is `HELD`, despite an effect with no demonstrated practical or statistical resolution.

Either rename the tokens to finite-panel `GATE_PASS/GATE_FAIL`, or prospectively specify effect margins and paired cluster inference. If early rungs are ever allowed to decide, add group-sequential error spending or confidence-sequence boundaries.

### F3. Stage-C freshness is false for the first 100 worlds; standalone world identity is also incomplete — **FIX**

The old DROP-C3 evaluation used `world-000001…000100` with seeds `2026090601…2026090700`. Stage-C begins with the same consecutive sequence. Thus all 100 observations at the first rung were already opened; they remain 20%, 6.7%, and 3.3% of later decision panels.

Evaluation also uses TRAIN, as did learning. Exact collision between learner training episodes and Stage-C evaluation episodes is **UNKNOWN** because no complete training-trajectory inventory is checked.

A further reproducibility defect is the persistent cross-episode `_age_rng`: world `k` receives draws after worlds `1…k−1`, so its full initial state is not a function of `world_seed=k` alone. R2 documents this stream at [R2:32–71](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-08-R2.md:32). This need not create material PRNG correlation, but it invalidates the simple “independent standalone world” interpretation.

**KAT:** Run seed `2026090602` alone and then after seed `2026090601`. Epoch, mobility seed, and keyed field remain bound to `2026090602`, but initial segment ages—and therefore the initial-state hash—differ.

Derive every reset stream from the episode’s own world domain, inventory training and prior-development worlds, and never call an opened panel fresh.

### F4. DROP arms are retrained neutral-source replacements, not masks—but identify only conditional effects — **DECLARE**

`DROP_C1` uses neutral C1 plus informed C2; `DROP_C2` uses informed C1 plus neutral C2. These are retrained at equal route-update budgets, which is materially fairer than masking a trained score head.

However, there is no `ALL_NEUTRAL_CONTROL`. The external `BASELINE` is a different pre-Catfish MODQN trained for 9000 episodes, not the missing `00` cell. Therefore:

- `FULL − DROP_C1` identifies the C1 contribution **conditional on informed C2 and this training protocol**;
- `FULL − DROP_C2` identifies the corresponding conditional C2 contribution;
- neither identifies standalone effects, average factorial main effects, or the C1×C2 interaction.

Only one successor training seed is used ([development contract:73–76](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-DEVELOPMENT-CONTRACT-2026-09-07.md:73)), so thousands of physical worlds cannot estimate training stochasticity.

**KAT:** Let factorial EEs be `EE00=200`, `EE10=90`, `EE01=90`, `EE11=101`. Current comparisons both report `101>90`, yet each component’s average main effect is `(90+101−200−90)/2 = −49.5`. Add the retrained all-neutral cell and multiple independently initialized training lineages before using unconditional “each component improves” language.

### F5. The temporal split is suitable only for same-period TRAIN development — **DECLARE**

The split cycles seven TRAIN days, one embargo day, seven TEST days, and one embargo day. Its nearest cross-split separation is only two calendar days. The documentation’s claim that this exceeds the relevant ground-track repeat is unsupported by a measured correlation analysis.

Uniform sampling over available file dates also produces an archive-conditioned target, not necessarily a deployment-time distribution.

**KAT:** For dates `d0…d15`, expected labels are TRAIN `d0…d6`, embargo `d7`, TEST `d8…d14`, embargo `d15`; the closest TRAIN/TEST dates are `d6` and `d8`. A synthetic feature constant over every three-day window will cross that embargo unchanged, demonstrating that the split rule alone cannot guarantee independence.

Keep TEST closed. Describe all current results as TRAIN-development, and justify any future embargo from empirical autocorrelation or use a prospectively frozen forward-time block.

### F6. The service margin is a hard gate but not an operationally grounded guarantee — **FIX**

“Served” means an action survived per-link feasibility; it is not demand satisfaction, minimum-rate service, or fairness. The `0.001` allowance means:

- Stage-C: up to `0.001 × 3,000,000 = 3,000` fewer served user-steps;
- C3-S: up to `0.001 × 36,000 = 36`;
- E1: up to `12` over 12,000 opportunities.

E1’s reported baseline is 11,975 served, so its threshold is 11,963; the U1/J1 witnesses have 11,974/11,972 and therefore have slack ([E1 result:13–17](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3-existence-e1/E1-RESULT-RECORD-2026-09-08.md:13)). It did not numerically bind those selected witnesses. Whether it binds Stage-C is not established here; C3-S has no authenticated run in this checkout.

**KAT:** With one million opportunities and baseline count one million, 999,000 passes exactly and 998,999 fails. All 1,000 allowed losses may be concentrated in the same users or consecutive intervals. Replace or supplement the margin with an operational demand/outage criterion and tail/run-length reporting.

### F7. Own trajectories are correct for total policy value; finite reset horizons still favor a policy class — **SENSITIVITY**

Each arm is reconstructed from the same initial state and exogenous seed, then follows its own endogenous trajectory ([C3-S runner:918–964](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_screen.py:918)). That is correct for estimating a policy’s total closed-loop effect. Forcing identical later states would remove genuine mediated effects.

But matching ends at time zero. Stage-C lasts 10 steps and C3-S 30; resets cold-start incumbent/radiating state, and neither endpoint assigns terminal value to consequences after the last step. This favors policies whose gains arrive quickly and disfavors delayed payback. Under the supplied energy model, a final-step handover can collect the reset/renewal effect without subsequent consequences, making horizon sensitivity mandatory.

**KAT:** Policy A costs one unit at step `H` and yields ten at `H+1`; policy B does nothing. An `H`-step endpoint chooses B, while `H+1` chooses A. Repeat at multiple horizons, include a burn-in or continuation value, and report handovers by step—especially the final steps.

### F8. The verifier is provenance-independent, not physics-independent — **DECLARE**

The verifier rechecks receipt coverage, hashes, world matching, pooled arithmetic, disposition logic, and persistent age-stream replay. It does not independently rerun propagation, rate, power, or service calculations from primitive simulator inputs. A shared error upstream of receipt creation can therefore survive verification.

**KAT:** Synthetic self-consistent receipts containing `(10 bits,2 J)` and `(30 bits,3 J)` necessarily yield `40/5=8 bits/J` in both runner and verifier regardless of whether those figures are physically possible. Call it an integrity/arithmetic verifier; a scientific cross-check must independently recompute selected raw trajectories or observables.

### F9. E1/S0/C3-S is a legitimate development chain, not confirmation — **DECLARE**

E1 is explicitly a finite-panel oracle existence test, not learnability or efficacy. It reports U1 `+1.992311%` and J1 `+2.222094%`; S0 reuses those opened E1 anchors and reports `+1.812631%` ([C3-S contract:7–13](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/V023-C3S-SET-LEVEL-COORDINATOR-KILL-SCREEN-CONTRACT-2026-09-08.md:7)). C3-S was then designed with those diagnostics visible, which the contract properly discloses.

C3-S’s four derived seeds are collision-checked and genuinely new relative to the inventoried worlds. Crossing them with three inherited lineages produces 12 cells, but only **four physical-world clusters**, not twelve independent worlds. Any inference would require crossed world/lineage accounting; four world clusters are too few for stable generalization.

**KAT:** Let four world-level effects be `(+4,−1,−1,−1)`. The pooled mean is positive, but deleting the single favorable world makes it negative. A SUPPORT token would still be a four-world development result.

Moreover, the current C3-S contract says `DRAFT, unsealed` at [contract:1–3](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/V023-C3S-SET-LEVEL-COORDINATOR-KILL-SCREEN-CONTRACT-2026-09-08.md:1), has no `.sha256` sidecar, and is writable, while the runner requires mode `0444` plus a matching sidecar ([runner:250–266](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_screen.py:250)). No authenticated C3-S result can be produced from this checkout in its present state.

## Code/document disagreements and ambiguities

1. `ServiceResolution.served` is described as surviving an “execution mask,” but the module says that mask was removed and service is now per-link feasibility ([service.py:25–31,96–129](/home/sat/mcrl-leo-handover-e1/src/mcrl/env/service.py:25)). Claims must use the implemented meaning.

2. Stage-C documentation calls comparisons “paired”; code verifies only equal world identifiers and initial-state hashes ([physical_runner.py:2559–2572](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:2559)). Pairing is at initial world/exogenous stream, not at later endogenous states.

3. “Independent verifier” overstates its scope: it independently verifies provenance and arithmetic, not simulator physics.

4. Any description of Stage-C’s entire ladder as fresh conflicts with the exact first-100 overlap. The successor document says it extends the 2026-09-06 scheme, but does not state the resulting percentage of already opened worlds.

5. The sealed E1 contract still textually labels itself “DRAFT; unsealed” ([E1 contract:3–5](/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3-existence-e1/V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md:3), despite having a read-only file and sidecar. This is a lifecycle-documentation contradiction, although its result record is present.

## The three assumptions I would overturn first

1. **“Stage-C is a fresh confirmatory ladder.”** Its first 100 worlds are an opened prior panel, all evaluation remains on TRAIN, and full world identity depends on a prefix-carried age stream.

2. **“Strict pooled inequalities establish that each component improves EE.”** They establish only finite-panel, conditional pipeline comparisons under one training seed; pooled weighting can reverse every matched episode result, and the all-neutral factorial cell is missing.

3. **“HELD/FALSIFIED is statistical evidence.”** It is an exact deterministic gate with no effect margin, uncertainty model, independent training replication, or error control—and its finite horizon is especially vulnerable to the model’s terminal renewal premium.