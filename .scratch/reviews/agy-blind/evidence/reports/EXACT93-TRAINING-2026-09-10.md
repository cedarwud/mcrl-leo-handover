**The exact-label corpus is 93 anchors. Its deterministic 2,000-row-per-route samples match the sealed surrogate fallback on C1 0/2,000 (0.0000%), C2 453/2,000 (22.6500%) and C3 0/2,000 (0.0000%). All 453 C2 matches sit at the structural floor −3.0 (zero forecast surplus, all three offsets lost), and outside that floor the C2 match rate is 0/1,545 (0.0000%). Exact-versus-surrogate argmax disagreement is C1 5,390/9,300 (57.9570%), C2 4,598/9,300 (49.4409%) and C3 76/93 (81.7204%). Runner v2 reproduced the v1 checkpoint bit-for-bit (both SHA-256 `e385cb4879ab321e37d2fd66888d5869767a01b3d0a11470aff3c820b3d70dd7`). On the complete seed-1 cadence-100 sequence, the first admissible update is C1 800, C2 2,200 and C3 2,200. Seeds 2–16 of the 16-seed run are still training.**

# EXACT93: 93-anchor exact-label corpus and five-arm training (2026-09-10)

`BUILD_NOT_CLAIM`. No EE quantity was computed. Loss values appear only as a
convergence diagnostic and are not evidence about EE. No sealed artefact was
modified, and nothing was written outside `/home/sat/mcrl-v025-exact93-ws`.

**Status.** The corpus, all gates, the C2 match audit, the v1/v2 equivalence
check and the seed-1 stopping rule are final. The 16-seed run is not finished.

- **Run state as of 2026-09-10 ~23:51Z.** Seed 1 had finished all 4,000
  updates. Seed 2 was at update 300. The detached run (PID 3131678) was not
  touched.
- **Earlier version of this file.** It was written at 18:53Z, before training,
  as a placeholder. This version replaces it.

Each number states its **reference, information class, estimand and
numerator**. Each claim is tagged **[V]** (verified by running code), **[D]**
(derived on paper) or **[I]** (inferred).

## 1. Corpus assembly

The assembly script is `scripts/assemble_corpus.py` (SHA-256 `18452e7c…20c0`).
It uses the layout of the EXACTTRAIN 22-anchor corpus: one flat `views/world-N/`
layer that holds each anchor's source-view shard and C3 coalition shard, each
beside its `.sha256` sidecar. It generates nothing; every file is a byte copy.

**[V] Anchors.** 93 anchors, `global-000..092`.

- **Reference.** The datepool build manifest `BUILD_NOT_CLAIM-manifest.json`
  (SHA-256 `f13f99d0…7605`), which lists 93 contiguous `anchor_records`.
- **Coverage.** The admitted development prefix: world 1 steps 0–29 × 3 carriers,
  plus world 2 step 0 × 3 carriers.
- **Excluded.** The three quarantined post-deadline anchors are not in the
  manifest and were not read. No evaluation-only claim date was read.

**[V] Rows.**

- 90,938 source rows, schema `mcrl-v025-stagec-source-row-v1`.
- 19,116 C3 rows, schema `mcrl-v025-stagec-c3-coalition-shard-v2`, split `TRAIN`.

**[V] Byte identity.**

- 93/93 source views match the datepool manifest `view_sha256` and their sidecars.
- 93/93 coalition shards match COALEXT's sealed manifest and their sidecars.
- 93/93 of COALEXT's mirrored source views are byte-identical to datepool's.

**[V] Corpus digest.** The production reader computes
`db2b4007323530e7f239491858fe7bf41a54f62b468470051a82e4a3a178c94b`. The earlier
22-anchor corpus was `3dd10c17…08e9`.

The assembly receipt is `.scratch/exact93/assembly-receipt.json`
(SHA-256 `0080403d…7c2a`). Peak RSS was 20,467,712 B.

## 2. Verification gates (all passed before training)

### 2a. Label provenance and 2b. argmax disagreement [V]

The EXACTTRAIN verifier `verify_corpus.py` (SHA-256 `f9b7250b…e378d86`) ran on
the assembled corpus through `scripts/verify_corpus_adapter.py`
(SHA-256 `13e8bbc7…ede6`). The adapter makes four path and inventory
adaptations, and each one asserts it matches exactly one patch point:

- a world-aware sealed-coalition lookup, the same one COALEXT used;
- source inventory skips the coalition shards stored alongside;
- the coalition index is read from the file name;
- the process cap counts only processes owned by this workspace.

The sample, the tolerances, the grouping, the tie-break and the fail-closed
gate are unchanged. The output is `.scratch/exact93/corpus-verification.json`
(SHA-256 `2df003ac…7aab`).

