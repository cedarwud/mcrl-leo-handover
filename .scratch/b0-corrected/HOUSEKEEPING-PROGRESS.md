# B0 branch housekeeping audit — progress log (Q8 part 2)

Task: content-equivalence audit of 4 commits unique to b0/corrected-baseline-20260911
vs HEAD (wip/multi-catfish-v023-20260907), archive tag, conditional worktree removal.
No science in this task — pure git housekeeping.

Commits under audit (b0 branch, not in HEAD ancestry):
- 832471ca (B0 D-2)
- 0acd146c (B0 D-3)
- 923d68b0 (B0 pilot: resumable driver + catfish-surface EE harness)
- ccbbb048 (D-3 fixup) -- branch tip

Candidate main-line SHAs the porting record claims carry the same content:
363845e8, db30b334, b50cd087 (to be verified, from .scratch/b0-corrected/PROGRESS.md
and B0-CORRECTED-BASELINE-2026-09-11.md)

## Status: DONE (2026-09-11)

- Found via PROGRESS.md: cherry-picks are 832471ca->ee0ffa60, 0acd146c->698f20d8,
  ccbbb048->6939fc78, 923d68b0->ff01f84d (all `-x`, all confirmed ancestors of HEAD).
  db30b334/b50cd087 (the task brief's other examples) turned out to be docs/registry
  commits ("round-2 report and final ledger", "Register CF3PILOT"), not porting commits
  -- noted in the audit file, not an error, just a red herring in the brief's examples.
- Per-commit content diff (git show <commit>:<path> vs git show HEAD:<path>, plus each
  commit's own hunk via git show <commit> -- <path>):
  - 832471ca (D-2 v1): PORTED-WITH-DIFFERENCES. step_types.py/trainer_env.py byte-identical;
    outage_gate.py's flat `-num_users` floor + test_b0_d2_outage_floor.py were rewritten by
    a LATER in-ancestry commit c00aca3e (controller ruling R4, per-step worst-served floor).
  - 0acd146c (D-3): PORTED-IDENTICAL. Every line it added (trainer_spec.py,
    training_pipeline.py, modqn.py, 3 test files) is byte-identical at HEAD; HEAD is only
    bigger due to unrelated later commits (57fb40b4 D-1 flag, b924c8a0 TLE pin) appended
    around it, never through it.
  - 923d68b0 (pilot driver + eval harness): PORTED-WITH-DIFFERENCES. Harness-core `run()`
    byte-identical; the arm loop was extended by a LATER in-ancestry commit 363845e8 to fix
    a real shared-env matched-conditions bug (_fresh_env/run_extended), plus
    --td-bootstrap-mode and TLE-pin fields from other rulings.
  - ccbbb048 (D-3 fixup): PORTED-IDENTICAL. Its print-block hunk and both test files are
    byte-identical at HEAD (HEAD adds one unrelated `out=` field next to it).
- git diff ccbbb048 HEAD --stat -- src scripts tests: 12 files, no deletions (confirmed via
  --diff-filter=D, empty). 7 are the four commits' own touched files (above); 5 are HEAD-only
  additions from OTHER named ancestor commits the four commits never touched
  (collapse_penalty.py new/f531ff99 PENALTYARM, trainer_config_validation.py/57fb40b4,
  test_b0_d1_scalarised_bootstrap.py/5219995a+57fb40b4, test_tle_archive_pin.py new/b924c8a0,
  test_w08_vanilla_td_target.py/5219995a+57fb40b4). None of these 5 are b0-branch content.
- Worktree confirmed clean (git status --porcelain empty) and unused (no matching process).
- Tag created: annotated `archive/b0-corrected-baseline-20260911` at ccbbb048
  (tag object a5230b4689af5a345b9041b4d71846a031e16fb8). Branch NOT deleted.
- Worktree removal bar ("every commit PORTED-IDENTICAL or differences confined to
  .scratch/docs") NOT met -- 832471ca and 923d68b0 both have real src/scripts/tests
  differences (see above), even though both are deliberate supersessions, not losses.
  Worktree /home/u24/papers/mcrl-leo-handover-b0 LEFT IN PLACE.
- Audit file written: B0-BRANCH-EQUIVALENCE-AUDIT-2026-09-11.md (this directory).
- Remaining: commit the audit file + this progress file only (named paths), trailer
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>.
