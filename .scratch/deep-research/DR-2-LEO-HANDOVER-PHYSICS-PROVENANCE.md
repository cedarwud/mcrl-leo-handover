# DR-2 — Survey: handover cost, operating points and payload power models in LEO / NTN

*Optional context: `00-EVIDENCE-LEDGER.md` describes one simulator. It is background only —
every factual claim in your report must come from standards or the literature.*

## Research question

Establish, from 3GPP specifications and the peer-reviewed LEO/NTN literature, what a beam
or satellite handover **costs**, what handover **rate** is realistic, and how satellite
**payload power** is normally modelled — so that a specific simulator's choices can be
checked against standard practice.

## Scope

Non-terrestrial networks with LEO constellations at roughly 500-700 km; beam and satellite
handover / beam management; satellite payload power and energy-efficiency modelling. Both
3GPP normative specifications and academic modelling papers.

**Source bar**: 3GPP TS/TR documents cited by number, clause and release; peer-reviewed
journal and conference papers; arXiv preprints with citations. For every numeric value give
the document and clause or the paper and table. Exclude vendor marketing and blog posts.

**Recency**: prioritise Release 17 and later for NTN, and 2019-present for the academic
literature, but include earlier foundational power models where they are still standard.

## Deliverable — a provenance table

One row per item below, with columns: **standard treatment in the literature** ·
**citation (spec clause / paper table)** · **numeric value or range** · **whether the
literature is consistent or divided**.

### A. Handover cost — enumerate every channel and its magnitude

Service interruption and measurement gaps; signalling and control-plane load (RACH, RRC
reconfiguration, core-network signalling); terminal re-acquisition and synchronisation
energy; payload beam-switching energy; radio link failure and ping-pong risk; higher-layer
effects (TCP stalls, HARQ/ARQ retransmission, user-perceived stalls).

For each, state **the units it is naturally measured in** — seconds of lost time, joules,
signalling messages, probability of failure — and whether the literature ever attributes it
to an **energy-efficiency** metric or keeps it as a separate QoS outcome or constraint.

Specific values to establish:
- The interruption times for conditional and non-conditional handover, DAPS, and RACH-less
  handover, including whether the standard treatment is a **fixed constant or a
  distribution** (3GPP TS 38.133 is the relevant spec; state the clause).
- Whether any source supports a **per-handover energy cost in joules** for a terminal or
  payload of this class, and of what magnitude.

### B. Realistic operating points

- Handovers per user per minute, or per satellite pass, for a Walker-type LEO constellation
  at ~550-600 km. Give the constellation assumptions with each figure.
- Satellite pass / visibility durations and beam dwell times for the same constellations.
- The **decision or reassignment interval** used in the beam-management literature — how
  often are assignments re-evaluated, and what interval do simulation studies use?
- Published limits on **signalling load** or handover frequency: what makes a handover rate
  operationally unacceptable, and is there a citable ceiling?

### C. Exogenous bases for a handover-rate constraint

What externally citable quantities could bound a handover rate: satellite dwell time and
pass duration; 3GPP signalling-capacity limits; mobility-robustness and ping-pong criteria
(TS 38.300, TS 38.331, TR 38.821); operator-reported handover budgets. For each, say
whether it yields a **derived** bound or only a **stipulated** one, and give the derivation
where it exists.

Separately: the standard definitions and thresholds for **service availability** in this
context — PHY decodability, BLER target, outage probability, session continuity — with the
citable values.

### D. Payload power models

- Is per-beam transmit power normally taken as a **maximum over served users**, a **sum**,
  or something else? What is the standard model?
- Standard values for fixed per-radiating-beam power, per-active-satellite baseband power,
  and PA supply versus radiated power (including where PA saturation is assumed to sit).
- Does the standard model make **beam occupancy** affect power — e.g. through required
  transmit power rising with per-user rate demand — or is power occupancy-independent?
  Report both conventions if both exist, and say which is more common and why.
- How is **co-channel interference between active beams** normally modelled? Is a
  load-independent, activation-gated term standard, and what does it omit?

### E. Energy-efficiency definitions in this field

How is EE defined in LEO/NTN papers — bits per joule, bits per hertz per joule, a ratio of
sums, or a mean of per-user ratios? **Is the ratio-of-sums versus mean-of-ratios
distinction stated explicitly in that literature, or left implicit?** Collect the
definitions actually used, with citations, and note the spread of reported magnitudes.

## Format

Provenance table by section, then a short list of items where the literature is genuinely
divided, then the reference list. Every number carries its source document and clause or
table.
