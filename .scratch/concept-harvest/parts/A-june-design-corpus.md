# Cluster A — June 2026 design corpus (old project `modqn-paper-reproduction`)

Source dir (all paths relative to it unless absolute):
`/home/u24/papers/modqn-paper-reproduction/analysis/family-b-collapse-diagnosis/`
Extraction worker: read-only, 2026-09-11. `[I]` = my inference; everything else is quoted/paraphrased from the file cited.
Written incrementally; entries appended in reading order.

## Shared run-condition facts (referenced by entries below, to avoid repetition)

- **COND-P4-6ARM** (the one scored catfish run of June 2026 = "p4-coverage-multiteacher", RESULT
  `artifacts/p4-coverage-multiteacher/p4-coverage-multiteacher-RESULT.json`):
  env = `family_b` (EUV chain sha `3cd5000a`, G1 `modqn.py aa877676` untouched), U = 100 users, 10 steps/episode,
  16 phases; `qos_floor = 1.0e7 bps` (v5 §4 citing `family_b_step.py:72`). Optimizer Adam **LR 1e-3**, minibatch 16,
  320 optimizer steps/episode (v5 §1 L104-105). **Wiring = distillation fine-tune, NOT from-scratch RL**: "All arms
  warm-start from a READ-ONLY copy of (P)" (v5 §6 L272; (P) = the gate-2b/gate-2 distilled win net), rounds R0–R3
  (`r_dagger=3`), E_pass = 400 passes/round; verdict: "runtime 958s (cheap = distillation fine-tune, not from-scratch
  RL)" (6-arm VERDICT L16). Main-side learning signal = **supervised imitation**, not env-reward TD: "The main injection
  is supervised ce-only imitation of the SELECTED subset, not env-reward TD with F=0" (v6-amendment §3 L130-133);
  sticky demos via DQfD large-margin (margin 0.8). η₀=0.1, λ=1.0, γ_CF=0.99, CF_RATIO=0.30. n = 3 train nets (enc
  1001/1002/1003) × 4 fresh eval seeds {2424,2525,2828,3131}; t df=2 → 2.920.
  Metrics scored: weighted **J_w** with weights `[0.5,0.3,0.2]` and scales `[2.341e15, 300.3, 6.13e9]` (r1 = η_EE-axis,
  r2 = churn/HO, r3 = load); QoS served-fraction; full-population **min-coverage** (per-user served-step fraction, min
  over users then phases; floor 0.05); primary attribution metric **R_starved** = fraction of (user,phase) cells below
  floor. NOT pooled EE. Bar = weak static `round_robin` J_w point.
  Old-trainer-defect notes: the per-head MODQN main is not trained by TD here (CE/margin imitation), so per-head
  bootstrap / outage-reward defects do not directly enter the main update `[I]`; the CF nets DO train by shaped TD
  (`cf_train_step`, state-augmented shaped-Q, v5 §13) — records silent on per-head-own-argmax bootstrap or
  outage-reward handling inside the CF `[I: not checked in code]`.
- **COND-FAMILY_B-DISEASE**: records name the root disease as "per-user-argmax + shared-Q **homogenization** — users
  collapse onto the same beam → sub-random" (CA-CPBR design note §1 L89-90). Later July records attribute collapse
  to lr (see `COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md`, outside priority list; noted where relevant).

---

### A-1. Catfish core, thesis-faithful (Ke-2025 CDRL): S1 stratification + S2 asymmetric discount + S3 ACRM + 70/30 conduit
- mechanism (one line): a second "catfish" agent trained on the high-EE stratum of experience, with larger discount, periodically injects its experiences into the main agent's batch (70% main / 30% catfish); ACRM adds `r^C = r + η(r^CF − r^M)`.
- intervention point: experience (conduit + stratification) + reward (ACRM) + other (discount asymmetry)
- defined in: `catfish-development-direction-2026-06-24.md:9-20`; `catfish-last-design-candidates-2026-06-24.md:26-31` (as M1–M4)
- run status: this file is a grounding/definition doc; the faithful re-implementation lives in `catfish_faithful/` and `catfish-v2/` (other clusters). Within cluster A it is the reference design, not a run.
- run conditions: n/a in this doc. Original = "actor-critic/DDPG over CONTINUOUS RIS → adapting to discrete value-based MODQN is a REAL design gap" (dev-direction L19); "Original uses ONE catfish, single EE axis. NO multi-catfish in the thesis" (L20).
- recorded outcome (quote, file): thesis ablation ranking — "S2 Asymmetric Discount ... (ablation: **LARGEST** — the load-bearing organ)"; "S3 ACRM ... (ablation: **SMALLEST** + **non-potential → Ng-1999-UNSOUND, can shift the optimum**)"; S1 "MODERATE" (dev-direction L14-16). `tanh` + `Q^mix` = "6pages-only extras the author DROPPED → OFF-by-default" (L18).
- recorded cause: S2's stated purpose = "avoid strategy HOMOGENIZATION" (L15).
- inferred cause [I]: —
- premises: a high-value experience region exists that a specialist can reach ahead of main; the main is stuck in a local optimum (stagnation) that injected experience can dislodge; "catfish needs a demo-guided-RL frame to FUNCTION ... In the pure-CE/DAgger imitation frame ... catfish has no mechanism (no exploration/stagnation to inject) → it is decorative there" (last-design-candidates L19-20).

### A-2. Agent→user bridge (re-target catfish anti-homogenization from agent level to user-level beam collapse)
- mechanism: make catfish's S2-style anti-homogenization act on the USER-level beam-assignment collapse by steering catfish to generate high-user-diversity experiences when main collapses.
- intervention point: experience (what CF generates) + reward (via Ψ potential)
- defined in: `catfish-development-direction-2026-06-24.md:22-23`; `catfish-ca-cpbr-design-note-2026-06-24.md:88-97` ("★ The bridge (design core)")
- run status: realized only through A-4 (CA-CPBR) in the 6-arm run.
- run conditions: see COND-P4-6ARM.
- recorded outcome: see A-4 (structurally inert).
- recorded cause: "catfish anti-homogenization is AGENT-level (main vs catfish), the project's collapse is USER-level → the innovation must bridge agent→user" (dev-direction L23).
- premises: **collapse exists** (per-user-argmax + shared-Q homogenization on family_b); "Catfish's load-bearing organ = S2 role-differentiation = anti-homogenization — and the project's ROOT disease = shared-Q + per-user-argmax HOMOGENIZATION" (dev-direction L23). If collapse is absent or has another cause (e.g. the later lr=0.01 finding), the bridge has nothing to act on `[I]`.

### A-3. Coverage-aware catfish re-conception (M1 routing-key = coverage-criticality; M3 coverage-advantage ACRM; M4 adaptive intervention on predicted-starvation states)
- mechanism: route hard-phase / predicted-sub-QoS-user transitions into the catfish buffer; add `cov_w·(served_tail^CF − served_tail^M)` to ACRM; intervene on predicted-starvation states instead of a fixed period.
- intervention point: experience (routing, intervention timing) + reward (coverage-advantage term)
- defined in: `catfish-last-design-candidates-2026-06-24.md:33-49`
- run status: **partially built**. Only a coverage-critical *filter* was built and run: "inject only when the rolling full-population min-served < **0.08**" applied IDENTICALLY to arm1 and arm2 of the 6-arm run (v5 §4 L171-178), so its effect was never isolated. The coverage-advantage ACRM term (M3) and adaptive intervention (M4): never built `[I: no build record found in cluster A]`.
- run conditions: COND-P4-6ARM (filter only).
- recorded outcome: no isolated outcome for the filter. Sub-idea "M2 asymmetric discount → weak lever (its benefit is §M8 hypothesis-only; leave mostly alone)" (L47).
- recorded cause: —
- premises: user-level **tail coverage** is the documented failure ("OUR documented failure (#26) = USER-LEVEL tail coverage in stochastic HARD-congestion phases (teacher-serveable)" L35-36); a teacher that serves the tail exists; the coverage-advantage counterfactual needs "the side-effect-free counterfactual evaluator the ACRM increment already built (SDD-01 §4.4 rev-6)" (L43-44). Make-or-break risk recorded: "If L2b's DAgger already fixes coverage, a coverage-aware catfish ... risk being REDUNDANT" (L84-89).

### A-4. CA-CPBR — Collapse-Adaptive Competitive Potential-Based Reward (per-objective, on the catfish's reward only)
- mechanism: CF_k trains with shaping `F_k = γ_CF·Φ_k(s',t') − Φ_k(s,t)`, `Φ_k(s,t)=η_k(t)·Ψ_k(s)`, `η_k(t)=η₀(1+λ·collapse_k^main(t))`, Ψ_k a joint state-only de-homogenization measure (Ψᴬ assignment entropy / Ψᴮ 1−Gini occupancy / Ψᶜ tail-coverage smooth-min); main never receives F, only CF experiences.
- intervention point: reward (catfish-side potential shaping) → experience (what gets injected)
- defined in: `catfish-development-direction-2026-06-24.md:25-38`; `catfish-ca-cpbr-design-note-2026-06-24.md:121-171` (v2 post-G6); code `src/modqn_paper_reproduction/demo_guided_catfish/ca_cpbr.py` (design note §10 L230-235: "11 unit tests — B1 invariance EMPIRICALLY VALIDATED (tabular-VI argmax-invariant ...)")
- run status: **ran** — 6-arm factorial arm4 (λ=1.0) vs arm5 (static PBRS, F-dose-matched), n=3 train nets × 4 fresh eval seeds, R0–R3 × E_pass 400.
- run conditions: COND-P4-6ARM. Ψ LEAD for the r1-CF = Ψᶜ tail-coverage, served indicator read from encoded state (`c[u] = clip((standing_rate_u − qos_floor)/qos_floor,0,1)`, v5 §4 L184-201). `collapse_k^main(t)` = exogenous per-round frozen snapshot on a FIXED held-state batch (v5 §4 L211-213; v6 §0 finding 2). Round boundary = state-augmented shaped-Q with η as input (v5 §13).
- recorded outcome (quote): "arm4 vs arm5 (CA-CPBR adaptivity novelty) = `delta-INCONCLUSIVE`, `earns_novelty=False` + STRUCTURALLY INERT ... `realized_eta_per_round` IDENTICAL `[0.123839]×4` for arm4 and arm5 and arm6; arm4 `realized_collapse_per_round` CONSTANT `0.238391` across all 4 rounds" (`catfish-6arm-VERDICT-G6-2026-06-25.md:32-34`). Paired Δ(arm5−arm4) mean +0.02333, CI [−0.03697,+0.08364] (L34). LATEST verdict: "structurally inert in this design → no demonstrable benefit (grounded); mechanism not refuted; re-wire = speculative future work. NEVER 'CA-CPBR coupling refuted' AND never 'promising live lead'" (L59). Revision chain: v6-amendment §3 had PREDICTED this ("arm4 > arm5 ships as a CLEAN STRUCTURAL NULL", L122-129); Gemini Pro argued "novelty REFUTED not untested" → adjudicated "PARTIALLY VALID → SHARPEN" into the dual tag (VERDICT L50). Raw per-net means from RESULT json (my extraction): R_starved arm3 0.0506, arm4 0.0267, arm5 0.0501, arm6 0.0294 — but since η was identical across arm4/5/6 the spread is "unattributed/non-mechanistic" (VERDICT L35).
- recorded cause (quote): "the collapse-adaptive coupling is degenerate BY DESIGN in the distillation wiring (the main-net collapse level is stable across the 4 distill rounds → nothing to adapt to)" (VERDICT L33); "`collapse` is computed from a FIXED held-state batch, independent of the live main → a CONSTANT every round" (v6 §0 L29-31); "The exogenous state-only collapse is ~constant across rounds (the v5 'collapse_k(t) EXOGENOUS' novelty differentiator pulls AGAINST live-main-adaptivity)" (v6 §3 L123-125).
- inferred cause [I]: the soundness requirement (collapse must be exogenous for Devlin–Kudenko invariance) and the mechanism requirement (collapse must track the live main) are in direct tension; with only 4 rounds of fine-tuning from a converged net, there is no collapse trajectory. A from-scratch or live-main wiring was never built.
- premises: **collapse exists and varies over training** (needed for λ to do anything); a JOINT state-only potential can express homogenization; transient-steering of CF experience generation reaches the main ("the benefit is transient-steering + the control loop, NOT a moved optimum", design note §4 L165-170); injected CF experiences are consumed by main (they were, via CE imitation).

