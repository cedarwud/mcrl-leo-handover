# Erratum 20 — I pointed the penalty assessment at the wrong module

Date: 2026-09-10 ~18:30Z · Controller · Found by the owner, not by me

## What happened

The owner said the sibling project's **penalty** was the most effective of its methods and had
been trained. I dispatched `PENALTY` to assess it. It returned:

> **the sibling faithful-ablation package was never enabled in any discoverable recorded run;
> the exact V0.25 input mapping does not exist; the mechanism cannot be instantiated or fire on
> the sealed interface.**

**That verdict is correct about the file I gave it, and the file I gave it was the wrong one.**

I grepped for `penalty`, found `modqn_faithful_ablation/capacity_penalty.py`, and sent that —
a **local copy for a faithful-ablation seam**, whose config flags read
`"capacity_penalty_enabled": False` and `"capacity_penalty_off": True`. I did not survey the
alternatives before choosing. I also shipped only `docs/`, so the job had no access to run
records, `artifacts/`, or `.agent-memory/` — its verdict was explicitly hedged on
**discoverability**, and that hedge was my doing.

## What the real mechanism is

`shared_q_isolation/penalties.py` — a module named for the pathology it addresses:

**1. `q_row_decorrelation_penalty(Q)`** — mean `|off-diagonal Pearson|` between the **user rows**
of the `(users x actions)` Q matrix at one step. Its own docstring:

> `1.0` = every user's Q row is a collinear copy (**the measured ~0.998 pathology**),
> `0.0` = mutually uncorrelated (**the z-score repair reaches 0.17-0.22**).

Pearson is scale- and shift-free per row, so it constrains only the **shape** of each user's
action-preference profile — "it cannot be satisfied by rescaling Q, only by making different
users prefer different actions, which is the intended pressure."

**2. `srank_penalty(features)`** — Kumar et al. arXiv:2010.14498 Eq. (6),
`sigma_max(Phi)^2 - sigma_min(Phi)^2` on penultimate features. Raises effective rank.

And the treatment matrix is a real 6-arm ablation with **three** mechanisms — `P` (penalty),
`EXP`, `ACRM`: `modqn_raw`, `modqn_z`, `full`, `wo_penalty`, `wo_exp`, `wo_acrm`. The
`wo_penalty` arm exists precisely to isolate `P`.

## Why this matters here, and it is not a small thing

**Two of today's findings are exactly what collinear Q rows and low effective rank produce:**

- `a0 = masked argmax(Q1+Q2)` is statistically indistinguishable from a **zero-learning myopic
  rule** in concentration terms;
- the sealed head **loses to plain linear on level calibration in all three routes**
  (C1 `-0.1605` vs `-0.0896`; C2 `-34.6314` vs `-1.8406`; C3 `-0.0685` vs `0.0365`).

**This project has never measured its Q-row correlation or its effective rank.** `QCOLLINEAR`
(dispatched 18:30Z) does it on existing checkpoints, with the z-view run as a built-in control.

## The hazard the sibling disclosed, carried forward

`rho = 1` is a **stationary point** of the decorrelation penalty — it is weakest exactly where
the pathology is worst. Plain SGD is captured; Adam escapes (`0.9973 -> 0.1320`) with a ~1700x
grad-norm spike. Therefore:

> **A null result on a decorrelation arm has two readings** — "decorrelation does not repair the
> collapse" versus "the penalty never escaped its own flat corner" — **and they are distinguished
> by the logged penalty trajectory, not by the endpoint metric.**

**If a decorrelation arm is ever run here, the penalty trajectory must be logged per update.**
Recording that now, before any such arm exists.

## What stands and what does not

- **`PENALTY`'s verdict stands, narrowly**: `capacity_penalty` was never enabled and cannot be
  instantiated on the V0.25 interface.
- **It does not stand as "the penalty idea is dead."** The mechanism the owner meant was never
  assessed.
- **Sequencing**: `QCOLLINEAR` first. If the pathology is absent here, no penalty is needed and
  the line closes cheaply. If present, the penalty design is assessed against a measured problem
  rather than an imported one — the mistake corrected in
  `imported-diagnostics-flip-direction`.

## The error shape

I searched for a keyword, took the first file whose **name** matched, and did not survey. The
same session already produced `run-nonlearned-baselines-first` and
`imported-diagnostics-flip-direction`; this is a third instance of the same family — **acting on
the first plausible match instead of enumerating the field.** The owner caught all three.
