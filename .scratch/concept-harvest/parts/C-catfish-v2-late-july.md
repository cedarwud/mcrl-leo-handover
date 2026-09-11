# Concept harvest — Cluster C: catfish-v2 mid/late July (2026-07-13 .. 07-21) + top-level July files

Extractor: read-only worker, 2026-09-11. Source root (abbrev `FBCD/`) =
`/home/u24/papers/modqn-paper-reproduction/analysis/family-b-collapse-diagnosis/`; `CV2/` = `FBCD/catfish-v2/`.
Convention: "SAYS" = quoted/paraphrased from the record; **[I]** = my inference. Line numbers are from the files as read on 2026-09-11.

## Common run conditions for this whole cluster (apply unless an entry says otherwise)

- **Env**: `family_b` step env (`env/family_b_step.py`), U=100 users, `l_w`=4 window satellites, `k_cap`=3 beams **per satellite** (total active beams ≤ 12; HANDOFF-2026-07-20-EP2K-COMPLETE.md:98-99), A = l_w×7 = 28 actions/user. Nominal operating point U=100, p_base=0.25.
- **Power model actually on the training AND eval path in July** (CV2/V2-COMPLETENESS-CHECK-2026-07-19.md:8-39, verdict PARTIAL): `eta_u = R_u / p_alloc`, `p_alloc = slot_power_w / beam_load`; per-beam power `P_b = min(0.25 + 0.35·load^0.5, 10 W)` for active beams, 0 W inactive, then a proportional per-satellite aggregate cap `SAT_AGG_CAP_W ≈ 19.95 W`. Angle-aware antenna gain G_T(θ) (Bessel) present **only in the numerator** (via SINR → rate). **Absent**: SINR-target-inverted P_req, P_DL=z·min(P_max,P_req), PA efficiency η, circuit/baseband fixed power (p0=0), **train/switch (handover) overhead energy = ZERO on every path in the repo**. The ÷G_T bug in r1 was fixed 2026-07-04 (commit 211a71a3) — runs before that date carried a ~1e4 EE inflation (see LR section, it was ruled out as the collapse cause).
- **Metric `argmax_EE`** (CV2/score_argmax_endpoint.py:86-128): frozen 48-episode nominal harness (seed 20260626), pure per-user argmax of `Q_w = Σ_k w_k Q_k`, w=(0.5,0.3,0.2), no decoder/coordinator; `argmax_EE = mean over episodes of mean over (slots × users) of per-user eta_u`, /1e6 → "Mbits/J". **This is a MEAN OF PER-USER RATIOS (unserved user contributes eta=0), NOT pooled EE (Σbits/ΣJ).** Also emitted: J_w, min_cov (worst-user served fraction), served, active_beams, argmax_distinct, cap_bump. Self-test: myopic per-user rule must reproduce EE=299.5703 bit-exactly.
- **r2/r3**: r2 = handover penalty; r3 = "legacy r3" = max−min load over active beams (made permanent 2026-07-19; CV2/V2-COMPLETENESS-CHECK:73-77). corrected-r3 was designed but never adopted.
- **Wiring**: every July run in this cluster trains the MAIN agent **from scratch** (MODQN shared-Q with 3 objective heads). Catfish agents are *sibling* learners trained concurrently alongside main and inject experience into main (M3 conduit / M1 cross-route); there is **no distillation from a frozen pre-trained main** anywhere in this cluster. DQfD/BC arms pretrain main from an *external teacher's* demonstrations (not a frozen main). [I from PACK-MINI-SDD §1-3 and the DQfD preregs; confirm per entry.]
- **Trainer defects named in the harvest brief**: I found **no mention** in this cluster of (a) per-head bootstrap from each head's own argmax, (b) outage free ride r2=r3=0 when unserved, or (c) an uncalibrated logged scalar as such. Related facts that ARE recorded: unserved users give eta=0 in r1 (score_argmax_endpoint + family_b_eta_r1 docstring "Zero-power cap-bumped slots ... eta is 0"); "the project has been scoring EE alone and calling three waves NULL for it" (score_argmax_endpoint.py:23) — i.e. the scalar being logged/scored was questioned. Anything more is noted per entry.

---

## SPECIAL SECTION — `FBCD/COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md` (144 lines, read fully)

**What it says (SAYS):**
- Verdict (l.3-6): "the collapse that this project has treated as a property of MODQN / shared-Q / per-user-argmax is identified as an artifact of `lr = 0.01`. Flipping ONLY the learning rate (0.01 → 0.001), with decode, episodes, state form, env and wave held fixed, doubles argmax EE and lifts worst-user coverage from 0.312 to 0.698."
- l.8-11: "This is NOT a contribution and must never be written as one ... a *premise* is withdrawn."
- Method (l.13-26): three controller explanations were refuted first — decoder train/eval mismatch; the E1 `÷G_T` reward bug (collapse persisted after the 2026-07-03 fix, in C1FIXED arms); augmented-state occupancy features. A leaf-diff of `run_metadata` reduced candidates to {decode, episodes, learning_rate}; a census of 323 `run_metadata.json` showed the old era is ONE cell (`hybrid / 0.01 / 3000`, 82 runs) and abl9k is ONE cell (`argmax / 0.001 / 9000`) — perfectly confounded — but separating cells existed in the `fulldqfd-*` / `waveE-*` waves.
- Measurement (l.28-50), same frozen argmax scorer, n=3 seeds/cell, EE in Mbits/J (mean-of-per-user-ratios, see header):

| decode | lr | ep | state | EE | min_cov | served | status |
|---|---|---|---|---|---|---|---|
| hybrid | 0.01 | 3000 | aug-224 | 145.47 | 0.167 | 0.297 | COLLAPSED (`A1_hybrid_k1_w503020_C1FIXED`, route_b_factorial) |
| argmax | 0.01 | 3000 | raw-224 | 150.13 | 0.167 | 0.297 | COLLAPSED (`fulldqfd_OFF_raw`, groupD) — identical 150.13 on all 3 seeds |
| argmax | 0.01 | 3000 | concat-448 | 235.53 | 0.312 | — | still far below healthy (`fulldqfd_OFF`) |
| argmax | **0.001** | 3000 | concat-448 | **472.22** | **0.698** | — | HEALTHY — only lr flipped (`fulldqfd_OFF_lr001`) |
| argmax | 0.001 | 9000 | raw-224 | 493.18 | 0.687 | 0.829 | healthy (`waveE_OFF_raw`) |
| argmax | 0.001 | 9000 | raw-224 | 428.60 | 0.586 | 0.753 | healthy (abl9k L1) |

- Isolation (l.52-57): `fulldqfd_OFF` vs `fulldqfd_OFF_lr001` leaf-diff has "exactly one substantive difference: `trainer_config.learning_rate = 0.01` vs `0.001`".
- Ruled out (l.59-64): decode (hybrid→argmax at 0.01 changes nothing, identical min_cov/served); episodes (0.001 healthy already at 3000).
- l.66-68: "z-score *helps* but does not prevent the collapse; lr is the controlling variable."
- Signature (l.72-75): at lr=0.01 "a **seed-independent degenerate attractor**: min_cov = 0.167 and served = 0.297 are bit-identical across seeds *and* across the decode flip ... structural homogenization, not noisy divergence."
- **WITHDRAWN** (l.79-84): "MODQN / shared-Q + per-user-argmax collapses on this environment" as a general statement — "The faithful paper form (eq 12–13 ...) does **not** collapse at `lr = 1e-3`"; and any thesis line "our framework fixes / de-collapses MODQN".
- **REQUIRES RE-CHECK — "suspect", not declared void** (l.86-91): (1) the original faithful family_b `B0` retrain collapse (M1 sub-random, 3/3 seeds); (2) the route-B factorial conclusion "coordinated allocation = the de-collapse engine"; (3) the CURRENT-STATE headline "de-collapse 3→12". "All three were measured in the `lr = 0.01` era ... none has been re-measured yet."
- **SURVIVES** (l.93-97), healthy lr=1e-3 substrate, 6 seeds: L2−L1 = +56.54 (representation/concat-z increment); L6−L2 = +124.31 (full MCCRL over normalized MODQN); min_cov 0.586 → 0.732 → 0.957 across L1 → L2 → L6.
- Caveats (l.104-111): evaluations of existing checkpoints, not a matched retrain; scope family_b, k_cap=3, nominal point, pure argmax; "says nothing about *why* lr = 0.01 produces the degenerate attractor; the mechanism is untested."

**Which runs used lr=0.01 (from this and other files in the cluster):**
- Entire "old era": every `route_b_factorial` arm (`hybrid / 0.01 / 3000`, 82 runs) incl. A1/A2, C1FIXED, coordinator/auction/hybrid decode arms.
- `fulldqfd-wave-2026-07-14` GROUP A/C/D arms (fulldqfd_OFF, fulldqfd_OFF_raw, DQfD ON arms) at 3000 ep — **except** `fulldqfd_OFF_lr001` (0.001). GROUPA "@lr=.01/3000: OFF 236.74 / DQfD +129.97 (anchor-effect witness)" (CV2/ABLATION-SPEC-9000EP:86-87).
- `SCFZA_p01 ×3 (lr=.01/3000)` local runs (lost, never completed; ABLATION-SPEC:80-83).
- (Per entries below: the July-13/14/15 catfish-v2 ablations, oracle/argmax studies, CHI ablation, wave-E? — see each entry; waveE_OFF_raw itself is lr=0.001/9000.)

**Which runs used lr=1e-3:** abl9k (9000 ep, 10 arms × 6 seeds), ep2000 wave (7 arms × 6 seeds), waveE-2026-07-14 OFF_raw (9000 ep), fulldqfd_OFF_lr001 (3000 ep), the 12000-ep OFF / OFFM4 / OFFSYMG / SCFZA diagnostic line (523.78 / 613.05 / 497.68 / 477.31; "[0,.9,.9]-regime", ABLATION-SPEC:22, 85).

**Verdicts it calls contaminated/suspect:** B0 faithful-retrain collapse; "coordinated allocation = de-collapse engine" (route-B factorial); "de-collapse 3→12". By implication **[I]**: every catfish/DQfD/coordinator result in this cluster whose premise is "MODQN collapses / homogenizes" and that was measured at lr=0.01 inherits the same suspicion (the file does not enumerate them; see per-entry flags).

