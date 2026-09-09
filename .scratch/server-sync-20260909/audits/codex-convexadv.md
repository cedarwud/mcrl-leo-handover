You are performing an adversarial review. Workspace: the current directory, `/home/sat/mcrl-v025-arch-ws`. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

`DIAGNOSTIC_NOT_CLAIM`. No training run, no policy run. Change no constant, threshold, sign, seed, horizon, price, service guard or acceptance rule in the sealed physics; any variant you evaluate must be on a clearly separated copy and labelled.

# Your task

A report in this workspace, `OCCUPANCY-CONVEXITY-2026-09-10.md`, together with the scripts that produced it, concludes that an interior energy-efficiency-optimal beam occupancy exists under two provisioning rules, that it survives setting the fixed per-chain and per-satellite costs to zero, and that it moves with off-axis angle and slant range.

**A research project is about to make that the central claim of a paper. Your job is to break it.**

Argue against the result. Find the error, the hidden assumption, or the artefact. Do not confirm it. If after genuine effort you cannot break it, say so — but only after you have tried the strongest attacks you can construct, and you must report each attack you tried and why it failed.

Do not take the report's arithmetic on trust: recompute independently from the production code where it matters.

# Attacks you must at minimum evaluate, plus any you devise

**A1. The numerator.** The report's pooled efficiency numerator is delivered ACM capacity, not the served rate target. The mode selector picks the lowest-threshold mode whose spectral efficiency meets the requirement, so the delivered efficiency generally exceeds what the users asked for, by an amount that varies rung to rung. Determine whether the interior peak is simply the rung whose delivered-efficiency-to-required-power ratio happens to be best — that is, an artefact of where the mode table's rungs fall — rather than a property of the physics. Recompute the optimum with a numerator that credits only the contracted per-user rate target and report whether the peak moves, flattens or vanishes.

**A2. Zero interference.** The analysis has no cross-beam geometry, so inter-beam interference is identically zero. Construct the cheapest defensible non-zero-interference setting you can from the production coupled solver and determine the direction and rough magnitude of the effect on the optimum. Interference is the one force the published literature uniformly cites in favour of spreading; if it reverses the conclusion at plausible coupling levels, that is the finding.

**A3. Placement.** All beams are packed onto one satellite because no per-satellite ceiling is declared. Test whether the interior result depends on that choice, and whether a per-satellite beam ceiling — which a real payload has — changes it.

**A4. The feasibility filter.** Occupancies whose uncapped power demand exceeds the cap, or which have no eligible mode, are excluded from the partition search. Check whether that exclusion, rather than an efficiency trade-off, is what produces the reported partitions, and whether a capped-but-degraded beam would have been admissible under the production rules.

**A5. The discriminator.** The zero-fixed-cost check is offered as proof that the interior optimum is driven by mode and amplifier physics rather than fixed costs. Verify that claim independently, and check whether the amplifier's square-root supply law alone — a concave cost in radiated power — is sufficient to produce an interior optimum for reasons that have nothing to do with the mode table. If it is, the mode-table explanation is not identified.

**A6. Geometry dependence.** The reported sensitivity to off-axis angle is 8 changes in 144 comparisons under the sealed rule. Determine whether that is a meaningful dependence or essentially integer rounding noise in a partition search, and whether it would survive as a usable decision signal.

# Output

Write `CONVEXITY-ADVERSARIAL-2026-09-10.md` in the workspace root and print it in full as your final message.

Lead with one line stating whether the interior-optimum result survives, and if it does not, the single strongest reason.

Then, for each attack: what you did, the numbers, and a verdict of `BREAKS_IT`, `WEAKENS_IT`, or `SURVIVES`. Be specific about magnitudes; "could matter" is not a finding.

End with the strongest honest statement of what the original result does and does not establish, written so that a hostile reviewer reading only that paragraph could not accuse the project of overclaiming.
