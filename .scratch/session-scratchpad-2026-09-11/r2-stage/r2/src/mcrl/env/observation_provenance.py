"""Immutable provenance for one native predecision observation event.

The receipt is deliberately outside every learner feature schema.  It binds
the observation-time random event to the exact candidate-SINR output without
making either the RNG state or raw SINR available to a downstream C3 encoder.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import struct
from typing import Any

import numpy as np

from ..errors import MCRLContractError
from .keyed_fading import KeyedFadingField


NATIVE_OBSERVATION_PROVENANCE_SCHEMA = (
    "multi-catfish-mcrl-native-observation-provenance-v1"
)
NATIVE_OBSERVATION_EVENT = "observation"
SEQUENTIAL_RNG_MODE = "numpy-sequential-v1"


class NativeObservationProvenanceError(MCRLContractError):
    """A native observation event receipt is malformed or stale."""


def _sha256(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise NativeObservationProvenanceError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return value


def _canonical(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, np.ndarray):
        return {
            "dtype": value.dtype.str,
            "shape": list(value.shape),
            "hex": np.ascontiguousarray(value).tobytes(order="C").hex(),
        }
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise NativeObservationProvenanceError(
        f"unsupported RNG-state value {type(value).__name__}"
    )


def numpy_rng_state_sha256(rng: np.random.Generator) -> str:
    """Hash a NumPy generator state without serializing it into receipts."""

    if not isinstance(rng, np.random.Generator):
        raise NativeObservationProvenanceError("rng must be a NumPy Generator")
    encoded = json.dumps(
        _canonical(rng.bit_generator.state),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def candidate_sinr_sha256(value: object) -> str:
    """Hash the exact native candidate-SINR output as receipt-only evidence."""

    array = np.asarray(value)
    if array.ndim != 2 or not np.issubdtype(array.dtype, np.floating):
        raise NativeObservationProvenanceError(
            "candidate_sinr must be a floating matrix"
        )
    if not np.all(np.isfinite(array)) or np.any(array < 0.0):
        raise NativeObservationProvenanceError(
            "candidate_sinr must be finite and nonnegative"
        )
    exact = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(b"native-candidate-sinr-v1")
    digest.update(exact.dtype.str.encode("ascii"))
    digest.update(struct.pack(">II", *exact.shape))
    digest.update(exact.tobytes(order="C"))
    return digest.hexdigest()


def _receipt_digest(receipt: "NativeObservationProvenance") -> str:
    payload = {
        "schema": receipt.schema,
        "event": receipt.event,
        "step_index": receipt.step_index,
        "candidate_sinr_sha256": receipt.candidate_sinr_sha256,
        "rng_pre_state_sha256": receipt.rng_pre_state_sha256,
        "rng_post_state_sha256": receipt.rng_post_state_sha256,
        "rng_bit_generator": receipt.rng_bit_generator,
        "field_mode": receipt.field_mode,
        "field_version": receipt.field_version,
        "field_root_digest": receipt.field_root_digest,
        "sinr_provenance": receipt.sinr_provenance,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class NativeObservationProvenance:
    """Opaque source/replay receipt; none of these fields is a learner input."""

    step_index: int
    candidate_sinr_sha256: str
    rng_pre_state_sha256: str
    rng_post_state_sha256: str
    rng_bit_generator: str
    field_mode: str
    field_version: str
    field_root_digest: str | None
    sinr_provenance: str
    content_digest: str = ""
    event: str = NATIVE_OBSERVATION_EVENT
    schema: str = NATIVE_OBSERVATION_PROVENANCE_SCHEMA

    def __post_init__(self) -> None:
        if type(self.step_index) is not int or self.step_index < 0:
            raise NativeObservationProvenanceError(
                "step_index must be a nonnegative exact integer"
            )
        for name, value in (
            ("candidate_sinr_sha256", self.candidate_sinr_sha256),
            ("rng_pre_state_sha256", self.rng_pre_state_sha256),
            ("rng_post_state_sha256", self.rng_post_state_sha256),
        ):
            _sha256(value, field=name)
        if self.field_root_digest is not None:
            _sha256(self.field_root_digest, field="field_root_digest")
        for name, value in (
            ("rng_bit_generator", self.rng_bit_generator),
            ("field_mode", self.field_mode),
            ("field_version", self.field_version),
            ("sinr_provenance", self.sinr_provenance),
        ):
            if not isinstance(value, str) or not value or value != value.strip():
                raise NativeObservationProvenanceError(
                    f"{name} must be a nonempty trimmed string"
                )
        if self.event != NATIVE_OBSERVATION_EVENT:
            raise NativeObservationProvenanceError(
                "native observation event must be 'observation'"
            )
        if self.schema != NATIVE_OBSERVATION_PROVENANCE_SCHEMA:
            raise NativeObservationProvenanceError(
                "native observation provenance schema drifted"
            )
        if self.field_mode != SEQUENTIAL_RNG_MODE:
            if self.field_root_digest is None:
                raise NativeObservationProvenanceError(
                    "keyed observation provenance lacks a field root digest"
                )
            if self.rng_pre_state_sha256 != self.rng_post_state_sha256:
                raise NativeObservationProvenanceError(
                    "keyed observation fading must not consume the sequential RNG"
                )
        elif self.field_root_digest is not None:
            raise NativeObservationProvenanceError(
                "sequential observation provenance cannot claim a keyed field root"
            )
        expected = _receipt_digest(self)
        if self.content_digest not in {"", expected}:
            raise NativeObservationProvenanceError(
                "native observation provenance digest mismatch"
            )
        object.__setattr__(self, "content_digest", expected)

    def verify(self) -> str:
        expected = _receipt_digest(self)
        if self.content_digest != expected:
            raise NativeObservationProvenanceError(
                "native observation provenance digest mismatch"
            )
        return expected

    def verify_candidate_sinr(self, value: object) -> str:
        actual = candidate_sinr_sha256(value)
        if actual != self.candidate_sinr_sha256:
            raise NativeObservationProvenanceError(
                "candidate SINR disagrees with native observation receipt"
            )
        return actual


def build_native_observation_provenance(
    *,
    step_index: int,
    candidate_sinr: object,
    rng: np.random.Generator,
    rng_pre_state_sha256: str,
    fading_field: KeyedFadingField | None,
    sinr_provenance: str,
) -> NativeObservationProvenance:
    """Seal the event immediately after the native observation draw."""

    pre = _sha256(rng_pre_state_sha256, field="rng_pre_state_sha256")
    post = numpy_rng_state_sha256(rng)
    if fading_field is None:
        mode = SEQUENTIAL_RNG_MODE
        version = SEQUENTIAL_RNG_MODE
        root = None
    elif isinstance(fading_field, KeyedFadingField):
        field_receipt = fading_field.receipt()
        mode = str(field_receipt["mode"])
        version = str(field_receipt["version"])
        root = _sha256(field_receipt["root_digest"], field="field_root_digest")
    else:
        raise NativeObservationProvenanceError(
            "fading_field must be KeyedFadingField or None"
        )
    return NativeObservationProvenance(
        step_index=step_index,
        candidate_sinr_sha256=candidate_sinr_sha256(candidate_sinr),
        rng_pre_state_sha256=pre,
        rng_post_state_sha256=post,
        rng_bit_generator=type(rng.bit_generator).__name__,
        field_mode=mode,
        field_version=version,
        field_root_digest=root,
        sinr_provenance=sinr_provenance,
    )


__all__ = [
    "NATIVE_OBSERVATION_EVENT",
    "NATIVE_OBSERVATION_PROVENANCE_SCHEMA",
    "SEQUENTIAL_RNG_MODE",
    "NativeObservationProvenance",
    "NativeObservationProvenanceError",
    "build_native_observation_provenance",
    "candidate_sinr_sha256",
    "numpy_rng_state_sha256",
]
