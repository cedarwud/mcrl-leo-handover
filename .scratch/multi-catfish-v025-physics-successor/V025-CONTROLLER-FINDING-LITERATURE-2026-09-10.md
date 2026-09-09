# Controller finding — the mechanism is novel against the field, and its headline may be a table-edge artefact
Recorded 2026-09-10, from a review of seven energy-efficiency papers in the project's own reading set. `DIAGNOSTIC_NOT_CLAIM`.

## Novelty: yes, but narrower than it looked
No paper in the set contains the occupancy to mode to power to servability chain, and **not one reports that consolidation beats spreading**. All five that take a position argue for spreading, and every one gives the same single reason: inter-beam co-channel interference under frequency reuse.

But the **upper half of the chain is already published, twice**. The nearest prior work shares our Ka-band multi-LEO multi-beam setting, our equal-share intra-beam rule, our per-user rate floor, our per-beam power cap and our pooled efficiency objective, and never draws the inference: its occupancy symbol appears three times in the whole paper and never enters the power-control section. With continuous Shannon rate its occupancy term is purely a **cost**.

Two algebraic notes that constrain how we may claim this. Equal-bandwidth division and equal-airtime multiplexing give the **same** map from occupancy to required spectral efficiency, so the sharing model is not ours to claim. And **no paper in the set uses a discrete mode table at all**; every one uses continuous Shannon. So what is new is precisely: replacing continuous rate with a discrete mode ladder **inverts the sign** of the occupancy term.

The complete-evacuation discontinuity is **not** new. It is the terrestrial sleep-mode and cell-DTX model, and a satellite beam-shut-off paper already exists. It must be cited, not presented as a finding.

## The load-bearing objection
At occupancy 1 the required spectral efficiency is the **lowest** it ever is, selecting the most robust mode with the **lowest** threshold. At a given transmit power that is the situation with the **largest** margin. Our model calls it unservable, which inverts the physics.

The cap cannot explain it: if the cap bound at occupancy 1 it would bind harder at occupancy 3, whose target threshold is higher. So "1 fails, 3 succeeds" can only come from the selection running off the **bottom of the mode table**.

My own reading of the code agrees on the mechanics and adds what I think is the deeper cause. Power is provisioned so the nominal signal-to-noise ratio lands **exactly** on the target threshold, so the nominal margin is zero at **every** occupancy by construction. The asymmetry is only that at higher occupancy there are lower modes to fall back to. That reframes the finding from "low occupancy is physically bad" to "**we provision no margin and only high occupancy has somewhere to fall**". A check is running to settle it and to re-measure the +6.359 % under a formulation that provisions for threshold plus margin instead.

If the effect does not survive, two strategic reviews will have recommended building a paper on a truncation artefact, and what remains is the evacuation discontinuity, which is prior art.

## Three further problems the field's conventions expose
**The realised margin is whatever the table spacing happens to be.** Because power lands on mode M's threshold and mode M−1 is transmitted, the margin equals the gap between adjacent thresholds, typically 0.5 to 1.5 dB against Ka-band rain margins of several dB. Margin is not a parameter we set; it varies rung to rung. And a demoted mode delivers less than the required spectral efficiency, so **the rate target is missed on every served beam**.

**"Full power, zero credited bits, still attached" has no precedent in the set.** The field offers exactly two treatments of a user that cannot meet its target: outage, removed from numerator and denominator, or admission control, never admitted. We do neither. That is defensible as a deliberate choice but must be declared as one, or it reads as omitted admission control.

**The pooled metric plus an always-on per-chain cost generates a consolidation incentive by itself**, with no mode physics involved. One paper produces the same shape with no rate floor and no discrete modes. Our defence is the hard per-user target, but that only holds if unserved users are penalised somewhere. The recommended test is to report the summed per-entity efficiency alongside the pooled one: **if the effect survives that, it is mechanism; if it vanishes, it was the metric.**

## Conventions worth adopting
Pooled bits per joule is the modal choice in the field and is described as having the strongest physical interpretation, so our estimand is conventional. But both papers offering the choice warn about exactly our failure mode, which a referee will use as ready-made vocabulary.

Comparators are three to seven cheap interpretable heuristics plus one prior learned method plus internal ablations. **Nobody compares against an oracle.** Two conventions to copy: strengthen the baseline along the dimension not being claimed, and present an upper bound re-scored under real conditions. And the field will expect the **anti-thesis run, not argued**: a load-balancing policy under our own physics.

## Positioning, if the mechanism survives
Prior work had equal-share allocation, a rate floor, a power cap and a pooled objective, and with continuous rate the occupancy term is a cost. We show that a discrete mode ladder inverts its sign, and that the resulting policy is consolidation rather than the interference-driven spreading the beam-hopping literature uniformly assumes. Load balancing is not refuted: it is optimal for the blocking objective it was designed for.

## Standing
No sealed value changes. No run is authorised. The variant formulation under test is evaluated on a copy and the declared physics is unchanged.