**Surrogate-match gate.**

- **Reference.** The sealed provider-primitive fallback labels.
- **Information class.** A 2,000-row deterministic sample per route
  (`EXACTTRAIN/20260910/{C1,C2,C3}`).
- **Frames.** C1 and C2: 81,638 non-reference rows. C3: all 19,116 multi-user rows.
- **Estimand.** The fraction of sampled labels whose exact value is bit-equal
  to the surrogate.

| Route | Exact identity passes | Bit-equal to surrogate | Fraction |
|---|---:|---:|---:|
| C1 | 2,000/2,000 | 0/2,000 | **0.0000%** |
| C2 | 2,000/2,000 | 453/2,000 | **22.6500%** (every match is at the structural floor; see §2e) |
| C3 | 2,000/2,000 | 0/2,000 | **0.0000%** |

All three fractions are far from one, so this is not the surrogate corpus.

Additional C3 checks:

- Across all 19,116 C3 rows, exact ψ equals the fallback residual on 0 rows.
- On the 93 rows that overlap the sealed pilot coalition, exact ψ equals the
  sealed pilot ψ on 0 rows.
- The maximum reconstruction residual is `2.842e-14`, against a contract of `1e-12`.

**Argmax disagreement.**

- **Reference.** The surrogate argmax within the same group.
- **Estimand.** The fraction of groups whose exact argmax differs.
- **Ties.** Broken toward the lowest action index. For C3, canonical row order
  breaks ties.

| Route | Groups | Disagreements | Fraction | 22-anchor reference |
|---|---:|---:|---:|---:|
| C1 | 9,300 (anchor × user) | 5,390 | **57.9570%** | 51.68% |
| C2 | 9,300 (anchor × user) | 4,598 | **49.4409%** | 55.27% |
| C3 | 93 (anchors) | 76 | **81.7204%** | 81.82% |

**[V]** These agree with independent computations: the datepool manifest's own
figures (C1 5,390/9,300 and C2 4,598/9,300) and COALEXT's C3 figure (76/93).
The 22-anchor column covers a different panel and is shown only for reference.

### 2c. Production-reader dry run: all five arms, one step [V]

**Runner dry run.** The runner-v2 copy ran unmodified with `--epochs 1 --seeds 16`.

- The reader passed: 90,938 source rows and 19,116 coalition rows.
- The fixture gate passed 4/4.
- All 16 seeds completed one epoch.
- Peak RSS was 2,310,737,920 B.

**Independent probe.** `scripts/five_arm_probe.py`; output
`.scratch/exact93/five-arm-probe.json` (SHA-256 `e9b6636b…36ff`).

- It ran one `train_epoch` on seed `V025_LEARNER/seed/1`.
- **All 15 arm × route Adam cursors went from 0 to 1, and every parameter
  fingerprint changed**, across `FULL`, `DROP_C1`, `DROP_C2`, `DROP_C3` and
  `ALL_NEUTRAL_CONTROL`.
- It produced exactly 2 distinct C1 fingerprints (informed vs neutral), as
  `SOURCE_MAP` requires.

### 2d. C3 width fail-closed

- **[D]** Q1 = 16, so the member width is 2·16 + 6 = 38. The C3 input width is
  1 + 2·38 + 4·7 + (32·4 + 1) + 6 = **240**.
- **[V]** The verifier fails closed unless the width is 240. The probe measured
  the persisted FULL C3 head's first-layer input width at **240**.

### 2e. Why C2 matches the surrogate on 453/2,000 rows [V]

Scripts: `scripts/c2_match_breakdown.py` (SHA-256 `6f9d3a2e…39e1`) and
`scripts/c2_floor_check.py` (SHA-256 `72533db2…6ee8`). Outputs:
`.scratch/exact93/c2-surrogate-match-breakdown.json` (SHA-256 `2a940c5f…af1a`)
and `.scratch/exact93/c2-floor-check.json` (SHA-256 `b466fc5d…e772`).

Both scripts replay EXACTTRAIN's C2 sample exactly: the same frame order, the
same RNG domain, and an assertion that the frame has 81,638 rows and 453
matches. Peak RSS was 132,050,944 B or less.

**Mechanism.**

- In every row, the exact persistence penalty equals `lost_offsets × κ`
  exactly: penalty/κ ∈ {0, 1, 2, 3} for 0 to 3 lost offsets.
- The normalized C2 label is therefore `surplus/κ − lost_offsets`.
- When the forecast surplus is exactly 0 and all three forecast offsets are
  lost, the label equals **−3.0 exactly**, whichever computation path
  produced it. This is the label's structural floor. The surrogate's formula
  lands on the same floor.

**Breakdown of the 453 sampled matches:**

