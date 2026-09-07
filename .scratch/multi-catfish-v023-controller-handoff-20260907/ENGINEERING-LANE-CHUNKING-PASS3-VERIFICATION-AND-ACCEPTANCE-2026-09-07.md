# Engineering lane — stage-C chunking fix pass 3 verification + acceptance attempt (2026-09-07 ~22:00 UTC)

Ceiling `ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. NON-FORMAL; no scientific token, no EE interpreted.
Classes: **(a)** contract/closure, **(b)** test gap, **(c)** implementation defect, **(d)** procedural.

## Part 1 — verification and commit

**(a) Per work-list item.** All 9 changed files match codex's SHA-256 list (9/9 OK).

| item | status | evidence |
|---|---|---|
| asymmetric provenance strip | **FIXED** | one constant `stagec_common.py:58-75` (16 fields), consumed by `accept_stage_c_chunk_equivalence.py:23,267`, `build_stage_c_chunk_acceptance_bundle.py:32`, `stagec_common.py:508`. `_assert_equivalent` strips **both** sides (`accept_…py:75-79`); merged checkpoint/rung/resume-state compares now route through it (`:206,238,243,248`) |
| 2×50 rehearsal merge boundaries | **FIXED** | non-formal merge restricted to `(0,50),(50,100)` `runner.py:1984-1991`; artifact boundaries `(50,100)` `:2092-2096`; per-episode resume states `:2076-2079`. Cadence gate `accept_…py:105-111`. `test_cadence_resume.py:585-590` now asserts merged 50/100 checkpoints **and** rungs exist |
| zero coverage of the two scripts | **FIXED** | `test_v023_c1c2_successor_stagec_launch.py:191-317` imports both and runs `accept()` end to end: formal 200 vs 2×100 PASS for all four arms (`:262-268`); mutated merged rung FAILs at `rungs[100].pooled.total_bits` (`:270-287`); non-formal 100 vs 2×50 PASS with `formal:false`, `rehearsal_chunk==50` (`:289-296`); formal bundle authenticates via `authenticate_launch` (`:298-312`); rehearsal bundle refused (`:314-317`). Real `build_chunk_boundary_states`/`run_arm_chunk`/`merge_arm_chunks`/`pool_receipts`/`EpisodeReceipt`; only episode physics is a deterministic synthetic producer (`:56-143`) |

**Seven-token addendum check: 6/7.** Missing token is the new acceptance digest `b6d6ab8b…`; the controller-owned
addendum still carries `6d3785ef…` (line 61) and has **no `.sha256` sidecar**. Class (d), controller-owned.

**`ACCEPTANCE-SERVER-EQUIVALENCE.md` changed.** CURRENT sha256:
`b6d6ab8baa07011d3d72ea6b54efa9f25d6f666ca47c837af75cc359c10b17ff` (previous `6d3785ef…`).

**(b) Tests.** Mandated command: **91 passed, 1 skipped in 126.93 s**, exit 0. No failures, no tracebacks. Skip =
`test_baseline_dependency_fails_closed_until_postfix_assertion_exists` (`…launch.py:678`). Pass 2 was 90+1; the new test is the
end-to-end `accept()` case. (Codex reported "77 passed" — fewer paths; non-blocking.)

**(c) Closure.** `--check` → `STAGEC_CODE_MANIFEST_CURRENT entries=269 sha256=a3b5c6bc7c75882c5c2d0c9318593bbedf9094960c0b1f5ce955ccf5cb81c96b`,
exit 0, no drift, no `--write`. Closure list 246 paths, **0 missing** from the 272-line sync list, 246/246 present on disk.

**(d) Spot-checks — all hold.** The single exclusion constant equals the addendum §2 list and the mandated 16-field
list **exactly and in order** (verified by parsing both). Strip is symmetric. Non-formal receipts carry
`formal:false, rehearsal_chunk:50` (`accept_…py:255-256`) and are refused as launch evidence by
`verify_acceptance_bundle` (`stagec_common.py:472-521`: `formal is True`, `episodes==200`, `chunks==[[1,100],[101,200]]`,
`rehearsal_chunk is None`); the bundle builder additionally refuses mode/shape drift and mixed modes (`build_…py:44-61`).

**(e) Commit.** Already present as **`e8cd55b332e01aa16fc3bec92ae58a1b585754c7`** with the exact mandated message and
`Co-Authored-By: Claude Fable 5.1`, 9 files; `git status --porcelain` for the four packages is empty, so nothing to add.
Rsync local → shadow re-run for all four directories (`--exclude __pycache__`): **zero transfers** (already current);
digests verified equal on both sides.

## Part 2 — server acceptance: **NOT RUN, blocked**

**No episode was executed.** Root `/home/sat/mcrl-v023-stageC-CHUNK-ACCEPTANCE-NONFORMAL-20260907T215059Z`; checkout
reused `…-20260907T210729Z-checkout` (HEAD `a179dea`, clean, pass-3 code byte-identical to local). Doc preconditions:
`.git` present; manifest `--check` in the checkout = same `269 / a3b5c6bc…`; `$BINDINGS`, `$SUPPLEMENT`, `$RUNTIME` **absent**.

Three-layer fail-closed evidence (all exit 2, nothing written):
1. binder → `STAGEC_BIND_ERROR: digest sidecar is missing: …SCHEDULING-ADDENDUM-2026-09-07.md.sha256`;
2. `accept_…py`, both formal and `--episodes 100 --chunks 2 --non-formal` →
   `STOP_PHYSICAL_EVALUATION_INTEGRITY: execution bindings is missing: …`;
3. **structural (a)/(d): there is no non-formal admission path.** `accept():88-100` verifies bindings → Stage-A/B
   supplement → runtime identity → runtime admission *before* the cadence branch at `:105`; `build_stage_ab_supplement`
   (`bind_…py:265-291`) requires a sealed Stage-A root deciding `PASS_SOURCE_TRAINING_INTEGRITY` plus a Stage-B gate
   `PASS_PLUMBING_INTEGRITY` with `formal:true`; and `FixedPolicyEpisodeAdapter.__init__` (`runner.py:1106-1131`)
   refuses **any** episode without a sealed runtime-admission file carrying both PASS statuses. A server-wide search
   found **zero** `PASS_SOURCE_TRAINING_INTEGRITY` artifacts; the only `PASS_PLUMBING_INTEGRITY` lives in the
   off-limits `codex-ws-*` workspace. Manufacturing either is fabrication and was not done. The earlier acceptance ran only via
   `--early-baseline-admission`, removed in pass 2.

**Substitute evidence produced on the server** (non-formal, no fabricated artifact):
- shipped end-to-end `accept()` test + non-formal cadence test in the pass-3 checkout: **3 passed in 9.89 s**,
  wall 0:10.16, peak RSS 656 MB. A prior two-file run gave 40 passed / 1 failed / 1 skipped in 29.6 s; the failure was
  `test_dry_run_…` asserting `<checkout>/.venv/bin/python`, absent in a throwaway checkout — class (d) environment,
  PASS after symlinking the venv.
- fresh two-route exports rebuilt through the **current** writer: FULL2 `223cb81b…`, DROP_C1 `aa815dd1…`,
  DROP_C2 `8173bfc1…` (wall 1.21 s, RSS 773 MB); all three load through `load_learned_two_route_checkpoint` and
  BASELINE through `load_baseline_policy` (wall 1.44 s, RSS 782 MB).
- **Schema clarification:** `v023_two_route_source_training_runner.py:57` `CHECKPOINT_SCHEMA=…-checkpoint-v1.1` names
  the runner's own *resume* checkpoint. The arm export Stage-C consumes carries `…-two-route-checkpoint-v1`
  (`ee_axis_two_route_model.py:354`, written at `…source_training_runner.py:1049`) — exactly
  `runner.TWO_ROUTE_CHECKPOINT_SCHEMA`, and the same token real Stage-A exports carry. **No v1.1 mismatch exists.**

Peak RSS across all my server processes < 1 GB (cap 6 GB); `OMP_NUM_THREADS=1`; `oom_score_adj` set. No `*r8*`,
`*lcsrs-gate*`, `*-r7-*`, `codex-ws-*`, `c3-contingency-f1-*` or sealed root was read or written.

**Controller actions:** (1) amend addendum §2 to `b6d6ab8b…` and write the `.sha256` sidecar; (2) Stage A then Stage B
must actually PASS before any acceptance run — by design there is no engineering bypass at any of the three layers.
