"""Pure pre-outcome V0.19 panel-plan unit-mode tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve()
V019 = HERE.parents[1]
REPO = V019.parents[1]
sys.path.insert(0, str(V019 / "learner"))
sys.path.insert(0, str(REPO / "src"))

from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402
import relational_source_panel_config_builder_v019 as builder  # noqa: E402
import relational_simulator_source_adapter_v019 as adapter  # noqa: E402


TRAIN_WORLDS = [2026120701, 2026120702, 2026120703, 2026120704]
VALIDATION_WORLDS = [2026120705, 2026120706, 2026120707]
LINEAGES = [2026092101, 2026092102, 2026092103]


def _digest(letter: str) -> str:
    return letter * 64


def _plan(tmp_path: Path) -> dict[str, object]:
    contract = tmp_path / "contract.md"
    contract.write_text("Status: `FROZEN_BEFORE_OUTCOME`\n", encoding="utf-8")
    manifest = tmp_path / "code-manifest.sha256"
    manifest.write_text("v019 synthetic closure\n", encoding="utf-8")
    prereg = tmp_path / "prereg.md"
    prereg.write_text("v019 synthetic prereg\n", encoding="utf-8")
    for name in ("q1", "q2", "tle"):
        (tmp_path / name).mkdir(exist_ok=True)
    worlds = (*TRAIN_WORLDS, *VALIDATION_WORLDS)
    return {
        "schema": builder.PANEL_PLAN_SCHEMA,
        "schema_version": 1,
        "learner_contract_path": str(contract),
        "learner_contract_sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
        "code_manifest_path": str(manifest),
        "code_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "q1_checkpoint_root": str(tmp_path / "q1"),
        "q2_checkpoint_root": str(tmp_path / "q2"),
        "q1_checkpoint_sha256_by_lineage": [
            {"lineage": value, "sha256": _digest("a")} for value in LINEAGES
        ],
        "q2_checkpoint_sha256_by_lineage": [
            {"lineage": value, "sha256": _digest("b")} for value in LINEAGES
        ],
        "q1_parameter_sha256_by_lineage": [
            {"lineage": value, "sha256": _digest("c")} for value in LINEAGES
        ],
        "q2_parameter_sha256_by_lineage": [
            {"lineage": value, "sha256": _digest("d")} for value in LINEAGES
        ],
        "prereg_path": str(prereg),
        "tle_root": str(tmp_path / "tle"),
        "output_root": str(tmp_path / "output"),
        "train_worlds": TRAIN_WORLDS,
        "validation_worlds": VALIDATION_WORLDS,
        "lineages": LINEAGES,
        "initialization_lineages": [
            {
                "initialization_seed": seed,
                "lineage": lineage,
                "schedule_seed": seed + 100,
            }
            for seed, lineage in zip((2026120711, 2026120712, 2026120713), LINEAGES)
        ],
        "field_component": builder.EXPECTED_FIELD_COMPONENT,
        "field_root_digest_by_world": [
            {
                "world_seed": world,
                "sha256": KeyedFadingField.from_components(
                    builder.EXPECTED_FIELD_COMPONENT, world
                ).root_digest,
            }
            for world in worlds
        ],
        "users": 100,
        "steps": 10,
        "action_dim": 28,
        "kappa_bits_hex": float(OPS3_KAPPA_BITS).hex(),
        "output_unit_mode": builder.EXPECTED_OUTPUT_UNIT_MODE,
        "contract_status": builder.FROZEN_CONTRACT_STATUS,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "outcome_opened": False,
    }


def test_panel_and_materialized_run_plan_carry_explicit_normalized_mode(
    tmp_path: Path,
) -> None:
    plan = builder.validate_plan(_plan(tmp_path), plan_sha256=_digest("e"))
    built = builder.build_panel(plan)
    assert built.learner_plan["output_unit_mode"] == builder.EXPECTED_OUTPUT_UNIT_MODE
    assert built.learner_plan["network"]["output_unit_mode"] == builder.EXPECTED_OUTPUT_UNIT_MODE
    assert built.learner_config["output_unit_mode"] == builder.EXPECTED_OUTPUT_UNIT_MODE
    assert built.learner_config["network"]["output_unit_mode"] == builder.EXPECTED_OUTPUT_UNIT_MODE
    assert built.manifest["output_unit_mode"] == builder.EXPECTED_OUTPUT_UNIT_MODE
    assert all(
        payload["output_unit_mode"] == builder.EXPECTED_OUTPUT_UNIT_MODE
        for _path, payload, _digest_value in built.configs
    )
    for index, (_path, payload, config_sha256) in enumerate(built.configs):
        config_path = tmp_path / f"adapter-{index}.json"
        config_path.write_bytes(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        )
        loaded = adapter.load_shard_config(config_path, expected_sha256=config_sha256)
        assert loaded.output_unit_mode == builder.EXPECTED_OUTPUT_UNIT_MODE


def test_panel_plan_rejects_missing_or_different_unit_mode(tmp_path: Path) -> None:
    payload = _plan(tmp_path)
    payload.pop("output_unit_mode")
    with pytest.raises(builder.SourcePanelConfigBuilderError, match="closed"):
        builder.validate_plan(payload)

    payload = _plan(tmp_path)
    payload["output_unit_mode"] = "raw_bits"
    with pytest.raises(builder.SourcePanelConfigBuilderError, match="normalized_bits_per_kappa"):
        builder.validate_plan(payload)

    payload = _plan(tmp_path)
    payload["network"] = {"output_unit_mode": "raw_bits"}
    # The panel plan does not contain a separate network object; adding one is
    # rejected as an unknown field instead of being silently ignored.
    with pytest.raises(builder.SourcePanelConfigBuilderError, match="closed"):
        builder.validate_plan(payload)
