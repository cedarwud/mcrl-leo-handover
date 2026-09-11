# CF3REVIEW progress

Read-only code review of CF3 pilot trainer (worktree /home/u24/papers/mcrl-leo-handover-cf3, branch cf3/pilot-20260911, base 363845e8).
Output: CF3-CODE-REVIEW-2026-09-11.md (this dir).
Reviewed commit: worktree HEAD ca678414 (training code == deployed e8a04ccf; only scripts/cf3_report.py differs).

## Steps (idempotent)
- [x] 1. Read declaration, amendment 1, amendment 2, addendum (incl. A-G additions), cf3-pilot PROGRESS
- [x] 2. Read cf_ratio.py, cf_sources.py, run_cf3_pilot.py, cf3_common.py, cf3_eval.py, cf3_premeasure.py, cf3_report.py, tests; MODQN update/train/state
- [x] 3. Check items 1-10
- [x] 4. Run test suite with worktree .venv: 15/15 pass
- [x] 6. Review written: CF3-CODE-REVIEW-2026-09-11.md (DONE)
- probe result: E term flips 0/240 myopic argmaxes; per-user vs system argmax differ 43%
- [x] 5. Compare deployed commit vs worktree HEAD: sat tree COMMIT=e8a04ccf; sha256 of cf_ratio/cf_sources/cf3_common/cf3_eval/run_cf3_pilot/modqn identical to worktree; only cf3_report.py differs (HEAD ca678414 newer)
- [ ] 6. Write review

## Coordinator note (received mid-task)
Known, assigned items (confirm/refute one line each): learning-check off-by-one; DECISION.json race; fingerprint lacks commit/hash; no process-level resume test; launcher PID reuse; 5 GB margin. Focus on training math & fairness.

## Log
- 2026-09-11 start
- verified: B sum exact (rate already 0 for unserved), E share, H inter; ReplayBuffer.sample casts rewards float32 (harmless)
- candidate findings being checked: eval uses TRAIN split sampler; report A0 3 seeds vs 5; source env stream lockstep
- tests: 15/15 pass at ca678414 (local .venv, pinned local archive, no skips)
- sat fingerprints read (config only, no metrics): A0 gamma 0.9 eq16; A1-A3 gamma 1.0 shared; lr/batch/eps/target identical; lambda0 0, dual_ascent False; same calib sha, tle sha
- FINDING: deployed cf3_report.py (e8a04ccf) is pre-Amendment-2 (branch 1 needs C-H; seeds 0-2 only; stale c2_activation/INACTIVE). HEAD ca678414 version fixed.
- caveats: diag100 term share is level share not decision share; equal-share E gives 1/U credit (probe running: scratchpad/probe_contrast.py, task budbulzxj)
