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

Pattern: defects found by launching cost 40 min–22 h each; the same classes found by offline probes, import smokes and read-only audits cost 30 s–8 min. Every new defect is appended here with the same five columns.
