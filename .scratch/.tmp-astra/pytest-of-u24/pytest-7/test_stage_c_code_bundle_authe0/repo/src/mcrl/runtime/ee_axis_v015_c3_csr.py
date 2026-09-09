"""Pure V0.15 C3 coalition-surplus-residual target.

The V0.15 spatial route is a current-slot two-user coalition residual.  Four
already matched :class:`~mcrl.env.step.ActionEvaluation` branches are
consumed without evaluating physics here or consulting either frozen Q head:

``M``
    the sealed reference branch;
``Cu`` and ``Cv``
    the two singleton changes; and
``Cuv``
    the same-slot consolidation change in which both users change.

The C1 singleton credits keep the existing focal EE formula intact.  C3 gets
the residual left after those two credits, including non-additive network
power.  A Shapley split makes the two per-user C3 labels additive at the
coalition boundary while retaining their signs.

For branch ``X`` the canonical current-slot surplus is

``F(X) = interval_s * (sum(served link_rate_bps) - lambda * system_power_w)``.

This module is formula-only: it does not select a source, access Q1/Q2,
advance an environment, or mutate any branch input.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from ..env.step import ActionEvaluation
from ..errors import MCRLContractError


V015_C3_CSR_SCHEMA = "multi-catfish-mcrl-v015-c3-coalition-surplus-residual-v1"
"""Schema for the pure V0.15 C3 coalition target."""

V015_C3_CSR_SOURCE_RULE = "c3-same-beam-two-user-coalition-v1"
"""Default provenance label for the small-group spatial source."""


class C3CSRContractError(MCRLContractError):
    """A V0.15 C3 coalition-surplus-residual contract was violated."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C3CSRContractError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise C3CSRContractError(f"{field} must be a nonempty trimmed string")
    return value


def _positive(value: object, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise C3CSRContractError(f"{field} must be finite and positive")
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise C3CSRContractError(f"{field} must be finite and positive") from error
    if not math.isfinite(parsed) or parsed <= 0.0:
        raise C3CSRContractError(f"{field} must be finite and positive")
    return parsed


def _user_id(value: object, *, field: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, np.integer)
    ):
        raise C3CSRContractError(f"{field} must be an integer user id")
    return int(value)


@dataclass(frozen=True)
class C3CSRProvenance:
    """Immutable lineage metadata attached to a C3 CSR target."""

    source_policy_version: int
    anchor_sha256: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    common_random_field_sha256: str
    source_rule: str = V015_C3_CSR_SOURCE_RULE
    schema: str = V015_C3_CSR_SCHEMA

    def verify(self) -> None:
        if type(self.source_policy_version) is not int or self.source_policy_version <= 0:
            raise C3CSRContractError(
                "provenance source_policy_version must be a positive exact integer"
            )
        for field in (
            "anchor_sha256",
            "source_manifest_sha256",
            "checkpoint_sha256",
            "common_random_field_sha256",
        ):
            _digest(getattr(self, field), field=f"provenance {field}")
        _text(self.source_rule, field="provenance source_rule")
        if self.schema != V015_C3_CSR_SCHEMA:
            raise C3CSRContractError("provenance schema is stale")


