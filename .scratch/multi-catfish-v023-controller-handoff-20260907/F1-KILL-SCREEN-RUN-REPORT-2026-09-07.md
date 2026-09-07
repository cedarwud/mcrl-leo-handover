# F1 Kill-Screen Run Report — 2026-09-07

**Outcome: `INVALID_RUN`** (fail-closed on an F0 integrity check, before any tape step was written). No retry performed, per protocol.

## Launch authority

Created `.scratch/multi-catfish-v023-c3-contingency-f1/F1-LAUNCH-AUTHORITY-2026-09-07-r1.json` (+ `.sha256`, both chmod 0444).
`sha256 = 9bf367cb72d1a6f005fdab09e885a8b8c069e265208e8798ee28026f6b6bb382`.

Content is exactly the 8 keys `_validate_launch_authority` compares by strict dict equality: `schema=multi-catfish-mcrl-v023-c3-contingency-f1-v1-launch-authority`, `status=FROZEN_LAUNCH_AUTHORITY`, `claim_ceiling` and `bindings` copied verbatim from the preflight manifest, `preflight_manifest={"path":".scratch/multi-catfish-v023-c3-contingency-f1/F1-PREFLIGHT-MANIFEST.json","sha256":"495d90d2e1dac41abac87f28aad3f75eaa7e1c448910ea27edcc172a12496e24"}`, `test_split_opened=false`, `episode_training=false`, `learner_update=false`. Confirmed by running `_validate_launch_authority` directly (local and server) via a small script that imports the runner module.

**Deviation, recorded per hard rule ("fix the authority file, never the runner"):** I tested adding `frozen_at_utc=2026-09-07T15:10:43Z`, `frozen_by="controller (Claude Fable 5.1) under owner delegation 2026-09-07"`, `ladder_branch="STOP_PHYSICS -> open F0/F1 for D and F"`, `r7_result_sha256=dfcc70e441e2ec2c3be20608124c704c6d5c80b4d902a1aa7b75328faadbd2f7`. The validator rejected the file with any extra top-level key (`launch authority does not pin the exact F1 preflight/bindings`, verified empirically) because it does full dict equality, not a superset check. The four fields above are recorded here instead of inside the JSON; the r7 hash also independently matches the preflight's pinned `r7_stop_receipt.sha256`.

## Commands run

```
rsync -a --exclude __pycache__ .scratch/multi-catfish-v023-c3-contingency-f1/ \
  sat:/home/sat/mcrl-v023-successor-shadow-20260907/.scratch/multi-catfish-v023-c3-contingency-f1/

ssh sat 'tmux new-session -d -s mcrl-v023-c3-f1-20260907-r1; tmux send-keys -t mcrl-v023-c3-f1-20260907-r1 -l -- \
  "cd /home/sat/mcrl-v023-successor-shadow-20260907 && echo 1000 > /proc/self/oom_score_adj; \
   PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 PYTHONPATH=$PWD/src /home/sat/mcrl-leo-handover/.venv/bin/python \
   .scratch/multi-catfish-v023-c3-contingency-f1/run_v023_c3_contingency_f1.py \
   --preflight-manifest .scratch/multi-catfish-v023-c3-contingency-f1/F1-PREFLIGHT-MANIFEST.json \
   --launch-authority .scratch/multi-catfish-v023-c3-contingency-f1/F1-LAUNCH-AUTHORITY-2026-09-07-r1.json \
   --tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 \
   --output /home/sat/mcrl-v023-c3-contingency-f1-20260907-r1 \
   2>&1 | tee /home/sat/mcrl-v023-c3-contingency-f1-20260907-r1.log" Enter'
```

Server digests matched local: preflight `495d90d2…496e24`, authority `9bf367cb…6bb382` (both `sha256sum -c` OK).

## Result

- Wall time: **~36 s** (tmux launch 2026-09-07 15:14:07 UTC → receipt/log mtime 15:14:43.8 UTC).
- Peak RSS: **not available** — process exited before the first 60 s sample in the bounded wait loop.
- Tape: **not produced** (`tape_complete=false`, `tape_sha256=null` in the receipt) — the crash occurred inside tape generation, before any step or candidate was written.
- Receipt: `/home/sat/mcrl-v023-c3-contingency-f1-20260907-r1/receipt.json`, `sha256=cfb6fa9e40a0acc844b034ec6bfa6fc205ff9071fdd72e23b88bb5e25cef906a`.
- BASE/D/F pooled EE, service, and "changes ≥1 legal action" counts: **not computed** — `metrics=null`, `kill_rules=null` in the receipt (INVALID_RUN short-circuits scoring).

