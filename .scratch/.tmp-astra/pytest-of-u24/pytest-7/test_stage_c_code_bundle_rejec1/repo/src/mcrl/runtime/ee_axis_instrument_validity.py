"""Non-EE diagnostics for the Multi-Catfish V0.3 learning instrument.

These metrics answer a question that must be settled before another EE
ablation: does the three-Q score learn state-conditional pairwise surplus, or
does a state-independent action-slot bias dominate its decisions?  Nothing in
this module evaluates throughput, energy, or EE, and none of its outputs is an
efficacy claim.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math

import numpy as np

from ..errors import MCRLContractError


E1_INSTRUMENT_SCHEMA = "multi-catfish-mcrl-v03-e1-instrument-validity-v1"


class EEAxisInstrumentValidityError(MCRLContractError):
    """An E1 diagnostic input is malformed or cannot identify its metric."""


class EEAxisActionGraphCoverageError(EEAxisInstrumentValidityError):
    """A held-out action contrast lacks training-comparison graph support."""


@dataclass(frozen=True)
class DeploymentDiversity:
    """Masked argmax concentration on a held-out state corpus."""

    eligible_decisions: int
    all_dark_decisions: int
    distinct_action_count: int
    modal_action: int
    modal_action_count: int
    modal_action_share: float

    def as_dict(self) -> dict[str, int | float]:
        return asdict(self)


@dataclass(frozen=True)
class HeadPivotality:
    """Masked action changes when one route-local head is removed."""

    route: str
    eligible_decisions: int
    changed_decisions: int
    changed_fraction: float

    def as_dict(self) -> dict[str, str | int | float]:
        return asdict(self)


@dataclass(frozen=True)
class ActionMainEffect:
    """Held-out fraction explained by validation-fitted action effects."""

    validation_states: int
    test_states: int
    actions: int
    centered_sum_squares: float
    residual_sum_squares: float
    action_main_effect_fraction: float

    def as_dict(self) -> dict[str, int | float]:
        return asdict(self)


@dataclass(frozen=True)
class PairGeneralization:
    """Held-out pair MAE against a fitted action-only difference baseline."""

    train_pairs: int
    heldout_pairs: int
    active_train_actions: int
    model_mae: float
    action_only_baseline_mae: float
    absolute_mae_improvement: float
    relative_mae_improvement: float | None

    def as_dict(self) -> dict[str, int | float | None]:
        return asdict(self)


@dataclass(frozen=True)
class StrongBaselinePairGeneralization:
    """Held-out pair MAE against a conservative no-state baseline family.

    Every member is fixed without held-out outcomes: the action-only
    difference model and global median are fit on training targets, while the
    zero predictor is parameter-free.  The held-out denominator is the lowest
    MAE among those predeclared null predictors, so a weak action-only fit
    cannot manufacture apparent state-conditioned skill.
    """

    train_pairs: int
    heldout_pairs: int
    active_train_actions: int
    model_mae: float
    action_only_baseline_mae: float
    zero_baseline_mae: float
    train_median_value: float
    train_median_baseline_mae: float
    strongest_baseline_name: str
    strongest_state_independent_baseline_mae: float
    absolute_mae_improvement: float
    relative_mae_improvement: float | None

    def as_dict(self) -> dict[str, str | int | float | None]:
        return asdict(self)


@dataclass(frozen=True)
class ObservabilityCollisions:
    """Exact model-input collisions and their deterministic MAE floor.

    A key contains the float32 state, decision mask, reference action and
    candidate action.  If one key maps to both positive and negative targets,
    no deterministic Q-difference learner can fit those rows simultaneously.
    Absence of repeated keys is *not* evidence that the state is sufficient;
    ``identified`` is therefore false until the preregistered repeated-key
    support is reached.
    """

    rows: int
    unique_input_keys: int
    repeated_input_groups: int
    repeated_rows: int
    conflicting_sign_groups: int
    conflicting_sign_rows: int
    deterministic_mae_floor: float
    target_abs_mean: float
    normalized_mae_floor: float | None
    persistent_positive_minimum: float
    persistent_negative_maximum: float
    persistent_count_per_sign: int

    def as_dict(self) -> dict[str, int | float | bool | None]:
        return asdict(self)


def _score_surface(scores: np.ndarray) -> np.ndarray:
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 2 or min(values.shape) < 1:
        raise EEAxisInstrumentValidityError("scores must be a nonempty (states, actions) matrix")
    if not np.all(np.isfinite(values)):
        raise EEAxisInstrumentValidityError("scores must be finite")
    return values


def compute_deployment_diversity(
    scores: np.ndarray,
    masks: np.ndarray,
    *,
    minimum_eligible_decisions: int,
) -> DeploymentDiversity:
    """Measure G-D inputs without consulting an EE endpoint."""

    values = _score_surface(scores)
    valid = np.asarray(masks)
    if valid.shape != values.shape or valid.dtype != np.bool_:
        raise EEAxisInstrumentValidityError(
            "masks must be boolean and match the score surface"
        )
    if (
        isinstance(minimum_eligible_decisions, bool)
        or not isinstance(minimum_eligible_decisions, int)
        or minimum_eligible_decisions < 1
    ):
        raise EEAxisInstrumentValidityError(
            "minimum_eligible_decisions must be a positive integer"
        )
    eligible = np.any(valid, axis=1)
    eligible_count = int(np.count_nonzero(eligible))
    if eligible_count < minimum_eligible_decisions:
        raise EEAxisInstrumentValidityError(
            "held-out corpus has fewer eligible decisions than preregistered"
        )
    selected = np.argmax(np.where(valid[eligible], values[eligible], -np.inf), axis=1)
    counts = np.bincount(selected, minlength=values.shape[1])
    modal_action = int(np.argmax(counts))
    modal_count = int(counts[modal_action])
    return DeploymentDiversity(
        eligible_decisions=eligible_count,
        all_dark_decisions=int(values.shape[0] - eligible_count),
        distinct_action_count=int(np.count_nonzero(counts)),
        modal_action=modal_action,
        modal_action_count=modal_count,
        modal_action_share=float(modal_count / eligible_count),
    )


def compute_head_pivotality(
    *,
    head_scores: tuple[np.ndarray, np.ndarray, np.ndarray],
    masks: np.ndarray,
    route_names: tuple[str, str, str] = ("C1", "C2", "C3"),
    minimum_eligible_decisions: int,
) -> tuple[HeadPivotality, HeadPivotality, HeadPivotality]:
    """Compute G-D action-change diagnostics on one fixed held-out corpus."""

    if len(head_scores) != 3 or len(route_names) != 3 or len(set(route_names)) != 3:
        raise EEAxisInstrumentValidityError(
            "G-D requires exactly three distinct route-local score surfaces"
        )
    surfaces = tuple(_score_surface(surface) for surface in head_scores)
    if any(surface.shape != surfaces[0].shape for surface in surfaces[1:]):
        raise EEAxisInstrumentValidityError("G-D head score surfaces must align")
    valid = np.asarray(masks)
    if valid.shape != surfaces[0].shape or valid.dtype != np.bool_:
        raise EEAxisInstrumentValidityError(
            "G-D masks must be boolean and match the head score surfaces"
        )
    if (
        isinstance(minimum_eligible_decisions, bool)
        or not isinstance(minimum_eligible_decisions, int)
        or minimum_eligible_decisions < 1
    ):
        raise EEAxisInstrumentValidityError(
            "minimum_eligible_decisions must be a positive integer"
        )
    eligible = np.any(valid, axis=1)
    eligible_count = int(np.count_nonzero(eligible))
    if eligible_count < minimum_eligible_decisions:
        raise EEAxisInstrumentValidityError(
            "held-out corpus has fewer eligible decisions than preregistered"
        )
    masks_eligible = valid[eligible]
    total = surfaces[0] + surfaces[1] + surfaces[2]
    full_actions = np.argmax(
        np.where(masks_eligible, total[eligible], -np.inf), axis=1
    )
    reports: list[HeadPivotality] = []
    for route, surface in zip(route_names, surfaces, strict=True):
        without = total - surface
        actions_without = np.argmax(
            np.where(masks_eligible, without[eligible], -np.inf), axis=1
        )
        changed = int(np.count_nonzero(actions_without != full_actions))
        reports.append(
            HeadPivotality(
                route=route,
                eligible_decisions=eligible_count,
                changed_decisions=changed,
                changed_fraction=float(changed / eligible_count),
            )
        )
    return tuple(reports)  # type: ignore[return-value]


def _center_legal_scores(
    scores: np.ndarray,
    masks: np.ndarray,
    *,
    label: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = _score_surface(scores)
    valid = np.asarray(masks)
    if valid.shape != values.shape or valid.dtype != np.bool_:
        raise EEAxisInstrumentValidityError(
            f"{label} masks must be boolean and match the score surface"
        )
    counts = np.count_nonzero(valid, axis=1)
    if np.any(counts < 2):
        raise EEAxisInstrumentValidityError(
            f"{label} G-S rows need at least two legal actions"
        )
    means = np.sum(np.where(valid, values, 0.0), axis=1) / counts
    centered = np.where(valid, values - means[:, None], 0.0)
    weights = np.where(valid, 1.0 / counts[:, None], 0.0)
    return centered, weights, valid


def fit_action_only_effects(
    scores: np.ndarray,
    masks: np.ndarray,
) -> np.ndarray:
    """Fit validation-only action-slot effects for G-S."""

    centered, weights, _valid = _center_legal_scores(
        scores, masks, label="validation"
    )
    support = np.sum(weights, axis=0)
    effects = np.divide(
        np.sum(weights * centered, axis=0),
        support,
        out=np.zeros_like(support),
        where=support > 0.0,
    )
    effects.setflags(write=False)
    return effects


def score_action_only_effects(
    scores: np.ndarray,
    masks: np.ndarray,
    effects: np.ndarray,
) -> tuple[float, float, float]:
    """Return test residual SS, centered SS, and out-of-sample G-S."""

    centered, weights, valid = _center_legal_scores(scores, masks, label="test")
    action_effects = np.asarray(effects, dtype=np.float64)
    if action_effects.shape != (centered.shape[1],) or not np.all(
        np.isfinite(action_effects)
    ):
        raise EEAxisInstrumentValidityError(
            "action effects must be a finite action_dim vector"
        )
    denominator = float(np.sum(weights * np.square(centered)))
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise EEAxisInstrumentValidityError(
            "a constant centered test surface has no identifiable G-S"
        )
    residual = np.where(valid, centered - action_effects[None, :], 0.0)
    numerator = float(np.sum(weights * np.square(residual)))
    fraction = 1.0 - numerator / denominator
    if not math.isfinite(fraction):
        raise EEAxisInstrumentValidityError("action main-effect fraction is non-finite")
    return numerator, denominator, float(fraction)


def compute_action_main_effect(
    *,
    validation_scores: np.ndarray,
    validation_masks: np.ndarray,
    test_scores: np.ndarray,
    test_masks: np.ndarray,
) -> ActionMainEffect:
    """Compute preregistered G-S with equal total weight per held-out state.

    Scores are centered within each state's legal action set.  One constant
    effect per relative action slot is fitted on validation states, then its
    out-of-sample explained fraction is evaluated once on test states.
    """

    validation_x, _validation_w, validation_valid = _center_legal_scores(
        validation_scores, validation_masks, label="validation"
    )
    test_x, _test_w, test_valid = _center_legal_scores(
        test_scores, test_masks, label="test"
    )
    if validation_x.shape[1] != test_x.shape[1]:
        raise EEAxisInstrumentValidityError(
            "validation and test score surfaces must share action_dim"
        )
    if validation_x.shape[0] < 2 or test_x.shape[0] < 2 or test_x.shape[1] < 2:
        raise EEAxisInstrumentValidityError(
            "G-S needs at least two validation states, test states, and actions"
        )
    effects = fit_action_only_effects(validation_scores, validation_masks)
    validation_support = np.any(validation_valid, axis=0)
    if np.any(np.logical_and(np.any(test_valid, axis=0), ~validation_support)):
        raise EEAxisInstrumentValidityError(
            "a legal test action lacks validation support"
        )
    numerator, denominator, fraction = score_action_only_effects(
        test_scores,
        test_masks,
        effects,
    )
    return ActionMainEffect(
        validation_states=int(validation_x.shape[0]),
        test_states=int(test_x.shape[0]),
        actions=int(test_x.shape[1]),
        centered_sum_squares=denominator,
        residual_sum_squares=numerator,
        action_main_effect_fraction=float(fraction),
    )


def _pair_arrays(
    reference_actions: np.ndarray,
    candidate_actions: np.ndarray,
    targets: np.ndarray,
    *,
    action_dim: int,
    label: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    reference = np.asarray(reference_actions)
    candidate = np.asarray(candidate_actions)
    target = np.asarray(targets, dtype=np.float64)
    if reference.ndim != 1 or candidate.shape != reference.shape or target.shape != reference.shape:
        raise EEAxisInstrumentValidityError(
            f"{label} pair arrays must be aligned one-dimensional vectors"
        )
    if reference.size < 1:
        raise EEAxisInstrumentValidityError(f"{label} pair set must be nonempty")
    if not np.issubdtype(reference.dtype, np.integer) or not np.issubdtype(
        candidate.dtype, np.integer
    ):
        raise EEAxisInstrumentValidityError(f"{label} actions must be integers")
    if (
        np.any(reference < 0)
        or np.any(candidate < 0)
        or np.any(reference >= action_dim)
        or np.any(candidate >= action_dim)
        or np.any(reference == candidate)
    ):
        raise EEAxisInstrumentValidityError(f"{label} actions are invalid")
    if not np.all(np.isfinite(target)):
        raise EEAxisInstrumentValidityError(f"{label} targets must be finite")
    return (
        reference.astype(np.int64, copy=False),
        candidate.astype(np.int64, copy=False),
        target,
    )


def compute_pair_generalization(
    *,
    train_reference_actions: np.ndarray,
    train_candidate_actions: np.ndarray,
    train_targets: np.ndarray,
    heldout_reference_actions: np.ndarray,
    heldout_candidate_actions: np.ndarray,
    heldout_targets: np.ndarray,
    heldout_q_surface: np.ndarray,
    action_dim: int,
) -> PairGeneralization:
    """Compare held-out Q differences with an action-only least-squares model.

    The baseline learns constants ``b_a`` on the training split such that
    ``b_candidate - b_reference`` approximates the pair target.  Its minimum-
    norm gauge is immaterial because only differences are evaluated.
    """

    if isinstance(action_dim, bool) or not isinstance(action_dim, int) or action_dim < 2:
        raise EEAxisInstrumentValidityError("action_dim must be an integer >= 2")
    train_r, train_c, train_y = _pair_arrays(
        train_reference_actions,
        train_candidate_actions,
        train_targets,
        action_dim=action_dim,
        label="training",
    )
    test_r, test_c, test_y = _pair_arrays(
        heldout_reference_actions,
        heldout_candidate_actions,
        heldout_targets,
        action_dim=action_dim,
        label="held-out",
    )
    q = _score_surface(heldout_q_surface)
    if q.shape != (test_y.size, action_dim):
        raise EEAxisInstrumentValidityError(
            "heldout_q_surface must be (heldout pairs, action_dim)"
        )

    design = np.zeros((train_y.size, action_dim), dtype=np.float64)
    rows = np.arange(train_y.size)
    design[rows, train_c] = 1.0
    design[rows, train_r] = -1.0
    coefficients, _residuals, _rank, _singular = np.linalg.lstsq(
        design, train_y, rcond=None
    )

    # A held-out contrast is identified only when its two actions lie in the
    # same connected component of the training comparison graph.
    adjacency = [set() for _ in range(action_dim)]
    for reference, candidate in zip(train_r.tolist(), train_c.tolist(), strict=True):
        adjacency[reference].add(candidate)
        adjacency[candidate].add(reference)
    component = np.full(action_dim, -1, dtype=np.int64)
    component_id = 0
    for start in range(action_dim):
        if component[start] >= 0 or not adjacency[start]:
            continue
        stack = [start]
        component[start] = component_id
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if component[neighbor] < 0:
                    component[neighbor] = component_id
                    stack.append(neighbor)
        component_id += 1
    if np.any(component[test_r] < 0) or np.any(component[test_r] != component[test_c]):
        raise EEAxisActionGraphCoverageError(
            "held-out action contrast is not identified by the training graph"
        )

    baseline_prediction = coefficients[test_c] - coefficients[test_r]
    indices = np.arange(test_y.size)
    model_prediction = q[indices, test_c] - q[indices, test_r]
    baseline_mae = float(np.mean(np.abs(baseline_prediction - test_y)))
    model_mae = float(np.mean(np.abs(model_prediction - test_y)))
    improvement = baseline_mae - model_mae
    relative = improvement / baseline_mae if baseline_mae > 0.0 else None
    active_actions = np.unique(np.concatenate((train_r, train_c)))
    return PairGeneralization(
        train_pairs=int(train_y.size),
        heldout_pairs=int(test_y.size),
        active_train_actions=int(active_actions.size),
        model_mae=model_mae,
        action_only_baseline_mae=baseline_mae,
        absolute_mae_improvement=float(improvement),
        relative_mae_improvement=float(relative) if relative is not None else None,
    )


def compute_strong_baseline_pair_generalization(
    *,
    train_reference_actions: np.ndarray,
    train_candidate_actions: np.ndarray,
    train_targets: np.ndarray,
    heldout_reference_actions: np.ndarray,
    heldout_candidate_actions: np.ndarray,
    heldout_targets: np.ndarray,
    heldout_q_surface: np.ndarray,
    action_dim: int,
) -> StrongBaselinePairGeneralization:
    """Evaluate pair learning against the strongest predeclared null model.

    This is the amended E1 metric.  It deliberately leaves
    :func:`compute_pair_generalization` unchanged so the original sealed E1
    ladder remains reproducible as historical diagnostic evidence.
    """

    legacy = compute_pair_generalization(
        train_reference_actions=train_reference_actions,
        train_candidate_actions=train_candidate_actions,
        train_targets=train_targets,
        heldout_reference_actions=heldout_reference_actions,
        heldout_candidate_actions=heldout_candidate_actions,
        heldout_targets=heldout_targets,
        heldout_q_surface=heldout_q_surface,
        action_dim=action_dim,
    )
    _train_r, _train_c, train_y = _pair_arrays(
        train_reference_actions,
        train_candidate_actions,
        train_targets,
        action_dim=action_dim,
        label="training",
    )
    _heldout_r, _heldout_c, heldout_y = _pair_arrays(
        heldout_reference_actions,
        heldout_candidate_actions,
        heldout_targets,
        action_dim=action_dim,
        label="held-out",
    )
    zero_mae = float(np.mean(np.abs(heldout_y)))
    train_median = float(np.median(train_y))
    median_mae = float(np.mean(np.abs(heldout_y - train_median)))
    candidates = (
        ("action_only", float(legacy.action_only_baseline_mae)),
        ("train_median", median_mae),
        ("zero", zero_mae),
    )
    strongest_name, strongest_mae = min(candidates, key=lambda row: (row[1], row[0]))
    improvement = strongest_mae - float(legacy.model_mae)
    relative = improvement / strongest_mae if strongest_mae > 0.0 else None
    return StrongBaselinePairGeneralization(
        train_pairs=legacy.train_pairs,
        heldout_pairs=legacy.heldout_pairs,
        active_train_actions=legacy.active_train_actions,
        model_mae=float(legacy.model_mae),
        action_only_baseline_mae=float(legacy.action_only_baseline_mae),
        zero_baseline_mae=zero_mae,
        train_median_value=train_median,
        train_median_baseline_mae=median_mae,
        strongest_baseline_name=strongest_name,
        strongest_state_independent_baseline_mae=float(strongest_mae),
        absolute_mae_improvement=float(improvement),
        relative_mae_improvement=float(relative) if relative is not None else None,
    )


def _input_key(
    state: np.ndarray,
    mask: np.ndarray,
    reference_action: int,
    candidate_action: int,
) -> bytes:
    digest = hashlib.sha256()
    digest.update(np.asarray(state, dtype="<f4").tobytes(order="C"))
    digest.update(np.asarray(mask, dtype=np.bool_).tobytes(order="C"))
    digest.update(int(reference_action).to_bytes(4, "little", signed=False))
    digest.update(int(candidate_action).to_bytes(4, "little", signed=False))
    return digest.digest()


def compute_observability_collisions(
    *,
    routes: tuple[str, ...] | list[str] | np.ndarray,
    policy_digests: tuple[str, ...] | list[str] | np.ndarray,
    states: np.ndarray,
    masks: np.ndarray,
    reference_actions: np.ndarray,
    candidate_actions: np.ndarray,
    targets: np.ndarray,
    persistent_positive_minimum: float = 0.05,
    persistent_negative_maximum: float = -0.05,
    persistent_count_per_sign: int = 2,
) -> ObservabilityCollisions:
    """Census exact input collisions without claiming sufficiency from absence."""

    values = np.asarray(states, dtype=np.float32)
    valid = np.asarray(masks)
    if values.ndim != 2 or min(values.shape) < 1:
        raise EEAxisInstrumentValidityError("states must be a nonempty matrix")
    if not np.all(np.isfinite(values)):
        raise EEAxisInstrumentValidityError("states must be finite")
    if valid.shape[0] != values.shape[0] or valid.ndim != 2 or valid.dtype != np.bool_:
        raise EEAxisInstrumentValidityError("masks must be a row-aligned boolean matrix")
    action_dim = valid.shape[1]
    reference, candidate, target = _pair_arrays(
        reference_actions,
        candidate_actions,
        targets,
        action_dim=action_dim,
        label="observability",
    )
    if target.size != values.shape[0]:
        raise EEAxisInstrumentValidityError("observability rows are not aligned")
    if not np.all(valid[np.arange(target.size), reference]) or not np.all(
        valid[np.arange(target.size), candidate]
    ):
        raise EEAxisInstrumentValidityError("observability actions violate their masks")
    if not math.isfinite(persistent_positive_minimum) or persistent_positive_minimum <= 0.0:
        raise EEAxisInstrumentValidityError(
            "persistent_positive_minimum must be finite and positive"
        )
    if not math.isfinite(persistent_negative_maximum) or persistent_negative_maximum >= 0.0:
        raise EEAxisInstrumentValidityError(
            "persistent_negative_maximum must be finite and negative"
        )
    if (
        isinstance(persistent_count_per_sign, bool)
        or not isinstance(persistent_count_per_sign, int)
        or persistent_count_per_sign < 1
    ):
        raise EEAxisInstrumentValidityError(
            "persistent_count_per_sign must be a positive integer"
        )
    route_values = np.asarray(routes, dtype=object)
    digest_values = np.asarray(policy_digests, dtype=object)
    if route_values.shape != (target.size,) or digest_values.shape != (target.size,):
        raise EEAxisInstrumentValidityError("route and policy provenance must align with rows")
    if any(not isinstance(value, str) or not value for value in route_values.tolist()):
        raise EEAxisInstrumentValidityError("routes must be nonempty strings")
    if any(
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
        for value in digest_values.tolist()
    ):
        raise EEAxisInstrumentValidityError("policy digests must be lowercase SHA-256")

    groups: dict[bytes, list[float]] = {}
    for row in range(target.size):
        digest = hashlib.sha256()
        digest.update(str(route_values[row]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(digest_values[row]).encode("ascii"))
        digest.update(
            _input_key(values[row], valid[row], int(reference[row]), int(candidate[row]))
        )
        key = digest.digest()
        groups.setdefault(key, []).append(float(target[row]))
    repeated = [group for group in groups.values() if len(group) >= 2]
    conflicting = [
        group
        for group in repeated
        if sum(value >= persistent_positive_minimum for value in group)
        >= persistent_count_per_sign
        and sum(value <= persistent_negative_maximum for value in group)
        >= persistent_count_per_sign
    ]
    absolute_residual = 0.0
    for group in groups.values():
        median = float(np.median(np.asarray(group, dtype=np.float64)))
        absolute_residual += float(math.fsum(abs(value - median) for value in group))
    mae_floor = absolute_residual / float(target.size)
    abs_mean = float(np.mean(np.abs(target)))
    normalized = mae_floor / abs_mean if abs_mean > 0.0 else None
    return ObservabilityCollisions(
        rows=int(target.size),
        unique_input_keys=len(groups),
        repeated_input_groups=len(repeated),
        repeated_rows=int(sum(len(group) for group in repeated)),
        conflicting_sign_groups=len(conflicting),
        conflicting_sign_rows=int(sum(len(group) for group in conflicting)),
        deterministic_mae_floor=float(mae_floor),
        target_abs_mean=abs_mean,
        normalized_mae_floor=float(normalized) if normalized is not None else None,
        persistent_positive_minimum=float(persistent_positive_minimum),
        persistent_negative_maximum=float(persistent_negative_maximum),
        persistent_count_per_sign=persistent_count_per_sign,
    )


__all__ = [
    "ActionMainEffect",
    "DeploymentDiversity",
    "E1_INSTRUMENT_SCHEMA",
    "EEAxisActionGraphCoverageError",
    "EEAxisInstrumentValidityError",
    "HeadPivotality",
    "ObservabilityCollisions",
    "PairGeneralization",
    "compute_action_main_effect",
    "compute_deployment_diversity",
    "compute_head_pivotality",
    "compute_observability_collisions",
    "compute_pair_generalization",
    "fit_action_only_effects",
    "score_action_only_effects",
]
