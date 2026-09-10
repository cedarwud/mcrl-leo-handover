The shared-catalogue lookup is sound for the implemented fixed-reference pilot; it is not a verified full-source tier, and per-arm learned seeds can break sharing for DROP_C1, DROP_C2 and all three single-informative arms.

`DIAGNOSTIC_NOT_CLAIM` — 2026-09-10. **The suspected component dependence is real, but the claimed deployed connection is missing.** The V1 proposal/repair helper depends on C1+C2, and the bounded builder depends on its supplied seed. I found no production caller connecting those functions. The existing real-physics pilot supplies a common carrier reference instead. Thus the probe below establishes a counterexample to *assuming equality after per-arm reseeding*, not an observed defect in a completed sealed deployment.

This report distinguishes **read** code, **executed** diagnostic measurements, and **inferred** measurement designs. No training, learner loop, policy rollout, selector ranking run, or acceptance test was run. No constant, threshold, sign, seed, horizon, price, guard, acceptance rule, sealed artefact, manifest or contract was changed. Writes are this report and the unsealed `.scratch/matched-anchor-tier/` diagnostic files; pre-existing workspace changes were left alone.

**Q1. Which outputs determine the seed?**

**Read:** the relevant model is `V1ThreeRouteModel`, with independent `q1`, `q2` and set-conditioned `psi`. Its `score("C1", state)` and `score("C2", state)` dispatch to their respective heads; C3 uses `interaction(context)`. The earlier `ThreeRouteModel` and `construct_reference_proposal` compatibility path are not the basis of this finding. [learner.py:930](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/learner.py:930).

The V1 proposal builder and infeasibility repair are both inside `ProfileSelector.repair_reference`:

1. For each user's legal actions, compute `q1(q1_state) + q2(q2_state)` and take the masked argmax. Ties select the lowest stable action index. **Both C1 and C2 affect this proposal; C3 does not.** [deployment.py:521](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/deployment.py:521), [deployment.py:101](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/deployment.py:101).
2. Return the proposal if jointly legal. Otherwise, filter the **supplied repair catalogue** for joint legality and choose the first strict maximum of the complete profile's summed C1+C2 scores. **Both C1 and C2 also affect repair; C3 does not.** The helper neither constructs that repair support nor calls the bounded builder. [deployment.py:531](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/deployment.py:531).
3. Separately, `_catalogue_with_census(tape, step, base, ...)` accepts the seed configuration. In its bounded branch, it copies `base.mapping` to create unilateral alternatives; computes exact nominal unilateral surplus relative to that base to identify the top users; assembles complete proposals and pairwise moves; and constructs evacuations from beams occupied in that base. Changing the seed can change all these candidate sets. [run_v025_matrix_probe.py:543](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:543), [run_v025_matrix_probe.py:578](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:578), [run_v025_matrix_probe.py:593](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:593), [run_v025_matrix_probe.py:624](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:624).

The proposed composition is therefore:

```text
C1 output ─┐
           ├─ per-user argmax(C1+C2) ─ joint validation/repair(C1+C2) ─ a0_r
C2 output ─┘                                                        │
                                                        [missing runner connection]
                                                                    │
                                                   bounded catalogue around a0_r
C3 output ─────────────────────────────────────────── profile ranking only
```

**Actual callers matter.** `ProfileSelector.select` receives `base_profile` and `catalogue`; it does not invoke `repair_reference`. It ranks supplied candidates using C1/C2 differences plus the complete-set C3 prediction. Searches of current source/scripts found the repair helper's call in the acceptance test, not a production integration. [deployment.py:647](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/deployment.py:647), [deployment.py:717](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/deployment.py:717), [test_contract_v1_acceptance.py:855](/home/sat/mcrl-v025-c1c2suff-ws/tests/stagec_v025/test_contract_v1_acceptance.py:855).

