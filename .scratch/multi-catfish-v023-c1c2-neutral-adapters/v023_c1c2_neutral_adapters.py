"""Fail-closed binding for the V0.23 C1/C2 source-ablation pairs.

This module is deliberately one layer above the current pre-decision source
selectors.  It accepts *already materialized and authenticated* source
objects, checks their route-specific invariants, and emits an immutable
attestation that can later be composed with the V0.23 five-arm plan.

It does not call a selector, a simulator, a learner, a rollout, or a training
loop.  In particular, the neutral objects must have been produced by the
existing ``sample_c1_cluster_matched_neutral_source`` or
``sample_c2_neutral_source`` seam before they reach this adapter.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

from mcrl.runtime.ee_axis_c1_selector import (
    C1_ACRM_PAIR_RULE,
    C1_CLUSTER_NEUTRAL_SOURCE_RULE,
    C1_INFORMED_SOURCE_RULE,
    C1SourceSelection,
)
from mcrl.runtime.ee_axis_c2_neutral_source import (
    C2_INFORMED_SOURCE_RULE,
    C2_NEUTRAL_SELECTOR_SCHEMA,
    C2_NEUTRAL_SOURCE_RULE,
    C2SourceSelection,
)
from mcrl.runtime.ee_axis_temporal_pairs import TEMPORAL_SOURCE_RULES
from mcrl.errors import MCRLContractError


SCHEMA = "multi-catfish-mcrl-v023-c1-c2-neutral-binding-v2"
"""Schema for this read-only adapter's attestation."""

C1_ROUTE = "C1"
C2_ROUTE = "C2"

_MISSING = object()
_DIGEST_FIELDS = frozenset(
    {
        "world_sha256",
        "seed_sha256",
    }
)
_COLLECTION_FIELDS = frozenset(
    {
        "world_ids",
        "training_seeds",
    }
)
_COMMON_FIELDS = (
    "split",
    "world_ids",
    "training_seeds",
    "world_sha256",
    "seed_sha256",
)
_FORBIDDEN_KEYS = frozenset(
    {
        "test",
        "test_id",
        "test_ids",
        "test_split",
        "test_split_opened",
        "test_world",
        "test_worlds",
        "episode",
        "episodes",
        "episode_id",
        "episode_count",
        "episode_training",
        "physical_episode",
        "outcome",
        "outcomes",
        "reward",
        "rewards",
        "metric",
        "metrics",
        "alias",
        "aliases",
        "source_alias",
        "source_aliases",
        "same_source",
        "head_drop",
        "drop_mode",
    }
)
_C2_INFORMED_ROW_RULES = (
    frozenset(TEMPORAL_SOURCE_RULES) - {C2_NEUTRAL_SOURCE_RULE}
) | {C2_INFORMED_SOURCE_RULE}


class C1C2NeutralBindingError(MCRLContractError):
    """An authenticated C1/C2 source pair violates the binding contract."""


