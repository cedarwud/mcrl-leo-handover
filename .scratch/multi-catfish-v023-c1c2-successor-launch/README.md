# V0.23 C1/C2 successor stage-A launch bundle

This directory is the formal, fail-closed launch surface for the three-arm,
two-route, 100-epoch successor source-training run. It does not open a
simulator episode, an efficacy claim, or a held-out split. It never edits the
development contract or the separately sealed scientific declaration.

## Freeze and launch order

The exact contract §8 order is:

> bind r8 digests → attach the astra review → seal this document's SHA-256 and
> the launch manifest → server one-epoch diagnostic → stage A → stage B →
> freeze stage C preflight → stage C rungs with receipts every 100 episodes →
> owner notification before 9000.

For this stage-A bundle, the executable portion is therefore:

1. On the server checkout, after the target root is sealed, run
   `bind_v023_c1c2_successor_freeze.py --write`. This writes the learner
   L-list manifest, factory-v3 configuration, execution bindings, and external
   sidecars. It only reads the contract and scientific declaration.
2. Attach/authenticate the named astra review, externally seal the unchanged
   contract digest through the launch manifest, then run
   `build_v023_c1c2_successor_launch_manifest.py --write`.
3. Run both scripts with `--check`. A missing stage-A placeholder binding,
   code drift, target drift, model/declaration sidecar mismatch, or circular
   self/manifest digest is fatal.
4. Run `sync_launch_v023_c1c2_successor_server.sh --dry-run` and inspect the
   exact commands. The real launch repeats bind/manifest checks, syncs only
   authenticated manifest paths, verifies the learner manifest on the server,
   performs factory preflight, and requires the non-formal one-epoch diagnostic
   PASS receipt before tmux is created.
5. The tmux controller runs `run_v023_c1c2_successor_formal.py`, which preserves
   a finite receipt for every one of the 200 route updates, then runs the
   independent verifier. Only the verifier may publish
   `PASS_SOURCE_TRAINING_INTEGRITY`, the output manifest, and `COMPLETE`.

The synchronized payload is intentionally a documented superset of the
authoritative 246-path shadow closure. Its exact set is the closure union the
closed `LAUNCH_MANIFEST_ADDITIONS` list in `successor_launch_common.py` (the ten
bundle source/documentation files, generated binder outputs when present, the
review, the closure-list authority, and the Stage-C code manifest plus its frozen
pin). The launch manifest and its sidecar are then transferred as the two
external authenticators; no closure-equality claim is made.

The fixed server identities are:

- checkout: `/home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1-checkout`
- output: `/home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1`
- tmux: `mcrl-v023-c1c2-successor-100e-r1`

The diagnostic uses the real authenticated target provider but writes model,
sampler, checkpoint, and receipt artifacts only under a fresh scratch root.
Its receipt carries `formal:false`; it can block launch but can never satisfy
or replace stage A.

## Files

- `bind_v023_c1c2_successor_freeze.py`: freeze-time bindings, learner L-list,
  provider configuration, git commit/tree identity, and dirty-state record.
- `build_v023_c1c2_successor_launch_manifest.py`: two-level payload manifest
  with a one-way external sidecar.
- `preflight_v023_c1c2_successor.py`: bindings/config/declaration/factory and
  absent-output authentication.
- `run_v023_c1c2_successor_one_epoch_diagnostic.py`: one-arm real-provider
  export/reload/continuation diagnostic with pre-update-Q2 behavioural check.
- `run_v023_c1c2_successor_formal.py`: stock-runner controller that adds the
  required per-update finite ledger.
- `verify_v023_c1c2_successor.py`: exact three-arm, 200-update, common-init,
  provider-route, export, storage-isolation, and epoch-100 resume verifier.
- `sync_launch_v023_c1c2_successor_server.sh`: authenticated sync, diagnostic,
  tmux launch, 120-second acknowledgement, and path handoff.

## Local tests

```bash
./.venv/bin/python -m pytest -q .scratch/multi-catfish-v023-c1c2-successor-launch
```

Fixtures are emitted by the real two-route runner/writer. Mutation negatives
cover unresolved freeze placeholders, a forbidden predecessor token, a fourth
arm, circular digest fields, and a failed diagnostic receipt.
