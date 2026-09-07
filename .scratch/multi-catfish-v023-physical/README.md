# V0.23 provisional physical evaluation adapter

`v023_physical_episode_runner.py` is a fixed-policy evaluation seam for the
current authenticated V0.20 repriced Q1/Q2 merge (`lineage=2026092101`, Q1
rung 10, Q2 rung 3000).  It does not train, refresh a source, open TEST, or
make a gate decision.  Every receipt is marked `PROVISIONAL_PRE_GATE` and
`EVALUATION_DEVELOPMENT`.

`V023-DROPC3-DEVELOPMENT-EVALUATION-CONTRACT-2026-09-06.md` freezes the
separate 100-episode, TRAIN-only `DROP_C3` timing/evaluation slice.  The
explicit server entrypoint is
`run_v023_dropc3_evaluation_server.py`; the sync/launch wrapper is
`sync_launch_v023_dropc3_evaluation_server.sh`.  Neither emits a BASELINE
artifact.  Because the current two-arm carrier deliberately selects the same
Q1+Q2 action, this slice records physical evaluation/timing only and performs
no between-arm comparison.

The only labels are:

* `BASELINE`: the native masked argmax of frozen Q1 + Q2;
* `DROP_C3`: the same frozen Q1 + Q2 action, with no third component.

Each world is built once as a `V023WorldBinding` and is replayed with the
same world seed and `KeyedFadingField` root for both labels.  The supplied
factory must return a real `TrainerEnvironment` backed by the frozen TLE
archive.  The stepping path consumes `TrainerEnvironment.last_outcome`, not
the reduced `StepResult`, and pools realised `link_rate_bps` and
`system_power_w` as ratio-of-sums bits/J.

## One-episode integration criterion

With a frozen TLE archive and a real `TrainerEnvironment` factory, this check
is complete only when one paired world returns two finite receipts that have
all of the following properties: ten committed steps for 100 users; identical
field root, initial-world digest, and action-trace digest across the two
labels; positive pooled energy; `total_bits / total_energy_j` exactly as the
reported EE endpoint; and all four forbidden flags false (`q3_evaluated`,
`test_split_opened`, `episode_training`, `learner_update`).

Use `V023EpisodePlan(..., integration_only=True)` for this one-world check.
Production plans must contain complete 100-episode blocks, and checkpoints
are written only at episodes 100, 200, ... .  Checkpoints bind the complete
receipt list, plan hash, both network parameter hashes, TLE/environment resume
state, all episode RNG states, and the exact V0.20 checkpoint/authority/
contract hashes.  Any mismatch fails closed.

For the explicit `DROP_C3`-only contract, the expected completed tree is:

```text
<output>/result.json
<output>/timing.json
<output>/checkpoints/checkpoint-000100.json
```

The server command prints `DROP_C3_EVALUATION_PASS` only after reopening and
validating that result.  A resume uses the same command with
`--resume-checkpoint <output>/checkpoints/checkpoint-000100.json`.

The exact future server command (not run by this checkout) is:

```text
V023_DROPC3_SERVER_HOST=sat \
V023_DROPC3_SERVER_ROOT=/home/sat/mcrl-v023-dropc3-evaluation-20260906-r1 \
V023_DROPC3_TLE_ROOT=/home/sat/mcrl-runtime/tle-frozen-20260820 \
./.scratch/multi-catfish-v023-physical/sync_launch_v023_dropc3_evaluation_server.sh
```

It stages the authenticated V0.20 lineage and the canonical TRAIN PREREG,
then starts the entrypoint in a fresh tmux session.  To resume the staged
output, set `V023_DROPC3_RESUME_CHECKPOINT` to the published
`.../run/drop-c3-100ep/checkpoints/checkpoint-000100.json` before invoking
the same wrapper.

The wrapper is launch glue only; it does not run automatically.  The
remaining launch blocker is external: an authorized controller must first
provide the fresh V0.23 evaluation contract and explicitly authorize a server
launch.
The current V0.20 source-fit artifact is only the frozen Q1/Q2 background;
there is no exact V0.23 BASELINE evaluation artifact yet.