**What the synthesiser should note [I]:** (a) the "collapse" disease is specific to lr=0.01 on family_b with this optimizer setup — so any old concept whose value came from "de-collapsing" is premise-dependent; (b) the surviving large effect is the **capacity penalty** (L5−L2 +134.59; see C-1), which was measured on the healthy substrate, but on a per-user mean-of-ratios EE metric with a *concave load-share* power model and **zero handover energy**.

---

## Concept entries

### C-1. Capacity penalty L_cap — "容量懲罰", 4th training strategy (old labels: M4, OFFM4, `capacity_penalty` block, L5/"僅懲罰塑形"/"懲罰塑形")
- mechanism (one line): training-only loss term: per-user masked softmax over scale-normalized weighted Q (Ṽ_u = (V_u − mean)/std) → aggregate into per-physical-beam "intent pressure" p_{ℓc}; penalize the squared preference mass that falls OUTSIDE each satellite's top-k_cap(=3) beams, `T_ℓ = Σ_c p_{ℓc} − TopKSum_3(p_{ℓ,·})`, `L_cap = λ Σ_ℓ T_ℓ²`, λ=0.05, τ=1; deployment = plain per-user argmax (term absent). "每顆衛星只留三條最受偏好的波束,落在其餘波束的偏好質量要付代價。"
- intervention point: penalty/loss (centralized-training population regularizer; computed on a fresh full-population forward at the CURRENT rollout step, entering each head's backward)
- defined in: CV2/CAPACITY-PENALTY-MINI-SDD-2026-07-18.md:40-55 (§2v2/§3v2 override v1 body l.64-83); prior-art card CV2/CAPACITY-PENALTY-PRIOR-ART-CARD-2026-07-18.md; code `shared_q_isolation/capacity_penalty.py`; arm prereg CV2/CLOSURE-AMENDMENT-M4-2026-07-18.md.
- run status: ran, three times:
  (a) OFFM4 diagnostic: 6 seeds × 12000 ep (CV2/CLOSURE-M4-RESULT-2026-07-18.md);
  (b) abl9k L5 `abl9k_capacity` 6 seeds × 9000 ep + in-stack arms L6/L8/L9/L10 (CV2/ABL9K-RESULT-2026-07-21.md);
  (c) ep2000 wave L5/L6/L8 6 seeds × 2000 ep, 20 periodic snapshots (CV2/EP2K-RESULT-2026-07-20.md);
  (d) `offm4_p01` pilot at lr=0.01/3000 ("cheap-regime pilot") — SIGSTOP'd with the 33 frozen runners, no recorded result found (ABLATION-SPEC-9000EP:77; CLOSURE-M4-RESULT:66-68).
- run conditions: env family_b, k_cap=3/satellite, U=100, concave load-share power, zero handover energy (see header); metric = argmax_EE (mean of per-user eta, Mbits/J) on best-weighted-reward-on-eval ckpt; **lr = 1e-3**; main trained **from scratch**; concat live-z 448 state; gamma [0,.9,.9] in (a) (comparator OFF 523.78), gamma null in (b)/(c). λ smoke-calibrated, never swept (CLOSURE-AMENDMENT-M4:20-23). Ignition gate + λ=0 bit-identical equivalence passed before launch (l.13-18).
- recorded outcome:
  (a) "**SIGNAL**: +89.28, 6/6 seeds, mechanism check PASS" — OFFM4 613.05 vs OFF 523.78; served 0.892→0.991, min_cov 0.792→0.960, **cap_bump 0.108→0.009 (−92%)**; r3 improved 6/6, r2 slightly worse (−5.8%, 3/6), J_w +38% 6/6 (CLOSURE-M4-RESULT:12-34, 83-88). Frozen prediction was NULL [−15,+12] — "Big miss" (l.48-51).
  (b) abl9k: `E_cap_alone` L5−L2 = **+134.59** [+116.0,+153.2] 6/6 (descriptive); P1 L6−L2 = +124.31 BENEFIT (Holm); P3 L6−L9 (full minus "w/o 3-strategy") = −7.35 INCONCLUSIVE; L5 619.73 ≥ L6 609.45 (ABL9K-RESULT:15-16, 26-37).
  (c) ep2000: capacity-carrying arms separate from all others at every one of 20 points (+222.9…+401.5); "懲罰塑形 (capacity penalty) is the only large effect among the mechanism contrasts" (EP2K-RESULT:65-75, 146-150); gap is 3× the 9000-ep gap because non-capacity arms are undertrained at ep2000 (l.178-184).
  LATEST verdict: capacity penalty = the whole measured framework effect on this substrate; HANDOFF-2026-07-20-EP2K-COMPLETE:65-66 "removing penalty shaping costs +169…+296, across 6 axes and 64 points without exception" (EE-vs-parameter sweeps, `ep1500-ee-sweeps-2026-07-20/` CSVs only, no README).
- recorded cause (quote): G6 downgraded mechanism to "two undiscriminated candidates": behavioral chain (tail compression → coverage → EE) vs "the penalty as a NUMERICAL STABILIZER (suppressing Q-explosion/representation thrashing)" — grad-norm 28 → ~2 (CLOSURE-M4-RESULT:77-82); codex F4: "ANY specific mediation chain ... = unestablished"; F5: "looks like overload-suppression / better coordination, NOT diversity expansion" (l.106-117). Also: best ckpts arrive early (ep 249–9349) — "premature-convergence / late-instability signature" (l.89-94). `p_exp` sweep: advantage ratio 1.71×→1.63× over power-exponent α 0.2→1.2 ⟹ "the advantage does **not** depend on economies of scale" of the concave power model (HANDOFF-2026-07-20-EP2K-COMPLETE:108-111). EP2K: "*why* 懲罰塑形 dominates" is hypothesis-untested (EP2K-RESULT:174).
- inferred cause [I]: the env HARD-DROPS any user whose chosen beam ranks 4th+ on its satellite (cap_bump; `family_b_step.py:496` per SDD l.6-7), and a dropped user scores eta=0 in a mean-of-per-user-ratios EE. OFF loses ~10.8% of user-slots to cap_bump; eliminating those alone lifts served 0.89→0.99, which by construction lifts the mean-of-ratios metric. So a large share of the +89/+135 is plausibly "stop self-inflicted outages under a hard per-satellite beam cap", not "better energy use". Synthesiser should check whether the new project (a) has a hard top-k beam drop that zeroes users, (b) scores pooled vs mean-of-ratios EE, (c) has the same concave load-share power — if the new env has no cap-bump outage mechanism, the premise of C-1 is absent.
- premises: "a hard per-satellite beam cap drops users (cap_bump) under independent per-user argmax"; "unserved users count as 0 in the scored EE"; "intent (softmax) tracks argmax action closely enough"; NOT dependent on "collapse exists" (measured at lr=1e-3).

### C-2. Multi-catfish "3-strategy" experience shaping — EE-stratification (M1) + asymmetric discount γ_CF (M2) + periodic intervention conduit (M3) (old labels: faithful-catfish, SCFZA, `faithful-full`, 經驗塑形, L3/L7, "3-strategy")
- mechanism (one line): sibling catfish agent(s) with their own replay trained on dual self-rollout; M1 routes high-EE ("stratified") transitions to the catfish buffer and mid-band to main via cross-route; M2 gives catfish a longer discount (GAMMA_CATFISH 0.99 vs GAMMA_MAIN 0.9); M3 periodically (period ~U[4,16] steps) replaces 30% of main's minibatch with catfish-buffer samples.
- intervention point: experience (replay composition) + objective (asymmetric γ)
- defined in: `route_b_factorial/faithful_catfish_trainer.py` (M3 at :322-324, M1 cross-route :418-425 per PACK-MINI-SDD:53-62); CLOSURE-AMENDMENT-TEACHER-MATRIX-2026-07-18.md:22-26 (SCFZA); ABLATION-SPEC-9000EP-2026-07-19.md:30.
- run status: ran —
  (a) SCFZA_catfish_argmax_k1 vs OFFSYMG, 6 seeds × 12000 ep (CLOSURE-B4-SCFZA-RESULT);
  (b) abl9k L7 `abl9k_strategy3_static` (non-annealed) and L3 `abl9k_strategy3_annealed`, 6 seeds × 9000 ep;
  (c) ep2000 L3 6 seeds × 2000 ep;
  (d) earlier lr=0.01 SCFZA_p01 ×3 local — LOST at ~2 h (process teardown), zero output (ABLATION-SPEC:80-83).
- run conditions: family_b, argmax endpoint, concat-z 448, **lr 1e-3**, gamma_per_objective **null** (catfish carries its own γ pair), main **from scratch** with catfish trained concurrently (NO Phase-1 external-expert/oracle seeding — "that faithfulness gap remains disclosed", CLOSURE-B4:51-54); metric argmax_EE.
- recorded outcome:
  (a) "**HURTS**: −20.37, 4/6 seeds" (477.31 vs 497.68); served −6.0pp, min_cov −4.8pp, cap_bump +2.7pp — "damage is ACROSS-THE-BOARD" (CLOSURE-B4-SCFZA-RESULT:1-38). Borderline: mean 0.37 past the −20 line, sign clause did not fire.
  (b) abl9k E_3strategy L3−L2 = −9.10 [−40.0,+21.8] 4/2; L7 465.70 < L2 485.14 (ABL9K-RESULT:13,17,38).
  (c) ep2000 Q5 (L3−L2): "**not credited** under the applied n=6 rule"; but under the literal frozen ADDENDUM-A n=4 clause "**CREDITED** — qualifying run ep1300–1500" (EP2K-RESULT:94-114). Training-reward stream showed L4−L2 = +211.64 @ep1500 (6/6) that ≈0 at 9000 ep (−2.03) (l.19-21).
  LATEST verdict + revision chain: HANDOFF-2026-07-20-EP2K-COMPLETE:63 said "NOT CREDITED ... null is informative rather than underpowered" → **WITHDRAWN** in EP2K-RESULT G6 revision (l.23-28): "does NOT rule out a slower, replay-mediated 經驗塑形 effect"; power for +40..+60 late transients ~20–45% (blind refuter MC, not reproduced). Phase-2 decomposition (w/o stratification / w/o asymmetric discount) NOT launched as "an OPERATIONAL gate decision only" (l.198-203). Codex review pinned to commit 9f09e7db was still OPEN in this file. RED LINE: "NOT 'catfish drives the win'" and "「鯰魚／經驗塑形無效」 may not be written from this wave" (l.207-212).
- recorded cause: SCFZA reading: "self-rollout catfish package ... hurts EE on the argmax+z-score substrate ... NOT a global 'catfish mechanism dead' claim; ... the paper's catfish was never fairly tested here (Phase-1 expert seeding absent from our code)" (CLOSURE-B4:47-54). Late-training interference: "help-window +155 @1500–2000ep (5/6 seeds), cliff at 2000ep, monotone decay to −423 @11–12k" in paired train-r1 (ABLATION-SPEC:37-39).
- inferred cause [I]: the catfish's high-EE samples come from its own self-rollout on the same per-user-argmax policy class — no better-than-learner source exists, so the conduit injects off-policy data without new information; early help = extra effective updates/exploration while main is undertrained, late harm = off-distribution replay once main converges (records call this "late interference", not tested).
- premises: "a better-than-learner experience source exists" (violated: self-rollout only); "main is under-exploring/homogenized" (the collapse premise — measured here at healthy lr, so the premise was weak); per-user r1 stratification threshold meaningful.

### C-3. Intervention annealing (M3 conduit ratio decay 30%→5%, coupled with M1 cross-route admission probability s(ep))
- mechanism: piecewise-linear schedule s(ep)=1 until ep 1500, linear to 0.05/0.30 at ep 3000, hold; multiplies M3 intervention ratio and M1 cross-route admission probability; dedicated RNG stream so cadence/exploration draws unchanged.
- intervention point: experience (schedule on the injection channel)
- defined in: CV2/PACK-MINI-SDD-2026-07-19.md:34-97; ABLATION-SPEC-9000EP:36-40 (anchors: Mnih 2015 ε-decay; Kirkpatrick 1983 annealing).
- run status: ran — local fast test 4b (3 DEV seeds × 4000 ep; attempt-1 killed by session reap, attempt-3 detached; HANDOFF-IMPL:14-47), 4c full-stack PASS (2 dev seeds × 2000 ep); abl9k L3 (annealed) vs L7 (static) 6 × 9000 ep.
- run conditions: same as C-2 (lr 1e-3, gamma null, concat-z 448, from scratch, argmax_EE).
- recorded outcome: abl9k E_annealing L3−L7 = +10.33 [−21.5,+42.2] 4/2 — "activates the prereg's future-study trigger — recorded ... NOT used to modify any verdict" (ABL9K-RESULT:41, 74-75). 4b adjudication outcome itself not in the files I read [not found in this cluster's list]. LATEST: descriptive only, inconclusive.
- recorded cause: none beyond the design rationale "keeps the early stirring dividend and retires the late interference" (ABLATION-SPEC:37-39).
- premises: C-2's early help window is real and the late harm is from injection volume.

### C-4. ACRM — linear differential competitive reward, self-competition via lockstep counterfactual clone (old labels: ACRM, 獎勵塑形, `acrm-annealed`, L4)
- mechanism: catfish r1 is reshaped `r^C = r^CF + η_w(r^CF − r^M)` (η_w=1, tanh OFF) where r^M is the r1 the MAIN greedy policy would have earned in the SAME state and SAME fading draw, obtained from a deep-copied env clone advanced in lockstep (only `_assignments_slot` synced each step); shaped reward drives ONLY the catfish critic ("containment" — main always gets raw rewards).
- intervention point: reward (catfish-side), indirectly experience for main
- defined in: CV2/PACK-MINI-SDD-2026-07-19.md:99-181; old-line design `catfish_faithful_familyb/config.py:96-110`, `trainer.py:330-404`; USER: "original paper's ACRM details not trusted; design ours from our env's first principles" (ABLATION-SPEC:41-45).
- run status: ran — abl9k L4 (3-strategy+ACRM), L6 (full), L8 (full w/o ACRM), 6 × 9000 ep; ep2000 L4/L6/L8 6 × 2000 ep.
- run conditions: lr 1e-3, gamma null, concat-z 448, main from scratch, argmax_EE, same-state/same-fading exact pairing.
- recorded outcome: abl9k E_acrm_nocap L4−L3 = +7.07 (5/1), E_acrm_instack L6−L8 = −6.10 (2/4) (ABL9K-RESULT:39-40); ep2000 Q3a (L4−L3, without capacity) **CREDITED** 3 points (ep1000–1200), peak +110.86, 5/6 — "minimally cleared the bar"; Q3b (with capacity) not credited (EP2K-RESULT:85-86, 161-165). Sweep figures: "removing reward shaping costs +10…+16" (HANDOFF-EP2K-COMPLETE:65). LATEST: "獎勵塑形 (ACRM) is small and conditional"; redundancy with capacity penalty = hypothesis-untested (EP2K-RESULT:161-175). EXP-ACRM-OPPORTUNITY-FINAL-REPORT (see C-? below) addresses its opportunity separately.
- recorded cause: none established.
- premises: "main's same-state counterfactual is a meaningful competitor baseline"; catfish learning propagates to main via the conduit.
  - ACRM citation fact (CV2/CDRL-THESIS-ACRM-CITATION-CARD-2026-07-21.md:9-17): the source CDRL thesis (柯博瀚 2025, RIS on/off control) itself reports ACRM "has the smallest effect" / "limited benefit"; asymmetric discount S2 was the LARGEST effect there. Card's explanation for S2 not transferring: "他們的 RIS 開關環境具跨步時間結構,我們的 family_b(10-step、per-step 重算)沒有" (l.40-44) — i.e. component value is substrate-dependent on temporal coupling.

### C-5. Gated conduit / direct-main ACRM (build gated by the catfish same-state WIN-RATE diagnostic)
- mechanism: only route catfish transitions (or apply ACRM ranking directly to main) when the co-trained catfish's action bundle beats main's greedy bundle on raw r1 in the same pre-state AND does not worsen cap_bump ("capacity-nonworsening", CNW).
- intervention point: experience (gated) / reward
- defined in: CV2/WINRATE-DIAG-PREREG-2026-07-20.md:7-16, 83-92 (diagnostic prereg; the build itself was never specified beyond this).
- run status: build **never built**. Diagnostic ran: 2 arms (`abl9k_full_mccrl`, `abl9k_strategy3_acrm`) × 3 seeds × 2000 ep local (first 1000-ep launch killed by host restart; AMENDMENT-C relaunch at 2000 ep); status demoted to EXPLORATORY (AMENDMENT-B).
- run conditions: lr 1e-3, gamma null, concat-z 448, from scratch, ε-greedy catfish vs pure-greedy main counterfactual (`catfish_pack.py:275` — acknowledged regime problem).
- recorded outcome: "capacity regime 下 bundle-CNW 勝率尾段僅 1.4% ⟹ 舊 conduit 無物可送" (archive/project-state/CURRENT-STATE-CHRONICLE-through-2026-07-22.md:18; EXP-ACRM-OPPORTUNITY-FINAL-REPORT:24 "EXPLORATORY——正式 Stage-1B 未做,關不了 redesign"). Frozen NO-GO bar was <5%, GO ≥10% (prereg l.42-46). Stage-1B (server, greedy-catfish third branch) never done.
- recorded cause: in the capacity regime the challenger rarely finds a better capacity-feasible bundle; two-stage logic (nothing-to-find vs challenger-blind) was resolved by C-6's probe as "nothing-to-find" (NULLSPACE-PROBE-RESULT:34-36).
- premises: "a co-trained challenger finds better same-state actions than main"; "there is re-pairing headroom above the penalty-only policy".

### C-6. Capacity-nullspace counterfactual catfish / constrained-swap re-pairing (「容量零空間反事實鯰魚」)
- mechanism: holding the per-satellite active-beam set (demand histogram) fixed, search user↔beam re-pairings (pair swaps, 3-cycles) that raise EE without changing capacity structure; would feed a catfish/ACRM that proposes such swaps.
- intervention point: decode/deployment-derived target for experience/reward (probe = oracle search, no training)
- defined in: CV2/NULLSPACE-PROBE-PREREG-2026-07-20.md (not read in full); result CV2/NULLSPACE-PROBE-RESULT-2026-07-21.md.
- run status: probe ran (3 seeds × 96 states, ≤600 sampled pair-swaps + 200 sampled 3-cycles/state; 18 boundary states fully enumerated for pair swaps) on **penalty-only ckpts**; learner never built.
- run conditions: family_b, argmax EE, one-step, lr-1e-3 capacity ckpts.
- recorded outcome: "**NO-GO (FINAL)**" — mean Δ_best **+2.137**, max **+8.896**, 288/288 states positive, vs GO bar +40 (l.9-17). LATEST revision (USER-caught 07-21): "NOT an upper bound ... measured +8.90 max is a **lower bound** of the nullspace optimum"; exact instrument (max-weight assignment / min-cost-flow with beam quotas) proposed, "optional, not scheduled" (l.47-55).
- recorded cause: "whatever learnable EE remains above best-tuned penalty-only lives in the **active-set (demand-histogram) configuration space** — capacity's own turf — not in WHO pairs with WHICH active beam" (l.37-40). [I] With the concave load-share power model, power and interference are fixed once the histogram is fixed, so re-pairing can only move rate via per-user gain/SINR differences.
- premises: "active-set fixed, pairing matters"; "a better-than-learner teacher exists within the nullspace".

### C-7. W-step (multi-step) ACRM / temporal credit for experience shaping
- mechanism: compute the competitive reward over a W-step window rather than one step, to capture delayed consequences.
- intervention point: reward
- defined in: NULLSPACE-PROBE-RESULT:19-27 (W=2 persistence mini-probe).
- run status: never built; W=2 persistence probe ran (288 states).
- recorded outcome: "ΔEE at t+1 and t+2 = **0.0000 exactly**"; "W-step ACRM is DE-PRIORITIZED on this evidence, not theorem-closed" (closed-loop divergence untested).
- recorded cause: "no accumulating state across the 10-step episode" (GROUNDED-INERT code note) — family_b recomputes per step.
- premises: "the env has cross-step coupling" — **absent in family_b** (base env persistence exactly 0), present on a queue substrate (C-8). [I] Synthesiser: check whether the new project's env has persistent state (handover, beam state carry-over, queues); if yes, this premise may hold there.

### C-8. Queue-substrate (backlog) lever for experience-shaping mechanisms (Level-1 queue probe)
- mechanism: add per-user traffic queues/backlog so actions have persistent consequences; a demand-aware policy could then harvest temporal credit that experience shaping / asymmetric discount can exploit.
- intervention point: other (environment/substrate change) enabling experience/objective mechanisms
- defined in: CV2/LEVEL1-QUEUE-PROBE-PREREG-2026-07-21.md (not read); result CV2/LEVEL1-QUEUE-PROBE-RESULT-2026-07-21.md.
- run status: probe ran (3 seeds, two load ranges ρ∈[0.2,1.2] and retry ρ∈[0.5,1.5]); H2 used a **20-line heuristic** demand-aware policy, no training.
- recorded outcome: H1 persistence ratio PASS 0.1261 / 0.1546 (12.6–15.5% of a perturbation's queue-EE effect survives to next step, vs exactly 0 on base env); H2 demand-awareness gap FAIL +0.83% / −0.13% (<+3% gate) ⟹ "queue lever DIES per the frozen contract" (l.1-13). LATEST (USER ruling 07-21): "a thesis-time resource stop, NOT a scientific exclusion of queue-aware mechanisms"; H2 is a lower bound (l.29-41).
- recorded cause: "utilization saturates at high load" = controller's frozen-prediction mechanism, "not a measured explanation" (l.24-27).
- premises: "temporal coupling exists" (TRUE on queue substrate); "demand-awareness has material EE dividend" (not shown).

### C-9. Capacity-penalty strength (λ) sweep + dose controls (sham-step, extra-TD, grad-norm-matched L2)
- mechanism: vary λ ∈ {0.0125,0.025,0.05,0.1,0.2} to discriminate "capacity-tail semantics" from "numerical stabilizer / extra-update dose"; matched controls isolate dose.
- intervention point: penalty/loss (diagnostic of C-1)
- defined in: CV2/LAMSWEEP-PREREG-2026-07-20.md.
- run status: **never run** — design check verdict "**DO-NOT-LAUNCH**(7+ MAJOR:控制臂須同批、exposure telemetry、lamsweep_0 臂…)⟹ rev-2+實作後才排" (CURRENT-STATE-CHRONICLE:16-17); "λ rev-2 + dose controls（保留）" (EXP-ACRM-OPPORTUNITY-FINAL-REPORT:75).
- planned conditions: 3000 ep, seeds 42/137/271, lr 1e-3, `abl9k_capacity` config ± λ.
- key design fact (l.26-31): "The penalty **compresses** per-satellite intent into the top-k_cap beams ...; it is NOT cross-satellite load dispersion" — direction note corrected 2026-07-20. [I] This matters for transfer: C-1 is NOT a "spread load / anti-homogenization" mechanism; it is "align intent with the env's hard top-k beam selection".
- premises: C-1's effect is real; mechanism is open.

---
### (07-13/07-14 block) Physics facts recorded this week that condition every "spread / load-balance" concept below
- **Per-user EE falls with beam load in family_b** (CV2/EE-LOAD-DEPENDENCE-PREREG-2026-07-13.md + RESULT json): chain `r1 = b_alloc/load · log2(1+sinr)`, `allocated_power = power_lc/load`, `beam_power_w(L) = min(0.25+0.35·L^0.5, 10)`; measured through real env.step(): "EE monotonically DECREASES" with load, total drop factor ~2.85× over load 1..40; satellite aggregate cap "PROVABLY never binds" (max sat total 11.25 W < 19.95 W).
- **Oracle mechanism = open all 12 beams + balance load** (CV2/ORACLE-AND-CATFISH-ABLATION-VERDICT-2026-07-13.md:56-64): ORACLE_LB 694.34 opens 12.0 beams, load 8.33, P 1.26 W vs AF 5.48 beams, load 18.2, P 1.74 W: "the entire +54.9 % comes from OPENING MORE BEAMS and BALANCING LOAD ... Not from per-user channel matching."
- **r1 is a contextual bandit** (AXIS-AND-CLAIRVOYANCE-VERDICT-2026-07-14.md:107-114): `r1 ⊥ a_{t-1}`; `r2` is the only temporal reward; `_window_sat_ids` frozen at reset; γ = [0, 0.9, 0.9].
- **r3 perversity (trainer/reward defect relevant to the brief's "free ride" item)**: legacy r3 = max−min throughput "over ACTIVE beams only" (`family_b_step.py:761`), so collapse onto ~3 beams earns an r3 bonus; with γ3=0.9 (×6.51 over H=10) "r3 ≈ FULLY offsets the EE penalty" (129 % discounted) (R3-DISCOUNTED-RESULT-2026-07-14.md:25-31, 72-80). And "Collapse (0 handovers ⟹ best r2) is NEARLY the immediate-reward optimum" once r2 is included (R3-LANDSCAPE-G6-REFUTED-2026-07-14.md:13-16). ⟹ the *reward* partly rewards collapse on the discounted objective; this was never fixed on the concat line (corrected-r3 abandoned 2026-07-19).
- **[I] Contrast for the synthesiser**: the harvest's memory notes that in the NEW project "每束功率取 max、無 PA 飽和區、PA 佔 94.8%、頻寬共享抵銷人數; C3 變體都多開 beam" — i.e. load balancing does NOT buy EE there. In family_b it DID (concave per-beam power, per-user share). Every concept whose premise is "spreading/opening beams raises EE" must be checked against this.
- **Endpoint/metric warning from this week**: training-log `r1_mean` = 10× the per-step mean EE (defect D7: `ep_reward` summed over users AND steps but divided by users only; `faithful_catfish_trainer.py:549`, `family_b_retrain/trainer.py:226`) — "Harmless within-arm; off by 10× against the eval harness" (ORACLE-AND-CATFISH-ABLATION-VERDICT:160-164). This is the cluster's instance of an **uncalibrated logged scalar**. Also the handoff's `Z = −2.63` was on `J_w` (mixed metric), "wrong axis" (l.118-127).

### C-10. Catfish-as-cause-of-degradation test (A1 catfish OFF vs A2 catfish ON, best→final degradation)
- mechanism: tests whether the catfish stack causes the thesis arm's best-ckpt → final-ckpt EE degradation.
- intervention point: experience (catfish ablation; diagnostic)
- defined in: CV2/A1-VS-A2-PREREG-2026-07-13.md; verdict CV2/ORACLE-AND-CATFISH-ABLATION-VERDICT-2026-07-13.md:83-136.
- run status: ran (eval-only re-scoring of existing ckpts; 2 matched pairs × 3 seeds: `faithful-augmented-2026-07-09` 224-d and `faithful-catfish-effect-2026-07-08` 140-d).
- run conditions: route-B / faithful-catfish era — **lr = 0.01, 3000 ep era [I from LR file: old era = hybrid/0.01/3000, and A1/A2 are C1FIXED arms]**; trained with coordinated (corrected/hybrid k_c=1) decode; scored on argmax-EE AND decode-EE; main from scratch with catfish sibling (faithful dual-rollout + γ_CF + intervention conduit, `intervention_fired_count = 3036`).
- recorded outcome: "Catfish does NOT cause the best→final degradation" — A1 (OFF) degrades at 93.2 % of A2's magnitude, 3/3 seeds; pair 1 A1 degrades MORE (ratio 1.373) (l.16-19, 92-116). Also: "`argmax min_cov = 0.000` on ALL 12 thesis-arm checkpoints ... argmax-EE is 104–150 — at or below the plain-MODQN collapsed floor (146.6). Their 444–476 EE comes **entirely from the decode**" (l.131-136). LATEST: "The A2-degradation line is CLOSED" (l.203). Note: this verdict table lists candidate 2 "DRL hyper-params (lr) — already excluded (USER, 2026-07-12)" (l.145) — **later overturned by COLLAPSE-ROOT-CAUSE-IS-LR (07-20)**.
- recorded cause: none for the degradation; catfish excluded.
- premises: measured on the lr=0.01 collapsed substrate ⟹ **contaminated per the LR file's logic [I]**: both arms were collapsed under pure argmax; "catfish neither helps nor hurts a collapsed agent" is what this shows.

### C-11. EE-aware decode valuation (replace the auction's rate bid log2(1+SNR) with an EE bid B·log2(1+SNR·P(L)/p_one)/P(L); + interference-aware; + E[fading] "F-mean"; + handover-priced "G")
- mechanism: zero-learning centralized facility-location / greedy auction decode whose per-user bid is the closed-form EE given the decoder's own induced load (E1/E2), plus interference (F), with fading replaced by its mean (F-mean), plus a switching-cost term at λ=(w2·c1)/(w1·c2) (G).
- intervention point: decode/deployment (centralized coordinator; also later used as an injection *teacher*)
- defined in: CV2/EE-AWARE-DECODE-PREREG-2026-07-13.md:23-50 (diagnosis: "`auction_decode.py:29` valuation ... NO power term. NO load term"); CV2/AXIS-AND-CLAIRVOYANCE-VERDICT-2026-07-14.md.
- run status: ran (eval-only, 48-ep harness, zero training).
- run conditions: family_b, k_cap=3, argmax_EE and J_w on the frozen harness; no learning; no lr.
- recorded outcome: AF (rate bid, k_c=1) 448.28; full auction k_c=3 447.09 ("letting the auction open all 12 beams buys +6 EE"); E1 505.08; E2 519.68 (≈11 beams); F 636.34; F-mean 636.05 (churn 17.9 %); G 596.0 EE with best J_w 9.748e-4 at min_cov 1.000 — "+95 %" J_w over the thesis arm A2 (EE-AWARE-DECODE-RESULT json; AXIS-AND-CLAIRVOYANCE-VERDICT:23-34, 81-90). "Knowing the future fading makes you WORSE" on J_w (F churns 3.2× more than F-mean, J_w −37 %) (l.43-60). LATEST: "`G` is NOT a contribution. It is a CONTROL" / strong static, ≤1 disclosure line (l.120-126); later adopted as best teacher for injection pools (C-13/C-14).
- recorded cause: "The auction has no incentive to spread. `k_c` is not the constraint — the VALUATION is" (EE-AWARE-DECODE-PREREG:44-46); "NO per-user valuation, however clever, can price the load — because the load is definitionally a JOINT quantity" (l.55-57).
- premises: spreading/lower per-beam load raises EE (true in family_b physics); a central decoder is allowed (USER later BANNED decoders from the thesis — "argmax action selection needs no such word", ABLATION-SPEC-9000EP:11-13; brief 07-14 "deployment-time coordinator ... is DELEGATION and is FORBIDDEN").

### C-12. Plasticity / high-replay-ratio composite (RLPD 50/50 sampling + D'Oro high replay ratio + periodic hard reset of final layers + LayerNorm Q-head + no BC/margin)
- mechanism: discrete-DQN adaptation of RLPD + "sample-efficient RL by breaking the replay ratio barrier": raise updates-per-step (currently 1), periodically hard-reset final 2 layers (+target nets, Adam stats) while preserving replay, LayerNorm on the Q-head to bound Q on out-of-data actions, symmetric 50/50 expert/own sampling, drop DQfD margin.
- intervention point: exploration/other (optimizer/update schedule, representation), experience (sampling ratio)
- defined in: CV2/CATFISH-REDESIGN-BRIEF-2026-07-14.md:112-146 (with two open hyperparameters: reset depth, target-net action selection vs Double-DQN).
- run status: **never built** (brief says "Only if X-1 says there is headroom"; AXIS verdict §7 l.169-172: "Do not go-server on them as posed"). Related: ReDo (`family_b_retrain/redo_trainer.py`) existed; "Old Family-B ReDo fired 89× and still 3/3 collapsed ⟹ plasticity is NOT shown primary" (R3-LANDSCAPE-G6-REFUTED:17-19) — that ReDo run was lr=0.01-era [I].
- premises: "the collapse is a plasticity/optimizer-instability pathology" — partly vindicated in spirit by the LR root cause (07-20), but no plasticity mechanism was ever tested at healthy lr.

### C-13. Decentralised-realisability ceiling (X-1: best per-user map f(obs_u)→a_u fitted to the specialist's actions, deployed as pure per-user argmax) and BC k-NN lookup
- mechanism: behavior-clone (1-NN/k-NN or supervised net) a centralized specialist (F-mean/G/ORACLE) and deploy per-user; measures how obs_u-predictable a good joint assignment is.
- intervention point: representation/decode (imitation ceiling instrument; also the "BC floor" baseline)
- defined in: CATFISH-REDESIGN-BRIEF-2026-07-14.md:88-104, 199-215; executed via FROZEN-Z-BC-PREREG-2026-07-14.md / BC-BAR-PREREG-2026-07-15.md (see C-15).
- run status: ran (zero-learning lookup; see C-15 for numbers): "BC k-NN 475.8/475.26" is the recorded "zero-learning floor" (CLOSURE-M4-RESULT:56; IDEATION-SYNTHESIS:24-29).
- recorded outcome: learning had not beaten lookup at lr=0.01/early lr=1e-3 (best trained 418–479 vs BC 475.26) (IDEATION-BRIEF pathology 4); at healthy lr=1e-3 the trained OFF reached 523.78 (12000 ep) and capacity penalty 613–620, so this floor was later exceeded.
- premises: "a better-than-learner teacher exists" (TRUE here: F-mean 636, G 596, ORACLE 681.8); "obs_u carries enough to imitate" (k-NN consistency 0.6541 vs myopic 0.6020).

### C-14. Ideation-panel survivors (07-14): S1 joint-gated self-promotion ("the catfish that evolves"), S2 injection thermostat (EE-regret-controlled ρ/λ), S3 teacher-bootstrap (Expected-SARSA on expert's next action for r2/r3 TD targets), S4 free-DAgger (expert shadow labels on agent-own states)
- mechanisms: S1 — after a step, compare the closed-form JOINT EE of the agent's whole assignment vs the expert's re-solved assignment at the same state; if agent wins, promote the whole step-bundle into the expert pool (pool ratchets above demonstrator; joint gate, NOT per-user gate, to avoid free-rider/unilateral-BR poisoning). S2 — set injection ρ (or margin λ) ∝ clipped joint-EE regret on a frozen probe set. S3 — r2/r3 TD target bootstraps on expert action at s' (targets "max-bootstrap divergence at lr=0.01"). S4 — DAgger-style margin on agent's own 70 % slice.
- intervention point: S1 experience; S2 experience schedule; S3 penalty/loss (TD target); S4 penalty/loss
- defined in: CV2/IDEATION-SYNTHESIS-2026-07-14.md:65-120 (brief: IDEATION-BRIEF-2026-07-14.md).
- run status: **never built** (no code/prereg found by grep for golden_pool/thermostat; later "SIL / margin-off 自我刺激 — NOT-DEMONSTRATED / underpowered (power ≈0.11) — 未排除", EXP-ACRM-OPPORTUNITY-FINAL-REPORT:26, refers to a related self-stimulation line I did not locate the run for).
- premises: S1/S2 need a free online-queryable expert with exact joint EE (TRUE in family_b: F-mean/G are zero-learning); S3 is framed against lr=0.01 bootstrap divergence (premise withdrawn by LR file [I]); gates recorded: "The injection baseline must be stable first (the lr / episode-budget confound is unresolved)" (IDEATION-SYNTHESIS:140-141).
- **S3 relevance to brief's "per-head bootstrap" defect [I]**: S3 explicitly proposes changing which action the r2/r3 heads bootstrap on (expert's a' instead of own argmax), i.e. the records did look at the bootstrap-action choice, but only as an idea; no record says MODQN heads bootstrap on their own per-head argmax.

### C-15 (killed-at-ideation list, 07-14; recorded as DEAD/DAMAGED by the "equilibrium lens"). Dense counterfactual EE distillation (CEESL / All-Action EE regression / EE-ROW stamp), EE-regret margin, EE-Boltzmann exploration, ε-expert exploration, cross-user repulsion penalty, dynamic Q-head range normalization
- mechanism: supply per-user counterfactual EE rows as dense supervision; or margin/exploration variants.
- intervention point: penalty/loss (distillation, margin), exploration, representation (repulsion), other (normalization)
- defined in: IDEATION-SYNTHESIS-2026-07-14.md:10-61.
- run status: dense-CF distillation RAN (closed-loop): "a **PERFECT** fit of the true counterfactual tensor A_cf ... scores **335.4** — worse than the current trained agent (418.5). With arm G as source: **64.8**" (l.18-25, quoting EVIDENCE-LEDGER-2026-07-15). Others never built.
- recorded cause: "A_cf[u,·] is a **unilateral best-response**; 100 users argmaxing it simultaneously is a **simultaneous best-response in a congestion game** ⟹ it loses the top-k_cap demand race in one step" (l.21-23). The lens: "Per-user VALUE information is FREE and WORTHLESS here ... What the expert data uniquely carries is EQUILIBRIUM information" (l.39-45). EE-regret margin "BACKFIRES" where the equilibrium signal lives; EE-Boltzmann correlates exploration noise across users (2.7× cost); repulsion "spread ≠ health" (distinct 11.04→12.55 while min_cov 0.718→0.559) (l.54-61).
- premises: hard top-k_cap ranking cut per satellite (congestion game) — [I] the killing mechanism depends on family_b's hard cap_bump drop; check if present in new env.

### C-16. Counterfactual-mirror probe → per-user identity signal (UID; SePS / HyperMARL-class per-user embedding) as prerequisite for any injection into a shared Q
- mechanism: probe whether near-identical observations of two users have DIFFERENT counterfactual-EE argmaxes under a good joint assignment (then a shared deterministic Q(obs_u) provably cannot fit them); if so, add a per-user identity/embedding (UID) so the shared net can emit different actions for near-identical obs.
- intervention point: representation (UID) — probe is diagnostic
- defined in: CV2/CF-MIRROR-PREREG-2026-07-14.md (decision rule l.44-52); result CV2/CF-MIRROR-RESULT-2026-07-14.json.
- run status: probe ran (8 episodes, specialist arm G, 39,600 nearest pairs); UID **never built** (`grep per_user_embed|hypernet|agent_id src/ = 0 hits`, prereg l.49; no later build found in this cluster).
- run conditions: zero-learning specialist G rollouts; obs = 224-d augmented encoding, raw and z-scored; no lr.
- recorded outcome (result json): `ARGMAX_DISAGREE_nearest` = **0.694** (raw) / **0.701** (z-scored) vs random-pairs 0.813 (control passes); `P_M3_each_prefers_own_beam` 0.838 / 0.941; EE cost of forcing one shared action ≈ 6.2–6.8 % of the pair's optimum. ⟹ frozen rule branch "≥ 0.50: a shared deterministic Q(obs_u) provably CANNOT fit the specialist's counterfactual optimum ... The UID ... becomes a PREREQUISITE" (prereg l.47-48). Self-test SC1 recorded `PASS: false` (fast objective vs published G rel err 1.6e-3 > 1e-9 tolerance) — **the probe's own validity gate failed** and I found no verdict doc adjudicating it.
- recorded cause: z-scoring does not rescue it (P-M4).
- premises: "a better-than-learner specialist's assignment is the target"; explicitly FORBIDDEN reading "the endpoint is impossible" — a trained Q might find a different, more obs_u-separable assignment (prereg l.56-58). [I] The later capacity-penalty result (613–620 without any UID) shows a shared Q can get far without per-user identity on this substrate.

### C-17. Behaviour-cloning floors in three normalization contracts (k-NN lookup of F-mean demos: live-z 475.26 / raw 421.40 / frozen-z 427.29) and the "same-contract rule"
- mechanism: net-less k-NN lookup of a zero-learning coordinator's (F-mean) per-user actions, deployed as pure per-user argmax; floors any learned arm only within its own obs-normalization contract.
- intervention point: other (baseline/floor instrument); representation (live cross-user z vs frozen per-feature stats vs raw)
- defined in: CV2/BC-BAR-PREREG-2026-07-15.md; CV2/FROZEN-Z-BC-PREREG-2026-07-14.md; results `bc-bar-2026-07-15/BC-BAR-RESULT-2026-07-15.json`, `frozen-z-bc-2026-07-14/FROZEN-Z-BC-RESULT-2026-07-14.json`.
- run status: ran (eval-only, 48-ep harness, BCa CIs).
- recorded outcome: live-z bar 475.26 [457.29, 491.38] @ min_cov 0.723; raw 421.40 @ 0.527; frozen-z 427.29 [413.0, 440.8] @ 0.481 (k=10); ORACLE-pool BC 378.7 ("ORACLE is harder to imitate", CLOSURE-PREREG:66). So "the live-z bar carries a cross-user-z boost" of ~48 EE on the lookup; frozen-z ≈ raw (P-1 prediction "strictly between" HIT marginally).
- recorded cause: the gap 475−421 is "the size of that [cross-user] boost on the lookup" (FROZEN-Z-BC-PREREG:25-27).
- premises: live-population z-score may be "smuggled coordination" (USER boundary question); a cheap zero-learning teacher exists.

### C-18. DQfD pre-training-only screen (P0 BC-net / P1 DQfD-pretrain TD+margin+L2 / P2 RBS TD-only) + follow-ups (capacity A1–A3, bootstrap removal B1/B2 γ=[0,0,0], C1)
- mechanism: DQfD's demo-only pre-training phase (no env interaction) on the F-mean demo pool, scored directly as per-user argmax; follow-ups test function-class capacity and "offline extrapolation / ungrounded bootstrap" as the reason DQfD-pretrain < BC.
- intervention point: experience (demo pretraining) / penalty/loss (margin) / objective (γ)
- defined in: CV2/DQFD-PRETRAIN-PREREG-2026-07-15.md; CV2/PRETRAIN-ABC-PREREG-2026-07-15.md; results in `dqfd-pretrain-2026-07-15/`.
- run status: ran, **n = 1 seed, SCREEN**, 20,000 updates, no env rollouts.
- run conditions: **lr = 0.01** (PRETRAIN-ABC-PREREG:36 "Baseline (parent): ... lr 0.01 · batch 128 · 20 000 updates"); nets 448→100→50→50→28 tanh; γ=[0,0.9,0.9] unless stated; margin m=0.8 λ=1.0; scored on frozen harness.
- recorded outcome (per-arm json): P0 BC-net 409.6 (min_cov 0.585); P1 DQfD-pretrain 344.8 declining (421→345); P2 RBS 165.7 distinct 1.0 "total collapse"; A1 428.2, A2 380.6, A3 261.3 (capacity NOT monotone-helpful — bigger net worse); B1 (DQfD, γ=0) 342.1; **B2 (RBS, γ=0, no bootstrap) 108.9 with beams 3.0, distinct 1.0, min_cov 0.1667**; C1 108.98 same collapse signature; M1–M5 (P1 variants, content not read) 265–373. All < BC bar 475.26. No verdict doc found for PRETRAIN-ABC in this cluster.
- recorded cause (pre-data hypothesis): "OFFLINE EXTRAPOLATION ERROR ... The TD target bootstraps max_a' Q(s') over actions the demos never took" (PRETRAIN-ABC-PREREG:13); decisive test R-4 "B2 does NOT collapse" — **MISSED**: B2 collapsed with γ=0 (no bootstrap), which per the prereg means "my mechanism story is WRONG".
- inferred cause [I]: B2/C1 land on **exactly the lr=0.01 degenerate-attractor signature** (min_cov 0.1667 = 1/6, 3 beams, distinct 1) that COLLAPSE-ROOT-CAUSE-IS-LR identifies (min_cov 0.167 bit-identical across seeds). These screens ran at lr=0.01, so their collapse/decline readings are **contaminated by the lr artifact**; the bootstrap-vs-margin conclusions should not be transferred.
- premises: "a better-than-learner teacher exists" (F-mean 636); "MODQN collapses" (lr-dependent).

### C-19. Full-DQfD external-expert injection (ρ=0.30 demo slice replacing agent samples + large-margin loss m=0.8 λ=1.0 (later "qw_sd"-rescaled) + 8000 demo-only pretrain steps + L2 1e-5; teacher = zero-learning F-mean coordinator)  (old labels: fulldqfd_ON, injection_rung1, "catfish" in WORK-ORDER; Group A/C/D; converge-probe ON)
- mechanism: DQfD (Hester 2018) — expert transitions from a zero-learning joint coordinator mixed into every minibatch with a supervised margin term that pins Q to the demo action.
- intervention point: experience + penalty/loss (margin) + pretraining
- defined in: top-level FBCD/FULLDQFD-WAVE-PREREG-2026-07-15.md (not fully read), FBCD/FULLDQFD-GROUPA-RESULT-2026-07-14.md; code `src/.../injection_rung1/` (trainer.py:7,17-19 per CATFISH-REDESIGN-BRIEF:36-42), `margin.py`, pool builder `fmean_pool_builder.py`.
- run status: ran — Group A 2 lrs × {OFF,ON} × {live-z, frozen-z scoring} × 6 seeds × 3000 ep; converge probe {OFF,ON}_lr001 × 6 seeds × 12000 ep (CV2/CONVERGE-PROBE-RESULT-2026-07-17.md).
- run conditions: family_b, concat-z 448 (live) or frozen-z scoring contract, argmax training decode and argmax endpoint (decoder exit 07-15), γ=[0,.9,.9]; main **from scratch** with demo pretrain; teacher F-mean (636.05, a coordinated congestion-game fixed point, `br_iters=8`).
- recorded outcome: lr=0.01/3000: ON−OFF **+129.97** [+70.05,+189.88] SEPARATED+ — but OFF collapsed (final ckpt distinct 1.01, EE 120.80) ⟹ prereg R-1 "substrate broken, wave void" (FULLDQFD-GROUPA-RESULT:37-68). lr=1e-3/3000: **−57.11** SEPARATED− on PRIMARY ckpt, NULL on SECONDARY; OFF_lr001 under-trained (best ckpt ep ~2824/3000) ⟹ "THIS WAVE CANNOT SETTLE THE ENDPOINT" (l.72-106). lr=1e-3/12000: **ON 440.63 vs OFF 523.78 = −83.15, 6/6, even ON-best (459.8) < OFF-worst (474.0)** (CONVERGE-PROBE-RESULT:21-30). LATEST (RECHECK-VERDICT-2026-07-18.md:88-104, C3 HOLDS): "DQfD (F-mean teacher) hurts EE; +129.97 was an lr=.01 divergence artifact"; gap widens with budget (−57 → −83). ON signature: "higher distinct (12.3 vs 11.2) with lower served (0.72 vs 0.89) and min_cov — label-noise imitation, not undertraining". EXP-ACRM-OPPORTUNITY-FINAL-REPORT:25 "外部注入 ... −57→−83 ... 有害 ... **SOLID**(此 substrate)".
- recorded cause: "the expert's per-user action is a function of information the per-user OBSERVATION does not carry — for F-mean, the joint congestion fixed-point (other users' choices) ... A per-user Q imitating such a teacher **fits LABEL NOISE**" (CONVERGE-PROBE-RESULT:32-44, `hypothesis`). Group-A §4: "injection's effect is a **spread-the-users push** — exactly what a collapsing arm needs, and an **over-correction** once the arm is already spread" (FULLDQFD-GROUPA-RESULT:123-127). Margin scale defect: "the margin is 1,884 × the sd of the quantity it is meant to separate ... the margin is the ONLY loss and TD is numerical noise" (LANE-FACTSHEET-2026-07-15.md:51-54). Review dispute (REVIEW-GROUPA-VERDICT-2026-07-14.md:4-17, agy): claimed r3 perversity is the root cause and lr=1e-3 "merely delaying" collapse — **later contradicted** by 12000-ep OFF_lr001 not collapsing (523.78, distinct 11.2) and by COLLAPSE-ROOT-CAUSE-IS-LR.
- inferred cause [I]: the +129.97 "anchor effect witness" (ABLATION-SPEC-9000EP:86-87) is exactly the lr=0.01-collapse-premise case: demos help a diverging learner; at healthy lr they hurt.
- premises: "a better-than-learner teacher exists" (TRUE: 636); "teacher's action is expressible from obs_u" (FALSE-leaning: CF-mirror 0.69 disagreement; ORACLE BC 378.7); "MODQN collapses" (lr-dependent).

### C-20. Margin-OFF / RLPD-style demo replay (keep demos in replay at ρ=0.30, drop margin, pretrain, L2) (old label: MOFF, `fulldqfd_MOFF_lr001`; INJ-RUNG1 C0 precedent)
- mechanism: expose the TD learner to expert transitions without any imitation pressure, so Q is never pinned to the teacher ("the genuine 'raise beyond the teacher' lever", CATFISH-DQFD-EE-BACKLOG:51-52).
- intervention point: experience
- defined in: CV2/CLOSURE-PREREG-2026-07-18.md:47-85 (Exp-2).
- run status: ran, 6 seeds × 12000 ep, lr 1e-3, F-mean schema-v2 pool.
- run conditions: argmax + concat-z 448, γ [0,.9,.9], from scratch, comparator OFF 523.78 reused.
- recorded outcome: "**HURTS**: −42.25, 5/6 seeds" (481.53 vs 523.78); "Demos from a joint teacher hurt EVEN AS PURE REPLAY DATA ... ON−MOFF ≈ −41 (imitation-pressure share) and MOFF−OFF ≈ −42 (data-distribution share)" (CV2/CLOSURE-EXP2-MOFF-RESULT-2026-07-18.md:8-35). Earlier precedent INJ-RUNG1 C0 (07-11): same-pool margin-OFF ρ=0.3, n=5, C0−A=+0.58 p=.942 "clean adverse precedent (non-separated, n=5)" at k_c=1 coordinated-decode endpoint, 3000 ep (RECHECK-VERDICT:33-36, 134-139). LATEST: injection route "SOLID" harmful on this substrate; "SIL / margin-off 自我刺激 — underpowered (power ≈0.11) — 未排除(不得併入 SOLID)" (EXP-ACRM-OPPORTUNITY-FINAL-REPORT:25-26) — i.e. the self-stimulation variant is not closed.
- recorded cause: off-manifold/OOD transitions; "z-score non-stationarity; conflicting-gradient averaging" (blind-review hypotheses, CLOSURE-EXP2:32-34).
- premises: same as C-19 minus the imitation term.

### C-21. Teacher matrix — swap the injection teacher to the de-clairvoyant ORACLE (local search, 681.8) or the handover-aware static G (596.0), margin-ON and margin-OFF (ORON / ORMOFF / GON / GMOFF)
- mechanism: better or more obs-compatible teacher for C-19/C-20.
- intervention point: experience (teacher identity)
- defined in: CV2/CLOSURE-AMENDMENT-TEACHER-MATRIX-2026-07-18.md; pools `D_oracle_declair_all_kc1.npz`, `D_g_handover_all_kc1.npz`; de-clairvoyant oracle FBCD/CATFISH-VS-DQFD-DESIGN-2026-07-15.md §11 (681.81 eval, clairvoyance premium only 12.53 EE).
- run status: **built, launched, never completed** — 24 teacher arms killed/SIGSTOP'd ("SIGSTOP'd (teacher×24, OFFCC×6, pilot-M4×3)", ABLATION-SPEC-9000EP:77; "24 KILLED teacher arms' harmless SCORE-FAILs", CLOSURE-B4:26-28). No score found.
- recorded outcome: none. Adverse witness: ORACLE-pool BC bar 378.7 (k10) / 341.9 (k5) vs F-mean 475.3 — "LOWERS the margin-ON ORACLE-teacher prior" but "does NOT isolate joint-information dependence" (CONVERGE-PROBE-RESULT:54-63).
- premises: "teacher's action expressible from obs_u"; "a better-than-learner teacher exists" (TRUE).

### C-22. Faithful CDRL Phase-1 seeding of the catfish replay from an external solver (+ margin on the catfish conduit as the "discrete-transfer fix"); 5-arm design A1/A2/B1/B2/D1
- mechanism: pre-fill the catfish replay with solver "exemplary solution cases" (as CDRL's DFT+WMMSE+argmax-EE Phase-1), then run M1/M2/M3 (+ACRM); B2 adds DQfD margin to the conduit because with a discrete 28-action argmax "the OTHER 27 actions NEVER RECEIVE A GRADIENT" without a supervision term.
- intervention point: experience (seeded catfish buffer) + penalty/loss (margin in conduit)
- defined in: FBCD/CATFISH-VS-DQFD-DESIGN-2026-07-15.md:51-178, 227-236 (build list: `catfish_faithful.phase1_pool` key ~20–50 lines).
- run status: **never built/run** — later records: SCFZA "no Phase-1 oracle dataprep — that faithfulness gap remains disclosed" (CLOSURE-B4:51-52); EP2K "still lacks the paper's Phase-1 external-expert seeding, so the published form remains untested here" (EP2K-RESULT:214-216).
- recorded outcome: none. Design doc's own prior: "In our env, CDRL likely reduces in practice to 'DQfD with a stochastic intervention schedule, an asymmetric γ, and no margin'" because catfish would have to exceed a 636–694 solver (l.86-90). The "27 actions never receive a gradient" measurement was at lr=0.01 (offline B2 distinct 1.0 / P2) and online C4m distinct 4.5–4.8 (l.116-123) — [I] contaminated by the lr=0.01 collapse attractor (see C-18).
- premises: "a better-than-learner teacher exists" (TRUE); "demos help a per-user argmax learner" (contradicted by C-19/C-20 at healthy lr).

### C-23. Context normalization of the observation across users (live z-score over the 100 users per step; "concat-448" = [raw ‖ z(raw)])  (old labels: z-score, IS line, `shared_q_isolation.form: concat`, "正規化 MODQN", L2)
- mechanism: per-feature standardization over the user population at each step (Context Normalization / InstanceNorm on the user axis), concatenated with raw; makes the numerically invisible load block (0.05 % L2 energy vs SNR 97.6 %) visible and provides a population-relative symmetry-breaker.
- intervention point: representation
- defined in: `shared_q_isolation/standardize.py:25-43`; prior-art CV2/ZSCORE-PRIOR-ART-CARD-2026-07-18.md; rationale CATFISH-REDESIGN-BRIEF-2026-07-14.md:59-68, 152-168.
- run status: ran many times — wave-E 3-way (concat/raw/width) 6 seeds × 9000 ep; abl9k L1 vs L2 6 × 9000; ep2000 Q7; CLOSURE-AMENDMENT-ZABLATION (RAW224/WIDTH at 12000 ep, queued last — no result found in this cluster).
- run conditions: lr 1e-3 (wave-E, abl9k, ep2k); earlier IS-v3 (07-12) at lr 0.01 [I].
- recorded outcome: wave-E: concat 523.78 vs raw 495.89 (+27.88, CI [−20.86,+76.63], 5/6 — "crosses zero") vs width 402.90 — "`[raw ‖ raw]` is not a neutral width match" (collinearity), retracting "the z-score effect is REAL" (ZSCORE-3WAY-FINDINGS-2026-07-17.md:12-68). abl9k: L2−L1 **+56.54** [+30.7,+82.4] 6/6 — renamed "**representation increment (L2−L1)** — the frozen correction bars pure z-score attribution (concat/width increment)" (ABL9K-RESULT:36, 76-77). ep2000 Q7 CREDITED +182.18 (undertraining-inflated). LR file: "z-score *helps* but does not prevent the collapse; lr is the controlling variable" (l.66-68). Group A: "z-score is NOT sufficient to prevent collapse — the learning rate is" (FULLDQFD-GROUPA-RESULT:117-121). Live→frozen drop on arms +22…+33 EE vs lookup −47.97 (l.137-139).
- recorded cause: brief's C-2 hypothesis "the load feature is NUMERICALLY INVISIBLE. zscore ... equalises the scales" — X-2 per-block ablation to test it was proposed, not found run.
- open USER boundary: "the z-score is a CROSS-USER operation at inference ... 'Part of the IS line's 146.6 → 357.1 may be a SMUGGLED COORDINATION GAIN' ... NO SUCH RULING EXISTS" (CATFISH-VS-DQFD-DESIGN:244-249); later adopted everywhere (V2-COMPLETENESS-CHECK:84-85).
- premises: "per-user obs carries a symmetry-breaker if scaled"; population statistics are broadcastable at deployment.

### C-24. Centralized auction decode on the trained Q (price of the decoder exit)
- mechanism: run the coordinated facility-location/auction decode over the trained OFF Q-heads instead of per-user argmax.
- intervention point: decode/deployment
- defined in: CV2/CENTRAL-DECODE-RESULT-2026-07-18.md.
- run status: ran (eval-only, 6 seeds, converge-probe OFF ckpts, lr 1e-3/12000).
- recorded outcome: argmax 523.78 → auction 545.55 (+21.77, 5/6); auction serves 1.000 with cap_bump 0; "~86% of the joint gap is NOT recoverable from the current Q by a better endpoint"; "delta anti-correlates with Q quality ... a feasibility floor, not an intelligence amplifier" (l.18-33). Earlier (07-15, lr=0.01-era arms) "THE DECODER COMPRESSES DQfD's EFFECT 7.5×" — **de-rated as single-seed artifact** (CATFISH-VS-DQFD-DESIGN:14-28). Decoder exited by USER decision 07-15 (constraint, not number).
- premises: centralized decode permitted (FORBIDDEN in the thesis line after 07-15).

### C-25. Paper-design pivot (absolute "common-seven" action catalog + paper-r3 Eq11 × z) and the homog-vs-spread falsifier
- mechanism: switch from relative (per-user slot) action labels to an absolute common action catalog so shared-Q label homogenization maps to physical crowding; paper-r3 with idle beams at 0.
- intervention point: other (action-space/env contract) + reward (r3 variant)
- defined in: CV2/PAPER-DESIGN-PIVOT-PREMISE-G6-PACKET-2026-07-18.md (not read); verdict CV2/PAPER-DESIGN-PIVOT-G6-MERGED-VERDICT-2026-07-18.md; falsifier CV2/HOMOG-VS-SPREAD-RESULT-2026-07-18.md.
- run status: pivot **never built** (unanimous 3-model "do NOT spend the big build"); homog-vs-spread probe ran (24 matched states, zero training).
- recorded outcome: probe: RELATIVE catalog spread vs homog — qos +58.9 pp, throughput 4.95×, eff_N 4×, 23/24 states; training r1 spread_rr ×1.81, spread_concentrate ×3.63 (24/24) ⟹ "The load-bearing premise ... 'the relative action env has a FLAT reward landscape' — is FALSIFIED"; "Spreading pays = disperse across **satellites**, concentrate to ≤k_cap **within** a satellite" (HOMOG-VS-SPREAD-RESULT:8-56). Pivot verdict: "REVISE / NO-GO on the big build. Do the cheap screens first" (l.92-97); paper-r3 "has no honest calibration" (l.21-26).
- recorded cause (RECHECK-VERDICT:59-79): collapse is "MIXED-mechanism — avoiding *naive* spread has an incentive-shaped component (γ-amplified r3 ...), while the failure to reach *concentrate-type* spread ... remains a learnability/representation failure" — note this pre-dates the 07-20 LR finding.
- premises: "collapse exists" (lr-dependent); "spread raises EE" (true in family_b; see physics block).

### C-26. Matched γ3 = 0 vs 0.9 ablation / corrected-r3 (Jain-style, idle-aware) as the direct test of reward-shaped collapse
- mechanism: remove the γ-amplification of the perverse legacy r3 (max−min over active beams) or replace r3 with an idle-aware corrected form.
- intervention point: objective/reward
- defined in: R3-DISCOUNTED-RESULT-2026-07-14.md (§ prescribing matched γ3 test, l.112 per RECHECK); RECHECK-VERDICT-2026-07-18.md:21-26 ("The most causally-targeted next test is a matched γ3 = 0 vs 0.9 (or corrected-r3) arm"); corrected-r3 substrate `family_b_r3/` (landed `12eb979a`).
- run status: **never run** on the concat line — corrected-r3 dispatch "G6 DO-NOT-LAUNCH"; "r3 = legacy, PERMANENTLY for the 定稿 plan" (V2-COMPLETENESS-CHECK:73-77). Separate asym-discount arm L10 (`abl9k_full_symgamma`, catfish γ pair) is not this.
- premises: "reward partly rewards collapse" (discounted sign UNRESOLVED at n=6).

### C-27. Coordinator Catfish (training-only coalition proposals executed on a deep-copied auxiliary env; dedicated replay; deployment stays per-user argmax) (old labels: CWRC, R_COORDINATOR, OFFCC, coord_catfish)
- mechanism: an auxiliary "catfish" proposes small user coalitions whose JOINT move is positive although every singleton move is non-positive ("singleton-negative coalition", admission gain +1), executes them only on a forked env, and feeds those joint transitions to main through a separate replay (CTDE-style, training only).
- intervention point: experience (joint/coalition-derived transitions)
- defined in: `src/modqn_paper_reproduction/coordinator_catfish/` (+ `r3_adapter.py`); CV2/PRE-R3-COORDINATOR-CATFISH-READINESS-RESULT-2026-07-16.md; CV2/POST-R3-COORDINATOR-CATFISH-TRAINER-INTEGRATION-SMOKE-RESULT-2026-07-17.md.
- run status: built readiness-only (21 + 43 tests pass, smoke on real corrected-r3 stack); OFFCC 6-seed training arm launched on server, then **SIGSTOP'd with the frozen queue** (ABLATION-SPEC-9000EP:77; HANDOFF-2026-07-20-EP2K-COMPLETE:74-76 "33 SIGSTOP'd runners ... must stay that way"). No result in this cluster. Backlog: "coordinator-catfish (training-only CTDE, never actually wired/run)" (CATFISH-DQFD-EE-BACKLOG:76-78).
- run conditions (planned): OFF substrate, lr 1e-3; corrected-r3 base-140 for the adapter smoke.
- recorded outcome: none ("EE effect, and novelty remain untested", PRE-R3 l.43-45).
- premises: "equilibrium/anti-congestion information must be injected" (the 07-14 lens); "coordinated joint transitions are learnable by a per-user Q" (contradicted-leaning by C-19 label-noise reading); relies on the hard k_cap congestion game.

### C-28. Per-user best-response ceiling probe / "obs_u-restricted gate" / exact min-cost-flow re-pairing bound (instruments)
- mechanism: measure headroom above the trained policy — unilateral BR (Exp-1); proposed true gate = frozen obs_u-constrained learner/oracle in a SIMULTANEOUS joint rollout; exact assignment with beam quotas for the nullspace.
- intervention point: other (diagnostic instruments)
- defined in: CV2/CLOSURE-PREREG-2026-07-18.md:10-45; CV2/CLOSURE-EXP1-CEILING-RESULT-2026-07-18.md; EXP-ACRM-OPPORTUNITY-FINAL-REPORT:45-46.
- run status: Exp-1 ran (6 OFF ckpts, 720 samples); obs_u gate and min-cost-flow **never run** ("便宜(無訓練)", listed as the decisive future-work instrument).
- recorded outcome: H_BR +97.2 % (+82.1 % on base>0) → PER-USER-OPEN; codex BLOCKER: "a **LOCAL-INCENTIVE SCREEN, not a policy-class ceiling gate**" (CLOSURE-EXP1:3-11); "mean BR eta ... EXCEEDS the joint feasible ceiling (ORACLE_LB ≈ 694) — everyone cannot take their BR simultaneously" (l.41-45).
- premises: none (instrument). [I] Useful for the new project as a cheap pre-screen before any teacher/injection concept.

### C-29. Objective-based (cost-sensitive) imitation loss instead of action-regression BC
- mechanism: train the per-user map on the objective (EE regret) rather than top-1 action match, because a capacitated joint assignment has massively non-unique optima.
- intervention point: penalty/loss
- defined in: FBCD/CATFISH-VS-DQFD-DESIGN-2026-07-15.md:281-300 (§9.2: "THE BETTER IMITATOR SCORES WORSE" — kNN raw top-1 0.837 → EE 421.4; kNN z top-1 0.712 → EE 475.3; cite Ross & Bagnell 2010, Amos amortized optimization).
- run status: **never built**.
- premises: "a better-than-learner teacher exists"; "imitation accuracy is not monotone in EE".
- related record: "EE = −674 · cap_bump + 601 · r = −0.972 · R² = 0.945" over 25 measured arms — "94.5 % OF EVERY NUMBER IN THIS LADDER IS ONE VARIABLE: HOW MANY USERS THE k_cap RANK-CUT DROPPED" (CATFISH-VS-DQFD-DESIGN:258-279); "the right argmax_distinct is ≈ 12 — the k_cap budget" (BC clones over-spread at 18–23). [I] This is the strongest recorded explanation of why C-1 (capacity penalty) dominates: the scored EE is ~a linear function of cap_bump on this env.
- UID revision: §9.5 (l.332) **"a per-user UID / SePS embedding — DO NOT"** — users are exchangeable and "expressivity is already proven sufficient (§9.3)" via leak-pool BC reproducing 636.05 exactly — this **supersedes C-16's "UID becomes a PREREQUISITE"** reading.

### C-30. FIX-N (write true pre-admission demand N(t) into the state's beam_loads) and χ-occupancy rescaling (÷k_cap or standardize the occupancy channel)
- mechanism: give / make readable the congestion signal in obs_u so a per-user Q can avoid crowded beams.
- intervention point: representation
- defined in: PAPER-RESTORE-PREREG-2026-07-15.md (not read; FIX-N); verdict FBCD/PAPER-RESTORE-G6-VERDICT-2026-07-15.md; FBCD/CHI-ABLATION-RESULT-2026-07-15.md.
- run status: FIX-N **never run** (prereg NOT-SOUND 3-lane unanimous; "FIX-N doesn't even compile" l.97); χ-ablation probe ran (eval-only, 6 `waveE_OFF_raw` ckpts, lr 1e-3/9000); χ-rescale retrain **never run**.
- recorded outcome: "FIX-N is a near-no-op, because the information is ALREADY in the state" — χ[·,·,0] = true pre-admission demand (PAPER-RESTORE-G6:19-40); χ-ablation: zeroing the demand feature moves argmax_distinct by −0.043 (CI [−0.178,+0.120]) ⟹ "the net had the congestion info and BARELY USED it" — "REPRESENTATION / SCALE problem ... ~1/559 of the SNR block's magnitude" (CHI-ABLATION:40-53). LATEST: "χ-scale = DEPRIORITIZED (wrong axis: collapse is on the satellite, χ is cell-load), NOT refuted" (CONTRIBUTION-LINE-HANDOFF:71).
- premises: "collapse exists" (lr-dependent); "the congestion signal is present but unreadable".

### C-31. RSS_max zero-learning control / satellite-axis collapse diagnosis (class-A vs class-B root)
- mechanism: score the paper's own RSS_max (argmax channel quality) rule — no learning — to test whether the collapse is learning-caused.
- intervention point: other (diagnostic control)
- defined in: PAPER-RESTORE-G6-VERDICT-2026-07-15.md:42-86.
- run status: ran (zero training).
- recorded outcome: RSS_max distinct 7.97, n_sats 1.53, lit_beams 4.06 vs trained MODQN 1.00/1.00/3.00 vs RANDOM 12 lit beams ⟹ at the time: "class (A) — reward (all three), calibration, DQN, Adam, **lr**, tanh, the episode budget, ε-greedy, replay ... — is REFUTED AS THE ROOT, EN BLOC ... learning is an AGGRAVATOR" (l.42-57); satellite preference unanimous (sat 0 best for 100/100 users), `beam_offsets` (40 % of base state) byte-identical across satellite slot-groups. Softened same day: "class-A REFUTED en bloc is an OVER-CLAIM ... it is 'class-A NOT NECESSARY as root'" (CONTRIBUTION-LINE-HANDOFF:68-70). **Contradicted for the learned policy by COLLAPSE-ROOT-CAUSE-IS-LR (07-20)**: at lr=1e-3 the trained MODQN does NOT collapse (the "trained MODQN (paper r1) distinct 1.00" row here is a lr=0.01-era run per defect (a) l.92). Also defect (c): "`active_beam_count` / `argmax_distinct` count distinct ACTIONS (ceiling 28), not physical beams (ceiling 12) ... The thesis 'de-collapse 3→12' narrative is pinned to a ceiling-28 metric" (l.94).
- premises: n/a (control). [I] For transfer: the satellite-tie mechanism (4 satellites blanketing a small box, identical offsets) is a geometry property of family_b.

### C-32. Contribution-ideation menu (07-15): CCF active coded probing (catfish window creates per-user causal fingerprint), posted-price gate (defer if opportunity-cost margin < learned load-conditioned price), ISJ per-user scalarization-weight jitter, disagreement-seeded catfish (demos from states where the 3 heads' argmaxes disagree), MSDE temporal desync (user acts only when t mod K = hash(u) mod K)
- mechanism: decentralized per-user symmetry breaking; frame: "Identical observation + shared DETERMINISTIC policy ⟹ necessarily identical action" (CONTRIBUTION-IDEATION-2026-07-15.md:15-24).
- intervention point: CCF exploration/representation; posted-price decode/deployment; ISJ objective (scalarization) at deployment; disagreement-seeded experience; MSDE other (interaction protocol)
- defined in: FBCD/CONTRIBUTION-IDEATION-2026-07-15.md:28-37.
- run status: **never built**; one premise screen ran (single seed, 12 ep, "bad-r3 substrate", on the decoded trajectory).
- recorded outcome: P1/P2 survive (env-optimal heads disagree a1≠a3 = 0.87–0.93; ~43 distinct head-argmax triples / 100 users); **P3 REFUTED as de-collapse exploit**: trained+decoded policy already at 11.6/12 active beams, served 0.89; head-union routing adds only 1.02–1.20× beams and k_cap starves spreading ("served collapses 0.89 → 0.47") ⟹ "'de-collapse by per-user spreading' has ≈0 headroom (saturated) AND costs served-fraction" (l.67-91). Surviving hypotheses: disagreement as TRAINING/catfish-replay seeding signal; load-balance with served-fraction + EE guard (CONTRIBUTION-LINE-HANDOFF:51-58).
- premises: "collapse exists"; "users are heterogeneous at collapse" (passive ideas); per-satellite k_cap starvation.
