# Corrected-physics interaction-existence probe (PROBE_NOT_CLAIM) — the decisive C3 test

## The workspace is already prepared. Verify, do not rebuild.
`/home/sat/mcrl-v025-probe-ws-acm2` is a clean checkout of engine commit `75c5c78c` ("Finish V0.25 stage 4h physics gate") with the three existence-probe scripts copied in. Confirm before starting:
* `src/mcrl/physics_v025/`: `acm.py` md5 starts `aa58aeeb`, `resolution.py` `e0b1cc50`, `batch.py` `3677d530`, `tapes.py` `108426ce`, `provider_legacy.py` `9127c245`, `channel.py` `03d3121f`, `architectures.py` `ea49b918`, `adapter.py` `da7de77d`.
* `.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py` is 277,997 bytes, with 30 occurrences of `fading_quantile_alpha` and 9 of `realised_outcome`. If it is not, stop and report.

Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, `/home/sat/mcrl-v025-probe-ws`, or `src/mcrl/env/`.

## Three traps that already destroyed one attempt. Avoid all three.
1. **Never reuse a tape from another workspace.** `tapes.py` and `provider_legacy.py` differ between trees. Build every world tape and calibration tape **fresh inside this workspace** with this tree's code. Do not hard-link, copy or symlink from `/home/sat/mcrl-v025-probe-ws`.
2. **Never reuse a calibration cache.** `probe_interaction_existence.py` caches to `{cache}/calibration-{regime}.pkl` and loads unconditionally if the file exists, keyed on regime name alone, with no physics digest and no invalidation. Point `--calibration-cache` at a directory inside this workspace that starts empty. The old cache holds genie-ACM prices for all six regimes and would be picked up silently.
3. **`u` must actually be certified.** The previous attempt logged `step 0: u iterations=2 sweeps=2 termination=BUDGET_LIMITED_MID_SWEEP wall=93.7s`. An uncertified `u` destroys the probe's entire premise: the argument that any improving joint move must carry `Psi_A^u > 0` holds only when every legal single move at `u` is non-improving. `--uni-budget-s` defaults to 240.0; raise it as far as needed. Corrected physics is more expensive than genie physics, so budget accordingly.

## What matters most
**Certification beats coverage.** Five anchors with a genuinely certified `u` are worth far more than fifty with `BUDGET_LIMITED_*`. Report the certification rate per regime as a headline number, and report the improving-move census separately for certified and uncertified anchors. Never pool them.

Raising the unilateral search budget is deliberately **conservative against C3**: a longer search yields a better `u`, which raises the bar an improving joint move must clear. Do not reduce it to save time.

## Regime order, by cost
Run `a-r0` first: it is the only setting that reaches the fast batch kernel (`evaluate_ar_tdm_catalogue`, about 0.003 s per configuration). Then `R7`, `R1`, `R3`, `R4`. Leave `R6` (`a-γ0`) last and treat it as optional — it has no batch kernel and costs about 0.556 s per configuration, roughly 180 times more. Do not let R6 starve the others. Up to 6 concurrent processes; the machine has 20 cores and is currently near idle.

## Do not change
No threshold, sign, seed, horizon, λ, κ, η_ref, service guard (`served >= base_served`), `Psi` decomposition, or acceptance rule. You may fix the existence-probe script where the newer runner's API differs from the old one, and you may raise compute budgets. Nothing else.

## Report
`/home/sat/mcrl-v023-codex-audits/parallel-20260909/PROBE-ACM2-REPORT-2026-09-09.md`, printed as your final message. Per regime:
* `u` certification rate, sweeps and iterations, and the termination string distribution;
* whether any strictly improving joint move from a **certified** `u` exists, under the coordinator objective `G` and separately under `F`;
* `max Psi_A^u` with its coalition size and candidate family;
* the positive-`Psi` census independent of improvement;
* candidates evaluated and the search budget, so a null reads as "none found within this budget", never as "none exists";
* the realised availability and the `m_tx` `NO_MODE` share, so I can see the corrected physics is actually in force.

End with an HONEST LIMITS paragraph. Label everything `PROBE_NOT_CLAIM`. Budget 4 wall hours. If a regime crashes, report the traceback and continue with the others.