### A-5. CF coverage-Q selection of teacher (planner) experiences to imitate (the "catfish system" in the 6-arm run; arm2 vs arm1)
- mechanism: a coverage-specialist r1-CF, trained on the filtered planner bank, picks the top-30% of planner transitions by its coverage-Q; main imitates the selected subset (CE, no margin); control = frozen uniform-random 30%.
- intervention point: experience (selection of demonstration data)
- defined in: `p4-coverage-multiteacher-catfish-prereg-2026-06-25-v6-amendment.md:61-87`; `p4-coverage-multiteacher-catfish-prereg-2026-06-24-v5.md:257-299`
- run status: **ran** (arm2 vs arm1; n=3 nets × 4 fresh seeds).
- run conditions: COND-P4-6ARM. Planner-sourced gradients masked to r1 head only, trunk + r2/r3 heads frozen (v5 §4 L179-183). RNG split (`rng_main` shared, `rng_cf` per-arm) (v6 §0.1 L48-52).
- recorded outcome (quote): "arm2 vs arm1 ... = no benefit + non-significant HARMFUL coverage lean. 3-net AGGREGATE (corrected ...): R_starved arm1 0.0328 / arm2 0.0413 = +26% mean WORSE on the very coverage axis the CF coverage-Q targets; J_w +1.55%. paired Δ(arm2−arm1) R_starved mean +0.00849, CI [−0.01457,+0.03154] crosses 0" (6-arm VERDICT L36-39). LATEST: "no benefit + non-significant harmful coverage lean (+26% mean)"; "catfish DECORATIVE (no earned role)" (L31, L60). Revision: earlier controller number "+85%" was first-net only, corrected by codex (L51).
- recorded cause: none mechanistic. Gate proved "conduit is LIVE" but "do NOT prove the CF's selection is SEMANTICALLY BETTER than random" (v6 §2 L114-117).
- inferred cause [I]: in pure CE imitation there is no exploration/stagnation for catfish to act on (the records' own A-1 premise); a 30% subset selected by a Q-net trained on a tiny filtered bank (smoke config filtered n≈14) may just reduce diversity of imitated data.
- premises: a better-than-student coverage teacher exists (planner witness min-cov 0.6–1.0 grounded, VERDICT L14); learned coverage-value can rank which teacher experiences matter; selection beats random.

### A-6. Per-objective multi-teacher distillation (sticky → J_w/churn via DQfD margin; planner → coverage via injection)
- mechanism: student distils J_w/churn from `sticky_planner` (DQfD margin) and coverage from `planner` (injected coverage-critical transitions, r1-head-only gradients), aiming to get "coverage WITHOUT its CHURN".
- intervention point: experience (demonstrations) + penalty/loss (DQfD margin)
- defined in: `catfish-ca-cpbr-design-note-2026-06-24.md:23-54` (§0c); `p4-coverage-multiteacher-catfish-prereg-2026-06-24-v5.md:165-215`
- run status: **ran** (all 6 arms include it; arm1 = pure multi-teacher, no catfish).
- run conditions: COND-P4-6ARM.
- recorded outcome (quote): "TREE-A (system win∌catfish, strict 5-gate on pre-selected primary arm1) = NO-SYSTEM-WIN ... g1_jw PASS ... arm1 J_w lower-CI beats round_robin weak-static by +2.4916e-4 ... g3_coverage FAIL — ALL 6 arms `min_coverage=0.0 < 0.05` floor on ALL fresh seeds ... g5_churn FAIL lcb −0.0273 < 0" (6-arm VERDICT L20-27). "coverage+churn are PROJECT-WIDE gaps (gate-2 had the coverage gap too), NOT catfish-specific" (L29). m4: student J_w (~4.5e-4) < planner 6.22e-4 < sticky 6.51e-4 (L40).
- recorded cause (quote): "the student's 0.0 is a distillation gap, NOT env-infeasibility" (L14); GemPro-adjudicated: "NOT global collapse, it is tail-user starvation" (L49).
- inferred cause [I]: coverage is a min-over-users statistic; ce imitation of a 30% filtered planner subset against a dominant sticky DQfD-margin channel likely cannot move the worst user; the J_w-vs-coverage separation ("coverage ⊥ J_w") was never shown (design note §0b L76-79 "UNPROVEN").
- premises: "No single teacher has BOTH" (sticky wins J_w, planner coverage) grounded on seed 1600 (design note L33-36); a single student can jointly realize both = explicitly "the make-or-break HYPOTHESIS" (v5 L38-41).

### A-7. Multi-teacher-AS-MAIN (naive multi-teacher distillation of the full objective) — REJECTED-as-main
- mechanism: distil the main policy jointly from the EE-best (planner) and churn-best (sticky) teachers.
- intervention point: experience / objective (teacher mixture)
- defined in: `catfish-last-design-candidates-2026-06-24.md:55-61`
- run status: never run as main (rejection by design review) `[I: record cites a 4-panel review, not a run]`.
- recorded outcome: "the EE-best teacher (planner, wants concentration) and the churn-best teacher (sticky, wants stability) CONFLICT → naive multi-teacher distillation → broken-compromise student (4/4-panel convergent, negative transfer; `NEXT-SESSION-P4-demote-rescope-handoff-2026-06-23.md` §49)". Parked: "Needs ADAPTIVE state-conditioned weighting (AMTML-KD 2103.04062) + vs-best-single ablation; naive diversity HURTS (Curse-of-Diversity ICLR24 2405.04342)" (L59-61).
- recorded cause: teacher conflict on the full objective.
- premises: teachers conflict; single sticky "is already J_w-optimal @ [0.5,0.3,0.2]=C" (L57-58) — premise tied to that specific J_w weighting.

### A-8. Static PBRS on the catfish (arm3 λ=0 η₀=0.1; arm5 dose-matched static)
- mechanism: potential shaping of CF reward with fixed η, same Ψᶜ.
- intervention point: reward (catfish-side)
- defined in: v5 §6 Table-1 L259-267
- run status: ran (arm3, arm5).
- run conditions: COND-P4-6ARM.
- recorded outcome: verdict does not grade arm3 vs arm2 explicitly; RESULT-json per-net means (my extraction): R_starved arm2 0.0413, arm3 0.0506, arm5 0.0501 (arm5 per-net [0.0619, 0.0805, 0.0078] — very high variance). `[I: no significance test recorded for B2 magnitude effect]`.
- recorded cause: —
- premises: same as A-4 minus the collapse coupling.

### A-9. Collapse-misaligned dose-matched control schedule (arm6)
- mechanism: permute arm4's η gains to anti-correlate with collapse, rescaled to arm4's F-dose, as a keying control.
- intervention point: other (experimental control)
- defined in: v5 §6 L277-286
- run status: ran, but degenerate: realized η identical for arm4/5/6 (VERDICT L33) so the permutation was a no-op `[I: follows from constant η]`.
- premises: collapse varies across rounds.

### A-10. Churn-watchdog (r2 non-inferiority guard) and head+trunk gradient mask for coverage-teacher data
- mechanism: (a) reject/flag any arm whose r2 (churn) degrades > τ_r2=0.02 vs control; (b) coverage-teacher gradients update only the r1 head, trunk + r2/r3 heads frozen for those samples.
- intervention point: penalty/loss (masking) + other (gate)
- defined in: v5 §4 L179-183, §6 L287-288, §7 L319-321; `ca_cpbr.churn_watchdog`
- run status: ran as part of 6-arm.
- recorded outcome: system churn gate failed for primary arm1 ("g5_churn FAIL lcb −0.0273 < 0", VERDICT L27) — i.e. the student's churn worse than preserved (P) by more than margin `[I: interpreted per v5 §7 gate 5 definition]`.
- premises: shared-trunk leakage of a high-churn teacher's data would drag churn; the r1 head is the right owner of coverage.

### A-11. Per-objective 3-catfish ("route C"): one CF head per MODQN objective (r1 coverage/throughput, r2 handover, r3 load), combined-rank selection of injected experience
- mechanism: 3-head CatfishCFNet, each head trained on its own normalized reward `r̃_k∈[0,1]` + its own potential Ψ_k shaping (η constant); inject the top-30% planner transitions by `score(u)=Σ_k w_k·q̄_k(u)`, w=(0.5,0.3,0.2); leave-one-out drop arms.
- intervention point: experience (selection) + reward (per-head potential shaping on CF)
- defined in: `3catfish-perobjective-design-and-prereg-v4-2026-06-25.md` (D1–D12); build spec `route-c-build-spec-for-codex-2026-06-25.md`; handoff `3catfish-NEXT-SESSION-build-handoff-2026-06-25.md`
- run status: **ran (scored, server, ~2026-06-26)**: arms baseline / 3catfish / drop_r1 / drop_r2 / drop_r3, n=3 train nets (design wanted n_primary=10; RESULT shows 3 per-net values) × 4 fresh eval seeds; runtime 843.6 s. RESULT = `archive/docs-eras/handoff/route-c/per-objective-catfish-RESULT.json` (the copy in `artifacts/per-objective-catfish/` is the smoke).
- run conditions: COND-P4-6ARM wiring (warm start from (P), R0–R3, E_pass 400, CE imitation of injected subset, sticky DQfD margin 0.8; env family_b EUV 3cd5000a). Adaptivity off (η constant). **Reward-axis mismatch recorded:** "route-C's catfish CF-shaping r1 uses `r1_throughput` (normalized), while the eval J_w r1 axis is EE (`family_b_eta_r1`)" (`archive/docs-eras/handoff/HANDOFF-NOTES.md` ~L44-47). catfish-v2 archaeology: "★ Regime/env: r1 = THROUGHPUT (the #19/#20 train/eval bug), NOT EE ... Doubly broken: wrong objective ... and pre-both-fixes" (`catfish-v2/gate-minus1-archaeology.md` D9). r3 = `r3_load_balance = −gap/U` (throughput gap over active physical beams), weights 0.5/0.3/0.2 (v4 D1).
- recorded outcome: RESULT verdict **`HALT-PER-HEAD-CONDUIT-DEAD`** — "§13 CORE r1-CF gate (a/b/c) PASS, but the PER-HEAD conduit-liveness gate FAILED (`per_head_conduit_live=False` vs the frozen permuted-head + matched-RNG negative control; heads[0,1,2], n_cat=3, J*=0.6, delta=1.476)" (HANDOFF-NOTES). My extraction from the RESULT json: primary non-regression J_w Δ(3catfish−baseline) per-net [+7.7e-6, +5.1e-5, −1.4e-5], LCB −4.1e-5 ("non_regressed": true); R_starved per-net baseline [0.0278,0.0433,0.0272] vs 3catfish [0.0453,0.0636,0.0361] (worse); drop_r1 [0.0731,0.0797,0.0678] (LCB of drop−full +0.0115 → removing the r1 head raised starvation); drop_r2 / drop_r3 CIs straddle 0; min_cov = 0.0 on all 4 fresh seeds for every arm; system gates: g3_coverage FAIL, g5_churn FAIL (lcb −0.0273) → NO-SYSTEM-WIN. Later: "route-C DEAD — a plain DQN-ext dominates the student (jw_lci 5.958e-4 > A1 4.97e-4)" (archaeology D9); "DQN_scalar also kills the route-C/P4 gate-2 (i)-WIN (student 4.03e-4 < DQN_scalar 5.96e-4)" (`route-b-LOCAL-CONTROLLER-thesis-handoff-2026-06-27.md:16`).
- recorded cause: design itself predicted decorative from the premeasure: "Ψ_r2 FLAT (Spearman +0.02 vs next-no-handover), Ψ_r3 FLAT (±0.08 vs realized r3, sign-unstable)" (v4 D0 L33); "Ψ_r1 carries; Ψ_r2 + Ψ_r3 are SAFE-but-decorative" (v4 D11 L203-204). Calib: Ψ_r2 rank_corr 0.0022 → "flat-descriptive-decorative" (calib json).
- inferred cause [I]: (1) handover (r2) and load gap (r3) are transition / cross-user physical-beam quantities not recoverable from the per-user 140-d encoded row ("all USER-LOCAL over the user's 28 candidate slots (a slot index ≠ a global physical beam)", v4 D1 L45-47) → their potentials cannot carry signal; (2) the CF r1 axis (throughput) ≠ the scored r1 axis (EE); (3) same distillation wiring as A-4/A-5, so no exploration for catfish to act on.
- premises: each objective has a state-recoverable potential that correlates with its realized reward (refuted for r2/r3 on family_b's encoding); per-objective experience selection helps a shared-trunk student; weights (0.5,0.3,0.2) are the right aggregation.

### A-12. Level-gated service-balance potential `Ψ_r3 = mean_u(served)·(1 − Gini(served))` (design lesson: "1−Gini is level-blind")
- mechanism: potential rewards both high service level and evenness; plain `1−Gini` rewards the all-starved state equally with all-served.
- intervention point: reward (potential design)
- defined in: `3catfish-perobjective-design-and-prereg-v4-2026-06-25.md:9-14, 74-94`
- run status: built (`shaped_q_trainer.py:psi_r3_batch`, commit f013b56, unit-tested), used in A-11 run.
- recorded outcome: "`psi_occupancy_spread(all-starved) = 1.0 = psi_occupancy_spread(all-served)` → it would have REWARDED the all-starved collapse the catfish is meant to FIX" (v4 L9-12). After fix: SAFE but not VALID — "Spearman(Ψ_r3, realized r3) = +0.086 (sticky), −0.074 (planner), sign-unstable ⇒ service-balance-only" (L186-187).
- recorded cause: "env r3 (physical-beam gap) is NOT state-recoverable (user-local slot→cell map hidden)" (L75).
- premises: a spread measure alone is a valid anti-collapse potential (false — must be level-gated). Generic lesson for any "balance/entropy" potential `[I]`: evenness measures are level-blind; multiply by level.

### A-13. Handover-stability potential Ψ_r2 = smooth-min over users of standing-beam SNR dominance margin
- mechanism: `d_u=clip((snr_{b*}−snr_{2nd})/(snr_{b*}+ε),0,1)`, Ψ_r2 = smooth-min_u(d); intended proxy for "user won't hand over next step".
- intervention point: reward (potential)
- defined in: v4 D2.2 L58-72
- run status: built + ran in A-11.
- recorded outcome: "Spearman(d_u, next-step-no-handover) = +0.02 (planner ...) → FLAT/DECORATIVE"; calib rank_corr 0.0022. Disclosed "COLLINEAR with r1 (SINR-margin ≈ throughput)" (handoff L63).
- recorded cause: "handover is a transition, not snapshot-recoverable" (handoff L63).
- premises: SNR margin predicts policy-driven handover (false when handovers are driven by policy/load not SNR).

- **COND-ROUTE-B** (the route-B 2×2 factorial, trained 2026-06-27, RESULT `route-b-factorial-RESULT.json`): env
  `family_b` (`family_b_step.py` sha `389eaaef`; G1 `modqn.py aa877676`), k_cap = 3 active cells per window satellite,
  4 sats → ≤12 active beams for ~100 users; users on non-active cells are cap-bumped to zero throughput
  (`route-b-factorial-design-note-v3` §1.1). **Trained FROM SCRATCH** (not distilled): "3000 ep, ε 1.0→0.01/decay
  2000, **lr 0.01**, batch 128, hidden [100,50,50] tanh, replay 50k, target/50, weights [0.5,0.3,0.2] ... seeds
  {42,137,271}" (`route-b-factorial-RUN-REPORT-2026-06-27.md` §5 L50-52). r1 = `family_b_eta_r1` "angle-aware EE"
  (`allocated_power=slot_power_w/max(load,1)` → off-axis Bessel gain → `p_tot_eff` → `per_ue_energy_efficiency`,
  design note v3 §7.1) — i.e. **off-axis gain present; per-UE EE (mean-of-ratios-style per-user EE, not pooled
  ratio-of-sums)** `[I: per_ue naming; not verified in code]`. Metric scored = calibrated weighted `J_w`
  (scales 2.341449e15, 300.316, 6.131915e9) on 48 matched eval episodes, paired bootstrap B=20000; collapse
  diagnostics qos_served / cap_bump / min_cov / active beams. r3 "is a single GLOBAL throughput-gap copied to every
  user" (design note v3 §8.2). ACRM off, PopArt off. Per-head TD "Q_k(s_u,a_u) ← r_k(u) + γ_k Q_k(s'_u,a'_u), a'_u
  from the cell's own decode" (v3 §6.1) — i.e. target uses the (scalarized) decode action, not each head's own argmax
  `[I: reading of §6.1 + RUN-REPORT "TD target = step-bundled decode-consistent recompute-at-update"]`. Outage handling:
  cap-bumped users get zero throughput; records silent on r2/r3 for unserved users.
  **★ lr caveat (later, 2026-07-20):** "the collapse that this project has treated as a property of MODQN / shared-Q /
  per-user-argmax is identified as an artifact of `lr = 0.01`" ... "REQUIRES RE-CHECK: ... the route-B factorial
  conclusion 'coordinated allocation = the de-collapse engine'" (`COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md` L3-6,
  L86-91). At lr 1e-3 plain per-user argmax: EE 472 Mbits/J, min_cov 0.698 vs lr 0.01: 150 Mbits/J, 0.167 (L34-41).

### A-14. Coordinated capacity-respecting decode ("auction" = greedy capacitated facility-location, AF when valuation is a fixed myopic rule)
- mechanism: per window satellite, greedily open up to k_cap cells maximizing summed positive value gain over users, then assign each user to its best opened beam; replaces independent per-user argmax.
- intervention point: decode/deployment
- defined in: `route-b-catfish-as-policy-design-note-2026-06-26.md:88-124`; `route-b-factorial-design-note-v3-2026-06-26.md:144-180`
- run status: **ran** (AF eval-only; A1/A2 trained under it; cross-over evals).
- run conditions: COND-ROUTE-B (lr 0.01 era).
- recorded outcome: AF calib J_w 4.44e-4, min_cov 1.000, qos 0.951; A1 4.97e-4, min_cov 0.999; B0 −1.0e-5 (collapsed); "AF−B0 = +4.54e-4 [lo>0]"; "the cross-over (same trained Q-heads, swap only the decode → collapse flips) is a clean ROOT-Q Branch-C diagnostic" (`route-b-factorial-VERDICT-G6-2026-06-27.md` L18-20, L52-67). But "A1/A2 SIGNIFICANTLY LOSE to a vanilla scalar-DQN ... DQN_scalar ... scores 6.10e-4 ... tops the entire board" (L12-16); later 5-seed nail: "WIN=FAILED seed-robust (mean ≈6.41e-4, all > A1 4.97e-4)" (`route-b-shared-q-isolation-COMPLETION-HANDOFF-2026-06-27.md` L7-8). Design-time warning: "Empirically, the load-blind facility-location arm A1 had WORSE cap_bump (0.4163) than per-user-argmax A0 (0.2422)" in the oracle probe (v3 §4.2 L168-174) → "cardinality ≠ coverage". LATEST: decode = the "de-collapse engine" in route-B but **under lr=0.01**; flagged "REQUIRES RE-CHECK" (lr file L86-91); decode flip at lr 0.01 in a later wave changed nothing ("flipping `hybrid → argmax` at 0.01/3000 gives 145.47 → 150.13 with identical min_cov", lr file L60-62). Phase-B: "The reusable asset is the coordinated DECODE itself" (`phase-b-verdict-CLOSURE-2026-07-01.md` L48-49).
- recorded cause: "per-user-argmax over a shared Q is a decode CLASS-failure — independent argmax mathematically cannot respect the env's strict per-satellite cardinality budget" (v3 §0 L43-46).
- inferred cause [I]: the decode's large effect is measured only against collapsed (lr-0.01) valuations; against a healthy lr-1e-3 learner the headroom is unmeasured in cluster A. It is also a hard-constraint-aware decode specific to family_b's k_cap cell-activation physics.
- premises: a hard cardinality/beam cap exists that independent argmax violates (env-specific); users pile on (collapse exists); valuation quality matters less than feasibility.

### A-15. Congestion context χ_u + user-specific symmetry-breaker (keep argmax, "B-column" state augmentation)
- mechanism: augment each user's state with pre-action per-(sat,cell) occupancy/demand-rank/active-set risk plus a per-user rank feature (SNR-rank among contenders) so identical-state users can learn different argmax actions.
- intervention point: representation
- defined in: `route-b-factorial-design-note-v3-2026-06-26.md:184-226` (§5.1a–5.1c)
- run status: **ran** (B1 = +χ plain TD; B2 = +χ catfish; also in A1/A2). No-leak + symmetry-breaker unit tests PASS; predictive diagnostic corr(pre-action χ contender-count, next-step cap-bump) = −0.44 (RUN-REPORT §4 L45-48).
- run conditions: COND-ROUTE-B; state 224-d χ-augmented.
- recorded outcome: "aug-credit B1−B0 = −5.6e-6 [−1.02e-5, −5.7e-7] (hi<0) — χ+state-aug alone does NOT help under argmax (slight harm)" (RUN-REPORT §7 L77). B1/B2 stay collapsed (active 3.0). Later: "the augmented-state occupancy features → refuted" as the collapse cause ("the historically-collapsed arms use the same augmented 224-d chi encoding") (lr file L18-19).
- recorded cause (design): "`χ_u` alone is mathematically insufficient ... it is a shared per-cell feature — identical-state users see the same χ_u ... argmax to the same cell together" (v3 §5.1a L196-199); symmetry-breaker was the fix.
- inferred cause [I]: trained at lr 0.01 — the lr-attractor ("seed-independent degenerate attractor ... bit-identical across seeds", lr file §4) plausibly swamped any representational effect; so the representation concept is untested on a healthy learner.
- premises: collapse is caused by simultaneous-move homogenization (later withdrawn as a general premise); a one-step-stale congestion signal predicts this-step pile-up.

### A-16. CDRL-core training bundle in route-B: asymmetric per-objective γ ([0.99, 0.90, 0.99]) + online value-stratified replay (no oracle, no second agent)
- mechanism: route top-X% transitions by realized per-objective return into a priority buffer; use near-myopic γ for handover, far-sighted for EE/load; applied to the same (single) learner.
- intervention point: experience (replay stratification) + other (discount)
- defined in: `route-b-factorial-design-note-v3-2026-06-26.md:230-250` (§6.2–6.3); `route-b-catfish-as-policy-design-note-2026-06-26.md:128-148`
- run status: **ran** (B2 vs B1 under argmax; A2 vs A1 under auction; 3 seeds × 3000 ep).
- run conditions: COND-ROUTE-B (lr 0.01, from scratch). Note: no second (catfish) agent and no injection — "catfish" here = the training recipe only (v3 §2 L102-104).
- recorded outcome: "B2−B1 = +6.085e-5 [+5.04e-5, +7.25e-5] lo>0 (sig)"; "A2−A1 = −1.48e-5 [−5.35e-5, +2.32e-5] SPAN0"; "catfish-protagonist = NO ... regime-trapped" (VERDICT-G6 L82-101). Secondary-effect mining (LATEST, 2026-07-01): auction column "catfish REDUNDANT-to-slightly-detrimental" (τ90 +59 ep slower, less stable, min_cov exact tie, lower qos 0.973 vs 0.990); argmax column "REAL but REGIME-TRAPPED" (faster τ90 3/3 seeds, −208 ep at W=51) (`catfish-secondary-effect-VERDICT-G6-2026-07-01.md` L20-44). Bottom line: "Catfish IS a real training enhancement — but its measurable effect is CONDITIONAL on the decode being weak" (L53-58). Later catfish-v2 archaeology tags this "built on pre-fix data" (÷G_T and C1 bugs; see A-11 note).
- recorded cause: "The coordinated decode already solves the allocation → catfish's value-stratified replay + asymmetric discount have no headroom to act" (secondary L31-32); "catfish acts on the value-LEARNING process, subsumed by the strong coordinated decode" (archaeology D10).
- inferred cause [I]: the only measurable lift was inside the lr-0.01 collapsed regime; whether it survives on a healthy lr-1e-3 learner is untested in cluster A. "catfish = a BUNDLE → B2−B1 = bundle-credit, intra-catfish sub-ablation deferred" (v3 changelog item 7) — so asym-γ vs stratified replay individually never isolated.
- premises: contested states are rare and under-fit by uniform replay; a learnable headroom exists that the decode does not already capture.

### A-17. Non-scalarized competitive auction ("genuine Multi-Catfish": per-objective bids traded off per cell, no pre-scalarization)
- mechanism: each objective head bids separately; open-set selection trades objectives off per cell (per-objective prices or Pareto open-set rule) — a state-dependent trade-off richer than fixed-w scalarization.
- intervention point: decode/deployment + objective
- defined in: `route-b-catfish-as-policy-design-note-2026-06-26.md:206-214`; `route-b-factorial-design-note-v3-2026-06-26.md:344-351`
- run status: **never built** (held option).
- recorded outcome (LATEST): "technically a LIVE pre-registered escalation — but less motivated post-fold: a vanilla scalar-DQN beats the auction, so the gap is the MODQN-shared-Q valuation ... a fancier auction is unlikely to be the lever. (Tag: hypothesis — §10 untested.)" (VERDICT-G6 L182-184); adjudication: "(b) §10 + Branch-A = NOT now / low-prior" (`route-b-INDEPENDENT-ADJUDICATION-2026-06-27.md` L76-79).
- premises: fixed-w scalarization loses value; objectives genuinely conflict per cell; decode-side competition is the lever. Premise "scalar-DQN beats auction" was itself measured at lr 0.01 era for the auction arms `[I]`.

### A-18. Decode cross-over evaluation (swap only the decode on fixed trained heads) — diagnostic method
- mechanism: score trained Q-heads under the other decode (argmax↔auction) with identical nets, isolating decode from training.
- intervention point: other (diagnostic)
- defined in: v3 §2 L105-114; used in VERDICT-G6 L64-67, L74-77
- run status: ran (eval-only).
- recorded outcome: "B1_xover (B1 heads, auction decode) → SPREAD J_w 4.76e-4; A1_xover (A1 heads, argmax) → COLLAPSE 1.95e-5" (boundary-map L17-20); "B2_xover ... 5.27e-4 @ min_cov 0.999" — "a disclosed eval-only upper-bound" (boundary-map L67-73).
- premises: decode and training are separable at eval time (pipeline coupling disclosed).

### A-19. MODQN shared-Q value-decomposition isolation (single-head scalar DQN vs shared-trunk 3-head with per-objective TD, same trainer/state/reward scale)
- mechanism: vary only the head architecture + its per-objective TD, with per-component rewards scaled by the same K_SCALAR as the scalar arm (target-magnitude parity).
- intervention point: representation / objective decomposition (diagnostic)
- defined in: `route-b-shared-q-isolation-PREREG-2026-06-27.md`
- run status: **built, run started, CANCELLED before completion** — "⛔ CANCELLED (2026-06-27, USER DECISION = CONCLUDE) — NO RESULT WILL BE PRODUCED" (`route-b-shared-q-isolation-COMPLETION-HANDOFF-2026-06-27.md` L3-8). (Prior progress note mentions "shared_q_isolation (penalties, EXP, ACRM)" configs under `configs/shared_q_isolation/v3/` used in July waves — other cluster.)
- recorded outcome: none from this prereg. The motivating counterexample: "DQN_scalar = per-user-argmax single-head, de-collapses active 11; B1 = per-user-argmax MODQN-3-head, collapses active 3" (VERDICT-G6 L154-158) — later superseded by the lr finding (the collapsed arms were lr 0.01; the field DQN trainer uses `LR = 1e-3` — verified in `field_baselines/dqn_baselines.py:193` — so the motivating single-head-vs-3-head contrast was also an lr contrast; see A-60).
- recorded cause of design: BLOCKER-3 "raw-normalized would be ~1000× too small → would fake an undertraining 'collapse'" (prereg L19-21) — a per-component reward-scale trap relevant to any multi-head decomposition.
- premises: collapse is architecture-rooted (withdrawn 2026-07-20 as general premise).

### A-20. Coverage/fairness Pareto reframe (score deployable arms on J_w × min_cov/qos instead of the scalar only)
- mechanism: treat worst-user coverage as a second objective; coordinated decode "guarantees every user is served" while scalar DQN "starves a tail user (11% served)".
- intervention point: objective (evaluation frame)
- defined in: `route-b-INDEPENDENT-ADJUDICATION-2026-06-27.md:64-75`; `route-b-boundary-map-FLOOR-DRAFT-2026-06-27.md:42-83`
- run status: ran eval-only (`route-b-factorial-fairness-pareto-RESULT.json`).
- recorded outcome: DQN_scalar J_w 6.10e-4 / qos 0.915 / min_cov 0.110 vs A1 4.97e-4 / 0.990 / 0.999 → "mutual non-domination = an efficiency-vs-equity trade-off"; DQN_scalar Jain 0.59/0.74; "the min_cov floor is a knife-edge" (boundary-map L51-82).
- premises: coverage is valued beyond the scalar bar (a user/frame decision); lr-0.01 era arms.

### A-21. Frozen-Q reuse under the coordinated decode (Phase B null-Q cross-over)
- mechanism: take archived trained (collapsed) Q-nets, evaluate them under the coordinated decode vs a matched random-weight net ("null") and vs AF.
- intervention point: decode/deployment (transfer)
- defined in: `phase-b-verdict-CLOSURE-2026-07-01.md`
- run status: ran eval-only, 11 archived generations, 48 matched episodes.
- recorded outcome: "0 ACTIONABLY-REUSABLE · 9 Q-INFORMATIVE-only · 2 DEAD-OTHER-frozen"; "NO frozen family_b Q clears the deployable AF floor ... they beat a matched-arch RANDOM net ... but never significantly beat AF" (L40-47). Scope: "do NOT foreclose warm-start / retrain / reward-shaping value" (L52-54).
- premises: learned valuations add value over a fixed myopic valuation under a coordinated decode (not supported for these lr-era nets).

- **COND-P4-DISTILL** (the June 22–25 "amortized distillation" line, gates 1 / 2 / 2b): env `family_b` EUV
  `3cd5000a`, U=100, 4 slots × 7 per-user neighborhood cells = 28 actions, k_cap=3 active cells per slot, active cell
  serves all its users (shared beam), cap-bumped users dropped (`p4-c1c2-constraint-mismatch-BLOCKER` §1). Per-user
  state 140-d `[access_vector(28), channel_quality(28), beam_offsets(56), beam_loads(28)]`; access_vector = one-hot of
  the user's PREVIOUS action (gate-2 prereg L11-12). **Wiring = supervised CE distillation of a static planner
  teacher** (planner_then_balance_t12 for gate-1; sticky_planner for gate-2/2b), Adam LR 1e-3, minibatch 16; **no RL,
  no TD, no reward-trained heads** in the student. Scored on realized η_EE (`family_b_eta_r1`; gate-1) or calibrated
  J_w [0.5,0.3,0.2] + QoS + min-coverage + matched latency speedup ≥10× (gate-2/2b). Bar = round_robin (weak static).
  η_EE here is "meaned over users/steps" (fidelity prereg §3) → a per-user mean (mean-of-ratios style) `[I]`.
  Later (July) a "÷G_T" EE-formula bug was fixed ("÷G_T distortion ~9200× confirmed (old panel genuinely wrong)",
  chronicle L2044) — all June η_EE / J_w numbers predate that fix `[I: dated before 2026-07-03]`.

### A-22. Amortized distillation of a strong static planner into a cheap student ("learn-to-optimize" frame), per-user-argmax (a) and autoregressive occupancy-conditioned (b) students
- mechanism: CE-clone the per-user actions of the expensive coordinated planner; (b) conditions user u's head on running occupancy of users decoded before it; one DAgger round for exposure bias.
- intervention point: experience (demonstrations) + decode/deployment (AR decode)
- defined in: `p4-distillation-fidelity-killtest-prereg-2026-06-22.md`; `THESIS-FRAMING-amortized-MORL-2026-06-22.md` (not yet read in full; see A-35)
- run status: **ran** (scored go-server, 3 seeds, 17246 s).
- run conditions: COND-P4-DISTILL; teacher planner_then_balance_t12 (η ceiling C=4.721e12, active 21, Jain 0.96).
- recorded outcome (quote, `p4-fidelity-ab-RESULT-adjudicated-2026-06-23.md`): "realized-η ANTI-correlates with CE/top-1 improvement ... (A) per-user: η peaks 0.59C @ep100, declines monotone to 0.50C @ep800 (CE 2.81→0.67, top-1 0.18→0.83). (B) autoregressive: η peaks 0.70C @ep150, settles 0.62C" (L12-15); "DAgger HURT ... pre-DAgger B @ep800 = 0.74C → post-DAgger 0.62C" (L16-17). LATEST: "a scoped NEGATIVE for the (a)/(b) CE-to-per-user-label students under THIS training/eval setup" (L27-29).
- recorded cause: "The failure mode = objective/decoder MISMATCH, NOT under-convergence (CE-to-per-user-argmax-label is a poor proxy for realized η — matching individual teacher actions ≠ reproducing the joint coordination that yields high η)" (L25-26).
- premises: a better-than-learner teacher exists (true here: static planner is the η ceiling); per-user labels carry the joint structure (refuted — "the same user-state maps to DIFFERENT teacher labels ACROSS snapshots", fidelity prereg §2).

### A-23. One-shot permutation-equivariant joint decoder (SetEncoder over users) + capacity-enforcing projection (c1 soft / c2 exact per-slot top-k cell selection) + untrained-encoder attribution control (c0)
- mechanism: Set-Transformer encodes all users jointly → per-(user,cell) scores → per-slot "open ≤3 cells, assign users" projection; (c0) = same projection on a random encoder, to test whether learning matters.
- intervention point: representation + decode/deployment
- defined in: `p4-amortized-morl-FROZEN-design-spec-2026-06-23.md:55-101`; corrected projection `p4-c1c2-constraint-mismatch-BLOCKER-2026-06-23.md:64-76`; used by gate-2 `p4-gate2-rescoped-demote-win-prereg-2026-06-23.md`
- run status: **ran** as gate-2 arm (P) with sticky teacher (A-24).
- run conditions: COND-P4-DISTILL; 141-d input (140 + has_prev bit); readout c2 selected on validation.
- recorded outcome: see A-24 (J_w lower-CI 4.03e-4, D=(P)−(c0) lower-CI 3.55e-4 ≫ τ 5e-5 = learned; 21.9× speedup; coverage 0.0). Design lesson recorded: the first frozen projection modelled capacity as 84 per-beam buckets — "wrong in both directions ... TOO TIGHT on within-cell sharing ... MISSING the real binding constraint" (BLOCKER §2); caught before running. Smoke: "(c2) smoke reached ~0.99C via the projection, at encoder top-1≈13%" → "the classical feasibility-greedy PROJECTION may be doing the work" (fidelity-ab §3 L35-37).
- recorded cause: tail-user starvation = "assignment-quality collapse, NOT a beam-budget shortfall. (P) uses MORE active beams than the teacher in every phase ... yet starves more users" (`tail-user-coverage-diagnosis-findings-2026-06-24.md` L36-39).
- premises: a hard per-slot cardinality constraint exists (family_b-specific); a coordinated teacher exists to distil.

### A-24. Low-churn (hysteresis) teacher distillation with a `has_prev` bit (gate-2 "demote-win")
- mechanism: distil `sticky_planner` (greedy + per-step hysteresis on prev actions) into A-23's decoder; the state's access_vector already exposes prev action, `has_prev` disambiguates t=0.
- intervention point: experience (teacher choice) + representation (has_prev bit)
- defined in: `p4-gate2-rescoped-demote-win-prereg-2026-06-23.md` (v7)
- run status: **ran** (scored, 3 train seeds, sealed {600,700}).
- run conditions: COND-P4-DISTILL; pure CE; "ce_flat convergence bug ... never converges → grinds to MAX_CEILING=2000" (postwin handoff L19).
- recorded outcome: "(P) sealed J_w lower-CI 4.0295e-4 (0.64C; mean 0.71C) ≫ bar round_robin 1.6071e-4 ≫ plain-MODQN −4.9e-5 ... 21.9× ... learned (D ... 3.5455e-4 ≫ τ_attr 5e-5) ... Coverage (per-eval-seed min): (P)=0.0/0.0, round_robin=0.0/0.0, teacher=0.8/1.0" (`NEXT-SESSION-P4-gate2-postwin-handoff-2026-06-24.md` L10-13). Later revisions: "The gate-2 J_w margin is ALL on the η_EE axis → NEVER headline 2.8× / 0.71C / beats-Sun2024" (6-arm VERDICT L65); "DQN_scalar also kills the route-C/P4 gate-2 (i)-WIN (student 4.03e-4 < DQN_scalar 5.96e-4) → win=FAILED" (`route-b-LOCAL-CONTROLLER-thesis-handoff-2026-06-27.md:16`).
- recorded cause: see A-23; plus win "margin is ALL-η_EE (r2/r3 worse than round_robin)" (CA-CPBR design note §1 L91).
- premises: the plain-MODQN baseline it beats is collapsed (−4.9e-5) — that baseline is the lr-era retrain (`family-b-baseline-retrain-2026-06-12`) `[I: lr of that retrain not verified here; route-B B0 reused a 2026-06-14 retrain; the July lr finding says the faithful B0 collapse "REQUIRES RE-CHECK"]`.

### A-25. Coverage-aware decode-time repair (L2a: reassign sub-QoS users to feasible beams at inference)
- mechanism: after the one-shot decode, greedily reassign users below QoS floor using the env's rate estimator, maximizing served count.
- intervention point: decode/deployment
- defined in: `tail-user-coverage-diagnosis-findings-2026-06-24.md:45-90`; script `coverage_aware_decode_screen.py`
- run status: ran (local screen, net-0, sealed seeds).
- recorded outcome: J_w 4.677e-4 → 4.841e-4 (103.5% retained), QoS 0.906 → 0.981, but "min-coverage 0.000 → 0.000"; speedup 21.8× → 6.2×; "min-coverage = converged greedy fixed-point ... No single-user beam swap can serve the worst-user-worst-phase without un-serving another → needs the teacher's JOINT/simultaneous coordination" (L63-82); verdict "a cheap decode patch does NOT cleanly win".
- recorded cause: "min-cov is a TEMPORAL-min: the worst user must be served across all 320 steps in every phase — per-step single-user greedy can't target it" (L77-78).
- premises: worst-user coverage metric is a temporal min (metric design drives the finding).

### A-26. DAgger on-policy relabelling to close the tail-coverage gap (gate-2b; also the fidelity-run DAgger round)
- mechanism: roll the student, relabel visited states with the (hysteresis) teacher using the student's actual prev action, aggregate, retrain R1–R3; control (P+BC) matched on D₀ exposure; hard-state ×3 variant.
- intervention point: experience
- defined in: `p4-gate2b-dagger-coverage-win-prereg-2026-06-24.md`
- run status: **built; scored run HALTed at faithfulness pre-gate before any student score** — "fresh seed 1600: `sticky_planner` teacher min-cov 0.0 < 0.05 ... no scored RESULT exists and none will" (`gate2b-halt-diagnosis-2026-06-24.md` L8-15; CA-CPBR note §0c L25-27). The earlier fidelity-run DAgger round (A-22) did run: "DAgger HURT ... 0.74C → 0.62C".
- recorded outcome / cause: teacher-design artifact — "`sticky_planner`'s per-step HYSTERESIS starves a user that the non-sticky `planner` serves" (halt L31); "NO single teacher has BOTH J_w AND coverage" (L32) → motivated A-6.
- premises: teacher serves the tail on every seed (false on seed 1600).

### A-27. Ω-conditioned MORL net (PD-MORL / envelope-Q) vs per-weight behaviour-clone ensemble — runtime multi-objective weight adaptation
- mechanism: one preference-conditioned net with vectorized per-objective Q heads, tested on out-of-sample Ω vs per-weight clones and Ω-conditioned BC.
- intervention point: objective + representation
- defined in: `p4-amortized-morl-FROZEN-design-spec-2026-06-23.md:105-141`; pretest `p4-morl-vs-clone-pretest-prereg-2026-06-23.md`
- run status: cheap REF-only pretest gate ran; full MORL net never built.
- recorded outcome: "Under this env/objective set and the frozen v2 coordinated reference, the preregistered runtime-weight control gate fails with persistent objective-control mismatch; objective-inherent thinness remains unproven" (`p4-morl-v2-RESULT-adjudicated-2026-06-23.md` L33-35); "only HANDOVER self-leads (and it leads BOTH r2 and r3); EE and LOAD weight corners do NOT control their own realized axes" (L36-38). Decision: demote to deployability frame.
- recorded cause: reference-conditioned objective-control mismatch (coordination amount gated only on w2).
- premises: the 3 objectives genuinely conflict so the Pareto front is non-trivial (unproven; EE/load weight corners did not separate on family_b).

### A-28. Demo-guided RL: DQfD (large-margin + n-step TD, permanent demo replay) with margin DECAY, then AWAC/CRR offline→online fine-tune
- mechanism: seed Q toward teacher actions with margin loss, let TD refine beyond cloning; decay margin so runtime-Ω adaptation isn't destroyed.
- intervention point: penalty/loss + experience
- defined in: `p4-amortized-morl-FROZEN-design-spec-2026-06-23.md:145-158`; role reconcile `p4-catfish-role-reconcile-design-DRAFT-2026-06-23.md`
- run status: DQfD margin (fixed 0.8) used only as the sticky channel inside the 6-arm distillation fine-tune (COND-P4-6ARM); AWAC/CRR never built in cluster A. (July "fulldqfd" waves exist — other cluster; COLLAPSE-ROOT-CAUSE-IS-LR uses `fulldqfd_OFF` vs `fulldqfd_OFF_lr001` cells.)
- recorded outcome: none isolated in cluster A.
- recorded principle: "catfish is load-bearing ONLY in route (ii) [demo-guided RL] ... catfish does NOT fix decoder REPRESENTABILITY ... it can only help the TRAINING / cold-start REACH fidelity" (role-reconcile L16-26).
- premises: from-scratch RL "won't find the coordinated policy under ε-greedy" (discoverability gap) — premise weakened by the later lr finding (healthy lr-1e-3 learner does not collapse) `[I]`.

### A-29. Near-global EE teacher via multi-ratio quadratic-transform fractional programming (+ WMMSE interference handling) — teacher upgrade
- mechanism: replace heuristic planner teacher with a sum-of-ratios FP optimizer so "% of optimal" is claimable.
- intervention point: other (teacher / reference)
- defined in: `p4-amortized-morl-FROZEN-design-spec-2026-06-23.md:200-207`
- run status: never built.
- premises: EE objective is a sum-of-ratios (per-user EE) — "single-ratio Dinkelbach is insufficient"; would be different for pooled EE (single ratio) `[I]`.

### A-30. Catfish generic-validity kill-test on toy hard-exploration envs (DeepSea N∈{20,30}, MountainCar) vs tuned DQN / NoisyNets / PER / DQfD, with leave-one-out M1/M2/M3
- mechanism: test whether catfish's transferable core (stratification + asymmetric γ + 70/30 conduit, ACRM off) has any generic merit.
- intervention point: experience + exploration
- defined in: `p1-catfish-generic-validity-killtest-prereg-2026-06-22.md`
- run status: **built, smoke only, never scored** — "BUILT (`src/modqn_paper_reproduction/catfish_generic_killtest/`), DeepSea smoke PASS ... MountainCar smoke used a STUB" (`NEXT-SESSION-P4-phaseL-build-handoff-2026-06-23.md:6`); later "real gymnasium MountainCar + DeepSea smokes PASS `dd326c4` (⚠ `killtest_analysis.py` ...)" (`NEXT-SESSION-P4-morl-respec-implement-handoff-2026-06-23.md:80`). No scored RESULT found `[I: grep found none]`. (Different from the July "P1 faithful catfish" on family_b — catfish-v2 cluster — which was NULL/NEGATIVE 3/3 seeds with "γ_cf wired-but-inert on family_b", chronicle L2030.)
- recorded prior: "Catfish-as-win-engine is [grounded] VERY-LOW prior from 5 angles (... M2 ≈ Curse-of-Diversity ICLR24, M3 ≈ SUPER NeurIPS23 ...)" (prereg L19-22).
- premises: catfish's value is an exploration / high-value-experience-concentration effect, testable where sparse reward makes such experience rare.

- **COND-JUNE19-TRACKB** (June 17–20 diagnosis era: newalgo / track-B / symmetry-breaker / foundation brief):
  env family_b (Walker-180, L_W=4, 28 slots, 100 users, k_cap admission), r1 = **throughput** ("r1 = throughput (EE
  deferred-not-dead)", `newalgo-design-v0-candidates.md` §2 L80; DR-MODQN "guards `r1_reward_mode == throughput`",
  `track-b-mechanism-sdd-dr-modqn-v1.md` §4). Scored on calibrated weighted scalar [0.5,0.3,0.2]; FIELD gate
  +1.2292081e-4 (= rss_max). Collapsed B0 = `family-b-baseline-retrain` 3000 ep, ε decay 2000 (foundation brief §1);
  trainer default `learning_rate: float = 0.01` (`runtime/trainer_spec.py:56`, verified) and stage-1 cells record
  `"learning_rate": 0.01` (verified in `artifacts/stage1-collapse-diagnostic/*/run_metadata.json`). ★ The foundation
  brief explicitly argued "**target-smoothing / Double-DQN / lr (general DQN-stability tricks) target the WRONG
  thing**" (`foundation-retrain-anti-homogenization-research-brief.md` §2 L56-59) — later contradicted by
  `COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md`. All "collapse" facts quoted below (Q-row corr 1.000, active≈1,
  M1≈26% of random) were measured on lr-0.01 checkpoints `[I: B0 retrain lr inferred from trainer default + the lr
  file's "old era is a SINGLE cell (hybrid/0.01/3000, 82 runs)"]`.

