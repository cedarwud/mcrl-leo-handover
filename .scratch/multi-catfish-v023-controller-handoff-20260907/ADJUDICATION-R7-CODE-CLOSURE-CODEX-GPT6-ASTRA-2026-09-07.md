# R7 code-closure boundary adjudication (codex gpt-6-astra, read-only, 2026-09-07)

Provenance: produced by `codex exec --model gpt-6-astra --config 'model_reasoning_effort="max"' --sandbox read-only`
from the brief `codex-optionA-adjudication-prompt.txt` (controller session e9fba164, Fable 5.1). The adjudicator
read the repository files it cites; it could not open SSH, so remote seal states were not re-verified by it.
Controller notes: (1) the ruling ADOPT_HETERO_Q2_448 and the GPT-6 R6 staged-provenance audit that the brief cites
live in the controller memory/prompt, not in the repository, which is why the adjudicator marks their attribution
unverified; (2) the decision below was accepted by the controller per the user's instruction to decide with codex.

---

**Decision memo — R7 provenance and learner execution**

**Adopt A, with explicit checks on both the historical code root and the authentication code actually executing.** This resolves the demonstrated incompatibility without changing the learner or weakening R7’s frozen checks. It does not establish that the prerequisite artifacts currently satisfy the GO admission gate.

Audit snapshot: `main@42a8247c3fe3078070828f1d3d3f3eec7b4009c2`, dirty working tree, 2026-09-07. I modified no files. Concurrent edits corrected the launcher’s initially inconsistent hash constants; the final checked 88-entry launch manifest had SHA-256 `5b2267d40a890b79e9b99e640e904d3a1c0085192ed27b8d388a22545d93cca5`.

**1. Findings on claims 1–4**

**Claim 1: confirmed, with an earlier failure than the quoted message.**

The factory derives `REPO` from its own location. `authenticate_r7_go()` calls `_verify_r7_preflight()`, which reads the code manifest from that checkout and passes `repo=REPO` to the frozen validator. See [factory root definition](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory.py:35), [code-manifest resolution](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory.py:405), [validator call](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory.py:500), and [authentication call chain](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory.py:649).

`validate_manifest()` checks every binding, but first checks the nested code manifest. The actual read-only reproduction exited **1** with:

```text
R7PreflightError: code binding hash drifted: src/mcrl/algorithms/ee_axis_v014_head.py
```

That comes from [the nested code-manifest loop](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py:184); the subsequent [launch-manifest loop](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py:312) contains the quoted `launch binding hash drifted` failure.

**Claim 2: confirmed for the inspected code and hashes.**

I hashed all **169 preflight bindings** and all **166 nested code-manifest bindings**. Both censuses found exactly these two mismatches:

| File | Frozen R7 SHA-256 | Live SHA-256 |
|---|---|---|
| `ee_axis_lcsrs_three_route.py` | `db8f2f1c5dbcbbc42e6cfc7aa13a9fb1a783b6737388f1183deddf2f983cd340` | `2dcf2c0f79ffe8aea437fbb26155e856252e0244038e08c7f5333e7005532aa5` |
| `ee_axis_v014_head.py` | `b1ac88edd16cbe19a0b9ffc8371c1bf15f161ebdb656802d801db21c15183fa8` | `585d2274eeba02ab9f8ef34c2dd745789eaa9a8d8238ace7fe2c85b60de9d265` |

The frozen bindings are in [R7-PREFLIGHT-MANIFEST.json](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/R7-PREFLIGHT-MANIFEST.json:1).

The live typed batch is defined at [V0.14 head:43](/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/ee_axis_v014_head.py:43), imported by [target adapter:29](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-target-batch-adapter/target_batch_adapter.py:29) and [bridge:26](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-provider-orchestrator-bridge/v023_provider_orchestrator_bridge.py:26). The factory loads that bridge at import time. The [three-route configuration](/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/ee_axis_lcsrs_three_route.py:183), [checkpoint version check](/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/ee_axis_lcsrs_three_route.py:459), [trainer C2 path](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-heterogeneous-trainer/v023_heterogeneous_trainer.py:307), and [runner configuration loader](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py:832) confirm the heterogeneous execution seam.