The pilot obtains its reference from `_base_configuration(..., carrier)`, generates its standard catalogue around `carrier_base`, then passes already-built catalogues into a custom arm-scoring loop. That loop does not use the public `ProfileSelector` to construct a learned proposal. Its alternate P-u catalogue is also shared. Hence **none of the three heads changes the pilot's supplied seed at a fixed anchor**. [run_v025_pilot_c3.py:361](/home/sat/mcrl-v025-c1c2suff-ws/scripts/run_v025_pilot_c3.py:361), [run_v025_pilot_c3.py:1622](/home/sat/mcrl-v025-c1c2suff-ws/scripts/run_v025_pilot_c3.py:1622), [run_v025_pilot_c3.py:1642](/home/sat/mcrl-v025-c1c2suff-ws/scripts/run_v025_pilot_c3.py:1642), [run_v025_pilot_c3.py:1687](/home/sat/mcrl-v025-c1c2suff-ws/scripts/run_v025_pilot_c3.py:1687), [run_v025_pilot_c3.py:1524](/home/sat/mcrl-v025-c1c2suff-ws/scripts/run_v025_pilot_c3.py:1524).

There is also an unresolved specification/integration tension: §A3 defines the learned Q1+Q2 reference, while §A4 requires authenticated identical catalogues at matched anchors. The implementation rejects differing catalogue hashes and authenticates BASE against the supplied reference. Those checks establish equality of supplied inputs; they do not prove equality of independently generated per-arm catalogues. I have not bypassed or changed them. [contract:8](/home/sat/mcrl-v025-c1c2suff-ws/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md:8), [interfaces.py:258](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/interfaces.py:258), [deployment.py:569](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/deployment.py:569).

**Q2. Which arms can have different catalogues?**

**Read:** neutral substitution changes training targets while preserving route inputs/support. All three heads are retained and updated in every learned arm. A common initialization is cloned, and each head is updated only from its own route's selected source. There is no C3-training gradient path into q1/q2. A neutral-trained head is not a hard-zero deployed contribution. [learner.py:30](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/learner.py:30), [learner.py:146](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/learner.py:146), [learner.py:634](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/learner.py:634), [learner.py:995](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/learner.py:995), [learner.py:1025](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/learner.py:1025).

**Inference from those functions:** the following table applies **if each arm's A3 proposal feeds the bounded builder**, at identical prefix, features, seed lineage and source epoch. `ONLY_Cx` is descriptive shorthand for the owner's requested source combination, not an added sealed arm; every head remains deployed.

| Arm | Sources C1/C2/C3 | Can differ from FULL? | Path |
|---|---|---|---|
| DROP_C1 | neutral / informative / informative | Yes | C1 changes proposal and/or infeasibility repair. |
| DROP_C2 | informative / neutral / informative | Yes | C2 changes proposal and/or infeasibility repair. |
| DROP_C3 | informative / informative / neutral | No at this matched prefix | q1/q2 remain identical; C3 only affects subsequent ranking. |
| ONLY_C1 | informative / neutral / neutral | Yes | Neutral C2; same seed family as DROP_C2. |
| ONLY_C2 | neutral / informative / neutral | Yes | Neutral C1; same seed family as DROP_C1. |
| ONLY_C3 | neutral / neutral / informative | Yes | Both neutral; same seed family as ALL_NEUTRAL_CONTROL. |

For the **existing fixed-reference pilot**, the supplied catalogue is shared across its implemented learned arms. The three ONLY arms are absent. The table is not a claim that the current runner already implements their per-arm proposals.

“Can differ” is essential: outputs may change without changing the argmax or repaired profile. The complete-Cartesian branch can also enumerate the same physical set despite different seeds. [run_v025_matrix_probe.py:559](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:559). In a closed loop, even DROP_C3 can change later seeds/catalogues through its earlier committed choices and changed history; the runner advances each arm's previous profile separately. [evaluation.py:1003](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/evaluation.py:1003), [evaluation.py:1055](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/evaluation.py:1055).

**Q3. What does a matched-anchor tier measure?**

