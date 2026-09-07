"""Unit checks for the V0.22 topology selector and adoption classifier."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys

import numpy as np


RUNNER = Path(__file__).with_name("run_v022_coalition_residual_probe.py")
SPEC = importlib.util.spec_from_file_location("v022_probe_test_target", RUNNER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

PREFLIGHT = Path(__file__).with_name("preflight_v022_coalition_residual.py")
PREFLIGHT_SPEC = importlib.util.spec_from_file_location(
    "v022_preflight_test_target", PREFLIGHT
)
assert PREFLIGHT_SPEC is not None and PREFLIGHT_SPEC.loader is not None
PREFLIGHT_MODULE = importlib.util.module_from_spec(PREFLIGHT_SPEC)
sys.modules[PREFLIGHT_SPEC.name] = PREFLIGHT_MODULE
PREFLIGHT_SPEC.loader.exec_module(PREFLIGHT_MODULE)


@dataclass
class _Table:
    norad_ids: np.ndarray
    cell_ids: np.ndarray


@dataclass
class _Candidates:
    slot_tables: tuple[_Table, ...]


@dataclass
class _Observation:
    candidates: _Candidates


def _table(reference: tuple[int, int], destination: tuple[int, int]) -> _Table:
    norads = np.full(MODULE.NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(MODULE.NUM_ACTIONS, -1, dtype=np.int64)
    norads[0], cells[0] = reference
    norads[1], cells[1] = destination
    return _Table(norads, cells)


def test_topology_proposal_uses_reference_occupancy_and_fixed_base_rank() -> None:
    source = (10, 1)
    destination = (20, 2)
    observation = _Observation(
        _Candidates(
            (
                _table(source, destination),
                _table(source, destination),
                _table(destination, (30, 3)),
            )
        )
    )
    legal = np.zeros((3, MODULE.NUM_ACTIONS), dtype=np.bool_)
    legal[:, 0] = True
    legal[:2, 1] = True
    opening = np.array(legal, copy=True)
    base = np.zeros_like(legal, dtype=np.float64)
    base[0, 1] = 2.0
    base[1, 1] = 3.0
    reference = np.zeros(3, dtype=np.int64)

    proposal = MODULE._topology_proposal(
        observation,
        reference_actions=reference,
        legal_mask=legal,
        opening_feasible=opening,
        base_surface=base,
    )

    assert proposal is not None
    assert proposal["source_key"] == [10, 1]
    assert proposal["coalition_user_ids"] == [0, 1]
    assert proposal["proposed_actions"] == [1, 1]
    assert proposal["proposed_keys"] == [[20, 2], [20, 2]]


def test_topology_proposal_rejects_unoccupied_destination() -> None:
    source = (10, 1)
    destination = (20, 2)
    observation = _Observation(
        _Candidates((_table(source, destination), _table(source, destination)))
    )
    legal = np.zeros((2, MODULE.NUM_ACTIONS), dtype=np.bool_)
    legal[:, :2] = True
    opening = np.array(legal, copy=True)
    base = np.zeros_like(legal, dtype=np.float64)

    assert (
        MODULE._topology_proposal(
            observation,
            reference_actions=np.zeros(2, dtype=np.int64),
            legal_mask=legal,
            opening_feasible=opening,
            base_surface=base,
        )
        is None
    )


def test_adoption_classifies_only_literal_profiles() -> None:
    reference = np.asarray([0, 0, 0], dtype=np.int64)
    members = np.asarray([0, 1], dtype=np.int64)
    proposed = np.asarray([1, 2], dtype=np.int64)

    assert MODULE._adoption(np.asarray([1, 2, 0]), reference, members, proposed) == "11"
    assert MODULE._adoption(np.asarray([1, 0, 0]), reference, members, proposed) == "10"
    assert MODULE._adoption(np.asarray([0, 2, 0]), reference, members, proposed) == "01"
    assert MODULE._adoption(reference, reference, members, proposed) == "00"
    assert (
        MODULE._adoption(np.asarray([1, 2, 1]), reference, members, proposed)
        == "OTHER_PROFILE"
    )


def test_topology_input_receipt_preserves_outcome_blind_recompute_inputs() -> None:
    source = (10, 1)
    destination = (20, 2)
    observation = _Observation(
        _Candidates((_table(source, destination), _table(source, destination)))
    )
    legal = np.zeros((2, MODULE.NUM_ACTIONS), dtype=np.bool_)
    legal[:, :2] = True
    opening = np.array(legal, copy=True)
    base = np.zeros_like(legal, dtype=np.float64)
    reference = np.zeros(2, dtype=np.int64)

    receipt = MODULE._topology_input_receipt(
        observation,
        reference_actions=reference,
        legal_mask=legal,
        opening_feasible=opening,
        base_surface=base,
    )

    assert receipt["reference_actions"] == [0, 0]
    assert receipt["legal_mask"][0][0] is True
    assert receipt["opening_feasible"] == receipt["legal_mask"]
    assert receipt["candidate_physical_keys"][0][0] == [10, 1]
    assert receipt["candidate_physical_keys"][1][1] == [20, 2]
    assert len(receipt["base_surface_sha256"]) == 64


def test_no_case_scan_requires_all_declared_worlds_and_steps() -> None:
    rows = [
        {"world": world, "step": step}
        for world in MODULE.WORLDS
        for step in range(MODULE.STEPS_PER_EPISODE)
    ]
    MODULE._assert_complete_no_case_scan(rows)

    with np.testing.assert_raises(MODULE.V022CoalitionProbeError):
        MODULE._assert_complete_no_case_scan(rows[:-1])

    duplicate = list(rows)
    duplicate[-1] = {"world": MODULE.WORLDS[-1], "step": MODULE.STEPS_PER_EPISODE - 2}
    with np.testing.assert_raises(MODULE.V022CoalitionProbeError):
        MODULE._assert_complete_no_case_scan(duplicate)


def test_external_manifest_preflight_authenticates_source_and_model_receipts() -> None:
    receipt = PREFLIGHT_MODULE.validate_manifest(
        PREFLIGHT.with_name("PREFLIGHT-MANIFEST.json"),
        manifest_digest_path=PREFLIGHT.with_name("PREFLIGHT-MANIFEST.sha256"),
        repo=MODULE.REPO,
        prereg_path=MODULE.REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json",
    )

    assert receipt["status"] == "PASS"
    assert receipt["manifest_binding_count"] >= 15
    assert receipt["configuration"]["lineage"] == 2026092101
    assert receipt["configuration"]["tle_file_set_sha256"]
