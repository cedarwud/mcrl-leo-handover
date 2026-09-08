"""Unit-fixture tests for the E1 catalog, tape boundaries, and merge."""

from __future__ import annotations

import argparse
from pathlib import Path
import stat
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.link_budget import fixed_power_w, pa_efficiency, supply_power_w, system_power_w

import build_e1_preflight_manifest as preflight
import run_v023_c3_existence_e1 as e1


def _profile(keys: list[tuple[int, int]], *, rate: float = 100.0) -> e1.f1.PhysicalProfile:
    users = len(keys)
    unique = sorted(set(keys))
    powers = np.ones(len(unique), dtype=np.float64)
    supply = supply_power_w(powers, pa_efficiency(powers))
    satellites = sorted({key[0] for key in unique})
    counts = np.asarray([sum(key[0] == satellite for key in unique) for satellite in satellites], dtype=np.float64)
    return e1.f1.PhysicalProfile(
        link_rate_bps=np.full(users, rate, dtype=np.float64),
        served=np.ones(users, dtype=np.bool_),
        serving_satellite=np.asarray([key[0] for key in keys], dtype=np.int64),
        serving_cell=np.asarray([key[1] for key in keys], dtype=np.int64),
        active_beam_satellites=np.asarray([key[0] for key in unique], dtype=np.int64),
        active_beam_cells=np.asarray([key[1] for key in unique], dtype=np.int64),
        beam_power_w=powers,
        fixed_power_w=fixed_power_w(counts),
        system_power_w=system_power_w(supply, counts),
        interval_s=2.0,
    )


class _Table:
    def __init__(self, entries: dict[int, tuple[int, int]]) -> None:
        self.mask = np.zeros(e1.f1.NUM_ACTIONS, dtype=np.bool_)
        self._entries = entries
        for action in entries:
            self.mask[action] = True

    def association(self, action: int) -> e1.f1.Association:
        key = self._entries[action]
        return e1.f1.Association(*key)


class _Evaluator:
    def evaluate_actions(self, actions: np.ndarray, _rng: np.random.Generator) -> object:
        if int(actions[0]) == 1 and int(actions[1]) == 1:
            keys = [(20, 3), (20, 3), *([(10, 2)] * 98)]
        else:
            raise AssertionError("catalog evaluated a non-common or partial joint action")
        profile = _profile(keys, rate=120.0)
        return SimpleNamespace(
            resolution=SimpleNamespace(
                served=profile.served,
                serving_satellite=profile.serving_satellite,
                serving_cell=profile.serving_cell,
            ),
            radiating=SimpleNamespace(
                norad_ids=profile.active_beam_satellites,
                cell_ids=profile.active_beam_cells,
                power_w=profile.beam_power_w,
            ),
            link_power_w=np.ones(profile.users, dtype=np.float64),
            link_rate_bps=profile.link_rate_bps,
            fixed_power_w=profile.fixed_power_w,
            system_power_w=profile.system_power_w,
        )


def test_joint_catalog_uses_only_common_destinations_and_checks_f0() -> None:
    tables = [
        _Table({0: (10, 1), 1: (20, 3), 2: (30, 4)}),
        _Table({0: (10, 1), 1: (20, 3)}),
        *[_Table({0: (10, 2)}) for _ in range(98)],
    ]
    observation = SimpleNamespace(candidates=SimpleNamespace(slot_tables=tuple(tables)))
    base = _profile([(10, 1), (10, 1), *([(10, 2)] * 98)])
    anchor = e1.JointWitnessAnchor(
        observation=observation,
        reference_actions=np.zeros(100, dtype=np.int64),
        reference_profile=base,
        step_env=_Evaluator(),
        rng=np.random.default_rng(7),
        interval_s=2.0,
    )
    rows = e1.build_joint_witness_catalog(anchor)
    assert len(rows) == 1
    assert rows[0]["origin_physical_key"] == [10, 1]
    assert rows[0]["destination_physical_key"] == [20, 3]
    assert rows[0]["origin_users"] == [0, 1]
    assert rows[0]["f0_conservation"]["verified"] is True
    assert rows[0]["metrics"]["served"] == 100


def test_world_derivation_and_unit_refusals() -> None:
    assert e1.WORLDS == (
        861587764845384088,
        3943897440191533562,
        5747196377242098234,
        4004348767321774260,
    )
    assert len(set(e1.WORLDS).intersection(e1.DISALLOWED_HISTORICAL_WORLDS)) == 0
    with pytest.raises(e1.E1Error, match="world"):
        e1.UnitKey(1, e1.LINEAGES[0]).verify()
    with pytest.raises(e1.E1Error, match="lineage"):
        e1.UnitKey(e1.WORLDS[0], 1).verify()
    with pytest.raises(e1.E1Error, match="unit"):
        e1.UnitKey.parse(f"{e1.WORLDS[0]}")


