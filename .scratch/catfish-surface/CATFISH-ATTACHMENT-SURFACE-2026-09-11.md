**(b) bounded code — no interface break, but the honest count is ~430 lines for DQfD-minus-prioritization and ~620 lines for full DQfD, i.e. 1.5–2× the brief's ~300-line bar, spread over six named files: `src/mcrl/algorithms/modqn.py` (~190), a new `src/mcrl/runtime/prioritized_demo_replay.py` (~230), a new `src/mcrl/runtime/demo_pool.py` (~120), `src/mcrl/runtime/trainer_spec.py` (~22), `src/mcrl/runtime/trainer_config_validation.py` (~40), `src/mcrl/runtime/training_pipeline.py` (~30) — and none of it matters, because the project has no demonstrator to put in the demonstration buffer.**

Date: 2026-09-11. Read-only audit; no training, no server job, no file modified outside this report and its sibling `PROGRESS.md`. Two trees, never mixed:

- **current** = `/home/u24/papers/mcrl-leo-handover` (branch `wip/multi-catfish-v023-20260907`, commit `da3d95a3`)
- **sibling** = `/home/u24/papers/modqn-paper-reproduction`

Evidence class per claim: **[V]** = I opened the file / ran the read-only check myself, with file:line. **[I]** = I reasoned it. Estimates are marked **[E]** and are my own, not measurements.

