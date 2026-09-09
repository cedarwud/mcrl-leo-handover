# Open owner decision — how to test "each component individually raises efficiency", with two reviewers disagreeing
Recorded 2026-09-10. Commissioned as a design consultation to `gpt-6-astra` at ultra effort and to `claude-fable-5-1`, both given the same neutral prompt that did not state my position. `DIAGNOSTIC_NOT_CLAIM`. Nothing was run; nothing sealed was modified. Related: [additive split], [pair insufficiency], [novelty closed].

## The owner's requirement, as stated
Each of the three components must individually improve pooled efficiency over a control. Adding two or three interacts, so magnitudes will not add, but every subset must stay positive and the ordering must hold: FULL above any two, any two above the control.

## Where the reviewers agree
- The phrase names **more than one experiment**, and interactions mean one does not establish another. Leave-one-out measures the *conditional* contribution of a component when the other two are present; single-component-only measures *standalone* benefit against a common control. These are different claims.
- The intervention is **neutral-source substitution**, not deletion. "C1 only" means only that route's training source is informative while the other two are trained on neutral sources, with all heads retained and deployed. It never means removing a predictor. Any wording that implies presence-versus-absence is wrong.
- **The reference matters and must be named.** Three candidates differ by orders of magnitude: the all-neutral control, the certified unilateral fixed point, and the geometry-only baseline. Neither of the outer two may silently stand in for the fixed point.
- The sealed panel already covers five of the eight factorial cells — the full arm, the three pair arms, and the control. The three singles are missing.
- **Neither would let a comfortable ordering license the conclusions the project wants.** Both refuse: that contributions are additive or independent; that the three-part architecture is necessary or better than a fairly trained simpler ranker; that the learned layer deserves credit for the prefix's several hundred per cent; that a large ablation gap is a large physical headroom.

## The disagreement
**One says add three arms.** Testing the literal standalone requirement needs the three single-source configurations. That yields nine or ten policies. The existing six can answer only the narrower "full above each pair above control" question; they cannot establish standalone efficacy or positivity of every non-empty subset. The necessary inequalities are three singles over the control, three pairs over the control, three full-over-pair, with full-over-control following by transitivity — and the separate contractual unilateral comparison still required on top.

**The other says do not add them, and restate the requirement instead.** Its argument has one step the first does not: **the entire span a ranker can add above the certified fixed point is about the same size as the margin demanded per contrast.** Therefore any leave-one-out gap that clears the margin is evidence that the *reference arm fell below the fixed point*, not that the missing component was worth that much. On that reading the recently measured full-minus-drop gap of **+15.6 %** is a degeneracy signal, not a contribution signal — and I reported it to the owner as encouraging, which was wrong.

Its recommendation is to restate the requirement as: each leave-one-out marginal has a positive paired lower bound; **every learned arm sits at or above the fixed point**; the full arm beats the unilateral comparator; and the materiality margin applies to full-over-fixed-point rather than to each contrast separately.

## What the second reviewer adds that costs nothing
- **Deterministic reference arms need no learner seeds** and remove the largest confound. They should be added first, not last.
- **A matched-anchor tier.** On common anchors the prefix and catalogue are identical across arms, so each catalogue row's realised outcome can be evaluated once and every arm's choice becomes a lookup. **Nine arms then cost about one.** It answers the first and third components cleanly but cannot answer the second, whose value is multi-step by construction.
- **Seeds are a nuisance replicate for a paired ordering test.** Three to five lose little; twelve buys a robustness statement, not power. Reserve the full count for the full arm and the three pair arms.
- **A size-prior comparator for the third component.** Its correction is a large, nearly size-proportional term. Until the full arm beats a variant where that component is replaced by a fixed per-size prior, the honest description is that the sum needs a size penalty and the component supplies one.

## My reading
The two are not as far apart as they look. The first answers "what tests the requirement as written"; the second answers "what would the result mean". Both are needed. The cheap path is the matched-anchor tier, which makes the singles nearly free and so removes the cost objection to running them — leaving only the interpretation question, which the degeneracy screen answers.

What I would put to the owner is therefore: **run the singles, but at the matched-anchor tier and with every arm first screened against the certified fixed point.** An arm below the fixed point is disqualified from contributing evidence before any ordering is read.

## Standing
No decision taken, no arm added, no contract touched. The owner asked that this be discussed with both reviewers before anything was drafted; it has been, and they disagree on the central question.
