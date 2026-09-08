**FIX_FIRST.** The optimization logic appears mathematically sound, but certification, provenance, and run-lifecycle requirements are incomplete.

No edits, network, SSH, or panel execution occurred. The permitted pytest command exited **1 before collection** because no writable temporary directory was available. Runner `--help` passed; `--dry-run` exited **2** because the E1 preflight manifest is absent. These are not passing test results.

File references below are within the E1 directory unless explicitly marked F0/F1/F2.

1. **§2 estimands — NOTE: objective and constrained optimization are correct; BLOCKING: certificate implementation is incomplete.**

   [e1_estimands.py:194](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/e1_estimands.py:194) computes the service threshold exactly as `ceil(C_BASE − N/1000)`. With twelve authenticated ten-anchor units and 100 users, this is **C_BASE − 12**, using **N = 12000**. BASE belongs to every choice set; energies must be positive.

   [e1_estimands.py:215](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/e1_estimands.py:215) recomputes same-served-count dominance for the **current q on every iteration**, uses rational scores, and preserves BASE-first lexicographic ties. [e1_estimands.py:411](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/e1_estimands.py:411) updates the pooled ratio and terminates only at an exact zero residual. Terminal HEADROOM comparisons also use exact fractions.

   **Binding-case check, mentally constructed:** use 120 BASE anchors, each `(B,E,C)=(100,100,100)`. At anchor 1 offer `(300,100,88)`; at anchor 2 offer `(180,100,99)`. Required service is 11988. Both changes together serve 11987 and are infeasible; the first change alone serves exactly 11988 and gives the best feasible ratio, `12200/12000`. The DP retains that solution and excludes the infeasible combination.

   **NON-BLOCKING:** line 237 saturates cumulative counts at the threshold rather than retaining every count through N. This is an exact compression here: additional service above the threshold cannot alter future feasibility.

   **BLOCKING certificate gaps:**
   - [e1_estimands.py:242](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/e1_estimands.py:242) constructs DP rows but serializes only their counts and hashes. The required **DP recurrence values and backpointers are absent**; final selected IDs do not replace them.
   - Census before/after final-q reduction, coefficients, final q, residuals and exact selected totals are present at lines 318–350 and 470–493.
   - [e1_estimands.py:387](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/e1_estimands.py:387) validates the stored coefficient hash against the input panel, but **never checks the stored `certificate["coefficients"]` against that hash**. Altering those coefficients alone passes this verifier. Several proof fields—including the reported terminal residual, minimum service and feasibility flags—also escape validation.
   - Verification reruns the same `_inner_exact` and `_totals_exact` helpers. Add an independent recomputation from the serialized witness/coefficients and validate the actual delivered proof.

2. **Joint witness catalog — NOTE: matches the accepted interpretation.**

   [run_v023_c3_existence_e1.py:456](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:456) derives origins from **BASE’s realised served occupancy**, intersects legal destinations by `(NORAD, cell)`, and evaluates each complete joint action through the environment.

   Singleton origins and empty destinations are included. There is no favourable-success filter. Origins/destinations are sorted; exact serialized physical duplicates receive aliases, including aliases to BASE. An empty catalog yields no candidates, leaving BASE alone in J1.

   **BLOCKING validation caveat:** joint profiles lack the interval consistency check described under item 4.

3. **§4 panel and continuation — NOTE: generation follows the declared conventions; BLOCKING: tape cannot authenticate the BASE argmax.**

   [run_v023_c3_existence_e1.py:136](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:136) implements the specified ASCII SHA-256 derivation. The declared seeds are:

   `861587764845384088`, `3943897440191533562`, `5747196377242098234`, `4004348767321774260`.

   Lines 269–287 enforce lineages **2026092101–03**, ten steps **0..9**, 100 users and the stage-C exclusion check. Historical inventory cleanliness beyond these checks remains the controller’s recorded evidence.

   [run_v023_c3_existence_e1.py:949](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:949) binds `MCRL_V023_LCSRS_C3_OBSERVABILITY_V1` before reset and imports the F1/F2 RNG construction. F1’s `_q12_surface` performs **float32 Q1+Q2**, first-index masked argmax and empty-mask NOOP handling. F1’s enumerator visits user then action and omits BASE-equivalent physical keys.

   Each physical evaluation uses the neutrality guard at runner lines 432–435. The native evaluator clones RNG and restores segment state. Only BASE is committed; runner lines 1011–1019 compare its complete physical payload against `last_outcome`.

   **BLOCKING:** [run_v023_c3_existence_e1.py:627](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:627) claims imported verification proves mask/**tie**/NOOP coverage, but `f1.target_surfaces_from_step` checks legality and enumeration, not whether BASE maximizes Q1+Q2. The missing Q surface prevents that check.