A separate fresh-process import of the fit adapter, gate, preflight, and schedule imported **neither conflicting module**. Its repository closure contained **18 R7-bound files, all hash-identical**, plus the newer schedule. This agrees with the [fit imports](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_fit_adapter.py:48) and [schedule imports](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-source-schedule/v023_c3_source_schedule.py:24).

**Claim 3: confirmed as an execution incompatibility; V1’s successful operation is not established.**

The launcher copies the seed, overlays manifest entries, and then invokes R7 preflight against the **overlaid checkout**. See [launcher:305–332](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh:305).

A remote read confirmed the five named runtime files are absent from the seed. Locally, the regenerated manifest contains **88 entries, including 53 `mcrl` files**; a fresh factory import loaded exactly those 53, with no unlisted `mcrl` imports. The [manifest builder](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/build_v023_100e_launch_manifest.py:68) lists that closure.

Thus the unchanged factory cannot authenticate the overlaid learner tree; restoring historical dependencies defeats the current learner seam.

V1 does pin `db8f…` at [manifest:33](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome/V023-100E-LAUNCH-MANIFEST.sha256:33) and uses [shared `q12` configuration](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome/V023-100E-MODEL-CONFIG.json:2). That proves historical alignment, not an end-to-end successful run.

**Claim 4: qualified confirmation.**

The fit/composition adapters do not directly use `EEAxisLCSRSThreeRoute`; stored historical snapshot digests need not change when their bytes are retained. However, **the live snapshot constructor and digest algorithm are not backward-compatible**: two new required fields participate in hashing. See [snapshot hashing and fields](/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/ee_axis_lcsrs_three_route.py:90). The frozen source adapter’s [constructor call](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:893) supplies neither field.

Therefore A must preserve historical snapshot digests as authenticated artifact data; it must not reconstruct them using the live snapshot class.

Also, “sealed R7 root” is not verified current state. The [R3 repair contract:117–128](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-domain-repair-r3/V023-R7-FINAL-VERIFIER-DOMAIN-REPAIR-CONTRACT-2026-09-07.md:117) explicitly records an unsealed R7-I1 root. Follow-up SSH was blocked, so I did not authenticate current whole-root seals or reopen the remote shards.

I did not locate the exact `ADOPT_HETERO_Q2_448` ruling or the quoted R6 clean-room audit. Their historical attribution remains unverified. The [V2 contract:14–17](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md:14) independently establishes the required 228/448 model.

**2. Ruling and residual risk**

A is justified because the incompatible files belong to historical source generation and newer learner execution, while the authentication runtime currently remains byte-identical.

Merely replacing `repo=REPO` is insufficient: a valid historical seed must not conceal a changed verifier executing in the learner checkout.

B adds serialization, identity, sampler-resume, and file-backed-provider contracts. Moreover, the current provider cannot simply be built unchanged in the historical tree. Keep B as a fallback if authentication acquires an unavoidable incompatible dependency.

C violates the current model contract.

Residual risks are incomplete import coverage, mutable roots between verification and use, and confusing preserved artifact hashes with proof of historical execution. Address these through checked execution provenance, isolated processes, protected checkouts, and existing artifact/launch receipts. A supplies no missing GO evidence and makes no scientific acceptance claim.

**3. Exact implementation specification for A**

Implement a **versioned successor**, retaining frozen manifests and historical implementations. Do not overwrite an existing frozen manifest to accommodate the change.

Use a required **provider-config field**, with schema bump:

```json
"schema": "multi-catfish-mcrl-v023-post-r7-provider-factory-config-v2",
"r7_code_root": "/home/sat/mcrl-v023-r7-launch-ready-20260906-r4"
```

Retain the existing fields and values. Bump factory and identity schemas to `v2`. Keep the two existing environment variables solely for the canonical config path and its expected SHA-256. No independent environment override or implicit fallback supplies the code root. Any retained launcher seed override must resolve to the configured root or fail.

