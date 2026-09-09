"""Outcome-independent decision rules for the V0.14 learner gate."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from ..errors import MCRLContractError


V014_JOINT_MIN_TEACHER_CHANGE_AGREEMENT = 0.50
V014_JOINT_MIN_SUPPORTED_CHANGE_RATE = 0.50
V014_MIN_POSITIVE_INITIALIZATIONS = 2


class EEAxisV014GateError(MCRLContractError):
    """A V0.14 report panel cannot be adjudicated mechanically."""


def select_head_rung(
    reports: Mapping[int, Mapping[int, Any]],
    *,
    initialization_seeds: Sequence[int],
    update_rungs: Sequence[int],
) -> tuple[int, dict[int, float]]:
    """Choose the minimum mean model/null ratio, ties to the smaller rung."""

    seeds = tuple(int(value) for value in initialization_seeds)
    rungs = tuple(int(value) for value in update_rungs)
    if len(seeds) < 1 or len(set(seeds)) != len(seeds) or set(reports) != set(seeds):
        raise EEAxisV014GateError("head reports do not match initialization seeds")
    if len(rungs) < 1 or len(set(rungs)) != len(rungs) or any(value < 1 for value in rungs):
        raise EEAxisV014GateError("update rungs must be distinct positive integers")
    means: dict[int, float] = {}
    for rung in rungs:
        ratios: list[float] = []
        for seed in seeds:
            report = reports[seed].get(rung)
            value = getattr(report, "model_to_strongest_null_mae_ratio", None)
            try:
                ratio = float(value)
            except (TypeError, ValueError, OverflowError) as error:
                raise EEAxisV014GateError("head report ratio is missing") from error
            if not math.isfinite(ratio) or ratio < 0.0:
                raise EEAxisV014GateError("head report ratio is invalid")
            ratios.append(ratio)
        means[rung] = float(np.mean(ratios))
    selected = min(rungs, key=lambda value: (means[value], value))
    return selected, means


def adjudicate_head(
    reports: Mapping[int, Mapping[int, Any]],
    *,
    selected_rung: int,
    initialization_seeds: Sequence[int],
) -> dict[str, object]:
    """Apply the frozen positive-mean and two-of-three skill rule."""

    seeds = tuple(int(value) for value in initialization_seeds)
    if len(seeds) != 3 or set(reports) != set(seeds):
        raise EEAxisV014GateError("head gate requires exactly three initializations")
    skills: dict[str, float] = {}
    for seed in seeds:
        report = reports[seed].get(int(selected_rung))
        value = getattr(report, "skill_vs_strongest_null", None)
        try:
            skill = float(value)
        except (TypeError, ValueError, OverflowError) as error:
            raise EEAxisV014GateError("head skill is missing") from error
        if not math.isfinite(skill):
            raise EEAxisV014GateError("head skill is non-finite")
        skills[str(seed)] = skill
    mean_skill = float(np.mean(list(skills.values())))
    positive = sum(value > 0.0 for value in skills.values())
    passed = mean_skill > 0.0 and positive >= V014_MIN_POSITIVE_INITIALIZATIONS
    return {
        "passed": passed,
        "selected_rung": int(selected_rung),
        "skills": skills,
        "mean_skill": mean_skill,
        "positive_initializations": positive,
    }


def _count(row: Mapping[str, Any], name: str, *, at_most: int | None = None) -> int:
    value = row.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise EEAxisV014GateError(f"joint {name} must be an integer")
    result = int(value)
    if result < 0 or (at_most is not None and result > at_most):
        raise EEAxisV014GateError(f"joint {name} is out of bounds")
    return result


def adjudicate_joint(
    diagnostics: Mapping[int, Mapping[str, Any]],
    *,
    initialization_seeds: Sequence[int],
) -> dict[str, object]:
    """Screen the summed learned policy against its oracle teacher surface."""

    seeds = tuple(int(value) for value in initialization_seeds)
    if len(seeds) != 3 or set(diagnostics) != set(seeds):
        raise EEAxisV014GateError("joint gate requires exactly three initializations")
    totals = {
        "anchors": 0,
        "agree": 0,
        "baseline": 0,
        "teacher_exposure": 0,
        "teacher_agree": 0,
        "student_exposure": 0,
        "student_supported": 0,
    }
    per_initialization: dict[str, dict[str, float | int | bool]] = {}
    improving = 0
    recovering = 0
    exposed = 0
    supported = 0
    for seed in seeds:
        row = diagnostics[seed]
        anchors = _count(row, "anchors")
        if anchors < 1:
            raise EEAxisV014GateError("joint diagnostics need validation anchors")
        agree = _count(
            row, "all_anchor_argmax_agreement_count", at_most=anchors
        )
        baseline = _count(
            row, "background_teacher_argmax_agreement_count", at_most=anchors
        )
        teacher_exposure = _count(
            row, "teacher_change_exposure", at_most=anchors
        )
        teacher_agree = _count(
            row, "teacher_change_agreement_count", at_most=teacher_exposure
        )
        student_exposure = _count(
            row, "student_change_exposure", at_most=anchors
        )
        student_supported = _count(
            row, "student_supported_change_count", at_most=student_exposure
        )
        recovery_rate = (
            teacher_agree / teacher_exposure if teacher_exposure else 0.0
        )
        support_rate = (
            student_supported / student_exposure if student_exposure else 0.0
        )
        improves = agree > baseline
        recovers = (
            teacher_exposure > 0
            and recovery_rate >= V014_JOINT_MIN_TEACHER_CHANGE_AGREEMENT
        )
        has_student_exposure = student_exposure > 0
        stays_supported = (
            has_student_exposure
            and support_rate > V014_JOINT_MIN_SUPPORTED_CHANGE_RATE
        )
        improving += int(improves)
        recovering += int(recovers)
        exposed += int(has_student_exposure)
        supported += int(stays_supported)
        totals["anchors"] += anchors
        totals["agree"] += agree
        totals["baseline"] += baseline
        totals["teacher_exposure"] += teacher_exposure
        totals["teacher_agree"] += teacher_agree
        totals["student_exposure"] += student_exposure
        totals["student_supported"] += student_supported
        per_initialization[str(seed)] = {
            "agreement": agree / anchors,
            "baseline_agreement": baseline / anchors,
            "teacher_change_exposure": teacher_exposure,
            "teacher_change_agreement": recovery_rate,
            "student_change_exposure": student_exposure,
            "student_supported_change_rate": support_rate,
            "has_student_change_exposure": has_student_exposure,
            "improves_on_background": improves,
            "recovers_teacher_changes": recovers,
            "student_changes_supported": stays_supported,
        }
    pooled_recovery = (
        totals["teacher_agree"] / totals["teacher_exposure"]
        if totals["teacher_exposure"]
        else 0.0
    )
    pooled_support = (
        totals["student_supported"] / totals["student_exposure"]
        if totals["student_exposure"]
        else 0.0
    )
    pooled_improvement = totals["agree"] > totals["baseline"]
    pooled_has_exposure = totals["student_exposure"] > 0
    passed = (
        pooled_has_exposure
        and pooled_support > V014_JOINT_MIN_SUPPORTED_CHANGE_RATE
        and exposed >= V014_MIN_POSITIVE_INITIALIZATIONS
        and supported >= V014_MIN_POSITIVE_INITIALIZATIONS
    )
    return {
        "passed": passed,
        "pooled_argmax_agreement": totals["agree"] / totals["anchors"],
        "pooled_background_teacher_agreement": (
            totals["baseline"] / totals["anchors"]
        ),
        "pooled_teacher_change_agreement": pooled_recovery,
        "pooled_supported_change_rate": pooled_support,
        "pooled_has_student_change_exposure": pooled_has_exposure,
        "improving_initializations": improving,
        "recovering_initializations": recovering,
        "exposed_initializations": exposed,
        "supported_initializations": supported,
        "per_initialization": per_initialization,
    }


__all__ = [
    "EEAxisV014GateError",
    "V014_JOINT_MIN_SUPPORTED_CHANGE_RATE",
    "V014_JOINT_MIN_TEACHER_CHANGE_AGREEMENT",
    "V014_MIN_POSITIVE_INITIALIZATIONS",
    "adjudicate_head",
    "adjudicate_joint",
    "select_head_rung",
]
