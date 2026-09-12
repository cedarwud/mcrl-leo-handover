# S1 MC2 manifest plan — the matrix, the schedule, and a draft of the reading rules

Lane E, 2026-09-12. Worktree `/home/u24/papers/mcrl-leo-handover-mc2-s1`, branch
`mc2/s1-port-20260912`. **Nothing here is launched and nothing here is frozen**: the matrix is
parameterised by the mechanism id the controller freezes, the optional cells are the controller's
decision, and §4's reading rules are a *draft for the controller to freeze* — the manifest writer
refuses to produce a formal declaration without the digest of a frozen rules document
(`s1_manifest.py --reading-rules FILE`, `s1_launch.py --reading-rules FILE`).

Authority: the MC2 contract r2 (`.scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md`),
Amendment 13 (the frozen S1 configuration), Amendment 12 (the optional second null), and lane B's
co-sign (`.scratch/mc2/B/CONTRACT-COSIGN.md`, R1-1 … R1-4, F-1 … F-3).

---

## 1. The matrix is a function of the frozen mechanism id

The two declared versions differ in **what "FULL with B removed" is**, so the matrix cannot be a
fixed list:

| frozen `mechanism_id` | drop-one of B | cells | runs (3 seeds) |
|---|---|---|---|
| `MC2-JGO-v1` | **`D3-T0`** — v1's A-only *is* the frozen single-Catfish arm, bit-identical by construction (contract §1, §5 test 2) | 7 | **21** |
| `MC2-ARB-v2` | **`A-only-v2`** — the judge-gated `{x_u, a^A}` cell; `D3-T0` stays as the baseline only | 8 | **24** |

`s1_common.cells(mechanism_id)` encodes exactly this and nothing else. Adding either optional null
adds 3 runs each.

### The table (`CELL:k`, k = 0, 1, 2 for every cell)

| # | cell | kind | mechanism / rule id | sources | S1 streams | eval | role | serves |
|---|---|---|---|---|---|---|---|---|
| 1 | `D0` | cf | `D0` | — | S1-TRAIN | formal ×24 @1000 | control, catfish off | `FULL_vs_D0`, `D3T0_vs_D0` |
| 2 | `D3-T0` | cf | `D3-T0` | — | S1-TRAIN | ″ | frozen single-Catfish arm; baseline for R1-1; **under v1 also the A-only drop-one** | `FULL_vs_D3T0`, `FULL_vs_A_only[v1]`, `D3T0_vs_D0` |
| 2a | `A-only-v2` *(v2 only)* | judge | `MC2` / `MC2-ARB-v2` | `A` | S1-TRAIN | ″ | v2's drop-one of B | `FULL_vs_A_only[v2]` |
| 3 | `B-only` | judge | `MC2` / **`MC2-B-ONLY-SHARED-v1`** | `B` | S1-TRAIN | ″ | drop-one of A; incumbent is the learner's own executed action | `FULL_vs_B_only` |
| 4 | `FULL` | judge | `MC2` / frozen id | `A+B` | S1-TRAIN | ″ | **the method under test** | every FULL comparison |
| 5 | `B-null` | judge | `MC2` / frozen id | `A+R` | S1-TRAIN + **S1-NULL-MC2 `(9_263_000, k)`** | ″ | matched null of B, anchor kept | `FULL_vs_B_null` |
| 6 | `D2-T0-tau0p3` | cf | `D2-T0`, τ = 0.3 | — | S1-TRAIN | ″ | strongest soft comparator, no superiority claim | `FULL_vs_D2T0` |
| 7 | `MODQN-eq16` | modqn | eq-(16) @1000 | — | S1-TRAIN | ″ | **same-budget win gate** | `FULL_vs_MODQN_eq16`, `D3T0_vs_MODQN_eq16` |
| — | `BASELINE_MODQN_eq16_frozen_9000ep` | rollout | `e6b063ef…1b09c28b`, `training: none` | — | none (formal eval only) | formal ×24, once | published reference, **not a veto** | `FULL_vs_REF9000` |
| O1 | `D3-null` *(OPTIONAL)* | cf | `D3-null` | — | S1-TRAIN + S1-NULL `(9_261_000, k)` | ″ | Amendment 4's matched hard null **of the anchor** | `D3T0_vs_D3_null` |
| O2 | `D3-XEP` *(OPTIONAL)* | cf | `D3-XEP` | — | S1-TRAIN + the sealed DEV-NULL reference `9bb0c01e…` | ″ | Amendment 12's plausible-but-uninformative null **of the anchor**; decides wording (ρ_info), no gate | `D3T0_vs_D3_XEP` |

