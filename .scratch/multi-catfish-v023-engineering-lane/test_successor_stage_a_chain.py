from __future__ import annotations

import importlib
import inspect
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SPEC = HERE / "specs/successor_stage_a_chain.json"
RUNNER = REPO / ".scratch/multi-catfish-v023-two-route-source-training-runner"
LAUNCH = REPO / ".scratch/multi-catfish-v023-c1c2-successor-launch"


def _payload() -> dict[str, object]:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_runner_config_kwargs_bind_real_frozen_config_signature() -> None:
    if str(RUNNER) not in sys.path:
        sys.path.insert(0, str(RUNNER))
    runner = importlib.import_module("v023_two_route_source_training_runner")
    payload = _payload()
    step = next(item for item in payload["steps"] if item["name"] == "runner_config")

    inspect.signature(runner.FrozenSourceTrainingConfig).bind(**step["kwargs"])
    assert step["kwargs"]["provider_config_sha256"] == {
        "sha256": {"artifact": "provider_config"}
    }


def test_authority_digest_sources_match_formal_producer() -> None:
    if str(LAUNCH) not in sys.path:
        sys.path.insert(0, str(LAUNCH))
    launch_common = importlib.import_module("successor_launch_common")
    payload = _payload()
    step = next(item for item in payload["steps"] if item["name"] == "authority_digests")

    expected_sources = launch_common.run_authority_digest_spec_sources()
    assert step["kwargs"] == expected_sources
    assert set(step["inputs"]) == launch_common.run_authority_digest_artifact_names()


def test_artifact_paths_exist_or_are_documented_binder_outputs() -> None:
    if str(LAUNCH) not in sys.path:
        sys.path.insert(0, str(LAUNCH))
    launch_common = importlib.import_module("successor_launch_common")
    payload = _payload()
    artifacts = {item["name"]: item for item in payload["artifacts"]}
    assert artifacts["target_root"]["path"] is None
    expected_binder_outputs = {
        "learner_manifest": (
            launch_common.BUNDLE_REL / launch_common.LEARNER_MANIFEST_NAME
        ).as_posix(),
        "provider_config": (
            launch_common.BUNDLE_REL / launch_common.PROVIDER_CONFIG_NAME
        ).as_posix(),
    }
    for name, artifact in artifacts.items():
        path_text = artifact["path"]
        if path_text is None:
            assert name == "target_root"
            continue
        path = REPO / path_text
        if path.exists():
            continue
        assert expected_binder_outputs[name] == path_text
        reason = artifact.get("requires_after", "")
        assert "bind_v023_c1c2_successor_freeze.py --write" in reason
        assert "after bind and before the launcher" in reason


def test_resume_probe_uses_orchestrator_continuation_not_unbegun_runner() -> None:
    payload = _payload()
    steps = {item["name"]: item for item in payload["steps"]}
    assert steps["resume"]["callable"] == {
        "method_of": "resumed_runner",
        "name": "orchestrator.load_checkpoint_state",
    }
    assert steps["resume_one_epoch"]["callable"] == {
        "module": "dryrun_support",
        "name": "advance_resumed_two_route_orchestrator_one_epoch",
    }
