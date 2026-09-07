# Follow-up adjudication: fresh-process closure (51 R7-bound files vs 18) — codex gpt-6-astra, read-only, 2026-09-07

**Adopt P with an explicit learner declaration and a separate authentication-only closure test.** Q adds unnecessary historical constraints to learner dependencies; reserve R for authentication that unavoidably requires divergent learner code.

Local probes confirm **51 = 18 + 33**, no missing authentication files, and exactly the two named R7 hash divergences. The authentication-only import probe still closes at 18. All 90 current launch-manifest entries match their files. The v2 → v1 → bridge import chain is confirmed.

P needs correction: if `L := discovered − A` automatically, P3(a) is tautological; a new dependency already present in the launch manifest also passes P3(c). Declare and pin **A’s 18 paths and L’s 33 paths independently**, with their module mappings. Classification follows dependency responsibility, never current hash equality. Shared files in A may also serve the learner.

Require exactly these identity-payload keys, retaining existing field meanings:

```text
schema, target_manifest_sha256, c3_schedule_receipt_sha256,
epoch_budget, c3_source_ids, r7_code_root,
r7_preflight_manifest_sha256, r7_code_manifest_sha256,
r7_result_manifest_sha256, r7_gate_result_sha256,
r7_authentication_runtime, r7_authentication_runtime_sha256,
r7_bound_learner_runtime, r7_bound_learner_runtime_sha256
```

Both runtime lists contain exactly `{path, module, loaded_from, sha256}` records from observed module objects. Preserve A’s declared ordering; sort L by `(path, module)`. Each digest hashes its complete list using the existing compact, sorted-key, finite ASCII JSON encoding **without a trailing newline**. The provider identity hashes the complete payload.

Keep `code_sha256` as the separately authenticated 100E launch-manifest digest. The admission receipt must bind that digest together with the provider identity/payload, and validate recorded hashes against that manifest; recording a digest alone is insufficient.

Require these assertions and corresponding runtime admission checks:

1. In a fresh factory process, independently discovered R7-bound paths `D` satisfy `D == A ∪ L`, `A ∩ L == ∅`, and both observed lists equal their explicit declarations—no missing, additional, or duplicate entries.
2. A separate fresh probe importing `_FIT/_R7_GATE/_PREFLIGHT/_SCHEDULE` without the bridge has R7-bound closure exactly A. Retain unmocked authentication integration coverage for dependencies reached only during execution; importing modules alone does not establish execution closure.
3. Every recorded module origin equals the exact regular, symlink-free `learner_checkout / path`. Reject missing, foreign, conflicting, or undeclared module origins **before filtering by checkout location**, so filtering cannot hide them.
4. For every A record, `sha256(loaded_from) == R7_binding[path] == launch_binding[path]`. For every L record, `sha256(loaded_from) == launch_binding[path]`; R7 equality is not required.
5. Every loaded project-owned executable module, including scratch seams and files absent from R7, is covered by the launch manifest and matches its hash. This extends coverage beyond the R7 intersection.
6. `ee_axis_lcsrs_three_route.py` and `ee_axis_v014_head.py` belong to L and never A.
7. Recompute both list digests and the complete identity; reject malformed records, omissions, reclassification, origin changes, or hash mismatches even when an altered receipt’s digest is recomputed.

Apply these checks before provider admission and at controller startup, retaining full historical-root validation and pre-import learner-manifest verification. Use an immutable checkout with source-consistent bytecode; source-file hashes alone cannot attest arbitrary cached or subsequently replaced code.

Update every strict receipt consumer. The [current 100E preflight](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/preflight_v023_100e_source_training.py:189) still requires two-field runtime records and rejects the implemented four-field records.

This preserves A’s **R7-bound authentication-code guarantee** and manifest-bound live learner execution. It does not imply that the entire mixed process—or newer factory/schedule code—is R7-era. Current import evidence establishes neither completed authentication nor launch readiness.