Let `h` contain the complete common prefix and current exogenous physical state; let `s_F(h)` be FULL's validated seed. Hold that seed, catalogue, features, reference-dependent contexts, guards, tie rules and fallback fixed. For arm `r`, let `a_r_fixed(h)` be its retained three-head selector's choice under those fixed inputs. The pooled endpoint is

```text
EE_r_fixed = sum_h w_h B(h, a_r_fixed(h)) / sum_h w_h E(h, a_r_fixed(h)).
```

Contrasting these pooled ratios measures the **conditional one-step ranking effect of source training at FULL's fixed seed**, on the declared anchor distribution. It excludes the effect transmitted through that arm's own proposal, repair, candidate coverage and subsequent trajectory. Anchors drawn from FULL's history remain a FULL-history conditional experiment. This is not the mean of per-row EE values.

Fixing the **catalogue alone** is a different intervention: an arm-specific seed can still change C3's changed-user set/context, BASE tie preference, guards and fallback. The selector explicitly authenticates reference-relative coalition contexts and considers BASE first. A fixed-seed ranking diagnostic must fix these inputs too. [deployment.py:598](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/deployment.py:598), [deployment.py:714](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/deployment.py:714), [deployment.py:738](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/deployment.py:738).

**Requirement coverage: partial mechanism evidence, not the owner's full requirement.** Neither the three sealed source marginals nor the three requested single-informative closed-loop pooled-EE comparisons are established by this tier. C2 can change the immediate selected action, so its one-step contrast need not be zero; however, its three-offset continuation benefit is unmeasured. Its target explicitly accumulates future outcomes and absorbing losses. The reviewer's C2 limitation is valid, but fixing histories also limits interpretation for C1 and C3. [targets.py:251](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/targets.py:251), [contract:21](/home/sat/mcrl-v025-c1c2suff-ws/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md:21), [contract:29](/home/sat/mcrl-v025-c1c2suff-ws/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md:29).

**Q4. A correct cheap diagnostic, and measured overlap.**

Two distinct diagnostic constructions are valid:

- **Fixed FULL seed:** run the explicitly labelled ranking sub-question above. Shared outcomes are legitimate under identical physical inputs. This is the implemented pilot's general kind of comparison, although its reference is a carrier rather than FULL's learned proposal.
- **Each arm's own seed and catalogue, shared physical cache:** preserve each arm's proposal/repair, candidate restrictions, reference contexts and score. Evaluate a physical configuration only once per identical physical context, then let each arm look up outcomes for its own candidates. This captures proposal plus ranking effects on the common prefix, still not closed-loop effects. It is a sound diagnostic composition; it is not an already-authenticated implementation of the unresolved §A3/§A4 contract.

The union is a **cache workload**, not a new search catalogue offered to every arm. Offering the union to every arm would change candidate coverage and the measurement. For the cheapest one-step pooled-EE comparison, compute each choice from its permitted nominal information and realise only the union of chosen configurations: at most nine outcomes per anchor. Realising every catalogue row is needed only for additional candidate-outcome/regret questions. Cached realised outcomes must never leak into selection.

Use canonical complete `(user_id, physical action)` assignments within a key that also binds tape/world, time, physical/run settings, evaluator/code identity, nominal-versus-realised field, boundary set and relevant prefix/transition history. Ordinary `CFG:` IDs encode assignments, but `BASE:` IDs contain carrier names, so raw IDs alone are not universally safe across reconstructed seeds. [run_v025_matrix_probe.py:402](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:402), [run_v025_matrix_probe.py:527](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:527).

`StepEvaluator` already caches configurations within one evaluator context. Reuse numeric physical results, retaining each arm's own `changed_users`, candidate kind, C3 context and reference-dependent scores. Scalar evaluation uses the transition ledger; prefix-sensitive accounting cannot be cached by configuration alone. Catalogue generation itself creates a nominal evaluator and pays for base/unilateral evaluations, so endpoint caching alone does not share all work. [run_v025_matrix_probe.py:763](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:763), [run_v025_matrix_probe.py:793](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:793), [run_v025_matrix_probe.py:903](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:903), [run_v025_matrix_probe.py:593](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:593).