### A-31. DR-MODQN: marginal-congestion difference reward D_i on the r1 (throughput) head (QUICR/WLU class)
- mechanism: replace user i's r1 training target with `D_i = G(a) − G(a_{−i})`, G = Σ r1 (true leave-one-out re-evaluation at the admission boundary, with exact fading replay), so piling onto a crowded beam yields negative credit; decode stays faithful per-user argmax; eval on unmodified reward.
- intervention point: reward (credit assignment)
- defined in: `newalgo-design-v0-candidates.md:111-141` (Candidate 1); `track-b-mechanism-sdd-dr-modqn-v1.md` (v1.1); prior art `track-b-prior-art-findings.md`
- run status: **cheap screens ran, heavy RL never trained**. (1) differentiation kill-screen (simultaneous best-response on D_i + supervised imitation), (2) corrected handover-aware screen. D_i counterfactual validated byte-exact (V1/V1b/V2 max-abs-diff 0.0).
- run conditions: COND-JUNE19-TRACKB; eval-only / supervised, no RL loop; 3 eval seeds × 3 phases × 30 states.
- recorded outcome: kill-screen "FAILED as executed ... weighted −7.6e-4…−9.3e-4 ≪ FIELD gate" but "dominated by an r2-handover-churn ARTIFACT of a handover-blind, r1-only best-response proxy ... c_r1 POSITIVE in all 3 seeds ... churn-free counterfactual sits AT the gate for 2/3 seeds" (`track-b-differentiation-gate-findings.md` L17-26). LATEST (corrected screen): "SCOPED-NEGATIVE-narrow ... Substantive read = reachability/representability wall (≈ INCONCLUSIVE-3a)"; single-shot supervised Q "collapses even when its s600 teacher contains those good labels" (`track-b-corrected-screen-findings.md` L25-30, L84-92). "Heavy = NO-GO at a LOWERED prior ... NOT 'unwinnable'".
- recorded cause: "D_i shapes the r1 head only ... so the prereg's 'argmax of D_i' simultaneous best-response is handover-blind → relocates ~all 100 users every round → floors r2" (differentiation L66-70); SDD's own risk: "D_i is computed from REALIZED post-assignment load, but the decode acts on STALE pre-assignment load ... the self-reinforcing simultaneity loop ... is structurally still present" (newalgo §7 L288-296).
- inferred cause [I]: the "homogenization attractor" D_i was built to escape was measured on lr-0.01 nets; with a healthy lr the need (and baseline) differ. Also D_i is defined on throughput; for an EE objective the externality definition would change (the SDD guard refuses EE r1-mode).
- premises: collapse exists and is a credit-assignment failure (per-user reward omits externality on co-assigned users); the win bar is a faithful-decode FIELD bar; hard k_cap cardinality physics.

