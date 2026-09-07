"""Production source bridge for the provisional V0.18 relational-Q3 seam.

This module only closes the source boundary.  It does not choose worlds,
lineages, thresholds, or a learner contract, and it never starts a simulator.
The canonical anchor order is deliberately explicit:

1. call the existing V0.18 ``encode_relational_zr_c3_state``;
2. copy and authenticate that predecision observation; and only then
3. ask a caller-supplied exact-ZR teacher adapter for the native-bit target.

Only the nominal relational tensors and the exact-ZR target surface are
written.  No exact measurement object, realised outcome, or other teacher
payload can cross the source-file boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile

import numpy as np

from mcrl.runtime.ee_axis_relational_zr_c3 import (
    RELATIONAL_ZR_C3_SCHEMA,
    RELATIONAL_ZR_C3_SCHEMA_SHA256,
    RELATIONAL_ZR_C3_SCHEMA_VERSION,
    RelationalZRC3Observation,
    _content_digest as _relational_content_digest,
    encode_relational_zr_c3_state,
)


# The draft schema is intentionally kept as a separate, reusable pure module.
# The fallback makes this standalone bridge importable by a future server
# runner without turning the scratch directories into a Python package.
try:
    from relational_source_schema import (  # type: ignore[import-not-found]
        ALLOWED_SPLITS,
        FEATURE_FIELDS,
        METADATA_FILENAME,
        NPZ_FILENAME,
        RECEIPT_FILENAME,
        SOURCE_SCHEMA,
        SOURCE_SCHEMA_VERSION,
        RelationalZRC3Source,
        file_sha256,
        read_source_shard,
        write_source_shard,
    )
except ImportError:  # pragma: no cover - exercised by standalone runners
    _DRAFT_ROOT = Path(__file__).resolve().parent.parent / "next-learner-draft"
    if str(_DRAFT_ROOT) not in sys.path:
        sys.path.insert(0, str(_DRAFT_ROOT))
    from relational_source_schema import (  # type: ignore[no-redef]
        ALLOWED_SPLITS,
        FEATURE_FIELDS,
        METADATA_FILENAME,
        NPZ_FILENAME,
        RECEIPT_FILENAME,
        SOURCE_SCHEMA,
        SOURCE_SCHEMA_VERSION,
        RelationalZRC3Source,
        file_sha256,
        read_source_shard,
        write_source_shard,
    )


BRIDGE_SCHEMA = "multi-catfish-mcrl-v018-relational-zr-source-bridge-v1"
BRIDGE_SCHEMA_VERSION = 1
BRIDGE_METADATA_FILENAME = "bridge.json"
BRIDGE_RECEIPT_FILENAME = "bridge.sha256"
BRIDGE_RECEIPT_FIELDS = (
    "schema",
    "metadata_sha256",
    "source_npz_sha256",
    "source_metadata_sha256",
    "source_arrays_sha256",
    "bridge_metadata_sha256",
)

ENCODER_NAME = (
    "mcrl.runtime.ee_axis_relational_zr_c3.encode_relational_zr_c3_state"
)
TARGET_SEMANTICS = "exact-ZR-centered-surface-label-only"
COMPATIBILITY_ROLE = "predecision-side-channel-not-target-derived"
CAPTURE_ORDER = "predecision-observation-before-exact-ZR-target"
IMPLEMENTATION_STATUS = "IMPLEMENTATION_ONLY_NO_OUTCOME"


class RelationalSourceBridgeError(ValueError):
    """The source bridge violated its predecision or provenance boundary."""


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise RelationalSourceBridgeError(
            "bridge payload is not finite canonical JSON"
        ) from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RelationalSourceBridgeError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RelationalSourceBridgeError(f"{field} must be a positive integer")
    return value


def _finite_positive(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise RelationalSourceBridgeError(
            f"{field} must be finite and positive"
        ) from error
    if not math.isfinite(result) or result <= 0.0:
        raise RelationalSourceBridgeError(f"{field} must be finite and positive")
    return result


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _source_observation_digest(source: RelationalZRC3Source) -> str:
    """Digest a source observation even when aggregate rows exceed victims.

    Runtime observations use one victim slot per live user.  A persisted
    source shard concatenates ten 100-user anchors, so its row count is 1000
    while the victim axis remains 100.  The source schema explicitly permits
    that shape; use the runtime content-digest byte contract without trying to
    construct an invalid live observation object.
    """

    if source.victim_count == source.rows:
        observation = RelationalZRC3Observation(
            action_context=source.action_context,
            victim_tokens=source.victim_tokens,
            action_mask=source.action_mask,
            victim_mask=source.victim_mask,
            positive_credit_compatible=source.positive_credit_compatible,
            reference_actions=source.reference_actions,
        )
        return observation.state_sha256
    return _relational_content_digest(
        source.action_context,
        source.victim_tokens,
        source.action_mask,
        source.victim_mask,
        source.positive_credit_compatible,
        source.reference_actions,
        RELATIONAL_ZR_C3_SCHEMA_VERSION,
    )


def _target_surface(value: object, *, observation: RelationalZRC3Observation) -> np.ndarray:
    """Materialise only a native-bit target array, never a teacher object."""

    if isinstance(value, Mapping):
        raise RelationalSourceBridgeError(
            "exact target adapter must return target_surface_bits only, not a mapping"
        )
    try:
        target = np.array(value, dtype=np.float64, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise RelationalSourceBridgeError(
            "exact target adapter did not return a numeric surface"
        ) from error
    expected_shape = observation.action_mask.shape
    if target.shape != expected_shape:
        raise RelationalSourceBridgeError(
            f"target_surface_bits must have shape {expected_shape}"
        )
    if not np.all(np.isfinite(target)):
        raise RelationalSourceBridgeError("target_surface_bits must be finite")
    if np.any(target[~observation.action_mask] != 0.0):
        raise RelationalSourceBridgeError(
            "target_surface_bits must be zero outside the native mask"
        )
    rows = np.arange(target.shape[0], dtype=np.int64)
    references = np.asarray(observation.reference_actions, dtype=np.int64)
    valid_reference = references >= 0
    if np.any(target[rows[valid_reference], references[valid_reference]] != 0.0):
        raise RelationalSourceBridgeError(
            "target_surface_bits must be exactly zero at each reference action"
        )
    target.setflags(write=False)
    return target


@dataclass(frozen=True)
class PredecisionCapture:
    """Authenticated nominal observation captured before the exact teacher."""

    observation: RelationalZRC3Observation
    world_seed: int
    lineage: int
    split: str
    field_root_digest: str
    kappa_bits: float
    encoder: str = ENCODER_NAME
    predecision_observation_sha256: str = ""
    status: str = IMPLEMENTATION_STATUS

    def __post_init__(self) -> None:
        if not isinstance(self.observation, RelationalZRC3Observation):
            raise RelationalSourceBridgeError(
                "predecision capture requires a V0.18 relational observation"
            )
        expected_observation_digest = self.observation.verify()
        _positive_int(self.world_seed, field="world_seed")
        _positive_int(self.lineage, field="lineage")
        if self.split not in ALLOWED_SPLITS:
            raise RelationalSourceBridgeError(
                f"split must be one of {sorted(ALLOWED_SPLITS)}"
            )
        _digest(self.field_root_digest, field="field_root_digest")
        _finite_positive(self.kappa_bits, field="kappa_bits")
        if self.encoder != ENCODER_NAME:
            raise RelationalSourceBridgeError("the source encoder identity is closed")
        if self.status != IMPLEMENTATION_STATUS:
            raise RelationalSourceBridgeError("bridge status must remain implementation-only")
        if self.predecision_observation_sha256 in (
            "",
            expected_observation_digest,
        ):
            object.__setattr__(
                self,
                "predecision_observation_sha256",
                expected_observation_digest,
            )
        else:
            raise RelationalSourceBridgeError(
                "predecision observation digest disagrees with the captured arrays"
            )


@dataclass(frozen=True)
class RelationalSourceCapture:
    """One source closure with nominal features and a native-bit exact target."""

    predecision: PredecisionCapture
    source: RelationalZRC3Source
    target_surface_sha256: str
    target_semantics: str = TARGET_SEMANTICS
    capture_order: str = CAPTURE_ORDER

    def __post_init__(self) -> None:
        if not isinstance(self.predecision, PredecisionCapture):
            raise RelationalSourceBridgeError("predecision capture is malformed")
        if not isinstance(self.source, RelationalZRC3Source):
            raise RelationalSourceBridgeError("source closure is malformed")
        self.source.arrays_sha256()
        if self.source.world_seed != self.predecision.world_seed:
            raise RelationalSourceBridgeError("source world differs from predecision capture")
        if self.source.lineage != self.predecision.lineage:
            raise RelationalSourceBridgeError("source lineage differs from predecision capture")
        if self.source.split != self.predecision.split:
            raise RelationalSourceBridgeError("source split differs from predecision capture")
        if self.source.field_root_digest != self.predecision.field_root_digest:
            raise RelationalSourceBridgeError(
                "source field digest differs from predecision capture"
            )
        if float(self.source.kappa_bits).hex() != float(self.predecision.kappa_bits).hex():
            raise RelationalSourceBridgeError("source kappa differs from predecision capture")
        if tuple(self.source.feature_fields) != FEATURE_FIELDS:
            raise RelationalSourceBridgeError("source feature fields are not closed")
        if not np.array_equal(
            self.source.action_context, self.predecision.observation.action_context
        ) or not np.array_equal(
            self.source.victim_tokens, self.predecision.observation.victim_tokens
        ):
            raise RelationalSourceBridgeError(
                "source features differ from captured nominal tensors"
            )
        if not np.array_equal(
            self.source.positive_credit_compatible,
            self.predecision.observation.positive_credit_compatible,
        ):
            raise RelationalSourceBridgeError(
                "compatibility side-channel differs from captured predecision support"
            )
        for field in ("action_mask", "victim_mask", "reference_actions"):
            if not np.array_equal(
                getattr(self.source, field),
                getattr(self.predecision.observation, field),
            ):
                raise RelationalSourceBridgeError(
                    f"source {field} differs from captured predecision observation"
                )
        _digest(self.target_surface_sha256, field="target_surface_sha256")
        if self.target_surface_sha256 != _array_sha256(self.source.target_surface_bits):
            raise RelationalSourceBridgeError(
                "target surface digest disagrees with source target array"
            )
        if self.target_semantics != TARGET_SEMANTICS:
            raise RelationalSourceBridgeError("target semantics are stale")
        if self.capture_order != CAPTURE_ORDER:
            raise RelationalSourceBridgeError("source capture order is stale")


def capture_predecision(
    *,
    encoder: Callable[[], object],
    world_seed: int,
    lineage: int,
    split: str,
    field_root_digest: str,
    kappa_bits: float,
) -> PredecisionCapture:
    """Call the nominal encoder and authenticate its immutable result."""

    try:
        observation = encoder()
    except RelationalSourceBridgeError:
        raise
    except Exception as error:  # pragma: no cover - adapter-specific failure
        raise RelationalSourceBridgeError("predecision encoder failed") from error
    if not isinstance(observation, RelationalZRC3Observation):
        raise RelationalSourceBridgeError(
            "predecision encoder must return RelationalZRC3Observation"
        )
    observation.verify()
    return PredecisionCapture(
        observation=observation,
        world_seed=world_seed,
        lineage=lineage,
        split=split,
        field_root_digest=field_root_digest,
        kappa_bits=kappa_bits,
    )


def attach_exact_zr_target(
    predecision: PredecisionCapture,
    target_surface_bits: object,
) -> RelationalSourceCapture:
    """Attach only the exact-ZR native-bit label after predecision capture."""

    if not isinstance(predecision, PredecisionCapture):
        raise RelationalSourceBridgeError("predecision capture is malformed")
    target = _target_surface(target_surface_bits, observation=predecision.observation)
    observation = predecision.observation
    source = RelationalZRC3Source(
        action_context=observation.action_context,
        victim_tokens=observation.victim_tokens,
        action_mask=observation.action_mask,
        victim_mask=observation.victim_mask,
        positive_credit_compatible=observation.positive_credit_compatible,
        reference_actions=observation.reference_actions,
        target_surface_bits=target,
        world_seed=predecision.world_seed,
        lineage=predecision.lineage,
        split=predecision.split,
        field_root_digest=predecision.field_root_digest,
        kappa_bits=predecision.kappa_bits,
        feature_fields=FEATURE_FIELDS,
    )
    return RelationalSourceCapture(
        predecision=predecision,
        source=source,
        target_surface_sha256=_array_sha256(target),
    )


def capture_anchor_source(
    *,
    predecision_encoder: Callable[[], object],
    exact_target_provider: Callable[[PredecisionCapture], object],
    world_seed: int,
    lineage: int,
    split: str,
    field_root_digest: str,
    kappa_bits: float,
) -> RelationalSourceCapture:
    """Capture one anchor with a mechanically ordered feature/target boundary.

    The exact target provider receives a completed ``PredecisionCapture``.  It
    is therefore impossible for this bridge to invoke it before the nominal
    observation has been validated and copied into the capture object.
    """

    predecision = capture_predecision(
        encoder=predecision_encoder,
        world_seed=world_seed,
        lineage=lineage,
        split=split,
        field_root_digest=field_root_digest,
        kappa_bits=kappa_bits,
    )
    try:
        target = exact_target_provider(predecision)
    except RelationalSourceBridgeError:
        raise
    except Exception as error:  # pragma: no cover - adapter-specific failure
        raise RelationalSourceBridgeError("exact target provider failed") from error
    return attach_exact_zr_target(predecision, target)


def harvest_v018_relational_anchor(
    *,
    environment: object,
    observation: object,
    reference_actions: object,
    required_power_surface: object,
    opening_feasibility_surface: object,
    pmax_w: float | None,
    exact_target_provider: Callable[[PredecisionCapture], object],
    world_seed: int,
    lineage: int,
    split: str,
    field_root_digest: str,
    kappa_bits: float,
) -> RelationalSourceCapture:
    """Use the current V0.18 encoder, then defer exact-ZR target production."""

    return capture_anchor_source(
        predecision_encoder=lambda: encode_relational_zr_c3_state(
            environment,
            observation,
            reference_actions=reference_actions,
            required_power_surface=required_power_surface,
            opening_feasibility_surface=opening_feasibility_surface,
            pmax_w=pmax_w,
        ),
        exact_target_provider=exact_target_provider,
        world_seed=world_seed,
        lineage=lineage,
        split=split,
        field_root_digest=field_root_digest,
        kappa_bits=kappa_bits,
    )


def _write_once(path: Path, payload: bytes) -> str:
    if path.exists() or path.is_symlink():
        raise RelationalSourceBridgeError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_bytes(payload)
        os.link(temporary, path)
    except FileExistsError as error:
        raise RelationalSourceBridgeError(f"refusing to overwrite {path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return file_sha256(path)


def _bridge_metadata(
    capture: RelationalSourceCapture,
    *,
    source_receipt: Mapping[str, str],
) -> dict[str, object]:
    observation = capture.predecision.observation
    source = capture.source
    return {
        "schema": BRIDGE_SCHEMA,
        "schema_version": BRIDGE_SCHEMA_VERSION,
        "status": IMPLEMENTATION_STATUS,
        "source_schema": SOURCE_SCHEMA,
        "source_schema_version": SOURCE_SCHEMA_VERSION,
        "source_npz_filename": NPZ_FILENAME,
        "source_metadata_filename": METADATA_FILENAME,
        "source_receipt_filename": RECEIPT_FILENAME,
        "source_npz_sha256": source_receipt["npz_sha256"],
        "source_metadata_sha256": source_receipt["metadata_sha256"],
        "source_arrays_sha256": source_receipt["arrays_sha256"],
        "source_target_surface_sha256": capture.target_surface_sha256,
        "source_row_count": source.rows,
        "source_victim_count": source.victim_count,
        "world_seed": source.world_seed,
        "lineage": source.lineage,
        "split": source.split,
        "field_root_digest": source.field_root_digest,
        "kappa_bits_hex": float(source.kappa_bits).hex(),
        "predecision_observation_schema": observation.schema,
        "predecision_observation_schema_version": observation.schema_version,
        "predecision_observation_schema_sha256": observation.schema_sha256,
        "predecision_observation_sha256": capture.predecision.predecision_observation_sha256,
        "encoder": capture.predecision.encoder,
        "feature_fields": list(FEATURE_FIELDS),
        "label_fields": ["positive_credit_compatible", "target_surface_bits"],
        "compatibility_role": COMPATIBILITY_ROLE,
        "target_semantics": TARGET_SEMANTICS,
        "capture_order": CAPTURE_ORDER,
        "target_source": "exact-ZR-live-teacher-label-only",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }


def _bridge_metadata_for_source(
    source: RelationalZRC3Source,
    *,
    source_receipt: Mapping[str, str],
) -> dict[str, object]:
    """Build bridge provenance for a concatenated source shard.

    The source schema permits ten anchors to be concatenated along the row
    axis while retaining 100 victim slots.  Such an aggregate cannot be
    represented as a live ``RelationalZRC3Observation`` (whose victim axis is
    its live-user count), but it still has the same authenticated byte-level
    observation digest and remains fully learner-readable.
    """

    return {
        "schema": BRIDGE_SCHEMA,
        "schema_version": BRIDGE_SCHEMA_VERSION,
        "status": IMPLEMENTATION_STATUS,
        "source_schema": SOURCE_SCHEMA,
        "source_schema_version": SOURCE_SCHEMA_VERSION,
        "source_npz_filename": NPZ_FILENAME,
        "source_metadata_filename": METADATA_FILENAME,
        "source_receipt_filename": RECEIPT_FILENAME,
        "source_npz_sha256": source_receipt["npz_sha256"],
        "source_metadata_sha256": source_receipt["metadata_sha256"],
        "source_arrays_sha256": source_receipt["arrays_sha256"],
        "source_target_surface_sha256": _array_sha256(source.target_surface_bits),
        "source_row_count": source.rows,
        "source_victim_count": source.victim_count,
        "world_seed": source.world_seed,
        "lineage": source.lineage,
        "split": source.split,
        "field_root_digest": source.field_root_digest,
        "kappa_bits_hex": float(source.kappa_bits).hex(),
        "predecision_observation_schema": RELATIONAL_ZR_C3_SCHEMA,
        "predecision_observation_schema_version": RELATIONAL_ZR_C3_SCHEMA_VERSION,
        "predecision_observation_schema_sha256": RELATIONAL_ZR_C3_SCHEMA_SHA256,
        "predecision_observation_sha256": _source_observation_digest(source),
        "encoder": ENCODER_NAME,
        "feature_fields": list(FEATURE_FIELDS),
        "label_fields": ["positive_credit_compatible", "target_surface_bits"],
        "compatibility_role": COMPATIBILITY_ROLE,
        "target_semantics": TARGET_SEMANTICS,
        "capture_order": CAPTURE_ORDER,
        "target_source": "exact-ZR-live-teacher-label-only",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }


def write_source_closure(
    output_dir: str | Path,
    capture: RelationalSourceCapture,
) -> dict[str, str]:
    """Write the source schema plus bridge provenance exactly once."""

    if not isinstance(capture, RelationalSourceCapture):
        raise RelationalSourceBridgeError("capture must be RelationalSourceCapture")
    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise RelationalSourceBridgeError(f"refusing to overwrite {destination}")
    source_receipt = write_source_shard(destination, capture.source)
    body = _bridge_metadata(capture, source_receipt=source_receipt)
    bridge_payload = {**body, "bridge_metadata_sha256": canonical_sha256(body)}
    bridge_metadata_path = destination / BRIDGE_METADATA_FILENAME
    bridge_metadata_sha256 = _write_once(
        bridge_metadata_path, _canonical_bytes(bridge_payload)
    )
    receipt_values = {
        "schema": BRIDGE_SCHEMA,
        "metadata_sha256": bridge_metadata_sha256,
        "source_npz_sha256": source_receipt["npz_sha256"],
        "source_metadata_sha256": source_receipt["metadata_sha256"],
        "source_arrays_sha256": source_receipt["arrays_sha256"],
        "bridge_metadata_sha256": bridge_payload["bridge_metadata_sha256"],
    }
    receipt_bytes = "".join(
        f"{field}={receipt_values[field]}\n" for field in BRIDGE_RECEIPT_FIELDS
    ).encode("ascii")
    bridge_receipt_path = destination / BRIDGE_RECEIPT_FILENAME
    bridge_receipt_sha256 = _write_once(bridge_receipt_path, receipt_bytes)
    return {
        **source_receipt,
        "bridge_metadata": str(bridge_metadata_path),
        "bridge_receipt": str(bridge_receipt_path),
        "bridge_metadata_sha256": bridge_metadata_sha256,
        "bridge_payload_sha256": str(bridge_payload["bridge_metadata_sha256"]),
        "bridge_receipt_sha256": bridge_receipt_sha256,
    }


def write_source_closure_for_source(
    output_dir: str | Path,
    source: RelationalZRC3Source,
) -> dict[str, str]:
    """Write an authenticated bridge closure for an aggregate source.

    ``write_source_closure`` remains the strict per-anchor API.  This sibling
    accepts only the already-validated source-schema object and is used by the
    ten-anchor harvester after its aggregate checks have completed.
    """

    if not isinstance(source, RelationalZRC3Source):
        raise RelationalSourceBridgeError("source must be RelationalZRC3Source")
    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise RelationalSourceBridgeError(f"refusing to overwrite {destination}")
    source_receipt = write_source_shard(destination, source)
    body = _bridge_metadata_for_source(source, source_receipt=source_receipt)
    bridge_payload = {**body, "bridge_metadata_sha256": canonical_sha256(body)}
    bridge_metadata_path = destination / BRIDGE_METADATA_FILENAME
    bridge_metadata_sha256 = _write_once(
        bridge_metadata_path, _canonical_bytes(bridge_payload)
    )
    receipt_values = {
        "schema": BRIDGE_SCHEMA,
        "metadata_sha256": bridge_metadata_sha256,
        "source_npz_sha256": source_receipt["npz_sha256"],
        "source_metadata_sha256": source_receipt["metadata_sha256"],
        "source_arrays_sha256": source_receipt["arrays_sha256"],
        "bridge_metadata_sha256": bridge_payload["bridge_metadata_sha256"],
    }
    bridge_receipt_path = destination / BRIDGE_RECEIPT_FILENAME
    bridge_receipt_sha256 = _write_once(
        bridge_receipt_path,
        "".join(
            f"{field}={receipt_values[field]}\n" for field in BRIDGE_RECEIPT_FIELDS
        ).encode("ascii"),
    )
    return {
        **source_receipt,
        "bridge_metadata": str(bridge_metadata_path),
        "bridge_receipt": str(bridge_receipt_path),
        "bridge_metadata_sha256": bridge_metadata_sha256,
        "bridge_payload_sha256": str(bridge_payload["bridge_metadata_sha256"]),
        "bridge_receipt_sha256": bridge_receipt_sha256,
    }


def _read_canonical_json(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise RelationalSourceBridgeError(f"missing bridge metadata: {path}")
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RelationalSourceBridgeError("bridge metadata is not JSON") from error
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload):
        raise RelationalSourceBridgeError("bridge metadata is not canonical JSON")
    return payload


def _read_bridge_receipt(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise RelationalSourceBridgeError(f"missing bridge receipt: {path}")
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise RelationalSourceBridgeError("bridge receipt is not ASCII") from error
    values: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            raise RelationalSourceBridgeError("bridge receipt contains a malformed line")
        key, value = line.split("=", 1)
        if key in values or key not in BRIDGE_RECEIPT_FIELDS:
            raise RelationalSourceBridgeError("bridge receipt contains unknown fields")
        values[key] = value
    if tuple(values) != BRIDGE_RECEIPT_FIELDS:
        raise RelationalSourceBridgeError("bridge receipt fields are incomplete or reordered")
    for field in BRIDGE_RECEIPT_FIELDS[1:]:
        _digest(values[field], field=f"bridge receipt {field}")
    if values["schema"] != BRIDGE_SCHEMA:
        raise RelationalSourceBridgeError("bridge receipt schema is stale")
    return values


def read_source_closure(
    output_dir: str | Path,
) -> tuple[RelationalZRC3Source, dict[str, object]]:
    """Read and authenticate source plus its predecision-order receipt."""

    root = Path(output_dir)
    source = read_source_shard(root)
    metadata = _read_canonical_json(root / BRIDGE_METADATA_FILENAME)
    receipt = _read_bridge_receipt(root / BRIDGE_RECEIPT_FILENAME)
    bridge_body = {
        key: value
        for key, value in metadata.items()
        if key != "bridge_metadata_sha256"
    }
    supplied_bridge_digest = _digest(
        metadata.get("bridge_metadata_sha256"),
        field="bridge_metadata_sha256",
    )
    if canonical_sha256(bridge_body) != supplied_bridge_digest:
        raise RelationalSourceBridgeError("bridge metadata self-digest failed")
    if receipt["metadata_sha256"] != file_sha256(root / BRIDGE_METADATA_FILENAME):
        raise RelationalSourceBridgeError("bridge receipt disagrees with metadata file")
    if receipt["source_npz_sha256"] != file_sha256(root / NPZ_FILENAME):
        raise RelationalSourceBridgeError("bridge receipt disagrees with source NPZ")
    if receipt["source_metadata_sha256"] != file_sha256(root / METADATA_FILENAME):
        raise RelationalSourceBridgeError(
            "bridge receipt disagrees with source metadata"
        )
    if receipt["source_arrays_sha256"] != source.arrays_sha256():
        raise RelationalSourceBridgeError(
            "bridge receipt disagrees with source arrays"
        )
    if receipt["bridge_metadata_sha256"] != supplied_bridge_digest:
        raise RelationalSourceBridgeError(
            "bridge receipt disagrees with metadata self-digest"
        )

    # Reconstructing the pure observation is the only way to authenticate the
    # bridge's predecision digest without storing another copy of the arrays.
    # An aggregate source has ten times as many rows as live victim slots, so
    # use the same runtime content-digest contract without constructing an
    # invalid live observation object.
    reconstructed_digest = _source_observation_digest(source)

    expected = {
        "schema": BRIDGE_SCHEMA,
        "schema_version": BRIDGE_SCHEMA_VERSION,
        "status": IMPLEMENTATION_STATUS,
        "source_schema": SOURCE_SCHEMA,
        "source_schema_version": SOURCE_SCHEMA_VERSION,
        "source_npz_filename": NPZ_FILENAME,
        "source_metadata_filename": METADATA_FILENAME,
        "source_receipt_filename": RECEIPT_FILENAME,
        "source_npz_sha256": receipt["source_npz_sha256"],
        "source_metadata_sha256": receipt["source_metadata_sha256"],
        "source_arrays_sha256": receipt["source_arrays_sha256"],
        "source_target_surface_sha256": _array_sha256(source.target_surface_bits),
        "source_row_count": source.rows,
        "source_victim_count": source.victim_count,
        "world_seed": source.world_seed,
        "lineage": source.lineage,
        "split": source.split,
        "field_root_digest": source.field_root_digest,
        "kappa_bits_hex": float(source.kappa_bits).hex(),
        "predecision_observation_schema": RELATIONAL_ZR_C3_SCHEMA,
        "predecision_observation_schema_version": RELATIONAL_ZR_C3_SCHEMA_VERSION,
        "predecision_observation_schema_sha256": RELATIONAL_ZR_C3_SCHEMA_SHA256,
        "predecision_observation_sha256": reconstructed_digest,
        "encoder": ENCODER_NAME,
        "feature_fields": list(FEATURE_FIELDS),
        "label_fields": ["positive_credit_compatible", "target_surface_bits"],
        "compatibility_role": COMPATIBILITY_ROLE,
        "target_semantics": TARGET_SEMANTICS,
        "capture_order": CAPTURE_ORDER,
        "target_source": "exact-ZR-live-teacher-label-only",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    expected_metadata_keys = set(expected) | {"bridge_metadata_sha256"}
    if set(metadata) != expected_metadata_keys:
        raise RelationalSourceBridgeError(
            "bridge metadata contains unknown or missing provenance fields"
        )
    for field, value in expected.items():
        if metadata.get(field) != value:
            raise RelationalSourceBridgeError(
                f"bridge provenance field {field!r} disagrees with source closure"
            )

    supplied_predecision_digest = _digest(
        metadata.get("predecision_observation_sha256"),
        field="predecision_observation_sha256",
    )
    if reconstructed_digest != supplied_predecision_digest:
        raise RelationalSourceBridgeError(
            "bridge predecision digest disagrees with source feature arrays"
        )
    return source, metadata


__all__ = [
    "BRIDGE_METADATA_FILENAME",
    "BRIDGE_RECEIPT_FILENAME",
    "BRIDGE_SCHEMA",
    "CAPTURE_ORDER",
    "COMPATIBILITY_ROLE",
    "ENCODER_NAME",
    "IMPLEMENTATION_STATUS",
    "PredecisionCapture",
    "RelationalSourceBridgeError",
    "RelationalSourceCapture",
    "TARGET_SEMANTICS",
    "attach_exact_zr_target",
    "canonical_sha256",
    "capture_anchor_source",
    "capture_predecision",
    "harvest_v018_relational_anchor",
    "read_source_closure",
    "write_source_closure",
    "write_source_closure_for_source",
]
