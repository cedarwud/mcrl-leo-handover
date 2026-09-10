Workspace: the current directory, `/home/sat/mcrl-v025-ceiling30-ws`. It holds the fast look completed minutes ago: `CONTROL-LAW-FAST-LOOK-2026-09-10.md` and its receipts under `.scratch/`. **Reuse them; do not re-run the search.** Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment. **At most 2 concurrent workers.**

`DIAGNOSTIC_NOT_CLAIM`. Rescoring existing receipts only. No search, no learner, no training run. No sealed constant, threshold, sign, seed, horizon, price, service guard or acceptance rule is changed, and **the sealed objective is not being replaced** — an additional numerator is reported beside it.

# Why this is needed immediately

The fast look reported that holding the association fixed and improving only the power and mode settings raises pooled efficiency by **+113.4 %**, with integrated bits up **115.3 %** while joules rose **0.87 %**, and rate-target attainment rising from 142 of 200 users to 200 of 200.

**Those numbers do not reconcile.** If the whole gain were bringing the 58 users below target up to target, delivered bits would rise by roughly ten per cent, not one hundred and fifteen. **So the great majority of the reported gain must be capacity delivered to users who were already at their target** — bits nobody requested.

A reading of twelve papers in this field established that the convention is to credit **`min(capacity, demand)`**: delivered capacity above the contracted rate is explicitly **not** counted. An adversarial review made the same objection against a different result today.

**If the gain is mostly over-delivery, the honest figure is far smaller, and the project must know that before acting on it.**

# What to compute

Rescore the two existing settings — the declared control law and the best-known coarse-search settings — from the receipts already written, under **three** numerators, and report all three side by side per anchor and pooled:

1. **`CAPACITY`** — delivered ACM capacity, the numerator the fast look used. This reproduces the published figure and is the check that your rescoring is correct.
2. **`DEMAND_CAPPED`** — per user per slot, `min(delivered, the contracted per-user rate)`, integrated the same way over the same boundaries and subslots. State precisely where the cap is applied: per slot, per boundary, or per user over the endpoint, and why that placement is the faithful one.
3. **`ATTAINMENT_ONLY`** — bits credited only for users who attain the per-user rate target over the endpoint, zero otherwise. This is the strictest reading and brackets the other two.

For each numerator report: pooled efficiency for both settings, the relative gain, integrated bits, joules, served counts and rate-target attainment.

Then answer directly:

- **How much of the +113.4 % survives a demand-capped numerator?**
- **How much of the bit increase went to users already at target, and how much to bringing users up to target?** Give the split.
- **Does the improvement still exist, and at what size, under the strictest numerator?**

# Rules

- **Lead with the demand-capped figure.** If it is small, say so in the first line; the project has already been misled once today by a headline that a stricter numerator would have deflated.
- Do not re-run or refine the search. If the receipts lack a field you need, say which and stop rather than approximating it.
- The sealed objective is unchanged; this is a diagnostic reported beside it.
- Every number reproducible from a script left here with exact commands.

Write `FAST-LOOK-DEMAND-CAPPED-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: the gain under the demand-capped numerator, against the +113.4 % under delivered capacity.
