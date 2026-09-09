# Provenance and sensitivity audit of every physical constant and formula

`DIAGNOSTIC_NOT_CLAIM`. Budget 3 hours. Read-only analysis plus arithmetic; run no simulation.

## Why this exists
Several modelling defects have been found in this project, and **not one of them was found by a systematic process**. The segment-anchored power reset came from an unrelated audit. The adaptive-coding causality defect came from a commissioned review. The per-chain circuit constant was traced by an outside reviewer to a paper whose definition is narrower than our usage. The mechanism figure's mode table was found while preparing a figure.

The last of those shows the failure mode precisely: **the number was copied correctly and the source is real, but the source's definition is narrower than the meaning we gave it.** That kind of error is invisible in the code and invisible in the tests. It appears only when a constant is checked against what its source actually says.

So audit them all, once, systematically.

## Scope
Every declared constant in `src/mcrl/physics_v025/constants_v025.py`, plus every constant embedded in `acm.py`, `channel.py`, `energy.py`, `architectures.py` and `batch.py`. The file already carries a provenance dictionary; that dictionary is the claim under audit, not the evidence.

## For each constant, report a row
| field | what it must contain |
|---|---|
| symbol and value | as declared |
| stated provenance | quoted from the code or the sealed declaration |
| what the source actually says | if the source is a standard, a paper or a datasheet, state its own definition in its own terms |
| semantic match | does our usage mean the same thing the source means? **This is the column that matters.** |
| verdict | `MATCHES`, `NARROWER_IN_SOURCE`, `WIDER_IN_SOURCE`, `UNSOURCED`, or `UNVERIFIABLE_HERE` |
| sensitivity | if this constant were wrong by a factor of two in each direction, which reported quantities move, and roughly how much |

Where a constant is declared as a benchmark assumption rather than a physical claim, say so and mark it `DECLARED`; that is a legitimate status and not a defect. The point is to separate the three cases: verified against a source, declared as an assumption, and **believed to be sourced but actually not**.

Known cases to include and check rather than assume:
* the per-chain circuit power `0.338 W` and per-satellite baseband `0.200 W`, which an outside review traced to a Ku-band hybrid-precoding paper where `338 mW` covers only DAC, mixer, low-pass filter and baseband amplifier with the power amplifier separate, and `200 mW` is a baseband digital precoder rather than all shared satellite overhead;
* the saturation efficiency `0.35` and saturated power `5.2178 W`, including whether `0.35` is a saturation efficiency or an average efficiency, since the difference changes every energy figure;
* the mode table: `28` modes with `SE_max = 3.7109` and `SINR_min = −1.4418 dB`, against EN 302 307-1 Table 13, roll-off `0.20` and implementation margin `1.7 dB`;
* the rate target `50 Mbit/s`, which a sealed amendment calls a power-control setpoint rather than a delivered-rate requirement;
* the decision interval `30.08 s` as `47 × 0.640`, and the coordinator budget `10 s` with the remaining `20 s` attributed to sensing, transport, validation and commit, an attribution that carries no cited source.

## Also audit four formulas, not only constants
1. **The amplifier supply law** `sqrt(p·p_sat)/eta`. It tends to zero as radiated power tends to zero, which cannot describe an amplifier that stays biased. Is a separate idle term added elsewhere, and if so does adding it change the effective saturation efficiency, that is does the model double-count?
2. **The energy identity**: confirm that the per-slot time-division amplifier energy is the airtime-weighted sum over slots and not the amplifier power at the mean or the maximum, and that a user with no transmitted mode still contributes energy.
3. **The coupled power fixed point**: state the map, whether a solution is proven unique, what happens at the cap, and what the iteration limit does when it has not converged.
4. **The segment-anchored power reset** found earlier: state whether it still exists in this engine, and if it was removed, what replaced it.

## Output
`CONSTANT-PROVENANCE-2026-09-09.md` in the workspace root, printed as your final message.

Lead with a table of every constant whose verdict is **not** `MATCHES` or `DECLARED`, ordered by the size of its sensitivity. That short list is the deliverable; the full table can follow.

Then one paragraph naming which reported result would change most if the worst item on that list were wrong, and by how much.

## Constraints
Workspace `/home/sat/mcrl-v025-provenance-ws`: `mkdir -p`, `git init`, commit empty; read `/home/sat/mcrl-v025-codex-ws-engine` **read-only**. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, or any other workspace. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`. Two processes maximum, `nice -n 15`.

Change nothing. Do not propose new values; this audit establishes what is and is not sourced, and correcting anything is a separate decision.
