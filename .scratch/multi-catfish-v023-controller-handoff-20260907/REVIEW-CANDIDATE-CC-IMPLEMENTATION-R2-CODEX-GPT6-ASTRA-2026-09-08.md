**R2: all five R1 behavioral probes pass, but one sealing gap remains.**

Reviewed HEAD `de0b806e482909d9ac923a47418c7fa74e814058`. Authorized pytest: **21 passed in 1.47s, exit 0**, using `/dev/shm` and disabling bytecode/cache writes. No project edits, network, or SSH.

| Requested verification | Result and evidence |
|---|---|
| F0 residual semantics | **PASS.** Actual E1/F0 synthetic profile with 100 users, Δt=30.08 and `−2⁻⁵⁰ W` is accepted; `1e-6 W` is rejected. Uses inherited `_assert_close` at [runner:515](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:515); regression at [tests:233](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/test_run_v023_c3_candidate_cc.py:233). |
| Reviewed E1 digest | **PASS.** A different terminal digest is refused before metadata extraction at [runner:298](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:298); builder also enforces it at [builder:63](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/build_cc_launch_authority.py:63). |
| C-C receipt provenance | **PASS for the requested probe.** Producing authority digest is supplied at [runner:1141](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:1141). Missing provenance and mismatched common bindings are refused at [runner:765](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:765). The otherwise supportive 12-unit in-memory merge probe now produces `INVALID_RUN`. |
| Documented invocation | **PASS.** Parsed the literal [README:81](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/README.md:81) invocation with both actual parsers. The erroneous separator is removed. |
| Absent versus corrupt units | **PASS.** Absent directories yield `C_C_MERGE_WAITING`, exit 3, without publishing terminal; present corrupt units yield `INVALID_RUN`. See [runner:1064](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:1064) and [tests:398](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/test_run_v023_c3_candidate_cc.py:398). |
| Additional arithmetic tests | **PASS.** Unequal-energy anchors pool sums before division at [tests:432](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/test_run_v023_c3_candidate_cc.py:432); losing 2/2400 services passes and 3/2400 fails at [tests:458](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/test_run_v023_c3_candidate_cc.py:458). |

The contract is **byte-identical to R1 implementation commit `ef48aca`**, including §4/§5. Exact float32 ties, deterministic unilateral selection, global rational pooling, strict EE improvement and the `1/1000` service margin remain unchanged. Current dry-run correctly refuses the unsealed contract with exit 2. Server tapes were not inspected.

Minimal remaining fix:

- **P1 — Bind the newly imported F0 verifier source.** [Runner:29](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:29) now imports decision-relevant F0 verification code, but [expected_code_bindings:180](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-candidate-cc/run_v023_c3_candidate_cc.py:180) omits `c3_contingency_f0.py`. Consequently, changing its tolerance implementation would leave C-C preflight/authority/common producer code bindings unchanged. Add its path/SHA-256 to those bindings and a regression proving verifier-source drift is refused. This preserves the accepted F0 semantics through sealing.

**ASTRA_CC_IMPL=FIX_FIRST**