| Category | Count |
|---|---:|
| Exact label value `-0x1.8p+1` (−3.0) | **453/453** |
| Forecast surplus exactly 0 (rational), `lost_offsets = 3` | 453/453 |
| Exact label equal to 0 | 0/453 |
| Candidate physically identical to BASE | 0/453 |
| Null action / real action | 52 / 401 |
| Outage flag set / not set | 70 / 383 |
| Bit-equal in unnormalised `c2_label_bits` too | 453/453 |
| Exact identity `label = surplus − penalty`, zero residual | 453/453 |
| Training label minus exact rational extension, max residual | 0.0 |

**Full frame (81,638 rows).**

- There are 18,577 matches, and **all of them are at −3.0**.
- **Matches off the floor: 0 of 63,042 rows.**
- Every one of the 18,577 matching rows passes the exact identity.

**Evidence that the exact labels did not come from the surrogate.** Where the
exact label and the surrogate sit on the floor, they overlap but do not coincide:

- 19 rows have an exact label of −3 but a surrogate label that is not −3.
- 6,915 rows have a surrogate label of −3 but an exact label that is not −3.
- 18,595 rows are in the exact floor state. One further row has
  surplus/κ = 1.17×10⁻¹⁶, a nonzero rational that rounds to −3.0 in binary64,
  which makes 18,596 rows with an exact label of −3.

**Verdict on whether any row carries a surrogate value where an exact one belongs.**

- **[V]** No row does. Every match is a row whose exact label legitimately
  equals −3.0: it comes from exact components (surplus 0, three offsets lost,
  penalty 3κ) that pass the rational identity.
- **Quantified:** 0 rows carry a surrogate value where an exact one belongs.
- **[I]** Scope of this check. It establishes that each label follows from its
  exact components. It does not independently re-run the physics that made
  the surplus zero. That comes from datepool's `evaluate_many` path, whose
  manifest records `c2_decomposition_identity_max_abs = 0`.

**Restricted match rate.** Rows at −3.0 are equal by construction, so they are
excluded.

- **Sample:** 0/1,545 (**0.0000%**).
- **Full frame:** 0/63,042.

**[I] The 22-anchor result.** The 22-anchor build's 359/2,000 (17.95%) is
consistent with the same floor mechanism. It was not recomputed here.

**[I] Consequence for training.** About 23% of the C2 frame (18,596/81,638) has
a label pinned at the floor.

## 3. Runner v1/v2 equivalence [V]

- **Runner under test.** Runner v2 was copied without edits. Its SHA-256 is
  `47313ed0…0e1f` in both workspaces.
- **Reference.** The v1 runner `run_stagec_training.py` (SHA-256 `4885570b…7bc797d66`).
  Its KAT checkpoint is at `exacttrain-ws/artifacts/checkpoint-width-kat-20260910`.
- **Settings.** Constant rate; corpus `3dd10c17…08e9`; seed
  `V025_LEARNER/seed/1` = 6407676579069309528; 100 epochs; cadence 100.

| Run | Checkpoint `learner-6407676579069309528-epoch-000100.json` SHA-256 |
|---|---|
| v1 (reference) | `e385cb4879ab321e37d2fd66888d5869767a01b3d0a11470aff3c820b3d70dd7` |
| v2 (`artifacts/v1-equivalence-20260911`) | `e385cb4879ab321e37d2fd66888d5869767a01b3d0a11470aff3c820b3d70dd7` |

The two checkpoints are identical.

## 4. Training

**[V] Command.** `run_stagec_training_v2.py --epochs 4000 --checkpoint-cadence 100
--seeds 16 --step-decay-start-rate 1e-3`, run on this corpus with a fresh
output directory `artifacts/exact93-step-decay-16seed-4000-20260911`.

**[V] Launch receipt.** `launch_receipt_sha256` is `770327a4…bb47`. It records:

- schedule `step_decay`, starting at 0.001, factor 0.1, applied after `[2000, 3000]`;
- the five sealed arms;
- 16 seeds;
- `head_literals_sha256` `201f6243…ebf0`;
- fixture gate PASS.

**[V] Seed-1 learning-rate trace.** Across its 40 checkpoints: `1e-3` at
updates 100–2000 (20 checkpoints), `1e-4` at 2100–3000 (10), and `1e-5` at
3100–4000 (10).

**[V] Seed-1 wall time.** The receipt was written at 18:45:02Z and update 4,000
landed at 23:30:55Z. That is **about 17,153 s per seed, or about 4.29 s per
update (all five arms)**.

**[V] Seed 2.** It takes about 364 s per 100 updates. Peak RSS was
2,334,736,384 B.

**[D] Projection for the remaining 15 seeds.** About 60–72 h at the current
load, ending around 2026-09-13. This is an observed rate, not a diagnosis.

