"""Fast synthetic tests for the V0.24 regime probe."""

from __future__ import annotations

from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import run_v024_regime_probe as probe
from mcrl.env.action_contract import Association
from mcrl.env.reference_policy import build_reference_policy


class Table:
    def __init__(self, entries: dict[int, tuple[int, int]]) -> None:
        self.mask = np.zeros(28, dtype=np.bool_)
        self.norad_ids = np.full(28, -1, dtype=np.int64)
        self.cell_ids = np.full(28, -1, dtype=np.int64)
        for action, (norad, cell) in entries.items():
            self.mask[action] = True
            self.norad_ids[action] = norad
            self.cell_ids[action] = cell

    @property
    def num_valid(self) -> int:
        return int(self.mask.sum())

    def association(self, action: int) -> Association:
        return Association(int(self.norad_ids[action]), int(self.cell_ids[action]))


def candidates() -> object:
    tables = (Table({2: (10, 1), 7: (20, 2)}), Table({1: (30, 3), 5: (40, 4)}))
    return SimpleNamespace(slot_tables=tables, masks=np.stack([table.mask for table in tables]))


@pytest.mark.parametrize("carrier", probe.CARRIERS)
def test_reference_carriers_are_deterministic_and_mask_legal(carrier: str) -> None:
    first = build_reference_policy(carrier, probe.carrier_seed(probe.WORLDS[0], carrier))
    second = build_reference_policy(carrier, probe.carrier_seed(probe.WORLDS[0], carrier))
    first.reset(); second.reset()
    left = first.act(candidates(), np.random.default_rng(first.seed))
    right = second.act(candidates(), np.random.default_rng(second.seed))
    assert np.array_equal(left, right)
    for uid, action in enumerate(left):
        assert candidates().slot_tables[uid].mask[action]


def raw_profile(capacity: list[float], *, energy_w: float = 2.0) -> dict[str, object]:
    users = len(capacity)
    return {
        "schema": "synthetic-complete-physical-profile",
        "link_rate_bps": [float(value / probe.INTERVAL_S).hex() for value in capacity],
        "capacity_bits": [float(value).hex() for value in capacity],
        "rate_semantics": "UNBOUNDED_SHANNON_CAPACITY_BITS_PER_S",
        "link_power_w": [1.0.hex()] * users,
        "served": [True] * users,
        "serving_satellite": [10] * users,
        "serving_cell": [1] * users,
        "active_beams": [{"serving_satellite": 10, "serving_cell": 1, "link_power_w": 1.0.hex()}],
        "fixed_power_w": 1.0.hex(),
        "system_power_w": energy_w.hex(),
        "interval_s": probe.INTERVAL_S.hex(),
    }


def synthetic_raw() -> dict[str, object]:
    base = raw_profile([probe.INTERVAL_S * 300e6, probe.INTERVAL_S * 20e6])
    candidate = raw_profile([probe.INTERVAL_S * 400e6, probe.INTERVAL_S * 40e6])
    step = {
        "step_index": 0,
        "reference_profile": base,
        "unilateral_profiles": [{"profile_id": "U:0:1", "focal_user": 0, "candidate_action": 1, "candidate_joint_actions": [1, 0], "profile": candidate}],
        "joint_profiles": [{"profile_id": "J:10:1->20:2", "origin_users": [0], "candidate_joint_actions": [1, 0], "profile": candidate}],
    }
    return {"schema": probe.RAW_TAPE_SCHEMA, "status": "COMPLETE_IMMUTABLE_TAPE", "unit": probe.ALL_UNITS[0].as_dict(), "preflight_sha256": "a" * 64, "steps": [step]}


def test_one_raw_tape_reproduces_each_grid_bits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "STEPS", 1)
    raw = synthetic_raw()
    for grid, demand in probe.GRIDS.items():
        derived = probe.derive_grid_tape(raw, grid=grid, raw_sha256="b" * 64)
        observed = derived["steps"][0]["base"]
        capacity = [probe.INTERVAL_S * 300e6, probe.INTERVAL_S * 20e6]
        expected = sum(capacity) if np.isinf(demand) else sum(min(value, probe.INTERVAL_S * demand) for value in capacity)
        assert observed["total_bits"] == expected
        assert derived["raw_tape_sha256"] == "b" * 64


