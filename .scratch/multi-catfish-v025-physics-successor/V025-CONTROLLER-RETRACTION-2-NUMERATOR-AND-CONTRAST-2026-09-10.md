# Retraction 2 — the numerator I "corrected" to, and the contrast I built the day on

**2026-09-10 11:05 UTC. Both items verified by the controller reading the sealed text and the
receipt directly, after an adversarial interrogation surfaced them. Neither was found by me.**

---

## Item 1 — the demand cap is a model change I was forbidden to make by relabelling

**Sealed, `V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.8-AMENDMENT-2026-09-09.md` item 5,
sealed 2026-09-09 02:05 UTC, before any successor outcome:**

> "The numerator is saturated (**full-buffer**) decodable throughput under a per-user
> rate-target power controller; the rate target is a **power-control setpoint, not a demand
> model**, and realised per-user rates may exceed it. … **Finite demand or queues would be a
> versioned model amendment with affected comparisons re-run, never a relabelling.**"

**All day I applied a per-user cap at `50 Mbit/s * 30.08 s` and called it "the reported
numerator" and "the field convention", and retracted capacity figures as "non-standard and
flattering".** The declared numerator is full-buffer capacity. The `50 Mbit/s` is a
**power-control setpoint**, not a demand. I performed exactly the relabelling the sealed text
forbids, and then used it to overturn figures computed under the declared model.

**This is the third time I have overturned a sealed declaration without reading it.** The
memory record `adversarial-review-before-overturning` states the first two, on 2026-09-09 and
2026-09-10, and prescribes: read the declaration and every amendment **first**, then search
whether I have attacked it before. I did neither.

### What this does and does not overturn

- The **literature finding stands**: the field credits `min(capacity, demand)`. That is a real
  finding about convention.
- **Acting on it is a versioned model amendment**, with affected comparisons re-run — not a
  reporting choice, and not something a controller adopts mid-session.
- Therefore **today's mixed usage is invalid in both directions**: capacity figures were
  wrongly retracted as inflated, and demand-capped figures were wrongly promoted as corrected.
- `CTRLCAP`'s `+82.78%` "demand-capped" `SEALED` figure is a **pure relabelling** — the same
  receipt records that the cap binds no `SEALED` user-anchor, so the capacity and
  demand-capped tables are identical there.

### The part that makes this worse than a bookkeeping error

The cap value **determines the sign of a route's marginal**. From the v0.23 four-point sweep
(`.scratch/multi-catfish-v023-c3-probe-results-20260908/ORACLE-MARGINALS-2026-09-08.md`):
C2's marginal is `-2.03%` at infinite demand, `-4.96%` at 200 Mbit/s, `+1.99%` at 50 Mbit/s,
`+9.92%` at 10 Mbit/s.

The owner's requirement is that each route is individually positive. **That sign is currently
a function of a constant nobody selected for that purpose, and v0.25 has never swept it.**
Choosing the cap after seeing which value makes routes positive is precisely what the
non-negotiables forbid. **The sweep must therefore be run and reported in full, across the
declared full-buffer case and a stated ladder, before any route sign is claimed.**

---

## Item 2 — the `-1.75%` contrast does not measure what I said it measures

I called `FULL - ALL_NEUTRAL_CONTROL = -0.01745324091886997` "the only measured contrast
between the learned routes and neutral-source training" in the consolidated position and in
the layer map. **I read the same receipt this morning and quoted `4.017143208622553` from it
without ever looking at the other seven contrasts in the same file.**

Read directly from `.scratch/c3-panel-smoke-r8/smoke.json`, both provisioning rules, all
`all_anchor.marginal_relative_pooled_ee`:

| contrast | value |
|---|---|
| `FULL-minus-BASELINE` | `4.017143208622553` |
| `FULL-minus-DROP_C1` | `0.00884473214140279` |
| `FULL-minus-ONLY_C2` | `0.00884473214140279` |
| `FULL-minus-DROP_C3` | `0.0` |
| `FULL-minus-ALL_NEUTRAL_CONTROL` | `-0.01745324091886997` |
| `FULL-minus-DROP_C2` | `-0.01745324091886997` |
| `FULL-minus-ONLY_C1` | `-0.01745324091886997` |
| `FULL-minus-ONLY_C3` | `-0.01745324091886997` |

**Eight contrasts, four distinct values.** The number I attributed to neutral-source
substitution is bit-identical to `FULL - ONLY_C1`, an arm in which **C1 is informed**. A
quantity that is invariant to the intervention it claims to measure is not a measurement of
that intervention; it is one of four discrete outcome levels wearing a label.

The same receipt records `anchor_count: 1`, `smoke_test_not_evidence: true`,
`production_training_run: false`, and `proposal_repaired: true` on **all eight** learned arms —
every arm's raw learned proposal was rejected by the served guard and replaced by the same
head-independent seed.

**The correct statement is: the contract §C3 contrast has never been measured. Not once.**

### The mechanism, and why it may be structural

Neutral source is implemented as **zeroing the target while leaving the feature rows
unchanged** (`PairwiseBatch.neutral`: `np.zeros_like(self.target_deltas)`;
`CoalitionBatch.neutral`: `target_psi=np.zeros_like(self.target_psi)`). A head that converges
to the zero function contributes about zero to every catalogue row's score — **which is what
removing the term does.** So neutral-source substitution and knockout may be the same
intervention in effect, and erratum 14 required them to be distinguishable.

**Nobody has asked whether they are distinguishable in principle.** That question is now open
and is prior to any panel.

---

## Standing consequence

Two of the three load-bearing statements in
`V025-CONTROLLER-CONSOLIDATED-2026-09-10-0950Z.md` are withdrawn: the numerator discipline
(item 1) and the routes-versus-neutral reading (item 2). The third — that C1's declared target
is weakly learnable on a defective schema, re-test running — stands.

Neither item was found by me. Both were found by an adversarial reader given my own records
and told that a record proves an assertion, not an event.
