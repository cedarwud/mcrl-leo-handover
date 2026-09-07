# V0.18 post-result cross-model adjudication

Status: `REVIEW_RECEIPT_NOT_SCIENTIFIC_AUTHORITY`.

All three reviews were fresh/read-only and were instructed not to run a
simulator, train a learner, open TEST, alter authority, or treat TRAIN evidence
as efficacy.

## Decisions

| reviewer | route | decision |
|---|---|---|
| GPT-5.6 Sol Ultra | isolated subagent `/root/v018_postresult_sol_review` | `GO_FRESH_SOURCE_LEARNED_Q3_GATE` |
| Claude Fable 5.1 Max | CLI session `159e1bf7-e6b6-495d-8e1b-24c571c697bb` | `GO_FRESH_SOURCE_LEARNED_Q3_GATE` |
| Claude Opus Max | CLI session `395b3904-3780-48d8-aa80-1b902570bbc2` | `GO_FRESH_SOURCE_LEARNED_Q3_GATE` |

## Common verified reading

- The 36-cell panel is complete: four worlds by three arms by three
  lineages.
- Recomputed pooled ratio-of-sums deltas are `+1.030617%` for `EXACT_ZR` and
  `+1.102733%` for `NOMINAL_ZR`.
- Both directions are positive in four of four world pools and three of three
  lineage pools; served-user-step delta is zero.
- Mechanics, compatibility, Q1/Q2 immutability, kappa identity, manifests,
  source diagnostics, and the no-TEST/no-learner/no-episode boundary passed.
- These facts establish an analytic target/context direction only. They do
  not establish that a learned Q3 works.

## Required prospective closures

The reviews converged on these next-gate requirements:

1. use fresh complete-world TRAIN and VALIDATION splits;
2. implement and authenticate the missing production source harvester;
3. implement decision-level validation metrics and explicit nulls rather
   than using MSE as the scientific gate;
4. bind exactly 100 updates, architecture, optimizer, kappa, Q1/Q2
   checkpoints, batch schedule, thresholds, receipts, and stop boundary
   before opening outcomes;
5. explicitly adjudicate the frozen six-token input schema's observed
   predecision candidate-SINR token instead of silently inheriting ambiguous
   Section 7 wording;
6. preserve the claim ceiling: a learner-gate pass may authorize only a
   separately sealed short-episode TRAIN screen.

The current learner preregistration remains a draft until these code and
contract closures are complete. This review receipt itself authorizes no run.