@dataclass(frozen=True)
class C3CSRTarget:
    """Immutable V0.15 C3 labels and their current-slot audit surface."""

    focal_user_u: int
    focal_user_v: int
    interval_s: float
    lambda_bits_per_j: float
    reference_surplus_bits: float
    candidate_u_surplus_bits: float
    candidate_v_surplus_bits: float
    candidate_uv_surplus_bits: float
    c1_u_bits: float
    c1_v_bits: float
    h_u_bits: float
    h_v_bits: float
    h_uv_bits: float
    z3_u_bits: float
    z3_v_bits: float
    energy_interaction_delta_w: float
    energy_interaction_surplus_bits: float
    identity_residual_bits: float
    provenance: C3CSRProvenance | None = None
    schema: str = V015_C3_CSR_SCHEMA

    def __post_init__(self) -> None:
        u = _user_id(self.focal_user_u, field="focal_user_u")
        v = _user_id(self.focal_user_v, field="focal_user_v")
        if u == v:
            raise C3CSRContractError("focal user ids must be distinct")
        object.__setattr__(self, "focal_user_u", u)
        object.__setattr__(self, "focal_user_v", v)

        interval = _positive(self.interval_s, field="interval_s")
        multiplier = _positive(
            self.lambda_bits_per_j, field="lambda_bits_per_j"
        )
        object.__setattr__(self, "interval_s", interval)
        object.__setattr__(self, "lambda_bits_per_j", multiplier)

        scalar_fields = (
            "reference_surplus_bits",
            "candidate_u_surplus_bits",
            "candidate_v_surplus_bits",
            "candidate_uv_surplus_bits",
            "c1_u_bits",
            "c1_v_bits",
            "h_u_bits",
            "h_v_bits",
            "h_uv_bits",
            "z3_u_bits",
            "z3_v_bits",
            "energy_interaction_delta_w",
            "energy_interaction_surplus_bits",
            "identity_residual_bits",
        )
        for field in scalar_fields:
            value = getattr(self, field)
            if isinstance(value, (bool, np.bool_)):
                raise C3CSRContractError(f"{field} must be finite")
            try:
                parsed = float(value)
            except (TypeError, ValueError, OverflowError) as error:
                raise C3CSRContractError(f"{field} must be finite") from error
            if not math.isfinite(parsed):
                raise C3CSRContractError(f"{field} must be finite")
            object.__setattr__(self, field, parsed)

        if self.schema != V015_C3_CSR_SCHEMA:
            raise C3CSRContractError("C3 CSR target schema is stale")
        if self.provenance is not None:
            if not isinstance(self.provenance, C3CSRProvenance):
                raise C3CSRContractError("provenance must be C3CSRProvenance")
            try:
                self.provenance.verify()
            except C3CSRContractError as error:
                raise C3CSRContractError(str(error)) from error

    @property
    def cu(self) -> float:
        """Alias for the unchanged C1 singleton credit of user ``u``."""

        return self.c1_u_bits

    @property
    def cv(self) -> float:
        """Alias for the unchanged C1 singleton credit of user ``v``."""

        return self.c1_v_bits

    @property
    def hu(self) -> float:
        """Alias for the singleton residual of user ``u``."""

        return self.h_u_bits

    @property
    def hv(self) -> float:
        """Alias for the singleton residual of user ``v``."""

        return self.h_v_bits

    @property
    def huv(self) -> float:
        """Alias for the two-user coalition residual."""

        return self.h_uv_bits

    @property
    def z3u(self) -> float:
        """Alias for the Shapley C3 label of user ``u``."""

        return self.z3_u_bits

    @property
    def z3v(self) -> float:
        """Alias for the Shapley C3 label of user ``v``."""

        return self.z3_v_bits

    @property
    def energy_interaction_w(self) -> float:
        """Signed ``P(Cuv)-P(Cu)-P(Cv)+P(M)`` diagnostic in watts."""

        return self.energy_interaction_delta_w

    @property
    def energy_synergy_surplus_bits(self) -> float:
        """Positive value means the pair saves canonical energy surplus."""

        return self.energy_interaction_surplus_bits

    @property
    def spatial_interaction_surplus_bits(self) -> float:
        """Non-additive current-slot surplus beyond the two singleton residuals."""

        return self.h_uv_bits - self.h_u_bits - self.h_v_bits

    def verify(self) -> float:
        """Check the C1/C3 coalition identity and return its residual."""

        lhs = math.fsum(
            (self.c1_u_bits, self.c1_v_bits, self.z3_u_bits, self.z3_v_bits)
        )
        rhs = self.candidate_uv_surplus_bits - self.reference_surplus_bits
        residual = lhs - rhs
        magnitude = max(1.0, abs(lhs), abs(rhs))
        tolerance = max(1e-12, 1024.0 * np.finfo(np.float64).eps * magnitude)
        if not math.isfinite(residual) or abs(residual) > tolerance:
            raise C3CSRContractError(
                "C3 CSR identity failed: c1_u+c1_v+z3_u+z3_v "
                "does not equal F(Cuv)-F(M)"
            )
        if not math.isclose(
            residual,
            self.identity_residual_bits,
            rel_tol=0.0,
            abs_tol=tolerance,
        ):
            raise C3CSRContractError(
                "C3 CSR identity_residual_bits disagrees with the target fields"
            )
        return self.identity_residual_bits


