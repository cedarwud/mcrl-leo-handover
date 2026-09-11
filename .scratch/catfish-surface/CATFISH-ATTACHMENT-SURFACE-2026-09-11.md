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

---

## Follow-up: is there a demonstrator on the MODQN action space

**Answer in one line: the premise as handed to me does not survive checking — `41.28` is a beam count, not an EE — but the underlying question has a better answer than my §10 gave, because a one-line rule that IS expressible on the MODQN action space beats the trained MODQN checkpoint by +23.9% on r1, measured by me on the MODQN harness this session. It is not `GAIN_IN_SET`, it is `RSS_MAX`, and on MODQN's own scalarized objective it is worse than the learner, not better.**

Added 2026-09-11 after the coordinator's follow-up. Still read-only: no training, no gradient step, one scripted rollout in the env, four read-only `ssh sat` file reads. Nothing written outside this report, `PROGRESS.md`, and the session scratchpad.

### 4 first, because it decides the rest — the premise does not check out

The coordinator's framing was *"`GAIN_IN_SET` … measured at pooled EE 62.502712 Mbit/J … against the learned policy's 41.28."* I read both source documents on `sat`. **That comparison is not like-for-like, and it is not a comparison of two EEs.**

**(i) `41.28` is a beam count, not an EE.** **[V]** `/home/sat/mcrl-v025-probe-ws/BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md:30` is a row of a table whose column headers are at `:25`:

| Profile | Profiles | `modal_frac` | **Active beams mean [range]** | Active satellites | `argmax_distinct` | Null users |
|---|---|---|---|---|---|---|
| Learned `a0`, q1-v1 sensitivity | 286 | 0.06864 | **41.28 [1, 60]** | 5.57 | 0.41283 | 4.51 |

`41.28` is the mean number of distinct selected physical beams. Its own document says at `:5`: *"This is a design-phase diagnostic, not a performance or EE claim."* Comparing `62.502712 Mbit/J` to `41.28 beams` is a unit mismatch. (I note the near-coincidence that `RSS_MAX` pooled EE is **41.621560** Mbit/J on the same panel family — two different quantities that both round to "41.")

**(ii) The learned policy's EE on that panel was never measured. The job that would have measured it was stopped.** **[V]** `/home/sat/mcrl-v025-beamcount-ws/BEAM-COUNT-CAP-2026-09-10.md:279-289`, heading verbatim: **"Part 3 — where the current policies land: NOT COMPLETED"**, body: *"was launched and then **stopped by the controller's cost-control instruction before its first anchor completed**. No projected number is reported and **none should be inferred**."* And on the two counts it does cite: *"Those counts are on the 22 TRAIN anchors, not this 12-anchor panel, and **carry no EE**."*

**(iii) `62.502712` is not a rule's score. It is a search winner selected on a proxy field.** **[V]** From the same report `:156-207`: the C = 50 winner is the best of nine declared rules **plus** first-improvement single-user local search (up to 3 passes) **plus** the nested winners of every smaller cap and `RSS_MAX`, with the winner picked by **boundary-0** EE. The best *declared rule* at C = 50 is `S2 + A2` at **52.042303** Mbit/J (`:222-241` table), 16.7% below the headline. And `/home/sat/mcrl-v025-specprofile-ws/PROGRESS.md:47` states the provenance outright: *"`GAIN_IN_SET` = the BEAMCOUNT `CAP_050` winner; winner_start `RSS_MAX_within_cap` (polished) at step 0 and `INHERITED_CAP_030_WINNER` at steps 1-3."* The name `GAIN_IN_SET` appears **nowhere** in `/home/sat/mcrl-v025-beamcount-ws/` (grep, 0 hits) — it is a later label for a search output, not a rule. The beamcount report also discloses that its selection field overstates: *"the uncapped search raised boundary-0 EE from `RSS_MAX` 71.84 to 114.06 while full-48 EE *fell* to 65.38"* (`:327-331`).

**(iv) Neither number is on the MODQN harness.** Both are V0.25 `a-r0` successor physics, 12 development anchors, `V025_PROBE/world/1`, 4 physical steps. The MODQN baseline is a different environment entirely. **[V]**

So the answer to question 4 is: **no, "the demonstrator beats the learner" was not a like-for-like claim, and it was not measured. It should not be carried forward.** This is precisely the shape the standing memory note *「報數字要帶四個欄位」* (reference point / information class / estimator / numerator) exists to catch.

### 1. The MODQN action space and per-step observation, precisely

**Action space** — `src/mcrl/env/action_contract.py:14-16`: **[V]**

```
a = 7·l + j        l ∈ {0,1,2,3} satellite slot,  j ∈ {0,…,6} beam slot
```

`NUM_SATELLITE_SLOTS = 4` (`:40`), `NUM_BEAM_SLOTS = 7` (`:43`), `NUM_ACTIONS = 28` (`:68`), plus `NO_OP_ACTION = -1` (`:71`) which is *"not a beam index and not maskable: it is the absence of a decision."*

**The decisive property: the index is user-relative, and it is not a beam identity.** `:43-58` — `J_w = 7` is *"how many cells one **user** can reach (their own plus the six neighbours)"*, and the module's load-bearing rule at `:16-18` is *"handover is decided from the REALISED ASSOCIATION (norad_id, cell_id), **never from the action index**"*, because the candidate table *"changes between steps"* (`state_encoding.py:149-151`). **[V]** User A's action 5 and user B's action 5 are different physical beams. (The MODQN-COLLAPSE report on `sat` reached the same conclusion from the other side: MODQN is concentrated in *local action-slot* indices while being physically spread.)

