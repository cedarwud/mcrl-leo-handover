# DR-2 — Is this simulator's handover and payload physics defensible, and what operating point is realistic?

*Paste `00-EVIDENCE-LEDGER.md` above this.*

A reviewer will ask whether the physics is right before asking whether the algorithm is.
Two of its premises have already been shown false **inside the model**, and one operating
point has been called absurd without anyone checking the literature.

## 1. Does a handover cost anything, and where?

The simulator charges a handover **zero joules** and, through a power-segment reset,
handovers slightly **save** energy. A sibling engine charges it as **lost useful time**
(0.062 s / 0.142 s, matching 3GPP TS 38.133 Annex A.14.2), which against a 30.08 s
decision interval is 0.21% / 0.47% of a step's bits.

- In the published **LEO / NTN** literature, what does a handover actually cost, and in
  what units? Enumerate every channel with a citation and a magnitude: **service
  interruption / measurement gap**, **signalling and control-plane load** (RACH,
  RRC reconfiguration, AMF/core signalling), **re-acquisition and synchronisation energy
  at the terminal**, **beam-switching energy at the payload**, **RLF and ping-pong risk**,
  **higher-layer effects** (TCP stalls, HARQ/ARQ retransmission, user-perceived stall).
- Is a **fixed** interruption constant the standard treatment, or is interruption
  **distributed** (conditional vs non-conditional handover, DAPS, RACH-less, TTT)? Give
  the distribution or range, not just the point value.
- **Which of these costs are legitimately attributable to an energy-efficiency metric at
  all**, and which belong in a constraint or a separate QoS outcome? This is the crux: if
  handover cost is genuinely not an energy cost, then penalising it inside an EE reward is
  a modelling error, and the literature should say where it belongs instead.
- Is the sibling's alternative treatment — `hoEnergyJoules` on a sensitivity grid of
  {3, 30, 100, 130, 150, 200} J — sourced to anything, or is a per-handover joule cost of
  that magnitude unsupportable for a terminal/payload of this class?

## 2. Is a 30.08 s decision interval, with these handover rates, a realistic operating point?

- For a LEO constellation (~550-600 km, Walker-type), what is the **realistic rate of beam
  and satellite handovers per user**, in handovers per minute or per pass? Give published
  figures with the constellation assumptions.
- The learner sits at **0.2796 handovers per user-step** at `dt` = 30.08 s (~0.56 per
  minute); the greedy EE rule sits at **0.7117** (~1.42 per minute). One reviewer called
  70% churn per 30 s operationally absurd (RACH flooding, core signalling, control-plane
  collapse). **Is that right, and is 28% also outside the realistic envelope?** Quantify
  against published signalling-load and mobility-robustness work.
- Is a **30 s** decision interval itself defensible for beam assignment in LEO, given
  satellite pass durations of roughly 300-600 s and much faster beam dynamics? What
  interval does the literature use, and what does choosing 30 s cost in realism?

## 3. Where should an operational handover constraint come from?

The project may adopt "maximise pooled EE **subject to** a handover-rate cap and a
service-availability floor". **The cap must be exogenous — derived from standards or
operational limits, never fitted to any evaluated policy's observed rate.**

- What **external, citable** basis exists for a handover-rate ceiling? Candidates to check:
  satellite dwell time and pass duration; 3GPP signalling-capacity limits; ping-pong and
  mobility-robustness criteria (TS 38.300, TS 38.331, TR 38.821); operator-reported
  handover budgets.
- One reviewer derived `H_max <= 0.40 per user-step` as `1/15` (one inter-satellite
  handover per ~450 s pass) plus `1/3` (a stipulated intra-satellite beam-switch budget).
  **The first term is a derivation; the second is a stipulation.** Is there a citable basis
  for an intra-satellite beam-switch budget, or must that term be declared as an
  assumption with a sensitivity sweep?
- What is the standard **service-availability** floor and how is it defined (PHY
  decodability, BLER target, outage probability, session continuity)? Give the citable
  thresholds.

## 4. Are the payload power constants and their structure standard?

- Per-beam power taken as a **`max` over served users** rather than a sum; 0.338 W fixed
  per radiating beam; 0.200 W per active satellite; PA supply dominating at ~94.8%; PA
  saturation unreachable in the operating range. **Is this a standard payload power model,
  a simplification, or wrong?** Cite the models the LEO/NTN literature actually uses.
- Does the standard model make **occupancy** affect power (through required transmit power
  rising with per-user rate demand), or not? The project has one engine where it does not
  and a sealed successor where it does (required SINR ∝ `2^(r*n_b/B)`). **Which is
  standard, and what does the choice change about whether load balancing helps EE?**
- How is **co-channel interference between active beams** normally modelled — is a
  z-gated, load-unweighted term standard, and what does that omit?

## Output

A provenance table: **claim → standard treatment in the literature → citation → how this
simulator differs → does the difference change the sign or only the magnitude of any
conclusion.** Flag every place where this simulator's choice would draw a referee
objection, ranked by how damaging it is. Where the literature genuinely disagrees with
itself, say so rather than picking.
