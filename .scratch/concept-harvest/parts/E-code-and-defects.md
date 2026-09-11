# E — Old-project code inventory and trainer defect check

Worker: read-only extraction, 2026-09-11. Old repo = `/home/u24/papers/modqn-paper-reproduction` (HEAD 8cb4aa66), paths below relative to `src/modqn_paper_reproduction/` unless prefixed `archive/` (= `archive/src-eras/`). New repo = `/home/u24/papers/mcrl-leo-handover`.
Every claim is marked [親驗] (read the line myself) unless noted.

## 0. New-project defect shapes (confirmed first)

- (a) per-head bootstrap: pre-fix line was `q_next_max = q_next_all.max(dim=1).values` inside the per-objective loop (shown as a `-` line in `git show 5219995a -- src/mcrl/algorithms/modqn.py`). **Already fixed in the working tree** by commit 5219995a "B0 D-1": `modqn.py:652-686` now computes `q_next_scalarized = Σ w_k Q_target_k(s')`, masks, takes `shared_next_action = argmax` (`modqn.py:668`) and gathers every head at it (`modqn.py:679-686`). Vanilla (target-net select + target-net evaluate), not Double-DQN. [親驗]
- (b) outage free ride: `env/step.py:1051-1105` — unserved user -> `realised = UNSERVED`; `classify_handover` returns `NONE` when current is unserved (`env/action_contract.py:447-448`) so r2 = -HANDOVER_COST[NONE] = 0; r3 = `-user_beam_load()` which is 0 for unserved (`env/service.py:164-182`, `277`). Served steps have r3 = -U_b <= -1 and r2 in {0,-0.5,-1}. Mitigations present: the re-entry step is charged φ2=1 (`action_contract.py:449-450`), and no-op (empty-mask) transitions are dropped (`modqn.py:1435-1441`), but a transition whose chosen action ends unserved is pushed (`modqn.py:1443-1452`). `runtime/outage_gate.py:1-30` documents the hole. [親驗]
- (c) uncalibrated logged scalar: `modqn.py:1443` pushes `apply_reward_calibration(reward_vec)` to replay, while `EpisodeLog.scalar_reward` = `scalarize_objectives(avg_reward, w)` over RAW `avg_reward` (`modqn.py:1479`, `1496`); calibrated means are now logged beside it (`modqn.py:1480`, `1502-1504`) but the headline scalar and best-eval selection (`modqn.py:1520-1521`, eval `mean_scalar_reward` from `modqn.py:845`) stay raw. [親驗]

## 1. Defect table — old-project trainers

Legend: (a) YES = each head bootstraps at its own `max_a'` (no single policy); NO = every head gathered at one shared action a' chosen from the scalarised Σw·Q (plus decode). (b) = unserved user gets r2 = r3 = 0 while served users pay. (c) = logged `scalar_reward` built from RAW rewards while replay gets calibrated ones. "(c) latent" = the code shape is there but the recorded runs had calibration OFF, so logged == trained.

**Env facts that decide (b) for every old trainer** [親驗]: no old env gives a per-user outage free ride. Base `env/step.py:784-866` gives every user a beam (empty mask → action 0, `algorithms/modqn.py:292-294`); r3 = `-gap/U` is ONE global number, the same for all users (`env/step.py:858`); r2 is charged on beam change (`env/step.py:1310-1329`). HOBS-faithful / realistic-cells envs inherit that `_compute_rewards` (`env/hobs_faithful_step.py` defines no reward method). Family-B `env/family_b_step.py:1432-1456`: r3 = `-(gap/U)` global (1455), r2 charged from the *action's* physical (sat, cell) ids whether or not the link was admitted (1432-1436, 1467-1472); unserved users only lose r1. Family-B-r3 corrected r3 = a global Jain-occupancy scalar in [-1,0] (`family_b_r3/contracts.py:830-852`). So **(b) = NO for every old trainer**. The new project's (b) comes from its per-user decomposable r3 = −U_{b_u} (new `env/service.py:264-277`), which the old envs never had. Porting any old mechanism brings no (b) protection with it.

**Calibration fact that decides (c)** [親驗]: base `TrainerConfig.reward_calibration_enabled=False` (`runtime/trainer_spec.py:98`); every Family-B lineage run builds its config from a prereg with `reward_calibration.enabled=true` (`family_b_retrain/runner_support.py:568`; `docs/research/env-foundation/retrain-prereg-family-b.json` arm.reward_calibration: scales r1=2.34e15, r2=300.3, r3=6.13e9). All 413 `artifacts/**/run_metadata.json` agree: Family-B/route-B/shared-Q/abl9k/waveE/fulldqfd runs have calibration True, while paper-baseline, Route-A catfish pilot, coordinated-multi-catfish pilot and realistic-cells runs have it False. Symptom in the records: `waveE_ON/seed-137/run_metadata.json` `floor_scalar_mean = 3.745e9` is a raw-unit scalar.

