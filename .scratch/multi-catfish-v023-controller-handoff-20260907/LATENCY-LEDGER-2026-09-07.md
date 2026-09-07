# Latency ledger — defects, where they lived, how found, what they cost (from 2026-09-07)

| when (UTC) | layer | defect | how found | cost |
|---|---|---|---|---|
| 09-06 15:10→09-07 12:54 | R7 final verifier | 6 verifier-vs-writer defects (digest domain, sibling import, broadcast, pair keys, c2_diagnostic type, float32 delta) | serial repair runs R1→R4 (40 min each) + offline inventory (last 3 in minutes) | ~22 h to decision |
| 09-07 06:1x | C1/C2 r4 | scope literal mismatch (wrapper vs producer) | server launch failure | ~40 min |
| 09-07 09:06 | C1/C2 r5 | `.rows` on dict at generator:1315 | 16-shard run failed after benchmarks | ~3 h server + 62 min unnoticed |
| 09-07 11:32 | C1/C2 r6 | controller claim-ceiling literal | run FAILED after 1 shard complete | ~95 min × 15 shards lost |
| 09-07 11:40 | C1/C2 consumer | q2_state action-major vs feature-major; H_t alignment (47 substeps); sealer literal; adapter merged-receipt fields | offline probes on real shard rows | ~1 min each to find |
| 09-07 12:32 | C1/C2 r7 | test fixture outside sync list; dir name containing `r5` rejected by preflight | launcher failed pre-compute | ~5 min |
| 09-07 14:12 | successor shadow checkout | heterogeneous-trainer package not in sync list (import by path) | server import smoke | 30 s |
| 09-07 14:14 | successor shadow checkout | producer code-closure hashes neutral-materialization file not synced | server pytest | 2 min |
| 09-07 14:15 | F1 dry-run | PREREG artifact not synced | server dry-run | 1 min |
| 09-07 14:25 | V1 rehearsal | provider rejects symlinked shard dirs (root is a symlink farm) | first rehearsal run | 8 min incl. fix |
| 09-07 14:18 | factory v3 + two-route runner | 8 formal-admission/integrity blockers | one consolidated read-only audit | found before any launch; fix in progress |
| 09-07 14:37 | V1 rehearsal (attempt 2) | provider requires per-shard `COMPLETE`; producer seals only the merged root (per-shard evidence = receipt + manifest + controller status file) | second rehearsal run | ~10 min to find; fix running on server codex, validated against the real shard root |
| 09-07 14:49 | server codex workspace (blocker fix) | producer code closure hashes `r6-fit-binding-fix/v023_lcsrs_source_adapter.py`, absent from the partial workspace → 15 test setup errors | server pytest | ~0 min lost (fix itself complete); tests rerun locally |
| 09-07 14:44 | V3 stage-B rehearsal | frozen baseline adapter rejects `UserState.contract_fields` that the live env now always populates → BASELINE cannot be evaluated (class (b)); learned-arm plumbing clean | first stage-B rehearsal with fresh models | ~20 min to find; fix on server codex with encoding-invariance test |
| 09-07 14:44 | V3 stage-B rehearsal | baseline artifacts `artifacts/training-2026-08-25-rerun01/main/` absent on server (closure gap) | same run | 2 min (synced) |
| 09-07 14:52 | controller ops | r8 shard completion files are `.terminal.json`, shadow verifier watched `.complete.json`; pkill self-match killed the ssh shell twice | monitor review | ~15 min of controller time; no run impact |
| 09-07 15:0x | heterogeneous-trainer tests | 3 stale tests build a plain `EEAxisPairBatch` for C2 while `update_c2` correctly requires `EEAxisV014NormalizedPairBatch` (pre-448 test debt) | server + local pytest via the closure agent | fix (tests only) dispatched; module untouched |
| 09-07 15:40 | successor dependents | hardened factory/runner contracts (formal seed at construction, `model_config_sha256` required) broke the rehearsal trainer and the stage-B/C gate | local full-tree pytest after pull-back | ~5 min to find; alignment dispatched; astra asked whether the seed check sits at the right layer |
| 09-07 15:08 | V1 rehearsal (attempt 3, in workspace) | r5 shards' receipt code closure drifted from the live producer closure → correctly rejected by controller validation; only r8 shards are valid inputs | server codex real-shard probe | ~0 min lost (discovery); V1 retargeted to r8 shards |
| 09-07 15:14 | stage-A launch bundle | 6 BLOCKERs + 1 MAJOR incl. a verifier bypass (`--no-reconstruct` PASS on non-formal root) and 179/246 sync paths missing | astra read-only re-audit before any launch | found in ~25 min of audit; fix pass 2 dispatched |
| 09-07 15:14 | F1 kill screen (F0 seam) | F0 cost-share conservation assertion fails on the first REAL BASE profile (18 synthetic-fixture tests were green) | first F1 run, 36 s | ~30 min incl. authority; diagnosed in ~20 min as pure roundoff (bitwise equality bypassing F0's own tolerance); minimal repair + real-profile regression; replay pending |
| 09-07 18:05 | stage-C launch bundle | manifest builder fell back to a 42-file list when the closure list was absent on the server workspace → 189/246 sync paths missing; `--dry-run` executes the remote python; unsigned owner marker | operator pull-back conformance check | ~15 min; fix dispatched |
| 09-07 16:05 | stage-A formal chain (V2-synthetic) | orchestrator identity field set hard-coded (18 vs factory's 22) → abort at update 0 with green preflight; `C3` token scan hits legitimate donor filenames; binder non-idempotent git-dirty; closure-list ordering | one end-to-end synthetic run (~20 min) | fix pass 3 dispatched; would have cost a formal launch |
| 09-07 16:35 | controller process | F1 test fix overwritten by a concurrent server→local rsync from another agent (two writers, one path) | operator re-verification before replay | ~15 min; fix re-applied; charter rule 12 |

Pattern: defects found by launching cost 40 min–22 h each; the same classes found by offline probes, import smokes and read-only audits cost 30 s–8 min. Every new defect is appended here with the same five columns.
