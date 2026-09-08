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

## Iteration-2 parallel lever matrix

`run_v024_lever_matrix_probe.py` is a separate successor runner; it does not
modify the finite-demand runner or its receipts. Its priority-ordered registry
contains L1, L12, L2 and L4. Unit/merge launches use `--lever ID` plus
`--unit WORLD:CARRIER` or `--merge`; `--estimate` reports every lever without
opening the simulator. L1/L12 are explicitly `REGEN_REQUIRED`. L2/L4 bind the
same r2 tape bytes read-only and reprice profiles individually, but their
declared `VERIFY_SOURCE` items remain `TODO_CONTROLLER_DECLARE` launch blockers.

The matrix-wide preflight binds code, the sealed memo/protocol, adjudications,
declaration, constants table, panel and all twelve r2 digests. Launch
authorities are per lever and exact invocation so valid levers can run
independently and up to two single-thread units can run in parallel. The
acquisition hooks require complete OPS-3, LC-SRS, set-catalog, composed-arm and
failure-ledger inputs; they never fabricate missing tapes.
