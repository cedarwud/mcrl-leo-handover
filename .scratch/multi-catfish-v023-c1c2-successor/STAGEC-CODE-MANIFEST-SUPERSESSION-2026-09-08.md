# Stage-C code manifest — versioned supersession record (2026-09-08 03:27 UTC)

Authority: astra ruling `ADJUDICATION-STAGEC-PREBIND-PROCEDURE-CODEX-GPT6-ASTRA-2026-09-08.md` (Q4: preserve old seals, authorise
supersession, authenticate the full closure, obtain a fresh scoped ultra verdict, rebind the final reviewed revision). Controller: Ben
(owner account). No stage-C run, chunk, acceptance or outcome exists at this time; stage A has not run (attempts #1/#2 stopped before
launch), so the contract's order "stage-C code pinned before stage A" is preserved by this re-pin.

| item | value |
|---|---|
| predecessor manifest (sealed at commit 5adf898) | entries 270, file sha256 `675431fa4c7132af35f9c62c49c3265bc434aa9daaeee2afa2cdae1bccb68ad8` (pin `675431fa4c7132af35f9c62c49c3265bc434aa9daaeee2afa2cdae1bccb68ad8`), preserved in git history |
| intermediate (branch commits, never bound) | M2 a7a51a1: 271 entries `4225377990…`; Q12: 272 entries `e9e04c0cfc…` (computed before the fix-pass-10 orchestrator change) |
| successor manifest (this tree, commit f000696 + this record) | entries 272, file sha256 `907bc7530e38b86a2b0ceda4b041df280ae5ec7a4a2553eb5f76a9f9e5f67894`; FROZEN pin line: `907bc7530e38b86a2b0ceda4b041df280ae5ec7a4a2553eb5f76a9f9e5f67894  V023-C1C2-SUCCESSOR-STAGEC-CODE-MANIFEST.sha256` |
| added members | `.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/build_stage_c_admission_mapping.py`, `.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/seal_stage_c_declined_continuation.py` |
| deleted members | none |
| changed members (12) | `.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/README.md`, `.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/test_cadence_resume.py`, `.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py`, `.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/README.md`, `.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/launch_stage_c_chunks.sh`, `.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/run_v023_c1c2_successor_stage_c.py`, `.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/run_v023_c1c2_successor_stage_c_chunks.py`, `.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/stagec_common.py`, `.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/test_v023_c1c2_successor_stagec_launch.py`, `.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/verify_v023_c1c2_successor_stagec.py`, `.scratch/multi-catfish-v023-two-route-source-training-runner/test_v023_two_route_source_training_runner.py`, `.scratch/multi-catfish-v023-two-route-source-training-runner/v023_two_route_learner_orchestrator.py` |

Changes and their evidence:
- **M2** `build_stage_c_admission_mapping.py` + shared sequential mapping path (`stagec_common.py`, `run_v023_c1c2_successor_stage_c.py`), byte-identity + drift tests — 41 physical-evaluation tests, launch bundle 32 passed/1 skipped/1 pre-existing environment-only failure (`test_dry_run_prints_commands_without_remote_execution`, absent workspace `.venv`).
- **Q1** `seal_stage_c_declined_continuation.py`, figure-pipeline closure authentication + rendered caption + manifest fields — figure tests 14 passed.
- **Q2** authorised chunked continuation 3001–9000 (barriers 6000/9000, authority chain, prefix preservation, bitwise boundary replay, verifier to 9000, append-only `continuation-result.json`) — 43 physical-evaluation tests, 36 launch tests passed/1 skipped/1 known env failure.
- **fix pass 10** (stage-A) changed `v023_two_route_learner_orchestrator.py`, a stage-C member (provenance-label exemption + `code_closure` closure context; real r8 receipt fixture; 35 runner tests).
- `ACCEPTANCE-SERVER-EQUIVALENCE.md` unchanged (`b6d6ab8baa07011d3d72ea6b54efa9f25d6f666ca47c837af75cc359c10b17ff`); addendum R2 sealed (`6e18469d…`), §2 byte-identical to the predecessor.

Review status: scoped ultra delta review requested from astra (`REVIEW-STAGEC-SUPERSESSION-DELTA-CODEX-GPT6-ASTRA-ULTRA-2026-09-08.md`); until it returns `ASTRA_STAGEC_CODE_FINAL=YES` for the successor digest above, no stage-A bind and no stage-C bind may use this tree.
Downstream: the stage-A launch manifest/bindings are regenerated at attempt #3 bind time; the four-arm 200-vs-2×100 acceptance is re-run against this code before any formal chunk.

## Re-pin after fix pass 6 (2026-09-08T05:15:32Z UTC)
Successor manifest after fix pass 6: entries 277, file sha256 `ed004025b77a097f5fa9e43d0062d12b2f0ff181c12f41ba6cf8ff29f39b00c9` (commit c9d0aba). The 907bc753… pin was never bound (ultra review FIX_FIRST). Second scoped ultra review requested against this digest.

## Re-pin after fix pass 6 (2026-09-08T07:02:20Z UTC)
Successor manifest after fix pass 6: entries 277, file sha256 `e290ef5059bd765a90e813c161fc4b97376aefd33d74ec3c20f23653454f7a67` (commit 2ee8866). The 907bc753… pin was never bound (ultra review FIX_FIRST). Second scoped ultra review requested against this digest.

## Re-pin after fix pass 6 (2026-09-08T10:09:01Z UTC)
Successor manifest after fix pass 6: entries 277, file sha256 `95182c8da3ef125bac39cb1f47e5cffb87f63ec35f8074ac8919b908c26b5fb4` (commit dc277aa). The 907bc753… pin was never bound (ultra review FIX_FIRST). Second scoped ultra review requested against this digest.

## Member inventory after fix pass 8 (authoritative; supersedes the earlier 2/12 figures)
Successor manifest `95182c8da3ef125bac39cb1f47e5cffb87f63ec35f8074ac8919b908c26b5fb4` (277 entries) versus the predecessor at 5adf898 (270 entries):
- added (7): `build_stage_c_admission_mapping.py`, `seal_stage_c_declined_continuation.py`, `V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-08-R2.md`, `V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-08-R2.md.sha256`, `README.md`, `render_v023_development_curves.py`, `test_render_v023_development_curves.py`
- changed (15): `README.md`, `test_cadence_resume.py`, `v023_c1c2_successor_physical_runner.py`, `README.md`, `bind_v023_c1c2_successor_stagec_freeze.py`, `build_v023_c1c2_successor_stagec_manifest.py`, `launch_stage_c_chunks.sh`, `run_v023_c1c2_successor_stage_c.py`, `run_v023_c1c2_successor_stage_c_chunks.py`, `stagec_common.py`, `sync_launch_v023_c1c2_successor_stagec_server.sh`, `test_v023_c1c2_successor_stagec_launch.py`, `verify_v023_c1c2_successor_stagec.py`, `test_v023_two_route_source_training_runner.py`, `v023_two_route_learner_orchestrator.py`
- deleted (0): none
