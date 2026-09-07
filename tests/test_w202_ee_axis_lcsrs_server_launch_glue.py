"""Non-heavy checks for the V0.23 Ubuntu-server launch glue.

These tests never load the production source/fit/composition adapters, never
open a simulator or TLE archive, and never run a fit or TEST stage.  The only
runtime exercise is a fake runner/adapter injected into the source launcher.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest


REPO = Path(__file__).resolve().parents[1]
OBS = REPO / ".scratch" / "multi-catfish-v023-c3-observability"
SOURCE_SERVER_PATH = OBS / "run_v023_lcsrs_source_server.py"
FULL_GATE_PATH = OBS / "run_v023_lcsrs_full_gate_server.sh"
SYNC_PATH = OBS / "sync_launch_v023_lcsrs_gate_server.sh"
FINALIZE_PATH = OBS / "finalize_v023_lcsrs_gate_server.sh"


def _load_source_server() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "test_w202_v023_source_server", SOURCE_SERVER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def source_server() -> ModuleType:
    return _load_source_server()


def test_source_server_import_is_inert() -> None:
    before = set(sys.modules)
    module = _load_source_server()
    after = set(sys.modules)

    # The source adapter and staged runner are dynamic launch dependencies,
    # not import-time dependencies.  Existing NumPy/Torch imports from a
    # broader test process are irrelevant; this module must not add them.
    assert "mcrl_v023_lcsrs_source_adapter_server" not in after - before
    assert "mcrl_v023_lcsrs_gate_runner_server" not in after - before
    assert not hasattr(module, "RUNNER")
    assert not hasattr(module, "ADAPTER")


def _source_args(module: ModuleType, output: Path) -> object:
    return module._parser().parse_args(
        [
            "--world",
            "2026121705",
            "--tle-root",
            "/srv/tle",
            "--prereg",
            str(REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json"),
            "--manifest",
            str(OBS / "PREFLIGHT-MANIFEST.json"),
            "--manifest-digest",
            str(OBS / "PREFLIGHT-MANIFEST.sha256"),
            "--preflight-sha256",
            "a" * 64,
            "--output",
            str(output),
        ]
    )


def test_source_server_builds_frozen_config_and_injects_runner(
    source_server: ModuleType, tmp_path: Path
) -> None:
    calls: dict[str, object] = {}

    class FakeConfig:
        def __init__(self, **kwargs: object) -> None:
            calls["config"] = kwargs
            self.kwargs = kwargs

    class FakeAdapter:
        def __init__(self, config: FakeConfig) -> None:
            calls["adapter_config"] = config

    @dataclass(frozen=True)
    class FakeSpec:
        world: int
        output: Path
        preflight_manifest_sha256: str

    def fake_run(spec: FakeSpec, *, adapter: FakeAdapter) -> Path:
        calls["spec"] = spec
        calls["adapter"] = adapter
        return spec.output

    runner = SimpleNamespace(SourceShardSpec=FakeSpec, run_source_stage=fake_run)
    adapter = SimpleNamespace(
        V023SourceAdapterConfig=FakeConfig,
        V023RuntimeSourceAdapter=FakeAdapter,
    )
    output = tmp_path / "world-2026121705.json"
    result = source_server.launch_source(
        _source_args(source_server, output),
        runner_module=runner,
        adapter_module=adapter,
    )

    assert result == output.resolve()
    assert calls["config"] == {
        "tle_root": Path("/srv/tle"),
        "prereg": (REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json").resolve(),
        "manifest": (OBS / "PREFLIGHT-MANIFEST.json").resolve(),
        "manifest_digest": (OBS / "PREFLIGHT-MANIFEST.sha256").resolve(),
        "execution_addendum": (
            REPO
            / "docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md"
        ).resolve(),
        "placebo_key": source_server.PLACEBO_KEY,
        "placebo_key_sha256": source_server.PLACEBO_KEY_SHA256,
        "lineage": source_server.LINEAGE,
        "source_family": source_server.SOURCE_FAMILY,
    }
    spec = calls["spec"]
    assert isinstance(spec, FakeSpec)
    assert spec.world == 2026121705
    assert spec.output == output.resolve()
    assert spec.preflight_manifest_sha256 == "a" * 64


def test_source_server_rejects_existing_output_before_dynamic_seam(
    source_server: ModuleType, tmp_path: Path
) -> None:
    output = tmp_path / "already-there.json"
    output.write_text("sealed", encoding="ascii")
    called = False

    def should_not_run(*_args: object, **_kwargs: object) -> Path:
        nonlocal called
        called = True
        raise AssertionError("write-once check did not run before the fake stage")

    runner = SimpleNamespace(SourceShardSpec=object, run_source_stage=should_not_run)
    adapter = SimpleNamespace(
        V023SourceAdapterConfig=object,
        V023RuntimeSourceAdapter=object,
    )
    with pytest.raises(source_server.V023SourceServerError, match="overwrite"):
        source_server.launch_source(
            _source_args(source_server, output),
            runner_module=runner,
            adapter_module=adapter,
        )
    assert called is False


def test_source_server_main_preserves_world_and_exception_chain(
    source_server: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root_cause = RuntimeError("segment age exceeds episode length")

    def fail_with_cause(_args: object) -> Path:
        raise source_server.V023SourceServerError(
            "V0.23 source shard failed closed"
        ) from root_cause

    monkeypatch.setattr(source_server, "launch_source", fail_with_cause)
    args = _source_args(source_server, tmp_path / "unused.json")
    argv = []
    for key, value in vars(args).items():
        argv.extend((f"--{key.replace('_', '-')}", str(value)))

    assert source_server.main(argv) == 2
    error = capsys.readouterr().err
    assert "SOURCE_ERROR world=2026121705 pid=" in error
    assert "V0.23 source shard failed closed" in error
    assert "segment age exceeds episode length" in error
    assert "The above exception was the direct cause" in error


def test_full_gate_shell_is_parseable_and_help_is_non_destructive() -> None:
    syntax = subprocess.run(
        ["bash", "-n", str(FULL_GATE_PATH)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert syntax.returncode == 0, syntax.stderr

    help_result = subprocess.run(
        ["bash", str(FULL_GATE_PATH), "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert help_result.returncode == 0, help_result.stderr
    assert "source(8)" in help_result.stdout
    assert "fit(48)" in help_result.stdout
    assert "composition(48)" in help_result.stdout


def test_server_transfer_shells_are_parseable_and_bind_full_result_manifest() -> None:
    for path in (SYNC_PATH, FINALIZE_PATH):
        syntax = subprocess.run(
            ["bash", "-n", str(path)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        assert syntax.returncode == 0, syntax.stderr
        text = path.read_text(encoding="utf-8")
        assert "MANIFEST.sha256" in text
        assert "sha256sum -c RESULTS.sha256" not in text
        assert '/RESULTS.sha256"' not in text
        assert "COMPLETE" in text
    sync_text = SYNC_PATH.read_text(encoding="utf-8")
    assert 'if bash "${GATE}"' in sync_text
    assert 'if "${PYTHON}" "${GATE}"' not in sync_text
    assert ".scratch/multi-catfish-v023-c3-observability/test_v023_lcsrs_source_adapter.py" in sync_text
    assert "tests/test_w181_ee_axis_coalition_residual_c3.py" in sync_text
    assert "tests/test_w184_ee_axis_lcsrs_c3_encoder.py" in sync_text
    assert "tests/test_w189_ee_axis_lcsrs_c3_teacher.py" in sync_text
    assert "MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-LAUNCH-DECISION-2026-09-05.md" in sync_text
    assert "launch decision digest drifted" in sync_text
    assert "MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-RELAUNCH-DECISION-R4-2026-09-06.md" in sync_text
    assert "R4 relaunch decision digest drifted" in sync_text
    assert "mcrl-v023-lcsrs-gate-20260906-r4" in sync_text
    assert "R2 relaunch decision" not in sync_text
    assert "mcrl-v023-lcsrs-gate-20260905-r2" not in sync_text
    finalize_text = FINALIZE_PATH.read_text(encoding="utf-8")
    assert "multi-catfish-v023-lcsrs-gate-20260906-r4" in finalize_text
    assert "multi-catfish-v023-lcsrs-gate-20260905-r2" not in finalize_text
    assert "multi-catfish-v023-lcsrs-gate-20260905-r1" not in finalize_text
    assert '${audit_root}/independent-final-verification.json' in finalize_text
    assert '${audit_root}/independent-source-stage-verification.json' in finalize_text
    assert '${staging}/independent-final-verification.json' not in finalize_text
    assert "FETCHED-PACKAGE-MANIFEST.sha256" in finalize_text
    assert 'if saved_result != expected_result:' in finalize_text
    assert 'if archived_source_stage != payload:' in finalize_text
    assert '"source_stage_receipt_sha256"' in finalize_text
    assert '"NOT_EVALUATED_SOURCE_STAGE_STOP"' in finalize_text


def test_full_gate_static_contract_keeps_strict_order_and_closed_boundaries() -> None:
    text = FULL_GATE_PATH.read_text(encoding="utf-8")
    assert "source-manifest" in text
    assert "run_v023_lcsrs_source_server.py" in text
    assert "run_v023_lcsrs_fit_server.py" in text
    assert "run_v023_lcsrs_composition_server.py" in text
    assert "verify_v023_lcsrs_final.py" in text
    assert "verify_v023_lcsrs_source_stage.py" in text
    assert "seal_v023_lcsrs_result_directory.py" in text
    assert "--runtime-module" in text
    assert "episode-policy training" in text
    assert "test_split_opened" in text
    assert 'payload.get("status") != "PASS_FINAL_INTEGRITY"' in text
    assert 'payload.get("integrity_status") != "VERIFIED"' in text
    assert "MANIFEST.sha256" in text
    assert "RESULTS.sha256" not in text
    assert "--kind source-insufficient" in text
    assert "--kind full" in text
    assert 'readlink -f -- "$PYTHON"' in text
    assert '! -L "$PYTHON"' not in text
    assert text.index('payload.get("status") != "PASS_FINAL_INTEGRITY"') < text.index(
        '--kind full'
    )
    # There is no post-composition action editor/coordinator in this launcher.
    assert "coordinator or post-selection action edit" in text