Every cell: 1000 episodes, ε-decay 222, batch 128, replay 50 000, η fixed at η₀ =
110 507 234.834 444 57, λ = 0, `equal_share`, D3 `m = 0.15` / `λ_E = 1.0`, TLE `427e6a91…8fe9`,
**one** evaluation read at episode 1000 on the 24 formal episodes `9_111_000+i / 9_112_000+i`,
greedy, fresh env per episode, one checkpoint.

### Dedup notes (what is deliberately *not* a second cell)

1. **A-only = `D3-T0` under v1.** Same mechanism, same code path, same payload — a second A-only
   identity would be the same configuration hash with a different name, and two names for one
   configuration is how a matrix starts lying. Under v2, A-only-v2 is a *different* mechanism
   (`{x_u, a^A}` gated), so there it is its own cell and `D3-T0` stays as the R1-1 baseline.
2. **`B-only` is rule-independent.** Lane A implements it under `MC2-B-ONLY-SHARED-v1`; its labels
   and target are identical under v1 and v2. So its S1 configuration hash does **not** depend on
   which version is frozen — the same physical cell serves either.
3. **`A-null` is not run.** The anchor's content is not in question (E1 + the optional D3-null /
   D3-XEP cells are the anchor's nulls).
4. **No second FULL.** Only the frozen version runs at S1; the losing version is not re-run on the
   formal set, ever.
5. **The rolled 9000-episode reference is one rollout, not a trained cell** — `training: none`.

### The optional cells, for the controller to decide at freeze (lane E does not decide)

| cell | what it buys | what it costs | what it does **not** buy |
|---|---|---|---|
| `D3-null` | Amendment 4's conjunctive gate on the **anchor**, on the formal set | 3 runs ≈ 0.65 h each ≈ 2 worker-hours; adds ~0 h to the makespan (fills wave gaps) | nothing about the second source |
| `D3-XEP` | ρ_info → the *wording* of the single-Catfish claim (Amendment 12 §3); the measured DEV leak (0.196 vs 0.039 random-legal) makes it a **lower bound**, i.e. harder to pass | 3 runs ≈ 2 worker-hours, same gap-filling | no pass/fail gate; it cannot rescue or sink FULL |

Both are **anchor** questions, not MC2 questions. Including them makes the S1 record self-contained
for the single-Catfish half of the headline (`D3T0_vs_D0`); excluding them keeps S1 strictly about
the second source and leaves those two readings at E1 depth. The cost is small enough that cost is
not the deciding argument.

---

## 2. Wall-time schedule on sat, at most 8 single-thread workers

### Inputs (all measured, none assumed except where stated)