Changes to the versioned successor of `v023_post_r7_provider_factory.py`:

| Function/type | Required change |
|---|---|
| `PostR7ProviderConfig.__post_init__()` | Require an absolute `Path` for `r7_code_root`; retain existing seed/budget validation. |
| `PostR7ProviderConfig.from_payload()` | Require the exact v2 field set; reject missing fields, v1, wrong types, and unknown fields. |
| `_config_from_environment()` | Preserve canonical-byte/hash authentication and parse v2; no default root. |
| `authenticate_r7_go(root, *, r7_code_root)` | Require the argument; validate its directory and separation from the learner checkout. Preserve COMPLETE, whole-tree manifest, authority, source-panel, and GO checks. Pass the root explicitly downstream. |
| `_verify_r7_preflight(..., r7_code_root=...)` | Resolve **both** code-manifest files beneath the supplied root using fixed repository-relative paths. Match their hashes to the sealed authority/result. Check the seed’s preflight manifest/sidecar against that same authority. Call unchanged `validate_manifest()` with the sealed manifest/sidecar and `repo=r7_code_root`, plus its preregistration path. Preserve all receipt checks. |
| New `_verify_r7_authentication_runtime()` | Authenticate the live copies of the 18 shared authentication files against their R7 bindings; verify loaded origins belong to the learner checkout. Return an auditable binding list and its canonical hash. |
| `R7GoAuthentication` | Carry the resolved code root, verified preflight/code-manifest hashes, result-manifest hash, and authentication-runtime binding hash. |
| `build_provider()` | Forward the configured root and incorporate verified provenance into identity. Preserve target authentication, schedule validation, and bridge construction. |
| `make_provider()` | Retain its zero-argument interface. |

Do not globally reassign `REPO`, put the seed on the learner’s import path, or use `sys.modules` aliases to switch historical/live implementations.

The explicit shared-runtime list is the three R7 modules—preflight, gate, fit adapter—and these 15 `mcrl` files:

```text
__init__.py
errors.py
algorithms/__init__.py
algorithms/ee_axis_lcsrs_c3_head.py
env/__init__.py
env/action_contract.py
runtime/__init__.py
runtime/ee_axis_lcsrs_c3_dataset.py
runtime/ee_axis_lcsrs_c3_gate_fit.py
runtime/ee_axis_lcsrs_c3_gate_metrics.py
runtime/ee_axis_lcsrs_c3_learner.py
runtime/ee_axis_lcsrs_c3_placebo.py
runtime/ee_axis_lcsrs_c3_source_artifact.py
runtime/ee_axis_lcsrs_c3_state.py
runtime/finiteness.py
```

A fresh-process closure test must detect additions to this list. The newer schedule and remaining learner dependencies stay bound by the successor 100E manifest.

Add these fields to the provider identity payload, populated from successful verification:

```text
r7_code_root                         canonical resolved path
r7_preflight_manifest_sha256         sealed authority manifest
r7_code_manifest_sha256              verified historical code manifest
r7_result_manifest_sha256            COMPLETE-bound result-tree manifest
r7_gate_result_sha256                authenticated result.json
r7_authentication_runtime_sha256     checked path/hash list
```

Retain the checked runtime list in the receipt so its hash can be recomputed. Retain all existing identity fields. The [100E input binding](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/preflight_v023_100e_source_training.py:251) already carries the provider payload; require the new fields there. Continue binding the learner manifest separately through `code_sha256`, avoiding a config/manifest hash cycle.

Launcher order:

1. Verify the successor launch manifest/config pins and prerequisite whole-root seals.
2. Validate distinct seed, learner-checkout, and output paths; reject existing output/checkouts.
3. Copy the historical seed into the new checkout.
4. Run frozen R7 preflight against **the seed**, using authority-bound manifest bytes.
5. Overlay the successor learner manifest entries.
6. Verify every learner-manifest entry before importing factory/runner code.
7. Run factory preflight in a fresh learner process using the v2 config and explicit historical root; retain both provenance bindings.
8. Complete the nonformal diagnostic and receipt checks before formal launch. Reauthenticate at controller startup; preserve all frozen parameters.

