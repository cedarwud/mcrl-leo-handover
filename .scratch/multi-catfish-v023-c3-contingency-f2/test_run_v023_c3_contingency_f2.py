"""Unit-scale F2 tests; no TLE archive or simulator is opened."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.link_budget import fixed_power_w, pa_efficiency, supply_power_w, system_power_w

import build_f2_preflight_manifest as preflight
import run_v023_c3_contingency_f2 as f2


def _profile(
    *, rates: list[float], cells: list[int], beam_cells: list[int], powers: list[float]
) -> f2.f1.PhysicalProfile:
    served = np.asarray(cells, dtype=np.int64) >= 0
    satellites = np.where(served, 10, -1).astype(np.int64)
    beam_power = np.asarray(powers, dtype=np.float64)
    supply = supply_power_w(beam_power, pa_efficiency(beam_power))
    counts = np.asarray([len(beam_cells)], dtype=np.float64)
    return f2.f1.PhysicalProfile(
        link_rate_bps=np.asarray(rates, dtype=np.float64),
        served=served,
        serving_satellite=satellites,
        serving_cell=np.asarray(cells, dtype=np.int64),
        active_beam_satellites=np.full(len(beam_cells), 10, dtype=np.int64),
        active_beam_cells=np.asarray(beam_cells, dtype=np.int64),
        beam_power_w=beam_power,
        fixed_power_w=fixed_power_w(counts),
        system_power_w=system_power_w(supply, counts),
        interval_s=2.0,
    )


def _f1_binding(survivors: tuple[str, ...] = ("D",)) -> dict[str, object]:
    return {
        "path": "/tmp/sealed-f1-result.json",
        "sha256": "c" * 64,
        "surviving_candidates": list(survivors),
    }


def _fixture_unit_tape(
    key: f2.UnitKey, *, d_rate: float = 250.0, survivors: tuple[str, ...] = ("D",)
) -> dict[str, object]:
    """Build ten synthetic steps through the imported F1 writer and F0 formula."""

    reference = _profile(
        rates=[100.0, 100.0, *([0.0] * 98)],
        cells=[1, 2, *([-1] * 98)],
        beam_cells=[1, 2],
        powers=[1.0, 1.0],
    )
    unilateral = _profile(
        rates=[100.0, 1000.0, *([0.0] * 98)],
        cells=[3, 2, *([-1] * 98)],
        beam_cells=[2, 3],
        powers=[1.0, 1.0],
    )
    d_deployment = _profile(
        rates=[d_rate, d_rate, *([0.0] * 98)],
        cells=[3, 2, *([-1] * 98)],
        beam_cells=[2, 3],
        powers=[1.0, 1.0],
    )
    link_power = np.asarray([1.0, 1.0, *([0.0] * 98)])
    masks = np.zeros((f2.USERS, f2.f1.NUM_ACTIONS), dtype=np.bool_)
    masks[0, :2] = True
    masks[1, 0] = True
    reference_actions = np.asarray(
        [0, 0, *([f2.f1.NO_OP_ACTION] * 98)], dtype=np.int64
    )
    key_table: list[list[list[int] | None]] = [
        [[10, 1], [10, 3], *([None] * 26)],
        [[10, 2], *([None] * 27)],
        *[[None] * f2.f1.NUM_ACTIONS for _ in range(98)],
    ]
    candidates = [
        {
            "focal_user": 0,
            "reference_action": 0,
            "candidate_action": 1,
            "reference_physical_key": [10, 1],
            "candidate_physical_key": [10, 3],
            "candidate_joint_actions": [1, 0, *([f2.f1.NO_OP_ACTION] * 98)],
            "profile": unilateral,
            "link_power_w": link_power,
        }
    ]
    q12 = np.full((f2.USERS, f2.f1.NUM_ACTIONS), -1000.0, dtype=np.float64)
    q12[0, 0] = 0.0
    q12[0, 1] = -1.0e-8
    q12[1, 0] = 0.0
    target = f2.f1.compute_c3_targets(
        reference,
        unilateral,
        focal_user=0,
        lambda_bits_per_j=f2.f1.LAMBDA_BITS_PER_J,
    )
    d = np.zeros_like(q12)
    ff = np.zeros_like(q12)
    d[0, 1] = target.d_bits
    ff[0, 1] = target.f_bits
    d_actions = f2.f1.masked_argmax_q12_plus_z(q12, d, masks)
    f_actions = f2.f1.masked_argmax_q12_plus_z(q12, ff, masks)
    assert d_actions[0] == 1
    deployments = {
        "D": d_actions if "D" in survivors else reference_actions,
        "F": f_actions if "F" in survivors else reference_actions,
    }
    profiles = {
        "D": (d_deployment, link_power) if "D" in survivors else (reference, link_power),
        "F": (reference, link_power),
    }
    steps = [
        f2.build_f2_step_payload(
            step_index=step,
            admitted_candidates=survivors,
            q12=q12,
            action_masks=masks,
            reference_actions=reference_actions,
            reference_profile=reference,
            reference_link_power_w=link_power,
            candidates=candidates,
            deployment_actions=deployments,
            deployment_profiles=profiles,
            state_sha256=f"{step + 1:064x}",
            action_physical_key_table=key_table,
        )
        for step in f2.CANONICAL_STEP_INDICES
    ]
    return f2.build_unit_tape_payload(
        key=key,
        steps=steps,
        q1_parameter_sha256="a" * 64,
        q2_parameter_sha256="b" * 64,
        preflight_manifest_sha256="d" * 64,
        f1_binding=_f1_binding(survivors),
    )


def _metrics(delta: float, *, service: float = 1.0) -> tuple[dict[str, object], dict[str, object]]:
    opportunities = 1_000_000
    base = {
        "total_bits": 100.0,
        "total_energy_j": 1.0,
        "ratio_of_sums_ee_bits_per_j": 100.0,
        "served_user_steps": opportunities,
        "service_opportunities": opportunities,
        "service_fraction": 1.0,
    }
    candidate = {
        "total_bits": 100.0 + delta,
        "total_energy_j": 1.0,
        "ratio_of_sums_ee_bits_per_j": 100.0 + delta,
        "served_user_steps": round(service * opportunities),
        "service_opportunities": opportunities,
        "service_fraction": service,
    }
    return base, candidate


def _panel_receipts(
    deltas: list[list[float]], *, candidates: tuple[str, ...] = ("D",), service: float = 1.0
) -> list[dict[str, object]]:
    rows = []
    for wi, world in enumerate(f2.WORLDS):
        for li, lineage in enumerate(f2.LINEAGES):
            base, candidate = _metrics(deltas[wi][li], service=service)
            metrics: dict[str, object] = {"BASE": base}
            rules: dict[str, object] = {}
            for name in candidates:
                metrics[name] = copy.deepcopy(candidate)
                rules[name] = {"integrity": True}
            rows.append(
                {
                    "unit": f2.UnitKey(world, lineage).as_dict(),
                    "metrics": metrics,
                    "unit_rules": rules,
                    "mechanics_integrity": True,
                    "provenance_integrity": True,
                }
            )
    return rows


BOUNDARY_PASS = [
    [3.0, 3.0, -1.0],
    [3.0, 3.0, -1.0],
    [3.0, 3.0, -1.0],
    [-1.0, -1.0, -10.0],
]


def test_unit_and_merge_are_deterministic_on_synthetic_tapes(tmp_path: Path) -> None:
    terminals = []
    for suffix in ("a", "b"):
        output = tmp_path / suffix
        receipts = []
        digests = []
        for key in f2.ALL_UNITS:
            tape = _fixture_unit_tape(key)
            _tape, _manifest, receipt_path = f2.write_unit_bundle(
                output, key=key, tape=tape
            )
            receipt, digest = f2.authenticate_unit_bundle(
                output,
                key=key,
                preflight_sha256="d" * 64,
                f1_binding=_f1_binding(),
            )
            assert receipt_path.read_bytes() == f2.canonical_bytes(receipt) + b"\n"
            receipts.append(receipt)
            digests.append((key, digest))
        terminals.append(
            f2.build_terminal_receipt(
                receipts=receipts,
                receipt_digests=digests,
                preflight_sha256="d" * 64,
                f1_binding=_f1_binding(),
            )
        )
    assert f2.canonical_bytes(terminals[0]) == f2.canonical_bytes(terminals[1])
    assert terminals[0]["outcome"] == "F2_PASS_D"


def test_pass_rule_accepts_exact_three_world_two_lineage_boundary() -> None:
    rule = f2.evaluate_panel_candidate(_panel_receipts(BOUNDARY_PASS), candidate="D")
    assert rule["world_positive_count"] == 3
    assert rule["lineage_positive_count"] == 2
    assert rule["pooled_ee_strictly_above_base"] is True
    assert rule["passes"] is True


@pytest.mark.parametrize(
    ("deltas", "worlds", "lineages"),
    [
        (
            [[5.0, 5.0, 1.0], [5.0, 5.0, 1.0], [-1.0, -1.0, -1.0], [-1.0, -1.0, -10.0]],
            2,
            2,
        ),
        (
            [[-1.0, -1.0, 5.0], [-1.0, -1.0, 5.0], [-1.0, -1.0, 5.0], [-1.0, -1.0, -1.0]],
            3,
            1,
        ),
    ],
)
def test_pass_rule_rejects_below_direction_boundaries(
    deltas: list[list[float]], worlds: int, lineages: int
) -> None:
    rule = f2.evaluate_panel_candidate(_panel_receipts(deltas), candidate="D")
    assert rule["pooled_ee_strictly_above_base"] is True
    assert rule["world_positive_count"] == worlds
    assert rule["lineage_positive_count"] == lineages
    assert rule["passes"] is False


@pytest.mark.parametrize(("service", "expected"), [(0.999, True), (0.998999, False)])
def test_service_noninferiority_margin(service: float, expected: bool) -> None:
    rule = f2.evaluate_panel_candidate(
        _panel_receipts(BOUNDARY_PASS, service=service), candidate="D"
    )
    assert rule["service_noninferior"] is expected
    assert rule["passes"] is expected


def test_d_before_f_and_f_only_after_d_failure() -> None:
    both_pass = {
        "D": {"integrity": True, "passes": True},
        "F": {"integrity": True, "passes": True},
    }
    assert f2.adjudicate_panel(both_pass) == "F2_PASS_D"
    assert (
        f2.adjudicate_panel(
            {"D": {"integrity": True, "passes": False}, "F": {"integrity": True, "passes": True}}
        )
        == "F2_PASS_F"
    )
    assert f2.adjudicate_panel({"F": {"integrity": True, "passes": True}}) == "F2_PASS_F"
    assert f2.adjudicate_panel({"D": {"integrity": True, "passes": False}}) == "F2_NO_SUPPORT"


def test_refuses_without_f1_survivor() -> None:
    with pytest.raises(f2.F2NotAdmitted, match="F2_NOT_ADMITTED"):
        f2.f1_result_binding({"f1_result": _f1_binding(())})


def test_integrity_failure_propagates_globally() -> None:
    receipts = _panel_receipts(BOUNDARY_PASS)
    receipts[7]["unit_rules"]["D"]["integrity"] = False
    rule = f2.evaluate_panel_candidate(receipts, candidate="D")
    assert rule["integrity"] is False
    assert rule["passes"] is False
    assert f2.adjudicate_panel({"D": rule}) == "INVALID_RUN"


def test_merge_missing_unit_emits_write_once_invalid_run(tmp_path: Path) -> None:
    terminal, skipped = f2.execute_merge(
        output=tmp_path,
        preflight_sha256="d" * 64,
        authority={"f1_result": _f1_binding()},
    )
    payload = f2._load_json(terminal, field="terminal fixture")
    assert skipped is False
    assert payload["outcome"] == "INVALID_RUN"
    assert payload["status"] == "INVALID_RUN"
    assert payload["unit_receipts"] is None
    assert terminal.stat().st_mode & 0o222 == 0
    repeated, skipped = f2.execute_merge(
        output=tmp_path,
        preflight_sha256="d" * 64,
        authority={"f1_result": _f1_binding()},
    )
    assert repeated == terminal
    assert skipped is True


@pytest.mark.parametrize(
    "value",
    ["2026121720:2026092101", "2026121721:2026092104", "2026121721:2026092101:10"],
)
def test_rejects_other_world_or_lineage(value: str) -> None:
    with pytest.raises(f2.F2Error):
        f2.UnitKey.parse(value)


def test_rejects_any_other_step_count() -> None:
    key = f2.ALL_UNITS[0]
    tape = _fixture_unit_tape(key)
    tape["steps"].pop()
    with pytest.raises(f2.F2Error, match="steps 0..9"):
        f2.verify_unit_tape(tape, key=key)


def test_resume_skips_authenticated_complete_unit(tmp_path: Path) -> None:
    key = f2.ALL_UNITS[0]
    tape = _fixture_unit_tape(key)
    f2.write_unit_bundle(tmp_path, key=key, tape=tape)

    def must_not_run(**_kwargs: object) -> dict[str, object]:
        raise AssertionError("complete unit was recomputed")

    receipt, skipped = f2.execute_unit(
        key=key,
        output=tmp_path,
        tle_root=tmp_path / "unused-tle",
        preflight_sha256="d" * 64,
        authority={"f1_result": _f1_binding()},
        generator=must_not_run,
    )
    assert skipped is True
    assert receipt.name == f2.DEFAULT_UNIT_RECEIPT_NAME


def test_f1_result_survivor_set_is_authenticated(tmp_path: Path) -> None:
    unit_tape = _fixture_unit_tape(f2.ALL_UNITS[0])
    f1_tape = f2.f1.build_tape_payload(
        unit_tape["steps"][:2],
        q1_parameter_sha256="a" * 64,
        q2_parameter_sha256="b" * 64,
        preflight_manifest_sha256="c" * 64,
    )
    receipt = f2.f1.screen_tape(
        f1_tape, tape_sha256=f2.f1.canonical_sha256(f1_tape)
    )
    path = tmp_path / "f1-result.json"
    f2._write_once(path, receipt)
    digest = f2.file_sha256(path)
    assert f2._validate_f1_result(
        path, expected_sha256=digest, declared_survivors=("D",)
    ) == receipt
    with pytest.raises(f2.F2Error, match="survivor set"):
        f2._validate_f1_result(
            path, expected_sha256=digest, declared_survivors=("D", "F")
        )


def test_preflight_builder_and_dry_run_validate_all_bindings(tmp_path: Path) -> None:
    manifest, sidecar, digest = preflight.write_manifest(tmp_path / "preflight.json")
    payload, observed = f2.validate_preflight_manifest(manifest)
    assert observed == digest
    assert sidecar.read_text(encoding="ascii").split() == [digest, manifest.name]
    assert payload["bindings"]["unit_count"] == 12
    assert len(payload["lineage_authorities"]) == 3
    assert payload["formula_digests"]["reused_f1_formula_digests"] == f2.f1.formula_digests()
    args = argparse.Namespace(
        dry_run=True,
        preflight_manifest=manifest,
        launch_authority=None,
        tle_root=None,
        output=None,
        unit=None,
        merge=False,
    )
    assert f2.run(args) == {"preflight": manifest}
