# Engineering lane — stage-A fix passes 8+9 commit report

**Committed: `e8f4cc57b44efc6994f833bd8ed46f01bfaf58b3`.** The blocker in fix-pass-8's report
(addendum sidecar absent from the stage-C manifest) is closed; the four-package suite is green.

## 1. Gates

- Four-package pytest: **90 passed, 0 failed, 0 errors, 309.44 s** (exit 0). Fix pass 8 saw
  89 collected / 73 passed / 5 failed / 11 errors, all on the one missing manifest row; the
  count is now 90 because fix pass 9 adds the non-formal replay test.
- `build_v023_c1c2_successor_launch_manifest.py --check` → exit 0,
  `SUCCESSOR_LAUNCH_MANIFEST_CURRENT sha256=c77e27328150c002bd318cd96781ca10a094aa16a8bcff91933845d192a33a6d`.
  Payload groups: 246 closure + 14 additions + 23 stage-C members = **283**.
- `build_v023_c1c2_successor_stagec_manifest.py --check` → exit 0,
  `STAGEC_CODE_MANIFEST_CURRENT entries=270 sha256=f2f3adca875af4ebacb88fb509f58f506e27fd66288dd73cbf76187726a7581f`.
  **No DRIFT**, run both before and after the suite; stage-C fix pass 4 had not yet touched a
  manifest member. No `--write` was run.

## 2. Spot-checks

- Sidecar is a member row: `V023-C1C2-SUCCESSOR-STAGEC-CODE-MANIFEST.sha256:46`
  (`7738bfc9…  …ADDENDUM-2026-09-07.md.sha256`), addendum at `:45` (`9673928f…`); emitted by
  `build_v023_c1c2_successor_stagec_manifest.py:49`; consumed at `successor_launch_common.py:486-496`;
  live pin equals the manifest digest.
- `--replay-arms --nonformal`: tokens at `verify_v023_c1c2_successor.py:38-39`, selected at
  `:623-625`; receipt `"formal": not nonformal` at `:630` and `:658-659`; CLI at `:1050`, `:1064`;
  sibling `write_once` receipt at `:410-422`. Torch single-thread is scoped `:501-502` → `finally :589-590`.
- Formal path unchanged: AST diff vs HEAD shows 7 functions added, 0 removed, only `main` changed —
  `verify_output`/`decision_for_output` byte-identical. `main` now defaults the previously required
  paths (relaxation only; explicit flags behave as before).
- Eight codex-declared SHA-256 values all matched live files before staging.

## 3. Commit and shadow

Staged: the four stage-A directories (only `…successor-launch` had changes, 8 files) plus the four
named stage-C files and `test_v023_c1c2_successor_stagec_launch.py` (diff is exactly the
sidecar-member assertion, `:652-657`). 13 files, +644/−23.

rsync local → shadow: 8 files transferred, other three packages already identical; all 8 digests
verified identical server-side.
