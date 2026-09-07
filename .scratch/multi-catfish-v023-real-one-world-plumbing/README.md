# V0.23 real one-world five-arm plumbing

Status: `PLUMBING_ONLY_FIXED_POLICY_TRAIN_NO_GATE_NO_EFFICACY`.

This isolated directory prepares, but does not launch, one current real-TLE
TRAIN world after five learned policy checkpoints are available.  It does not
change the gate-admitted real adapter or claim gate admission.  The separate
plumbing binding is domain-separated from evaluation bindings and records only
the fixed-policy routing contract.

The fixed diagnostic order is `ALL_NEUTRAL_CONTROL`, `FULL`, `DROP_C1`,
`DROP_C2`, `DROP_C3`.  `ALL_NEUTRAL_CONTROL` is the all-neutral current
three-route diagnostic arm; it is not the physical evaluation `BASELINE`, which
remains the externally authenticated pre-Catfish MODQN.
Every arm is a complete independent `EEAxisLCSRSThreeRoute` model with Q1,
Q2, and structured Q3.  The closed source mapping is:

| arm | C1 | C2 | C3 |
| --- | --- | --- | --- |
| `ALL_NEUTRAL_CONTROL` | neutral | neutral | neutral |
| `FULL` | informed | informed | informed |
| `DROP_C1` | neutral | informed | informed |
| `DROP_C2` | informed | neutral | informed |
| `DROP_C3` | informed | informed | neutral |

`DROP_*` means source ablation during learner fitting, never inference-time
head removal.  The adapter forces `eval()` and frozen parameters, uses the
current structured `C3View`, retains one shared keyed TRAIN world identity,
and builds a fresh `TrainerEnvironment` per arm.  It writes no checkpoints,
receipts, results, or scientific decision.

The server alias is a dry-run only and was not invoked here:

```bash
.venv/bin/python .scratch/multi-catfish-v023-real-one-world-plumbing/run_v023_real_one_world_plumbing_server.py preflight
```

Before a separate authorized host integration can call the physical adapter,
it needs five explicit complete current learner checkpoint paths in the fixed
order, an explicit frozen TLE root, an explicit TRAIN world index/id/seed, a
current outcome-blind `CurrentOpeningFeasibilityProvider`, and an explicit
execute request.  Supplying `--execute` to the dry-run alias still does not
open a world; it only reports whether those inputs are present.

Focused checks:

```bash
.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-real-one-world-plumbing/test_v023_real_one_world_plumbing.py
```
