# Concept harvest, cluster D: docs / explainer packages / late handoffs (old project, Jul–Aug 2026)

Worker: read-only extraction. Source root: `/home/u24/papers/modqn-paper-reproduction/` (paths below are relative to it).
Convention: "SAYS" = quoted or paraphrased from the record; **[I]** = my inference, used only where the records are silent or thin.

## Progress (resume marker)
- [x] docs/catfish-explainer-package (00–09, 99; 08 and WEB-AGENT-PROMPT skimmed: figure spec / prompt only, no new concepts)
- [x] docs/dqfd-env-viability-dr-package-2026-07-18 (3 files)
- [x] docs/PROJECT-STATE-AND-FAILURE-LEDGER.md, CURRENT-STATE.md
- [x] docs/CATFISH-DESIGN-HANDOFF-2026-08-21.md, docs/HANDOFF-GPT-CATFISH-DEV-2026-08-23.md
- [x] catfish-review-2026-08-21 adjudication + orchestrator errors
- [x] capacity-penalty package (00, 01, 02, 04, 05, 99 read; 03 grep-skimmed; ASK prompt not needed)
- [x] MCRL-NEW-PROJECT-SDD-01, RULING no-beam-count-cap, ADR-002/003 (skim)/004/007; DECISION-RECORD-2026-08-21 consulted for B-items
- [x] failure-route-ledger, DEAD-LINE, OPEN-QUESTION zscore, REORG, thesis-defense positioning
- [x] research/ subfolders (skimmed: new-algorithm handoff; route-A README, 5-layer narrative, ACRM brief + decision record, NO-GO conclusion, SDD headings; angle-aware README, catalog, role SDD, gate-B retraction, inspiration A/D; deepresearch convergence synthesis; coordinated provenance headings; modqn-faithful-ablation Phase-I SDDs + LR adjudication + load-fairness note)
- [x] repo-root files (catfish-v2-theory, catfish.md = explainer-package planning note, v2 brief, governed-dissent SPEC = process only, new.md = 06-18 fork stance, 3catfish package, web-agent coordinator pack 00)
- [x] handoff carry-forward section (at end of file)
- Not opened: every *.log codex transcript; 09-sensitivity-sweep / 07-HOBS sibling SDD bodies (>800 lines each; concept covered via ledger); per-file JSON preregs; analysis/ outside cluster (except three catfish-v2 verdict heads, for the D-47 verdict)
- COMPLETE (2026-09-11). Entries D-1…D-65 + carry-forward section.

---

## Shared run-condition block for the Jul-2026 "catfish-v2 / shared_q_isolation / fulldqfd" line (referenced below as COND-FB-JUL)

What the records SAY, pooled from `docs/catfish-explainer-package/01-pipeline-walkthrough.md`, `02-collapse-mechanism.md` and `docs/dqfd-env-viability-dr-package-2026-07-18/01-ENV-MECHANICS.md`:
- **Env:** `family_b` (`FamilyBStepEnvironment`). U=100 users, L_w=4 window satellites x 7 cells = 28 actions per user (relative catalog: own cell + 6 axial neighbours per satellite rank). **k_cap=3 beams per satellite, chosen by demand rank**, so at most 12 beams network-wide; a user on a cell outside the top-3 is "cap-bumped" and gets throughput 0, r1=0 (`02-collapse-mechanism.md:42-67`). Episode length: explainer says 10 steps (`07:214`); DQfD package says T=20 (`01-ENV-MECHANICS.md:7`). The records disagree; both describe family_b.
- **Physics (pre-2026-08 contract, now archived):** `P_beam(L)=min(0.25+0.35*sqrt(L),10)` W per active beam (**load-concave power**), plus a per-satellite aggregate cap of 19.95 W. Power is angle-independent after the 2026-07-03 fix. Off-axis gain `G_T(theta)` (Bessel J1/J3) enters SINR only. Rate `R_u=(B/3)/L*log2(1+SINR)`. So `r1=eta_u=(B/3)log2(1+SINR_u)/P_beam(L)`, strictly decreasing in beam load (`01:242-272`). Fading: Rician K=20 dB, drawn fresh each step after the action; the observation carries the previous step's channel. **No handover energy term.** r2 is a handover penalty (0 / -0.5 / -1.0). r3 = -(max-min)/U of active-beam throughput (`01-ENV-MECHANICS.md:27-40`).
- **Old-contract caveat:** `CURRENT-STATE.md` (2026-08-20) says every EE-trained checkpoint, replay/pool and result from this era is "HISTORICAL — INVALID FOR CURRENT PROTOCOL". The active contract is now single-SINR with a 2 W start per link segment and a gain-ratio recurrence. Load-concave power is "historical or explicit negative controls only" (`CURRENT-STATE.md:74-76`).
- **Metric:** `argmax-EE` = per-user greedy argmax deployed closed-loop on a frozen 48-episode harness (`SEED=20260626`). `EE = family_b_eta_r1/1e6`, i.e. the **mean over users and steps of per-user eta. This is a mean of ratios, not the pooled ratio of sums** (`02-MEASUREMENTS-LEDGER.md:1`, `99:81-83`). Second axis: `min_cov`. Diagnostics: `cap_bump`, `argmax_distinct` (target about 12 = k_cap budget), `J_w`. The two-axis Pareto rule vs the BC k-NN bar was frozen by codex G6 CODE-9 (`09:85-98`).
- **Learner:** shared 3-head MODQN (EE/HO/load heads), scalarisation `w=[0.5,0.3,0.2]`, Double-DQN 1-step, per-head gamma `[0.0,0.9,0.9]` in fulldqfd. **Older arms had gamma1=0.9, measured -55 EE** (`01:147-154`). Input is 448-dim = raw224 plus live cross-user z-score. Raw224 = base140 + chi84. Trained **from scratch** (no distillation from a frozen main).
- **lr:** fulldqfd Group A/C ran lr=0.01 and lr=1e-3 as co-primaries (`05:343`). The 07-18 ledger says lr=1e-3 is the converged setting and that "lr=1e-2 … diverges": OFF peaks around ep300–400 and decays to 0.58–0.65 of peak (`02-MEASUREMENTS-LEDGER.md:14`). The 3-seed C2/C4/C4m landmarks predate this. Their lr is not stated in this cluster [I: probably the 0.01 default].
- **Trainer defects (items 6):** the records in this cluster are silent on per-head own-argmax bootstrap and the outage free ride. They do note that the **TD target `a'`, the rollout, checkpoint eval and best-ckpt selection all used the coordinated `decode`, not argmax, in older arms** (`01:216-231`). They also record a checkpoint-selection knob larger than seed noise: within-arm checkpoint swing median 71.6 / max 139.3 EE vs sigma_seed 54.9 (`09:312-336`). Cap-bumped users get r1=0 (the outage is priced at 0 in r1). r2/r3 for unserved users are not stated.

---

### D-1. Demo injection into replay, DQfD-style with large-margin loss (fulldqfd `ON`; older cell `C4`)
- mechanism (one line): A zero-learning specialist's transitions (`F-mean` pool) replace rho=0.30 of each minibatch. A large-margin loss `J_E=max_a[Q_w+m*1(a!=a_E)]-Q_w(a_E)` acts on the demo slice. Adds 8000 demo-only pretrain steps and L2 1e-5.
- intervention point: experience + penalty/loss
- defined in: `docs/catfish-explainer-package/05-full-dqfd.md:10-81`; config `configs/shared_q_isolation/v3/fulldqfd_ON.yaml`; loss `injection_rung1/margin.py:49-68`
- run status: ran. C4: 3 seeds (coordinated `corrected` decode, gamma1=0.9, fixed m=0.8, pool of trained-DQN self-demos EE 454–523). fulldqfd Group A: 4 configs x 6 seeds, 3000 ep. Later: 6 seeds x 12000 ep at lr=1e-3 (`02-MEASUREMENTS-LEDGER.md` L1).
- run conditions: COND-FB-JUL; metric argmax-EE (mean-of-ratios) + min_cov; lr 1e-3 (L1) and 0.01 (Group A co-primary); trained from scratch; teacher = F-mean (joint-state heuristic, EE 636.05). `scale_mode: qw_sd` margin.
- recorded outcome: L1 (6 seeds, 12000 ep, lr=1e-3): OFF 523.78 vs ON 440.63. "Paired ON−OFF = −83.15, ON worse in 6/6 seeds; best ON seed (459.8) < worst OFF seed (474.0)". ON served 0.72 vs 0.89, min_cov 0.57 vs 0.78 (`02-MEASUREMENTS-LEDGER.md:6-16`). At lr=1e-2 "BOTH arms are sick… the pair difference at lr=1e-2 is +129.97 in ON's favor". Older C4 (3 seeds) 386.8 vs C2 357.1 (`05:305-311`).
- LATEST verdict + revisions: the explainer (07-15) says no quotable number yet (`09:24`). The 07-18 ledger gives ON worse than OFF 6/6 at lr=1e-3. The lr=1e-2 "ON helps" reading is a sick-baseline artifact [the ledger frames it that way; the verdict wording is mine]. Algebraic ceiling "grounded": "any m ≥ 0 pins demo action as argmax ⟹ structurally capped at the expert" (`05:176-240`).
- recorded cause: the structural imitation cap (`05:225-232`). Margin scale: "0.8 / 4.2461e-4 = 1,884×", loss ratio 7.85 fixed vs 1.77 qw_sd (`05:117-141`). `qw_sd` "fixes magnitude only, not the structural cap" (`09:183-192`).
- inferred cause [I]: in L1, ON loses coverage (min_cov 0.57) while roughly matching distinct actions (12.3). That fits cloning a **joint-state teacher from per-user obs**: demo actions are a function of other users' assignments, which per-user obs cannot see (`01-ENV-MECHANICS.md:60-61` "none is a function of obs_u alone"). Correlated same-direction errors then flip k_cap demand ranks (`04:250-253`).
- premises: collapse exists and is an exploration/fixed-point failure; a better-than-learner teacher exists (F-mean 636 >> learner). The teacher's actions must be learnable from per-user observations. The reward penalises crowding (`r1` decreasing in load).

### D-2. Demo-injected TD without margin (fulldqfd `ONnm`; older cell `C4m`; "RLPD-family", not DQfD)
- mechanism (one line): Same demo pool and same rho=0.30 replacement, but pure TD. No margin; in the later L7 design also no pretrain and no L2. The hope is that TD finds actions better than the demonstrator.
- intervention point: experience
- defined in: `05-full-dqfd.md:326-373`; `06-cdrl-continuous.md:104-151`; `99:32-34`; prereg `analysis/family-b-collapse-diagnosis/FULLDQFD-GROUPC-PREREG-2026-07-14.md`
- run status: ran. C4m: 2 seeds (confounded). Group C: 6 seeds x 2 lr x 3000 ep, queued 07-14. L7: 6 seeds x 12000 ep, "in-flight" 07-18.
- run conditions: COND-FB-JUL; argmax-EE + min_cov, same-contract BC bar; lr 0.01 and 1e-3 co-primary; from scratch; F-mean teacher.
- recorded outcome: C4m = 236.1 {247.9, 224.2}, "the worst cell", n=2, p=0.10, not significant, with four confounds (`05:300-319`). The accepted transitions in the pool scored EE 608.1, above the learner's 463–540 band: "there is headroom, and margin-OFF still fell to 236" (`05:317-319`). Offline demo-only without a supervised term: `argmax_distinct=1.0`, EE 108.9. Online: distinct 4.5–4.8 (`05:102-110`).
- LATEST verdict + revisions: open as of 07-18 (L7 "results pending"). This cluster's docs contain no Group C or L7 numbers; they may be in `analysis/…/FULLDQFD-*` (other clusters).
- recorded cause: the "discrete transplant" problem. "a demo labels 1 of 28 actions ⟹ the other 27 get no gradient ⟹ argmax degenerates" offline; online epsilon-greedy anchors them partly (`06:68-100`).
- premises: exploration anchors the 27 undemonstrated actions well enough; TD over the true reward can exceed the demonstrator; the demonstrator is better than the learner.