**Exact error** (from `run_v023_c3_contingency_f1.py:1380` → `c3_contingency_f0.py:923→902→821→777`, raised in `CostShareResult.__post_init__` at `c3_contingency_f0.py:623`, while validating the **reference/BASE** profile's cost shares — i.e. this recurs on the very first candidate regardless of order):

```
F1_ERROR: total share energy does not equal beam plus satellite share
c3_contingency_f0.C3F0Error: total share energy does not equal beam plus satellite share
```

## Roots

- Shadow checkout: `/home/sat/mcrl-v023-successor-shadow-20260907`
- Output root: `/home/sat/mcrl-v023-c3-contingency-f1-20260907-r1` (receipt.json only)
- Log: `/home/sat/mcrl-v023-c3-contingency-f1-20260907-r1.log`
- tmux session `mcrl-v023-c3-f1-20260907-r1`: still present, idle at shell prompt (left as-is, not killed)

Per protocol: stopping here, no retry, no attempt to repair `c3_contingency_f0.py`.

---

## r2 follow-up (2026-09-07, ~16:15 UTC) — repair verified, **replay withheld** pending a defect decision

**Diagnosis accepted, class (i) roundoff, corroborated independently:** the repair reuses the module's own pre-existing `_roundoff_tolerance()` helper (already used by `_assert_close`) for the one `total_share_energy_j` check that previously used bitwise `np.array_equal`; the neighbouring `total_share_power_w` check is untouched (power has no multiply-by-`interval_s` step, so it doesn't exhibit the same non-associativity). The new test asserts the exact discrepancy `2.842170943040401e-14` against a tolerance the same helper computes as far larger, matching the coordinator's `2.8e-14 vs 5.1e-11` figures.

**Files pulled read-only from `/home/sat/mcrl-v023-codex-ws-f1diag-20260907`** (never written to) into the local repo at identical relative paths, via per-file `rsync` (no chmod needed — rsync's temp-file+rename replaced the 0444 originals cleanly): `c3_contingency_f0.py`, `run_v023_c3_contingency_f1.py`, `test_run_v023_c3_contingency_f1.py`, `F1-PREFLIGHT-MANIFEST.json`/`.sha256`. New preflight digest confirmed both locally and server-side: `3711b9307b8cd12002df5bd9d4caacf9f96b5b5633dbf1fe4a4a062f421ff887`. New `c3_contingency_f0.py` digest: `9a8a97c02d2f0833cda6878a5327d5bd94662c95b662ee8b6c9aa138e0a806d2`.

**Test suite: 40/41 pass, `F1_DRY_RUN_PASS` locally and server-side.** The one failure, `test_real_base_anchor0_energy_roundoff_is_accepted`, is unrelated to the fix's correctness — it is a fixture-path defect:

```python
fixture_path = Path(__file__).resolve().parents[2] / ".tmp" / "base-profile-anchor0.npz"
```

This resolves to `<repo_root>/.tmp/base-profile-anchor0.npz` — **outside** the F1 package directory and outside every rsync scope this whole procedure uses (package-dir syncs never touch repo-root `.tmp/`). Per instruction, I copied the fixture to the requested canonical location on both sides, `.scratch/multi-catfish-v023-c3-contingency-f1/fixtures-real-anchor/base-profile-anchor0.npz` (sha256 `4aa5e00abd26a262a1651df2cba89d74b22f2e8d144bfc086236001ceda71631`, verified equal to the workspace source), but the test's hardcoded `.tmp` literal does not read from that location, so the copy does not make it pass. **I did not create a repo-root `.tmp/` directory** (outside my authorized write scope, and doing so would have silently defeated the intended stop-gate). Result: `FileNotFoundError` locally; 40 other tests, including all other F0/F1 regressions, pass.

**F2 rebuilt (independent of the defect above), fully green:** relocated the stale `F2-PREFLIGHT-MANIFEST.{json,sha256}` to `*.pre-f0-roundoff-repair.*` (non-destructive rename, since the builder exclusive-creates), reran `build_f2_preflight_manifest.py` → new digest `625ad7f2c8f384bcb62242e7786b566d39172e4d6ba2f09f771d3d2dcfc98789` (F2 imports F1 live, so it picked up both new digests automatically, including `reused_f1_formula_digests.f0_file_sha256=9a8a97c0…`). F2: 17/17 tests pass, `F2_DRY_RUN_PASS` locally and server-side.

**r2 launch authority**, same 8-key strict shape as r1, bindings/claim_ceiling unchanged (only `preflight_manifest.sha256` differs): `.scratch/multi-catfish-v023-c3-contingency-f1/F1-LAUNCH-AUTHORITY-2026-09-07-r2.json` (+ `.sha256`, chmod 0444), `sha256 = c3f9c2b254480b26df03e57352aed958a1232f4cccf383bd813ac82b8fa4f1a1`. Validated by direct `_validate_launch_authority` call, locally and server-side (both `True`). Provenance for this r2 (recorded here, not embedded — same reason as r1): `frozen_at_utc=2026-09-07T16:15:55Z`, `frozen_by="controller (Claude Fable 5.1) under owner delegation 2026-09-07"`, repair class `(i) IEEE-754 roundoff, permitted repair-and-replay`.

**Shadow sync done, all digests verified server-side:** F0, F1 (incl. r2 authority and the fixture copy), and F2 package directories rsynced to `/home/sat/mcrl-v023-successor-shadow-20260907`; every sha256 above matches byte-for-byte between local and server.

**STOPPING BEFORE THE REPLAY.** Per explicit instruction ("if the test hard-codes `.tmp`, report it as a defect and do not run the replay until the controller decides"), tmux session `mcrl-v023-c3-f1-20260907-r2` was **not** created and `/home/sat/mcrl-v023-c3-contingency-f1-20260907-r2` was **not** launched. Everything needed to launch is staged and verified; awaiting the controller's decision on the test-fixture defect (e.g., fix the test's path convention, or explicitly waive it and proceed) before replaying F1 once.