Required tests, using disposable copies only:

| Test | Required result |
|---|---|
| Historical seed + live heterogeneous checkout | Full historical closure passes; factory imports; actual sealed GO/target artifacts build all route/source batches; Q1=228, Q2=448; checkpoint v2 works. No authentication mocks in this acceptance test. |
| Deterministic reconstruction | Repeated builds yield identical identity, schedule, batches, and sampler continuation. Historical snapshot digests remain unchanged. |
| One drifted seed binding | Fail for either conflicting module **and** an unrelated historical binding; proves the full closure remains enforced. |
| Wrong nested manifest/sidecar | Fail even if the surrounding seed otherwise looks valid. |
| Code root equals learner checkout | Fail, including alternate spellings/aliases resolving to the same directory. Reject symlink/escape cases. |
| Missing `r7_code_root`, v1 schema, relative path, wrong config SHA | Fail before provider construction. |
| Valid seed, drifted executing authentication file | Fail through learner-manifest/runtime checks. The seed cannot mask this drift. |
| Missing COMPLETE, corrupt manifests, non-GO, corrupt target | Preserve existing fail-closed behavior. |
| Provenance tampering | Missing/changed identity fields or mismatched receipt bindings are rejected; changing to another accepted root changes the path-bound identity. |
| Exact launcher integration | Exercise seed-check → overlay → learner-check → factory-preflight order; any failure prevents runner launch. A local `--dry-run` alone is insufficient. |

The real-artifact positive test remains pending until authentic prerequisite roots are available.

**4. Why the repair loop occurs**

The diagnosis is **substantially supported, but its historical absolute is unproven**.

The demonstrated chain is:

- **Digest domain:** the [source loader/writer domain](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_source_artifact.py:117) is `source-array-v1`; the [final NPZ loader](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:196) applies the composition domain.
- **Sibling import:** this is specifically a repair-entrypoint/import-context defect, documented in [R2:38–55](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-domain-repair-r2/V023-R7-FINAL-VERIFIER-DOMAIN-REPAIR-CONTRACT-2026-09-07.md:38).
- **Broadcast:** [final verifier:896–901](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:896) compares different shapes without broadcasting; [R3:59–63](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-domain-repair-r3/V023-R7-FINAL-VERIFIER-DOMAIN-REPAIR-CONTRACT-2026-09-07.md:59) documents the real-shard diagnosis.
- **Missing pair keys:** the [source schema](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/SOURCE-ARTIFACT-SCHEMA.md:141) and [source writer](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1189) omit both arrays. The [composition writer](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3018) emits them, and the [final join](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1018) requires them on both sides, producing the stated error at line 1038.

The fourth mismatch is code/schema-proven; I did not independently reopen every remote NPZ or verify its terminal failure log.

The test gap is concrete. [W201](/home/u24/papers/mcrl-leo-handover/tests/test_w201_ee_axis_lcsrs_final_verifier.py:1) tests an earlier verifier with synthetic inputs; its [NPZ fixture](/home/u24/papers/mcrl-leo-handover/tests/test_w201_ee_axis_lcsrs_final_verifier.py:287) derives expected hashes from the verifier’s own domain. [Factory tests](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-post-r7-provider-factory/test_v023_post_r7_provider_factory.py:317) mock major authentication/construction seams. These tests cannot establish real producer-to-consumer compatibility. They do not prove nobody ever attempted an end-to-end run.

**A read-only, non-fail-fast inventory is the right next step**, before another narrowly frozen repair:

1. Inventory all expected 8 source, 48 fit, and 48 composition shards, seals, schemas, array names/dtypes/shapes/domains, and cross-shard identity requirements.
2. Report each check as PASS, FAIL, or BLOCKED by a named prerequisite. Continue independent checks after failures; never convert skipped checks into passes or emit a scientific token.
3. Separate actual missing evidence from fields recoverable unambiguously from authenticated source data.
4. For pair keys, investigate derivation from source topology records, physical keys, references, users, actions, and pair IDs. Compare independently derived values with composition evidence. Never copy composition values into the supposed source evidence or silently drop the check.
5. Consolidate demonstrated defects into one versioned repair; validate it against real preserved artifacts and mutation-negative cases before freezing its release.

