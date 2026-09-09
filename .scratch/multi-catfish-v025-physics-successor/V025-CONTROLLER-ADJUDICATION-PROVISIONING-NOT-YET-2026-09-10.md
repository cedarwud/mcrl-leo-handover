# Controller adjudication — do not authorise the provisioning change, and I have rebuilt a case I was already corrected on once
Recorded 2026-09-10 from an adversarial adjudication at ultra effort, commissioned with an explicit instruction to argue against the change and told that the controller already favoured it. `DIAGNOSTIC_NOT_CLAIM`. Nothing was run and nothing sealed was modified.

**Verdict: do not authorise yet.**

## The part I have to own
The sealed declaration **v1.9 §1** states, in terms: *"The margin must not be re-solved into transmit power."* The change I spent the day building a case for reverses exactly that instruction.

On 2026-09-09 I declared that same margin rule wrong, an adversarial review ruled **KEEP_AND_DOCUMENT** and listed sixteen over-claims, and the recorded lesson was that I had attacked a strawman. **I rebuilt the same case against the same instruction, from a different direction, and did not notice.**

My load-bearing argument — that zero of 2,000 users attain the rate target, so the model never delivers what it promises — does not survive contact with the declarations:
- **v1.1** calls the 50 Mbit/s figure a *nominal, synthetic* operating point, expressly permits partial delivery, credits achieved full-buffer bits, and separates physical service from target attainment;
- **v1.7 §1** had already withdrawn the availability rationale and named the tenth percentile as a pre-specified **scoring** convention.

Zero attainment is therefore not a breached contract. **No such promise was ever made.** The convention I called an error is coherent: spend power for a nominal operating point, then choose a more robust mode under a conservative channel view — provided the target is a control setpoint rather than promised delivery, the demoted mode is actually transmitted, failed attempts still cost energy and interference, and neither guaranteed delivery nor network availability is claimed. Those conditions match the declarations and the implementation.

## The concrete blocker
The evidence I assembled **mixes two different numerical implementations**.

- **Simple division** divides the target by the quantile and stops. It leaves **1,179 uncapped occupancy-one no-mode attempts sitting 5.76 × 10⁻¹² to 2.616 × 10⁻⁹ dB below threshold** — numerically induced failures.
- **Strict clearance** adds a loop verifying both nominal and quantile-adjusted target-mode clearance.

| panel | simple | strict |
|---|---:|---:|
| twenty-anchor joint-over-unilateral | +0.544766 % | +0.512537 % |
| eight-anchor at the sealed width | **−0.302750 %** | **−0.176800 %** |

Committed assignments agree at only **18 of 24**. **The five-width curve has never been produced under the strict implementation**, so every corrected-physics beam-width number the project holds comes from the defective one. This also corrects my earlier explanation of that discrepancy: it was never an intermediate file, it was a different algorithm.

A job is running to produce the strict five-width curve with all three arms side by side.

## Other over-claims corrected
- **"Ninety per cent availability" is wrong.** Target-mode decoding requires the desired fade to clear `q × (N + I_realised)/(N + I_nominal)`, not `q`. An elevation-binned desired-link quantile does not deliver a percentile of coupled signal-to-interference-and-noise ratio, network availability, or endpoint delivery.
- **The corrected rule loses service at middling occupancy.** Decoded instances fall 24,351 → 22,046 at occupancy three, 30,800 → 24,561 at four, 9,029 → 7,619 at five. I reported the low-occupancy restoration and not this.
- **"Every user's power rises 1.107 to 4.830 dB" is inaccurate.** That range is the imposed target margin; the realised ratio also carries the interference term.
- **"2,000 users" is twenty populations of one hundred**, and the 12,000 sweep results reuse users, steps and arms across five widths. These are census denominators, not independent samples.
- The cap-onset occupancy is not universal, and the counterfactual restoration shares are not a unique additive causal decomposition.

## What survives
The veto is not absolute. **Versioning can legitimately change the policy** — but as an explicitly justified change of planning objective, acknowledging the earlier declaration, disclosing that every outcome was known before the decision, and with the rationale made **independent of the third component's sign**.

The conditions attached are extensive and I accept them in full: preserve the original primary, seals, receipts, figures and unfavourable findings as results of the nominal-power convention; **freeze the sealed beam width for the provisioning comparison** and give any antenna change its own separate decision, never promoting a favourable width to erase the original primary; specify and review the clearance algorithm at every scalar and dense site before regenerating anything; publish both rules, all widths, energy costs, user losses, caps, failures and negative signs including the simple-versus-strict distinction; and report the strict full-width comparison as **uncompleted until it exists**.

## The lesson, restated because once was not enough
A prior adversarial review already told me this. The failure mode is not that I lack the correction — it is that I did not check whether a new argument was the old argument wearing different evidence. **Before assembling any case against a sealed declaration, the first step is to read that declaration and every amendment to it, and to search the record for whether I have attacked it before.**
