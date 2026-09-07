## VERIFIED

References: **H** = [handoff audit](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-controller-handoff-20260907/HANDOFF-EXECUTION-CLOSURE-AUDIT-2026-09-07.md); **S** = [100E V2 contract](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md). Other filenames refer to the packages named in the request.

- Local receipt hashes match the R7 manifest, whose digest matches `COMPLETE`. The result records `integrity_status=VERIFIED`, `c3_decision=STOP_PHYSICS_R7`, `no_rescue=true`. The earlier adjudication traces all six corrections without changing the physics predicates. [`r7-sealed-receipts/result.json`: named fields; earlier adjudication:18–29.]
- V2 requires R7 GO; accepting this STOP would violate its admission rule. [S:47–65; `v023_post_r7_provider_factory_v2.py:632–657`.]
- The latest local record reports r8’s 16 shards running since approximately 12:56 UTC, six benchmarks completed, and independent target-generation authorization. **Current server activity and sealing were not rechecked.** [H:511,520.]
- Measured generator costs are approximately 189 seconds loading, 25 seconds setup, and 0.106/0.164 seconds per C2 full-cohort row; completed r5 shards took 80–178 minutes concurrently. These are **not learner or episode throughput measurements**. [H:410–415,453–461.]
- The existing model constructs three networks/optimizers; the source runner hard-codes five arms and three routes. The episode runner supports only 100/500 and explicitly records `learner_update=false`, `episode_training=false`. [`ee_axis_lcsrs_three_route.py:242–275`; `v023_five_arm_source_training_runner.py:59–69`; `v023_real_five_arm_episode_runner.py:71,770–772`.]
- Reported regression evidence includes 18 adapter tests, seven runner tests, 60 bundle tests, and a real 525-row Q2 update taking 0.15 seconds. The rehearsal documents unresolved checkpoint decoding and Q2-call compatibility. These checks were not rerun here. [H:495–511; `REHEARSAL-README.md:27–46`.]

## INFERRED

**High confidence:** Route C reaches genuine **C1/C2 source learning** as soon as A while preserving the owner’s three-Catfish research goal. B adds an admission experiment of unknown duration and outcome. Neither C nor A establishes three-Catfish training.

**High confidence:** Removing the failed mechanism is an outcome-informed scope change, eligible when disclosed and prospectively bounded. It becomes prohibited selection when residuals, favorable worlds, or successor outcomes determine mechanisms, parameters, exclusions, or reintroduction. A new contract alone does not erase such selection.

**Low confidence:** Calendar estimates beyond first source learning remain engineering allowances; current episode throughput is unavailable.

## DECISION

1. **Adopt Route C.** Close R7 and its conditional five-arm launch permanently. Establish the independent C1/C2 successor; keep C3 outside its critical path. Exercise the delegated authority without asking the owner.

2. **Carry this exact disclosure sentence:**

   > “Following the pre-registered STOP_PHYSICS_R7, we closed the LC-SRS successor and prospectively declared a separate C1/C2-only development experiment with unchanged C1/C2 definitions; this outcome-informed scope change does not rescue R7 or establish three-Catfish efficacy, and R7 residuals and successor outcomes are not used to select formulas, signs, thresholds, seeds, horizons, lambda, budgets, or acceptance rules.”

3. **Freeze the scientific declaration before any successor learner computation, including its diagnostic.** Specify:

   - Existing C1/C2 physical formulas, normalization, objectives, architecture and optimizer constants; deployment by masked, unweighted `Q1+Q2`, with fixed tie handling.
   - Three independent two-head learners: `FULL2=(informed,informed)`, `DROP_C1=(neutral,informed)`, `DROP_C2=(informed,neutral)`. Define drops as retrained source ablations. Bind the fourth physical arm, `BASELINE`, to the unchanged pre-Catfish MODQN artifact; do not train or rename an all-neutral baseline.
   - Prediction `FULL2 > each drop > BASELINE`, physical EE estimand, service constraints, falsifiers, numerical decision rules and all failure dispositions. Keep mechanical passage separate from efficacy.
   - Retain the existing outcome-unopened source train seed `2927175120652069826`; freeze initialization bytes, sampling/file order, independent optimizer storage, and prospective TRAIN-evaluation world/seed policy without outcome-based replacement.
   - Exactly 100 source epochs, `C1→C2`, hence **200 updates per learner**; initial and epoch-100 checkpoints. Freeze the cumulative episode ladder, the role of 1500, mandatory 3000 boundary, every-100-episode checkpoints, and notification before entering 9000.
   - TRAIN-only inputs, development claim ceilings, verifier code, controller/Astra decision authority, environments, resource budgets, absent output roots, manifests and independent review. Bind actual r8 seal digests once available, before consumption.

