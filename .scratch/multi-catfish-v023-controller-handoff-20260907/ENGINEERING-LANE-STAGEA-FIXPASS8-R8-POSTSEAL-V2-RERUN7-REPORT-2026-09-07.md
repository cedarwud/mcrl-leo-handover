# Engineering lane — stage-A fix pass 8 + r8 post-seal + V2-synthetic rerun #7

**NOT `V2_RERUN7_CLEAN`.** Fix pass 8's three items are implemented and correct, but the whole stage-A chain is
fail-closed behind **one missing row in a stage-C manifest owned by another operator**. Ceiling
`ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. No edits, no bypasses; nothing launched.

## Part 1 — fix pass 8

### (a) All three items implemented; all six declared digests and all three codex citations verified
1. **Stage-C member-hash authentication — FIXED.** `successor_launch_common.py:452` `verify_stage_c_code_bundle`:
   pin (`:459-465`), member existence (`:467-474`), per-member SHA-256 vs live bytes (`:475-483`), addendum+sidecar
   membership (`:485-493`), sidecar authentication (`:496`), exact physical-evaluation coverage (`:497-507`),
   stage-C verifier presence (`:508-511`). Negatives at `test_v023_c1c2_successor_launch.py:72-127` (7 selected, **7 passed**).
2. **Authenticated transport set — FIXED.** `build_v023_c1c2_successor_launch_manifest.py:20-41` forms the ordered
   union closure ∪ additions ∪ live stage-C members (`:28-30`) and re-asserts closure coverage (`:40`). After rsync the
   launcher reruns the manifest `--check` on the server, `sync_launch_v023_c1c2_successor_server.sh:166-167`, which
   re-hashes **every** payload path (`successor_launch_common.py:628-660`, `:655`), so a member missing after sync
   fails closed with `die 'server launch payload or Stage-C manifest member verification failed'`.
3. **`--replay-arms` — FIXED.** `verify_v023_c1c2_successor.py:423-625`; distinctness/panel report `:579-602`;
   CLI `:990`, `:998`, `:1010-1036`. Receipt path `:408-409` is a **sibling** `<root>-REPLAY-ARMS.json` (+ sidecar),
   `write_once`, so it neither enters the root schema nor touches the formal PASS token.

### (b) Test suite — 89 collected, **73 passed, 5 failed, 11 errors**, 236 s (re-run post-seal: identical)
All 16 non-passes share **one** root cause. First traceback: fixture `producer_output` →
`test_v023_c1c2_successor_launch.py:403 COMMON.verify_stage_c_code_bundle(REPO)` →
`successor_launch_common.py:492 SuccessorLaunchError: Stage-C addendum and sidecar must both be manifest members:
.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-07.md.sha256`.

### (c) Chain checks — both refuse, correctly
Manifest `--write` and `--check`: **exit 3**, same boundary, no manifest written. Would-be payload computed offline:
**282** = 246 closure + 13 new additions + 23 new stage-C members (269 stage-C members, 246 overlap).
`sync_… --dry-run`: **exit 2**, exactly two lines, at the **first** local gate — it never reaches the manifest check,
never opens ssh/rsync, launches nothing:
`SUCCESSOR_EXECUTION_BINDINGS_FAIL: required r8 target root is absent: /home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8`
/ `SUCCESSOR_LAUNCH_REFUSED: execution bindings are not current`.

**Blocker 1 (out of my lane).** `.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/build_v023_c1c2_successor_stagec_manifest.py:48`
emits the addendum `.md` but **not** its `.sha256` (contrast `:44` and `:47`, which do emit sidecars), while the
consumer `successor_launch_common.py:485-493` requires both. The sidecar itself now exists and authenticates
(`9673928f20fae6…`, landed in commit `96a2b14`); the 269-row manifest simply lacks that one row. All 269 declared
digests match live files and the pin matches (`b8774f54…`). Fix = one line in the stage-C producer + rebuild/pin.

**Blocker 2 (structural).** The dry-run's first gate is `bind … --target-root /home/sat/…-r8 --check` run **locally**
(`sync_…sh:92`, `:96`), and `/home/sat` does not exist on the controller box, so `bind_v023_c1c2_successor_freeze.py:195`
always reports the sealed root absent. The non-dry path (`:140`) has the same gate. Now that r8 exists on the server,
this is the launcher's remaining host mismatch, not a target problem.

### (d) Spot-checks (live)
Member hashes: `sha256sum -c` over all 269 declared rows → **0 mismatches**; pin self-consistent; physical-evaluation
coverage exact (7 declared = 7 on disk). Negatives all pass: stale member, missing member, missing pin, stale pin,
missing addendum sidecar, unlisted addendum sidecar. Exact-union test asserts the stage-C members explicitly
(`test_…:209-211`) — currently red only via the same blocker. `--replay-arms` read-only probe on the rerun-#6
finished root: **`REPLAY_ARMS_FAIL: VerificationError: non-formal rehearsal roots cannot pass formal verification`** —
`replay_arms` calls `verify_output(…, nonformal=False)` at `verify_…:436`, which `:659-660` refuses for any
`REHEARSAL-NONFORMAL` root. So `--replay-arms` is **undrillable non-formally**; its only exercise is the unit test,
which the blocker keeps red. This matches README step 6 (sealed formal root), but leaves the feature untested here.

### (e) Not green → **no commit, no shadow rsync** of the four packages (gate honoured). They are otherwise ready.

## Part 2 — r8 post-seal load check (read-only) — **PASS**
Both modes load; **16 shards per mode** (8 C1 + 8 C2 worlds ×2). C1 49 422 rows @228D, C2 4 330 rows @448D per mode
(`c2_rows_match_files` true); unit `normalized-repriced-ops3-delta-over-kappa`; type `EEAxisV014NormalizedPairBatch`;
`all_checks_pass: true`. `MANIFEST.sha256` = `8e1bd59e83d48c15ebc50054f2197936864f12f9c749225680a100c389f4bffd`;
`receipt.json` = `e9f8452646a3acc2cc96262501f3894dfc28558b73d191777c46f7c91a6f2376`; `COMPLETE` =
`8e1bd59e…  MANIFEST.sha256` (written 21:09:54 UTC; shadow verifier `CONTROLLER_TERMINAL` 21:12:58 UTC).
Receipt `status=TARGETS_MATERIALIZED_TRAIN`, `schema=multi-catfish-mcrl-v023-c1c2-target-generation-v1`,
`claim_ceiling=TRAIN_PHYSICAL_TARGET_GENERATION_ONLY_NO_LEARNER_NO_EPISODE_TRAINING_NO_EFFICACY_NO_TEST`.
Shadow verifier tally: **16 × `"validate_pass": 1`**, 16/16 shards PASS.
Receipts copied and committed: **`b89f478`** (digests re-verified after transfer).

## Part 3 — V2-synthetic rerun #7 — **BLOCKED at S1**
Mini-repo `…shadow-20260907/.tmp/stageA-synth-bundle-v7` (shadow clone + current local packages + `git init`, clean
`31f3346`); target `…-target-root-r2` (`3775c257…`); roots `…-SYNTH-REHEARSAL-NONFORMAL-20260907T215820Z*`; 50 MB,
peak RSS 625 MB (< 4 GB). No `*r8*` (other than the Part-2 read), `*lcsrs-gate*`, `*-r7-*`, `codex-ws-*`,
`c3-contingency-f1-*` or `stageC-*` root touched. S1 binder ×2 **exit 3**, S2 manifest **exit 3** — both at Blocker 1;
S3 preflight, S4 diagnostic, S5 wrapper, S6-S8 verifier/`--replay-arms` all cascade (no bindings, no provider config,
no preflight receipt, no output root). Re-run after the 21:58 UTC seal on the refreshed tree: identical.
