# Controller decision — stop the broad search and cut to the minimum set
Recorded 2026-09-09, server clock about 09:20 UTC. **No probe result has been read.** The reason below is a method fact, not an outcome.

## Why the broad search stops
The `acm2` interaction-existence probe searches a bounded neighbourhood for a configuration with positive interaction. That question now has a **predicted answer to verify instead of a space to search**:

* round 11A derives the exact condition under which a beam holding one or two users selects no transmitted mode while three activate one;
* the engine's own quantile was checked against it and sits inside the window at every realistic elevation, `q10 = 0.42923539` at 10 degrees against a window of `0.3483373150 <= q < 0.6237348355`.

Verifying one predicted configuration costs minutes. Searching a neighbourhood for it costs hours and six concurrent processes each holding an 800 MB tape. When the prediction is this specific, the search is the wrong instrument.

## The operational reason, stated plainly
I oversubscribed the machine. Two probe arms each building their own tapes caused an out-of-memory stall, and the load has sat between 32 and 64 on 20 cores with repeated loss of connectivity. That is my error and it has cost hours today. Running fewer things is not caution here; it is the only way anything finishes.

## What runs
| job | why it stays |
|---|---|
| the predicted-configuration witness test | answers today's question, minutes of compute |
| the adversarial margin review | decides whether the mechanism is real physics or an artefact of a defective rule |
| the minimal stage-C pilot | operational proof that the training path runs end to end |

## What stops
| job | why it stops |
|---|---|
| `acm2` broad neighbourhood search | superseded by the prediction; no result read |
| widened neighbourhood arm | already paused; same reason, and its families were designed around a ranking argument since withdrawn |
| the deadline measurement at scale | the fix is implemented and its report's results sections are empty placeholders. The matrix is withheld tonight for other reasons, so the measurement is not on today's critical path |

## Standing
No threshold, sign, seed, horizon, price, acceptance rule or claim condition changes. No run is authorised. Nothing stopped here had reported a result, and none was read before deciding.
