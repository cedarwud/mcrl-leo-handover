**FIX_FIRST — one blocking issue remains: the BLAS fallback still does not authenticate effective threads.** Items (b)–(d) resolve the requested R3 cases.

Reviewed `91af519712acbeab6069f4e3ca2041f0d4fd126d` against R3’s `ffb0ce76`. No repository edits, network, SSH, or physical execution. With `/dev/shm` temporary files and bytecode/cache writes disabled, the requested E1 suite completed: **54 passed in 22.50 s**, exit 0. Collection confirms 54 tests; the reported **112 server passes remain independently unverified**.

1. **(a) Runtime bindings — BLOCKING.** The `threadpoolctl` branch rejects effective BLAS/OpenMP counts other than one at [runner:414](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:414). However, [runner:428](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:428) accepts `numpy.show_config()` when that dependency is unavailable. This describes build configuration, not the current pool size.

   **Reproduced against actual loaded OpenBLAS:** effective threads **1 → 2**, while **`process_bindings()` remained identical** and accepted both configurations. Environment variables and effective Torch counts stayed at one; only the server-interpreter assertion was bypassed. `threadpoolctl` is actually absent locally. The current test explicitly accepts this fallback at [tests:901](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:901).

2. **(b) Full elapsed accounting — accepted for the requested cases.**
   
   - **9 s elapsed / 6 s reserved → 9 s charged:** [runner:1611](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1611) no longer clips charges; the regression at [tests:468](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:468) passed.
   - **3 s compute + 7 s publication → 10 s charged:** terminal publication and immutable readback now precede settlement at [runner:2224](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:2224), with elapsed sampled at **2242**. The end-to-end merge regression at [tests:594](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:594) passed.

3. **(c) Settlement interruption — accepted.** Deferred SIGTERM’s `E1Incomplete` on mask restoration is caught **after exactly-once settlement**, then publishes an INCOMPLETE receipt: [unit:1914](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1914), [merge:2238](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:2238). Thus the third R3 case now yields **an INCOMPLETE receipt with no remaining reservation**. Both regressions passed; they inject the deferred exception rather than deliver an OS signal.

4. **(d) Concurrency/publication regressions — accepted.** [tests:416](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:416) starts **two forked processes**, releases them through shared events against the same ledger file, observes both 6-second reservations, refuses another reservation, and verifies 9+3 seconds charged exactly once with duplicate settlements rejected. [tests:494](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:494) exercises **`execute_unit` end-to-end**, interrupting the actual publication rename, checking INCOMPLETE/staging cleanup, then resuming successfully with exactly 2+3 seconds charged.

**Scientific choices unchanged by fix pass 3:** contract, world derivation and `e1_estimands.py` are unchanged; the runner diff preserves estimands, δ=0, service margin, N=12000, worlds/lineages, steps/users, keyed fields, ties, catalog and λ/κ roles.

Minimal remaining fix: **fail closed when effective BLAS/OpenMP inspection is unavailable**, or provide an equivalent runtime query; replace fallback-acceptance coverage with missing-inspector refusal and an actual 1→2 pool-mutation regression.

`ASTRA_E1_IMPL=FIX_FIRST`

