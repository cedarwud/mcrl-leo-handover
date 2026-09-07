# HOBS geometry audit receipt

## Inputs

- HOBS local PDF SHA-256:
  `1b2a8eda4647c4f7b68f8ffb08347aaa9cde18ae32b7d6af84d68f827a0f3089`
- Frozen preregistration byte SHA-256:
  `8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543`
- Frozen preregistration self-digest:
  `3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4`
- Episode-8999 checkpoint SHA-256:
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`

## Source anchors

- HOBS PDF page 2, equation (3):
  `mu(theta) = 2.07123 sin(theta) / sin(theta_3dB)` and `theta_3dB` is described
  as the 3 dB half-power beamwidth angle.
- HOBS PDF page 6, Table I: `theta_3dB = 0.058 rad`, `G0 = 40 dBi`, aperture
  `10c/f_c` radius.
- Current runtime: `src/mcrl/env/antenna.py:43-85`.
- Current lattice: `src/mcrl/env/cells.py:49-59,319-374`.
- Current preregistration: `artifacts/PREREG-FROZEN-2026-08-25-R2.json:45-46,88,111-112,2808-2852`.

## Reproduced anchors

```text
F(mu = 2.07123)              = 0.500000408332787
relative gain                = -3.0102964099077365 dB
source one-sided angle       = 3.323155211758775 deg
source full HPBW             = 6.64631042351755 deg
current F(1.66 deg)          = 0.500000408332787
current F(3.32 deg)          = 0.04236871686809121
current mu(3.32 deg)         = 4.140721523358197
source radius at 483 km      = 28.045455359009214 km
source pitch at 483 km       = 48.5761536032088 km
source radius at 550 km      = 31.93581873179103 km
source pitch at 550 km       = 55.31446062477193 km
```

With the current deterministic total-order selection at 483 km:

```text
guarded lattice cells        = 37
12-cell coverage             = 0.9434976095672422
13-cell coverage             = 0.9976853446494262
candidate 13 cell IDs        = [9, 10, 11, 12, 16, 17, 18, 19, 20, 24, 25, 26, 27]
```

Gain-normalization derivation:

```text
current back-computed eta    = 0.6456877935088223
current narrow D/lambda      = 17.71551724137931
proposed wide D/lambda       = 8.857758620689655
consistent wide G0           = 500 linear = 26.989700043360187 dBi
HOBS table G0                = 10000 linear
eta if 10 lambda is radius   = 2.5330295910584444
eta if 10 lambda is diameter = 10.132118364233778
```

## Claim ceiling

This receipt verifies equations, current implementation semantics, and
deterministic geometry calculations. It does not accept the proposed ADR,
authorize a runtime change, validate service feasibility under `G0 = 500`, or
authorize retraining or Catfish treatment outcomes.
