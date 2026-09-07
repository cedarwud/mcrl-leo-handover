"""W-153 -- frozen V0.14 learner/joint gate decisions."""

from __future__ import annotations

from types import SimpleNamespace

from mcrl.runtime.ee_axis_v014_gate import (
    adjudicate_head,
    adjudicate_joint,
    select_head_rung,
)


def _report(ratio: float):
    return SimpleNamespace(
        model_to_strongest_null_mae_ratio=ratio,
        skill_vs_strongest_null=1.0 - ratio,
    )


def test_head_rung_selection_and_two_of_three_positive_rule() -> None:
    reports = {
        1: {3: _report(0.9), 10: _report(0.5)},
        2: {3: _report(1.1), 10: _report(0.6)},
        3: {3: _report(0.8), 10: _report(1.2)},
    }
    selected, means = select_head_rung(
        reports, initialization_seeds=(1, 2, 3), update_rungs=(3, 10)
    )
    assert selected == 10
    assert means[10] < means[3]
    decision = adjudicate_head(
        reports, selected_rung=10, initialization_seeds=(1, 2, 3)
    )
    assert decision["passed"] is True
    assert decision["positive_initializations"] == 2


def _joint(*, agree: int, baseline: int, changed_agree: int, supported: int):
    return {
        "anchors": 100,
        "all_anchor_argmax_agreement_count": agree,
        "background_teacher_argmax_agreement_count": baseline,
        "teacher_change_exposure": 20,
        "teacher_change_agreement_count": changed_agree,
        "student_change_exposure": 20,
        "student_supported_change_count": supported,
    }


def test_joint_gate_binds_exposure_and_majority_supported_changes() -> None:
    passed = adjudicate_joint(
        {
            1: _joint(agree=90, baseline=80, changed_agree=12, supported=20),
            2: _joint(agree=88, baseline=80, changed_agree=11, supported=19),
            3: _joint(agree=79, baseline=80, changed_agree=8, supported=20),
        },
        initialization_seeds=(1, 2, 3),
    )
    assert passed["passed"] is True
    assert passed["improving_initializations"] == 2

    failed = adjudicate_joint(
        {
            1: _joint(agree=90, baseline=80, changed_agree=12, supported=10),
            2: _joint(agree=88, baseline=80, changed_agree=11, supported=10),
            3: _joint(agree=79, baseline=80, changed_agree=8, supported=10),
        },
        initialization_seeds=(1, 2, 3),
    )
    assert failed["passed"] is False
    assert failed["pooled_supported_change_rate"] == 0.5


def test_joint_gate_rejects_zero_student_change_exposure() -> None:
    rows = {
        seed: {
            **_joint(agree=90, baseline=80, changed_agree=12, supported=0),
            "student_change_exposure": 0,
        }
        for seed in (1, 2, 3)
    }
    decision = adjudicate_joint(rows, initialization_seeds=(1, 2, 3))
    assert decision["passed"] is False
    assert decision["pooled_has_student_change_exposure"] is False
