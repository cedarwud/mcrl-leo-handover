# Restore the pairwise cross-gain block to the C3 encoder, and make T2 actually test it

This is a contract-conformance repair. It touches the learner's feature path only. Do not change physics, thresholds, signs, seeds, horizons, prices, the service guard or any acceptance rule.

## The defect
`V025-STAGES-6-8-CONTRACT-v1.2-AMENDMENT-2026-09-09.md` §C2 requires the encoder's input to contain "the **pairwise cross-gain terms among the affected beams** (not only a scalar interference summary — a summary can hide exactly the difference that flips a coupled fixed point)."

In `/home/sat/mcrl-v025-pilot-ws`:
* `scripts/run_v025_pilot_c3.py::_coalition_context` computes `relations = _cross_gain_terms(...)`, then reduces them with `math.fsum` into `AffectedBeamContext.interference_summary` and into a sum and a max in `global_resource_features`.
* `src/mcrl/stagec_v025/coalitions.py::AffectedBeamContext` has **no pairwise field**.

So the pairwise structure is computed and discarded. The head cannot distinguish one aggressor carrying most of the interference from many weak ones summing to the same total, and those cases have opposite consequences for whether a two-member coalition helps.

## Task 1: carry the pairwise block
Add an ordered, canonical pairwise cross-gain block to the coalition context and thread it into the set-conditioned interaction head's encoder.

* Keep `interference_summary` as it is. This is an addition, not a replacement, so existing receipts stay comparable.
* The block must be **deterministic and permutation-canonical**: sort by (source beam key, target beam key) so the same physical situation always yields the same bytes. The existing member-order invariance test must still pass, and add the same invariance for the pair block.
* Give it a fixed, declared truncation rule if the head needs a bounded input, for example the top-K pairs by magnitude with K declared in the context and the residual sum carried alongside so nothing is silently dropped. State K in the report.
* Update the context's schema version and its payload hashing so a stale shard cannot be silently mixed with a new one. The pilot has already hit `StageCContractError("... context schema drifted")` several times; make the drift explicit and legible rather than a bare raise.

## Task 2: make T2 test what it was written to test
`tests/stagec_v025/test_contract_v1_acceptance.py::test_T2_information_twins_reversal_and_additive_placebo` currently contains **zero** occurrences of `cross_gain` or `interference`. It builds contexts labelled `synergy` and `antagonistic` and asserts the head predicts synergy on the one labelled synergy. That asserts the head can fit a supplied label; it cannot fail for the reason the test exists.

Implement the extension the amendment actually specifies:

> the information-twin pair must be separable with the full context and **provably ambiguous when the cross-gain block is removed**.

Concretely, construct two coalitions that are **identical in every scalar feature**, including `interference_summary`, occupancies, activation, member count and shared capacity, but differ in the pairwise distribution: one has a single dominant aggressor, the other has many weak ones summing to the same total. One is genuinely profitable and the other is not.

* With the pair block present, assert the head can separate them.
* With the pair block removed or zeroed, assert the two contexts are **byte-identical**, so no model whatsoever can separate them. That is the provable ambiguity, and it is stronger than asserting a particular model fails.

## Task 3: report what the old features could see
As a diagnostic, not a claim: over the existing pilot shards, measure how much of the variance in the exact interaction value is explainable from the old scalar features alone, versus with the pair block added. A simple linear or gradient-boosted fit is fine. If the old features are near-uninformative, say so with the number.

## Workspace and constraints
`/home/sat/mcrl-v025-pilot-ws`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, `/home/sat/mcrl-v025-prevalence-ws`, or `src/mcrl/env/`. Run the stage-C test suite and report the pass line. At most 3 concurrent processes, `nice -n 10`.

Write `CROSSGAIN-REPAIR-2026-09-09.md` in the workspace root and print it as your final message: what you added, the canonical ordering and truncation rule, the T2 rewrite with its byte-identity assertion, the variance-explained numbers, the test line, and anything you could not do.