### D-3. DQfD pretrain (demo-only gradient steps before env interaction) + L2
- mechanism: 8000 demo-only TD(+margin)+L2 steps before any env step, so the agent does not start inside the collapse fixed point.
- intervention point: experience (warm start) + penalty/loss (L2)
- defined in: `05-full-dqfd.md:250-268`
- run status: ran, bundled inside `ON` (D-1). No isolated arm in this cluster. In ONnm the pretrain is "TD-ONLY" (`05:342`).
- run conditions: as D-1.
- recorded outcome: not separable from D-1. Prereg hypothesis: "ON caps near the offline pretrain level (~425)" (`05:362`). L1 ON = 440.63.
- recorded cause: none isolated.
- premises: a good starting policy avoids the collapse basin; demos are informative from per-user obs.

### D-4. Margin scaled to live Q spread (`scale_mode: qw_sd`) and margin-scale ladder
- mechanism: `m = qw_sd_mult * std(Q_w(s,.)|valid)`, recomputed per step; ladder {8e-2 … 5e-5}.
- intervention point: penalty/loss
- defined in: `05-full-dqfd.md:156-172`
- run status: ran as part of fulldqfd ON. The ladder was designed [I: no ladder results found in this cluster].
- recorded outcome: loss ratio 7.85 → 1.77 (smoke). "does NOT guarantee margin ~ TD gradient parity… do not claim the scale 'fixes' the balance" (`09:183-192`). A "margin-scale sweep cannot answer whether learning can exceed the demonstrator" (ruled-out claim, `99:124`).
- premises: margin is needed at all (D-2 is the contrary branch).

### D-5. Cross-user live z-score input normalisation (`form: concat` = [raw224 ‖ z224])
- mechanism: each feature is standardised across the 100 users of the same step (live mu, sigma) and concatenated with raw features. This removes common-mode drift so per-user inputs become distinguishable.
- intervention point: representation
- defined in: `04-zscore.md:12-66`; `shared_q_isolation/standardize.py:25-43`
- run status: ran (C2 arm family, 3 seeds; all fulldqfd arms; L1 6 seeds x 12000 ep).
- run conditions: COND-FB-JUL; argmax-EE; from scratch.
- recorded outcome: argmax-EE 146.6 (raw) → 357.1 mean {418.5, 340.2, 312.6} (`04:56-64`). Later OFF (with z) = 523.78 at lr=1e-3/12000 ep (`02-MEASUREMENTS-LEDGER.md` L1). `form: center` (no scaling) re-collapsed on 1/3 seeds {297.6, 144.3, 310.4}, so "full z-score (center+scale) is necessary". On the BC lookup, live-z vs raw is worth about 54 EE (475.26 vs 421.40), the "smuggled coordination gain" (`04:132-138`). Coordination screen R=0.336 = "IN BETWEEN" (`04:140-157`).
- LATEST verdict + revisions: whether live z counts as coordination is an "open USER ruling (escalated 2026-07-13, never answered)" (`99:35`). A prior claim that "the USER has ruled live z is not delegation" is RETRACTED as nonexistent (`99:20`). The 2026-08-21 handoff keeps chi + z-score as the "input-layer de-homogenisation" half of a symmetric design (`CATFISH-DESIGN-HANDOFF-2026-08-21.md:163-169`). `CURRENT-STATE.md:66` lists "same-step across-user normalization" in the live MCRL method.
- recorded cause (why it works): de-saturation / common-mode removal (`04:29-56`). Side effect (hypothesis): it zeroes 77/224 near-constant dims (`04:78-82`).
- premises: collapse is caused by input homogeneity (common mode dominates); a population statistic is allowed at deployment.

### D-6. Frozen-z normalisation (fixed per-feature mu*, sigma* from eval-disjoint rollouts)
- mechanism: z with constant mu*, sigma*, so inference involves no cross-user computation. This is the "honest pure per-user" version of D-5.
- intervention point: representation
- defined in: `04-zscore.md:161-209`; `frozen_endpoint_probe.py`
- run status: eval-only probe on live-z-trained checkpoints; frozen-z BC floor built (`09:229-310`). "frozen-stats has no code path in the trainer" (`04:202-209`). Never used in training in this cluster's records.
- recorded outcome: frozen/live EE ratio about 0.921 (~92% capture), tagged `uncertain`, "not reproducible in this checkout" (`04:187-200`). Frozen-z BC floor = 427.29 @ min_cov 0.481. On the lookup, "the live-z advantage comes almost entirely from live cross-user computation" (−47.97 EE live→frozen), explicitly "not extrapolable to trained arms" (`09:301-308`).
- premises: most of the z benefit is de-saturation reachable with static constants.

### D-7. chi congestion-context features (84 dims: previous-step occupancy, contender count, own SNR rank per action)
- mechanism: state augmentation with 3 per-action congestion features. chi[1] and chi[2] are current-step cross-user quantities; chi[2] is a symmetry breaker.
- intervention point: representation
- defined in: `01-pipeline-walkthrough.md:62-85`; `04-zscore.md:213-232`; `route_b_factorial/congestion_context.py:38-111`
- run status: ran. Present in all arms including baselines (aug224).
- recorded outcome: no isolated ablation in this cluster. The 08-21 handoff says "chi alone recovers only 0.4% of the coordination gain (B15)", so the symmetric design "holds narratively, not proven in effect" (`CATFISH-DESIGN-HANDOFF-2026-08-21.md:169`). `CURRENT-STATE.md:66` keeps "congestion context" in the live method.
- LATEST: whether chi violates the "pure per-user" red line is open (`99:36`).
- premises: per-user obs lacks congestion info; per-user symmetry breaking helps.

### D-8. Coordinated decode (greedy facility-location auction / `corrected`) in the training loop, and the "decoder exit" to argmax
- mechanism: a joint submodular greedy opening of cells (<= k_cap per satellite) over V_Q summed across users. It was used in the TD target `a'`, the rollout, checkpoint eval and best-checkpoint selection. The "exit" sets `decode: argmax` on all four surfaces.
- intervention point: decode/deployment (and TD target)
- defined in: `03-decode-and-masking.md:11-45,180-185`; `01:216-231`; `auction_decode.py:108-119`
- run status: ran (all C-cells before fulldqfd used `corrected`); decoder-exit ran in fulldqfd.
- recorded outcome: with decoder C2 506.21 / C4 510.19 (d=+3.98); without, 357.14 / 386.80 (d=+29.66) (`03:145-148`). The "decoder compresses the catfish effect 7.5x" claim is RETRACTED as a single-seed artifact: 82% of +29.66 comes from seed 271 (`03:152-166`). The invariance-group null-space story is RETRACTED; the cause is "redundancy" (hypothesis, `03:120-137`).
- LATEST: the decoder exits "by CONSTRAINT (deployment coordinator banned), not by the number" (`03:170-176`). Deployment is per-user argmax with "no coordinated allocator, auction, bid, or decoder" (`CURRENT-STATE.md:48`). Trained Q under a decode is `Q^{pi_decode}`, evaluated off-distribution by argmax, "a confound for all old catfish results" (`01:227-231`).
- premises: a joint optimiser is allowed (now banned); Q improvement is visible through the decoder.

### D-9. BC k-NN lookup of specialist demos as a zero-learning per-user policy ("BC k-NN bar", k=10)
- mechanism: k-NN over (obs, action) pairs from the F-mean demos, run as a pure per-user policy. Used as the floor any learned arm must Pareto-dominate.
- intervention point: decode/deployment (as a baseline/bar) / evaluation
- defined in: `00-README-START-HERE.md:99-146`; `09:62-120`
- run status: ran (frozen 48-ep harness, 10/10 self-tests PASS).
- recorded outcome: live-z 475.26 @ min_cov 0.723; raw 421.40 @ 0.527; frozen-z 427.29 @ 0.481; k=1 is 439.67 (z) / 373.00 (raw) (`09:275-281`). The leak pool (same episode) gives 636.05 at min_cov 1.000. This shows "per-user function class can express the joint optimum… Gap A = 100% generalisation, 0% expressivity" (`02:142-163`). More accurate imitators score worse: raw top-1 0.8368 → 421.4 vs z top-1 0.7123 → 475.3 (`04:236-257`). Same 16.3% error rate: random errors cost 80 EE, kNN's own errors cost 215 (`04:250-253`). ORACLE demos k=10: 378.71 (`02-MEASUREMENTS-LEDGER.md:33`).
- LATEST: bar is "grounded". Two-axis, same-contract rule binding.
- recorded cause: the k_cap rank cut makes correlated clone errors cascade ("error structure, not accuracy").
- premises: demo pool is eval-disjoint; per-user obs carries enough of the joint state.

### D-10. gamma1=0 for the EE head (EE head as contextual bandit)
- mechanism: set per-head gamma [0.0,0.9,0.9] because r1 is a pure function of (physical state, joint action), which the action does not change in the next state.
- intervention point: objective (per-head discount)
- defined in: `01:147-154`; `01-ENV-MECHANICS.md:36-40`
- run status: ran (fulldqfd, L1).
- recorded outcome: old arms with gamma1=0.9 measured −55 EE vs gamma1=0 (`01:153-154`, citing `fulldqfd_ON.yaml` comment).
- premises: the action does not influence the next physical state. **This fails if power has a previous-step recurrence**, as the active single-SINR contract does [I: `CURRENT-STATE.md:50`, "only consecutive service of the same physical link uses the previous-step gain-ratio recurrence"].

### D-11. CDRL Phase-1 solver seeding of the catfish replay (DFT codebook + WMMSE + argmax-EE)
- mechanism: an external solver enumerates, solves and picks max-EE exemplars, which are stored as the initial catfish replay data.
- intervention point: experience
- defined in: `07-true-catfish-formulas.md:32-53`
- run status: **never built** ("grep 0 hits… buffer never seeded", `07:256-274`). The pool label "DFT+WMMSE" on `D_fmean_solver_all_kc1.npz` is "a KNOWN stale mislabel" (`09:168-179`).
- recorded outcome: none. Hypothesis (low confidence): in this env the CDRL "moving target" property (the catfish improves beyond the seed) likely fails. "the seed is a 636–694 EE near-optimum and the strongest learned thing is ~418… the catfish would have to beat the solver" (`07:364-367`).
- premises: a solver exists that is better than the learner; its data is learnable.

