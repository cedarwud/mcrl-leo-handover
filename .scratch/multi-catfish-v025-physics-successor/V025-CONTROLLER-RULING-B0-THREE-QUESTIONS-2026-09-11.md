# Ruling — B0's three open questions, and a correction to my own "defect" finding

Date: 2026-09-11. Source: `.scratch/b0-corrected/B0-CORRECTED-BASELINE-2026-09-11.md`.

## 1. B1 / SDD §8 stands — for the baseline arm. D-1 becomes a flag.

**What B1 is** (`docs/PREREG-DRAFT.md:324`, `docs/PATCH-LEDGER.md:152`, `docs/G9-TEST-MAP.md:40`):
the TD target is **MODQN eq. (16) vanilla — each objective takes its own max**, frozen so that the
baseline is **unambiguously the published MODQN**.

**Correction to `V025-CONTROLLER-FINDING-PER-HEAD-BOOTSTRAP-2026-09-11.md`.** I called per-head
bootstrap a "verified defect". **It is not a reproduction bug; it is the published algorithm,
reproduced faithfully and frozen on purpose.** What DR-1 / ASK-1 established is that this published
design is **theoretically incoherent** for a scalarised deployment rule (independently-optimal heads
describe no single policy). That is a **finding about published MODQN**, and a useful one for the
thesis — not a licence to change the baseline.

And the owner's success gate is **beating baseline MODQN**. If the baseline is silently given a
better bootstrap, the gate stops meaning what the owner decided it means.

**Ruling:**
- **Baseline-MODQN arm**: eq. (16) per-head max, **B1 intact**, W-08 assertions restored.
- **Successor learner** (stage 1 single-head `Q_eta`, stage 2 three heads with shared continuation):
  **shared continuation action** — which is D-1 — as DR-1 requires.
- D-1 moves behind a **config flag, default = eq. (16)**, so B1 holds by default and the published
  contract is testable as-is. Commit `5219995a` currently makes D-1 unconditional on the shared
  branch; that is to be converted, not reverted.
- **No adversarial review is needed**, because B1 is not overturned: it keeps governing exactly the
  arm it was written for.
- **PENALTYARM's arms ran on `5219995a`**, i.e. with shared bootstrap. They are the shared-bootstrap
  variant and are labelled as such; they are not the eq. (16) baseline.

## 2. D-2's outage floor: use the per-step worst served value, not −100

`−100 = −num_users` is a loose bound; it made ~5-6% of steps carry ~80% of the r3 signal (inferred).
The minimal honest floor is the **worst value any served user actually receives in the same step**
(for r3, `−max_b U_b` at that step; for r2 the existing `−PHI2`). It removes the inversion
(service can never score worse than outage) without inventing a magnitude and without letting the
floor dominate the head. Applies to **every** arm — the free ride is a reproduction artefact
(`outage_gate.py` is marked "S, PROPOSED — Not yet frozen"), not part of the paper.

(The r3 head disappears in the successor design, `Q_B`/`Q_E`/`Q_H`; this matters for the
baseline-MODQN arm.)

## 3. Checkpoint selection: no selection — evaluate the final checkpoint

Selecting the "best" checkpoint on the uncalibrated scalar (numerically `0.5 * r1`) is inconsistent
with training; selecting on the declared endpoint would be selection on the outcome. **Declared:
every arm is evaluated at its final checkpoint**, training curves reported alongside. D-3's
calibrated logging stays; the selection path is simply not used for claims.

## 4. New standing rule found by B0: the two hosts give different numbers

The local harness reproduces the catfish-surface document's random arm exactly; **`sat` uses a
different TLE archive and gives a different random-arm number.** So **no figure from one host may be
compared with a figure from the other** — including FEASFRONT's local 93.11M / 112.46M against any
`sat` evaluation. Required before stage 1: **pin one TLE archive by content hash and make both hosts
use it**, with a placebo showing the random arm matches bit-for-bit on both.

## B0's pilot, recorded as smoke only

At episode 500 (ε = 0.753): B0 77,365,317 vs unfixed 79,567,896 bit/J (−2.8%, 1.3 se, n = 24,
unresolved); outage steps 12 vs 101 of 24,000. Unfixed-at-500 reproduces the frozen run's first 500
episodes exactly. **Not a result.** Headline curve confirmed to have been `0.5 * r1` within 5e-6.