def _branch_values(
    branch: ActionEvaluation,
    *,
    field: str,
) -> tuple[np.ndarray, float]:
    if not isinstance(branch, ActionEvaluation):
        raise C3CSRContractError(f"{field} must be an ActionEvaluation")
    try:
        rates = np.asarray(branch.link_rate_bps, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise C3CSRContractError(f"{field} rate vector is malformed") from error
    if rates.ndim != 1 or rates.size < 2:
        raise C3CSRContractError(
            f"{field} link_rate_bps must be a vector for at least two users"
        )
    if not np.all(np.isfinite(rates)) or np.any(rates < 0.0):
        raise C3CSRContractError(
            f"{field} link_rate_bps must be finite and non-negative"
        )

    resolution = getattr(branch, "resolution", None)
    supplied_served = getattr(resolution, "served", None)
    if supplied_served is None:
        # Canonical ActionEvaluation guarantees zero rate for an unserved user.
        served_rates = np.array(rates, dtype=np.float64, copy=True)
    else:
        served = np.asarray(supplied_served)
        if served.dtype != np.bool_ or served.shape != rates.shape:
            raise C3CSRContractError(
                f"{field} resolution.served must be Boolean shape {rates.shape}"
            )
        served_rates = np.where(served, rates, 0.0).astype(
            np.float64, copy=False
        )

    raw_power = getattr(branch, "system_power_w", None)
    if isinstance(raw_power, (bool, np.bool_)):
        raise C3CSRContractError(f"{field} system_power_w must be finite")
    try:
        power = float(raw_power)
    except (TypeError, ValueError, OverflowError) as error:
        raise C3CSRContractError(f"{field} system_power_w must be finite") from error
    if not math.isfinite(power) or power < 0.0:
        raise C3CSRContractError(
            f"{field} system_power_w must be finite and non-negative"
        )
    return served_rates, power


def _current_surplus(
    rates: np.ndarray,
    power: float,
    *,
    interval: float,
    multiplier: float,
    field: str,
) -> float:
    try:
        result = interval * (
            math.fsum(float(value) for value in rates) - multiplier * power
        )
    except (OverflowError, ValueError) as error:
        raise C3CSRContractError(f"{field} surplus arithmetic is non-finite") from error
    if not math.isfinite(result):
        raise C3CSRContractError(f"{field} surplus arithmetic is non-finite")
    return float(result)


def canonical_current_slot_surplus(
    branch: ActionEvaluation,
    *,
    interval_s: float,
    lambda_bits_per_j: float,
) -> float:
    """Return ``F(X)`` for one already evaluated current-slot branch."""

    interval = _positive(interval_s, field="interval_s")
    multiplier = _positive(lambda_bits_per_j, field="lambda_bits_per_j")
    rates, power = _branch_values(branch, field="branch")
    return _current_surplus(
        rates,
        power,
        interval=interval,
        multiplier=multiplier,
        field="branch",
    )


def build_c3_csr_target(
    main: ActionEvaluation,
    candidate_u: ActionEvaluation,
    candidate_v: ActionEvaluation,
    candidate_uv: ActionEvaluation,
    *,
    focal_user_u: int,
    focal_user_v: int,
    interval_s: float,
    lambda_bits_per_j: float,
    provenance: C3CSRProvenance | None = None,
) -> C3CSRTarget:
    """Build one V0.15 C3 coalition-surplus-residual target.

    ``candidate_u`` and ``candidate_v`` are the two singleton branches, and
    ``candidate_uv`` is their same-slot coalition branch.  All four branches
    must already be matched at one current-slot anchor.  This function only
    reads their rate/power fields and never calls an environment method.
    """

    interval = _positive(interval_s, field="interval_s")
    multiplier = _positive(lambda_bits_per_j, field="lambda_bits_per_j")
    u = _user_id(focal_user_u, field="focal_user_u")
    v = _user_id(focal_user_v, field="focal_user_v")
    if u == v:
        raise C3CSRContractError("focal user ids must be distinct")

    if provenance is not None and not isinstance(provenance, C3CSRProvenance):
        raise C3CSRContractError("provenance must be C3CSRProvenance")
    if provenance is not None:
        try:
            provenance.verify()
        except C3CSRContractError as error:
            raise C3CSRContractError(f"provenance is invalid: {error}") from error

    branches = (
        ("main", main),
        ("candidate_u", candidate_u),
        ("candidate_v", candidate_v),
        ("candidate_uv", candidate_uv),
    )
    values = {
        name: _branch_values(branch, field=name)
        for name, branch in branches
    }
    user_counts = {rates.size for rates, _ in values.values()}
    if len(user_counts) != 1:
        raise C3CSRContractError("all ActionEvaluation rate vectors must be identical")
    users = next(iter(user_counts))
    if not 0 <= u < users:
        raise C3CSRContractError("focal_user_u is outside the user vector")
    if not 0 <= v < users:
        raise C3CSRContractError("focal_user_v is outside the user vector")

    surplus = {
        name: _current_surplus(
            rates,
            power,
            interval=interval,
            multiplier=multiplier,
            field=name,
        )
        for name, (rates, power) in values.items()
    }
    main_rates, main_power = values["main"]
    candidate_u_rates, candidate_u_power = values["candidate_u"]
    candidate_v_rates, candidate_v_power = values["candidate_v"]
    candidate_uv_rates, candidate_uv_power = values["candidate_uv"]

    c1_u = interval * (
        float(candidate_u_rates[u]) - float(main_rates[u])
    ) - multiplier * interval * (candidate_u_power - main_power)
    c1_v = interval * (
        float(candidate_v_rates[v]) - float(main_rates[v])
    ) - multiplier * interval * (candidate_v_power - main_power)

    h_u = surplus["candidate_u"] - surplus["main"] - c1_u
    h_v = surplus["candidate_v"] - surplus["main"] - c1_v
    h_uv = (
        surplus["candidate_uv"]
        - surplus["main"]
        - c1_u
        - c1_v
    )
    z3_u = 0.5 * (h_u + h_uv - h_v)
    z3_v = 0.5 * (h_v + h_uv - h_u)

    energy_delta = (
        candidate_uv_power
        - candidate_u_power
        - candidate_v_power
        + main_power
    )
    energy_surplus = -multiplier * interval * energy_delta
    scalars = (
        ("c1_u", c1_u),
        ("c1_v", c1_v),
        ("h_u", h_u),
        ("h_v", h_v),
        ("h_uv", h_uv),
        ("z3_u", z3_u),
        ("z3_v", z3_v),
        ("energy_interaction_delta_w", energy_delta),
        ("energy_interaction_surplus_bits", energy_surplus),
    )
    if any(not math.isfinite(float(value)) for _, value in scalars):
        raise C3CSRContractError("C3 CSR target arithmetic is non-finite")

    lhs = math.fsum((c1_u, c1_v, z3_u, z3_v))
    rhs = surplus["candidate_uv"] - surplus["main"]
    identity_residual = lhs - rhs
    if not math.isfinite(identity_residual):
        raise C3CSRContractError("C3 CSR identity arithmetic is non-finite")

    target = C3CSRTarget(
        focal_user_u=u,
        focal_user_v=v,
        interval_s=interval,
        lambda_bits_per_j=multiplier,
        reference_surplus_bits=surplus["main"],
        candidate_u_surplus_bits=surplus["candidate_u"],
        candidate_v_surplus_bits=surplus["candidate_v"],
        candidate_uv_surplus_bits=surplus["candidate_uv"],
        c1_u_bits=c1_u,
        c1_v_bits=c1_v,
        h_u_bits=h_u,
        h_v_bits=h_v,
        h_uv_bits=h_uv,
        z3_u_bits=z3_u,
        z3_v_bits=z3_v,
        energy_interaction_delta_w=energy_delta,
        energy_interaction_surplus_bits=energy_surplus,
        identity_residual_bits=identity_residual,
        provenance=provenance,
    )
    target.verify()
    return target


# Descriptive compatibility aliases keep the seam discoverable without
# creating a second implementation or another C3 route.
V015C3CSRTarget = C3CSRTarget
V015C3CSRProvenance = C3CSRProvenance
build_v015_c3_csr_target = build_c3_csr_target
c3_csr_target = build_c3_csr_target


__all__ = [
    "C3CSRContractError",
    "C3CSRProvenance",
    "C3CSRTarget",
    "V015C3CSRProvenance",
    "V015C3CSRTarget",
    "V015_C3_CSR_SCHEMA",
    "V015_C3_CSR_SOURCE_RULE",
    "build_c3_csr_target",
    "build_v015_c3_csr_target",
    "c3_csr_target",
    "canonical_current_slot_surplus",
]
