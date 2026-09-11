**Of the four `b0/corrected-baseline-20260911`-only commits, two (`0acd146c` D-3, `ccbbb048` D-3 fixup) are PORTED-IDENTICAL and two (`832471ca` D-2, `923d68b0` pilot driver+eval) are PORTED-WITH-DIFFERENCES that touch `src/`/`scripts/`/`tests/` (not just docs); the archive tag `archive/b0-corrected-baseline-20260911` was created at `ccbbb048`, and the worktree `/home/u24/papers/mcrl-leo-handover-b0` was NOT removed because the removal bar (every commit PORTED-IDENTICAL or differences confined to `.scratch/`/docs) is not met.**

Git housekeeping audit, Q8 part 2. No science; this is a content-equivalence check between the
throwaway worktree branch `b0/corrected-baseline-20260911` (tip `ccbbb048`) and HEAD of
`wip/multi-catfish-v023-20260907` (`53e059cf` at audit time), to decide whether the branch's
content is safely on the main line before removing its worktree.

Every commit named below is confirmed an ancestor of HEAD by `git merge-base --is-ancestor <sha> HEAD`.

---

## Per-commit classification

### `832471ca` — "B0 D-2: an outage no longer dominates service on either bounded head" — **PORTED-WITH-DIFFERENCES**

Cherry-picked onto the shared branch as `ee0ffa60` (confirmed same subject line, parent chain
recorded in `.scratch/b0-corrected/PROGRESS.md` R2). Its v1 fix (an unserved user floored at a
flat `r3 = -num_users = -100`) was then **superseded** by the controller's R4 ruling, landed as
`c00aca3e` ("D-2 per-step floor: an outage scores the worst served value of its own step"), which
replaces the flat floor with a **per-step, physics-derived** floor (`r3 = -max_b U_b(t)`, the worst
value any served user actually received in that same step). Both `c00aca3e` and `ee0ffa60` are
ancestors of HEAD.

| file touched by `832471ca` | present at HEAD | comparison (`git show 832471ca:<path>` vs `git show HEAD:<path>`) |
|---|---|---|
| `src/mcrl/env/step_types.py` | yes | **byte-identical** (`diff` empty) |
| `src/mcrl/runtime/trainer_env.py` | yes | **byte-identical** (`diff` empty) |
| `src/mcrl/algorithms/modqn.py` | yes | `832471ca`'s own hunk (import `apply_outage_floor`; `reward_vector_from_step_result` gains a `num_users` kwarg and calls `apply_outage_floor(vector, num_users=...)` gated on `served`) is **structurally present** at HEAD's `reward_vector_from_step_result` (same `served is None` guard, same doc-referenced defect), but the call site now reads `cached = (result, per_step_outage_floor(result.rewards, served)); vector = apply_outage_floor(vector, r3_floor=r3_floor)` and the `num_users` kwarg is gone — this is `c00aca3e`'s rewrite, not a loss of `832471ca`'s content. |
| `src/mcrl/runtime/outage_gate.py` | yes | **real diff.** `832471ca`'s `outage_r3_floor(num_users) -> -float(num_users)` and the module docstring's "loose bound... needs W-13" text are replaced by `per_step_outage_floor(rewards, served) -> (r2_floor, r3_floor)`, which computes `r3_floor = min(served r3 values)` and raises `MCRLContractError` if nobody is served. `apply_outage_floor`'s signature changed from `num_users: int` to `r3_floor: float`. |
| `tests/test_b0_d2_outage_floor.py` | yes | **rewritten.** 183 lines (at `832471ca`) -> 213 lines (HEAD); 292 differing lines out of a ~200-line file (near-total rewrite) to assert the v2 per-step-floor contract (e.g. "a step with nobody served raises", "the floor equals -max_b U_b from real physics") instead of the v1 flat-`-100` contract. |

**Verdict for `832471ca`:** the defect this commit fixes (outage inverting the reward compared to
service) is fixed in HEAD, and the fix is gated and placed exactly the way `832471ca` put it
(in `reward_vector_from_step_result`, keyed on `served`, `r1` untouched) — but the floor's numeric
rule and its test were substantively rewritten by a later, in-ancestry commit (`c00aca3e`) per
controller ruling R4. This is a real `src/`+`tests/` difference, not a docs-only one.

### `0acd146c` — "B0 D-3: log the calibrated scalar as the headline; keep the old one renamed" — **PORTED-IDENTICAL**

