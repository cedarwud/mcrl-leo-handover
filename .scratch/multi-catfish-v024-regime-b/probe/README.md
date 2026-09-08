# V0.24 regime-B probe

The runner accepts `--grid G0|G1|G2|G3` and exactly one of `--unit W:C` or
`--merge`. `--estimate` is authority- and simulator-inert. `--dry-run`
authenticates the controller-sealed design memo, protocol, preflight, grid,
world panel, code bindings, and optional launch authority without opening a
simulator.

Unit execution runs one world/carrier physical tape in G0, under the E1 RNG,
TRAIN epoch, TLE, exact unilateral enumerator, joint evacuation catalog, and
keyed-field conventions. The raw tape is at
`raw-units/world-W-C/physical-tape.json` and is never duplicated across grids.
Each grid unit stores only demand-capped metrics plus the raw tape SHA-256.

The three fixed carrier rules and their world-rooted seeds are documented in
the runner module docstring and `panel_bindings()`. They never read Q values,
checkpoints, rewards, or outcomes. The terminal claim ceiling is always
`TRAIN_DEVELOPMENT_V024_REGIME_PROBE_NO_LEARNER_NO_EFFICACY_NO_TEST`.

Launch-authority JSON is controller-owned and must contain exactly the object
constructed by `validate_launch_authority`: the sealed preflight, design memo,
protocol, fixed panel, one grid/mode, checkout, output root, and four false
scientific-boundary flags. `G0` is reported but `select_grid()` can only choose
the first qualifying member of `G1`, `G2`, `G3`.