Keep formal verification fail-closed. The improvement is broader diagnostic visibility and production-schema integration coverage before another repair freeze.

DECISION: A — Adopt explicit historical R7 code-root authentication with separately bound learner execution and checked authentication-runtime provenance, while withholding launch until authentic sealed GO inputs and the specified integration tests pass.
tokens used
201,433
**Decision memo — R7 provenance and learner execution**

**Adopt A, with explicit checks on both the historical code root and the authentication code actually executing.** This resolves the demonstrated incompatibility without changing the learner or weakening R7’s frozen checks. It does not establish that the prerequisite artifacts currently satisfy the GO admission gate.

Audit snapshot: `main@42a8247c3fe3078070828f1d3d3f3eec7b4009c2`, dirty working tree, 2026-09-07. I modified no files. Concurrent edits corrected the launcher’s initially inconsistent hash constants; the final checked 88-entry launch manifest had SHA-256 `5b2267d40a890b79e9b99e640e904d3a1c0085192ed27b8d388a22545d93cca5`.

**1. Findings on claims 1–4**

**Claim 1: confirmed, with an earlier failure than the quoted message.**

The factory derives `REPO` from its own location. `authenticate_r7_go()` calls `_verify_r7_preflight()`, which reads the code manifest from that checkout and passes `repo=REPO` to the frozen validator. See [factory root definition](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory.py:35), [code-manifest resolution](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory.py:405), [validator call](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory.py:500), and [authentication call chain](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory.py:649).

`validate_manifest()` checks every binding, but first checks the nested code manifest. The actual read-only reproduction exited **1** with:

```text
R7PreflightError: code binding hash drifted: src/mcrl/algorithms/ee_axis_v014_head.py
```

That comes from [the nested code-manifest loop](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py:184); the subsequent [launch-manifest loop](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py:312) contains the quoted `launch binding hash drifted` failure.

**Claim 2: confirmed for the inspected code and hashes.**

I hashed all **169 preflight bindings** and all **166 nested code-manifest bindings**. Both censuses found exactly these two mismatches:

| File | Frozen R7 SHA-256 | Live SHA-256 |
|---|---|---|
| `ee_axis_lcsrs_three_route.py` | `db8f2f1c5dbcbbc42e6cfc7aa13a9fb1a783b6737388f1183deddf2f983cd340` | `2dcf2c0f79ffe8aea437fbb26155e856252e0244038e08c7f5333e7005532aa5` |
| `ee_axis_v014_head.py` | `b1ac88edd16cbe19a0b9ffc8371c1bf15f161ebdb656802d801db21c15183fa8` | `585d2274eeba02ab9f8ef34c2dd745789eaa9a8d8238ace7fe2c85b60de9d265` |

The frozen bindings are in [R7-PREFLIGHT-MANIFEST.json](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/R7-PREFLIGHT-MANIFEST.json:1).

The live typed batch is defined at [V0.14 head:43](/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/ee_axis_v014_head.py:43), imported by [target adapter:29](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-target-batch-adapter/target_batch_adapter.py:29) and [bridge:26](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-provider-orchestrator-bridge/v023_provider_orchestrator_bridge.py:26). The factory loads that bridge at import time. The [three-route configuration](/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/ee_axis_lcsrs_three_route.py:183), [checkpoint version check](/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/ee_axis_lcsrs_three_route.py:459), [trainer C2 path](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-heterogeneous-trainer/v023_heterogeneous_trainer.py:307), and [runner configuration loader](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py:832) confirm the heterogeneous execution seam.

A separate fresh-process import of the fit adapter, gate, preflight, and schedule imported **neither conflicting module**. Its repository closure contained **18 R7-bound files, all hash-identical**, plus the newer schedule. This agrees with the [fit imports](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_fit_adapter.py:48) and [schedule imports](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-source-schedule/v023_c3_source_schedule.py:24).