4. **Implement factory v3 as a new C1/C2 provider, not a relaxed v2.** Give sol this scope:

   - Closed configuration: successor schema/contract digest, exact r8 root and manifest/receipt digests, learner-manifest digest, model/config digest, seed and 100-epoch budget.
   - Call `load_completed_target_artifact`; authenticate `COMPLETE`, every file, both modes, all 16 expected mode×world shards, producer provenance, formula constants, dimensions, masks and row bindings. Recheck hashes after loading.
   - Authenticate the learner closure separately, including loaded module origins. Preserve historical producer provenance.
   - Expose deterministic `next_batch(route, source, update_cursor)`, identity, budget and sampler save/restore. Bind consumed-file order and all input/code/config digests into identity.
   - Deliver C1 raw surplus for its existing single normalization; deliver C2 normalized `target_delta` unchanged. Reject C3/R7 configuration, TEST, missing modes, drift and fallback providers. Require no R7 admission dependency.

5. **Create the remaining successor code and reuse only compatible components.** Reuse byte-identical sealed targets, target-loader functions, Q1/Q2 network implementations, and compatible simulator components. Create new two-route model/trainer/checkpoint schemas, scheduler, orchestrator, source runner, launcher/preflight/sealer, diagnostic and physical-policy adapter. The adapter’s existing scheduler also requires C3 (`target_batch_adapter.py:1355–1431`); do not reuse it unchanged. Preserve every frozen predecessor.

   Define the immediate episode ladder honestly as **fixed-policy development evaluation after genuine source learning**. Actual episode-based learning additionally requires a frozen rollout-to-update schedule and implementation; the existing runners do not provide it.

6. **Require offline real-artifact closure before long execution.** Reuse adapter authentication/normalization tests, producer-derived fixtures, resume/isolation tests, launcher acknowledgements and diagnostic mutation checks as regression evidence. Add successor-specific negatives proving Q3 absence and baseline separation. Exercise sealed r8→v3→updates→export/reload→exact continuation→matched real-world stepping, including baseline. Historical green tests cannot certify these new interfaces.

7. **Parallelize preparations now.** Assign **non-heavy** contract/factory/model work, launcher/verifier review, baseline-binding audit and C3 independent-justification drafting to isolated new paths. Keep existing artifacts untouched. Continue already-authorized **heavy** r8 work on Ubuntu. Queue later heavy diagnostics/training there without competing with r8’s approximately 77 GB footprint. Admit C3 later only through its own gate and a separately frozen five-arm contract, without selecting from two-route outcomes.

## ESTIMATE

Planning origin: approximately **13:20 UTC, September 7**. Assume r8 seals at the supplied 15:30–16:00 UTC estimate, implementation starts immediately, and no scientific stop occurs. Historical shard timing makes that seal estimate plausible, not verified.

| Milestone | Optimistic | Expected | Pessimistic |
|---|---:|---:|---:|
| First formal 100E learner update | 3–6 hours | 6–12 hours | 24–72 hours |
| Episode-evaluation ladder starts | 8–16 hours | 1–3 days | 4–7 days |
| 9000 cumulative episodes per arm | Ladder start + `10τ` hours | Ladder start + `10τ` hours | Ladder start + `10τ` hours |
| Genuine three-Catfish training | No defensible date | Admission-dependent | May never qualify |

Here `τ` is measured average seconds per arm-episode, including reset, scoring, stepping and amortized checkpoint costs, assuming four serial arms and one lineage. Thus `τ=10` means another **100 hours**; it is an illustration, not measured throughput. Additional lineages multiply compute.

The source estimate assumes 100 epochs complete within roughly two hours after loading. Expected/pessimistic allowances include newly exposed consumer boundaries; they are not statistical confidence intervals.

**Make one timed real-artifact vertical-slice measurement:** v3 load → one source epoch → export/reload/resume → one matched four-arm world. Record phase timings separately. This measures source cost and `τ`; §9 cannot substitute for it. Scientific failure terminates the schedule rather than authorizing another attempt.

**Controller decision line:** “Execute Route C through a fresh C1/C2 contract; preserve R7 STOP, keep C3 independently gated, and require real-artifact consumer closure before launch.”

**Owner answer:** “We can start real C1/C2 learning without waiting for another C3 attempt. Budget 6–12 hours for the first formal update and 1–3 days for episode evaluation, subject to r8 sealing and integration checks. We cannot honestly date 9000 episodes until we measure the real runtime, or promise three-Catfish training before a new C3 source qualifies.”

ASTRA_SUCCESSOR_ROUTE=C