| quantity | value | source |
|---|---|---|
| plain CF arm, training only | **1.9–2.3 s/episode** at 3–7 concurrent workers (E0a 216 s/100 ep at 3-way; lane M k8 222–230 s/100 ep at 5-way; D3-T0 634 s/300 ep at 7-way) | `.scratch/dev-training/E0-BATCH-1-2026-09-12.md`, `.scratch/catfish2-successor/results/LANE-M-K8-RESULT.json` |
| `evaluate_actions` on sat | **7.8 ms/call at 8 concurrent workers** (652 756 calls / 5 103 s); no measurable 4→8-way degradation | `…-cf2s-b0/.scratch/catfish2-successor/results/JOINT-J.json` |
| judge calls per decision step, **trained** (controller probe, realised) | FULL ≈ **95**; B-null ≈ **125**; B-only ≈ 65; A-only-v2 ≈ 30 | `…-mc2/.scratch/mc2/CONTROLLER-PROBE-READOUT-2026-09-12.md` + controller message |
| judge calls per decision step at **ε ≈ 1**, measured by this lane's own preflight (`judge_evaluations` per episode ÷ 9 judged steps, 100 users) | FULL **110** (995/ep); B-null **160** (1442/ep); B-only **87** (779/ep); A-only-v2 **71** (637/ep) | `.scratch/mc2/S1/S1-MC2-PORT.md` §5; call counts are machine-independent, so these replace the ≈ 200/step early-regime assumption (which was ~1.6× pessimistic: the judge evaluates `κ(a^A)` only on rows where the challenger differs, and reuses the base evaluation whenever `a^A = x_u`) |
| judged steps per episode | **9** (B and R abstain at t = T−1) | contract §1, §3 |
| 24-episode evaluation read | 35–40 s | `.scratch/catfish2-discovery/results/DEVVAL-REFERENCES.json` |
| MODQN eq-(16) | 1.55–1.59 s/episode alone (9000-ep runs) | `artifacts/training-2026-08-*/…/status.json` |
| RSS per worker | 1.9–2.3 GB; cap `MemoryMax=5G`, `--rss-cap-gb 4.5` | lane M k8, E0/E1 |

**Assumption, stated:** 8.5 ms per judge call (between sat's measured 7.8 and the controller's
8–9), 2.3 s/episode learner cost at 8-way, and the ε-decay span (episodes 1–222) costing the mean
of the early and trained call rates. Lane A's own smoke timings should replace this; if the judge
costs 10 ms/call the judge cells grow ~15 %.

### Per-run estimate (1000 episodes)

| cell | calls/step (ε ≈ 1 measured → trained) | s/episode | **wall per run** |
|---|---|---|---|
| `FULL` (v1 or v2) | 110 → 95 | 10.7 → 9.6 | **2.5–3.1 h** (point 2.7 h) |
| `B-null` | 160 → 125 | 14.5 → 11.9 | **3.1–3.9 h** (point 3.5 h) |
| `B-only` | 87 → 65 | 9.0 → 7.3 | **1.9–2.4 h** (point 2.1 h) |
| `A-only-v2` (v2 only) | 71 → 30 | 7.7 → 4.6 | **1.3–1.7 h** (point 1.5 h) |
| `D0`, `D3-T0`, `D2-T0`, (`D3-null`, `D3-XEP`) | — | 2.3 | **0.6–0.7 h** |
| `MODQN-eq16` | — | 1.6–2.0 | **0.5–0.6 h** |
| rolled reference | — | — | ~40 s, one rollout |

### Makespan with 8 workers (longest-first, which the launcher does)

| matrix | worker-hours | wave 1 | **makespan** |
|---|---|---|---|
| v1 mandatory (21 runs) | ≈ 33 | 3×`B-null` + 3×`FULL` + 2×`B-only` | **≈ 4.5 h** |
| v1 + both optional (27) | ≈ 37 | same | **≈ 5 h** |
| v2 mandatory (24) | ≈ 37 | same | **≈ 5 h** |
| v2 + both optional (30) | ≈ 41 | same | **≈ 5.5 h** |

The bound is the load (worker-hours / 8), not the longest run (3.7 h), so the complete matrix fits
in **one working day** with the cap respected; 8 × ~2.2 GB ≈ 18 GB of sat's 91 GiB, so memory is
not the constraint. `s1_launch.py --keep-filled --max-live-workers 8` refills the wave until every
declared run is complete, counting **every** lane's live workers by an anchored `/proc` scan (never
`pgrep -f`), so an S1 wave cannot oversubscribe a machine that is still running the DEV screen.

