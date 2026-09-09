# Open decision for the owner — the beam half-power angle is read as a full span when the source defines a one-sided angle
Recorded 2026-09-09. The reading is **settled numerically**, not a matter of interpretation. What is open is whether to correct the geometry, and that is the owner's call because it changes the physical model the main run will measure.

## The proof, which was already on the machine
An audit dated **2026-08-26**, two weeks old, and a proposal `ADR-002` already establish this. Neither was acted on.

The source's pattern is `G(theta) = G0 [J1(mu)/(2mu) + 36 J3(mu)/mu^3]^2` with `mu(theta) = 2.07123 sin(theta)/sin(theta_3dB)`. At `theta = theta_3dB` the argument is exactly `2.07123`, and

```
A(2.07123)^2      = 0.5000004
10 log10 of that  = -3.0103 dB
```

That is the half-power point. So `theta_3dB` in the implemented equation is **the one-sided off-axis half-power angle**. An independent primary source confirms it: the expanded article defines `theta_3dB = atan(r/D)` with `r` a **radius**, which is centre-to-edge.

| quantity | value |
|---|---|
| one-sided half-power angle, from Table I | 0.058 rad = **3.3232 degrees** |
| symmetric full half-power beamwidth | 0.116 rad = **6.6463 degrees** |

The engine registers `3.32` as the **full** span and passes half of it down, putting the half-power point at **1.66 degrees**. Under the current pattern `F(3.32 degrees) = 0.0424`, which is not one half. **The modelled beam is half as wide as the source's.**

## Why this is not a "would it help" question
The owner asked whether enlarging the value would help. The answer is that the source determines the value and the direction is not ours to choose. Correcting it because a source says so is admissible; correcting it because the result improves is not, and the standing rules forbid it.

The network effect is also **not** known to be favourable. A wider beam raises the wanted link's off-axis gain, which helps, and equally raises every aggressor's gain at its victim, which hurts. Our results are dominated by interference: 91.1 per cent of infeasible user-steps are interference-limited, 98.9 per cent of interference arrives from an adjacent beam on the victim's own satellite, and a single aggressor carries 74.3 per cent of it. Doubling the width changes that structure directly and the sign of the net effect is unmeasured.

A provenance audit's sensitivity figure of +42.5 per cent energy efficiency at a 2-degree off-axis point is an **isolated single-user fixture**, not the network, and must not be quoted as the expected gain.

## What is running
A two-reading measurement on real anchors under both conventions, reporting pooled energy efficiency for the baseline, the unilateral optimum and the bounded oracle selector, the served counts, **the coordination headroom**, and the interference structure itself. It is explicitly forbidden from recommending a value on the basis of which result is better.

## The decision
Whether to adopt the source's convention. Three considerations, none of which I resolve here:

1. **Provenance says yes.** The code's comment asserts a convention the source does not support, and unlike the circuit constants this was never declared as a modelling choice. It is an attribution error, not a declared assumption.
2. **Cost.** Changing it invalidates every physics measurement taken today, including the witness, the prevalence census and the headroom ceiling, because all of them depend on the antenna pattern. They would need re-running, though not re-designing.
3. **`ADR-002` is a proposal, not an adopted decision.** The provenance audit is explicit that a proposal "is not authority to change the current geometry".

## What I recommend, and why it is only a recommendation
Adopt the source's convention **after** the two-reading measurement reports, so the change is made with its network consequence known rather than assumed, and record the reason as provenance with the consequence stated separately. If the correction happens to improve the headline, that must be written as a consequence and never as a justification.

## Standing
Nothing here changes any sealed value. No run is authorised. The geometry is unchanged pending the owner's decision.
