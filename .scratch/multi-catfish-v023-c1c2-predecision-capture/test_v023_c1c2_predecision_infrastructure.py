"""Cheap tests for the V0.23 pre-outcome capture infrastructure.

These tests authenticate static bindings and orchestration plans only.  They do
not launch a server, simulator, learner, evaluation, TEST split, or
materialization against a real capture.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

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


preflight = _load(
    "v023_c1c2_infrastructure_preflight",
    HERE / "preflight_v023_c1c2_predecision.py",
)
controller = _load(
    "v023_c1c2_infrastructure_controller",
    HERE / "run_v023_c1c2_predecision_capture_controller.py",
)


def _canonical(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        + b"\n"
    )


def test_static_code_manifest_reruns_original_v023_preflight() -> None:
    receipt = preflight.validate_code_manifest(
        preflight.CODE_MANIFEST,
        repo=REPO,
        v023_manifest=preflight.V023_MANIFEST,
        v023_manifest_digest=preflight.V023_MANIFEST_DIGEST,
        v023_preflight=preflight.V023_PREFLIGHT,
        preregistration=preflight.PREREGISTRATION,
    )
    assert receipt["status"] == "PASS"
    assert receipt["configuration"]["worlds"] == list(preflight.FROZEN_WORLDS)
    assert receipt["configuration"]["source_concurrency"] == 4
    assert receipt["configuration"]["panel_neutral_seeds"]["C1"]["seed"] == 3733296141
    assert receipt["configuration"]["panel_neutral_seeds"]["C2"]["seed"] == 3936591716
    assert receipt["inherited_v023_preflight"]["status"] == "PASS"


def test_sync_closure_covers_every_inherited_r5_manifest_binding() -> None:
    """Prevent a fresh server copy from omitting an authenticated R5 input."""

    manifest = json.loads(
        preflight.V023_MANIFEST.read_text(encoding="ascii")
    )
    launcher = (
        HERE / "sync_launch_v023_c1c2_predecision_capture_server.sh"
    ).read_text(encoding="utf-8")
    sync_block = launcher.split("sync_paths=(", 1)[1].split("\n)", 1)[0]
    synced = {
        line.strip()
        for line in sync_block.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    def covered(relative: str) -> bool:
        target = Path(relative)
        for entry in synced:
            source = Path(entry)
            if source == target:
                return True
            if (REPO / source).is_dir() and target.is_relative_to(source):
                return True
        return False

    missing = sorted(
        entry["path"]
        for entry in manifest["bindings"]
        if not covered(str(entry["path"]))
    )
    assert missing == []


def test_preflight_rejects_panel_seed_or_domain_drift(tmp_path: Path) -> None:
    payload = json.loads(preflight.CODE_MANIFEST.read_text(encoding="ascii"))
    payload["configuration"]["panel_neutral_seeds"]["C1"]["seed"] += 1
    manifest = tmp_path / "CODE-MANIFEST.json"
    manifest.write_bytes(_canonical(payload))
    with pytest.raises(preflight.PredecisionPreflightError, match="configuration"):
        preflight.validate_code_manifest(manifest, repo=REPO)


def test_controller_has_only_standard_library_imports() -> None:
    tree = ast.parse(
        (HERE / "run_v023_c1c2_predecision_capture_controller.py").read_text(
            encoding="utf-8"
        )
    )
    forbidden = {"numpy", "torch", "mcrl", "gym", "stable_baselines3"}
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    assert not (imports & forbidden)


def test_world_plan_is_fixed_and_uses_compute_only_concurrency() -> None:
    assert controller.SOURCE_CONCURRENCY == 4
    assert controller.FROZEN_WORLDS == tuple(range(2026121705, 2026121713))
    args = controller._parser().parse_args(
        [
            "--output-root",
            "/tmp/v023-c1c2-capture",
            "--tle-root",
            "/tmp/frozen-tle",
            "--code-manifest-sha256",
            "0" * 64,
        ]
    )
    command = controller._world_command(
        args,
        world=controller.FROZEN_WORLDS[0],
        output=Path("/tmp/v023-c1c2-capture/world.json"),
        inherited_manifest_sha256="1" * 64,
    )
    assert "--c1-neutral-seed" in command
    assert command[command.index("--c1-neutral-seed") + 1] == "3733296141"
    assert command[command.index("--c2-neutral-seed") + 1] == "3936591716"
    assert "--learner" not in command
    assert "--test" not in command


def test_controller_and_sync_are_write_once_and_fail_closed() -> None:
    controller_text = (
        HERE / "run_v023_c1c2_predecision_capture_controller.py"
    ).read_text(encoding="utf-8")
    sync_text = (
        HERE / "sync_launch_v023_c1c2_predecision_capture_server.sh"
    ).read_text(encoding="utf-8")
    assert "ThreadPoolExecutor(max_workers=SOURCE_CONCURRENCY)" in controller_text
    assert "one_panel_merge" not in controller_text
    assert "refusing to overwrite" in controller_text
    assert "type(error).__name__" in controller_text
    assert "refusing to overwrite remote server root" in sync_text
    assert "tmux has-session" in sync_text
    assert "rsync --delete" not in sync_text
    assert "--dry-run" in sync_text
    assert 'server_root="/home/sat/mcrl-v023-c1c2-predecision-20260906-r4"' in sync_text
    assert 'tmux_session="mcrl-v023-c1c2-predecision-20260906-r4"' in sync_text
    assert "tests/test_w47_ee_axis_c1_selector.py" in sync_text
    assert (
        preflight.EXPECTED_BINDINGS["c1_selector_test"]
        == "tests/test_w47_ee_axis_c1_selector.py"
    )
    assert (
        preflight.EXPECTED_CONFIGURATION["c1"]["neutral_source_rule"]
        == "c1-cluster-profile-matched-randomized-predecision-v2"
    )


def test_sync_launch_persists_controller_log_and_checks_bounded_liveness() -> None:
    sync_text = (
        HERE / "sync_launch_v023_c1c2_predecision_capture_server.sh"
    ).read_text(encoding="utf-8")

    # A successful SSH return must not be mistaken for a live controller.  The
    # launcher writes one exact server-root log, uses exec so the tmux pane is
    # the controller itself, and checks the pane for a bounded ten-second
    # window before emitting the launch PASS marker.
    assert 'controller_log="${server_root}/controller.log"' in sync_text
    assert "exec '${server_python}' '${controller}'" in sync_text
    assert ">> '${controller_log}' 2>&1" in sync_text
    assert (
        "for attempt in 1 2 3 4 5 6 7 8 9 10; do"
        in sync_text
    )
    assert "tmux list-panes -t '${tmux_session}:0.0'" in sync_text
    assert r'test \"\$pane_dead\" = 0' in sync_text
    assert r'test \"\$liveness\" -ne 1' in sync_text
    assert "tail -n 100 '${controller_log}'" in sync_text
    assert "V023_C1C2_CONTROLLER_LIVE" in sync_text


def test_capture_uses_authenticated_step_result_observation_bridge() -> None:
    bridge_text = (
        HERE / "v023_c1c2_predecision_capture.py"
    ).read_text(encoding="utf-8")
    assert "adapter._step_result_observation(environment, outcome)" in bridge_text
    assert "observation = outcome.observation" not in bridge_text


def test_complete_marker_seal_formula_is_explicit() -> None:
    source = (
        HERE / "run_v023_c1c2_predecision_capture_controller.py"
    ).read_text(encoding="utf-8")
    assert '"manifest_sha256": manifest_sha256' in source
    assert '"receipt_sha256": receipt_sha256' in source
    assert 'field="capture complete marker"' in source
