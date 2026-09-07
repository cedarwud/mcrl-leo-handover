# Engineering lane — stage-C chunking fix pass 2 verification (2026-09-08 ~03:30 UTC)

Claim ceiling: `ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. NON-FORMAL. No scientific token emitted.
Failure classes used below: **(a)** producer↔consumer contract/closure, **(b)** test/verification gap,
**(c)** implementation defect, **(d)** procedural/ownership deviation.

## Part 1 — verification and commit

**(a) Per audit id.** All 24 changed files match codex's SHA-256 list exactly (24/24 `OK`).

| id | verdict | evidence (file:line) |
|---|---|---|
| B1 | CONFIRMED | worker authenticates bindings→supplement→acceptance→runtime identity→policy→admission→TLE→sampler before any episode: `run_v023_c1c2_successor_stage_c_chunks.py:86-116`; launch gate `:43-82` |
| B2 | CONFIRMED | only the current interval is scheduled: `launch_stage_c_chunks.sh:63-67` (`previous`→`barrier`); previous cumulative barrier re-verified `:45-48` → `check_barrier` `run_..._chunks.py:169-206`; all four authorities mandatory `:27`, `check-launch` `:44` |
| B3 | CONFIRMED | `formal:false`/STOP/rehearsal/symlink rejected `verify_v023_c1c2_successor_stagec.py:38-61`; checkpoint cadence+identity `:713-729`; end state `:516-551,700-712`; merge indexed hashes + boundary continuity `v023_c1c2_successor_physical_runner.py:2004-2027` |
| B4 | CONFIRMED | append-only sealed supplement, Stage-B `PASS_PLUMBING_INTEGRITY` + Stage-A exports authenticated `stagec_common.py:485-514`; writer `bind_..._freeze.py:262-291` (`append_only_import: true`); four-arm publish re-authenticates `run_..._chunks.py:209-221` |
| M1 | CONFIRMED | exclusive non-blocking root lock `runner.py:282-297`, applied `:1948`; prefix resume replayed `:1749-1753`; final checkpoint written and re-read **before** `chunk-receipt.json` `:1826-1885,1934`; repair authority STOP/root/prefix-bound `:1622-1659` |
| M2 | CONFIRMED | parent identity `runner.py:1661-1677`; four-thread attestation, append-only attempts, original start preserved `:1756-1780,1892-1897` |
| M3 | CONFIRMED | shared `/tmp` flock allocator, cores−2−occupied, cross-arm/session `launch_stage_c_chunks.sh:73-85`; all four backends attested `stagec_common.py:243-256,289-301` |
| M4 | PARTIAL | real `ScenarioDriver`/`StepEnvironment`/`TrainerEnvironment` + bitwise binary64 `test_cadence_resume.py:622-726`; merged compare added `accept_stage_c_chunk_equivalence.py:170-201` — **but that path is defective, see Part 2** |
| m1 | **OPEN** | `V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-07.md` unchanged since `4cd39f1`, **no `.sha256` sidecar**, and 0/7 required §2 tokens present. Patch prepared at `SCHEDULING-ADDENDUM-SECTION2-CONTROLLER-PATCH.md:12-49`. Class (d) — controller-owned. README freeze order corrected (`README.md:26-60`); cosmetic: step 7 is skipped in the numbering |

Five acceptance findings: closure list in sync list **FIXED** (`…SYNC-LIST.txt:79`); 50-episode knob **PRESENT**
(`accept_…py:85-91,238`) but **broken** (Part 2); aggregate cap **FIXED**; warm-start assertion **FIXED**
(`runner.py:1072-1075`, negative test `test_cadence_resume.py:590-602`); early-BASELINE mode **REMOVED**
(`test_…launch.py:469-480`) and the relaxed sampler check replaced by a full `as_dict` digest compare
(`run_…_chunks.py:67-68`, `runner.py:1216-1229`).

**(b) Tests.** `90 passed, 1 skipped in 109.76s`, exit 0. No failures, no tracebacks. Skip =
`test_v023_c1c2_successor_stagec_launch.py:442` ("workspace already contains the required post-fix adapter").

**(c) Closure.** `--check` → `STAGEC_CODE_MANIFEST_CURRENT entries=269 sha256=5ca0d2d5de54a62b59bf43a98ce11c1fc949d35ddd25331a52a157ca72c72ff5`, exit 0, no drift, no `--write` needed.
Closure list 246 paths, **0 missing** from the 272-line sync list; the closure list itself is at sync-list line 79.
`sync_… --dry-run` exit **0**, mode `prepare-and-bind-only-no-stage-b-no-stage-c-launch`; last line
`BINDINGS=sat:…-stagec-20260907-r1-checkout/…/V023-C1C2-SUCCESSOR-STAGEC-EXECUTION-BINDINGS.json`.

**(d)** `git status --porcelain src/` is **empty** (the earlier src WIP is already committed).

**(e) Commit `2a226f0584d953ed84f86d50be793472a55dedcc`** (tree `b20d322f…`) on `wip/multi-catfish-v023-20260907`,
24 files, `git diff --cached --check` clean. Five directories rsynced (`--exclude __pycache__`, local → shadow only)
into `/home/sat/mcrl-v023-successor-shadow-20260907/.scratch/`; spot-checked digests match.

## Part 2 — server acceptance: NOT RUN, three blockers

**No episode was executed.** No server root was created; nothing outside the shadow was written.

1. **(c) The fixed acceptance script cannot pass for any arm at any size.** `accept_stage_c_chunk_equivalence.py:196-201`
   strips provenance from the **merged side only** (`_without_provenance(merged_checkpoint.get(key))`) and compares it
   against an **unstripped** expectation. `EpisodeReceipt.as_dict()` carries `schema` and `status`; the resume state
   carries `schema` — all three are in `PROVENANCE_ONLY_FIELDS`. Reproduced locally (stub transport, 2×100):
   `receipts` and `resume_state` mismatch at boundaries 100 and 200; raw compare **True**, symmetric compare **True**,
   shipped asymmetric compare **False**. One-line fix: strip both sides, or neither for these two keys.
2. **(c) The 100/2×50 learned rehearsal is dead on arrival.** `merge_arm_chunks` emits merged checkpoints/rungs only at
   `CHECKPOINT_EVERY=100` (`runner.py:2083`), so a 2×50 merge yields `['checkpoint-000100.json']` /
   `['rung-000100.json']`; `accept_…py:172-180` reads `checkpoint-000050.json` → missing → STOP. Reproduced.
   **(b)** `test_cadence_resume.py:560-587` merges 2×50 but never asserts the merged artifacts exist.
3. **(d)/(a) Preconditions absent.** `bind_…_freeze.py:158-176` now requires the addendum sealed **and** carrying seven
   §2 tokens — sidecar missing, 0/7 tokens (m1). Independently, `--admission-supplement` requires real Stage-A
   `PASS_SOURCE_TRAINING_INTEGRITY` + Stage-B `PASS_PLUMBING_INTEGRITY`; `ls -d /home/sat/mcrl-v023-c1c2-successor-*`
   returns nothing — Stage A/B have not run. Fabricating either is forbidden.

**(b) Root cause of 1 and 2:** `accept_stage_c_chunk_equivalence.py` and `build_stage_c_chunk_acceptance_bundle.py`
have **zero test coverage** — no test in the four packages imports either. The mandatory formal-launch gate is untested.

Next: controller applies+seals the §2 patch (m1); implementation owner fixes the two acceptance defects and adds a
test that runs `accept()` end to end; then Stage A → Stage B → acceptance → barriers.
