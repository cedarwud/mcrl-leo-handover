# Harvest part B — catfish-v2, early July (2026-07-08 .. 07-12) + prior-art cards

Extractor: read-only worker (2026-09-11). Old project root = `/home/u24/papers/modqn-paper-reproduction` (abbrev `OLD/`).
Cluster dir = `OLD/analysis/family-b-collapse-diagnosis/catfish-v2/` (abbrev `CV2/`); top-level dir = `OLD/analysis/family-b-collapse-diagnosis/` (abbrev `FBD/`).
Convention: "SAY" = records state it; "[I]" = my inference. Every quote is copied verbatim from the cited file.

## 0. Shared run conditions (apply to every trained arm below unless an entry overrides)

- **Base training protocol (single-sourced by every catfish-v2 retrain via `base_prereg`)**:
  `OLD/docs/research/env-foundation/retrain-prereg-family-b-w503020-C1FIXED.json` — `"learning_rate": 0.01` (line 95),
  `"discount_factor": 0.9`, `"episodes": 3000`, batch 128, hidden [100,50,50] tanh, replay 50000, target update every 50 ep,
  ε 1.0→0.01 linear over 2000 ep, `objective_weights [0.5,0.3,0.2]`, reward calibration divide-by-fixed-scales
  r1 2.532105322e11 / r2 300.31625 / r3 6.13191542189837e9 ("C1FIXED" = era E3). **So lr = 0.01 for every catfish-v2 trained arm** (SAY: the prereg; the catfish-v2 yamls add no lr override — `CV2/configs/*.yaml`, `CV2/A2_ee_*.yaml`).
- **Env**: `family_b` (Walker constellation geometry, 10-step episodes, U=100 users). Physics per base prereg `d3_prereg_record`:
  "frozen D2c-concave power x D4 B/3 x D5 TDM combination"; r1 = `angle_aware_ee` via `slot_power_w` ("NO ÷G_T" after the 07-04 fix);
  r2 = `_handover_penalty(prev,cur)` (a per-transition switching cost, per GAMMA-PREMISE verdict); r3 = load-balance. Beam cap k_cap(=v_max)=3.
  Base prereg records "the link-level EE gradient pushes NEAR-SATELLITE CONCENTRATION (max-eta-proxy slot = slot-0 nearest 95.0%)".
  No handover energy term in r1 is recorded for family_b [I: the switching-cost C3 probe (B-8) was the proposal to add one].
  Gate-0 config (`CV2/GATE-PLAN.md`): "U=100: k_cap(v_max)=3, l_w=4, steps/ep=10, A=28, C=59, P_BASE=0.25, P_MAX=10.0".
  **Power model / load dependence** (quoted in `CV2/C3-GAP-REACH-PREREG-2026-07-12.md:115-125`, citing the 07-13 EE-LOAD-DEPENDENCE probe):
  "`beam_power_w(L) = min(0.25 + 0.35·√L, 10.0)` (`family_b_geometry.py:374`)"; per-user EE = B·log2(1+SINR)/power_beam, and "EE *PENALISES* load"
  (load 1→40 ⇒ EE 1.000×→0.350×); cap-bumped users get r1 = 0 ("Collapse is punished by EXCLUSION"). Reset starts every episode with all users on
  action 0 and step-1 handover is charged against that artificial start (B-11). No off-axis beam-gain term is discussed in these records beyond
  "angle_aware_ee" naming; the ÷G_T (transmit-gain) division was removed from r1 on 2026-07-04 (E1→E2 boundary).
- **Wiring**: every trained arm below is **trained from scratch** (3000 ep) with catfish/injection co-trained; NONE is a
  distillation of a frozen pre-trained main over a few rounds. Exceptions (frozen teacher → replay pool) are noted per entry.
- **Decode eras** (`FBD/EVIDENCE-USABILITY-2026-07-10.md`): `decode_hybrid_auction` = F5-leaky (opens >k_c on ~10% slot-events; defect `D5`);
  `decode_hybrid_corrected` = strict ≤k_c. Arms trained through the leaky decode cannot be re-scored clean.
- **Metric conventions**: "EE" in catfish-v2 = `family_b_eta_r1`/1e6 averaged over users/steps. Verified in the scorer
  (`CV2/score_inj_rung1.py:135-140`): `r1 = np.array([family_b_eta_r1(res, env, u) for u in range(U)])`, `row["r1"] = np.mean(r1)`,
  then mean over steps/episodes ⇒ a **mean over users of per-user ratios R_u/p_alloc,u, unserved users counted as 0** — a mean-of-ratios,
  NOT pooled ΣR/ΣP. [I: the July-era `family_b_eta_r1` was the per-user η; in today's tree it is aliased to a later
  `family_b_system_ee_contribution` (`src/.../family_b_recalibration.py:135-143`) — a post-July change, out of this cluster.] `J_w` = calibrated weighted scalar
  Σ w_i r_i / scale_i. `min_cov` = min over users of the fraction of steps served (COUNT/48 or fraction — a unit bug was found, see B-12).
- **Trainer defect (per-head bootstrap) — recorded explicitly**: `CV2/EE-CATFISH-PREREG-2026-07-08.md:31-33`: "MODQN bootstraps each
  head's max independently (`qᵢ = rᵢ + γᵢ·maxₐ' qᵢ`, trainer.py:181), so the decoded `Σwᵢqᵢ` over-estimates the achievable scalar
  return vs DQN_scalar's **joint** `maxₐ' Σwᵢqᵢ`. Catfish (γ / stratify / ACRM) keeps the per-head architecture → it **does not
  touch that structural bias**." Present in every MODQN-based arm in this cluster.
- **Outage free-ride**: base prereg line ~60: "cap-bumped/mask-invalid assigned slot => slot_power_w 0.0 => eta = 0.0" (r1=0 when unserved).
  Records in this cluster do NOT discuss whether r2/r3 are also 0 when unserved [I: not addressed here].
- **Uncalibrated logged scalar**: base prereg: "calibration applies ONLY at replay push … EpisodeLog r*_mean, eval metrics, and ckpt
  selection stay RAW" — i.e. the best-ckpt selector (`best-weighted-reward-on-eval.pt`) is chosen on a RAW weighted reward
  [I: raw r1 ~1e8 dominates r2 ~0.1, so ckpt selection is effectively EE-driven; later cluster files BEST-VS-FINAL-CKPT-RESULT.json (07-12) probe this].
- **Era defects** (`FBD/EVIDENCE-USABILITY-2026-07-10.md:30-31`): E1 (<07-04) r1=`R·G_T/p` wrong quantity (`D2a`); E2 (07-05/06) stale c1=2.34e15
  → EE=0.009% of objective (`D2b`); E3 `_C1FIXED` normal. All catfish-v2 trained arms are E3 unless noted.

## 1. Concept entries

### B-1. Abstracted "Multi-Catfish" route-B catfish, LB-tuned (old label: A2 / `A2_hybrid_k1_w503020_C1FIXED`, "A2_LB")
- mechanism (one line): single agent; value-stratified replay prioritised on the calibrated J_w (λ=0.5, ρ=0.25) + asymmetric per-head discount γ=[0.90,0.90,0.99] (long horizon on the load-balance head r3).
- intervention point: experience (replay priority) + objective (per-head γ)
- defined in: `CV2/EE-CATFISH-PREREG-v2-stratify-2026-07-08.md:53-57` (arm table); config in `route_b_factorial`; `FBD/EVIDENCE-USABILITY-2026-07-10.md` rows CF-1..CF-6.
- run status: ran (reference arm reused; 3 seeds {42,137,271}, 3000 ep); earlier also thesis Table 5-2 route-B factorial (n=3/arm, E1 era).
- run conditions: family_b; hybrid decode k_c=1 **trained through the F5-leaky `decode_hybrid_auction`** (defect D5; CF-5); E3 C1FIXED scales; lr 0.01 (base prereg); from scratch; scored 48-ep at k_c=1 through `decode_hybrid_corrected`, EE=`family_b_eta_r1`/1e6, w=[0.5,0.3,0.2]; 224-d augmented state (χ_u).
- recorded outcome: `CV2/EE-CATFISH-STRATIFY-RESULT.CORRECTED-DECODE.json` A2_LB seed-mean EE 413.0 vs A1 399.8 vs AF 448.3 (min_cov_frac 0.944 vs 0.917). LATEST: "de-collapse min_cov 0↔>0; A2≈A1 (catfish decorative) = fair readings" (`FBD/EVIDENCE-USABILITY-2026-07-10.md` CF-6); "A2 − A1 = −3.0%" harm claim **RETRACTED → "not separated from zero"** (CF-2).
- recorded cause (quote): "On family_b it is currently **decorative on EE** (A2≈A1) because it is **LB-tuned** (`gamma_per_objective=[0.90,0.90,0.99]` = long horizon on the LB/r3 head; stratify on J_w)" (`CV2/EE-CATFISH-PREREG-2026-07-08.md:9-11`). Later: "high γ on **r3 / load-balance** … `r1` and `r3` are **per-step separable** … γ on them *is* inert, correctly" (`CV2/GAMMA-INERTNESS-PREMISE-FALSIFIED-2026-07-09.md:71-74`).
- inferred cause [I]: coordinated decode at k_c=1 does most of the work (DL-2: "coordination (not the MO reward) rescues coverage"), so any Q-side change is washed out; plus per-head bootstrap bias untouched.
- premises: collapse exists under per-user argmax; long-horizon credit on a coupled head matters; stratified replay improves the relevant head's fit.

### B-2. EE-pointed γ (old label: `A2_eeG`, "catfish γ→EE")
- mechanism: same abstracted catfish but γ=[0.99,0.90,0.90] (long horizon on the EE head r1), stratify still on J_w.
- intervention point: objective (per-head discount)
- defined in: `CV2/EE-CATFISH-PREREG-v2-stratify-2026-07-08.md:57-59` (demoted to CONTROL); `CV2/A2_ee_g_hybrid_k1_w503020_C1FIXED.yaml`.
- run status: ran (3 seeds {42,137,271}, 3000 ep).
- run conditions: family_b; hybrid k_c=1, **trained through F5-leaky decode** (D5); E3; lr 0.01; from scratch; scored corrected decode k_c=1, 48 ep; EE per-user `family_b_eta_r1`/1e6.
- recorded outcome: corrected-decode re-score EE per seed [403.7, 410.7, 443.3], mean 419.2 vs A1 399.8 (A1 per seed [379.1, 430.4, 389.8]) → not seed-separated (`CV2/EE-CATFISH-STRATIFY-RESULT.CORRECTED-DECODE.json`). Prereg treated it as "cheap **CONTROL** (predicted ≈A1 → confirms γ-inert)". LATEST: no dedicated verdict file for eeG; CF-8 row covers the P3 pair as "underpowered null".
- recorded cause: original: "γ does not change the argmax / the policy. Therefore **γ→EE (`A2_eeG`) is predicted-NULL**" (`…v2-stratify…:44-46`). REVISED: the "s' ⊥ a" premise is **false** (a_{t-1} is in the state via `access_vector`; r2 is a switching cost), but r1 is per-step separable so γ on r1 stays inert "correctly" (`CV2/GAMMA-INERTNESS-PREMISE-FALSIFIED-2026-07-09.md:48-49,71-74`; `CV2/GAMMA-PREMISE-G6-VERDICT-2026-07-09.md`).
- premises: EE reward has an inter-step coupling a long horizon can exploit (records say it does NOT for r1 on family_b).

### B-3. Value-stratified replay pointed at EE (old label: `A2_eeGS`, "stratify→EE", P3)
- mechanism: replay priority_value = calibrated r1 (EE) instead of J_w (`trainer.py` patch `priority_axis: ee`), plus γ→EE; oversample high-EE transitions to improve EE-head fit.
- intervention point: experience (replay sampling)
- defined in: `CV2/EE-CATFISH-PREREG-v2-stratify-2026-07-08.md:40-50,96-101`; `CV2/A2_ee_gs_hybrid_k1_w503020_C1FIXED.yaml` (`value_stratified: {enabled: true, lambda: 0.5, rho: 0.25, priority_axis: ee}`).
- run status: ran (3 seeds {42,137,271}, 3000 ep).
- run conditions: family_b; hybrid k_c=1 trained through F5-leaky decode (D5); E3; lr 0.01; from scratch; first scored through the WRONG (leaky) decode, re-scored corrected; EE per-user mean; PRIMARY = min-seed separation AND coverage not materially below A1.
- recorded outcome: "Re-scored with corrected decode → **conclusion survives** (A2_eeGS − A1 per-seed ΔEE=[+61.1,−19.9,+14.4], min −19.9 → still NOT-DEMONSTRATED) but ABSOLUTE numbers shift … decode shift is **per-arm (not a constant offset)** → cross-arm ordering CAN flip" (`CV2/SESSION-2026-07-09-INJECTION-FAIL-ENVDIR-ROOTQ-VERDICT.md:37`). LATEST: CF-8 "**NOT-DEMONSTRATED** (min ΔEE −19.9 …) … MAY close nothing on catfish effect (underpowered n=3)" (`FBD/EVIDENCE-USABILITY-2026-07-10.md`).
- recorded cause: prereg honest prior "it improves the EE-head's fit, but does **not** touch the §2-structural per-head bootstrap bias" (`…v2-stratify…:83-86`); session verdict: "shared `family_b` myopic-sufficiency + k_c=1 decode washing out learned-Q" (`SESSION-2026-07-09…:21`).
- inferred cause [I]: n=3 with ±40 per-seed spread ≫ effect; trained through leaky decode; lr=0.01 (later root-cause blamed) not varied.
- premises: EE head is under-fit and replay re-weighting can fix it; learned Q changes decode outcome.

