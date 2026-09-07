#!/usr/bin/env python3
"""Verify the exact V0.19 panel identity and generated closure before execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

import relational_source_panel_config_builder_v019 as panel_builder
from relational_learner_runner_v019 import read_run_config


TRAIN_WORLDS = (2026120701, 2026120702, 2026120703, 2026120704)
VALIDATION_WORLDS = (2026120705, 2026120706, 2026120707)
LINEAGES = (2026092101, 2026092102, 2026092103)
INITIALIZATION_LINEAGES = (
    (2026120711, 2026092101),
    (2026120712, 2026092102),
    (2026120713, 2026092103),
)
SCHEDULE_SEEDS = (2026120721, 2026120722, 2026120723)


class FrozenPanelClosureError(ValueError):
    """The generated panel differs from the frozen V0.19 declaration."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise FrozenPanelClosureError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_canonical(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FrozenPanelClosureError(f"noncanonical JSON: {path}") from error
    if not isinstance(value, dict) or raw != _canonical_bytes(value):
        raise FrozenPanelClosureError(f"noncanonical JSON: {path}")
    return value


def _initialization_rows(value: object) -> tuple[tuple[int, int], ...]:
    if not isinstance(value, list):
        raise FrozenPanelClosureError("identity binding is not a list")
    result: list[tuple[int, int]] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != {
            "initialization_seed",
            "lineage",
            "schedule_seed",
        }:
            raise FrozenPanelClosureError("identity binding is malformed")
        result.append((int(item["initialization_seed"]), int(item["lineage"])))
    return tuple(result)