### D-12. CDRL M1 experience stratification (EE-threshold routing into catfish vs main buffers)
- mechanism: transitions with EE >= EE_high go to the catfish buffer, the rest to main. In code, a rolling 0.80 quantile (soft by default: main keeps the full stream; hard preset discards the bottom 50%).
- intervention point: experience
- defined in: `07:71-86,189-203`; `catfish_faithful_familyb/stratification.py:66-122`
- run status: built and ran inside the faithful catfish trainers (see D-15). In the fulldqfd wave: absent.
- recorded outcome: see D-15 / D-16. The 08-21 handoff says routing on r1 only "brings selection bias into the r2/r3 contents of the injected batch… active harm, not neutral neglect" (`CATFISH-DESIGN-HANDOFF-2026-08-21.md:30-32`). Observed B2 vs B0 (both argmax): r2 +33% (best of 7 arms), r1 +18%, r3 −14% (`:35-41`).
- premises: high-EE transitions are informative for main; single-objective routing is harmless in multi-objective setting (refuted per 08-21).

### D-13. CDRL M2 asymmetric discount (gamma_main=0.9 <= gamma_catfish=0.99)
- mechanism: the main agent is myopic and the catfish farsighted.
- intervention point: objective
- defined in: `07:88-100,205-217`
- run status: built, ran (faithful trainers).
- recorded outcome: "family_b episode only 10 steps and no accumulated state ⟹ gamma*Q(s') is action-independent ⟹ zero effect on policy… disclosed dead-weight" (`07:212-217`).
- LATEST: S4 per-objective catfish discount "excluded" (derivative; breaks c_j calibration) (`CATFISH-DESIGN-HANDOFF-2026-08-21.md:85`).
- premises: actions affect future states. **In the new project, recurrent link power and handover could make this non-dead** [I].

### D-14. CDRL M3 randomized periodic intervention (mix 30% catfish + 70% main into a main update)
- mechanism: every Uniform[4,16] steps, one main update on a mixed batch drawn 30% from the catfish buffer.
- intervention point: experience
- defined in: `07:130-151,219-230`; `catfish_faithful_familyb/config.py:85-89`
- run status: built, ran (faithful trainers; Phase-I S1/S2/S3 isolation, see D-cross ref in ADR entries below).
- recorded outcome (Phase-I, `CURRENT-STATE.md:40`): "S3-versus-N identity audit… exact equality across 160 eval rows… no-intervention catfish is behaviorally inert here and the bounded divergence is caused by intervention". Divergence is bounded/transient.
- LATEST: 08-21 surviving direction: replace the random schedule with a measured trigger, and make the 70/30 ratio tunable and directional (`CATFISH-DESIGN-HANDOFF-2026-08-21.md:98-104`). DQfD ρ-replace "starves 30% of the agent's own updates at fixed update count" (`07:337`).
- premises: catfish buffer contains better-than-main experience.

### D-15. ACRM adaptive competitive reward (r^C = r + eta*(r^CF − r^M), counterfactual r^M from main's greedy action)
- mechanism: the catfish r1 is shaped by its lead over the main's counterfactual EE on the same state (linear; tanh variant OFF).
- intervention point: reward
- defined in: `07:103-128,232-254`; `catfish_faithful_familyb/trainer.py:385-404`
- run status: built (familyB trainer) but "False by default and no config in the repo turns it on" (`07:249`). Not ported in the route-B trainer (NotImplementedError). Phase-I isolation ran "ACRM/capacity penalty off" (`CURRENT-STATE.md:40`).
- recorded outcome: none run. Later: `CURRENT-STATE.md:66` lists "a matched competitive term on r1 only" in the live MCRL method. The 08-21 handoff proposes per-objective ACRM as a surviving direction (`CATFISH-DESIGN-HANDOFF-2026-08-21.md:98-99`).
- premises: the catfish can outperform the main on the same states (a lead exists).

### D-16. qblend / Q-mix (omega*Q^M + (1−omega)*Q^CF) and tanh competitive shaping (6-pages-only extras)
- mechanism: scalar convex blend of main and catfish Q, "NOT QMIX", and tanh on r^S.
- intervention point: decode/deployment (qblend), reward (tanh)
- defined in: `07:246-251,320-321`
- run status: built, OFF; "correctly OFF" (removed in thesis final version).
- premises: n/a.

### D-17. "A2" = per-head gamma vector [0.9,0.9,0.99] + value-stratified prioritized replay (lambda 0.5, rho 0.25), reported as "catfish" in Table 5-2
- mechanism: a per-objective gamma vector plus prioritized replay stratified by value.
- intervention point: experience + objective
- defined in: `07:157-175`; `route_b_factorial/trainer.py::RouteBFactorialMODQN`
- run status: ran (Route-B factorial, thesis Table 5-2).
- recorded outcome: "catfish = scoped-negative (A2 ≈ A1)". But "Zero of CDRL's 3 strategies survive as mechanisms in A1/A2/B1/B2 — they are gamma-vector + prioritized replay, NOT catfish" (`07:171-175`).
- LATEST: the negative does not apply to catfish (naming misleading).
- premises: n/a.

### D-18. Faithful catfish trainers (dual rollout: learning catfish agent with its own env rollout + M1 + M2 + M3; ACRM off)
- mechanism: a second learning agent collects experience in its own env copy, filtered by M1, and injected via M3.
- intervention point: experience (population)
- defined in: `07:177-187`; `route_b_factorial/faithful_catfish_trainer.py` (aug-224 + corrected decode) and `catfish_faithful_familyb/trainer.py` (base-140 + per-user argmax)
- run status: built; route-B version ran with coordinated decode. 07-18 L7: "A 'dual self-rollout catfish' arm… vs a gamma-matched no-injection comparator", in flight (`02-MEASUREMENTS-LEDGER.md:57-60`). Phase-I (Aug) S1/S2/S3 × 8 seeds × 2000 ep (`CURRENT-STATE.md:40`).
- recorded outcome: see ADR-004/007 entries below.
- premises: the catfish agent can find better-than-main experience by itself.

### D-19. cap_bump as low-noise estimator; argmax_distinct target = k_cap budget (about 12)
- mechanism (metric concept): the fraction of cap-bumped users explains 94.5% of EE variance across 25 arms (`EE = −674*cap_bump + 601`, R²=0.945). Margin moves distinct actions from 7.8 (below budget) to 12.2 (at budget); BC clones sit at 18–23 (over-spread).
- intervention point: other (evaluation)
- defined in: `02-collapse-mechanism.md:69-92`
- run status: measured post hoc.
- recorded outcome: `d/sd` 1.23 for cap_bump vs 0.29 for EE on C4−C2. "the past three waves were judged NULL because only EE was counted" (`02:92-93`).
- premises: the hard k_cap demand-rank cut exists. **The 08-22 ruling removes beam-count caps** (see RULING entry below).

### D-20. F-mean specialist (submodular greedy beam opening + iterated best response on the exact EE table, expected fading)
- mechanism: a zero-learning, deployable-but-joint heuristic (congestion-game iterated best response). EE 636.05. Also ORACLE local search with an `m2_open_beam` move (681.81) and G, a handover-priced EE auction (596.00).
- intervention point: other (teacher / reference policy)
- defined in: `05:32-41`; `02-collapse-mechanism.md:103-107`; `01-ENV-MECHANICS.md:52-59`
- run status: ran (reference and demo source).
- recorded outcome: F-mean 636.05; de-clairvoyant ORACLE 681.81; clairvoyant 694.34 (premium 1.8%). All compute each user's action "USING the joint state… none is a function of obs_u alone" (`01-ENV-MECHANICS.md:60-61`). Later `CURRENT-STATE.md:158-159`: "the F-mean coordinator has no lagged-Î input schema… fenced as a historical load-only negative control."
- premises: the load-concave power model (its EE table). Under the active contract it is blocked.

### D-21. Unilateral best-response headroom probe on the trained OFF policy
- mechanism (diagnostic): from the trained policy's states, one user switches to its best action with others fixed.
- intervention point: other (diagnostic of where headroom lives)
- defined in: `02-MEASUREMENTS-LEDGER.md:48-54`
- run status: ran (720 paired samples, 6 checkpoints).
- recorded outcome: "+97.2% of the step-mean eta on average… 95.3% of samples have a positive gain". The one-at-a-time BR mean (about 960 EE units) "EXCEEDS the joint feasible references". 15.6% of samples have base eta=0.
- inferred cause [I]: much per-user-reachable headroom remains, so the learner is far from even a Nash point. Headroom is not only coordination-required. The sum of unilateral gains is not jointly feasible (above ORACLE).
- premises: n/a (diagnostic).

### D-22. Reward-landscape probe: homogeneous vs spread profiles (L5)
- mechanism (diagnostic): matched 24 states, all-same-action vs round-robin vs concentrated spread.
- defined in: `02-MEASUREMENTS-LEDGER.md:38-46`
- run status: ran (no training).
- recorded outcome: per-user eta round-robin ×1.81 (20/24), concentrate ×3.63 (24/24). The single-step weighted scalar gap between round-robin and the best homogeneous action is about 0 (14/24). r3 penalises round-robin spread (−7.09e6 vs −4.13e6).
- inferred cause [I]: the scalarised objective (w with calibration) barely rewards spreading; only the EE axis does, and r3 works against it. The concept "spreading helps EE" holds for r1 but not for J_w in this env.
- premises: n/a.

### D-23. Ruled-out representation/other ideas (listed as dead in the explainer)
- per-user UID / SePS embedding: "do NOT do… users are exchangeable (iid reset)… expressivity already sufficient" (`02:191`, `99:119`). Never built.
- dense-CF distillation: "perfect fit only 335.4, worse than status quo (closed-loop)" (`99:121`). Ran.
- `k_c` sweep: "code-proof DEAD" (`99:120`). J_w oracle: DEAD (`99:122`). "handover is the axis": retracted (`99:123`).
- tanh saturation and action mask as causes: ruled out, 0.000 saturated at init; 27.98/28 legal (`02:184-191`). This is for the z-scored input. See D-24 for the earlier offset-saturation finding.

### D-24. Input de-saturation: zero physically unreachable beam offsets (SDD-11 "Fix B", `offset_mask`)
- mechanism: offsets for unreachable far-satellite beams (15,000–21,000 km ÷ 100) entered tanh at about 150–210, saturating about 97%. Masking them to 0 restores gradient.
- intervention point: representation
- defined in: `docs/PROJECT-STATE-AND-FAILURE-LEDGER.md:52-80`; SDD-11 `docs/research/catfish-faithful-route-a/11-foundation-offset-saturation-fix-matched-retrain-sdd.md`
- run status: ran (matched retrain, faithful HOBS env, seeds 42/137/271, 3000 ep).
- run conditions: HOBS-faithful env (not family_b); baseline MODQN; neutral metrics (active beams, throughput vs RANDOM).
- recorded outcome: "un-fixed baseline collapses (modal_frac=1.0, active=1…) while the de-saturated arm converges and spreads (active 5–7 beams) on all 3 seeds and beats RANDOM on throughput". codex RESULT-SOUND. The about 15 prior "structural-collapse" closures were "downgraded… to inconclusive (confounded)".
- premises: raw unnormalised geometric inputs. Relevant to any new encoder [I].

---

## Batch 2: capacity penalty, 2026-08-21 cross-family review, Phase-I diagnostics (Aug), lr, ADRs, SDD-01