**Scope note from the coordinator, mid-task:** the target mechanism is **DQfD** (Hester et al., AAAI 2018, arXiv:1704.03732), not the RIS/CDRL catfish. Both source papers are reference-only. Questions 1, 2, 3, 6, 7 are unchanged (they are DQfD's surfaces too); question 4 is one line; a new §8 answers the DQfD loss-surface question. The catfish mechanisms are retained here only where they coincide with DQfD; establishing that mapping is DQFDGROUND's job, not mine.

---

## 1. Where is the MODQN/DQN trainer that produced `e6b063ef…`?

**[V] Module, class, step function, config object:**

| Thing | Location |
|---|---|
| Module | `/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/modqn.py` (1,380 lines) |
| Trainer class | `modqn.py:84` `class MODQNTrainer` |
| **Gradient-step function** | `modqn.py:511` `def update(self) -> tuple[float, float, float]` — samples one batch, loops `obj_idx` in 0..2, one `MSELoss` per objective, one `Adam.step()` per objective |
| Episode loop | `modqn.py:1077` `def train(...)`; the single `update()` call site is `modqn.py:1282` |
| Config object | `/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/trainer_spec.py:25` `@dataclass class TrainerConfig` |
| Config validator | `src/mcrl/runtime/trainer_config_validation.py:54` `validate_trainer_config`, invoked from `trainer_spec.py:132-135` `__post_init__` |
| Run driver | `src/mcrl/runtime/training_pipeline.py:1199` constructs the trainer; `scripts/run_server_training.py:1-8` is documented as *"the only supported long-run entry point"* |

**Is it runnable in this repo today?** **Yes — verified by running it, not by reading it.** **[V]** In `/home/u24/papers/mcrl-leo-handover/.venv`:

```
torch 2.13.0+cpu   numpy 2.5.2
TrainerConfig OK; gamma= 0.9 cap= 50000 batch= 128 sharing= shared
mcrl.runtime.training_pipeline import OK
make_training_environment(users=100) built in 0.0s
num_beams_total 28  num_users 100  steps_per_episode 10
```

Those torch/numpy versions are byte-identical to the ones the frozen run recorded in its `run_fingerprint.dependencies` (`artifacts/training-2026-08-25-rerun01/main/status.json`: `torch 2.13.0`, `numpy 2.5.2`, `python 3.13.3`, `sgp4 2.27`). The frozen prereg `artifacts/PREREG-FROZEN-2026-08-25-R2.json` is present locally. **[V]**

**But the local tree is not the producer tree.** I recomputed the pipeline's own closure algorithm (`training_pipeline.py:385-404`: every `src/mcrl/**/*.py` sorted by path, plus `scripts/run_server_training.py` and `pyproject.toml`, each contributing `label\0bytes\0`) over the local checkout:

```
local  code_sha256 = 817dc1a137fbfd53f6ff267b3a959d6d4d6029d4ad1e03458a3c219946dc9b46   (158 files)
frozen code_sha256 = 544fcf078f7e0d74c38e79288081c60357bc64b59540120dbe4e30bffe014ec4
```

**[V]** They differ. `modqn.py` itself gained +260 lines and `replay_buffer.py` +104 lines in the `14174d60` WIP snapshot of 2026-09-07 (`git show --stat 14174d60`), and ~46 `ee_axis_*` modules that did not exist on 2026-08-25 are now inside the closure. **[V]**

The important consequence, and it cuts in favour of the delta: **`code_sha256` is *recorded*, not *enforced*.** `training_pipeline.py:438` writes it into the fingerprint payload; nothing compares it against a frozen constant. **[V]** So a modified trainer still runs — it simply produces a different `fingerprint_sha256`, and `_load_resume_checkpoint` will refuse to resume a run started under the old fingerprint. A DQfD arm is a *new* run, so this is not a blocker; it does mean the arm cannot be called a continuation of `e6b063ef…`, and any ON/OFF pair must have **both** arms rebuilt under the new fingerprint. **[I]**

One governance fact that is a real (if soft) obstacle. `trainer_spec.py:110-128` records W-09's deletion of *four* opt-in config surfaces (44 + 9 + 4 + 2 fields) on the stated ground that *"the 2026-08-22 ruling forbids leaving a socket for a deleted mechanism"*, and `modqn.py:498-509` records PATCH P-11 deleting `_update_from_arrays` — *the* subclass override seam — because *"a dormant path that would violate a gate the moment it were wired up is a trap, not a spare part."* **[V]** Adding DQfD knobs to `TrainerConfig` is therefore admissible only if the mechanism is actually wired and exercised in the same change; a default-off stub is explicitly the pattern this repo has already ruled against twice.

---

## 2. Replay buffer

**[V] Yes, exactly one, and it is plain.**

| | |
|---|---|
| Class | `src/mcrl/runtime/replay_buffer.py:13` `class ReplayBuffer` — *"Fixed-capacity FIFO experience replay (ASSUME-MODQN-REP-006)"*, backed by `deque(maxlen=capacity)` at `:24` |
| Capacity | `TrainerConfig.replay_capacity: int = 50_000` (`trainer_spec.py:68`); instantiated `self.replay = ReplayBuffer(config.replay_capacity)` at `modqn.py:143` |
| Push site | `modqn.py:1270-1278`, inside the per-user loop, after two admission filters (`:1261` no-op drop, `:1265` empty-next-mask drop, both counted by PATCH P-03) |
| Sample site | `modqn.py:527` `self.replay.sample(cfg.batch_size, self._train_rng)` |
| Sampling law | `replay_buffer.py:44` `indices = rng.choice(len(self._buf), size=batch_size, replace=False)` — **uniform, without replacement, no weights** |
| Resume | `replay_buffer.py:57-110` `state_dict` / `load_state_dict`, wired into `modqn.py:917` and `:1017` |

**Can a second buffer be added and sampled alongside?** **Yes. The trainer's interface does not assume the buffer is singular.** **[V]** `self.replay` is a plain instance attribute set once at `modqn.py:143`; `update()` touches it at exactly one line (`:527`), and `train()` at exactly two (`:1270` push, `:1324` `len()` for the log). Nothing subclasses the trainer, nothing type-annotates on `ReplayBuffer`, and there is no registry. A second buffer is four new lines plus a mixing call.

Three real costs, not blockers: **(i)** `training_state_dict` (`modqn.py:881-924`) and `load_training_state_dict` (`:926-1020`) would each need the second buffer added, and the loader is strict (`"training state is missing {key}"`, `"training state trainer_config does not match this trainer"`) **[V]**; **(ii)** `EpisodeLog.replay_size` is a single int (`modqn.py:1324`) so the per-episode log schema changes; **(iii)** the deque is FIFO with `maxlen` — a demonstration region put in the *same* buffer would be evicted, which DQfD forbids (its demo data is permanently retained), so the second buffer must be a separate object, not a tagged region of this one. **[I]**

---

## 3. Discount factor

**[V] One module-level-ish scalar, shared by all three objective heads, used at exactly one line.**

- Declaration: `trainer_spec.py:49` `discount_factor: float = 0.9` — a `TrainerConfig` field, so per-*run*, not per-agent and not a hard-coded module constant.
- TD target: `modqn.py:550`
  ```
  target = r + cfg.discount_factor * q_next_max * (1.0 - dn)
  ```
  This is the **only** place γ enters. `grep -n discount_factor modqn.py` returns `:12` (docstring) and `:550`. **[V]**
- It is inside the `for obj_idx in range(3)` loop (`modqn.py:536`), so all three objective networks share the one γ. **[V]**
- Validation: `trainer_config_validation.py` requires a positive discount (its module docstring, `:20`: *"a non-positive discount silently deletes the future"*). **[V]**
- Sourced from the frozen prereg at `training_pipeline.py:851` `discount_factor=float(training["discount_factor"])`. **[V]**

**What would two different discounts take?** Mechanically almost nothing: change `cfg.discount_factor` at `:550` to a per-something lookup, plus the config field and its validation. But note the direction of the finding — **DQfD does not want two discounts.** DQfD has one agent and one γ; what it wants at this line is a *second* target, the n-step return (see §8a). For the record on the catfish side: the sibling wires `GAMMA_MAIN = 0.9 / GAMMA_CATFISH = 0.99` (`catfish_faithful_familyb/presets.py:27-28`) and its own disclosure calls the mechanism structurally inert in a 10-step episodic env. **This env is also 10 steps per episode** (`steps_per_episode 10`, measured above) **[V]**, so the same inertness concern would transfer verbatim.

---

## 4. Two agents (low priority per the reframe)

**[V] One agent. The three `q_nets` at `modqn.py:123-129` are one per *objective* (r1/r2/r3), not one per agent — three `DQNNetwork`s, three targets (`:130`), three `Adam`s (`:137-140`), all fed by the same shared rollout and the same buffer.** A second *agent* has never been supported: `trainer_config_validation.py:39` `VALID_POLICY_SHARING = frozenset({"shared"})`, commented *"Per-user parameters were never this project's design."* It would be buildable (nothing couples the nets to the env beyond `select_actions`), but DQfD is single-agent, so this is moot.

---

## 5. ACRM

**[V] The implementation exists only in the sibling, is not reachable from this project's trainer, and — correcting the companion facts doc — it was actually executed.**

**What it computes**, `modqn-paper-reproduction/src/modqn_paper_reproduction/catfish_faithful_familyb/trainer.py:480-497`:

```python
def _apply_acrm_shaping(self, reward_vec, counterfactual_result, uid):
    r_cf = float(reward_vec[0])
    r_m  = float(counterfactual_result.rewards[int(uid)].r1_system_ee_contribution)
    r_s  = r_cf - r_m
    shaped = reward_vec.copy()
    shaped[0] = r_cf + float(self.catfish_config.acrm_eta_weight) * r_s
    return shaped
```

i.e. eq. (4.8)/(4.9) applied to the **r1 slot only**, leaving r2/r3 untouched.

**At which call site**, same file `:115-160`: inside `_catfish_dual_rollout_step`, *before* the catfish env is stepped, it (a) computes the main agent's greedy joint action `_main_greedy_joint_action`, (b) `copy.deepcopy`s the whole catfish env, (c) clones the RNG bit-generator state so the counterfactual cannot perturb the live stream, (d) steps the clone with the main agent's joint action, and (e) uses that clone's rewards as `r^M`. **[V]** So ACRM is not a reward arithmetic change — it is a **matched joint counterfactual env rollout per step**.

**Reachable from this project's trainer? No.** **[V]** It is a method of `CatfishFaithfulFamilyBMODQN(FamilyBRetrainMODQN)` (`trainer.py:102`), typed against `FamilyBTrainerEnvAdapter` / `FamilyBTrainerConfig` / `CatfishFaithfulConfig` — a different package, a different base trainer, a different env adapter and a different config class from anything in `mcrl`. There is no import path, no shared interface, and `grep -rn acrm --include=*.py src/` in the current tree returns nothing outside the `ee_axis_c1_selector` re-use of the *name* for pair construction.

**Has any recorded run enabled it? YES — verified, and this corrects the companion facts doc's "Not established here: whether any sibling *run* ever used the ACRM-enabling presets."** **[V]**

`modqn-paper-reproduction/artifacts/diag-winrate-2026-07-20/abl9k_strategy3_acrm/seed-{42,137,271}/run_metadata.json` each record:

```
acrm.acrm_on = true        acrm.acrm_eta_weight = 1.0
catfish_faithful.preset = "acrm-annealed"     episodes = 2000     smoke_run = false
```

The wave carries `artifacts/diag-winrate-2026-07-20/ALL-DONE.sentinel` and per-seed `done/abl9k_strategy3_acrm-{42,137,271}.done`. A second arm, `abl9k_full_mccrl`, ran the same preset. Enabling configs: `configs/shared_q_isolation/v3/abl9k_strategy3_acrm.yaml:12`, `abl9k_full_mccrl.yaml:12`, `abl9k_full_nostrat.yaml:13`, `abl9k_full_symgamma.yaml:14`, `abl9k_strategy3_acrm_symgamma.yaml:11`. **[V]**

Two numbers from that run's own instrumentation, both relevant to anyone tempted to port it:

- **The counterfactual clone is cheap.** `clone_count = 2000`, `clone_seconds_total = 11.458` → **5.7 ms per cloned counterfactual step**, `peak_rss_kb = 726288` (710 MB). **[V]** The cost objection to ACRM is not a real objection.
- **The competitive term ran net negative.** `uid_win_rate = 0.3389` over 2,000,000 user comparisons, `d_signed_mean = −1.589e7` against `r_cf_mean = 2.634e8`. **[V]** The catfish agent trailed the main agent on ~66% of per-user comparisons, so `η·(r^CF − r^M)` was, on average, a **penalty**, not a bonus. I did not look for what the arm's EE outcome was; that is outside this audit.

---

## 6. Phase-1 / demonstration seeding

**[V] There is no such path in the current project. None. No warmup, no demonstration loader, no offline-data path, no `push_batch`, no `seed_buffer`.** The only writer to `self.replay` is `modqn.py:1270`, inside `train()`'s per-user loop, fed by `self.env.step(...)` at `:1226`. `grep -rniE 'pretrain|pre_train|warmup|warm_up|learning_starts|min_replay' --include=*.py src/` returns only `env/scenario.py:152` and `env/d2.py:128,309,313` — `warmup_steps` there is the **D2 measurement window** (a TTT-sized quantity for the handover trigger), not gradient pre-training. **[V]**

**So: the exact interface a seeded transition must satisfy.** From `replay_buffer.py:29-54` (`push` signature and `sample` dtype coercion) and `:113-152` (`_copy_transition`, which is the schema that resume enforces):

A transition is a **7-field tuple**, in this order, with these types — and `_copy_transition` **raises** on any violation:

| # | Field | Required type | Shape | dtype after `sample()` |
|---|---|---|---|---|
| 0 | `state` | `np.ndarray` (TypeError otherwise, `:132-137`) | `(112,)` = `4 × num_beams_total`, `state_encoding.py:139` with `num_beams_total = 28` | `float32` (`:47`) |
| 1 | `action` | `int` / `np.integer`, **`bool` explicitly rejected** (`:139-142`) | scalar | `int64` (`:48`) |
| 2 | `reward_3` | `np.ndarray` | `(3,)` | `float32` (`:49`) |
| 3 | `next_state` | `np.ndarray` | `(112,)` | `float32` (`:50`) |
| 4 | `mask` | `np.ndarray`, boolean (`ActionMask.mask`, `env/step_types.py:137-138` *"Boolean array, shape (L*K,)"*) | `(28,)` | as-is (`:51`) |
| 5 | `next_mask` | `np.ndarray`, boolean | `(28,)` | as-is (`:52`) |
| 6 | `done` | `bool` / `np.bool_` (`:143-146`) | scalar | `float32` (`:53`) |

Four semantic obligations a hand-built demonstration must also honour, all read off the push site, none of them enforced by the buffer:

1. **`reward_3` must be post-calibration.** `modqn.py:1269` pushes `apply_reward_calibration(reward_vec, cfg)`, which divides by `reward_calibration_scales = (2029238.4328742754, 1.0, 6.0)` (`objective_math.py:38-40`, scales from `status.json`). **[V]** A demonstration carrying raw bit/J r1 would be ~2e6× the live scale and would dominate every TD target in the batch.
2. **`state` must come from `encode_state`** with the same `TrainerConfig` (`modqn.py:579-584`), not a hand-rolled vector.
3. **The two admission filters must be respected**: no no-op actions (`modqn.py:1261`, `is_no_op`), and `done or next_mask.any()` (`:1265`) — otherwise the target row is all `-1e9`.
4. **`action` must be valid under `mask`** — nothing checks this here, but DQfD's margin loss does (`injection_rung1/margin.py:62` raises *"expert action invalid under valid_mask (corrupt injected batch)"*).

The sibling has the reference for the file format: `route_b_factorial/external_inject.py:76-82` documents a frozen `.npz` bundle schema `(states_aug, actions, rewards_calib, next_states_aug, next_mask, slot_cell, done)` stacked over step-bundles, built offline and loaded with a sha256 pin, *"so the trainer never imports the DQN / decode machinery, and the pool is a frozen, inspectable artifact with zero RNG interaction with training."* **[V]** That is the right shape and it is directly adaptable.

---

## 7. Cost

**[V] Measured, not estimated. Source: `artifacts/training-2026-08-25-rerun01/*/status.json`, the `started_utc`/`finished_utc`/`episodes_completed` fields of the four completed runs that produced `e6b063ef…`.**

| Run | Episodes | Wall (s) | Wall (h) | s / episode |
|---|---|---|---|---|
| `main` (lr 0.001) | 9000 | 14282.2 | 3.967 | **1.5869** |
| `p6-lr-0.001` | 9000 | 14297.4 | 3.971 | 1.5886 |
| `p6-lr-0.003` | 9000 | 14309.2 | 3.975 | 1.5899 |
| `p6-lr-0.01` | 9000 | 14042.5 | 3.901 | 1.5603 |

**One MODQN training episode = 1.56–1.59 s wall**, single-process CPU, on whatever host ran the 2026-08-25 rerun (the `checkpoint` path in that same status.json is `/home/sat/…`, i.e. the server). An episode is 10 env steps × 100 users = 1,000 candidate transitions, 10 `update()` calls at batch 128.

**A 3000-episode run costs 1.32 h wall** (`3000 × 1.5869 s = 4761 s`). **[V-derived from the measured rate.]** A DQfD ON/OFF pair at 3000 episodes is **2.6 h**; at the frozen 9000-episode length a pair is **7.9 h**; the full four-run shape of the original pipeline (3 P6 arms + main) was **15.8 h** end-to-end. **[V]** Add DQfD's pre-training phase, which is pure gradient steps with no env cost: at the measured ~10 updates per 1.59 s, 10,000 pre-training steps ≈ **26 min**. **[E — a rate extrapolation, not a measurement, and it ignores that pre-training batches are demo-only and so skip env stepping entirely, which makes it an over-estimate.]**

This is small. Cost is not what stands in the way.

---

## 8. The DQfD loss surface (added at §6 priority by the coordinator)

DQfD's combined objective is `J(Q) = J_DQ(Q) + λ₁·J_n(Q) + λ₂·J_E(Q) + λ₃·J_L2(Q)` over a replay that permanently retains demonstrations and is sampled by priority, after a pre-training phase.

**All four requested items are ABSENT. Two further DQfD ingredients I checked unprompted are also absent.** Stated plainly, one row each:

| DQfD requirement | Present? | Evidence |
|---|---|---|
| **(a) n-step return** | **ABSENT.** 1-step TD only. | `modqn.py:544-550`: the comment says *"Target: r + gamma * max_a' Q_target(s', a') where a' valid"*, and `:550` is a single-step bootstrap. `grep -rniE 'n_step\|nstep\|n-step\|multi_step\|bootstrap_n' --include=*.py src/` returns **zero** relevant hits (only `decision_steps` in `outage_gate.py` / `probe_p3.py` and `TEMPORAL_HORIZON_STEPS` in the unrelated ee_axis stage-C dataset). **[V]** The replay stores `(s,a,r,s')` only — no episode index, no step index, no trajectory linkage (`replay_buffer.py:29-38`), so n-step returns cannot even be *reconstructed* from a stored buffer; they must be accumulated in `train()` before the push. **[V]** |
| **(b) supervised / margin / imitation loss** | **ABSENT.** The loss is a single Bellman term per objective. | `modqn.py:145` `self._loss_fn = nn.MSELoss()` is the only loss object. `modqn.py:552` `loss = self._loss_fn(q_current, target)` is the only loss expression; `:557-563` is `zero_grad → backward → step` on that one term. `grep -niE 'margin\|supervised_loss\|imitation\|demonstration\|demo_\|expert'` over `modqn.py`, `replay_buffer.py`, `trainer_spec.py`, `q_network.py` returns only `q_margin` — which is the **G-3 collapse diagnostic** (`trainer_spec.py:139-160`, `modqn.py:1207-1219`), a logged statistic, not a gradient term. **[V]** |
| **(c) prioritized experience replay** | **ABSENT.** Uniform sampling, no priorities, no importance weights. | `replay_buffer.py:44` `rng.choice(len(self._buf), size=batch_size, replace=False)`; `sample()` returns exactly seven arrays with no weight or index channel (`:41-55`), so the trainer has no handle to write priorities back with. `grep -rniE 'priorit\|is_weight\|importance_weight\|sumtree\|sum_tree' --include=*.py src/` returns **one** hit, `ee_axis_v015_c3_selector.py:285`, an unrelated deterministic ordering docstring. **[V]** Notably PER is **absent from the sibling too** — the same grep over `modqn-paper-reproduction/src/` returns zero. **[V]** |
| **(d) pre-training phase** | **ABSENT.** No gradient step ever happens before environment interaction. | `update()` has exactly one call site, `modqn.py:1282`, inside the per-step loop of `train()`, after `env.step` at `:1226` and after the pushes at `:1270`. The only gate is a size check, `modqn.py:521` `if len(self.replay) < cfg.batch_size: return (0.0, 0.0, 0.0)` — a "don't sample an under-full buffer" guard, not a pre-training budget. `train()` (`:1077-1380`) has no pre-loop over the buffer. **[V]** |
| *(bonus)* **double-DQN target** | **ABSENT.** Plain DQN. | `modqn.py:546-549`: `q_next_all = self.target_nets[obj_idx](ns)` then `.max(dim=1).values` — argmax and evaluation both on the target net. DQfD's `J_DQ` is specified as a double-Q loss. **[V]** |
| *(bonus)* **L2 regularization (`J_L2`)** | **ABSENT.** | `modqn.py:137-140` `optim.Adam(self.q_nets[i].parameters(), lr=config.learning_rate)` — no `weight_decay`, and there is no explicit weight-norm term in `update()`. **[V]** |

**A structural detail that the four questions do not surface, and that I think is the most consequential one in this section.** DQfD's `J_E` is defined on **one** Q function; MODQN has **three**, with **three separate optimizers**, stepped inside a `for obj_idx in range(3)` loop that does `zero_grad / backward / step` per objective (`modqn.py:536, 557-563`). **[V]** The sibling solved exactly this by defining the margin on the *scalarized* Q, `Q_w = Σ_k w_k Q_k` — `injection_rung1/margin.py:22-30` `scalarized_q_grad`, with the stated reason *"the same quantity `column_greedy_decode` ranks on, so the supervision pushes exactly the surface whose argmax must shift."* **[V]** That is the right choice here too (`modqn.py:261-272` `_scalarize_q_values` is the decision-time surface). But a scalarized margin term back-propagates into **all three** networks from **one** loss, which does not fit a loop that zeroes and steps one optimizer at a time. The update must be restructured to: build all three TD losses + the one margin loss, `zero_grad()` all three, `backward()` once on the total, then `step()` all three. That is ~20 lines, it is not an interface break, but it **changes the gradient semantics of the frozen baseline path** — so the OFF arm must be re-run under the restructured code, not reused from `e6b063ef…`. **[I, from the verified code shapes above.]**

---

## 9. What already exists in the sibling that is directly portable

I went looking because the honest delta depends on whether this is greenfield. It is not. **[V]**

| Piece | Sibling location | Lines | Portability |
|---|---|---|---|
| **DQfD margin loss `J_E`** | `injection_rung1/margin.py:49-68` `dqfd_margin_loss` | 68 (whole file) | **Directly portable.** Imports `torch` and nothing else — no env, no config, no trainer. Cites Hester et al. 2018, `DQFD_MARGIN_DEFAULT = 0.8`, `DQFD_LAMBDA_DEFAULT = 1.0`. Also ships `qw_valid_spread` (`:32-46`), the margin-scale diagnostic. |
| **Demonstration-pool loader + fixed-ρ batch mixing** | `route_b_factorial/external_inject.py` (142) + `injection_rung1/pool.py` (579) | 142 / 579 | Adaptable, not portable — `.npz` schema and sha-pinning logic transfer; the `RouteBStepReplay` bundle layout does not. |
| **ρ-mixing trainer wiring** | `injection_rung1/trainer.py:1-30, 92-122` | 398 | Reference only (it subclasses the sibling's route-B trainer). The design is the useful part: `n_ext = round(ρ·B)` items **replace** self-samples inside the same minibatch budget, never add to it, with a dedicated `_pool_rng` so ON's pool draws cannot shift OFF's replay stream (`route_b_factorial/trainer.py:86-92`). **That RNG-lockstep discipline is the non-obvious part of a matched ON/OFF, and it was a review blocker there** (`route_b_factorial/replay.py:40-44`). |
| **Pre-training phase with target-sync schedule** | `coordinator_dqfd_zscore/study_plan.py:42, 59-65, 165-174, 231` (`pretrain_steps`, `pretrain_batch_size`, `pretrain_sync_after_steps`, `pretrain_demo_items_complete_run`, `dqfd_pretrain_final_target_online_byte_equality_required`) | pkg ≈14,900 | Reference only — it is a whole study harness, not a component. |

**One warning the sibling already paid for, written into its own source.** `injection_rung1/margin.py:38-45`:

> *"DQfD's default m = 0.8 is calibrated to Atari … On the family_b EE Q_w scale the spread is ~4e-4 (measured: `dqfd_pretrain_probe.py` SD_QW = 4.2461e-4), so a fixed m = 0.8 is ~1e3x the very quantity it is supposed to separate → the margin term dominates the max and the TD gradient becomes numerical noise (pure imitation)."*

**[V]** This is the companion facts doc's confound #2, in the sibling's own words, with a measured number. Its fix is a `scale_mode: 'qw_sd'` knob (`injection_rung1/trainer.py:70-73, 116-122`) setting `m = k·std(valid Q_w)` live per batch. **Any port here must carry that knob from day one**, and must re-measure the Q_w spread on *this* project's calibrated scale `(2029238.4, 1.0, 6.0)` — the sibling's `4.2e-4` is not transferable, exactly as the memory note "借來的診斷會翻方向" says. **[I]**

---

## 10. The judgement

### Classification: **(b) bounded code — with an honest count above the brief's bar.**

Not (a): nothing in `TrainerConfig` can turn any of this on; six of six DQfD ingredients are absent from the code, not merely disabled. **[V]**

Not (c): the trainer's interface does **not** obstruct DQfD. DQfD is single-agent — which is what this trainer is. `self.replay` is a bare attribute with three touch points; `update()` is a single method with one call site; there is no plugin registry, no abstract base, no serialized interface that a second buffer or a fourth loss term violates. **[V]** The one structural edit (§8, the per-objective optimizer loop vs. a scalarized margin term) is ~20 lines and is a reordering, not a rewrite.

It is (b) — but I will not round the number down. **Honest line count, my estimate [E], excluding tests and excluding the demonstration producer:**

| File | Change | Full DQfD | DQfD − PER |
|---|---|---|---|
| `src/mcrl/runtime/prioritized_demo_replay.py` (**new**) | Demo buffer with permanent retention + proportional priorities + ε_d/ε_a bonuses + IS weights + `state_dict`/`load_state_dict` to the same standard as the existing buffer (which spends 90 of its 150 lines on exactly that) | ~230 | ~80 (plain second FIFO buffer + fixed-ρ mixer) |
| `src/mcrl/runtime/demo_pool.py` (**new**) | Frozen `.npz` loader, sha256 pin, schema + dtype validation against the §6 7-tuple, calibration-scale assertion, mask/action validity check | ~120 | ~120 |
| `src/mcrl/algorithms/modqn.py` | n-step accumulation in `train()` (~50); `update()` restructure — demo slice, `J_E`, `J_n`, IS weights, L2, priority write-back (~100); `pretrain(steps)` method (~30); double-Q target (~5); resume-state additions (~15) | ~200 | ~190 |
| `src/mcrl/runtime/trainer_spec.py` | ~13 new `TrainerConfig` fields | ~22 | ~18 |
| `src/mcrl/runtime/trainer_config_validation.py` | Fail-loud checks for each, to the file's existing standard | ~40 | ~32 |
| `src/mcrl/runtime/training_pipeline.py` | Prereg plumbing + pool sha into `run_fingerprint` | ~30 | ~30 |
| **Total** | | **~640** | **~470** |

Plus ~200–250 lines of tests to match the repo's existing discipline (`tests/test_w12_checkpoints.py`, `test_w30_resume_checkpoint.py` already cover the surfaces being changed and would need extending). **[E]**

So: **(b), no interface break, six named files, ~470 lines for DQfD-minus-prioritization and ~640 for full DQfD — roughly 1.5–2× the ~300-line threshold the brief set for (b).** The gap between the two columns is the PER machinery; dropping it yields a mechanism the DQfD paper itself names as an ablation, not "DQfD". Calling the smaller number "the delta" would be a softening, so I am reporting both.

### The single biggest reason this would not be a faithful DQfD, even after the delta

**There is no demonstrator. DQfD's `J_E` supervises the Q surface toward an expert's action; this project has no source of expert actions on the MODQN action space, at any budget, and the delta above does not create one.**

Evidence:

- **[V]** `grep -rniE 'def .*(myopic|greedy|oracle|expert|specialist|teacher|baseline_policy)' --include=*.py src/ scripts/` over the current tree returns nothing that is a policy over the 28-action MODQN space. The hits are: `modqn.py:291 _select_masked_greedy_action` and `head_pivotality.py:79 masked_greedy_actions` (greedy over the **learned** Q — the student, not a teacher); `cells.py:240 greedy_coverage_order` (a cell-grid geometry helper — I read `:240-270`, it is greedy max-coverage over sampled service-area points, not an action policy); and the `ee_axis_*` / `lcsrs_*_teacher` modules, which live in **stage C**, over a different action catalogue, and which the facts doc establishes are comparator/label machinery, not a replay source.
- **[V, from the companion facts doc's verified section, which I did not re-run]** The nearest thing the project owns — `S_UNI`, exact iterated unilateral improvement with a termination certificate — **did not reach its certificate on even anchor 0 at 600 s, 60× the 10 s production budget**, and falls back to `DEADLINE_FALLBACK_BASE`. A demonstrator that cannot certify one anchor cannot fill a pool. Nothing DFT+WMMSE-shaped exists in either tree.
- **[V]** The sibling already ran the experiment that this failure mode produces. `route_b_factorial/external_inject.py:1-15` states the distinction in its own module docstring: injecting *the agent's own* high-value transitions is **self-imitation**, *"ceiling-limited, empirically subsumed on family_b"*; what makes injection a different mechanism is that the pool comes from a specialist reaching *"EE ≈ 552 @ 0.98 coverage … far above MODQN-L's ≈ 388"*, carrying *"actions/states MODQN's own policy does NOT generate (off-MODQN-policy)."* Without a better-than-learner source, DQfD here degenerates precisely into the arm that was already found subsumed.

This is why the cost answer in §7 is beside the point. 1.32 h for a 3000-episode arm is nothing; ~640 lines is a week. The blocking quantity is a demonstration pool that does not exist, whose producer is not in either repository, and whose only local candidate has a measured wall-clock failure at 60× budget. **Any plan that counts the trainer delta as the cost of a DQfD arm is counting the cheap half.** **[I, from the verified items above.]**

A second reason, close behind and worth pre-declaring rather than discovering: **the margin scale.** `J_E`'s `m` must be commensurate with the spread of the very Q surface it separates; DQfD's `m = 0.8` is an Atari number; the sibling measured its own `Q_w` spread at `4.2461e-4` and found `m = 0.8` to be ~1e3× too large, turning the arm into pure imitation with TD as numerical noise (`injection_rung1/margin.py:38-45`) **[V]**. This project's Q surface lives on a *third* scale again — calibrated by `(2029238.4328742754, 1.0, 6.0)` **[V]** — so both the Atari default and the sibling's measured value are wrong here, and the spread must be measured on this env before any arm is declared. The `scale_mode: qw_sd` knob exists in the sibling and should be ported as a requirement, not an option.

---

## Evidence classification summary

**Verified by opening the file or running a read-only check, this session:** every file:line in §§1–9 — `modqn.py:84, 123-145, 261-272, 291, 498-509, 511-570, 574-577, 579-584, 881-924, 926-1020, 1077-1380 (esp. 1226, 1261-1282, 1324)`; `replay_buffer.py:13-55, 57-110, 113-152`; `trainer_spec.py:25-135, 139-160`; `trainer_config_validation.py:1-70`; `training_pipeline.py:385-404, 434-472, 844-856, 1160-1260`; `objective_math.py:25-50`; `q_network.py` (whole); `env/step_types.py:129-143`; `env/cells.py:235-270`; `state_encoding.py:131-142`; `scripts/run_server_training.py:1-80`. The four `status.json` timing rows and the local `code_sha256` recomputation. The import + env-construction smoke in `.venv`. All six absence greps in §8 and their sibling counterparts. In the sibling: `catfish_faithful_familyb/trainer.py:102, 115-160, 480-497`; `presets.py:110-120, 138-150`; `injection_rung1/margin.py` (whole, 68 lines); `route_b_factorial/external_inject.py:1-82`; `route_b_factorial/trainer.py:81-92, 157`; `route_b_factorial/replay.py:40-44`; `injection_rung1/trainer.py:1-122`; `coordinator_dqfd_zscore/study_plan.py:42, 59-65`; the five enabling YAMLs; the three `abl9k_strategy3_acrm` `run_metadata.json` files and the wave's `ALL-DONE.sentinel`.

**Inferred (reasoning over verified facts, not measured):** that a modified trainer still runs because `code_sha256` is recorded rather than enforced; that the per-objective optimizer loop must be restructured for a scalarized margin term and that this forces the OFF arm to be re-run; that a demo region cannot share the FIFO deque; that the absence of a demonstrator reduces DQfD here to the sibling's already-subsumed self-imitation arm.

**Estimated (my numbers, flagged as such):** every line count in §10's table; the ~26 min pre-training extrapolation in §7.

**Taken from the companion facts doc without re-verification:** the `S_UNI` 600-second non-certification, and that nothing DFT+WMMSE-shaped exists in either tree.

**Not established here:** what the sibling's ACRM arms measured on EE (I read their instrumentation, not their outcome); whether the +260-line `modqn.py` delta in commit `14174d60` touched `update()`/`train()` semantics or only added diagnostics — I verified the hashes differ and the line counts, not the semantic content of that diff; whether DQfD's published results are independently reproduced (DQFDGROUND's question, not mine).