**Claim 3: confirmed as an execution incompatibility; V1’s successful operation is not established.**

The launcher copies the seed, overlays manifest entries, and then invokes R7 preflight against the **overlaid checkout**. See [launcher:305–332](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh:305).

A remote read confirmed the five named runtime files are absent from the seed. Locally, the regenerated manifest contains **88 entries, including 53 `mcrl` files**; a fresh factory import loaded exactly those 53, with no unlisted `mcrl` imports. The [manifest builder](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/build_v023_100e_launch_manifest.py:68) lists that closure.

Thus the unchanged factory cannot authenticate the overlaid learner tree; restoring historical dependencies defeats the current learner seam.

V1 does pin `db8f…` at [manifest:33](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome/V023-100E-LAUNCH-MANIFEST.sha256:33) and uses [shared `q12` configuration](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome/V023-100E-MODEL-CONFIG.json:2). That proves historical alignment, not an end-to-end successful run.

**Claim 4: qualified confirmation.**

The fit/composition adapters do not directly use `EEAxisLCSRSThreeRoute`; stored historical snapshot digests need not change when their bytes are retained. However, **the live snapshot constructor and digest algorithm are not backward-compatible**: two new required fields participate in hashing. See [snapshot hashing and fields](/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/ee_axis_lcsrs_three_route.py:90). The frozen source adapter’s [constructor call](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:893) supplies neither field.

Therefore A must preserve historical snapshot digests as authenticated artifact data; it must not reconstruct them using the live snapshot class.

Also, “sealed R7 root” is not verified current state. The [R3 repair contract:117–128](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-domain-repair-r3/V023-R7-FINAL-VERIFIER-DOMAIN-REPAIR-CONTRACT-2026-09-07.md:117) explicitly records an unsealed R7-I1 root. Follow-up SSH was blocked, so I did not authenticate current whole-root seals or reopen the remote shards.

I did not locate the exact `ADOPT_HETERO_Q2_448` ruling or the quoted R6 clean-room audit. Their historical attribution remains unverified. The [V2 contract:14–17](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md:14) independently establishes the required 228/448 model.

**2. Ruling and residual risk**

A is justified because the incompatible files belong to historical source generation and newer learner execution, while the authentication runtime currently remains byte-identical.

Merely replacing `repo=REPO` is insufficient: a valid historical seed must not conceal a changed verifier executing in the learner checkout.

B adds serialization, identity, sampler-resume, and file-backed-provider contracts. Moreover, the current provider cannot simply be built unchanged in the historical tree. Keep B as a fallback if authentication acquires an unavoidable incompatible dependency.

C violates the current model contract.

Residual risks are incomplete import coverage, mutable roots between verification and use, and confusing preserved artifact hashes with proof of historical execution. Address these through checked execution provenance, isolated processes, protected checkouts, and existing artifact/launch receipts. A supplies no missing GO evidence and makes no scientific acceptance claim.

**3. Exact implementation specification for A**

Implement a **versioned successor**, retaining frozen manifests and historical implementations. Do not overwrite an existing frozen manifest to accommodate the change.

Use a required **provider-config field**, with schema bump:

```json
"schema": "multi-catfish-mcrl-v023-post-r7-provider-factory-config-v2",
"r7_code_root": "/home/sat/mcrl-v023-r7-launch-ready-20260906-r4"
```

Retain the existing fields and values. Bump factory and identity schemas to `v2`. Keep the two existing environment variables solely for the canonical config path and its expected SHA-256. No independent environment override or implicit fallback supplies the code root. Any retained launcher seed override must resolve to the configured root or fail.

Changes to the versioned successor of `v023_post_r7_provider_factory.py`:

