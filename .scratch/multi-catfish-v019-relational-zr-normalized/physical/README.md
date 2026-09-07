# V0.19 five-arm short-screen draft

This directory is an isolated, pre-outcome preparation lane.  Read
`MULTI-CATFISH-MCRL-V019-FIVE-ARM-SHORT-SCREEN-DRAFT-2026-09-04.md`
and `READINESS-REPORT.md` before using the evaluator.

The implementation is intentionally callback-based:

```python
from v019_five_arm_screen import run_five_arm_screen

result = run_five_arm_screen(
    spec=post_gate_spec,
    route_episode_runner=run_one_route_episode,
    main_episode_runner=run_one_main_episode,
    output_dir=screen_output,
)
```

The callbacks are the only place where the canonical simulator, frozen
checkpoint loaders, keyed fading field, and physical EE outcome are composed.
They must be bound only after an authenticated `PASS_LEARNER_GATE`.  The
module itself performs no simulator call, no training, no learner update, and
no TEST access.

The post-gate physical binding is now available in
`v019_physical_adapter.py`.  Its `V019PhysicalAdapter` implements both
canonical callbacks (route and independent `MAIN`) and can be passed directly
to the pure loop.  `run_v019_five_arm_screen_server.py` is the explicit
launcher skeleton: `assemble_post_pass_runtime(...)` authenticates the gate,
loads the three normalized Q3 checkpoints, wires the existing frozen Q1/Q2
and Main helpers, and returns a prepared `V019PostPassRuntime`.  Calling
`runtime.run(output_dir=...)` is the only episode boundary; importing the
launcher or running it with `--print-inputs` does not open a simulator.

The launcher requires an explicit initialization-to-source-lineage map because
the learner checkpoint format authenticates the source-panel digest but does
not repeat the lineage field.  It never guesses this mapping from a mutable
directory.

For active Q3 arms, the callback must provide identical
`q3_reference_actions_sha256` and `q3_state_sha256` values for each paired
world/lineage.  Those values prove that `DROP_C1` and `DROP_C2` did not
silently change the learned Q3 input.  `DROP_C3` must report
`q3_evaluated=false` and no Q3 input hashes.

The physical adapter records these two receipt hashes as canonical
episode-level digests over all ten predecision anchors (each anchor is first
authenticated by the relational encoder).  Thus the receipt does not silently
reduce the audit to only the last step.
