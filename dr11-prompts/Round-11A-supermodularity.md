# Round 11A (deep research): is our objective structurally incapable of positive interaction?

## What I need
A literature-grounded answer to one question: **for a multi-beam satellite downlink with per-user rate targets, equal-airtime time-division multiplexing, adaptive coding and modulation with hard decode thresholds, and a network objective of bits minus a price times joules, is the objective submodular, supermodular, or neither, as a function of the user-to-beam assignment?**

If it is submodular, the interaction term we have been chasing for weeks is non-positive by construction and no amount of search or learning will find it. That would settle the question without further computation. If the hard decode threshold breaks submodularity, we need to know under what conditions, because that tells us where to look.

Please also tell me whether this question has a standard name in the literature that I should have been using, and whether the answer is known for the special cases below.

## The exact setting

**Assignment.** Each of about 100 users is assigned to one satellite beam. An assignment is a mapping `a: users -> beams`. Let `n_b(a)` be the occupancy of beam `b`.

**Airtime.** Users sharing a beam share its time equally. A user on a beam with `n` occupants transmits during a `1/n` fraction of the interval.

**Rate target.** Every served user must deliver an average of `r* = 50` Mbit/s. Because it only transmits `1/n` of the time, during its slot it must carry `r*·n`. With beam bandwidth `W`, the required spectral efficiency is `r*·n / W`, so **occupancy determines the required modulation and coding mode**.

**Transmit power.** Power is solved so the nominal signal-to-interference-plus-noise ratio lands exactly on the required mode's threshold, capped at 1.65 W:
`p = min(p_cap, Gamma(n) · (N0·W + I) / h)` where `h` is the channel gain and `I` the interference from other beams.

**Decode rule, and this is the part I think matters.** The transmitted mode is chosen from a **margin-adjusted** prediction, `SINR_pred = q · h · p / (N0·W + I)` with `q` the 10th percentile of the fading distribution, so `q < 1`. Bits are credited **only** if the realised signal clears the transmitted mode's threshold, and are credited at that mode's spectral efficiency. Otherwise the user delivers **zero bits while still consuming its full transmit power** and still contributing interference.

**Energy.** Per beam and interval: a power amplifier term proportional to `sqrt(p · p_sat)`, a fixed circuit term per active chain, and a fixed baseband term per active satellite.

**Objective.** `F(a) = B(a) - eta · E(a) - Phi(a)`, where `B` is total credited bits, `E` total joules, `eta` a fixed price, and `Phi` a handover and signalling penalty.

**The quantity in question.** For a coalition `A` of users moving together from an anchor assignment `a0` to `a_A`:
```
d_i  = F(a_i, a0_-i) - F(a0)          for each user i in A, moving alone
Psi_A = F(a_A) - F(a0) - sum_i d_i
```
`Psi_A > 0` means the moves are super-additive. We anchor at an iterated unilateral optimum, where every `d_i <= 0` by construction, so any strictly improving joint move must have `Psi_A > 0`.

## The specific sub-questions

1. **The general structure.** Assignment problems with shared-resource congestion are usually submodular in the sense of diminishing returns, which would force `Psi <= 0`. Is that the right frame here? Is there a standard result for interference-coupled assignment with an energy price?

2. **The threshold nonlinearity.** Our decode rule is a step function: a user contributes its full spectral efficiency or exactly zero. Does a hard threshold of this kind break submodularity, and is that documented? Intuitively two users moving together can push a third across its threshold when neither alone can, which sounds like complementarity.

3. **The occupancy inversion, which surprised me.** Because occupancy sets the required mode, **raising** a beam's occupancy raises its target mode, which raises the transmit power, which can lift users above their decode threshold. So adding load to a beam can make its existing users decodable when they were not. Is this a recognised effect, and does it create the complementarity that submodularity would otherwise forbid? Note the consequence we measured: a user alone on a beam is targeted at the lowest mode, has nothing to back off to once the margin is applied, and is therefore never served.

4. **Where the interaction lives, if it exists.** If the objective is neither sub- nor supermodular, what is known about where complementarities concentrate in such problems, and what search strategy finds them? We currently enumerate a bounded neighbourhood around a unilateral optimum and may be looking in the wrong place.

5. **Is the decomposition itself standard?** `F(a_A) - F(a0) - sum_i d_i` is a second-order mixed difference. Is there a better-established decomposition for this purpose, and does the literature warn about anything in this one?

## What I will do with the answer
If the answer is "submodular, so `Psi <= 0` identically", we stop searching and report a structural negative result with a proof rather than an empirical null. If the answer is "the threshold breaks it under conditions X", we build the test case for exactly X. Either way this changes what we compute next, so please be direct about which it is, and say clearly if the honest answer is that it depends on parameters we would have to check ourselves.
