from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


dryrun = _load("v023_partial_merge_dryrun_test", HERE / "partial_merge_dryrun.py")
controller = dryrun._load_controller(REPO)
adapter_test = _load(
    "v023_partial_merge_adapter_test_helpers",
    REPO
    / ".scratch/multi-catfish-v023-target-batch-adapter/"
    "test_target_batch_adapter.py",
)
generator = controller._load_generator()


def _schedule_and_shards(staging: Path) -> dict[str, dict[str, object]]:
    schedule: dict[str, dict[str, object]] = {}
    sealed = SimpleNamespace(
        capture_path=Path("/authority/capture.json"),
        capture_sha256=adapter_test._digest("capture"),
        materialization_dir=Path("/authority/materialization"),
        materialization_manifest_sha256=adapter_test._digest("materialization"),
        pool_sha256=adapter_test._digest("pool"),
        source_manifest_sha256=adapter_test._digest("target-source-manifest"),
        checkpoint_sha256=adapter_test._digest("target-checkpoint"),
    )
    ctx = SimpleNamespace(
        modules=SimpleNamespace(
            opening_dataset=SimpleNamespace(
                write_opening_dataset=adapter_test.write_opening_dataset
            )
        ),
        source_family="fixture-source-family",
        lambda_bits_per_j=2.0,
        kappa_bits=3.0,
        interval_s=1.0,
    )
    for mode in ("informed", "neutral"):
        for world in range(1000, 1008):
            key = f"{mode}:{world}"
            c1_dataset = adapter_test._c1_dataset(mode=mode, world=world)
            c1_binding = adapter_test._c1_binding(
                c1_dataset, mode=mode, world=world
            )
            c2_dataset, c2_binding = adapter_test._c2_dataset_and_binding(
                mode=mode, world=world
            )
            entry = {
                "mode": mode,
                "world": world,
                "C1": [adapter_test._schedule_row(c1_binding, route="C1")],
                "C2": [adapter_test._schedule_row(c2_binding, route="C2")],
            }
            schedule[key] = entry
            root = staging / mode / f"world-{world}"
            generator._write_outputs(
                root,
                sealed=sealed,
                ctx=ctx,
                schedule={key: entry},
                c1_datasets={(mode, world): c1_dataset},
                c2_datasets={(mode, world): c2_dataset},
                c1_bindings=(c1_binding,),
                c2_bindings=(c2_binding,),
            )
    return schedule


def _mark_terminal(staging: Path, schedule: dict[str, dict[str, object]], keys) -> None:
    status = staging / "shard-status"
    status.mkdir()
    for key in keys:
        mode, world_text = key.split(":", 1)
        root = staging / mode / f"world-{world_text}"
        payload = {
            "schema": controller.SHARD_STATUS_SCHEMA,
            "event": "terminal",
            "state": "PASS",
            "mode": mode,
            "world": int(world_text),
            "recorded_unix_s": 1.0,
            "returncode": 0,
            "receipt_sha256": controller._sha(root / "receipt.json"),
            "manifest_sha256": controller._sha(root / "MANIFEST.sha256"),
            "log": f"{mode}-world-{world_text}.log",
        }
        controller._validate_shard(
            key, root, controller._read_receipt(root), schedule[key]
        )
        (status / f"{mode}-world-{world_text}.terminal.json").write_bytes(
            controller._canonical(payload)
        )


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _args(tmp_path: Path, staging: Path, scratch: Path) -> SimpleNamespace:
    return SimpleNamespace(
        checkout=REPO,
        staging=staging,
        scratch=scratch,
        capture=tmp_path / "capture.json",
        materialization_dir=tmp_path / "materialization",
        tle_root=tmp_path / "tle",
        prereg=tmp_path / "prereg.json",
        manifest=tmp_path / "manifest.json",
        manifest_digest=tmp_path / "manifest.sha256",
        execution_addendum=tmp_path / "execution-addendum.md",
        python=Path(sys.executable),
        users=100,
    )


@pytest.mark.parametrize(
    ("selected", "guard_status", "expected_rows"),
    [
        (("informed:1000", "neutral:1000", "informed:1001"),
         "EXPECTED_FULL_SCHEDULE_GUARD", {"informed": 2, "neutral": 1}),
        (None, "PASS", {"informed": 8, "neutral": 8}),
    ],
    ids=("three-shard-subset", "full-sixteen-shard-set"),
)
def test_producer_written_terminal_shards_reach_real_merge_seal_and_adapter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    selected,
    guard_status: str,
    expected_rows: dict[str, int],
) -> None:
    staging = tmp_path / "staging"
    schedule = _schedule_and_shards(staging)
    keys = tuple(schedule) if selected is None else selected
    _mark_terminal(staging, schedule, keys)
    before = _tree_digest(staging)
    monkeypatch.setattr(dryrun, "_load_controller", lambda _checkout: controller)
    monkeypatch.setattr(controller, "_expected_schedule", lambda _args: schedule)
    scratch = tmp_path / "scratch"

    assert dryrun.run(_args(tmp_path, staging, scratch)) == 0

    assert _tree_digest(staging) == before
    output = capsys.readouterr().out.strip().splitlines()
    assert output[-1] == "PARTIAL_MERGE_DRYRUN_PASS"
    report = json.loads((scratch / dryrun.REPORT_NAME).read_text(encoding="ascii"))
    assert report["claim_ceiling"] == "ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT"
    assert len(report["input_identities"]) == len(keys)
    guard = next(
        step for step in report["steps"]
        if step["step"] == "full_schedule_merge_guard"
    )
    assert guard["status"] == guard_status
    if selected is not None:
        assert guard["exception"]["text"] == (
            "mode/world shard set disagrees with the authenticated schedule"
        )
        assert not (scratch / "full-schedule-guard-probe").exists()
    assert (scratch / "merged-output/COMPLETE").is_file()
    adapter_step = next(
        step for step in report["steps"]
        if step["step"] == "adapter_dataset_concatenation"
    )
    assert adapter_step["status"] == "PASS"
    for mode, mode_layouts in adapter_step["layouts"].items():
        assert mode_layouts["C1"]["states"]["shape"] == [
            expected_rows[mode], adapter_test.EE_AXIS_STATE_DIM
        ]
        assert mode_layouts["C2"]["states"]["shape"] == [expected_rows[mode], 448]
        assert mode_layouts["C1"]["states"]["dtype"] == "float32"
        assert mode_layouts["C2"]["states"]["dtype"] == "float32"
        assert mode_layouts["C1"]["target_surplus_bits"]["dtype"] == "float64"
        assert mode_layouts["C2"]["normalized_target_deltas"]["dtype"] == "float64"
        assert mode_layouts["C1"]["action_masks"]["dtype"] == "bool"
        assert mode_layouts["C2"]["action_masks"]["dtype"] == "bool"
        for route_layouts in mode_layouts.values():
            for layout in route_layouts.values():
                assert layout["c_contiguous"] is True
                assert layout["writeable"] is False


def test_controller_path_loader_does_not_install_its_spec_name() -> None:
    sys.modules.pop("_v023_partial_merge_controller", None)
    loaded = dryrun._load_controller(REPO)

    assert loaded._merge is not None
    assert "_v023_partial_merge_controller" not in sys.modules
