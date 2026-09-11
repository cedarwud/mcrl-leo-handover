"""Q1 schema v4 family: Q1 v2 order, then the v3 gain scalar, then the
per-option incumbent congestion fields that passed the derivability gate.

One stored vector (the ``both`` subset, width 19) carries every added field.
Any subset of the four added fields is a pure column projection of it; each
subset has its own canonical schema object, digest, Q1 width, member width and
derived C3 width.  Two subsets are, by construction, byte-identical to earlier
authorities:

* ``none``      == Q1 v2 (digest 66ed4a...)  -- the v2 baseline
* ``gain_only`` == Q1 v3 (digest 3850d2...)  -- the v3 schema

The congestion fields are computed from this project's own a-r0 physics with
no parameter chosen here:

* gamma(n) = rate_target_sinr(RATE_TARGET_BPS, BEAM_BANDWIDTH_HZ, n)
  (acm.py:95 required_se = r* n / B; batch.py:105-113 builds the same table)
* N = noise_power_w(BEAM_BANDWIDTH_HZ)          (channel.py:41-46; batch.py:115)
* first power iterate from the solver's mandated zero initialisation:
  p1 = min(cap, gamma(n) * N / g_nominal), forced to cap when gamma is None
  (batch.py:255 zeros, 261-266 update)            -- interference term is 0
* cap binding: p1 >= cap - 1e-9                   (batch.py:390-391 cap_hits)
* max aggregate over transmitters                 (batch.py:351-352 max_rf_power_w)
* occupancy = live users on the beam              (batch.py:227-231)

Incumbents are the live users, other than the focal user, that the anchor's
base (default) mapping places on the candidate beam -- the same focal-absent
counterfactual as the v2 coordinate background_occupancy_excluding_focal.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from itertools import combinations
import json
import math
from typing import Any, Callable, Sequence


class Q1SchemaV4Error(RuntimeError):
    """A v4 schema, derivation, or projection invariant failed closed."""


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise Q1SchemaV4Error("value is not canonical finite JSON") from error


def canonical_sha256(value: Any) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def float_hex(value: float | int) -> str:
    number = float(value)
    if not math.isfinite(number):
        raise Q1SchemaV4Error("schema floats must be finite")
    return number.hex()


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    name: str
    unit: str
    scale: float


def _payload(feature: FeatureSpec) -> dict[str, object]:
    return {"name": feature.name, "unit": feature.unit, "scale_hex": float_hex(feature.scale)}


# ---------------------------------------------------------------------------
# Authorities this family must reproduce exactly (checked at import time).
# ---------------------------------------------------------------------------
Q1_V2_SCHEMA_SHA256 = "66ed4a3f9222ac7f20f4334ffab92f6164d2dad203cbac7f7d4e1728ae4ad654"
Q1_V3_SCHEMA_SHA256 = "3850d23fa9cd5a5c2744e60c57e103766ecc73cf46cdf8755382e61e3aaafc01"
Q2_SCHEMA_SHA256 = "a891dd9831d76bccd981cef054ff204fa1d49c3cf6e5f3265015f16f1057019c"
Q1_V4_SCHEMA_VERSION = "mcrl-v025-stagec-q1-action-v4"
CAP_HIT_TOLERANCE_W = 1.0e-9  # batch.py:391
COUNT_SCALE = 10.0            # same "user" scale as v2 background_occupancy_excluding_focal

GAIN_FIELD = "decision_boundary_log_nominal_gain_db"
CONGESTION_FEATURES = (
    FeatureSpec("incumbent_isolated_cap_bound_count_before_join", "user", COUNT_SCALE),
    FeatureSpec("incumbent_isolated_cap_bound_count_added_by_join", "user", COUNT_SCALE),
    FeatureSpec("incumbent_isolated_max_rf_over_cap_after_join", "ratio", 1.0),
)
CONGESTION_FIELDS = tuple(item.name for item in CONGESTION_FEATURES)


def bind_authorities(q1v2_module: Any, q1v3_module: Any) -> None:
    """Pin the v2 and v3 schema objects this family is defined against."""

    global Q1_V2_FEATURES, GAIN_FEATURE, Q1_V2_SCHEMA, Q1_V3_SCHEMA, ALL_ADDED
    global FULL_FEATURES, ADDED_ORDER
    if q1v2_module.Q1_V2_SCHEMA_SHA256 != Q1_V2_SCHEMA_SHA256:
        raise Q1SchemaV4Error("Q1 v2 authority digest drifted")
    if q1v3_module.Q1_V3_SCHEMA_SHA256 != Q1_V3_SCHEMA_SHA256:
        raise Q1SchemaV4Error("Q1 v3 authority digest drifted")
    if canonical_sha256(q1v2_module.Q1_V2_SCHEMA) != Q1_V2_SCHEMA_SHA256:
        raise Q1SchemaV4Error("Q1 v2 schema object does not hash to its digest")
    if canonical_sha256(q1v3_module.Q1_V3_SCHEMA) != Q1_V3_SCHEMA_SHA256:
        raise Q1SchemaV4Error("Q1 v3 schema object does not hash to its digest")
    v2 = tuple(FeatureSpec(x.name, x.unit, float(x.scale)) for x in q1v2_module.Q1_V2_FEATURES)
    v3 = tuple(FeatureSpec(x.name, x.unit, float(x.scale)) for x in q1v3_module.Q1_V3_FEATURES)
    if len(v2) != 15 or v3[:15] != v2 or len(v3) != 16 or v3[15].name != GAIN_FIELD:
        raise Q1SchemaV4Error("v3 is not v2 plus the gain scalar")
    Q1_V2_FEATURES = v2
    GAIN_FEATURE = v3[15]
    Q1_V2_SCHEMA = q1v2_module.Q1_V2_SCHEMA
    Q1_V3_SCHEMA = q1v3_module.Q1_V3_SCHEMA
    ADDED_ORDER = (GAIN_FEATURE, *CONGESTION_FEATURES)
    ALL_ADDED = tuple(item.name for item in ADDED_ORDER)
    FULL_FEATURES = (*Q1_V2_FEATURES, *ADDED_ORDER)


def derivation_block(physics: dict[str, str]) -> dict[str, object]:
    return {
        "estimand": (
            "interference-free first power iterate of the a-r0 nominal solver for the "
            "incumbents of the candidate beam; a lower bound on the converged power "
            "(iterates are nondecreasing from zero, batch.py:267-268 rejects decrease)"
        ),
        "gamma": "rate_target_sinr(RATE_TARGET_BPS, BEAM_BANDWIDTH_HZ, n); acm.py:95, batch.py:105-113",
        "noise": "noise_power_w(BEAM_BANDWIDTH_HZ); channel.py:41-46, batch.py:115",
        "first_iterate": "min(cap, gamma(n)*N/g_nominal), forced cap when gamma is None; batch.py:255,261-266",
        "cap_binding": "first_iterate >= cap - 1e-9; batch.py:390-391",
        "max_aggregate": "max over transmitting incumbents; batch.py:351-352; empty set radiates 0 W",
        "occupancy": "live (visible & d2_eligible & cell_reachable) users on the beam; batch.py:227-231",
        "incumbents": "live users != focal that the anchor default_mapping places on the candidate beam",
        "n_after": "n_before + 1[focal option live at boundary 0]",
        "null_action": "explicit null joins no beam: empty incumbent set -> counts 0, max RF 0",
        "incumbent_gain_source": (
            "mcrl-v025-exact-source-row-physics-v1.default_geometry_offsets_0_1_2_3[0]."
            "nominal_gain_hex of each incumbent (build.py:292 writes arrays.nominal_gain[0,row])"
        ),
        "constants_hex": dict(sorted(physics.items())),
    }


def subset_schema(added: Sequence[str], physics: dict[str, str]) -> dict[str, object]:
    added = tuple(added)
    if len(set(added)) != len(added) or any(name not in ALL_ADDED for name in added):
        raise Q1SchemaV4Error(f"unknown or duplicate added field in {added}")
    ordered = tuple(name for name in ALL_ADDED if name in added)
    if ordered != added:
        raise Q1SchemaV4Error("added fields must follow canonical v4 order")
    if not added:
        return Q1_V2_SCHEMA
    if added == (GAIN_FIELD,):
        return Q1_V3_SCHEMA
    features = (*Q1_V2_FEATURES, *(f for f in ADDED_ORDER if f.name in added))
    congestion = [name for name in added if name in CONGESTION_FIELDS]
    return {
        "schema": Q1_V4_SCHEMA_VERSION,
        "subset_added_fields": list(added),
        "successor_of": {"schema": "mcrl-v025-stagec-q1-action-v2", "sha256": Q1_V2_SCHEMA_SHA256},
        "gain_field_authority": (
            {"schema": "mcrl-v025-stagec-q1-action-v3", "sha256": Q1_V3_SCHEMA_SHA256}
            if GAIN_FIELD in added else None
        ),
        "normalization": "raw_value / positive_frozen_scale; signed values retained",
        "shape": [len(features)],
        "features": [_payload(f) for f in features],
        "congestion_derivation": derivation_block(physics) if congestion else None,
    }


def subset_widths(added: Sequence[str]) -> dict[str, int]:
    q1 = 15 + len(tuple(added))
    member = 2 * q1 + 6
    c3 = 1 + 2 * member + 4 * 7 + (32 * 4 + 1) + 6
    return {"q1_width": q1, "member_width": member, "c3_width": c3}


NAMED_SUBSETS = {
    "none": (),
    "gain_only": (GAIN_FIELD,),
    "congestion_only": CONGESTION_FIELDS,
    "both": (GAIN_FIELD, *CONGESTION_FIELDS),
}
# Fail-closed expectations, derived on paper from 1 + 2*(2*Q1+6) + 4*7 + (32*4+1) + 6.
EXPECTED_WIDTHS = {
    "none": {"q1_width": 15, "member_width": 36, "c3_width": 236},
    "gain_only": {"q1_width": 16, "member_width": 38, "c3_width": 240},
    "congestion_only": {"q1_width": 18, "member_width": 42, "c3_width": 248},
    "both": {"q1_width": 19, "member_width": 44, "c3_width": 252},
}


def projection_indices(added: Sequence[str]) -> tuple[int, ...]:
    """Column indices into the stored full (``both``) vector for a subset."""

    keep = set(added)
    indices = list(range(15))
    for offset, name in enumerate(ALL_ADDED):
        if name in keep:
            indices.append(15 + offset)
    return tuple(indices)


def project(full_state: Sequence[Any], added: Sequence[str]) -> list[Any]:
    if len(full_state) != len(FULL_FEATURES):
        raise Q1SchemaV4Error("stored v4 vector has the wrong width")
    return [full_state[i] for i in projection_indices(added)]


def all_subsets() -> tuple[tuple[str, ...], ...]:
    result = []
    for size in range(len(ALL_ADDED) + 1):
        for combo in combinations(ALL_ADDED, size):
            result.append(tuple(combo))
    return tuple(result)


def incumbent_congestion(
    *,
    null_action: bool,
    focal_live: bool,
    incumbent_gains: Sequence[float],
    gamma: Callable[[int], float | None],
    noise_w: float,
    cap_w: float,
) -> tuple[float, float, float]:
    """Return raw (count_before, count_added, max_rf_over_cap_after)."""

    if null_action:
        if incumbent_gains:
            raise Q1SchemaV4Error("null action cannot carry incumbents")
        return 0.0, 0.0, 0.0
    gains = tuple(float(g) for g in incumbent_gains)
    if any(not math.isfinite(g) or g <= 0.0 for g in gains):
        raise Q1SchemaV4Error("incumbent nominal gain must be positive finite")
    n_before = len(gains)
    n_after = n_before + (1 if focal_live else 0)

    def first_iterate(g: float, n: int) -> float:
        target = gamma(n)
        if target is None:
            return cap_w
        return min(cap_w, target * noise_w / g)

    if n_before == 0:
        return 0.0, 0.0, 0.0
    before = [first_iterate(g, n_before) for g in gains]
    after = [first_iterate(g, n_after) for g in gains]
    bound_before = sum(p >= cap_w - CAP_HIT_TOLERANCE_W for p in before)
    bound_after = sum(p >= cap_w - CAP_HIT_TOLERANCE_W for p in after)
    if bound_after < bound_before:
        raise Q1SchemaV4Error("gamma is not nondecreasing in occupancy")
    return float(bound_before), float(bound_after - bound_before), max(after) / cap_w


def normalized_congestion(raw: tuple[float, float, float]) -> tuple[float, float, float]:
    out = tuple(value / spec.scale for value, spec in zip(raw, CONGESTION_FEATURES, strict=True))
    if not all(math.isfinite(x) for x in out):
        raise Q1SchemaV4Error("non-finite congestion coordinate")
    return out