**Executed:** [probe.py](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/matched-anchor-tier/probe.py) rehydrated existing PILOT_NOT_CLAIM epoch-2000 checkpoints for learner seed `5166716249291843642`; no fitting or parameter perturbation occurred. It read source anchors 000/003/006 from `V025_PROBE/world/1`, corresponding to physical steps 0/1/2, with 100 users and the nearest-eligible reference. The world seed remained `5261619120743994529`; the provider retained its canonical world construction. Only three physical steps were sampled, without evaluating a shortened continuation or policy horizon.

All five existing learned checkpoint payloads were compared: the non-intervened route payloads matched FULL exactly. FULL and DROP_C1 supplied the two catalogue parameterisations; proposal differences were also computed for DROP_C2, DROP_C3 and all-neutral. The actual V1 proposal helper's legal-return branch was called after exact joint-physics validation of those two proposals. Both proposals were valid at all three anchors. The infeasible repair branch was **read, not exercised**; no repair support or service rule was invented.

| Physical step | Users changed: DROP_C1 vs FULL | Users changed: DROP_C2 vs FULL | FULL catalogue | DROP_C1 catalogue | Intersection | Union | Jaccard |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | 26 | 61 | 908 | 910 | 0 | 1,818 | 0 |
| 1 | 12 | 69 | 911 | 912 | 0 | 1,823 | 0 |
| 2 | 12 | 29 | 910 | 909 | 0 | 1,819 | 0 |

DROP_C3 changed **zero** proposed assignments at every anchor. All-neutral changed 86, 92 and 64 respectively. Counts compare complete physical assignment identities in the builder's raw bounded catalogues, before final service filtering. Across these anchors, the two-catalogue union contained **5,460 configurations versus 2,729 for FULL alone: 2.0007×**, with **zero cross-arm reuse** for this pair. This demonstrates that reseeding need not produce even approximately shared coverage. It does not estimate overlap for the claim panel, other seed lineages, or every arm pair.

For cost only, eight deterministic rows from each catalogue were evaluated using the existing dense exact physical evaluator, its unchanged `a-r0` setting and all 48 realised boundaries. All 48 sampled profiles were valid. Repeating the valid lookups added **zero** boundary evaluations. The historical C3 checkpoint's architecture description differs from the current label; numeric payload restoration was checked, and **no C3 inference or ranking was attempted**. These are pilot-head/real-anchor component measurements, not current-model deployment conformance or source-benefit evidence. Checkpoint/shard hashes, the engine hash and detailed timings are in [results.json](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/matched-anchor-tier/results.json); execution output is in [probe.log](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/matched-anchor-tier/probe.log).

