# V0.23 C1/C2 successor provider factory v3

`v023_c1c2_provider_factory_v3.py` is a new, fail-closed two-route factory for
the successor source-training runner. It is not a relaxed post-R7 factory and
has no R7 admission dependency.

The factory authenticates:

- the canonical, digest-bound provider configuration loaded from
  `MCRL_V023_C1C2_PROVIDER_CONFIG_PATH` and
  `MCRL_V023_C1C2_PROVIDER_CONFIG_SHA256`;
- the configured target root's `COMPLETE`, `MANIFEST.sha256`, `receipt.json`,
  every manifest-listed file, exact informed/neutral × worlds
  `2026121705..2026121712` shard topology, producer header and formula constants,
  typed 228-D C1 and feature-major 448-D C2 batches,
  legal masks, and receipt-to-row bindings through the existing authenticated
  target adapter;
- the separately digest-bound successor learner manifest selected by
  `MCRL_V023_C1C2_LEARNER_MANIFEST_PATH` (or the fixed sibling default), every
  listed runtime file, its SHA-256, and its live natural module origin. The
  mandatory closure includes the successor model, orchestrator and runner,
  the reused heterogeneous trainer, and the imported three-route snapshot
  helper module; and
- the factory, target-adapter, provider-protocol, contract, model-config,
  target, learner-manifest, train-seed, epoch-budget, and planned consumed-file
  identities in `provider_identity`.

The configuration must bind train seed `2927175120652069826` and model-config
SHA-256 `9eafcd184bd0ec015498832be61b5c95a71373e98f63ab804c9654775a8b1d5d`.

The learner manifest is canonical JSON with the exact fields `schema`,
`status`, `claim_ceiling`, and `bindings`. Each path-sorted binding has exactly
`path`, `module`, and `sha256`. Its schema is
`multi-catfish-mcrl-v023-c1c2-successor-learner-manifest-v1`, its status is
`FROZEN`, and its claim ceiling is the successor source-training claim ceiling.

The provider emits only `C1` raw-surplus `EEAxisPairBatch` values and `C2`
already-normalized `EEAxisV014NormalizedPairBatch` values. It never divides C2
targets by kappa. Requests and sampler restoration must follow the deterministic
`C1 -> C2`, neutral-then-informed cursor order. Target and learner digests are
rechecked before each provider operation.

This package does not authenticate scientific efficacy, physical deployment
benefit, TEST performance, simulator execution, learner convergence, or any C3
admission. It performs no learner update, target generation, simulator run, or
artifact write outside caller-provided test/runtime state.

Run the isolated tests with:

```bash
./.venv/bin/python -m pytest -q .scratch/multi-catfish-v023-c1c2-provider-factory-v3
```
