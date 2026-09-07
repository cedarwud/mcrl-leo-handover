"""Focused local checks for the frozen R7 launch revision.

These tests authenticate only repository bytes and synthetic metric inputs. No
SSH, TLE archive, simulator, learner fit, TEST split, or episode training is
opened.
"""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


preflight = _load("r7_launch_preflight_test", "preflight_r7_balanced.py")
gate = _load("r7_launch_decision_test", "r7_balanced_successor_gate.py")
runner = _load("r7_launch_runner_test", "run_v023_lcsrs_observability_gate.py")


def test_frozen_launch_preflight_passes_without_runtime_access() -> None:
    receipt = preflight.validate_manifest(
        preflight.MANIFEST,
        manifest_digest_path=preflight.MANIFEST_SHA,
        repo=REPO,
        prereg_path=REPO / preflight.PREREGISTRATION,
    )
    assert receipt["status"] == "PASS_FROZEN_PRE_OUTCOME_PREFLIGHT"
    assert receipt["manifest_status"] == "FROZEN_PRE_OUTCOME"
    assert receipt["launch"] == "AUTHORIZED_ONE_SHOT"
    assert receipt["output_root"] == "/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1"
    assert receipt["tmux_session"] == "mcrl-v023-lcsrs-gate-20260906-r7-i1"
    assert receipt["configuration"]["tle"]["root_default"] == preflight.TLE_ROOT
    roles = {item["role"] for item in receipt["bindings"]}
    assert {"source_adapter", "source_artifact_schema", "invalid_run_i0"} <= roles
    assert receipt["test_split_opened"] is False
    assert receipt["episode_training"] is False
    assert receipt["scientific_efficacy"] is False


def test_launch_manifest_binds_exact_fresh_panel_and_initial_networks() -> None:
    payload = preflight._canonical_json(preflight.MANIFEST)[0]
    assert payload["worlds"] == list(range(2026121801, 2026121809))
    assert payload["student_seeds"] == [2026135201, 2026135202, 2026135203]
    assert payload["configuration"]["source_jobs"] == 8
    assert payload["configuration"]["fit_jobs"] == 8
    assert payload["configuration"]["composition_jobs"] == 8
    assert payload["configuration"]["selected_checkpoint_role"].startswith(
        "FROZEN_GATE_BACKGROUND_PROVENANCE_ONLY"
    )


def test_code_manifest_and_launch_decision_are_separate_digest_domains() -> None:
    code_payload = preflight._canonical_json(preflight.CODE_MANIFEST)[0]
    assert code_payload["status"] == "FROZEN_PRE_OUTCOME"
    assert code_payload["launch"] == "AUTHORIZED_ONE_SHOT"
    assert "R7-LAUNCH-CODE-MANIFEST.json" not in {
        item["path"] for item in code_payload["bindings"]
    }
    code_paths = {item["path"] for item in code_payload["bindings"]}
    assert {
        "src/mcrl/__init__.py",
        "src/mcrl/algorithms/__init__.py",
        "src/mcrl/env/__init__.py",
        "src/mcrl/runtime/__init__.py",
    } <= code_paths
    decision = (REPO / preflight.LAUNCH_DECISION).read_text(encoding="utf-8")
    assert "CODE_MANIFEST_SHA256_PLACEHOLDER" not in decision
    assert "R6_FAILURE_RETAINED" in decision
    assert "NO_TEST" in decision and "NO_EPISODE_TRAINING" in decision
    assert "NO_EFFICACY" in decision


def test_code_manifest_binds_exact_dynamic_source_provenance_closure() -> None:
    """Literal importlib/Path dependencies must be transferred and hashed."""

    payload = preflight._canonical_json(preflight.CODE_MANIFEST)[0]
    bound = {item["path"] for item in payload["bindings"]}
    assert set(preflight.REQUIRED_DYNAMIC_SOURCE_PATHS) <= bound
    for relative in preflight.REQUIRED_DYNAMIC_SOURCE_PATHS:
        target = REPO / relative
        assert target.is_file() and not target.is_symlink(), relative


def test_launch_entrypoints_have_no_copied_draft_blocker_or_r6_identity() -> None:
    names = (
        "run_v023_lcsrs_source_server.py",
        "run_v023_lcsrs_fit_server.py",
        "run_v023_lcsrs_composition_server.py",
        "run_v023_lcsrs_full_gate_server.sh",
        "sync_launch_v023_lcsrs_gate_server_r7.sh",
        "finalize_v023_lcsrs_gate_server_r7.sh",
        "v023_lcsrs_source_adapter.py",
        "v023_lcsrs_fit_adapter.py",
        "v023_lcsrs_composition_adapter.py",
        "v023_lcsrs_composition_runtime.py",
    )
    forbidden = (
        "R7_NO_LAUNCH",
        "NO_LAUNCH",
        "r7_launch_blocker",
        "2026121705",
        "2026135101",
        "multi-catfish-v023-r6",
        "gate-20260906-r6",
    )
    for name in names:
        text = (HERE / name).read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), name


