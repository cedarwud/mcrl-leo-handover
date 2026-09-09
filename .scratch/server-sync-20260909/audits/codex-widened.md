# WIDENED interaction-existence arm (PROBE_NOT_CLAIM)

Read the sealed declarations in `/home/sat/mcrl-records/decisions/` first, specifically `V025-CONTROLLER-DECISIONS-PROBE-NEIGHBOURHOOD-2026-09-09.md` and its `-AMENDMENT-1-` companion. They are there; do not look in `/home/sat/mcrl-hub`. It states exactly what this arm is and why widening an existence search is admissible. Follow it literally.

## Setup
The workspace `/home/sat/mcrl-v025-probe-ws-widened` is already prepared for you: it is a clean
`git archive` of engine commit `75c5c78c` ("Finish V0.25 stage 4h physics gate"), which carries the
corrected causal ACM, with the three existence-probe scripts copied in. Verify before starting:
`src/mcrl/physics_v025/acm.py` md5 starts `aa58aeeb`, `resolution.py` `e0b1cc50`, `batch.py` `3677d530`;
`probe/run_v025_matrix_probe.py` is 277,997 bytes with 30 occurrences of `fading_quantile_alpha`.
If any of that is wrong, stop and report.

Build every world and calibration tape **fresh inside this workspace**; never link or copy one from
another workspace, because `tapes.py` and `provider_legacy.py` differ between trees. Point the
calibration cache at a directory inside this workspace that starts empty: the cache is keyed on regime
name alone with no physics digest and would otherwise silently load pre-fix prices. Raise
`--uni-budget-s` until `u` is genuinely certified and report the certification rate; an uncertified `u`
destroys the premise that every legal single move is non-improving there.

Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Never write into
`/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`,
`/home/sat/mcrl-v025-probe-ws-acm2`, `/home/sat/mcrl-v025-witness-ws`, or `src/mcrl/env/`.

## What to add to `analyse_anchor_from` in `probe/probe_interaction_existence.py`
Keep every existing candidate family exactly as it is. **Add** these four, each tagged with its own `kind` string so the census can be read per family:

1. `pairwise-marginal` — the ten users with the **smallest** `|d_i^u|` among those with a legal move, all pairs, each contributing their **top four** ranked options.
2. `pairwise-straddle` — one user from the smallest-`|d_i|` ten and one from the largest-`|d_i|` ten, all such pairs, top four options each.
3. `vacate-and-fill` — for each active beam `b`: identify the occupant of `b` whose `|d_i|` is smallest (the most nearly indifferent), and the non-occupant whose best legal option is `b` and whose `d_i` is most negative (the most blocked). Move the first out to their best alternative and the second in to `b`. One candidate per beam.
4. `triples-marginal` — all triples among the **five** smallest-`|d_i|` users, each contributing their top two options.
5. `aggressor-coalition` — **the best-aimed family; do this one first if time is short.** A headroom diagnostic verified against the sealed receipt found that 91.1 % of infeasible user-steps are interference-limited, that 98.9 % of interference comes from an adjacent beam on the victim's own satellite, and that removing a victim's single strongest aggressor restores feasibility for 76.4 % of them. The remaining **23.6 % need two or more aggressors relieved**, and that is the signature of a super-additive interaction: each aggressor alone changes nothing, both together cross the decode threshold. Where one aggressor suffices the benefit already sits in that aggressor's own marginal and belongs to C1, so the multi-aggressor tail is the actual candidate territory. For each interference-limited victim **not** restored by removing its top-1 aggressor alone, build: the victim plus its top-2 aggressors, the victim plus its top-3, and the aggressors-only versions of each without the victim moving. Move every coalition member to its own best legal alternative, in every combination.

## What must not change
No threshold, sign, seed, horizon, λ, κ, η_ref, service guard, or acceptance rule. The service guard `served >= base_served` stays. The `Psi` decomposition stays. The certified-`u` procedure stays. You are only enlarging the candidate set.

## Report
`/home/sat/mcrl-v023-codex-audits/parallel-20260909/PROBE-WIDENED-REPORT-2026-09-09.md`, printed as your final message. Per regime and **per candidate family**: improving-move count under `G` and under `F`, the positive-`Psi` census independent of improvement, the max `Psi_A^u` with its coalition size and family, and the number of candidates evaluated. State the total search budget so a null reads as budget-limited. Add an HONEST LIMITS paragraph reproducing the declaration's final section. Label everything `PROBE_NOT_CLAIM`. Never pool these results with the original neighbourhood's.

Regimes: `a-r0`, `R1`, `R3`, `R4`, `R6`, `R7`. Six concurrent processes maximum, `nice -n 10`. Budget 3 wall hours. If a regime crashes, report the traceback and continue with the others.