### B-4. ACRM→EE competitive reward (old label: `A2_eeGSA`, ACRM rung)
- mechanism: "competitive reward, Eq 4.8/4.9 linear" on r1 using a same-state main-greedy counterfactual η (dual/self-rollout recomputing what the main-greedy action would earn) to form a competitive advantage.
- intervention point: reward
- defined in: `CV2/EE-CATFISH-PREREG-v2-stratify-2026-07-08.md:103-110` ("ACRM is a **hard `NotImplementedError` guarded stub** (`trainer.py:59`)").
- run status: never built (route-B stub; faithful line has `counterfactual_eta` "ACRM-only+UNTESTED", `CV2/FAITHFUL-AUGMENTED-CORRECTED-SDD-2026-07-09.md:76`).
- run conditions: n/a. Would need "(a) implement the counterfactual EE rollout, (b) the linear competitive reward on r1, (c) a non-degeneracy gate (… r2/r3 competitive semantics + degeneracy risk)".
- recorded outcome: none. Session verdict cites CDRL's own ablation: "asymmetric-γ = #1 lever, competitive-reward (ACRM) = LAST" (`SESSION-2026-07-09…:55`).
- premises: a counterfactual main-greedy baseline exists per state; competitive advantage signal adds information beyond r1.

### B-5. Faithful CDRL catfish on the plain per-user-argmax base (old label: P1, `A2_faithfulcatfish_w503020_C1FIXED`, "faithful-full")
- mechanism: separate catfish DQN + dual self-rollout (catfish steps its own env with its own policy) + M1 hard 20/50/discard EE-stratification into the catfish pool + M3 70/30 periodic-intervention conduit into main; γ_cf 0.99 vs γ_main 0.9; ACRM OFF.
- intervention point: experience (second agent's experience injected into main replay)
- defined in: `CV2/configs/A2_faithfulcatfish_w503020_C1FIXED.yaml`; `CV2/FAITHFUL-CATFISH-EFFECT-VERDICT-2026-07-08.md`; prereg `CV2/PREREG-FAITHFUL-CATFISH-EFFECT-2026-07-08.json`.
- run status: ran (2 arms × 3 seeds {42,137,271}, 3000 ep, ~59 min CPU).
- run conditions: family_b; base 140-d state; **per-user argmax decode both train and eval**; E3 C1FIXED; lr 0.01 (base prereg); γ_main 0.9; from scratch (catfish co-trained, not distilled); metric = calibrated J_w (PRIMARY), per-objective raw r_i SECONDARY; ckpt `best-weighted-reward-on-eval.pt` (selected on RAW weighted reward).
- recorded outcome: "paired Δ = A2 − A1 on J_w … mean **−1.983e-04** … 3/3 seeds negative … proper **t-CI(n=3) = [−8.20e-04, +4.23e-04] STRADDLES 0** → honest read = **null-to-negative**, NOT 'catfish harms'"; "Catfish delivers NO robust EE (r1) gain — EE up on only seed137 … bought by a **handover collapse** (Δr2 = −0.458 on seed137) … catfish spreads beams more, active ~6.4 vs ~4.8 → more churn). min_coverage = 0 on all 6" (`CV2/FAITHFUL-CATFISH-EFFECT-VERDICT-2026-07-08.md:21-44`). G6 SOUND-WITH-FIXES ×2. LATEST: EVIDENCE-USABILITY forbids "the faithful catfish does not work"; SESSION-07-09 lists it as convergent negative #1.
- recorded cause: "evidence the **env is myopic-sufficient** … NOT that a better catfish is needed" (`…VERDICT…:63-69`) — this causal story rests on the γ-inertness premise later FALSIFIED (`CV2/GAMMA-PREMISE-G6-VERDICT-2026-07-09.md` §7.2: "its **OBSERVATION** … is untouched; its **CAUSAL STORY** is wrong").
- later recorded fact (`CV2/TRAINING-DIVERGES-FINDING-2026-07-12.md:31-32`): best-checkpoint episode for `A2_faithfulcatfish` = "99 / 99 / 99 | **3% / 3% / 3%**" and for `A1_plain_faithful` = "349 / 199 / **99**" — i.e. the scored policies are from the first 3–12% of training (ε still ≈0.9+). Marking doc: "一隻沒有任何優勢的挑戰者，它的 70/30 導管注入的是 on-policy 資料，必然是 no-op … 那是定義，不是發現" (a challenger with no advantage injects on-policy data; a no-op by definition) (`CV2/CATFISH-EVIDENCE-MARKING-2026-07-09.md:42-44`).
- inferred cause [I]: per-user argmax collapses coverage in both arms (min_cov 0), so the base is the collapse regime; catfish policy is a near-clone of main (same reward, same state, same decode), so injected experience ≈ main's own; lr 0.01 divergence + ep-99 checkpoint selection means the comparison is between two barely-trained nets.
- premises: a catfish agent with a different (longer) horizon discovers better experience than main; that experience transfers via replay.

### B-6. Faithful catfish on augmented-224 state + corrected coordinated decode ("λ=0 anchor"; old label `A2_faithful_corrected`)
- mechanism: B-5 mechanisms re-hosted on route-B mechanics — separate augmented net triplet, dual self-rollout with coordinated corrected decode, M1 step-bundle stratification (top 20% step-aggregate EE, `strat_threshold_quantile=0.80`), M3 70/30 conduit via `mix_route_b_batches`; γ_M [0.9,0.9,0.9], γ_CF [0.99,0.99,0.99]; ACRM OFF (3-of-4 mechanisms).
- intervention point: experience
- defined in: `CV2/FAITHFUL-AUGMENTED-CORRECTED-SDD-2026-07-09.md` §2; prereg `CV2/FAITHFUL-AUGMENTED-PREREG-2026-07-09.md`.
- run status: ran (2 arms × 3 seeds, 3000 ep).
- run conditions: family_b; 224-d augmented χ state; **corrected decode in both train and eval** (first arms clean on every 07-10 defect class, F1); k_c=1, k_cap=3; E3; lr 0.01; from scratch; PRIMARY = min-seed ΔEE>0 AND min-seed Δmin_cov ≥ −0.02; EE per-user mean; ckpt `best-weighted-reward-on-eval.pt`.
- recorded outcome: per-seed ΔEE [−3.21, −15.69, +8.44], Δmin_cov [+0.35, −0.23, +0.05]; A1 EE 459.74 / min_cov 0.504; A2 456.25 / 0.562 → "**PRIMARY = False ⟹ `NOT-DEMONSTRATED / underpowered`**" … "Simulated power at n=3: a *genuine* `ΔEE = +2.2 %` together with `Δcov = +0.05` passes with probability **≈ 0.11**" (`CV2/FAITHFUL-AUGMENTED-VERDICT-2026-07-10.md:26-49`). LATEST = same file (post-close note 2026-07-12: NC2 guard lacked `catfish_update_count>0` conjunct; measured 29998/29999/29999 updates rules out no-op).
- recorded cause: "underpowered BY DESIGN … coverage_guard tolerance is ±0.02, while the cross-seed range of min_cov is 0.579" (`…VERDICT…:44-49`). SDD prior: "family_b is myopic-sufficient → γ inert → any co-trained catfish ≈ a clone → subsumed" (`…CORRECTED-SDD…:25-28`) — premise later falsified; the verdict notes the artifacts' `gamma_note` "is STALE and must not be quoted" (`…VERDICT…:96-103`).
- side finding (F2): learned A1 EE 459.74 > AF 447.66 but "min_cov 0.504 vs AF 1.0000 ⟹ it buys EE by starving the tail — the **same RED-LINE-c pattern as `DQN_scalar`**, not a win" (`…VERDICT…:67-72`).
- inferred cause [I]: catfish uses the same reward/state/decode as main, so its pool is not a better-than-learner teacher; the coordinated decode dominates the outcome.
- premises: catfish-generated experience is better than main's; the M1 stratifier selects genuinely better experience; power adequate.

### B-7. γ₂ ablation — per-head DOWNWARD discount on the only inter-step-coupled head (handover r2) (old label: `A1_gamma2_zero` / `A1_gamma_all_zero` / `A1_gamma2_high`)
- mechanism: vary γ only on the handover head (γ=[0.9,0.0,0.9] kill; [0,0,0] fully myopic; [0.9,0.99,0.9] high) to test whether long-horizon credit on the switching-cost head shapes the deployed policy.
- intervention point: objective (per-head discount)
- defined in: `CV2/GAMMA-PREMISE-G6-VERDICT-2026-07-09.md:132-144` (arm table); `CV2/GAMMA2-ABLATION-PREREG-2026-07-09.md`; binding amendment `CV2/GAMMA2-ABLATION-PREREG-AMENDMENT-2026-07-09.md`.
- run status: **built (config-only), never run** — "STATUS = `HOLD, DO NOT DISPATCH`" (banner added 2026-07-10, `GAMMA2-ABLATION-PREREG-2026-07-09.md:5`). EVIDENCE-USABILITY: "the γ₂ ablation (9 runs, `HOLD/DO-NOT-DISPATCH`, 5 blockers) … produced no scored result".
- run conditions (planned): family_b, corrected decode k_c=1, E3, lr 0.01, 3000 ep, from scratch; reference `A1_faithful_corrected`; PRIMARY (amended) two-sided on `ho_count_rate`, NO-DYNAMIC-RANGE-aware.
- recorded outcome: none. Blockers: B1 reference had no ckpts; B2 scorer averaged r2 over all steps; B3 `ho_rate` = φ-weighted cost not a rate; B4 "the frozen PRIMARY has the WRONG SIGN" (t1b: farsighted 31 vs myopic 10 switches, REVERSE=0 ⇒ "Farsightedness never reduces switching in this env; it strictly increases it"); B4b step-1-excluded axis "no dynamic range" (myopic-J_w planner puts 99.3% of handovers at step 1) (`…AMENDMENT…:15-95`).
- recorded cause (why it was never run): prereg defects above; plus JOINT-D ruling that the training-free surrogate cannot gate it (B-10). Amendment also: "A rational policy at any γ in this env does not churn. Therefore any steady churn observed in a *trained* arm is largely **Q-approximation noise**" (`…AMENDMENT…:93-95`).
- key physics fact recorded: break-even persistent ΔEE for one φ2 handover = 505.9 (γ=0), 82.6 (γ=0.9), 58.5 (γ=0.99) readable-EE units vs mean EE ≈ 420; "γ-inertness is **CALIBRATION-DEPENDENT, not structural**" — at w=[0.9,0.05,0.05] a myopic agent switches immediately on a 1e8 gain (`CV2/GAMMA-INERTNESS-PREMISE-FALSIFIED-2026-07-09.md:151-164`).
- premises: switching cost r2 creates a delayed consequence (a_{t-1} in state); handover weight/scale leaves a non-empty amortization window.

### B-8. Switching-cost-augmented env + C3 value-of-foresight probe (method-blind, non-learned planners)
- mechanism: add previous assignment to state and `r1 −= λ·re-pointing energy`; measure Δ_fore = J(lookahead) − J(myopic) with non-learned planners over a (λ, volatility, H_ep) grid; only if ≥3% foresight region exists, train {plain-MODQN, raise-γ_M control, catfish}.
- intervention point: other (environment/physics change) + reward
- defined in: `CV2/SESSION-2026-07-09-INJECTION-FAIL-ENVDIR-ROOTQ-VERDICT.md:67-75` (§6); prereg `CV2/SWITCHING-COST-C3-PREREG-2026-07-09.md`.
- run status: ran (planner probe only; 480 items, 16 seeds, U=50, ζ∈{0,0.3,1.0}, H_ep∈{10,30,60}); the training stage never built.
- run conditions: family_b Walker-180 geometry; objective `J_EE − λ·n_switch` (**omits family_b's native r2**); 2-candidate planner menu {C0 switch-to-best, C1 hold}; exact physics scoring; no learning (lr n/a).
- recorded outcome: draft verdict "C3 FAILS everywhere … Peak healthy-subset `Δ_fore = +0.0205`" → **RETRACTED** after both G6 reviewers returned UNSOUND (`CV2/SWITCHING-COST-C3-HELD-2026-07-09.md`: discount asymmetry "the lookahead is handicapped exactly where it is measured"; health guard post-hoc; "GATE-PASS = 0 for every cut" FALSE; planner cannot express per-user hysteresis). C2 deciding experiment + menu ladder: Δ_fore `{C0,C1}` +0.0685 → `+C2` +0.0386 → `+C3iter` +0.0250 (all CI lo < 3%) ⇒ "**passing the 3% gate is decided by the implementation strength of the myopic baseline** … **The gate adjudicates nothing**" (`CV2/SWITCHING-COST-C3-C2-FINDINGS-2026-07-09.md:106-131`). LATEST: "**Retired as a direction gate. Data kept as exploratory. No boundary, no inversion, no STOP claim.**" (`…C2-FINDINGS…:158`); EVIDENCE-USABILITY G-3 "RETIRED as a direction gate (menu-ladder artifact …)".
- recorded cause: premise false — "`a_{t-1}` is **already in the state** … `r2_handover` is already a per-user switching cost … This probe's `step_utility` **omits `r2`**" (`…HELD…:18-22`); the env proposal is "half-redundant" (`GAMMA-PREMISE-G6-VERDICT` §4B).
- other recorded fact: literature exhaustion (~85 papers) concluded "hard energy / battery | ❌ **no template in corpus** … battery only a reward penalty (`−λ·E_handover`), NOT a depleting MDP state"; "data queue … ❌ ruled-out"; "handover / RVT | ✅ the one alive" with design rule "CLEAN (γ load-bearing) = **RVT in STATE, HO-penalty in REWARD**" (`SESSION-2026-07-09…:43-52`).
- premises: beam allocation has foresight value once switching is costly; family_b lacked a switching cost (FALSE — r2 exists).

### B-9. J_w-aligned joint value-of-foresight probe (menu-ladder + small-U exact oracle)
- mechanism: Δ_fore on the real J_w (r2 is the switching cost, no λ), reported as a ladder over increasing myopic planner classes P_1⊂…⊂P_K plus a U≤8 exact subset oracle; anchors: H=1 vs H=1 zero, analytic toy MDP, duplicate-candidate invariance, w2=0 action-independent-future control.
- intervention point: other (diagnostic instrument / env property)
- defined in: `CV2/JW-JOINT-FORESIGHT-PREREG-DRAFT-2026-07-10.md`.
- run status: never built ("DRAFT. NOT FROZEN. NOT IMPLEMENTED. No numbers exist.").
- run conditions: n/a (planned U∈{50,8}, H_ep∈{10,30,60}, ≥16 seeds, gate = one-sided CI lo ≥3% on the strongest myopic).
- recorded outcome: none. Erratum in same file: its "γ₂ ablation first … already frozen and ready" is FALSE (HOLD).
- premises: joint (multi-user simultaneous) switching may amortize differently than single-user deviation; foresight value is planner-class-relative.

### B-10. Joint-D / D-statistic — training-free decode-sensitivity statistic for γ (instrument)
- mechanism: fraction of (t,u) decisions whose deployed-decode choice changes when a surrogate Q is rebuilt under a different γ (e.g. (0.9,0.99) or γ₂ 0.9 vs 0.0), with homogeneous-scaling/additive-shift negative controls.
- intervention point: other (diagnostic instrument)
- defined in: `CV2/D-STATISTIC-FINDINGS-2026-07-09.md`; `CV2/D-STATISTIC-G6-VERDICT-2026-07-09.md`; `CV2/JOINT-D-G6-VERDICT-2026-07-09.md`.
- run status: ran (training-free surrogate Q; AF vs sticky continuation).
- run conditions: family_b; decodes auction/corrected/hybrid_auction × shift_to_nonneg; no training.
- recorded outcome: D_joint(0.9,0.99) "= 0.74–1.35% ⟹ **`WEAKLY-OBSERVABLE`, ∈ [0, 1.35%]**" — "M2 is a no-op" FORBIDDEN (`D-STATISTIC-G6-VERDICT…:97-100`; EVIDENCE-USABILITY G-2). For γ₂: "**NOT IDENTIFIABLE** … Sticky ⟹ `φ(a→a) = 0` ⟹ `D ≡ 0` as a structural identity … the **estimand is undefined**"; "joint-`D` cannot supersede the γ₂ ablation's `A4` pre-check" (`JOINT-D-G6-VERDICT…:30-45`). Also: "C4 binarized EE landscape ⟹ γ's action window is an EMPTY SET … REFUTED"; "C6 γ-load-bearing needs ≈8 slots … REFUTED"; "C8 M2 is a STRUCTURAL NO-OP … REFUTED" (`D-STATISTIC-G6-VERDICT…:14-18`).
- recorded cause: continuation not given by data; surrogate lacks environment feedback ("`u`'s action changes `active_loads_lc` and hence *everyone's* `s'`").
- side fact: "O1 … the live decode consumes Q **magnitudes**" (decode ranks by Q gaps, not per-user argmax) — CONFIRMED.
- premises: γ's effect reaches the deployed policy through decode ranking; a surrogate continuation is representative.

### B-11. Single-user amortization-window probe (t1b structural probe)
- mechanism: exact deepcopy rollouts; one user deviates (others pinned to AF auction); count decisions where a farsighted (sum of remaining EE gain) planner switches but a myopic (one-step gain) planner does not, cost = w2·φ/S2.
- intervention point: other (diagnostic instrument)
- defined in: `CV2/GAMMA-INERTNESS-PREMISE-FALSIFIED-2026-07-09.md` §4-AMORT; artifact `t1b-structural-RESULT.json`.
- run status: ran (4 phases × 6 seeds = 24 cells; 449 deviations, 118 clean).
- run conditions: family_b, real J_w calibration (C1FIXED scales, w=[0.5,0.3,0.2]), no training; cap-bump guard (73.7% of stay branches were cap-bumped → EE=0, excluded).
- recorded outcome: "**21 / 118 clean deviations (17.8 %) are amortization cases** … `reverse = 0`" ⇒ "`γ` has something to exploit on family_b" (`…FALSIFIED…:124-128`). Revision: the cost is undiscounted and "`m` = **單步**增益 … `f` = **未折現總**增益" so the window measures EE-head γ as a D(0,1)-type contrast, not φ-head γ nor (0.9,0.99); "window-mass 問題 = `UNRESOLVED`" (`D-STATISTIC-G6-VERDICT…:72-85`).
- premises: partial equilibrium (others fixed) is representative; staying is served.
- also recorded (reset artifact): "`env.reset` starts every episode in a COLLAPSE state" (all users on action 0) and step-1 handover is charged against it — step-1 share AF 24.7–32.1%, argmax 13.5–16.1%, myopic 99.3%; "**not** magnitude-symmetric across arms" (`GAMMA-PREMISE-G6-VERDICT…:76-84`).

### B-12. External-specialist replay injection, DQfD-style (old label: `A2_inject_dqnscalar`, INJ-1)
- mechanism: a frozen pre-trained DQN_scalar specialist rolls out through the full-coordination auction (k_c=k_cap=3); admit step-bundles with served_frac ≥0.90 AND step_EE ≥ median (EE_TOP_QUANTILE 0.50) into D^ext; each minibatch = 30% D^ext + 70% own replay (ρ=0.30), targets recomputed Double-DQN over MODQN's online net.
- intervention point: experience
- defined in: `CV2/EXTERNAL-INJECT-PREREG-2026-07-08.md` §3; design origin `CV2/CANDIDATE-EXTERNAL-EE-INJECTION-2026-07-08.md`.
- run status: ran (n=5 seeds {42,137,271,314,628}, 3000 ep; each MODQN seed paired with its own DQN_scalar seed 0–4).
- run conditions: family_b; target arm `_hybrid_k1_C1FIXED` = E3 calib but **F5-TRAINED** (leaky decode, D5); **teacher = frozen DQN_scalar trained in E1 (`D2a`, wrong-EE reward)**; lr 0.01; MODQN trained from scratch with the frozen teacher's pool (not distillation of a pre-trained main); scored corrected decode k_c=1, 48 ep; PRIMARY = min-seed ΔEE>0 AND cov guard.
- recorded outcome: n=5 per-seed ΔEE [+41.8, −44.8, +30.3, −47.1, +23.4], A1 403.5 / A2 404.3 / AF 448.3 → "**PRIMARY FAIL / NOT-DEMONSTRATED**" (`SESSION-2026-07-09…:7-21`). LATEST scope (`FBD/EVIDENCE-USABILITY-2026-07-10.md` INJ-1): "MAY close **ONLY** the {ρ=0.30 · DQN_scalar-source · F5-trained-k1 target · min-seed-sign rule} config … **'injection fails' is FORBIDDEN**" — EVIDENCE-OF-NOTHING beyond that config.
- recorded defects: scorer first ran the WRONG (F5) decode (fixed; verdict survives); cov_guard unit bug ("`min_coverage` is a COUNT/48, compared against a FRACTION 0.02 tolerance"); "the frozen selective-injection's coverage clause is **non-binding** on this pool (all 5 dqn-seeds `cov_pass_frac`=1.0) → … degenerated to EE-median-split only" (`SESSION-2026-07-09…:24-30`).
- recorded cause: "shared `family_b` myopic-sufficiency + k_c=1 decode washing out learned-Q" (`SESSION-2026-07-09…:21`); literature: "DQfD / Amortization … injection/distillation is source-bounded, buys sample-efficiency not asymptotic lift; no lift when source not stronger or task near-ceiling" (`…:58`).
- inferred cause [I]: teacher was trained on the wrong EE quantity (E1), the target was F5-trained, and the selection rule degenerated — three confounds, so the null is uninformative about injection per se (as the records themselves say).
- premises: a better-than-learner teacher exists (DQN_scalar+coord ≈552 EE at 0.98 cov — but that landmark is E1/D2a, NOT-USABLE); off-policy value is absorbable by MODQN via replay.

### B-13. Swap the catfish stimulus source to an external DQN_EE specialist (design candidate; "SIL is ceiling-limited")
- mechanism: inherited catfish = self-imitation (extracts high-value experience from own rollouts, ceiling-limited); replace the source with a pre-trained single-objective DQN_EE specialist's high-EE-AND-high-coverage transitions; HO/LB heads treated as instrumental ("EE-favourable"), exploiting corr(EE, r3)=+0.81.
- intervention point: experience
- defined in: `CV2/CANDIDATE-EXTERNAL-EE-INJECTION-2026-07-08.md`.
- run status: never built as such; realised first as B-12 (DQN_scalar source) and later as INJ Rung-1 pools (B-17).
- run conditions: n/a.
- recorded outcome: design only. Caveat recorded: "'All params controllable → no reason not to win' is OVER-CONFIDENT … beat-AF-on-EE (very-low-prior; AF = matched-coverage EE ceiling; the coverage-EE bind is structural, not a knob)".
- premises: "catfish = SIL is ceiling-limited on under-fit EE"; an external specialist is better than the learner; EE-favourable LB ≈ high coverage (+0.81 correlation). Later: the coverage clause was non-binding on the pool (B-12), undercutting the +0.81 premise.

### B-14. Expert delegation / static hybrid decode (old label: "catfish-v2 Candidate-A", arm F)
- mechanism: at deployment, learner chooses the k_c=1 coordinated beam; the fixed AF heuristic assigns users on the remaining v_max−k_c (argmax) beams; no per-step arbitration.
- intervention point: decode/deployment
- defined in: `CV2/gate2-3-VERDICT.md`, `CV2/gate3b-SCOPE-VERDICT.md`, prereg `CV2/EXPERT-DELEG-PRODUCTION-PREREG-2026-07-08.md`; results `CV2/EXPERT-DELEG-3SEED-LOCAL-RESULT-2026-07-08.md`, `CV2/EXPERT-DELEG-PRODUCTION-VERDICT-2026-07-08.md`.
- run status: ran eval-only (n=3 ep=12 preview; n=3 ep=48; n=5 ep=48 after training 2 more learner seeds {314,628}); 6 axes, 24 grid points (18 distinct cells).
- run conditions: family_b; learner `A1_hybrid_k1_w503020_C1FIXED` (**F5-TRAINED**, corrected eval, "symmetric across L/F"), lr 0.01, from scratch; U=100 nominal, k_cap=3, k_c=1; EE per-user `family_b_eta_r1`/1e6; min_cov = min-over-users fraction with throughput>0; AF = matched k_c=1 hybrid with `shift_to_nonneg=False`.
- recorded outcome: n=5 "PRIMARY seed-separation `min_seed(F) > max_seed(L)`: 24/24 … nominal L=403.5 < AF=448.3 < F=488.6"; F improves coverage (cov_L 0.48–0.86 → cov_F 0.90–0.98); F>AF 22/24, fails only high noise (`…PRODUCTION-VERDICT…:14-20`). G6 SOUND-WITH-FIXES (unanimous). LATEST (`CV2/EXPERT-DELEG-G6-VERDICT-2026-07-10.md:45-49`): "The USER has RULED OUT the delegation mechanism as a deliverable (a deploy-time expert = shipping the catfish, not the sardine)" → retained only as "**HEADROOM EVIDENCE** … and as an **effect-size prior** for a training-time injection experiment". EVIDENCE-USABILITY DL-1: "AF ≠ 'ceiling / auction on all beams'".
- recorded cause: "F>L = a FIXED heuristic (AF) rescuing a COLLAPSED learner's argmax beams, not learned delegation … F−L grows +85 (v=3) → +169 (v=15) as L collapses 403→92"; "only `k_cap` genuinely perturbs the learner"; "effect → 0 as k_c → v_max" (`…PRODUCTION-VERDICT…:26-40`). "F>AF is the genuinely-LEARNED result … the learner's `k_c=1` coordinated beam adds ≈+40 EE (~+9%) over the matched AF reference" (fix 6).
- premises: learner's non-coord (argmax) beams are collapsed/poor; a heuristic expert is better there; deployment-time expert is acceptable (USER said NO).

### B-15. Per-step oracle arbitration between learner and expert (arm M) + deployable arbiters (PHYS model-based, Q1 learner-EE-head)
- mechanism: per step choose whichever of {learner assignment, expert assignment} yields higher single-step EE — M uses true post-action EE (deepcopy+step); PHYS uses env reward physics at pre-move geometry with expected fading=1; Q1 uses the learner's own EE head.
- intervention point: decode/deployment
- defined in: `CV2/gate1-oracle-VERDICT.md`; `CV2/gate2-3-VERDICT.md` (Gate 2 table).
- run status: ran eval-only (3 seeds, ep=12, nominal U=100, v_max=3, k_c=1).
- run conditions: same learner as B-14 (F5-trained A1_hybrid_k1, lr 0.01); fish = AF.
- recorded outcome: M 483.3 / cov 0.825 vs L 388.7 / 0.500 vs AF 448.2 / 1.000; "**PHYS** … reproduces the oracle EXACTLY (100% retention + 100% choice-agreement, all seeds)"; "**Q1 FAILS** (learner EE-head is degenerate, |absmax|=0.385, the C1-era magnitude issue) → the gain comes from the physics/delegation, NOT learned value"; "**M − F = +4.6 (<5)** → per-step arbitration is ~DECORATIVE" (`gate2-3-VERDICT.md:10-24`). Oracle-M "EE-beat-over-AF is a COVERAGE TRADE".
- recorded cause: see quotes; learner EE head magnitude degenerate.
- premises: a single-step EE model is an adequate arbiter (true on family_b because EE is per-step separable given the joint action).

### B-16. Decision-time competitive injection at high v_max ("fish jurisdiction = v_max − k_c") — knob recon of the co-trained A2
- mechanism: hypothesis that the more non-coordinated beams there are (larger v_max−k_c), the more the catfish (co-trained A2) can add EE.
- intervention point: other (operating-point knob)
- defined in: `CV2/knob-recon.md` (reads the kc1 5-arm ablation CSVs).
- run status: ran (eval-only analysis of existing CSVs; n=3 seeds, 6 axes).
- run conditions: arms trained in the F5-leaky kc1 line (CF-6: "corrected-decode EVAL of **F5-TRAINED** hybrid ckpts"), lr 0.01, E3.
- recorded outcome: "gap(MCCRL − A1) [catfish EE benefit]: non-monotone, SIGN-FLIP. Positive only at v=3 (+13.24) and v=4 (+15.61); crosses to negative at v=5 … CI-negative for v_max ≥ 12"; "coordination EE benefit (MCCRL − NoCoord) **strictly shrinks** with v_max (295.7 → 10.6)"; no-coord `min_cov = 0.0` at every point (`CV2/knob-recon.md:13-27,103-118`).
- recorded cause: "High v_max is the region with the least EE for a fish to recover and where catfish already underperforms without-catfish."
- premises: EE headroom grows with the number of uncoordinated beams (FALSE per this recon).

### B-17. INJ Rung-1 — DQfD-inspired external-experience injection wave (ρ-REPLACE mixing + large-margin loss), with source/value/margin/decode-floor controls and a faithful-CDRL arm (old label: INJ Rung-1 v5.4, arms A/B/C0/D/E/F/G; EVIDENCE-USABILITY row INJ-2)
- mechanism: frozen teacher policy rolled out through the student's OWN deployed decode (corrected, k_c=1) builds a pool; admit top-20% EE step-bundles; each update = 38 pool + 90 own-replay items (ρ=0.30, B=128, never extra updates); DQfD large-margin loss J_E over the scalarized surface Σ_k w_k Q_k on injected (s,a) only (margin 0.8, λ=1.0); no pretrain; teacher absent at eval. Arms: A off (n=8); **B DQN_EE top-20% margin ON (PRIMARY, n=8)**; C0 = B pool margin OFF (n=5); D = AF-rule rollout pool ("decode-floor" control, n=5); E = DQN_EE bottom-20% (value control, n=5); F = recalib E3 DQN_scalar top-20% (source ablation, n=8); G = faithful CDRL self-rollout (B-6 machinery, 5 fresh seeds).
- intervention point: experience + penalty/loss (margin)
- defined in: `CV2/INJECTION-DESIGN-DECISION-BRIEF-2026-07-10.md` (v5.4); `CV2/INJ-RUNG1-PREREG-2026-07-10.md` §3–§7 (frozen `fadc7c3e`@`6f03f97`); result `CV2/INJ-RUNG1-RESULT.json`; verdict `CV2/INJ-RUNG1-ADJUDICATION-2026-07-11.md`.
- run status: ran (44 fresh runs × 3000 ep).
- run conditions: family_b; base prereg `retrain-prereg-family-b-w503020-C1FIXED.json` ⇒ **lr 0.01**, γ scalar 0.9, value-stratification OFF, ACRM OFF; w=[0.5,0.3,0.2]; r1=angle_aware_ee; **corrected decode in train+eval**, k_c=1 (E3, not F5); 224-d augmented state; from scratch (teacher = frozen separately-trained DQN; student not distilled from a frozen main); eval = 48-ep matched harness SEED 20260626, EE per-user `family_b_eta_r1`/1e6, ckpt class best-weighted-reward-on-eval; PRIMARY = two-sided per-seed CI separation (MDE: n=8 t-test 29.9, CI-sep 33.2, `CV2/MDE-NOTE-2026-07-10.md`). Teacher quality (T3): DQN_EE view-B pool 489.9 (per seed 514.0/510.4/445.3), recalib DQN_scalar 528.6; random-through-auction 449.1 ≈ AF ⇒ "the learned Q adds ~+41 (~9%) on top of the coordination structure" (DQN_EE) / ~+79 (scalar); teacher action-overlap with A1 only 0.35–0.52 (`CV2/T3-SOURCE-POOL-MEASURE-2026-07-10.md`, `CV2/T3-SCALAR-POOL-MEASURE-2026-07-10.md`).
- recorded outcome (from RESULT JSON): arm means A 462.9 · B 465.9 · C0 463.4 · D 469.7 · E 464.2 · F 463.6 · G 463.8 (AF 448.3). "**NOT-DEMONSTRATED on all 7 preregistered contrasts** (PRIMARY B−A +3.08, CI [−13.54, +19.70]) … G−A +0.93, CI [−23.0, +24.9]" (`…ADJUDICATION…:129-134`). Status FORMAL 2026-07-11. Licensed secondary: "arm B's across-training-seed EE mean was above the fixed AF landmark with its 95% mean CI entirely above AF (B 465.94, CI [459.30, 472.58]; AF 448.28)" — "NOT attributable to injection (B−A not separated; A mean 462.87)" (`…:78-83`). EVIDENCE-USABILITY INJ-2: "a REAL scoped null, unlike INJ-1/CF-7 (this wave was MDE-powered)" — closes "ρ=0.3 DQfD-style EE-pool injection lifts eval-EE by ≥ ~+20 at this operating point".
- [computed by me from `INJ-RUNG1-RESULT.json`, not quoted in a verdict] per-arm mean min_cov_frac: A 0.917 · B 0.953 · C0 0.949 · D 0.979 · E 0.958 · F 0.961 · **G 0.623** (G scored by its own faithful scorer; unit guard exists; not adjudicated in the records I read).
- recorded cause: NOT adjudicated. Scoped flat-Q finding: "On three sampled injection-OFF checkpoints … the learned scalarized Q supplied essentially no decision-changing per-user discrimination" ("behaviorally absent", corr 0.994–1.0); "The CAUSE is NOT grounded — encoder information loss vs optimization failure (target-net staleness, **lr**, replay distribution, ε-greedy visitation, reward calibration, 10-step returns, function-class bias, decode-induced state-distribution feedback) are NOT distinguished"; "ROOT = state encoding — NOT ADJUDICABLE" (`…ADJUDICATION…:84-97`). Design-phase washout mechanism: teach@k₃ / learn@k₁ "TD-vs-margin conflict" — at k_c=3 the argmax-shift was +44.8 pt, at k_c=1 −5.8/−13.4 pt; fixed by rebuilding pools at k₁ (`CV2/INJ-RUNG1-ARGMAX-GATE-BLOCK-2026-07-10.md`). Gate-v2 "margin absorption" G-1 +1.73/+2.38 GREEN but "DEMOTED to PLUMBING-SANITY … s137's rank +2.38 coexists with a greedy teacher-agreement COLLAPSE 0.09975→0.00025" (prereg line 252).
- training-time vs eval (server preliminary package, `OLD/INJ-RUNG1-DISCUSSION/README.md`): "訓練期看到的 B−A +135 EE 抬升**沒有存活到 eval**,只剩 +3" (the +135 training-rollout lift of B over A did not survive to the frozen greedy eval; only +3) — end-of-training r1/1e6 A 4104 / B 4239 / C0 4091 / D 4266 / E 4244 / F 4259. [I: consistent with B-28 — the eval scores the best-eval ckpt, which is typically early, while the training-rollout proxy is late-training.]
- REFRAME recorded: "fresh k₁ corrected-trained learners eval 460-470 > random floors (435.9/423.9) > AF 448 ⟹ Card-1's 'Q worse than random' was a stale-ckpt read" (`FBD/EVIDENCE-USABILITY-2026-07-10.md` INJ-2).
- inferred cause [I]: teachers are only ~+41..+79 above a decode floor the student already exceeds (student 460–470 vs teacher k₁ pools ~450–523), so the "better-than-learner teacher" premise is thin at k_c=1; learned Q rows are near-identical across users so injected per-user action preferences have no representational channel; lr 0.01 unvaried.
- premises: a better-than-learner teacher exists at the student's operating decode; off-policy demos are absorbable by the shared per-user Q; the decode passes Q discrimination through.

### B-18. Teacher-weight search — drop the handover weight to get a higher-EE teacher (T4; W1 [0.5,0,0.5], W2 [0.7,0,0.3], W3 [0.35,0,0.65])
- mechanism: train scalar-fold DQN teachers with EE+LB weights (HO weight 0) hoping for a stronger injection source than DQN_scalar[.5,.3,.2] without DQN_EE's coverage starvation.
- intervention point: other (teacher construction for experience injection)
- defined in: `CV2/T4-TEACHER-SEARCH-2026-07-10.md`; premise check `CV2/T4-CONTROLLER-PREMISE-CHECK-2026-07-11.md`.
- run status: ran (3 candidates × 1 seed (42), 3000 ep, ~7.6 h each).
- run conditions: family_b, clean calib (REWARD_SCALES[0]=2.532105322e11); pure DQN scalar-fold (not MODQN); lr not stated in these files [I: DQN baseline trainer config not read]; teacher quality scored as view-B (k_c=3 full auction) pool EE; eval min_cov 0.00 for all three under argmax.
- recorded outcome: W1 535.2 / W3 523.6 / W2 517.2 vs incumbent per-seed [523.0, 517.0, 552.2, 535.9, 514.9]; ruling: "**the best variant (W1) only ties the incumbent … The USER's mechanism intuition (drop the handover weight → higher-EE teacher) is not supported** at these three points" → "DEFER the +2 seeds" (`…PREMISE-CHECK…`).
- premises: teacher EE strength is the binding variable for injection (conditional on B-17 being positive — it was not).

### B-19. Argmax-shift / margin-absorption pre-server gate (instrument for "does injection move the student's Q ranking at all")
- mechanism: short training ON vs OFF; G-1 = mean over probe pool states of (rank_OFF − rank_ON) of the demo action in the student's masked scalarized-Q ordering; G-2 greedy teacher-agreement (report-only).
- intervention point: other (instrument)
- defined in: `CV2/INJ-RUNG1-GATE-V2-PRESTATE-2026-07-10.md`; v1 `CV2/INJ-RUNG1-ARGMAX-GATE-BLOCK-2026-07-10.md`; `CV2/INJ-RUNG1-K1POOL-PREVIEW-FINDINGS-2026-07-10.md`.
- run status: ran (v1 60-ep 4 runs; k₁ preview 2 seeds; v2 200 ep 2 seeds).
- recorded outcome: v1 "instrument premise — ε@60 ep ≈ 0.97 … the gate is currently measuring a regime the wave never ships" (retired); v2 GREEN (G-1 +1.73/+2.38) but demoted to plumbing-sanity (pseudo-replicated CI; teacher-agreement collapse on s137).
- recorded cause: see B-17.
- premises: Q-rank movement at 200 ep predicts 3000-ep effect.

### B-20. Cross-user input standardization (z-score each feature across the 100 users per step) — REPLACE form (IS v2: IS_off / IS_injection)
- mechanism: before the shared per-user Q-net, standardize every state feature across users at that step (zeroes the component shared by all users; ε=1e-6 guard); v2 = z REPLACES raw input.
- intervention point: representation
- defined in: `CV2/IS-DESIGN-REVIEW-2026-07-11.md` §1; prereg `CV2/IS-PREREG-DRAFT-2026-07-11.md` (+ v2.2/v2.3 amendments); readout `CV2/IS-RESULT-L1L4-2026-07-11.md`; verdict `CV2/IS-READOUT-VERDICT-2026-07-11.md`.
- run status: ran (2 arms × 3 seeds {42,137,271}, 3000 ep).
- run conditions: family_b; "A1_C1FIXED base config, wave ε-schedule/replay/calibration" ⇒ lr 0.01; corrected decode k_c=1 train+eval; from scratch; both arms `standardize_input=true`; arms differ ONLY in `injection_rung1.enabled` (IS_injection = INJ1_B package: DQN_EE top-20% pools, ρ 0.30, margin ON); value-strat OFF, γ-vector null; `catfish_challenger_enabled=true` "INERT flag". Endpoint ladder L1 input corr → L2 Q de-flatten (argmax_distinct ≥8 & Q-row Pearson ≤0.90) → L3 argmax-decode structural (cap_bump ≤0.40 & min_cov ≥0.40) → L4 corrected EE.
- recorded outcome: L1 PASS both (net-input user-row corr 0.9588 → −0.0095). L2/L3: IS_injection 3/3 PASS (distinct 16/18/15, Q-corr 0.22/0.17/0.21; argmax cap 0.36/0.33/0.34, min_cov 0.52/0.53/0.54); IS_off 1/3 FAIL both (distinct 7/7/11). L4: "+35.67 EE, CI95 [+1.37, +69.98], all three paired deltas positive. This is fragile screen evidence, not a confirmed effect (exact sign test p = 0.25 …)"; IS_injection corrected EE 522.2–528.1 with min_cov 0.970–0.992 (descriptive landmark) (`IS-READOUT-VERDICT…:16-38`). LATEST: superseded as evidence by v3 (B-21) — "The v2 REPLACE-screen +35.67 was NOT SEPARATED under concat and v3 therefore provides no additional support for it — but … v3 also does not refute it" (`CV2/IS-V3-READOUT-VERDICT-2026-07-12.md:18-21`).
- recorded cause: split driver "OPEN, three candidates": "external transition CONTENT · the 30% self-replay replacement itself · teacher-action MARGIN supervision" (`IS-READOUT-VERDICT…:42-46`).
- premise evidence recorded: born-flat — "raw init Qcorr 0.98-0.99 == trained 0.96-0.99 ⟹ born-flat LITERAL for raw; z/concat de-flatten already at init (0.66-0.87)" (`FBD/PRIOR-ART-CARDS-2026-07-10.md` Card 7, init_flatness_probe 2026-07-12). Design warning: "LayerNorm normalizes ACROSS FEATURES within one user's input; it does nothing about a feature whose VALUE is shared by all users" (`IS-DESIGN-REVIEW…:20-23`). Reward-curvature caution: "sum-operator reward families derive NO heterogeneity gain" (arXiv:2506.09434) → "IS succeeds at every representation level and EE still does not move" is a pre-registered possible reading.
- premises: the flat-Q/argmax collapse is caused by cross-user input homogeneity (shared-feature drowning); per-user diversity in Q translates to EE (records caution it may not for a sum-type EE).

### B-21. Concat(raw ‖ z-score) input + width control + self-pool content control + margin ablation (IS v3, Branch W, 20 runs)
- mechanism: 448-d input = raw channel ‖ cross-user-z channel (keeps absolute levels); cells C1 (224 raw, OFF, reused wave A), C3 (224 raw, injection, reused wave B), C2 (concat OFF), C4 (concat + DQN_EE injection margin ON), C4s (concat + frozen SELF-experience pool, margin ON — "same-rule, different-source-policy bundle"), C4m (concat + injection margin OFF), C2w/C4w ([raw‖raw]-448 width controls).
- intervention point: representation (+ experience, penalty/loss via margin)
- defined in: `CV2/IS-V3-DESIGN-REQUIREMENTS-RULING-2026-07-11.md`; `CV2/IS-V3-RULING-V2.1-2026-07-12.md`; verdict `CV2/IS-V3-READOUT-VERDICT-2026-07-12.md`; follow-up `CV2/IS-V3-CHEAPCHECKS-ADJUDICATION-2026-07-12.md`.
- run status: ran (20 runs: new cells n=3/2, 3000 ep; C1/C3 reused).
- run conditions: family_b; A1_C1FIXED base ⇒ lr 0.01; corrected decode k_c=1; from scratch; E-5 telemetry (training-time cross-user std of per-head TD targets) on new cells only; eval_concat-448 scorer for new cells.
- recorded outcome: "All 9 registered contrasts NOT-SEPARATED ⟹ **NOT-DEMONSTRATED** … Primary C4−C2 = +4.0 [−29.6, +37.6]; interaction DiD = +0.9 [−19.8, +21.6]; z-specific … = −11.6 [−163, +140]"; "every concat checkpoint de-flattened (argmax_distinct 4.5–14.4, Q-row corr 0.36–0.92) and every width-control checkpoint did not (distinct exactly 1.0, corr ≈1.0, 4/4 runs)"; descriptive min_cov C4 0.985–0.992 ≥ C2 0.960–0.981 ≥ C1 0.915–0.938 (`IS-V3-READOUT-VERDICT…:15-38`). Cheap checks (LATEST, 2026-07-12): width nets "trained into a CONSTANT-FUNCTION regime (output rows invariant to ANY input)" (training fact); E-5 "**DQfD margin (on top of z): ~26-30×** (0.0013 → 0.034) … the margin loss is what SUSTAINS cross-user target differentiation during training"; T-C per-user-argmax EE: width 147.2 < C4m 236.1 < C4s 329.7 < C2 357.1 < C4 386.8 vs AF 448.3 ⇒ "**the remove-coordinate route is NOT viable on current mechanisms** … The decode stays load-bearing" (`IS-V3-CHEAPCHECKS-ADJUDICATION…:10-61`).
- recorded cause (why EE did not separate): "NON-EXHAUSTIVE hypotheses, v3 cannot discriminate: (a) raw channel lets SGD default to raw features … (b) the v2 +35.67 was fragile/noise; (c) concat z-only checkpoints already show the de-flattening PHENOTYPE … (d) REPLACE-vs-CONCAT optimization-geometry differences; (e) checkpoint selection / seed-specific instability; (f) evaluator/scorer-shell differences" (`IS-V3-READOUT-VERDICT…:47-54`).
- premises: same as B-20; plus "per-user Q discrimination can be restored by training" (partly supported: argmax 146.6 → 350–420 class, still < AF).

### B-22. Bootstrap-locking knobs — reduced γ / n-step returns to break flat-Q self-consistency (IS v3 Rider-4 sub-study / "E-1v2")
- mechanism: flat Q may be locked in by bootstrapping (TD targets computed from an already-flat target net); shorten the bootstrap (lower γ) or use n-step returns to inject more per-user reward signal into targets.
- intervention point: objective / penalty/loss (target construction)
- defined in: `CV2/IS-V3-PREREG-DRAFT-2026-07-11.md:21,48` ("Bootstrap-locking sub-study (Rider 4) — on the pure-IS cell C2"); cut in `CV2/IS-V3-DESIGN-REQUIREMENTS-RULING-2026-07-11.md:36-38`.
- run status: never run ("CUT from v3 … reduced-γ / n-step TRAINING cells (premature for a fragile screen effect; **pre-register a stage-2**: triggered iff E-5 shows target-variance stays compressed post-concat)").
- recorded outcome: none; E-5 later showed target cross-user std for concat-OFF C2 ≈0.0012 (compressed) vs margin-ON 0.034 (B-21) [I: the stage-2 trigger condition appears met by the numbers, but no record of the stage-2 being run in this cluster].
- related: PRIOR-ART Card 3 lists "**n-step demo returns** (DQfD's actual workhorse per its ablations — our pools are step-bundles, no trajectories; stage-2 candidate already recorded)" and "demo-PRIORITIZED replay (PER bonus on demos — cheap, untested here)".
- premises: flat-Q is partly an optimization/bootstrapping artifact rather than an input artifact.

### B-23. Catfish (implemented M1 EE-stratify + M2 asym-γ + M3 periodic intervention) on the REPAIRED input substrate (Tier-1 pilot arms S-CFZ = z+catfish, S-CFC = centering+catfish)
- mechanism: re-test the faithful catfish machinery after the input repair (concat-z or cross-user mean-centering), on the hypothesis that the catfish could only act once the Q is no longer born-flat.
- intervention point: experience (+ objective via γ)
- defined in: `CV2/TIER2-PREREG-SKELETON-2026-07-12.md` (branch rule); intake `CV2/TIER1-FINAL-INTAKE-2026-07-12.md`.
- run status: ran (Tier-1 pilot 14 runs: S-C2×3, S-CEN×3, S-RAW×2, S-CFZ×3, S-CFC×3; 3000 ep).
- run conditions: family_b; wave base ⇒ lr 0.01; corrected decode k_c=1; from scratch; injection OFF; `M3_fired = 2977–3033` per seed; wiring controls exact (S-C2 == v3 C2, S-RAW == v3 C1).
- recorded outcome: "Registered contrasts, all **NOT-SEPARATED** (paired-t, n=3, decode-EE): center-vs-z −29.4 [−130.7,+71.9] · **catfish-on-z −5.6 [−116.4,+105.2]** · catfish-on-center −2.75 [−62.3,+56.8]"; branch B by frozen rule; "**Catfish on the repaired substrate: NOT-DEMONSTRATED** … The substrate does everything; catfish adds nothing on top of it"; measured SD_paired 44.6 ⇒ MDE(n=5) ≈ 74 EE; "a RESOURCE decision, **not** a terminal route declaration" (`TIER1-FINAL-INTAKE…:76-115,229-242`).
- recorded cause: none adjudicated; M2 "already declared GROUNDED-INERT on family_b" [note: that label conflicts with the 07-09 γ-premise falsification, B-7]; later §7: training past the best-eval ckpt degrades the net (B-28).
- premises: repaired substrate gives catfish experience something to differentiate; M1/M3 transfer diversity.

### B-24. Margin-ized catfish — catfish challenger's demonstrations + DQfD large-margin loss (old label: T-B, `TB-MARGIN-CATFISH.yaml`)
- mechanism: use the separately-trained catfish challenger (different objective) as the demo source for the INJ margin loss, so the catfish's "different behaviour" is transferred by supervision rather than replay mixing.
- intervention point: penalty/loss + experience
- defined in: `CV2/TB-CHALLENGER-TEACHER-GATE-2026-07-12.md`; `CV2/TIER2-PREREG-SKELETON-2026-07-12.md` Appendix C.4.
- run status: built (+smoked), never run — "BUILT-NOT-DISPATCHED"; gated by a teacher-usability probe.
- run conditions (probe): raw-224 challenger from `A2_faithful_corrected` (lr 0.01, corrected decode, from scratch).
- recorded outcome: "**T-B: NO-GO (raw substrate). Do not run it.**" — per-user argmax distinct beams across 100 users: DQN_EE teacher 10.93, AF rule 12.78, **catfish challenger 1.00**, learner 1.00; challenger demos EE ratio vs learner 0.911/0.950/0.925; "the **learner** sends all 100 users to a single beam **X**; the **challenger** sends all 100 users to a single beam **Y ≠ X** … It would RELOCATE the collapse, not cure it" (`TB-CHALLENGER…:14-46`). Scope: raw substrate only; repaired-substrate (S-CFZ) challenger UNTESTED (probe built). Later: C3 gap-reach prereg (B-30) records a hypothesis that the DQfD margin "WIDENS top-1 margins = the p<1 direction = the one that COSTS −13…−24 EE" (`CV2/C3-GAP-REACH-PREREG-2026-07-12.md:33-38`, hypothesis-untested).
- recorded cause: "Behavioural difference and cross-user diversity are different quantities, and only the second is what a margin loss can transfer."
- premises: "the challenger is trained on a different objective, therefore its behaviour is different, therefore its demonstrations carry diversity the learner lacks" — recorded as **FALSE on this substrate**.

### B-25. Teacher-diversity pre-flight criterion (source policy's per-user argmax differentiation ≫ 1)
- mechanism: before any injection/distillation arm, measure how many distinct beams the demo source's per-user argmax picks across users; usable only if materially >1 (working DQN_EE teacher ≈ 10.93).
- intervention point: other (teacher screening instrument)
- defined in: `CV2/TB-CHALLENGER-TEACHER-GATE-2026-07-12.md:50-74`.
- run status: ran as a probe (3 seeds; 4 sources).
- recorded outcome: "The discriminator between the teacher that WORKED and the teachers that did not is **teacher argmax-differentiation (≈11–13 versus 1)** — *not* 'external versus self'" — external DQN_EE (distinct ≈11) → only CI-separated positive (+35.67, REPLACE substrate); self-pool (≈1) → null (v3); challenger (≈1) → nothing to donate. Tagged "`hypothesis-untested` … three points and one positive do not establish it".
- premises: the transferable ingredient is cross-user diversity in the teacher; the +35.67 positive is real (itself fragile, B-20).

### B-26. Symptom penalties on the shared Q — Q-row de-correlation loss, srank (Kumar) penalty, user-axis normalization layer (Tier-1b arms TB-DECORR-lo/-hi/-escape, TB-SRANK-nudge/-parity/-kumar)
- mechanism: add a loss term that directly penalises cross-user Q-row Pearson correlation, or a feature-rank (srank) penalty, without touching the input encoding; menu also lists a cross-user BatchNorm ("user-axis BN = in-net z-score"; Daneshmand 2003.01652 "BN provably avoids rank collapse").
- intervention point: penalty/loss (+ representation for the BN variant)
- defined in: `CV2/TIER1B-DISCRIMINATING-PREREG-2026-07-12.md`; menu `CV2/TIER2-PREREG-SKELETON-2026-07-12.md` Appendix C.1–C.3; configs `configs/shared_q_isolation/tier1b/` (cluster-4 files `shared_q_isolation/{penalties,trainer_penalty}.py`).
- run status: built + 3-ep smoked, 12 runs **HELD** (not dispatched as of 07-12; `NEXT-SESSION-HANDOFF-2026-07-12-EVENING.md:21`; chronicle `archive/project-state/CURRENT-STATE-CHRONICLE-through-2026-07-22.md:1549`). Later status belongs to the 07-13+ clusters.
- run conditions (planned): raw substrate, S-RAW matched control, seeds {42,137}, 3000 ep, lr 0.01.
- recorded smoke facts: "ρ = 1 is a **stationary point** of the de-correlation penalty (measured |∂P/∂Q| = 4.6e-18 at exact collinearity) and the raw substrate sits at ρ ≈ 0.998"; TB-DECORR-lo (0.05× TD) and -hi (0.49× TD) "TRAPPED, the penalty RISES"; only TB-DECORR-escape (4.88× TD) de-correlated (0.975 → 0.677) (`TIER1B…:34-37,56-60`). Reading rule: H_rep (argmax UP, decode UP) / H_inv (UP/DOWN) / H_null (DOWN/DOWN).
- recorded cause for holding: the "inversion" hypothesis it was built to test died; training divergence (B-28) found.
- premises: collapse/homogenisation is the disease (the records later question this — "de-correlation is a PASSENGER, not a cause", `TIER1-FINAL-INTAKE…:381-383`); Goodhart risk explicitly noted.

### B-27. Cross-user mean-centering (subtract the per-step cross-user mean of each feature, no σ division) (S-CEN, "Tier-0 centering")
- mechanism: remove the shared component only; Tier-0 found "centering does 100% of the de-correlation, σ-division none" (`FBD/PRIOR-ART-CARDS-2026-07-10.md` Card 1 correction 2).
- intervention point: representation
- defined in: `CV2/TIER2-PREREG-SKELETON-2026-07-12.md` (arm S-CEN, branch B "centering-canonical confirmation"); intake `CV2/TIER1-FINAL-INTAKE-2026-07-12.md`.
- run status: ran (S-CEN ×3, S-CFC ×3 in the Tier-1 pilot).
- run conditions: as B-23.
- recorded outcome: center-vs-z −29.4 [−130.7, +71.9] NOT-SEPARATED; srank "concat ~99-106 > center 0-72 > raw 3-46"; S-CFC "additionally *worsens* the unstable centering base: srank 0/0/65 vs S-CEN's 54/0/72 — descriptive" (`TIER1-FINAL-INTAKE…:76-96,235-236`).
- premises: as B-20.

### B-28. Fix the TD divergence — learning rate 0.01 → 1e-4, gradient clipping, target-update cadence (and the finding that motivates it)
- mechanism: the project's trainer (Adam, lr 0.01, no gradient clipping, target update every 50 ep, raw-unscaled reward normalization) diverges; the best-eval checkpoint selector harvests a pre-divergence peak.
- intervention point: other (optimizer / training stability)
- defined in: `CV2/TRAINING-DIVERGES-FINDING-2026-07-12.md` §4–§6.
- run status: finding measured (eval-only on committed artifacts, n=135 arm/seed ckpt census); the fix itself **never run in this cluster** ("The test is cheap: ~3 runs, 2–3 h … USER decision"); later lr root-cause work belongs to cluster 4.
- recorded outcome (finding): best-ckpt episode median 30% of 3000; "37.8% of all runs peak in the FIRST 20% of training"; `A2_faithfulcatfish` best episode "99 / 99 / 99 | **3% / 3% / 3%**", `A1_plain_faithful` 349/199/99; final vs best decode-EE falls on 7/7 arm-seeds (A1 459.8 → 398.0; A2 448.2 → 386.5; IS_pure 475/508/484 → 432/431/431, below AF 448.3); TD loss ratio vs best-episode loss explodes "**408× … 1308×**" by ep 1200–2000 for IS_pure while "IS_cat … 0.9–1.6× (stable)" (`TRAINING-DIVERGES…:18-78`). "`learning_rate = 0.01` is an UNDISCLOSED, UNREGISTERED choice of ours — not a fidelity requirement … 100× off the field standard" (`…:104-107`).
- recorded cause: "`hypothesis` (strong …): this is TD divergence — the deadly triad … the best-eval selector has been catching the network *just before it does*, in every run, for the entire project" (`…:80-83`).
- implication for other entries [I, drawn from the quoted numbers]: every catfish/injection arm in this cluster (B-1..B-6, B-12, B-17, B-20..B-23) was trained at lr 0.01 and scored at a best-eval checkpoint; the faithful catfish A2 was scored at its **episode-99** checkpoint (3% of training, still in the ε≈0.95 exploration phase [I: linear ε 1.0→0.01 over 2000 ep ⇒ ε≈0.95 at ep 99]). Note also that margin-ON injection (IS_cat) had STABLE TD loss — [I] the DQfD margin may act as a stabiliser, not only as a demo-transfer channel.
- premises: divergence is the binding constraint on every learned arm's ceiling.

### B-29. Decoder invariance group / "change the decoder, not the Q" (and within-user gap flattening)
- mechanism: the corrected auction decode (`shift_to_nonneg=True`, per-user row-min outside option) is exactly invariant to `V'[u,a] = c·V[u,a] + d_u`, so any Q-side improvement that is a per-user offset or global rescale is invisible to deployment; the live channels are per-user bid STRENGTH dispersion (`top1 − rowmin`, varying across users) and within-user gap SHAPE. Proposed routes: measure/optimise those channels, or change the decoder so it consumes what Q mechanisms produce.
- intervention point: decode/deployment (and diagnostic)
- defined in: `CV2/DECODE-TRANSFER-FINDING-2026-07-12.md` §6.0, §7; causal probe `CV2/decode_gap_sensitivity_probe.py` → `DECODE-GAP-SENSITIVITY-RESULT.{A1-seed42,A1-seed137,synthetic}.json`.
- run status: invariance derived from code + causal eval-only gap probe ran (2 A1 ckpts, 28 null-space controls = exactly +0.0000); "change the DECODER" = "**NOT proposed, NOT costed**".
- run conditions: A1 (lr 0.01, corrected decode) checkpoints; family_b; k_c=1.
- recorded outcome: "**flattening** the within-user gap profile (`p>1`) buys **+6.8 / +8.5** decode-EE; **sharpening** it (`p<1`) costs **−13.1 / −23.7**" (`C3-GAP-REACH-PREREG…:47-49`); observational pass-through "decode_EE = 418.3 + 0.243 · argmax_EE … n = 8, R² = 0.80" — "the coordinated decode delivers ~420 EE on its own" (`DECODE-TRANSFER…:44-52`); learned-Q `gap_strength_cv` 0.000–0.023 vs myopic rule 0.314 (chronicle quote in `C3-GAP-REACH-PREREG…:33-36`). Thesis-level sentence recorded: "*The property that lets the coordinated decode work with an imperfect learned Q — its invariance to per-user value offsets and to global rescaling — is the same property that bounds how much any per-agent value improvement can contribute to the deployed objective.*" (`DECODE-TRANSFER…:386-388`). k_c sweep killed: "The only step in the 'weaken the decoder' direction is k_c = 0, and it is dead."
- premises: the deployed metric is scored through this specific decoder; Q improvements that matter must be decoder-visible.

### B-30. C3 gap-reach test — does the DQfD margin move the decoder-visible gap statistics? (instrument)
- mechanism: compare G-invariant gap statistics (`gap_margin_rel_mean`, `gap_strength_cv`, …) on margin-ON (C4) vs margin-OFF (C4m) vs OFF (C2) checkpoints, with C2's own seed range as the noise band.
- intervention point: other (instrument)
- defined in: `CV2/C3-GAP-REACH-PREREG-2026-07-12.md` (frozen 2026-07-12; file mtime 07-22 with 07-13 banner).
- run status: never run as of this file ("⟹ C3 has never been run. This prereg is written before it is."); later outcome in 07-13+ clusters.
- recorded physics fact (important for transfer): "`beam_power_w(L) = min(0.25 + 0.35·√L, 10.0)` (`family_b_geometry.py:374`) … `EE = b·log2(1+SINR)/power` with `SINR ∝ power` … MEASURED: load 1→40 ⇒ EE 1.000×→0.350× … **EE *PENALISES* load**" (banner citing `EE-LOAD-DEPENDENCE-{PREREG,RESULT}-2026-07-13`), and "users pushed out by the K-cap get `r1 = 0`, hence `EE = 0`. Collapse is punished by EXCLUSION" (`…:109-145`). "A null on EE is NOT a null on the mechanism" — C4−C2 2/3 inconsistent on EE but 3/3 on min_cov and cap_bump.

### B-31. Stronger delayed-consequence env — persistent (Lyapunov, paper Eq-1) queue + standing-backlog penalty, to make γ / catfish load-bearing (Track-2 + P2)
- mechanism: replace the H1 Convention-B queue (TTL expiry + overflow drops, drop-penalty only) with a persistent backlog `Q^{t+1}=max(Q−D,0)+α`, add a Lyapunov drift-plus-penalty `−V·ΣQ_c` to the reward, give capacity headroom (ρ=0.7) and predictable hotspot ramps, then measure clean foresight value with the scheduler held fixed.
- intervention point: other (environment + reward redesign)
- defined in: `CV2/TRACK2-QUEUE-ETIOLOGY-2026-07-08.md` §4; `CV2/P2-QUEUE-ENV-C3-SCREEN-2026-07-08.md` §1.
- run status: ran as non-learned cheap screens (Track-2 probe; P2 prototype, 8 seeds + robustness battery, ~30 s); no training.
- run conditions: Phase-C geometry (C=59 cells, S=12 served columns/step, γ_f=0.9, H=5); H1 numerics buffer_cap 2e8, TTL 10, AR(1) 0.85, 50 steps/ep, U=100, k_cap=3; non-learned planners (MaxWeight myopic, receding-horizon with pers/fore/clair oracles).
- recorded outcome: Track-2: H1 C3 Δ_fore +0.079% ≪ 3%; "FORESIGHT IS UN-ACTIONABLE in this env"; "the naive 'stronger queue' makes C3 headroom *smaller*, not larger" → NO-GO. P2: "**VERDICT: NO-GO. P2 closes here.** … value of demand foresight = 0.028% (primary), ≤ 0.97% (all variants) ≪ 3%"; first-run +7.07% "was a **scheduler-sophistication artifact**" (Δ_sched-art 2.7–9.2% even with a demand-blind oracle) (`P2…:3-20,97-128`).
- recorded cause: "on a work-conserving, persistent, capacity-headroom queue with a strong backlog-greedy (MaxWeight) baseline, **current backlog is a near-sufficient statistic for scheduling urgency**" (`P2…:130-136`).
- premises: catfish/γ need a delayed consequence to matter (the 07-09 γ-premise work later showed family_b already has one via r2); a demand queue creates actionable foresight (ruled out; also cited Lyapunov Lemma-1 "handover-frequency absorbable → greedy near-optimal", `SESSION-2026-07-09…:48`).

### B-32. Single-objective DQN specialists as landmarks / teachers, and "specialist Q through the coordinated decode" (DQN_EE, DQN_handover, DQN_loadbalance; view A vs view B)
- mechanism: train one-hot-preference DQN per axis; evaluate under per-user argmax (view A, deployable) and with the specialist's Q fed through the coordinated auction (view B).
- intervention point: objective (single-objective reward) / decode (view B)
- defined in: `CV2/DQN-LANDMARKS-PREREG-2026-07-08.md`; verdict `CV2/DQN-LANDMARKS-VERDICT-2026-07-08.md`; EVIDENCE-USABILITY DQN-1.
- run status: ran (3 modes × 3 seeds, 3000 ep).
- run conditions: family_b (U=100, k_cap=3, p_base 0.25); **DQN hparams differ from MODQN: "gamma 0.99, lr 1e-3, batch 256, replay 100k, target_sync 500 … MLP (256,256,128)+Tanh"** (`DQN-LANDMARKS-PREREG…:2`) vs MODQN lr 0.01, γ 0.9, [100,50,50]; from scratch; best-validation-J_w ckpt; E3 calibration.
- recorded outcome: "**Axis-imbalance** (the strong finding): no single-objective reward yields a balanced allocation — DQN_EE ignores HO/LB; DQN_handover freezes to 1 beam …; DQN_loadbalance games raw r3 by collapsing"; "**DQN_EE is the top single-preference EE learner + its Q is coordination-reusable** (view B: 492–510 EE at cov~1.0, > AF 448–454, approaching DQN_scalar 534–552)"; "`min_cov=0` is NON-DISCRIMINATIVE (universal under per-user argmax)" (`…VERDICT…:31-49`). DQN_EE view A per seed 476.7/442.1/153.5 (seed 271 collapsed) (`EXTERNAL-STIMULUS…:20`). T3: random valuations through the same auction reach 449.1 ≈ AF ⇒ the Q-specific increment ≈ +41 (DQN_EE) / +79 (recalib scalar).
- recorded cause: "DQN_loadbalance failure is partly designed-in (a per-user-independent Q-net structurally cannot optimize a joint r3 objective)".
- premises for use as teachers: specialist trained with a better optimiser config really is better-than-learner at the learner's operating decode (at k_c=1 teachers ~450–523 vs learner ~460–470 fresh; B-17).

### B-33. Coordinated capacity-aware decode over learned per-user Q (greedy submodular auction; the "framework engine")
- mechanism: at deployment, open physical cells greedily by marginal gain `Σ_u max(V[u,c]−best_val[u],0)` under per-slot k_cap (partition matroid) with k_c coordinated cells and k_cap−k_c argmax cells; per-user row-min outside option (FOLD-2).
- intervention point: decode/deployment
- defined in: `CV2/TRACK3-CORE-AUDIT-2026-07-08.md` §2–§3 (`decode_hybrid_corrected`, `decode_af_physical_auction`); EVIDENCE-USABILITY DL-2.
- run status: ran (every arm in this cluster is scored through it).
- run conditions: family_b; k_c=1, k_cap=3 (thesis operating point).
- recorded outcome: "de-collapse (min_cov 0↔>0 under same weights) = **grounded framework win** … MAY NOT: attribute the win to catfish (A2≈A1) or claim an EE win" (DL-2). Coordination experience does not transfer to argmax: A1 vs A1_xover min_cov 0.9986 → 0, served 1.0 → 0.2969 ("**100% 劑量的協調經驗都不轉移 ⟹ 30% 的導管注入不可能做到**", `CV2/CATFISH-EVIDENCE-MARKING-2026-07-09.md:59-70`). Cards: "greedy under partition matroid = **1/2** (FNW 1978)". Remove-coordinate route "NOT viable on current mechanisms" (B-21 T-C). Invariance-group limitation: B-29.
- premises: learned Q carries some decision-relevant per-user value (records: it adds ~+14..+21 over the decode floor; decode alone ≈420).

### B-34. CDRL Phase-I offline-oracle prefill of the catfish buffer (brute-force max-EE candidates seed the high-reward replay)
- mechanism: offline enumerate candidate actions per layout, compute EE, pick the max-EE candidate, and prefill the catfish (top-20% EE) and main buffers with those exemplars as "initial experience replay data".
- intervention point: experience
- defined in: source thesis via `CV2/CATFISH-CONCEPT-FIDELITY-BRIEF-2026-07-10.md` §2–§3 ("Source A — offline oracle (Phase-1 dataprep, §4.1) … This is an **offline brute-force optimizer, not a neural expert**").
- run status: never built in the old repo ("**無 Phase-I**（grep = 0）", `CV2/CATFISH-EVIDENCE-MARKING-2026-07-09.md:29`).
- recorded outcome: none. Marking doc: without Phase-I, ACRM, or a different decode, the co-trained catfish has "零有效不對稱" (zero effective asymmetry) so P1's null is "定義，不是發現" (by definition, not a finding); recommendation "先修 build（ACRM ON + Phase-I），或改變它的宣稱" (`…MARKING…:43-47,144-147`).
- premises: an oracle better than the learner can be computed per state (on family_b EE is per-step separable given the joint action, so a single-step model-based oracle exists — cf. PHYS arbiter B-15).

### B-35. Candidate-B — DQfD/AWAC advantage-weighted imitation retrain from a strong static planner (amortise the planner into the learner)
- mechanism: retrain the learner with demonstration loss (DQfD) + advantage weighting (AWAC/CRR) toward a slow EE planner (`planner_then_balance_t12`) or AF.
- intervention point: penalty/loss + experience
- defined in: `CV2/GATE-PLAN.md:58-63`; `CV2/gate-minus1-archaeology.md` (07-07; D5 = `p4-amortized-morl-FROZEN-design-spec-2026-06-23.md` §4).
- run status: never run ("0/11 = Candidate-B's post-fix DQfD advantage-weighted retrain → that experiment does NOT exist"); 11 earlier distill/imitation attempts D1–D11 were all pre-EE-fix except D11 (eval-only).
- recorded outcome (prior evidence): D11 "Gate ③ FAIL = the kill — a **zero-learning** `AF+balance` (5.128e8) **statistically TIES the planner ceiling** (5.279e8…)" and "`AF+balance` ≫ trained A1/A2 by ~17 %" ⇒ "B-PRIOR = RESET-TO-UNKNOWN, leaning-NEGATIVE" (`gate-minus1-archaeology.md:112,117,194`).
- wiring note for the synthesiser: none of the 11 old distillation attempts distilled a learner from a *frozen pre-trained main over a few rounds*; they distilled static planners/teachers (D11 never trained at all).
- premises: a planner better than the learner exists and its gap is learnable (D11: a zero-learning rule already closes 81% of the gap).

### B-36. Separate-trunk 3-DQN "shared-Q isolation" (one independent net per objective, trained and evaluated under per-user argmax)
- mechanism: test whether homogenisation is caused by a shared trunk across objectives by giving each objective its own net.
- intervention point: representation (architecture)
- defined in: `OLD/INJ-RUNG1-DISCUSSION/SHARED-Q-ISOLATION-PREREG-DRAFT.md`.
- run status: never run in this form (draft superseded by the IS line).
- recorded premise correction: "`build_augmented_q_nets` = THREE separate per-objective DQNs (`for _ in range(3)`, shaped_q.py:30) — 'shared' is across USERS only" (`CV2/INJ-RUNG1-ADJUDICATION-2026-07-11.md:39-40`) ⇒ the separate-trunk hypothesis tests an already-true condition; the sharing that matters is across users. Later disease statement: "**非「共享」本身，是「共享+輸入不可辨識」**" (not sharing per se, but sharing + indistinguishable inputs) (`CV2/TIER2-PREREG-SKELETON-2026-07-12.md` App. D).
- premises: cross-objective sharing causes homogenisation (FALSE as stated).

### B-37. Architecture ladder for cross-user homogenisation — ID-conditioning, partial/selective parameter sharing (SePS, Kaleidoscope masks, CDS private heads), per-entity embeddings (HPN), hypernetworks (HyperMARL), low-rank per-agent adapters (LoRASA)
- mechanism: give the shared per-user Q-network per-user capacity so identical inputs are not forced to identical outputs, while avoiding cross-agent gradient interference.
- intervention point: representation (architecture)
- defined in: `FBD/PRIOR-ART-CARDS-2026-07-10.md` Card 6; `FBD/DR-RUN2-CONSUMPTION-VERDICT-2026-07-11.md` §3b; `CV2/TIER2-PREREG-SKELETON-2026-07-12.md` App. D (Tier-3 trigger: only if input repair + loss/norm menu all fail to beat AF 448).
- run status: never built.
- recorded literature caution: "naive agent-ID concatenation into a shared trunk under-delivers, mechanism = cross-agent gradient interference (HyperMARL, NeurIPS 2025)"; "restored per-user diversity is not guaranteed additive with, and can degrade, a coordinator that was compensating for homogeneity" (EMERGING, R3DM/Amir) (`DR-RUN2…:89-105`). Rejected in App. D "不去清單": independent 100 Q-nets (sample starvation + identity), QMIX (anti-MR + ReBorn mixing pathology), naive LayerNorm (does not touch the user axis), quantile transform (loses magnitudes). "整換 sharedQ=另一篇論文" (replacing shared Q = a different thesis).
- premises: homogenisation is the binding constraint on EE (records increasingly doubt this: decoder invariance B-29; "de-correlation is a PASSENGER" B-28/Tier-1 §7).

### B-38. Action-gap / Q-ranking operators on the MODQN heads — dueling V+A, (persistent) Advantage Learning, distributional heads (C51/QR), ensembles, learning-to-rank losses
- mechanism: increase the separation of the best action's Q from runners-up so a downstream ranker (the auction) receives clearer rankings.
- intervention point: penalty/loss / representation (head/operator)
- defined in: `FBD/PRIOR-ART-CARDS-2026-07-10.md` Card 1.
- run status: never built ("If the wave shows Q-quality remains the binding constraint, THIS card is the next rung, starting with dueling + AL").
- LATEST revision: "this card's remedy shelf (dueling/AL/action-gap) carries its inductive bias on CROSS-ACTION discrimination; the observed pathology is CROSS-USER row identity … 'untested/unguaranteed', not 'cannot'" (`PRIOR-ART-CARDS` Card 1 correction 2; `FBD/DR-RUN3-CONSUMPTION-VERDICT-2026-07-12.md` §4 D6: "not a direct, guaranteed cross-user remedy; effect … UNTESTED here; screen-tier candidate only"). The sibling near-neighbour paper (Chou et al. arXiv:2605.02416) uses Dueling DDQN (DR-RUN1 §2). Also B-29's gap probe: sharpening per-user top-1 margins COSTS decode-EE (−13.1/−23.7) — [I] an action-gap enlarger could push the wrong way for this decoder.
- premises: the auction consumes cross-action ranking quality (partly true: it reads within-user gap shape and bid strength, B-29).

### B-39. Preference-conditioned / envelope MORL, CCS-derived weights, Bayesian optimisation over weight vectors (replace hand weight search)
- mechanism: one weight-conditioned network over the weight simplex (envelope Q, PD-MORL), or pick candidate weights from the convex-coverage-set corner points / BO instead of a hand grid.
- intervention point: objective
- defined in: `FBD/PRIOR-ART-CARDS-2026-07-10.md` Card 2.
- run status: never built ("Heavy refactor; not thesis-timeline"; "CCS/BO is the upgrade if a second round happens").
- recorded context: the 3 weights "are ALREADY swept (MO-sweep 18 runs, G6-SOUND: no learned arm beats AF on EE across the simplex)" — but that MO-sweep is E2 era (EE=0.009% of objective, D2b) per EVIDENCE-USABILITY CF-4 [I: so the "already swept" statement rests on a defective-era sweep].
- premises: the best operating weight is not yet found; weight choice is a binding lever.

### B-40. Other ingestion channels for external experience — n-step demo returns, demo-prioritised replay (PER bonus), supervised pretrain phase, Kickstarting-style distillation aux loss annealed to 0, potential-based shaping Φ from a teacher's frozen Q, advantage-weighted BC (AWBC), counterfactual same-state EE advantage
- mechanism: alternatives to ρ-mixing + margin for getting teacher knowledge into the learner.
- intervention point: experience / penalty/loss / reward (PBRS)
- defined in: `FBD/PRIOR-ART-CARDS-2026-07-10.md` Card 3; `CV2/STRATEGY-REVIEW-VERDICT-2026-07-10.md` Q5; `CV2/INJECTION-DESIGN-DECISION-BRIEF-2026-07-10.md` (R6: "Stage-2 candidates recorded: counterfactual same-state EE advantage · contiguous n-step demo bundles"); `CV2/INJECTION-LITERATURE-ANCHORS-2026-07-10.md` (Kickstarting "λ annealed→0").
- run status: never built.
- recorded rulings: "KEEP DQfD-family (codex; Gemini's AWBC refuted — learner-Q advantage weighting discards exactly the novel low-overlap demos worth injecting; Φ-shaping = reward-channel, out of scope)" (brief v5.4 R6); cards: PBRS "is THE provably-invariant channel (Ng 1999 …); keep as a card option, not dismissed forever"; n-step demos need trajectory pools ("our pools are step-bundles, no trajectories").
- premises: a teacher better than the learner at its decode exists (thin at k_c=1, B-17); the bottleneck is the ingestion channel rather than the representation.

### B-41. Assignment/credit alternatives for the coordination layer — Hungarian/optimal assignment, optimal transport (soft assignment), difference rewards / COMA counterfactual credit ("Branch C"), mean-field approximations
- mechanism: replace the greedy auction or give per-user counterfactual credit so a shared Q learns each user's marginal contribution.
- intervention point: decode/deployment (Hungarian/OT) or reward (difference rewards/COMA)
- defined in: `FBD/PRIOR-ART-CARDS-2026-07-10.md` Card 4 ("difference rewards / COMA counterfactual credit (= the decision-map's Branch C, precedented cure for shared-Q homogenization, never executed here)").
- run status: never built ("Branch C would be an ALGORITHM contribution … post-thesis material honestly").
- related record: CATFISH-EVIDENCE-MARKING N1 inference — "`χ_u` 依設計只用動作前資訊 … 實際競爭度對每個使用者是不可觀測變數 ⟹ per-user `Q` 無法條件化於它。解崩只能來自 (i) decode 看見聯合動作，或 (ii) state 洩漏它" (hypothesis) — i.e. per-user Q cannot see realised contention unless the decode sees the joint action or the state leaks it.
- premises: homogenisation stems from missing per-user credit / unobservable contention.

### B-42. Multi-objective conflict framings — CMDP/Lagrangian constraint formulation; gradient-conflict remedies (PCGrad, CAGrad); Pareto (EE, min_cov) projection presentation; worst-user / max-min framing
- mechanism: treat coverage/fairness as a constraint with a Lagrange multiplier instead of a scalarised weight; or de-conflict per-head gradients; or present the specialist-vs-MO trade-off as a non-dominated 2-D projection.
- intervention point: objective (CMDP) / penalty/loss (gradient surgery) / other (presentation)
- defined in: `FBD/DR-RUN1-CONSUMPTION-VERDICT-2026-07-11.md` §5 (PROPOSED-2/3) and §1 (flash H4 "CMDP-baseline counter").
- run status: never built; queued eval-only check "random-valuation-through-corrected-decode min_cov at the thesis operating point" (§3e, not run in this doc).
- recorded status: gradient-conflict = "**candidate explanation to DISCUSS, not an established attribution** — no local gradient-conflict measurement exists"; Kurin et al. (unitary scalarisation) = disclosed counter-position; CMDP "disclosed alongside it".
- premises: learner deficit is multi-task value interference (untested); the MO point is not dominated by the random-through-decode floor (unchecked here).

### B-43. Representation-first-then-inject ordering principle
- mechanism: do not re-run experience injection until the value representation is measurably de-collapsed; measure with srank/CKA/effective rank/SND instead of row-Pearson.
- intervention point: other (sequencing / instrumentation)
- defined in: `FBD/DR-RUN2-CONSUMPTION-VERDICT-2026-07-11.md` §3e, §4 ("ADOPTED … representation-first ordering principle"); instrument upgrade `FBD/DR-RUN3-CONSUMPTION-VERDICT-2026-07-12.md` §4 (srank_δ(Φ), CKA, NC1, dormant-neuron ratio; action-gap as a separate tier).
- run status: principle adopted; partially enacted by IS v2/v3 (B-20/B-21), whose injection-under-standardisation contrast was +35.67 (REPLACE, fragile) then +4.0 n.s. (concat).
- premises: injection failed because the representation could not carry per-user distinctions (NOT-ADJUDICABLE at the wave; later decoder-invariance finding B-29 offers a competing explanation).

### B-44. "Coordinated catfish" — build coordination into the catfish and drop external coordination
- mechanism: let the catfish agent act with the coordinated decode and inject its (coordinated) experience so the main learns coordination through replay.
- intervention point: experience
- defined in: `CV2/CATFISH-EVIDENCE-MARKING-2026-07-09.md:152-153` ("「協調式鯰魚（把協調做進鯰魚、丟掉外部協調）」是否可行").
- run status: never built; planned 6-run negative control recommended cancelled.
- recorded outcome/cause: "controller 主張由 (N1) 直接否證" — N1: a Q trained 100% on coordinated-decode rollouts, deployed with argmax, collapses (A1_xover min_cov 0, served 0.297) ⇒ "100% 劑量的協調經驗都不轉移 ⟹ 30% 的導管注入不可能做到" (`…:59-70`); "capitulation 風險已明文送審" (sent to review).
- premises: coordination knowledge can be carried by experience rather than by the decode (records: FALSE for per-user argmax deployment on family_b).

### B-45. Cross-over deployment — argmax-trained Q + value-stratified bundle deployed through the coordinated decode (B2_xover)
- mechanism: train with per-user argmax (with χ_u state augmentation + catfish bundle), deploy with the coordinated auction.
- intervention point: decode/deployment
- defined in: `CV2/CATFISH-EVIDENCE-MARKING-2026-07-09.md` N2; EVIDENCE-USABILITY CF-3.
- run status: ran (route-B factorial, n=3, E1 era).
- recorded outcome: "`J_w = 5.266e-4`、… `min_cov = 0.9993` —— **兩項都是全庫 learned arm 最高**"; B2_xover − B1_xover = +10.6% J_w / +6.1% EE; then demoted: E1 ÷G_T EE is per-user gain-weighted so concentrated arms are inflated ⇒ "**N2 從「線索」降級為「疑似 artifact」**"; later CF-3 (latest): "survives corrected re-score **+9.6% `J_w` / +5.7% EE**; **NOT a `G_T` artifact** (retraction-of-retraction); **still not a win** (`D3` no seed variance)".
- premises: training-decode ≠ deployment-decode can help (train/eval mismatch class that voided route-C elsewhere).

### B-46. χ_u state augmentation — pre-action per-user signal-ranking features appended to the shared-Q input (224-d "augmented" state)
- mechanism: append per-user symmetry-breaking features (e.g. the user's signal ranking) computed only from pre-action information, so identical-looking users get distinguishable inputs.
- intervention point: representation
- defined in: route-B factorial (`state_aug: true`); discussed `CV2/CATFISH-EVIDENCE-MARKING-2026-07-09.md:72-80`; DR-RUN2 §3b.
- run status: ran (route-B factorial B1/B2 argmax arms with χ_u, n=3, E1 era; and every 224-d arm in this cluster).
- recorded outcome: "`B1`（argmax + `χ_u` + plain）vs `B2`（argmax + `χ_u` + bundle）… **六位有效數字全等** … ⟹ 「argmax 臂沒有對稱破壞輸入」的混淆**不存在**" (six metrics identical to 6 significant figures; the "no symmetry-breaker" confound does not exist); DR-RUN2: "consistent with our χ_u augmentation barely moving the needle (0.971→0.956, itself an unverified server number)". Wave q_internals (224-d arms, corrected decode): user-row Q Pearson 0.994–1.000 despite χ_u.
- recorded cause (hypothesis): realised contention is unobservable pre-action, so χ_u cannot tell users what they need (B-41 quote); literature: naive agent-feature concatenation under full sharing suffers gradient interference.
- premises: homogenisation is due to indistinguishable inputs (the later IS line shows cross-user standardisation de-flattens where χ_u did not).

### B-47. (methodology card, not a learning concept) Prior-art-first + DR-before-freeze + collide-PRIMARY-sign-with-own-evidence + two-pipeline reconciliation + guards-that-can-fire
- defined in: `FBD/PRIOR-ART-CARDS-2026-07-10.md` Card 5; `FBD/DR-METHODOLOGY-SYNTHESIS-2026-07-11.md` §1/§3; `CV2/GAMMA2-ABLATION-PREREG-AMENDMENT-2026-07-09.md:229-230` ("before finalizing any prereg or dispatch prompt, collide PRIMARY's predicted sign with that document's own cited motivating evidence; a mismatch is a BLOCKER").
- run status: adopted as process. Listed only so the synthesiser can see recurring defect classes that produced several nulls in this cluster: guard tolerance 29× tighter than noise (B-6), min-seed rule monotone on supersets (B-12), wrong-sign PRIMARY (B-7), instrument inside the decoder's null space (B-29), probe on a different input distribution than eval (Tier-1 §3), selection clause non-binding (B-12/B-17).

---

## 2. Cross-cutting facts the synthesiser will need (collected from the entries; each with its source)

1. **Environment**: every trained run in this cluster is `family_b` (U=100, 10-step episodes, k_cap=3, k_c=1 thesis point), E3 calibration, weights [0.5,0.3,0.2]. The collapse disease is per-user argmax + fully shared-across-users per-objective Q (three separate per-objective nets; sharing is across users — `INJ-RUNG1-ADJUDICATION…:39-40`). Learned Q rows are near-identical across users (Pearson 0.994–1.0) on raw input; raw-input init is already flat (Card 7).
2. **Learning rate**: every MODQN/catfish/injection/IS arm used lr 0.01 (base prereg) with Adam, no gradient clipping; TD loss explodes 400–1300× shortly after the best checkpoint; best checkpoints median at 30% of training; the faithful catfish A2 was scored at episode 99 (`TRAINING-DIVERGES-FINDING…`). The DQN teachers/landmarks used lr 1e-3, γ 0.99, bigger nets — a different, likely more stable optimiser config (B-32).
3. **Wiring**: all learners trained from scratch; catfish co-trained; external teachers were frozen separately-trained DQNs feeding replay pools. No run distilled a main from a frozen pre-trained main over a few rounds (B-35 note).
4. **Metric**: EE = per-user mean of R_u/p_alloc,u with unserved users = 0 (mean-of-ratios), scored through the coordinated corrected decode at k_c=1 on a best-eval checkpoint; J_w calibrated; min_cov = min-over-users served fraction. No pooled ΣR/ΣP EE is reported anywhere in this cluster.
5. **Decode dominance**: the decode alone yields ≈420 EE (random-Q-through-decode 424–436; AF 448); learned Q adds ~+14..+115 depending on quality with pass-through ≈0.24 (B-29); the decode is exactly invariant to per-user offsets/global rescales, so many Q-side improvements are invisible (B-29).
6. **Physics**: per-beam power grows with √load and EE penalises load; handover r2 is an immediate per-transition cost with a_{t-1} in state; at the thesis weights one φ2 handover costs ≈ the full per-user EE of one step (break-even ΔEE 505.9 at γ=0) so rational policies rarely churn and the γ₂ amortisation window is small and calibration-dependent (B-7, B-11).
7. **Trainer defects recorded here**: per-head bootstrap from each head's own max (explicitly noted, `EE-CATFISH-PREREG…:31-33`); outage → r1=0 (cap-bumped users), r2/r3 behaviour when unserved not discussed; ckpt selection and EpisodeLog on RAW (uncalibrated) weighted reward (base prereg) [I: raw r1 ~1e8 dominates]; reset-to-action-0 step-1 handover artifact (B-11); F5-leaky hybrid decode in training for several arms (D5).
8. **Only positive signals in the cluster** (all scoped): expert delegation F>L (deployment-time AF on non-coord beams, USER ruled out as deliverable, B-14); IS_injection +35.67 EE on the REPLACE-standardised substrate (fragile, not replicated under concat, B-20/B-21); B's CI above AF (not injection-attributable, B-17); margin-ON injection kept TD loss stable (0.9–1.6× vs 400–1300×) and sustained cross-user target std ~30× (B-21/B-28; decoder-visibility of that effect disputed, B-29/B-30); B2_xover +9.6% J_w / +5.7% EE without seed variance (B-45).
