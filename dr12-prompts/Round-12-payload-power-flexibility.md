# Round 12 (deep research): what can a real multi-beam satellite payload actually do about per-beam transmit power?

## The question
For a multi-beam Ka-band satellite downlink, **how much freedom does the payload have to change the transmit power of one individual beam, on the timescale of tens of seconds, without reducing another beam's power?**

Please answer for the architectures that actually fly, and say which is most common in current LEO broadband constellations.

## Why I am asking neutrally
I am modelling a system and I need to know which of two assumptions is the realistic one. I am deliberately not telling you which I currently use or which I would prefer, because I want the answer the hardware gives, not the answer that suits my model.

## What I need covered

1. **The amplifier.** For a travelling-wave tube amplifier and for a solid-state amplifier, what sets the per-beam output power in operation? Is the operating point effectively fixed at commissioning, adjustable by ground command on a slow timescale, or continuously controllable per beam? What are the realistic adjustment ranges and timescales?

2. **The power budget.** Is total radio-frequency power a shared pool across beams, so that raising one beam necessarily lowers others, or does each beam have an independent allocation with its own headroom? Cover both the classical transponder architecture and the multiport-amplifier or beam-hopping architectures.

3. **Flexible payloads.** For payloads described as flexible or software-defined, what is actually reconfigurable, on what timescale, and at what granularity? Distinguish what the literature demonstrates from what vendors advertise.

4. **Beam hopping.** In a beam-hopping payload, is the per-beam power fixed while the *time* allocation varies? If so, what does "increasing a beam's power" even mean there, and what is the right way to model fade margin in that architecture?

5. **The modelling convention.** In the academic literature on multibeam satellite resource allocation, which assumption is standard: fixed per-beam power with adaptive coding and modulation only, a shared power pool with per-beam allocation as a decision variable, or joint power and rate optimisation? Please give the split rather than a single answer, and say which venues and years favour which.

6. **Fade margin under a fixed-power constraint.** If per-beam power genuinely cannot be raised, how do real systems reserve margin against fading? What happens to a user whose link cannot close at the fixed power? Specifically, is there a recognised behaviour where a terminal is simply not served during a fade, and is that considered normal operation or a design failure?

7. **The consequence I care about most.** Suppose a system sets each beam's power to exactly what is needed for a target modulation and coding mode under nominal conditions, then requires additional margin for fading. If power cannot be raised, the only way to obtain that margin is to use a more robust mode, and a user already on the most robust mode has no move left. **Is a system that leaves such users unserved a recognised operating regime, a known pathology with a name, or an artefact that no real design would exhibit?**

## What I will do with the answer
It decides whether one rule in my model is a reasonable abstraction of real hardware or a modelling error I should remove. Both outcomes are useful to me. Please be explicit about which parts are established practice, which are active research, and which you are inferring.

Please cite primary sources, standards, or vendor documentation where possible, and say clearly when the honest answer is that it depends on an architecture choice I have not specified.