4. **§5 accounting — NOTE: B/E and F0 accounting are correct; BLOCKING: two conformance gaps.**

   The interval comes from `DECISION_STEP_S = 47 × 0.640` in [constants.py:73](/home/u24/papers/mcrl-leo-handover/src/mcrl/env/constants.py:73), with runtime agreement required at runner lines 964–966.

   [run_v023_c3_existence_e1.py:383](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:383) uses `Δt × math.fsum(rates)` and `Δt × P_system`, matching F1. Imported profile conversion calls `verify_canonical_power`; E1 calls `compute_cost_shares` and verifies conservation. F0 retains occupancy/service, unserved-zero, PA, circuit/baseband and roundoff checks. Network energy is not replaced by summed link power.

   **BLOCKING:**
   - [run_v023_c3_existence_e1.py:696](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:696) checks joint metrics and conservation without requiring `profile.interval_s == INTERVAL_S` or the BASE user count. A joint profile with a different positive interval and consistently updated metrics/hash passes this boundary; its different interval weighting can alter J1.
   - Runner line 629 calls [F1:838](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f1/run_v023_c3_contingency_f1.py:838), which computes legacy **D/F targets using λ**. Thus λ is not solely authenticating, and valid E1 tapes acquire an unnecessary legacy-target arithmetic failure path.

   **NON-BLOCKING numerical caveat:** F1’s BASE helper also executes `Q + 0/κ` through its composition helper ([F1:1326](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f1/run_v023_c3_contingency_f1.py:1326)). No nonzero residual affects BASE or E1 optimization, but the literal “no z/κ composition anywhere” condition is not met. Use reusable validation-only and BASE-only entry points.

5. **§7 freeze, authority and receipts — BLOCKING.**

   **Correct pieces:** [run_v023_c3_existence_e1.py:331](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:331) requires exact launch-authority keys and values and authenticates the read-only contract/sidecar. Unit/world/lineage/step refusals are present. All defined receipt constructors carry the exact required claim ceiling. F2 authenticates unique checkpoints, authority files/body seals and lineage semantics; generation checks Q1/Q2 parameter hashes before/after. PREREG and its listed TLE files are authenticated through imported machinery.

   The remaining blockers are:

   - **Preflight can freeze without a sealed contract.** [build_e1_preflight_manifest.py:15](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/build_e1_preflight_manifest.py:15) calls static bindings and code bindings only. Neither checks the E1 contract sidecar. The contract check occurs later in launch validation. The current preflight test explicitly expects success without arranging a sealed contract.
   - **Launch inputs are not fully frozen.** Runner lines 335–338 exclude checkout/output roots, TLE root and exact launch arguments from authority keys; lines 1241–1246 accept arbitrary supplied output/TLE paths. The required `/home/sat/mcrl-runtime/tle-frozen-20260820` root is not enforced.
   - **Dependency/environment coverage is incomplete.** [run_v023_c3_existence_e1.py:248](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:248) omits E1 tests and runtime environment bindings. It also misses F2’s imported multi-lineage loader: E1 invokes F2 static validation, not F2’s complete code-binding list, which includes that loader.
   - **Publication lacks required readback.** [run_v023_c3_existence_e1.py:826](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:826) stages and renames unit bundles, but imported [F1 `_write_once`:1025](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f1/run_v023_c3_contingency_f1.py:1025) returns the hash of intended bytes without reopening the file. Tapes, manifests and receipts therefore are not readback/hash-verified before publication succeeds. Resume authentication does not repair this initial-publication gap.
   - **INCOMPLETE is unimplemented.** [run_v023_c3_existence_e1.py:1031](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1031) catches ordinary exceptions as INVALID_RUN; interruptions receive no INCOMPLETE receipt. There is no budget accounting/enforcement or bound supervisor for the accepted 16-worker-hour cap. The solver’s 10,000-iteration limit also becomes INVALID_RUN rather than resource exhaustion.
   - **Incomplete acquisition is permanently invalidated.** [run_v023_c3_existence_e1.py:1199](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1199) converts missing units into a write-once INVALID_RUN terminal. Premature merge therefore prevents normal completion after remaining units arrive.
   - Initial merge correctly suppresses both estimands on integrity failure. However, authentication failures on existing-unit/existing-COMPLETE-terminal paths occur outside that invalidation handler and do not publish a global invalidation record.

