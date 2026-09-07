# Opus Max SMC-ER v0.4 concept review receipt

- Date: 2026-08-27
- Reviewer: Claude Opus 5, effort max
- CLI session: `28054d0e-8c7e-475f-84d2-6d7c99b3c47e`
- Result UUID: `497b1b1d-2e64-4072-a318-109625019f74`
- Mode: read-only concept, lineage, and figure-readiness review
- Verdict: `REVISE_BEFORE_FIGURE_HANDOFF`

## Scope read by the reviewer

- `docs/MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md`
- `docs/MULTI-CATFISH-CONCEPT-ALGORITHM-FREEZE-V0.1-2026-08-27.md`
- `/home/u24/papers/modqn-paper-reproduction/docs/ADR-004-phase1-source-transfer-diagnostic.md`
- the Phase-I and dual-rollout sections of
  `/home/u24/papers/modqn-paper-reproduction/docs/catfish-explainer-package/07-true-catfish-formulas.md`

The complete response is preserved in the Claude session transcript at
`/home/u24/.claude/projects/-home-u24-papers-mcrl-leo-handover/28054d0e-8c7e-475f-84d2-6d7c99b3c47e.jsonl`.

## Blocking documentation findings

1. The advertised `R3 <-> C3` mapping is false in v0.4: canonical `r3` is load
   balance, whereas the current C3 private signal is marginal payload power.
   The architecture and C3 figures must not encode that mapping unchanged.
2. The two documents disagree about whether the frozen C1 EXP corpus enters
   C1 or Main. The source lineage supports C1 replay prefill; the Algorithm 1
   listings must state the destination explicitly.
3. The concept freeze omits the Main-consumer / observational-alias gate even
   though the technical method forbids specialist transfer before it passes.
   The gate must appear in the operator, phase sequence, failure table, and
   architecture caveat.

## Major bounded revisions

- Align Stage-0 failure semantics: a failed role is removed from the promoted
  method rather than silently redesigned after seeing the sealed evidence.
- Record `H=10` and the current decision interval as experiment context, while
  keeping role horizons outside the top-level theory claim.
- Add a C1 non-learning source gate and disclose the difference between the
  LEO-native generator and literal RIS DFT/WMMSE Phase-I.
- Add a Phase-I/M1/M2/M3/ACRM lineage table, including intentional departures.
- Explain and measure C1/C3 overlap rather than merely asserting that they are
  non-duplicative.
- State that behavior probabilities are provenance-only for one-step
  off-policy Q-learning, and disclose the consequence of bundle-uniform
  weighting.
- Make Stage-0 seeds disjoint from pilot evaluation seeds.
- Apply the same anti-overclaim warning to both C2-to-EE and C3-to-EE arrows.

## Stable core accepted by the reviewer

- four logical learner states and six online Q functions plus targets;
- atomic complete joint bundles as the dose, quota, age, and routing unit;
- specialist-private learning signals never enter Main replay, evaluation,
  checkpoint selection, or the headline metric;
- executed outcomes are retained regardless of sign;
- Main receives the unchanged complete environment reward vector;
- no voting, auction, coordination, action fusion, intent exchange, or
  post-training override; and
- Main-only evaluation and deployment.

## Claim ceiling

The review found no present top-level conceptual blocker and explicitly judged
the repair as bounded documentation/design clarification rather than evidence
for effectiveness. Until the revisions and empirical gates pass, the method is
only a coherent proposed, falsifiable algorithm. It is not validated, proven
EE-improving, jointly best, globally novel, or ready for final result claims.
