"""Pre-outcome C2 schedules for the Multi-Catfish MCRL V0.3 E1 run.

This module is deliberately a data-only boundary.  It does not import the
simulator, a trainer, or the C2 forecast backend, and it never evaluates an
action.  A source runner can therefore discover and seal the schedule before
it starts any detached C2 forecast.

One :class:`E1C2PreOutcomeSchedule` is scoped to one source seed.  Each
cluster is the immutable ``(source_seed, anchor, focal_user)`` identity of a
single pre-outcome fork and carries its own keyed common-random-field digest.
Candidate actions are already selected by the source policy, but no target,
trace, release, service, or other outcome is allowed to cross this boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile
from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError
from .ee_axis_temporal_pairs import (
    C2_POLICY_VERSION,
    TEMPORAL_HORIZON_STEPS,
    TEMPORAL_SOURCE_RULES,
)


E1_C2_SCHEDULE_SCHEMA = "multi-catfish-mcrl-v03-e1-c2-preoutcome-schedule-v1"
E1_C2_CLUSTER_SCHEMA = "multi-catfish-mcrl-v03-e1-c2-preoutcome-cluster-v1"
E1_C2_WORLD_ANCHOR_SCHEMA = "multi-catfish-mcrl-v03-e1-c2-world-anchor-v1"
E1_C2_SCHEDULE_VERSION = 1
E1_C2_HORIZON_OFFSETS = tuple(range(TEMPORAL_HORIZON_STEPS))
E1_C2_SOURCE_RULES = frozenset(TEMPORAL_SOURCE_RULES)


class E1C2ScheduleContractError(MCRLContractError):
    """A prospective E1 C2 schedule is malformed or violates its seal."""


# The schedule deliberately has an allow-list rather than silently retaining
# arbitrary metadata.  In particular, target/trace/outcome fields must not be
# smuggled into a supposedly pre-outcome artifact.
_SCHEDULE_KEYS = frozenset(
    {
        "schema",
        "version",
        "source_seed",
        "policy_version",
        "policy_sha256",
        "source_manifest_sha256",
        "checkpoint_sha256",
        "horizon_offsets",
        "clusters",
        "schedule_sha256",
    }
)
_CLUSTER_KEYS = frozenset(
    {
        "schema",
        "source_seed",
        "anchor_sha256",
        "world_anchor_sha256",
        "anchor_schedule_sha256",
        "anchor_step",
        "focal_user",
        "reference_action",
        "candidate_action",
        "reference_physical_key",
        "candidate_physical_key",
        "candidate_source_rule",
        "policy_sha256",
        "source_manifest_sha256",
        "checkpoint_sha256",
        "common_random_field_sha256",
        "cluster_sha256",
    }
)
_OUTCOME_FIELD_NAMES = frozenset(
    {
        "candidate_trace",
        "candidate_trace_sha256",
        "reference_trace",
        "reference_trace_sha256",
        "target",
        "target_surplus_bits",
        "zeta",
        "zeta2",
        "zeta2_temporal_surplus_bits",
        "g_k",
        "release_offset",
        "release_reason",
        "service_safe",
        "outcome",
        "forecast",
        "forecast_payload_sha256",
        "served",
        "power",
        "rate",
        "energy",
        "censor",
    }
)


def _canonical_json_bytes(payload: object) -> bytes:
    """Encode JSON deterministically, refusing non-finite values."""

    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise E1C2ScheduleContractError(
            "schedule payload is not canonical JSON or contains a non-finite value"
        ) from error


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise E1C2ScheduleContractError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise E1C2ScheduleContractError(
            f"{field} must be a nonempty trimmed string"
        )
    return value


def _exact_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise E1C2ScheduleContractError(
            f"{field} must be a nonnegative exact integer"
        )
    return value


def _action(value: object, *, field: str) -> int:
    action = _exact_nonnegative_int(value, field=field)
    if action >= NUM_ACTIONS:
        raise E1C2ScheduleContractError(
            f"{field} must lie in the current action space [0, {NUM_ACTIONS})"
        )
    return action


def _physical_key(value: object, *, field: str) -> tuple[int, int]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise E1C2ScheduleContractError(
            f"{field} must be a two-integer physical key"
        )
    return (
        _exact_nonnegative_int(value[0], field=f"{field}[0]"),
        _exact_nonnegative_int(value[1], field=f"{field}[1]"),
    )


def _tuple_of_exact_nonnegative_ints(
    value: object, *, field: str, require_nonempty: bool = True
) -> tuple[int, ...]:
    if not isinstance(value, (tuple, list)):
        raise E1C2ScheduleContractError(f"{field} must be an integer sequence")
    if require_nonempty and not value:
        raise E1C2ScheduleContractError(f"{field} must not be empty")
    return tuple(
        _exact_nonnegative_int(item, field=f"{field}[{index}]")
        for index, item in enumerate(value)
    )


def _reject_unknown_fields(
    payload: Mapping[str, object], *, allowed: frozenset[str], label: str
) -> None:
    unknown = sorted(set(payload) - set(allowed))
    if unknown:
        outcome = sorted(set(unknown) & _OUTCOME_FIELD_NAMES)
        if outcome:
            raise E1C2ScheduleContractError(
                f"{label} contains outcome-derived field(s): {', '.join(outcome)}"
            )
        raise E1C2ScheduleContractError(
            f"{label} contains unsupported field(s): {', '.join(unknown)}"
        )


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise E1C2ScheduleContractError(f"{field} must be a JSON object")
    return value


def _reject_json_constant(value: str) -> object:
    raise E1C2ScheduleContractError(
        f"JSON contains non-finite numeric constant {value!r}"
    )


def e1_c2_world_anchor_sha256(*, source_seed: int, anchor_step: int) -> str:
    """Identify one focal-independent world state in the sealed episode."""

    seed = _exact_nonnegative_int(source_seed, field="source_seed")
    step = _exact_nonnegative_int(anchor_step, field="anchor_step")
    return _sha256_bytes(
        _canonical_json_bytes(
            {
                "schema": E1_C2_WORLD_ANCHOR_SCHEMA,
                "source_seed": seed,
                "anchor_step": step,
            }
        )
    )


def _cluster_identity_payload(
    *,
    source_seed: int,
    anchor_sha256: str,
    world_anchor_sha256: str,
    focal_user: int,
) -> dict[str, object]:
    return {
        "schema": E1_C2_CLUSTER_SCHEMA,
        "source_seed": source_seed,
        "anchor_sha256": anchor_sha256,
        "world_anchor_sha256": world_anchor_sha256,
        "focal_user": focal_user,
    }


@dataclass(frozen=True)
class E1C2ScheduleCluster:
    """One pre-outcome ``(anchor, focal-user)`` C2 fork identity."""

    source_seed: int
    anchor_sha256: str
    world_anchor_sha256: str
    anchor_schedule_sha256: str
    anchor_step: int
    focal_user: int
    reference_action: int
    candidate_action: int
    reference_physical_key: tuple[int, int]
    candidate_physical_key: tuple[int, int]
    candidate_source_rule: str
    policy_sha256: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    common_random_field_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_seed",
            _exact_nonnegative_int(self.source_seed, field="source_seed"),
        )
        object.__setattr__(
            self,
            "anchor_sha256",
            _digest(self.anchor_sha256, field="anchor_sha256"),
        )
        object.__setattr__(
            self,
            "anchor_schedule_sha256",
            _digest(
                self.anchor_schedule_sha256,
                field="anchor_schedule_sha256",
            ),
        )
        object.__setattr__(
            self,
            "anchor_step",
            _exact_nonnegative_int(self.anchor_step, field="anchor_step"),
        )
        world_anchor = _digest(
            self.world_anchor_sha256, field="world_anchor_sha256"
        )
        if world_anchor != e1_c2_world_anchor_sha256(
            source_seed=self.source_seed, anchor_step=self.anchor_step
        ):
            raise E1C2ScheduleContractError(
                "world_anchor_sha256 disagrees with source seed and anchor step"
            )
        object.__setattr__(self, "world_anchor_sha256", world_anchor)
        object.__setattr__(
            self,
            "focal_user",
            _exact_nonnegative_int(self.focal_user, field="focal_user"),
        )
        object.__setattr__(
            self,
            "reference_action",
            _action(self.reference_action, field="reference_action"),
        )
        object.__setattr__(
            self,
            "candidate_action",
            _action(self.candidate_action, field="candidate_action"),
        )
        if self.reference_action == self.candidate_action:
            raise E1C2ScheduleContractError(
                "reference_action and candidate_action must differ"
            )
        reference_key = _physical_key(
            self.reference_physical_key, field="reference_physical_key"
        )
        candidate_key = _physical_key(
            self.candidate_physical_key, field="candidate_physical_key"
        )
        if reference_key == candidate_key:
            raise E1C2ScheduleContractError(
                "reference_physical_key and candidate_physical_key must differ"
            )
        object.__setattr__(self, "reference_physical_key", reference_key)
        object.__setattr__(self, "candidate_physical_key", candidate_key)
        source_rule = _text(
            self.candidate_source_rule, field="candidate_source_rule"
        )
        if source_rule not in E1_C2_SOURCE_RULES:
            raise E1C2ScheduleContractError(
                "candidate_source_rule is not an admitted pre-outcome C2 rule"
            )
        object.__setattr__(self, "candidate_source_rule", source_rule)
        for field in (
            "policy_sha256",
            "source_manifest_sha256",
            "checkpoint_sha256",
            "common_random_field_sha256",
        ):
            object.__setattr__(
                self,
                field,
                _digest(getattr(self, field), field=field),
            )

    @property
    def cluster_key(self) -> tuple[int, str, int]:
        """Stable duplicate-detection key for this focal intervention."""

        return (self.source_seed, self.anchor_sha256, self.focal_user)

    @property
    def cluster_sha256(self) -> str:
        """Digest of identity only; no outcome can influence this value."""

        return _sha256_bytes(
            _canonical_json_bytes(
                _cluster_identity_payload(
                    source_seed=self.source_seed,
                    anchor_sha256=self.anchor_sha256,
                    world_anchor_sha256=self.world_anchor_sha256,
                    focal_user=self.focal_user,
                )
            )
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema": E1_C2_CLUSTER_SCHEMA,
            "source_seed": self.source_seed,
            "anchor_sha256": self.anchor_sha256,
            "world_anchor_sha256": self.world_anchor_sha256,
            "anchor_schedule_sha256": self.anchor_schedule_sha256,
            "anchor_step": self.anchor_step,
            "focal_user": self.focal_user,
            "reference_action": self.reference_action,
            "candidate_action": self.candidate_action,
            "reference_physical_key": list(self.reference_physical_key),
            "candidate_physical_key": list(self.candidate_physical_key),
            "candidate_source_rule": self.candidate_source_rule,
            "policy_sha256": self.policy_sha256,
            "source_manifest_sha256": self.source_manifest_sha256,
            "checkpoint_sha256": self.checkpoint_sha256,
            "common_random_field_sha256": self.common_random_field_sha256,
            "cluster_sha256": self.cluster_sha256,
        }

    @classmethod
    def from_mapping(cls, value: object) -> "E1C2ScheduleCluster":
        payload = _mapping(value, field="cluster")
        _reject_unknown_fields(payload, allowed=_CLUSTER_KEYS, label="cluster")
        if payload.get("schema") != E1_C2_CLUSTER_SCHEMA:
            raise E1C2ScheduleContractError("cluster schema is stale or unsupported")
        required = _CLUSTER_KEYS
        missing = sorted(required - set(payload))
        if missing:
            raise E1C2ScheduleContractError(
                f"cluster is missing required field(s): {', '.join(missing)}"
            )
        cluster = cls(
            source_seed=payload["source_seed"],  # type: ignore[arg-type]
            anchor_sha256=payload["anchor_sha256"],  # type: ignore[arg-type]
            world_anchor_sha256=payload["world_anchor_sha256"],  # type: ignore[arg-type]
            anchor_schedule_sha256=payload["anchor_schedule_sha256"],  # type: ignore[arg-type]
            anchor_step=payload["anchor_step"],  # type: ignore[arg-type]
            focal_user=payload["focal_user"],  # type: ignore[arg-type]
            reference_action=payload["reference_action"],  # type: ignore[arg-type]
            candidate_action=payload["candidate_action"],  # type: ignore[arg-type]
            reference_physical_key=_physical_key(
                payload["reference_physical_key"], field="reference_physical_key"
            ),
            candidate_physical_key=_physical_key(
                payload["candidate_physical_key"], field="candidate_physical_key"
            ),
            candidate_source_rule=payload["candidate_source_rule"],  # type: ignore[arg-type]
            policy_sha256=payload["policy_sha256"],  # type: ignore[arg-type]
            source_manifest_sha256=payload["source_manifest_sha256"],  # type: ignore[arg-type]
            checkpoint_sha256=payload["checkpoint_sha256"],  # type: ignore[arg-type]
            common_random_field_sha256=payload["common_random_field_sha256"],  # type: ignore[arg-type]
        )
        supplied_cluster_digest = _digest(
            payload["cluster_sha256"], field="cluster_sha256"
        )
        if supplied_cluster_digest != cluster.cluster_sha256:
            raise E1C2ScheduleContractError(
                "cluster_sha256 disagrees with the anchor/focal identity"
            )
        return cluster


def _schedule_body(schedule: "E1C2PreOutcomeSchedule") -> dict[str, object]:
    return {
        "schema": E1_C2_SCHEDULE_SCHEMA,
        "version": E1_C2_SCHEDULE_VERSION,
        "source_seed": schedule.source_seed,
        "policy_version": schedule.policy_version,
        "policy_sha256": schedule.policy_sha256,
        "source_manifest_sha256": schedule.source_manifest_sha256,
        "checkpoint_sha256": schedule.checkpoint_sha256,
        "horizon_offsets": list(schedule.horizon_offsets),
        "clusters": [cluster.to_mapping() for cluster in schedule.clusters],
    }


@dataclass(frozen=True)
class E1C2PreOutcomeSchedule:
    """Write-once, one-source-seed C2 schedule sealed before forecasting."""

    source_seed: int
    clusters: tuple[E1C2ScheduleCluster, ...]
    policy_sha256: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    policy_version: str = C2_POLICY_VERSION
    horizon_offsets: tuple[int, ...] = E1_C2_HORIZON_OFFSETS

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_seed",
            _exact_nonnegative_int(self.source_seed, field="source_seed"),
        )
        if not isinstance(self.clusters, tuple) or not self.clusters:
            raise E1C2ScheduleContractError(
                "clusters must be a nonempty immutable tuple"
            )
        seen: set[tuple[int, str, int]] = set()
        for index, cluster in enumerate(self.clusters):
            if not isinstance(cluster, E1C2ScheduleCluster):
                raise E1C2ScheduleContractError(
                    f"clusters[{index}] is not E1C2ScheduleCluster"
                )
            cluster_key = cluster.cluster_key
            if cluster_key in seen:
                raise E1C2ScheduleContractError(
                    "duplicate (source_seed, anchor_sha256, focal_user) cluster"
                )
            seen.add(cluster_key)
            if cluster.source_seed != self.source_seed:
                raise E1C2ScheduleContractError(
                    "cluster source_seed disagrees with schedule source_seed"
                )
        object.__setattr__(
            self,
            "policy_version",
            _text(self.policy_version, field="policy_version"),
        )
        if self.policy_version != C2_POLICY_VERSION:
            raise E1C2ScheduleContractError(
                "policy_version is stale or unsupported for current C2"
            )
        for field in (
            "policy_sha256",
            "source_manifest_sha256",
            "checkpoint_sha256",
        ):
            value = _digest(getattr(self, field), field=field)
            object.__setattr__(self, field, value)
            if any(getattr(cluster, field) != value for cluster in self.clusters):
                raise E1C2ScheduleContractError(
                    f"mixed {field} values across schedule clusters"
                )
        offsets = _tuple_of_exact_nonnegative_ints(
            self.horizon_offsets, field="horizon_offsets"
        )
        if offsets[0] != 0 or tuple(sorted(set(offsets))) != offsets:
            raise E1C2ScheduleContractError(
                "horizon_offsets must be strictly increasing and start at zero"
            )
        if offsets != E1_C2_HORIZON_OFFSETS:
            raise E1C2ScheduleContractError(
                "horizon_offsets disagree with the current C2 temporal horizon"
            )
        object.__setattr__(self, "horizon_offsets", offsets)

    @property
    def schedule_sha256(self) -> str:
        """Digest of the canonical pre-outcome schedule body."""

        return _sha256_bytes(_canonical_json_bytes(_schedule_body(self)))

    @property
    def file_sha256(self) -> str:
        """Digest of the canonical JSON document written by ``seal``."""

        return _sha256_bytes(_canonical_json_bytes(self.to_mapping()))

    def to_mapping(self) -> dict[str, object]:
        return _schedule_body(self) | {"schedule_sha256": self.schedule_sha256}

    def verify(self) -> str:
        """Validate this immutable schedule and return its body digest."""

        # ``__post_init__`` performs the complete structural validation.  A
        # second construction keeps this method useful after a caller has
        # obtained the object through a generic dataclass boundary.
        type(self)(
            source_seed=self.source_seed,
            clusters=self.clusters,
            policy_sha256=self.policy_sha256,
            source_manifest_sha256=self.source_manifest_sha256,
            checkpoint_sha256=self.checkpoint_sha256,
            policy_version=self.policy_version,
            horizon_offsets=self.horizon_offsets,
        )
        return self.schedule_sha256

    @classmethod
    def from_mapping(cls, value: object) -> "E1C2PreOutcomeSchedule":
        payload = _mapping(value, field="schedule")
        _reject_unknown_fields(payload, allowed=_SCHEDULE_KEYS, label="schedule")
        if payload.get("schema") != E1_C2_SCHEDULE_SCHEMA:
            raise E1C2ScheduleContractError("schedule schema is stale or unsupported")
        missing = sorted(_SCHEDULE_KEYS - set(payload))
        if missing:
            raise E1C2ScheduleContractError(
                f"schedule is missing required field(s): {', '.join(missing)}"
            )
        if payload.get("version") != E1_C2_SCHEDULE_VERSION:
            raise E1C2ScheduleContractError("schedule version is unsupported")
        raw_clusters = payload["clusters"]
        if not isinstance(raw_clusters, list):
            raise E1C2ScheduleContractError("schedule clusters must be a JSON list")
        clusters = tuple(
            E1C2ScheduleCluster.from_mapping(cluster) for cluster in raw_clusters
        )
        schedule = cls(
            source_seed=payload["source_seed"],  # type: ignore[arg-type]
            clusters=clusters,
            policy_sha256=payload["policy_sha256"],  # type: ignore[arg-type]
            source_manifest_sha256=payload["source_manifest_sha256"],  # type: ignore[arg-type]
            checkpoint_sha256=payload["checkpoint_sha256"],  # type: ignore[arg-type]
            policy_version=payload["policy_version"],  # type: ignore[arg-type]
            horizon_offsets=_tuple_of_exact_nonnegative_ints(
                payload["horizon_offsets"], field="horizon_offsets"
            ),
        )
        supplied_digest = _digest(
            payload["schedule_sha256"], field="schedule_sha256"
        )
        if supplied_digest != schedule.schedule_sha256:
            raise E1C2ScheduleContractError(
                "schedule_sha256 disagrees with canonical schedule contents"
            )
        return schedule


def _validate_cluster_crf_bindings(
    schedule: E1C2PreOutcomeSchedule,
    cluster_crf_sha256: Mapping[str, str] | None,
) -> None:
    """Optionally bind every cluster identity to its backend-derived CRF.

    The keyed common-random field is derived from the individual anchor,
    focal user, and evaluation seed.  It is therefore intentionally a
    cluster-local lineage value rather than a schedule-wide digest.  A
    caller may provide the expected identity-to-CRF mapping when loading or
    sealing from a manifest; the schedule itself still validates each stored
    digest syntactically and carries it with its cluster.
    """

    if cluster_crf_sha256 is None:
        return
    if not isinstance(cluster_crf_sha256, Mapping):
        raise E1C2ScheduleContractError(
            "cluster_crf_sha256 must be a mapping keyed by cluster_sha256"
        )
    expected_keys = {cluster.cluster_sha256 for cluster in schedule.clusters}
    supplied_keys = set(cluster_crf_sha256)
    if supplied_keys != expected_keys:
        raise E1C2ScheduleContractError(
            "cluster_crf_sha256 keys must match schedule cluster_sha256 identities"
        )
    for cluster in schedule.clusters:
        field = f"cluster_crf_sha256[{cluster.cluster_sha256}]"
        expected_digest = _digest(
            cluster_crf_sha256[cluster.cluster_sha256], field=field
        )
        if expected_digest != cluster.common_random_field_sha256:
            raise E1C2ScheduleContractError(
                f"cluster CRF digest disagrees for {cluster.cluster_sha256}"
            )


def validate_e1_c2_schedule(
    schedule: E1C2PreOutcomeSchedule,
    *,
    source_seed: int | None = None,
    policy_sha256: str | None = None,
    source_manifest_sha256: str | None = None,
    checkpoint_sha256: str | None = None,
    cluster_crf_sha256: Mapping[str, str] | None = None,
) -> str:
    """Validate a schedule and optional caller-bound identity fields."""

    if not isinstance(schedule, E1C2PreOutcomeSchedule):
        raise E1C2ScheduleContractError(
            "schedule must be E1C2PreOutcomeSchedule"
        )
    schedule.verify()
    if source_seed is not None:
        expected_seed = _exact_nonnegative_int(source_seed, field="source_seed")
        if schedule.source_seed != expected_seed:
            raise E1C2ScheduleContractError(
                "schedule source_seed disagrees with requested seed"
            )
    for field, expected in (
        ("policy_sha256", policy_sha256),
        ("source_manifest_sha256", source_manifest_sha256),
        ("checkpoint_sha256", checkpoint_sha256),
    ):
        if expected is not None and schedule.__getattribute__(field) != _digest(
            expected, field=field
        ):
            raise E1C2ScheduleContractError(
                f"schedule {field} disagrees with requested lineage"
            )
    _validate_cluster_crf_bindings(schedule, cluster_crf_sha256)
    return schedule.schedule_sha256


def seal_e1_c2_schedule(
    path: str | Path,
    schedule: E1C2PreOutcomeSchedule,
    *,
    source_seed: int | None = None,
    policy_sha256: str | None = None,
    source_manifest_sha256: str | None = None,
    checkpoint_sha256: str | None = None,
    cluster_crf_sha256: Mapping[str, str] | None = None,
) -> str:
    """Atomically write a new schedule exactly once and return file SHA-256.

    A temporary file is fully written and fsynced before an atomic hard-link
    installs it at ``path``.  The hard-link is no-replace, so a concurrent or
    repeated seal cannot overwrite an existing artifact.
    """

    validate_e1_c2_schedule(
        schedule,
        source_seed=source_seed,
        policy_sha256=policy_sha256,
        source_manifest_sha256=source_manifest_sha256,
        checkpoint_sha256=checkpoint_sha256,
        cluster_crf_sha256=cluster_crf_sha256,
    )
    destination = Path(path)
    if os.path.lexists(destination):
        raise FileExistsError(f"refusing to overwrite E1 C2 schedule: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_json_bytes(schedule.to_mapping())
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            raise FileExistsError(
                f"refusing to overwrite E1 C2 schedule: {destination}"
            ) from error
        try:
            directory_fd = os.open(destination.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return _sha256_bytes(encoded)


def load_e1_c2_schedule(
    path: str | Path,
    *,
    expected_file_sha256: str | None = None,
    expected_sha256: str | None = None,
    source_seed: int | None = None,
    policy_sha256: str | None = None,
    source_manifest_sha256: str | None = None,
    checkpoint_sha256: str | None = None,
    cluster_crf_sha256: Mapping[str, str] | None = None,
) -> E1C2PreOutcomeSchedule:
    """Load and fail-closed validate one sealed E1 C2 schedule."""

    destination = Path(path)
    if destination.is_symlink() or not destination.is_file():
        raise E1C2ScheduleContractError(
            "E1 C2 schedule must be a regular non-symlink file"
        )
    encoded = destination.read_bytes()
    actual_file_sha256 = _sha256_bytes(encoded)
    if expected_file_sha256 is not None and actual_file_sha256 != _digest(
        expected_file_sha256, field="expected_file_sha256"
    ):
        raise E1C2ScheduleContractError(
            "schedule file SHA-256 disagrees with expected seal"
        )
    if expected_sha256 is not None and actual_file_sha256 != _digest(
        expected_sha256, field="expected_sha256"
    ):
        raise E1C2ScheduleContractError(
            "schedule file SHA-256 disagrees with expected seal"
        )
    try:
        payload = json.loads(
            encoded.decode("ascii"), parse_constant=_reject_json_constant
        )
    except E1C2ScheduleContractError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
        raise E1C2ScheduleContractError("cannot decode E1 C2 schedule JSON") from error
    schedule = E1C2PreOutcomeSchedule.from_mapping(payload)
    expected_encoded = _canonical_json_bytes(schedule.to_mapping())
    if encoded != expected_encoded:
        raise E1C2ScheduleContractError(
            "schedule file is not canonical JSON bytes"
        )
    validate_e1_c2_schedule(
        schedule,
        source_seed=source_seed,
        policy_sha256=policy_sha256,
        source_manifest_sha256=source_manifest_sha256,
        checkpoint_sha256=checkpoint_sha256,
        cluster_crf_sha256=cluster_crf_sha256,
    )
    return schedule


# Short aliases make the boundary convenient for a runner while retaining
# explicit names for code review and import search.
E1C2ScheduleError = E1C2ScheduleContractError
C2E1ScheduleCluster = E1C2ScheduleCluster
C2E1PreOutcomeSchedule = E1C2PreOutcomeSchedule
seal_schedule = seal_e1_c2_schedule
write_schedule = seal_e1_c2_schedule
load_schedule = load_e1_c2_schedule
read_schedule = load_e1_c2_schedule
validate_schedule = validate_e1_c2_schedule


__all__ = [
    "C2E1PreOutcomeSchedule",
    "C2E1ScheduleCluster",
    "E1C2PreOutcomeSchedule",
    "E1C2ScheduleCluster",
    "E1C2ScheduleContractError",
    "E1C2ScheduleError",
    "E1_C2_CLUSTER_SCHEMA",
    "E1_C2_HORIZON_OFFSETS",
    "E1_C2_SCHEDULE_SCHEMA",
    "E1_C2_SCHEDULE_VERSION",
    "E1_C2_SOURCE_RULES",
    "E1_C2_WORLD_ANCHOR_SCHEMA",
    "e1_c2_world_anchor_sha256",
    "load_e1_c2_schedule",
    "load_schedule",
    "read_schedule",
    "seal_e1_c2_schedule",
    "seal_schedule",
    "validate_e1_c2_schedule",
    "validate_schedule",
    "write_schedule",
]
