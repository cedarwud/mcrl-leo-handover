**FIX_FIRST.** R3 review of `5adf898..10791b539a994fed5bf3c8f4c763197db70f6a32`, limited to the remaining round-two items. No repository edits, network or SSH.

**BLOCKING — Item 7: wrapper recovery still fails after continuation-result publication.** The wrapper checks the preceding 6000 barrier at [launch_stage_c_chunks.sh:88](/home/sat/mcrl-v023-review-stagec/.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/launch_stage_c_chunks.sh:88). Although the controller receives `--resume-continuation`, [verify_arm_chunk:843](/home/sat/mcrl-v023-review-stagec/.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/verify_v023_c1c2_successor_stagec.py:843) calls the authority chain without permitting published-result recovery.

Reproduced through the **real wrapper → real barrier checker → real continuation-chunk verifier**, using isolated admission and preceding-prefix fixtures:

```text
STOP_PHYSICAL_EVALUATION_INTEGRITY: continuation result already exists
```

The wrapper exits **2** before finalization. The checkpoint-only probe passes this publication guard; it does not establish complete wrapper recovery. The existing wrapper tests conceal the failure by substituting an always-successful controller at [test_v023_c1c2_successor_stagec_launch.py:1363](/home/sat/mcrl-v023-review-stagec/.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/test_v023_c1c2_successor_stagec_launch.py:1363). Propagate narrowly scoped recovery authority through independent chunk verification and test both interruptions with the actual controller.

**BLOCKING — Item 10: continuation-boundary evidence still bypasses production execution.** At [test_cadence_resume.py:974](/home/sat/mcrl-v023-review-stagec/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/test_cadence_resume.py:974) and line 994, both comparisons call `_replay_arm_prefix_for_equivalence` with a test-local adapter. That helper has no production callers; the executing controller calls `FixedPolicyEvaluationRunner.run` at [run_v023_c1c2_successor_stage_c.py:431](/home/sat/mcrl-v023-review-stagec/.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/run_v023_c1c2_successor_stage_c.py:431).

Real environment transitions at offsets 3000 and 6000 improve coverage, but neither production chunk execution nor the production episode adapter executes. The required bitwise comparison against the actual sequential controller remains missing.

**NON-BLOCKING — Supersession inventory remains stale.** The [latest record:30](/home/sat/mcrl-v023-review-stagec/.scratch/multi-catfish-v023-c1c2-successor/STAGEC-CODE-MANIFEST-SUPERSESSION-2026-09-08.md:30) appends the correct digest without updating the inventory. Against the predecessor manifest, the authenticated changes are **7 additions, 15 changed members, zero deletions**, rather than the retained 2/12 inventory.

**NOTE — Remaining fixes verified:**

| Item | Result |
|---|---|
| **6: registered activity + later STOP** | Regression passes using the actual STOP filter. Registration now invokes live finished-root verification under the root lock before scheduling. [Registration:203](/home/sat/mcrl-v023-review-stagec/.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/run_v023_c1c2_successor_stage_c_chunks.py:203) |
| **8: receipt identity** | Independent probes reject `split="TEST"`, `status="C3_EFFICACY"` and `authorized_from_3000_token=FALSIFIED`. [Verifier:489](/home/sat/mcrl-v023-review-stagec/.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/verify_v023_c1c2_successor_stagec.py:489) |
| **Q1 renderer** | The unrelated-addendum probe with valid sidecars is refused. Authentication now binds the addendum to authenticated execution bindings. [Renderer:490](/home/sat/mcrl-v023-review-stagec/.scratch/multi-catfish-v023-ch5-figure-pipeline/render_v023_development_curves.py:490) |
| **10: direct publication integration** | Both interruption cases pass using the real merger, independent finished verifier and seal. Prefix hashes remain unchanged. Synthetic producer/admission fixtures remain explicit. [Integration:1297](/home/sat/mcrl-v023-review-stagec/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/test_cadence_resume.py:1297) |
| **Fixture isolation** | The fixture no longer rewrites the repository’s sealed R2 sidecar. [Fixture:220](/home/sat/mcrl-v023-review-stagec/.scratch/multi-catfish-v023-ch5-figure-pipeline/test_render_v023_development_curves.py:220) |

The unmodified three-package pytest run completed with **131 passed, 1 skipped; exit 0**, using the supplied interpreter and matplotlib path, `/dev/shm` temporary storage, and disabled bytecode/cache writes. `git status --porcelain` was empty before and after.

Manifest `--check` passes: **277 authenticated members, no missing or stray members**, exact pin and sync list. R2 §2 is byte-identical to its predecessor; both addendum sidecars authenticate. Acceptance-procedure bytes remain unchanged at `b6d6ab8baa07011d3d72ea6b54efa9f25d6f666ca47c837af75cc359c10b17ff`. The physical runner, world-plan builder and orchestrator have no changes since R2.

Requested report: `REVIEW-STAGEC-SUPERSESSION-DELTA-R3-CODEX-GPT6-ASTRA-ULTRA-2026-09-08.md`. The read-only checkout prevents saving it; this response contains the report.

**Stage-A attempt #3 bind is not authorized by this review.**

Successor manifest SHA-256: `e290ef5059bd765a90e813c161fc4b97376aefd33d74ec3c20f23653454f7a67`

`ASTRA_STAGEC_CODE_FINAL=FIX_FIRST`