Cherry-picked onto the shared branch as `698f20d8` (same subject, recorded in `PROGRESS.md` R2).

| file touched by `0acd146c` | present at HEAD | comparison |
|---|---|---|
| `src/mcrl/runtime/trainer_spec.py` | yes | `0acd146c`'s own hunk (`scalar_reward_calibrated`, `scalar_reward_uncalibrated_deprecated` fields, the read-only `scalar_reward` property) is **byte-identical** in HEAD. A whole-file diff shows HEAD carries two extra, unrelated blocks appended around it — a `td_bootstrap_mode` field and its comment block (from `57fb40b4`, the D-1-flag ruling) and an `outage_user_steps` field (from `c00aca3e`, D-2 v2) — neither overlaps or edits D-3's lines. |
| `src/mcrl/runtime/training_pipeline.py` | yes | `0acd146c`'s own hunk (`OBJECTIVE_WEIGHTS_FOR_LOG_RECONSTRUCTION`, the `scalar_reward_uncalibrated_deprecated`/`scalar_reward_calibrated` branch in `_episode_log_from_dict`, the four `status["last_*_calibrated"]` lines) is **byte-identical** in HEAD. The whole-file diff shows only additions (the TLE-pin block: `resolve_tle_root`, `assert_tle_archive_pinned`, from `b924c8a0`) plus one unrelated line changed (`archive = TleArchive(Path(TLE_ROOT_DEFAULT).expanduser())` -> `archive = TleArchive(resolve_tle_root())`, also from `b924c8a0`, not part of D-3). |
| `src/mcrl/algorithms/modqn.py` | yes | `0acd146c`'s own hunk (`scalar_calibrated = scalarize_objectives(calibrated, ...)`, `scalar_uncalibrated = scalarize_objectives(avg_reward, ...)`, `EpisodeLog(..., scalar_reward_calibrated=..., scalar_reward_uncalibrated_deprecated=...)`) is present **byte-identical** at HEAD (confirmed by locating `scalar_calibrated`/`scalar_uncalibrated`/`scalar_reward_calibrated` at the same call sites). |
| `tests/test_b0_d3_calibrated_scalar_log.py` | yes | **byte-identical** to the b0-branch tip (`ccbbb048`, which is `0acd146c` + the fixup) — `diff` empty. |
| `tests/test_w12_collapse_metrics.py` | yes | **byte-identical** to the b0-branch tip — `diff` empty. |
| `tests/test_w30_training_pipeline.py` | yes | **byte-identical** to the b0-branch tip — `diff` empty. |

**Verdict for `0acd146c`:** every line this commit added or changed survives unchanged in HEAD.
The touched files are larger at HEAD only because of later, unrelated, in-ancestry work (D-1 flag,
TLE pin) layered around D-3's lines, never through them.

### `923d68b0` — "B0 pilot: resumable short-run driver and the catfish-surface EE harness" — **PORTED-WITH-DIFFERENCES**