| Function/type | Required change |
|---|---|
| `PostR7ProviderConfig.__post_init__()` | Require an absolute `Path` for `r7_code_root`; retain existing seed/budget validation. |
| `PostR7ProviderConfig.from_payload()` | Require the exact v2 field set; reject missing fields, v1, wrong types, and unknown fields. |
| `_config_from_environment()` | Preserve canonical-byte/hash authentication and parse v2; no default root. |
| `authenticate_r7_go(root, *, r7_code_root)` | Require the argument; validate its directory and separation from the learner checkout. Preserve COMPLETE, whole-tree manifest, authority, source-panel, and GO checks. Pass the root explicitly downstream. |
| `_verify_r7_preflight(..., r7_code_root=...)` | Resolve **both** code-manifest files beneath the supplied root using fixed repository-relative paths. Match their hashes to the sealed authority/result. Check the seed’s preflight manifest/sidecar against that same authority. Call unchanged `validate_manifest()` with the sealed manifest/sidecar and `repo=r7_code_root`, plus its preregistration path. Preserve all receipt checks. |
| New `_verify_r7_authentication_runtime()` | Authenticate the live copies of the 18 shared authentication files against their R7 bindings; verify loaded origins belong to the learner checkout. Return an auditable binding list and its canonical hash. |
| `R7GoAuthentication` | Carry the resolved code root, verified preflight/code-manifest hashes, result-manifest hash, and authentication-runtime binding hash. |
| `build_provider()` | Forward the configured root and incorporate verified provenance into identity. Preserve target authentication, schedule validation, and bridge construction. |
| `make_provider()` | Retain its zero-argument interface. |

Do not globally reassign `REPO`, put the seed on the learner’s import path, or use `sys.modules` aliases to switch historical/live implementations.

The explicit shared-runtime list is the three R7 modules—preflight, gate, fit adapter—and these 15 `mcrl` files:

```text
__init__.py
errors.py
algorithms/__init__.py
algorithms/ee_axis_lcsrs_c3_head.py
env/__init__.py
env/action_contract.py
runtime/__init__.py
runtime/ee_axis_lcsrs_c3_dataset.py
runtime/ee_axis_lcsrs_c3_gate_fit.py
runtime/ee_axis_lcsrs_c3_gate_metrics.py
runtime/ee_axis_lcsrs_c3_learner.py
runtime/ee_axis_lcsrs_c3_placebo.py
runtime/ee_axis_lcsrs_c3_source_artifact.py
runtime/ee_axis_lcsrs_c3_state.py
runtime/finiteness.py
```

A fresh-process closure test must detect additions to this list. The newer schedule and remaining learner dependencies stay bound by the successor 100E manifest.

Add these fields to the provider identity payload, populated from successful verification:

```text
r7_code_root                         canonical resolved path
r7_preflight_manifest_sha256         sealed authority manifest
r7_code_manifest_sha256              verified historical code manifest
r7_result_manifest_sha256            COMPLETE-bound result-tree manifest
r7_gate_result_sha256                authenticated result.json
r7_authentication_runtime_sha256     checked path/hash list
```

Retain the checked runtime list in the receipt so its hash can be recomputed. Retain all existing identity fields. The [100E input binding](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/preflight_v023_100e_source_training.py:251) already carries the provider payload; require the new fields there. Continue binding the learner manifest separately through `code_sha256`, avoiding a config/manifest hash cycle.

Launcher order:

1. Verify the successor launch manifest/config pins and prerequisite whole-root seals.
2. Validate distinct seed, learner-checkout, and output paths; reject existing output/checkouts.
3. Copy the historical seed into the new checkout.
4. Run frozen R7 preflight against **the seed**, using authority-bound manifest bytes.
5. Overlay the successor learner manifest entries.
6. Verify every learner-manifest entry before importing factory/runner code.
7. Run factory preflight in a fresh learner process using the v2 config and explicit historical root; retain both provenance bindings.
8. Complete the nonformal diagnostic and receipt checks before formal launch. Reauthenticate at controller startup; preserve all frozen parameters.

Required tests, using disposable copies only:

