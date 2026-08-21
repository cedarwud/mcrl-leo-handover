"""Frozen scenario constants.

Single source of truth for every number that more than one layer needs, so
the ephemeris, D2, beam, and link-budget layers cannot drift apart.  SDD §3.1
requires the Earth model and coordinate transforms to stay consistent with
the source project's ``env/family_b_geometry.py``; the provenance column
below cites the line each value comes from.

Class codes follow ``NEW-PROJECT-PARAMETER-SPEC-2026-08-21.md`` §0:
P = MODQN paper, P' = other published source, D = derived, S = self-chosen,
X = deviation from a paper-stated value.
"""

from __future__ import annotations

import math

# -- Earth model (SDD §3.1: must match family_b_geometry.py) ---------------

R_E_KM: float = 6371.0
"""Spherical Earth radius, km.  Source: ``family_b_geometry.py:24``.  **S**.

⚠ Deliberately spherical while SGP4 itself runs on WGS-72
(``a = 6378.135 km``).  The ground model is only used for user/cell
positions and elevation angles; satellite states come from SGP4 unchanged.
At the service-area latitude (40°N) the WGS-84 geocentric radius is
≈ 6369.3 km, so the spherical approximation costs ≈ 1.7 km of ground
radius.  Declared, not hidden — G-1 bounds the *satellite* position error,
not the ground model.
"""

OMEGA_E_RAD_S: float = 7.2921159e-5
"""Earth rotation rate, rad/s.  Source: ``family_b_geometry.py:29``.  **P'**.

Cross-checked against d(GMST)/dt in ``tests/test_w02_geometry.py``; the two
must agree, otherwise the real-TLE layer and the legacy geometry disagree
about how fast the Earth turns.
"""

# -- Service area (MODQN §IV) ---------------------------------------------

AREA_CENTER_LAT_DEG: float = 40.0
"""**P** — MODQN §IV service area centre latitude."""

AREA_CENTER_LON_DEG: float = 116.0
"""**P** — MODQN §IV service area centre longitude."""

AREA_EW_KM: float = 200.0
"""**P** — MODQN §IV service area east-west extent."""

AREA_NS_KM: float = 90.0
"""**P** — MODQN §IV service area north-south extent."""

KM_PER_DEG_LAT: float = math.pi * R_E_KM / 180.0
"""**D** — great-circle km per degree of latitude on the spherical Earth."""

# -- Time (MODQN Table I; SDD F1) -----------------------------------------

TIME_STEP_S: float = 1.0
"""**P** — Table I time slot.  SDD §3.1 requires this to be frozen."""

STEPS_PER_EPISODE: int = 10
"""**P** — Table I episode length.  SDD F1 keeps ``H = 10``."""

# -- Ephemeris policy (SDD F3) --------------------------------------------

TLE_ROOT_DEFAULT: str = "~/demo/tle_data/starlink/tle"
"""**S** — SDD §3.1 names this directory as the TLE source."""

MAX_TLE_AGE_H: float = 24.0
"""**S** — SDD F3: "TLE 取 epoch 最近者、齡期 ≤ 24 h"."""

SGP4_GRAVITY_MODEL: str = "wgs72"
"""**P'** — the gravity model TLEs are generated against.  Using WGS-84 with
a TLE is a known modelling error, so this is not a free choice."""

# -- Altitude is NOT a constant any more (SDD F3) -------------------------

TABLE_I_ALTITUDE_KM: float = 780.0
"""**P**, *superseded*.  MODQN Table I ``h = 780 km``.

SDD F3 replaces the synthetic orbit with real Starlink TLEs, which makes
altitude an **observed distribution**, not a parameter.  This value is kept
only so the deviation can be stated and so no code silently reuses 780 km.
Every quantity previously derived from it (``R_b``, ``V``, FSPL, pass
duration, angular rate) must be recomputed from the observed ephemeris.
"""
