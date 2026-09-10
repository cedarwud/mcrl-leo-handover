# What each training outcome means, and what is already dispatched against it

**2026-09-10 14:35 UTC. Written while both runs are in flight and no contrast exists.**
Design phase: these are exploration branches, not acceptance rules.

Two runs are live on the same 22-anchor physics, same arms, same epochs, same seeds. **The
only difference is the Q1 representation** — v1 (defective) versus v2 (off-axis repaired,
elevation added, duplicate indicators dropped).

---

## The outcome space for `FULL - ALL_NEUTRAL_CONTROL`

| # | outcome | what it means | response | prepared? |
|---|---|---|---|---|
| 1 | **positive on v2, ~0 on v1** | the representation was the binding constraint | repair Q2 as well and retest; representation is the design direction | **`Q2REPAIR` dispatched** |
| 2 | **~0 on both, flat across checkpoints** | heads learned nothing usable | `LRSWEEP` discriminates: bad learning rate vs unlearnable target vs arms that cannot differ in the selector | **`LRSWEEP` running** |
| 3 | **~0 on both, but moving** | 500 epochs too few | extend. The 2,000 bound is an implementation guard (`learner.py`), **not sealed** — changeable if the design needs it | trivial, no prep needed |
| 4 | **negative** | informed heads are *worse* than neutral | points at scale, not information: `C3REACH` measured the learned interaction head at `2,518-11,205` against an additive spread of `107-264` — one to two orders too large. Response is calibration of the head's output scale, not more training | diagnosis already in hand |
| 5 | **positive but under ~1%** | consistent with the panel's own ceilings and therefore **not a learning problem** | find an operating point where the ceiling is materially larger | **`BEAMSWEEP` dispatched** |

**Outcome 5 deserves emphasis.** `PANELCEIL` measured, on this exact 12-anchor panel:
coordination ceiling `+1.944795%`, **acceleration ceiling `+1.045609%`** (`13.291278 ->
13.430253` Mbit/J), traversal-order gap `+0.905261%`. **At this operating point no learned
method can be substantial on either axis, however good it is.** So a result of `+0.5%` would
not be a failure of learning; it would be a correct reading of a small ceiling.

## The per-route outcome space for `FULL - DROP_Ci`

| outcome | meaning | response |
|---|---|---|
| C1 carries everything, C2 and C3 ~0 | the three-route claim is really a one-route claim | either repair C2/C3's targets, or change the decomposition — two candidates already specified |
| C3 ~0 | consistent with `93.06%` of its training support being `\|A\| = 2` while the deployed catalogue contains size-100 rows; a head trained on pairs is extrapolating | enlarge the coalition support, or change what route 3 predicts |
| C2 ~0 | expected: declaration v1.9 §5 already states C2's set-level marginal is **zero by construction**, and its 22 inputs were **never repaired** | `Q2REPAIR` |

## Dispatched now, because they have the longest lead

**`BEAMSWEEP`** — rebuild physics at a wider beam and recompute both panel ceilings with
`PANELCEIL`'s construction. This is the largest measured lever on the thing that actually
binds: `+0.899%` at the sealed `1.66°` versus `+8.16%` at `3.32°`. **It needs new physics
(~1.5 h) and is therefore started before it is known to be needed.**

**`Q2REPAIR`** — repair the 22-slot `q2_state` the way Q1 was repaired. `C2REALV2` verified
that **none of the 22 slots changed** under the Q1 repair: `off_axis_angle` and
`focal_link_elevation` do not enter C2's inputs, slot 9 `missing_incumbent` is still constant
zero, and slot 6 still carries an indicator whose Q1 copy was dropped. **C2 has never been
tested on a repaired representation**, and its verdict cannot be read as final until it has.

## Held, with the trigger written down

- **The decomposition bake-off** — needed only if the routes are individually dead after the
  representation is repaired. Both candidates' targets derive from the same physics layer, so
  it costs no new physics. Trigger: both runs report and at least one route is ~0 on the
  repaired representation.
- **Extending past 500 epochs** — trigger: outcome 3.
- **Head output-scale calibration** — trigger: outcome 4.

## What no outcome licenses

None of these branches is chosen by whether it improves a contrast. Each is triggered by a
**diagnosis** — flat versus moving, representation-bound versus ceiling-bound, scale versus
information — and each diagnosis is stated here before any number exists. The 48 evaluation
dates remain untouched by every branch above.
