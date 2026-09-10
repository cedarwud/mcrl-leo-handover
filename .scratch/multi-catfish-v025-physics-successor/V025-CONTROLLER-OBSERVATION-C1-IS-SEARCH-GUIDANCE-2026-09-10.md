# Controller observation — the first route already predicts what the 451 % search needs at every step
Recorded 2026-09-10, arising from the owner asking why learning cannot approach the improvement a classical search achieves. This is **reasoning from measured facts, not a measurement**, and it is recorded as a candidate direction rather than a proposal. `DIAGNOSTIC_NOT_CLAIM`.

## The structural observation
The first route's target is `d_i = F(a_i, a⁰_{-i}) − F(a⁰)` — the surplus from user *i* deviating alone from the reference.

The iterated best-response search that produces the entire improvement over the geometric baseline asks, at **every step**, which single-user move helps most. That is the argmax of exactly that quantity, recomputed at the current configuration.

**The search that delivers the improvement computes this route's label at every one of its steps.** It makes about seventy-eight committed moves over four and a half passes, scanning every legal alternative each time — roughly twelve thousand evaluations per anchor — which is precisely why it takes about sixty-five seconds.

So the first route is not ill-suited to its target. **It is attached to the wrong consumer**: its label is native to guiding a search, and it is currently used to rank perturbations of that search's *output*.

## Where the improvement actually comes from
| arm | pooled efficiency, corrected rule |
|---|---:|
| geometry-only baseline | 7.93 |
| **iterated unilateral, not learned** | **43.71** |
| bounded joint search, exact evaluation | 44.27 |

The learned layer sits downstream of the second row. It **inherits** that improvement and was never asked to produce it; its entire working range is the third row's margin over the second, about one per cent. That ceiling is an architectural consequence, not a property of the problem — the problem has the larger margin, and it was assigned to a component that does not learn.

## Whether the three-route design would survive a reattachment
The roles map naturally onto search guidance: which user to move now, whether that move persists, and when a single move is insufficient so several must go together. The mechanistic separation already measured would carry over — today's probe found the third route changing **zero** proposed assignments while the first two change twelve to twenty-six and twenty-nine to sixty-nine, so they already enter through different paths.

Two things would **not** survive:
- the contract's identity fixing the sum of the first and third routes to the joint objective change, which exists to make coalition scores exact and is unnecessary for guidance;
- the label distribution, because the target would be evaluated at every configuration the search visits rather than at an anchor's reference. **Whether the first route predicts well on that distribution has never been measured.**

## The nearest precedent
This is the learning-to-branch pattern that the external round already cited: learn a cheap surrogate for an expensive expert decision so the existing search runs faster, rather than replacing the search. Applied here it would let a learned component stand legitimately on the large margin, by producing it sooner rather than by improving on it.

## Why nothing is being proposed
Three reasons to measure before moving. The screening run will separate the cases: if all three routes show positive contributions where they are, nothing needs changing; if the **first** route alone shows nothing, that is evidence *for* this observation rather than against the route; if none of the three shows anything, the problem lies elsewhere and reattachment would not help.

The screen is cheap and those three outcomes point to three different next steps. And a reattachment is a larger change than the one I declined earlier today for removing the three-route structure — it would rewrite the targets, the heads and three contract sections. It is not something to start on an argument.