### Shared run-condition block for the Aug-2026 Phase-I line (COND-FB-AUG)
- **Env:** family_b sibling ("MODQN-faithful Family-B"). U=100, C=28, L_w=4, **k_cap=3 still on**, 10 steps per episode (`PHASE1-EXP-STRATEGY-ISOLATION-SDD-2026-08-18.md:22-28`). Includes the accepted reachable-offset mask (D-24).
- **Physics:** R4/R5/R6/S-pilot ran 08-15..08-18 under the ADR-003 contract: target-SINR power inversion `p_req` → capped actual P_DL, PA/fixed costs, **event (handover) energy = 0 as an explicit assumption** (`ADR-003-canonical-ee-closure.md:130,231`). That contract was archived 08-19 and superseded by single-SINR with recurrent link power. ADR-007 was bound to the single-SINR contract (`PHASE1-LONG-HORIZON-B-VS-HM-SDD-2026-08-19.md:14-31`).
- **Metric:** **ratio of sums** (total delivered bits / total consumed J) on fixed-policy held-out eval (5 eval seeds x 5 phase cells). QoS 1 Mbit/s and handover are co-metrics; mean-step EE is diagnostic only.
- **lr = 0.001** (LR pilot, `LR-PILOT-ADJUDICATION-2026-08-15.md`). Input: concat raw || same-step cross-user z. Trained **from scratch** from episode 0. "No old checkpoint, replay, pool… imported" (`ADR-004:124-126`). No distillation from a frozen main. gamma_main 0.9. ACRM and capacity penalty OFF.
- **TD target:** ADR-007 parent binds "three per-objective item replay memories and **independent objective TD maxima**" (`PHASE1-LONG-HORIZON-…-SDD:28-29`). That is **per-head bootstrap from each head's own max** (MODQN eq. 16 vanilla; SDD-01 decision B1). This relates to trainer-defect item 6a; the records present it as the faithful choice, not as a defect.

### D-25. Capacity penalty (L_cap; "penalty shaping", internal code M4/OFFM4)
- mechanism: a differentiable surrogate of the per-satellite beam cap. Per-user softmax (tau=1) of the scale-normalised scalarised Q, aggregated to physical-beam pressure Pi_{s,v}. Tail mass Delta_s = total − top-v_max pressure; loss `lambda*sum_s (Delta_s/|U|)^2` with lambda=0.05, added to the main update only.
- intervention point: penalty/loss
- defined in: `docs/capacity-penalty-explainer-package/02-formulas.md:38-160`
- run status: ran. Batch A: 12000 ep x 6 seeds. Batch B (abl9k): 9000 ep x 6 seeds, some arms n=3.
- run conditions: COND-FB-JUL substrate (family_b, **k_cap=3 hard demand-rank cut present, load-concave power**), argmax-EE (mean of ratios, Mbits/J, frozen 48-ep harness), best-weighted-reward-on-eval checkpoint, lr=1e-3 [I: the OFF arm 523.78 equals the L1 lr=1e-3 OFF in `02-MEASUREMENTS-LEDGER.md`]. From scratch.
- recorded outcome: Batch A: 613.05 vs 523.78, **+89.28, 6/6 seeds**, mechanical SIGNAL. served 0.892→0.991, min_cov 0.792→0.960, **cap_bump 0.108→0.009 (−92%)** (`04-measured-results.md:15-50`). r3 +42% (6/6), r2 −5.8% (3/6), J_w +38% (6/6). Batch B: L5 (+penalty, no catfish) 615.10 (n=3) vs L2 485.14. Paired 2x2 (n=3): penalty +130.39 without catfish, +125.26 with (`04:60-92`). Best checkpoints are early (ep 249–9349, 0/6 in the last 500 episodes).
- LATEST verdict + revisions: (1) M-14 erratum 2026-08-03: the numbers predate the /|U| normalisation and "are no longer results of the current implementation" (`04:5-7`). (2) G6: codex "SIGNAL supported decisively; causal mechanism and broader generality not established". agy: two undistinguished causes, behavioural tail compression vs "generic stabiliser (grad-norm 28 → 2)" (`04:130-150`). (3) **2026-08-21 user ruling: removed.** "capacity penalty has no substantive relation to the catfish mechanism… v_max exists mainly so the penalty has something to act on. Both removed together" (`DECISION-RECORD-2026-08-21…md:280-292`). SDD-01 FORBIDDEN list: "capacity penalty — unrelated to catfish" (`MCRL-NEW-PROJECT-SDD-01…md:641`). 08-22 RULING removes any beam-count cap (`RULING-2026-08-22-no-beam-count-cap.md:9-12`).
- recorded cause: not established (two candidates, no lambda sweep, no matched generic-regulariser control) (`99-open-questions.md:26-36`).
- inferred cause [I]: the effect is almost entirely the removal of k_cap demand-rank cap-bump events (cap_bump −92%, served +0.10). EE = −674·cap_bump + 601 across 25 arms (D-19). Without a hard count cap the concept has no target.
- premises: **a hard per-satellite beam-count cap that the learner cannot observe.** Absent in the new project by ruling.

### D-26. Learning-rate mis-tuning as the collapse cause (lr 0.01 → 0.001)
- mechanism (diagnostic finding): collapse attributed to lr=0.01 (MODQN Table I value).
- intervention point: other (optimiser)
- defined in: `capacity-penalty-explainer-package/05-claim-boundaries.md:79-92`, `99-open-questions.md:13-18`; `MCRL-NEW-PROJECT-SDD-01…md:163-182`; `LR-PILOT-ADJUDICATION-2026-08-15.md`
- run status: ran (2026-07-20 single-variable isolation; 06-15 step3-cause-ablation; 08-15 pilot 3 lr x 3 seeds x 3000 ep).
- recorded outcome: "only flipping lr 0.01 → 0.001… argmax EE 235.53 → 472.22, min_cov 0.312 → 0.698. A correctly tuned baseline does not collapse" (`05:81-84`). The 07-18 ledger: at lr=1e-2 OFF peaks at ep300–400, then decays to 0.58–0.65 of peak (6/6). The 08-15 pilot (ratio-of-sums, training windows): lr 0.001 → 10.450 Mbit/J, 0.003 → 8.040, 0.01 → 5.864.
- LATEST verdict + revisions: SDD-01 §2.3 (08-21) qualifies this: "0.001 buys not discriminability: α=0.01 → active beams 1.00 / argmax agreement 1.000; α=0.001 → 4.39 / 0.484, but q_margin drops 0.0057 → 0.00055… 'escape is argmax-dispersion under near-flat Q, not a discriminative Q'". The normalised gap is still 10–29x, so "Q relatively flat" holds. "that the small margin is noise… not established; P6 decides" (`SDD-01:163-182`). Hence the four-item collapse gate (active_beam_count, argmax_agreement, normalised q_margin, q_entropy).
- premises: n/a. **Implication for transfer:** any old arm whose result depended on a collapsed lr=0.01 baseline had a sick comparator (for example D-1 at lr=1e-2: "+129.97 in ON's favor").

