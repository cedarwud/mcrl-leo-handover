# V0.18 five-arm short-screen draft

This directory is an isolated, pre-outcome preparation lane.  Read
`MULTI-CATFISH-MCRL-V018-FIVE-ARM-SHORT-SCREEN-PREREG-DRAFT-2026-09-04.md`
and `READINESS-REPORT.md` before using the evaluator.

The implementation is intentionally callback-based:

```python
from v018_five_arm_screen import run_five_arm_screen

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

For active Q3 arms, the callback must provide identical
`q3_reference_actions_sha256` and `q3_state_sha256` values for each paired
world/lineage.  Those values prove that `DROP_C1` and `DROP_C2` did not
silently change the learned Q3 input.  `DROP_C3` must report
`q3_evaluated=false` and no Q3 input hashes.

