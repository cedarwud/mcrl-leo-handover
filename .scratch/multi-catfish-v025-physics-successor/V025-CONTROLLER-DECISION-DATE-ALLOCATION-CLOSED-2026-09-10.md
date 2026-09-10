# Decision — date allocation, closed

**2026-09-10 12:00 UTC. Adopted from the delegated adjudication
`DATE-ALLOCATION-DECISION-2026-09-10.md` (`/home/sat/mcrl-v025-dates-ws/`), which the owner
delegated with authority to conclude. No sealed file, margin, arm, physics, checkpoint or
acceptance rule is altered.**

## The allocation

**166 TRAIN dates → 116 source/development · 48 evaluation-only claim · 2 quarantined claim
reservations.**

The archive suffices for this allocation and for conditional date-only sizing. It **does not**
establish adequate power for the learned claim, and it does **not** supply the ~160 fresh claim
dates the contract's §D1 assumed. This decision prospectively replaces that §D1 allocation and
resolves the ambiguous phrase "training on the claim panel".

**This item was open from 2026-09-09 and was not re-raised by the controller for over a day.
It required no owner input; the delegation to adjudicate already existed.**

## The defect it found, which I had been quoting as a guarantee

I repeatedly cited `DATE-VARIANCE:22` — the guard "never compares evaluation dates with
training-source dates" — as though disjointness were enforced. **It is not.**

The adjudication opened the code: the guard rejects a `CLAIM_PANEL` date accompanied by any
**other supplied role**, but the mandatory development roles are `PROBE`, `CALIBRATION`,
`REHEARSAL`, `KAT`, `SYNTHETIC_REAL` and `SMOKE`. **Training-source identities are not among
them, and manifest construction never reconciles against the source corpus.** So "never
compares" means *no compulsory comparison against actual training provenance*, and the emitted
freshness flag is **not proof of source exclusion**.

**Owed repair, added to the register:** enforce claim-panel/training-source disjointness by
reconciling the claim manifest against the source corpus's actual date provenance, not against
a role list. Until that exists, any disjointness statement in a receipt is aspirational and
must be labelled as such.

## What this unblocks and what it does not

- **Unblocks:** world generation, which the 2026-09-09 record named as the longest-lead item
  and which was blocked on precisely this decision.
- **Does not unblock:** the first training run. That is blocked on the exact corpus
  (`EXACTGEN2`, in progress) and on a parameterised training runner, which **does not exist** —
  `run_c3_panel_smoke.py` is hard-coded to two source epochs (`:612`, `:721`) with `--output`
  as its only argument and no corpus input. `TRAINRUNNER` was dispatched at 11:56 UTC to build
  one, with the arm-difference fixture wired in as a start-time gate.
- **Does not settle power.** The contract's analytic power paragraph was withdrawn and replaced
  by a calibration table in the v1.1 amendment; the date SD it assumed (5%) is contradicted by
  the nearest measured analogue (`0.751%`, 30 dates, `CEILING30-MARGIN:34`); and a separate
  adjudication found the acceptance calibration's injected effect and its checked target differ
  (`g = 0.02` injected against a population `θ ≈ 0.01867`). **Power remains UNDETERMINED and no
  panel is sized on it.**