---

## r2 replay attempt (2026-09-07, ~16:33 UTC) — **premise not verified; replay still withheld**

The coordinator reported the fixture-path defect fixed ("test now loads `fixtures-real-anchor/base-profile-anchor0.npz`, asserts sha256 `4aa5e00a…`, 41/41 pass locally"). **I could not confirm this and did not proceed to replay.**

**What I checked:** re-pulled `test_run_v023_c3_contingency_f1.py` from `/home/sat/mcrl-v023-codex-ws-f1diag-20260907` (the only source I have for this fix). Its sha256 is `8196631f1dac1bdd30198bd6118da5b6e179a576f7fb7d3043925714b9a14191` — byte-identical to what I pulled originally (`git diff` against that workspace's own HEAD is unchanged: same blob `572874d`, same 58-line insertion, same test body, still `fixture_path = Path(__file__).resolve().parents[2] / ".tmp" / "base-profile-anchor0.npz"`). Neither the string `4aa5e00a` nor `fixtures-real-anchor` appears anywhere under that workspace's `.scratch/`, nor anywhere in my local F1 package. There is only one `mcrl-v023-codex-ws-f1diag-*` directory on the server.

**Empirical result, both sides, identical:** ran `pytest -q -p no:cacheprovider .scratch/multi-catfish-v023-c3-contingency .scratch/multi-catfish-v023-c3-contingency-f1` after re-syncing this file to the shadow checkout — **1 failed, 40 passed** on both local and shadow, same test, same error:
```
FileNotFoundError: [Errno 2] No such file or directory: '.../.tmp/base-profile-anchor0.npz'
```
`--dry-run` still passes both sides (unaffected, as expected, since the preflight indeed does not cover the test file — that part of the coordinator's claim checks out).

**Likely context:** this repo checkout is shared with an active, separate process — `git log` shows a running series of `WIP <timestamp> UTC` commits (e.g. `d371908 WIP ... F1 roundoff diagnosis; F2 prep`, `a8de0f6 WIP ... F1 launch authority r1 + INVALID_RUN report`) on branch `wip/multi-catfish-v023-20260907` (not `main` — the branch changed under me since this session started). The real fixture-path fix may exist in that process's own state and not yet be written back to the diagnostic workspace or this checkout.

**(1) Shadow sync:** done — F1 package (incl. the as-is test file and `fixtures-real-anchor/`) rsynced to `/home/sat/mcrl-v023-successor-shadow-20260907`; tests and `--dry-run` run there (results above).

**(2) Commit:** done. `git add -A -- .scratch/multi-catfish-v023-c3-contingency .scratch/multi-catfish-v023-c3-contingency-f1 .scratch/multi-catfish-v023-c3-contingency-f2` then committed with the exact requested message and trailer.
- SHA: `eaf044f298fcbdadfd4384f12b2c5b2b4e5bc966`
- Branch: `wip/multi-catfish-v023-20260907`
- 12 files changed (7 modified, 5 added — the r2 authority pair, the fixture copy, and the renamed pre-repair F2 preflight pair), no unrelated files swept in (pathspec-scoped).

**(3) Replay:** **not run.** Launching a 90-minute shared-server job on a test suite I cannot verify at 41/41 — when the file I can directly inspect still fails the same way it did before — would repeat the same "don't proceed on an unverified premise" mistake this whole ladder is designed to prevent. Requesting: either point me to the actual fixed `test_run_v023_c3_contingency_f1.py` (or push it to `mcrl-v023-codex-ws-f1diag-20260907` or directly to this checkout) so I can re-verify 41/41 myself, or confirm the fixture-test failure should be explicitly waived (it does not gate the run itself — `run_v023_c3_contingency_f1.py --dry-run` and the launch authority are unaffected). No tmux session or output root was created for r2.

---

## r2 replay (executed) — 2026-09-07 — **outcome `FAST_SCREEN_NO_SUPPORT`**

Root cause confirmed: my earlier server→local rsync had overwritten the coordinator's already-committed fix (two writers on one path). Fix re-verified from the **local repo only** (commit `077aed8`, no further pulls from `mcrl-v023-codex-ws-f1diag-20260907`): `test_run_v023_c3_contingency_f1.py` sha256 `c46578fd8c9ee0ae98d2d1cdca956372a4dd0fe9a5c23b117a3927aee5ee8c1a`, loads `fixtures-real-anchor/base-profile-anchor0.npz` from inside the package, asserts its sha256. **41/41 pass locally**, `F1_DRY_RUN_PASS`.

Synced local → shadow only (three `rsync -a --exclude __pycache__` calls, one per package dir, exactly as specified). Server verification: test file sha256 confirmed `c46578fd8c9ee0ae…` (matches); **41/41 pass on the shadow checkout**; `F1_DRY_RUN_PASS`. r2 authority re-checked unchanged, `c3f9c2b2…`.

Launched tmux `mcrl-v023-c3-f1-20260907-r2` at 2026-09-07 16:40:25 UTC (output root and log confirmed absent beforehand) with the r2 authority, TLE root, and env exactly as specified. My local bounded-wait process was killed mid-wait by an unrelated local low-memory event (not a server event); the server run was unaffected (detached tmux) and had already finished by the time I reconnected and checked directly.

- **Outcome token: `FAST_SCREEN_NO_SUPPORT`** (`status="COMPLETE"`, not `INVALID_RUN` — no retry needed, nothing to quote).
- Wall time: **383 s (~6 min 23 s)**, 16:40:25 → 16:46:48.25 UTC (tmux launch → receipt mtime).
- Peak RSS: **not available** (monitor killed before any sample; process had already exited by reconnect).
- Tape digest: `738f9f01b7a455e92d70f6e7348be8004b7d33f97b81b0557b77f4ffaeaba244` (matches tape manifest and receipt `tape_sha256`; tape file 62,022,148 bytes, mode 0444).
- Receipt: `/home/sat/mcrl-v023-c3-contingency-f1-20260907-r2/receipt.json`.

**Recorded, verbatim from `receipt.json`, without interpretation:**

`kill_rules`:
| | integrity | action_changed | service_noninferior | ee_strictly_above_base | survives |
|---|---|---|---|---|---|
| D | true | true | false | false | false |
| F | true | true | true | false | false |

(The receipt records "changes at least one legal action" only as this boolean `action_changed` field — true for both D and F; no numeric count field is present.)

`metrics`:
| | ratio_of_sums_ee_bits_per_j | served_user_steps | service_fraction | service_opportunities | total_bits | total_energy_j |
|---|---|---|---|---|---|---|
| BASE | 118630258.50679842 | 200 | 1.0 | 200 | 2619974613947.755 | 22085.21372983108 |
| D | 117054987.33796957 | 199 | 0.995 | 200 | 2801477796300.5664 | 23933.006700619586 |
| F | 113248875.74791098 | 200 | 1.0 | 200 | 3006393310511.618 | 26546.782832562247 |

No further action taken on this receipt; the ladder's own branching for `FAST_SCREEN_NO_SUPPORT` is the controller's decision, not mine.
