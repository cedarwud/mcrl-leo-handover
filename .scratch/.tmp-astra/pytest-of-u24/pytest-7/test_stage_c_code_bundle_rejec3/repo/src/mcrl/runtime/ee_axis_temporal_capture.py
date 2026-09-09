"""Pre-forecast capture and post-forecast materialization for C2/Q2.

The real C2 backend owns simulator execution.  This module is the small
bridge that turns one prepared backend fork into the current V0.3 temporal
pair contract.  It deliberately has a two-phase API:

``capture_temporal_anchor``
    must be called while the prepared fork is still at its anchor, before
    ``run_forecast``.  It records the 228-dimensional focal state, mask, and
    the physical-to-slot mapping from the *current* ``SlotTable``.

``materialize_temporal_pair``
    may be called only after the same prepared fork has completed its
    detached forecast.  It checks that the live anchor did not become stale,
    extracts complete offsets 0..3 from the two raw traces, and delegates all
    final formula, provenance, and digest validation to ``build_temporal_pair``.

The helper is intentionally duck-typed at the C2 boundary.  The production
backend lives under ``.scratch/c2-v03`` and is not imported by the package;
only its stable prepared-anchor/forecast fields are required here.  No gate
JSON is read, rewritten, or relabelled.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import math
from typing import Any

import numpy as np

from ..env.action_contract import NUM_ACTIONS, SlotTable
from ..errors import MCRLContractError
from .ee_axis_state import (
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
    EEAxisStateObservation,
    encode_ee_axis_state,
)
from .ee_axis_temporal_pairs import (
    TEMPORAL_DOWNSTREAM_OFFSETS,
    TEMPORAL_HORIZON_STEPS,
    C2_POLICY_VERSION,
    EEAxisTemporalPair,
    build_temporal_pair,
)


KEYED_FADING_MODE = "keyed-branch-independent-v1"
"""The only fading mode admitted by the current C2 pilot capture seam."""


class TemporalCaptureContractError(MCRLContractError):
    """The live C2 capture is malformed, stale, or out of sequence."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TemporalCaptureContractError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _integer(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise TemporalCaptureContractError(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _finite(value: object, *, field: str, positive: bool = False) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.number)
    ):
        raise TemporalCaptureContractError(f"{field} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted) or (positive and converted <= 0.0):
        qualifier = "positive finite" if positive else "finite"
        raise TemporalCaptureContractError(f"{field} must be {qualifier}")
    return converted


def _physical_key(value: object, *, field: str) -> tuple[int, int]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise TemporalCaptureContractError(
            f"{field} must be a two-integer physical key"
        )
    return (
        _integer(value[0], field=f"{field}.norad"),
        _integer(value[1], field=f"{field}.cell"),
    )


def _copy_readonly(
    value: object,
    *,
    field: str,
    dtype: np.dtype[Any],
    shape: tuple[int, ...],
) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != shape:
        raise TemporalCaptureContractError(
            f"{field} must have shape {shape}, got {raw.shape}"
        )
    try:
        copied = np.array(raw, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError) as error:
        raise TemporalCaptureContractError(f"{field} has an invalid dtype") from error
    if np.issubdtype(copied.dtype, np.floating) and not np.all(np.isfinite(copied)):
        raise TemporalCaptureContractError(f"{field} must be finite")
    copied.setflags(write=False)
    return copied


def _attr(value: object, name: str, *, field: str | None = None) -> Any:
    if not hasattr(value, name):
        label = field or type(value).__name__
        raise TemporalCaptureContractError(f"{label} lacks required field {name}")
    return getattr(value, name)


def _anchor_from_prepared(prepared: object) -> object:
    anchor = _attr(prepared, "anchor", field="prepared fork")
    _attr(anchor, "wrapped", field="C2 anchor")
    _attr(anchor, "observation", field="C2 anchor")
    _attr(anchor, "focal_user", field="C2 anchor")
    _attr(anchor, "main_actions", field="C2 anchor")
    _attr(anchor, "anchor_sha256", field="C2 anchor")
    _attr(anchor, "evaluation_seed", field="C2 anchor")
    _attr(anchor, "checkpoint_sha256", field="C2 anchor")
    _attr(anchor, "environment_source_sha256", field="C2 anchor")
    _attr(anchor, "reward_source_sha256", field="C2 anchor")
    return anchor


def _prepared_phase(prepared: object) -> str:
    gate = _attr(prepared, "gate", field="prepared fork")
    phase = _attr(gate, "phase", field="C2 chronology gate")
    if not isinstance(phase, str):
        raise TemporalCaptureContractError("C2 chronology phase must be a string")
    return phase


def _current_state(anchor: object) -> EEAxisStateObservation:
    wrapped = _attr(anchor, "wrapped", field="C2 anchor")
    environment = _attr(wrapped, "environment", field="C2 wrapped anchor")
    observation = _attr(anchor, "observation", field="C2 anchor")
    try:
        state = encode_ee_axis_state(environment, observation)
        state.verify()
    except MCRLContractError as error:
        raise TemporalCaptureContractError(str(error)) from error
    if state.state_matrix.shape[1] != EE_AXIS_STATE_DIM:
        raise TemporalCaptureContractError("current anchor is not a 228-D V0.3 state")
    return state


def _slot_table(anchor: object, *, focal_user: int) -> SlotTable:
    observation = _attr(anchor, "observation", field="C2 anchor")
    candidates = _attr(observation, "candidates", field="C2 observation")
    tables = _attr(candidates, "slot_tables", field="C2 candidates")
    if not isinstance(tables, Sequence) or focal_user >= len(tables):
        raise TemporalCaptureContractError(
            "C2 focal user is outside the current slot tables"
        )
    table = tables[focal_user]
    if not isinstance(table, SlotTable):
        raise TemporalCaptureContractError(
            "current focal candidate table is not a SlotTable"
        )
    return table


def _physical_at(table: SlotTable, action: int, *, field: str) -> tuple[int, int]:
    if not 0 <= action < NUM_ACTIONS or not bool(table.mask[action]):
        raise TemporalCaptureContractError(
            f"{field} is not legal in the current action mask"
        )
    try:
        association = table.association(action)
    except Exception as error:
        raise TemporalCaptureContractError(
            f"{field} is not bound by the current slot table"
        ) from error
    if not hasattr(association, "norad_id") or not hasattr(association, "cell_id"):
        raise TemporalCaptureContractError(f"{field} has no physical association")
    return _physical_key(
        (int(association.norad_id), int(association.cell_id)), field=field
    )


def _unique_action_for_physical(
    table: SlotTable, physical_key: tuple[int, int], *, field: str
) -> int:
    matches: list[int] = []
    for action in np.flatnonzero(table.mask).tolist():
        bound = _physical_at(table, int(action), field=f"{field}[{action}]")
        if bound == physical_key:
            matches.append(int(action))
    if len(matches) != 1:
        reason = "missing" if not matches else "non-unique"
        raise TemporalCaptureContractError(
            f"{field} physical key has {reason} slot mapping (matches={matches})"
        )
    return matches[0]


def _trace_sequence(prepared: object, name: str) -> tuple[object, ...]:
    trace = _attr(prepared, name, field="prepared fork")
    if isinstance(trace, (str, bytes)):
        raise TemporalCaptureContractError(f"{name} must be a trace sequence")
    try:
        values = tuple(trace)
    except TypeError as error:
        raise TemporalCaptureContractError(f"{name} must be a trace sequence") from error
    expected = tuple(range(TEMPORAL_HORIZON_STEPS))
    offsets = tuple(
        _integer(_attr(step, "offset", field=name), field=f"{name}.offset")
        for step in values
    )
    if offsets != expected:
        raise TemporalCaptureContractError(
            f"{name} must contain complete ordered offsets 0..3, got {offsets}"
        )
    return values


def _trace_arrays(
    trace: tuple[object, ...], *, field: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rates_rows: list[list[float]] = []
    power_rows: list[float] = []
    served_rows: list[list[bool]] = []
    users: int | None = None
    for offset, step in enumerate(trace):
        raw_rates = _attr(step, "link_rate_bps", field=f"{field}[{offset}]")
        raw_served = _attr(step, "served", field=f"{field}[{offset}]")
        try:
            rates = [
                _finite(
                    value,
                    field=f"{field}[{offset}].link_rate_bps",
                    positive=False,
                )
                for value in raw_rates
            ]
            served = []
            for index, value in enumerate(raw_served):
                if type(value) not in (bool, np.bool_):
                    raise TemporalCaptureContractError(
                        f"{field}[{offset}].served[{index}] must be Boolean"
                    )
                served.append(bool(value))
        except (TypeError, ValueError) as error:
            raise TemporalCaptureContractError(
                f"{field}[{offset}] rate/served vectors are malformed"
            ) from error
        if not rates or len(rates) != len(served):
            raise TemporalCaptureContractError(
                f"{field}[{offset}] rate/served vectors disagree"
            )
        if any(value < 0.0 for value in rates):
            raise TemporalCaptureContractError(
                f"{field}[{offset}].link_rate_bps must be nonnegative"
            )
        if users is None:
            users = len(rates)
        elif len(rates) != users:
            raise TemporalCaptureContractError(f"{field} user width changes across offsets")
        rates_rows.append(rates)
        served_rows.append(served)
        power_rows.append(
            _finite(
                _attr(step, "system_power_w", field=f"{field}[{offset}]"),
                field=f"{field}[{offset}].system_power_w",
                positive=True,
            )
        )
    assert users is not None  # trace length is checked by _trace_sequence
    return (
        np.asarray(rates_rows, dtype=np.float64),
        np.asarray(power_rows, dtype=np.float64),
        np.asarray(served_rows, dtype=np.bool_),
    )


def _support_metadata(
    candidate_trace: tuple[object, ...], *, candidate_key: tuple[int, int]
) -> tuple[tuple[int, ...], int, str]:
    counts: list[int] = []
    release_offsets: list[int] = []
    release_reasons: list[str] = []
    for offset, step in enumerate(candidate_trace):
        held = _attr(step, "held_physical_key", field=f"candidate_trace[{offset}]")
        if held is None:
            raise TemporalCaptureContractError(
                f"candidate trace offset {offset} lacks held physical key"
            )
        if (
            _physical_key(
                tuple(held), field=f"candidate_trace[{offset}].held_physical_key"
            )
            != candidate_key
        ):
            raise TemporalCaptureContractError("candidate trace held key disagrees with captured key")
        count = _attr(step, "held_key_match_count", field=f"candidate_trace[{offset}]")
        counts.append(
            _integer(
                count,
                field=f"candidate_trace[{offset}].held_key_match_count",
            )
        )
        release_offset = _attr(step, "release_offset", field=f"candidate_trace[{offset}]")
        release_reason = _attr(step, "release_reason", field=f"candidate_trace[{offset}]")
        release_offsets.append(
            _integer(
                release_offset,
                field=f"candidate_trace[{offset}].release_offset",
                minimum=1,
            )
        )
        if not isinstance(release_reason, str) or not release_reason:
            raise TemporalCaptureContractError("candidate trace release reason is missing")
        release_reasons.append(release_reason)
    if len(set(release_offsets)) != 1 or len(set(release_reasons)) != 1:
        raise TemporalCaptureContractError("candidate trace release metadata is inconsistent")
    release_offset = release_offsets[0]
    release_reason = release_reasons[0]
    if not 1 <= release_offset < TEMPORAL_HORIZON_STEPS:
        raise TemporalCaptureContractError(
            "candidate trace release offset must be within 1..3"
        )
    return tuple(counts), release_offset, release_reason


@dataclass(frozen=True)
class C2TemporalAnchorCapture:
    """Immutable pre-forecast focal state and physical slot snapshot."""

    anchor_sha256: str
    anchor_schedule_sha256: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    environment_source_sha256: str
    reward_source_sha256: str
    seed: int
    step_index: int
    focal_user: int
    state_schema: str
    state_schema_sha256: str
    state_observation_sha256: str
    state: np.ndarray
    action_mask: np.ndarray
    reference_action: int
    candidate_action: int
    reference_physical_key: tuple[int, int]
    candidate_physical_key: tuple[int, int]
    _prepared: object = field(repr=False, compare=False)
    _observation: object = field(repr=False, compare=False)

    def verify(self) -> None:
        _digest(self.anchor_sha256, field="anchor_sha256")
        _digest(self.anchor_schedule_sha256, field="anchor_schedule_sha256")
        _digest(self.source_manifest_sha256, field="source_manifest_sha256")
        _digest(self.checkpoint_sha256, field="checkpoint_sha256")
        _digest(self.environment_source_sha256, field="environment_source_sha256")
        _digest(self.reward_source_sha256, field="reward_source_sha256")
        _integer(self.seed, field="seed")
        _integer(self.step_index, field="step_index")
        _integer(self.focal_user, field="focal_user")
        if self.state_schema != EE_AXIS_STATE_SCHEMA:
            raise TemporalCaptureContractError("captured state schema is stale")
        if self.state_schema_sha256 != EE_AXIS_STATE_SCHEMA_SHA256:
            raise TemporalCaptureContractError("captured state schema digest drifted")
        _digest(self.state_observation_sha256, field="state_observation_sha256")
        if (
            np.asarray(self.state).dtype != np.dtype(np.float32)
            or np.asarray(self.state).shape != (EE_AXIS_STATE_DIM,)
        ):
            raise TemporalCaptureContractError(
                "captured focal state must be immutable float32 shape (228,)"
            )
        if np.asarray(self.state).flags.writeable:
            raise TemporalCaptureContractError("captured focal state must be immutable")
        if (
            np.asarray(self.action_mask).dtype != np.bool_
            or np.asarray(self.action_mask).shape != (NUM_ACTIONS,)
        ):
            raise TemporalCaptureContractError(
                "captured action mask must be immutable Boolean shape (28,)"
            )
        if np.asarray(self.action_mask).flags.writeable:
            raise TemporalCaptureContractError("captured action mask must be immutable")
        _integer(self.reference_action, field="reference_action")
        _integer(self.candidate_action, field="candidate_action")
        if (
            not 0 <= self.reference_action < NUM_ACTIONS
            or not 0 <= self.candidate_action < NUM_ACTIONS
        ):
            raise TemporalCaptureContractError(
                "captured action slot is outside the action space"
            )
        if self.reference_action == self.candidate_action:
            raise TemporalCaptureContractError("captured reference and candidate slots must differ")
        _physical_key(self.reference_physical_key, field="reference_physical_key")
        _physical_key(self.candidate_physical_key, field="candidate_physical_key")


def capture_temporal_anchor(
    prepared: object,
    *,
    anchor_schedule_sha256: str,
    source_manifest_sha256: str,
) -> C2TemporalAnchorCapture:
    """Capture the current 228-D anchor before any detached forecast runs."""

    if _prepared_phase(prepared) != "anchor":
        raise TemporalCaptureContractError(
            "temporal anchor must be captured before C2 forecast starts"
        )
    build = _attr(prepared, "build", field="prepared fork")
    if build is not None:
        raise TemporalCaptureContractError(
            "prepared C2 fork already has a forecast build"
        )
    for trace_name in ("candidate_trace", "reference_trace"):
        trace = _attr(prepared, trace_name, field="prepared fork")
        try:
            trace_values = tuple(trace)
        except TypeError as error:
            raise TemporalCaptureContractError(
                f"{trace_name} must be a trace sequence"
            ) from error
        if trace_values:
            raise TemporalCaptureContractError(
                "prepared C2 fork already contains forecast trace data"
            )
    _digest(anchor_schedule_sha256, field="anchor_schedule_sha256")
    _digest(source_manifest_sha256, field="source_manifest_sha256")
    anchor = _anchor_from_prepared(prepared)
    observation = _attr(anchor, "observation", field="C2 anchor")
    focal_user = _integer(
        _attr(anchor, "focal_user", field="C2 anchor"), field="focal_user"
    )
    if focal_user >= int(_attr(observation, "num_users", field="C2 observation")):
        raise TemporalCaptureContractError(
            "focal user is outside the current observation"
        )
    state_observation = _current_state(anchor)
    state = _copy_readonly(
        state_observation.state_matrix[focal_user],
        field="captured focal state",
        dtype=np.dtype(np.float32),
        shape=(EE_AXIS_STATE_DIM,),
    )
    action_mask = _copy_readonly(
        state_observation.action_masks[focal_user],
        field="captured focal action mask",
        dtype=np.dtype(np.bool_),
        shape=(NUM_ACTIONS,),
    )
    table = _slot_table(anchor, focal_user=focal_user)
    main_actions = _attr(anchor, "main_actions", field="C2 anchor")
    try:
        reference_action = int(main_actions[focal_user])
    except (IndexError, TypeError, ValueError) as error:
        raise TemporalCaptureContractError("C2 anchor has no focal Main action slot") from error
    reference_key = _physical_at(table, reference_action, field="reference_action")
    candidate_key = _physical_key(
        tuple(_attr(prepared, "candidate_key", field="prepared fork")),
        field="prepared.candidate_key",
    )
    candidate_action = _unique_action_for_physical(
        table, candidate_key, field="prepared.candidate_key"
    )
    if reference_key == candidate_key:
        raise TemporalCaptureContractError(
            "prepared candidate equals the opening Main physical action"
        )
    if not bool(action_mask[reference_action]) or not bool(action_mask[candidate_action]):
        raise TemporalCaptureContractError(
            "captured action slots disagree with the current mask"
        )
    capture = C2TemporalAnchorCapture(
        anchor_sha256=_digest(
            _attr(anchor, "anchor_sha256", field="C2 anchor"),
            field="anchor_sha256",
        ),
        anchor_schedule_sha256=anchor_schedule_sha256,
        source_manifest_sha256=source_manifest_sha256,
        checkpoint_sha256=_digest(
            _attr(anchor, "checkpoint_sha256", field="C2 anchor"),
            field="checkpoint_sha256",
        ),
        environment_source_sha256=_digest(
            _attr(anchor, "environment_source_sha256", field="C2 anchor"),
            field="environment_source_sha256",
        ),
        reward_source_sha256=_digest(
            _attr(anchor, "reward_source_sha256", field="C2 anchor"),
            field="reward_source_sha256",
        ),
        seed=_integer(
            _attr(anchor, "evaluation_seed", field="C2 anchor"), field="seed"
        ),
        step_index=_integer(
            _attr(observation, "step_index", field="C2 observation"),
            field="step_index",
        ),
        focal_user=focal_user,
        state_schema=state_observation.schema,
        state_schema_sha256=state_observation.schema_sha256,
        state_observation_sha256=state_observation.state_sha256,
        state=state,
        action_mask=action_mask,
        reference_action=reference_action,
        candidate_action=candidate_action,
        reference_physical_key=reference_key,
        candidate_physical_key=candidate_key,
        _prepared=prepared,
        _observation=observation,
    )
    capture.verify()
    return capture


def _field_receipt(prepared: object) -> str:
    receipt = _attr(prepared, "forecast_rng_state", field="prepared fork")
    if not isinstance(receipt, Mapping):
        raise TemporalCaptureContractError("forecast RNG receipt is missing")
    fading = receipt.get("fading_field_receipt")
    if not isinstance(fading, Mapping) or fading.get("mode") != KEYED_FADING_MODE:
        raise TemporalCaptureContractError(
            "C2 pilot requires a keyed common-random field receipt"
        )
    return _digest(fading.get("root_digest"), field="common_random_field_sha256")


def materialize_temporal_pair(
    capture: C2TemporalAnchorCapture,
    prepared: object,
    *,
    anchor_schedule_sha256: str | None = None,
    lambda_bits_per_j: float,
    interval_s: float,
) -> EEAxisTemporalPair:
    """Build one Q2 pair from the same fork after a complete forecast."""

    if not isinstance(capture, C2TemporalAnchorCapture):
        raise TemporalCaptureContractError("capture must be C2TemporalAnchorCapture")
    capture.verify()
    if capture._prepared is not prepared:
        raise TemporalCaptureContractError(
            "capture and prepared fork do not share identity"
        )
    if _prepared_phase(prepared) != "forecast_complete":
        raise TemporalCaptureContractError(
            "temporal pair requires a completed detached forecast"
        )
    build = _attr(prepared, "build", field="prepared fork")
    if build is None:
        raise TemporalCaptureContractError("completed C2 fork lacks its forecast build")
    anchor = _anchor_from_prepared(prepared)
    observation = _attr(anchor, "observation", field="C2 anchor")
    if (
        _attr(observation, "step_index", field="C2 observation")
        != capture.step_index
    ):
        raise TemporalCaptureContractError("C2 anchor step changed after capture")
    if _attr(anchor, "observation", field="C2 anchor") is not capture._observation:
        raise TemporalCaptureContractError(
            "C2 anchor observation was replaced after capture"
        )
    current = _current_state(anchor)
    if current.state_sha256 != capture.state_observation_sha256:
        raise TemporalCaptureContractError(
            "captured C2 state is stale at forecast completion"
        )
    if (
        not np.array_equal(current.state_matrix[capture.focal_user], capture.state)
        or not np.array_equal(
            current.action_masks[capture.focal_user], capture.action_mask
        )
    ):
        raise TemporalCaptureContractError(
            "captured focal state or mask changed before pair materialization"
        )
    table = _slot_table(anchor, focal_user=capture.focal_user)
    if (
        _unique_action_for_physical(
            table, capture.candidate_physical_key, field="captured candidate key"
        )
        != capture.candidate_action
    ):
        raise TemporalCaptureContractError(
            "captured candidate slot is stale or no longer unique"
        )
    if (
        _physical_at(
            table, capture.reference_action, field="captured reference action"
        )
        != capture.reference_physical_key
    ):
        raise TemporalCaptureContractError("captured reference slot is stale")
    if (
        anchor_schedule_sha256 is not None
        and anchor_schedule_sha256 != capture.anchor_schedule_sha256
    ):
        raise TemporalCaptureContractError(
            "anchor schedule digest disagrees with pre-forecast capture"
        )

    reference_trace = _trace_sequence(prepared, "reference_trace")
    candidate_trace = _trace_sequence(prepared, "candidate_trace")
    reference_rates, reference_power, reference_served = _trace_arrays(
        reference_trace, field="reference_trace"
    )
    candidate_rates, candidate_power, candidate_served = _trace_arrays(
        candidate_trace, field="candidate_trace"
    )
    if (
        reference_rates.shape != candidate_rates.shape
        or reference_served.shape != candidate_served.shape
    ):
        raise TemporalCaptureContractError("matched C2 trace user axes disagree")
    expected_users = int(_attr(observation, "num_users", field="C2 observation"))
    if reference_rates.shape[1] != expected_users:
        raise TemporalCaptureContractError(
            "C2 trace user axis disagrees with the captured anchor"
        )
    counts, release_offset, release_reason = _support_metadata(
        candidate_trace, candidate_key=capture.candidate_physical_key
    )
    authority = _attr(build, "authority", field="forecast build")
    certificate = _attr(build, "certificate", field="forecast build")
    if (
        _attr(certificate, "version", field="forecast certificate")
        != C2_POLICY_VERSION
    ):
        raise TemporalCaptureContractError("forecast certificate uses a stale C2 policy")
    if (
        _attr(certificate, "reference_action", field="forecast certificate")
        != capture.reference_action
        or _attr(certificate, "candidate_action", field="forecast certificate")
        != capture.candidate_action
    ):
        raise TemporalCaptureContractError(
            "forecast certificate action slots disagree with capture"
        )
    if (
        tuple(_attr(certificate, "reference_key", field="forecast certificate"))
        != capture.reference_physical_key
        or tuple(_attr(certificate, "candidate_key", field="forecast certificate"))
        != capture.candidate_physical_key
    ):
        raise TemporalCaptureContractError(
            "forecast certificate physical keys disagree with capture"
        )
    if (
        _attr(certificate, "release_offset", field="forecast certificate")
        != release_offset
        or _attr(certificate, "release_reason", field="forecast certificate")
        != release_reason
    ):
        raise TemporalCaptureContractError(
            "forecast certificate release metadata disagrees with trace"
        )
    if (
        _attr(authority, "anchor_sha256", field="forecast authority")
        != capture.anchor_sha256
    ):
        raise TemporalCaptureContractError("forecast authority anchor disagrees with capture")
    if (
        _attr(authority, "reference_checkpoint_sha256", field="forecast authority")
        != capture.checkpoint_sha256
    ):
        raise TemporalCaptureContractError(
            "forecast checkpoint disagrees with capture"
        )
    if (
        _attr(authority, "environment_source_sha256", field="forecast authority")
        != capture.environment_source_sha256
        or _attr(authority, "reward_source_sha256", field="forecast authority")
        != capture.reward_source_sha256
    ):
        raise TemporalCaptureContractError(
            "forecast source digests disagree with capture"
        )
    reference_trace_sha256 = _digest(
        _attr(build, "reference_trace_sha256", field="forecast build"),
        field="reference_trace_sha256",
    )
    candidate_trace_sha256 = _digest(
        _attr(build, "candidate_trace_sha256", field="forecast build"),
        field="candidate_trace_sha256",
    )
    forecast_payload_sha256 = _digest(
        _attr(build, "forecast_payload_sha256", field="forecast build"),
        field="forecast_payload_sha256",
    )
    if (
        _attr(authority, "forecast_payload_sha256", field="forecast authority")
        != forecast_payload_sha256
    ):
        raise TemporalCaptureContractError(
            "forecast authority payload digest disagrees with build"
        )
    interval = _finite(interval_s, field="interval_s", positive=True)
    multiplier = _finite(lambda_bits_per_j, field="lambda_bits_per_j", positive=True)
    delta_rates = candidate_rates - reference_rates
    offset_surplus = np.asarray(
        [
            interval * math.fsum(float(value) for value in delta_rates[offset])
            - multiplier
            * interval
            * float(candidate_power[offset] - reference_power[offset])
            for offset in TEMPORAL_DOWNSTREAM_OFFSETS
        ],
        dtype=np.float64,
    )
    zeta2 = float(math.fsum(float(value) for value in offset_surplus))
    try:
        pair = build_temporal_pair(
            c2_policy_version=C2_POLICY_VERSION,
            source_rule=_attr(prepared, "source_rule", field="prepared fork"),
            anchor_sha256=capture.anchor_sha256,
            anchor_schedule_sha256=capture.anchor_schedule_sha256,
            seed=capture.seed,
            step_index=capture.step_index,
            source_manifest_sha256=capture.source_manifest_sha256,
            checkpoint_sha256=capture.checkpoint_sha256,
            common_random_field_sha256=_field_receipt(prepared),
            forecast_payload_sha256=forecast_payload_sha256,
            reference_trace_sha256=reference_trace_sha256,
            candidate_trace_sha256=candidate_trace_sha256,
            state_schema=capture.state_schema,
            state_schema_sha256=capture.state_schema_sha256,
            state_observation_sha256=capture.state_observation_sha256,
            focal_user=capture.focal_user,
            state=capture.state,
            action_mask=capture.action_mask,
            reference_action=capture.reference_action,
            candidate_action=capture.candidate_action,
            held_physical_key=capture.candidate_physical_key,
            held_key_match_counts=counts,
            release_offset=release_offset,
            release_reason=release_reason,
            reference_rates_bps=reference_rates,
            candidate_rates_bps=candidate_rates,
            reference_system_power_w=reference_power,
            candidate_system_power_w=candidate_power,
            reference_served=reference_served,
            candidate_served=candidate_served,
            lambda_bits_per_j=multiplier,
            interval_s=interval,
            offset_surplus_bits=offset_surplus,
            zeta2_temporal_surplus_bits=zeta2,
        )
        pair.verify()
    except MCRLContractError as error:
        raise TemporalCaptureContractError(str(error)) from error
    return pair


__all__ = [
    "C2TemporalAnchorCapture",
    "KEYED_FADING_MODE",
    "TemporalCaptureContractError",
    "capture_temporal_anchor",
    "materialize_temporal_pair",
]