def test_runtime_configuration_contains_no_retired_r6_identity() -> None:
    payload = preflight._canonical_json(preflight.MANIFEST)[0]
    text = (HERE / "R7-PREFLIGHT-MANIFEST.json").read_text(encoding="ascii")
    assert payload["worlds"] == list(preflight.WORLDS)
    assert payload["student_seeds"] == list(preflight.STUDENT_SEEDS)
    for token in ("2026121705", "2026135101", "multi-catfish-v023-r6", "gate-20260906-r6"):
        assert token not in text
    assert "selected_checkpoint_role" in payload["configuration"]
    assert payload["configuration"]["selected_checkpoint_role"].startswith(
        "FROZEN_GATE_BACKGROUND_PROVENANCE_ONLY"
    )
    assert "_verify_frozen_tle" in (HERE / "run_v023_lcsrs_source_server.py").read_text(encoding="utf-8")


def test_actual_staged_runner_classes_are_present_and_closed() -> None:
    assert callable(runner.SourceShardSpec)
    assert callable(runner.FitShardSpec)
    assert runner.CLAIM_CEILING.endswith("NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY")
    plan = runner.build_plan()
    assert plan.source_count == 8
    assert plan.fit_count == 48


def test_balanced_primary_raw_secondary_and_frozen_adjudication() -> None:
    predictions = np.asarray([0.5, -0.5, 0.5, -0.5])
    targets = np.asarray([0.03, 0.03, -0.03, -0.03])
    metrics = gate.balanced_sign_metrics(predictions, targets)
    assert metrics["balanced_accuracy"] == pytest.approx(0.5)
    assert metrics["raw_sign_accuracy"] == pytest.approx(0.5)
    base = dict(
        integrity=True,
        pair_coverage=True,
        mechanics=True,
        physical_signature=True,
        teacher_composition=True,
        target_support=True,
        held_out_learner=True,
        world_stability=True,
        action_exposure=True,
        literal_11=True,
        harmful_partial=True,
        topology_consistency=True,
        learned_composition=True,
        service=True,
    )
    assert gate.adjudicate_section14_r7(**base) == "GO_FIXED_LEARNER_SCREEN_CONTRACT_R7"


def test_server_defaults_guards_help_and_syntax_are_non_destructive() -> None:
    full = HERE / "run_v023_lcsrs_full_gate_server.sh"
    sync = HERE / "sync_launch_v023_lcsrs_gate_server_r7.sh"
    finalizer = HERE / "finalize_v023_lcsrs_gate_server_r7.sh"
    for script in (full, sync, finalizer):
        parsed = subprocess.run(["bash", "-n", str(script)], cwd=REPO, capture_output=True, text=True)
        assert parsed.returncode == 0, parsed.stderr
        help_result = subprocess.run(["bash", str(script), "--help"], cwd=REPO, capture_output=True, text=True)
        assert help_result.returncode == 0, (script, help_result.stderr)
    full_text = full.read_text(encoding="utf-8")
    assert "SOURCE_JOBS=8" in full_text
    assert "FIT_JOBS=8" in full_text
    assert "COMPOSITION_JOBS=8" in full_text
    assert "--run-root must equal the frozen R7 output root" in full_text
    sync_text = sync.read_text(encoding="utf-8")
    assert "--source-jobs 8" in sync_text
    assert "--fit-jobs 8" in sync_text
    assert "--composition-jobs 8" in sync_text
    assert "R7_REMOTE_PRIOR_RUN_SCAN_PASS" in sync_text
    assert "R7_INVALID_I0_AUTHENTICATED" in sync_text
    assert "R7_SOURCE_CONSUMER_SMOKE_PASS" in sync_text
    assert "tmux new-session" in sync_text
    assert "/home/sat/mcrl-leo-handover/src" not in sync_text
    assert sync_text.index("rsync -aR") < sync_text.index("R7_TLE_FROZEN")
    assert "fresh checkout import shadowed" in sync_text
    finalizer_text = finalizer.read_text(encoding="utf-8")
    assert "R7_REMOTE_RESULT_VERIFIED" in finalizer_text
    assert "MANIFEST.sha256" in finalizer_text


def test_result_boundary_is_explicitly_non_efficacy() -> None:
    text = (HERE / "verify_v023_lcsrs_final.py").read_text(encoding="utf-8")
    assert '"scientific_claim": False' in text
    assert "episode_training" in text
    assert "test_split_opened" in text
    assert "no_scientific_token_before_integrity" in text


