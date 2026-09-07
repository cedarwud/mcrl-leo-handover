#!/usr/bin/env python3
"""Rebuild the V2 100E launch manifest and its external frozen pin.

The closure is explicit and auditable: the V2 package, every scratch module the
runner/factory/bridge/adapter/orchestrator/trainer/schedule/diagnostic import,
their focused tests, the governing documents, and the complete transitive
``mcrl`` import closure of the learner seam (53 files, computed on 2026-09-07
by importing the seam and listing ``sys.modules``).  Binding the whole closure
matters because the R7 seed checkout used to seed the launch checkout lacks
five of these runtime files and carries the R7-era three-route / V0.14 head.
This script writes only the manifest and its pin; it never contacts a server.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PACKAGE = ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2"
MANIFEST_NAME = "V023-100E-LAUNCH-MANIFEST.sha256"
PIN_NAME = "V023-100E-LAUNCH-MANIFEST-FROZEN.sha256"

PACKAGE_FILES = (
    "V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md",
    "V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.sha256",
    "V023-100E-MODEL-CONFIG.json",
    "V023-100E-MODEL-CONFIG.sha256",
    "V023-100E-POST-R7-PROVIDER-CONFIG.json",
    "V023-100E-POST-R7-PROVIDER-CONFIG.sha256",
    "preflight_v023_100e_source_training.py",
    "verify_v023_100e_source_training.py",
    "sync_launch_v023_100e_source_training_server.sh",
    "test_v023_100e_source_training_server.py",
    "run_v023_one_epoch_provider_diagnostic.py",
    "test_v023_one_epoch_provider_diagnostic.py",
    "build_v023_100e_launch_manifest.py",
)
SCRATCH_FILES = (
    ".scratch/multi-catfish-v023-c3-source-schedule/test_v023_c3_source_schedule.py",
    ".scratch/multi-catfish-v023-c3-source-schedule/v023_c3_source_schedule.py",
    ".scratch/multi-catfish-v023-five-arm-learner-orchestrator/test_v023_five_arm_learner_orchestrator.py",
    ".scratch/multi-catfish-v023-five-arm-learner-orchestrator/v023_five_arm_learner_orchestrator.py",
    ".scratch/multi-catfish-v023-five-arm-training-runner/test_v023_five_arm_source_training_runner.py",
    ".scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py",
    ".scratch/multi-catfish-v023-heterogeneous-trainer/test_v023_heterogeneous_trainer.py",
    ".scratch/multi-catfish-v023-heterogeneous-trainer/v023_heterogeneous_trainer.py",
    ".scratch/multi-catfish-v023-post-r7-provider-factory/test_v023_post_r7_provider_factory.py",
    ".scratch/multi-catfish-v023-post-r7-provider-factory/test_v023_post_r7_provider_factory_v2.py",
    ".scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory.py",
    ".scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory_v2.py",
    ".scratch/multi-catfish-v023-provider-orchestrator-bridge/test_v023_provider_orchestrator_bridge.py",
    ".scratch/multi-catfish-v023-provider-orchestrator-bridge/v023_provider_orchestrator_bridge.py",
    ".scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py",
    ".scratch/multi-catfish-v023-r7-launch-ready/r7_balanced_successor_gate.py",
    ".scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_fit_adapter.py",
    ".scratch/multi-catfish-v023-target-batch-adapter/target_batch_adapter.py",
    ".scratch/multi-catfish-v023-target-batch-adapter/test_target_batch_adapter.py",
)
DOC_FILES = (
    "docs/MULTI-CATFISH-MCRL-CONDITIONAL-EXECUTION-AUTHORIZATION-2026-09-06.md",
    "docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md",
    "docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md",
    "docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md",
    "docs/decisions/ADR-007-action-shared-three-q-instrument.md",
)
MCRL_FILES = (
    "src/mcrl/__init__.py",
    "src/mcrl/algorithms/__init__.py",
    "src/mcrl/algorithms/ee_axis_action_shared.py",
    "src/mcrl/algorithms/ee_axis_lcsrs_c3_head.py",
    "src/mcrl/algorithms/ee_axis_lcsrs_three_route.py",
    "src/mcrl/algorithms/ee_axis_pairwise.py",
    "src/mcrl/algorithms/ee_axis_v014_head.py",
    "src/mcrl/env/__init__.py",
    "src/mcrl/env/action_contract.py",
    "src/mcrl/env/antenna.py",
    "src/mcrl/env/candidates.py",
    "src/mcrl/env/cells.py",
    "src/mcrl/env/constants.py",
    "src/mcrl/env/d2.py",
    "src/mcrl/env/dwell.py",
    "src/mcrl/env/ephemeris.py",
    "src/mcrl/env/geometry.py",
    "src/mcrl/env/interference.py",
    "src/mcrl/env/keyed_fading.py",
    "src/mcrl/env/link_budget.py",
    "src/mcrl/env/mobility.py",
    "src/mcrl/env/observation_provenance.py",
    "src/mcrl/env/pointing.py",
    "src/mcrl/env/scenario.py",
    "src/mcrl/env/service.py",
    "src/mcrl/env/step.py",
    "src/mcrl/env/step_types.py",
    "src/mcrl/env/tle.py",
    "src/mcrl/errors.py",
    "src/mcrl/runtime/__init__.py",
    "src/mcrl/runtime/bessel.py",
    "src/mcrl/runtime/ee_axis_c1_selector.py",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_dataset.py",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_gate_fit.py",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_gate_metrics.py",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_learner.py",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_placebo.py",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_source_artifact.py",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_state.py",
    "src/mcrl/runtime/ee_axis_opening_dataset.py",
    "src/mcrl/runtime/ee_axis_opening_pairs.py",
    "src/mcrl/runtime/ee_axis_opening_runner.py",
    "src/mcrl/runtime/ee_axis_opening_source.py",
    "src/mcrl/runtime/ee_axis_ops3.py",
    "src/mcrl/runtime/ee_axis_source_selectors.py",
    "src/mcrl/runtime/ee_axis_state.py",
    "src/mcrl/runtime/ee_axis_v014_q2_state.py",
    "src/mcrl/runtime/ee_surplus_targets.py",
    "src/mcrl/runtime/energy_efficiency.py",
    "src/mcrl/runtime/finiteness.py",
    "src/mcrl/runtime/q_network.py",
    "src/mcrl/runtime/state_encoding.py",
    "src/mcrl/runtime/trainer_spec.py",
)


def closure() -> list[str]:
    entries = [f"{PACKAGE}/{name}" for name in PACKAGE_FILES]
    entries += list(SCRATCH_FILES) + list(DOC_FILES) + list(MCRL_FILES)
    if len(set(entries)) != len(entries):
        raise SystemExit("closure repeats a path")
    return sorted(entries)


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"closure member missing or symlinked: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def render(repo: Path) -> bytes:
    lines = [f"{_sha256(repo / relative)}  {relative}" for relative in closure()]
    return ("\n".join(lines) + "\n").encode("ascii")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="rewrite the manifest and its pin")
    mode.add_argument("--check", action="store_true", help="verify the existing manifest and pin without writing")
    arguments = parser.parse_args(argv)
    repo = arguments.repo.resolve()
    manifest = repo / PACKAGE / MANIFEST_NAME
    pin = repo / PACKAGE / PIN_NAME
    payload = render(repo)
    manifest_sha = hashlib.sha256(payload).hexdigest()
    pin_text = f"{manifest_sha}  {MANIFEST_NAME}\n"
    if arguments.write:
        manifest.write_bytes(payload)
        pin.write_text(pin_text, encoding="ascii")
        print(f"V023_100E_LAUNCH_MANIFEST_WRITTEN entries={len(closure())} sha256={manifest_sha}")
        return 0
    if manifest.read_bytes() != payload:
        print("V023_100E_LAUNCH_MANIFEST_DRIFTED", file=sys.stderr)
        return 3
    if pin.read_text(encoding="ascii") != pin_text:
        print("V023_100E_LAUNCH_MANIFEST_PIN_DRIFTED", file=sys.stderr)
        return 3
    print(f"V023_100E_LAUNCH_MANIFEST_CURRENT entries={len(closure())} sha256={manifest_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