def _canonical_jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, child in value.items():
            if not isinstance(key, str):
                raise C1C2NeutralBindingError(
                    "canonical mappings require string keys"
                )
            result[key] = _canonical_jsonable(child)
        return result
    if isinstance(value, (tuple, list)):
        return [_canonical_jsonable(child) for child in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise C1C2NeutralBindingError(
                "canonical values cannot contain non-finite floats"
            )
        return value
    raise C1C2NeutralBindingError(
        f"unsupported canonical value {type(value).__name__}"
    )


def canonical_sha256(value: object) -> str:
    """Hash one finite canonical JSON value."""

    try:
        encoded = json.dumps(
            _canonical_jsonable(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise C1C2NeutralBindingError(
            "value is not finite canonical ASCII JSON"
        ) from error
    return hashlib.sha256(encoded).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C1C2NeutralBindingError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise C1C2NeutralBindingError(f"{field} must be a non-empty trimmed string")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise C1C2NeutralBindingError(f"{field} must be a positive exact integer")
    return value


def _value(source: object, name: str) -> object:
    if isinstance(source, Mapping):
        return source.get(name, _MISSING)
    return getattr(source, name, _MISSING)


def _as_mapping(value: object, *, field: str) -> Mapping[str, object] | None:
    if value is _MISSING or value is None:
        return None
    if isinstance(value, Mapping):
        return value
    result: dict[str, object] = {}
    for name in _COMMON_FIELDS + (
        "source_rule",
        "row_budget",
        "source_sha256",
        "source_identity",
        "authenticated",
        "test_split_opened",
        "episode_training",
    ):
        child = _value(value, name)
        if child is not _MISSING:
            result[name] = child
    return result or None


def _reject_forbidden_tree(value: object, *, field: str) -> None:
    """Reject control/outcome metadata at the source-binding boundary."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise C1C2NeutralBindingError(
                    f"{field} contains a non-string metadata key"
                )
            normalized = key.strip().lower()
            if normalized in _FORBIDDEN_KEYS:
                raise C1C2NeutralBindingError(
                    f"{field} contains forbidden {key} field"
                )
            _reject_forbidden_tree(child, field=f"{field}.{key}")
    elif isinstance(value, (tuple, list)):
        for index, child in enumerate(value):
            _reject_forbidden_tree(child, field=f"{field}[{index}]")


def _mapping_field_values(source: object, field: str) -> tuple[object, ...]:
    """Return direct and nested provenance values without invoking providers."""

    values: list[object] = []
    direct = _value(source, field)
    if direct is not _MISSING:
        values.append(direct)
    for name in ("common", "metadata", "provenance", "contract"):
        nested = _as_mapping(_value(source, name), field=f"source.{name}")
        if nested is not None and field in nested:
            values.append(nested[field])
    return tuple(values)


def _tuple_value(value: object, *, field: str) -> tuple[object, ...]:
    if isinstance(value, (str, bytes, Mapping)):
        raise C1C2NeutralBindingError(f"{field} must be a sequence")
    try:
        result = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise C1C2NeutralBindingError(f"{field} must be a sequence") from error
    if not result:
        raise C1C2NeutralBindingError(f"{field} must be non-empty")
    return result


def _normalize_common(common: object) -> tuple[dict[str, object], str]:
    if common is None:
        raise C1C2NeutralBindingError("common binding is required")
    if isinstance(common, Mapping):
        raw = dict(common)
        extra = sorted(set(raw) - set(_COMMON_FIELDS))
        if extra:
            raise C1C2NeutralBindingError(
                f"common binding carries non-common route fields: {extra}"
            )
    else:
        raw = {}
        for field in _COMMON_FIELDS:
            value = _value(common, field)
            if value is not _MISSING:
                raw[field] = value
    for field in _COMMON_FIELDS:
        if field not in raw:
            raise C1C2NeutralBindingError(f"common.{field} is missing")

    split = _text(raw["split"], field="common.split")
    if "TEST" in split.upper() or not split.upper().startswith("TRAIN"):
        raise C1C2NeutralBindingError("common.split must be TRAIN-only")

    normalized: dict[str, object] = {"split": split}
    for field in ("world_ids", "training_seeds"):
        values = _tuple_value(raw[field], field=f"common.{field}")
        if len(set(values)) != len(values):
            raise C1C2NeutralBindingError(
                f"common.{field} must contain unique values"
            )
        for index, value in enumerate(values):
            if field == "world_ids":
                if type(value) is int:
                    if value < 0:
                        raise C1C2NeutralBindingError(
                            f"common.world_ids[{index}] must be nonnegative"
                        )
                elif not isinstance(value, str) or not value.strip():
                    raise C1C2NeutralBindingError(
                        f"common.world_ids[{index}] is malformed"
                    )
                elif "TEST" in value.upper():
                    raise C1C2NeutralBindingError(
                        "common.world_ids contains a TEST identifier"
                    )
            elif field == "training_seeds":
                if type(value) is not int or value < 0:
                    raise C1C2NeutralBindingError(
                        f"common.{field}[{index}] must be a nonnegative integer"
                    )
        normalized[field] = values

    for field in _DIGEST_FIELDS:
        normalized[field] = _digest(raw[field], field=f"common.{field}")

    for field, label in (
        ("world_ids", "world_ids"),
        ("training_seeds", "training_seeds"),
    ):
        digest_field = {
            "world_ids": "world_sha256",
            "training_seeds": "seed_sha256",
        }[field]
        expected = canonical_sha256({label: list(normalized[field])})
        if normalized[digest_field] != expected:
            raise C1C2NeutralBindingError(
                f"common.{field} disagrees with common.{digest_field}"
            )

    payload = {
        "schema": SCHEMA,
        "split": normalized["split"],
        "world_ids": list(normalized["world_ids"]),
        "training_seeds": list(normalized["training_seeds"]),
        "world_sha256": normalized["world_sha256"],
        "seed_sha256": normalized["seed_sha256"],
    }
    return normalized, canonical_sha256(payload)


def _authenticate(source: object, *, label: str) -> None:
    if source is None:
        raise C1C2NeutralBindingError(f"{label} source is required")
    if isinstance(source, Mapping):
        _reject_forbidden_tree(source, field=label)
    verify = _value(source, "verify")
    if verify is not _MISSING:
        if not callable(verify):
            raise C1C2NeutralBindingError(f"{label}.verify is not callable")
        try:
            result = verify()
        except Exception as error:  # pragma: no cover - defensive boundary
            raise C1C2NeutralBindingError(
                f"{label} authentication failed"
            ) from error
        if result is False:
            raise C1C2NeutralBindingError(f"{label} authentication returned false")
    authenticated = _value(source, "authenticated")
    if authenticated is not _MISSING and (
        type(authenticated) is not bool or not authenticated
    ):
        raise C1C2NeutralBindingError(f"{label} is not authenticated")
    for name in ("metadata", "provenance", "contract"):
        nested = _as_mapping(_value(source, name), field=f"{label}.{name}")
        if nested is not None:
            _reject_forbidden_tree(nested, field=f"{label}.{name}")

    for field in ("test_split_opened", "episode_training"):
        values = _mapping_field_values(source, field)
        if any(value is not False for value in values):
            raise C1C2NeutralBindingError(
                f"{label} crossed the {field} boundary"
            )


def _check_provenance(source: object, common: Mapping[str, object], *, label: str) -> None:
    """Compare any source-carried common provenance with the shared contract."""

    for field in _COMMON_FIELDS:
        values = _mapping_field_values(source, field)
        for value in values:
            if field in _DIGEST_FIELDS:
                value = _digest(value, field=f"{label}.{field}")
            elif field in _COLLECTION_FIELDS:
                value = _tuple_value(value, field=f"{label}.{field}")
            elif field == "split":
                value = _text(value, field=f"{label}.split")
            elif field == "learner_update_count":
                value = _positive_int(value, field=f"{label}.learner_update_count")
            expected = common[field]
            if value != expected:
                raise C1C2NeutralBindingError(
                    f"{label}.{field} drifts from the common binding"
                )


def _route(source: object, *, expected: str, label: str) -> None:
    for name in ("route", "source_route"):
        value = _value(source, name)
        if value is _MISSING:
            continue
        if str(value).upper() != expected:
            raise C1C2NeutralBindingError(
                f"{label}.{name} is not the {expected} route"
            )


def _source_rule(source: object, *, route: str, label: str) -> str:
    direct = _value(source, "source_rule")
    if direct is not _MISSING:
        return _text(direct, field=f"{label}.source_rule")
    rows = _value(source, "rows")
    if rows is _MISSING:
        raise C1C2NeutralBindingError(f"{label}.source_rule is missing")
    try:
        materialized = tuple(rows)
    except TypeError as error:
        raise C1C2NeutralBindingError(f"{label}.rows is not iterable") from error
    if not materialized:
        raise C1C2NeutralBindingError(f"{label}.rows is empty")
    rules = []
    for index, row in enumerate(materialized):
        value = _value(row, "source_rule")
        if value is _MISSING:
            raise C1C2NeutralBindingError(
                f"{label}.rows[{index}].source_rule is missing"
            )
        rules.append(_text(value, field=f"{label}.rows[{index}].source_rule"))
    if route == C2_ROUTE and all(rule in _C2_INFORMED_ROW_RULES for rule in rules):
        return C2_INFORMED_SOURCE_RULE
    raise C1C2NeutralBindingError(
        f"{label} has no single admitted informed source rule"
    )


def _row_budget(source: object, *, label: str) -> int:
    for name in ("row_budget", "source_row_count", "row_count", "budget"):
        value = _value(source, name)
        if value is not _MISSING:
            return _positive_int(value, field=f"{label}.{name}")
    rows = _value(source, "rows")
    if rows is not _MISSING:
        try:
            return _positive_int(len(rows), field=f"{label}.rows")
        except TypeError as error:
            raise C1C2NeutralBindingError(f"{label}.rows has no length") from error
    raise C1C2NeutralBindingError(f"{label} row budget is missing")


def _digest_for(source: object, supplied: str | None, *, label: str) -> str:
    if supplied is not None:
        expected = _digest(supplied, field=f"{label}.source_sha256")
        for name in (
            "selection_digest",
            "source_sha256",
            "source_digest",
            "content_digest",
            "provider_receipt_sha256",
        ):
            value = _value(source, name)
            if value is _MISSING:
                continue
            actual = _digest(value, field=f"{label}.{name}")
            if actual != expected:
                raise C1C2NeutralBindingError(
                    f"{label} supplied source digest drifts from {name}"
                )
        return expected
    for name in (
        "selection_digest",
        "source_sha256",
        "source_digest",
        "content_digest",
        "provider_receipt_sha256",
    ):
        value = _value(source, name)
        if value is not _MISSING:
            return _digest(value, field=f"{label}.{name}")
    raise C1C2NeutralBindingError(
        f"{label} source digest is missing; implicit hashing is forbidden"
    )


def _identity_for(source: object, supplied: str | None, *, digest: str, label: str) -> str:
    value = supplied
    embedded = _MISSING
    for name in ("source_identity", "artifact_id", "selection_id"):
        candidate = _value(source, name)
        if candidate is not _MISSING:
            embedded = candidate
            break
    if supplied is not None and embedded is not _MISSING and embedded != supplied:
        raise C1C2NeutralBindingError(
            f"{label} supplied source identity drifts from artifact"
        )
    if value is None:
        if embedded is not _MISSING:
            value = embedded
    if value is None:
        # A digest is a safe minimum identity; callers can provide a stronger
        # artifact identity when a receipt contains one.
        value = digest
    return _text(value, field=f"{label}.source_identity")


def _selection_digest(source: object) -> str | None:
    value = _value(source, "selection_digest")
    if value is _MISSING:
        return None
    return _digest(value, field="selection_digest")


def _c1_profile(source: C1SourceSelection, *, label: str) -> tuple[tuple[int, ...], ...]:
    selected_users = tuple(source.selected_focal_users)
    all_rows = tuple(source.all_opportunities)
    by_user: dict[tuple[str, int], int] = {}
    for row in all_rows:
        key = (row.anchor_sha256, row.focal_user)
        by_user[key] = by_user.get(key, 0) + 1
    per_anchor: dict[str, list[int]] = {}
    for anchor, focal_user in selected_users:
        key = (anchor, focal_user)
        if key not in by_user:
            raise C1C2NeutralBindingError(
                f"{label} selected focal user has no source opportunities"
            )
        per_anchor.setdefault(anchor, []).append(by_user[key])
    if not per_anchor:
        raise C1C2NeutralBindingError(f"{label} has no selected C1 clusters")
    return tuple(
        sorted(tuple(sorted(counts)) for counts in per_anchor.values())
    )


def _c2_universe_signature(source: object, *, label: str) -> tuple[object, ...]:
    """Bind an informed/neutral pair to the exact same physical universe."""

    raw = _value(source, "all_opportunities")
    if raw is _MISSING:
        raise C1C2NeutralBindingError(
            f"{label}.all_opportunities is required for universe authentication"
        )
    try:
        rows = tuple(raw)
    except TypeError as error:
        raise C1C2NeutralBindingError(
            f"{label}.all_opportunities is not iterable"
        ) from error
    if not rows:
        raise C1C2NeutralBindingError(f"{label}.all_opportunities is empty")
    keys: list[tuple[object, ...]] = []
    for index, row in enumerate(rows):
        verify = _value(row, "verify")
        if verify is not _MISSING:
            if not callable(verify):
                raise C1C2NeutralBindingError(
                    f"{label}.all_opportunities[{index}].verify is not callable"
                )
            verify()
        opportunity_key = _value(row, "opportunity_key")
        if opportunity_key is _MISSING:
            raise C1C2NeutralBindingError(
                f"{label}.all_opportunities[{index}].opportunity_key is missing"
            )
        key = _tuple_value(
            opportunity_key,
            field=f"{label}.all_opportunities[{index}].opportunity_key",
        )
        keys.append(key)
    if len(set(keys)) != len(keys):
        raise C1C2NeutralBindingError(
            f"{label}.all_opportunities contains duplicate physical opportunities"
        )
    return tuple(sorted(keys))


def _same_lineage(
    informed: object,
    neutral: object,
    *,
    fields: Sequence[str],
    label: str,
) -> None:
    for field in fields:
        left = _value(informed, field)
        right = _value(neutral, field)
        if left is _MISSING or right is _MISSING:
            continue
        if left != right:
            raise C1C2NeutralBindingError(
                f"{label} {field} differs between informed and neutral sources"
            )


def _check_artifact_budget_metadata(
    source: object,
    *,
    initialization_ids: tuple[object, ...],
    initialization_sha256: str,
    learner_config_sha256: str,
    updates: int,
    label: str,
) -> None:
    initializations = len(initialization_ids)
    for field in ("learner_initialization_count", "initialization_count"):
        for value in _mapping_field_values(source, field):
            if _positive_int(value, field=f"{label}.{field}") != initializations:
                raise C1C2NeutralBindingError(
                    f"{label}.{field} drifts from the route-local learner binding"
                )
    for field in ("learner_initialization_ids", "initialization_ids"):
        for value in _mapping_field_values(source, field):
            if _tuple_value(value, field=f"{label}.{field}") != initialization_ids:
                raise C1C2NeutralBindingError(
                    f"{label}.{field} drifts from the route-local learner binding"
                )
    for field, expected in (
        ("learner_initialization_sha256", initialization_sha256),
        ("initialization_sha256", initialization_sha256),
        ("learner_config_sha256", learner_config_sha256),
        ("config_sha256", learner_config_sha256),
    ):
        for value in _mapping_field_values(source, field):
            if _digest(value, field=f"{label}.{field}") != expected:
                raise C1C2NeutralBindingError(
                    f"{label}.{field} drifts from the route-local learner binding"
                )
    for field in ("learner_update_count", "update_budget", "updates"):
        for value in _mapping_field_values(source, field):
            if _positive_int(value, field=f"{label}.{field}") != updates:
                raise C1C2NeutralBindingError(
                    f"{label}.{field} drifts from the route-local learner binding"
                )


def _reject_cross_pair_aliases(
    pairs: Sequence[C1C2SourcePairBinding],
) -> None:
    seen_hashes: dict[str, str] = {}
    seen_identities: dict[str, str] = {}
    for pair in pairs:
        for binding in (pair.informed, pair.neutral):
            label = f"{pair.route}/{binding.mode}"
            prior_hash = seen_hashes.get(binding.source_sha256)
            if prior_hash is not None and prior_hash != label:
                raise C1C2NeutralBindingError(
                    f"source digest aliases distinct bindings: {prior_hash} and {label}"
                )
            seen_hashes[binding.source_sha256] = label
            prior_identity = seen_identities.get(binding.source_identity)
            if prior_identity is not None and prior_identity != label:
                raise C1C2NeutralBindingError(
                    f"source identity aliases distinct bindings: {prior_identity} and {label}"
                )
            seen_identities[binding.source_identity] = label


@dataclass(frozen=True)
class SourceArtifactBinding:
    """An authenticated route source's immutable binding metadata."""

    route: str
    mode: str
    source_rule: str
    source_sha256: str
    source_identity: str
    row_budget: int
    learner_initialization_ids: tuple[object, ...]
    learner_initialization_sha256: str
    learner_config_sha256: str
    learner_update_count: int
    common_sha256: str
    selection_digest: str | None = None

    def verify(self) -> None:
        if self.route not in (C1_ROUTE, C2_ROUTE):
            raise C1C2NeutralBindingError("binding route is not C1 or C2")
        if self.mode not in ("INFORMED", "CLUSTER_MATCHED_NEUTRAL", "EQUAL_BUDGET_NEUTRAL"):
            raise C1C2NeutralBindingError("binding mode is unsupported")
        _text(self.source_rule, field=f"{self.route}.source_rule")
        _digest(self.source_sha256, field=f"{self.route}.source_sha256")
        _text(self.source_identity, field=f"{self.route}.source_identity")
        _positive_int(self.row_budget, field=f"{self.route}.row_budget")
        if not self.learner_initialization_ids:
            raise C1C2NeutralBindingError(
                f"{self.route}.learner_initialization_ids must be non-empty"
            )
        if len(set(self.learner_initialization_ids)) != len(self.learner_initialization_ids):
            raise C1C2NeutralBindingError(
                f"{self.route}.learner_initialization_ids must be unique"
            )
        _digest(
            self.learner_initialization_sha256,
            field=f"{self.route}.learner_initialization_sha256",
        )
        expected_initialization_sha256 = canonical_sha256(
            {"learner_initialization_ids": list(self.learner_initialization_ids)}
        )
        if self.learner_initialization_sha256 != expected_initialization_sha256:
            raise C1C2NeutralBindingError(
                f"{self.route}.learner_initialization_sha256 disagrees with IDs"
            )
        _digest(
            self.learner_config_sha256,
            field=f"{self.route}.learner_config_sha256",
        )
        _positive_int(
            self.learner_update_count,
            field=f"{self.route}.learner_update_count",
        )
        _digest(self.common_sha256, field=f"{self.route}.common_sha256")
        if self.selection_digest is not None:
            _digest(self.selection_digest, field=f"{self.route}.selection_digest")

    def to_dict(self) -> dict[str, object]:
        self.verify()
        return {
            "route": self.route,
            "mode": self.mode,
            "source_rule": self.source_rule,
            "source_sha256": self.source_sha256,
            "source_identity": self.source_identity,
            "row_budget": self.row_budget,
            "learner_initialization_count": len(self.learner_initialization_ids),
            "learner_initialization_ids": list(self.learner_initialization_ids),
            "learner_initialization_sha256": self.learner_initialization_sha256,
            "learner_config_sha256": self.learner_config_sha256,
            "learner_update_count": self.learner_update_count,
            "common_sha256": self.common_sha256,
            "selection_digest": self.selection_digest,
        }


@dataclass(frozen=True)
class C1C2SourcePairBinding:
    """One C1 or C2 informed/neutral pair with equal learner budgets."""

    route: str
    informed: SourceArtifactBinding
    neutral: SourceArtifactBinding
    common_sha256: str
    structural_signature: tuple[object, ...] = ()

    @property
    def row_budget(self) -> int:
        return self.informed.row_budget

    def verify(self) -> None:
        if self.route not in (C1_ROUTE, C2_ROUTE):
            raise C1C2NeutralBindingError("pair route is not C1 or C2")
        self.informed.verify()
        self.neutral.verify()
        if self.informed.route != self.route or self.neutral.route != self.route:
            raise C1C2NeutralBindingError("pair route disagrees with its bindings")
        if self.informed.mode != "INFORMED":
            raise C1C2NeutralBindingError("pair informed binding is not INFORMED")
        expected_neutral = {
            C1_ROUTE: "CLUSTER_MATCHED_NEUTRAL",
            C2_ROUTE: "EQUAL_BUDGET_NEUTRAL",
        }[self.route]
        if self.neutral.mode != expected_neutral:
            raise C1C2NeutralBindingError(
                f"{self.route} neutral binding is not {expected_neutral}"
            )
        if self.common_sha256 != self.informed.common_sha256 or self.common_sha256 != self.neutral.common_sha256:
            raise C1C2NeutralBindingError("pair common binding drifted")
        if self.informed.row_budget != self.neutral.row_budget:
            raise C1C2NeutralBindingError(
                f"{self.route} informed and neutral row budgets differ"
            )
        if self.informed.learner_initialization_ids != self.neutral.learner_initialization_ids:
            raise C1C2NeutralBindingError(
                f"{self.route} initialization IDs differ"
            )
        if (
            self.informed.learner_initialization_sha256
            != self.neutral.learner_initialization_sha256
        ):
            raise C1C2NeutralBindingError(
                f"{self.route} initialization digests differ"
            )
        if self.informed.learner_config_sha256 != self.neutral.learner_config_sha256:
            raise C1C2NeutralBindingError(f"{self.route} learner configs differ")
        if self.informed.learner_update_count != self.neutral.learner_update_count:
            raise C1C2NeutralBindingError(f"{self.route} update budgets differ")
        if self.informed.source_sha256 == self.neutral.source_sha256:
            raise C1C2NeutralBindingError(
                f"{self.route} neutral source aliases the informed digest"
            )
        if self.informed.source_identity == self.neutral.source_identity:
            raise C1C2NeutralBindingError(
                f"{self.route} neutral source aliases the informed identity"
            )
        _digest(self.common_sha256, field=f"{self.route}.common_sha256")

    def to_dict(self) -> dict[str, object]:
        self.verify()
        return {
            "route": self.route,
            "common_sha256": self.common_sha256,
            "informed": self.informed.to_dict(),
            "neutral": self.neutral.to_dict(),
            "structural_signature": list(self.structural_signature),
        }


@dataclass(frozen=True)
class C1C2SourceBindingBundle:
    """The C1 and C2 pair attestations ready for five-arm composition."""

    schema: str
    common_sha256: str
    c1: C1C2SourcePairBinding
    c2: C1C2SourcePairBinding

    def verify(self) -> None:
        if self.schema != SCHEMA:
            raise C1C2NeutralBindingError("unsupported C1/C2 binding schema")
        _digest(self.common_sha256, field="common_sha256")
        self.c1.verify()
        self.c2.verify()
        _reject_cross_pair_aliases((self.c1, self.c2))
        if self.c1.route != C1_ROUTE or self.c2.route != C2_ROUTE:
            raise C1C2NeutralBindingError("bundle must contain C1 and C2 exactly once")
        for pair in (self.c1, self.c2):
            if pair.common_sha256 != self.common_sha256:
                raise C1C2NeutralBindingError("bundle common binding drifted")

    def to_dict(self) -> dict[str, object]:
        self.verify()
        return {
            "schema": self.schema,
            "common_sha256": self.common_sha256,
            "route_learner_budgets": {
                "C1": {
                    "initialization_count": len(self.c1.informed.learner_initialization_ids),
                    "update_count": self.c1.informed.learner_update_count,
                },
                "C2": {
                    "initialization_count": len(self.c2.informed.learner_initialization_ids),
                    "update_count": self.c2.informed.learner_update_count,
                },
            },
            "pairs": [self.c1.to_dict(), self.c2.to_dict()],
        }


def _bind_route_source(
    source: object,
    *,
    route: str,
    mode: str,
    expected_rule: str,
    common: Mapping[str, object],
    common_sha256: str,
    row_budget: int | None,
    source_sha256: str | None,
    source_identity: str | None,
    learner_initialization_ids: tuple[object, ...],
    learner_initialization_sha256: str,
    learner_config_sha256: str,
    learner_update_count: int,
    label: str,
) -> SourceArtifactBinding:
    _authenticate(source, label=label)
    _check_provenance(source, common, label=label)
    _check_artifact_budget_metadata(
        source,
        initialization_ids=learner_initialization_ids,
        initialization_sha256=learner_initialization_sha256,
        learner_config_sha256=learner_config_sha256,
        updates=learner_update_count,
        label=label,
    )
    _route(source, expected=route, label=label)
    actual_rule = _source_rule(source, route=route, label=label)
    if actual_rule != expected_rule:
        raise C1C2NeutralBindingError(
            f"{label}.source_rule expected {expected_rule}, got {actual_rule}"
        )
    actual_budget = _row_budget(source, label=label)
    if row_budget is not None and row_budget != actual_budget:
        raise C1C2NeutralBindingError(f"{label} row budget disagrees with artifact")
    digest = _digest_for(source, source_sha256, label=label)
    identity = _identity_for(source, source_identity, digest=digest, label=label)
    selection_digest = _selection_digest(source)
    binding = SourceArtifactBinding(
        route=route,
        mode=mode,
        source_rule=actual_rule,
        source_sha256=digest,
        source_identity=identity,
        row_budget=actual_budget,
        learner_initialization_ids=learner_initialization_ids,
        learner_initialization_sha256=learner_initialization_sha256,
        learner_config_sha256=learner_config_sha256,
        learner_update_count=learner_update_count,
        common_sha256=common_sha256,
        selection_digest=selection_digest,
    )
    binding.verify()
    return binding


def bind_c1_c2_source_pairs(
    *,
    common: object,
    c1_informed: C1SourceSelection,
    c1_cluster_neutral: C1SourceSelection,
    c2_informed: object,
    c2_equal_budget_neutral: C2SourceSelection,
    c1_informed_sha256: str,
    c1_neutral_sha256: str,
    c2_informed_sha256: str,
    c2_neutral_sha256: str | None = None,
    c1_informed_identity: str | None = None,
    c1_neutral_identity: str | None = None,
    c2_informed_identity: str | None = None,
    c2_neutral_identity: str | None = None,
    c1_learner_initialization_ids: Sequence[object],
    c1_learner_config_sha256: str,
    c1_learner_update_count: int,
    c2_learner_initialization_ids: Sequence[object],
    c2_learner_config_sha256: str,
    c2_learner_update_count: int,
) -> C1C2SourceBindingBundle:
    """Bind the authenticated C1/C2 informed and neutral source objects.

    The C1 neutral object must be a result of
    ``sample_c1_cluster_matched_neutral_source`` and the C2 neutral object
    must be a result of ``sample_c2_neutral_source``.  This function does not
    call either sampler; it only re-verifies the immutable result and checks
    pair/budget/provenance equality.
    """

    if not isinstance(c1_informed, C1SourceSelection):
        raise C1C2NeutralBindingError("c1_informed must be C1SourceSelection")
    if not isinstance(c1_cluster_neutral, C1SourceSelection):
        raise C1C2NeutralBindingError(
            "c1_cluster_neutral must be C1SourceSelection"
        )
    if not isinstance(c2_equal_budget_neutral, C2SourceSelection):
        raise C1C2NeutralBindingError(
            "c2_equal_budget_neutral must be C2SourceSelection"
        )
    if c1_informed is c1_cluster_neutral or c2_informed is c2_equal_budget_neutral:
        raise C1C2NeutralBindingError("informed and neutral artifacts may not alias")
    common_values, common_sha256 = _normalize_common(common)
    c1_initializations = _tuple_value(
        c1_learner_initialization_ids,
        field="c1_learner_initialization_ids",
    )
    c2_initializations = _tuple_value(
        c2_learner_initialization_ids,
        field="c2_learner_initialization_ids",
    )
    if len(set(c1_initializations)) != len(c1_initializations):
        raise C1C2NeutralBindingError("C1 learner initialization IDs must be unique")
    if len(set(c2_initializations)) != len(c2_initializations):
        raise C1C2NeutralBindingError("C2 learner initialization IDs must be unique")
    c1_initialization_sha256 = canonical_sha256(
        {"learner_initialization_ids": list(c1_initializations)}
    )
    c2_initialization_sha256 = canonical_sha256(
        {"learner_initialization_ids": list(c2_initializations)}
    )
    c1_config_sha256 = _digest(
        c1_learner_config_sha256, field="c1_learner_config_sha256"
    )
    c2_config_sha256 = _digest(
        c2_learner_config_sha256, field="c2_learner_config_sha256"
    )
    c1_updates = _positive_int(
        c1_learner_update_count, field="c1_learner_update_count"
    )
    c2_updates = _positive_int(
        c2_learner_update_count, field="c2_learner_update_count"
    )

    _same_lineage(
        c1_informed,
        c1_cluster_neutral,
        fields=(
            "selector_schema",
            "acrm_pair_rule",
            "partition",
            "source_manifest_sha256",
            "checkpoint_sha256",
            "state_schema",
            "state_schema_sha256",
        ),
        label="C1 pair",
    )
    if c1_informed.acrm_pair_rule != C1_ACRM_PAIR_RULE:
        raise C1C2NeutralBindingError("C1 ACRM pair rule is stale")
    if _c1_profile(c1_informed, label="C1 informed") != _c1_profile(
        c1_cluster_neutral, label="C1 neutral"
    ):
        raise C1C2NeutralBindingError(
            "C1 neutral does not preserve the informed cluster profile"
        )

    _same_lineage(
        c2_informed,
        c2_equal_budget_neutral,
        fields=(
            "horizon_steps",
            "release_grammar",
            "source_manifest_sha256",
            "checkpoint_sha256",
            "state_schema",
            "state_schema_sha256",
        ),
        label="C2 pair",
    )
    if c2_equal_budget_neutral.selector_schema != C2_NEUTRAL_SELECTOR_SCHEMA:
        raise C1C2NeutralBindingError("C2 neutral selector schema is stale")
    informed_budget = _row_budget(c2_informed, label="C2 informed")
    if c2_equal_budget_neutral.informed_budget != informed_budget:
        raise C1C2NeutralBindingError(
            "C2 neutral informed_budget does not match C2 informed rows"
        )
    c1_i = _bind_route_source(
        c1_informed,
        route=C1_ROUTE,
        mode="INFORMED",
        expected_rule=C1_INFORMED_SOURCE_RULE,
        common=common_values,
        common_sha256=common_sha256,
        row_budget=None,
        source_sha256=c1_informed_sha256,
        source_identity=c1_informed_identity,
        learner_initialization_ids=c1_initializations,
        learner_initialization_sha256=c1_initialization_sha256,
        learner_config_sha256=c1_config_sha256,
        learner_update_count=c1_updates,
        label="C1 informed",
    )
    c1_n = _bind_route_source(
        c1_cluster_neutral,
        route=C1_ROUTE,
        mode="CLUSTER_MATCHED_NEUTRAL",
        expected_rule=C1_CLUSTER_NEUTRAL_SOURCE_RULE,
        common=common_values,
        common_sha256=common_sha256,
        row_budget=c1_i.row_budget,
        source_sha256=c1_neutral_sha256,
        source_identity=c1_neutral_identity,
        learner_initialization_ids=c1_initializations,
        learner_initialization_sha256=c1_initialization_sha256,
        learner_config_sha256=c1_config_sha256,
        learner_update_count=c1_updates,
        label="C1 cluster neutral",
    )
    c2_i = _bind_route_source(
        c2_informed,
        route=C2_ROUTE,
        mode="INFORMED",
        expected_rule=C2_INFORMED_SOURCE_RULE,
        common=common_values,
        common_sha256=common_sha256,
        row_budget=None,
        source_sha256=c2_informed_sha256,
        source_identity=c2_informed_identity,
        learner_initialization_ids=c2_initializations,
        learner_initialization_sha256=c2_initialization_sha256,
        learner_config_sha256=c2_config_sha256,
        learner_update_count=c2_updates,
        label="C2 informed",
    )
    c2_n = _bind_route_source(
        c2_equal_budget_neutral,
        route=C2_ROUTE,
        mode="EQUAL_BUDGET_NEUTRAL",
        expected_rule=C2_NEUTRAL_SOURCE_RULE,
        common=common_values,
        common_sha256=common_sha256,
        row_budget=c2_i.row_budget,
        source_sha256=c2_neutral_sha256,
        source_identity=c2_neutral_identity,
        learner_initialization_ids=c2_initializations,
        learner_initialization_sha256=c2_initialization_sha256,
        learner_config_sha256=c2_config_sha256,
        learner_update_count=c2_updates,
        label="C2 equal-budget neutral",
    )
    c2_universe = _c2_universe_signature(c2_informed, label="C2 informed")
    if c2_universe != _c2_universe_signature(
        c2_equal_budget_neutral, label="C2 neutral"
    ):
        raise C1C2NeutralBindingError(
            "C2 informed and neutral sources do not share the exact physical universe"
        )
    c1_pair = C1C2SourcePairBinding(
        route=C1_ROUTE,
        informed=c1_i,
        neutral=c1_n,
        common_sha256=common_sha256,
        structural_signature=("cluster_profile", _c1_profile(c1_informed, label="C1 informed")),
    )
    c2_pair = C1C2SourcePairBinding(
        route=C2_ROUTE,
        informed=c2_i,
        neutral=c2_n,
        common_sha256=common_sha256,
        structural_signature=(
            "horizon_steps",
            c2_equal_budget_neutral.horizon_steps,
            "universe_sha256",
            canonical_sha256({"opportunity_keys": list(c2_universe)}),
        ),
    )
    bundle = C1C2SourceBindingBundle(
        schema=SCHEMA,
        common_sha256=common_sha256,
        c1=c1_pair,
        c2=c2_pair,
    )
    bundle.verify()
    return bundle


__all__ = [
    "C1C2NeutralBindingError",
    "C1C2SourceBindingBundle",
    "C1C2SourcePairBinding",
    "SCHEMA",
    "SourceArtifactBinding",
    "bind_c1_c2_source_pairs",
    "canonical_sha256",
]