def option(name: str, bits: float, energy: float) -> dict[str, object]:
    return {"profile_id": name, "total_bits": bits, "total_energy_j": energy, "served": 100, "opportunities": 100}


def brute(panel: list[dict[str, object]], field: str) -> Fraction:
    best = Fraction(0)
    for rows in itertools.product(*[[anchor["base"], *anchor[field]] for anchor in panel]):
        bits = sum((Fraction.from_float(row["total_bits"]) for row in rows), Fraction())
        energy = sum((Fraction.from_float(row["total_energy_j"]) for row in rows), Fraction())
        best = max(best, bits / energy)
    return best


def test_u1_j1_reused_exact_solver_matches_bruteforce() -> None:
    u_panel = [
        {"anchor_id": "a", "base": option("BASE", 10, 10), "unilateral_profiles": [option("u", 30, 12)]},
        {"anchor_id": "b", "base": option("BASE", 20, 10), "unilateral_profiles": [option("v", 21, 8)]},
    ]
    j_panel = [
        {"anchor_id": "a", "base": option("BASE", 10, 10), "joint_profiles": [option("j", 35, 11)]},
        {"anchor_id": "b", "base": option("BASE", 20, 10), "joint_profiles": [option("k", 24, 8)]},
    ]
    u = probe.e1_estimands.solve_u1(u_panel)
    j = probe.e1_estimands.solve_j1(j_panel)
    assert Fraction.from_float(u["U1"]) == Fraction.from_float(float(brute(u_panel, "unilateral_profiles")))
    assert Fraction.from_float(j["J1"]) == Fraction.from_float(float(brute(j_panel, "joint_profiles")))


def test_four_qualification_boundaries() -> None:
    exact = probe.qualification(
        j1=105.0, u1=104.0, eta_ref=100.0,
        interaction_fraction=0.005, positive_world_count=3,
        demand_guard_pass=True,
    )
    assert exact["qualifies"] is True
    mutations = (
        {"j1": np.nextafter(105.0, 0.0)},
        {"u1": np.nextafter(104.0, np.inf)},
        {"interaction_fraction": np.nextafter(0.005, 0.0)},
        {"positive_world_count": 2},
        {"demand_guard_pass": False},
    )
    base = dict(j1=105.0, u1=104.0, eta_ref=100.0, interaction_fraction=0.005, positive_world_count=3, demand_guard_pass=True)
    for mutation in mutations:
        assert probe.qualification(**(base | mutation))["qualifies"] is False


def seal(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    sidecar = Path(f"{path}.sha256")
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="ascii")
    path.chmod(0o444); sidecar.chmod(0o444)
    return digest


def test_refusals_for_unsealed_authority_other_world_and_grid(tmp_path: Path) -> None:
    document = tmp_path / "memo.md"
    document.write_text("authority\n", encoding="ascii")
    with pytest.raises(probe.ProbeError, match="controller-sealed"):
        probe._sealed_binding(document, label="memo")
    with pytest.raises(probe.ProbeError, match="world"):
        probe.UnitKey(1, probe.CARRIERS[0])
    raw = synthetic_raw()
    with pytest.raises(probe.ProbeError, match="grid"):
        probe.derive_grid_tape(raw, grid="G4", raw_sha256="b" * 64)

    launch = tmp_path / "launch.json"
    launch.write_text("{}\n", encoding="ascii")
    with pytest.raises(probe.ProbeError, match="controller-sealed"):
        probe.validate_launch_authority(
            launch, preflight=tmp_path / "preflight.json",
            preflight_sha256="a" * 64, grid="G0", output=tmp_path,
            mode="dry-run",
        )


