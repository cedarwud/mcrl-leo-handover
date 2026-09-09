# Epoch trend from checkpoints that already exist. Do not retrain.

`PILOT_NOT_CLAIM`. Budget 60 minutes. Report energy efficiency; that is the outcome that matters here.

The previous pilot already trained at full scale and saved **400 checkpoints** (4 seeds x 5 learned arms x 2000 source epochs, checkpoint every 100). Only evaluation had failed. A minimal evaluation at the **epoch-200** checkpoint has been run. Nobody has looked at the trend across epochs, and it is nearly free because the checkpoints are on disk.

## Task
In `/home/sat/mcrl-v025-pilot-ws`, evaluate the existing checkpoints at **epochs 200, 600, 1000, 1400, 2000** using the same minimal evaluation scope that already worked: world 3, 5 anchors, nearest-eligible carrier, 2 seeds, arms FULL / DROP_C3 / BASELINE. Reuse the artefacts in `artifacts/v025-pilot-min-20260909-PILOT_NOT_CLAIM/` and the tape-prefix truncation that made it finish, since a full 33-step tape build did not complete in 19 minutes.

Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, `/home/sat/mcrl-v025-prevalence-ws`, or `src/mcrl/env/`. **Another job is repairing the coalition feature path in this same workspace right now**, so work on a copy of anything you need to modify and do not edit `src/mcrl/stagec_v025/coalitions.py` or `scripts/run_v025_pilot_c3.py`. At most 3 processes, `nice -n 10`.

## Report, as a table with epochs down the rows
For each epoch: pooled EE per arm in bit/J, the FULL minus DROP_C3 relative difference, the availability per arm, and the mean selected coalition size for FULL.

Then answer three questions in plain words:
1. **Is the FULL minus DROP_C3 contrast trending up, flat, or down with training?** A contrast that decays with training means the epoch-200 result was noise or an early-training artefact.
2. **Does the selected coalition size change with training?** At epoch 200 FULL selected the all-users coalition at every anchor and never a size between 2 and 6. If that persists to epoch 2000, it is not a warm-up artefact.
3. **Does availability move with training?** At epoch 200, FULL had the lowest availability of any arm, so its efficiency gain may have come from serving fewer users.

## One thing to state prominently
These checkpoints were trained with a coalition feature path that has since been found defective: the pairwise cross-gain terms were summed into a single scalar before the head saw them, which the contract forbids. **So this trend describes a model that could not see the mechanism.** Say so at the top of the report. The trend is still worth having, because a contrast that decays with training tells us something either way.

Write `EPOCH-TREND-2026-09-09.md` in the workspace root and print it as your final message.
