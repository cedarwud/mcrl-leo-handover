| mutant | executed | rejected | assertion / semantic verdict |
|---|---:|---:|---|
| replace the structured coupling with the existing scalar summary | no | not established | No replayable test-only historical switch was exercised within the budget; no assertion text is available. |
| broadcast that scalar into the correctly shaped pair matrix | no | not established | No shape-preserving broadcast mutant was executed; semantic protection is unproved. |
| keep the values but attach them to the wrong resource pairs | no | not established | No endpoint-permutation mutant was executed; endpoint-association protection is unproved. |
| pass the block into the model interface but bypass the branch that consumes it | no | not established | No consumption-bypass mutant was executed; actual-use protection is unproved. |
| replace the head with a constant positive output | no | not established | No constant-positive mutant was executed; checking both sides of the contrast is unproved. |

## Regression witness result

**NOT ESTABLISHED — `DIAGNOSTIC_NOT_CLAIM`.** The required red/green/red sequence was not run. Consequently there is no designated assertion failure message to report, and the current green test must not be treated as evidence that the historical bug is rejected.

The prerequisite `CROSSGAIN-REPAIR-2026-09-09.md` did not exist after 20 polls at two-minute intervals (40 minutes total). Work therefore proceeded against the current dirty tree, as authorized, without a repair handoff.

## Witness audit

The unfinished in-tree repair does satisfy the representation-side twin conditions for the default-scale pair constructed by `_context` in `tests/stagec_v025/test_contract_v1_acceptance.py`:

- the contexts become canonically byte-identical when `pairwise_cross_gain_terms` is removed, so their non-pairwise context features—including member features, affected-beam rows, global features, and anchor—are identical;
- every affected beam has the same `interference_summary` in both contexts, including `0.9` for `victim` and `0.0` for the other beams;
- both pairwise structures sum to `0.9`, while one uses gains `(0.7, 0.1, 0.1)` and the other `(0.3, 0.3, 0.3)`.

That is not yet a valid oracle witness. The opposite signs come from `_coalition_row("synergy")` and `_coalition_row("antagonistic")`, which supply manually constructed `NetworkOutcome` values (`physical_f=4.0` versus `physical_f=-2.0`). They are not exact profile evaluations through the real V0.25 physics engine. The names `synergy` and `antagonistic` therefore still function as asserted labels. No defensible `eps` above measured engine numerical noise has been established.

The current test additionally trains a model and checks `model.interaction(dominant) > 1.0` and `model.interaction(diffuse) < 0.0`. This can at most support “this setup can fit this diagnostic distinction” once the labels are supplied by a valid engine oracle. It does not establish that the reduced representation is insufficient for a physically admissible opposite-sign pair.

## Honest limit

No conclusion was reached about whether the real physics supports an admissible information-twin pair with exact interaction above `+eps` and below `-eps`. That question remains open; it would be incorrect either to invent opposite labels or to claim the contract's ambiguity premise is false without completing the engine search.

Even a completed indistinguishability witness would prove only that the reduced scalar representation is insufficient. It would not prove that the full representation is sufficient everywhere, that the architecture can use every relevant distinction, that training will find it, or that any learned distinction generalizes. The in-tree test docstring has not yet been repaired to state this limit.

## Required next step

Build one deterministic, agent-runnable test command that:

1. constructs candidate profile quartets and evaluates all four profiles through `mcrl.physics_v025` production resolution;
2. finds or verifies two contexts with byte-identical non-coupling features and equal scalar summaries/totals, but different endpoint-bound pair structures;
3. computes exact `Psi = F(11) - F(10) - F(01) + F(00)` and fixes `eps` from a stated numerical-noise measurement;
4. stops with an explicit physics-nonexistence finding if no admissible opposite-sign pair exists;
5. otherwise executes repaired, historical-collapse, repaired and all five runnable shape-preserving mutants, capturing the obligation-bearing assertion text for each;
6. adds the stated insufficiency limitation to the test docstring.

No thresholds, signs, seeds, horizons, prices, service guards, acceptance rules, or files under `src/mcrl/env/` were changed in this diagnostic pass.
