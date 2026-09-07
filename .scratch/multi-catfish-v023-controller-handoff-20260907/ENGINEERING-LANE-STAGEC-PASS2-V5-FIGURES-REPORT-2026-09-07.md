# Engineering lane — stage-C fix pass 2 / V5 drill / figure smoke (2026-09-07)

Claim ceiling: `ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`.

## Part 1 — stage-C fix pass 2: VERIFIED AND COMMITTED

**(a) Codex claims per id** — all **FIXED** (marker: FIXED *procedurally*); every
site re-checked and all 17 claimed file SHA-256 match the tree byte-for-byte.
B2 `stage_c.py:352` + `physical_runner.py:1300` (test `test_cadence_resume.py:276`);
M1 `physical_runner.py:1534`, `:1675`; M2 `stage_b.py:85`, `stagec_common.py:312`,
`verify_stagec.py:314`; M4 `stagec_common.py:401`, `:490`, `renderer:167`;
marker `stage_c.py:259`, `:422`, `README.md:97`; N1 `verify_stagec.py:32`, `:67`,
`:264`; N2 `stagec_common.py:277` + launcher `:50`; n1 launcher `:40` + test
`:446`; n2 `test_render_v023_development_curves.py:382`.
B1 stays PARTIAL, owned by the stage-A lane; not touched.

**(b) pytest** (5 dirs): **90 passed, 1 skipped, exit 0, 51.4 s**; no failures, no
traceback. Skip = `test_..._stagec_launch.py:441` ("workspace already contains the
required post-fix adapter"). **`test_stage_bc_default_status_matrix` PASSES**
(isolated re-run: 1 passed). Note: `pyproject.toml:27` sets `addopts = "-q"`, so
adding `-q` yields `-qq` and hides the count line.

**(c) Manifest / dry-run.** `--check` exit 0, no drift, `entries=259`, digest
`f581d4f30b4809425447c54405f4724a7da2fbac4cf1c2f20ad06ce8dfa57643` (= FROZEN pin
and codex's claim); `--write` not needed. Independently recomputed: **0/246
closure paths missing** from the manifest, 0/246 from the 262-path sync list.
Launcher `--dry-run`: **exit 0**; caller `TMPDIR` preserved verbatim; local
`/proc/self/oom_score_adj` unchanged (0 → 0). n1 confirmed at launcher:41-45.

**(d) Spot checks — all hold.** B2: controller passes the authority *path* plus
digest; the runner re-reads the sealed file and checks schema, 3000→9000 bounds,
plan/policy digests, HELD token, marker sidecar. M2: stage-B gate carries
`runtime_admission`/`admitted_stage_a`/`admitted_exports`; stage C builds and
re-verifies a four-arm `admission_mapping` with resolved export paths + digests.
N1: STOP refusal (:47-54), frozen-policy reconstruction (:67), cumulative-prefix
identity **and** prefix+delta additivity (:264). N2: `verify_runtime_identity`
enforces `HEAD`/`HEAD^{tree}` plus the frozen process config at runtime; the
launcher enforces both on the seed checkout and after rsync. Marker:
`owner_reply_verbatim` (≥20 chars), both UTC-Z timestamps (ordered),
`notification_channel`, `recorded_by` (== session id) and `result_3000_sha256`
all bound; README calls it a **procedural control, not cryptographic owner
verification**.

*Non-blocking:* `git_identity` hashes `HEAD^{tree}`, not the working tree, so
drift outside the code closure is invisible; and the dry-run echoes
`V023_STAGEC_PYTHON` verbatim into the remote command.

**(e) Committed `90cc860`** on `wip/multi-catfish-v023-20260907` (17 files;
`__pycache__` gitignored; engineering-lane dir unchanged). Rsynced the four dirs
to `sat:/home/sat/mcrl-v023-successor-shadow-20260907/.scratch/`, verified by
remote sha256sum.

## Part 2 — V5 interruption drill: **BLOCKED** (not started; no V5 root created)

Three independent blockers, all confirmed on `sat`:

1. **No single-arm path.** Live probe: a BASELINE-only adapter →
   `policy arm order/coverage is not the fixed four-arm order`
   (`physical_runner.py:1044`); an `arms=("BASELINE",)` plan → the same for plans
   (`:688`); a 500-world plan → `plan must contain exactly 9000 worlds` (`:694`);
   `FixedPolicyEvaluationRunner.__init__:1439/1454` re-checks four arms.
2. **Four-arm cost exceeds the 90-min cap.** V4 `timing-100.json`: 4235.1 s / 100
   ep = **42.35 s/ep** (BASELINE alone 1.657 s/ep). The 100→500 leg alone
   ≈ **282 min**; the full drill (→100, +150, SIGKILL, resume →500) ≈ **7.6 h**.
3. **The V4 driver no longer constructs under pass-2 code:**
   - **(b) producer↔consumer:** M4 made `runtime_admission` mandatory and
     file-backed (`physical_runner.py:1050-1052`) and `admission_mapping`
     mandatory for real adapters (`:1447-1457`). `.tmp/run_stage_c_rehearsal.py`
     supplies neither, so a copy cannot run without a sealed admission (which
     needs stage-A + stage-B PASS receipts).
   - **(a) sync gap:** V4's learned fixtures fail authentication —
     `ee_axis_two_route_model.py:388` `unsupported two-route checkpoint schema`
     → `physical_runner.py:593`. Commit `dd2468e` added `formal` to the required
     key set; fixture builder `.tmp/build_fresh_two_route_checkpoints.py`
     (14:43 UTC) predates it, so the three `.pt` files lack exactly that key.

To unblock: rebuild fixtures with `formal`, mint a non-formal sealed runtime
admission, then either accept a ≈7.6 h four-arm drill or authorise a
rehearsal-only single-arm seam (a code change → science-lane question). Probes at
`sat:…/shadow/.tmp/v5_singlearm_probe.py`, `v5_probe2.py`.

## Part 3 — figure smoke: PASS

`rungs/` + `checkpoints/` of the V4 root rsynced to `/tmp/v4-rehearsal-root/`.
`--help` clean. Render with `--allow-nonformal` into an absent `/tmp/v4-figures/`:
**exit 0**, `{"figures": 6}` — `root-01-{ee,service,paired}.{png,pdf}` + manifest.
Watermark **present** both in the manifest (`nonformal_watermark = "REHEARSAL —
NOT A RESULT"`) and visibly rendered diagonally across the PNG, over the footer
"Development-only disclosure; no held-out use or scientific claim".
`FIGURE-MANIFEST.json` sha256
`3c058665c46862d4da2232c3686bf0232aa83c7ee1558826869cfd8509f35ed9`
(`code_sha256 = e12b70fe…`, `receipt_count = 400`, four arms). Without
`--allow-nonformal` it refuses (`FIGURE_PIPELINE_REFUSED`, exit 2, no output dir).
One rung only, so each curve is one point; no EE values interpreted.

Wall times: pytest 51.4 s; `--check` ~2 s; dry-run ~4 s; V5 probes ~40 s;
render ~6 s.
