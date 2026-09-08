**FIX_FIRST.** Items 1–3 are resolved. Items 4–6 retain blockers.

Reviewed local HEAD `aa63c2434f6cdd360439c62233f24dc38879f9c0`, including fix commit `8bf7227`. No edits, network, SSH, or physical execution occurred. `/dev/shm` supported pytest temporary files. The E1-only suite produced **37 passes, 1 failure** with bytecode/cache writes disabled. The reported 96 server passes remain unverified. Local `--dry-run` exited **2** with the expected unsealed-contract refusal.

1. **Certificate completeness — NOTE: resolved.**

   [e1_estimands.py:248](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/e1_estimands.py:248) serializes retained exact DP values and backpointers; [line 718](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/e1_estimands.py:718) constructs the final backtrace.

   [Line 561](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/e1_estimands.py:561) recomputes the hash **from stored coefficients**, then compares those coefficients with the input panel. The independent checker at [line 351](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/e1_estimands.py:351) parses serialized rationals, rebuilds recurrence/backpointers, and independently sums the witness without calling `_inner_exact` or `_totals_exact`. The outer verifier additionally replays the solver and validates the authoritative proof fields.

2. **Lossless float32 Q1+Q2 and BASE authentication — NOTE: resolved.**

   [Runner:662](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:662) stores the complete **100 × 28 float32** surface as little-endian bytes encoded in hexadecimal. Decoding checks schema, dtype, shape, byte length, canonical encoding and finite values.

   [Runner:942](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:942) authenticates BASE against the decoded tape using masked first-index argmax. Empty masks select `NO_OP_ACTION=-1`. Generation now retains `q12` in the step payload.

3. **Profile boundaries and legacy-path removal — NOTE: resolved.**

   BASE, unilateral and joint verification enforce 100 users and the canonical interval at [runner:934](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:934), [957](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:957), and [1012](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1012). Generation also checks these boundaries through `_profile_metrics` and joint-catalog construction.

   E1 now uses the BASE-only helper at [runner:730](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:730) and validation-only helper at [772](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:772). Neither executes legacy D/F targets or `Q + 0/κ`. Donor formula hashes remain provenance bindings.

4. **Preflight and frozen bindings — BLOCKING: environment freeze remains incomplete.**

   The seal gate is correctly first in static validation at [runner:372](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:372), before [preflight publication:30](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/build_e1_preflight_manifest.py:30).

   The requested E1 tests, complete F2 code-binding list—including its multi-lineage loader—and RNG/keyed-field modules are included at [runner:268](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:268). PREREG file/semantic digests and rebuilt canonical TLE manifest are bound at [322](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:322). Checkout/output roots, `/home/sat/mcrl-runtime/tle-frozen-20260820`, and exact launch arguments are compared at [439](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:439).

   **Remaining gap:** [process_bindings:357](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:357) records Python, NumPy and four environment variables, but omits PyTorch/SGP4 versions, hardware and effective thread configuration required by [contract:186](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md:186). Comparing resolved interpreter paths also does not authenticate the selected virtual environment when different executables resolve to the same Python binary.

5. **Publication, resource handling and invalidation — BLOCKING: partially resolved.**

   Readback is implemented: [_write_once:1088](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1088) reopens actual bytes, verifies mode/content and hashes them. Unit staging verifies all three artifacts before rename. Separate INCOMPLETE paths preserve unit/terminal filenames; missing units produce WAITING; existing-unit authentication failures now publish global invalidation.

   The remaining defects are:

   - **Budget accounting is incorrect.** [Runner:1509](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1509) gives each concurrent worker the same remaining budget; the lock protects only completed-time updates, with no reservation or accounting for active workers. Merge/verification consumes no budget. This does not enforce the contract’s **16 worker-hours total**, including solver/verifier reserve.
   - **Interruptions are charged twice.** The exception handler charges at [1538](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1538); after its handled return, `sys.exc_info()` is clear, so [1555](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1555) charges again. A mocked-clock reproduction recorded charges of **2 seconds plus 3 seconds** for one attempt.
   - **Revalidating COMPLETE can poison valid completion.** The broad handler at [1732](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1732) converts `E1ResourceIncomplete` and SIGTERM’s `E1Incomplete` into permanent global invalidation. Both were reproduced in memory. Initial merge has the correct resource handlers; existing-COMPLETE revalidation does not.
   - **Publication interruptions remain unsafe.** Terminal writing at [1769](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1769) is outside the interruption handler and writes directly to the final filename. An interruption can leave a partial terminal that later becomes INVALID_RUN. Separately, failure after unit rename at [1200](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1200) reaches `_write_invalid_unit`, which refuses the already-existing unit instead of publishing global invalidation.
   - **Global invalidation does not govern unit execution.** [execute_unit:1482](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1482) never checks the global invalidation marker, allowing subsequent unit invocations to return successful COMPLETE despite global invalidation.

6. **Regression tests — BLOCKING: substantial additions, incomplete boundary coverage.**

   Meaningful tests now cover rational service thresholds/variable energies, BASE ties, coefficient/backpointer mutations, independent witness arithmetic, Q-surface refusals, catalog edge cases, and authenticated synthetic publication→resume→merge. See [estimand tests:31](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_e1_estimands.py:31), [runner tests:104](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:104), and [304](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:304).

   However, the budget test checks only **already exhausted before start**; interruption tests do not check charged time; solver exhaustion is tested only before initial terminal publication. Concurrent budgeting, COMPLETE revalidation interruptions, publication interruption and global-marker precedence are absent. The dominance test at [estimand tests:133](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_e1_estimands.py:133) exercises the census helper, not changing survivors across actual solver iterations.

   **NON-BLOCKING portability issue:** [runner tests:450](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:450) mocks contract/TLE bindings but leaves the server-interpreter requirement active, causing the single local failure.

**NOTE — scientific choices unchanged.** The fix-pass diff preserves δ=0, service margin 0.001, N=12000, all four world seeds, three lineages, steps 0..9, 100 users, keyed-field construction, tie rules, catalog definition and λ/κ’s authentication role. Exact comparisons remain at [runner:1600](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1600); the contract and world-derivation files are unchanged.

Minimal fixes: complete runtime bindings; enforce total concurrent worker budgeting with exactly-once charging; make interruption/publication/revalidation and global-invalidation precedence consistent; add regressions for these paths and obtain passing validation.

`ASTRA_E1_IMPL=FIX_FIRST`

