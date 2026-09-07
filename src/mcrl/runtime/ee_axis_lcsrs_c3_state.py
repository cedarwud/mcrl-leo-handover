"""Immutable V0.23 LC-SRS C3 learner view.

This is deliberately the Interface-A boundary, not the physical descriptor
encoder.  A capture adapter may assemble the declared predecision descriptors
into :class:`C3View`; this module copies, validates, freezes, and authenticates
those arrays without consulting an environment, an RNG, or a teacher result.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import struct

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError


LCSRS_C3_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-c3-view-v1"
LCSRS_C3_SCHEMA_VERSION = 1
LCSRS_ACTION_CONTEXT_DIM = 29
LCSRS_TOKEN_DIM = 38
LCSRS_ACTION_DIM = NUM_ACTIONS

LCSRS_ACTION_CONTEXT_FIELDS = (
    "focal_candidate_off_axis_rad_div_pi",
    "focal_candidate_slant_km_over_plus_earth_radius",
    "focal_candidate_elevation_deg_div_90",
    "focal_opening_feasible",
    "candidate_reference_same_sat_same_cell",
    "candidate_reference_same_sat_diff_cell_same_color",
    "candidate_reference_same_sat_diff_cell_diff_color",
    "candidate_reference_diff_sat_same_cell",
    "candidate_reference_diff_sat_diff_cell_same_color",
    "candidate_reference_diff_sat_diff_cell_diff_color",
    "candidate_equals_committed_incumbent",
    "committed_destination_load_div_u",
    "committed_destination_beam_active",
    "committed_destination_satellite_active",
    "committed_destination_rf_power_div_pmax",
    "committed_detached_source_load_div_u",
    "committed_detached_source_beam_active",
    "committed_detached_source_satellite_active",
    "committed_detached_source_rf_power_div_pmax",
    "committed_recurrence_power_div_pmax",
    "current_start_gain_ratio_over_plus_one",
    "segment_age_div_episode_length",
    "missing_committed_incumbent",
    "tanh_q12_candidate_minus_reference",
    "q12_descending_legal_rank_div_max_l_minus_one",
    "detached_source_occupancy_div_u",
    "detached_source_opening_feasible_load_div_u",
    "detached_destination_occupancy_div_u",
    "detached_destination_opening_feasible_load_div_u",
)

LCSRS_ORDINARY_TOKEN_FIELDS = (
    "token_type_ordinary",
    "token_type_pair",
    "victim_is_focal",
    "victim_is_partner",
    "victim_reference_equals_common_source",
    "victim_reference_equals_focal_destination",
    "victim_reference_equals_partner_destination",
    "victim_reference_opening_feasible",
    "victim_reference_occupancy_div_u",
    "victim_reference_opening_feasible_load_div_u",
    "victim_reference_off_axis_rad_div_pi",
    "victim_reference_slant_km_over_plus_earth_radius",
    "victim_reference_elevation_deg_div_90",
    "source_seen_by_victim_off_axis_rad_div_pi",
    "source_seen_by_victim_slant_km_over_plus_earth_radius",
    "source_seen_by_victim_elevation_deg_div_90",
    "focal_destination_seen_by_victim_off_axis_rad_div_pi",
    "focal_destination_seen_by_victim_slant_km_over_plus_earth_radius",
    "focal_destination_seen_by_victim_elevation_deg_div_90",
    "partner_destination_seen_by_victim_off_axis_rad_div_pi",
    "partner_destination_seen_by_victim_slant_km_over_plus_earth_radius",
    "partner_destination_seen_by_victim_elevation_deg_div_90",
    "source_victim_reference_cochannel",
    "focal_destination_victim_reference_cochannel",
    "partner_destination_victim_reference_cochannel",
    "source_equals_victim_reference",
    "focal_destination_equals_victim_reference",
    "partner_destination_equals_victim_reference",
    "focal_only_reference_load_delta_div_u",
    "joint_reference_load_delta_div_u",
    "focal_reference_opening_feasible",
    "focal_candidate_opening_feasible",
    "partner_designated_opening_feasible",
    "bounded_source_coupling_times_p0_div_noise",
    "bounded_focal_destination_coupling_times_p0_div_noise",
    "bounded_partner_destination_coupling_times_p0_div_noise",
    "bounded_victim_reference_wanted_signal_div_noise",
    "tanh_victim_q12_reference_minus_legal_mean",
)

LCSRS_PAIR_TOKEN_FIELDS = (
    "token_type_ordinary",
    "token_type_pair",
    "source_occupancy_exactly_two",
    "pair_supported",
    "current_cell_is_designated",
    "focal_designated_opening_feasible",
    "partner_designated_opening_feasible",
    "destinations_same_physical_key",
    "source_occupancy_div_u",
    "focal_destination_nonmember_occupancy_div_u",
    "partner_destination_nonmember_occupancy_div_u",
    "focal_destination_ready_nonmember_count_div_u",
    "partner_destination_ready_nonmember_count_div_u",
    "source_satellite_other_active_beams_div_cells",
    "focal_destination_satellite_other_active_beams_div_cells",
    "partner_destination_satellite_other_active_beams_div_cells",
    "committed_source_beam_active",
    "committed_focal_destination_beam_active",
    "committed_partner_destination_beam_active",
    "committed_source_rf_power_div_pmax",
    "committed_focal_destination_rf_power_div_pmax",
    "committed_partner_destination_rf_power_div_pmax",
    "committed_source_satellite_active",
    "committed_focal_destination_satellite_active",
    "committed_partner_destination_satellite_active",
    "partner_designated_off_axis_rad_div_pi",
    "partner_designated_slant_km_over_plus_earth_radius",
    "partner_designated_elevation_deg_div_90",
    "partner_destination_from_focal_off_axis_rad_div_pi",
    "partner_destination_from_focal_slant_km_over_plus_earth_radius",
    "partner_destination_from_focal_elevation_deg_div_90",
    "tanh_focal_q12_candidate_minus_reference",
    "tanh_partner_q12_candidate_minus_reference",
    "tanh_partner_destination_margin_minimum",
    "tanh_partner_destination_margin_maximum",
    "tanh_partner_destination_margin_mean",
    "tanh_focal_reference_q12",
    "tanh_partner_reference_q12",
)

if (
    len(LCSRS_ACTION_CONTEXT_FIELDS) != LCSRS_ACTION_CONTEXT_DIM
    or len(LCSRS_ORDINARY_TOKEN_FIELDS) != LCSRS_TOKEN_DIM
    or len(LCSRS_PAIR_TOKEN_FIELDS) != LCSRS_TOKEN_DIM
):  # pragma: no cover - import-time schema invariant
    raise RuntimeError("LC-SRS C3 feature-name tables disagree with frozen widths")


class LCSRSC3StateError(MCRLContractError):
    """The frozen LC-SRS Interface-A state does not meet its contract."""


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    ).hexdigest()


def _schema_payload() -> dict[str, object]:
    return {
        "schema": LCSRS_C3_SCHEMA,
        "schema_version": LCSRS_C3_SCHEMA_VERSION,
        "action_dim": LCSRS_ACTION_DIM,
        "action_context": "(U,28,29)-float32",
        "tokens": "(U,28,U+1,38)-float32",
        "token_mask": "(U,28,U+1)-bool",
        "action_mask": "(U,28)-bool-native-mask",
        "reference_actions": "(U,)-int64-detached-q12-reference",
        "action_context_fields": list(LCSRS_ACTION_CONTEXT_FIELDS),
        "ordinary_token_fields": list(LCSRS_ORDINARY_TOKEN_FIELDS),
        "pair_token_fields": list(LCSRS_PAIR_TOKEN_FIELDS),
        "ordinary_token_type": [1.0, 0.0],
        "pair_token_type": [0.0, 1.0],
        "pair_slot": "U",
        "transforms": {
            "signed_bounded": "x/(1+abs(x))",
            "nonnegative_bounded": "x/(1+x)",
            "distance": "d_km/(d_km+6371)",
            "angle": "theta_rad/pi",
            "elevation": "elevation_deg/90",
            "count": "count/U",
            "beam_count": "count/num_cells",
            "power": "power_w/pmax_w",
            "q12": "tanh(authenticated_normalized_value)",
        },
        "ordinary_mask": (
            "source-focal-destination-partner-destination exact-key-or-"
            "structural-cochannel union plus focal-and-partner"
        ),
        "sentinels": {
            "illegal_action": "all-zero-context-and-tokens",
            "no_partner_pair_status": [0.0, 0.0, 0.0],
            "unsupported_pair_status": [1.0, 0.0, 0.0],
            "missing_incumbent_temporal": [0.0, 0.0, 0.0, 1.0],
        },
        "forbidden": [
            "outcome",
            "rate",
            "energy",
            "post-action-state",
            "teacher-fading",
            "label",
            "future",
            "raw-identifier",
        ],
    }


def _config_payload() -> dict[str, object]:
    """The fixed Interface-C architecture bound to this state format."""

    return {
        "input_width": LCSRS_ACTION_CONTEXT_DIM + LCSRS_TOKEN_DIM,
        "layers": [67, 64, 64, 1],
        "activation": "relu",
        "aggregation": "masked-token-sum",
        "centering": "reference-action",
        "output_unit": "normalized-bits-per-kappa",
        "illegal_output": "zero",
        "q12": "detached-input-only",
    }


LCSRS_C3_SCHEMA_SHA256 = _canonical_sha256(_schema_payload())
LCSRS_C3_CONFIG_SHA256 = _canonical_sha256(_config_payload())


def _readonly(value: object, *, dtype: np.dtype) -> np.ndarray:
    try:
        result = np.array(value, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise LCSRSC3StateError("C3View array cannot be materialised") from error
    result.setflags(write=False)
    return result


def _digest_array(digest: "hashlib._Hash", name: str, value: np.ndarray) -> None:
    array = np.ascontiguousarray(value)
    digest.update(name.encode("ascii"))
    digest.update(b"\0")
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))


def _content_digest(
    action_context: np.ndarray,
    tokens: np.ndarray,
    token_mask: np.ndarray,
    action_mask: np.ndarray,
    reference_actions: np.ndarray,
    schema_version: int,
    schema_sha256: str,
    config_sha256: str,
) -> str:
    digest = hashlib.sha256()
    digest.update(LCSRS_C3_SCHEMA.encode("ascii"))
    digest.update(struct.pack(">I", schema_version))
    digest.update(schema_sha256.encode("ascii"))
    digest.update(config_sha256.encode("ascii"))
    for name, value in (
        ("action_context", action_context),
        ("tokens", tokens),
        ("token_mask", token_mask),
        ("action_mask", action_mask),
        ("reference_actions", reference_actions),
    ):
        _digest_array(digest, name, value)
    return digest.hexdigest()


@dataclass(frozen=True)
class C3View:
    """Versioned, immutable structured C3 input for exactly one anchor."""

    action_context: np.ndarray
    tokens: np.ndarray
    token_mask: np.ndarray
    action_mask: np.ndarray
    reference_actions: np.ndarray
    schema_version: int = LCSRS_C3_SCHEMA_VERSION
    schema_sha256: str = LCSRS_C3_SCHEMA_SHA256
    config_sha256: str = LCSRS_C3_CONFIG_SHA256
    content_digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "action_context",
            _readonly(self.action_context, dtype=np.dtype(np.float32)),
        )
        object.__setattr__(self, "tokens", _readonly(self.tokens, dtype=np.dtype(np.float32)))
        object.__setattr__(self, "token_mask", _readonly(self.token_mask, dtype=np.dtype(np.bool_)))
        object.__setattr__(
            self,
            "action_mask",
            _readonly(self.action_mask, dtype=np.dtype(np.bool_)),
        )
        object.__setattr__(
            self,
            "reference_actions",
            _readonly(self.reference_actions, dtype=np.dtype(np.int64)),
        )
        if self.content_digest == "":
            object.__setattr__(
                self,
                "content_digest",
                _content_digest(
                    self.action_context,
                    self.tokens,
                    self.token_mask,
                    self.action_mask,
                    self.reference_actions,
                    self.schema_version,
                    self.schema_sha256,
                    self.config_sha256,
                ),
            )
        self.verify()

    @property
    def schema(self) -> str:
        return LCSRS_C3_SCHEMA

    def verify(self) -> str:
        if type(self.schema_version) is not int or self.schema_version != LCSRS_C3_SCHEMA_VERSION:
            raise LCSRSC3StateError("unsupported LC-SRS C3View schema version")
        if self.schema_sha256 != LCSRS_C3_SCHEMA_SHA256:
            raise LCSRSC3StateError("LC-SRS C3View schema hash drifted")
        if self.config_sha256 != LCSRS_C3_CONFIG_SHA256:
            raise LCSRSC3StateError("LC-SRS C3View config hash drifted")

        contexts = np.asarray(self.action_context)
        tokens = np.asarray(self.tokens)
        token_mask = np.asarray(self.token_mask)
        action_mask = np.asarray(self.action_mask)
        references = np.asarray(self.reference_actions)
        if contexts.dtype != np.float32 or contexts.ndim != 3 or contexts.shape[1:] != (
            LCSRS_ACTION_DIM,
            LCSRS_ACTION_CONTEXT_DIM,
        ):
            raise LCSRSC3StateError("action_context must be float32 shape (U,28,29)")
        users = int(contexts.shape[0])
        if users < 1:
            raise LCSRSC3StateError("C3View requires at least one user")
        if tokens.dtype != np.float32 or tokens.shape != (
            users,
            LCSRS_ACTION_DIM,
            users + 1,
            LCSRS_TOKEN_DIM,
        ):
            raise LCSRSC3StateError("tokens must be float32 shape (U,28,U+1,38)")
        if token_mask.dtype != np.bool_ or token_mask.shape != (
            users,
            LCSRS_ACTION_DIM,
            users + 1,
        ):
            raise LCSRSC3StateError("token_mask must be Boolean shape (U,28,U+1)")
        if action_mask.dtype != np.bool_ or action_mask.shape != (users, LCSRS_ACTION_DIM):
            raise LCSRSC3StateError("action_mask must be Boolean shape (U,28)")
        if references.dtype != np.int64 or references.shape != (users,):
            raise LCSRSC3StateError("reference_actions must be int64 shape (U,)")
        if not np.all(np.isfinite(contexts)) or not np.all(np.isfinite(tokens)):
            raise LCSRSC3StateError("C3View feature arrays must be finite")
        if np.any(~np.any(action_mask, axis=1)):
            raise LCSRSC3StateError("each C3View user needs a legal action")
        if np.any(references < 0) or np.any(references >= LCSRS_ACTION_DIM):
            raise LCSRSC3StateError("reference action is out of range")
        if not np.all(action_mask[np.arange(users), references]):
            raise LCSRSC3StateError("every reference action must be legal")
        if not np.array_equal(token_mask[:, :, users], action_mask):
            raise LCSRSC3StateError("every legal cell must have exactly one pair token")
        if np.any(token_mask[:, :, :users] & ~action_mask[:, :, None]):
            raise LCSRSC3StateError("ordinary token mask cannot widen the native action mask")
        if np.any(contexts[~action_mask] != 0.0) or np.any(tokens[~action_mask] != 0.0):
            raise LCSRSC3StateError("illegal action rows and tokens must be zero")
        if np.any(tokens[~token_mask] != 0.0):
            raise LCSRSC3StateError("masked token slots must be zero")
        tolerance = np.float32(1.0 + 32.0 * np.finfo(np.float32).eps)
        if np.any(np.abs(contexts[action_mask]) > tolerance) or np.any(
            np.abs(tokens[token_mask]) > tolerance
        ):
            raise LCSRSC3StateError("bounded C3View features must lie in [-1,1]")

        context_binary = contexts[:, :, [3, *range(4, 11), 12, 13, 16, 17, 22]]
        context_binary = context_binary[action_mask]
        if np.any((context_binary != 0.0) & (context_binary != 1.0)):
            raise LCSRSC3StateError("declared Boolean action-context fields must be binary")
        relation = contexts[:, :, 4:10][action_mask]
        if np.any(np.sum(relation, axis=1) > 1.0):
            raise LCSRSC3StateError("candidate/reference relation must be one-hot or absent")

        ordinary = token_mask[:, :, :users]
        if np.any(tokens[:, :, :users, 0][ordinary] != 1.0) or np.any(
            tokens[:, :, :users, 1][ordinary] != 0.0
        ):
            raise LCSRSC3StateError("ordinary tokens must carry type [1,0]")
        ordinary_values = tokens[:, :, :users, :]
        ordinary_binary = ordinary_values[:, :, :, [*range(0, 8), *range(22, 28), *range(30, 33)]]
        ordinary_binary = ordinary_binary[ordinary]
        if np.any((ordinary_binary != 0.0) & (ordinary_binary != 1.0)):
            raise LCSRSC3StateError("declared Boolean ordinary-token fields must be binary")
        pair = tokens[:, :, users, :]
        if np.any(pair[:, :, 0][action_mask] != 0.0) or np.any(
            pair[:, :, 1][action_mask] != 1.0
        ):
            raise LCSRSC3StateError("pair tokens must carry type [0,1]")
        status = pair[:, :, 2:5]
        legal_status = status[action_mask]
        if np.any((legal_status != 0.0) & (legal_status != 1.0)):
            raise LCSRSC3StateError("pair status fields must be exact binary sentinels")
        pair_binary = pair[:, :, [*range(0, 8), *range(16, 19), *range(22, 25)]]
        pair_binary = pair_binary[action_mask]
        if np.any((pair_binary != 0.0) & (pair_binary != 1.0)):
            raise LCSRSC3StateError("declared Boolean pair-token fields must be binary")
        if np.any(legal_status[:, 1] > legal_status[:, 0]) or np.any(
            legal_status[:, 2] > legal_status[:, 1]
        ):
            raise LCSRSC3StateError("pair status sentinels are inconsistent")
        no_partner = action_mask & (status[:, :, 0] == 0.0)
        unsupported = action_mask & (status[:, :, 0] == 1.0) & (status[:, :, 1] == 0.0)
        if np.any(pair[no_partner, 2:] != 0.0) or np.any(pair[unsupported, 5:] != 0.0):
            raise LCSRSC3StateError("unsupported pair token sentinel must be zero-filled")

        arrays = (contexts, tokens, token_mask, action_mask, references)
        if any(array.flags.writeable for array in arrays):
            raise LCSRSC3StateError("C3View arrays must be immutable")
        expected = _content_digest(
            contexts,
            tokens,
            token_mask,
            action_mask,
            references,
            self.schema_version,
            self.schema_sha256,
            self.config_sha256,
        )
        if self.content_digest != expected:
            raise LCSRSC3StateError("C3View content digest disagrees with arrays")
        return expected


def assemble_c3_view(
    *,
    action_context: object,
    tokens: object,
    token_mask: object,
    action_mask: object,
    reference_actions: object,
) -> C3View:
    """Purely assemble and authenticate already-captured Interface-A arrays.

    A physical encoder adapter is intentionally not provided here: callers must
    supply the contract-ordered, predecision-only descriptors explicitly.
    """

    return C3View(
        action_context=action_context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=action_mask,
        reference_actions=reference_actions,
    )


__all__ = [
    "LCSRS_C3_SCHEMA",
    "LCSRS_C3_SCHEMA_VERSION",
    "LCSRS_C3_SCHEMA_SHA256",
    "LCSRS_C3_CONFIG_SHA256",
    "LCSRS_ACTION_DIM",
    "LCSRS_ACTION_CONTEXT_DIM",
    "LCSRS_ACTION_CONTEXT_FIELDS",
    "LCSRS_TOKEN_DIM",
    "LCSRS_ORDINARY_TOKEN_FIELDS",
    "LCSRS_PAIR_TOKEN_FIELDS",
    "LCSRSC3StateError",
    "C3View",
    "assemble_c3_view",
]
