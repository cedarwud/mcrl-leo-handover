# Decision A provider-factory v2 implementation note

Status: the versioned provider-factory successor and its synthetic tests are
implemented in this directory. The successor 100E bundle has **not** been
changed. Frozen R7 manifests and v1 remain untouched. Authentic sealed GO and
target roots were unavailable, so the ruling's real-artifact positive test is
still pending and this note grants no launch or scientific acceptance.

## What the successor V2 bundle must adopt next

### 1. Canonical provider config v2

Add a new canonical JSON config with the exact field set
`{schema,r7_root,target_root,epoch_budget,schedule_seed,r7_code_root}`. Relative
to the existing adjudicated config, make these two changes:

```json
{
  "schema": "multi-catfish-mcrl-v023-post-r7-provider-factory-config-v2",
  "r7_code_root": "/home/sat/mcrl-v023-r7-launch-ready-20260906-r4"
}
```

Preserve the bundle's adjudicated `epoch_budget`, `schedule_seed`, `r7_root`,
and `target_root` values. Confirm that the named historical root is the
authenticated seed actually being used. Serialize the complete object as
sorted, compact, finite ASCII JSON with one trailing newline, calculate its
byte SHA-256, and update the bundle's config pin. Continue exporting only
`MCRL_V023_POST_R7_PROVIDER_CONFIG_PATH` and
`MCRL_V023_POST_R7_PROVIDER_CONFIG_SHA256`. Do not add an environment fallback
for `r7_code_root`. Any retained launcher seed override must resolve to the
configured `r7_code_root` or fail.

The successor launch manifest must bind the v2 factory module and the v2 config
bytes/digest. Do not alter either frozen R7 preflight manifest or the frozen R7
launch-code manifest to accommodate the successor.

### 2. Successor preflight and verifier EXPECTED values

Update the successor 100E preflight and verifier together so their fixed
expectations name and authenticate:

- config schema `multi-catfish-mcrl-v023-post-r7-provider-factory-config-v2`
  and its exact six-field set;
- factory schema `multi-catfish-mcrl-v023-post-r7-provider-factory-v2`;
- identity schema `multi-catfish-mcrl-v023-post-r7-provider-identity-v2`;
- the v2 factory relative path and byte SHA-256;
- the new canonical config relative path and byte SHA-256; and
- the regenerated successor learner-manifest digest/count after those new
  bindings are adopted.

Require the provider identity payload to retain every v1 field and also contain
all of:

```text
r7_code_root
r7_preflight_manifest_sha256
r7_code_manifest_sha256
r7_result_manifest_sha256
r7_gate_result_sha256
r7_authentication_runtime_sha256
r7_authentication_runtime
```

The verifier must independently recompute the canonical SHA-256 of
`r7_authentication_runtime`, require it to equal
`r7_authentication_runtime_sha256`, recompute the complete provider identity,
and require the resolved `r7_code_root` to equal the config value. It must keep
the successor learner closure bound separately through `code_sha256`; do not
create a config/manifest hash cycle. Missing, extra, changed, or mismatched
provenance fields must fail closed. Reauthenticate the provider at controller
startup rather than trusting an earlier receipt.

### 3. Required launcher order

The integrated launcher must implement and test this exact order:

1. Verify successor launch-manifest/config pins and prerequisite whole-root
   seals.
2. Validate that the historical seed, learner checkout, and output paths are
   distinct; reject pre-existing output/checkouts.
3. Copy the historical seed into the new checkout.
4. Run frozen R7 preflight against the seed using the authority-bound manifest
   bytes.
5. Overlay the successor learner-manifest entries.
6. Verify every learner-manifest entry before importing factory or runner code.
7. In a fresh learner process, run factory preflight with the v2 config and the
   explicit historical root; retain both historical and learner provenance.
8. Complete nonformal diagnostics and receipt checks before formal launch.
   Reauthenticate again at controller startup and preserve every frozen
   parameter.

The integration test must observe this sequence and prove that failure at any
step prevents runner launch. A local `--dry-run` alone is not sufficient. After
authentic prerequisite roots exist, also run the ruling's no-authentication-
mock positive test and deterministic reconstruction/continuation checks before
any launch authorization.
