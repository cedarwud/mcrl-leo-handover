"""Complete v1 coalition rows, invariant encoding, and authenticated shards."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from itertools import combinations
import json
import math
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from mcrl.physics_v025.targets import NetworkOutcome, coalition_identity

from .canonical import (
    StageCContractError,
    canonical_json_bytes,
    canonical_sha256,
    float_hex,
    parse_float_hex,
    verify_sha256_sidecar,
    write_once_with_sha256,
)
from .state import PhysicalAction


COALITION_ROW_SCHEMA = "mcrl-v025-stagec-c3-coalition-row-v1"
COALITION_SHARD_SCHEMA = "mcrl-v025-stagec-c3-coalition-shard-v1"
MAX_LABEL_COALITION_SIZE = 4


@dataclass(frozen=True, slots=True)
class CoalitionMember:
    user_id: int
    reference_action: PhysicalAction
    selected_action: PhysicalAction
    selected_q1_row: tuple[float, ...]
    incumbent_q1_row: tuple[float, ...]
    missing_incumbent: bool

    def __post_init__(self) -> None:
        if (
            not self.selected_q1_row
            or len(self.selected_q1_row) != len(self.incumbent_q1_row)
            or not all(
                math.isfinite(value)
                for value in (*self.selected_q1_row, *self.incumbent_q1_row)
            )
        ):
            raise StageCContractError("selected and incumbent Q1 rows must be finite and aligned")

    @property
    def invariant_features(self) -> tuple[float, ...]:
        return (*self.selected_q1_row, *self.incumbent_q1_row, float(self.missing_incumbent))


@dataclass(frozen=True, slots=True)
class AffectedBeamContext:
    beam_key: str
    occupancy_before: int
    occupancy_after: int
    active_before: bool
    active_after: bool
    shared_capacity: float
    interference_summary: float
    capacity_margin: float = 0.0

    def __post_init__(self) -> None:
        if self.occupancy_before < 0 or self.occupancy_after < 0:
            raise StageCContractError("coalition occupancy must be nonnegative")
        if self.shared_capacity < 0.0 or not all(
            math.isfinite(value)
            for value in (self.shared_capacity, self.interference_summary, self.capacity_margin)
        ):
            raise StageCContractError("coalition shared-resource context is invalid")


@dataclass(frozen=True, slots=True)
class CoalitionContext:
    anchor_id: str
    reference_profile: tuple[tuple[int, PhysicalAction], ...]
    members: tuple[CoalitionMember, ...]
    affected_beams: tuple[AffectedBeamContext, ...]
    global_resource_features: tuple[float, ...]

    def __post_init__(self) -> None:
        reference_users = tuple(user for user, _ in self.reference_profile)
        member_users = tuple(member.user_id for member in self.members)
        if (
            not reference_users
            or reference_users != tuple(sorted(reference_users))
            or len(set(reference_users)) != len(reference_users)
        ):
            raise StageCContractError("coalition a0 must be a complete sorted user profile")
        if not 0 <= len(self.members) <= MAX_LABEL_COALITION_SIZE:
            raise StageCContractError("coalition support is capped at four users")
        if len(set(member_users)) != len(member_users) or not set(member_users) <= set(reference_users):
            raise StageCContractError("changed users must be unique members of a0")
        if not self.affected_beams:
            raise StageCContractError("coalition context requires affected resource rows")
        if not self.global_resource_features or not all(
            math.isfinite(value) for value in self.global_resource_features
        ):
            raise StageCContractError("global coalition features must be finite and nonempty")
        widths = {len(member.invariant_features) for member in self.members}
        if len(widths) > 1:
            raise StageCContractError("coalition member feature widths differ")

    @property
    def changed_users(self) -> tuple[int, ...]:
        return tuple(sorted(member.user_id for member in self.members))

    def payload(self) -> dict[str, object]:
        return {
            "anchor_id": self.anchor_id,
            "reference_profile": [
                {"user_id": user, "action": action.payload()}
                for user, action in self.reference_profile
            ],
            "members": [
                {
                    "user_id": member.user_id,
                    "reference_action": member.reference_action.payload(),
                    "selected_action": member.selected_action.payload(),
                    "selected_q1_row_hex": [
                        float_hex(value) for value in member.selected_q1_row
                    ],
                    "incumbent_q1_row_hex": [
                        float_hex(value) for value in member.incumbent_q1_row
                    ],
                    "missing_incumbent": member.missing_incumbent,
                }
                for member in sorted(self.members, key=lambda item: item.user_id)
            ],
            "affected_beams": [
                {
                    "beam_key": beam.beam_key,
                    "occupancy_before": beam.occupancy_before,
                    "occupancy_after": beam.occupancy_after,
                    "active_before": beam.active_before,
                    "active_after": beam.active_after,
                    "shared_capacity_hex": float_hex(beam.shared_capacity),
                    "interference_summary_hex": float_hex(beam.interference_summary),
                    "capacity_margin_hex": float_hex(beam.capacity_margin),
                }
                for beam in sorted(self.affected_beams, key=lambda item: item.beam_key)
            ],
            "global_resource_features_hex": [
                float_hex(value) for value in self.global_resource_features
            ],
        }

    def invariant_vector(self, *, member_width: int) -> np.ndarray:
        """DeepSets-style deterministic encoding; IDs/order are not features."""

        if len(self.members) <= 1:
            # Empty and singleton values are hard anchored by the head, but a
            # stable vector remains useful for schema and KAT checks.
            member_matrix = np.zeros((1, member_width), dtype=np.float64)
        else:
            member_matrix = np.asarray(
                [member.invariant_features for member in self.members],
                dtype=np.float64,
            )
            if member_matrix.shape[1] != member_width:
                raise StageCContractError("coalition member feature width drifted")
        beams = tuple(sorted(self.affected_beams, key=lambda beam: beam.beam_key))
        if len(beams) > MAX_LABEL_COALITION_SIZE:
            raise StageCContractError("set-head affected-beam context exceeds the four-row cap")
        beam_features = [
            [
                beam.occupancy_before,
                beam.occupancy_after,
                float(beam.active_after) - float(beam.active_before),
                beam.shared_capacity,
                beam.interference_summary,
                beam.capacity_margin,
                1.0,
            ]
            for beam in beams
        ]
        beam_features.extend(
            [[0.0] * 7 for _ in range(MAX_LABEL_COALITION_SIZE - len(beam_features))]
        )
        vector = np.concatenate(
            (
                np.asarray([float(len(self.members))], dtype=np.float64),
                member_matrix.sum(axis=0),
                member_matrix.max(axis=0),
                np.asarray(beam_features, dtype=np.float64).reshape(-1),
                np.asarray(self.global_resource_features, dtype=np.float64),
            )
        )
        if not np.isfinite(vector).all():
            raise StageCContractError("coalition invariant encoding is non-finite")
        return vector


@dataclass(frozen=True, slots=True)
class CoalitionRow:
    schema: str
    split: str
    world_id: str
    world_seed: int
    learner_seed: int | None
    anchor_id: str
    anchor_index: int
    decision_time_utc: str
    decision_time_ns: int
    setting_id: str
    context: CoalitionContext
    original_changed_user_count: int
    capped_decomposition: bool
    original_changed_users: tuple[int, ...]
    decomposition_id: str
    decomposition_weight_hex: str
    lambda_bits_per_j_hex: str
    eta_ref_bits_per_j_hex: str
    kappa_normalization_bits_hex: str
    c1_normalized_hex: str
    psi_normalized_hex: str
    objective_delta_normalized_hex: str
    physical_c1_normalized_hex: str
    physical_psi_normalized_hex: str
    physical_delta_normalized_hex: str
    code_digest: str
    physics_digest: str
    catalogue_digest: str
    setting_digest: str
    calibration_digest: str
    allocation_manifest_digest: str

    def __post_init__(self) -> None:
        if self.schema != COALITION_ROW_SCHEMA or self.split != "TRAIN":
            raise StageCContractError("C3 coalition rows are versioned TRAIN rows")
        size = len(self.context.members)
        if not 2 <= size <= MAX_LABEL_COALITION_SIZE:
            raise StageCContractError("trainable C3 rows require coalition size 2..4")
        if self.original_changed_user_count < size:
            raise StageCContractError("original coalition count cannot be smaller than its cap")
        if self.capped_decomposition != (self.original_changed_user_count > size):
            raise StageCContractError("larger-set capped-decomposition flag is inconsistent")
        if self.original_changed_user_count != len(self.original_changed_users):
            raise StageCContractError("larger-set original user inventory is incomplete")
        if not set(self.context.changed_users) <= set(self.original_changed_users):
            raise StageCContractError("capped subset is not drawn from the original evacuation")
        weight = parse_float_hex(self.decomposition_weight_hex, field="decomposition_weight")
        if not self.decomposition_id or weight <= 0.0 or weight > 1.0:
            raise StageCContractError("capped decomposition identity/weight is invalid")
        expected = capped_coalition_decomposition(self.original_changed_users)
        expected_weights = {users: value for users, value in expected}
        if expected_weights.get(self.context.changed_users) != weight:
            raise StageCContractError("capped decomposition subset or row weight drifted")
        expected_id = canonical_sha256({
            "schema": "mcrl-v025-stagec-capped-coalition-decomposition-v1",
            "original_changed_users": list(self.original_changed_users),
            "subsets": [list(users) for users, _ in expected],
        })
        if self.decomposition_id != expected_id:
            raise StageCContractError("capped decomposition digest drifted")
        for field in (
            "code_digest",
            "physics_digest",
            "catalogue_digest",
            "setting_digest",
            "calibration_digest",
            "allocation_manifest_digest",
        ):
            digest = getattr(self, field)
            if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
                raise StageCContractError(f"C3 {field} must be a lowercase SHA-256")
        kappa = parse_float_hex(self.kappa_normalization_bits_hex, field="kappa")
        lambda_bits = parse_float_hex(self.lambda_bits_per_j_hex, field="lambda")
        eta_ref = parse_float_hex(self.eta_ref_bits_per_j_hex, field="eta_ref")
        if kappa <= 0.0 or lambda_bits <= 0.0 or lambda_bits != eta_ref:
            raise StageCContractError("C3 row prices must be positive and lambda=eta_ref")
        c1 = parse_float_hex(self.c1_normalized_hex, field="c1")
        psi = parse_float_hex(self.psi_normalized_hex, field="psi")
        delta = parse_float_hex(self.objective_delta_normalized_hex, field="objective_delta")
        pc1 = parse_float_hex(self.physical_c1_normalized_hex, field="physical_c1")
        ppsi = parse_float_hex(self.physical_psi_normalized_hex, field="physical_psi")
        pdelta = parse_float_hex(self.physical_delta_normalized_hex, field="physical_delta")
        if not math.isclose(c1 + psi, delta, rel_tol=0.0, abs_tol=1e-12) or not math.isclose(
            pc1 + ppsi, pdelta, rel_tol=0.0, abs_tol=1e-12
        ):
            raise StageCContractError("C3 row reconstruction identity drifted")

    def payload(self) -> dict[str, object]:
        value = asdict(self)
        value["context"] = self.context.payload()
        return value


def build_coalition_row(
    *,
    context: CoalitionContext,
    reference_outcome: NetworkOutcome,
    unilateral_outcomes: Mapping[int, NetworkOutcome],
    coalition_outcome: NetworkOutcome,
    original_changed_user_count: int | None = None,
    original_changed_users: Sequence[int] | None = None,
    world_id: str,
    world_seed: int,
    anchor_index: int,
    decision_time_utc: str,
    decision_time_ns: int,
    setting_id: str,
    lambda_bits_per_j: float,
    eta_ref_bits_per_j: float,
    kappa_normalization_bits: float,
    code_digest: str,
    physics_digest: str,
    catalogue_digest: str,
    setting_digest: str,
    calibration_digest: str,
    allocation_manifest_digest: str,
) -> CoalitionRow:
    """Production B4/B5 builder from nominal counterfactual outcomes."""

    identity = coalition_identity(
        coalition_users=context.changed_users,
        reference=reference_outcome,
        unilateral_by_user=unilateral_outcomes,
        coalition=coalition_outcome,
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref_bits_per_j,
        kappa_bits_per_user_s=kappa_normalization_bits,
    )
    kappa = Fraction(str(kappa_normalization_bits))
    original_users = (
        context.changed_users
        if original_changed_users is None
        else tuple(sorted(int(user) for user in original_changed_users))
    )
    original_count = len(original_users) if original_changed_user_count is None else original_changed_user_count
    if original_count != len(original_users):
        raise StageCContractError("original changed-user count requires the complete user inventory")
    decomposition = dict(capped_coalition_decomposition(original_users))
    if context.changed_users not in decomposition:
        raise StageCContractError("coalition context is absent from the sealed capped decomposition")
    return CoalitionRow(
        schema=COALITION_ROW_SCHEMA,
        split="TRAIN",
        world_id=world_id,
        world_seed=world_seed,
        learner_seed=None,
        anchor_id=context.anchor_id,
        anchor_index=anchor_index,
        decision_time_utc=decision_time_utc,
        decision_time_ns=decision_time_ns,
        setting_id=setting_id,
        context=context,
        original_changed_user_count=original_count,
        capped_decomposition=original_count > len(context.members),
        original_changed_users=original_users,
        decomposition_id=canonical_sha256({
            "schema": "mcrl-v025-stagec-capped-coalition-decomposition-v1",
            "original_changed_users": list(original_users),
            "subsets": [list(users) for users, _ in capped_coalition_decomposition(original_users)],
        }),
        decomposition_weight_hex=float_hex(decomposition[context.changed_users]),
        lambda_bits_per_j_hex=float_hex(lambda_bits_per_j),
        eta_ref_bits_per_j_hex=float_hex(eta_ref_bits_per_j),
        kappa_normalization_bits_hex=float_hex(kappa_normalization_bits),
        c1_normalized_hex=float_hex(float(identity.c1 / kappa)),
        psi_normalized_hex=float_hex(float(identity.c3 / kappa)),
        objective_delta_normalized_hex=float_hex(float(identity.objective_delta / kappa)),
        physical_c1_normalized_hex=float_hex(float(identity.physical_c1 / kappa)),
        physical_psi_normalized_hex=float_hex(float(identity.physical_c3 / kappa)),
        physical_delta_normalized_hex=float_hex(float(identity.physical_delta / kappa)),
        code_digest=code_digest,
        physics_digest=physics_digest,
        catalogue_digest=catalogue_digest,
        setting_digest=setting_digest,
        calibration_digest=calibration_digest,
        allocation_manifest_digest=allocation_manifest_digest,
    )


def capped_coalition_decomposition(
    changed_users: Sequence[int],
) -> tuple[tuple[tuple[int, ...], float], ...]:
    """B5 frozen rule: all lexicographic size-four subsets, equal row weight."""

    users = tuple(sorted(int(user) for user in changed_users))
    if len(set(users)) != len(users) or len(users) < 2:
        raise StageCContractError("capped decomposition requires unique changed users")
    subsets = (users,) if len(users) <= MAX_LABEL_COALITION_SIZE else tuple(
        combinations(users, MAX_LABEL_COALITION_SIZE)
    )
    weight = 1.0 / len(subsets)
    return tuple((tuple(subset), weight) for subset in subsets)


def pair_reporting_credit(
    *, psi_normalized: float, coalition_users: Sequence[int], roster: Sequence[int]
) -> dict[int, float]:
    """B5 reporting-only equal pair credit, with explicit dummy-user zeros."""

    users = tuple(coalition_users)
    complete_roster = tuple(roster)
    if len(users) != 2 or len(set(users)) != 2 or not set(users) <= set(complete_roster):
        raise StageCContractError("pair reporting credit requires two roster members")
    return {
        user: float(psi_normalized) / 2.0 if user in users else 0.0
        for user in complete_roster
    }


def exact_shapley_reporting_credit(
    *,
    coalition_users: Sequence[int],
    subset_values: Mapping[frozenset[int], float],
    roster: Sequence[int],
) -> dict[int, float]:
    """Exact reporting-only Shapley allocation for a coalition of at most four."""

    users = tuple(sorted(coalition_users))
    complete_roster = tuple(roster)
    if not 2 <= len(users) <= MAX_LABEL_COALITION_SIZE or len(set(users)) != len(users):
        raise StageCContractError("exact Shapley reporting requires 2..4 unique users")
    if not set(users) <= set(complete_roster):
        raise StageCContractError("Shapley coalition users must be in the roster")
    expected = {
        frozenset(user for index, user in enumerate(users) if mask & (1 << index))
        for mask in range(1 << len(users))
    }
    if set(subset_values) != expected:
        raise StageCContractError("exact Shapley reporting requires every subset value")
    factorial = math.factorial
    count = len(users)
    credit = {user: 0.0 for user in complete_roster}
    for user in users:
        others = tuple(candidate for candidate in users if candidate != user)
        for mask in range(1 << len(others)):
            subset = frozenset(
                candidate for index, candidate in enumerate(others) if mask & (1 << index)
            )
            weight = (
                factorial(len(subset))
                * factorial(count - len(subset) - 1)
                / factorial(count)
            )
            credit[user] += weight * (
                float(subset_values[subset | {user}]) - float(subset_values[subset])
            )
    return credit


@dataclass(frozen=True, slots=True)
class CoalitionShard:
    path: Path
    file_sha256: str
    rows_sha256: str
    rows: tuple[CoalitionRow, ...]


def write_coalition_shard(path: str | Path, rows: Iterable[CoalitionRow]) -> CoalitionShard:
    material = tuple(rows)
    if not material:
        raise StageCContractError("cannot write an empty coalition shard")
    payloads = [row.payload() for row in material]
    rows_sha256 = canonical_sha256(payloads)
    header = {
        "schema": COALITION_SHARD_SCHEMA,
        "split": "TRAIN",
        "row_count": len(material),
        "rows_sha256": rows_sha256,
        "max_label_coalition_size": MAX_LABEL_COALITION_SIZE,
        "row_schema": COALITION_ROW_SCHEMA,
    }
    encoded = b"\n".join(canonical_json_bytes(value) for value in (header, *payloads)) + b"\n"
    destination = Path(path)
    digest = write_once_with_sha256(destination, encoded)
    return CoalitionShard(destination, digest, rows_sha256, material)


def _action(payload: Mapping[str, object]) -> PhysicalAction:
    return PhysicalAction(
        None if payload["norad_id"] is None else int(payload["norad_id"]),
        None if payload["beam_chain_id"] is None else int(payload["beam_chain_id"]),
    )


def _context(payload: Mapping[str, object]) -> CoalitionContext:
    if set(payload) != {
        "anchor_id",
        "reference_profile",
        "members",
        "affected_beams",
        "global_resource_features_hex",
    }:
        raise StageCContractError("coalition context schema drifted")
    for row in payload["reference_profile"]:
        if set(row) != {"user_id", "action"}:
            raise StageCContractError("coalition reference-profile schema drifted")
    for row in payload["members"]:
        if set(row) != {
            "user_id",
            "reference_action",
            "selected_action",
            "selected_q1_row_hex",
            "incumbent_q1_row_hex",
            "missing_incumbent",
        }:
            raise StageCContractError("coalition member schema drifted")
    for row in payload["affected_beams"]:
        if set(row) != {
            "beam_key",
            "occupancy_before",
            "occupancy_after",
            "active_before",
            "active_after",
            "shared_capacity_hex",
            "interference_summary_hex",
            "capacity_margin_hex",
        }:
            raise StageCContractError("affected-beam context schema drifted")
    return CoalitionContext(
        anchor_id=str(payload["anchor_id"]),
        reference_profile=tuple(
            (int(row["user_id"]), _action(row["action"])) for row in payload["reference_profile"]
        ),
        members=tuple(
            CoalitionMember(
                user_id=int(row["user_id"]),
                reference_action=_action(row["reference_action"]),
                selected_action=_action(row["selected_action"]),
                selected_q1_row=tuple(
                    parse_float_hex(value, field="selected_action_feature")
                    for value in row["selected_q1_row_hex"]
                ),
                incumbent_q1_row=tuple(
                    parse_float_hex(value, field="incumbent_action_feature")
                    for value in row["incumbent_q1_row_hex"]
                ),
                missing_incumbent=bool(row["missing_incumbent"]),
            )
            for row in payload["members"]
        ),
        affected_beams=tuple(
            AffectedBeamContext(
                beam_key=str(row["beam_key"]),
                occupancy_before=int(row["occupancy_before"]),
                occupancy_after=int(row["occupancy_after"]),
                active_before=bool(row["active_before"]),
                active_after=bool(row["active_after"]),
                shared_capacity=parse_float_hex(row["shared_capacity_hex"], field="shared_capacity"),
                interference_summary=parse_float_hex(row["interference_summary_hex"], field="interference"),
                capacity_margin=parse_float_hex(row["capacity_margin_hex"], field="capacity_margin"),
            )
            for row in payload["affected_beams"]
        ),
        global_resource_features=tuple(
            parse_float_hex(value, field="global_resource_feature")
            for value in payload["global_resource_features_hex"]
        ),
    )


def read_coalition_shard(path: str | Path) -> CoalitionShard:
    source = Path(path)
    digest = verify_sha256_sidecar(source)
    try:
        raw_lines = source.read_bytes().splitlines()
        values = [json.loads(line.decode("ascii")) for line in raw_lines]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StageCContractError("cannot parse coalition shard") from error
    if not values or values[0] != {
        "max_label_coalition_size": MAX_LABEL_COALITION_SIZE,
        "row_count": len(values) - 1,
        "row_schema": COALITION_ROW_SCHEMA,
        "rows_sha256": values[0].get("rows_sha256") if isinstance(values[0], dict) else None,
        "schema": COALITION_SHARD_SCHEMA,
        "split": "TRAIN",
    }:
        raise StageCContractError("coalition shard header drifted")
    if any(line != canonical_json_bytes(value) for line, value in zip(raw_lines, values, strict=True)):
        raise StageCContractError("coalition shard is not canonical JSONL")
    rows: list[CoalitionRow] = []
    for payload in values[1:]:
        if not isinstance(payload, Mapping) or set(payload) != set(CoalitionRow.__dataclass_fields__):
            raise StageCContractError("coalition row schema drifted")
        context = _context(payload["context"])
        scalar = {key: value for key, value in payload.items() if key != "context"}
        scalar["original_changed_users"] = tuple(
            int(user) for user in scalar["original_changed_users"]
        )
        rows.append(CoalitionRow(context=context, **scalar))
    material = tuple(rows)
    rows_sha256 = canonical_sha256([row.payload() for row in material])
    if rows_sha256 != values[0]["rows_sha256"]:
        raise StageCContractError("coalition shard row digest drifted")
    return CoalitionShard(source, digest, rows_sha256, material)


__all__ = [
    "AffectedBeamContext",
    "COALITION_ROW_SCHEMA",
    "COALITION_SHARD_SCHEMA",
    "CoalitionContext",
    "CoalitionMember",
    "CoalitionRow",
    "CoalitionShard",
    "MAX_LABEL_COALITION_SIZE",
    "build_coalition_row",
    "capped_coalition_decomposition",
    "exact_shapley_reporting_credit",
    "pair_reporting_credit",
    "read_coalition_shard",
    "write_coalition_shard",
]