DECISION: Adopt hardened P with explicit 18/33 declarations, authentication-only closure coverage, and runtime origin/hash enforcement; retain R as the dependency-conflict fallback.
tokens used
89,305
**Adopt P with an explicit learner declaration and a separate authentication-only closure test.** Q adds unnecessary historical constraints to learner dependencies; reserve R for authentication that unavoidably requires divergent learner code.

Local probes confirm **51 = 18 + 33**, no missing authentication files, and exactly the two named R7 hash divergences. The authentication-only import probe still closes at 18. All 90 current launch-manifest entries match their files. The v2 → v1 → bridge import chain is confirmed.

P needs correction: if `L := discovered − A` automatically, P3(a) is tautological; a new dependency already present in the launch manifest also passes P3(c). Declare and pin **A’s 18 paths and L’s 33 paths independently**, with their module mappings. Classification follows dependency responsibility, never current hash equality. Shared files in A may also serve the learner.

Require exactly these identity-payload keys, retaining existing field meanings:

```text
schema, target_manifest_sha256, c3_schedule_receipt_sha256,
epoch_budget, c3_source_ids, r7_code_root,
r7_preflight_manifest_sha256, r7_code_manifest_sha256,
r7_result_manifest_sha256, r7_gate_result_sha256,
r7_authentication_runtime, r7_authentication_runtime_sha256,
r7_bound_learner_runtime, r7_bound_learner_runtime_sha256
```

Both runtime lists contain exactly `{path, module, loaded_from, sha256}` records from observed module objects. Preserve A’s declared ordering; sort L by `(path, module)`. Each digest hashes its complete list using the existing compact, sorted-key, finite ASCII JSON encoding **without a trailing newline**. The provider identity hashes the complete payload.

Keep `code_sha256` as the separately authenticated 100E launch-manifest digest. The admission receipt must bind that digest together with the provider identity/payload, and validate recorded hashes against that manifest; recording a digest alone is insufficient.

Require these assertions and corresponding runtime admission checks:

1. In a fresh factory process, independently discovered R7-bound paths `D` satisfy `D == A ∪ L`, `A ∩ L == ∅`, and both observed lists equal their explicit declarations—no missing, additional, or duplicate entries.
2. A separate fresh probe importing `_FIT/_R7_GATE/_PREFLIGHT/_SCHEDULE` without the bridge has R7-bound closure exactly A. Retain unmocked authentication integration coverage for dependencies reached only during execution; importing modules alone does not establish execution closure.
3. Every recorded module origin equals the exact regular, symlink-free `learner_checkout / path`. Reject missing, foreign, conflicting, or undeclared module origins **before filtering by checkout location**, so filtering cannot hide them.
4. For every A record, `sha256(loaded_from) == R7_binding[path] == launch_binding[path]`. For every L record, `sha256(loaded_from) == launch_binding[path]`; R7 equality is not required.
5. Every loaded project-owned executable module, including scratch seams and files absent from R7, is covered by the launch manifest and matches its hash. This extends coverage beyond the R7 intersection.
6. `ee_axis_lcsrs_three_route.py` and `ee_axis_v014_head.py` belong to L and never A.
7. Recompute both list digests and the complete identity; reject malformed records, omissions, reclassification, origin changes, or hash mismatches even when an altered receipt’s digest is recomputed.

Apply these checks before provider admission and at controller startup, retaining full historical-root validation and pre-import learner-manifest verification. Use an immutable checkout with source-consistent bytecode; source-file hashes alone cannot attest arbitrary cached or subsequently replaced code.

Update every strict receipt consumer. The [current 100E preflight](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/preflight_v023_100e_source_training.py:189) still requires two-field runtime records and rejects the implemented four-field records.

This preserves A’s **R7-bound authentication-code guarantee** and manifest-bound live learner execution. It does not imply that the entire mixed process—or newer factory/schedule code—is R7-era. Current import evidence establishes neither completed authentication nor launch readiness.

DECISION: Adopt hardened P with explicit 18/33 declarations, authentication-only closure coverage, and runtime origin/hash enforcement; retain R as the dependency-conflict fallback.
