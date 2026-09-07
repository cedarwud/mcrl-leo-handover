# Sol Ultra fresh-context review of SMC-ER v0.3 — 2026-08-27

## Identity

- Reviewer: `gpt-5.6-sol`, reasoning effort ultra, fresh context
- Reviewed file SHA-256:
  `e0bedb7aac35544b8be166fe3be343a7fc998fa572c2365d236c918503f25999`
- Independently recomputed SHA: exact match
- Verdict: **`REVISE_BEFORE_IMPLEMENTATION`**

## Blocking defects

1. C3 moved beyond its authority. Its result adjudication permits only a
   sealed, new-seed, non-training H3 shadow and withholds implementation, Main
   transfer, and an RL pilot.
2. C2/C3 option learning was not Bellman-complete. The specialist state did
   not include open-option identity or remaining duration, and C3 continuation
   actions, reference sequence, termination, and specialist observation were
   under-specified.
3. Main replay lacked an atomic joint-bundle credit contract: focal versus all
   rows, bundle/row quota units, weighting, specialist update rows, duplicate
   routing, and the required observation-alias/focal-versus-bundle gate were
   not fixed.
4. The proposed controls did not fully identify the mechanism: C1 combined EXP
   and ACRM; C2 omitted stay-if-possible and post-release accounting; C3 random
   within its certified mask tested ranking but not certificate value; and
   independent learning trajectories cannot promise identical realised trigger
   frames/support after state divergence.
5. Stochastic smoke could miss rare C3 paths, and the short pilot lacked frozen
   seed-level directional rules, safeguard thresholds, deferred-event
   accounting, and an explicit no-training-stability claim.

## Minimum correction contract

- Add Stage 0: no C3 implementation, transfer, smoke, or RL pilot before a new
  sealed H3 shadow passes; any failure removes C3.
- Give specialists augmented option state
  `(base_state, option_open, physical_association, remaining_steps)`; restrict
  continuation masks and log conditional probability one.
- Define C3's deterministic reference/non-focal sequence, relocation hold,
  validity, early termination, and certificate commitment before stochastic
  execution.
- Make one environment step one atomic joint bundle containing the complete
  `U x 3` canonical reward matrix. Count dose/quota/age by bundle, unfold Main
  rows atomically with total weight one, update C2/C3 only on focal rows, and
  prohibit duplicate routing.
- Add observational-alias and focal-versus-bundle Main-consumer gates.
- Split C1 mechanism controls or limit the claim to a composite.
- Add matched random and stay-if-possible C2 controls, score the release step
  and full episode, and make served-to-unserved a hard failure.
- Distinguish C3 Q-ranking control from a broad hard-safe pre-certificate
  control.
- Promise identical trigger/support only for exact paired anchor forks;
  independent arms match ex-ante schedule, budgets, updates, quotas, and
  opportunity strata and report realised divergence.
- Add deterministic path fixtures and frozen seed-level pilot rules.

## Nonblocking findings

The three roles remain scientifically distinct. Private rewards can remain
private if the bundle contract is enforced. Main replay remains an acknowledged
off-policy/function-approximation heuristic. The draft does not resurrect the
failed variants, and its novelty boundary is honest.

## Permissible claim after correction

SMC-ER is a proposed, falsifiable training-time experience-routing composition
with three distinct candidate specialist roles; specialists retain complete
outcomes, Main alone receives canonical reward vectors, and Main alone acts at
evaluation. Effectiveness, C3 support, joint superiority, generalization, and
global novelty remain unestablished.
