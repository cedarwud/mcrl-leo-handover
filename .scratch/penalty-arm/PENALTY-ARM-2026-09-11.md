**At the 500-episode pilot checkpoint (one training seed, greedy, 24 evaluation episodes, ratio of sums) pooled EE is OFF 88,894,962.36 bit/J, PENALTY 85,996,841.88 bit/J, NULL_PENALTY 85,767,802.06 bit/J. PENALTY does not separate from NULL_PENALTY (+0.27%, 0.13 evaluation-sem), and neither beats OFF. Every between-arm gap is smaller than the swing the same arms show across their own 100–400-episode checkpoints, and the sibling's own record for this mechanism turns out to contain no performance measurement at all.**

Date 2026-09-11. Agent PENALTYARM. **500 episodes is not convergence**: the frozen reference run is 9,000 episodes, and at episode 500 the training ε is still 0.753. No number here is compared with a 9,000-episode checkpoint, and none may be.

Evidence tags: **[V]** means I verified it this session, by running code or by reading the named file:line myself (the sibling-repo reads were done by a read-only subagent I dispatched, which cited file:line for each). **[I]** means I inferred it.

**Accounting caveat (coordinator, 2026-09-11):** these pooled-EE figures use this simulator's per-beam power accounting, which takes a `max` over served users. That is non-standard; the literature sums them. All three arms use the same physics, so the comparison between arms is clean, but the absolute figures inherit whatever the parallel re-scoring under standard accounting finds.

**Tree measured on:** commit `5219995a`, "B0 D-1: every head bootstraps at one shared scalarised argmax", plus this port and nothing else. **[V]** I compared the server snapshot file by file against local git; no `src/` changes exist between `5219995a` and HEAD `fe433c16`.
- B0CORRECT **D-1 (per-head bootstrap): landed, included.**
- B0CORRECT **D-2 (outage free ride): not landed, not included.**
- B0CORRECT **D-3 (uncalibrated logged scalar): not landed, not included.** It affects only a logged scalar. My driver logs the three calibrated means directly and never reads the defective scalar, so D-3 cannot affect any number here.
- **So all three arms must be re-measured against the corrected baseline once D-2 lands.** This report is on a partially corrected tree. (`.scratch/b0-corrected/PROGRESS.md` still lists every step as PENDING, D-1 included. That ledger is stale; git is authoritative.)

---

## 1. What the sibling's own evidence for this mechanism actually is

The brief called this "the one mechanism in the sibling project with a measured positive effect." **That does not survive a reading of the sibling's own records.** [V, all file:line in `/home/u24/papers/modqn-paper-reproduction`]

- **It was never run as an experiment.** The penalties were built, unit-tested and smoke-tested over 3 episodes, and the 12-run Tier-1b wave was then **held and never dispatched**. `NEXT-SESSION-HANDOFF-2026-07-12-EVENING.md:113` has a section titled "BUILT, TESTED, NOT DISPATCHED (do not rebuild)", and `:21` says "Tier-1b (12 runs) | HELD", because the hypothesis it was built to discriminate had been refuted in the meantime (`SERVER-DISPATCH-PROMPT-INVERSION-2026-07-12.md:3-21`: "THE INVERSION HYPOTHESIS IS REFUTED"). There is no `penalty_log.json` anywhere in the repo, and no `run_metadata.json` carries a penalty stamp. The build commit `aef6fa68` says "No training run was launched."
- **It makes no performance claim of any kind.** Verbatim in `penalties.py:53`, `trainer_penalty.py:44`, and at the end of all six `configs/shared_q_isolation/tier1b/*.yaml`: *"READINESS-ONLY. No effectiveness claim."* The sidecar hardcodes `"readiness_only": True` (`trainer_penalty.py:429`).
- **Every existing number is a diagnostic of the penalty itself.** The fullest record, `archive/project-state/CURRENT-STATE-CHRONICLE-through-2026-07-22.md:1729-1746`, gives four fields as follows:
  - reference point: the arm's own first decile, with no control arm;
  - information level: 3-episode smoke, about 29 updates, seed count unrecorded;
  - estimator: relative change from first-decile mean to last-decile mean;
  - numerator: the penalty value itself.

  On that basis `TB-DECORR-escape` "fell" 0.975→0.677. The low and high decorrelation arms stayed trapped and rose. The chronicle and the YAML disagree on the high arm (0.994 vs 0.998), and because no artefact was ever committed that disagreement cannot be resolved.
