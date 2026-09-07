The revised flow is proportionate and sufficient for the demonstrated receipt, import, and authentication failures once the delivery fixes pass against the exact transferred package. Source authentication alone does not guarantee that every later interface will succeed, but that does not justify a new full-pipeline qualification gate. At the **22:10:34 Taipei snapshot**, the code manifest still lacked 19 declared dynamic dependencies and had four stale code bindings; the newer working launcher had already corrected the old-checkout TLE check. I found no scientific-semantic change in the inspected repairs. ([Manifest](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/R7-LAUNCH-CODE-MANIFEST.json:1), [corrected TLE check](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/sync_launch_v023_lcsrs_gate_server_r7.sh:161))

**Mandatory before relaunch**

1. **Complete the exact manifest-bound dependency closure.** Preserve the inherited V020 → V018 → V015 → V014/V013 code and authentication behavior, including imported helpers, package initializers, contracts, receipts, and required checkpoints. Transfer all three historical Q1/Q2 checkpoints: V020 authenticates all three even though R7 selects one lineage. This is faster and safer than extracting a new adapter now. ([Authentication chain](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1738), [checkpoint requirement](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate.py:210))

2. **Finish edits, reseal one stable package, and verify it locally.** Code manifest, launch-decision digest, preflight manifest, and sidecars must agree. Run the focused tests against **launch-ready paths**, then materialize only the actual transfer list in an isolated checkout and exercise real `validate_manifest()` → source configuration → `_authenticate()`. Require correct `mcrl.__file__`, complete `configuration`/`bindings`, matching `source_adapter` role, and authenticated Q1/Q2 provenance. Static import coverage alone misses the demonstrated Path-loaded dependencies. ([Closure requirement](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py:62), [focused tests](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/test_r7_launch_ready.py:39))

3. **Pass one remote pre-root smoke on those same sealed bytes.** Use the declared interpreter, checkout paths, and process environment; authenticate manifests, fresh-checkout imports, canonical preregistration, frozen TLE digest, and actual source-adapter authentication. Retain the I0 inventory check and existing checkout/run/session collision checks. Only afterward create the run root and launch the eight source workers. ([Actual consumer smoke](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/sync_launch_v023_lcsrs_gate_server_r7.sh:189))

**Do not block relaunch**

- **Preregistration caller-path enforcement is deferred hardening on the normal route.** The validator accepts an unused `prereg_path`, but the authorized controller explicitly supplies the same manifest-bound file under `$SERVER_ROOT`. Arbitrary direct invocation remains weaker; that is not evidence of a present normal-path mismatch. ([Validator](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py:221), [controller](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/sync_launch_v023_lcsrs_gate_server_r7.sh:256))
- Defer adapter extraction, comprehensive downstream seam coverage, new physical pilots, and repeated unrelated regression suites. Existing textual tests are limited, but the actual consumer smoke directly covers the repaired boundary.
- The fetcher’s `rmdir "$STAGING"` follows a copy that leaves staging populated, so cleanup can fail after successful retrieval. This needs bounded correction, but does not invalidate the sealed remote Gate. ([Fetcher](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/finalize_v023_lcsrs_gate_server_r7.sh:136))

**Science-contamination check**

No contamination found: the source-adapter comparison changes authorization tokens and binding-role alignment; fit and composition adapters are byte-identical to their R7 draft counterparts. The balanced-primary/raw-secondary change was already prospectively declared, and R6 remains failed. I0 is locally recorded as zero source artifacts and no scientific outcome. Engineering tests and the separate C1/C2 job establish no efficacy. ([Repair boundary](/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-MCRL-V023-LC-SRS-R7-LAUNCH-DECISION-2026-09-06.md:55), [I0](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/R7-INVALID-RUN-I0.json:1))

**Stop rule**

Once the sealed-package checks, focused current-path tests, isolated authentication smoke, and remote smoke/collision checks pass on identical bytes, **stop adding checks and launch once**. Consolidate closure repairs locally and avoid repeated transfer–fail–repair cycles; combine duplicate remote TLE checks where convenient. Keep C1/C2 generation parallel.

A valid non-GO ends this LC-SRS successor route; GO proceeds to the already planned five-arm screen under its frozen authority. Only demonstrated infrastructure invalidity permits the smallest invalid/unopened unit to be repaired. ([Frozen stop rule](/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md:129))

**One immediate next action**

Complete and reseal the exact transfer closure, then run the isolated actual `_authenticate()` smoke. This audit performed read-only inspection and hashing; it did not execute those checks.

FLOW_GO_AFTER_LISTED_FIXES