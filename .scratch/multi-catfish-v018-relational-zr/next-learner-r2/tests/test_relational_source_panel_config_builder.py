"""Pure tests for the canonical V0.18 source-panel config builder."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest


R2_ROOT = Path(__file__).resolve().parents[1]
REPO = R2_ROOT.parents[2]
sys.path.insert(0, str(R2_ROOT))
sys.path.insert(0, str(REPO / "src"))

from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402
from relational_learner_runner import read_run_config  # noqa: E402
import relational_simulator_source_adapter as adapter  # noqa: E402
import relational_source_panel_config_builder as builder  # noqa: E402


TRAIN_WORLDS = [2026120501, 2026120502, 2026120503, 2026120504]
VALIDATION_WORLDS = [2026120505, 2026120506, 2026120507]
LINEAGES = [2026092101, 2026092102, 2026092103]


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _sha(letter: str) -> str:
    return letter * 64


def _plan(tmp_path: Path, *, relative_paths: bool = False) -> dict[str, object]:
    contract = tmp_path / "learner-contract.md"
    contract.write_text("Status: `FROZEN_BEFORE_OUTCOME`\n", encoding="utf-8")
    code_manifest = tmp_path / "code-manifest.sha256"
    code_manifest.write_text("synthetic code closure\n", encoding="utf-8")
    prereg = tmp_path / "prereg.md"
    prereg.write_text("synthetic frozen prereg\n", encoding="utf-8")
    for name in ("q1", "q2", "tle"):
        (tmp_path / name).mkdir(exist_ok=True)
    output = tmp_path / "panel-output"

    def path(value: Path) -> str:
        if relative_paths:
            return value.relative_to(tmp_path).as_posix()
        return str(value)

    worlds = (*TRAIN_WORLDS, *VALIDATION_WORLDS)
    return {
        "schema": builder.PANEL_PLAN_SCHEMA,
        "schema_version": 1,
        "learner_contract_path": path(contract),
        "learner_contract_sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
        "code_manifest_path": path(code_manifest),
        "code_manifest_sha256": hashlib.sha256(code_manifest.read_bytes()).hexdigest(),
        "q1_checkpoint_root": path(tmp_path / "q1"),
        "q2_checkpoint_root": path(tmp_path / "q2"),
        "q1_checkpoint_sha256_by_lineage": [
            {"lineage": lineage, "sha256": _sha("a")} for lineage in LINEAGES
        ],
        "q2_checkpoint_sha256_by_lineage": [
            {"lineage": lineage, "sha256": _sha("b")} for lineage in LINEAGES
        ],
        "q1_parameter_sha256_by_lineage": [
            {"lineage": lineage, "sha256": _sha("c")} for lineage in LINEAGES
        ],
        "q2_parameter_sha256_by_lineage": [
            {"lineage": lineage, "sha256": _sha("d")} for lineage in LINEAGES
        ],
        "prereg_path": path(prereg),
        "tle_root": path(tmp_path / "tle"),
        "output_root": path(output),
        "train_worlds": TRAIN_WORLDS,
        "validation_worlds": VALIDATION_WORLDS,
        "lineages": LINEAGES,
        "initialization_lineages": [
            {
                "initialization_seed": seed,
                "lineage": lineage,
                "schedule_seed": seed + 100,
            }
            for seed, lineage in zip((2026120511, 2026120512, 2026120513), LINEAGES)
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
        "contract_status": builder.FROZEN_CONTRACT_STATUS,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "outcome_opened": False,
    }


def test_build_panel_is_the_exact_rectangle_and_run_config_is_compatible(
    tmp_path: Path,
) -> None:
    payload = _plan(tmp_path)
    plan = builder.validate_plan(payload, plan_sha256=_sha("e"))
    built = builder.build_panel(plan)

    assert len(built.configs) == 21
    identities = {
        (config["split"], config["world_seed"], config["lineage"])
        for _path, config, _digest in built.configs
    }
    assert identities == {
        (split, world, lineage)
        for split, worlds in (("TRAIN", TRAIN_WORLDS), ("VALIDATION", VALIDATION_WORLDS))
        for world in worlds
        for lineage in LINEAGES
    }
    assert all(set(config) == adapter.CONFIG_FIELDS for _path, config, _digest in built.configs)
    assert all(
        config["code_manifest_path"] == str(plan.code_manifest_path)
        and config["code_manifest_sha256"] == plan.code_manifest_sha256
        for _path, config, _digest in built.configs
    )
    assert all(config["users"] == 100 and config["steps"] == 10 for _path, config, _digest in built.configs)
    assert all(config["action_dim"] == 28 for _path, config, _digest in built.configs)
    assert all(config["kappa_bits_hex"] == builder.EXPECTED_KAPPA_HEX for _path, config, _digest in built.configs)
    assert len(built.learner_plan["train_source_paths"]) == 12
    assert len(built.learner_plan["validation_source_paths"]) == 9
    assert built.learner_config["train_source_paths"] == built.learner_plan["train_source_paths"]
    assert built.learner_config["validation_source_paths"] == built.learner_plan["validation_source_paths"]
    assert built.manifest["q1_parameter_sha256_by_lineage"] == payload["q1_parameter_sha256_by_lineage"]
    assert built.manifest["q2_parameter_sha256_by_lineage"] == payload["q2_parameter_sha256_by_lineage"]

    config_path = tmp_path / "synthetic-run-config.json"
    config_path.write_bytes(_canonical(built.learner_config))
    _config, train_paths, validation_paths = read_run_config(config_path)
    assert len(train_paths) == 12
    assert len(validation_paths) == 9


def test_write_panel_binds_external_files_and_rejects_rewrite(tmp_path: Path) -> None:
    payload = _plan(tmp_path, relative_paths=True)
    plan_path = tmp_path / "panel-plan.json"
    plan_path.write_bytes(_canonical(payload))
    plan_sha256 = hashlib.sha256(plan_path.read_bytes()).hexdigest()

    receipt = builder.write_panel(plan_path, expected_sha256=plan_sha256)
    assert receipt["config_count"] == 21
    output_root = Path(str(receipt["output_root"]))
    manifest_path = output_root / "panel-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    assert manifest["manifest_sha256"] == builder.canonical_sha256(
        {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    )
    assert len(manifest["adapter_configs"]) == 21
    for entry in manifest["adapter_configs"]:
        config_path = Path(entry["path"])
        assert not config_path.is_symlink()
        assert hashlib.sha256(config_path.read_bytes()).hexdigest() == entry["config_sha256"]
        config = adapter.load_shard_config(
            config_path, expected_sha256=entry["config_sha256"]
        )
        assert config.world_seed == entry["world_seed"]
        assert config.lineage == entry["lineage"]
        assert config.split == entry["split"]

    learner_config_path = output_root / "learner-run-config.json"
    _config, train_paths, validation_paths = read_run_config(learner_config_path)
    assert len(train_paths) == 12
    assert len(validation_paths) == 9
    with pytest.raises(builder.SourcePanelConfigBuilderError, match="overwrite"):
        builder.write_panel(plan_path, expected_sha256=plan_sha256)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("users", 99, "shape"),
        ("steps", 9, "shape"),
        ("action_dim", 27, "shape"),
        ("kappa_bits_hex", "0x1.0p+1", "kappa"),
        ("learner_update", True, "forbidden"),
        ("contract_status", "DRAFT_NOT_FROZEN_NO_OUTCOME_OPENED", "frozen"),
    ),
)
def test_plan_rejects_shape_scale_and_boundary_drift(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    payload = _plan(tmp_path)
    payload[field] = value
    with pytest.raises(builder.SourcePanelConfigBuilderError, match=message):
        builder.validate_plan(payload)


def test_plan_rejects_field_root_drift_world_overlap_and_symlink(tmp_path: Path) -> None:
    payload = _plan(tmp_path)
    payload["field_root_digest_by_world"][0]["sha256"] = _sha("f")
    with pytest.raises(builder.SourcePanelConfigBuilderError, match="field root"):
        builder.build_panel(builder.validate_plan(payload))

    payload = _plan(tmp_path)
    payload["validation_worlds"][0] = payload["train_worlds"][0]
    with pytest.raises(builder.SourcePanelConfigBuilderError, match="overlap"):
        builder.validate_plan(payload)

    payload = _plan(tmp_path)
    payload["train_worlds"][0] = 2026120401
    with pytest.raises(builder.SourcePanelConfigBuilderError, match="analytic world"):
        builder.validate_plan(payload)

    payload = _plan(tmp_path)
    link = tmp_path / "q1-link"
    link.symlink_to(tmp_path / "q1", target_is_directory=True)
    payload["q1_checkpoint_root"] = str(link)
    with pytest.raises(builder.SourcePanelConfigBuilderError, match="symlink"):
        builder.validate_plan(payload)


def test_plan_fields_are_closed_and_missing_identity_is_not_inferred(tmp_path: Path) -> None:
    payload = _plan(tmp_path)
    payload.pop("lineages")
    with pytest.raises(builder.SourcePanelConfigBuilderError, match="closed"):
        builder.validate_plan(payload)

    payload = _plan(tmp_path)
    payload["lineages"] = [LINEAGES[0], LINEAGES[1]]
    with pytest.raises(builder.SourcePanelConfigBuilderError, match="exactly 3"):
        builder.validate_plan(payload)