- **The only srank "engagement" number was self-corrected to null.** Against a first-decile baseline, `TB-SRANK-nudge` read "PENALTY-FELL −61.2%". Against the true initial value the same arm was **+20.9%**; the apparent fall was the unpenalised transient decaying off its own peak. The sibling now hardcodes `informative=None` and `in_run_verdict_is_authoritative=False` for every srank arm (`trainer_penalty.py:408-421`).
- **Beware a false match.** The one sibling sentence that pairs a penalty with EE ("the penalty changed training; coverage and EE improved together", `CLOSURE-M4-RESULT-2026-07-18.md:106`) is about the sibling's **capacity-side penalty (L_cap)**. That is a different mechanism, and the sibling's own runner forbids stacking it with these two (`runner_concat.py:368-370`).

**So what was ported is an untested mechanism.** The sibling's record supports only this: *two penalties were implemented, their zero-coefficient bit-identity control passes, and a 3-episode smoke showed the decorrelation penalty trapped at its own stationary point unless its coefficient is about 5× the TD loss.* Nothing stronger has a record behind it.

## 2. The port

**Files.** [V] Local tree, uncommitted:
- `src/mcrl/runtime/collapse_penalty.py` (new): the two sibling penalties, the read-only srank diagnostic, the six presets and the null control.
- `src/mcrl/algorithms/modqn.py`: an optional `penalty_config` argument to the constructor, the penalty block in `update()`, and helper methods.

The edit sits after `loss = self._loss_fn(...)` and does not touch the lines B0CORRECT is editing. **Off by default:** `PenaltyConfig(kind="none")`.

**Tests.** [V] `.scratch/penalty-arm/test_penalty_offpath.py`, 8/8 passing:
- OFF is bit-identical to the no-config trainer, both in weights and in losses.
- The read-only diagnostics do not perturb OFF.
- PENALTY fires on every update and changes the weights.
- NULL injects exactly the declared norm.
- NULL does not shift the torch initialisation stream.
- Eq. (6) matches a hand SVD.
- All six presets construct.

The G-6 forbidden-vocabulary test was already failing on HEAD because of the `ee_axis_*` modules. The two files I touched add no offender.

**Taken from the sibling, not from my judgement.** [V] The `collapse_penalty.py` docstring carries the sibling file:line for each item.
- Coefficient: `TB-SRANK-kumar` α = 1e-3. This equals the sibling's code default `KUMAR_ALPHA_DEFAULT` and arXiv:2010.14498 p.9 verbatim.
- Φ: penultimate activations over the 128-sample TD minibatch, shape (128, 50), raw, not mean-centred.
- The term is added after the TD reduction.
- It is applied per head, three times per update, each inside that head's own backward. This is the sibling's own answer to the same three-head shape (`trainer_penalty.py:192-195, 279-303`); I reproduced it rather than choosing it.
- No schedule: the coefficient is constant from update 0.
- A non-finite penalty is skipped entirely, not zeroed.
- The logged TD loss stays TD-only.

**Unspecified in the sibling. My choices, declared before any result** (`DECLARATION-2026-09-11.md`):
- **Which preset runs.** There are six presets and one authorised arm. I ran `TB-SRANK-kumar`; the other five are ported and named but not run. No sweeping.
- **`decorr` cannot be ported faithfully.** Its rows are "the U=100 users of ONE env step", taken from a step snapshot this trainer does not keep. The branch here would compute a different quantity. Not run.
- **NULL_PENALTY design.** After the TD backward, each head's `.grad` gets an isotropic Gaussian vector added, rescaled to a fixed L2 norm. That norm equals **PENALTY's own measured mean penalty-gradient norm per head**: 0.266806, 0.357390 and 0.070064 (mean over 5,000 updates) [V]. The noise comes from a separate seeded generator, so initialisation is identical to OFF [V, test]. The magnitude is matched to the *measured term*, not to the coefficient. **Limitation:** this matches a norm, not a distribution of directions. In a parameter space of about 20k, an isotropic vector is nearly orthogonal to any fixed direction, and the penalty's gradient is not isotropic. The control therefore bounds the reading "any perturbation of this size would do it"; it does not reproduce the penalty's geometry.

