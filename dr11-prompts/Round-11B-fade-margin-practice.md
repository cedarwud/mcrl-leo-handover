# Round 11B (Q&A, engineering practice): is our fade-margin rule a real design or a modelling artefact?

## The one question
In a Ka-band satellite downlink using adaptive coding and modulation, when the system must reserve margin against fading, **is margin normally taken by transmitting more power, or by demoting the modulation and coding mode, or both?** And is the specific combination below a recognised design, or an artefact that a practising link engineer would reject on sight?

## Our combination, stated precisely
1. A per-user rate target sets a required mode from beam occupancy.
2. Transmit power is solved so the **nominal** signal-to-interference-plus-noise ratio lands **exactly** on that mode's threshold, capped at 1.65 W.
3. Margin is then applied **only to the mode decision**, not to the power: the transmitted mode is the highest whose threshold is cleared by `q · SINR_nominal`, where `q` is the 10th percentile of the fading product.
4. Bits are credited only if the realised signal clears the transmitted mode's threshold. A user with no valid mode transmits at full power, delivers zero bits, and still causes interference.

Our own rule explicitly forbids re-solving the margin into power. The stated reason was that setting `p = p_nominal / q` makes the link target exactly the threshold again, so "the margin buys no reserve, only more power and more interference".

**I think that reasoning may be wrong and I want it checked.** If power is raised to `p_nominal / q`, the realised signal is `G · h · p_nominal / (q · N)`, which exceeds the threshold whenever the realised fading `G` exceeds `q`, that is with 90 percent probability by construction. That looks like a genuine reserve to me, and it is what I understood a link budget margin to be.

## The consequence we measured, which is why this matters
Because power is aimed exactly at the threshold, applying any `q < 1` **always** demotes the mode. A user whose target mode is already the lowest in the table has nothing to demote to and is therefore never served.

In our simulation, at a mean beam occupancy of 2.44 users:

| quantity | value |
|---|---:|
| transmissions with no valid mode | about 62 % |
| user-steps that cannot reach the 50 Mbit/s target at full power | 40.8 % |
| link availability | 0.453 |

A lone user on a beam is never served, and adding a second user to that beam makes both of them servable, because the higher occupancy raises the target mode and creates room to demote. That is the opposite of what load balancing would suggest and it is why I doubt the rule.

## Sub-questions
1. What is standard practice in DVB-S2 and DVB-S2X adaptive systems for fade margin: power control, mode back-off, or a defined split? Please cite the practice, not just the standard's tables.
2. Is "aim power exactly at the target mode threshold, then demote the mode by a fade quantile" something a real system does? If not, what is the closest real design?
3. Is our reasoning against `p = p_nominal / q` correct or mistaken? Please answer this one directly.
4. Is a 62 percent no-mode rate and 0.453 availability plausible for a Ka-band LEO downlink at 10 degrees elevation, 2000 km slant range, 1.65 W per beam, 166.7 MHz beam bandwidth, 35 dBi receive gain, or does it indicate a modelling error?
5. Separately: our mechanism figure uses an 11-entry **QPSK-only** table while our specification calls for the full 28-mode set including 8PSK, 16APSK and 32APSK. At the link budget above, the carrier-to-noise ratio at the power cap is about 19.2 dB at boresight and 9.9 dB at the half-power edge. Should higher-order modes be reachable at those values, making the QPSK-only restriction an error?

## What I will do with the answer
If the rule is wrong, we amend it before the main run and re-derive the figure. If it is defensible, we state it in the paper as a deliberate conservative choice with its named consequence, rather than presenting the low availability as a link-budget result.
