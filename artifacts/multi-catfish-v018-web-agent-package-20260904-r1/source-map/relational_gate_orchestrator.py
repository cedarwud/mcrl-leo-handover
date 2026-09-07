"""Deterministic source-only evaluation closure for V0.18 learned Q3.

This command authenticates the already harvested source rectangle and the
already written 100-update learner outputs, materialises the frozen validation
configuration and Q1+Q2 background packages, generates the decision-level
report, and independently verifies it.  It never opens a simulator, TEST
split, or episode-policy learner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Sequence

from relational_learner_runner import (
    RelationalLearnerRunnerError,
    load_verified_source_panel,
    read_run_config,
    verify_harvest_source_panel_bindings,
)
from relational_validation_report import (
    BACKGROUND_PANEL_FILENAME,
    FROZEN_STATUS,
    RelationalValidationConfig,
    RelationalValidationReportError,
    canonical_sha256,
    generate_validation_report,
    write_background_surface_packages_from_harvests,
)
from verify_relational_validation_report import (
    RelationalValidationVerificationError,
    verify,
)


ORCHESTRATOR_SCHEMA = "multi-catfish-mcrl-v018-relational-q3-gate-orchestrator-v1"
VALIDATION_CONFIG_FILENAME = "validation-config.json"
VERIFICATION_FILENAME = "independent-verification.json"
SUMMARY_FILENAME = "gate-orchestrator-result.json"


class RelationalGateOrchestratorError(ValueError):
    """The frozen source-only orchestration boundary failed."""


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise RelationalGateOrchestratorError(
            "orchestrator payload is not finite canonical JSON"
        ) from error


def _file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise RelationalGateOrchestratorError(f"expected a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_once(path: Path, payload: bytes) -> str:
    if path.exists() or path.is_symlink():
        raise RelationalGateOrchestratorError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    except FileExistsError as error:
        raise RelationalGateOrchestratorError(
            f"refusing to overwrite {path}"
        ) from error
    finally:
        temporary.unlink(missing_ok=True)
    return _file_sha256(path)


def run_gate(
    *,
    contract_path: str | Path,
    code_manifest_path: str | Path,
    learner_config_path: str | Path,
    learner_output_root: str | Path,
    output_root: str | Path,
) -> dict[str, object]:
    """Close one frozen learned-Q3 source-only gate without choices."""

    contract = Path(contract_path).absolute()
    code_manifest = Path(code_manifest_path).absolute()
    learner_config_file = Path(learner_config_path).absolute()
    learner_output = Path(learner_output_root).absolute()
    destination = Path(output_root).absolute()
    if destination.exists() or destination.is_symlink():
        raise RelationalGateOrchestratorError(
            f"refusing to overwrite gate output: {destination}"
        )
    config, train_paths, validation_paths = read_run_config(learner_config_file)
    if _file_sha256(contract) != config.contract_sha256:
        raise RelationalGateOrchestratorError(
            "contract digest disagrees with learner config"
        )
    if _file_sha256(code_manifest) != config.code_manifest_sha256:
        raise RelationalGateOrchestratorError(
            "code-manifest digest disagrees with learner config"
        )
    panel = load_verified_source_panel(
        train_paths,
        validation_paths,
        train_worlds=config.train_worlds,
        validation_worlds=config.validation_worlds,
        lineages=tuple(
            lineage for _seed, lineage in config.initialization_lineages
        ),
    )
    harvest_bindings_sha256 = verify_harvest_source_panel_bindings(
        panel, config, (*train_paths, *validation_paths)
    )
    validation_config = RelationalValidationConfig(
        contract_sha256=config.contract_sha256,
        code_manifest_sha256=config.code_manifest_sha256,
        source_panel_sha256=panel.source_sha256,
        train_worlds=config.train_worlds,
        validation_worlds=config.validation_worlds,
        initialization_lineages=config.initialization_lineages,
        q1_checkpoint_sha256_by_lineage=(
            config.q1_checkpoint_sha256_by_lineage
        ),
        q2_checkpoint_sha256_by_lineage=(
            config.q2_checkpoint_sha256_by_lineage
        ),
        kappa_bits=config.kappa_bits,
        null_kinds=("zero", "action_only"),
        gate_config={
            "contract_sha256": config.contract_sha256,
            "contract_status": FROZEN_STATUS,
            "min_mean_skill": 0.0,
            "min_positive_initializations": 2,
            "min_supported_change_rate": 0.5,
            "min_supported_initializations": 2,
            "required_updates": 100,
        },
    )
    destination.mkdir(parents=True, exist_ok=False)
    validation_config_body = validation_config.as_dict()
    validation_config_sha256 = _write_once(
        destination / VALIDATION_CONFIG_FILENAME,
        _canonical_bytes(validation_config_body),
    )
    background_outputs, background_manifest = (
        write_background_surface_packages_from_harvests(
            panel=panel,
            config=validation_config,
            output_root=destination / "background",
        )
    )
    initialization_outputs = {
        seed: learner_output / f"init-{seed}"
        for seed in validation_config.initialization_seeds
    }
    report_root = destination / "report"
    report = generate_validation_report(
        panel=panel,
        config=validation_config,
        initialization_outputs=initialization_outputs,
        output_dir=report_root,
        contract_path=contract,
        background_outputs=background_outputs,
    )
    independent = verify(
        report_root,
        config=validation_config,
        contract_path=contract,
    )
    verification_sha256 = _write_once(
        destination / VERIFICATION_FILENAME, _canonical_bytes(independent)
    )
    body: dict[str, object] = {
        "schema": ORCHESTRATOR_SCHEMA,
        "status": "SOURCE_ONLY_GATE_CLOSED",
        "decision": report["gate"]["decision"],
        "contract_sha256": config.contract_sha256,
        "code_manifest_sha256": config.code_manifest_sha256,
        "learner_config_sha256": _file_sha256(learner_config_file),
        "source_panel_sha256": panel.source_sha256,
        "harvest_bindings_sha256": harvest_bindings_sha256,
        "validation_config_sha256": validation_config_sha256,
        "background_panel_sha256": background_manifest[
            "background_panel_sha256"
        ],
        "background_panel_file_sha256": _file_sha256(
            destination / "background" / BACKGROUND_PANEL_FILENAME
        ),
        "validation_result_sha256": report["result_sha256"],
        "independent_verification_sha256": verification_sha256,
        "test_split_opened": False,
        "episode_training": False,
    }
    payload = {**body, "orchestrator_result_sha256": canonical_sha256(body)}
    _write_once(destination / SUMMARY_FILENAME, _canonical_bytes(payload))
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--code-manifest", required=True, type=Path)
    parser.add_argument("--learner-config", required=True, type=Path)
    parser.add_argument("--learner-output", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args(argv)
    try:
        result = run_gate(
            contract_path=arguments.contract,
            code_manifest_path=arguments.code_manifest,
            learner_config_path=arguments.learner_config,
            learner_output_root=arguments.learner_output,
            output_root=arguments.output,
        )
    except (
        OSError,
        RelationalGateOrchestratorError,
        RelationalLearnerRunnerError,
        RelationalValidationReportError,
        RelationalValidationVerificationError,
    ) as error:
        parser.error(str(error))
    print(_canonical_bytes(result).decode("ascii"))
    return 0


if __name__ == "__main__":  # pragma: no cover - explicit server boundary
    raise SystemExit(main())


__all__ = [
    "ORCHESTRATOR_SCHEMA",
    "RelationalGateOrchestratorError",
    "SUMMARY_FILENAME",
    "VALIDATION_CONFIG_FILENAME",
    "VERIFICATION_FILENAME",
    "main",
    "run_gate",
]