**Workspace deviation.** The brief named `/home/sat/mcrl-v025-penalty-ws`, but that directory already existed with an unrelated completed study (`INTENT-TAIL-PENALTY-2026-09-10.md`). I ran in a fresh `/home/sat/mcrl-v025-penalty-arm-ws` (`git init`, snapshot commit `5d4116e`) so the other study was not destroyed.

**Run setup.** [V] 500 episodes per arm, checkpoints every 100, seeds (train 42, env 1337, mobility 7), learning rate 1e-3, `nice -n 16`, one BLAS thread, at most 2 processes at a time, peak RSS 2.2 GB. Each arm took about 790–800 s. Checkpoint SHA-256 at episode 500: OFF `829c15c8…`, PENALTY `c7349f50…`, NULL `c7543e39…`.

## 3. Results

### 3a. Endpoint: greedy evaluation of the 500-episode checkpoints

**Four fields for every number in this table:**
- **reference point:** OFF, which is the same tree, seeds and episode count, differing only in the penalty flag;
- **information level:** a 500-episode pilot, one training seed per arm, not converged;
- **estimator:** pooled EE as a ratio of sums, i.e. pooled decoded bits over pooled system joules, divided once. The sem is over the 24 per-episode ratios and does not include training-seed variance;
- **numerator:** full-buffer Shannon bits from the environment's own `energy.system_throughput_bps × dt`, with dt = 30.08 s.

The harness is reused from `.scratch/catfish-surface/CATFISH-ATTACHMENT-SURFACE-2026-09-11.md`, i.e. the shape of `anchor_ablation.py`. Each cell builds a **fresh environment**, which removes the `_age_rng` confound. Evaluation uses ε = 0, and `PenaltyConfig()` is inert: `update()` is never called, so no penalty and no perturbation is active. [V]

| arm | pooled bits | pooled joules | **pooled EE (bit/J)** | eval-sem | vs OFF | served | handovers per user-step (intra-sat / inter-sat) | mean active beams |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| untrained initial weights (floor) | 6.167067e+13 | 1.535717e+06 | 40,157,563.28 | 948,383.2 | 0.452× | 0.9043 | 0.3537 (0.0565 / 0.2972) | 40.66 |
| **OFF** | 2.389629e+14 | 2.688149e+06 | **88,894,962.36** | 1,222,940.3 | 1.000× | 0.9966 | 0.1774 (0.0002 / 0.1772) | 58.42 |
| **PENALTY** (`TB-SRANK-kumar`) | 2.450450e+14 | 2.849465e+06 | **85,996,841.88** | 1,487,797.1 | 0.9674× | 0.9988 | 0.1752 (0.0029 / 0.1724) | 62.39 |
| **NULL_PENALTY** | 2.446170e+14 | 2.852084e+06 | **85,767,802.06** | 1,010,882.8 | 0.9648× | 0.9991 | 0.1777 (0.0026 / 0.1751) | 62.17 |

[V] OFF was evaluated in two separate invocations and reproduced **bit-identically** (88,894,962.36 both times), so the harness is deterministic.

The gaps between arms, measured in independent-arm evaluation sems ([V] arithmetic; the resolvability reading is [I]):
- **PENALTY − OFF:** −2,898,120 bit/J (−3.26%), 1.50 sem.
- **NULL − OFF:** −3,127,160 bit/J (−3.52%), 1.97 sem.
- **PENALTY − NULL:** +229,040 bit/J (+0.27%), **0.13 sem**.

**None is resolvable, and the evaluation sem is a lower bound on the uncertainty**: it contains no training-seed variance, and §3b shows that variance dominates.

Both perturbed arms lit about 4 more beams than OFF (62.4 and 62.2 vs 58.4) and drew about 6% more joules for about 2.4% more bits. That accounts for the endpoint EE deficit mechanically [V, arithmetic]. §3b shows this beam difference is not stable across checkpoints [V].

### 3b. The same harness on the 100–400-episode checkpoints (descriptive, not a gate)

Four fields: same as §3a, except the reference point is OFF's checkpoint at the same episode count. I added this readout after seeing the endpoint and before writing any interpretation. It evaluates checkpoints the runs had already written. It adds no arm, no seed and no coefficient, and I use it only to size the noise.