6. **C-C tape schema — BLOCKING: Q1+Q2 is missing.**

   [run_v023_c3_existence_e1.py:971](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:971) receives `_q12` and discards it. [run_v023_c3_existence_e1.py:554](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:554) stores masks, physical-key tables, BASE actions/profile/metrics, and unilateral rows containing user, action, B, E, served count and F0 checks.

   **Missing required field:** the losslessly serialized **100 × 28 float32 Q1+Q2 surface**, with dtype/shape validation. Without it, C-C cannot identify physically distinct exact primary maximizers from the tape.

   BASE conservation is recomputed during verification, though there is no separate serialized BASE F0-check record.

7. **Tests — BLOCKING: insufficient coverage of the identified boundaries.**

   [test_e1_estimands.py:52](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_e1_estimands.py:52) contains useful brute-force binding/non-binding comparisons, candidate ties, an all-BASE optimum, J1 comparison and one final-q mutation test.

   Missing coverage includes dominance survivors changing with q, BASE-versus-candidate exact ties, DP/proof-field mutations, an independent exact witness check, and broader variable-energy cases. The brute-force oracle itself uses floating arithmetic for the service threshold.

   [test_run_v023_c3_existence_e1.py:150](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:150) builds abbreviated synthetic tapes and calls terminal construction directly, bypassing tape authentication. Tests do not establish a valid complete tape→publication→resume→merge path.

   Add focused refusal tests for missing contract seals, changed launch roots, missing/malformed Q surfaces, non-argmax BASE, joint interval mismatch, interrupted acquisition, premature merge and corrupted published artifacts. Catalog tests also need singleton, unserved-origin exclusion, alias, empty-catalog and unsuccessful-realisation cases.

8. **README “Plainest readings” — NOTE: consistent with accepted scientific interpretations.**

   [README.md:6](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/README.md:6) correctly describes pooled U1/J1, their restricted scope, exact optimization, BASE continuation and the claim ceiling. It introduces no additional scientific choice.

   **NON-BLOCKING documentation correction:** its proof description is valid mathematically, but the current delivered certificate lacks the required DP evidence. Outside “Plainest readings,” the receipt claims at lines 78–80 overstate readback and comprehensive invalidation handling.

Minimal fixes, in priority order:

1. Complete and independently validate the serialized certificate, including DP values/backpointers and every authoritative proof field.
2. Store/validate float32 Q1+Q2 and authenticate BASE’s exact masked argmax from the tape.
3. Enforce canonical interval/user counts for every profile; remove legacy D/F evaluation and residual composition from E1’s validation/BASE path through reusable donor interfaces.
4. Require the sealed contract before preflight publication; freeze roots, arguments, tests, loader/RNG dependencies and runtime bindings.
5. Add publication readback/hash verification, resumable INCOMPLETE handling, budget accounting and global invalidation handling.
6. Add the focused regression tests above and obtain an actual passing run in an environment supporting pytest temporary files.

`ASTRA_E1_IMPL=FIX_FIRST`

