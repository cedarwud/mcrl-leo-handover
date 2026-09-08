"""Boundary tests for the E1 catalog, tape, publication, and lifecycle."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
import json
import multiprocessing
from pathlib import Path
import stat
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.link_budget import fixed_power_w, pa_efficiency, supply_power_w, system_power_w

import build_e1_preflight_manifest as preflight
import build_e1_launch_authority as authority_builder
import run_v023_c3_existence_e1 as e1


def _competing_budget_worker(
    output: str, cap: float, key: e1.UnitKey, elapsed: float,
    start: object, reserved: object, release: object, finished: object,
) -> None:
    """Reserve and settle in a real child process under parent-controlled timing."""

    try:
        start.wait()
        reservation = e1._reserve_budget(
            Path(output), cap, scope="unit", key=key, declared_default=6.0
        )
        reserved.put(("reserved", reservation.token))
        if not release.wait(10.0):
            raise RuntimeError("parent did not release budget worker")
        charged = e1._finish_budget(
            Path(output), cap, reservation=reservation, elapsed=elapsed
        )
        try:
            e1._finish_budget(
                Path(output), cap, reservation=reservation, elapsed=elapsed
            )
        except e1.E1Error as error:
            duplicate = str(error)
        else:
            duplicate = "duplicate charge unexpectedly succeeded"
        finished.put(("finished", charged, duplicate))
    except BaseException as error:
        reserved.put(("error", type(error).__name__, str(error)))


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


def test_concurrent_budget_reservations_are_visible_and_charged_once(
    tmp_path: Path,
) -> None:
    context = multiprocessing.get_context("fork")
    cap = 12.0
    start = context.Event()
    release = context.Event()
    reserved = context.Queue()
    finished = context.Queue()
    processes = [
        context.Process(
            target=_competing_budget_worker,
            args=(
                str(tmp_path), cap, e1.ALL_UNITS[index], elapsed,
                start, reserved, release, finished,
            ),
        )
        for index, elapsed in enumerate((9.0, 3.0))
    ]
    for process in processes:
        process.start()
    start.set()
    reservation_messages = [reserved.get(timeout=10.0) for _ in processes]
    assert all(message[0] == "reserved" for message in reservation_messages)

    during = e1._budget_snapshot(tmp_path, cap)
    assert {row["token"] for row in during["reservations"]} == {
        message[1] for message in reservation_messages
    }
    assert [
        float.fromhex(row["reserved_worker_seconds_hex"])
        for row in during["reservations"]
    ] == [6.0, 6.0]
    with pytest.raises(e1.E1Incomplete, match="cannot reserve"):
        e1._reserve_budget(
            tmp_path, cap, scope="merge", declared_default=6.0
        )

    release.set()
    finish_messages = [finished.get(timeout=10.0) for _ in processes]
    for process in processes:
        process.join(timeout=10.0)
        assert process.exitcode == 0
    assert all(message[0] == "finished" for message in finish_messages)
    assert all("already charged" in message[2] for message in finish_messages)

    after = e1._budget_snapshot(tmp_path, cap)
    assert after["reservations"] == []
    assert float.fromhex(after["charged_worker_seconds_hex"]) == 12.0
    assert after["unit_charge_count"] == 2


def test_budget_charges_full_elapsed_beyond_reservation(tmp_path: Path) -> None:
    reservation = e1._reserve_budget(
        tmp_path, 20.0, scope="unit", key=e1.ALL_UNITS[0], declared_default=6.0
    )
    assert reservation.reserved_worker_seconds == 6.0
    assert e1._finish_budget(
        tmp_path, 20.0, reservation=reservation, elapsed=9.0
    ) == 9.0


def test_interruption_charges_exact_mocked_elapsed_once(tmp_path: Path) -> None:
    ticks = iter((10.0, 13.5))
    receipt, skipped, valid = e1.execute_unit(
        key=e1.ALL_UNITS[0], output=tmp_path, tle_root=e1.CANONICAL_TLE_ROOT,
        preflight_sha256="a" * 64, clock=lambda: next(ticks),
        generator=lambda **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt("stop")),
    )
    assert not skipped and not valid
    payload = e1._load_json(receipt, field="interruption receipt")
    assert float.fromhex(payload["worker_seconds_hex"]) == 3.5
    ledger = e1._budget_snapshot(tmp_path, e1.DEFAULT_BUDGET_WORKER_SECONDS)
    assert float.fromhex(ledger["charged_worker_seconds_hex"]) == 3.5
    assert ledger["unit_charge_count"] == 1
    assert ledger["reservations"] == []


def test_execute_unit_publication_interruption_resumes_without_duplicate_charge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = e1.ALL_UNITS[0]
    preflight_sha = "6" * 64
    ticks = iter((10.0, 12.0, 20.0, 23.0))
    real_rename = e1.os.rename
    interrupted = False

    def interrupt_before_unit_rename(source: object, destination: object) -> None:
        nonlocal interrupted
        destination_path = Path(destination)
        if not interrupted and destination_path == tmp_path / "units" / key.slug:
            interrupted = True
            raise KeyboardInterrupt("between unit staging and rename")
        real_rename(source, destination)

    monkeypatch.setattr(e1.os, "rename", interrupt_before_unit_rename)
    receipt, skipped, valid = e1.execute_unit(
        key=key, output=tmp_path, tle_root=e1.CANONICAL_TLE_ROOT,
        preflight_sha256=preflight_sha, clock=lambda: next(ticks),
        generator=lambda **_kwargs: _synthetic_tape(key, preflight_sha),
    )
    assert not skipped and not valid
    assert e1._load_json(receipt, field="publication interruption")["status"] == "INCOMPLETE"
    assert not (tmp_path / "units" / key.slug).exists()
    assert list((tmp_path / "units").glob(".stage-*")) == []

    completed, skipped, valid = e1.execute_unit(
        key=key, output=tmp_path, tle_root=e1.CANONICAL_TLE_ROOT,
        preflight_sha256=preflight_sha, clock=lambda: next(ticks),
        generator=lambda **_kwargs: _synthetic_tape(key, preflight_sha),
    )
    assert not skipped and valid and completed.exists()
    ledger = e1._budget_snapshot(tmp_path, e1.DEFAULT_BUDGET_WORKER_SECONDS)
    assert float.fromhex(ledger["charged_worker_seconds_hex"]) == 5.0
    assert ledger["unit_charge_count"] == 2
    assert ledger["reservations"] == []


def test_execute_unit_deferred_sigterm_during_settlement_is_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = e1.ALL_UNITS[0]
    preflight_sha = "5" * 64
    real_mask = e1._interruption_safe_publication
    real_finish = e1._finish_budget
    settling = False
    raised = False

    def tracked_finish(*args: object, **kwargs: object) -> float:
        nonlocal settling
        settling = True
        return real_finish(*args, **kwargs)

    @contextmanager
    def defer_once_at_settlement() -> object:
        nonlocal raised
        with real_mask():
            yield
        if settling and not raised:
            raised = True
            raise e1.E1Incomplete("deferred SIGTERM during unit settlement")

    monkeypatch.setattr(e1, "_finish_budget", tracked_finish)
    monkeypatch.setattr(e1, "_interruption_safe_publication", defer_once_at_settlement)
    receipt, skipped, valid = e1.execute_unit(
        key=key, output=tmp_path, tle_root=e1.CANONICAL_TLE_ROOT,
        preflight_sha256=preflight_sha,
        generator=lambda **_kwargs: _synthetic_tape(key, preflight_sha),
    )
    assert not skipped and not valid
    assert e1._load_json(receipt, field="unit settlement interruption")["status"] == "INCOMPLETE"
    assert len(list((tmp_path / "incomplete").glob("*.json"))) == 1
    ledger = e1._budget_snapshot(tmp_path, e1.DEFAULT_BUDGET_WORKER_SECONDS)
    assert ledger["unit_charge_count"] == 1
    assert ledger["reservations"] == []


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


def test_merge_charges_through_terminal_publication_and_readback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight_sha = "2" * 64
    for key in e1.ALL_UNITS:
        e1.write_unit_bundle(tmp_path, key=key, tape=_synthetic_tape(key, preflight_sha))
    now = [0.0]
    real_build = e1.build_terminal_receipt
    real_publish = e1._publish_write_once

    def timed_build(**kwargs: object) -> dict[str, object]:
        now[0] += 3.0
        return real_build(**kwargs)

    def timed_publish(path: Path, payload: dict[str, object]) -> str:
        now[0] += 7.0
        return real_publish(path, payload)

    monkeypatch.setattr(e1, "build_terminal_receipt", timed_build)
    monkeypatch.setattr(e1, "_publish_write_once", timed_publish)
    terminal, skipped, valid = e1.execute_merge(
        output=tmp_path, preflight_sha256=preflight_sha, clock=lambda: now[0]
    )
    assert not skipped and valid
    assert e1._load_json(terminal, field="terminal")["status"] == "COMPLETE"
    ledger = e1._budget_snapshot(tmp_path, e1.DEFAULT_BUDGET_WORKER_SECONDS)
    assert float.fromhex(ledger["charged_worker_seconds_hex"]) == 10.0


def test_merge_deferred_sigterm_during_settlement_publishes_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight_sha = "1" * 64
    for key in e1.ALL_UNITS:
        e1.write_unit_bundle(tmp_path, key=key, tape=_synthetic_tape(key, preflight_sha))
    real_mask = e1._interruption_safe_publication
    real_finish = e1._finish_budget
    settling = False
    raised = False

    def tracked_finish(*args: object, **kwargs: object) -> float:
        nonlocal settling
        settling = True
        return real_finish(*args, **kwargs)

    @contextmanager
    def defer_once_at_settlement() -> object:
        nonlocal raised
        with real_mask():
            yield
        if settling and not raised:
            raised = True
            raise e1.E1Incomplete("deferred SIGTERM during merge settlement")

    monkeypatch.setattr(e1, "_finish_budget", tracked_finish)
    monkeypatch.setattr(e1, "_interruption_safe_publication", defer_once_at_settlement)
    receipt, skipped, valid = e1.execute_merge(
        output=tmp_path, preflight_sha256=preflight_sha
    )
    assert not skipped and not valid
    assert e1._load_json(receipt, field="merge settlement interruption")["status"] == "INCOMPLETE"
    incomplete = list((tmp_path / "incomplete").glob("merge-*.json"))
    assert incomplete == [receipt]
    ledger = e1._budget_snapshot(tmp_path, e1.DEFAULT_BUDGET_WORKER_SECONDS)
    assert ledger["reservations"] == []


@pytest.mark.parametrize(
    "interruption",
    [
        KeyboardInterrupt("fixture terminal revalidation interruption"),
        e1.estimands.E1ResourceIncomplete("fixture terminal solver exhaustion"),
    ],
    ids=["keyboard-interrupt", "solver-exhaustion"],
)
def test_complete_terminal_revalidation_interruption_stays_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interruption: BaseException,
) -> None:
    preflight_sha = "7" * 64
    for key in e1.ALL_UNITS:
        e1.write_unit_bundle(tmp_path, key=key, tape=_synthetic_tape(key, preflight_sha))
    terminal, _skipped, valid = e1.execute_merge(
        output=tmp_path, preflight_sha256=preflight_sha
    )
    assert valid and e1._load_json(terminal, field="complete terminal")["status"] == "COMPLETE"

    def interrupted(**_kwargs: object) -> dict[str, object]:
        raise interruption

    monkeypatch.setattr(e1, "build_terminal_receipt", interrupted)
    receipt, skipped, valid = e1.execute_merge(
        output=tmp_path, preflight_sha256=preflight_sha
    )
    assert not skipped and not valid
    assert e1._load_json(receipt, field="revalidation incomplete")["status"] == "INCOMPLETE"
    assert terminal.exists()
    assert not (tmp_path / e1.DEFAULT_GLOBAL_INVALIDATION_NAME).exists()


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


def test_failure_after_unit_rename_publishes_global_invalidation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = e1.ALL_UNITS[0]
    preflight_sha = "b" * 64
    monkeypatch.setattr(
        e1, "authenticate_unit_bundle",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(e1.E1Error("post-rename failure")),
    )
    path, skipped, valid = e1.execute_unit(
        key=key, output=tmp_path, tle_root=e1.CANONICAL_TLE_ROOT,
        preflight_sha256=preflight_sha,
        generator=lambda **_kwargs: _synthetic_tape(key, preflight_sha),
    )
    assert not skipped and not valid
    assert path.name == e1.DEFAULT_GLOBAL_INVALIDATION_NAME
    assert (tmp_path / "units" / key.slug).is_dir()


def test_staged_publication_interruption_leaves_clean_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "terminal.json"
    real_rename = e1.os.rename
    calls = 0

    def interrupt_once(source: object, destination: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise KeyboardInterrupt("between staging and rename")
        real_rename(source, destination)

    monkeypatch.setattr(e1.os, "rename", interrupt_once)
    with pytest.raises(KeyboardInterrupt, match="between staging"):
        e1._publish_write_once(target, {"status": "COMPLETE"})
    assert not target.exists()
    assert list(tmp_path.glob(".stage-*")) == []
    digest = e1._publish_write_once(target, {"status": "COMPLETE"})
    assert e1.file_sha256(target) == digest


def test_global_marker_precedes_unit_and_merge_with_digest(tmp_path: Path) -> None:
    preflight_sha = "c" * 64
    marker = e1._publish_global_invalidation(
        tmp_path, preflight_sha256=preflight_sha, error=e1.E1Error("fixture")
    )
    digest = e1.file_sha256(marker)
    with pytest.raises(e1.E1Error, match=rf"unit: .*sha256={digest}"):
        e1.execute_unit(
            key=e1.ALL_UNITS[0], output=tmp_path, tle_root=tmp_path / "wrong-tle",
            preflight_sha256=preflight_sha,
        )
    with pytest.raises(e1.E1Error, match=rf"merge: .*sha256={digest}"):
        e1.execute_merge(output=tmp_path, preflight_sha256=preflight_sha)


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


def _write_sidecar(path: Path) -> None:
    path.chmod(0o444)
    digest = e1.file_sha256(path)
    sidecar = path.with_suffix(".sha256")
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="ascii")
    sidecar.chmod(0o444)


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
    monkeypatch.setattr(e1, "process_bindings", lambda: {"mocked": "portable"})
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
        "preflight_manifest": {
            "path": e1._preflight_path_record(preflight_path), "sha256": preflight_sha,
        },
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
    _write_sidecar(path)
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


def test_process_bindings_capture_runtime_hardware_threads_and_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import torch

    (tmp_path / "pyvenv.cfg").write_text("home = /portable-fixture\n", encoding="ascii")
    monkeypatch.setattr(e1, "_assert_server_interpreter", lambda: None)
    monkeypatch.setattr(e1.sys, "prefix", str(tmp_path))
    for name in e1.THREAD_ENVIRONMENT_NAMES:
        monkeypatch.setenv(name, "1")
    monkeypatch.setattr(torch, "get_num_threads", lambda: 1)
    monkeypatch.setattr(torch, "get_num_interop_threads", lambda: 1)
    monkeypatch.setattr(e1, "_threadpool_info", lambda: None)
    bindings = e1.process_bindings()
    assert set(bindings["third_party_versions"]) == {"numpy", "torch", "sgp4"}
    assert bindings["hardware"]["cpu_model"]
    assert bindings["hardware"]["logical_core_count"] >= 1
    threads = bindings["effective_threads"]
    assert threads["declared_threads"] == 1
    assert threads["authentication"] == "torch+environment+numpy.show_config"
    assert threads["environment"] == {name: "1" for name in e1.THREAD_ENVIRONMENT_NAMES}
    assert threads["torch_num_threads"] == 1
    assert threads["torch_num_interop_threads"] == 1
    assert threads["threadpoolctl"] is None
    assert "Build Dependencies" in threads["numpy_show_config"]["text"]
    assert e1.hashlib.sha256(
        threads["numpy_show_config"]["text"].encode("utf-8")
    ).hexdigest() == threads["numpy_show_config"]["sha256"]
    venv = bindings["virtual_environment"]
    assert Path(venv["root"]) == Path(e1.sys.prefix).resolve()
    assert e1.file_sha256(Path(venv["pyvenv_cfg_path"])) == venv["pyvenv_cfg_sha256"]

    monkeypatch.setenv("OPENBLAS_NUM_THREADS", "2")
    with pytest.raises(e1.E1Error, match="one-thread rule"):
        e1.process_bindings()


def test_process_bindings_refuse_effective_threadpoolctl_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import torch

    (tmp_path / "pyvenv.cfg").write_text("home = /portable-fixture\n", encoding="ascii")
    monkeypatch.setattr(e1, "_assert_server_interpreter", lambda: None)
    monkeypatch.setattr(e1.sys, "prefix", str(tmp_path))
    for name in e1.THREAD_ENVIRONMENT_NAMES:
        monkeypatch.setenv(name, "1")
    monkeypatch.setattr(torch, "get_num_threads", lambda: 1)
    monkeypatch.setattr(torch, "get_num_interop_threads", lambda: 1)
    monkeypatch.setattr(
        e1, "_threadpool_info",
        lambda: [{
            "user_api": "blas", "internal_api": "openblas", "num_threads": 4,
            "prefix": "libscipy_openblas", "filepath": "/fixture/libblas.so",
            "version": "fixture", "threading_layer": "pthreads",
            "architecture": "fixture",
        }],
    )
    with pytest.raises(e1.E1Error, match="effective BLAS/OpenMP"):
        e1.process_bindings()


def test_launch_authority_builder_roundtrip_and_every_field_mutation_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(e1, "HERE", tmp_path)
    contract = _seal_contract(tmp_path)
    frozen_inputs = {
        "preregistration": {
            "path": "artifacts/prereg.json", "sha256": "8" * 64,
            "record_digest": "7" * 64,
        },
        "tle_archive": {
            "root": str(e1.CANONICAL_TLE_ROOT), "manifest_sha256": "6" * 64,
            "file_set_sha256": "5" * 64, "file_count": 373,
        },
    }
    static = {"contract": contract, **frozen_inputs, "process_environment": {"mocked": True}}
    monkeypatch.setattr(e1, "prereg_tle_bindings", lambda: frozen_inputs)
    monkeypatch.setattr(e1, "validate_static_bindings", lambda: static)
    monkeypatch.setattr(e1, "expected_code_bindings", lambda: [])
    preflight_path, _sidecar, preflight_sha = preflight.write_manifest(
        tmp_path / "preflight.json"
    )
    output_root = (tmp_path / "run-output").resolve()
    authority_path = (tmp_path / "authority.json").resolve()
    arguments = [
        "--merge", "--preflight-manifest", str(preflight_path),
        "--launch-authority", str(authority_path),
        "--tle-root", str(e1.CANONICAL_TLE_ROOT),
        "--output", str(output_root),
    ]
    built, sidecar, authority_sha = authority_builder.write_authority(
        preflight_manifest=preflight_path, contract=Path(contract["path"]),
        output_root=output_root, tle_root=e1.CANONICAL_TLE_ROOT,
        launch_arguments=arguments, output=authority_path,
    )
    payload = e1.validate_launch_authority(
        built, preflight_path=preflight_path, preflight_sha256=preflight_sha,
        output_root=output_root, tle_root=e1.CANONICAL_TLE_ROOT,
        launch_arguments=arguments,
    )
    assert e1.file_sha256(built) == authority_sha
    assert sidecar.read_text(encoding="ascii").split() == [authority_sha, built.name]

    for field in payload:
        mutated = copy.deepcopy(payload)
        value = mutated[field]
        if isinstance(value, bool):
            mutated[field] = not value
        elif isinstance(value, str):
            mutated[field] = value + "-mutated"
        elif isinstance(value, list):
            mutated[field] = [*value, "--mutated"]
        else:
            assert isinstance(value, dict)
            mutated[field] = {**value, "mutated": True}
        candidate = tmp_path / f"authority-mutated-{field}.json"
        digest = e1._write_once(candidate, mutated)
        candidate_sidecar = candidate.with_suffix(".sha256")
        candidate_sidecar.write_text(
            f"{digest}  {candidate.name}\n", encoding="ascii"
        )
        candidate_sidecar.chmod(0o444)
        with pytest.raises(e1.E1Error):
            e1.validate_launch_authority(
                candidate, preflight_path=preflight_path,
                preflight_sha256=preflight_sha, output_root=output_root,
                tle_root=e1.CANONICAL_TLE_ROOT, launch_arguments=arguments,
            )
