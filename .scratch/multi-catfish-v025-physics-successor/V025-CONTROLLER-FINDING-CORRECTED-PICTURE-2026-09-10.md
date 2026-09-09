# Controller finding — the corrected-physics coordination picture, from two panels
Recorded 2026-09-10 from the strict-clearance beam-width curve and the thirty-date corrected panel. `DIAGNOSTIC_NOT_CLAIM`. No learner, no training run, no policy run; nothing sealed modified.

## The numerical-implementation question is settled
Two implementations of the corrected provisioning existed, and an adjudication blocked a decision until the stricter one had produced a full five-width curve. It has:

| one-sided width | simple division | **strict clearance** | difference |
|---:|---:|---:|---:|
| **1.66°** (sealed) | −0.3028 % (5/8 negative) | **−0.1768 % (3/8 negative)** | +0.126 |
| 2.40° | +1.2089 % | **+1.9483 %** | +0.739 |
| **3.32°** (the source's own value) | +0.9848 % | **+2.3460 %** | **+1.361** |
| 4.50° | +3.2052 % | +3.0077 % | −0.197 |
| 6.65° | +7.3153 % | **+8.1628 %** | +0.847 |

**No sign changes.** Both remain negative only at the sealed width, so the attempt to rescue a positive value through the stricter numerics fails — exactly as the adjudication predicted.

**The shape does change**, and this corrects something I reported to the owner. Simple division dips from +1.209 % at 2.40° to +0.985 % at 3.32°; strict clearance rises at **every** sampled step. My statement that the monotone rise "does not survive" was an artefact of the defective numerics: under the correct implementation it does survive.

## Thirty dates under the corrected rule
**Mean +0.717 %, sample SD 0.751 %, 95 % interval [+0.436 %, +0.997 %], positive on 26 of 30 dates.** The four negatives are small: −0.075 %, −0.070 %, −0.265 % and −0.230 %. Maximum +3.246 %.

The report leads with the honest reading and I adopt it: **the corrected gap is small and its interval includes practically immaterial values.**

Its compatibility gate is the standard I want everywhere: before any corrected date was run, the copied evaluator was compiled with its divisor set to one and three complete six-anchor dates rerun, with **every deterministic receipt field bit-identical** — world identity, seed, epoch, search paths and counts, terminal certificates, configuration identifiers, committed bits, joules and served counts, and summaries — excluding only wall and CPU timing.

## The finding I did not anticipate
The Spearman rank correlation between the per-date gains under the two provisioning rules is **ρ = +0.006**. Which dates favour coordination under the sealed rule tells you **nothing** about which favour it under the corrected one, and four dates flip from favourable to non-positive. Any date-selection intuition carried over from the sealed rule is worthless.

## Both panels carry the old pairing
| panel | pairing | corrected span |
|---|---|---:|
| twenty anchors | **correct** | **+1.29 %** |
| thirty dates | old | +0.717 % [+0.436, +0.997] |
| five widths | old | −0.177 % at the sealed width |

Both of the latter were started before the pairing defect was found. On the twenty-anchor panel correct pairing raised the corrected figure by 0.75 points. **I am not extrapolating that**; the five-width curve is being re-measured with strict clearance and correct pairing together, and the thirty-date panel's transferable value is its variance structure rather than its point estimate.

## Where this leaves the coordination side
Small, positive, with an interval whose lower edge approaches immateriality. Three routes must each show a resolvable positive marginal inside that band. It is tight — but the owner's bar is an ordering rather than a fixed per-contrast threshold, and a leave-one-out arm can fall **below** the fixed point, so the marginals are not bounded by the band.
