# Round 15: what does a satellite beam actually cost to keep switched on, and can it be switched off?

## The question
For a multi-beam Ka-band satellite payload, **how much power is consumed by a beam that is powered up but carrying no traffic, and can an operator actually switch that consumption off on the timescale of tens of seconds?**

I am modelling this and I want the hardware answer, not the answer that suits my model. I am deliberately not saying which way my result goes.

## What I need covered

1. **The fixed cost of an active chain.** For a transmit chain feeding one beam, what draws power independently of the traffic it carries? Please separate the amplifier's own quiescent or bias consumption, the up-converter and driver stages, the digital beamforming or channelizer share, and anything else. Give figures or ranges where public sources support them, and say where they do not.

2. **The variable part.** How does total chain consumption scale with radiated power for a travelling-wave tube amplifier and for a solid-state amplifier? I am currently modelling amplifier supply power as proportional to the square root of the radiated power, plus a constant per-chain term and a constant per-satellite term. Is that a recognised model, and if not, what is?

3. **Switching a beam off.** If a beam has no users, can its chain be powered down, and on what timescale? Distinguish: reducing drive to zero while the chain stays biased; putting the amplifier into standby; and fully powering down. What are the realistic transition times and what does each actually save? Are there thermal, reliability or reacquisition reasons operators avoid switching chains off frequently?

4. **Beam hopping as the comparison case.** In a beam-hopping payload, a beam is illuminated only part of the time by design. Does an unilluminated beam consume the fixed cost or not? This seems to be the closest deployed analogue to what I am modelling.

5. **The numbers I am using.** My model charges **0.338 W per active chain** and **0.200 W per active satellite**, against a per-beam radio-frequency cap of **1.65 W** and a saturated amplifier power of **5.2178 W**. Are those fixed terms plausible in relation to the radio-frequency output for a small Ka-band payload, or are they implausibly small or large? If the fixed terms are unrealistic in either direction, say so and give the range you would expect.

6. **The consequence I care about.** In my model, the per-chain cost is saved **only when every user leaves a beam**, so emptying a beam completely is worth something while partly emptying it is worth nothing. That discontinuity is doing real work in my results. Is that a faithful representation of how a real payload behaves, or is it an artefact of treating the chain cost as a step function? What would the honest continuous alternative look like?

## What I will do with the answer
If the fixed per-chain cost is realistic and genuinely switchable, one of my mechanisms stands. If it is not, that mechanism is a modelling artefact and I need to know before I publish it. Both answers are useful to me. Please distinguish established practice from vendor claims from your own inference, and say clearly when the honest answer depends on an architecture I have not specified.