**Observation** — 112 = 4 × 28 (`state_encoding.py:139`), four blocks, built at `src/mcrl/env/step.py:1125-1184`: **[V]**

| Block | Content | Built at | What it gives a rule |
|---|---|---|---|
| 1 | `access` = `x_u(t−1)` one-hot **in the current candidate ordering** | `step.py:1125-1141` | the incumbent's *slot*, never its identity |
| 2 | `channel_quality` = per-candidate SINR, *"gamma over every candidate, **previous-step interference**"* | `step.py:1151-1152` | **the per-user per-option nominal gain** |
| 3 | `beam_offsets` = per-candidate off-axis θ, radians | `step.py:1143-1149` | geometry |
| 4 | `beam_loads` = *"`N_u(t−1)`: the previous step's **UNGATED** demand"*, looked up by physical beam `(norad, cell)` | `step.py:1163-1174`; semantics `step_types.py:95-107` | congestion, **one step stale** |

**Which of `GAIN_IN_SET`'s three ingredients are computable at decision time:**

| Ingredient | Available? | Evidence |
|---|---|---|
| **per-user per-option nominal gain** | **YES.** Block 2 is exactly this, and it is a *nominal* estimate carrying previous-step interference — no realised current-step fading is needed or used. | `step.py:1151` **[V]** |
| **the active beam set** | **NO — and it is not a decision variable at all.** In MODQN activation is *derived*, not chosen: `beam_active_b = beam_load_b > 0.0` (`step.py:1027`), documented as *"activation is derived, `z = 1{U > 0}` (ruling 2026-08-22 §7.4)"* (`step_types.py:104-106`). No user observes the union of the 100 users' choices; each sees only its own 28 slots' *previous-step* demand. | **[V]** |
| **the cap** | **NO — it does not exist in this project, by ruling.** `action_contract.py:60-64`: *"there is deliberately **no per-satellite beam-count constant anywhere in this project** (ruling 2026-08-22 §7.2-7.3)."* | **[V]** |
| another user's committed choice **this** step | **NO.** Block 4 is `t−1`. | `step.py:1163` **[V]** |

### 3. The two physics differ in action space — stated plainly, because it is true

**They are different decision problems, and the difference is exactly the half of `GAIN_IN_SET` that does the work.** **[V]**

| | MODQN baseline | V0.25 `a-r0` successor |
|---|---|---|
| Option identity | user-relative slot `(l ∈ 4, j ∈ 7)` | **global** `(norad_id, cell_id)`, e.g. `(57502,25)` — `run_v025_matrix_probe.py:435-439` |
| Options per user | 28, fixed by construction | 28 legal at the measured panel, from a top-K shortlist |
| Satellites | 4 slots | **9** |
| Distinct physical beams | not a modelled global set | **370** |
| Active beam set | **derived** (`z = 1{U>0}`) | **chosen** — an explicit decision variable |
| Beam-count cap | **none, by ruling** | swept {8,9,10,15,20,30,50} |
| Steps | 10 per episode, episodic | 4 physical steps per anchor |
| Objective | vector `(r1, r2, r3)`, weights `(0.5, 0.3, 0.2)` | scalar pooled EE, with QoS reported beside |

`GAIN_IN_SET` = *choose a global beam set S under a cap*, then *assign each user its max-gain option inside S*, then *polish by single-user local search on boundary-0 EE*. **Only the second clause is expressible over MODQN's action space.** The first clause names an object MODQN has no decision variable for and no cap on; the third is an outcome-selected search, not a policy.

**And the expressible half has a name and a measured value on the V0.25 panel: it is `RSS_MAX`, 41.621560 Mbit/J** (`BEAM-COUNT-CAP-2026-09-10.md:68`) — **below** the crowded min-cover's 46.110374 and 33% below the 62.502712 headline. **[V]** So the portable half of the rule is the *weakest* member of the family there, not the strong one. That is the honest translation.

A second, independent mismatch that would remain even if the set clause were expressible: **`GAIN_IN_SET` hands over almost every user, every step.** `/home/sat/mcrl-v025-specprofile-ws/PROGRESS.md:33-35`, rehearsal anchor `V025_PROBE/world/1|0|nearest-eligible`, full-48 endpoint: `GAIN_IN_SET` 98 handovers / Φ = 59.5 κ; `RSS_MAX` 100 handovers / Φ = 60.0; `BASE` 0 handovers / Φ = 0. **[V]** MODQN does not optimise EE — it optimises `0.5·r1 + 0.3·r2 + 0.2·r3` with `r2` the handover penalty. A near-total-churn demonstrator supervises against 30% of the learner's declared objective by construction.

### 2. What a demonstrator on the MODQN action space actually costs — measured, not argued

Because the max-nominal-gain clause **is** expressible, I ran it. One scripted rollout, no gradient step, no `update()` call, `MODQNTrainer` used only for its env/reward plumbing so the statistic is the trainer's own `EpisodeLog.r1_mean`. Script: session scratchpad `scripted_probe.py` (95 lines). 8 episodes per arm, `train_seed=42, env_seed=1337, mobility_seed=7` — the frozen run's seeds. **[V]**