### D-27. Per-objective admission bank + per-objective ACRM (replace r1-only routing)
- mechanism: each objective j gets its own elite buffer routed by `omega_j*r_j/c_j`, plus its own ACRM (and per-head beta in Fable's version).
- intervention point: experience + reward
- defined in: `CATFISH-DESIGN-HANDOFF-2026-08-21.md:96-104`; `catfish-review-2026-08-21/adjudication.md:71-78`
- run status: never built (design direction, "three families converge").
- recorded outcome: none. Honest self-assessment: "none of the three parts is a new mechanism alone… engineering transplant of single-objective mechanisms to multi-objective" (`HANDOFF:109-111`). "All proposals presuppose fixing r3 first" (`adjudication.md:78`).
- recorded motivation: routing on r1 only leads to "selection bias… Q_2 trained on a high-r1-skewed distribution, active harm". Observed B2 vs B0 (Route-B factorial, both argmax): r2 +33%, r1 +18%, r3 −14% (`HANDOFF:24-41`). Conditions of that observation: old 180-sat 780 km Walker geometry, v_max/k_cap on, chi on, Double-DQN, **old load-blind r3**, 10 s earth-fixed beams (`DECISION-RECORD…:839-850`); lr not stated [I: likely lr=0.01; B0 served only 33.7% at k_cap=3 (`DECISION-RECORD…:688-696`)].
- premises: multi-objective imbalance exists and hurts; the r3 signal is meaningful (it was broken when observed).

### D-28. Measured (state-conditioned) intervention trigger replacing the random periodic schedule
- mechanism: fire the catfish conduit on main-side stagnation signals: policy change rate, TD-error collapse, contraction of scalarised-Q dispersion.
- intervention point: experience (schedule)
- defined in: `CATFISH-DESIGN-HANDOFF-2026-08-21.md:63-74,100-101`; `adjudication.md:73-78`
- run status: never built.
- premises: stagnation is detectable and intervention helps when it happens. Principle borrowed (cited, not the mechanism) from LLM catfish paper 2505.21503. Red line: "anchor on inter-objective imbalance, not on 'adaptive intensity'".

### D-29. Tunable, directional mix ratio (70/30 becomes a knob scaled by stagnation, injecting only the most-neglected objective's bank)
- intervention point: experience
- defined in: `CATFISH-DESIGN-HANDOFF-2026-08-21.md:102-104`; `adjudication.md:66`
- run status: never built. "Fable-unique finding"; the CDRL p.33 70/30 was verified by the orchestrator.

### D-30. Excluded catfish options (2026-08-21; do not re-propose; citations flagged as unverified)
Source: `CATFISH-DESIGN-HANDOFF-2026-08-21.md:78-90`, `adjudication.md:40-58`. None was built or run.
- **One catfish per objective:** excluded, "difference too thin". There are already 3 objective nets. Note: the June SDD-07 "clean per-objective 3-catfish" was this concept (see research entries).
- **S3 Pareto-dominance competition:** "DEAD". Joint-action dominance is "a single global boolean shared by 100 users", reproducing r3 non-decomposability, plus sparsity. It could revive only as per-user or epsilon-dominance/hypervolume comparison.
- **S1 catfish with different Omega (weights):** derivative (envelope Q, DOL, PGMORL). Data from Omega_CF != Omega "is no longer elite" for main, which reduces to off-policy shift.
- **S4 per-objective catfish discount beta_CF,j:** derivative (HRA). "Breaks c_j calibration" because Q scale ~1/(1−gamma) differs by objective.
- **S2 explore objective-conflict states:** downgraded to optional. It paired the wrong heads (the true long-horizon trade-off is Q1 vs Q2 handover oscillation); under the old r3, Q3's argmax is noise (false conflicts). Nearest neighbour: Pathak 2019 disagreement exploration.
- **Catfish as a penalty:** excluded (category error; the author already removed the capacity penalty).
- **Only give the new r3 to catfish:** excluded (contradictory rewards in the shared buffer; the main is what deploys).
- Minority direction (Gemini Flash): adversarial environment-perturbation catfish (minimax robust RL) + Successor Features/GPI (`adjudication.md:68`). Never built.
- Codex note: "the biggest omission is the decoder: independent per-user argmax violates beam capacity and causes collisions, which no replay scheme can fix" (`adjudication.md:62-64`).

### D-31. Difference reward / per-user decomposable r3 (credit-assignment fix)
- mechanism: r3 = −(max−min) of a global quantity is identical for all users at a fixed joint action; one user's marginal effect is swamped by 99 others. Fix via a difference reward or a per-user quantity.
- intervention point: reward
- defined in: `catfish-review-2026-08-21/orchestrator-own-errors.md:15-26`; realised as **B13 count-based `r3,u = −U_{b_u}`** (`MCRL-NEW-PROJECT-SDD-01…md:288-296`), with identity `sum_u U_{b_u} = sum_b U_b^2`.
- run status: B13 adopted in the new project (baseline design). No run in this cluster.
- recorded outcome/caveats: "the true disease is credit assignment / SNR, not scale". Three objections: feasibility, herd oscillation (a synchronous congestion game on −U_b), non-equivalence to MODQN (`adjudication.md:24-35`). C10: "B8 ↔ B13 interaction: count r3 amplifies herding pressure while chi is kept for that. Only the B17 baseline can answer" (`DECISION-RECORD…:861`).
- premises: the r1 rate `(B^w/U)log2(1+gamma)` already carries an anti-crowding signal, so count r3 "amplifies existing pressure" (`adjudication.md:31-33`).

### D-32. Coordinator Catfish (former CWRC, "Capacity-Winning Relay Catfish"): stateless coalition proposer producing training-time coalition experience
- mechanism: top-k admission plus masked ranking. It proposes "singleton-negative" coalitions: groups of users moved together to win a beam's demand rank, a unilateral move being a loss under k_cap. The joint bundles are fed to the main learner through protected, dose-matched source lanes. 0 new DQNs. Deployment stays masked per-user argmax.
- intervention point: experience (population/joint exploration)
- defined in: `docs/web-agent-coordinator-catfish-integration-pack-2026-07-16/00-READ-ME-FIRST.md:25-168`; `docs/ADR-002-coordinator-catfish-naming-and-endpoint-boundary.md`
- run status: **built, never run** (readiness only: kernel + contracts, 38 tests). Runtime lanes, four-arm runner and scorer not implemented (`00-READ-ME-FIRST.md:138-145`).
- LATEST: **retired 2026-07-17.** "both Coordinator algorithms retire, because the Coordinator's job was de-collapse and the z-score representation now does that job" (`ADR-002:5-9`). Code moved to `archive/src-eras/REATTACH-coordinator.md`.
- premises: collapse is a k_cap congestion-game fixed point where coordinated group moves are needed (`02-collapse-mechanism.md:97-107`); joint exploration is impossible by epsilon^m. **This fails without k_cap** (no demand-rank cliff) [I].

### D-33. Phase-I offline prefill from a LEO-native source (local_snr_greedy), H/M/HM strata, source-transfer tracing (ADR-004, R4/R5/R6)
- mechanism: an immutable pool from a per-user mask-valid SNR-greedy policy, validated against masked-uniform (Source Gate A), stratified q80/q50 on r1. High → catfish raw+shaped buffers; mid → main (arms H, M, HM). Arm C/HM = B + prefill. Lineage tracing of retention, sampling and gradients.
- intervention point: experience
- defined in: `docs/ADR-004-phase1-source-transfer-diagnostic.md`; `docs/research/modqn-faithful-ablation/PHASE1-SOURCE-TRANSFER-DIAGNOSTIC-SDD-2026-08-15.md`; disaggregation prereg `…-2026-08-17.json:94-96`
- run status: ran. R4 N/A/B/C x 8 x 2000 (quarantined `TRANSFER-UNIDENTIFIABLE`). R5 repaired, 32/32. R6 N/B/H/M/HM x 8 x 2000 ep, 40/40. Matched peak warm-start probe 16 jobs.
- run conditions: COND-FB-AUG (ADR-003 contract, k_cap=3, lr 0.001, ratio-of-sums EE, from scratch).
- recorded outcome: R5 Gate C `NO-PROMOTION`: endpoint C/B 0.9265, 3/8 wins, transient ep-1400 peak 1.4821. R6 Gate C `NO-PROMOTION`: H/B geomean 0.8833 (2/8), M/B 0.9924 (4/8), HM/B 0.9265 (3/8). "B/N falls 0.9284 at ep100 to 0.7140 at ep2000". Peaks HM/B 1.4821 (ep1400), then regress. "Checkpoint diagnostics show transient peaks, not stability" (`CURRENT-STATE.md:33-37,42`). Warm-start from the ep-1400 checkpoint: EE geomean 1.1552, 4/8 wins, QoS delta −0.03168 (2/8); "non-formal diagnostic" (`CURRENT-STATE.md:41`).
- LATEST: ADR-007 long-horizon B vs HM x 8 x 9000 ep under single-SINR: frozen, but **launch blocked** (child prereg absent + P-6 parity gap) as of 08-21 (`CURRENT-STATE.md:30,224`). Never run in this cluster's records.
- recorded cause: none adjudicated ("diagnostic only, not a root-cause verdict").
- inferred cause [I]: **B/N < 1 at ep2000 (0.714) means the full EXP catfish makes the main worse than no catfish at the endpoint**, with transient mid-training peaks. The source (per-user SNR greedy) is not better than a learner at lr 1e-3, so the "elite" data is not elite.
- premises: the source is better than a neutral source (Gate A is required to pass) and better than the learner; transfer through replay persists.

### D-34. EXP leave-one-mechanism-out isolation (S1 minus stratification, S2 minus asymmetric discount, S3 minus intervention)
- mechanism: diagnostic ablation of the three faithful-catfish mechanisms against B = faithful-full.
- intervention point: experience / objective
- defined in: `docs/research/modqn-faithful-ablation/PHASE1-EXP-STRATEGY-ISOLATION-SDD-2026-08-18.md`
- run status: ran, 5 arms x 8 seeds x 2000 ep, 40/40, 800 checkpoints, ARTIFACTS-VALID.
- run conditions: COND-FB-AUG.
- recorded outcome: "B/N endpoint geomean 0.7288 (2/8), S1/B 1.3454 but not stable (5/8; 2/5 late checkpoints), S2/B 1.0160 not stable, **S3/B 1.3721 passes the prereg stability rule (6/8; 5/5 late checkpoints)**". S3-vs-N identity audit: "exact equality across 160 eval rows, action streams… **no-intervention catfish is behaviorally inert here and the bounded divergence is caused by intervention**" (`CURRENT-STATE.md:40`).
- LATEST: diagnostic only, "no method-success or Chapter 5 claim".
- inferred cause [I]: removing the M3 conduit returns the main exactly to N, and B is 0.73x N. So **the intervention conduit is the only active ingredient and it harms the main's endpoint EE**. M1 (stratification) and M2 (discount) have effects only through the conduit; M2 is ≈ inert (S2/B ≈ 1.0).
- premises: n/a (diagnostic).

### D-35. Count-based r3 (B13), no execution mask (B10), no beam-count cap (08-22), vanilla per-head TD (B1), chi+z default OFF (B8): the new-project substrate decisions
- Not catfish concepts, but they change the conditions of every concept above. Source: `MCRL-NEW-PROJECT-SDD-01-2026-08-21.md:32-160`, `RULING-2026-08-22-no-beam-count-cap.md`.
- B1: "TD target back to MODQN eq. (16) vanilla, **each objective takes max on its own target network**" (`SDD-01:38`). This is the per-head own-argmax bootstrap (item 6a) adopted deliberately for faithfulness; the Double-DQN with a shared scalarised action is FORBIDDEN (`:645`).
- B8: chi + z-score default OFF, code kept. The question is whether the old problem still exists (`:40,644`).
- B10 / C-11: the execution mask is deleted; two-gate `x=a·z`; per-link power feasibility `p_req > p_max (1.65 W) ⟹ outage_infeasible`, "fires on 0.94% of decision steps" (`:139-160`).
- 08-22: no per-satellite beam-count cap; activation `z = 1{U>0}` (`RULING:9-12,148-163`). The motivation cites the old k_cap: "own-cell demand 3–8 → mean r1 = 0.0 Mbps, 68/100 starve, the congestion incentive sign-reversed" (`RULING:135-138`).
- Episode H=10, beta_M=0.9. "Under H=10 you may not claim asymmetric discount gives a longer horizon" (`SDD-01:51-52`). This is the M2 dead-weight carried forward.
- Outage handover rule: re-entry after outage = phi2 (so an agent cannot go offline to clear handover cost), outage step = 0 (`SDD-01:471-477`). This relates to the "outage free ride" item: SDD-01 closes the r2 loophole; r1/r3 for outage users are not specified here.
- G-3: collapse must be reported with active_beam_count, argmax_agreement, normalised q_margin, q_entropy (`:595`). G-8: any EE comparison must carry served and eff_beams (`:597`).

---

## Batch 3: failure ledgers (May–Jun 2026), position docs, repo-root concept files

### Condition block for the May–Jun 2026 routes (COND-JUN)
- Envs varied: "old broken" env with **no off-axis gain** (beams of a satellite channel-identical, SNR about −56 dB, served-at-QoS 0 for every policy). Realistic-cells 37-cell hex with G_T(theta). HOBS-faithful SDD-04 env (G_T 40 dBi + G_R 35 dBi, N=8 satellites, colour-aware interference, Table-II reward calibration). The Walker-180 "family_b" retrain (`PROJECT-STATE-AND-FAILURE-LEDGER.md:3-80,160-171`; `failure-route-ledger.md:56-176`).
- Collapse metrics: modal_frac, effective/active beams. Metrics: J_w, throughput, Jain, coverage, served-at-QoS. **Not EE for most routes.**
- Input saturation bug (D-24) was present in every multi-satellite run before 2026-06-09. "The ~15 prior structural-collapse closures [are] downgraded… to inconclusive (confounded)" (`PROJECT-STATE…:69-75`).
- lr: mostly not stated in these ledgers. The anchor "trained only ~200 episodes (epsilon never left ~0.97)" (`PROJECT-STATE…:93-96`). The later finding that lr=0.01 was the collapse cause (D-26) applies retroactively [I: MODQN Table I default 0.01 was in use].

### D-36. QMIX / value mixers (Route 1)
- mechanism: a value-mixing network over per-user Qs. intervention point: representation/objective. Defined in `PROJECT-STATE-AND-FAILURE-LEDGER.md:314`.
- run status: ran. Outcome: "Collapse… wrong axis (it mixes values, doesn't de-homogenize per-user argmax)". Listed in "do NOT re-propose" (`:336-338`).
- LATEST: confounded by the offset-saturation bug; "the dead collapse-rescue routes — QMIX, mask, capacity-rescue, w532, coordinated — are NOT re-opened" (`failure-route-ledger.md:163-165`).
- premises: collapse is a value-combination problem.

### D-37. Action masking of infeasible beams (Route 3)
- run status: ran. Outcome: "Masking infeasible beams did not change the collapsed optimum" (`PROJECT-STATE…:316`). Later "27.98/28 legal, identical across users ⟹ vacuous" (`02-collapse-mechanism.md:189`). Do-not-re-propose.

### D-38. Hard capacity caps / "make it harder" (Branch G, capacity-constrained pilot, w532 cap sweep)
- mechanism: a per-beam user cap that forces a split. intervention point: other (env). Ran (Cap25/Cap50, 24-cell w532).
- outcome: `CLOSE_NO_A4_ADVANTAGE`: "Physical geometry forces the split (Trap B); the enhanced arm is bit-identical to baseline" (`PROJECT-STATE…:318-319`). Trap B: "any admission rule achieves it → learned coordination layer redundant" (`:287-290`).
- premises: identical users; the cap is what makes spread necessary.

### D-39. Reward re-scaling / re-weighting / PopArt
- ran (Route alpha HOBS; realistic-cells PopArt-on cheap gate). Outcome: PopArt "perturbed but did not fix the collapse", GATE-FAIL 0/3 (`failure-route-ledger.md:58-65`). Do-not-re-propose (`PROJECT-STATE…:340-341`).
- recorded cause: "the EE-best feasible beam varies with state… but the policy collapses to a FIXED beam per seed… shared-Q + per-agent argmax homogenization" (`failure-route-ledger.md:64`). This was before the saturation fix and the lr finding.

### D-40. Add co-channel interference / HOBS-faithful interference env; frequency sub-band (R3) coupling
- intervention point: other (env physics). The two-coupling spike ran (no training); the HOBS env was not built.
- outcome: "HOBS = Trap A (collapse wins; interference zero at one beam)". R3 sub-band "EE 'win' just tracked throughput… optimum a corner rule, not coordination-required". FREEZE_DISCLOSE (`failure-route-ledger.md:106-130`).
- premises: spread must be reward-better than collapse, which the old no-off-axis-gain env did not give.

### D-41. Single faithful catfish (SDD-01, `catfish_faithful/`: EE stratification + asymmetric discount + competitive reward + periodic intervention)
- intervention point: experience + reward + objective
- defined in: `docs/research/catfish-faithful-route-a/01-catfish-faithful-route-a-sdd.md` (per the ledger)
- run status: ran (cheap probe, June). Conditions: old broken env (no off-axis gain), pre-saturation-fix, metric = deployed policy identity / neutral metrics.
- outcome: `NO_GO_NO_DIVERGENCE_SIGNAL`. "intervention fired ~1467×/episode, catfish updated ~15000× but the deployed main policy was bit-identical to baseline — catfish operates on the agent/objective axis; the collapse lives on the user/execution axis" (`failure-route-ledger.md:84-89`).
- LATEST: confounded, "never ran on the faithful env → does not transfer" (`PROJECT-STATE…:168-170`). July P1 faithful catfish (dual rollout, gamma + stratify + intervention) on family_b: "NULL/NEGATIVE (3/3 seeds, G6 ×2)" (`thesis-defense-catfish-positioning-2026-07-08.md:79`). The Aug S1/S2/S3 isolation found an intervention-only effect, harmful at the endpoint (D-34).
- recorded cause (07-08): "gamma is structurally INERT on family_b (no accumulating state + short episodes)… catfish cannot differentiate in TIME HORIZON → degrades to a near-copy of the main → decorative" (`thesis-defense…:74-77`).
- premises: the catfish can reach better experience than the main; asymmetric discount differentiates (needs action-dependent future state).

### D-42. Coordinated Multi-Catfish (SDD-02): execution-time coordination decoder + separable per-objective catfish
- intervention point: decode/deployment + experience
- run status: cheap probe ran. Outcome `NO_GO`: "still collapsed (modal_frac=1.0, all arms bit-identical, the same 873.093 fixed-point attractor) in the OLD broken env" (`failure-route-ledger.md:90-99`). 06-14 forward-decode proxy on a faithful-geometry sibling: `O-MIXED` → scoped-negative; "a zero-learning LP-round solver already closes 64–82% of the gap without catfish/MODQN" (`PROJECT-STATE…:35-41`).
- LATEST: 07-21 "coordinated beam allocation = dead line, fully deleted, no revival path" (`DEAD-LINE-coordinated-beam-allocation-2026-07-21.md:3-8,62-65`). Deployment decoders are banned in the new project (`MCRL-NEW-PROJECT-SDD-01…md:640`).

### D-43. Clean per-objective 3-catfish (SDD-07): three single-head catfish, one per MODQN Q-head, no decoder
- intervention point: experience (population per objective)
- defined in: `docs/research/catfish-faithful-route-a/07-three-catfish-method-architecture-sdd.md` (codex r4 SOUND per `PROJECT-STATE…:156`)
- run status: in the 06-07 ledger "being built (Rung 1)". Its outcome is outside this file set (see research entries below).
- LATEST (08-21): "one catfish per objective: excluded — difference too thin" (`CATFISH-DESIGN-HANDOFF-2026-08-21.md:82`).

### D-44. Channel-surrogate / global-assignment executor (SDD-05/06, "Rung-3 fallback"; LP-round solver)
- mechanism: a non-learned global assignment executor that spreads users. decode/deployment.
- run status: built, codex-SOUND (SDD-06). Eval-only landscape diagnostics. LP-round closes 64–82% of gap (`PROJECT-STATE…:39-41`).
- LATEST: a deployment coordinator is banned. It survives only as a reference/ceiling concept [I].

### D-45. Supervised learnability gate: can a per-user-argmax net over the per-user state represent a spread?
- mechanism (diagnostic): train the same DQN architecture supervised on a geometry/load-derived planner spread (no UID), deploy with per-user masked argmax.
- defined in: `new.md` (2026-06-18; `supervised_learnability_probe.py`)
- run status: ran (300 epochs, 32k samples).
- outcome: f spreads, active 9.88/9.12 vs planner 12.18 vs greedy 4.45 vs collapsed ≈1; rate 43.8–51.3 vs random 54.1; served 0.89–0.91. "THE FROZEN DECODE IS NOT THE BLOCKER… the MODQN collapse is a TRAINING/optimization failure… NOT a decode-structural or representation limit" (`new.md:22-27`). "Even the supervised UPPER BOUND f only reaches ~80–93% of random/planner rate… does NOT beat the static floor" (`new.md:36-40`). The 20-epoch smoke had collapsed; the full run reversed it.
- LATEST: consistent with the 07-15 BC k-NN leak-pool result (expressivity 100%) (D-9). Led to "Fork 1: training-side anti-homogenization".
- premises: n/a; supports the concept family "spread is representable, learning fails".

### D-46. Training-side anti-homogenization (EOI / cross-user diversity / anti-collapse), "Fork 1"
- mechanism: a training mechanism that pushes per-user Qs toward a representable spread with the deploy decode unchanged.
- intervention point: penalty/loss or exploration (unspecified)
- defined in: `new.md:28-34`
- run status: never built as such in this cluster (stance document only). The later z-score (D-5) and capacity penalty (D-25) filled this role.
- premises: collapse exists and is a training fixed point.

### D-47. Expert delegation / hybrid decode, "catfish v2" (GPI arbitration: at decision time, per step, pick learner vs fish (AF / DQN_scalar / EE-greedy static) by one-step counterfactual EE)
- mechanism: decision-time competitive injection. On the non-coordinated beams the fish's proposal replaces or competes with the learner's. Justified by GPI (Barreto 2017 Thm 1): the guarantee covers only the arbitrated reward (r1).
- intervention point: decode/deployment
- defined in: `catfish-v2-theory.md` (whole); `modqn-catfish-v2-brief.md:69-108`; results in `analysis/family-b-collapse-diagnosis/catfish-v2/` (outside this cluster, skimmed for the verdict)
- run status: ran. Gate-1 oracle preview (ep=12 x 3 seeds). Production n=5 seeds x 24 grid points (48 ep).
- run conditions: family_b (k_cap=3, k_c=1 coordinated beam), A1 hybrid learner `C1FIXED`, argmax-EE mean-of-ratios. Learner trained 3000 ep [lr not stated]. The deployment decode was hybrid/coordinated.
- recorded outcome: Gate 1: L 388.7, AF 448.2, F 478.7, oracle mix M 483.3 EE; min_cov L 0.500 → F 0.916 (`gate1-oracle-VERDICT.md`). Production: "min_seed(F) > max_seed(L): 24/24… F_mean > AF_mean: 22/24". But "**F>L = a FIXED heuristic (AF) rescuing a COLLAPSED learner's argmax beams**"; "18 distinct cells… only k_cap genuinely perturbs the learner" (`EXPERT-DELEG-PRODUCTION-VERDICT-2026-07-08.md` §1–3). G6: "catfish branding is an over-claim… STATIC delegation to a fixed heuristic" (`G6-VERDICT.md` finding 1).
- LATEST: banned. "delegation forbidden: no entity chooses actions for the user at deployment" (`catfish-explainer-package/00-README-START-HERE.md:31`). Deployment = pure per-user argmax (`CURRENT-STATE.md:48`).
- premises: a fish better than the learner on EE; the learner collapsed (lr=0.01 era [I]); deployment-time arbitration allowed.

### D-48. Route-C: amortised distillation (planner teacher → cheap Set-Transformer student over rounds R0→R3) + 3 per-objective catfish heads on a shared trunk with potential-based shaping; catfish choose which 30% of demos are injected
- mechanism: PBRS per objective, `Phi_k = eta_k*Psi_k`, `F_k = gamma_CF*Phi_k(s') − Phi_k(s)` with fixed eta=0.1. Psi = smooth-min tail coverage / best-vs-2nd SNR margin / mean·(1−Gini). A state-augmented shaped Q `Q((s,eta_k),a)`. Conduit: the top 30% of users by combined-rank `sum_k w_k q̄_k(u)` are injected into main with F stripped. The planner coverage demos update only the CF1 head. An earned-validity gate (rank-corr of Psi_k vs r_k vs rho*=0.1) decides which heads stay shaped.
- intervention point: experience (selection of demos) + reward (PBRS on catfish heads) + representation (eta in state)
- defined in: `3catfish-understanding-package/01-CORE-FORMULAS.md:24-110`, `02-CORE-ALGORITHM.md:5-85`
- run status: ran (route-C 5-arm: baseline random-30% vs 3catfish selection vs drop-r1/r2/r3).
- run conditions: **wiring = the main/student is distilled from a planner teacher (`sticky_planner`) over a few rounds R0→R3 (DQfD-style CE on the demo subset)** (`02:37-50`). This is the "distilled over rounds" wiring of item 4, but from a planner, not from a frozen pre-trained main. Metric J_w (lci) + per-objective + min-coverage. **Bug: the catfish reward trained on r1 = throughput instead of EE**, so the results are "invalid for the intended algorithm; EE re-run pending" (`README.md:3-13`). Env: route-C era family_b sibling, U=100. lr not stated.
- recorded outcome: "catfish is DECORATIVE on this run… the win comes from the distillation base" (`README.md:28-31`). Student J_w lci 4.03e-4 vs teacher 6.327e-4 (0.64–0.71x) at 1/22 compute; min-coverage 0.0 (`00-PROJECT-STATE.md:36-60`).
- LATEST: superseded by the July line; "collapse-adaptive eta" variant = "6-arm null… structurally inert" (`01-CORE-FORMULAS.md:60-63`). The EE re-run outcome is not in this file set.
- premises: a better-than-student teacher exists (planner); the potentials correlate with the objectives (earned-validity).

### D-49. Collapse-adaptive eta (shaping gain rising as the main weakens on objective k), "6-arm null"
- intervention point: reward (adaptive PBRS). Ran (6-arm). Outcome: "found structurally inert" (`3catfish-understanding-package/00-PROJECT-STATE.md:54-55`). Deferred.

### D-50. CDRL's own injection-vs-replacement rationale (experience-level transfer vs teacher-student distillation)
- concept: experience-level injection avoids over-imitation and preserves diversity. "the teacher's simplified design may cap the ultimate performance ceiling" (CDRL Table 3.1, quoted in `thesis-defense-catfish-positioning-2026-07-08.md:29-50`).
- recorded family_b crack: "DQN_scalar-Q + coordination decode = ~552 EE @ 0.98 cov > AF 454… MODQN's own EE ≈ 420. → the source is BETTER than the main… the 'main exceeds source' mechanism fails on family_b" (`thesis-defense…:66-71`). "P3 eeGS (stratify→EE) = NOT-DEMONSTRATED (419.3 ≈ A1 420.2)" (`:79-80`).
- LATEST: 08-21 handoff: the CDRL reading "perturbation → avoid stagnation" is judged correct. The catfish does not need to be an environment competitor, and CDRL does measure the frozen main every step (ACRM); "only the intervention timing is not measured" (`CATFISH-DESIGN-HANDOFF-2026-08-21.md:46-61`).
- premises: the main can exceed the source (it failed on family_b when the source was stronger and gamma was inert).

### D-51. Cross-user z-score as "conditioning" vs coordination as "composition" (reframe) and per-user-relative action space as root
- concept: two orthogonal axes. Composition (joint decoder vs independent argmax) is what retired. Conditioning (what each Q sees; the z-score) is alive. "per-user argmax is not a deployment constraint — it is a tractability factorisation (28^100)" (`OPEN-QUESTION-cross-user-zscore-is-it-coordination.md:41-72`). **Also recorded:** "ROOT-Q reopened 07-15: the real root is the per-user-relative action space (paper = one globally shared 28-beam catalog; ours = each user's own neighbourhood)" (`:109-113`).
- status: OPEN (no user ruling). The later study `{relative, absolute action catalog} x {independent argmax, full physical auction}` was frozen (`web-agent-coordinator-catfish-integration-pack…/00-READ-ME-FIRST.md:17-21`); its results are not in this file set.
- premises: n/a. **Transfer relevance [I]:** the new project's action index is also relative (anchor cell + 6 neighbours per user, `MCRL-NEW-PROJECT-SDD-01…md:411-425`). If the relative catalog is a collapse root, it is still present.

### D-52. Corrected r3 = global eligible anonymous admitted-occupancy Jain (J_occ − 1)
- reward concept (July). "not throughput max-minus-min, not measured airtime" (`web-agent-coordinator…/00-READ-ME-FIRST.md:152-154`). Superseded in the new project by count-based per-user r3 (D-31).

### D-53. Governed-dissent / directive value gate (`governed-dissent-gate-SPEC-v1.md`)
- **Not an RL concept.** It is a process spec for agent decision gating (triggers P1–P4/V1–V7, dispatch recipes, scorer state machine). No catfish, design or RL mechanism. Listed for completeness only.

---

## Batch 4: docs/research subfolders (skimmed)

### D-54. Dual-rollout: the catfish acts under its own Q in its own env rollout ("Layer 3, the load-bearing layer")
- mechanism: the catfish DQN picks `a^CF = argmax Q_CF` in a separate catfish env rollout, generating experience the main would not generate. Without it, the catfish buffer holds the main's own high-r_j transitions.
- intervention point: experience (population)
- defined in: `docs/research/catfish-faithful-route-a/2026-06-08-faithful-cdrl-5layer-narrative.md:80-94`; `12-sdd-b-catfish-5layer-effectiveness-sdd.md`
- run status: built in `catfish_faithful` (default ON). The per-objective SDD-07 line was single-rollout. Ran in July P1 and 07-18 L7 ("dual self-rollout catfish arm… vs gamma-matched comparator", in flight), and in the Aug Phase-I B arm.
- recorded outcome: single-rollout per-objective catfish: "the catfish Q-net is decorative (effect collapses to prioritized-replay-toward-high-reward)" (`5layer-narrative:85-90`). With dual-rollout: P1 NULL/NEGATIVE 3/3 (`thesis-defense…:79`). Aug: B/N 0.73 (D-34).
- premises: the catfish's own exploration finds better experience; the catfish differs from the main (via gamma/ACRM), which fails when gamma is inert.

### D-55. Per-catfish ACRM x3 on the per-objective 3-catfish vehicle (user decision 2026-06-11)
- mechanism: each per-objective catfish competes with the main on its own objective axis only (6 DQNs total).
- intervention point: reward
- defined in: `docs/research/catfish-faithful-route-a/2026-06-11-acrm-per-objective-3catfish-decision-record.md:13-36`
- run status: never built ("No per-objective (x3) ACRM exists in code today", `:47-49`).
- recorded design risks: (1) sign/scale semantics for cost-type r2/r3. (2) "**Degenerate competition.** A single-objective catfish can trivially win its own axis by sacrificing the others (e.g. the r2 catfish never hands over)… ACRM pressure becomes a constant". A pre-registered non-degeneracy gate is required. (3) 6-DQN cost; per thesis §5.3 "ACRM is not expected to carry effectiveness" (`:67-85`).
- LATEST: re-proposed 08-21 as "per-objective admission bank + per-objective ACRM" (D-27), still unbuilt; "one catfish per objective" itself excluded (D-30).
- premises: a catfish can lead the main on its axis without degenerate sacrifice.

### D-56. Occupancy penalty (soft anti-concentration nudge)
- intervention point: reward/penalty. Mentioned in `2026-06-03-coordination-probe-no-go-conclusion.md:142-145`: "The occupancy penalty lost to the Q-gap." Ran in May–Jun (details not in this file set).
- premises: collapse is reward-suboptimal but the nudge is weaker than the Q-gap.

### D-57. Learned assignment objective (optimal transport / bipartite matching / pointer-net), per-beam frequency sub-band action dimension
- intervention point: decode/deployment (learned joint assignment) / env action space
- defined in: `2026-06-03-coordination-probe-no-go-conclusion.md:118-160`; `new-algorithm-design-handoff.md` (06-19 pivot: "remove the argmax, change the decode/architecture"; learning supplies the cost matrix and a solver assigns)
- run status: the sub-band landscape spike ran and REFUTED (D-40). The learned assignment was never built. The 06-19 pivot's two "bars": attribution ("a ZERO-LEARNING LP/Hungarian solver might MATCH it… closed 64–82% of the gap") and novelty (`new-algorithm-design-handoff.md:25-34`).
- LATEST: a deployment joint decoder is banned (07-21 dead line; SDD-01 FORBIDDEN).

### D-58. v1 Multi-Catfish role specialists (catfish-ee / catfish-ho / catfish-load) with per-role quantile admission, quotas, coordinator scoring (May 2026)
- mechanism: three role catfish admit transitions by per-objective quantile into per-role buffers D_k; quotas prevent starvation; coordinator scoring with random/equal-budget controls.
- intervention point: experience
- defined in: `docs/research/angle-aware-ee-multicatfish/03-multicatfish-role-specialist-integration-sdd.md`; v1 spec referenced in `enhancement-catalog.md:4`
- run status: ran as early v2 catfish + EE pilots (Branch D) → "NULL + IMMATERIAL; all arms bit-identical, modal_frac=1.0" (`PROJECT-STATE-AND-FAILURE-LEDGER.md:312`).
- conditions: old env with no off-axis gain, pre-saturation-fix, throughput or HOBS metrics. Confounded.
- premises: collapse is breakable by experience curation.

### D-59. Enhancement catalog E1–E7 (never built; historical design reference, May 2026)
Source `docs/research/angle-aware-ee-multicatfish/enhancement-catalog.md`:
- E1 per-objective Q-normalisation before scalarisation (running mu/sigma), for the case where one head dominates argmax.
- E2 hysteretic-DQN loss (beta<1 on negative TD errors, scheduled 0.2→1.0), against non-stationarity.
- E3 NoisyNets per head, replacing epsilon-greedy.
- E4 PER inside each catfish buffer.
- E5 HOBS dual-condition admission gate for catfish-ho (SINR gap > gamma_os AND time-to-trigger), replacing quantile admission.
- E6 structural-signature AND-rule; E7 energy-distance audit, as anti-random guards (evaluation-side).
- Explicitly out of scope at the time: reward rewriting, asymmetric discount, competitive reward shaping, QMIX mixer (`:86-95`).

### D-60. MARL inspiration mechanisms (never built)
Source `docs/research/angle-aware-ee-multicatfish/inspiration/A-marl-coordination.md`, `D-exploration-boosters.md`:
- multi-agent fingerprints (append other agents' previous-step actions to local state; MAFDDQN reports 5–10% gain);
- successive-Q (score candidate satellites one at a time);
- Boltzmann/softmax exploration mixed with epsilon;
- VDN sum-mixer;
- max-entropy / learnable temperature, variance-based gradient scaling across heterogeneous reward scales (TADRL);
- reward-centering DQN.
- run status: never built as catfish components (QMIX was run separately, D-36).

### D-61. 2026-07-06 deep-research convergence directions (4 engines; common-mode priming caveat)
Source `docs/research/open-solutions-deepresearch-2026-07-06/CONVERGENCE-SYNTHESIS-2026-07-06.md:61-126,258-333`. None was run in this file set.
- B. **Temporal-demand + per-user queues env** (4/4): creates temporal coupling / non-myopic credit. Hedged: "load-regime-dependent… a delay/throughput/load-balance win, **not an EE win**… only real against an upgraded queue-aware/Whittle baseline".
- D. **EE via learned power control under interference** (4/4): "EE headroom in power control, not in the assignment"; the prior is "match → beat, uncertain".
- E. **CMDP / primal-dual coverage constraint** (4/4, "adopt regardless"): encode "don't starve users" as a constraint, not a reward term. (Note: CATFISH-DESIGN-HANDOFF §7 warns that turning an objective into a constraint activates the Agorio/Calvo-Fullana Prop. 1 caveat.)
- C1–C3. **MAPPO / autoregressive NCO / GNN**: "QMIX is NOT a safe fix — monotonic mixing cannot represent within-slot coordination". Contingent on the diagnostic. "argmax-universal-collapse is RULED OUT (DQN_scalar de-collapses under argmax on the same env)" (`:325-326`).
- H. **Diagnostic-first ablation**: rich per-user features under pure argmax (state), softmax vs argmax decode, 2-user monotonicity check (`:121-126`).
- "flash-D2's 'learning-to-optimize / LORM' = our already-killed amortized-distillation — do not re-open" (`:332-333`).
- premises for B/D: the env has temporal or power-control headroom. **The new project's recurrent link power with a 2 W segment start is a partial step toward D** [I].

### D-62. Handover energy in the EE denominator (HOBS `eta_ee_ho_active_tx = R / (P_active*T + M3*E_HO)`, E_HO = 150 J) (Route alpha, May 2026)
- mechanism: the objective/metric includes a per-handover energy cost, so handover-heavy policies lose EE.
- intervention point: objective
- defined in: `docs/research/angle-aware-ee-multicatfish/2026-05-27-gate-b-w433-stage-a-fail-RETRACTION-AND-CORRECTED.md:28-38`
- run status: ran (Gate B w433, 15 runs, Cap25 forced).
- recorded outcome: the phantom verdict used raw R/P_active; the corrected metric gives a1 5.33 vs a5_hobs 872.64 (+16229%, "Tier A PASS on Q2"). The overall authoritative outcome remained "STAGE_A_FAIL on Q3 axis (M4 fairness)". Later ledger: Route alpha "Classical-MORL tradeoff, no strict Pareto win… served_at_qos = 0/1000 for all arms" (`PROJECT-STATE…:320`).
- LATEST: ADR-003 (08-12) set "event energy = 0" as an explicit assumption (`ADR-003:231`). Handover energy is not in the active contract.
- inferred [I]: a 150 J E_HO dwarfs per-step transmit energy, so the metric mostly counts handovers. That contrast would be almost fully determined by handover rate.
- premises: handover energy is physically material.

### D-63. Hazard state augmentation (B1-hazard: F1/F2/F3 hazard summaries)
- intervention point: representation. Ran (cheap gate). Outcome `O-NEG-orth` (codex FD-4): "hazard summaries do not separate planner-bumped from served users → wrong lever for the cap_bump battlefield". Scope: "does not kill hazard for the r1-EE / r2-HO axes — open-but-untested" (`PROJECT-STATE-AND-FAILURE-LEDGER.md:30-34`).

### D-64. Random near-tie-breaking control arm (is the argmax spread learned signal or noise?)
- mechanism: a control policy that breaks near-ties in Q randomly, to test whether "spread" at lr 1e-3 is a learned weak ordering or dispersion under a flat Q.
- intervention point: decode (control arm)
- defined in: `MCRL-NEW-PROJECT-SDD-01-2026-08-21.md:358` (probe P6); motivated by `:167-175`
- run status: designed for the new project (P6). Not run in the old project.
- premises: Q is relatively flat at lr 1e-3 (supported: normalised margin gap 10–29x).

### D-65. Source-quality screen before transfer (Source Gate A) + transfer lineage tracing
- methodological concept: before any learning, prove that the source generator beats a matched neutral source (geomean ≥ 1.05, ≥ 6/8 seeds), then trace retention, sampling and gradients of injected items.
- defined in: `ADR-004-phase1-source-transfer-diagnostic.md:37-48`; `PHASE1-SOURCE-TRANSFER-DIAGNOSTIC-SDD-2026-08-15.md:159-184`
- run status: ran. Gate A PASS: "paired EE geometric-mean ratio 2.4992…, 8/8 seed wins" for local_snr_greedy vs masked_uniform (`PHASE1-PRELAUNCH-PROTOCOL-BLOCKER-LOAD-FAIRNESS-2026-08-16.md:10`). Transfer: no stable promotion (D-33).
- note [I]: Gate A compares the source with uniform random, not with the learner, so "better than neutral" does not imply "better than the main".

---

## What the 2026-08 handoff to the new project said should be carried forward, and what it said was still unresolved

Sources: `docs/MCRL-NEW-PROJECT-SDD-01-2026-08-21.md` (SDD-01), `docs/CATFISH-DESIGN-HANDOFF-2026-08-21.md` (CDH), `docs/HANDOFF-GPT-CATFISH-DEV-2026-08-23.md` (HGD), and the decision record they cite (`docs/DECISION-RECORD-2026-08-21-scenario-and-notation.md`, DR), plus `docs/RULING-2026-08-22-no-beam-count-cap.md`.

### Carried forward (explicitly)
1. **Baseline first, catfish last.** "First milestone: plain MODQN baseline (vanilla TD, no catfish, chi off, new env)" answering four questions (DR B17 `:821-835`; CDH §5). SDD-01 FORBIDDEN list: "catfish in any form" until C2/C3 are settled (`SDD-01:646`). HGD: the catfish mechanism library is built **outside** mcrl-leo-handover (G-6 forbids the word "catfish" in `src/mcrl`), so the new project can plug it in after training (`HGD:49-60`).
2. **Ported code (verified):** `approved_transmit_gain_linear()`, the four-term loss chain, rate `(B^w/U)log2(1+gamma)`, the handover-cost branch, **`algorithms/modqn.py` vanilla TD**, network 100/50/50 + Adam + batch 128 + 9000 episodes (DR B14 `:750-753`). SDD-01 B1: per-objective TD target taking each head's own max (MODQN eq. 16) (`SDD-01:38`). From the auction module only `decode_a0_argmax` and `valuation` are ported (DR `:758`).
3. **Guards carried as port requirements:** P-1…P-10 (Bessel Miller routing, G^T half-angle convention, finiteness battery, action-validity assert, execution-time mask re-validation, single load semantics, zero-power EE fail-closed, vacuum first step, masked epsilon exploration, rx-gain override) and live defects L-1…L-6 to fix (invalid action silently falls back to index 0; no finiteness check in `update()`; all-invalid transitions written to replay; `gate_g_pmax` always False) (`SDD-01:298-336`).
4. **The collapse gate is four metrics**, reported together: active_beam_count, argmax_agreement, normalised q_margin, q_entropy (G-3), because lr 1e-3 buys "argmax-dispersion under near-flat Q" (`SDD-01:163-182,595`). **lr is a controlled variable**, and P6 must also run the known-divergent 0.01 (`:600,615`). **G-8:** every EE comparison must carry served and eff_beams (the "3.9x" headline was a k_cap coverage artifact) (`:597`).
5. **Catfish design reasoning to keep (CDH §2):** the misplacement finding: all mechanisms keyed on r1, yet the biggest gain landed on r2 (+33%) and r3 got worse (−14%), "clearly the author's own finding", measured under old conditions. CDRL reads the catfish effect as perturbation / anti-stagnation. CDRL measures the frozen main every step through ACRM; only the intervention timing is unmeasured. LLM-catfish paper: borrow the *principles* (conditional, non-uniform, not-too-much intervention), not the mechanisms.
6. **Surviving directions (CDH §4, three-family convergence), all conditional on §5:** per-objective admission bank + per-objective ACRM; a measured trigger replacing the random schedule; a tunable, directional 70/30 mix. Honest self-assessment: "none is a new mechanism alone" (CDH `:109-111`; HGD `:120-123` repeats this: "do not promote them to innovation").
7. **Excluded options to keep excluded** (CDH §3; HGD requires the table in the integration manual): per-objective catfish, S3 Pareto competition, S1 different Omega, S4 per-objective discount, S2 conflict-state exploration (downgraded), catfish-as-penalty, r3-only-for-catfish. **Caveat carried with it:** "all citations provided by review families, unverified" (CDH `:90`). HGD Stage 2 orders re-verification, and a failed citation can revive an option (`HGD:131-151`).
8. **Symmetric-design framing:** chi + z-score = input-layer de-homogenisation; catfish = training-layer de-homogenisation. The catfish's job is defined as "break the behavioural homogenisation caused by shared-Q", which has four peer-reviewed failure-mode citations (CDH §6). Caveat: "chi alone recovers only 0.4% of coordination gain (B15)".
9. **HGD process requirements for any mechanism:** a matched random-perturbation control of equal magnitude ("true catfish vs decoration"), a falsifiable statement, and a PREREG-touch declaration. The testbed must separate "action-family-only" from "Q-family-only" collapse. "The testbed proves which mechanism works *when collapse exists*, not whether collapse exists" (`HGD:38-45,177-223`). HGD also names six intervention layers: observation, parameter, selection (random tie-break, ranked/sequential commitment with load feedback), reward, population, coordination (the last marked as an architecture change) (`HGD:199-208`).
10. **Substrate decisions that condition every old result:** no per-satellite beam-count cap (08-22); no execution mask (C-11, two-gate with per-link power feasibility, fires on 0.94% of decisions); count-based `r3,u = −U_{b_u}` (B13); chi + z default OFF (B8); H = 10, beta_M = 0.9, with the explicit warning that asymmetric discount cannot be claimed to give a longer horizon at H=10 (F1/F2); re-entry after outage = phi2 (closes the "go offline to clear handover cost" loophole) (SDD-01 §2, §4A.4).

### Dropped on the way over (explicitly)
- Capacity penalty (with v_max): "no substantive relation to catfish… hard to defend under the catfish name" (DR `:291-292`), even though it was the only mechanism with a large 6/6 effect (D-25).
- Coordinated / auction decode (confound of the B15 headline; A1 no-catfish beat A2 with catfish) (DR B15 `:765-800`; SDD-01 `:640`).
- `shared_q_isolation/` (13 files, "built on the decoder"), `injection_rung1/` (DQfD injection), `corrected_decode.py`, Double-DQN (`DR:755-757`).
- Old numbers: "A1 = 3.919 coordination ceiling, catfish 6.3% recovery, 65% selected-but-unserved, r1/r3 correlation (broken r3)" all "will mostly be invalid in the new env" (DR `:839-850`).

### Still unresolved at handoff
1. **Whether the collapse exists at all in the new env** (B17 Q1). "Without v_max, collisions only dilute bandwidth and do not deny service; collapse may be greatly reduced. If the new baseline does not collapse… the homogenisation catfish is meant to break may not exist, and the whole contribution line must be rethought" (DR `:833-835`). The HGD criterion document (`mcrl-leo-handover/docs/CONTROLLER-CRITERION-CATFISH-GO-NOGO-2026-08-23.md`) decides "necessary / uncertain / unnecessary". "Unnecessary" means do not attach the menu and rethink the contribution (HGD `:255-256`).
2. **Catfish design (C2/C3)**, "not settled because the design depends on unmeasured answers" (CDH `:3-4`). Q4 ("is high-EE = well-spread?") was **withdrawn as the watershed**. It is answered analytically: spreading raises EE but is bounded by `(2^x−1)/(x ln2)`, **24.0% at x=0.6**, so "catfish design cannot be unlocked by this question; another criterion is needed" (CDH `:124-137`). DR notes the bound holds only at the QoS-limited operating point, and the "3.9x" was a coverage artifact with an unattributed 1.53x residual at k_cap=15 (DR `:683-714`).
3. **C10: B8 ↔ B13 interaction.** Count r3 amplifies herding pressure; chi was kept for that; "only the B17 baseline can answer" (DR `:861`).
4. **r3 comparison scope without v_max** (dark beams: max/min over all positions degenerates; active-only lets collapse look balanced). "Currently unsolved" (DR `:303-315`). Q-D r3 recalibration scale (SDD-01 `:668`).
5. **Is the lr-1e-3 spread noise or weak learned ordering?** P6 with the random near-tie-break control (SDD-01 `:172-175,358`).
6. **Cross-user z-score as coordination:** still an open user ruling (OPEN-QUESTION doc). The new baseline sidesteps it by defaulting z to OFF (B8).
7. **Dwell N, V (39 vs 47), D2 thresholds, all-invalid-mask frequency** (semi-MDP fallback if non-negligible) (SDD-01 §4A.5a, §10).
8. **Prop. 1 caveat:** if any objective is rewritten as a constraint (for example, restoring v_max as an average-reward requirement or a per-beam user limit), the Agorio/Calvo-Fullana threat activates. Linear scalarisation cannot reach concave Pareto regions (disclose) (CDH §7).
