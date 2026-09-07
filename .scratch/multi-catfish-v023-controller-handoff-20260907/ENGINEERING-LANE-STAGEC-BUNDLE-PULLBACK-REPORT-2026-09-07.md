# Engineering lane — stage-C launch bundle pullback (2026-09-07)

## 1. Server workspace state

`/home/sat/mcrl-v023-codex-ws-stagec-20260907` @ `main` `4394f27`.
`git status --porcelain` = exactly one line, `?? .scratch/multi-catfish-v023-c1c2-successor-stagec-launch/`;
`git diff --stat` empty. `.tmp` present but untracked/ignored. No tracked file touched.

Codex final message (`/home/sat/codex-sol-stagec-launch-final.md`): 14 files with SHA-256; test command
under `.venv`; result `9 passed in 1.94s`; manifest check "70 authenticated entries"; `TASK_EXIT=DONE`.
Self-declared open conditions: bindings JSON not generated (no sealed stage-A), baseline adapter lacked the
post-fix assertion, **shadow closure list absent so the manifest builder used its 42-file runtime fallback**.

## 2. Pullback

rsync'd only that directory (`--exclude __pycache__ --exclude .tmp`). Local `git status --porcelain` on the
path = one `??` line. All 14 SHA-256 match the claimed list byte-for-byte.

## 3. Local execution

- pytest: **8 passed, 1 skipped**, no failures. Skip = `test_..._baseline_dependency_fails_closed...`
  (`test_v023_c1c2_successor_stagec_launch.py:198`, "workspace already contains the required post-fix adapter") —
  the local adapter *is* post-fix, so the negative cannot fire here. Server's 9/9 is the same suite with that
  branch taken.
- `sync_launch_..._server.sh --dry-run` as-invoked → `line 39: /home/sat/mcrl-leo-handover/.venv/bin/python:
  No such file or directory`, exit 127. **Defect:** line 35 exempts `$python_bin` executability under `--dry-run`,
  but line 39 still executes it. With `V023_STAGEC_PYTHON` set to the local venv the exact refusal line is:

  `STAGEC_CODE_MANIFEST_DRIFTED` (exit 3)

  It fails closed at line 39, *before* any ssh/rsync — not on the stage-A root, which is only probed remotely (line 71).
- `bind_..._freeze.py --help` exits 0; requires `--stage-a-output/--plan-output/--stage-b-output/--stage-c-output`.

## 4. Conformance (contract §5/§6/§9, stage-C audit)

- **(a) PASS — audit B1 cleared.** No `DEFERRED` anywhere. Runner + verifier are hashed into the bindings at
  freeze: `build_..._manifest.py:64` puts every bundle file in the closure; `bind_...freeze.py:195-196,225`
  emits `code.stagec_bundle`; `bind_...freeze.py:173` (`verify_code_manifest`) runs before any computation, and
  `:170`/`:172` require both output roots absent.
- **(b) PASS — audit B2 cleared.** `run_..._stage_c.py:220-223` demands authority + owner marker + 3000 checkpoint;
  `:131-133` requires the preserved `HELD` 3000 `result.json`; `:136-143` cross-authenticates authority SHA,
  bindings SHA and plan SHA against the owner marker; `:194-197` writes `continuation-009000.json` with
  `scientific_result_remains` / `new_scientific_token_emitted: false`, so 3000 is never suppressed.
  *Residual:* the owner marker is unsigned, so one actor can author both files.
- **(c) PASS.** `verify_...stagec.py:30-35` rejects `REHEARSAL-NONFORMAL` in root path and receipt names;
  `:40-41` rejects `formal: false`; `:42` rejects the token inside receipt JSON.
- **(d) PASS.** `stagec_common.py:33` `ARMS = ("FULL2","DROP_C1","DROP_C2","BASELINE")`; `:31` `PLAN_SHA256 = 866d28e0…5e01bb`;
  enforced at `stagec_common.py:267,269`, `preflight_...py:92-93`, `bind_...freeze.py:186-187`, `verify_...py:170`.
- **(e) PASS.** `preflight_...py:22-35` `_reject_circular_digest` rejects `self_sha256`/`bindings_sha256`/
  `execution_bindings_sha256` keys and any value equal to the bindings digest; called at `:91`.
- **(f) FAIL as shipped, correct in logic.** `build_..._manifest.py:67-77` reads the 246-path closure list and
  only falls back to the 42-file tuple when absent. Shipped artifacts were built server-side without it:
  manifest 70 entries, sync list 73 → **189 of 246 closure paths missing** (100 under `src/mcrl/runtime`,
  14 target-generation-launch, 10 `src/mcrl/algorithms`, …). Rebuilding locally yields 259 entries with
  **0 of 246 missing**. `--check` catches this (exit 3) before sync, so it is fail-closed, not silent.
  Note `stagec_common.py:176-195` verifies only *listed* members, so completeness rests solely on launcher line 39.

## 5. Shadow sync

Bundle rsync'd to `/home/sat/mcrl-v023-successor-shadow-20260907/.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/`
(14 files, digest-of-digests `3fab7ebeb4949cc3c0682980615e31f2a4b4e4a52df582c68fd45a0197a7b781`).

**Blocking before launch:** rebuild the manifest/pin/sync list on a tree carrying the closure list (`--write`),
and guard launcher line 39 under `--dry-run`.