**Harness verification first.** My `RANDOM_MASKED (ε=1)` arm reproduces the frozen run's own first eight episodes (which ran at ε ≈ 1.0), so the accounting is the same accounting:

| | r1_mean | r2_mean | r3_mean |
|---|---:|---:|---:|
| frozen run, episodes 0–7 (`episode-logs.json`) | 5.416029e+06 | −7.779 | −13.514 |
| my `RANDOM_MASKED` arm, 8 episodes | 5.543606e+06 | −7.762 | −13.350 |
| delta | +2.4% | +0.2% | +1.2% |

**Results.** `r1` is the raw per-user system-EE contribution in bit/J; "calibrated scalar" is `Σ ωⱼ·rⱼ/cⱼ` with the run's own `(0.5,0.3,0.2)` and `(2029238.4328742754, 1.0, 6.0)` — i.e. **MODQN's actual training objective**:

| Arm | r1_mean (bit/J) | vs trained r1 | r2_mean | r3_mean | active slots | **calibrated scalar** |
|---|---:|---:|---:|---:|---:|---:|
| `RANDOM_MASKED` (ε=1) | 5.543606e+06 | −38.0% | −7.762 | −13.350 | 26.76 | −1.4077 |
| `UNTRAINED_Q_GREEDY` | 4.255708e+06 | −52.4% | −3.413 | −27.585 | 2.70 | −0.8948 |
| **`MAX_NOMINAL_GAIN`** (the expressible half; RSS_MAX analogue) | **1.107376e+07** | **+23.9%** | −6.761 | −20.968 | 13.14 | **+0.0013** |
| `LEAST_LOADED` (A3 analogue) | 6.423171e+06 | −28.1% | −5.747 | −46.720 | 4.86 | −1.6988 |
| `GAIN_PER_LOAD` (snr/(1+load)) | 1.008737e+07 | +12.9% | −8.073 | −23.171 | 15.36 | −0.7088 |
| **trained MODQN `e6b063ef…`, last 100 episodes** | **8.938629e+06** | — | −2.322 | −18.598 | — | **+0.8859** |

Two readings, and they point opposite ways:

1. **On r1 alone there IS a demonstrator, and it is one line of code.** `MAX_NOMINAL_GAIN` = `argmax over the mask of state block 2` beats the 9000-episode trained checkpoint by **+23.9%** on r1. Controlling for RNG-stream position via the random arm (mine sits at stream position 0–7, the trained tail at 8900–8999): rule/random = **1.998** against learned/random = **1.650**, so ~21% of the gap survives the control. This is the standing memory note *「先跑非學習基線再量天花板」* reproducing itself on a third harness.
2. **On MODQN's declared objective it is not a demonstrator at all.** Calibrated scalar **+0.0013 vs the learner's +0.8859**. The rule buys r1 by handing over three times as often (r2 −6.761 vs −2.322) and crowding beams (r3 −20.968 vs −18.598). Its EE win is bought with exactly the two terms MODQN is also paid to protect.

**Cost of generating demonstrations, measured.** A scripted rollout with no gradient step: **4.5408 s/episode on this local WSL host** (timed, 3 episodes, 13.622 s). **[V]** So 500 demonstration episodes = **37.8 min locally**. On the host that produced the frozen run, full training — env step *plus* ten gradient steps — ran at 1.5869 s/episode, and a rollout without the gradient steps cannot be slower on the same host, so **500 episodes ≤ 13.2 min there**. **[V for both rates; the server bound is a bound, not a measurement.]** For scale: 500 episodes × 10 steps × 100 users = **500,000 transitions**, ten times the 50,000 buffer capacity — **50 episodes already overfills it**, so demonstration generation is a ~4-minute job, not a budget item.

**Tuple shape to write them into** — unchanged from §6, `replay_buffer.py:29-54` and `:113-152`: the 7-field tuple `(state float32 (112,), action int (bool rejected), reward_3 float32 (3,), next_state float32 (112,), mask bool (28,), next_mask bool (28,), done bool)`, with `reward_3` **post-`apply_reward_calibration`**, `state` from `encode_state`, no-op actions dropped, and `done or next_mask.any()`.

**Line count for a production demonstration generator** — the probe I ran is 95 lines for five arms; a single-arm version that also writes a frozen `.npz` with a sha256 pin and validates the tuple schema on the way out is **~130–150 lines**, one new file. **[E]** That is *inside* the ~470–640 estimate of §10, not additional to it: §10's `demo_pool.py` (~120) is the *loader*; this is the *producer*, and it is the item §10 said did not exist.

### What this changes in §10, and what it does not

**Changed.** My §10 statement *"there is no demonstrator … at any budget"* was about `src/`, and the coordinator is right that it under-answered. Corrected: **a cheap, deployable, better-than-learner-on-r1 demonstrator does exist on the MODQN action space, it is realizable from the observation alone (it is an argmax over one of the four state blocks, so a network of this capacity can represent it — which is what `J_E` needs), and producing 500 episodes of it costs minutes.** The DQfD delta therefore has something to point at that I said it did not.

**Not changed, and now sharper.** The failure reason moves rather than disappears. It is no longer "no demonstrator exists"; it is:

