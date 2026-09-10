# Erratum 16 — the panel I designed would have made C3 inert by construction

**2026-09-10. Verified by the controller against his own design record. No sealed artefact,
constant, threshold, sign, seed, horizon, price, guard or acceptance rule is changed.**

**`V025-CONTROLLER-DESIGN-C3-PANEL-SPINE-2026-09-10.md` line 10 specifies first-improvement
local search over single-user neighbours for every panel arm. The deployed pilot does not
work that way — it is a catalogue argmax. So the panel would have measured C3 as inert
regardless of how good the C3 head was, and the inertness would have been an artefact of my
own spine decision, not a property of the route.**

## The two objects, and which argument applies to which

| Object | Selection | Is C3 reachable? |
|---|---|---|
| Deployed pilot / learned arms | argmax over the whole legal catalogue, interaction added per row (`run_v025_pilot_c3.py:1542-1563`) | **Yes** |
| `ProfileSelector` `S3`/`S0` | `for profile in (base, *catalogue)`, `additive + interaction` (`deployment.py:647`) | **Yes** |
| `S_UNI` comparator | single-user loop, does not take the model | not applicable |
| **The C3 panel as I designed it** | **first-improvement over single-user neighbours (spine, line 10)** | **No** |

Erratum 15 established the first row and corrected the premise I had given both reviewers.
**It did not go far enough.** The premise was wrong about the pilot and *right about my own
panel*. fable's round-2 answer is what surfaced this: "Both theorems still bind for the claim
panel, because the controller's spine decision fixes the panel's search as first-improvement
over single-user neighbours."

## Consequence

A residual that is hard zero on singletons cannot fire strict improvement from an
additive-optimal seed. Under the spine as written, every learned arm would have committed the
seed, and `FULL` and `DROP_C3` would have agreed at every such anchor — **for a reason
entirely internal to the harness**. The panel would have produced a confident, well-receipted,
meaningless null for C3.

The spine's own justification for first-improvement was that it reaches a better fixed point
than best-improvement (+8.13% / +1.62% pooled), "better for every arm equally, so declaring it
is not outcome-selection." That reasoning is sound **for arms that differ only additively**.
It is not sound for an arm whose entire contribution is defined on multi-user sets, because
the move set never presents one. **I checked the choice for outcome-selection bias and did not
check it for route sterilisation.**

## The receipts are no longer unexplained

Erratum 15 said the zero-effect receipts had become "unexplained". fable supplies both
explanations, neither of which needs the argmax selector:

- **`DROP_C3` changed 0 proposed assignments** — the *proposal builder* never consults the
  interaction head at all.
- **r8 smoke byte-identity between `FULL` and `DROP_C3`** — the panel harness is first-
  improvement with a hard-zero singleton head and a shared seed hash across learned arms.

And, contradicting the inert reading: **under the argmax selector, zeroing the interaction
head changed 5 of 10 committed rows** in the selector diagnosis. C3 does reach the decision
there — but **destructively**, because the learned head is reported off by two orders of
magnitude at the grand row.

**Roughly 77% of the sealed catalogue is singleton rows**, which the residual can never
reorder. That is by design, not a defect, and it caps how often C3 can matter under argmax.

## Register

1. The panel spine's search order must be re-declared before any panel is built, and the
   declaration must state which routes the move set can and cannot express. This is a design
   defect in a controller record, not in a sealed artefact.
2. The `+8.13% / +1.62%` first-improvement finding stands on its own terms; only its use as
   the panel's move set is withdrawn pending re-declaration.
3. `C3REACH` continues. It independently measures the singleton share, the context coverage,
   and the argmax-change count with the learned term and with exact `Psi`. fable's figures
   above are a worker's report; C3REACH is the measurement.
