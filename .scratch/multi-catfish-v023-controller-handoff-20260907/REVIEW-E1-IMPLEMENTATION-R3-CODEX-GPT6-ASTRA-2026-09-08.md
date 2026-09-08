**FIX_FIRST. Items 1–3 remain accepted; 4–6 still have blockers. Item 7 is implemented.**

Reviewed HEAD `ffb0ce76fd8bc9c8f10adb86e4f81829ca3bdb3d` against R2’s `aa63c243`. No edits, network, SSH, or physical execution. The read-only sandbox provides no permitted writable temporary directory, so I did not rerun pytest. The reported **106 server passes remain unverified locally**. I ran read-only, in-memory reproductions against the actual functions.

4. **Runtime bindings — partially resolved.** NumPy/PyTorch/SGP4 versions, CPU/platform identity, and venv root, `pyvenv.cfg` digest and `sys.prefix` are recorded at [runner:379](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:379), then compared during preflight validation.

   **Remaining blocker:** [runner:418](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:418) records effective Torch threads but only environment strings for BLAS. **Reproduced:** changing the loaded OpenBLAS pool from **1 to 2 threads produced identical `process_bindings()`**. The effective thread configuration is therefore not fully authenticated.

5. **Budget/lifecycle — partially resolved.** Reservations use one ledger; its lock spans the full read-modify-write at [runner:1449](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1449). The previous handler/post-return double charge is gone. Existing-unit verification and merge/revalidation reserve budget. COMPLETE revalidation correctly classifies `E1ResourceIncomplete`/`E1Incomplete` as INCOMPLETE at [runner:2143](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:2143).

   Staged publication exists at [runner:1214](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1214); post-unit-rename failure publishes global invalidation at [runner:1857](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1857). Global-marker precedence is implemented at [unit:1783](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1783) and [merge:2028](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:2028).

   **Remaining blockers:**

   - [runner:1545](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1545) clips actual elapsed time to the reservation. **Reproduced: 9 seconds elapsed, 6 reserved → only 6 charged.**
   - Merge finishes charging at [runner:2134](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:2134), before terminal publication/readback at **2163–2164**. **Reproduced: 3 seconds computation + 7 seconds publication → 3 charged, successful COMPLETE.**
   - The charge-region mask restoration lies outside the interruption handler at [unit:1849](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1849) and **merge:2134**. **Reproduced:** deferred SIGTERM’s `E1Incomplete` escapes merge with **zero INCOMPLETE receipts**. Staging fixes the partial-file problem, but interruption coverage remains incomplete.

6. **Regression tests — improved, still incomplete.** Exact interruption charging, terminal revalidation/exhaustion, post-rename invalidation, marker precedence and portable mocking exist. The dominance test now invokes real solver iterations at [estimand tests:143](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_e1_estimands.py:143).

   However, the “concurrent” test at [runner tests:384](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:384) sequentially calls ledger helpers: no competing workers, mocked concurrent clock, or reservation-refusal assertion. Publication interruption/resume at [tests:520](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:520) exercises only `_publish_write_once`, not `execute_merge`. Revalidation parameters omit SIGTERM’s `E1Incomplete`. These tests miss the reproduced failures above.

7. **Launch-authority builder — accepted by source/test inspection.** The builder produces the validator’s exact 16-key schema, requires authenticated preflight/sealed contract, and writes once with a verified sidecar: [builder:15](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/build_e1_launch_authority.py:15), [builder:73](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/build_e1_launch_authority.py:73). The build→validate test mutates and reseals every top-level field at [tests:692](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:692). [README:73](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/README.md:73) gives the correct seal order.

**Scientific choices unchanged:** the diff preserves estimands, δ=0, service margin, N=12000, worlds, lineages, steps/users, keyed fields, ties, catalog and λ/κ roles. Contract, world derivation and `e1_estimands.py` are unchanged.

Minimal fixes: authenticate effective BLAS threads; charge full elapsed time through publication; cover settlement interruptions; add real concurrency and end-to-end publication regressions.

`ASTRA_E1_IMPL=FIX_FIRST`

