# Engineering lane — stage-C fix-pass verification (2026-09-07)

## 1. Codex claims (`codex-sol-stagec-fixpass-final.md`)

| id | claimed | anchor (all resolve) |
|---|---|---|
| B1 | SKIPPED — launch-bundle authority, separately owned | — |
| B2 | FIXED | runner.py:1287, 1495, 1579, 1708 |
| M1 | FIXED | runner.py:1322, 1421, 1467 |
| M2 | FIXED | runner.py:295, 354, 1151; diagnostic.py:105 |
| M3 | FIXED | renderer.py:246, 268, 500 |
| M4 | FIXED | renderer.py:129, 167, 346, 446 |
| M5 | FIXED | renderer.py:696 |
| M6 | FIXED | runner.py:56 |
| M7 | FIXED | runner.py:1063; test_world_plan_and_bindings.py:250 |
| m1 | FIXED | renderer.py:631, 657 |

All eight changed-file SHA-256 match codex's list byte-for-byte.

## 2. Tests

`pytest -q` over physical-evaluation + ch5-figure-pipeline + engineering-lane + baseline-adapter:
**64 passed, exit 0**, no failures (29 / 12 / 11 / 12 per package). No traceback to report.

## 3. Static spot-checks

**B2 — PASS.** `runner.py:1367-1372` refuses boundary 9000 without a continuation-authority *file*;
`_authenticate_continuation_authority` (:1287) reads it through `_read_sealed_json` (:258), which requires
the file bytes to hash to the caller-bound digest **and** a matching `.sha256` sidecar, then binds
`plan_sha256`, `policy_bindings_sha256` and `held_terminal_token_sha256` (:1300-1309), the 3000 result and
checkpoint digests (:1310-1311) and an `owner_notification` whose `status == OWNER_NOTIFIED` and whose bytes
are verified by `_bound_file` (:1312-1315). A SHA-shaped string alone is refused —
`test_cadence_resume.py:179` (`sealed continuation authority file`); a forged authority is refused at
`:270-279`. `:1495-1517` re-checks the preserved HELD 3000 result against the authority. The plain
3000 `result.json` no longer blocks continuation: `:1591` only refuses it when `terminal_boundary != 9000`,
and the 9000 run writes a separate `continuation-result.json` (:1708).

**Figures — PASS.** `test_render_v023_development_curves.py:29-55` builds roots from the real
`adapter.run_episode` plus `evaluation._checkpoint_payload` / `_rung_payload` and `runner._write_once` —
no hand-shaped stub. `test:230` compares `figures._pool` bit-for-bit with `runner.pool_receipts`.
`renderer.py:317-335` recomputes EE as ratio-of-sums from additive `total_bits`/`total_energy_j` (:329).

**Parity — PASS.** Single import site `runner.py:56 from ee_axis_two_route_model import deploy_q12_action`,
used at `:949`; the diagnostic imports the same module object (`diagnostic.py:21`) and runs only through
`runner.FixedPolicyEpisodeAdapter` (:163, :176), asserting `binding()["routes"] == []` at `:200`.
`FrozenBaselinePolicy` forces `routes = ()` / `[]` (`runner.py:468-473, 500`); `pool_receipts:829` likewise.

## 4. Stage-C bundle

`--write` → `--check`: **STAGEC_CODE_MANIFEST_CURRENT entries=259
sha256=62180dbd98709a90e740405ed92f3b28b8f2dfc937f1e65746ca62ae3b2f5deb`
(was `bb68f84b…c066a5`); pin file agrees. **0 of the 246 closure paths missing** from the 262-line
`V023-C1C2-SUCCESSOR-STAGEC-SYNC-LIST.txt` (sync list itself unchanged). Bundle pytest:
**10 passed, 1 skipped** (skip = post-fix adapter already present, `test_…launch.py:256`).

`--dry-run`: **exit 0, no refusal** — it prints the six remote commands and returns. Deviation from the
step-4 expectation: the stage-A output root is never probed locally. Running step 3 directly gives the
fail-closed line: `STAGEC_BIND_ERROR: sealed Stage-A output root is unavailable` (exit 2, nothing written).
The prior report's line-39 defect is fixed — with `V023_STAGEC_PYTHON` unset the dry-run now exits 0.

## 5. Commit and shadow sync

`cdf2dd5f8f7bccc7824fe9155c5687a0c84d3e5f` — 10 files, +1156/−136. Rsynced to
`/home/sat/mcrl-v023-successor-shadow-20260907/.scratch/`; all three trees verified digest-identical
(`__pycache__` excluded).