| # | Trainer (class @ file) | (a) bootstrap | (b) | (c) logged scalar | lr default / recorded | Evidence (file:line) |
|---|---|---|---|---|---|---|
| 1 | `MODQNTrainer` @ `algorithms/modqn.py` (base) | **YES**, per-head own max | NO | YES shape, active only if calib on (latent in paper-baseline runs) | 0.01 (`trainer_spec.py:56`) | `update()` 753-767, max at 763; `_update_from_arrays` 691-697, max at 696; push calibrated 1238, log raw 1273/1282; best-eval raw 1299 |
| 2 | `OffsetMaskedMODQN` @ `offset_fix/trainer.py:19` | YES (inherits 1) | NO | latent | 0.01 | only overrides `_encode_states` (54-70) |
| 3 | `FamilyBRetrainMODQN` @ `family_b_retrain/trainer.py:446` (+ `FamilyBRetrainMODQNReDo` `redo_trainer.py:167`) | **YES** (inherits 1) | NO | **YES, active** | 0.01 (prereg); 0.001 in the lr001-ep9000 preregs | `update`/`_update_from_arrays` just call super (542-548); r-vector 662-705 |
| 4 | `CatfishFaithfulFamilyBMODQN` @ `catfish_faithful_familyb/trainer.py:102` | **YES** on all 3 paths (main `self.update()`, catfish critic, 70/30 conduit all go to modqn.py:696/763) | NO | **YES** | from prereg (0.01) | catfish `_update_from_arrays` 423-431; conduit 473-479; main loop push calibrated 745, `ep_reward += reward_vec` raw 755, log 789, best-eval raw 807 |
| 5 | `RouteBFactorialMODQN` @ `route_b_factorial/trainer.py:46` | **NO**: a' = column decode over the ONLINE scalarised Σw·Q (261-267), each head's TARGET gathered at a' (286). Double-DQN + per-objective γ (287) | NO | **YES** | 0.01 (prereg), `optim.Adam` 141 | raw `ep_reward += rv` 386, log 416-421, best-eval raw 435 |
| 6 | `RouteBFaithfulCatfishMODQN` @ `route_b_factorial/faithful_catfish_trainer.py:96` | **NO** (main, catfish critic at γ_CF, conduit all use `_route_update_from_batch` 244-295) | NO | **YES** | 0.01 | raw 557, log 612, best-eval 626 |
| 7 | `InjectionRung1Trainer` @ `injection_rung1/trainer.py:51` | **NO** (`_inj_td_losses` 145-194: online scalarised a', target gather 191); one combined backward over the 3 heads + margin (266-278) | NO | **YES** (inherits 5) | 0.01 / waveE 0.001, 0.003 / fulldqfd 0.01, 0.001 | pretrain 292-359 |
| 8 | `StandardizedInjectionRung1Trainer` @ `shared_q_isolation/trainer_std.py:46` | NO (inherits 7) | NO | YES | inherits | encode-only override 67-75 |
| 9 | `ConcatInjectionRung1Trainer` @ `trainer_concat.py:41` | NO | NO | YES | rebuilds Adam at `config.learning_rate` (66) | |
| 10 | `ConcatFaithfulCatfishMODQN` / `ConcatCatfishE5Trainer` @ `trainer_concat_catfish.py:143,206` | NO (inherits 6) | NO | YES | 52, 62 | |
| 11 | `ConcatCatfishInjectionMODQN` @ `trainer_concat_catfish_inject.py:264` | NO (7's `_route_update` via MRO) | NO | YES | inherits | MRO note 226-243 |
| 12 | `E5LoggerMixin` / `ConcatE5Trainer` / `RawE5Trainer` @ `trainer_e5.py:34,167,171` | NO for training. **But the E-5 diagnostic** computes its "bootstrap term" with a per-head UNMASKED `max` (140), which is not the bootstrap the trainer uses; its cross-user-std readouts describe a per-head-max target | NO | YES | inherits | probe 123-149 |
| 13 | `PenaltyMixin` / `RawPenaltyE5Trainer` @ `trainer_penalty.py:128,503` | NO (a verbatim copy of 5's loop, 254-289) | NO | YES | inherits | penalty inserted per head 294-302 |
| 14 | `ConcatCatfishCapacityE5Trainer` / `AcrmCatfishMODQN` @ `catfish_pack.py:507,254` (the abl9k 9000-ep ablation trainer) | NO (inherits 6) | NO | YES | **0.001** (abl9k/ep2k run_metadata) | ACRM 300-457; L_cap via `capacity_penalty.py:94-137` |
| 15 | `FaithfulMODQNAblationTrainer` @ `modqn_faithful_ablation/trainer.py:332` (the 6-arm matrix) | **YES, on purpose** ("paper-faithful": each objective samples its OWN item batch AND takes its own masked max, docstring 8-11; `_update_objective_batches` 700-757, max at 725) | NO | **YES** (raw `episode_reward += reward`, log `_episode_log_template` 1427-1447) | **0.001** pinned (`config.py:348`), pilot sweep {0.001,0.003,0.01} (243) | catfish/capacity use the same `_update_objective_batches` |
| 16 | Phase-1 trainer @ `modqn_faithful_ablation/phase1_trainer.py` | **YES** (335-341, same pattern) | NO | inherits 15 | 0.001 | |
| 17 | `PreqEERouteBMODQN` @ `preq_ee/trainer.py:77` | NO (inherits 5) | NO | **YES** (docstring 7-9: "EpisodeLog r*_mean / eval metrics / ckpt selection stay RAW") | 0.01 | only r1 slot overridden 151-189 |
| 18 | `CommonFactorialTrainer` @ `family_b_r3/common_trainer.py:181` | **NO** (`update_common` 458-520: `decode_with_audit` over online scalarised values 427-456, target gather 508) | NO | **PARTIAL**: `EpisodeLog.scalar_reward` still raw (753) but a calibrated `mean_calibrated_weighted_scalar` is logged beside it (741, 762) | **0.001** pinned (290) | |
| 19 | `DQNScalarTrainer` @ `algorithms/dqn_scalar.py` | N/A (single scalar Q; own max is correct, 196) | NO | latent | 0.01 | |
| 20 | `coordinator_dqfd_zscore/` | **no trainer.** Non-runnable declarative plan (`study_plan.py:1-7`); `dqfd_margin.evaluate_dqfd_margin` (297-395) is a detached audit of a scalarised margin | — | — | — | |
| 21 | ISO harness `ISO_M` (shared-trunk 3-head) vs `ISO_S` (single head) @ `field_baselines/shared_q_isolation.py:230-360` | **YES in ISO_M**: `nq = ...max(dim=2).values` gives a (B,3) per-head own max (343); ISO_S is a single scalar head (N/A) | n/a (family_b) | n/a | db defaults | **Consequence:** the ISO experiment that located collapse in the "MODQN value-decomposition bundle" (docstring 5-13: ISO_M collapses, ISO_S spreads) changed (a) together with the head architecture. The per-head bootstrap is one of the confounds inside that "bundle" |
| A1 | archive `CatfishFaithfulMODQN` @ `archive/src-eras/catfish_faithful/trainer.py:101` (Route-A pilot) | **YES** (main `self.update()` 1088; catfish 605; conduit 664 → modqn.py) | NO | latent (pilot calib False) | 0.01 | |
| A2 | archive `OffsetMaskedCatfishFaithfulMODQN` @ `catfish_offset_fix/trainer.py:9` | YES (MRO → A1) | NO | latent | 0.01 | |
| A3 | archive `PerObjectiveCatfishMODQN` @ `per_objective_catfish/trainer.py:77` | **YES** (main `self.update()` 644; each catfish-j and its intervention = single-head own max 237-241) | NO | YES shape (626, 676) | 0.01 | |
| A4 | archive `CoordinatedMultiCatfishMODQN` @ `coordinated_multi_catfish/trainer.py:127` | **YES**, and it disagrees with its own deployed decode: acts by sequential occupancy decode but bootstraps per-head max (`_update_coordination` 495-513 → modqn.py:696; single-head 560-564). `sequential_decode/trainer.py:17-21` names it "the explicit anti-pattern" | NO | latent (pilot calib False; shape 1004/1062) | 0.01 | |
| A5 | archive demo-guided CF net @ `demo_guided_catfish/shaped_q_trainer.py` | **YES** (`_masked_max_next_q` 346-355 per head; `shaped_td_target` 358-384; each head trained alone via `cf_train_step`) | NO | n/a (probe harness) | — | |
| A6 | archive `sequential_decode/trainer.py` (C1 kill-test) | **NO** (target-net sequential decode a', every head gathered at it: 300-319, 369-373) | NO | **NO for ckpt selection** (calibrated J_w eval override 22-25, 389-393) | 0.01 | |
| A7 | archive `catfish_generic_killtest/trainer.py` | N/A (single-head Double-DQN 402-403; DeepSea/MountainCar) | n/a | n/a | 1e-3 (229) | |
| A8 | archive `coordinator_catfish/` | no trainer (`__init__.py:1-6`: "no live scheduler, trainer update ...") | — | — | — | |

**What Section 1 says about the old findings.** (a) splits the old evidence into two lineages. **Lineage P (per-head max): rows 1-4, 15-16, 21 (ISO_M), A1-A5.** This covers the paper baseline, Family-B retrain, Route-A catfish, faithful-familyB catfish (C1FIXED), per-objective / coordinated multi-catfish, and the whole 6-arm `modqn_faithful_ablation` matrix. **Lineage S (shared scalarised action, Double-DQN): rows 5-14, 17-18, A6.** This covers route-B, injection/DQfD, every shared-Q-isolation arm (z-score, concat, penalty, E5), the abl9k/ep2k catfish-pack ablation, preq-EE and family-B-r3. The mechanisms that ran in lineage S (DQfD injection + qw_sd margin, concat z-score, capacity penalty, ACRM, faithful catfish on route-B) were never exposed to (a). (c) is present in essentially every Family-B-era trainer, because checkpoint selection (`best-weighted-reward-on-eval`) ranks on the raw scalar, which r1 dominates (raw r1 scale ~1e9-1e15 against r2 ~1). So old "best checkpoints" were effectively picked on r1.

**Distillation from a frozen main?** [親驗 grep]: no old trainer distils from a frozen copy of its own main network (no KL or policy-distillation loss anywhere in `src/` or `archive/src-eras`). What the old code does instead is **demonstration injection from frozen teachers**: frozen DQN_EE / DQN_scalar / AF-rule / F-mean-solver pools (`injection_rung1/pool.py`, `fmean_pool_builder.py`), frozen *self* checkpoints (`self_pool_builder.py:9-15`, `ckpt:<path>` source), and the frozen catfish *challenger* nets (`challenger_pool_builder.py:1-45`). Separately there is a planner-to-student distillation probe outside the trainers (`analysis/family-b-collapse-diagnosis/p4_distillation_fidelity_probe.py:1-30`, teacher = `planner_then_balance_t12`).

## 2. Mechanism inventory (old code → port facts)

The new trainer, restated so the port notes below are comparable: a single `update()`; three Q-heads, each with its own Adam; one uniform FIFO item replay of 7-tuples `(s(112), a, r(3), s', mask(28), next_mask, done)`; obs = 4×28 [access one-hot, SINR, off-axis angle, prev-step beam load]; 28 user-relative actions; U=100; 10 steps per episode.
**The old base state is the same 4×28=112 layout** (`runtime/state_encoding.py:18-19, 81-83`: `[access, log1p(SNR), theta, load]`), so any encode-level mechanism written for the old 112 (`modqn_faithful_ablation/encoding.py`) maps onto the new obs one-to-one. Old route-B and shared-Q code sits on 112+84 χ = 196/224 (`route_b_factorial/shaped_q.py:1-9, 25-27`) or 140 (family_b_r3 / coordinator), and needs the χ feature or a re-width before it ports.
Common port obstacle: most route-B-era mechanisms assume **step-bundled replay** (`route_b_factorial/replay.py:1-16, 65-160`: stores all U users of a step so the joint decode / cross-user statistics can be recomputed at update time). The new item FIFO lacks that. A mechanism marked "needs bundle" requires either a step-bundle replay or an encode-time population-context capture (the trick `capacity_penalty.py:72-93` uses, which is replay-free).
"Runs" below = what I found in `configs/` + `artifacts/**/run_metadata.json` (413 files). "none local" = no run_metadata in this checkout; server-only results may exist elsewhere.

### 2.1 shared_q_isolation/

- **penalties.py — Q-row decorrelation and Kumar srank penalty.**
  - What it does: adds a loss term against the two measured symptoms of shared-Q collapse.
  - Intervention: penalty-loss, per head.
  - Code: `q_row_decorrelation_penalty` 121 (mean |off-diag Pearson| across user Q rows); `srank_penalty` 172 (σ_max²−σ_min² of penultimate features, Kumar Eq. 6); `penultimate_features` 161; `srank_diagnostic` 194 (non-differentiable readout); `PENALTY_KINDS=("decorr","srank")` 71; `KUMAR_ALPHA_DEFAULT=0.001` 62. Consumed by `trainer_penalty.PenaltyMixin` 128-343 (knobs `penalty.{kind,coef,interval=1,log_every=10}`; coef=0 is the bit-identity control).
  - Tests: `shared_q_isolation/tests/test_penalty.py`.
  - Runs: configs `configs/shared_q_isolation/tier1b/TB-DECORR-{lo,hi,escape}.yaml`, `TB-SRANK-{kumar,nudge,parity}.yaml`; no local run_metadata.
  - Port: **already ported** to new `src/mcrl/runtime/collapse_penalty.py`, off by default, hooked at new `modqn.py:690-705`. srank is item-replay friendly (minibatch features). decorr needs a full (U,A) snapshot of one step: the old code took `step_next_ctx[item_step[0]]` from the bundle (`trainer_penalty.py:204-211`), so on the new FIFO it needs encode-time capture.
  - Caveat: old evidence for it is "READINESS-ONLY" (collapse_penalty.py:36-40 audit).
- **capacity_penalty.py — M4 capacity penalty "容量懲罰" L_cap.**
  - What it does: puts a squared per-satellite top-k_cap intent-tail penalty on the softmax of row-normalised scalarised Q.
  - Intervention: penalty-loss on all 3 heads jointly.
  - Code: `capacity_penalty_loss` 148-182 (Ṽ = per-row z over valid actions; q = softmax(Ṽ/τ); p_b = Σ_u q aggregated to physical beam via `(a//7)*grid + slot_cell`; T_ℓ = Σ − TopK_{k_cap}; L = λ Σ_ℓ (T_ℓ/U)²); `CapacityPenaltyMixin` 40-146 (captures the population context at `_encode_aug` 72, applies one extra grad step before the TD update at `_route_update` 94-107); `ignition_selftest` 185.
  - Knobs: `capacity_penalty.{enabled, lam, tau=1.0, every=1}`; the recorded runs use lam 0.05.
  - Tests: `shared_q_isolation/tests/test_capacity_penalty.py`, `tests/test_system_ee_acrm.py`.
  - Runs: **enabled in recorded runs**: `abl9k_capacity`, `abl9k_full_*` (abl9k-2026-07-19, ep2k-2026-07-20, diag-winrate; lr 0.001, 9000 ep), plus `lamsweep_*` configs (λ ∈ {0.0125…0.2}) and `offm4_*`.
  - Port: **easy and replay-free.** It needs the current population's encoded states, masks, and an action→physical-beam key. The new env has one: 28 user-relative actions → (sat, cell) via `action_contract` cell_ids. Also needs k_cap. A local copy for the item-replay learner exists at `modqn_faithful_ablation/capacity_penalty.py:19`.
- **coord_catfish.py — "協調者鯰魚" CC coalition counterfactual transitions.**
  - What it does: every K steps it proposes a coalition joint action that moves cap-bumped users onto beams that win top-k admission, executes it in a DEEPCOPY of the env, and pushes that real auxiliary transition into replay. Deployment is unchanged.
  - Intervention: experience (auxiliary data).
  - Code: `propose_coalition` 198, `resolve_topk_admission` 141, `execute_in_cloned_env` 325, `CoordCatfishMixin` 342-475, `coordination_selftest` 496; `TOP_N_ACTIONS=3`, `MIN_COALITION_SIZE=2` (68-69).
  - Knobs: `coord_catfish.{enabled, every=5, min_gain=1}`.
  - Tests: none found by name in tests/; archive `test_coordinator_catfish.py` covers the archive twin.
  - Runs: config `v3/offcc_coord_lr001.yaml`; no local run_metadata.
  - Port: medium. The new trainer needs env deepcopy (the new `StepEnvironment` has a `commit=False` counterfactual reward path, `env/step.py:1051-1063`, but not a full-state clone contract), plus the physical-key map. It fits an item FIFO, because the aux transition is pushed per user.
- **catfish_pack.py — the abl9k mechanism pack: ACRM + composition.**
  - What it does: ACRM (linear differential competitive reward) r^C = r^CF + η_w(r^CF − r^M). r^M comes from the MAIN policy's greedy joint action on the same pre-action state, obtained by deepcopying the catfish env and cloning the live RNG state (300-457). Shaped rewards feed only the catfish critic (`AcrmStepReplay` 69-157).
  - Intervention: reward (catfish stream only).
  - Classes: `AcrmCatfishMODQN` 254; `ConcatCatfishCapacityE5Trainer` 507 composes ACRM + faithful catfish + capacity penalty.
  - Knobs: preset `acrm-annealed` (η_w=1.0, tanh off; `catfish_faithful_familyb/presets.py:139-151`). "Annealing" was removed on 2026-08-03 (docstring 6-11).
  - Tests: `tests/test_system_ee_acrm.py`, `test_acrm_fresh_replication_runner.py`, `test_acrm_gamma_followup.py`.
  - Runs: **abl9k_full_mccrl, abl9k_full_noacrm/nostrat/symgamma, abl9k_strategy3_{static,annealed,acrm}** (lr 0.001, calib on, concat).
  - Port: hard. It needs (i) a second agent + second env (catfish), (ii) an env deepcopy that replays the same fading (old family_b env ignored the step rng; `coord_catfish.py:12-16`), and (iii) step bundles for the catfish critic in route-B form. The item-replay variant (`catfish_faithful_familyb/trainer.py:360-376`, `modqn_faithful_ablation/trainer.py:872-900`) is closer to the new trainer.
- **challenger_pool_builder.py — the frozen faithful-catfish challenger nets as a DQfD demo teacher.**
  - What it does: loads `catfish_q_networks` (96-185), rolls them out with the self-pool rollout verbatim, and selects top-20% step-EE among coverage ≥ 0.90 steps (`FROZEN_SELECTION` 70), writing an `InjectionPool` npz.
  - Intervention: experience (teacher pool).
  - Gate: `challenger_distinctness_probe.py` decides whether the challenger is behaviourally distinct from the learner (results in `artifacts/shared_q_isolation/tier1b/CHALLENGER-DISTINCTNESS-RESULT.seed{42,137,271}.json`, `challenger_pools/`).
  - Runs: config `tier1b/TB-MARGIN-CATFISH.yaml`.
  - Port: the pool format is the route-B 224 bundle npz; it would need re-encoding to 112 7-tuples.
- **self_pool_builder.py — the "placebo teacher" self-pool control.**
  - What it does: builds an injection pool from `af` (AF angle-fair rule), `random` (random-init route-B), or `ckpt:<path>` (a frozen trained route-B policy, i.e. self-imitation) (9-15; `collect_route_b_self_rollout` 66; `build_self_pool` 134, quantile 0.20).
  - Intervention: experience.
  - Runs: config `v3/V3_concat_inj_selfpool.yaml`.
  - Port: same as above. Conceptually it is the control arm any teacher injection needs.
- **concat_encode.py + standardize.py — cross-user z-score / concat / center / width-control input.**
  - What it does: `zscore_over_users` 25 standardises each feature across the 100 users of one step (eps 1e-6); `center_over_users` 90; `concat` = [raw ‖ z] (`augmented_encode_concat` 48); `width` = [raw ‖ raw] is the matched-width negative control (71); pools are standardised per step (`standardize_pool_arrays` 59, `concat_pool_arrays` 86); readout `mean_offdiag_row_pearson` 110. Trainers: `trainer_std.py` (pure z), `trainer_concat.py` (concat/width/center).
  - Intervention: representation.
  - Runs: **enabled in nearly every late run**: waveE_*, fulldqfd_*, abl9k_* (`concat_input.form=concat`, 448 = 224‖224), `waveE_OFF_width` / `fulldqfd_WIDTH_lr001` width control, `waveE_OFF_raw` / `abl9k_baseline_raw` raw control; configs `IS_pure.yaml` / `IS_cat.yaml`, `tier1/S-{C2,CEN,CFC,CFZ,RAW}`.
  - Port: **trivial** on the new 112 obs. z-score the (100,112) encoded array per step before storing, concat to 224, and widen the input layer. The new env always steps all 100 users together, so the per-step population exists at encode time.
  - Caveat: the old repo's own open question is whether z-score is "coordination" or a feature fix (`docs/OPEN-QUESTION-cross-user-zscore-is-it-coordination.md`).
- **runner_acrm_fresh_replication.py** — no mechanism. A fail-closed wrapper that re-runs `abl9k_strategy3_static` vs `abl9k_strategy3_acrm` on fresh seeds derived from a namespace (`EXPECTED_ARM_NAMES` 56-59, `derive_fresh_seed_roots` 183; delegates to `runner_concat`). Test `test_acrm_fresh_replication_runner.py`. Port: methodology only (fresh-seed replication gate).
- **runner_gamma_factorial.py** — no mechanism. It authorises 3 missing ACRM × catfish-γ cells (`abl9k_strategy3_static_symgamma`, `abl9k_strategy3_acrm_symgamma`, `abl9k_full_noacrm_symgamma`; 46-50) as a follow-up overlay. Test `test_acrm_gamma_followup.py`.
- **trainer_e5.py — E-5 cross-user TD-target variance logging + phenotype probe.**
  - What it does: per head, it logs the cross-user std (grouped by step) of reward, bootstrap and target (123-149), plus argmax_distinct / Q-row Pearson / gap stats every 3000 updates (73-111).
  - Intervention: diagnostic only.
  - Runs: on in waveE / fulldqfd / abl9k.
  - Port: needs the step grouping. **Its bootstrap uses a per-head unmasked max (140)**, so a port must switch it to the shared scalarised a'.
- **Also here:** `gap_stats.py` (Q-gap readouts), `heldout_eval.py`, `gate_readout.py`, `l1_readout.py`, `eval_{raw,std,concat}.py` (eval harnesses). No training mechanism.

**EXP in the 6-arm matrix.** The matrix is defined at `modqn_faithful_ablation/config.py:80-125` (docstring 8-21). **EXP = "faithful item-replay experience machinery"**, i.e. the catfish agent's experience channel: a separate catfish agent and critic, hard EE stratification into its buffer, asymmetric γ_CF, and the periodic 70/30 conduit into the main update (`config.py:287`: `EXP_item_replay_catfish`). P = capacity penalty; ACRM = matched-rollout linear competitive reward (only possible when EXP is on, 123). The arms are `modqn_raw` (raw 112, no P/EXP/ACRM), `modqn_z` (concat 224), `full` (P+EXP+ACRM), `wo_penalty` (EXP+ACRM), `wo_exp` (P only), `wo_acrm` (P+EXP). The thesis chapter calls it a proposal "尚未取代既有 9-arm 歷史 preregistration", with no scores reported (`archive/thesis-mc-modqn-faithful/ch5-experimental-result.md:162-180`). Locally only pilot configs `configs/modqn_faithful_ablation/pilot/modqn_z_lr{001,003,01}.yaml` exist; no run_metadata. The *executed* 9-arm analogue is the shared-Q `abl9k_*` wave (lineage S, row 14).

### 2.2 catfish_faithful_familyb/ (C1FIXED port of CDRL catfish onto the Family-B item-replay trainer)

- **What it does:** M1 EE stratification; M2 asymmetric γ (0.9 < 0.99); M3 70/30 periodic conduit; L3 dual self-rollout in the catfish's own env; ACRM (off by default); optional Q-blend.
- **Intervention:** experience (M1, M3), exploration (L3), reward (ACRM), decode (Q-blend).
- **Code:**
  - `CatfishStratifier.route` `stratification.py:66-122`. SOFT: top-q to catfish. HARD: ≥q_hi (0.80) → catfish, [q_mid (0.50), q_hi) → cross-route into the main buffer, below that discarded. Rolling window 5000, min window 5000. The label is raw `r1_system_ee_contribution` (`trainer.py:492-494`).
  - Catfish critic `_update_catfish` `trainer.py:414-432` (γ_CF).
  - Conduit `_maybe_intervene` 440-485 (period ~ U[4,16], ratio 0.30, min catfish replay 32).
  - Dual rollout `_catfish_dual_rollout_step` 496.
  - ACRM `_apply_acrm_shaping` 360-376 (r1_cf + η(r1_cf − r1_main-counterfactual); matched joint env deepcopy step).
  - Q-blend `_select_actions_blended` 273-295 (ω=0.7 main + 0.3 catfish scalarised Q for `qblend_window` steps after an intervention).
- **Config defaults** (`config.py:46-150`): catfish_enabled False, gamma_catfish 0.99, strat quantiles 0.80/0.50, window 5000, hard_discard False (the faithful-full preset sets True), intervention_ratio 0.30, period 4-16, acrm_eta_weight 1.0, qblend_omega 0.7, catfish_replay_capacity 50,000.
- **Presets:** `presets.py:31-193` (v1-default, faithful-full, minus-strat/-discount/-intervention, plus-qblend, acrm-full, acrm-annealed[-nostrat/-symgamma]).
- **Disclosed:** M2 γ is **structurally inert** on the 10-step Family-B episode (docstring 12-17; `faithful_catfish_trainer.py:13-17`).
- **Tests:** 6 test files (`test_acrm_gamma_followup.py`, `test_phase1_config.py`, `test_system_ee_acrm.py`, …); archive `test_catfish_faithful_{mechanisms,parity,…}.py`.
- **Runs:** item-replay version: `faithful-catfish-effect-2026-07-08/A{1_plain,2_faithfulcatfish}` (lr 0.01, calib on). Route-B step-bundle version (`route_b_factorial/faithful_catfish_trainer.py`) via configs `A{1,2}_faithful_corrected_k1_w503020_C1FIXED.yaml`. Pack version is abl9k.
- **Port:** **the most directly portable catfish.** It is per-user item replay with a 7-tuple buffer (`_replay_sample_to_update_kwargs` 380-406 expects exactly the new 7-tuple). It needs a second Q triplet, a second optimizer set, a second env instance, and a catfish FIFO. **It inherits defect (a) through `_update_from_arrays`**, so the port must route catfish and conduit updates through the new shared-a' `update()`.

### 2.3 injection_rung1/ + route_b_factorial/ injection + replay

- **injection_rung1 — DQfD-style demonstration injection + large-margin loss.**
  - What it does: each update replaces n_ext = round(ρ·B) own items with frozen-pool items (not added on top; `trainer.py:234-289`). It adds λ·J_E with J_E = E_ext[max_a(Q_w(s,a) + m·1[a≠a_E]) − Q_w(s,a_E)] on the **scalarised** Q_w (`margin.py:1-11`, `dqfd_margin_loss` 49, `scalarized_q_grad` 23). Optional margin-scale fix m = k·std(valid Q_w) (`qw_valid_spread` 33; `trainer.py:196-208`), DQfD pre-training on the pool only (`pretrain` 292-359, target sync every 500), and L2 via Adam weight_decay (222-231).
  - Intervention: experience + penalty-loss (+ pretraining).
  - Knobs: `injection_rung1.{enabled, rho=0.30, margin.{enabled, margin=0.8, lambda=1.0, scale_mode=fixed|qw_sd, qw_sd_mult=1.0}, pretrain_steps=0, weight_decay=0.0, pools[], pool_sha256}`. Matched-ablation RNG via `decouple_explore_rng` (`route_b_factorial/trainer.py:77-105`).
  - Pools: `pool.py` (`select_steps` 122, top quantile 0.20 among coverage ≥ 0.90; `collect_teacher_rollout` 179; `InjectionPool` 334; teachers DQN_EE / DQN_scalar / AF rule). `fmean_pool_builder.py:80` (F-mean zero-learning EE best-response solver demos). Oracle / g-handover pools exist in configs (`D_oracle_declair_all_kc1.npz`, `D_g_handover_all_kc1.npz`).
  - Tests: `injection_rung1/tests/test_injection_rung1.py`, `tests/test_inj_rho_arithmetic.py`.
  - Runs: **enabled in recorded runs**: waveE_ON / ONnm (ρ .30, qw_sd, pretrain 8000, lr 0.001), fulldqfd_ON / ONnm / ON_raw / ON_lr001 (weight_decay 1e-5, F-mean pool), INJ1_{B..F} configs; γ = [0, 0.9, 0.9] (r1 treated as a bandit).
  - Port: **good fit.** Pool = frozen 7-tuples in the new format, mixed into the uniform batch at ρ; margin on Σw·Q over the valid mask; one combined backward (the three heads' params are disjoint, so the grads are identical). Needs a teacher in the new env (a reference policy / oracle) and a pool builder.
  - Disclosure in configs: "NOT literal DQfD — n-step TD omitted, prioritized demo replay OFF".
- **route_b_factorial/external_inject.py — earlier external-specialist injection (no margin).**
  - What it does: mixes ρ of a frozen DQN_scalar specialist pool into the minibatch (`load_external_pool` 61, `mix_route_b_batches` 122, `resolve_pool_path` 47; trainer hook `route_b_factorial/trainer.py:155-178, 225-241`).
  - Intervention: experience.
  - Knobs: `external_inject.{enabled, rho=0.30, pool_dir, source=dqn_scalar}`.
  - Runs: `route_b_factorial/A2_inject_dqnscalar_hybrid_k1_w503020_C1FIXED` (5 seeds) vs `A1_noinject_…`.
  - Port: as above, minus the margin.
- **route_b_factorial/replay.py — step-bundled replay + value-stratified (self-imitation) priority.**
  - What it does: stores whole steps (capacity 50,000 // 100 = 500 steps). An item is tagged priority if calibrated J_w > μ + λσ (Welford after warmup; 91-135); ρ of each batch is drawn from the priority set (`sample` 145). `priority_axis: ee` ranks on r1 instead of J_w (`trainer.py:111-119, 389-392`).
  - Intervention: experience.
  - Knobs: `value_stratified.{enabled=False, lambda=0.5, rho=0.25, priority_axis=jw|ee}` (`config.py:158-173`).
  - Runs: **enabled** in A2_hybrid_* / A2_ee_g(s)_* route-B runs (3 seeds each, lr 0.01).
  - Port: priority sampling ports easily to an item FIFO. Step bundling only matters for coordinated decodes.
- **route_b_factorial other mechanisms:**
  - χ congestion context (`congestion_context.py:38-91`: per candidate action, prev-step occupancy of the physical cell, #contenders who can reach it, the user's SNR rank among them; normalised by `normalize_chi` 93). It is **pre-action and action-free** (no-leak guard). Appended as 3×28 features (`shaped_q.augmented_encode` 53).
  - Coordinated decodes `column_greedy_decode` (`auction_decode.py:235`: argmax / physical auction / hybrid, with k_c) and `decode_hybrid_corrected` (`corrected_decode.py:65`).
  - Per-objective γ (`route_cfg.gamma_vec`).
  - Decode-consistent Double-DQN target (shared a').
  - Port: χ is a representation add-on computable from the new obs + candidate map. The decodes need k_cap and the physical map, and a bundle replay if used inside the TD target.

### 2.4 coordinator_dqfd_zscore/, modqn_faithful_ablation/, preq_ee/, offset_fix/

- **coordinator_dqfd_zscore/** — a **non-runnable** 6-cell screen plan: Z(z-score) × D(DQfD) × C(coordinator) on the corrected-r3 base-140 substrate. Arms `Z1_D1_C1, Z0_D1_C1, Z1_D1_C0, Z0_D1_C0, Z1_D0_C1, Z1_D0_C0`, seeds 42/137/271/7/91/2026 (`study_plan.py:1-7, 26-45`).
  - Components: Z1 = [raw140 ‖ per-step cross-user z] (280); Z0 = [raw ‖ raw] width control (`representation.py:1-9`). A deterministic **F-mean teacher** (8-sweep synchronous Jacobi best-response over the expected-fading assignment surface + greedy beam-opening state machine; `fmean_teacher.py:1-8`) with a production pool writer (`fmean_{builder,producer,artifact,runtime,physics,rng}.py`). `dqfd_sampling.py` (D0/D1 item accounting), `dqfd_margin.py` (detached margin audit on Σw·Q with qw_sd scale, 297-395), `state280_replay.py` (joint-step replay at width 280), `schedule_events.py`.
  - The coordinator factor was retired 2026-07-17 (`__init__.py:7-15`; `archive/src-eras/REATTACH-coordinator.md`).
  - Tests: 16 files (`test_coordinator_dqfd_zscore_*`).
  - Runs: none (plan only).
  - Port: the **F-mean teacher** is the reusable idea (a zero-learning EE-aware best-response demo source). The rest is contracts.
- **modqn_faithful_ablation/** — the paper-faithful item-replay learner with P/EXP/ACRM treatments (Section 1 row 15).
  - `replay.py` `ObjectiveReplayBank` 179: three independent objective memories; each objective samples its own batch with its own RNG.
  - `encoding.py` (raw 112 / concat 224 via `cross_user_zscore` 62, `encode_population` 88).
  - Capacity penalty local copy (`capacity_penalty.py:19`; knobs `capacity_lam=0.05, capacity_tau=1.0, capacity_every=1`, `config.py:166-168`).
  - EXP catfish (`trainer.py:465-518` builds the catfish side; `_maybe_intervene` 925; `_shape_acrm` 872-880 = r1 + (r1 − r1_main), η=1).
  - `lineage.py` (observational replay-provenance tracer, 84-303).
  - `phase1_trainer.py` (`FixedThresholdStratifier` 32 with frozen Gate-A thresholds; **episode-0 source prefill** = verified source pool inserted before the first reset, docstring 1-7).
  - `strategy_pilot.py` (EXP-strategy isolation arms N / B / S1 no-strat / S2 sym-γ / S3 no-conduit, 1-24, 163).
  - Tests: `test_modqn_faithful_ablation.py`, `test_phase1_*`, `test_phase1_exp_strategy_pilot.py` (11 files).
  - Runs: pilot configs only; ADR-004 / ADR-007 describe phase-1 diagnostics.
  - Port: closest code shape to the new trainer (item replay, 112 base, per-user argmax). **Defect (a) is deliberate here**, and it samples per-objective batches, so a port must re-unify onto one batch + shared a'.
- **preq_ee/** — a reward-definition variant, not a learning mechanism. r1 is repriced to "preq-EE" (required-power consumed EE with PA efficiency η_PA = clip(η_min, η_max·√(P_DL/P_sat), η_max), DCPC serve-clipped served set, optional interference lag 1 via `LaggedRhoCarry`; `reward.py:1-40, 198, 353, 561`).
  - Intervention: reward (r1 only). Trainer `trainer.py:77` inherits route-B.
  - Runs: `preq-ee-2026-07-04/runs/A{1,2}` and a T9 grid g00-g18 × 3 seeds (lr 0.01, calib on).
  - Tests: 7 in `preq_ee/tests/`.
  - Port: n/a (the new project has its own EE axis). Relevant only as a record of PA-saturation EE modelling.
- **offset_fix/** — encode-side masking. `zero_unreachable_beam_offsets` / `reachable_beam_mask_from_state` (`masked_encoder.py:18, 48`; threshold 1000 km, historical; current branch only checks finite θ).
  - Intervention: representation.
  - Runs: `sdd11-retrain-2026-06-09` (OffsetMaskedMODQN).
  - Port: the new obs already carries angle per candidate; nothing to port.

### 2.5 archive/src-eras/

- **demo_guided_catfish/ — P4 "coverage multiteacher": shaped-Q catfish CF net with CA-CPBR reward shaping + planner-bank injection.** Six-arm factorial harness; READINESS-ONLY.
  - `ca_cpbr.py` — Collapse-Adaptive Competitive Potential-Based Reward. State-only potentials Ψ: assignment entropy 67, occupancy spread 101, tail coverage 134 (β=12). Collapse-adaptive gain η_k = f(collapse, η0, λ) 180. `CollapseSchedule` 204, `phi_k` 276, `shaping_F` = γ_CF·η(t')Ψ(s') − η(t)Ψ(s) 312, `churn_watchdog` 375. Intervention: reward (potential shaping).
  - `shaped_q_trainer.py` — the net IS the shaped Q with η carried in the INPUT (state augmentation). The docstring explains that the v1 outer-offset wrapper was vacuous: Φ telescopes out (9-31). Shared-trunk + 3 heads; the r1 head is head+trunk-masked for planner transitions. **Per-head own-max target (346-384).**
  - `planner_bank.py` — immutable filtered planner bank B_pl, injected only when rolling full-population min-served < 0.08 (`coverage_critical_mask` 69, sha256 identity 85-123, `assert_identical_filtered_subset` 181). Intervention: experience.
  - `arms.py` — arm5 F-dose-yoked static gain (`dose_matched_eta` 45) and arm6 collapse-anti-correlated dose-matched schedule (`build_arm6_schedule` 136). These are controls for "is the adaptive schedule the cause".
  - `witness_prescreen.py` — teacher-feasibility witness: the planner must reach min-cov ≥ 0.05 on every seed; planner-vs-sticky well-posedness CIs (33-121).
  - `state_adapter.py` — state-only served indicator from the encoded row, and reward norms `norm_r1/2/3` 143-155.
  - `coverage_multiteacher_probe.py` — harness. R0 distils the sticky bank into a SetEncoderHP (319); J_E large-margin loss (552-555).
  - `per_objective_catfish_probe.py` — Route-C 3-catfish per-objective: every head trained with its own Ψ, combined-rank selection, arms baseline / 3catfish / drop_r{1,2,3}, per-head conduit-liveness gate with negative controls (1-40).
  - Tests: 9 `test_demo_guided_catfish_*.py`.
  - Runs: artifacts `p4-coverage-multiteacher/`, `p4-gate2b/` (no run_metadata).
  - Port: the potential shaping is portable (state-only Ψ over the new obs). The planner-bank injection needs a planner teacher. The CF net inherits (a).
- **per_objective_catfish/** — three single-head catfish, one per objective. M1 per-objective soft top-quantile on raw r_j, M2 γ_CF 0.99, M3 per-head 70/30 into main head j (`trainer.py:1-40, 197-258, 287-427`). Plain heads, no coordination.
  - Presets: baseline / faithful-full / minus-{strat, discount, intervention, ee/handover/load-catfish} (`presets.py:30-96`).
  - Tests: `test_per_objective_catfish*.py`. Runs: `artifacts/per-objective-catfish/`.
  - Port: item-replay friendly. **Per-head intervention is precisely the per-head update pattern that defect (a) lives in.** A port must evaluate each head at the shared a'.
- **coordinated_multi_catfish/** — execution-time sequential/autoregressive per-user decode over occupancy-augmented heads, plus 3 per-objective catfish as a separable arm. `occupancy.py` (`encode_occupancy` 23, `decode_order_indices` 41, `occupancy_from_actions` 76); `replay.py` joint snapshots with occupancy recomputed at update time (35-160).
  - Runs: `coordinated-multi-catfish-pilot-2026-06-03/probe/{baseline, coordination, coordination_catfish, coordination_control}` (lr 0.01, calib off).
  - Defect: (a) YES + decode-inconsistent bootstrap (row A4).
- **coordinator_catfish/** — pure coalition-proposal kernel (`coalition.py`: `propose_coalition` 175, `resolve_topk_admission` 91), protected-lane 2×2 isolation contracts (`isolation.py`), and a corrected-r3 auxiliary-fork adapter (`r3_adapter.py`: coalition actions confined to an aux env fork; the endpoint stays per-user argmax). No trainer. The live descendant is `shared_q_isolation/coord_catfish.py`.
- **catfish_generic_killtest/** — P1 generic-validity kill-test of catfish M1/M2/M3 on DeepSea(N) and MountainCar. Arms A DQN-tuned, B catfish-FULL, C −strat, D −discount, E −intervention, F NoisyNets, G PER, H DQfD-style (`arms.py:1-45`). Single-head Double-DQN, lr 1e-3. Tests archived. Port: methodology (a generic-env sanity test of the catfish claim).
- **sequential_decode/** — C1 kill-test. Deployment = single sequential occupancy-conditioned pass. Joint-snapshot replay (`replay.py:1-30, 109`). **Decode-consistent target: target-net sequential decode a', every head gathered there** (`trainer.py:300-373`). Checkpoint selection on calibrated J_w (22-25). Artifacts `c1-killtest/`. Port: shows the fix for (a) + decode consistency in the old repo.
- **global_assign_decode/** — eval-time, policy-independent channel-surrogate global assignment (w = log2(1+SNR), multi-start coordinate ascent; `decode.py:33-96`, `GlobalAssignDecodeMODQN` 97). It ignores Q, so it is a landscape cell, not a learning mechanism.
- **joint_assign_decode/** — eval-time joint-assignment decoders: `q_primary_lexicographic_actions` 21, `planner_actions` 61, subclass 80. Decode only. No training change.
- **catfish_offset_fix/** — MRO composition of the archive catfish with the offset mask (`trainer.py:9`); parity test `test_catfish_offset_fix_parity.py`.
- **catfish_faithful/** (archive Route-A original) — the ancestor of 2.2, on `MODQNTrainer` (row A1). Runs `catfish-faithful-route-a-pilot-2026-06-02/probe/{FULL, acrm_full, baseline, minus_intervention, v1_default}`.

### 2.6 Other mechanisms found (not in the brief's list)

- `runtime/popart_online.py` — online PopArt reward standardisation (warmup, σ floor, clip). Reward-scale lever. Family-B preregs pin it OFF (`family_b_retrain/trainer.py:481-482`). Runs: `realistic-cells-popart-on-cheap-gate-2026-05-29`.
- `runtime/catfish_replay.py` — Phase-04-B Catfish-MODQN replay utilities (earliest catfish; `legacy/multi_catfish_modqn_v2.py` has per-head max at 311). Runs: `phase04-capacity-constrained-multi-catfish-v2*` configs.
- `family_b_retrain/redo_trainer.py` — **ReDo dormant-neuron recycling** (plasticity control; τ and every-F-grad-steps knobs, 53-190). Intervention: representation/optimiser.
- `family_b_r3/decode.py` — audited decoders `independent-argmax-v1` vs `full-physical-auction-v1` (24-27), used inside the r3 2×2 TD target.
- `field_baselines/shared_q_isolation.py` — ISO_S vs ISO_M architecture isolation (see row 21 caveat). `field_baselines/dqn_baselines.py` — DQN / set-encoder field baselines.
- `analysis/family-b-collapse-diagnosis/p4_distillation_fidelity_probe.py` — planner → student distillation (per-user-argmax vs autoregressive student).
- Per-objective γ vectors used in recorded runs: `[0.0, 0.9, 0.9]` (r1 bandit; waveE/fulldqfd), `[0.9, 0.9, 0.99]` (route-B A2), `[0.99, 0.9, 0.9]` (A2_ee_g), `[0.99, 0.9, 0.99]` (preq A2). Knob `gamma_per_objective`.
