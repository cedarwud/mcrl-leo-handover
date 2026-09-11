# R2-PHYS provenance matrix

## Material Passport

- Origin Skill: `academic-research-suite` source-verification route
- Origin Mode: primary-source fact check and design gate
- Origin Date: 2026-08-26
- Verification Status: `R2_PHYS_NOT_CLOSED`
- Runtime Authority: none
- Reward Authority: none
- Training Authority: none

## Scope and claim ceiling

This record asks whether the current handover classes can be assigned sourced
physical interruption time `T_HO` and incremental access energy `E_HO` for the
proposed temporal Catfish reward. It does not select parameters, edit the
environment, or establish that an R2 Catfish improves energy efficiency.

The current simulator has two distinct clocks:

- D2 measurement/triggering step: `0.640 s`;
- agent decision step: `47 * 0.640 = 30.08 s`.

Its current R2 is only `0`, `-phi1`, or `-phi2`, with `phi1 = 0.5` and
`phi2 = 1.0`. These are dimensionless project choices, not physical time or
energy.

## Audited primary sources

### HOBS

Chen et al., *Energy-Efficient Joint Handover and Beam Switching Scheme for
Multi-LEO Networks*, IEEE VTC2024-Spring,
[DOI 10.1109/VTC2024-Spring62846.2024.10683088](https://doi.org/10.1109/VTC2024-Spring62846.2024.10683088).
The audited local PDF has SHA-256
`1b2a8eda4647c4f7b68f8ffb08347aaa9cde18ae32b7d6af84d68f827a0f3089`.

HOBS equation (7) defines per-satellite beam-training latency as

```text
C_n(t) = |phi_n^LEO(t)| T_beam
       + sum_m U_n,m(t) (T_fb + T_ack).
```

Table I gives `T_beam = 500 us`, `T_fb = 50 us`, and `T_ack = 50 us`.
Therefore `600 us` is only the one-beacon/one-user training-feedback-ack
component. It is not a reported end-to-end beam-switch interruption, an
inter-satellite handover interruption, or an access-energy value. `C_n(t)` also
depends on the complete training set and user count, so the three constants do
not define one scalar `T_HO(phi1)`.

### 3GPP/ETSI Release 18

The current primary standards anchor is
[ETSI TS 138 133 V18.13.0 (3GPP TS 38.133 Release 18)](https://www.etsi.org/deliver/etsi_ts/138100_138199/138133/18.13.00_60/ts_138133v181300p.pdf),
published April 2026. The downloaded PDF has SHA-256
`663fcf99486599b1087dad68017e90a24ebdc3ff430aea9ed1f6aba08f9a82fb`.

Clause 6.1C.1.3 covers SAN FR2-NTN to SAN FR2-NTN handover. Clause
6.1C.1.3.2 defines interruption from the last old-cell PDSCH TTI to new-cell
PRACH readiness, excluding RRC procedure delay. For a different satellite it
defines

```text
T_interrupt_inter_sat = T_search + T_IU + T_processing
                      + T_sat_beam + T_delta + T_margin.
```

It distinguishes electronic steering (`T_sat_beam = 3 T_rs`) from mechanical
steering (`T_sat_beam = O_angle / 22.5 s`). It therefore does not support one
antenna-agnostic scalar.

The conformance examples provide reproducible reference configurations:

- Annex A.14.2.1.7.3: intra-frequency, intra-satellite FR2-NTN cell
  handover has `T_interrupt = 62 ms` plus `10 ms` RRC procedure delay, hence
  `D_handover = 72 ms`.
- Annex A.14.2.1.9.2-.3: inter-satellite sub-test 1 applies to a VSAT declaring
  an electronic antenna; it has `T_interrupt = 142 ms` plus `10 ms` RRC
  procedure delay, hence `D_handover = 152 ms`. The mechanical sub-test remains
  `TBD` in V18.13.0.

These are normative test-configuration bounds, not measurements of this
simulator or HOBS. Applying them requires an explicit SAN, FR2-NTN, cell,
frequency, synchronization, PRACH/SMTC, and terminal-antenna mapping.

### Supporting model structures that do not close a parameter

Zhang et al., *Handover-Aware Power Minimization for Networked LEO Satellite
Communications: Joint Cooperative Beamforming and Scheduling*,
[arXiv:2603.07434v1](https://arxiv.org/abs/2603.07434), 8 March 2026, is a
recent preprint rather than a standards or measurement source. Its equation
(8) adds an effective per-new-link handover power term `P_HO` and separates a
frame into handover and data fractions; Table I uses `P_HO = 50 dBm`,
`tau_HO = 0.2`, and a 30 s frame. The paper supports the **structure** that a
LEO handover model can contain both a switching-energy equivalent and lost
data time. It does not report a measurement establishing those values for this
simulator, distinguish the present `phi1/phi2/re-entry` classes, or make its
many-to-many cooperative-link boundary equal to the present one-beam-per-user
payload model. Its values therefore cannot be imported as `E_HO` or `T_HO`.

Tayyab et al., *Uplink Reference Signals for Energy-Efficient Handover*, IEEE
Access 8 (2020),
[DOI 10.1109/ACCESS.2020.3020618](https://doi.org/10.1109/ACCESS.2020.3020618),
provides a component-level terrestrial LTE/NR air-interface signaling model.
Equations (5)-(8) combine transmit power, PA/RF/baseband supply power,
signaling-message resource blocks, duration, and occurrence rate; Table II
includes 1 ms signaling durations and separate BS/UE components. This is a
useful template for constructing event energy from named components, but it
does not supply a single satellite handover joule value. Importing its UE and
terrestrial-BS terms would also expand the current denominator boundary, which
otherwise includes satellite payload power only. It therefore cannot close
`E_HO` without a declared boundary change and a satellite/terminal mapping.

## Event-class matrix

| Simulator event | Time evidence | Energy evidence | Current disposition |
|---|---|---|---|
| No handover; same physical satellite and cell | `T_HO = 0` follows from the event definition | `E_HO = 0` follows from the event definition | Source-complete only as the zero reference |
| Same-satellite, different beam/cell (`phi1`) | HOBS supplies a set- and load-dependent beam-training latency, not one per-switch outage. TS 38.133 supplies `62 ms` interruption / `72 ms` delay for an FR2-NTN **cell handover** reference test | No handover-specific joule value found | `UNSOURCED_PRIMARY`; 3GPP value is only a cell-handover sensitivity unless one simulated beam is formally declared one PCell |
| Different satellite (`phi2`, served-to-served) | TS 38.133 supplies `142 ms` interruption / `152 ms` delay for its electronic-VSAT inter-satellite reference test; mechanical remains `TBD` | No handover-specific joule value found | `CONDITIONAL_TIME_PROXY`; requires SAN and electronic-VSAT rulings plus a choice between interruption and full-delay semantics |
| Re-entry after an unserved step (currently charged `phi2`) | This is not automatically a successful handover. TS 38.133 clause 6.2C treats loss/failure as RRC re-establishment and does not provide a matching scalar for the current FR2-NTN/different-satellite case | No matching joule value found | `UNSOURCED`; must be its own event, not silently inherit inter-satellite handover time |
| Episode start | The episode boundary is a simulator boundary. Current code deliberately has no prior association and records no handover | Zero only if the episode is explicitly a warm-start observation; physical initial access would need its own procedure and energy | `MODEL_CONVENTION`; keep separate from physical initial access |

## Clock-scale implications

The standards values have very different salience on the two live clocks:

| Reference quantity | Fraction of `30.08 s` decision step | Fraction of `0.640 s` measurement step |
|---|---:|---:|
| `62 ms` intra-satellite interruption | 0.206117% | 9.6875% |
| `72 ms` intra-satellite total delay | 0.239362% | 11.2500% |
| `142 ms` inter-satellite interruption | 0.472074% | 22.1875% |
| `152 ms` inter-satellite total delay | 0.505319% | 23.7500% |

This does not prove that a shorter agent decision step is better. It establishes
that a one-slot reward at `30.08 s` dilutes the direct useful-time cost by about
47-fold relative to the project-selected `0.640 s` simulator
measurement/triggering clock.

As an outcome-independent scale illustration only, applying `62/142 ms` to the
legacy main replay's `514 phi1 + 2268 served-to-served phi2` events over 10,000
user-decisions would average `0.0353924 s`, or `0.117661%` of one decision
step, per user-decision. Using `72/152 ms` gives `0.0381744 s`, or `0.126910%`.
The replay's eight re-entry events are excluded because their timing is
unsourced. This is not a parameter selection, causal effect, or HOBS-primary
estimate; the class-to-procedure mapping is not yet accepted and the replay is
legacy-narrow geometry.

## Energy provenance

None of the audited sources closes `E_HO`:

- HOBS includes radiated beam power in its EE denominator but reports no
  incremental beam-switch, random-access, or handover energy in joules.
- TS 38.133 specifies timing/performance requirements. Its satellite random
  access clauses point to PRACH transmit-power procedures, but a power formula
  plus a timing bound is not a complete event-energy model. UE RF/baseband,
  satellite payload, gateway/network, retransmission, and overlap boundaries
  remain unspecified.
- Zhang et al. supplies a LEO switching-cost model form but selects an
  effective `P_HO` simulation value rather than measuring this system's event
  energy.
- Tayyab et al. supplies component equations for terrestrial LTE/NR signaling,
  not a boundary-compatible LEO event-energy parameter.

Setting `E_HO = 0` could be declared as a lower-bound sensitivity, but cannot be
called the sourced physical primary. Estimating a nonzero value requires either
a named component-level power-state model or measured per-procedure power
traces, with explicit prevention of double counting against `P_system * Delta`.

## Gate result

```text
R2_PHYS = NOT_CLOSED
```

The proposed one-slot reward

```text
d_u(t) = max(0, Delta - T_HO(c_u(t)))
B(t)   = sum_u R_u(t) d_u(t)
E(t)   = P_system(t) Delta + sum_u E_HO(c_u(t))
eta_HO = B(t) / E(t)
```

must not be frozen yet. The current `0/-phi1/-phi2` reward remains a
baseline/QoS diagnostic only.

Before R2 can claim an EE role, a controller must freeze, without viewing
Catfish treatment outcomes:

1. whether the network is modeled as SAN for this procedure;
2. whether the 0.6 m fixed LOS VSAT is electronic or mechanical;
3. whether a simulated same-satellite beam change is a PCell handover or only
   HOBS beam switching;
4. whether useful-data loss uses `T_interrupt`, full `D_handover`, or a measured
   user-plane outage;
5. the re-entry and episode-start semantics;
6. PRACH/SMTC/synchronization assumptions and any uncertainty arms;
7. the `E_HO` system boundary and source; and
8. whether event physics are evaluated at 0.640 s, represented by a
   remaining-interruption state, or deliberately diluted into 30.08 s.

No coefficient may be enlarged merely to make the R2 effect visible. If a
sourced event-local or multi-step model still has negligible EE effect, R2 must
remain a continuity/QoS specialist rather than being advertised as an
EE-improving Catfish.

## Consistency with the Catfish design gate

- R1 remains the only physically complete direct EE role.
- R2 remains plausible but conditional: the standards evidence makes a real
  time pathway available, while exposing that the current decision clock may
  make its direct EE contribution small.
- R3's final reciprocal-composition falsifier remains logically independent of
  this source gap.
- The proposed HOBS-primary geometry can change handover incidence, so legacy
  event counts are sensitivity evidence only. Source selection must remain
  outcome-independent, and a matched primary checkpoint is still required
  before treatment validation.
