#!/usr/bin/env python3
"""Run the frozen two-route runner while preserving all 200 update receipts."""

from __future__ import annotations

import argparse
import importlib
import math
from pathlib import Path
import sys

from successor_launch_common import (
    ARM_ORDER, CLAIM_CEILING, ROUTE_ORDER, RUNNER_REL, SOURCE_MAP,
    SuccessorLaunchError, canonical_bytes, read_canonical_json, write_once,
)


SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-update-ledger-v1"


def _finite(value: object, *, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise SuccessorLaunchError(f"{field} is not numeric") from error
    if not math.isfinite(number):
        raise SuccessorLaunchError(f"{field} is not finite")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--epochs", required=True, type=int)
    parser.add_argument("--provider-factory", required=True)
    parser.add_argument("--model-config-json", required=True)
    parser.add_argument("--train-seed", required=True, type=int)
    parser.add_argument("--authority-sha256")
    parser.add_argument("--code-sha256")
    parser.add_argument("--input-sha256")
    parser.add_argument("--preflight-receipt", required=True, type=Path)
    parser.add_argument("--execute", action="store_true", required=True)
    arguments = parser.parse_args(argv)
    repo = Path(__file__).resolve().parents[2]
    for path in (repo / "src", repo / RUNNER_REL):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    runner_module = importlib.import_module("v023_two_route_source_training_runner")
    preflight = read_canonical_json(arguments.preflight_receipt, field="preflight receipt")
    if preflight.get("status") != "PASS_FROZEN_C1C2_SUCCESSOR_PREFLIGHT":
        parser.error("preflight receipt does not bind the requested formal run")
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
        parser.error("explicit digest disagrees with the preflight receipt")
    namespace = argparse.Namespace(
        output_root=str(arguments.output_root), epochs=arguments.epochs,
        provider_factory=arguments.provider_factory,
        model_config_json=arguments.model_config_json,
        train_seed=arguments.train_seed,
        authority_sha256=authority_sha256,
        code_sha256=code_sha256,
        input_sha256=input_sha256, execute=arguments.execute,
    )
    try:
        runner = runner_module.preflight_from_args(namespace)
        runner.begin_new(arguments.output_root)
        rows = []
        for cursor in range(200):
            receipt = runner.orchestrator.advance()
            expected_route = ROUTE_ORDER[cursor % 2]
            if receipt.update_cursor != cursor or receipt.route != expected_route:
                raise SuccessorLaunchError("runner update route order drifted")
            updates = []
            for update in receipt.arm_updates:
                if update.source != SOURCE_MAP[update.arm][update.route]:
                    raise SuccessorLaunchError("runner update source mapping drifted")
                values = {
                    key: _finite(value, field=f"update {cursor} {update.arm} {key}")
                    for key, value in update.update.items()
                    if isinstance(value, (int, float)) and not isinstance(value, bool)
                }
                if "loss" not in values:
                    raise SuccessorLaunchError("runner update has no finite loss")
                updates.append(
                    {
                        "arm": update.arm, "route": update.route,
                        "source": update.source, "file_id": update.file_id,
                        "metrics": values,
                    }
                )
            if [item["arm"] for item in updates] != list(ARM_ORDER):
                raise SuccessorLaunchError("runner update arm order drifted")
            rows.append(
                {
                    "update_cursor": cursor, "route": receipt.route,
                    "source_files": [list(item) for item in receipt.source_files],
                    "arm_updates": updates,
                }
            )
        if runner.completed_epochs != 100 or runner.orchestrator.next_route != "C1":
            raise SuccessorLaunchError("runner did not close at the epoch-100 boundary")
        ledger = {
            "schema": SCHEMA, "claim_ceiling": CLAIM_CEILING,
            "arm_order": list(ARM_ORDER), "route_order": list(ROUTE_ORDER),
            "completed_epochs": 100, "completed_updates": 200,
            "updates": rows,
        }
        write_once(arguments.output_root / "update-ledger.json", canonical_bytes(ledger))
        runner._write_checkpoint(100)
        runner._write_final_receipt()
    except (OSError, SuccessorLaunchError, runner_module.V023TwoRouteSourceTrainingRunnerError) as error:
        print(f"SUCCESSOR_FORMAL_RUN_FAIL: {error}", file=sys.stderr)
        return 3
    print(f"SUCCESSOR_FORMAL_RUN_COMPLETE output={arguments.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