> **The only demonstrator that is both expressible and better than the learner is better on r1 only, and is worse than the learner on the objective MODQN is actually trained on (+0.0013 vs +0.8859 calibrated scalar). DQfD's `J_E` would supervise the argmax of the scalarized `Q_w = Σ ωⱼQⱼ` — the decision surface — toward actions selected by a rule that ignores two of its three terms. The margin loss would pull the policy *away* from its own objective while the TD loss pulls it back, and `λ₂` would be tuning the trade-off between them rather than weighting a supervision signal that agrees with the reward.**

That is a real and testable design problem, not a dead end. Three ways out, none of which I am authorised to pick, all cheap to screen with the harness above:

1. **Build the demonstrator on the scalarized objective, not on r1.** A one-step greedy over a *predicted* `0.5·r̂1 + 0.3·r̂2 + 0.2·r̂3` — `r2` is predictable at decision time from block 1 (the incumbent's slot is in the state, so "does this action change my association" is observable) and `r3` from block 4. That is still a one-line-ish rule and it is the honest analogue of `A2` for *this* objective. Nobody has measured it; my `GAIN_PER_LOAD` arm is a crude two-term version of it and already recovers +12.9% on r1 at −0.7088 scalar, i.e. worse. **A myopic-scalar demonstrator is the single cheapest unmeasured thing in this whole report.**
2. **Accept the objective mismatch and pre-declare it** — run DQfD with an r1-only demonstrator and score on r1 only, with r2/r3 reported beside it as the price. Legitimate, but it changes the claim from "DQfD improves MODQN" to "DQfD improves MODQN's EE term at a stated handover cost."
3. **Drop `J_E` and keep the rest** — demonstrations in replay + n-step + pre-training, with no margin term. That is closer to "DQfD without the supervised loss", which the DQfD paper's own ablations report as the component that matters most, so it is the weakest of the three.

**Every prior caveat stands**: the margin-scale hazard of §9 is unchanged and now has a specific number to be measured against (the spread of the calibrated `Q_w`, not r1's raw bit/J); the delta is still (b) at ~470–640 lines; the OFF arm must still be re-run.

### Evidence classification for this section

**Verified by reading primary source (`ssh sat`, read-only):** `BEAM-COUNT-CAP-2026-09-10.md` lines 1, 39-57, 94-115, 156-241, 279-289, 327-345; `BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md:5, 15-17, 25-33`; `/home/sat/mcrl-v025-specprofile-ws/PROGRESS.md:24, 33-36, 47`; `run_v025_matrix_probe.py:422-439`; the 0-hit grep for `GAIN_IN_SET` under `/home/sat/mcrl-v025-beamcount-ws/`.

**Verified by reading local source:** `action_contract.py:14-24, 40-68, 71`; `step.py:1027, 1125-1184`; `step_types.py:95-107`; `state_encoding.py:139, 149-151`; `replay_buffer.py:29-54, 113-152`; `episode-logs.json` (9000 records).

**Verified by running code, this session, read-only, no gradient step:** the five-arm scripted probe (8 episodes each) and the 3-episode rate measurement, both in the session scratchpad, both using the frozen run's seeds; the random-arm agreement with the frozen run's episodes 0–7; the calibrated-scalar arithmetic.

**Estimated:** the ~130–150-line producer.

**Not established:** the myopic-scalarized demonstrator of option 1 — proposed, never measured. Whether the +23.9% r1 gap survives at the frozen run's RNG-stream position (I controlled for it by ratio against a matched random arm; I did not advance the stream 8,900 episodes). Whether `GAIN_IN_SET`'s advantage over `RSS_MAX` on V0.25 would reappear in MODQN physics — untestable, since MODQN has no beam-set decision variable.

---

## Scalarized-objective demonstrator

**No. No expressible arm beats the trained checkpoint on the scalarized objective: the best of them, `GREEDY_R1R2`, scores +0.8750 ± 0.0236 (n = 24) against the checkpoint's +0.8859 ± 0.0190 (n = 100) — a point estimate **below** the target, statistically indistinguishable from it, and further below the checkpoint's five-window plateau mean of +0.9257; every arm was realizable from the 112-dim observation alone, so this is not a representability failure but an absence.**

Added 2026-09-11 on the coordinator's instruction, after erratum 23 accepted the three corrections above. Read-only: no `update()` call, no gradient step, no optimizer touched; `MODQNTrainer` used only for env-reset / encode / reward-vector plumbing so every statistic is the trainer's own `EpisodeLog` quantity. Scripts in the session scratchpad (`scalar_demo.py`, `scalar_power.py`). **[V for everything in this section unless marked.]**

### How the myopic predictions are built, and what makes them observation-only

Every arm scores each legal action `a` for each user `u` from that user's 112-dim state and nothing else — no realised fading, no future state, no other user's current-step choice.

| Term | Prediction | Source in the observation | Exact? |
|---|---|---|---|
| `r̂1_raw(u,a)` | `(B / (load[u,a]+1)) · log₂(1 + sinr[u,a])` bit/s — eq. (3.14) `R = (Bʷ/U)·log₂(1+γ)`, `link_budget.py:590-615`, `B = 1.666667e8 Hz` | block 2 `channel_quality` (per-candidate SINR, previous-step interference, `step.py:1151`) and block 4 `beam_loads` | **Approximate.** The realised r1 is `R_u / P^N`, and `P^N` is a global scalar absent from the observation, so the rule carries **one** free positive constant `κ`. |
| `r̂2(u,a)` | `0` if `a` = incumbent slot; `−φ1 = −0.5` if `a // 7` = incumbent's satellite slot; `−φ2 = −1.0` otherwise | block 1 `access` one-hot + the action index layout `a = 7l + j` (`action_contract.py:14-16`); `PHI1 = 0.5`, `PHI2 = 1.0` (`action_contract.py:408, 411`); branch rule `classify_handover` (`:422-457`) | **Exact**, except when block 1 is all-zero (incumbent left the candidate table): φ1 and φ2 are then indistinguishable, so I charge −φ2 for every action — constant across actions, hence no effect on that user's argmax. |
| `r̂3(u,a)` | `−(load[u,a] + 1)` — the count form `−U_{b_u}` in whole users (`step_types.py:178-180`) | block 4, which is `N_u(t−1)`, **the previous step's ungated demand** (`step.py:1163-1174`) | **Approximate and one step stale**, unavoidably: no user can see this step's committed choices. |

Score, in the trainer's own calibrated units — `objective_weights (0.5, 0.3, 0.2)`, `reward_calibration_scales (2029238.4328742754, 1.0, 6.0)`:

```
s(u,a) = 0.5·κ·r̂1_raw(u,a)  +  0.3·r̂2(u,a)  +  0.2·r̂3(u,a)/6
```

**The one free constant, and why sweeping it makes the negative stronger.** `κ` absorbs the unobservable `1/(P^N · 2029238.43)`. Rather than pick it, I anchored it (`κ* = 8.394622e-10`, set so the median legal candidate's calibrated r1 term equals the trained checkpoint's own realised 0.44049 per user-step — a physically sane anchor: it implies `P_REF ≈ 587 W`) and then **swept a multiplier `m` over eight declared values spanning five decades**, so no value of the constant can be blamed for the outcome:

| m | r1_mean | r2_mean | r3_mean | **calibrated scalar** | handover rate |
|---:|---:|---:|---:|---:|---:|
| 0 (r1 ignored) | 6.592553e+06 | −2.352 | −32.670 | −0.1701 | 0.3243 |
| **0.1** | 7.629748e+06 | −1.427 | −16.903 | **+0.8885** | 0.1497 |
| 0.3 | 7.494579e+06 | −1.520 | −16.007 | +0.8571 | 0.1673 |
| 1 | 9.841624e+06 | −4.692 | −18.100 | +0.4141 | 0.6090 |
| 3 | 9.891890e+06 | −7.637 | −24.547 | −0.6719 | 0.8873 |
| 10 | 1.004349e+07 | −8.202 | −25.147 | −0.8240 | 0.8993 |
| 100 | 9.866370e+06 | −8.430 | −23.570 | −0.8836 | 0.8990 |
| 10⁴ (≈ pure rate max) | 9.901748e+06 | −8.435 | −23.653 | −0.8792 | 0.8990 |

The curve is single-peaked at `m* = 0.1` and falls away in both directions. 3 episodes each; used only to fix `m*`.

### Result — all arms, 8 episodes each at `m*`

| Arm | r1_mean | r2_mean | r3_mean | **calibrated scalar** | ho rate | φ1 rate | φ2 rate | r1 vs random |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `RANDOM_MASKED` (harness check) | 5.554242e+06 | −7.756 | −13.361 | −1.4037 | 0.8664 | 0.1815 | 0.6849 | 1.000 |
| `MAX_NOMINAL_GAIN` | 1.107121e+07 | −6.757 | −20.964 | +0.0021 | 0.7010 | 0.0506 | 0.6504 | 1.993 |
| `GREEDY_SCALARIZED` (r1+r2+r3) | 7.462246e+06 | −1.426 | −15.936 | +0.8798 | 0.1486 | 0.0121 | 0.1365 | 1.344 |
| `GREEDY_R1R2` | 7.518463e+06 | −1.366 | −16.587 | +0.8897 | 0.1366 | 0.0000 | 0.1366 | 1.354 |
| `GREEDY_R1R3` | 9.321370e+06 | −8.364 | −25.389 | −1.0587 | 0.9000 | 0.1273 | 0.7728 | 1.678 |
| **trained `e6b063ef…`, last 100 ep** | **8.938629e+06** | **−2.322** | **−18.598** | **+0.8859** | **0.2490** | — | — | 1.650 |

`RANDOM_MASKED` reproduces the frozen run's own first eight episodes (which ran at ε ≈ 1.0) — r1 5.554e+06 vs 5.416e+06, scalar −1.4037 vs −1.4498 — so the accounting is the same accounting. (The residual is expected: the frozen run's `_train_rng` is also consumed by `replay.sample` at `modqn.py:527`, so the two streams diverge once its buffer fills.)

### The 8-episode margin was noise. At n = 24 it reverses.

`GREEDY_R1R2` at +0.8897 sat +0.0038 above the target — inside a tenth of one standard deviation of the reference (trained sd = 0.1898). So I reran the two candidate arms at **n = 24** with per-episode scalars, same seeds, no `update()`:

| Arm | scalar mean | sd | sem | handover rate |
|---|---:|---:|---:|---:|
| `GREEDY_SCALARIZED` | **+0.8659** | 0.1135 | 0.0232 | 0.1501 |
| `GREEDY_R1R2` | **+0.8750** | 0.1155 | 0.0236 | 0.1412 |
| `MAX_NOMINAL_GAIN` | −0.0866 | 0.2083 | 0.0425 | 0.7115 |
| trained checkpoint, last 100 ep | +0.8859 | 0.1898 | 0.0190 | 0.2490 |

**Best scripted arm +0.8750 vs +0.8859: delta −0.0109**, against a combined sem of ≈0.0303. The point estimate is below the target and the difference is not resolvable.

And the reference is not a lucky window. The checkpoint has plateaued — five separated 100-episode windows: ep 4000–4100 **+0.9509**, 6000–6100 **+0.9259**, 7000–7100 **+0.9349**, 8000–8100 **+0.9311**, 8900–9000 **+0.8859**; plateau mean **+0.9257**. Measured against the plateau rather than the final window, the gap widens to **−0.0507**. This also bounds the residual RNG-stream-position confound (my arms sit at stream positions 0–23, the reference at 8900–8999): the trained level does not move systematically with position across 5,000 episodes.

### Which term carried it, and which broke it — both questions answered

- **`r2` is the term that carries the whole thing.** Removing it (`GREEDY_R1R3`) collapses the arm to **−1.0587**, the worst of every arm including random-with-r1-blind, and drives the handover rate to **0.9000**. The scalarized rule's entire advantage over `MAX_NOMINAL_GAIN` is handover suppression.
- **`r3` does not carry it; its stale prediction is mildly harmful.** Removing it (`GREEDY_R1R2`) *improves* the arm. Paired over the same 24 episodes and seeds: `GREEDY_R1R2 − GREEDY_SCALARIZED = +0.0091, sd 0.0168, sem 0.0034` — small but ~2.7 sem, so real. Block 4 is `N_u(t−1)`; steering on a one-step-stale load count costs more than it buys.
- **`MAX_NOMINAL_GAIN`'s collapse on the scalar is confirmed to be r2, as suspected.** Its handover rate is **0.7115** against the trained policy's **0.2490** and `GREEDY_SCALARIZED`'s **0.1501** — 2.9× the learner's. Its r1 advantage (+23.9%, 1.993× random) is real and survives; it is simply paid for at a price the objective does not accept. At n = 24 its scalar is **−0.0866**, i.e. below zero, not the marginal +0.0021 that 8 episodes suggested.

### Realizability

Moot in the direction that matters, but worth stating because it removes an escape route: **every arm above is realizable from the observation alone.** Each is an argmax over an affine combination of three functions of the 112-dim state at decision time — no realised fading (block 2 carries *previous-step* interference), no future state, no other user's current-step choice (block 4 is `t−1`), and the single free constant `κ` is a declared scalar, not information. A network of this capacity can represent them. So the finding is **not** "the demonstrator exists but `J_E` cannot be trained toward it"; it is that **the demonstrator does not exist**: among the expressible myopic rules over MODQN's declared objective, none reaches the learner.

### Verdict

**No arm beats +0.8859.** The best expressible myopic scalarized rule ties the trained checkpoint within measurement error with the point estimate below it, and falls −0.0507 short of its plateau. Combined with §"Follow-up" — where the only arm that *did* beat the learner beat it on r1 alone and scored +0.0021 (n=8) / −0.0866 (n=24) on the objective — the position on the MODQN action space is:

- there is a better-than-learner source **for r1 alone**, at 1.993× random against the learner's 1.650×;
- there is **no** better-than-learner source for the objective the learner is trained on;
- and the term that separates them is `r2`, which every high-EE rule violates and which the learner has evidently learned to respect (handover rate 0.2490 while holding r1 at 1.650× random).

Per the coordinator's instruction I am not widening the search and not proposing a rescue. The design decision is the coordinator's.

### Evidence classification for this section

**Verified by running code, this session, read-only, no gradient step:** the κ sweep (8 points × 3 episodes), the five-arm panel (8 episodes each), the higher-n paired rerun (3 arms × 24 episodes), and the harness-validity agreement between `RANDOM_MASKED` and the frozen run's episodes 0–7. All at `train_seed=42, env_seed=1337, mobility_seed=7`.

**Verified by reading local source:** `link_budget.py:590-615` (eq. 3.14 and `BEAM_BANDWIDTH_HZ`); `action_contract.py:14-16, 402-457` (index layout, `PHI1`/`PHI2`, `classify_handover`); `step.py:1027, 1125-1184`; `step_types.py:95-107, 178-180`; `episode-logs.json` (9,000 records — the trained mean, sd, plateau windows and `total_handovers`).

**Derived:** the calibrated scalars (`Σ ωⱼ·rⱼ/cⱼ` with the run's own constants); the sems; the implied `P_REF ≈ 587 W`; the plateau mean +0.9257.

**Residual caveat, not eliminated:** my arms are measured at env-RNG stream positions 0–23 and the reference at 8900–8999. I bounded it two ways — a matched random arm at positions 0–7, and the five-window plateau showing no positional drift in the reference — but I did not evaluate the checkpoint itself at positions 0–23, which would need the frozen weights (on `sat`) and an evaluation run.

**Not established:** anything about arms I did not run. Non-myopic rules, learned demonstrators, and rules using information outside the observation were out of scope by instruction and are not evidence either way.

---

## Pooled EE — the declared primary endpoint

**On the declared estimand — pooled bits over pooled joules, two running totals divided once — `MAX_NOMINAL_GAIN` scores 111,553,182.85 bit/J (3.267020e+14 bits / 2.928666e+06 J) against the trained `e6b063ef…` checkpoint's 93,137,893.02 bit/J (2.850357e+14 bits / 3.060363e+06 J): the scripted rule is 1.1977× the learner, +1.8415e+07 bit/J, a 13.2-sem gap that is comfortably resolvable at this seed count — so by the pre-declared reading this is the second branch, **the trained objective and the declared primary objective disagree**, and it is a finding about the objective, not a reopening of the demonstration line.**

Added 2026-09-11 on the coordinator's instruction; the pre-declared reading was fixed before the run and is applied as written. Read-only: no `update()` call, no gradient step, no optimizer step; the trained arm **loads** the frozen checkpoint read-only. Script: session scratchpad `pooled_ee.py`. Wall 474.4 s. **[V for everything below unless marked.]**

### Estimand, stated so it is auditable

```
pooled_EE = ( Σ over all steps  system_throughput_bps · dt )
          / ( Σ over all steps  system_consumed_power_w · dt )
```

accumulated as **two running totals over all 24 episodes × 10 steps** and divided **once** at the end. Not a mean of per-step EE, not a mean of per-user EE. `dt = DECISION_STEP_S = 30.08 s` (`env/constants.py:76`). Both per-step quantities are the environment's own, read off `env.last_outcome.energy` — a `SystemEnergyEfficiency` (`runtime/energy_efficiency.py:37-49`) reached through the frozen trainer view's escape hatch (`runtime/trainer_env.py:239-248`) — **not** reconstructed by me from the reward fields.

**Numerator convention: full-buffer Shannon, no demand cap.** `env/link_budget.py:590-615` implements eq. (3.14) `R = (Bʷ / U_{s,v}) · log₂(1 + γ)`, and `env/step.py:964-970` applies it as `rate = where(served, shannon_rate_bps(sinr, beam_load=load, bandwidth_hz=...), 0.0)`. A grep for `demand_cap|rate_target|nominal_rate|setpoint|target_rate|min_rate|qos_rate` over `src/mcrl/env/` returns **zero hits**. **[V]**

**Rate attainment has no referent in this environment.** There is no nominal rate setpoint to attain — the grep above is the evidence. Rather than import the V0.25 panel's 50 Mbit/s setpoint, which belongs to different physics, I report **served rate** (the environment's own `energy.served`, users actually receiving service, over user-steps) beside every EE figure and state that attainment is undefined here. **[V]**

### Result — 24 episodes per arm, frozen seeds (42 / 1337 / 7)

| Arm | pooled bits (numerator) | pooled joules (denominator) | **pooled EE (bit/J)** | vs random | vs trained | served rate | handover rate | calibrated scalar |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `RANDOM_MASKED` (harness check) | 1.842866e+14 | 3.473162e+06 | 53,060,175.56 | 1.000× | 0.570× | 0.9360 | 0.8680 | −1.4104 |
| `GREEDY_SCALARIZED` | 2.614246e+14 | 3.473047e+06 | 75,272,421.21 | 1.419× | 0.808× | 0.9961 | 0.1502 | +0.8649 |
| `GREEDY_R1R2` | 2.612398e+14 | 3.445650e+06 | 75,817,283.47 | 1.429× | 0.814× | 0.9960 | 0.1413 | +0.8743 |
| **`TRAINED e6b063ef…`** (greedy, ε=0) | 2.850357e+14 | 3.060363e+06 | **93,137,893.02** | 1.755× | 1.000× | **0.9988** | 0.2796 | +0.9063 |
| **`MAX_NOMINAL_GAIN`** | 3.267020e+14 | 2.928666e+06 | **111,553,182.85** | **2.102×** | **1.1977×** | 0.9981 | 0.7117 | −0.0867 |

The trained arm loads `artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt`, whose SHA-256 I recomputed locally as `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b` — **byte-identical to the frozen artefact**. It therefore runs at the **same RNG stream positions 0–23 as every scripted arm**; the residual stream-position caveat carried by the previous two sections **does not apply here**, and no proxy was substituted. It is evaluated greedy (ε = 0), the deployed policy, matching the determinism of the scripted arms; for reference its calibrated scalar under these conditions is **+0.9063**, consistent with the +0.8859 training-time last-100 mean quoted earlier (measured at ε = 0.01 at a different stream position).

**Resolvability.** Per-episode pooled EE (each episode's own bits/joules), 24 episodes:

| Arm | mean | sd | sem |
|---|---:|---:|---:|
| `RANDOM_MASKED` | 53,045,171.95 | 1,932,371.59 | 394,443.70 |
| `GREEDY_SCALARIZED` | 75,253,969.10 | 3,433,511.04 | 700,862.51 |
| `GREEDY_R1R2` | 75,810,852.81 | 3,241,135.73 | 661,594.06 |
| `TRAINED e6b063ef…` | 93,081,610.83 | 4,445,489.88 | 907,431.82 |
| `MAX_NOMINAL_GAIN` | 111,558,594.999 | 5,221,058.78 | 1,065,744.16 |

`MAX_NOMINAL_GAIN − TRAINED = +1.841529e+07` against a combined sem of `1.3997e+06` — **13.2 sem**. This is resolvable at this seed count by a wide margin; the third branch of the declared reading does not apply. (The two are also run on the same 24 episodes and seeds, so a paired test would be tighter still; the unpaired figure already settles it and I did not add one.)

### Two distinct things are going on, and they must not be conflated

**(a) The estimand defect is real but small here.** Comparing the episode-level mean of ratios against the ratio of sums, arm by arm: `RANDOM` 53,045,171.95 vs 53,060,175.56 (−0.03%), `MAX_NOMINAL_GAIN` 111,558,595.00 vs 111,553,182.85 (+0.005%), `TRAINED` 93,081,610.83 vs 93,137,893.02 (−0.06%). At the episode level the two estimators agree to within 0.06% and **no ordering depends on the choice**. **[V]** I did not instrument both estimators at the per-user-per-step level in the same pass, so I do not quantify the defect at that level and will not infer it across windows. **[stated as a limit, not a result]**

**(b) The disagreement that flips the ranking is not an estimator artefact — it is that the two objectives price different things.** Pooled EE prices `r1` and nothing else. The trained objective prices `0.5·r1 + 0.3·r2 + 0.2·r3`. The two rank the arms in **different orders**:

| Rank | by calibrated scalar (trained objective) | by pooled EE (declared endpoint) |
|---|---|---|
| 1 | `TRAINED` +0.9063 | **`MAX_NOMINAL_GAIN`** 1.1155e8 |
| 2 | `GREEDY_R1R2` +0.8743 | `TRAINED` 9.3138e7 |
| 3 | `GREEDY_SCALARIZED` +0.8649 | `GREEDY_R1R2` 7.5817e7 |
| 4 | **`MAX_NOMINAL_GAIN`** −0.0867 | `GREEDY_SCALARIZED` 7.5272e7 |
| 5 | `RANDOM_MASKED` −1.4104 | `RANDOM_MASKED` 5.3060e7 |

`MAX_NOMINAL_GAIN` moves from **last to first**. The mechanism is visible in the table: its handover rate is 0.7117 against the learner's 0.2796, and `r2` carries weight 0.3 in the trained objective and weight **zero** in pooled EE. So the flip is a **weighting disagreement between a three-term objective and a one-term endpoint**, not a mean-of-ratios artefact — (a) is far too small to produce it.

Two further observations that belong beside the numbers, per G-8:

- **No arm buys EE by dropping service.** Served rates are 0.9981 (`MAX_NOMINAL_GAIN`), 0.9988 (trained), 0.9960–0.9961 (greedy arms), 0.9360 (random). The EE ranking is not a service-for-efficiency trade.
- **`MAX_NOMINAL_GAIN` wins on both halves of the ratio simultaneously**: it produces the most bits (3.267e+14, 1.146× the learner's) *and* consumes the fewest joules (2.929e+06, 0.957× the learner's). Its advantage is not a denominator effect.
- **The two `GREEDY_*` arms, which won on the trained objective, are the *worst* non-random arms on pooled EE** (0.808× and 0.814× the learner). Optimising the declared three-term objective myopically costs pooled EE relative to the learner, in the same direction and for the same reason.

### Reading, as pre-declared

The measured branch is the second one, and I apply it exactly as written and no further:

> **`MAX_NOMINAL_GAIN`'s pooled EE > the learner's → the trained objective and the declared primary objective disagree. That is a finding about the objective, not a reopening of the demonstration line.**

The demonstration-line closure of the previous section is unaffected: on the objective the learner is trained on, no expressible arm reaches it (best +0.8750 ± 0.0236 vs +0.8859 ± 0.0190, point estimate below). What this section adds is that **the objective the learner is trained on is not the objective the project declares as primary**, and on the declared one a one-line rule beats the authenticated checkpoint by 19.8%. I am not widening the search, not adding arms, and not sweeping anything. The design decision is the coordinator's.

### Evidence classification for this section

**Verified by running code, this session, read-only, no gradient step:** the five-arm pooled-EE panel (24 episodes each, frozen seeds 42/1337/7); the local SHA-256 of `final-checkpoint.pt` matching `e6b063ef…1b09c28b`; the per-episode spreads; the zero-hit grep for a demand cap / rate setpoint.

**Verified by reading local source:** `runtime/energy_efficiency.py:37-49, 114-144`; `runtime/trainer_env.py:239-248`; `env/step.py:964-970, 1005-1030`; `env/link_budget.py:590-615`; `env/constants.py:76`; `env/step_types.py:168-172` (the additivity contract that makes `Σ_u r1_u` the system EE, which is why the denominator here is the same `P^N` the reward uses).

**Derived:** the ratios, the 13.2-sem figure (unpaired, from the two per-episode sems), and the two ranking tables.

**Limit, stated rather than papered over:** I compared mean-of-ratios against ratio-of-sums only at the **episode** level, where they agree to ≤0.06%. I did not instrument both at the per-user-per-step level in the same pass, so the size of the estimand defect at that level is **not established here**, and the earlier sections' `r1_mean` figures should continue to be read as what they are — a mean over steps of a per-step system EE, not the declared pooled estimand.

**Not established:** anything about arms I did not run, or about this checkpoint under any evaluation harness other than the 24 episodes at stream positions 0–23 used here.
