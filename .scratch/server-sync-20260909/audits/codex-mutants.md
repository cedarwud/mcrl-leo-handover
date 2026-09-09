# Prove the repaired test rejects the historical bug, and four nearby variants

`DIAGNOSTIC_NOT_CLAIM`. Budget 90 minutes. Wait until `CROSSGAIN-REPAIR-2026-09-09.md` exists in `/home/sat/mcrl-v025-pilot-ws`; if it does not, poll every two minutes for up to 40 minutes, then proceed with whatever is in the tree and say so.

## Why this exists
A repaired test that passes on the repaired code proves almost nothing. The evidence that matters is the opposite direction: **which specific wrong implementation does this test demonstrably reject?** The test being replaced passed for months while the requirement it named was violated, so a fresh green run is not acceptable evidence this time.

## Part 1: fix the witness itself, which is currently too weak
The repair task was told to construct an information-twin pair that is identical in every scalar feature. Verify that it actually satisfies **all three** of these, and repair it if not:

1. every non-coupling feature is identical between the two members of the pair;
2. **the forbidden scalar itself is identical**, that is `interference_summary` is equal for both. A pair whose coupling totals differ is still separable by a scalar-only encoder and would not catch the historical bug;
3. the pairwise structures differ, for example one dominant contributor versus many weak ones summing to the same total.

## Part 2: the opposite answers must come from an oracle, not a label
The two members must have genuinely opposite correct answers, established by **exactly evaluating the interaction with the real engine**, not by a fixture named `synergy` or by an asserted label. Require a margin: one member's exact interaction above `+eps` and the other below `-eps`, with `eps` chosen above the numerical noise of the evaluation and stated in the report.

If the physics does not support such a pair on the admissible domain, **say so and stop**. Do not invent opposite labels to make the test constructible. That finding would itself be important: it would mean the contract's ambiguity claim needs revision.

## Part 3: the regression witness
The sequence that constitutes evidence is:

1. the new test **fails** on the historical implementation, the one that summed the pairwise terms;
2. it **passes** on the repaired implementation;
3. replaying the historical implementation makes the **designated assertion** fail again, and the failure message names the obligation.

Implement this by keeping the old collapsing code path available behind a test-only switch, so the old bug is replayable rather than described. Report the actual assertion text that fires.

## Part 4: five semantic mutants, each of which must be rejected
For each, record whether the mutant actually executed, which assertion rejected it, and whether that assertion expresses the obligation rather than merely crashing.

| mutant | what its rejection proves |
|---|---|
| replace the structured coupling with the existing scalar summary | the historical bug is detected |
| broadcast that scalar into the correctly shaped pair matrix | correct dimensions are not correct values |
| keep the values but attach them to the wrong resource pairs | endpoint association matters, not the multiset of numbers |
| pass the block into the model interface but bypass the branch that consumes it | acceptance checks actual use, not argument presence |
| replace the head with a constant positive output | both sides of the contrast are checked, not only the positive one |

A mutant that fails with a `KeyError` or a shape error has **not** demonstrated semantic protection. Prefer shape-preserving, runnable wrong implementations, and say which of the five are of that kind.

## Part 5: state the limit honestly
An indistinguishability witness proves the **reduced** representation is insufficient. It does **not** prove the full representation is sufficient everywhere, that the architecture can use the distinction, or that training will find it. Write that limitation into the test's docstring so a future reader does not over-read it. If you also want to show the architecture can use the distinction, fit a small model through the real production path and label that claim as "this setup can fit this diagnostic distinction", never as generalisation.

## Constraints
Workspace `/home/sat/mcrl-v025-pilot-ws`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, `/home/sat/mcrl-v025-oracle-ws`, `/home/sat/mcrl-v025-prevalence-ws`, or `src/mcrl/env/`. Change no threshold, sign, seed, horizon, price, service guard or acceptance rule. At most 3 processes, `nice -n 10`.

Write `MUTANT-WITNESS-2026-09-09.md` in the workspace root and print it as your final message. Lead with a table of the five mutants and whether each was rejected, then the regression witness result.
