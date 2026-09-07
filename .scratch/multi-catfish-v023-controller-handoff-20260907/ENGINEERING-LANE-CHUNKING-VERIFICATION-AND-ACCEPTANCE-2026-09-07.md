# Engineering lane — stage-C chunking verification + server acceptance (2026-09-07 19:30 UTC)

Claim ceiling: `ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. NON-FORMAL. No scientific token emitted.

## Part 1 — verification and commit

**(a) Tests.** `86 passed, 1 skipped in 69.19 s`, exit 0 (skip: `test_v023_c1c2_successor_stagec_launch.py:442`,
"workspace already contains the required post-fix adapter"). No failures, no tracebacks. Note `pyproject.toml:27`
sets `addopts="-q"`, so the mandated `-q` becomes `-qq` and suppresses the count line; re-ran with `-o addopts=`.

**(b) Manifest.** `STAGEC_CODE_MANIFEST_CURRENT entries=265 sha256=4ffa5b2c95efe5964d3e41c326b43966263ca60b3523a9e639b43a123770a324`
— matches codex. `SHADOW-CLOSURE-LIST-2026-09-07.txt` = 246 paths, 0 missing. Builder fails closed if the list is
absent (`build_v023_c1c2_successor_stagec_manifest.py:28-30`), satisfying charter rule 11.

**(c) Spot checks — all six ruling items hold.**
1. Boundary replay: `runner.py:1533-1537` draws `age_rng.integers(0, STEPS, size=USERS)` per episode; `:1500-1503`
   spawns the stream once from world-1's env RNG, mirroring `src/mcrl/env/step.py:534-536`. No `advance(` anywhere in
   the two packages; no per-episode reseeding. `git status --porcelain src/` is empty.
2. Ranges: `runner.py:1587-1592` (positive, contiguous, 100-aligned); write-once roots `:245-264`, duplicate refusal
   `:1610-1611`.
3. Merge: `merge_arm_chunks:1817-1820` re-runs `pool_receipts` over the ordered per-episode prefix; `pool_receipts:897-898`
   is the unchanged `math.fsum` over individual episode totals. Chunk subtotals are never summed.
4. `merge_four_arm:1958` adjudicates only at `completed == 3000`; `:1888` refuses >3000.
5. Early BASELINE: sealed-file authentication `runner.py:375-420` (`episode_range == [1,3000]`,
   `continuation_to_9000_authorized is False`); boundary builder refuses beyond the limit `:1495-1497`.
6. `merge_four_arm:1866` refuses a missing arm. Fan-out `launch_stage_c_chunks.sh:33-37` caps workers at cores−2 and
   exports `OMP/OPENBLAS/MKL/NUMEXPR=1` per worker. Verifier float equality is bitwise
   (`verify_...py:31-35`, `struct.pack(">d",…)`); the one remaining `math.isclose` (`:310`) is the prefix+delta
   cumulativity cross-check, where bitwise equality would be wrong. Local equivalence tests exist and pass
   (`test_cadence_resume.py:484,520,537`). Sequential reference untouched: `run_v023_c1c2_successor_stage_c.py` is not
   in the diff, and the runner diff has no hunk between old lines 1273 and 1815 (`FixedPolicyEvaluationRunner` intact).

**(d) Commit `2b476b0`** on `wip/multi-catfish-v023-20260907` — 18 files, every SHA-256 matching codex's list. Four
directories rsynced to `/home/sat/mcrl-v023-successor-shadow-20260907/.scratch/` (local → shadow only).

## Part 2 — server acceptance (BASELINE)

Roots: `/home/sat/mcrl-v023-stageC-CHUNK-ACCEPTANCE-NONFORMAL-20260907T185925Z{,-checkout}`.

**Deviation (blocker, class (d)):** `ACCEPTANCE-SERVER-EQUIVALENCE.md` runs in the shadow, but that root has neither
`.git` nor `.venv`, while `stagec_common.py:282` requires `git_identity(REPO)` on it. I built a purpose-made
non-formal checkout instead (sync-list closure rsynced from the committed tree, `git init`+commit, manifest re-checked
CURRENT with the same `4ffa5b2c…` digest), bound in early-BASELINE mode, and used
`PYTHONPATH=<checkout>/src` (required by `process_environment`, so the mandated shadow PYTHONPATH was not usable).
**Class (a):** the sync list omits `SHADOW-CLOSURE-LIST-2026-09-07.txt`, so a sync-list-only checkout cannot pass its
own `--check` until that file is added (the formal flow gets it from the seed checkout).

| check | result |
|---|---|
| BASELINE 200 sequential vs 2×100 chunks | **PASS** `PASS_BITWISE_CHUNK_EQUIVALENCE`, 200 episodes, chunks [[1,100],[101,200]]; boundary hashes 0/100/200 = `b2229343…`/`7cd756e2…`/`ce6d2eef…`; wall **10:43.95**, peak RSS **1.67 GB**; sidecar verified |
| two workers **in parallel** (`run-chunk` ×2) | **PASS** — episode records, `boundary-start`, `boundary-end` byte-identical to the acceptance chunks; receipts differ only in `started_utc`/`ended_utc`/`runtime`, all inside the enumerated excluded set. Wall 2:55.01 / 2:52.28, RSS 1.48/1.47 GB |
| SIGKILL mid-chunk + resume (300→400) | **PASS** — killed at 75/100; 75-file prefix digest `024aaa01…` unchanged after resume; resume completed 100 in 44.34 s, RSS 1.05 GB, end state matched the authenticated table |
| duplicate completed chunk | **PASS** — `STOP_PHYSICAL_EVALUATION_INTEGRITY: duplicate completed chunk refused`, exit 2 |
| concurrent second writer (accidental) | refused by write-once (`refusing to overwrite output: …episode-000297.json`); prefix uncorrupted |

Measured 1.71–1.73 s/episode. My processes peaked at 3.31 GB total, under the 6 GB cap. No sealed, `*r8*`,
`*lcsrs-gate*`, `*-r7-*`, `codex-ws-*` or `c3-contingency-f1-*` path was touched.

**FULL2 skipped — deliberately.** `accept_stage_c_chunk_equivalence.py` hardcodes 200 episodes and boundaries
`(0,100,200)` with no CLI knob, and `run_arm_chunk` (`runner.py:1590-1591`) refuses non-100-aligned ranges, so a
2×50 rehearsal is not supported. Independently, no Stage-A/B PASS receipts exist and fabricating them is forbidden;
sequential 100 + 2×50 at 13.6 s/episode would also exceed the 60-min budget. **Three learned-arm acceptances remain
pending — formal chunk execution is still gated.**

## Non-blocking notes
- `launch_stage_c_chunks.sh` caps workers at cores−2 **per invocation**; four concurrent arm launches could reach
  4×(cores−2). The aggregate cap must be enforced by the operator.
- The acceptance script runs its two chunks serially in-process; the parallel-worker case is only covered by the extra
  run above.
- Early-BASELINE admission relaxes the sealed sampler-digest check to a structural one (`runner.py:1240-1246`).
  Moot now that addendum §1 is withdrawn (19:10 UTC), but it should be restored if the path is ever reinstated.
- Boundary replay hardcodes `integers(0, STEPS, size=USERS)`, valid only while `segment_warm_start ==
  "uniform-episode-length"` (`src/mcrl/env/step.py:142,1398-1406`). `run_episode` asserts steps/users but not the
  mode; the physical acceptance is what actually proves the stream matches.
- Addendum §1 (early BASELINE) was withdrawn at 19:10 UTC. This run used that code path purely as an engineering
  vehicle for the equivalence proof; it materialises nothing and adjudicates nothing.
