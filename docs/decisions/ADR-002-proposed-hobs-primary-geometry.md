# ADR-002: Proposed HOBS-equation primary geometry

## Status

Proposed. This record fixes the interpretation recommended for independent
review, but it has no runtime, preregistration, checkpoint, Catfish, or training
authority. The current frozen preregistration remains immutable.

## Date

2026-08-26

## Context

The Catfish design-data gate cannot admit treatment outcomes until antenna
geometry is independent of mechanism success. The current MCRL implementation
and completed episode-8999 checkpoint use a narrower convention than the
literal HOBS antenna equation.

The source is Chen et al., *Energy-Efficient Joint Handover and Beam Switching
Scheme for Multi-LEO Networks*, IEEE VTC2024-Spring,
DOI `10.1109/VTC2024-Spring62846.2024.10683088`. The audited local PDF has
SHA-256
`1b2a8eda4647c4f7b68f8ffb08347aaa9cde18ae32b7d6af84d68f827a0f3089`.

HOBS equation (3) defines

```text
mu(theta) = 2.07123 * sin(theta) / sin(theta_3dB)
```

and calls `theta_3dB` the 3 dB half-power beamwidth angle. Table I gives
`theta_3dB = 0.058 rad`. HOBS does not explicitly say whether that number is a
one-sided angle or a full angular span. Direct substitution gives

```text
F(mu = 2.07123) = 0.5000004083 = -3.010296 dB.
```

Therefore the source equation places the reported parameter at a half-power
boundary. Interpreting the pattern argument as off-boresight angle yields the
following derived, one-sided reading:

```text
theta_hp_one_sided = 0.058 rad = 3.3231552118 deg
HPBW_full          = 0.116 rad = 6.6463104235 deg.
```

The current MCRL API instead registers `THETA_3DB_DEG = 3.32` as the full HPBW
and halves it in both the antenna pattern and cell-radius function. It therefore
places the half-power point at `1.66 deg`. Under the current pattern,
`F(3.32 deg) = 0.0423687`, not one half.

The completed checkpoint is bound to preregistration digest
`3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4`,
whose byte SHA-256 is
`8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543`.
That record explicitly stores full HPBW `3.32 deg`, passes half of it to the
pattern, uses `G0 = 2000`, and freezes 39 pointing cells. The episode-8999
checkpoint SHA-256 is
`e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`.

## Proposed decision

### 1. Use unambiguous names at every boundary

No new interface may use bare `theta_3dB` without a convention field. The
geometry bundle must carry both:

```text
theta_hp_one_sided_rad
hpbw_full_rad = 2 * theta_hp_one_sided_rad
```

Degree representations are derived reporting values, not independent inputs.

### 2. Make the literal HOBS equation the primary angle convention

The proposed primary geometry uses:

```text
theta_hp_one_sided_rad = 0.058
hpbw_full_rad          = 0.116
hpbw_full_deg          = 6.6463104235
```

If the existing full-HPBW API is retained, it receives `6.6463104235 deg` and
halves exactly once internally. The source value must never be halved twice.

The current convention becomes the named sensitivity arm:

```text
legacy_narrow_hpbw_full_deg          = 3.32
legacy_narrow_theta_hp_one_sided_deg = 1.66
```

### 3. Couple the primary cell lattice to the one-sided angle

For the existing earth-fixed hexagonal lattice:

```text
cell_radius(h) = h * tan(0.058)
pitch(h)       = sqrt(3) * cell_radius(h).
```

At the current grid-freeze altitude `h = 483 km`, this gives:

```text
cell_radius = 28.0454553590 km
pitch       = 48.5761536032 km.
```

Using the current crop, one guard ring, service-area sample, and deterministic
total ordering produces a 37-cell guarded lattice. The first 13 receipt-selected
cells
`[9, 10, 11, 12, 16, 17, 18, 19, 20, 24, 25, 26, 27]` cover
`0.9976853446` of the 200 x 90 km service-area sample; 12 cover only
`0.9434976096`. These are provisional reproducible measurements, not a new
preregistration. A future accepted freeze must regenerate and store the exact
IDs and algorithm/source digests.

The proposed live geometry remains the complete 37-cell guarded lattice. The
13-cell set is a **receipt-only coverage summary** under the existing
deterministic coverage rule; it does not filter runtime cell identities,
anchors, neighbours, observations, or actions. A later decision to make a
finite selected set constrain runtime would require a separate ADR and matched
runtime tests. The local action width remains four satellite slots times seven
local anchor/neighbour beam slots, or 28 actions per user.

