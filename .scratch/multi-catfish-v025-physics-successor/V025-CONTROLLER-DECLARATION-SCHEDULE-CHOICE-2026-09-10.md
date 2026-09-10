# Declaration — the training schedule, chosen before any EE exists

Date: 2026-09-10 ~16:32Z · Controller
**No EE quantity exists for any schedule. None was computed anywhere in this chain.**

## What was established, and by whom

Three jobs, all using a convergence rule fixed in `.scratch/lr-convergence-sweep/spec.md`
**before the first of them ran**, all computing **no EE**:

| job | finding |
|---|---|
| `LRSWEEP` | 21 of 21 route x **constant** learning-rate cells fail at 500 full-batch updates |
| `HORIZON` | at a 4,000-update cap, **more steps** `NONE` and **minibatching** `NONE`, with no minibatch advantage at equal wall time |
| `DECAY` | **three of four decay schedules reach the unchanged criterion** |

`DECAY` reproduced `HORIZON` Arm A's parity exactly before reporting anything, and it was
instructed **not to name a winner**. It did not.

| schedule | start | first admissible update | 16-seed x 5-arm cost |
|---|---:|---:|---:|
| **step decay**, factor 0.1 after 2,000 and 3,000 | `1e-3` | **2,200** | **0.28–0.32 CPU-h** |
| step decay, same shape | `3e-3` | 2,300 | 0.32–0.35 CPU-h |
| plateau decay, factor 0.5, `n=3` | `1e-3` | 2,800 | 0.36–0.40 CPU-h |
| cosine to zero at 4,000 | `1e-3` | 3,200 | 0.47–0.55 CPU-h |
| inverse-time, `tau=1000` | `1e-3` | **NONE** (objective motion 1.9460% vs 1%) | — |

## The choice, and the grounds

**Adopt step decay from `1e-3`, factor 0.1 after 2,000 and after 3,000 updates.**

Two grounds, **both computable without any EE and both known before this declaration**:

1. **Earliest first-admissible update** — 2,200, the smallest of the admissible set.
2. **Lowest extrapolated production cost** — 0.28–0.32 CPU-hours, the smallest of the
   admissible set.

**It wins on both simultaneously, so no weighting between them has to be argued.** Had they
disagreed I would have had to declare a weighting, and that declaration would have been the
place an outcome could leak in. It did not arise.

**What was NOT used as a ground:** predictive quality at any epoch, any held-out metric level,
any route contrast, and any EE quantity. `DECAY` reports held-out metrics as convergence
diagnostics only; they play no part here.

## The horizon is a stopping rule, not a literal

Run to a stated cap with cadence-100 checkpoints and take **the first checkpoint satisfying the
pre-declared stability condition** — objective relative motion `<= 0.01`, held-out level R2
within `0.01`, ordering and top-1 each within `0.005`, over the preceding 100 updates. If no
checkpoint satisfies it, the run reports **non-convergent** and no head from it may be used to
say a route is dead.

`2,200` is the expected first-admissible point for C3 on this panel, not a horizon literal. Set
the cap at 4,000 so the stopping rule has room, and record where it actually stopped.

## Consequences for tonight's three runs

The v1 (13:55Z), v2 (14:25Z) and z (15:12Z) runs are all **500 constant-`1e-3` updates**.
They are therefore **under-run by construction**, and that reading was fixed in
`V025-CONTROLLER-PREDECLARATION-ZSCORE-AND-HORIZON-2026-09-10.md` **before** any contrast from
them existed.

**They still run to completion and are still scored.** They remain a valid **paired** comparison
at equal budget, and they are the only artefacts the rebuilt panels can be acceptance-tested
against. What they cannot do is establish that a route is dead.

**A converged rerun costs about 0.3 CPU-hours per configuration.** That is the obvious next
generation, and per `V025-CONTROLLER-RULING-C3-ENCODER-CONTRACT-2026-09-10.md` it is the launch
at which the stored encoder-contract digest is introduced, since it starts from a clean state.

## Not authorised here

This declaration fixes the schedule. **It does not authorise a rerun.** Two things gate that:
`SCALE`, which may show the five arms never make different decisions — in which case no schedule
makes the ablation informative — and `STATICS2`, which is rebuilding the reference scale the
rerun would be measured against. Launching before those report would be launching on a hunch.