### A-32. Private per-user random tag (fresh per-episode ξ appended to state) as symmetry-breaker — REJECTED
- mechanism: give identical users a random input to break argmax ties.
- intervention point: representation
- defined in: `track-b-mechanism-sdd-dr-modqn-v0.md` (not read; summarized in v1 §0 and `symmetry-breaker-design-2026-06-19.md` §2)
- run status: never built (dropped at design review).
- recorded outcome/cause: "premised on 'identical inputs → identical action → collision,' but the measured collapse is representation homogenization (the net maps DISTINCT inputs → affinely-identical Q-rows), and the supervised `f` (no tag) already spreads (active 9.58)" (DR-MODQN v1 §0 L27-31); "Nullable ... Cannot agree on the scarce cell ... Concurrent-fragile" (symmetry-breaker §2).
- premises: users are indistinguishable (false on family_b geometry).

### A-33. Common-signal correlated-equilibrium symmetry-breaker (shared per-step nonce ω_t appended to every user's observation, sticky/rate-limited; SIC-class)
- mechanism: a broadcast shared random signal lets simultaneous independent argmaxes agree on who takes which scarce cell (plays the role of the sequential planner's order), with stickiness to avoid induced handovers; paired with D_i and a spread/sticky catfish injector.
- intervention point: representation (+ experience via catfish)
- defined in: `symmetry-breaker-design-2026-06-19.md` §3
- run status: **never built** (design-gate PASS "credible, NOT a design-level kill"; KEEP-vs-CONCEDE user fork).
- recorded outcome: "most-likely failure = ω_t-NULLING → T0"; "hollow is the MODAL non-T0 outcome: A_zero-signal (a constructive-class ranked heuristic) will LIKELY clear the weak gate" (§7 L229-238); "a per-step-FRESH ω_t ... can INDUCE needless handovers" (codex, §3 L106-110).
- premises: hard cardinality cap makes coordination necessary; users are distinguishable by geometry; herd-relocation is the failure (flagged "HYPOTHESIZED, NOT cleanly demonstrated", §1 L50-58).

### A-34. Population-equivariant symmetry-breaking joint policy (Deep-Sets/attention over users, trained end-to-end on MO reward with an anti-correlation objective)
- mechanism: a joint policy that sees all users and outputs the joint assignment, with a symmetry-breaking training objective.
- intervention point: representation + decode/deployment
- defined in: `newalgo-design-v0-candidates.md:163-177` (Candidate 3, "ESCALATION (Rung 2)")
- run status: never trained with RL. A Set-Transformer student was later built for supervised distillation (A-23), not this RL form.
- premises: collapse is a shared-policy symmetry problem; attribution cost accepted (least faithful).

### A-35. Anti-homogenization training-signal menu for a frozen per-user-argmax decode: EOI identifiability reward, direct cross-user Q-row diversity penalty, DR3 feature-rank regularizer, action/beam-occupancy count penalty, Munchausen soft target, CDS MI reward, SePS parameter clustering
- mechanism: add an intrinsic/auxiliary loss or reward on top of the frozen task reward to push per-user Q rows apart (or keep features full-rank / soften greedy peaking).
- intervention point: penalty/loss + exploration (intrinsic reward) + representation (SePS)
- defined in: `foundation-retrain-anti-homogenization-research-brief.md` §4–§5 (ranking: EOI and cross-user diversity regularizer co-primary; DR3 diagnostic; occupancy-count penalty candidate; Munchausen complement; CDS/SePS/congestion difference-reward reserve)
- run status: **none of these arms trained in cluster A** `[I: no RESULT found in the files read; later "shared_q_isolation (penalties, EXP, ACRM)" July configs may relate — other cluster]`. Only the cheap supervised-learnability gate ran (A-36).
- recorded outcome: design-level: vanilla state-novelty exploration (RND/ICM/pseudo-counts) "expected to FAIL against per-user-argmax herding" — narrowed to "rules out observation-novelty, NOT ... an ACTION/beam-occupancy count" (§4c L124-131). Envelope-Q / per-objective ε decoupling = "wrong axis (our herding is cross-USER)" (L133).
- recorded cause (design): the collapse is "shared-parameter MARL homogenization where the 'agents' are the USERS" (§4 L106-109).
- inferred cause [I]: premise that "lr ... target the WRONG thing" (§2) was falsified in July; these anti-homogenization losses were designed against an lr-induced attractor.
- premises: collapse exists and is NOT an optimizer-hyperparameter artifact.

### A-36. Supervised faithful upper bound `f` (DQN-sized per-user argmax net trained to imitate a spread planner) — representability probe
- mechanism: supervised imitation of a geometry-keyed spread assignment through the same per-user argmax decode.
- intervention point: other (diagnostic)
- defined in: `foundation-retrain-anti-homogenization-research-brief.md` §9; `newalgo-design-v0-candidates.md` §10
- run status: ran (local supervised).
- recorded outcome: "SPREADS: active 9.88 / modal 0.329 ... → the frozen per-user-argmax decode is NOT the blocker ... the collapse is a TRAINING/optimization failure" (brief §9 L281-285); but on weighted metric "f-FLOOR-CAPPED (W_f −5.33e-5 ...)" — "cap-bumps 0.327 / served 0.654" (newalgo §10 L407-414).
- recorded cause: "a SIMULTANEOUS per-user argmax cannot reproduce the planner's SEQUENTIAL joint construction" (symmetry-breaker §1 L42-48).
- premises: a hard k_cap cardinality constraint (family_b-specific).

### A-37. Plasticity remedy control (ReDo / periodic reset) as first control before any anti-collapse mechanism
- mechanism: reset dormant neurons / periodic re-init to counter primacy/plasticity loss (early-best/late-worse signature).
- intervention point: other (optimizer / network plasticity)
- defined in: `newalgo-design-v0-candidates.md` §7 L268-272 (codex BLOCKER), locked in `foundation-retrain-fork-stance.md` (not read)
- run status: ran in Wave-1 per later record — "Wave-1 already ruled out the TRAINING-side plasticity lever on family_b (ReDo, 3/3 collapsed)" (`collapse-rootcause-diagnostic-design-2026-06-20.md` §6 L186-187).
- run conditions: family_b lr-0.01 era `[I]`.
- recorded outcome: 3/3 collapsed.
- premises: collapse is plasticity loss (not supported); note the brief observed "best-eval episode ... ε ≈ 0.85/0.83/0.98 → best = HIGH-ε exploration residual" (brief §1 L43-48) — a signature consistent with a too-high lr `[I]`.

### A-38. Occupancy-aware sequential decode ("coordination-learned", `coordinated_multi_catfish`) and state de-saturation (`OffsetMaskedMODQN` offset mask) — stage-1 algo levers; plus hard-cap removal / finite-demand env rungs
- mechanism: (a) decode users sequentially conditioned on running occupancy; (b) de-saturate the state offsets block; (c) env ladder R1 no hard cap, R2 served-demand reward.
- intervention point: decode (a), representation (b), environment (c)
- defined in: `collapse-rootcause-diagnostic-design-2026-06-20.md` §1–§4; result `stage1-RESULT-sufficiency-map-2026-06-20.md`
- run status: **ran** (45 learned cells, 5 seeds, 9000 ep budget, ε decay 2000, reward calibration on).
- run conditions: family_b R0 frozen + sibling R1/R2; **lr 0.01** (verified in run_metadata); weighted calibrated scalar; per-user argmax.
- recorded outcome: "de-sat dissolves R0 = False (offset_mask is a NO-OP: byte-identical to plain on every rung). coordination-LEARNED dissolves R0 = False (active=1.0, slightly worse than plain). oracle-UB dissolves R0 = True (active 28, weighted 0.959)"; "on R1 (no cap) full spread DEGRADES weighted to −0.236 (spreading is HARMFUL once the cap is gone)" (stage1 L28-38). Reading: "a reachability / LEARNABILITY gap on the frozen env" (L42-45).
- recorded cause: learnability gap (records), vs later lr artifact (July).
- premises: collapse is intrinsic; **spreading helps only under the hard cap** (explicit finding: without the cap, spreading hurt the weighted scalar).

### A-39. Weighted-balance / FIELD-bar objective reframe (win on the source paper's weighted [0.5,0.3,0.2] vs weak statics; strong statics disclosure-only)
- mechanism: re-center the win claim on the multi-objective balance axis a single-criterion static cannot occupy.
- intervention point: objective (evaluation frame)
- defined in: `newalgo-design-v0-candidates.md` §0, §8.1–8.2
- run status: probes ran (weighted-balance headroom, f-on-weighted).
- recorded outcome: "the zero-learning ceiling on the weighted metric is HIGH + balanced (fair `sticky_planner` +3.18e-4; uid-keyed `round_robin` +3.73e-4) and the faithful-per-user-argmax floor is LOW (+1.25e-4). No faithful arm spans the gap ... the 4th 'static eats it'" (§9 L386-391).
- premises: J_w is the scored metric (the new project scores pooled EE — different objective) `[I]`.

### A-40. SDD-01: sequential occupancy-conditioned decode IN the training loop (C1) + congestion/hazard state-aug F1/F2/F3 (C2) + "catfish re-conceived" as a training-only joint best-response planner Ψ_{J_w} injected as reward shaping S[u,j] + per-objective difference reward d[u,j] (C3) + collapse-triggered routing (C4)
- mechanism: users decode one by one conditioned on running virtual occupancy; TD target re-runs the sequential decode on s′ with the target net (joint-snapshot replay); training reward `shaped_r[u,j] = (r_j/scale_j)[u] + α_S·S[u,j] + α_D·d[u,j]` from a non-learning weighted joint planner; deploy/eval shaping-free.
- intervention point: decode/deployment (C1) + representation (C2) + reward (C3) + other (C4 trigger)
- defined in: `contribution-sdd-01-sequential-decode-catfish-credit-2026-06-21.md` (codex r5 SOUND)
- run status: **only C1 was built and run** ("USER chose the C1-only cheap kill-test", header L9-10). C2/C3/C4 never built.
- run conditions: family_b R0 frozen, r1 throughput `[I: §6 figure says "r1 thrpt"]`, calibrated J_w (R0 gate RSS_max +0.582, round-robin floor +1.45 on that calibration), 5 seeds, lr presumably 0.01 trainer default `[I]`.
- recorded outcome (C1 kill-test, `G6-codex-verdict-c1-killtest-2026-06-21.md`): "seq J_w=+0.1197 ≈ plain +0.1224 (paired Δ=−0.0027 ...) ... seq active-beams = 1.0, identical to plain → the sequential decode did NOT spread" (L14-16). Verdict "SOUND-WITH-CAVEATS ... the negative is NARROW": "the decode adds only 1/num_users = 0.01 to the load slice per assignment ... swamped by the ~1e7-scale throughput head" (L24-28). Follow-up occupancy-strength probe: "amplify the EXISTING in-feature occupancy term is DEAD ... (5/5 seeds incl. 2 old ckpts, k≤100, argmax_flips=0/100, only the external penalty spreads)" (`G6-occupancy-result-verdict-2026-06-22.md` L15-18). THESIS-FRAMING §8 lists "C1 sequential-decode as a collapse-cure — tested-FAILED (active 1.0, tied plain)".
- recorded cause: in-feature occupancy signal too weak relative to throughput-head scale; frozen Q "load-insensitive" ("a free sequential decode over the FROZEN Q is byte-identical to argmax", SDD §1 L62-64).
- inferred cause [I]: unnormalized reward scale (~1e7 throughput head) and lr 0.01 — a collapsed, load-insensitive Q is the lr-attractor signature; the decode had nothing to condition on.
- premises: collapse exists; the Q can become load-sensitive under training; hard cardinality cap.
- sub-concept (C3 shaping) premises: a better-than-learner joint planner exists (true on family_b); "non-hollowness is EMPIRICAL, not theorem-backed" (§5.3).

### A-41. Per-user local potential PBRS `Φ_j(row_u)` (and the withdrawn "provably non-hollow" joint-planner PBRS)
- mechanism: potential-based shaping from a function of the per-user decision row (incl. running occupancy), giving per-head invariance; the stronger joint-Ψ PBRS was the original claim.
- intervention point: reward
- defined in: SDD-01 §5.3 L267-281; referenced in `catfish-last-design-candidates-2026-06-24.md:71-76`
- run status: never built (documented fallback only).
- recorded outcome: "The earlier 'provably non-hollow PBRS' claim is WITHDRAWN: PBRS policy-invariance (Ng'99) requires the potential to be a function of the state the Q-value is defined over, but Q_j is over the per-user local row while Ψ_{J_w} is joint" (SDD-01 §5.3 L268-270); "per-user potential cannot carry the full JOINT signal" (CA-CPBR note §7).
- premises: per-user Q over a local row + joint objective (shared-Q per-user architecture). In an architecture where Q is over the joint state, the joint potential would be admissible `[I]`.

### A-42. External occupancy penalty at decode (Ye-bias / live-load bias over a frozen Q)
- mechanism: add a per-beam load penalty to Q at decode time, building load online per assignment.
- intervention point: decode/deployment
- defined in: referenced in `newalgo-design-v0-candidates.md` §1 L66-69 (`materiality-verdict.md`); `G6-codex-verdict-c1-killtest-2026-06-21.md` L28-29
- run status: ran (materiality probe, occupancy-strength probe).
- recorded outcome: "a load-biased / live-load argmax over the frozen collapsed Q reaches ≈ RANDOM"; external penalty "DID force spread (active 28, J_w +1.45..+1.59) and exposed a ~0.14 SNR-spatial signal"; but "spreads HOLLOW (near-uniform, active=28, modal 0.04; no spatial capture computed)" (occupancy verdict L28-30).
- premises: frozen collapsed Q (lr-0.01 era); spreading is valuable (true under hard k_cap; false without cap per A-38).

### A-43. Demand-in-state (per-beam demand block appended to state) + de-saturated (relu) net
- mechanism: make per-cell demand visible in the per-user observation so argmax can differentiate.
- intervention point: representation
- defined in: `demand-in-state-splitter-design-2026-06-22.md`
- run status: **learned test never run** — closed by a data-blind preflight.
- recorded outcome: "demand signal STRUCTURALLY COARSE — ~13 unique demand blocks / 100 users ... ~1.86 distinct demand VALUES per user"; demand-greedy heuristic "buys NO meaningful extra spread over the zero-info references" → "DO NOT spend go-server ... CLOSE it" (L138-153).
- recorded cause: family_b demand is a 7-cell neighbourhood tiled ×4 with bimodal hot/cold; and "A per-user state feature CANNOT solve SIMULTANEOUS coordination" (codex, L109-111).
- premises: demand heterogeneity exists in state at useful granularity (false on het family_b).

### A-44. Soft-share (no hard cap) env family + channel-aware coordination heuristics — "existence gate" for a coordination prize
- mechanism: remove hard k_cap (soft B/N share), sweep U, test whether any cheap channel-aware / sticky coordination heuristic beats the best zero-learning rule on J_w.
- intervention point: other (environment / existence test)
- defined in: `step1-existence-gate-VERDICT-2026-06-22.md`; `softshare-existence-scoping-NOTE-2026-06-22.md`
- run status: ran (non-learning, local).
- recorded outcome: "EARNED (D) ... at no load does the best feasible non-learning coordination heuristic beat the best zero-learning rule by the seed-material margin δ*, and the network is never coordination-relevantly congested (blind spread serves ~99–100% of users above the 10 Mbps QoS floor at every load)" (step1 L17-22). Mechanism: "every COORD candidate ... pays a large r2 handover penalty (r2 ≈ −0.7 to −0.85) because it re-optimizes per step chasing the best-γ beam" (L65-72). Soft-share scoping: "the closed-form soft-share objective J = Σ_b (B/N_b)·Σ log2(1+γ) is anti-correlated with realized throughput" and both probe envs were in a "+75 dB link-budget hole" (softshare NOTE L23-28, L63-67).
- premises: J_w with handover weight 0.3 prices churn heavily; env SNR-healthy. For an EE objective with different handover pricing, the ranking could differ `[I]`.

### A-45. Behaviour-clone representability diagnostic (Step-0) — input-symmetry refutation
- mechanism: CE-clone a joint coordinate-ascent oracle through a per-user net; check for ε-identical states with different labels.
- intervention point: other (diagnostic)
- defined in: `step0-behavior-clone-VERDICT-2026-06-22.md`
- run status: ran (local, 5 seeds, 60 epochs; capacity probe 400 epochs).
- recorded outcome: "INTERMEDIATE"; "Input symmetry is cleanly refuted ... zero have ε-identical encoded states yet different oracle labels" (L43-48); top-1 0.176 / 0.145, but "the clone was under-converged" (capacity probe climbs to 0.446, L51-59).
- premises: per-user state separability (true; the collapse is not an input-tie).

### A-46. Amortized "learn-to-optimize" framing + zero-learning control gate (distillation-EE reopen)
- mechanism: claim deployability (latency/runtime weights) of a slow optimal planner via a learned student; gate: does any fast zero-learning heuristic already reach the ceiling?
- intervention point: objective (framing) / other (gate)
- defined in: `THESIS-FRAMING-amortized-MORL-2026-06-22.md`; verdict `distillation-ee-gates-VERDICT-G6-2026-07-05.md`
- run status: gates ran (eval-only) on corrected std-EE (÷G_T removed), protocol-matched to route-B (48 ep).
- run conditions: family_b EUV `389eaaef`, G1 `10600c20`; r1 = corrected `family_b_eta_r1` "(std R/p, per-user mean = the binding r1 reward)" — **mean-of-ratios per-user EE** (L23-24); route-B A1/A2 = lr-0.01 era arms `[I]`.
- recorded outcome: "Gate ③ = FAIL — 'zero-learning eats the gap' ... AF+balance 5.128e8, which closes 81.2% of the AF→ceiling gap and statistically TIES the ceiling" (L52-56); "AF+balance (5.128e8, zero-learning) dominates the TRAINED A1/A2 (4.379/4.254e8) by ~17% on corrected EE" (L62-65); caveat "the M2 aggregate `system_energy_efficiency` INVERTS, ranking random/round_robin above the planner" (L48-49) — i.e. pooled vs per-user EE disagree.
- recorded cause: "a fast, deployable, ZERO-LEARNING method already reaches the amortization target. There is nothing un-deployable to distill" (L56-58).
- premises: a slow teacher with a real quality gap over fast heuristics; per-user-mean EE is the metric (pooled EE ranks differently — relevant to the new project) `[I]`.

### A-47. Weighted-MCCRL EE-win search via decode-weight sweep (hybrid auction) — and the decode "opened-set" F5 artifact
- mechanism: sweep decode-time objective weights on trained MCCRL to find an EE win over AF at matched coverage.
- intervention point: decode/deployment (weights) + objective
- defined in: `EE-WIN-FINAL-VERDICT-2026-07-06.md`
- run status: ran (eval sweeps on C1FIXED retrains w503020 / ee90 + bug-trained std_A2); planned 18-run retrain killed.
- run conditions: family_b; C1-scale-bug fixed ("C1FIXED, c1→2.532e11 put EE back into the training objective for the first time", L15-16); EE = `family_b_eta_r1` averaged over ALL 100 users with unserved→0 (L27-29); hybrid/C1FIXED arms were lr 0.01 (lr file §2 L36, L45-46).
- recorded outcome: "There is NO robust energy-efficiency (EE) win over the non-learning fixed-rule auction (AF) at matched coverage on family_b. The apparent win was largely a decode-implementation artifact" (L9-11); strict-k_c corrected decode shrinks +11.6 to "+1.6 at nominal — within seed noise" (L25-26). Also: "only coverage-starvation beats AF (DQN_scalar 530, min_cov 0.165)" (L59-60).
- recorded cause: F5 decode bug — "builds the 'opened k_c cells' set from the AF assignments (which include fallback-argmax cells), so k_c=1 can effectively open >1 coordinated cell" (L22-24).
- premises: EE per-user mean with unserved→0 (couples EE and coverage).

### A-48. Partial-coordination hybrid decode (k_coord < k_cap) + lower EE discount (γ 0.90) to expose catfish (A2 > A1)
- mechanism: open only k_coord cells per satellite via the auction, leave k_cap−k_coord to per-user argmax, so the value-learning recipe ("catfish" = asym-γ + value-stratified replay) can matter; "catfish flip" at k_c=1.
- intervention point: decode/deployment (+ other: discount)
- defined in: `hybrid_ee_sdd_proposal.md` (top-level); decision memo `OPERATING-POINT-AND-CATFISH-NARRATIVE-DECISION-2026-07-06.md`
- run status: ran (hybrid k0/k1/k2/k3 retrains, 3 seeds; sweeps over p_base, num_users).
- run conditions: family_b, hybrid decode, γ 0.90, C1FIXED, **lr 0.01** (the lr file's collapsed cell is exactly `A1_hybrid_k1_w503020_C1FIXED` at hybrid/0.01/3000); A2 here = single agent, "ONE agent, ONE rollout, ONE replay, `acrm_enabled:false`, no second agent, no conduit ⟹ 0 of CDRL's 3 strategies as mechanisms" (chronicle L1951 — catfish-v2 cluster).
- recorded outcome (06-07 memo): "k_c=1 ... A2 > A1 flip: Jw +17% (5.745e-4 vs 4.913e-4), EE +7.5% (4.44e8 vs 4.13e8), 3/3 seed-consistent ... NOT final (needs 5-seed + cross-model G6)"; "k_c=2 ... A2 < A1 (no flip)"; full coordination A2≈A1 (memo §1). LATEST revisions (outside cluster A, chronicle): "the live k_c=1 line's coverage is substantially an F5 artifact ... A1_hybrid_k1 scored leaky → min_cov 0.929; scored corrected → 0.597" (chronicle L1902); F5 leak "inflates min_cov by +0.30–0.33 and EE by +14–20 for the LIVE thesis A1/A2_hybrid_k1 arms, which were TRAINED through it ⟹ NOT re-scorable" (L1926); an n=5 corrected-decode injection test: "ΔEE(A2−A1)=[+41.8,−44.8,+30.3,−47.1,+23.4] → NOT seed-separated ... NOT-DEMONSTRATED / underpowered" (L1976). Under pure argmax at lr 0.01 these arms are collapsed (lr file table).
- recorded cause (memo): "partial coordination → subsumption incomplete → catfish shows"; later: decode leak + lr attractor.
- premises: a strong decode subsumes any value-learning improvement; catfish's benefit is conditional on a weak decode; collapse exists (lr-0.01).

---

## Supplement — July 2026 concepts found in the SAME top-level directory (outside the June priority list; skimmed, not exhaustive; the catfish-v2/ subdir is another cluster)

- **COND-JULY** (07-03 → 07-20): env family_b EUV `family_b_step.py 389eaaef`, G1 `modqn.py 10600c20`; ÷G_T EE-formula
  bug fixed 07-03/04 ("÷G_T distortion ~9200×"); C1-scale bug fixed (C1FIXED); EE unit Mbits/J = `family_b_eta_r1/1e6`
  = per-user mean R_u/p_u over ALL users with unserved→0 (EE#1). Pooled EE (EE#2 "`system_energy_efficiency` =
  ΣR/Σ(active power) = textbook EE") is recorded as a DIFFERENT ranking: "EE#2 ... Coverage-sacrifice can RAISE it"
  (`HANDOFF-coverage-free-ee2-catfish-2026-07-05.md` "3 EE definitions"); "random 5.85e8 ≈ DQN_scalar 5.96e8" on EE#2.
  k_cap=3 active cells / window satellite, ≤12 lit beams; regression "EE = −674·cap_bump + 601, r = −0.972, R² = 0.945"
  over 25 arms (`CATFISH-VS-DQFD-DESIGN-2026-07-15.md` §9.1). **lr: waves A/C/D co-primary lr ∈ {0.01, 1e-3}, 3000 ep;
  wave E lr 1e-3 (+3e-3 insurance), 9000 ep.**

### A-49. DQfD-style external-expert injection into the main agent (F-mean greedy-auction demo pool, ρ=0.30, pretrain 8000, margin on/off) — "full-DQfD" waves
- mechanism: permanent demo replay from a deployable zero-learning expert + large-margin loss + TD, mixed at ratio ρ.
- intervention point: experience + penalty/loss (margin)
- defined in: `FULLDQFD-WAVE-PREREG-2026-07-15.md` (not read in full); result `FULLDQFD-GROUPA-RESULT-2026-07-14.md`; `WAVE-E-PREREG-2026-07-14.md`
- run status: **ran** (group A: 6 seeds × 2 lrs × ON/OFF, 3000 ep; wave E: 9000 ep, lr 1e-3 — results in catfish-v2 cluster).
- run conditions: COND-JULY; trained from scratch with demos (not distilled from a frozen main); pure per-user argmax scorer; z-score ("concat-448") substrate.
- recorded outcome: "R-3 (ON − OFF) is SEPARATED POSITIVE at one co-primary learning rate and SEPARATED NEGATIVE at the other": lr 0.01 **+129.97** EE [+70.05, +189.88]; lr 1e-3 **−57.11** [−112.15, −2.06] (GROUPA §0–§1). "At lr = 0.01, the no-injection arm collapses by the end of training — WITH the z-score on" (argmax_distinct 1.01) (§2). "DQfD injection DOES prevent that collapse ... But 'de-collapses' ≠ 'better': a free lr change de-collapses BETTER (479.50 vs 366.70)" (§4.2); at lr 1e-3 "injection raises argmax_distinct (12.55 vs 11.04) while LOWERING min_cov (0.5587 vs 0.7181) and EE. It spreads them more and serves them worse" (§4.2). LATEST: R-3 "is not a converged effect ... withdrawn" — episode-budget confound (OFF_lr001 still climbing at 3000) (§3); wave E launched to fix it.
- recorded cause: "lr = 0.01 is not 'a learning-rate choice' — it is a DIVERGING RUN" (§3); "injection's effect is a spread-the-users push — exactly what a collapsing arm needs, and an over-correction once the arm is already spread" (§4.2, tagged hypothesis).
- premises: base learner collapses (true only at lr 0.01); a demonstrator better than the learner (F-mean 636 EE vs learned ~480).
- ★ transfer-relevant fact: demo injection's benefit sign flipped with the base learner's health.

### A-50. Phase-1 solver-seeded catfish replay (the thesis-faithful CDRL Phase-1: external solver's exemplary cases pre-loaded into the catfish buffer) + DQfD margin as the "discrete-transfer fix"
- mechanism: (a) seed catfish replay with a solver pool (F-mean 636 EE or de-clairvoyant local-search ORACLE 681.8 EE); (b) add a large-margin supervised loss because in a 28-way discrete action space "the OTHER 27 actions NEVER RECEIVE A GRADIENT".
- intervention point: experience (seeding) + penalty/loss (margin)
- defined in: `CATFISH-VS-DQFD-DESIGN-2026-07-15.md` §0–§7 (5-arm design A1/A2/B1/B2/D1)
- run status: design + offline measurements; pools built (`dqfd_pool_F-mean.npz`, `dqfd_pool_ORACLE.npz`, 47,995 transitions each, eval-disjoint). Scored 5-arm wave: not found in cluster A `[I: may be in catfish-v2]`.
- recorded outcome (offline, demo-only): "no supervision term: argmax_distinct 1.0 — all 100 users pick the SAME beam, EE 108.9; with the margin: 18.5, EE 344.8; no supervision term, ONLINE (ρ=0.30): 4.5–4.8, EE 236.1" (§3). Earlier faithful-catfish negatives were judged "passed on a CRIPPLED implementation ... The catfish buffer is NEVER seeded" (§0). Adversarial lane: "94.5 % OF EVERY NUMBER IN THIS LADDER IS ONE VARIABLE: HOW MANY USERS THE k_cap RANK-CUT DROPPED" (§9.1); "what the margin actually does is move distinct from 7.8 (UNDER budget) to 12.2 (ON budget)".
- recorded cause: continuous-action actor-critic (original CDRL) never faces the unlabelled-action problem; value-based discrete argmax does.
- premises: expert ≫ learner (681.8 vs best learned ~428–480); value-based discrete action head; k_cap consensus game.

### A-51. Behaviour-cloning lookup / cost-sensitive (objective-based) imitation instead of regression; ε-corruption analysis
- mechanism: per-user kNN lookup of expert actions; recognise that imitation accuracy is not monotone in EE because optima are non-unique → use objective-based amortization.
- intervention point: experience / penalty/loss
- defined in: `CATFISH-VS-DQFD-DESIGN-2026-07-15.md` §9.2–§9.3, §10
- run status: ran (offline, eval).
- recorded outcome: "a pure per-user LOOKUP — no decoder, no coordinator — rolled closed-loop, reproduces the centralised joint optimum EXACTLY: 636.05, min_cov 1.000" (leak pool) → "Gap A is 100 % GENERALISATION, 0 % EXPRESSIVITY"; accuracy↔EE inversion (kNN raw top-1 0.8368 → EE 421.4; kNN z top-1 0.7123 → EE 475.3); "STRUCTURED errors cost 2.7× more than random ones" (§10).
- premises: a joint-optimal teacher; per-user function class sufficient (grounded here).

### A-52. Cross-user input standardization (z-score of per-user features over the live 100-user population, "concat" [raw ‖ z]) and congestion-feature rescaling (χ occupancy ÷ k_cap)
- mechanism: standardize each feature across users per step (a broadcast population statistic) so users' observations differ; or rescale the demand/occupancy channel that sits at ~1/559 of the SNR block's magnitude.
- intervention point: representation
- defined in: `CATFISH-VS-DQFD-DESIGN-2026-07-15.md` §8 (open question), `CHI-ABLATION-RESULT-2026-07-15.md`, `WAVE-E-AMENDMENT-width-and-insurance-2026-07-14.md`
- run status: z-score ran in waves A/C/D/E; χ-rescaling retrain never run (proposed).
- recorded outcome: "The z-score is NOT sufficient to prevent collapse — the learning rate is" (GROUPA §4.1); standardization "drops the augmented-encode per-user correlation 0.95 → 0.044" (`test2-sinr-candidate-design-2026-07-12.md` §1); χ ablation: zeroing the demand feature moves argmax_distinct by −0.043 [−0.178, +0.120] → "the collapse is a REPRESENTATION / SCALE problem ... demand feature is normalised ÷ num_users ⟹ ~1/559 of the SNR block's magnitude" (CHI L42-50). Width confound: concat(448) vs raw(224) differ in width too → added `waveE_OFF_width` (amendment). Open: "the z-score is a CROSS-USER operation at inference ... may be a SMUGGLED COORDINATION GAIN" (§8).
- premises: per-user argmax over shared Q; unscaled heterogeneous input blocks.

### A-53. July ideation menu for decentralized per-user symmetry breaking: CCF active coded probing (causal fingerprint in the catfish 30% window), posted-price deferral gate, ISJ per-user objective-weight jitter, disagreement-seeded catfish (inject demos where the 3 heads' argmaxes disagree), MSDE temporal desync (user decides only at t mod K = hash(u) mod K)
- mechanism: see name; frame: "Identical observation + shared DETERMINISTIC policy ⟹ necessarily identical action".
- intervention point: exploration (CCF) / decode (posted-price, ISJ, MSDE) / experience (disagreement-seeded)
- defined in: `CONTRIBUTION-IDEATION-2026-07-15.md`
- run status: never built; one premise screen (single seed, 12 ep).
- recorded outcome: "the TRAINED + decoded policy is NOT collapsed — active beams 11.6/12, served 0.89"; head disagreement real ("~43 distinct (a1,a2,a3) triples / 100 users") but "routing adds only 1.02–1.20× ⟹ no headroom on the de-collapse axis; ... served collapses 0.89 → 0.47" → "de-collapse by per-user spreading has ≈0 headroom (saturated) AND costs served-fraction (k_cap)".
- premises: collapse exists at the deployed policy (false once decoded/trained); spreading helps (false under k_cap).

### A-54. Interference-aware SINR for candidate (non-active) beams in the observation
- mechanism: fill candidate-beam channel features with 1-step-stale interference-aware SINR (reusing `color_sums`) instead of noise-only prospective SNR.
- intervention point: representation
- defined in: `test2-sinr-candidate-design-2026-07-12.md`
- run status: design only ("Not built, not run"); adjudicated KEEP 07-13.
- recorded rationale: "AF→oracle gap (246.06) decomposes into power/load 29 % · INTERFERENCE 47 % · search 24 %, and the 47 % is about PRICING interference" (banner).
- premises: interference materially shapes EE and is location-dependent.

### A-55. Coverage-free EE#2 catfish (train on pooled textbook EE, coverage sacrificeable) — Path A
- mechanism: switch the r1 objective to system EE = ΣR/ΣP so catfish's valuation effect shows at a competitive operating point.
- intervention point: objective/reward
- defined in: `coverage-free-ee2-catfish-PATH-A-SDD-PREREG-2026-07-05.md`; `HANDOFF-coverage-free-ee2-catfish-2026-07-05.md`
- run status: design + prereg; outcome not found in cluster A `[I]`.
- recorded state: "Catfish raises EE ONLY where the decode is BAD (argmax-collapse: B2>B1). But that is exactly where absolute EE is LOW" (catch-22); "EE#2 is myopic-trivial (random 5.85e8 ≈ DQN_scalar 5.96e8, within 2%)"; A2−A1 EE#2 −7.4e6 [−2.4e7,+8.9e6]; B2−B1 EE#2 +6.08e7 CI-sep (HANDOFF board).
- premises: ★ pooled EE on family_b is nearly policy-insensitive (random ≈ best) — directly relevant to a pooled-EE project `[I]`.

### A-56. Physical consumed-power angle-aware EE (p_req varies with off-axis angle; angle-clustering coordinated decode)
- mechanism: make power depend on required power at angle so clustering users by angle could create coordination headroom.
- intervention point: objective/reward (physics) + decode
- defined in: `physical-ee-KILL-GATE-0-VERDICT-2026-07-03.md`
- run status: ran (env-replay clustering probe, 8 cells).
- recorded outcome: "VERDICT → KILL (0/8 reopen) ... the coupling taxes coordination, it does not manufacture new headroom" (gate ρ 0.71–0.75).
- premises: max-over-served power coupling creates exploitable clustering value (refuted on family_b geometry).

### A-57. Demand-dynamic env (queues/TTL, heterogeneous demand; "Phase-2"), demand-augmented state, and temporal foresight (EVPI)
- mechanism: add time-varying demand + queues so learned temporal prediction has headroom.
- intervention point: other (environment) + representation (demand aug)
- defined in: `phase2-demand-env-build-sdd-2026-06-22.md` (not read); results `phase2-galpha-RESULT-VERDICT-2026-06-22.md`, `phase2-served-demand-ceiling-VERDICT-2026-06-22.md`; `hard-ee-regime-C-EVPI-result-verdict.md`
- run status: ran (G-α 3 seeds × 3000 ep; ceiling probes; EVPI probe).
- recorded outcome: G-α "NO-WIN ... HOLLOW vs the zero-learning floor: A−D = +0.0209 ≪ delta_star 0.2103 ... r2 per-objective floor VIOLATED"; ceiling "CAPACITY-BOUND ... A's qos 0.406 = 86% of that ceiling"; EVPI "61× BELOW the frozen ε-floor ... even PERFECT demand-foresight is worth ~0.024%".
- premises: temporal structure with exploitable foresight (absent: "orbits + i.i.d. fading → forecast-aware static ties any learner on the temporal axis").

### A-58. Metric/estimator lessons that condition every catfish outcome above (not mechanisms, but recorded as design rules)
- cap_bump as a lower-noise estimator of EE ("d/sd = 1.23 vs 0.29 on the C4−C2 contrast", CATFISH-VS-DQFD §9.1).
- within-arm checkpoint-to-checkpoint EE spread "median 71.6 EE · max 139.3" at lr 0.01 > effect sizes (+29.7) (§9.4); "σ_seed = 54.9. At n=3 the MDE is 166.7" (§8).
- per-user mean EE with unserved→0 couples EE with coverage ("the metric PENALIZES coverage loss", EE-WIN-FINAL L27-29) whereas pooled EE rewards sacrificing coverage (HANDOFF EE#2).
- "materiality": collapse was reward-SUBoptimal under the trainer's own calibrated reward (round-robin beat trained ckpt 26–72×; `materiality-verdict.md` L8-17) → a learnability failure, later traced to lr (`COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md`).

### A-59. F1/F2/F3 hazard state-augmentation (F1 occupancy, F2 exogenous contention, F3 cap/saturation hazard) — "B1-hazard"
- mechanism: append per-user criticality / contention / cap-hazard features to the state to break Q_i≡Q_j aliasing.
- intervention point: representation
- defined in: SDD-01 §5.2 (C2); summarized `catfish-last-design-candidates-2026-06-24.md:63-70`; `catfish-development-direction-2026-06-24.md:42`
- run status: an earlier B1-hazard variant ran (pre-June-19, outside priority list); SDD-01's C2 never built.
- recorded outcome: "O-NEG on the cap_bump battlefield — they did not separate planner-bumped from served users" (last-design L68-70); "per-user DEGENERATE (std 0.009/0.005, 99.6% zero)" (`symmetry-breaker-design-2026-06-19.md` §1 L38-41); "B1-hazard" counted as the 1st "static/trivial eats it" (`track-b-strategic-rec-2026-06-19.md:91`).
- premises: the hazard signal varies per user (false on family_b).

### A-60. Single-head scalarized DQN on the exact weighted reward (DQN_scalar field baseline) — the comparator that "de-collapses" and tops J_w
- mechanism: one 28-way Q head trained on `K_SCALAR·⟨w, r/scales⟩`, per-user argmax.
- intervention point: objective (scalarization) + representation (single head)
- defined in: `src/modqn_paper_reproduction/field_baselines/dqn_baselines.py` (verified constants: `LR = 1e-3`, `GAMMA = 0.99`, `HIDDEN = (256,256,128)`, `BATCH_SIZE = 256`); used in `route-b-factorial-VERDICT-G6-2026-06-27.md` STEP 6
- run status: ran (5 seeds).
- recorded outcome: "DQN_scalar ... scores 6.10e-4 on the matched harness — above A1 (4.97e-4), A2 (4.82e-4), and even AF (4.44e-4) ... active 11.0"; min_cov 0.110; later 5-seed "mean ≈6.41e-4, all > A1 4.97e-4"; on corrected EE "DQN_scalar 530, min_cov 0.165" (EE-WIN-FINAL L59-60).
- recorded cause: "per-user-argmax collapse is RULED OUT as universal by counterexample ... 'the MODQN shared-3-head architecture is THE cause' is supported but NOT cleanly isolated (DQN_scalar also differs in reward + training protocol)" (VERDICT-G6 L154-158).
- inferred cause [I]: ★ DQN_scalar used **lr 1e-3** while the collapsed MODQN arms (B0/B1/B2/A1/A2, stage-1) used **lr 0.01** — the "architecture" counterexample was lr-confounded; consistent with the July lr isolation. It maximizes the scalar by starving a tail user (Jain 0.59/0.74).
- premises: the scored metric is J_w (or per-user EE); coverage not valued.

### A-61. ACRM competitive reward `r^C = r + η(r^CF − r^M)` (linear, tanh/Q^mix OFF) in family_b
- mechanism: catfish reward includes its advantage over the main's counterfactual reward.
- intervention point: reward
- defined in: `catfish-development-direction-2026-06-24.md:16`; `route-b-factorial-design-note-v3-2026-06-26.md` §6.4
- run status: **never enabled in any scored cluster-A run** ("ACRM off / PopArt off ... acrm_enabled=false ×12", route-B VERDICT L38); P1 toy test excluded it ("counterfactual_eta is welded to satellite EE-geometry ... no natural single-agent analog", p1 prereg §0 L38-43). Later: "route_b ACRM is a NotImplementedError stub" (chronicle L2043, catfish-v2 era).
- recorded prior: thesis ablation SMALLEST; "non-potential → Ng-1999-UNSOUND, can shift the optimum"; CA-CPBR (A-4) was designed as its potential-based replacement.
- premises: a second agent whose counterfactual reward is computable per state.

### A-62. Literature-prior refutations of catfish components (recorded as priors, not experiments)
- M2 asymmetric discount ≈ "Curse of Diversity (ICLR 2024)"; M3 30% heterogeneous sharing ≈ "SUPER (NeurIPS 2023) shows M3's exact 30%-uncorrected-heterogeneous regime is WORSE than no-sharing"; "M1 reward-keying is itself a documented cause of premature convergence" (`b-pivot-decision-map-2026-06-20.md` Agent 4, L47-51). "catfish is AGENT-LEVEL anti-stagnation; LEO failure is USER-LEVEL coordination → axis mismatch" (Agent 1, L36-37). Later family_b finding: "γ_cf wired-but-inert on family_b" (chronicle L2030, catfish-v2).
- premises for revival: an env where discount horizon matters (non-myopic) and where the catfish can collect experience the main cannot.

---

## Cross-cutting condition notes for the synthesiser (records + my inferences, marked)

1. **lr**: every June "collapse" measurement on MODQN-family learners (B0 2026-06-12/14 retrain, stage-1, route-B B0/B1/B2/A1/A2,
   hybrid k_c arms, P1-faithful era) is at `learning_rate = 0.01` (trainer default verified; stage-1 + route-B verified in
   records); the July isolation says "Flipping ONLY the learning rate (0.01 → 0.001) ... doubles argmax EE and lifts worst-user
   coverage from 0.312 to 0.698" and "The faithful paper form ... does not collapse at lr = 1e-3". The distillation line
   (P4, 6-arm, route-C) used Adam 1e-3 but distilled from a teacher and never trained the main by TD. DQN_scalar (the
   "de-collapsing" comparator) used lr 1e-3 `[I: this lr asymmetry is not called out in the route-B verdict]`.
2. **Wiring**: 6-arm (A-4/5/6/8/9) and route-C (A-11) = warm-start from a converged distilled net (P), 4 rounds, supervised
   CE imitation into the main (catfish only selects/filters teacher data) → catfish had no exploration/stagnation to act on
   (records' own premise A-1). Route-B (A-14..A-16) = from scratch, single agent (no second catfish agent, no conduit,
   no ACRM) — "catfish" = asym-γ + value-stratified replay recipe. July DQfD waves (A-49) = from scratch with demos.
3. **Metric**: June = calibrated weighted J_w [0.5,0.3,0.2] (r1 throughput in June-19 era; r1 per-user angle-aware EE in
   route-B/July, ÷G_T-inflated before 07-03/04); coverage = min over users of per-user served-step fraction; R_starved.
   **Pooled EE (ΣR/ΣP) was only a diagnostic ("EE#2"), on which random ≈ DQN_scalar within 2% and the planner ranks
   below random/round_robin** (A-46, A-55). No catfish concept in cluster A was ever scored on pooled EE.
4. **Physics** (family_b): hard k_cap = 3 cells per window satellite (≤12 lit beams), cap-bumped users get zero rate;
   shared-beam rate `B/load·log2(1+SINR)`; off-axis Bessel gain present in angle-aware EE r1; handover energy appears only
   as an r2 reward term (−0.5/−1.0), not in power; candidate beams observed as noise-only SNR (A-54). "94.5% of EE variance
   = cap_bump" (A-50). Removing the hard cap made spreading HARMFUL on the weighted scalar (A-38) — the value of every
   spreading/anti-collapse concept here is conditional on the hard cap.
5. **Trainer defects**: ★ the frozen baseline MODQN itself uses per-head own-argmax bootstrap — "Sealed per-objective
   TD — `modqn.py:691` (each head j: `r_j + γ·max_{a'} Q_target,j(s',a')`, **independent per head**). G1 forbids editing it"
   (SDD-01 §4 L150-151; I verified in code: `algorithms/modqn.py` loop `for obj_idx in range(3)` →
   `q_next_max = q_next_all.max(dim=1).values`, `target = r + discount_factor * q_next_max * (1.0 - dn)`) → every June MODQN-trained arm that inherits the base update (B0 retrain, stage-1 plain/de-sat,
   C1 plain comparator) carries this defect `[I: sibling trainers that override the update — route-B, SequentialDecodeMODQN
   — replace it]`. Route-B per-head TD bootstraps on the (scalarized) decode action `a′` from the cell's own decode
   (not each head's own argmax) per design v3 §6.1; the stage-1 "coordinated_multi_catfish" trainer "still bootstraps with
   per-head max_{a'}" (SDD-01 §5.1 L188-191 — codex r3 M-3: do NOT inherit) → **per-head own-argmax bootstrap existed in
   `coordinated_multi_catfish/trainer.py:425-434,562-564`** (quoted). Outage handling: r1 = 0 for cap-bumped/unserved users;
   records silent on r2/r3 free ride for unserved users in these files (the r3 "pays for collapse" issue is raised in
   July: `WAVE-E-AMENDMENT` "BLOCKER-3 (r3 pays for collapse)"; `R3-ENV-DEPARTURE-G6-VERDICT-2026-07-15.md` — r3 env
   scope differs from paper Eq 11, sign not identified). Uncalibrated logged scalar: SDD-01 §4 notes baseline eval/ckpt
   selection used the RAW `scalarize_objectives`, overridden to calibrated J_w in later harnesses; the June-22 C1 kill-test
   had "ckpt-selection asymmetry (plain=raw scalar, seq=J_w)" (C1 verdict L20-21). `[I: no record in cluster A of the
   exact "logged scalar uncalibrated" defect named by the harvest brief beyond these.]`