def test_refuses_other_step_indices() -> None:
    base = _profile([(10, 1)] * 100)
    masks = np.zeros((100, e1.f1.NUM_ACTIONS), dtype=np.bool_)
    masks[:, 0] = True
    with pytest.raises(e1.E1Error, match="step index"):
        e1.build_step_payload(
            step_index=10,
            reference_actions=np.zeros(100, dtype=np.int64),
            action_masks=masks,
            reference_profile=base,
            reference_link_power_w=np.ones(100),
            unilateral_candidates=[],
            joint_catalog=[],
            state_sha256="a" * 64,
            action_physical_key_table=[[[10, 1], *([None] * 27)] for _ in range(100)],
        )


def test_write_once(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    digest = e1._write_once(path, {"status": "COMPLETE"})
    assert e1.file_sha256(path) == digest
    assert stat.S_IMODE(path.stat().st_mode) == 0o444
    with pytest.raises(e1.E1Error, match="overwrite"):
        e1._write_once(path, {"status": "COMPLETE"})


def _synthetic_tapes() -> tuple[list[dict[str, object]], list[dict[str, object]], list[tuple[e1.UnitKey, str]]]:
    base = _profile([(10, 1)] * 100, rate=100.0)
    better = _profile([(10, 1)] * 100, rate=110.0)
    base_payload = e1.f1.profile_to_payload(base, link_power_w=np.ones(100))
    better_payload = e1.f1.profile_to_payload(better, link_power_w=np.ones(100))
    receipts = []
    tapes = []
    digests = []
    for index, key in enumerate(e1.ALL_UNITS):
        steps = []
        for step in e1.CANONICAL_STEP_INDICES:
            steps.append({
                "step_index": step,
                "reference_profile": base_payload,
                "unilateral_candidates": [{"profile_id": "U:0:1", "profile": better_payload}],
                "joint_witness_catalog": [{"profile_id": "J:10:1->20:2", "profile": better_payload}],
            })
        tapes.append({"unit": key.as_dict(), "steps": steps})
        receipts.append({"unit": key.as_dict(), "integrity": True})
        digests.append((key, f"{index + 1:064x}"))
    return receipts, tapes, digests


def test_merge_solver_is_bitwise_deterministic() -> None:
    receipts, tapes, digests = _synthetic_tapes()
    first = e1.build_terminal_receipt(
        receipts=receipts, receipt_digests=digests, tapes=tapes,
        preflight_sha256="f" * 64,
    )
    second = e1.build_terminal_receipt(
        receipts=list(reversed(list(reversed(receipts)))),
        receipt_digests=digests,
        tapes=list(reversed(list(reversed(tapes)))),
        preflight_sha256="f" * 64,
    )
    assert e1.canonical_bytes(first) == e1.canonical_bytes(second)
    assert first["outcome"] == {
        "unilateral": "E1_UNILATERAL_HEADROOM",
        "joint": "E1_JOINT_HEADROOM",
    }


def test_missing_units_emit_write_once_invalid_run(tmp_path: Path) -> None:
    path, skipped, valid = e1.execute_merge(output=tmp_path, preflight_sha256="f" * 64)
    assert skipped is False and valid is False
    receipt = e1._load_json(path, field="terminal")
    assert receipt["status"] == receipt["outcome"] == "INVALID_RUN"
    repeated, skipped, valid = e1.execute_merge(output=tmp_path, preflight_sha256="f" * 64)
    assert repeated == path and skipped is True and valid is False


def test_preflight_builder_and_dry_run(tmp_path: Path) -> None:
    manifest, sidecar, digest = preflight.write_manifest(tmp_path / "preflight.json")
    payload, observed = e1.validate_preflight_manifest(manifest)
    assert observed == digest
    assert sidecar.read_text(encoding="ascii").split() == [digest, manifest.name]
    args = argparse.Namespace(
        dry_run=True,
        preflight_manifest=manifest,
        launch_authority=None,
        unit=None,
        merge=False,
        tle_root=None,
        output=None,
    )
    result = e1.run(args)
    assert result == {"preflight": manifest, "worlds": e1.WORLDS}
    assert payload["claim_ceiling"] == e1.CLAIM_CEILING

