# V0.23 100-epoch pre-outcome screen bundle (V2)

This directory is the V2 execution-correction bundle for the first current
five-arm source-to-learner screen. V1 remains provenance only. V2 contains no
result and does not authorize a non-GO branch or bypass either prerequisite
seal.

The correction is execution-only: Q1 is the native 228-D action-shared head;
Q2 is the native V0.14 OPS-3 448-D action-set head; C2 labels are already
kappa-normalized exactly once; and all server paths are dedicated `r2` paths.
The fixed R7 C3 view/target is an offline source while Q1/Q2 update, so later
deployment covariate shift is measured rather than silently rebuilt.
DECISION A is integrated through provider factory/config/identity schema v2:
the immutable R7 seed authenticates the historical closure, while the launch
manifest separately binds the successor learner checkout.

Files:

- `V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md`: frozen parameters,
  admission, arm mapping, integrity decision, and next boundary.
- `V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.sha256`: contract digest.
- `V023-100E-MODEL-CONFIG.json`: exact runner-compatible current model config.
- `V023-100E-MODEL-CONFIG.sha256`: model-config digest.
- `V023-100E-POST-R7-PROVIDER-CONFIG.json`: canonical zero-argument provider
  factory v2 input for the sealed R7 and OPS-3 target roots, including the
  required immutable `r7_code_root`.
- `V023-100E-POST-R7-PROVIDER-CONFIG.sha256`: provider-config byte digest.
- `V023-100E-LAUNCH-MANIFEST.sha256`: current contract/config/code/test closure
  for the conditional server launch.

`V023-100E-LAUNCH-MANIFEST.sha256` is the canonical manifest over this V2
bundle and every current implementation file used by the runner, provider,
adapter, orchestrator, trainer, heads, and tests. Its external
`V023-100E-LAUNCH-MANIFEST-FROZEN.sha256` pin must match before launch.

The formal command is the V2 server launcher. It authenticates the manifest,
config pins, and prerequisite seals; copies the immutable R7 seed; runs frozen
R7 preflight against that seed before overlay; verifies every successor
learner-manifest entry after overlay; then runs factory v2 preflight in a fresh
process. Before it writes the controller or creates tmux, it also runs the
mandatory non-formal one-epoch provider diagnostic in a fresh
`<checkout>/v023-100e-one-epoch-diagnostic` root with the same checkout-local
`PYTHONPATH` and environment as factory preflight. The launcher authenticates
the diagnostic receipt and sidecar, requires
`PASS_ONE_EPOCH_PROVIDER_PLUMBING_DIAGNOSTIC`, requires `failed_checks == []`,
and requires its provider identity to equal the preflight input binding. It
then creates a fresh r2 checkout/output/session and waits only a bounded
interval for the tmux controller's write-once startup marker plus live session.
It does not run in this environment unless explicitly invoked by the parent
workflow; `--dry-run` performs no remote call.

The launcher's mandatory non-formal one-epoch diagnostic command is:

```text
ssh sat 'cd /home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r2-checkout && /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v023-100e-screen-preoutcome-v2/run_v023_one_epoch_provider_diagnostic.py --provider-config /home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r2-checkout/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-POST-R7-PROVIDER-CONFIG.json --model-config /home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r2-checkout/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-MODEL-CONFIG.json --output-root /home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r2-checkout/v023-100e-one-epoch-diagnostic'
```

That diagnostic is expressly outside the formal 100E contract, writes to its
separate checkout-local diagnostic root, and cannot create a formal `COMPLETE` result or
change the 100E runner. The launcher treats it only as a pre-controller
execution-plumbing gate; it is not an EE, efficacy, or scientific result.

## V2 correction status (2026-09-07, controller session)

- Target root is now the corrected r8 path
  `/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8` (provider config,
  contract §0/§1, verifier, launcher default/guard); the R7 result root remains
  `/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1`.
- Provider config/factory/identity are schema v2. The configured historical
  code root is `/home/sat/mcrl-v023-r7-launch-ready-20260906-r4`; the launcher
  refuses a divergent seed override, authenticates R7 against that seed before
  learner overlay, and verifies the overlaid learner manifest before factory
  import. The controller reauthenticates through
  `v023_post_r7_provider_factory_v2:make_provider`.
- The generated controller retains the write-once startup marker
  (`v023-100e-source-training-startup.json`) before the runner starts, and the
  launcher waits at most 120 s for marker + live tmux
  (`V023_100E_SOURCE_TRAINING_STARTUP_ACKNOWLEDGED`), otherwise it dies.
- `V023-100E-LAUNCH-MANIFEST.sha256` is rebuilt by
  `build_v023_100e_launch_manifest.py --write` (90 entries: V2 package,
  provider factory v1+v2 modules/tests, learner seam modules/tests, governing
  docs, and the complete 53-file `mcrl` import closure of the seam). `--check`
  verifies manifest and pin without writing.
  Binding the whole closure is necessary because the R7 seed checkout lacks
  five learner runtime files and carries the R7-era `ee_axis_lcsrs_three_route.py`
  / `ee_axis_v014_head.py`.
- `run_v023_one_epoch_provider_diagnostic.py` (+ tests) is the mandatory
  non-formal one-epoch real-provider plumbing gate run and authenticated by
  the launcher before controller creation.
- NOT yet launchable. DECISION A code integration is complete, but launch still
  requires an authentically sealed R7 result root and an authentically sealed
  corrected r6 C1/C2 target root. No sealed-GO or scientific acceptance is
  claimed by this bundle.