Cherry-picked onto the shared branch as `ff01f84d` (recorded in `PROGRESS.md` R2). A real defect in
the driver it introduced was found and fixed by a later, in-ancestry commit, `363845e8` ("B0 pilot +
eval: bootstrap-mode flag, host pin, phi1/phi2 and outage counts, fresh env per arm", ruling R5/R6).

| file touched by `923d68b0` | present at HEAD | comparison |
|---|---|---|
| `scripts/b0_pooled_ee_eval.py` | yes | 182 lines (at `923d68b0`) -> 277 lines (HEAD), 97 differing lines. The harness core (the `run()` function, `923d68b0`'s original "HARNESS-CORE" block) is **byte-identical**. `363845e8` adds a TLE host-pin assertion at import time, a new `run_extended()` that also counts φ1/φ2 handovers and outage user-steps and computes calibrated head means, a `_fresh_env()` helper, and rewrites the arm loop in `_driver` from a single `run(fn, ...)` call to `_fresh_env(); run_extended(...); _fresh_env(); run(...)` plus an assertion that the two agree — **fixing a real bug**: the original driver built one module-level `env` and ran every arm on it, so `StepEnvironment`'s persistent `_age_rng` stream put arms after the first at unmatched conditions. |
| `scripts/run_b0_pilot.py` | yes | 289 -> 315 lines, 32 differing lines. `923d68b0`'s CLI, resume logic and fingerprinting survive; additions are a `--td-bootstrap-mode` flag threaded into `dataclasses.replace(frozen_config, ...)` and the run fingerprint/role string (from `57fb40b4`, D-1 flag), a TLE host-pin assertion and `tle_root`/`tle_file_set_sha256` status fields (from `b924c8a0`), and `outage_user_steps_so_far` / `outage_user_steps_total` status fields (from `c00aca3e`). These edit two lines `923d68b0` wrote (the `config = dataclasses.replace(...)` call and the `role=f"..."` fingerprint string) to append the new argument/suffix; they do not remove anything `923d68b0` added. |

**Verdict for `923d68b0`:** the original harness core and driver skeleton are intact, but the arm-running
logic in the eval script was extended with a real bug fix (matched-conditions `_fresh_env`) and both
scripts gained fields from unrelated later ruling items. This is a real `scripts/` difference, not a
docs-only one.

### `ccbbb048` — "B0 D-3 fixup: the stdout progress line still read the removed `scalar`" — **PORTED-IDENTICAL**

Cherry-picked onto the shared branch as `6939fc78` (recorded in `PROGRESS.md` R2).

| file touched by `ccbbb048` | present at HEAD | comparison |
|---|---|---|
| `src/mcrl/algorithms/modqn.py` | yes | `ccbbb048`'s own hunk (the `progress_every` print block: `scalar_cal=`, `r1c=`, `r2c=`, `r3c=`, `r1_raw=`, `ho=`, `buf=`, `flush=True`) is present **verbatim** at HEAD, plus exactly one appended field, `f"out={ep_outages} "` (from `c00aca3e`, D-2 v2's outage counter) — confirmed by a line-range diff of the print block: the only delta is that one added `out=` line. |
| `tests/test_b0_d3_calibrated_scalar_log.py` | yes | **byte-identical** to HEAD — `diff` empty (same file `0acd146c` touched; `ccbbb048` added the progress-line test to it, and that addition is intact). |

**Verdict for `ccbbb048`:** fully ported, unchanged; HEAD adds one unrelated field next to it.

---

## `git diff ccbbb048 HEAD --stat -- src scripts tests`

12 files differ, 1159 insertions / 278 deletions. No file present at `ccbbb048` under `src/`,
`scripts/`, or `tests/` is **absent** at HEAD (`git diff ccbbb048 HEAD --diff-filter=D -- src scripts
tests` is empty). The 12 files split into two groups:

**Group A — the four audited commits' own touched files (7 files), already covered above:**
`scripts/b0_pooled_ee_eval.py`, `scripts/run_b0_pilot.py`, `src/mcrl/algorithms/modqn.py`,
`src/mcrl/runtime/outage_gate.py`, `src/mcrl/runtime/trainer_spec.py`,
`src/mcrl/runtime/training_pipeline.py`, `tests/test_b0_d2_outage_floor.py`.

**Group B — HEAD-only additions, from other named commits already ancestors of HEAD, that the
four audited commits never touched (5 files; fine, not b0-branch content):**

| file | status | source (per `PROGRESS.md`) |
|---|---|---|
| `src/mcrl/runtime/collapse_penalty.py` | new (403 lines) | `f531ff99` PENALTYARM |
| `src/mcrl/runtime/trainer_config_validation.py` | new hunk (+13) | `57fb40b4` D-1 flag (`td_bootstrap_mode` validation) |
| `tests/test_b0_d1_scalarised_bootstrap.py` | new hunk (+90/-…) | `5219995a` D-1 + `57fb40b4` D-1 flag |
| `tests/test_tle_archive_pin.py` | new (46 lines) | `b924c8a0` TLE pin |
| `tests/test_w08_vanilla_td_target.py` | changed (55 lines touched) | `5219995a` D-1, restored by `57fb40b4` |

**Conclusion for step 2:** every byte the four b0-only commits contributed to `src/`, `scripts/`,
or `tests/` is traceable at HEAD, either unchanged (`0acd146c`, `ccbbb048`) or deliberately
superseded by a named, in-ancestry, later commit tied to an explicit controller ruling
(`832471ca` -> `c00aca3e`; `923d68b0` -> `363845e8`, plus `57fb40b4`/`b924c8a0`/`c00aca3e`
field additions). Nothing from the b0 branch is silently missing.

---

## Housekeeping checks

- Worktree cleanliness: `git -C /home/u24/papers/mcrl-leo-handover-b0 status --porcelain` -> **empty** (clean). Worktree HEAD = `ccbbb0488d602e179f8bf65235a2abbf59ff3058` on branch `b0/corrected-baseline-20260911`.
- No process uses it: `ps -eo pid,ppid,cmd | grep -i leo-handover-b0` (excluding the grep itself) -> **no matches**.
- Two commit SHAs named as examples in the task brief, `db30b334` and `b50cd087`, exist as commits and are ancestors of HEAD, but are **not** code-porting commits for this branch — `db30b334` is "B0CORRECT: round-2 report and final ledger" and `b50cd087` is "Register CF3PILOT" (both documentation/registry commits, unrelated to the four audited commits' content). The actual porting commits are the ones `PROGRESS.md` itself names: `ee0ffa60`, `698f20d8`, `6939fc78`, `ff01f84d` (cherry-picks, `-x`), plus the superseding commits `c00aca3e`, `363845e8`, `57fb40b4`, `b924c8a0`, `f531ff99` — all nine confirmed ancestors of HEAD by `git merge-base --is-ancestor`.

## Tag and worktree decision

- Created: annotated tag **`archive/b0-corrected-baseline-20260911`** at `ccbbb048` (tag object
  `a5230b4689af5a345b9041b4d71846a031e16fb8`), message = one line per commit (reproduced above in
  substance). Branch `b0/corrected-baseline-20260911` was **not** deleted (per instruction).
- Worktree removal bar: "every commit PORTED-IDENTICAL, or PORTED-WITH-DIFFERENCES confined to
  `.scratch/`/docs." **Not met** — `832471ca` differs in `src/mcrl/runtime/outage_gate.py` and
  `tests/test_b0_d2_outage_floor.py`, and `923d68b0` differs in `scripts/b0_pooled_ee_eval.py` and
  `scripts/run_b0_pilot.py`. Both are real `src/`/`scripts/`/`tests/` differences, not docs-only,
  even though in both cases the difference is a later, deliberate, in-ancestry improvement over the
  b0-branch version (confirmed above) rather than a regression or lost content.
- **Decision: the worktree `/home/u24/papers/mcrl-leo-handover-b0` was left in place, not removed.**
  It is clean and unused, so leaving it costs nothing but disk; removing it despite the two real
  code-level diffs would go beyond what this audit was authorised to decide.

---

## Exact commands run

```
git rev-parse HEAD
git branch --show-current
git worktree list

git cat-file -t 832471ca 0acd146c 923d68b0 ccbbb048 363845e8 db30b334 b50cd087  # (looped, one at a time)
grep -n "363845e8\|db30b334\|b50cd087" .scratch/b0-corrected/PROGRESS.md .scratch/b0-corrected/B0-CORRECTED-BASELINE-2026-09-11.md

for sha in ee0ffa60 698f20d8 6939fc78 ff01f84d c00aca3e b924c8a0 363845e8 db30b334 b50cd087 5219995a f531ff99 57fb40b4; do
  git cat-file -e "$sha" && git merge-base --is-ancestor "$sha" HEAD && git log -1 --format='%s' "$sha"
done

git show --stat --format='%H%n%s%n%an %ad' <each of 832471ca 0acd146c 923d68b0 ccbbb048>
git log -1 --format='%P' <each commit>          # parents, incl. the ee0ffa60/698f20d8/ff01f84d/6939fc78 chain

git show <commit> -- <path>                      # each commit's own hunk, per touched file
diff <(git show <commit>:<path>) <(git show HEAD:<path>)   # full-file comparison, per touched file
git show HEAD:src/mcrl/algorithms/modqn.py | sed -n '<range>p'   # read the current call sites directly

git diff ccbbb048 HEAD --stat -- src scripts tests
git diff ccbbb048 HEAD --diff-filter=D --name-status -- src scripts tests
git diff ccbbb048 HEAD --diff-filter=A --name-status -- src scripts tests

git -C /home/u24/papers/mcrl-leo-handover-b0 status --porcelain
git -C /home/u24/papers/mcrl-leo-handover-b0 rev-parse HEAD
git -C /home/u24/papers/mcrl-leo-handover-b0 branch --show-current
ps -eo pid,ppid,cmd | grep -i "leo-handover-b0" | grep -v grep

git tag -a archive/b0-corrected-baseline-20260911 ccbbb048 -F <message file>
git tag -l -n1 archive/b0-corrected-baseline-20260911
git rev-parse archive/b0-corrected-baseline-20260911
```