def test_write_once(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    digest = probe._write_once(path, {"status": "COMPLETE"})
    assert probe.file_sha256(path) == digest
    assert path.stat().st_mode & 0o777 == 0o444
    with pytest.raises(probe.ProbeError, match="overwrite"):
        probe._write_once(path, {"status": "COMPLETE"})


def test_invalid_unit_receipt_includes_exception_text_and_absent_merge_waits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    def broken(**kwargs: object) -> dict[str, object]:
        raise probe.ProbeError("synthetic physical failure")

    monkeypatch.setattr(probe, "generate_raw_tape", broken)
    receipt, written = probe.execute_unit(
        key=probe.ALL_UNITS[0], grid="G0", output=tmp_path / "unit",
        tle_root=tmp_path, preflight_sha256="a" * 64,
    )
    assert written is True
    payload = json.loads(receipt.read_text(encoding="ascii"))
    assert payload["status"] == payload["outcome"] == "INVALID_RUN"
    assert payload["integrity"] is False
    assert payload["error_text"] == "synthetic physical failure"

    terminal = probe.execute_merge(
        output=tmp_path / "merge", grid="G0", preflight_sha256="a" * 64
    )
    assert terminal is None
    assert not (tmp_path / "merge/grids/G0/terminal-receipt.json").exists()
    monkeypatch.setattr(probe, "validate_preflight", lambda path: ({}, "a" * 64))
    monkeypatch.setattr(probe, "validate_launch_authority", lambda *args, **kwargs: {})
    assert probe.main([
        "--grid", "G0", "--merge", "--preflight", str(tmp_path / "preflight"),
        "--launch-authority", str(tmp_path / "authority"),
        "--output", str(tmp_path / "merge"),
    ]) == 3
    assert capsys.readouterr().out.strip() == "V024_PROBE_MERGE_WAITING"


def test_interrupted_unit_makes_merge_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = probe.ALL_UNITS[0]

    def interrupted(**kwargs: object) -> dict[str, object]:
        raise probe.e1_estimands.E1ResourceIncomplete("synthetic interruption")

    monkeypatch.setattr(probe, "generate_raw_tape", interrupted)
    receipt, written = probe.execute_unit(
        key=key, grid="G0", output=tmp_path,
        tle_root=tmp_path, preflight_sha256="a" * 64,
    )
    assert written is True
    assert json.loads(receipt.read_text(encoding="ascii"))["status"] == "INCOMPLETE"
    terminal = probe.execute_merge(
        output=tmp_path, grid="G0", preflight_sha256="a" * 64
    )
    assert terminal is not None
    merged = json.loads(terminal.read_text(encoding="ascii"))
    assert merged["status"] == merged["outcome"] == "INCOMPLETE"
    assert merged["error_text"].endswith(": synthetic interruption")


def test_generate_raw_tape_advances_from_full_last_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(probe, "USERS", 2)
    monkeypatch.setattr(probe, "STEPS", 2)
    observations = [
        SimpleNamespace(
            step_index=index,
            candidates=candidates(),
            masks=candidates().masks,
            observation_provenance=SimpleNamespace(content_digest=str(index) * 64),
        )
        for index in range(2)
    ]
    evaluation = SimpleNamespace(link_rate_bps=np.array([300e6, 20e6]))
    step_env = SimpleNamespace(
        driver=SimpleNamespace(config=SimpleNamespace(ephemeris=SimpleNamespace(time_step_s=probe.INTERVAL_S))),
        num_users=2,
    )

    class Environment:
        def __init__(self) -> None:
            self.environment = step_env
            self.last_outcome = SimpleNamespace(observation=observations[0], done=False)
            self.index = 0

        def reset(self, env_rng: object, mobility_rng: object) -> tuple[list[object], list[object], object]:
            return [], [], observations[0]

        def step(self, actions: object, rng: object) -> object:
            self.last_outcome = SimpleNamespace(
                observation=observations[min(self.index + 1, 1)],
                done=self.index == 1,
            )
            self.index += 1
            return SimpleNamespace(done=self.last_outcome.done)

    profile = raw_profile([probe.INTERVAL_S * 300e6, probe.INTERVAL_S * 20e6])
    monkeypatch.setattr(
        probe, "ENVIRONMENT_FACTORY",
        lambda key, tle_root: (Environment(), (np.random.default_rng(1), np.random.default_rng(2))),
    )
    monkeypatch.setattr(probe, "_evaluate", lambda env, actions, rng: evaluation)
    monkeypatch.setattr(
        probe, "_physical_profile",
        lambda value, interval_s: (profile, SimpleNamespace(users=2), np.zeros(2)),
    )
    monkeypatch.setattr(probe.e1_runner.f1, "enumerate_unilateral_candidates", lambda *args: ())
    monkeypatch.setattr(probe, "JOINT_BUILDER", lambda **kwargs: ())

    raw = probe.generate_raw_tape(
        key=probe.ALL_UNITS[0], tle_root=tmp_path, preflight_sha256="a" * 64
    )
    assert [step["step_index"] for step in raw["steps"]] == [0, 1]


def test_tiny_synthetic_unit_cli_reuses_raw_tape_across_grids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(probe, "USERS", 2)
    monkeypatch.setattr(probe, "STEPS", 1)
    monkeypatch.setattr(probe, "validate_preflight", lambda path: ({}, "a" * 64))
    monkeypatch.setattr(probe, "validate_launch_authority", lambda *args, **kwargs: {})
    calls: list[str] = []
    observation = SimpleNamespace(
        step_index=0,
        candidates=candidates(),
        masks=candidates().masks,
        observation_provenance=SimpleNamespace(content_digest="d" * 64),
    )
    evaluation = SimpleNamespace(link_rate_bps=np.array([300e6, 20e6]))
    step_env = SimpleNamespace(
        driver=SimpleNamespace(config=SimpleNamespace(ephemeris=SimpleNamespace(time_step_s=probe.INTERVAL_S))),
        num_users=2,
        evaluate_actions=lambda actions, rng: evaluation,
    )

    class Environment:
        def __init__(self) -> None:
            self.environment = step_env
            self.last_outcome = evaluation

        def reset(self, env_rng: object, mobility_rng: object) -> tuple[list[object], list[object], object]:
            return [], [], observation

        def step(self, actions: object, rng: object) -> object:
            self.last_outcome = evaluation
            return SimpleNamespace(done=True, observation=observation)

    def factory(key: probe.UnitKey, tle_root: Path) -> tuple[object, tuple[np.random.Generator, ...]]:
        calls.append(key.slug)
        return Environment(), (np.random.default_rng(1), np.random.default_rng(2))

    profile = raw_profile([probe.INTERVAL_S * 300e6, probe.INTERVAL_S * 20e6])
    monkeypatch.setattr(probe, "ENVIRONMENT_FACTORY", factory)
    monkeypatch.setattr(probe, "_evaluate", lambda env, actions, rng: evaluation)
    monkeypatch.setattr(
        probe, "_physical_profile",
        lambda value, interval_s: (profile, SimpleNamespace(users=2), np.zeros(2)),
    )
    monkeypatch.setattr(probe, "JOINT_BUILDER", lambda **kwargs: ())
    common = ["--unit", f"{probe.WORLDS[0]}:{probe.CARRIERS[0]}", "--preflight", str(tmp_path / "p"), "--launch-authority", str(tmp_path / "a"), "--output", str(tmp_path / "out")]
    assert probe.main(["--grid", "G1", *common]) == 0
    assert probe.main(["--grid", "G2", *common]) == 0
    assert len(calls) == 1
    raw_paths = list((tmp_path / "out/raw-units").rglob("physical-tape.json"))
    assert len(raw_paths) == 1


def test_selection_rule_never_selects_g0() -> None:
    qualifying = {grid: {"status": "COMPLETE", "outcome": "V024_PROBE_QUALIFIES"} for grid in probe.GRIDS}
    assert probe.select_grid(qualifying) == "G1"
    assert probe.select_grid({"G0": qualifying["G0"]}) is None


def test_dry_run_is_simulator_inert(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "authority_documents", lambda: {})
    monkeypatch.setattr(probe, "validate_preflight", lambda path: ({}, "c" * 64))
    monkeypatch.setattr(
        probe, "ENVIRONMENT_FACTORY",
        lambda *_args, **_kwargs: pytest.fail("dry-run opened the simulator"),
    )
    assert probe.main([
        "--grid", "G0", "--dry-run", "--preflight", str(tmp_path / "preflight")
    ]) == 0
