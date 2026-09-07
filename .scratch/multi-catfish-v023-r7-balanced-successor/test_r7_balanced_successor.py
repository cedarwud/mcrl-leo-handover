"""Focused R7 semantic tests; these use no simulator, TLE, or learner fit."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gate = _load("r7_balanced_successor_gate", HERE / "r7_balanced_successor_gate.py")
preflight = _load("preflight_r7_balanced", HERE / "preflight_r7_balanced.py")
reseal = _load("reseal_r7_preflight", HERE / "reseal_r7_preflight.py")


def _shards(*, all_negative: bool = False):
    result = []
    for world in gate.WORLDS:
        # Every world contributes three eligible positives and 12 negatives.
        target = np.array(([-0.03] * 12) if all_negative else ([0.03] * 3 + [-0.03] * 12))
        informed = np.array(([0.1] * 3 + [-0.1] * 3 + [0.1] * 9) if not all_negative else [-0.1] * 12)
        placebo = np.array(([-0.1] * 3 + [-0.1] * 6 + [0.1] * 6) if not all_negative else [-0.1] * 12)
        for seed in gate.STUDENT_SEEDS:
            result.append(gate.HeldOutShard(
                world, seed, "INFORMED", informed, target,
                gate.tie_aware_spearman(informed, target),
            ))
            result.append(gate.HeldOutShard(
                world, seed, "MATCHED_PLACEBO", placebo, target,
                gate.tie_aware_spearman(placebo, target),
            ))
    return result


def test_balanced_predicate_is_decisive_while_raw_gap_is_only_serialized() -> None:
    panel = gate.evaluate_r7_panel(
        _shards(), informed_world_wins=8,
        informed_seed_nonnegative_worlds={seed: 8 for seed in gate.STUDENT_SEEDS},
    )
    aggregate = panel["aggregate"]
    assert panel["predicates"]["held_out_learner"] is True
    assert aggregate["informed_minus_placebo_balanced_accuracy"] >= 0.05
    assert aggregate["informed_minus_placebo_raw_sign_accuracy"] == pytest.approx(0.0)
    assert panel["predicates"]["raw_sign_accuracy_reported_nondecisive"] is True
    for arm in gate.ARMS:
        sign = panel["seed_metrics"][str(gate.STUDENT_SEEDS[0])][arm]["sign"]
        assert "raw_sign_accuracy" in sign and "raw_correct_rows" in sign
        world_sign = panel["world_metrics"][str(gate.WORLDS[0])][arm][
            "seed_metrics"
        ][str(gate.STUDENT_SEEDS[0])]["sign"]
        assert {
            "positive_denominator",
            "negative_denominator",
            "correct_positive",
            "correct_negative",
            "positive_recall",
            "negative_recall",
            "balanced_accuracy",
            "raw_sign_accuracy",
            "excluded_rows",
        } <= set(world_sign)


def test_zero_predictions_and_missing_class_denominators_fail_closed() -> None:
    zero = gate.balanced_sign_metrics([0.0, 0.0], [0.03, -0.03])
    assert zero["correct_positive"] == 0 and zero["correct_negative"] == 0
    assert zero["balanced_accuracy"] == 0.0
    panel = gate.evaluate_r7_panel(
        _shards(all_negative=True), informed_world_wins=0,
        informed_seed_nonnegative_worlds={seed: 0 for seed in gate.STUDENT_SEEDS},
    )
    assert panel["predicates"]["finite_nonzero_class_denominators"] is False
    assert panel["predicates"]["held_out_learner"] is False


def test_seed_spearman_is_pooled_over_rows_not_averaged_over_worlds() -> None:
    shards = []
    target = np.asarray([0.03, 0.04, 0.05, -0.03, -0.04, -0.05])
    informed_by_world = []
    for offset, world in enumerate(gate.WORLDS):
        informed = target + 10.0 * offset
        placebo = -target + 10.0 * offset
        informed_by_world.append(informed)
        for seed in gate.STUDENT_SEEDS:
            shards.append(gate.HeldOutShard(
                world,
                seed,
                "INFORMED",
                informed,
                target,
                gate.tie_aware_spearman(informed, target),
            ))
            shards.append(gate.HeldOutShard(
                world,
                seed,
                "MATCHED_PLACEBO",
                placebo,
                target,
                gate.tie_aware_spearman(placebo, target),
            ))
    panel = gate.evaluate_r7_panel(shards)
    pooled = gate.tie_aware_spearman(
        np.concatenate(informed_by_world),
        np.concatenate([target for _world in gate.WORLDS]),
    )
    reported = panel["seed_metrics"][str(gate.STUDENT_SEEDS[0])]["INFORMED"][
        "spearman"
    ]
    per_world_mean = np.mean([
        panel["world_metrics"][str(world)]["INFORMED"]["mean_spearman"]
        for world in gate.WORLDS
    ])
    assert reported == pytest.approx(pooled)
    assert reported != pytest.approx(per_world_mean)


def test_fresh_panels_and_all_required_metrics_are_frozen_in_preflight() -> None:
    reseal.build()
    manifest = preflight.validate_manifest()
    assert manifest["worlds"] == list(range(2026121801, 2026121809))
    assert manifest["student_seeds"] == [2026135201, 2026135202, 2026135203]
    assert min(manifest["worlds"]) == 2026121801
    assert min(manifest["student_seeds"]) == 2026135201
    assert manifest["initial_network_sha256_by_seed"] == preflight.INITIAL_DIGESTS
    assert manifest["manifest_status"] == "DRAFT_PRE_OUTCOME" and manifest["launch"] == "NO_LAUNCH"
    assert "r7_launch_blocker.sh" in {Path(item["path"]).name for item in manifest["bindings"]}


def test_thread_environment_is_exact_and_fail_closed() -> None:
    assert gate.validate_process_environment(gate.PROCESS_ENVIRONMENT) == gate.PROCESS_ENVIRONMENT
    with pytest.raises(gate.R7BalancedGateError, match="process environment"):
        gate.validate_process_environment({"OMP_NUM_THREADS": "2"})


def test_r6_section14_precedence_is_preserved_with_r7_tokens() -> None:
    base = dict(
        integrity=True, pair_coverage=True, mechanics=True, physical_signature=True,
        teacher_composition=True, target_support=True, held_out_learner=True,
        world_stability=True, action_exposure=True, literal_11=True,
        harmful_partial=True, topology_consistency=True, learned_composition=True,
        service=True,
    )
    assert gate.adjudicate_section14_r7(**base) == "GO_FIXED_LEARNER_SCREEN_CONTRACT_R7"
    assert gate.adjudicate_section14_r7(**(base | {"held_out_learner": False})) == "STOP_OBSERVABILITY_R7"
    assert gate.adjudicate_section14_r7(**(base | {"service": False})) == "REDESIGN_INTERFACE_R7"