| checkpoint | OFF | PENALTY | NULL_PENALTY | PENALTY / OFF | NULL / OFF |
|---|---:|---:|---:|---:|---:|
| ep 100 | 72,304,056.48 | 75,262,219.26 | 84,019,564.87 | 1.0409 | 1.1620 |
| ep 200 | 77,490,973.22 | 76,694,061.16 | 72,809,107.17 | 0.9897 | 0.9396 |
| ep 300 | 76,027,955.64 | 81,616,949.72 | 79,095,859.93 | 1.0735 | 1.0404 |
| ep 400 | 89,904,100.16 | 91,068,577.15 | 95,652,013.78 | 1.0130 | 1.0639 |
| **ep 500** | **88,894,962.36** | **85,996,841.88** | **85,767,802.06** | **0.9674** | **0.9648** |

[V] The ordering of the arms changes sign from checkpoint to checkpoint:
- PENALTY/OFF runs from 0.967 to 1.074.
- NULL/OFF runs from 0.940 to 1.162.
- PENALTY is above OFF at 3 of 5 checkpoints, and so is NULL.

The endpoint gaps of −3.3% and −3.5% fall well inside this swing. [I] The most economical reading: any perturbation, structured or random, sends a single-seed trajectory somewhere different, and at n = 1 seed per arm this pilot cannot tell the mechanism apart from that divergence. The five checkpoints within one arm are serially correlated, so I do not average them into a pooled effect.

### 3c. Training-time readouts

**Four fields for this table:**
- **reference point:** OFF, same episodes;
- **information level:** the training behaviour policy, with ε falling from 1.0 to 0.753 over these 500 episodes, so it is still more than 75% random. These are **not** policy-quality readouts;
- **estimator:** per-episode means averaged over the stated episode window;
- **numerator:** the per-user calibrated reward, i.e. `apply_reward_calibration` applied to the environment reward.

[V]

| arm | calibrated (r1, r2, r3), mean over ep 0–499 | same, ep 400–499 | handovers per episode, ep 400–499 |
|---|---|---|---:|
| OFF | (+2.9244, −7.3841, −2.3021) | (+3.1603, −7.0358, −2.3556) | 812.9 |
| PENALTY | (+2.9101, −7.3282, −2.2962) | (+3.1182, −6.9362, −2.3438) | 796.8 |
| NULL_PENALTY | (+2.8942, −7.4467, −2.2971) | (+3.0903, −7.0566, −2.3558) | 820.2 |

**The penalty's own magnitude, and the effective rank.** [V] Per head, ep 1–100 mean → ep 401–500 mean. srank_δ is Kumar's diagnostic: δ = 0.01, mean-centred Φ, 50 features, read-only. It is a **different object from the penalty** and is never reported as one.

| head | PENALTY raw Eq. (6) value | PENALTY term ÷ TD loss (mean) | penalty gradient norm (mean) | srank_δ OFF | srank_δ PENALTY | srank_δ NULL |
|---|---|---:|---:|---|---|---|
| 0 (r1) | 26.55 → 18.99 | 0.121 | 0.2668 | 41.38 → 40.77 | 38.02 → **38.59** | 41.69 → 43.66 |
| 1 (r2) | 50.53 → 14.54 | 0.280 | 0.3574 | 39.20 → 40.35 | 39.14 → **39.38** | 38.14 → 39.49 |
| 2 (r3) | 3.02 → 2.67 | 0.072 | 0.0701 | 40.15 → 41.54 | 42.40 → **39.74** | 40.54 → 42.99 |

Three facts from this table decide how the result can be read.

1. **The penalty engaged.** [V] Its value fell on all three heads; head 1 fell to 29% of its early level. So the sibling's "it never escaped its own flat region" reading of a null does not apply here. For scale: the term was 0.07–0.28× the TD loss on this substrate, whereas the sibling measured 9.9× at the same α on its own substrate. That figure is substrate-specific and was measured, not assumed.
2. **Minimising the surrogate did not raise the diagnostic rank.** [V] At ep 401–500 PENALTY's srank_δ is **below** OFF on all three heads, by 2.18, 0.97 and 1.80. The matched random perturbation **raised** it on two of three heads. [I] Eq. (6) can be reduced by shrinking σ_max, i.e. the overall feature scale, as well as by spreading the spectrum, and here it did not buy rank.
3. **The pathology the penalty targets is absent in OFF at 500 episodes.** [V] OFF's srank_δ holds steady at about 40–41 of 50. The sibling's motivating pathology was a collapse from 60 to 3–46 during training, and it was measured on the sibling's own network. [I] At this horizon there was no collapse to repair, and that alone makes a null the expected outcome.