### 4. Do not silently retain the old gain normalization

HOBS Table I also lists `G0 = 40 dBi` and the text `10c/f_c rad` for aperture.
That text does not unambiguously establish a physical radius or diameter. Under
either interpretation, however, the reported gain and aperture cannot be
reconciled with aperture efficiency at or below one: the stated gain would
require efficiency `2.5330` if `10 lambda` is a radius, or `10.1321` if it is a
diameter. Thus table-literal `G0 = 10000` is a source-reproduction diagnostic,
not a provenance-closed physical primary.

The live code documents an aperture-efficiency range of `0.639--0.645` and uses
an aperture/beamwidth relation with the narrower full HPBW to obtain the rounded
legacy value `G0 = 2000`. If that same relation and legacy normalization are
held conditionally while the full HPBW doubles, `D/lambda` halves and gain is
approximately quartered. This produces the conditional candidate:

```text
G0_conditional_linear ~= 500
G0_conditional_dBi    ~= 26.99 dBi.
```

This is a derived MCRL candidate, not a value reported by HOBS and not yet the
primary. The exact aperture relation, efficiency source, and meaning of the
HOBS aperture field require independent closure. The candidate set is:

- `G0 ~= 500`: conditional same-relation candidate;
- `G0 = 2000`: width-only sensitivity that holds the current link-budget
  normalization; and
- `G0 = 10000`: HOBS-table-literal diagnostic with the aperture inconsistency
  explicitly disclosed.

No outcome may be used to choose among these gain normalizations. Independent
source/physics review and an explicit controller ruling are required before the
primary gain is accepted. Until then, `G0_primary = UNRESOLVED`.

### 5. Reclassify existing evidence, do not invalidate it

The episode-8999 checkpoint and all measurements bound to its preregistration
remain valid evidence for the legacy-narrow sensitivity geometry. They are not
a matched reference for the proposed primary geometry. Running that checkpoint
under changed antenna/lattice physics would be a domain-shift sensitivity test,
not a primary baseline.

## Alternatives considered

### Keep full HPBW 3.32 degrees as HOBS-faithful primary

Rejected as a source claim. It contradicts HOBS equation (3), where the stated
parameter itself lands at the half-power point. Retained as legacy sensitivity.

### Use HOBS Table I gain 40 dBi unchanged

Rejected as the physical primary because it requires aperture efficiency above
one under either legal radius/diameter reading. Retained only as a literal-table
diagnostic.

### Widen the beam but keep G0 = 2000 as the primary

Not selected. It would hold link-budget normalization while changing beamwidth
and therefore requires explicit sensitivity labeling. It remains a candidate
only until the gain-normalization gate is independently closed.

### Select geometry by whichever Catfish result is strongest

Rejected. It leaks treatment outcomes into the physical model and invalidates
the mechanism comparison.

## Consequences

- No existing Catfish effect size transfers from the legacy-narrow geometry to
  the proposed primary.
- The current 39-cell preregistration receipt cannot be reused: the proposed
  wide geometry generates a 37-cell guarded live lattice. Its 13-cell
  receipt-only coverage summary does not constrain runtime candidates.
- Antenna gain, interference, candidate overlap, beam load, handover frequency,
  and angle-aware EE/power sensitivity can all change together.
- A new matched Main reference checkpoint is required before primary-geometry
  treatment development or validation. That later retraining is heavy work and
  belongs on the Ubuntu server; this ADR does not authorize it.
- Legacy checkpoint probes may continue only when labelled
  `legacy_narrow_sensitivity`.

## Required acceptance gates

1. Independent review confirms the HOBS equation/table interpretation and
   identifies a sourced aperture/gain relation and efficiency range.
2. A controller selects the primary gain normalization without seeing Catfish
   treatment outcomes; `G0 ~= 500` is not privileged before that ruling.
3. Runtime implementation exposes the two angle fields and a named geometry
   stratum; it does not overwrite the frozen legacy constants in place.
4. Runtime and receipt semantics are tested separately: runtime uses the full
   guarded lattice, while any receipt-selected coverage subset is audit-only.
5. Absolute tests establish `F(3.323155 deg) = 0.5`, the 483/550 km radius and
   pitch anchors, exact pointing-cell IDs/count/coverage, guard completeness,
   units, RNG, and resume parity.
6. A new preregistration and matched reference checkpoint are sealed before any
   primary-geometry design or validation seed is opened.