| Test | Required result |
|---|---|
| Historical seed + live heterogeneous checkout | Full historical closure passes; factory imports; actual sealed GO/target artifacts build all route/source batches; Q1=228, Q2=448; checkpoint v2 works. No authentication mocks in this acceptance test. |
| Deterministic reconstruction | Repeated builds yield identical identity, schedule, batches, and sampler continuation. Historical snapshot digests remain unchanged. |
| One drifted seed binding | Fail for either conflicting module **and** an unrelated historical binding; proves the full closure remains enforced. |
| Wrong nested manifest/sidecar | Fail even if the surrounding seed otherwise looks valid. |
| Code root equals learner checkout | Fail, including alternate spellings/aliases resolving to the same directory. Reject symlink/escape cases. |
| Missing `r7_code_root`, v1 schema, relative path, wrong config SHA | Fail before provider construction. |
| Valid seed, drifted executing authentication file | Fail through learner-manifest/runtime checks. The seed cannot mask this drift. |
| Missing COMPLETE, corrupt manifests, non-GO, corrupt target | Preserve existing fail-closed behavior. |
| Provenance tampering | Missing/changed identity fields or mismatched receipt bindings are rejected; changing to another accepted root changes the path-bound identity. |
| Exact launcher integration | Exercise seed-check → overlay → learner-check → factory-preflight order; any failure prevents runner launch. A local `--dry-run` alone is insufficient. |

The real-artifact positive test remains pending until authentic prerequisite roots are available.

**4. Why the repair loop occurs**

The diagnosis is **substantially supported, but its historical absolute is unproven**.

The demonstrated chain is:

- **Digest domain:** the [source loader/writer domain](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_source_artifact.py:117) is `source-array-v1`; the [final NPZ loader](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:196) applies the composition domain.
- **Sibling import:** this is specifically a repair-entrypoint/import-context defect, documented in [R2:38–55](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-domain-repair-r2/V023-R7-FINAL-VERIFIER-DOMAIN-REPAIR-CONTRACT-2026-09-07.md:38).
- **Broadcast:** [final verifier:896–901](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:896) compares different shapes without broadcasting; [R3:59–63](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-domain-repair-r3/V023-R7-FINAL-VERIFIER-DOMAIN-REPAIR-CONTRACT-2026-09-07.md:59) documents the real-shard diagnosis.
- **Missing pair keys:** the [source schema](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/SOURCE-ARTIFACT-SCHEMA.md:141) and [source writer](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1189) omit both arrays. The [composition writer](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3018) emits them, and the [final join](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1018) requires them on both sides, producing the stated error at line 1038.

The fourth mismatch is code/schema-proven; I did not independently reopen every remote NPZ or verify its terminal failure log.

The test gap is concrete. [W201](/home/u24/papers/mcrl-leo-handover/tests/test_w201_ee_axis_lcsrs_final_verifier.py:1) tests an earlier verifier with synthetic inputs; its [NPZ fixture](/home/u24/papers/mcrl-leo-handover/tests/test_w201_ee_axis_lcsrs_final_verifier.py:287) derives expected hashes from the verifier’s own domain. [Factory tests](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-post-r7-provider-factory/test_v023_post_r7_provider_factory.py:317) mock major authentication/construction seams. These tests cannot establish real producer-to-consumer compatibility. They do not prove nobody ever attempted an end-to-end run.

**A read-only, non-fail-fast inventory is the right next step**, before another narrowly frozen repair:

1. Inventory all expected 8 source, 48 fit, and 48 composition shards, seals, schemas, array names/dtypes/shapes/domains, and cross-shard identity requirements.
2. Report each check as PASS, FAIL, or BLOCKED by a named prerequisite. Continue independent checks after failures; never convert skipped checks into passes or emit a scientific token.
3. Separate actual missing evidence from fields recoverable unambiguously from authenticated source data.
4. For pair keys, investigate derivation from source topology records, physical keys, references, users, actions, and pair IDs. Compare independently derived values with composition evidence. Never copy composition values into the supposed source evidence or silently drop the check.
5. Consolidate demonstrated defects into one versioned repair; validate it against real preserved artifacts and mutation-negative cases before freezing its release.

Keep formal verification fail-closed. The improvement is broader diagnostic visibility and production-schema integration coverage before another repair freeze.

DECISION: A — Adopt explicit historical R7 code-root authentication with separately bound learner execution and checked authentication-runtime provenance, while withholding launch until authentic sealed GO inputs and the specified integration tests pass.