## 4. Reading, against the declaration fixed before the numbers

The declared branches (`DECLARATION-2026-09-11.md` §4) were:
- **PENALTY > OFF and NULL ≈ OFF → structure:** not observed.
- **PENALTY ≈ NULL > OFF → perturbation:** not observed. PENALTY ≈ NULL holds, but neither is above OFF at the endpoint.
- **Neither beats OFF → the mechanism does not transfer here; report and stop, no coefficient sweep:** **this is the branch the endpoint falls in.**

I qualify it as follows [I]:
- The endpoint does not show the mechanism *hurting* either. No gap is resolvable, and §3b shows the arm ordering flipping between checkpoints.
- The accurate statement: *at 500 episodes and one training seed, the ported Kumar penalty is indistinguishable both from no penalty and from a matched structureless perturbation. The collapse it is meant to repair does not occur in OFF at this horizon, and the penalty lowered rather than raised the effective rank.*
- PENALTY does not separate from NULL_PENALTY on any readout. That includes the representation diagnostic, where NULL moved rank the "right" way more than PENALTY did.

**Per the declaration, I am stopping here.** I did not sweep the coefficient, add an arm or re-run the seed set. Nothing about the result was surprising enough to trigger the "re-run at larger n" clause: a null from an untested mechanism, applied where its target pathology is absent, is the expected outcome.

**If the owner wants this question to have a resolvable answer, this is what it would take.** It is a scoping statement, not a recommendation to proceed.
- Several training seeds per arm: §3b's swing suggests at least 5.
- A horizon at which OFF actually shows rank collapse. That precondition has to be checked first, on OFF alone, for example on the frozen 9,000-episode run's collapse indicators.
- D-2 landed first.
- At the observed ~2 s per episode, 3 arms × 5 seeds × 9,000 episodes is roughly 75 CPU-hours. That is **heavy**, so it belongs on the server.

## 5. Verified vs inferred

- **Verified by running code this session:**
  - the 8 acceptance tests;
  - three 500-episode pilots;
  - PENALTY's measured gradient norms, and NULL configured from them;
  - greedy evaluation of 16 cells (endpoint, trajectory and floor);
  - OFF's bit-identical reproduction;
  - the file-by-file comparison of the snapshot against git `5219995a`.
- **Verified by reading:**
  - the sibling's penalty code, presets, attachment site and records (via a read-only subagent citing file:line; I spot-checked `penalties.py` myself);
  - B0CORRECT's ledger and git log;
  - the catfish-surface harness and its `_age_rng` confound.
- **Inferred:**
  - that the endpoint gaps are trajectory noise rather than an effect;
  - that Eq. (6) was reduced by scale rather than by spectral spread;
  - that the absence of collapse makes a null the expected outcome;
  - the compute estimate in §4.
- **Not established:**
  - any effect at convergence;
  - any effect at n > 1 training seed;
  - anything under standard (summed) per-beam power accounting;
  - anything on the fully corrected tree (D-2 and D-3 absent);
  - the five unrun presets;
  - the `decorr` penalty, which cannot be ported faithfully to this trainer.

## 6. Files

- Report: `/home/u24/papers/mcrl-leo-handover/.scratch/penalty-arm/PENALTY-ARM-2026-09-11.md`
- Declaration: `/home/u24/papers/mcrl-leo-handover/.scratch/penalty-arm/DECLARATION-2026-09-11.md`
- Progress: `/home/u24/papers/mcrl-leo-handover/.scratch/penalty-arm/PROGRESS.md`
- Port: `/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/collapse_penalty.py` (new) and `/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/modqn.py`. **Uncommitted.** B0CORRECT is editing the same file, so whoever commits next should check it takes only its own hunks.
- Driver, evaluation and tests: `.scratch/penalty-arm/{run_penalty_pilot.py, eval_pooled_ee.py, test_penalty_offpath.py}`
- Results, local copy (JSON and logs): `.scratch/penalty-arm/results/`
- Checkpoints, server only: `sat:/home/sat/mcrl-v025-penalty-arm-ws/runs/{OFF,PENALTY,NULL_PENALTY}/`
