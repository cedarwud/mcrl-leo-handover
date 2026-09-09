# Verify what the source says about the beam half-power angle, then measure both readings

`DIAGNOSTIC_NOT_CLAIM`. Budget 2 hours. **No constant is being changed.** This establishes what the cited source actually defines and measures the consequence of each reading. Any change is a separate decision made on provenance grounds.

## The finding to verify
A provenance audit reports that `TX_FULL_HPBW_DEG = 3.32` is commented as retaining a HOBS full half-power beamwidth convention, but that the source's own equation uses `sin(theta_3dB)` with `theta_3dB = 0.058 rad`, which is **3.323 degrees as an off-axis angle**, meaning the half-power point sits at that off-axis angle rather than at half of it. The engine registers 3.32 as a **full span** and halves it to 1.66 degrees for the pattern edge.

If the audit's reading is right, the source's beam is **twice as wide** as the one we model.

## Task 1: settle the reading
Locate the cited source and quote the equation and the table entry verbatim. Determine whether `theta_3dB` there is a half-power **off-axis angle** or a **full beamwidth**. Check how the symbol is used in the equation, since substituting it into a pattern formula usually disambiguates. If the source is not retrievable, say so and stop at that; do not infer the convention from what would be convenient.

Also check whether any other constant in the engine was derived from the same source under the same convention, since a misreading would propagate.

## Task 2: measure both readings on the network, not on an isolated link
The audit's sensitivity figure, +42.5 % energy efficiency at a 2 degree off-axis point when the width is doubled, comes from an **isolated single-user fixture**. That is not the network answer, and the direction there is not obvious:

* a wider beam raises the wanted link's off-axis gain, which helps;
* it equally raises every aggressor's gain at its victim, which hurts.

Our results are dominated by interference structure: 91.1 % of infeasible user-steps are interference-limited, 98.9 % of interference comes from an adjacent beam on the victim's own satellite, and a single aggressor carries 74.3 % of it. Widening the beam changes that structure directly.

So evaluate, on real anchors with the corrected physics, under **both** the current 3.32 full-span reading and the doubled reading the source appears to support:
* pooled energy efficiency for BASELINE, the iterated unilateral optimum, and the bounded oracle set selector;
* the served counts;
* **the coordination headroom, oracle over unilateral**, which is the number the project's result rests on;
* the interference structure: the share of infeasible user-steps that are interference-limited, and the top-1 aggressor share.

Cover at least 10 anchors and say how many.

## What this task must not do
Do not change `TX_FULL_HPBW_DEG` in any sealed or engine path; work on a copy. Do not recommend a value on the basis of which gives a better result. Report the source's definition and the two measurements, and let the provenance decide. If the wider reading happens to improve the headline, say so plainly and label it as a consequence, never as a justification.

## Constraints
Workspace `/home/sat/mcrl-v025-beam-ws`, built with `git -C /home/sat/mcrl-v025-codex-ws-engine archive 75c5c78c | tar -x -C /home/sat/mcrl-v025-beam-ws`, then `git init` and commit. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, or any other `mcrl-v025-*-ws`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Large files under `/home/sat/bigtmp`, never `/tmp`, a RAM-backed tmpfs here. At most 3 processes, `nice -n 12`.

Write `BEAMWIDTH-READING-2026-09-09.md` in the workspace root and print it as your final message. Lead with what the source actually defines, then the two-reading comparison table.
