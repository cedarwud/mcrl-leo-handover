# Retraction — the numbers reported between 07:00 and 09:00 UTC, and why they fall

**2026-09-10 09:30 UTC. Triggered by `SWEEP-fable-2026-09-10.md`, commissioned by the owner
precisely to catch this. No sealed artefact is modified. Nothing here is tuned; this record
only withdraws readings.**

## What was withdrawn, and the specific reason

| number | as I reported it | why it falls |
|---|---|---|
| `FULLSPAN` `+17.03%` / `+10.80%` | "the whole-system span against the owner's bar" | **Reference is vacuous** and **the selector is clairvoyant** (below) |
| `FACTORIAL` `C1 +10.80% / C2 +0.45% / C3 -0.06%`, "4 of 6 pass" | "the three single-route marginals" | **They are not the contract's three routes** |
| `RESIDTOGGLE` `+5.62%` against the 10%/5% screens | "the ceiling on any C3 head in the deployed selector" | Same construction as `FULLSPAN`: clairvoyant residual on a catalogue no arm deploys |
| `9.8698%` multi-start | "assignment headroom that survives the numerator" | **Order statistic**, and it imports the defective provisioning rule |
| `+78.02%` causal mode selection | "the second pillar of headroom" | Measured on the **carrier assignment** (`3.89` Mbit/J base); does not transfer to the `43` Mbit/J fixed point |
| `+119% / +134%` control law | quoted as headroom | Non-causal, best-known not a bound, and shaped like the `+113.4% -> +0.273%` deflation |

## The four mechanisms, each checkable

**1. The reference is vacuous.** In the r8 panel smoke, `FULL - BASELINE` is `+401.7%` while
`FULL - ALL_NEUTRAL_CONTROL` is `-1.75%`. `repair_reference` hands **every** arm the same
exact-surplus whole-profile seed, so a system with all heads neutral-trained satisfies
"`FULL - BASELINE` substantial". **The bar as restated measures nothing about the routes.**

I had the number `4.017143208622553` in my own `MARGIN_Q` record this morning, read it as a
contrast magnitude, and never registered that it is `+401.7%`.

**2. The selector is clairvoyant.** `run_oracle_residual_toggle.py:379-384` scores every
candidate by its **realised** 48-boundary outcome. My own
`V025-CONTROLLER-PREDECLARATION-RESIDUAL-READING-2026-09-10.md` excludes "any oracle-only
gain, including one that uses the realised fading draw". I wrote that exclusion and then
reported against it.

**3. `FACTORIAL` measures a different decomposition.** `run_oracle_factorial.py:735`: its C1
is atomic **association** deltas, its C2 atomic **adjacent-mode/control** deltas, its C3 the
residual. The contract's C2 is `c2_persistence_forecast` over three future offsets
(`targets.py:251`). **The factorial's C2 has no counterpart in the contract, and the
contract's C2 has no term in the factorial.** Declaration v1.9 §5 already states the
set-level C2 oracle marginal is zero by construction.

**4. The three exact identities are structural, not a defect — and not what I guessed.**
Every eligible row is association-only or control-only, so each arm's argmax is the maximum
over **two disjoint row families**, not a sum of contributions. `DROP_C3 = C1_ONLY`,
`DROP_C1 = C3_ONLY`, `FULL = DROP_C2` follow by construction. The "route interaction" table
is arithmetic over mutually exclusive families and **cannot be read as synergy**.

`C2WIRING` independently confirms the runner itself is sound: a source-shaped fixture put
through the real `compact_anchor`/`choose_for_anchor` has `DROP_C2` select the association
row and `FULL` select the control row — **PASS, the wiring is live**. C2 is exactly zero on
`96.3736%` of eligible rows and must be scaled by `k = 17.2467` before any of the eight
choices changes. **So the instrument works; it is pointed at a different object than the
contract's three routes.**

## What still stands

- Reseeded span `+1.29%` (20 anchors) and `+0.899%` (8 anchors, strict, correctly paired).
- Occupancy floor `-7.66x`; ladder floor `+6.36% -> +0.51%`. Clean negatives.
- `128/128` endpoints not 2-swap optimal, **scoped to one-boundary `F`**.
- The corpus finding: all 176,223 shipped rows carry surrogate labels.
- The checkpoint-format limits, round-trip verified; resume bit-exact.
- **The 30-date interval `[+0.436%, +0.997%]` is old-pairing and must never be cited as the
  corrected span's interval.**

## The consequence for the goal

`SWEEP` answers the owner's Q3 directly: the substantial EE sits in the per-user
best-response step (`~+400%` from the carrier, head-independent) and in the control law —
**neither of which is a learned route**. C3's physics-supported territory is about one per
cent. C2 has **no EE measurement of any kind**, and the contract already predicts a zero
selection marginal for it.

**What cannot be claimed today: that any route raises EE relative to neutral-source training.
That contrast has never been run.** Not once, all day, in any receipt.

## Standing corrections to my own process

1. **G1 is void as written.** It must name the estimand and the reference before any reading.
2. **The bar must be restated** relative to `ALL_NEUTRAL_CONTROL` or the head-independent
   exact proposal, not the carrier incumbent — as my own `ARM-SET` record already required.
3. **A pre-declared exclusion is not self-enforcing.** I wrote the clairvoyance exclusion and
   then reported six numbers that violate it. Every future reading states, in the same
   sentence as the number, which reference and which information class produced it.

`SWEEPA` (astra) has not reported and has not seen this.