**The complete matrix is a declaration, not a simultaneity requirement.** All runs are declared and
hashed in one manifest before anything starts (Amendment 13 §7); `--launch-limit` / `--keep-filled`
only defer *starts*. A partial spec list is refused outside `--dry-run` / `--i-am-resuming`.

---

## 3. Launch sequence, once the gate conditions hold

```
# 0. freeze: the mechanism id, the optional cells, and the reading-rules document
# 1. the declaration, hashed before any formal outcome exists
scripts/s1_manifest.py --out artifacts/s1/S1-MC2-MANIFEST-<date>.json \
    --calibration <calibration.json> --mechanism-id <frozen id> \
    [--optional D3-null,D3-XEP] --reading-rules <frozen rules>.md
git add artifacts/s1/S1-MC2-MANIFEST-<date>.json*        # commit BEFORE launching
# 2. the fresh-context review (S1-MC2-REVIEW-BRIEF.md) -> 0 INVALIDATES, 0 BIASES
# 3. dry run on sat: plan, worker count, T0-XEP reference verification, nothing started
scripts/s1_launch.py --root <runs-s1-root> --calibration … --mechanism-id … \
    --reading-rules … --init-manifest --dry-run
# 4. launch, waves of 8, supervised until complete
scripts/s1_launch.py --root <runs-s1-root> … --keep-filled --max-live-workers 8
# 5. the published reference, once (no training)
scripts/s1_reference.py --out <runs-s1-root>/REFERENCE-MODQN-9000.json
```

Fresh roots only: the new `DevSettings`-free lane fields and the new modules change every code
digest, so no existing root can be resumed against this tree (correct behaviour of the identity
scheme; a resume attempt would look harmless and would not be).

---

## 4. Draft reading rules — **for the controller to freeze before launch**

### 4.1 Estimand and quantities

- **Primary estimand**: seed-wise relative pooled EE at episode 1000 on the 24 formal evaluation
  episodes, `EE_X,k / EE_Y,k − 1`, with `EE = Σbits / Σjoules` pooled over the 24 episodes
  (**ratio of sums, divided once**; full-buffer Shannon; consumed power, per-beam max over served
  users), greedy, fresh env per episode, the single ep-1000 checkpoint.
- **Seed-mean** = arithmetic mean over k ∈ {0, 1, 2} of the per-seed ratios. Report the three
  per-seed ratios always, never only the mean.
- **Paired per-episode reading**: the 24 paired per-episode EE values per seed pair (72 per
  comparison) and the count positive, reported beside every seed-mean — the k = 8 round's headline
  failure was visible as 0/24 paired long before any mean was computed.
- **Every number carries four fields and three condition columns**: reference point, information
  level, estimator, numerator + physical harness, power pricing, host and TLE file set.

### 4.2 The comparisons, fixed now

| id | numerator / denominator | status |
|---|---|---|
| `FULL_vs_MODQN_eq16` | FULL / MODQN eq-(16) @1000 | **gate** — the project's only success gate |
| `FULL_vs_A_only` | FULL / drop-one of B (`D3-T0` under v1, `A-only-v2` under v2) | **gate** |
| `FULL_vs_D3T0` | FULL / `D3-T0` | **gate** (R1-1; identical to the previous row under v1) |
| `FULL_vs_B_only` | FULL / `B-only` | **gate** |
| `FULL_vs_B_null` | FULL / `B-null` | **gate** |
| `FULL_vs_D0` | FULL / `D0` | **QoS floors** + the headline causal number |
| `D3T0_vs_D0` | `D3-T0` / `D0` | **reported, never merged into the headline** (the split ruling) |
| `FULL_vs_D2T0`, `D3T0_vs_MODQN_eq16`, `FULL_vs_REF9000` | — | reported, no superiority claim from the last one unless it also succeeds |
| `D3T0_vs_D3_null`, `D3T0_vs_D3_XEP` | — | only if the optional cells are included; ρ_info decides **wording** |

### 4.3 QoS floors (per seed, FULL vs the same-seed `D0`), unrelaxed

