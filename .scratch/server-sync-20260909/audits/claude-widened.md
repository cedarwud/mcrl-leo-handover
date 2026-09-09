# WIDENED interaction-existence arm (PROBE_NOT_CLAIM)

Read the sealed declaration `V025-CONTROLLER-DECISIONS-PROBE-NEIGHBOURHOOD-2026-09-09.md` first. Copy it from `/home/sat/mcrl-hub` or ask git for it. It states exactly what this arm is and why widening an existence search is admissible. Follow it literally.

## Setup
Workspace `/home/sat/mcrl-v025-probe-ws-widened`, copied from `/home/sat/mcrl-v025-probe-ws-acmfix` if that exists (it carries the corrected ACM already), otherwise from `/home/sat/mcrl-v025-probe-ws` with `src/mcrl/physics_v025/` replaced wholesale by the copy from `/home/sat/mcrl-v025-codex-ws-engine/src/mcrl/physics_v025/`. Record the md5sums either way. Reuse the exogenous tapes by hard link if you can show they do not depend on the ACM, resolution or batch code; rebuild them if they do; state your evidence. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Never write into `/home/sat/mcrl-v025-probe-ws`, `/home/sat/mcrl-v025-probe-ws-acmfix`, `/home/sat/mcrl-leo-handover`, `/home/sat/mcrl-hub`, or `src/mcrl/env/`.

## What to add to `analyse_anchor_from` in `probe/probe_interaction_existence.py`
Keep every existing candidate family exactly as it is. **Add** these four, each tagged with its own `kind` string so the census can be read per family:

1. `pairwise-marginal` — the ten users with the **smallest** `|d_i^u|` among those with a legal move, all pairs, each contributing their **top four** ranked options.
2. `pairwise-straddle` — one user from the smallest-`|d_i|` ten and one from the largest-`|d_i|` ten, all such pairs, top four options each.
3. `vacate-and-fill` — for each active beam `b`: identify the occupant of `b` whose `|d_i|` is smallest (the most nearly indifferent), and the non-occupant whose best legal option is `b` and whose `d_i` is most negative (the most blocked). Move the first out to their best alternative and the second in to `b`. One candidate per beam.
4. `triples-marginal` — all triples among the **five** smallest-`|d_i|` users, each contributing their top two options.

## What must not change
No threshold, sign, seed, horizon, λ, κ, η_ref, service guard, or acceptance rule. The service guard `served >= base_served` stays. The `Psi` decomposition stays. The certified-`u` procedure stays. You are only enlarging the candidate set.

## Report
`/home/sat/mcrl-v023-codex-audits/parallel-20260909/PROBE-WIDENED-REPORT-2026-09-09.md`, printed as your final message. Per regime and **per candidate family**: improving-move count under `G` and under `F`, the positive-`Psi` census independent of improvement, the max `Psi_A^u` with its coalition size and family, and the number of candidates evaluated. State the total search budget so a null reads as budget-limited. Add an HONEST LIMITS paragraph reproducing the declaration's final section. Label everything `PROBE_NOT_CLAIM`. Never pool these results with the original neighbourhood's.

Regimes: `a-r0`, `R1`, `R3`, `R4`, `R6`, `R7`. Six concurrent processes maximum, `nice -n 10`. Budget 3 wall hours. If a regime crashes, report the traceback and continue with the others.
