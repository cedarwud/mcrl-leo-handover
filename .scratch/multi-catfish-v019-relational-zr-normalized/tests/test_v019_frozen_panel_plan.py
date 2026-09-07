"""Pure checks for the frozen V0.19 fresh-world panel-plan constants."""

from __future__ import annotations

from argparse import Namespace
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

import build_frozen_panel_plan_v019 as plan  # noqa: E402
import relational_source_panel_config_builder_v019 as builder  # noqa: E402
import verify_frozen_panel_closure_v019 as verifier  # noqa: E402


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _fixture_args(tmp_path: Path) -> Namespace:
    contract = tmp_path / "contract.md"
    manifest = tmp_path / "code-manifest.sha256"
    contract.write_text("Status: `FROZEN_BEFORE_OUTCOME`\n", encoding="utf-8")
    manifest.write_text("synthetic manifest\n", encoding="utf-8")
    (tmp_path / "prereg.json").write_text("{}\n", encoding="utf-8")
    for name in ("q1", "q2", "tle"):
        (tmp_path / name).mkdir()
    return Namespace(
        contract=contract,
        code_manifest=manifest,
        q1_root=tmp_path / "q1",
        q2_root=tmp_path / "q2",
        prereg=tmp_path / "prereg.json",
        tle_root=tmp_path / "tle",
        output_root=tmp_path / "output",
    )


def test_fresh_plan_uses_declared_new_worlds_and_normalized_mode(
    tmp_path: Path,
) -> None:
    args = _fixture_args(tmp_path)

    payload = plan.build_payload(args)

    assert payload["train_worlds"] == [2026120701, 2026120702, 2026120703, 2026120704]
    assert payload["validation_worlds"] == [2026120705, 2026120706, 2026120707]
    assert [item["initialization_seed"] for item in payload["initialization_lineages"]] == [
        2026120711,
        2026120712,
        2026120713,
    ]
    assert [item["schedule_seed"] for item in payload["initialization_lineages"]] == [
        2026120721,
        2026120722,
        2026120723,
    ]
    assert payload["output_unit_mode"] == builder.EXPECTED_OUTPUT_UNIT_MODE
    assert not set(payload["train_worlds"] + payload["validation_worlds"]) & builder.FORBIDDEN_PRIOR_WORLDS


def test_generated_panel_closure_binds_exact_plan_and_config(tmp_path: Path) -> None:
    args = _fixture_args(tmp_path)
    payload = plan.build_payload(args)
    plan_path = tmp_path / "panel-plan.json"
    plan_path.write_bytes(_canonical(payload))
    plan_sha256 = hashlib.sha256(plan_path.read_bytes()).hexdigest()

    builder.write_panel(plan_path, expected_sha256=plan_sha256)
    result = verifier.verify(plan_path=plan_path, panel_root=args.output_root)

    assert result["status"] == "V019_FROZEN_PANEL_CLOSURE_VERIFIED"
    assert result["adapter_config_count"] == 21
    assert result["output_unit_mode"] == builder.EXPECTED_OUTPUT_UNIT_MODE


def test_panel_closure_rejects_a_different_fresh_identity(tmp_path: Path) -> None:
    args = _fixture_args(tmp_path)
    payload = plan.build_payload(args)
    payload["validation_worlds"][-1] = 2026120799
    payload["field_root_digest_by_world"][-1]["world_seed"] = 2026120799
    plan_path = tmp_path / "panel-plan.json"
    plan_path.write_bytes(_canonical(payload))

    with pytest.raises(verifier.FrozenPanelClosureError, match="VALIDATION worlds"):
        verifier.verify(plan_path=plan_path, panel_root=args.output_root)
