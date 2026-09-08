**Not ready to seal.** The authorised pytest command passed: **9 passed in 1.42s, exit 0**, using `TMPDIR=/dev/shm` and disabling bytecode writes. No project edits, network access, or SSH.

Five fixes are required:

1. **P1 — Valid corrected-F0 receipts are rejected.** [Runner:489](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:489) requires both conservation residuals to equal zero. Accepted F0 instead uses its existing roundoff bound ([F0:243](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency/c3_contingency_f0.py:243)); E1 serialises the resulting residuals ([E1:778](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:778)). A read-only synthetic probe with **100 users and Δt=30.08** passed E1 conservation but produced `−2⁻⁵⁰ W`; C-C rejected it. Preserve accepted E1/F0 verification semantics without introducing a new tolerance.

2. **P1 — The specified E1 terminal digest is not enforced.** [Runner:313](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:313) returns whatever terminal hash it reads, and [authority builder:74](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/build_cc_launch_authority.py:74) freezes that discovery. Nothing compares it with `0bc54fad23c8cdac2ce789c49ee37880f4df6e32110576c7a800443df0e7c4a6`. Enforce that reviewed digest before accepting the source bundle.

3. **P1 — Unit receipts are not bound to the C-C implementation that produced them.** [Runner:713](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:713) records E1 provenance but omits C-C contract, preflight/code, and unit-authority digests. [Merge validation:942](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:942) therefore accepts receipts from another C-C implementation if their E1 tape hash matches. An in-memory probe with filesystem reads mocked reached SUPPORT without any C-C provenance. Bind each receipt to its producer authority and require the common sealed contract/preflight/code bindings at merge.

4. **P2 — The documented authority command cannot parse.** [README:76](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/README.md:76) supplies `--launch-arguments --`. With the builder’s `argparse.REMAINDER` declaration ([builder:113](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/build_cc_launch_authority.py:113)), the standalone `--` causes **exit 2: unrecognized arguments**. Reproduced with the actual parser. Remove that separator and test the documented invocation.

5. **P2 — An interrupted valid panel becomes INVALID_RUN.** Missing unit receipts fail [runner:938](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:938), then [runner:969](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:969) publishes an immutable INVALID_RUN terminal. The [contract:116](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/candidates/V023-C3-CANDIDATE-C-CONTRACT-2026-09-08.md:116) requires INCOMPLETE for interrupted valid acquisition. Distinguish absent unfinished units from corrupt or invalid units, preserving completion/recovery.

The remaining requested checks are supported by the code:

| Check | Evidence |
|---|---|
| Exact tape Q, ties, BASE | E1 computes the specified float32 sum at [E1:1010](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1010). C-C decodes its bytes at [runner:496](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:496), uses numerical equality including signed zeros at :533, and checks BASE against the minimum tie index at :603. |
| Physical focal and complete deployment | [Runner:611](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:611) selects the lowest user with distinct physical maximisers. :647–662 authenticates the complete unilateral action vector and minimises `(energy, native action)`. Non-focal actions remain BASE. |
| Alias handling | [Runner:571](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:571) rejects duplicate **non-BASE** physical aliases. BASE-key aliases are skipped, matching [F1:699](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f1/run_v023_c3_contingency_f1.py:699). |
| Accounting and panel | [E1:751](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:751) supplies binary64-hex bits, energy and served counts; energy is Δt × canonical system power ([F0:432](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency/c3_contingency_f0.py:432)). [Runner:709](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:709) requires steps 0–1; :818 requires 12 receipts, 24 anchors and 2,400 opportunities. |
| Exact decision arithmetic | [Runner:742](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:742) converts binary64 values to exact fractions before pooling. :779–792 implements strict EE improvement, exact service margin and every applicable NO_SUPPORT reason. |
| Authority and publication mechanics | Exact authority keys/values are checked at [runner:412](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:412); contract mode/sidecar at :133; code bindings at :170; tape hashes at :358/:398; exclusive creation, 0444 and readback at :858. These mechanics do not resolve findings 2–3. |

The exact claim ceiling is consistent:

`TRAIN_DEVELOPMENT_C3_CANDIDATE_CC_FAST_SCREEN_NO_LEARNER_NO_EFFICACY_NO_TEST`

Tests meaningfully cover **(a)–(e)** at [tests:86](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/test_run_v023_c3_candidate_cc.py:86), **(f)** write-once/seal/key refusals at [tests:143](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/test_run_v023_c3_candidate_cc.py:143), and **(g)** lossless rational conversion at [tests:195](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/test_run_v023_c3_candidate_cc.py:195). However, (g) uses only one anchor; add unequal-energy multi-anchor pooling and the 2-versus-3 lost-service boundary, alongside regressions for the findings.

No ε band, additive `z/κ` composition, tuning, or new physics execution was found. Actual server tape contents were not inspected.

**ASTRA_CC_IMPL=FIX_FIRST**

