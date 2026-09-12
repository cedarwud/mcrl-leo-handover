# PROGRESS-E — lane E (S1 engineering: port + manifest + review brief), MC2 round

Worktree `/home/u24/papers/mcrl-leo-handover-mc2-s1`, branch `mc2/s1-port-20260912`, base
`67e175bd` (MC2 contract r0), merged with lane A's mechanism commit `11466998`.
Hard rules honoured throughout: no S1 launch, no sat compute, no formal / calibration / CONFIRM /
S1-TRAIN seed stepped, lane A's worktree never touched, named-path commits only.

## State: BOTH PHASES DONE. Waiting on controller decisions, not on engineering.

| deliverable | state |
|---|---|
| `S1-MC2-PORT.md` | done — ported files, the 9 shared-file hunks, merge resolution, tests, preflight receipts |
| `S1-MC2-MANIFEST-PLAN.md` | done — the matrix (parameterised by the frozen mechanism id), the 8-worker schedule, the draft reading rules, the open items |
| `S1-MC2-REVIEW-BRIEF.md` | done — 13 checks, placeholders for the final commit / manifest / rules hashes |
| `PROGRESS-E.md` | this file |

## Commits (read back from git)

- `4611f68f` — phase 1: the accepted S1 harness on the MC2 lineage, the lane as a subclass.
- `004e1c50` — phase 2: merge of `11466998` + the judge cells wired into the S1 matrix.
- `46682219` — phase 2b: the cell-position-out-of-the-identity fix found by the manifest dry run.

## Phase log

- **Phase 1.** Read the contract (r0 → r2 during the work), the accepted harness, the acceptance
  record, the preflight, Amendments 12/13, lane M's k8 code and lane A's in-flight diff. Created the
  worktree. Ported the harness with the S1 lane as `S1DevSettings` / `S1Trainer` subclasses in two
  new modules so that `DevSettings` gains no field and no development configuration hash moves.
  Declared `S1-NULL-MC2 = (9_263_000, k)`. 23 tests green, 17 mutants red, 67 development tests
  green. DEV-seed preflight of `D3-XEP`, `D3-T0` (+resume) and `MODQN-eq16` through the formal
  driver, with an independent RNG audit. Committed `4611f68f`.
- **Phase 2.** Lane A committed `11466998` (both judge rules). Merged: **one** conflict (two lanes
  adding an import on the same line of `cf_dev.py`), resolved by keeping both. Corrected the port to
  lane A's final API: judge cells carry `DevSettings.mechanism = "MC2"`, the rule lives in
  `JudgeSpec.mechanism_id`, and **`B-only` carries the rule-independent `MC2-B-ONLY-SHARED-v1`** so
  its hash does not depend on which version is frozen. Three further hunks: the lane-aware B-null key
  in `JudgeSpec`, the lane guard on the judge's null stream in the trainer, and naming the new
  namespace in the development forbidden list. All suites green (mine, lane A's, lane M's, the
  development ones); judge cells construct on S1 seeds under both versions; judge cells preflighted
  on DEV seeds (`FULL`, `B-null`, `B-only`, `A-only-v2`).

## Preflight budget

**14 development episodes of the ≤ 20 allowance** (6 phase 1 + 6 v1 judge + 2 v2), plus 25
construct-only builds that step nothing. No formal, calibration, CONFIRM, S1-TRAIN, S1-NULL or
S1-NULL-MC2 value was ever constructed — audited by an RNG spy independent of the harness's guards.

## What would block an immediate S1 launch (none of it is engineering)

1. The **DEV screen** must pass (lane A's ep-100 selection, then ep-300 survival on fresh seeds).
2. The controller must freeze **which mechanism id** runs — the matrix, and whether `A-only-v2`
   exists at all, follow from it.
3. The controller must decide the **optional cells** (`D3-null`, `D3-XEP`, both, neither).
4. The controller must freeze the **reading rules** as a document; `s1_manifest.py` /
   `s1_launch.py` refuse a formal manifest without its digest.
5. The **fresh-context review** must return 0 INVALIDATES and 0 BIASES on the frozen manifest.
6. The tree must be **synced to sat** (it never has been by this lane) and the frozen MODQN
   checkpoint's sha256 re-verified there.

## Next step if resumed

Nothing is pending in this lane. If lane A commits a **further** mechanism change (a fix, or v2
changes), re-merge it, re-run `pytest tests/test_s1_harness.py tests/test_mc2_judge.py
tests/test_cf_dev.py tests/test_cf_multid3.py tests/test_cf_tnext.py` plus
`bash scripts/s1_mutants.sh`, and re-run the judge construct-only sweep. The tripwire for an
accidental identity change is `test_the_s1_port_changed_no_development_identity`, whose goldens are
baselined at `6136c514`.