`served`: `D0.served − FULL.served ≤ 0.005`; `per_served_user_rate_p10_bps ≥ 0.5 ×`;
pooled `bits ≥ 0.95 ×`. A breach on **any** seed is a failure of that cell, not an average.

### 4.4 What counts as "survives S1" (draft)

All of the following, at ep 1000 on the formal set:

1. `FULL_vs_MODQN_eq16` seed-mean > 0 with ≥ 2/3 seeds positive — **the same-budget win gate**.
2. `FULL_vs_A_only` seed-mean ≥ **+1.0 %** with ≥ 2/3 seeds positive.
3. `FULL_vs_D3T0` seed-mean ≥ **+1.0 %** with ≥ 2/3 seeds positive (R1-1).
4. `FULL_vs_B_only` seed-mean > 0 with ≥ 2/3 seeds positive.
5. `FULL_vs_B_null` seed-mean > 0 with ≥ 2/3 seeds positive.
6. The §4.3 floors hold on every seed.
7. **B activity** ≥ 1 % of decision rows on every seed (contract F-1 / R1-3), from the training logs:
   v1 numerator = user-steps tagged `B`; v2 numerator = user-steps whose winner is `a^B` with
   `a^B ≠ a^A`; denominator = user-steps with at least one legal action over all t.

### 4.5 What does **not** count as surviving

- Beating only `D0` (that is the backbone plus the anchor, most of which `D3-T0` already delivers).
- Beating only the frozen 9000-episode reference, or losing to the same-budget MODQN while beating
  the 9000-episode one.
- A positive seed-mean with < 2/3 seeds positive, or carried by one seed.
- Any comparison not in §4.2; any threshold different from §4.4; any floor relaxed anywhere.
- `ρ_info`, the judge's own win/override rate, the margin dose, the judge's evaluation count, or
  any training-log quantity: **diagnostics, never evidence**. A judge win is not an EE improvement.
- Anything read from a checkpoint other than ep 1000 — there is only one, by construction.
- `FULL_vs_B_null` alone: it identifies whether T_NEXT's specific proposals beat content-free ones
  under the same judge and anchor. It is **not dose-matched** and identifies nothing about the value
  of the judge, whether foresight is the active ingredient, or whether privileged information is
  necessary (contract §7 disclosure).

### 4.6 Nothing chosen after seeing formal data

The cell list, the seeds, the depth, the estimand, the thresholds, the floors, the QoS definitions
and the wording map are in the manifest and in the hashed rules document **before** launch; the
formal set is read **once**, at ep 1000; no cell is added, no seed extended, no threshold moved, no
re-run on the formal set. If a gate fails, what goes to the owner is the data, the smallest blocking
reason and the specific hypothesis that would have to change — not a repair.

### 4.7 Reported beside every reading, never hidden

FULL vs `D3-T0` bits / joules / served / p10; override and win rates for FULL and for `B-null`
(with the "not dose-matched" disclosure); per-episode margin doses for `B-only` and every v2 cell;
per-source margin-loss share and sampled rows per tag; judge evaluations and judge wall; formal-set
greedy agreement with `a^A` and with `a^B` where they differ; and, if the optional cells ran,
`t0xep_agreement` against its exact uniform-legal expectation (the null's residual leakage, making
ρ_info a lower bound).

---

## 5. Open items the controller must close before the manifest is hashed

1. **Which mechanism id is frozen** (`MC2-JGO-v1` or `MC2-ARB-v2`) — the matrix, and whether
   `A-only-v2` exists, follow from it.
2. **Which optional cells are included** (`D3-null`, `D3-XEP`, both, neither).
3. **The reading-rules document**: §4 of this file, amended as the controller wants, saved and
   hashed into the manifest (`--reading-rules`).
4. **The calibration file** to pin (`59952214…` is the one this lane used locally).
5. Whether the 24 formal evaluation episodes stay at 24 (Amendment 13's count; unchanged here).
