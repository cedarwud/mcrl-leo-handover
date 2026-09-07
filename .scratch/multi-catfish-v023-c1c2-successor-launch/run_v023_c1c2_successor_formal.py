#!/usr/bin/env python3
"""Run the frozen two-route runner while preserving all 200 update receipts."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import sys

from successor_launch_common import (
    ARM_ORDER, CLAIM_CEILING, ROUTE_ORDER, RUNNER_REL,
    SuccessorLaunchError, authenticate_preflight_freeze_authorities,
    canonical_bytes, file_sha256, read_canonical_json, verify_sidecar, write_once,
)


SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-update-ledger-v1"


def _write_or_validate(path: Path, payload: dict[str, object]) -> None:
    raw = canonical_bytes(payload)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or path.read_bytes() != raw:
            raise SuccessorLaunchError(f"existing resume artifact drifted: {path.name}")
        return
    write_once(path, raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output-root", type=Path)
    destination.add_argument("--resume", type=Path, metavar="OUTPUT_ROOT")
    parser.add_argument("--epochs", required=True, type=int)
    parser.add_argument("--provider-factory", required=True)
    parser.add_argument("--model-config-json", required=True)
    parser.add_argument("--train-seed", required=True, type=int)
    parser.add_argument("--authority-sha256")
    parser.add_argument("--code-sha256")
    parser.add_argument("--input-sha256")
    parser.add_argument("--preflight-receipt", required=True, type=Path)
    parser.add_argument("--nonformal", action="store_true")
    parser.add_argument("--execute", action="store_true", required=True)
    arguments = parser.parse_args(argv)
    repo = Path(__file__).resolve().parents[2]
    for path in (repo / "src", repo / RUNNER_REL):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    runner_module = importlib.import_module("v023_two_route_source_training_runner")
    try:
        output_root = arguments.resume or arguments.output_root
        assert output_root is not None
        preflight = read_canonical_json(arguments.preflight_receipt, field="preflight receipt")
        if preflight.get("status") != "PASS_FROZEN_C1C2_SUCCESSOR_PREFLIGHT":
            raise SuccessorLaunchError("preflight receipt does not bind the requested formal run")
        expected_formal = not arguments.nonformal
        if preflight.get("formal") is not expected_formal:
            if arguments.nonformal:
                raise SuccessorLaunchError(
                    "formal preflight receipt cannot be laundered into a non-formal rehearsal"
                )
            raise SuccessorLaunchError("preflight receipt does not bind the requested formal run")
        if arguments.nonformal != (
            "REHEARSAL-NONFORMAL" in output_root.name.upper()
        ):
            raise SuccessorLaunchError(
                "--nonformal requires an output-root basename containing REHEARSAL-NONFORMAL"
            )
        preflight_sha256 = verify_sidecar(arguments.preflight_receipt)
        freeze_authorities = authenticate_preflight_freeze_authorities(
            repo=repo,
            preflight=preflight,
            requested_output_root=output_root,
        )
        authority_sha256 = arguments.authority_sha256 or preflight.get("authority_sha256")
        code_sha256 = arguments.code_sha256 or preflight.get("code_sha256")
        input_sha256 = arguments.input_sha256 or preflight.get("input_sha256")
        if any(
            explicit is not None and explicit != observed
            for explicit, observed in (
                (arguments.authority_sha256, preflight.get("authority_sha256")),
                (arguments.code_sha256, preflight.get("code_sha256")),
                (arguments.input_sha256, preflight.get("input_sha256")),
            )
        ):
            raise SuccessorLaunchError("explicit digest disagrees with the preflight receipt")
        namespace = argparse.Namespace(
            output_root=None if arguments.resume else str(output_root),
            resume=str(output_root) if arguments.resume else None,
            nonformal=arguments.nonformal,
            epochs=arguments.epochs,
            provider_factory=arguments.provider_factory,
            model_config_json=arguments.model_config_json,
            train_seed=arguments.train_seed,
            authority_sha256=authority_sha256,
            code_sha256=code_sha256,
            input_sha256=input_sha256, execute=arguments.execute,
        )
        runner = runner_module.preflight_from_args(namespace)
        if arguments.resume:
            runner.resume_from_root(output_root)
        else:
            runner.begin_new(output_root)
        runner.run()
        if runner.completed_epochs != 100 or runner.orchestrator.next_route != "C1":
            raise SuccessorLaunchError("runner did not close at the epoch-100 boundary")
        rows = runner.update_ledger_rows
        if len(rows) != 200:
            raise SuccessorLaunchError("runner update ledger did not retain all 200 receipts")
        ledger = {
            "schema": SCHEMA, "claim_ceiling": CLAIM_CEILING,
            "formal": expected_formal,
            "arm_order": list(ARM_ORDER), "route_order": list(ROUTE_ORDER),
            "completed_epochs": 100, "completed_updates": 200,
            "updates": rows,
        }
        _write_or_validate(output_root / "update-ledger.json", ledger)
        input_binding = preflight.get("input_binding")
        if not isinstance(input_binding, dict):
            raise SuccessorLaunchError("preflight input binding is missing")
        provenance = {
            "schema": (
                "multi-catfish-mcrl-v023-c1c2-successor-formal-provenance-v1"
                if expected_formal
                else "multi-catfish-mcrl-v023-c1c2-successor-nonformal-provenance-v1"
            ),
            "formal": expected_formal,
            "preflight_receipt_sha256": preflight_sha256,
            "authority_sha256": authority_sha256,
            "learner_manifest_sha256": code_sha256,
            "r8_manifest_sha256": input_sha256,
            "provider_config_sha256": input_binding.get("provider_config_sha256"),
            "model_config_sha256": file_sha256(Path(arguments.model_config_json)),
            "provider_identity": input_binding.get("provider_identity"),
            "launch_manifest_sha256": freeze_authorities[
                "launch_manifest_sha256"
            ],
            "execution_bindings_sha256": freeze_authorities[
                "execution_bindings_sha256"
            ],
            "requested_output_root": freeze_authorities["requested_output_root"],
        }
        _write_or_validate(
            output_root
            / ("formal-provenance.json" if expected_formal else "nonformal-provenance.json"),
            provenance,
        )
    except (OSError, SuccessorLaunchError, runner_module.V023TwoRouteSourceTrainingRunnerError) as error:
        print(f"SUCCESSOR_FORMAL_RUN_FAIL: {error}", file=sys.stderr)
        return 3
    label = "SUCCESSOR_FORMAL_RUN_COMPLETE" if not arguments.nonformal else "SUCCESSOR_NONFORMAL_RUN_COMPLETE"
    print(f"{label} output={output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
