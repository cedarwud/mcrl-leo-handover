# Finding — each head bootstraps with its own argmax, so the scalarised sum is not a Q-function

Date: 2026-09-11. Surfaced by LFDSCREEN; **verified in place by the controller.**

## The code

`src/mcrl/algorithms/modqn.py:536-552`, read verbatim:

```python
for obj_idx in range(3):
    ...
    q_current = self.q_nets[obj_idx](st).gather(1, act).squeeze(1)
    with torch.no_grad():
        q_next_all = self.target_nets[obj_idx](ns)
        q_next_all[~nm] = -1e9
        q_next_max = q_next_all.max(dim=1).values
        target = r + cfg.discount_factor * q_next_max * (1.0 - dn)
```

Each head takes **its own** `max` over next actions. So head `i` converges toward
`Q*_i` — the optimal action-value for objective `i` **alone** — not toward `Q^pi_i`, the
value of objective `i` **under the deployed policy**.

## Why it matters

The deployed rule is `argmax_a sum_i w_i Q_i(s,a)` with `w = (0.5, 0.3, 0.2)`.

- `sum_i w_i Q*_i` is **not** the Q-function of the scalarised reward `sum_i w_i r_i`.
- Each `Q*_i` is achieved by a **different** policy. Their weighted sum is an optimistic
  bound that no single policy attains, and the gap grows with how much the three optima
  disagree — which in this system is exactly the thing under investigation, since `r1` and
  `r2` are anti-aligned on pooled EE by 22.2%.
- Successor-feature theory names the correct object: `psi^pi`, **all heads evaluated under
  one common policy**. LFDSCREEN reports that as a two-line change (bootstrap every head
  from the argmax of the scalarised sum, not from its own).

## What this revises

**"The learner is optimal on the objective it is trained on" was never established.** What
was measured is that the deployed argmax over `sum w_i Q*_i` scores +0.8859 on the
scalarised reward and that no expressible myopic rule beats it. Both facts stand. But the
learner was never solving the scalarised MDP, so the statement "a learned head cannot
exceed its exact oracle" does not license the conclusion that no learner can do better on
that scalar — a **correctly bootstrapped** multi-head learner is a different agent and has
not been run.

## What this does not revise

- The pooled-EE gap (+22.2%, surviving anchor ablation with a positive control and a
  placebo) is a measurement of the **frozen checkpoint as it exists**, whatever objective
  it was actually solving. Unchanged.
- The C1VSGAIN closure concerns the V0.25 stage-C route and does not touch this trainer.
  Unchanged.
- `r2` still prices a zero-joule event and `r3`'s premise still fails in the power model.
  Both are properties of the reward, not of the bootstrap. Unchanged.

## Status

**Verified defect, not yet fixed, and not to be fixed in isolation.** Fixing it changes the
baseline, so it belongs in the same batch as the two known reward defects (the outage free
ride, and the uncalibrated logged `scalar_reward`) and any objective change — one corrected
baseline, re-measured once, rather than three separate resets.

Cross-reference: arXiv:2402.06266 reports silent value-interference and overestimation for
exactly this configuration — value-based, vector Q, non-linear utility. **Read before
committing to any multi-head design.**