def test_sync_transfer_list_binds_code_manifest_and_digest() -> None:
    text = (HERE / "sync_launch_v023_lcsrs_gate_server_r7.sh").read_text(encoding="utf-8")
    marker = 'mapfile -t SYNC_PATHS'
    start = text.index(marker)
    end = text.index("<<'PY'", start)
    invocation = text[start:end]
    assert '"$CODE_MANIFEST" "$CODE_MANIFEST"' in invocation
    assert '"$CODE_DIGEST"' in invocation
    assert '"$MANIFEST" "$MANIFEST_DIGEST"' in invocation


def test_generated_controller_binds_server_python_and_remote_prereg() -> None:
    text = (HERE / "sync_launch_v023_lcsrs_gate_server_r7.sh").read_text(encoding="utf-8")
    assert "SERVER_ROOT=${V023_SERVER_ROOT:-/home/sat/mcrl-v023-r7-launch-ready-20260906-r4}" in text
    body_start = text.index("body = f'''", text.index("CONTROLLER="))
    body_end = text.index("'''", body_start + len("body = f'''"))
    body_template = text[body_start:body_end]
    assert 'export PYTHON="{python}"' in body_template
    assert 'export PYTHONPATH="{root}/src:{root}"' in body_template
    assert 'exec "{root}/{package}/run_v023_lcsrs_full_gate_server.sh"' in body_template
    assert '--prereg "{remote_prereg}"' in body_template
    assert '--prereg "{prereg}"' not in body_template
    assert 'remote_prereg = f"{root}/artifacts/PREREG-FROZEN-2026-08-25-R2.json"' in text
    # Local manifest/prereg generator inputs are not interpolated into the
    # controller body; runtime paths are rooted at the remote checkout.
    generator_start = text.index('ssh "$SERVER_HOST" "umask 077; python3 -', text.index("CONTROLLER="))
    generator_end = text.index("<<'PY'", generator_start)
    generator_invocation = text[generator_start:generator_end]
    assert "'$PREREG'" not in generator_invocation
    assert "'$MANIFEST'" not in generator_invocation
    assert "'$MANIFEST_DIGEST'" not in generator_invocation
    assert "manifest" not in body_template
    assert "manifest_digest" not in body_template


def test_runtime_code_manifest_closes_static_mcrl_imports() -> None:
    """Every local MCRL import reachable from runtime-bound Python is shipped."""

    payload = json.loads((HERE / "R7-LAUNCH-CODE-MANIFEST.json").read_text(encoding="ascii"))
    bound = {item["path"] for item in payload["bindings"]}
    pending = [
        path
        for path in bound
        if path.endswith(".py") and not path.startswith("tests/") and (REPO / path).is_file()
    ]
    seen: set[str] = set()
    required: set[str] = set()

    def module_path(module: str) -> str | None:
        stem = REPO / "src" / Path(*module.split("."))
        source = stem.with_suffix(".py")
        package = stem / "__init__.py"
        if source.is_file():
            return source.relative_to(REPO).as_posix()
        if package.is_file():
            return package.relative_to(REPO).as_posix()
        return None

    while pending:
        relative = pending.pop()
        if relative in seen:
            continue
        seen.add(relative)
        tree = ast.parse((REPO / relative).read_text(encoding="utf-8"))
        current = ""
        if relative.startswith("src/mcrl/"):
            current = relative.removeprefix("src/").removesuffix(".py").replace("/", ".")
            current = current.removesuffix(".__init__")
        package = current if relative.endswith("/__init__.py") else current.rpartition(".")[0]
        modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(
                    alias.name
                    for alias in node.names
                    if alias.name == "mcrl" or alias.name.startswith("mcrl.")
                )
            elif isinstance(node, ast.ImportFrom):
                if node.level and current:
                    parts = package.split(".")
                    base = ".".join(parts[: len(parts) - node.level + 1])
                    module = ".".join(value for value in (base, node.module or "") if value)
                else:
                    module = node.module or ""
                if module == "mcrl" or module.startswith("mcrl."):
                    modules.append(module)
                    modules.extend(
                        f"{module}.{alias.name}" for alias in node.names if alias.name != "*"
                    )
        for module in modules:
            candidate = module_path(module)
            if candidate is not None:
                required.add(candidate)
                if candidate not in seen:
                    pending.append(candidate)
        if current:
            parts = current.split(".")
            for index in range(1, len(parts)):
                candidate = module_path(".".join(parts[:index]))
                if candidate is not None:
                    required.add(candidate)
                    if candidate not in seen:
                        pending.append(candidate)

    assert not sorted(required - bound)
