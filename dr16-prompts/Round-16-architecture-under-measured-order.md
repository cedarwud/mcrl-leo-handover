# Round 16: my interaction model is provably misspecified. What replaces it?

## The measurement that changed the question
I asked you earlier whether my anchored coalition-interaction residual was the right target, and you correctly said that for coalitions of three or more it is the sum of every interaction order above one, not a pairwise quantity. I now have the number.

On 5,003 coalitions of size three or more, computing

```
R3(A) = Psi(A) - sum over pairs {i,j} in A of Psi({i,j})
```

with all members holding the same proposed actions in both terms, gives, in normalised units:

| statistic | value |
|---|---:|
| p05 | −0.787 |
| p50 | ≈ 0 |
| p95 | +4.209 |
| max | +15.18 |
| mean | +0.454 |
| mean absolute | +0.775 |
| fraction with abs value above 1e-3 | **38.50 %** |

So a pairwise-only interaction model cannot represent about two fifths of my labelled coalitions.

## The physical mechanism behind it, which may constrain the answer
The dominant verified mechanism is a **threshold in shared-resource occupancy**. Under equal-airtime time-division multiplexing with a per-user rate target, a beam's occupancy sets the required modulation mode, which sets the transmit power. A beam holding one or two users selects no transmitted mode at all; a third arrival activates one. So two arrivals together produce credited bits where either alone produces none.

That is a step function of a summed load, which is exactly the shape you identified as producing genuine higher-order terms. A second mechanism is a unanimity effect: a beam's fixed per-chain power is saved only when its **last** occupant leaves.

## Corpus, for feasibility
11,924 exactly-labelled coalitions across 180 anchors, sizes 2 through 6 with counts 6921, 4691, 270, 36, 6. Roughly 46 coalitions per anchor at the median. Labels are exact evaluations; an additional coalition costs one new physics evaluation once the anchor's baseline and singletons are cached.

## What I am asking

1. **Given that the interaction arises from thresholds on summed resource load rather than from agent-to-agent affinity, what model form should I use?** I am currently planning an anchored per-resource residual, `sum over resources r of [ g_r(l_r0 + sum_i d_l_ir) - g_r(l_r0) - sum_i ( g_r(l_r0 + d_l_ir) - g_r(l_r0) ) ]`, with a learned nonlinear `g_r`. Is that the right family here, what does it assume that I should test rather than presume, and what would you use instead?

2. **How should a step-like `g_r` be learned?** The true function is close to a staircase in occupancy. A smooth network may fit the average and miss the step, which is the entire mechanism. Is there an established treatment for learning threshold-shaped resource functions from aggregate outcomes, and how do I avoid smoothing away the thing I am trying to capture?

3. **Does my size distribution support learning higher-order structure at all?** Sizes 4, 5 and 6 have 270, 36 and 6 examples. Am I data-limited for the very orders that are misspecified, and if so is the right response to generate larger coalitions, to choose a form whose higher-order behaviour is determined by a low-dimensional `g_r` rather than fitted per order, or to accept a bounded misspecification and report it?

4. **Ranking rather than regression.** My selector only needs the correct ordering at one anchor. Does the misspecification argument weaken if the target is a ranking, since a pairwise model could preserve order while getting magnitudes wrong? Or does a 38.5 % material third-order share break ordering too? How would I test that cheaply and decisively?

5. **What would tell me the third-order structure is not what limits me?** I would rather learn that early than after fitting a more expressive model. Is there a diagnostic that bounds the achievable selection quality of a pairwise form on this corpus, without training the alternative?

## What I will do with the answer
Choose between a resource-aware form, a ranking objective, and accepting bounded misspecification with a stated limitation. Please distinguish established results from your judgement, and say where my numbers are too sparse to support a recommendation.
