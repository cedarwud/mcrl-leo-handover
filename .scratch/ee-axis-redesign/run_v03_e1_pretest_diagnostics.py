#!/usr/bin/env python3
"""Train/validation-only E1 diagnostics for possible false skill.

This file is deliberately outside the sealed source-generation and ladder
closures.  It is a post-ladder, no-EE diagnostic: it compares the same three
initializations at rung zero and every trained rung, makes the zero and
action-only baselines explicit, and audits the action-incidence design.  The
claim-bearing command-line path below accepts only the sealed ladder index and
never has an opener seam for the E1 test split.
"""

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (HERE, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v03_e1_fresh_sources as sources  # noqa: E402
import run_v03_e1_validation_ladder as ladder_driver  # noqa: E402
from mcrl.algorithms.ee_axis_pairwise import (  # noqa: E402
    EEAxisPairBatch,
    EEAxisPairwiseConfig,
    EEAxisPairwiseTrainer,
)
from mcrl.runtime.ee_axis_e1_c2_schedule import (  # noqa: E402
    e1_c2_world_anchor_sha256,
)
from mcrl.runtime.ee_axis_e1_ladder import (  # noqa: E402
    E1_LADDER_CHECKPOINT_SCHEMA,
    E1_UPDATE_RUNGS,
)
from mcrl.runtime.ee_axis_e1_split import E1PairIndexRow  # noqa: E402
from mcrl.runtime.ee_axis_e1_statistics import E1StatisticsError  # noqa: E402
from mcrl.runtime.ee_axis_instrument_validity import (  # noqa: E402
    ObservabilityCollisions,
    compute_observability_collisions,
)
from mcrl.runtime.ee_axis_opening_dataset import read_opening_dataset  # noqa: E402
from mcrl.runtime.ee_axis_reference_probe import (  # noqa: E402
    E1ReferenceProbeConfig,
    E1ReferenceProbeResult,
    run_reference_action_probe,
)
from mcrl.runtime.ee_axis_temporal_dataset import read_temporal_dataset  # noqa: E402


CLAIM_CEILING = "NO_EE_PRETEST_DIAGNOSTIC_ONLY"
ROUTES = ("C1", "C2", "C3")
DIAGNOSTIC_CPU_THREADS = 1


class E1PretestDiagnosticError(RuntimeError):
    """A train/validation-only diagnostic boundary was violated."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise E1PretestDiagnosticError(f"{field} must be lowercase SHA-256")
    return value


def _diagnostic_code_manifest() -> dict[str, object]:
    paths = (
        Path(__file__),
        HERE / "run_v03_e1_fresh_sources.py",
        HERE / "run_v03_e1_validation_ladder.py",
        REPO / "src" / "mcrl" / "algorithms" / "ee_axis_pairwise.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_e1_c2_schedule.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_e1_ladder.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_e1_split.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_e1_statistics.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_instrument_validity.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_opening_dataset.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_opening_pairs.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_reference_probe.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_temporal_dataset.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_temporal_pairs.py",
        REPO / "src" / "mcrl" / "runtime" / "finiteness.py",
        REPO / "src" / "mcrl" / "runtime" / "q_network.py",
    )
    if any(not path.is_file() for path in paths):
        raise E1PretestDiagnosticError("diagnostic code closure is incomplete")
    rows = [
        {
            "path": str(path.resolve().relative_to(REPO.resolve())),
            "sha256": _sha256_file(path),
        }
        for path in sorted(paths, key=lambda item: str(item))
    ]
    body = {
        "schema": "multi-catfish-mcrl-v03-e1-pretest-diagnostic-code-v1",
        "files": rows,
    }
    return {**body, "manifest_sha256": _canonical_sha256(body)}


def _validated_train_validation_entries(
    *, index: Mapping[str, object], expected_seed_split: Mapping[int, str]
) -> tuple[tuple[int, str, Mapping[str, object]], ...]:
    """Validate all split identities before returning any dataset pathname."""

    if not isinstance(index, Mapping):
        raise E1PretestDiagnosticError("ladder index must be a mapping")
    raw_split = index.get("seed_split")
    if not isinstance(raw_split, Mapping):
        raise E1PretestDiagnosticError("ladder index seed split is malformed")
    observed_split = dict(raw_split)
    expected = {str(seed): split for seed, split in sorted(expected_seed_split.items())}
    if (
        any(split not in {"train", "validation"} for split in observed_split.values())
        or observed_split != expected
    ):
        raise E1PretestDiagnosticError(
            "pre-test diagnostics require the exact train/validation seed split"
        )
    if (
        index.get("schema")
        != "multi-catfish-mcrl-v03-e1-ladder-source-index-v1"
        or index.get("test_split_opened") is not False
    ):
        raise E1PretestDiagnosticError("ladder index violates the pre-test boundary")
    datasets = index.get("datasets")
    if not isinstance(datasets, Mapping) or set(datasets) != set(expected):
        raise E1PretestDiagnosticError("ladder dataset map is incomplete")
    entries: list[tuple[int, str, Mapping[str, object]]] = []
    for seed_text, split in expected.items():
        entry = datasets[seed_text]
        if not isinstance(entry, Mapping):
            raise E1PretestDiagnosticError("ladder dataset entry is malformed")
        seed = int(seed_text)
        if entry.get("opening_path") != f"opening-{seed}.json" or entry.get(
            "temporal_path"
        ) != f"temporal-{seed}.json":
            raise E1PretestDiagnosticError("ladder dataset basename changed")
        entries.append((seed, split, entry))
    return tuple(entries)


def _verify_checkpoint_payload(
    payload: object,
    *,
    expected_spec: Mapping[str, object],
    expected_batch_digests: Mapping[str, object],
    initialization_seed: int,
    rung: int,
) -> Mapping[str, object]:
    if not isinstance(payload, Mapping):
        raise E1PretestDiagnosticError("ladder checkpoint payload is malformed")
    if payload.get("test_split_opened") is not False:
        raise E1PretestDiagnosticError("ladder checkpoint claims test was opened")
    if payload.get("held_out_ee_evaluated") is not False:
        raise E1PretestDiagnosticError("ladder checkpoint claims an EE endpoint")
    if (
        payload.get("schema") != E1_LADDER_CHECKPOINT_SCHEMA
        or _canonical_sha256(payload.get("spec"))
        != _canonical_sha256(expected_spec)
        or _canonical_sha256(payload.get("batch_digests"))
        != _canonical_sha256(expected_batch_digests)
        or payload.get("initialization_seed") != initialization_seed
        or payload.get("completed_updates_per_head") != rung
    ):
        raise E1PretestDiagnosticError("ladder checkpoint authority mismatch")
    trainer = payload.get("trainer")
    if (
        not isinstance(trainer, Mapping)
        or trainer.get("train_seed") != initialization_seed
        or trainer.get("update_count") != rung * len(ROUTES)
    ):
        raise E1PretestDiagnosticError("ladder trainer checkpoint mismatch")
    return trainer


@dataclass(frozen=True)
class E1RidgeSensitivity:
    penalty: float
    validation_mae: float
    max_prediction_delta_from_minimum_norm: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class E1ActionOnlyDesignDiagnostics:
    train_rows: int
    validation_rows: int
    incidence_rank: int
    active_actions: int
    connected_components: int
    gauge_nullity: int
    residual_degrees_of_freedom: int
    low_residual_df: bool
    validation_supported_rows: int
    validation_unsupported_rows: int
    gauge_fixed_max_prediction_delta: float
    minimum_norm_validation_mae: float
    minimum_norm_validation_prediction: np.ndarray
    ridge_sensitivity: tuple[E1RidgeSensitivity, ...]

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["minimum_norm_validation_prediction"] = (
            self.minimum_norm_validation_prediction.tolist()
        )
        payload["ridge_sensitivity"] = [row.as_dict() for row in self.ridge_sensitivity]
        return payload


@dataclass(frozen=True)
class E1ValidationScore:
    model_mae: float
    constant_zero_mae: float
    action_only_mae: float
    skill_vs_constant_zero: float | None
    skill_vs_action_only: float | None

    def as_dict(self) -> dict[str, float | None]:
        return asdict(self)


@dataclass(frozen=True)
class E1RungComparison:
    rung: int
    is_untrained: bool
    model_mae_delta_from_untrained: float
    skill_vs_zero_delta_from_untrained: float | None
    skill_vs_action_delta_from_untrained: float | None

    def as_dict(self) -> dict[str, int | bool | float | None]:
        return asdict(self)


@dataclass(frozen=True)
class E1DiagnosticPairRow:
    """Authenticated train/validation row with route-aware index identity."""

    split: str
    index: E1PairIndexRow
    state: np.ndarray
    action_mask: np.ndarray
    normalized_target: float
    policy_sha256: str
    comparison_sha256: str

    def verify(self) -> None:
        if self.split not in {"train", "validation"}:
            raise E1PretestDiagnosticError(
                "pre-test diagnostics accept only train or validation rows"
            )
        self.index.verify()
        state = np.asarray(self.state, dtype=np.float32)
        mask = np.asarray(self.action_mask)
        if state.ndim != 1 or state.size < 1 or not np.all(np.isfinite(state)):
            raise E1PretestDiagnosticError("diagnostic state must be a finite vector")
        if mask.shape != (len(self.index.action_mask),) or mask.dtype != np.bool_:
            raise E1PretestDiagnosticError(
                "diagnostic mask must be boolean and match index action_dim"
            )
        if tuple(bool(value) for value in mask.tolist()) != self.index.action_mask:
            raise E1PretestDiagnosticError("diagnostic mask differs from sealed index")
        if not math.isfinite(float(self.normalized_target)):
            raise E1PretestDiagnosticError("diagnostic target must be finite")
        for name, digest in (
            ("policy_sha256", self.policy_sha256),
            ("comparison_sha256", self.comparison_sha256),
        ):
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise E1PretestDiagnosticError(f"{name} must be lowercase SHA-256")


def persistent_collision_report(
    rows: Sequence[E1DiagnosticPairRow], *, route: str
) -> ObservabilityCollisions:
    """Census G-O exact-key collisions across train plus validation rows."""

    selected = tuple(rows)
    if not selected:
        raise E1PretestDiagnosticError(f"{route} collision census has no rows")
    if route not in ROUTES:
        raise E1PretestDiagnosticError(f"route must be one of {ROUTES}")
    for row in selected:
        row.verify()
        if row.index.route != route:
            raise E1PretestDiagnosticError("collision census mixes routes")
    try:
        return compute_observability_collisions(
            routes=[route] * len(selected),
            policy_digests=[row.policy_sha256 for row in selected],
            states=np.stack(
                [np.asarray(row.state, dtype=np.float32) for row in selected]
            ),
            masks=np.stack(
                [np.asarray(row.action_mask, dtype=np.bool_) for row in selected]
            ),
            reference_actions=np.asarray(
                [row.index.reference_action for row in selected], dtype=np.int64
            ),
            candidate_actions=np.asarray(
                [row.index.candidate_action for row in selected], dtype=np.int64
            ),
            targets=np.asarray(
                [row.normalized_target for row in selected], dtype=np.float64
            ),
        )
    except (TypeError, ValueError) as error:
        raise E1PretestDiagnosticError(
            f"{route} collision census input is invalid"
        ) from error


def _pair_arrays(
    batch: EEAxisPairBatch, *, kappa_bits: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    if not math.isfinite(float(kappa_bits)) or float(kappa_bits) <= 0.0:
        raise E1PretestDiagnosticError("kappa_bits must be finite and positive")
    states = np.asarray(batch.states)
    masks = np.asarray(batch.action_masks)
    if states.ndim != 2 or masks.ndim != 2:
        raise E1PretestDiagnosticError("pair batch must contain matrix states and masks")
    batch.validate(state_dim=states.shape[1], action_dim=masks.shape[1])
    reference = np.asarray(batch.reference_actions, dtype=np.int64)
    candidate = np.asarray(batch.candidate_actions, dtype=np.int64)
    target = np.asarray(batch.target_surplus_bits, dtype=np.float64) / float(kappa_bits)
    if np.any(reference == candidate):
        raise E1PretestDiagnosticError("action-only contrasts must compare two actions")
    return reference, candidate, target, int(masks.shape[1])


def _incidence(
    reference: np.ndarray, candidate: np.ndarray, *, action_dim: int
) -> np.ndarray:
    design = np.zeros((reference.size, action_dim), dtype=np.float64)
    rows = np.arange(reference.size)
    design[rows, reference] = -1.0
    design[rows, candidate] = 1.0
    return design


def _action_components(
    reference: np.ndarray, candidate: np.ndarray, *, action_dim: int
) -> tuple[np.ndarray, tuple[tuple[int, ...], ...]]:
    adjacency = [set() for _ in range(action_dim)]
    for left, right in zip(reference.tolist(), candidate.tolist(), strict=True):
        adjacency[left].add(right)
        adjacency[right].add(left)
    component_ids = np.full(action_dim, -1, dtype=np.int64)
    components: list[tuple[int, ...]] = []
    for start in range(action_dim):
        if component_ids[start] >= 0 or not adjacency[start]:
            continue
        stack = [start]
        members: list[int] = []
        component_id = len(components)
        component_ids[start] = component_id
        while stack:
            action = stack.pop()
            members.append(action)
            for neighbor in sorted(adjacency[action]):
                if component_ids[neighbor] < 0:
                    component_ids[neighbor] = component_id
                    stack.append(neighbor)
        components.append(tuple(sorted(members)))
    return component_ids, tuple(components)


def action_only_design_diagnostics(
    *,
    train_batch: EEAxisPairBatch,
    validation_batch: EEAxisPairBatch,
    kappa_bits: float,
    ridge_penalties: Sequence[float] = (1e-8, 1e-6, 1e-4, 1e-2, 1.0),
) -> E1ActionOnlyDesignDiagnostics:
    """Fit and stress-test the state-independent action-incidence baseline."""

    train_r, train_c, train_y, action_dim = _pair_arrays(
        train_batch, kappa_bits=kappa_bits
    )
    val_r, val_c, val_y, validation_action_dim = _pair_arrays(
        validation_batch, kappa_bits=kappa_bits
    )
    if validation_action_dim != action_dim:
        raise E1PretestDiagnosticError("train and validation action dimensions differ")
    penalties = tuple(float(value) for value in ridge_penalties)
    if not penalties or any(not math.isfinite(value) or value <= 0.0 for value in penalties):
        raise E1PretestDiagnosticError("ridge penalties must be finite and positive")

    train_x = _incidence(train_r, train_c, action_dim=action_dim)
    validation_x = _incidence(val_r, val_c, action_dim=action_dim)
    coefficients, _residuals, rank, _singular = np.linalg.lstsq(
        train_x, train_y, rcond=None
    )
    minimum_norm_prediction = validation_x @ coefficients
    component_ids, components = _action_components(
        train_r, train_c, action_dim=action_dim
    )
    supported = np.logical_and(
        component_ids[val_r] >= 0,
        component_ids[val_r] == component_ids[val_c],
    )
    if not np.all(supported):
        raise E1PretestDiagnosticError(
            "validation action contrast lacks train-incidence graph support"
        )

    # Fix one coefficient to zero in every connected component.  Only action
    # differences are identified, so its validation predictions must equal the
    # Moore-Penrose minimum-norm solution up to numerical roundoff.
    gauges = {component[0] for component in components}
    free_columns = [
        action
        for action in range(action_dim)
        if component_ids[action] >= 0 and action not in gauges
    ]
    gauge_coefficients = np.zeros(action_dim, dtype=np.float64)
    if free_columns:
        solved, _residuals, _rank, _singular = np.linalg.lstsq(
            train_x[:, free_columns], train_y, rcond=None
        )
        gauge_coefficients[free_columns] = solved
    gauge_prediction = validation_x @ gauge_coefficients
    gauge_delta = float(np.max(np.abs(gauge_prediction - minimum_norm_prediction)))

    ridge_rows: list[E1RidgeSensitivity] = []
    gram = train_x.T @ train_x
    rhs = train_x.T @ train_y
    identity = np.eye(action_dim, dtype=np.float64)
    for penalty in penalties:
        ridge_coefficients = np.linalg.solve(gram + penalty * identity, rhs)
        prediction = validation_x @ ridge_coefficients
        ridge_rows.append(
            E1RidgeSensitivity(
                penalty=penalty,
                validation_mae=float(np.mean(np.abs(prediction - val_y))),
                max_prediction_delta_from_minimum_norm=float(
                    np.max(np.abs(prediction - minimum_norm_prediction))
                ),
            )
        )

    residual_df = int(train_y.size - int(rank))
    active_actions = int(np.count_nonzero(component_ids >= 0))
    return E1ActionOnlyDesignDiagnostics(
        train_rows=int(train_y.size),
        validation_rows=int(val_y.size),
        incidence_rank=int(rank),
        active_actions=active_actions,
        connected_components=len(components),
        gauge_nullity=len(components),
        residual_degrees_of_freedom=residual_df,
        low_residual_df=bool(residual_df <= max(2, int(rank))),
        validation_supported_rows=int(np.count_nonzero(supported)),
        validation_unsupported_rows=int(supported.size - np.count_nonzero(supported)),
        gauge_fixed_max_prediction_delta=gauge_delta,
        minimum_norm_validation_mae=float(
            np.mean(np.abs(minimum_norm_prediction - val_y))
        ),
        minimum_norm_validation_prediction=minimum_norm_prediction,
        ridge_sensitivity=tuple(ridge_rows),
    )


def score_validation_surface(
    *,
    validation_batch: EEAxisPairBatch,
    q_surface: np.ndarray,
    action_only_prediction: np.ndarray,
    kappa_bits: float,
) -> E1ValidationScore:
    """Score one route/rung against both explicit non-neural baselines."""

    reference, candidate, target, action_dim = _pair_arrays(
        validation_batch, kappa_bits=kappa_bits
    )
    q = np.asarray(q_surface, dtype=np.float64)
    if q.shape != (target.size, action_dim) or not np.all(np.isfinite(q)):
        raise E1PretestDiagnosticError(
            "q_surface must be finite shape (validation rows, action_dim)"
        )
    action_prediction = np.asarray(action_only_prediction, dtype=np.float64)
    if action_prediction.shape != target.shape or not np.all(
        np.isfinite(action_prediction)
    ):
        raise E1PretestDiagnosticError(
            "action-only prediction must be a finite validation-row vector"
        )
    rows = np.arange(target.size)
    model_prediction = q[rows, candidate] - q[rows, reference]
    model_mae = float(np.mean(np.abs(model_prediction - target)))
    zero_mae = float(np.mean(np.abs(target)))
    action_mae = float(np.mean(np.abs(action_prediction - target)))

    def _skill(baseline: float) -> float | None:
        return float((baseline - model_mae) / baseline) if baseline > 0.0 else None

    return E1ValidationScore(
        model_mae=model_mae,
        constant_zero_mae=zero_mae,
        action_only_mae=action_mae,
        skill_vs_constant_zero=_skill(zero_mae),
        skill_vs_action_only=_skill(action_mae),
    )


def compare_rungs_to_untrained(
    scores_by_rung: Mapping[int, E1ValidationScore],
) -> dict[int, E1RungComparison]:
    """Compare every trained rung to the same-init rung-zero surface."""

    if 0 not in scores_by_rung or not scores_by_rung:
        raise E1PretestDiagnosticError("rung-zero score is mandatory")
    if any(type(rung) is not int or rung < 0 for rung in scores_by_rung):
        raise E1PretestDiagnosticError("rungs must be nonnegative integers")
    if any(not isinstance(score, E1ValidationScore) for score in scores_by_rung.values()):
        raise E1PretestDiagnosticError("all rung values must be E1ValidationScore")
    baseline = scores_by_rung[0]

    def _delta(value: float | None, initial: float | None) -> float | None:
        if value is None or initial is None:
            return None
        return float(value - initial)

    return {
        rung: E1RungComparison(
            rung=rung,
            is_untrained=rung == 0,
            model_mae_delta_from_untrained=float(score.model_mae - baseline.model_mae),
            skill_vs_zero_delta_from_untrained=_delta(
                score.skill_vs_constant_zero, baseline.skill_vs_constant_zero
            ),
            skill_vs_action_delta_from_untrained=_delta(
                score.skill_vs_action_only, baseline.skill_vs_action_only
            ),
        )
        for rung, score in sorted(scores_by_rung.items())
    }


def derive_route_cluster_ids(
    rows: Sequence[E1DiagnosticPairRow], *, route: str
) -> tuple[str, ...]:
    """Derive resampling identities from authenticated sealed index rows."""

    if route not in ROUTES:
        raise E1PretestDiagnosticError(f"route must be one of {ROUTES}")
    identifiers: list[str] = []
    for row in rows:
        if not isinstance(row, E1DiagnosticPairRow):
            raise E1PretestDiagnosticError("diagnostic rows have wrong type")
        row.verify()
        if row.index.route != route:
            raise E1PretestDiagnosticError("diagnostic route differs from index route")
        fields: tuple[object, ...] = (
            route,
            row.index.source_seed,
            row.index.inference_anchor_sha256,
        )
        if route == "C2":
            # C2 inference is intervention-cluster primary: one focal-specific
            # keyed-CRF intervention inside a shared world anchor.
            fields = (*fields, row.index.focal_user)
        identifiers.append(":".join(str(value) for value in fields))
    return tuple(identifiers)


def _probe_rows(
    rows: Sequence[E1DiagnosticPairRow], *, route: str, split: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[str, ...]]:
    selected = tuple(row for row in rows if row.split == split)
    if not selected:
        raise E1PretestDiagnosticError(f"{route} has no {split} probe rows")
    # The classifier has one observation per intervention cluster.  C1/C3
    # focal interventions at the same world anchor remain separate examples,
    # but receive the same inference-anchor bootstrap identity.
    unique: dict[tuple[str, int, str, int], E1DiagnosticPairRow] = {}
    for row in selected:
        row.verify()
        intervention = row.index.cluster_key
        previous = unique.setdefault(intervention, row)
        if previous is not row and (
            previous.index.reference_action != row.index.reference_action
            or not np.array_equal(previous.state, row.state)
            or not np.array_equal(previous.action_mask, row.action_mask)
        ):
            raise E1PretestDiagnosticError(
                "one route-aware probe identity contains inconsistent rows"
            )
    intervention_keys = tuple(sorted(unique))
    chosen = tuple(unique[key] for key in intervention_keys)
    resampling_ids = derive_route_cluster_ids(chosen, route=route)
    return (
        np.stack([np.asarray(row.state, dtype=np.float32) for row in chosen]),
        np.stack([np.asarray(row.action_mask, dtype=np.bool_) for row in chosen]),
        np.asarray([row.index.reference_action for row in chosen], dtype=np.int64),
        resampling_ids,
    )


def run_route_reference_action_probe(
    *,
    train_rows: Sequence[E1DiagnosticPairRow],
    validation_rows: Sequence[E1DiagnosticPairRow],
    route: str,
    config: E1ReferenceProbeConfig,
    train_seed: int,
    bootstrap_seed: int,
    device: str = "cpu",
) -> E1ReferenceProbeResult:
    """Run train→validation G-O probe with internally derived identities."""

    train_x, train_m, train_y, _train_ids = _probe_rows(
        train_rows, route=route, split="train"
    )
    validation_x, validation_m, validation_y, validation_ids = _probe_rows(
        validation_rows, route=route, split="validation"
    )
    return run_reference_action_probe(
        train_states=train_x,
        train_masks=train_m,
        train_reference_actions=train_y,
        test_states=validation_x,
        test_masks=validation_m,
        test_reference_actions=validation_y,
        test_cluster_ids=validation_ids,
        config=config,
        train_seed=train_seed,
        bootstrap_seed=bootstrap_seed,
        device=device,
    )


def _regular_directory(path: Path, *, label: str) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise E1PretestDiagnosticError(f"{label} must be a regular directory")
    return path


def _load_ladder_context(
    *,
    source_root: Path,
    ladder_root: Path,
    expected_source_receipt_sha256: str,
    expected_ladder_result_seal_sha256: str,
) -> tuple[
    Mapping[str, object],
    EEAxisPairwiseConfig,
    object,
    Mapping[str, object],
    Mapping[str, object],
    Mapping[str, object],
    Mapping[str, object],
]:
    """Authenticate the sealed train/validation ladder and all 12 rungs."""

    source = _regular_directory(source_root, label="source root")
    ladder = _regular_directory(ladder_root, label="ladder root")
    expected_source = _digest(
        expected_source_receipt_sha256,
        field="expected_source_receipt_sha256",
    )
    expected_ladder_seal = _digest(
        expected_ladder_result_seal_sha256,
        field="expected_ladder_result_seal_sha256",
    )
    if _sha256_file(ladder / "result-seal.json") != expected_ladder_seal:
        raise E1PretestDiagnosticError(
            "ladder result seal differs from externally captured digest"
        )

    _manifest, prereg, _schedules = sources._load_authority(source)
    config = ladder_driver._config_from_prereg(prereg)
    batches, access_receipt = ladder_driver._load_ladder_batches(
        source_root=source,
        prereg=prereg,
        config=config,
        expected_source_receipt_sha256=expected_source,
    )
    authority = sources._read_canonical_json(ladder / "authority.json")
    result = sources._read_canonical_json(ladder / "result.json")
    seal = sources._read_canonical_json(ladder / "result-seal.json")
    if (
        authority.get("schema") != ladder_driver.LADDER_AUTHORITY_SCHEMA
        or result.get("schema") != ladder_driver.LADDER_RESULT_SCHEMA
        or seal.get("schema") != ladder_driver.LADDER_RESULT_SEAL_SCHEMA
    ):
        raise E1PretestDiagnosticError("ladder authority schema is stale")
    for label, payload in (("authority", authority), ("result", result)):
        if payload.get("test_split_opened") is not False:
            raise E1PretestDiagnosticError(f"ladder {label} claims test was opened")
        if payload.get("held_out_ee_evaluated") is not False:
            raise E1PretestDiagnosticError(f"ladder {label} claims EE was evaluated")
    authority_sha256 = _digest(
        authority.get("authority_sha256"), field="authority_sha256"
    )
    authority_body = dict(authority)
    authority_body.pop("authority_sha256", None)
    if _canonical_sha256(authority_body) != authority_sha256:
        raise E1PretestDiagnosticError("ladder authority self-digest changed")
    if (
        seal.get("authority_sha256") != authority_sha256
        or result.get("authority_sha256") != authority_sha256
        or seal.get("result_file_sha256") != _sha256_file(ladder / "result.json")
    ):
        raise E1PretestDiagnosticError("ladder result is not bound by its seal")
    if (
        authority.get("source_prereg_sha256") != prereg.get("prereg_sha256")
        or authority.get("source_manifest_sha256")
        != prereg.get("source_manifest_sha256")
        or _canonical_sha256(authority.get("learner_config"))
        != _canonical_sha256(asdict(config))
        or authority.get("batch_digests") != batches.digests()
        or authority.get("source_access_receipt") != access_receipt
        or authority.get("execution_device") != "cpu"
    ):
        raise E1PretestDiagnosticError("ladder runtime authority differs from source")
    spec = authority.get("ladder_spec")
    if not isinstance(spec, Mapping):
        raise E1PretestDiagnosticError("ladder spec is malformed")
    init_seeds = tuple(spec.get("initialization_seeds", ()))
    update_rungs = tuple(spec.get("update_rungs", ()))
    if (
        len(init_seeds) != 3
        or len(set(init_seeds)) != 3
        or update_rungs != E1_UPDATE_RUNGS
    ):
        raise E1PretestDiagnosticError("ladder seed/rung geometry changed")
    expected_files = {
        f"init-{seed}-rung-{rung:06d}.pt"
        for seed in init_seeds
        for rung in update_rungs
    }
    recorded_digests = result.get("checkpoint_file_sha256s")
    if not isinstance(recorded_digests, Mapping) or set(recorded_digests) != expected_files:
        raise E1PretestDiagnosticError("ladder result does not bind all rung files")
    checkpoint_root = _regular_directory(
        ladder / "run" / "checkpoints", label="ladder checkpoint root"
    )
    if {path.name for path in checkpoint_root.iterdir()} != expected_files:
        raise E1PretestDiagnosticError("ladder checkpoint directory has changed")
    for filename in sorted(expected_files):
        path = checkpoint_root / filename
        if path.is_symlink() or not path.is_file():
            raise E1PretestDiagnosticError("ladder checkpoint is non-regular")
        expected_digest = _digest(
            recorded_digests[filename], field=f"checkpoint_file_sha256s[{filename}]"
        )
        if _sha256_file(path) != expected_digest:
            raise E1PretestDiagnosticError("ladder checkpoint file digest changed")
    selected_rung = result.get("selected_common_rung")
    selected = result.get("selected_checkpoint_files")
    if selected_rung not in update_rungs or not isinstance(selected, Mapping):
        raise E1PretestDiagnosticError("selected common rung is malformed")
    expected_selected = {
        str(seed): {
            "path": f"checkpoints/init-{seed}-rung-{selected_rung:06d}.pt",
            "file_sha256": recorded_digests[
                f"init-{seed}-rung-{selected_rung:06d}.pt"
            ],
        }
        for seed in init_seeds
    }
    if dict(selected) != expected_selected:
        raise E1PretestDiagnosticError("selected checkpoint receipt changed")
    status_path = ladder / "run" / "status.json"
    if result.get("run_status_file_sha256") != _sha256_file(status_path):
        raise E1PretestDiagnosticError("ladder status receipt changed")
    return prereg, config, batches, access_receipt, authority, result, seal


def _load_diagnostic_rows(
    *,
    source_root: Path,
    prereg: Mapping[str, object],
    config: EEAxisPairwiseConfig,
) -> tuple[E1DiagnosticPairRow, ...]:
    """Read only authenticated ladder-index train/validation datasets."""

    data_root = _regular_directory(source_root / "source-data", label="source-data")
    index = sources._read_canonical_json(data_root / "ladder-index.json")
    raw_split = prereg.get("source_seed_split")
    if not isinstance(raw_split, Mapping):
        raise E1PretestDiagnosticError("source prereg seed split is malformed")
    expected_split = {
        int(seed): str(split)
        for seed, split in raw_split.items()
        if split in {"train", "validation"}
    }
    entries = _validated_train_validation_entries(
        index=index, expected_seed_split=expected_split
    )
    policy_sha256 = _digest(prereg.get("c2_policy_sha256"), field="c2_policy_sha256")
    if policy_sha256 != sources._policy_sha256():
        raise E1PretestDiagnosticError("source policy digest differs from prereg")
    rows: list[E1DiagnosticPairRow] = []
    for seed, split, entry in entries:
        opening_path = ladder_driver._canonical_dataset_path(
            data_root=data_root,
            raw=entry.get("opening_path"),
            expected=f"opening-{seed}.json",
        )
        temporal_path = ladder_driver._canonical_dataset_path(
            data_root=data_root,
            raw=entry.get("temporal_path"),
            expected=f"temporal-{seed}.json",
        )
        opening = read_opening_dataset(opening_path)
        temporal = read_temporal_dataset(temporal_path)
        if opening.verify() != entry.get("opening_dataset_sha256"):
            raise E1PretestDiagnosticError("opening dataset content digest changed")
        if temporal.verify() != entry.get("temporal_dataset_sha256"):
            raise E1PretestDiagnosticError("temporal dataset content digest changed")
        for route in ("C1", "C3"):
            for pair in opening.route_pairs(route):
                row = E1DiagnosticPairRow(
                    split=split,
                    index=E1PairIndexRow(
                        route=route,
                        source_seed=seed,
                        anchor_sha256=pair.anchor_sha256,
                        inference_anchor_sha256=pair.anchor_sha256,
                        focal_user=pair.focal_user,
                        reference_action=pair.reference_action,
                        candidate_action=pair.candidate_action,
                        action_mask=tuple(
                            bool(value) for value in pair.action_mask.tolist()
                        ),
                    ),
                    state=np.asarray(pair.state, dtype=np.float32),
                    action_mask=np.asarray(pair.action_mask, dtype=np.bool_),
                    normalized_target=float(pair.route_target_surplus_bits)
                    / float(config.kappa_bits),
                    policy_sha256=policy_sha256,
                    comparison_sha256=pair.comparison_sha256,
                )
                row.verify()
                rows.append(row)
        for pair in temporal.rows:
            if pair.seed != seed:
                raise E1PretestDiagnosticError("temporal row source seed changed")
            row = E1DiagnosticPairRow(
                split=split,
                index=E1PairIndexRow(
                    route="C2",
                    source_seed=seed,
                    anchor_sha256=pair.anchor_sha256,
                    inference_anchor_sha256=e1_c2_world_anchor_sha256(
                        source_seed=seed, anchor_step=pair.step_index
                    ),
                    focal_user=pair.focal_user,
                    reference_action=pair.reference_action,
                    candidate_action=pair.candidate_action,
                    action_mask=tuple(
                        bool(value) for value in pair.action_mask.tolist()
                    ),
                ),
                state=np.asarray(pair.state, dtype=np.float32),
                action_mask=np.asarray(pair.action_mask, dtype=np.bool_),
                normalized_target=float(pair.zeta2_temporal_surplus_bits)
                / float(config.kappa_bits),
                policy_sha256=policy_sha256,
                comparison_sha256=pair.comparison_sha256,
            )
            row.verify()
            rows.append(row)
    if not rows:
        raise E1PretestDiagnosticError("diagnostic source has no rows")
    return tuple(rows)


def _checkpoint_trainer(
    *,
    checkpoint_path: Path,
    expected_file_sha256: str,
    expected_spec: Mapping[str, object],
    expected_batch_digests: Mapping[str, object],
    config: EEAxisPairwiseConfig,
    initialization_seed: int,
    rung: int,
) -> tuple[EEAxisPairwiseTrainer, Mapping[str, object]]:
    if checkpoint_path.is_symlink() or not checkpoint_path.is_file():
        raise E1PretestDiagnosticError("ladder checkpoint is non-regular")
    if _sha256_file(checkpoint_path) != expected_file_sha256:
        raise E1PretestDiagnosticError("ladder checkpoint digest changed before load")
    try:
        payload = torch.load(
            checkpoint_path,
            map_location="cpu",
            weights_only=False,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise E1PretestDiagnosticError("ladder checkpoint cannot be deserialized") from error
    trainer_payload = _verify_checkpoint_payload(
        payload,
        expected_spec=expected_spec,
        expected_batch_digests=expected_batch_digests,
        initialization_seed=initialization_seed,
        rung=rung,
    )
    trainer = EEAxisPairwiseTrainer(config, train_seed=initialization_seed, device="cpu")
    try:
        updates = trainer.load_checkpoint_state(trainer_payload)
    except (RuntimeError, TypeError, ValueError) as error:
        raise E1PretestDiagnosticError("ladder trainer state cannot be loaded") from error
    if updates != rung * len(ROUTES):
        raise E1PretestDiagnosticError("ladder checkpoint update count changed")
    return trainer, payload


def _score_rungs(
    *,
    config: EEAxisPairwiseConfig,
    batches: object,
    ladder_root: Path,
    authority: Mapping[str, object],
    result: Mapping[str, object],
) -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    spec = authority["ladder_spec"]
    batch_digests = authority["batch_digests"]
    if not isinstance(spec, Mapping) or not isinstance(batch_digests, Mapping):
        raise E1PretestDiagnosticError("ladder scoring authority is malformed")
    initialization_seeds = tuple(spec["initialization_seeds"])
    update_rungs = tuple(spec["update_rungs"])
    recorded_digests = result["checkpoint_file_sha256s"]
    if not isinstance(recorded_digests, Mapping):
        raise E1PretestDiagnosticError("checkpoint digest map is malformed")

    design_by_route: dict[str, E1ActionOnlyDesignDiagnostics] = {}
    for route in ROUTES:
        design_by_route[route] = action_only_design_diagnostics(
            train_batch=batches.batch("train", route),
            validation_batch=batches.batch("validation", route),
            kappa_bits=config.kappa_bits,
        )

    all_scores: dict[int, dict[int, dict[str, E1ValidationScore]]] = {}
    comparisons: dict[int, dict[str, dict[int, E1RungComparison]]] = {}
    checkpoint_root = ladder_root / "run" / "checkpoints"
    for seed in initialization_seeds:
        seed_scores: dict[int, dict[str, E1ValidationScore]] = {}
        untrained = EEAxisPairwiseTrainer(config, train_seed=seed, device="cpu")
        untrained_q = untrained.q_values(batches.validation[0].states)
        # q_values must be evaluated on each route's own validation states.
        seed_scores[0] = {
            route: score_validation_surface(
                validation_batch=batches.batch("validation", route),
                q_surface=untrained.q_values(
                    batches.batch("validation", route).states
                )[route_index],
                action_only_prediction=(
                    design_by_route[route].minimum_norm_validation_prediction
                ),
                kappa_bits=config.kappa_bits,
            )
            for route_index, route in enumerate(ROUTES)
        }
        del untrained_q
        for rung in update_rungs:
            filename = f"init-{seed}-rung-{rung:06d}.pt"
            trainer, payload = _checkpoint_trainer(
                checkpoint_path=checkpoint_root / filename,
                expected_file_sha256=_digest(
                    recorded_digests[filename], field=f"checkpoint[{filename}]"
                ),
                expected_spec=spec,
                expected_batch_digests=batch_digests,
                config=config,
                initialization_seed=seed,
                rung=rung,
            )
            route_scores: dict[str, E1ValidationScore] = {}
            for route_index, route in enumerate(ROUTES):
                validation = batches.batch("validation", route)
                score = score_validation_surface(
                    validation_batch=validation,
                    q_surface=trainer.q_values(validation.states)[route_index],
                    action_only_prediction=(
                        design_by_route[route].minimum_norm_validation_prediction
                    ),
                    kappa_bits=config.kappa_bits,
                )
                metrics = payload.get("validation_metrics")
                if not isinstance(metrics, Mapping) or not isinstance(
                    metrics.get(route), Mapping
                ):
                    raise E1PretestDiagnosticError(
                        "checkpoint validation metric receipt is malformed"
                    )
                recorded = metrics[route]
                if (
                    not math.isclose(
                        score.model_mae,
                        float(recorded["model_mae"]),
                        rel_tol=1e-7,
                        abs_tol=1e-6,
                    )
                    or not math.isclose(
                        score.action_only_mae,
                        float(recorded["action_only_baseline_mae"]),
                        rel_tol=1e-7,
                        abs_tol=1e-6,
                    )
                ):
                    raise E1PretestDiagnosticError(
                        "recomputed validation score differs from checkpoint: "
                        f"seed={seed} rung={rung} route={route} "
                        f"model={score.model_mae!r}/"
                        f"{recorded['model_mae']!r} action={score.action_only_mae!r}/"
                        f"{recorded['action_only_baseline_mae']!r}"
                    )
                route_scores[route] = score
            seed_scores[rung] = route_scores
        all_scores[seed] = seed_scores
        comparisons[seed] = {
            route: compare_rungs_to_untrained(
                {rung: route_scores[route] for rung, route_scores in seed_scores.items()}
            )
            for route in ROUTES
        }

    score_payload = {
        str(seed): {
            str(rung): {
                route: score.as_dict() for route, score in route_scores.items()
            }
            for rung, route_scores in seed_scores.items()
        }
        for seed, seed_scores in all_scores.items()
    }
    comparison_payload = {
        str(seed): {
            route: {
                str(rung): comparison.as_dict()
                for rung, comparison in route_comparisons.items()
            }
            for route, route_comparisons in seed_comparisons.items()
        }
        for seed, seed_comparisons in comparisons.items()
    }
    design_payload = {
        route: diagnostics.as_dict()
        for route, diagnostics in design_by_route.items()
    }
    return score_payload, comparison_payload, design_payload


def _probe_diagnostics(
    *,
    rows: Sequence[E1DiagnosticPairRow],
    config: EEAxisPairwiseConfig,
    initialization_seeds: Sequence[int],
    updates: int,
    bootstrap_replications: int,
) -> dict[str, object]:
    by_split_route = {
        split: {
            route: tuple(
                row
                for row in rows
                if row.split == split and row.index.route == route
            )
            for route in ROUTES
        }
        for split in ("train", "validation")
    }
    probe_config = E1ReferenceProbeConfig(
        state_dim=config.state_dim,
        action_dim=config.action_dim,
        learning_rate=config.learning_rate,
        updates=updates,
        activation=config.activation,
        bootstrap_replications=bootstrap_replications,
        bootstrap_confidence=0.95,
    )
    output: dict[str, object] = {}
    for route_index, route in enumerate(ROUTES):
        route_results: dict[str, object] = {}
        for seed_index, seed in enumerate(initialization_seeds):
            bootstrap_seed = 2026091201 + route_index * 100 + seed_index
            validation_ids = derive_route_cluster_ids(
                by_split_route["validation"][route], route=route
            )
            try:
                report = run_route_reference_action_probe(
                    train_rows=by_split_route["train"][route],
                    validation_rows=by_split_route["validation"][route],
                    route=route,
                    config=probe_config,
                    train_seed=int(seed),
                    bootstrap_seed=bootstrap_seed,
                    device="cpu",
                )
            except E1StatisticsError as error:
                # A resample with perfect action-prior accuracy makes relative
                # error reduction undefined.  That is a route/inference-unit
                # coverage result, not permission to drop replications or
                # silently condition the interval on finite draws.
                route_results[str(seed)] = {
                    "status": "INSUFFICIENT_COVERAGE",
                    "reason": str(error),
                    "train_seed": int(seed),
                    "bootstrap_seed": bootstrap_seed,
                    "validation_rows_before_intervention_deduplication": len(
                        by_split_route["validation"][route]
                    ),
                    "validation_resampling_clusters": len(set(validation_ids)),
                    "passes_contract_point_and_interval_gate": False,
                }
                continue
            interval = report.relative_error_reduction_interval
            route_results[str(seed)] = {
                **report.as_dict(),
                "status": "COMPLETE",
                "passes_contract_point_and_interval_gate": bool(
                    report.probe_top1_accuracy >= 0.80
                    and report.relative_error_reduction >= 0.50
                    and interval.lower > 0.25
                ),
            }
        output[route] = route_results
    return output


def _selected_rung_summary(
    *, scores: Mapping[str, object], selected_rung: int
) -> dict[str, object]:
    summary: dict[str, object] = {}
    for route in ROUTES:
        route_rows: list[dict[str, float | bool]] = []
        for seed, seed_scores_object in scores.items():
            seed_scores = seed_scores_object
            if not isinstance(seed_scores, Mapping):
                raise E1PretestDiagnosticError("score payload is malformed")
            untrained = seed_scores["0"]
            selected = seed_scores[str(selected_rung)]
            if not isinstance(untrained, Mapping) or not isinstance(selected, Mapping):
                raise E1PretestDiagnosticError("rung score payload is malformed")
            initial_route = untrained[route]
            selected_route = selected[route]
            if not isinstance(initial_route, Mapping) or not isinstance(
                selected_route, Mapping
            ):
                raise E1PretestDiagnosticError("route score payload is malformed")
            initial_mae = float(initial_route["model_mae"])
            selected_mae = float(selected_route["model_mae"])
            initial_skill = float(initial_route["skill_vs_action_only"])
            selected_skill = float(selected_route["skill_vs_action_only"])
            route_rows.append(
                {
                    "initialization_seed": float(seed),
                    "untrained_model_mae": initial_mae,
                    "selected_model_mae": selected_mae,
                    "selected_minus_untrained_model_mae": selected_mae - initial_mae,
                    "untrained_skill_vs_action_only": initial_skill,
                    "selected_skill_vs_action_only": selected_skill,
                    "selected_minus_untrained_skill_vs_action_only": (
                        selected_skill - initial_skill
                    ),
                    "selected_beats_untrained": bool(selected_mae < initial_mae),
                }
            )
        summary[route] = {
            "per_initialization": route_rows,
            "selected_beats_untrained_count": sum(
                bool(row["selected_beats_untrained"]) for row in route_rows
            ),
            "mean_selected_minus_untrained_model_mae": float(
                np.mean(
                    [row["selected_minus_untrained_model_mae"] for row in route_rows]
                )
            ),
            "mean_selected_minus_untrained_skill_vs_action_only": float(
                np.mean(
                    [
                        row["selected_minus_untrained_skill_vs_action_only"]
                        for row in route_rows
                    ]
                )
            ),
        }
    return summary


def run(
    *,
    source_root: Path,
    ladder_root: Path,
    output_dir: Path,
    expected_source_receipt_sha256: str,
    expected_ladder_result_seal_sha256: str,
    device: str = "cpu",
    probe_updates: int = 1000,
    probe_bootstrap_replications: int = 2000,
) -> dict[str, object]:
    """Run the sealed no-EE diagnostic without any held-out opener."""

    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite diagnostic output: {output_dir}")
    if device != "cpu":
        raise E1PretestDiagnosticError("claim-bearing diagnostics are CPU-sealed")
    if type(probe_updates) is not int or probe_updates < 1:
        raise E1PretestDiagnosticError("probe_updates must be positive")
    if (
        type(probe_bootstrap_replications) is not int
        or probe_bootstrap_replications < 100
    ):
        raise E1PretestDiagnosticError(
            "probe_bootstrap_replications must be at least 100"
        )
    # These are tiny full-batch networks.  Sealing one intra-op thread avoids
    # nondeterministic oversubscription and is substantially faster than
    # launching a large BLAS team for each of 9,000 small probe updates.
    torch.set_num_threads(DIAGNOSTIC_CPU_THREADS)
    code_manifest = _diagnostic_code_manifest()
    (
        prereg,
        config,
        batches,
        access_receipt,
        authority,
        ladder_result,
        ladder_seal,
    ) = _load_ladder_context(
        source_root=source_root,
        ladder_root=ladder_root,
        expected_source_receipt_sha256=expected_source_receipt_sha256,
        expected_ladder_result_seal_sha256=expected_ladder_result_seal_sha256,
    )
    rows = _load_diagnostic_rows(
        source_root=source_root,
        prereg=prereg,
        config=config,
    )
    scores, comparisons, action_design = _score_rungs(
        config=config,
        batches=batches,
        ladder_root=ladder_root,
        authority=authority,
        result=ladder_result,
    )
    collisions = {
        route: persistent_collision_report(
            tuple(row for row in rows if row.index.route == route), route=route
        ).as_dict()
        for route in ROUTES
    }
    spec = authority["ladder_spec"]
    if not isinstance(spec, Mapping):
        raise E1PretestDiagnosticError("ladder spec is malformed")
    probes = _probe_diagnostics(
        rows=rows,
        config=config,
        initialization_seeds=tuple(spec["initialization_seeds"]),
        updates=probe_updates,
        bootstrap_replications=probe_bootstrap_replications,
    )
    selected_rung = int(ladder_result["selected_common_rung"])
    selected_summary = _selected_rung_summary(
        scores=scores, selected_rung=selected_rung
    )
    if _diagnostic_code_manifest() != code_manifest:
        raise E1PretestDiagnosticError("diagnostic code changed during execution")
    result_body = {
        "schema": "multi-catfish-mcrl-v03-e1-pretest-diagnostic-result-v1",
        "status": "PRETEST_DIAGNOSTIC_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "selected_common_rung": selected_rung,
        "validation_scores_by_initialization_and_rung": scores,
        "comparisons_to_same_initialization_rung_zero": comparisons,
        "selected_rung_summary": selected_summary,
        "action_only_design_diagnostics": action_design,
        "train_validation_persistent_collisions": collisions,
        "train_to_validation_reference_action_probes": probes,
        "diagnostic_rows": {
            split: {
                route: sum(
                    row.split == split and row.index.route == route for row in rows
                )
                for route in ROUTES
            }
            for split in ("train", "validation")
        },
        "probe_updates": probe_updates,
        "probe_bootstrap_replications": probe_bootstrap_replications,
        "execution_device": "cpu",
        "torch_intraop_threads": DIAGNOSTIC_CPU_THREADS,
        "opened_dataset_paths": access_receipt["opened_dataset_paths"],
        "heldout_dataset_paths_opened": [],
        "heldout_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    result_sha256 = _canonical_sha256(result_body)
    authority_body = {
        "schema": "multi-catfish-mcrl-v03-e1-pretest-diagnostic-authority-v1",
        "claim_ceiling": CLAIM_CEILING,
        "diagnostic_code_manifest": code_manifest,
        "source_prereg_sha256": prereg["prereg_sha256"],
        "source_manifest_sha256": prereg["source_manifest_sha256"],
        "source_receipt_file_sha256": access_receipt[
            "source_receipt_file_sha256"
        ],
        "ladder_authority_sha256": authority["authority_sha256"],
        "ladder_result_file_sha256": ladder_seal["result_file_sha256"],
        "ladder_result_seal_file_sha256": _digest(
            expected_ladder_result_seal_sha256,
            field="expected_ladder_result_seal_sha256",
        ),
        "learner_config": asdict(config),
        "batch_digests": batches.digests(),
        "execution_device": "cpu",
        "torch_intraop_threads": DIAGNOSTIC_CPU_THREADS,
        "heldout_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    authority_sha256 = _canonical_sha256(authority_body)
    output_dir.mkdir(parents=True, exist_ok=False)
    sources._write_once_json(
        output_dir / "authority.json",
        {**authority_body, "authority_sha256": authority_sha256},
    )
    result_file_sha256 = sources._write_once_json(
        output_dir / "result.json",
        {
            **result_body,
            "result_sha256": result_sha256,
            "authority_sha256": authority_sha256,
        },
    )
    receipt = {
        "schema": "multi-catfish-mcrl-v03-e1-pretest-diagnostic-receipt-v1",
        "status": "PRETEST_DIAGNOSTIC_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "authority_sha256": authority_sha256,
        "result_file_sha256": result_file_sha256,
        "selected_common_rung": selected_rung,
        "torch_intraop_threads": DIAGNOSTIC_CPU_THREADS,
        "opened_dataset_paths": access_receipt["opened_dataset_paths"],
        "heldout_dataset_paths_opened": [],
        "heldout_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    receipt_file_sha256 = sources._write_once_json(
        output_dir / "receipt.json", receipt
    )
    return {**receipt, "receipt_file_sha256": receipt_file_sha256}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=(
            REPO
            / "artifacts"
            / "multi-catfish-v03-e1-instrument-validity-20260901"
        ),
    )
    parser.add_argument("--ladder-root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-source-receipt-sha256", required=True)
    parser.add_argument("--expected-ladder-result-seal-sha256", required=True)
    parser.add_argument("--device", choices=("cpu",), default="cpu")
    parser.add_argument("--probe-updates", type=int, default=1000)
    parser.add_argument("--probe-bootstrap-replications", type=int, default=2000)
    args = parser.parse_args(argv)
    ladder_root = args.ladder_root or args.source_root / "ladder-authority"
    receipt = run(
        source_root=args.source_root,
        ladder_root=ladder_root,
        output_dir=args.output_dir,
        expected_source_receipt_sha256=args.expected_source_receipt_sha256,
        expected_ladder_result_seal_sha256=(
            args.expected_ladder_result_seal_sha256
        ),
        device=args.device,
        probe_updates=args.probe_updates,
        probe_bootstrap_replications=args.probe_bootstrap_replications,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False))
    return 0


__all__ = [
    "CLAIM_CEILING",
    "E1ActionOnlyDesignDiagnostics",
    "E1DiagnosticPairRow",
    "E1PretestDiagnosticError",
    "E1RidgeSensitivity",
    "E1RungComparison",
    "E1ValidationScore",
    "action_only_design_diagnostics",
    "compare_rungs_to_untrained",
    "derive_route_cluster_ids",
    "run_route_reference_action_probe",
    "score_validation_surface",
]


if __name__ == "__main__":
    raise SystemExit(main())
