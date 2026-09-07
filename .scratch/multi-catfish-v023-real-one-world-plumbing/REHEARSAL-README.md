# V0.23 fresh-model one-world plumbing rehearsal

This is a **non-formal dress rehearsal**, not source training, a trained
policy, gate evidence, or an efficacy result. It creates five independent
`EEAxisLCSRSThreeRoute` models from the V2 model JSON with the identical train
seed `2927175120652069826`. Their checkpoints truthfully carry
`update_count=0` and are written in the five-arm runner layout:

```text
<export-root>/exports/epoch-0000/
  00-ALL_NEUTRAL_CONTROL.current-ee-axis-lcsrs-three-route.pt
  01-FULL.current-ee-axis-lcsrs-three-route.pt
  02-DROP_C1.current-ee-axis-lcsrs-three-route.pt
  03-DROP_C2.current-ee-axis-lcsrs-three-route.pt
  04-DROP_C3.current-ee-axis-lcsrs-three-route.pt
  (one .sha256 sidecar beside each checkpoint)
<export-root>/exports/epoch-0000.json
```

The manifest explicitly says `formal: false` and
`models: UNTRAINED_FRESH_INITIALIZATION_NOT_A_TRAINED_POLICY`. Both the export
root and receipt root must be absent, live below this checkout's `.scratch`,
and have `REHEARSAL-UNTRAINED` in their final directory name. Nothing is
written to a sealed R7, target, 100E, or evaluation root. There is no TEST
argument or TEST code path.

## Current expected refusal

The rehearsal calls the existing
`v023_real_one_world_plumbing.load_current_five_arm_models` unchanged. The
current implementation refuses a truthful fresh checkpoint in
`load_current_model_checkpoint_state` because it calls
`_positive_int(state["update_count"], zero_allowed=False)`, requiring
`checkpoint.update_count >= 1`. The rehearsal does **not** disguise a fresh
model as update 1 and does not weaken this check.

The mandated existing package test also currently exposes a second, later
checkpoint-decoding defect: `_config_from_checkpoint_state` converts only the
serialized `q12` and `q3` mappings back to dataclasses, leaving the current
serialized `q1` and `q2` mappings as dictionaries. Consequently even its
positive-update fixture is rejected as `current checkpoint configuration is
incompatible`. This rehearsal does not patch or bypass that existing file.
After those loader checks are repaired in their owning package, its
`CurrentV023FixedPolicy.select_actions` call must also be rechecked against the
current required `capture_q12(..., q2_states=..., q2_action_masks=...)`
signature before claiming ten-step plumbing closure.

When that refusal occurs, the receipt status is
`BLOCKED_BY_EXISTING_PLUMBING_UNTRAINED_EXPORT_CHECK`. With the explicit
first-decision flag, the server then attempts only the smallest read-only
diagnostic: five fresh TRAIN environments, one common keyed field and initial
state, Q1 228-D capture, Q2 448-D OPS-3 capture, masks, current C3 provider,
and (if the provider authenticates) the Q1+Q2+Q3 masked argmax. It never calls
`environment.step`, so bits and energy remain unavailable and are recorded as
null. Any provider/sealed-root refusal is recorded verbatim and is not
bypassed.

## Exact server command

The checkout is
`/home/sat/mcrl-v023-learner-rehearsal-checkout-20260907`; use the shared
server interpreter exactly as follows (an exit status of `3` means the
expected existing-plumbing refusal was recorded):

```bash
cd /home/sat/mcrl-v023-learner-rehearsal-checkout-20260907 && \
/home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/multi-catfish-v023-real-one-world-plumbing/rehearsal_v023_one_world_plumbing_fresh_models.py \
  --export-root /home/sat/mcrl-v023-learner-rehearsal-checkout-20260907/.scratch/multi-catfish-v023-real-one-world-plumbing/V023-ONE-WORLD-EXPORTS-REHEARSAL-UNTRAINED \
  --output-root /home/sat/mcrl-v023-learner-rehearsal-checkout-20260907/.scratch/multi-catfish-v023-real-one-world-plumbing/V023-ONE-WORLD-RECEIPTS-REHEARSAL-UNTRAINED \
  --tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 \
  --model-config /home/sat/mcrl-v023-learner-rehearsal-checkout-20260907/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-MODEL-CONFIG.json \
  --execute-first-decision-diagnostic
```

Do not reuse either output path. Choose new absent sibling names, still ending
in a clear `REHEARSAL-UNTRAINED` marker, for a later attempt.

## Required checkout sync closure

In addition to the stated `src/` tree and V2 100E manifest overlay, sync these
directories for the plumbing package and its current C3 provider chain:

- `.scratch/multi-catfish-v023-real-one-world-plumbing/`
- `.scratch/multi-catfish-v023-physical/`
- `.scratch/multi-catfish-v023-current-c3view-provider/`
- `.scratch/multi-catfish-v023-r6-fit-binding-fix/`
- `.scratch/multi-catfish-v020-c3-source-audit/` (including its repriced fit)
- `.scratch/multi-catfish-v018-relational-zr/`
- `.scratch/multi-catfish-v015-c3-learned-context/`
- `.scratch/zero-energy-c3-v013/`
- `.scratch/c3-v04/`

The transitive current-provider authentication also reads its pinned documents
and artifact roots. Preserve the paths already named by those modules,
especially `docs/MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md`,
`artifacts/PREREG-FROZEN-2026-08-25-R2.json`, the V0.13 frozen authority, the
V0.14 learner-gate root, and the V0.20 repriced-Q1/Q2 fit files. Missing or
digest-mismatched inputs should remain a recorded provider blocker.

## Local tests (no simulator)

Only these two targets are in scope:

```bash
./.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-real-one-world-plumbing/test_rehearsal_v023_one_world_plumbing_fresh_models.py \
  .scratch/multi-catfish-v023-real-one-world-plumbing/test_v023_real_one_world_plumbing.py
```
