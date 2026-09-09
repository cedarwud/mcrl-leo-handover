# Controller adjudication — the margin rule stands. My objection attacked a different claim.
Recorded 2026-09-09, after an adversarial cross-model review that was commissioned to argue against me. Verdict: **KEEP_AND_DOCUMENT**. The sealed rule is not amended. This closes the question that was blocking the physics.

## 1. What I got wrong, precisely
The original v1.6 objection was **not** that a power margin cannot create a reserve. It was that under v1.6 as written, **scoring** recomputed power as `p_m = p_N/q` while **execution** still transmitted `p_N`. The review that produced v1.9 says so directly: "§1 can predict bits using increased power that execution never supplies."

So the defect was a **prediction-versus-execution mismatch**, and the reserve existed only inside the scoring calculation.

My rebuttal silently changed execution to `p_m`. That is a legitimate alternative controller, and its arithmetic is correct, but it answers a different question. I attacked a claim the declaration was not making.

## 2. What survives, and it is small
v1.9's compressed wording is genuinely imprecise as a standalone sentence. "More power and more interference" should be identified as the **hypothetical scoring quantities**, and "no reserve" as the **unchanged execution**. Read as a universal claim that physical power margins cannot work, the sentence is wrong; read in its documented origin, the objection is sound. That is a wording correction in a later erratum, not an amendment to the rule.

## 3. A practical obstacle to my proposal that I had not considered
Under the coupled solve, with `u_i = Γ_i N_i / h_ii` and `A_ij = Γ_i h_ji / h_ii`, the current controller iterates `p ← min(c, u + A·p)`. A wanted-link reserve gives `p ← min(c, Q⁻¹u + Q⁻¹A·p)`.

The capped map converges either way. But the **uncapped** reserve system needs `ρ(Q⁻¹A) < 1`, so with a common `q` the spectral condition tightens from `ρ(A) < 1` to `ρ(A) < q`. For a symmetric system the power multiplier is

`p_q / p_N = (1 − ρ) / (q − ρ)`

which exceeds `1/q` in general and **grows without bound as ρ approaches q**. In interference-limited cases my proposed amendment would demand unbounded power, not a modest `1/q` increase. Convergence of the capped map does not certify that the reserve is feasible.

## 4. Sixteen overstatements in my own adjudication, and the four that matter most
The review listed sixteen. Recording the ones that change a fact rather than a hedge:

* **The occupancy-2 rate.** I wrote that a backed-off user at occupancy 2 delivers 34.04 Mbit/s against a 50 Mbit/s target. Under the **actual** quantile, occupancy 2 selects `NO_MODE` and delivers **zero**. The 34.04 figure is a hypothetical successfully-decoded rate. I quoted a hypothetical as a measurement.
* **Scintillation is not double-counted.** I said nothing ruled it out. The source rules it in: `provider_legacy.py` explicitly removes scintillation from the nominal gain, and the complete fading product supplies it once. **Closed.** The figure's own normalisation remains a separate, smaller check.
* **The mode-selection bug does not exist.** Both the scalar and the batch selection paths maximise efficiency. I had already verified the scalar path; the batch path is confirmed too. **Closed.**
* **My claim that amending would shrink C3's headroom is a hypothesis, not a consequence.** A constructed cap externality disproves monotonic rescue, and raising power does not by itself reduce occupancy contention. I stated a direction I had not established, in a document whose whole point was that the decision must not be made on what helps C3.

Also corrected: "zero-payload transmission at full power" should read **computed** power, not the cap; and my claim that the availability and no-mode figures were mutually inconsistent establishes only that they use **different denominators**, which is weaker and is what I should have written.

## 5. Consequence for the schedule
The physics does **not** change. No engine change, no recalibration, no re-derived figure, no probe restart. The gate that could have cost most of a day is closed by a review instead of by a rerun.

What is required is a **documentation** obligation: the paper must name the composition as a declared conservative policy with its consequence stated, that a user whose target mode is already the floor is not served at the nominal reference condition. It must not present that as a Ka-band link-budget result.

## 6. What this says about my own process
I called a sealed rule wrong on the strength of one outside opinion that I had primed by stating my position first. The adversarial review, commissioned to attack me, found the error in under an hour. The lesson is the cheap one: when I am about to overturn a sealed decision, the first step is an adversarial review, not a confirming one.

## 7. Standing
No threshold, sign, seed, horizon, price, service guard, acceptance rule or claim condition changes. No run is authorised. The sealed declaration is unchanged; only a wording erratum is owed.
