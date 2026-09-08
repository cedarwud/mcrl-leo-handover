"""Boundary tests for the E1 catalog, tape, publication, and lifecycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import stat
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.link_budget import fixed_power_w, pa_efficiency, supply_power_w, system_power_w

import build_e1_preflight_manifest as preflight
import run_v023_c3_existence_e1 as e1


def _profile(
    keys: list[tuple[int, int] | None], *, rate: float = 100.0,
    interval: float = e1.INTERVAL_S,
) -> e1.f1.PhysicalProfile:
    users = len(keys)
    served = np.asarray([key is not None for key in keys], dtype=np.bool_)
    identities = [(-1, -1) if key is None else key for key in keys]
    unique = sorted({key for key in keys if key is not None})
    powers = np.ones(len(unique), dtype=np.float64)
    supply = supply_power_w(powers, pa_efficiency(powers))
    satellites = sorted({key[0] for key in unique})
    counts = np.asarray(
        [sum(key is not None and key[0] == satellite for key in unique) for satellite in satellites],
        dtype=np.float64,
    )
    return e1.f1.PhysicalProfile(
        link_rate_bps=np.where(served, rate, 0.0).astype(np.float64),
        served=served,
        serving_satellite=np.asarray([key[0] for key in identities], dtype=np.int64),
        serving_cell=np.asarray([key[1] for key in identities], dtype=np.int64),
        active_beam_satellites=np.asarray([key[0] for key in unique], dtype=np.int64),
        active_beam_cells=np.asarray([key[1] for key in unique], dtype=np.int64),
        beam_power_w=powers,
        fixed_power_w=fixed_power_w(counts),
        system_power_w=system_power_w(supply, counts),
        interval_s=interval,
    )


class _Table:
    def __init__(self, entries: dict[int, tuple[int, int]]) -> None:
        self.mask = np.zeros(e1.f1.NUM_ACTIONS, dtype=np.bool_)
        self._entries = entries
        for action in entries:
            self.mask[action] = True

    def association(self, action: int) -> e1.f1.Association:
        return e1.f1.Association(*self._entries[action])


class _Evaluator:
    def __init__(self, result: e1.f1.PhysicalProfile) -> None:
        self.driver = SimpleNamespace(step_index=0)
        self.result = result
        self.calls: list[np.ndarray] = []

    def evaluate_actions(self, actions: np.ndarray, _rng: np.random.Generator) -> object:
        self.calls.append(np.asarray(actions).copy())
        profile = self.result
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
            link_power_w=np.where(profile.served, 1.0, 0.0),
            link_rate_bps=profile.link_rate_bps,
            fixed_power_w=profile.fixed_power_w,
            system_power_w=profile.system_power_w,
        )


def _catalog_anchor(
    tables: list[_Table], base: e1.f1.PhysicalProfile,
    result: e1.f1.PhysicalProfile | None = None,
) -> tuple[e1.JointWitnessAnchor, _Evaluator]:
    evaluator = _Evaluator(base if result is None else result)
    anchor = e1.JointWitnessAnchor(
        observation=SimpleNamespace(candidates=SimpleNamespace(slot_tables=tuple(tables))),
        reference_actions=np.zeros(e1.USERS, dtype=np.int64),
        reference_profile=base,
        reference_link_power_w=np.where(base.served, 1.0, 0.0),
        step_env=evaluator,
        rng=np.random.default_rng(7),
        interval_s=e1.INTERVAL_S,
    )
    return anchor, evaluator


def test_joint_catalog_common_destination_and_unsuccessful_realisation_retained() -> None:
    tables = [
        _Table({0: (10, 1), 1: (20, 3), 2: (30, 4)}),
        _Table({0: (10, 1), 1: (20, 3)}),
        *[_Table({0: (10, 2)}) for _ in range(98)],
    ]
    base = _profile([(10, 1), (10, 1), *([(10, 2)] * 98)])
    anchor, _ = _catalog_anchor(tables, base, result=base)
    rows = e1.build_joint_witness_catalog(anchor)
    assert len(rows) == 1
    assert rows[0]["origin_physical_key"] == [10, 1]
    assert rows[0]["destination_physical_key"] == [20, 3]
    assert rows[0]["origin_users"] == [0, 1]
    assert rows[0]["alias_of_profile_id"] == e1.BASE_PROFILE_ID
    assert rows[0]["f0_conservation"]["verified"] is True


def test_joint_catalog_singleton_unserved_exclusion_and_empty_catalog() -> None:
    base = _profile([(10, 1), None, *([(10, 2)] * 98)])
    tables = [
        _Table({0: (10, 1), 1: (20, 3)}),
        _Table({0: (99, 9), 1: (20, 3)}),
        *[_Table({0: (10, 2)}) for _ in range(98)],
    ]
    anchor, _ = _catalog_anchor(tables, base)
    rows = e1.build_joint_witness_catalog(anchor)
    assert len(rows) == 1
    assert rows[0]["origin_users"] == [0]
    assert all(1 not in row["origin_users"] for row in rows)

    empty_tables = [_Table({0: key or (99, 9)}) for key in [(10, 1), None, *([(10, 2)] * 98)]]
    empty_anchor, _ = _catalog_anchor(empty_tables, base)
    assert e1.build_joint_witness_catalog(empty_anchor) == ()


def test_joint_catalog_exact_aliases_are_recorded() -> None:
    base = _profile([(10, 1), *([(10, 2)] * 99)])
    tables = [
        _Table({0: (10, 1), 1: (20, 3), 2: (30, 4)}),
        *[_Table({0: (10, 2)}) for _ in range(99)],
    ]
    anchor, _ = _catalog_anchor(tables, base, result=base)
    rows = e1.build_joint_witness_catalog(anchor)
    assert len(rows) == 2
    assert [row["destination_physical_key"] for row in rows] == [[20, 3], [30, 4]]
    assert [row["alias_of_profile_id"] for row in rows] == ["BASE", "BASE"]


def _base_step(*, step_index: int = 0, q12: np.ndarray | None = None) -> dict[str, object]:
    base = _profile([(10, 1)] * e1.USERS)
    masks = np.zeros((e1.USERS, e1.f1.NUM_ACTIONS), dtype=np.bool_)
    masks[:, 0] = True
    surface = np.zeros((e1.USERS, e1.f1.NUM_ACTIONS), dtype=np.float32) if q12 is None else q12
    return e1.build_step_payload(
        step_index=step_index, q12=surface,
        reference_actions=np.zeros(e1.USERS, dtype=np.int64), action_masks=masks,
        reference_profile=base, reference_link_power_w=np.ones(e1.USERS),
        unilateral_candidates=[], joint_catalog=[], state_sha256="a" * 64,
        action_physical_key_table=[[[10, 1], *([None] * 27)] for _ in range(e1.USERS)],
    )


def _joint_step() -> dict[str, object]:
    base = _profile([(10, 1)] * e1.USERS)
    joint = _profile([(20, 2)] * e1.USERS)
    masks = np.zeros((e1.USERS, e1.f1.NUM_ACTIONS), dtype=np.bool_)
    masks[:, :2] = True
    q12 = np.zeros((e1.USERS, e1.f1.NUM_ACTIONS), dtype=np.float32)
    q12[:, 0] = 1.0
    profile_payload = e1.f1.profile_to_payload(joint, link_power_w=np.ones(e1.USERS))
    row = {
        "profile_id": "J:10:1->20:2",
        "origin_physical_key": [10, 1],
        "destination_physical_key": [20, 2],
        "origin_users": list(range(e1.USERS)),
        "candidate_joint_actions": [1] * e1.USERS,
        "profile": joint,
        "link_power_w": np.ones(e1.USERS),
        "physical_profile_sha256": e1.canonical_sha256(profile_payload),
        "alias_of_profile_id": None,
        "metrics": e1._profile_metrics(joint),
        "f0_conservation": e1._conservation(joint),
    }
    unilateral = []
    for user in range(e1.USERS):
        actions = [0] * e1.USERS
        actions[user] = 1
        unilateral.append({
            "focal_user": user, "reference_action": 0, "candidate_action": 1,
            "reference_physical_key": [10, 1], "candidate_physical_key": [20, 2],
            "candidate_joint_actions": actions, "profile_id": f"U:{user}:1",
            "profile": joint, "link_power_w": np.ones(e1.USERS),
            "metrics": e1._profile_metrics(joint), "f0_conservation": e1._conservation(joint),
        })
    return e1.build_step_payload(
        step_index=0, q12=q12,
        reference_actions=np.zeros(e1.USERS, dtype=np.int64), action_masks=masks,
        reference_profile=base, reference_link_power_w=np.ones(e1.USERS),
        unilateral_candidates=unilateral, joint_catalog=[row], state_sha256="b" * 64,
        action_physical_key_table=[[[10, 1], [20, 2], *([None] * 26)] for _ in range(e1.USERS)],
    )


def test_q_surface_roundtrip_and_base_authentication() -> None:
    q12 = np.arange(e1.USERS * e1.f1.NUM_ACTIONS, dtype=np.float32).reshape(e1.USERS, e1.f1.NUM_ACTIONS)
    masks = np.zeros_like(q12, dtype=np.bool_)
    masks[:, 0] = True
    masks[:, 3] = True
    q12[:, 0] = q12[:, 3]
    base = _profile([(10, 1)] * e1.USERS)
    step = e1.build_step_payload(
        step_index=0, q12=q12, reference_actions=np.zeros(e1.USERS, dtype=np.int64),
        action_masks=masks, reference_profile=base, reference_link_power_w=np.ones(e1.USERS),
        unilateral_candidates=[], joint_catalog=[], state_sha256="c" * 64,
        action_physical_key_table=[[[10, 1], None, None, None, *([None] * 24)] for _ in range(e1.USERS)],
    )
    assert np.array_equal(e1._decode_q12_surface(step["q1_q2_float32"]), q12)
    assert e1.verify_step_payload(step)["base"].users == e1.USERS


def test_e1_validation_does_not_call_legacy_targets_or_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> object:
        pytest.fail("E1 called a forbidden F1 D/F or z/kappa entry point")

    monkeypatch.setattr(e1.f1, "target_surfaces_from_step", forbidden)
    monkeypatch.setattr(e1.f1, "masked_argmax_q12_plus_z", forbidden)
    assert e1.verify_step_payload(_base_step())["base"].users == e1.USERS


@pytest.mark.parametrize("mutation", ["missing", "shape", "dtype", "non-argmax"])
def test_q_surface_refusals(mutation: str) -> None:
    step = _base_step()
    if mutation == "missing":
        del step["q1_q2_float32"]
    elif mutation == "shape":
        step["q1_q2_float32"]["shape"] = [99, 28]
    elif mutation == "dtype":
        step["q1_q2_float32"]["dtype"] = "<f8"
    else:
        raw = e1._decode_q12_surface(step["q1_q2_float32"])
        raw[:, 1] = 1.0
        step["q1_q2_float32"] = e1._encode_q12_surface(raw)
        for row in step["action_masks"]:
            row[1] = True
    with pytest.raises(e1.E1Error, match=r"Q1\+Q2|BASE"):
        e1.verify_step_payload(step)


def test_joint_interval_mismatch_is_rejected() -> None:
    step = _joint_step()
    step["joint_witness_catalog"][0]["profile"]["interval_s"] = float(2.0).hex()
    with pytest.raises(e1.E1Error, match="interval"):
        e1.verify_step_payload(step)


def test_world_derivation_and_unit_refusals() -> None:
    assert e1.WORLDS == (
        861587764845384088, 3943897440191533562,
        5747196377242098234, 4004348767321774260,
    )
    assert not set(e1.WORLDS).intersection(e1.DISALLOWED_HISTORICAL_WORLDS)
    with pytest.raises(e1.E1Error, match="world"):
        e1.UnitKey(1, e1.LINEAGES[0]).verify()
    with pytest.raises(e1.E1Error, match="lineage"):
        e1.UnitKey(e1.WORLDS[0], 1).verify()


def test_refuses_other_step_indices() -> None:
    with pytest.raises(e1.E1Error, match="step index"):
        e1.build_step_payload(
            step_index=10, q12=np.zeros((e1.USERS, 28), dtype=np.float32),
            reference_actions=np.zeros(e1.USERS, dtype=np.int64),
            action_masks=np.zeros((e1.USERS, 28), dtype=np.bool_),
            reference_profile=_profile([(10, 1)] * e1.USERS),
            reference_link_power_w=np.ones(e1.USERS), unilateral_candidates=[],
            joint_catalog=[], state_sha256="a" * 64,
            action_physical_key_table=[[None] * 28 for _ in range(e1.USERS)],
        )


def test_write_once_reopens_hashes_and_sets_mode(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    digest = e1._write_once(path, {"status": "COMPLETE"})
    assert e1.file_sha256(path) == digest
    assert stat.S_IMODE(path.stat().st_mode) == 0o444
    with pytest.raises(e1.E1Error, match="overwrite"):
        e1._write_once(path, {"status": "COMPLETE"})


def _synthetic_tape(key: e1.UnitKey, preflight_sha: str) -> dict[str, object]:
    return e1.build_unit_tape_payload(
        key=key,
        steps=[_base_step(step_index=index) for index in e1.CANONICAL_STEP_INDICES],
        q1_parameter_sha256="1" * 64,
        q2_parameter_sha256="2" * 64, preflight_manifest_sha256=preflight_sha,
    )


def test_full_synthetic_publication_resume_and_merge(
    tmp_path: Path,
) -> None:
    preflight_sha = "f" * 64

    receipts = []
    for key in e1.ALL_UNITS:
        receipt, skipped, valid = e1.execute_unit(
            key=key, output=tmp_path, tle_root=e1.CANONICAL_TLE_ROOT,
            preflight_sha256=preflight_sha,
            generator=lambda **kwargs: _synthetic_tape(kwargs["key"], preflight_sha),
        )
        assert not skipped and valid
        assert stat.S_IMODE(receipt.stat().st_mode) == 0o444
        e1.authenticate_unit_bundle(tmp_path, key=key, preflight_sha256=preflight_sha)
        receipts.append(receipt)
    key = e1.ALL_UNITS[0]
    resumed, skipped, valid = e1.execute_unit(
        key=key, output=tmp_path, tle_root=e1.CANONICAL_TLE_ROOT,
        preflight_sha256=preflight_sha,
        generator=lambda **_kwargs: pytest.fail("complete unit was regenerated"),
    )
    assert resumed == receipts[0] and skipped and valid
    terminal, skipped, valid = e1.execute_merge(output=tmp_path, preflight_sha256=preflight_sha)
    assert not skipped and valid
    assert e1._load_json(terminal, field="terminal")["status"] == "COMPLETE"
    repeated, skipped, valid = e1.execute_merge(output=tmp_path, preflight_sha256=preflight_sha)
    assert repeated == terminal and skipped and valid
    tape = tmp_path / "units" / key.slug / e1.DEFAULT_TAPE_NAME
    tape.chmod(0o644)
    tape.write_text("{}\n", encoding="ascii")
    tape.chmod(0o444)
    invalidation, skipped, valid = e1.execute_merge(
        output=tmp_path, preflight_sha256=preflight_sha
    )
    assert not skipped and not valid
    assert invalidation.name == e1.DEFAULT_GLOBAL_INVALIDATION_NAME


def test_interrupted_acquisition_is_incomplete_and_resumable(
    tmp_path: Path,
) -> None:
    key = e1.ALL_UNITS[0]
    preflight_sha = "e" * 64

    def interrupted(**_kwargs: object) -> dict[str, object]:
        raise KeyboardInterrupt("fixture interruption")

    receipt, skipped, valid = e1.execute_unit(
        key=key, output=tmp_path, tle_root=e1.CANONICAL_TLE_ROOT,
        preflight_sha256=preflight_sha, generator=interrupted,
    )
    assert not skipped and not valid
    assert e1._load_json(receipt, field="incomplete")["status"] == "INCOMPLETE"
    assert not (tmp_path / "units" / key.slug).exists()
    completed, skipped, valid = e1.execute_unit(
        key=key, output=tmp_path, tle_root=e1.CANONICAL_TLE_ROOT,
        preflight_sha256=preflight_sha,
        generator=lambda **_kwargs: _synthetic_tape(key, preflight_sha),
    )
    assert not skipped and valid and completed.exists()


def test_exhausted_worker_budget_is_incomplete(
    tmp_path: Path,
) -> None:
    key = e1.ALL_UNITS[0]
    cap = 1.0
    e1._record_budget(tmp_path, cap, cap)
    receipt, skipped, valid = e1.execute_unit(
        key=key, output=tmp_path, tle_root=e1.CANONICAL_TLE_ROOT,
        preflight_sha256="4" * 64, budget_worker_seconds=cap,
        generator=lambda **_kwargs: pytest.fail("budgeted-out generator was invoked"),
    )
    assert not skipped and not valid
    assert e1._load_json(receipt, field="budget incomplete")["status"] == "INCOMPLETE"


def test_solver_resource_exhaustion_is_incomplete_not_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    preflight_sha = "3" * 64
    for key in e1.ALL_UNITS:
        e1.write_unit_bundle(
            tmp_path, key=key, tape=_synthetic_tape(key, preflight_sha)
        )

    def exhausted(_panel: object) -> dict[str, object]:
        raise e1.estimands.E1ResourceIncomplete("fixture solver cap")

    monkeypatch.setattr(e1.estimands, "solve_u1", exhausted)
    receipt, skipped, valid = e1.execute_merge(
        output=tmp_path, preflight_sha256=preflight_sha
    )
    assert not skipped and not valid
    assert e1._load_json(receipt, field="solver incomplete")["status"] == "INCOMPLETE"
    assert not (tmp_path / e1.DEFAULT_TERMINAL_RECEIPT_NAME).exists()


def test_premature_merge_waits_without_terminal(tmp_path: Path) -> None:
    with pytest.raises(e1.E1MergeWaiting, match="12 units missing"):
        e1.execute_merge(output=tmp_path, preflight_sha256="f" * 64)
    assert not (tmp_path / e1.DEFAULT_TERMINAL_RECEIPT_NAME).exists()


def test_corrupted_published_unit_creates_global_invalidation(
    tmp_path: Path,
) -> None:
    key = e1.ALL_UNITS[0]
    preflight_sha = "d" * 64
    e1.write_unit_bundle(tmp_path, key=key, tape=_synthetic_tape(key, preflight_sha))
    tape = tmp_path / "units" / key.slug / e1.DEFAULT_TAPE_NAME
    tape.chmod(0o644)
    tape.write_text("{}\n", encoding="ascii")
    tape.chmod(0o444)
    path, skipped, valid = e1.execute_unit(
        key=key, output=tmp_path, tle_root=e1.CANONICAL_TLE_ROOT,
        preflight_sha256=preflight_sha,
    )
    assert not skipped and not valid
    assert path.name == e1.DEFAULT_GLOBAL_INVALIDATION_NAME
    assert e1._load_json(path, field="global invalidation")["status"] == "INVALID_RUN"


def test_preflight_refuses_missing_contract_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(e1, "HERE", tmp_path)
    (tmp_path / e1.CONTRACT_FILENAME).write_text("draft\n", encoding="ascii")
    target = tmp_path / "preflight.json"
    with pytest.raises(e1.E1Error, match="not sealed"):
        preflight.write_manifest(target)
    assert not target.exists()


def _seal_contract(root: Path) -> dict[str, str]:
    contract = root / e1.CONTRACT_FILENAME
    contract.write_text("frozen contract\n", encoding="ascii")
    contract.chmod(0o444)
    digest = e1.file_sha256(contract)
    sidecar = Path(f"{contract}.sha256")
    sidecar.write_text(f"{digest}  {contract.name}\n", encoding="ascii")
    sidecar.chmod(0o444)
    return {"path": str(contract.resolve()), "sha256": digest}


def test_preflight_builder_and_dry_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = {"path": "/controller/contract", "sha256": "9" * 64}
    frozen_inputs = {
        "preregistration": {"path": "artifacts/prereg.json", "sha256": "8" * 64, "record_digest": "7" * 64},
        "tle_archive": {"root": str(e1.CANONICAL_TLE_ROOT), "manifest_sha256": "6" * 64, "file_set_sha256": "5" * 64, "file_count": 373},
    }
    monkeypatch.setattr(e1, "sealed_contract_binding", lambda: contract)
    monkeypatch.setattr(e1, "prereg_tle_bindings", lambda: frozen_inputs)
    manifest, sidecar, digest = preflight.write_manifest(tmp_path / "preflight.json")
    payload, observed = e1.validate_preflight_manifest(manifest)
    assert observed == digest
    assert sidecar.read_text(encoding="ascii").split() == [digest, manifest.name]
    args = argparse.Namespace(
        dry_run=True, preflight_manifest=manifest, launch_authority=None,
        unit=None, merge=False, tle_root=None, output=None,
        budget_worker_seconds=e1.DEFAULT_BUDGET_WORKER_SECONDS,
    )
    assert e1.run(args) == {"preflight": manifest, "worlds": e1.WORLDS}
    assert payload["contract"] == contract


def test_launch_authority_freezes_roots_and_arguments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(e1, "HERE", tmp_path)
    contract = _seal_contract(tmp_path)
    frozen_inputs = {
        "preregistration": {"path": "artifacts/prereg.json", "sha256": "8" * 64, "record_digest": "7" * 64},
        "tle_archive": {"root": str(e1.CANONICAL_TLE_ROOT), "manifest_sha256": "6" * 64, "file_set_sha256": "5" * 64, "file_count": 373},
    }
    monkeypatch.setattr(e1, "prereg_tle_bindings", lambda: frozen_inputs)
    preflight_path = tmp_path / "preflight.json"
    preflight_sha = "a" * 64
    output = (tmp_path / "output").resolve()
    arguments = ["--merge", "--output", str(output)]
    authority = {
        "schema": e1.LAUNCH_AUTHORITY_SCHEMA,
        "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": e1.CLAIM_CEILING,
        "preflight_manifest": {"path": str(preflight_path), "sha256": preflight_sha},
        "contract": contract,
        "bindings": e1.panel_bindings(),
        "checkout_root": str(e1.REPO.resolve()),
        "output_root": str(output),
        "tle_root": str(e1.CANONICAL_TLE_ROOT),
        **frozen_inputs,
        "launch_arguments": arguments,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }
    path = tmp_path / "authority.json"
    path.write_text(json.dumps(authority), encoding="ascii")
    assert e1.validate_launch_authority(
        path, preflight_path=preflight_path, preflight_sha256=preflight_sha,
        output_root=output, tle_root=e1.CANONICAL_TLE_ROOT,
        launch_arguments=arguments,
    ) == authority
    with pytest.raises(e1.E1Error, match="output root"):
        e1.validate_launch_authority(
            path, preflight_path=preflight_path, preflight_sha256=preflight_sha,
            output_root=tmp_path / "changed", tle_root=e1.CANONICAL_TLE_ROOT,
            launch_arguments=arguments,
        )
    with pytest.raises(e1.E1Error, match="TLE root"):
        e1.validate_launch_authority(
            path, preflight_path=preflight_path, preflight_sha256=preflight_sha,
            output_root=output, tle_root=tmp_path / "tle", launch_arguments=arguments,
        )
    with pytest.raises(e1.E1Error, match="launch arguments"):
        e1.validate_launch_authority(
            path, preflight_path=preflight_path, preflight_sha256=preflight_sha,
            output_root=output, tle_root=e1.CANONICAL_TLE_ROOT,
            launch_arguments=["--merge", "--changed"],
        )