The successful command was:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/matched-anchor-tier/probe.py
```

That interpreter/dependency environment was used read-only with bytecode writes disabled. The workspace interpreter lacked NumPy; no environment was installed into or modified.

**Q5. Cost relative to one closed-loop arm.**

**Executed cost:** the successful probe took **99.75 s**, including **48.64 s** to construct the physical tape prefix. Six bounded catalogue builds took **41.29 s** total, with individual times **3.17–10.41 s** and median **7.12 s**. Each build performed **701 nominal boundary evaluations**. The three 16-profile realised batches took **0.863, 0.951 and 3.594 s**: 48 profiles × 48 boundaries, **2,304 boundary evaluations**, in **5.41 s**. Repeated batch lookups took roughly 3–4 microseconds each. These small-batch timings do not justify a linear whole-catalogue wall-time forecast.

**Defensible scale estimate:** the user's panel and the executable allocation checks imply `160 × 12 × 2 × 30 = 115,200` decisions per closed-loop arm. Three extra arms add 345,600 decisions, a 50% increase over six arms. The code checks 12 seeds and 30 steps. A separate v1.1 amendment says 16 seeds; I preserve that discrepancy rather than silently choosing a new panel. At 16, the denominator becomes 153,600 decisions per arm. [evaluation.py:214](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/evaluation.py:214), [evaluation.py:926](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/stagec_v025/evaluation.py:926), [v1.1 amendment:14](/home/sat/mcrl-v025-c1c2suff-ws/V025-STAGES-6-8-CONTRACT-v1.1-AMENDMENT-2026-09-09.md:14).

Let `K` count sampled anchor–learner-seed pairs, and `r_h` be the total nine-arm diagnostic cost at anchor `h` divided by the mean cost of one decision in the closed-loop panel. Then, excluding new training,

```text
T_tier / T_one_arm_panel ≈ sum_h r_h / 115,200 + unmatched setup / T_one_arm_panel.
```

For **20 anchors per each of 12 seeds**, `K=240`. Under the explicit assumption that each arm's diagnostic work costs one average panel decision and there is no sharing, nine arms cost **2,160 decision equivalents, or 1.875% of one arm's full panel evaluation**. This is a workload estimate, not a measured wall-time speedup or a statistical-power guarantee. Sharing can reduce it; extra exhaustive realised-row evaluation can increase it substantially. On the three measured anchors, the union contained about twice FULL's candidate identities; evaluating every union row would require about twice as many configuration evaluations, before batching effects. No full-density panel workload was measured.

There are two further savings supported by the learner structure:

- At one common prefix and lineage, eight informative/neutral combinations have at most **four C1/C2 seed families**: I/I, N/I, I/N and N/N. C3 changes ranking, not the seed. In particular, each requested ONLY arm shares a seed family with an existing DROP or all-neutral arm. Its additional catalogue work can therefore be zero **if those existing per-arm families are already computed**; this does not mean every family costs one shared catalogue. BASELINE follows its external policy.
- The independent fixed-source training permits **inferred reuse of retained head states**: ONLY_C1 can combine FULL.q1, DROP_C2.q2 and DROP_C3.psi; ONLY_C2 can combine DROP_C1.q1, FULL.q2 and DROP_C3.psi; ONLY_C3 can combine DROP_C1.q1, DROP_C2.q2 and FULL.psi. With matching initialization, source/batch identities and update dose, these are the same route-local trained states, not knockouts. No composite arm or checkpoint was created. Their authentication and deployment integration remain unimplemented.

Thus adding the three source combinations to an already cached six-arm matched-anchor diagnostic need add only scoring and any newly selected realised outcomes; it need not add catalogue families. This supports cheap **incremental** arms without assuming nine arms share one catalogue.

The main cost drivers are tape construction, feature/forecast computation, nominal catalogue construction and validation, reference-dependent C3 contexts, per-arm ranking, realised evaluation of distinct selected configurations, and deadline/fallback accounting. A cache accelerates offline outcome computation; it does not establish equal operational latency or permission to remove timeout outcomes. Even a completely shared physical catalogue still requires distinct learned scores. An existing independent oracle harness reported 48.07 s per anchor, of which 45.42 s was dense physics, but that is **read evidence from a different selector**, not a timing of this V1 source experiment. [EVAL-HARNESS-2026-09-10.md:206](/home/sat/mcrl-v025-harness-ws/EVAL-HARNESS-2026-09-10.md:206).

**Not reached:** an integrated, conforming per-arm A3-to-catalogue runner; resolution of the A3/A4 or 12/16-seed discrepancies; an executed infeasibility-repair witness; overlap for all arm pairs/learner seeds/dates; full catalogue realised endpoints; a ranking comparison; continuation or closed-loop pooled EE; deadline-inclusive latency; or any evidence that a route improves the sealed acceptance endpoint. No cheap construction here replaces that endpoint. The measured result is narrower and concrete: retained neutral-C1 training changed the proposal, and feeding those changed proposals into the unchanged bounded builder produced disjoint catalogues on three real anchors.
