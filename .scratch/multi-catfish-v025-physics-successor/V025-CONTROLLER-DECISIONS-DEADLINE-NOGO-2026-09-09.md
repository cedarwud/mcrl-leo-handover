# Controller decision — the a-r0 matrix is NO-GO until the coordinator meets its decision deadline at matrix scale
Recorded 2026-09-09, server clock 06:22 UTC. Recorded before any matrix outcome exists.

## The finding
The stage-4h report contradicts itself about the coordinator's decision latency.

| section | anchors | result |
|---|---:|---|
| §6 real-anchor gate | 3 | PASS. Decision wall mean 8.250 s, p95 9.816 s, max 9.921 s against a 10 s budget. |
| §7 ten-anchor SMOKE | 10 | Every coordinator decision missed the ten-second deadline and fell back to BASE. |

In the §7 condition, S0, FULL, DROP_C1, DROP_C2, DROP_C3, UNI, ALL_NEUTRAL_CONTROL and NULL are **bit-identical** at 3.492094 Mbit/J, and the realised C1, C2 and C3 marginals and the matched `g_A`/`g_I` are all exactly zero.

## Why this is a NO-GO rather than a recorded deviation
`V025-TONIGHT-RUN-DECISION` §2 pre-declares that a deadline miss is "recorded, not a blocker". That pre-declaration was written for **occasional** misses, where fallback adds noise to a contrast that still exists. It does not cover a **100 %** fallback rate, where fallback *is* the policy for every arm.

At a 100 % fallback rate the arms are not similar, they are the same object. Every contrast the matrix exists to measure is identically zero before a single satellite moves. Launching it would consume a night and return a null that carries no information about C1, C2 or C3, because the coordinator never ran.

The §6 pass margin is about 0.1 s at three anchors. It does not survive 90 anchors across 4 worlds.

**This is not a new scientific gate.** It adds no threshold, no acceptance rule and no claim condition. It is the precondition that the instrument executes the policy it is supposed to measure. Refusing to launch an instrument whose arms are provably identical is arithmetic, not conservatism.

## Decision
1. **`AR0-SEAL-GO` is withheld** until the coordinator's selection completes inside its declared budget on a large majority of real anchors, demonstrated at **at least 20 anchors across at least 2 worlds**, not at 3.
2. The declared 10 s selection budget, the 0.5 s guard and `Δt` are **not** to be changed to satisfy this. Moving the deadline to fit the solver would convert a deployability constraint into a free parameter, which is exactly the failure mode the freeze discipline exists to prevent.
3. Only **provably lossless** speedups are admissible: wider batch-kernel coverage, caching and hoisting, and pruning that carries a proof that the pruned candidate cannot be the argmax. Every optimisation must pass a **selection-identity** test: the same anchors must select the bit-identical configuration for every arm, before and after.
4. If the budget turns out to be unreachable without relaxing a declared constant, that is reported to the owner as a finding about the design, not worked around.

## Related items that must close before the matrix, from the overnight review digest
* `learner.py:40` iterates `range(1, 13)`, giving **12** learner seeds where contract v1.1 and the stage-C spec erratum require **16**. Document-side closed, code-side open. This silently under-powers every conjunction test.
* Six `.sha256` sidecars are absent from the stage-4h workspace, so that tree cannot verify its own seals. The `.md` bodies are byte-identical to the hub copy, so this is a missing-file defect, not a divergence.
* The end-to-end map reports three different final tallies, and its addendum's stated deltas do not reproduce its own totals. The defect register states 60 rows against 65 actual, with DEFECT 41 stated against 45 counted.
* `ADMIT_FULL` carries a "≥ +1 % S0 over BASE" condition that was set under the pre-fix ACM. The correction cut pooled EE by 3.35×. Whether that condition still means what it was written to mean is an open adjudication, and it is the owner's call, not mine, because it touches an admission rule.

## What is unaffected
The interaction-existence probes are unaffected by this decision. They do not run the coordinator under a decision deadline; they enumerate a bounded neighbourhood offline. Their answer about whether positive interaction exists arrives independently of the matrix.
