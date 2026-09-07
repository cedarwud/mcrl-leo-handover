# Multi-Catfish MCRL V0.23 LC-SRS gate relaunch decision R3

Date: 2026-09-05  
Status: **R3 AUTHORIZED AFTER RESEAL AND FOCUSED TEST PASS**

## 1. R2 disposition

The R2 server run is an invalid execution receipt, not a scientific C3
outcome. It stopped in the first source batch before writing any source JSON,
source array sidecar, source manifest, learner fit, composition receipt, or
final result. Its `FAILED` marker and run directory shall be retained and
shall not be resumed, repaired, or interpreted as negative LC-SRS evidence.

A one-world diagnosis on the same TRAIN world `2026121705`, with unchanged
physics, source formula, multiplier, checkpoint, and keyed fading family,
recovered the collapsed exception chain:

```text
LCSRSC3EncoderError: segment age exceeds episode length
```

The exception originated in
`src/mcrl/runtime/ee_axis_lcsrs_c3_encoder.py::_committed_temporal`, before any
source receipt was sealed.

## 2. Root cause and bounded repair

The rejected state is legal simulator state. Under the frozen
`uniform-episode-length` warm start, the initial segment age is drawn from
`0,...,H-1`. A served segment records `warm_age + 1` at the first committed
slot and increments on every continuation. With `H=10`, a valid persistent
segment can therefore have age 10 before decision 1 and age 18 before decision
9.

The C3View feature domain is bounded to `[-1,1]`, and the existing ordinary
segment-age encoding is `age/H`. R3 therefore defines the domain-complete
encoding as

```text
bounded_segment_age = min(age, H) / H
```

for nonnegative integer `age` and positive `H`. This preserves every value
previously accepted by the implementation, including `age=2, H=10 -> 0.2`,
and saturates only valid warm-start continuations older than one episode.

This is a runtime descriptor-domain repair. It does **not** change the LC-SRS
teacher target, the four `00/10/01/11` physical profiles, lambda, kappa, worlds,
draws, source selection, learner, loss, checkpoint lineage, composition rule,
service guard, or acceptance thresholds.

## 3. Failure observability repair

The R2 production source wrapper collapsed every underlying exception into the
same generic message. Before R3, the source wrapper must retain the fail-closed
exit status while also printing the world, process id, and complete chained
traceback to the controller log. This changes diagnostic observability only;
it does not change a source shard or a scientific output.

## 4. Required prelaunch evidence

R3 may launch only after all of the following hold:

1. the focused C3 encoder regression verifies ages `0,2,9,10,11,18` map to
   `0,.2,.9,1,1,1` for `H=10`;
2. candidate-independent repetition, missing-incumbent sentinel, deterministic
   repeated capture, immutability, and the full C3View bound still pass;
3. the source wrapper test proves that a nested exception and its world are
   visible in stderr;
4. the StepResult-to-last-outcome repair remains covered;
5. the complete frozen V0.23 focused suite passes;
6. `PREFLIGHT-MANIFEST.json` and its digest are regenerated from the exact R3
   implementation and tests, and the preflight validator passes locally and on
   the Ubuntu server.

## 5. R3 execution boundary

R3 must use a fresh server checkout/run root and a fresh tmux name containing
`20260905-r3`. It must retain the frozen eight TRAIN worlds
`2026121705--2026121712`, the three student seeds, 32 matched draws, source
parallelism 2, fit parallelism 4, composition parallelism 2, and CPU device.

R3 remains an offline C3 observability/source-to-learner/composition
development gate. It does not authorize TEST, episode-policy training, a
100/500/1500/3000/9000-episode run, efficacy claims, or any modification of C1
or C2.

R3 may be interpreted only after the existing independent finalizer has fetched
and reverified a complete sealed result tree. A runtime failure remains a
runtime failure; a gate token remains development evidence rather than policy
efficacy.
