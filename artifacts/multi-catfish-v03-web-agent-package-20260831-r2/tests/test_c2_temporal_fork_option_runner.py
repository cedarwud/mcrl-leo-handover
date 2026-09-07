from __future__ import annotations

from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
SMC_DIR = HERE.parent / "smc-er-short-ep"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SMC_DIR))
sys.path.insert(0, str(HERE.parents[1] / "src"))

import c2_temporal_fork_learning_adapter as learning  # noqa: E402
import c2_temporal_fork_option_runner as runner  # noqa: E402
import c2_temporal_fork_trainer_backend as backend  # noqa: E402
from test_c2_temporal_fork_trainer_backend import (  # noqa: E402
    _backend as deterministic_backend,
)


def test_complete_option_builds_only_admitted_hash_bound_learning_items():
    service, wrapped, trainer = deterministic_backend()
    prepared = service.prepare_incumbent_hold(focal_user=0)
    built = prepared.run_forecast()
    assert built.certificate.passed
    inference_before_commit = trainer.inference_calls

    unit = runner.commit_prepared_option(
        prepared,
        opening_behavior_probability=0.25,
        discount_factor=0.9,
        block_id=7,
        selection_receipt_sha256="d" * 64,
    )

    assert unit.closure.plan.admitted
    assert len(unit.committed_payloads) == 4
    assert len(unit.bundles) == 4
    assert unit.sequence is not None
    assert unit.transition is not None
    assert learning.assert_admission_bound(unit.sequence) == unit.sequence.admission_proof
    assert learning.assert_admission_bound(unit.transition) == unit.transition.admission_proof
    assert unit.sequence.chronology_receipt_sha256 == unit.closure.plan.chronology_receipt_sha256
    assert unit.transition.chronology_receipt_sha256 == unit.closure.plan.chronology_receipt_sha256
    assert tuple(bundle.step_index for bundle in unit.bundles) == (0, 1, 2, 3)
    assert tuple(bundle.provenance["offset"] for bundle in unit.bundles) == (0, 1, 2, 3)
    for payload in unit.committed_payloads:
        assert payload.executed_actions[1] == payload.detached_main_actions[1]
        assert (
            payload.executed_physical_actions[1]
            == payload.detached_main_physical_actions[1]
        )
        if payload.offset < 3:
            assert payload.executed_physical_actions[0] == (1, 3)
        else:
            assert payload.executed_actions == payload.detached_main_actions
            assert (
                payload.executed_physical_actions
                == payload.detached_main_physical_actions
            )
    assert unit.closure.plan.main_focal_actions == (3, 3, 3, 11)
    assert unit.sequence.constituent_bundle_ids == unit.closure.plan.main_bundle_ids
    assert unit.transition.bootstrap_discount == 0.0
    assert wrapped._offset == 4
    assert trainer.inference_calls == inference_before_commit + 3


def test_option_commit_rejects_an_unforecast_prepared_fork():
    service, _wrapped, _trainer = deterministic_backend()
    prepared = service.prepare_incumbent_hold(focal_user=0)

    try:
        runner.commit_prepared_option(
            prepared,
            opening_behavior_probability=1.0,
            discount_factor=0.9,
            block_id=0,
            selection_receipt_sha256="d" * 64,
        )
    except runner.C2OptionRunnerError as error:
        assert "completed forecast" in str(error)
    else:  # pragma: no cover - explicit fail-closed assertion
        raise AssertionError("unforecast option was committed")