def verify(*, plan_path: Path, panel_root: Path) -> dict[str, object]:
    plan_path = plan_path.absolute()
    panel_root = panel_root.absolute()
    plan_sha256 = _sha256(plan_path)
    plan_payload = _read_canonical(plan_path)
    validated = panel_builder.validate_plan(
        plan_payload,
        plan_sha256=plan_sha256,
        base=plan_path.parent,
    )
    if _sha256(validated.learner_contract_path) != validated.learner_contract_sha256:
        raise FrozenPanelClosureError("learner contract hash differs from the plan")
    if _sha256(validated.code_manifest_path) != validated.code_manifest_sha256:
        raise FrozenPanelClosureError("code-manifest file hash differs from the plan")
    contract_text = validated.learner_contract_path.read_text(encoding="utf-8")
    if "Status: `FROZEN_BEFORE_OUTCOME`" not in contract_text:
        raise FrozenPanelClosureError("learner contract is not frozen")
    if validated.train_worlds != TRAIN_WORLDS:
        raise FrozenPanelClosureError("TRAIN worlds differ from the V0.19 declaration")
    if validated.validation_worlds != VALIDATION_WORLDS:
        raise FrozenPanelClosureError("VALIDATION worlds differ from the V0.19 declaration")
    if validated.lineages != LINEAGES:
        raise FrozenPanelClosureError("lineages differ from the V0.19 declaration")
    initialization_rows = _initialization_rows(
        plan_payload.get("initialization_lineages")
    )
    if initialization_rows != INITIALIZATION_LINEAGES:
        raise FrozenPanelClosureError("initialization mapping differs from V0.19")
    schedule_rows = tuple(
        int(item["schedule_seed"])
        for item in plan_payload["initialization_lineages"]  # type: ignore[index]
    )
    if schedule_rows != SCHEDULE_SEEDS:
        raise FrozenPanelClosureError("schedule seeds differ from V0.19")
    if validated.output_unit_mode != panel_builder.EXPECTED_OUTPUT_UNIT_MODE:
        raise FrozenPanelClosureError("panel plan output unit is not normalized")
    if validated.output_root != panel_root:
        raise FrozenPanelClosureError("panel root differs from the plan output root")

    manifest_path = panel_root / "panel-manifest.json"
    manifest = _read_canonical(manifest_path)
    manifest_body = dict(manifest)
    recorded_manifest_sha256 = manifest_body.pop("manifest_sha256", None)
    computed_manifest_sha256 = hashlib.sha256(_canonical_bytes(manifest_body)).hexdigest()
    if recorded_manifest_sha256 != computed_manifest_sha256:
        raise FrozenPanelClosureError("panel manifest self-hash mismatch")
    if manifest.get("plan_sha256") != plan_sha256:
        raise FrozenPanelClosureError("panel manifest does not bind the plan")
    for key, expected in (
        ("train_worlds", list(TRAIN_WORLDS)),
        ("validation_worlds", list(VALIDATION_WORLDS)),
        ("lineages", list(LINEAGES)),
        ("output_unit_mode", panel_builder.EXPECTED_OUTPUT_UNIT_MODE),
        ("contract_status", panel_builder.FROZEN_CONTRACT_STATUS),
        ("test_split_opened", False),
        ("episode_training", False),
        ("learner_update", False),
        ("outcome_opened", False),
    ):
        if manifest.get(key) != expected:
            raise FrozenPanelClosureError(f"panel manifest field drifted: {key}")

    run_plan_path = panel_root / "learner-run-plan.json"
    run_config_path = panel_root / "learner-run-config.json"
    if manifest.get("learner_run_plan_path") != str(run_plan_path):
        raise FrozenPanelClosureError("manifest learner-run-plan path drifted")
    if manifest.get("learner_run_config_path") != str(run_config_path):
        raise FrozenPanelClosureError("manifest learner-run-config path drifted")
    if manifest.get("learner_run_plan_sha256") != _sha256(run_plan_path):
        raise FrozenPanelClosureError("learner-run-plan hash mismatch")
    if manifest.get("learner_run_config_sha256") != _sha256(run_config_path):
        raise FrozenPanelClosureError("learner-run-config hash mismatch")

    config, _train_paths, _validation_paths = read_run_config(run_config_path)
    if config.train_worlds != TRAIN_WORLDS:
        raise FrozenPanelClosureError("run config TRAIN worlds drifted")
    if config.validation_worlds != VALIDATION_WORLDS:
        raise FrozenPanelClosureError("run config VALIDATION worlds drifted")
    if config.initialization_lineages != INITIALIZATION_LINEAGES:
        raise FrozenPanelClosureError("run config initialization mapping drifted")
    if config.output_unit_mode != panel_builder.EXPECTED_OUTPUT_UNIT_MODE:
        raise FrozenPanelClosureError("run config output unit drifted")

    adapter_rows = manifest.get("adapter_configs")
    if not isinstance(adapter_rows, list) or len(adapter_rows) != 21:
        raise FrozenPanelClosureError("adapter rectangle is not exactly 21")
    identities: set[tuple[str, int, int]] = set()
    for row in adapter_rows:
        if not isinstance(row, Mapping):
            raise FrozenPanelClosureError("adapter manifest row is malformed")
        path = Path(str(row.get("path"))).absolute()
        if _sha256(path) != row.get("config_sha256"):
            raise FrozenPanelClosureError(f"adapter config hash mismatch: {path}")
        identities.add((str(row.get("split")), int(row.get("world_seed")), int(row.get("lineage"))))
    expected_identities = {
        (split, world, lineage)
        for split, worlds in (("TRAIN", TRAIN_WORLDS), ("VALIDATION", VALIDATION_WORLDS))
        for world in worlds
        for lineage in LINEAGES
    }
    if identities != expected_identities:
        raise FrozenPanelClosureError("adapter rectangle identities drifted")

    return {
        "status": "V019_FROZEN_PANEL_CLOSURE_VERIFIED",
        "plan_sha256": plan_sha256,
        "learner_contract_sha256": validated.learner_contract_sha256,
        "code_manifest_file_sha256": validated.code_manifest_sha256,
        "panel_manifest_file_sha256": _sha256(manifest_path),
        "panel_manifest_body_sha256": computed_manifest_sha256,
        "learner_run_plan_sha256": _sha256(run_plan_path),
        "learner_run_config_sha256": _sha256(run_config_path),
        "adapter_config_count": len(adapter_rows),
        "output_unit_mode": config.output_unit_mode,
        "test_split_opened": False,
        "episode_training": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--panel-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(plan_path=args.plan, panel_root=args.panel_root)
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))
    print(_canonical_bytes(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