**[I] Why the run was not split across processes.** The runner trains seeds
one after another and has no seed-range flag. It could not use the
three-process cap without being modified.

## 5. Stopping rule, applied offline

The analysis script is `scripts/stopping_analysis.py` (SHA-256 `1650f9d7…2bb`).
Its output is `.scratch/exact93/stopping-analysis-seed1.json`
(SHA-256 `65e78ac8…971b`). Peak RSS was 2,309,935,104 B.

**Reused unchanged from LRSWEEP** `run_sweep.py` (SHA-256 `dde9a8e9…0fc6`):

- tolerances `0.01 / 0.01 / 0.005 / 0.005`;
- `metric()`;
- `pair_objective()`.

**Reused verbatim from DECAY:** `stability()` and the first-admissible logic.

**What the rule was applied to.**

- **Arm:** `FULL`, the only arm with every route informed.
- **Seed:** `V025_LEARNER/seed/1`, the single seed that LRSWEEP and DECAY
  defined the rule on.
- **Checkpoints:** all 40, loaded through the sealed loader.

**Declared deviation.** This was fixed before any result was read. The corpus
is split `TRAIN` throughout and the runner has no held-out panel. The
"held-out" R², ordering and top-1 are therefore computed **in-sample**:

- C1 and C2: 90,938 rows in 9,300 groups;
- C3: 19,116 rows in 93 groups.

LRSWEEP computed them with leave-one-anchor-out folds instead. In-sample
evaluation weakens the stability test; it does not strengthen it.

**[V] First admissible update, seed 1, FULL arm.**

- **Reference.** The checkpoint 100 updates earlier.
- **Information class.** In-sample levels on the 93-anchor exact corpus.
- **Estimand.** The first cadence at which all four motions are within tolerance.

| Route | First admissible | Admissible cadences (of 39) | Motion there: objective rel / R² / ordering / top-1 |
|---|---:|---:|---|
| C1 | **800** | 31 | 0.00861 / 0.00226 / 0.00349 / 0.00290 |
| C2 | **2,200** | 19 (every one from 2,200 to 4,000) | 0.00230 / 0.00111 / 0.00021 / 0.00011 |
| C3 | **2,200** | 19 (every one from 2,200 to 4,000) | 0.00307 / 0.00018 / 0.00011 / 0.00000 |

No route is non-convergent.

**[V] Qualifications.**

- **C1** fails again at 900 (ordering 0.00567, top-1 0.00742) and at 1,900.
  It is admissible at every cadence from 2,000 on.
- **C2** is still moving at 2,000 (R² 0.0886) and at 2,100 (objective 0.0248,
  R² 0.134).
- **C3** fails on the objective at 1,900, 2,000 and 2,100.

**[V] In-sample levels at update 4,000.** These are a diagnostic, not EE.

| Route | R² | Ordering | Top-1 |
|---|---:|---:|---:|
| C1 | −0.0345 | 0.532 | 0.066 |
| C2 | 0.198 | 0.720 | 0.383 |
| C3 | 0.943 | 0.598 | 0.484 |

**[I] How to read these results.**

- **The C2 and C3 value of 2,200 is set by the schedule.** It is the first
  cadence whose whole 100-update window falls after the decay at update 2,000.
  It shows that those heads were not stable at `1e-3` and became stable once
  the rate dropped. It says nothing about how well they fit.
- **The DECAY match is a coincidence.** DECAY's 2,200 for C3 came from a
  different 12-anchor LOAO panel. The schedule and the rule were not changed,
  and nothing was tuned toward that number.
- **C1 passes the motion rule while its in-sample R² is negative.** The rule
  measures motion, not fit.

## 6. Resources and constraints [V]

- **Interpreter and environment.** Every Python run used the server venv
  interpreter under `nice -n 15`, with all six BLAS thread variables set to 1
  and `PYTHONPATH` pointing at the sealed retrain Stage-C tree (`learner.py`
  `7bc714f5…ca3b`).
- **Processes.** At most 2 Python processes owned by this workspace ran at once.
- **Memory.** The largest peak RSS was 2,334,736,384 B, below the 5 GB cap.
- **Other workspaces.** They were only read, never written.
- **Bug fixed before any result was read.** Commit `400ffcb` registers modules
  loaded by path in `sys.modules`, because `@dataclass` needs it. The smoke-test
  outputs from before the fix were deleted.

## 7. Remaining work

- **Seeds 2–16.** They are still training and were not touched. To get
  cross-seed stopping statistics once they finish, re-run
  `scripts/stopping_analysis.py` for each seed.
- **Held-out stopping test.** Every metric here is in-sample. A true held-out
  test needs a declared held-out panel, and the runner contract does not have one.
