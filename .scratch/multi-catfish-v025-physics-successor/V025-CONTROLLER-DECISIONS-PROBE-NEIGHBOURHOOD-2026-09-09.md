# Controller decision — the probe's candidate neighbourhood has a mechanism-specific blind spot; declare a widened arm
Recorded 2026-09-09, server clock 06:25 UTC. **No regime has reported a verdict.** Recorded before any probe outcome exists, from reading the instrument's source, not its results.

## What the probe searches
`probe_interaction_existence.py` re-anchors at a certified iterated unilateral optimum `u` and enumerates a bounded joint neighbourhood of three kinds:

1. `pairwise-topK-top2` — pairs drawn from the top `PAIRWISE_TOP_K_USERS = 10` users, each contributing one of their top `TOP_PROPOSALS = 2` legal options. About 180 candidates per anchor.
2. `beam-evacuation` — one complete evacuation set per active beam.
3. `s0-top-two` — two complete profiles assembled from every user's rank-r single-user proposal.

The top-K users are selected by `sorted(d_best, key=lambda user: (-abs(d_best[user]), user))`.

## The blind spot
At a certified unilateral optimum every legal single move is non-improving, so `d_i^u <= 0` for all `i`. Ranking by `-abs(d_i)` therefore selects the ten users whose best available single move is the **most harmful**, and excludes the users whose `d_i` sits closest to zero.

The canonical positive-interaction coalition in this physics runs the other way. A congestion-relief swap needs:
* a user who is **nearly indifferent** between two beams, so vacating costs almost nothing. Small `|d_i|`. Excluded by the current ranking.
* a user who is **blocked** and whose own best legal move is badly degraded. Large `|d_i|`. Included.

The pair that constitutes the swap therefore straddles the ranking, and only one half of it is enumerated. Compounding this, the pairwise family draws only each user's **top two** options by the coordinator objective, while the vacating half of a swap moves to an option that is, by construction, *not* among their best.

The search is thus concentrated where theory says the interaction is least likely to be, and thin exactly where it is most likely to be.

## Why widening the search is admissible here, and is not goalpost-moving
The probe asks an **existence** question: does any joint move from `u` carry `Psi_A^u > 0` while remaining service-guarded?

* A positive answer is a **constructive existence proof**. A specific configuration either exhibits a positive interaction term and an improved guarded objective, or it does not. Enlarging the search cannot manufacture one.
* A null answer is only ever "none within the searched neighbourhood and budget". Enlarging the neighbourhood makes a null **stronger**, never weaker.

Search breadth is therefore not a parameter that can be tuned toward a desired conclusion, unlike a threshold or a margin. This declaration changes no threshold, sign, seed, horizon, λ, κ, η_ref, acceptance rule or claim condition, and creates no new gate.

## Decision
1. The two running probes are **not modified and not killed**. The pre-fix arm and the corrected-ACM arm both complete under the original neighbourhood.
2. A third arm, `WIDENED`, is declared now and runs on the corrected physics when a compute slot frees. It **adds** candidate families and removes none:
   * `pairwise-marginal` — pairs drawn from the ten users with the **smallest** `|d_i^u|`, each contributing their top four options.
   * `pairwise-straddle` — pairs formed by taking one user from the smallest-`|d_i|` ten and one from the largest-`|d_i|` ten, which is the shape the swap argument predicts.
   * `vacate-and-fill` — for each active beam, one candidate that moves the beam's most nearly indifferent occupant out and moves in the blocked user whose best legal option is that beam.
   * `triples-marginal` — triples among the five smallest-`|d_i|` users, to test whether interaction needs a coalition larger than two.
3. The `WIDENED` arm reports the same census as the original: certified-`u` status, improving-move counts under both `G` and `F`, the positive-`Psi` census independent of improvement, coalition sizes, and the search budget, so that a null remains readable as budget-limited.
4. Results are reported **per arm and never pooled** with the original neighbourhood. The original arm's null or positive stands on its own record.

## Honest statement of what this cannot fix
Even the widened neighbourhood is a bounded local search around one anchor point. A null across all three arms means "no improving joint move was found within the declared families and budget at the certified unilateral optimum". It does not prove that no such move exists anywhere in the configuration space, and no report from this probe may say that it does.
