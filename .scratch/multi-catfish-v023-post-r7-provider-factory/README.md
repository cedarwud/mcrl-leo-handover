# V0.23 post-R7 provider factory

This isolated implementation seam closes the remaining pre-learner wiring
gap. It does not modify the source-training runner, simulator, learner, TEST
split, or any shared authority file.

`make_provider()` is a zero-argument provider factory for the unchanged
five-arm source-training runner. It requires these exact environment variables:

```text
MCRL_V023_POST_R7_PROVIDER_CONFIG_PATH=/absolute/path/post-r7-provider.json
MCRL_V023_POST_R7_PROVIDER_CONFIG_SHA256=<sha256-of-the-config-bytes>
```

The canonical JSON config has exactly this shape:

```json
{"epoch_budget":100,"r7_root":"/home/sat/mcrl-v023-lcsrs-gate-...","schedule_seed":2026090701,"schema":"multi-catfish-mcrl-v023-post-r7-provider-factory-config-v1","target_root":"/home/sat/mcrl-v023-c1c2-targets-..."}
```

The config is required to be an absolute-path, canonical ASCII JSON regular
file, and its externally supplied SHA-256 must match before any result is
opened. `epoch_budget` is frozen to 100 or 500; the source runner still owns
the later budget authority for budgets above 100.

## Authentication and construction

1. `authenticate_r7_go()` first requires `COMPLETE`, authenticates the entire
   R7 `MANIFEST.sha256` tree, and only then reads `result.json` and
   `verification.json`.
2. It authenticates the authority preflight snapshot, reconstructs all eight
   typed source worlds through the audited fit adapter, computes the canonical
   record-panel digest, and constructs the current `R7GoDecisionBinding`.
   A pre-outcome launch token, an unsealed root, a missing world, a changed
   source record, or a non-GO result fails closed.
3. `build_provider()` reopens the completed C1/C2 target artifact, builds the
   deterministic paired C3 informed/neutral schedule from the same records,
   validates the sealed schedule receipt, and connects both C3 source inputs to
   the existing bridge.
4. The returned thin facade delegates only `next_batch`, `sampler_state`, and
   `load_sampler_state`. Its compact `provider_identity` is bound to the
   authenticated target MANIFEST digest, C3 schedule receipt digest, epoch
   budget, and both C3 source IDs. `provider_identity_payload` exposes those
   fields for audit without changing the runner protocol.

No fallback source, filename inference, neutral-surface fabrication, outcome
tuning, simulator call, or artifact write is present in this seam.

Focused tests are synthetic and monkeypatch only the expensive external
artifact reconstruction; they do not inspect live or unsealed R7 outcomes.

```bash
.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-post-r7-provider-factory/test_v023_post_r7_provider_factory.py
```
