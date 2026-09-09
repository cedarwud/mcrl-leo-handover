# Corrected-ACM interaction-existence probe (PROBE_NOT_CLAIM)

## Why this exists
An identical probe is ALREADY RUNNING in `/home/sat/mcrl-v025-probe-ws` on the **pre-fix** physics. Stage 4h has since landed a confirmed ACM causality correction (credited MODCOD was chosen from realised post-fading SINR, so the 1.7 dB margin cancelled). On a paired smoke the correction moves availability 0.791 -> 0.453 and pooled EE 18.94e6 -> 5.66e6 bit/J at identical joules. The corrected physics is strictly more contended, so a null result on the old physics would not carry over. This run is selected purely by a code-version fact, before any probe outcome exists. Do not look at the other probe's results and do not let them influence anything here.

## Task
Reproduce the same probe, unchanged in question and protocol, on the CORRECTED physics.

1. **New workspace** `/home/sat/mcrl-v025-probe-ws-acmfix`. Copy `/home/sat/mcrl-v025-probe-ws` into it. Never write into `/home/sat/mcrl-v025-probe-ws`, `/home/sat/mcrl-v025-codex-ws-engine`, `/home/sat/mcrl-leo-handover` or `/home/sat/mcrl-hub`.
2. **Swap in the corrected physics**: replace `src/mcrl/physics_v025/` wholesale with the copy from `/home/sat/mcrl-v025-codex-ws-engine/src/mcrl/physics_v025/`. Record `md5sum` of every replaced file, before and after, in the report. If the probe script then fails on a changed API, fix the *probe script*, never the physics.
3. **Tapes.** `artifacts/v025-interaction-existence-probe/tape-world-*.pkl` and `calibration-tape-*.pkl` already exist in the source workspace (about 800 MB each). Determine whether these exogenous tapes are independent of the ACM/resolution/batch code. Read the tape builder to decide; do not guess. If independent, hard-link or copy them and say so. If they depend on the changed code, rebuild them and say so. Getting this wrong silently is the worst outcome here, so state your evidence.
4. **Run the same regimes** the other probe runs: `a-r0`, `R1`, `R3`, `R4`, `R6`, `R7`. Same flags, same calibration reference `nominal-greedy`, same `--calibration-steps 10`. Do NOT change any threshold, seed, horizon, or acceptance rule. Cap yourself at 6 concurrent processes; the machine has 20 cores and is already at load 10, so use `nice -n 5`.
5. **Report** `/home/sat/mcrl-v023-codex-audits/parallel-20260909/PROBE-ACMFIX-REPORT-2026-09-09.md`, and print it as your final message. Per regime state plainly:
   - whether a certified iterated unilateral optimum `u` was reached, and in how many sweeps;
   - whether any strictly improving joint move from `u` exists, that is whether max Psi_A^u > 0;
   - the value and the coalition size that achieves it;
   - the count of improving moves found and the search budget, so a null can be read as "none within budget" rather than "none exists".
   Add a one-paragraph HONEST LIMITS section. Label everything `PROBE_NOT_CLAIM`.

## Hard constraints
Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Never modify `/home/sat/mcrl-leo-handover` or its venv. No edits under `src/mcrl/env/`. Do not tune anything against an observed result. If a regime crashes, report the traceback and move on to the others rather than stopping. Budget 3 wall hours.
