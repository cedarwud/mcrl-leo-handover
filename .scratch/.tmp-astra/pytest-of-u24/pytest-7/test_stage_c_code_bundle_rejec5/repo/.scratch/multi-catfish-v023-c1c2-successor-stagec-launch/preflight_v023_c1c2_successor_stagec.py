#!/usr/bin/env python3
"""Authenticate the formal Stage-C freeze without opening the output root."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import os
from pathlib import Path
import sys
from typing import Any, Mapping

import numpy as np

import stagec_common as common


PASS = "PASS_V023_C1C2_SUCCESSOR_STAGEC_PREFLIGHT"


def _reject_circular_digest(value: object, bindings_sha: str) -> None:
    def walk(child: object, key: str = "") -> None:
        normalized = key.lower().replace("-", "_")
        if normalized in {"self_sha256", "bindings_sha256", "execution_bindings_sha256"}:
            raise common.StageCError("execution bindings contain a circular self digest")
        if isinstance(child, Mapping):
            for nested_key, nested in child.items():
                walk(nested, str(nested_key))
        elif isinstance(child, (list, tuple)):
            for nested in child:
                walk(nested, key)
        elif isinstance(child, str) and child == bindings_sha:
            raise common.StageCError("execution bindings embed their own digest")
    walk(value)


def _import_from(path: Path) -> Any:
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    module = importlib.import_module(path.stem)
    if Path(module.__file__).resolve() != path.resolve():
        raise common.StageCError(f"module origin drifted: {path}")
    return module


def _baseline_invariance(bindings: Mapping[str, object]) -> dict[str, object]:
    baseline = bindings.get("baseline")
    if not isinstance(baseline, Mapping) or baseline.get("contract_fields_excluded") is not True:
        raise common.StageCError("BASELINE contract_fields_excluded binding is absent")
    checkpoint = Path(str(baseline.get("checkpoint_path")))
    status = Path(str(baseline.get("status_path")))
    module = _import_from(common.BASELINE / "baseline_adapter.py")
    excluded = getattr(module, "CONTRACT_FIELDS_EXCLUDED", None)
    loaded = module.BaselineAdapter.from_artifacts(checkpoint, status)
    if excluded is None:
        excluded = getattr(loaded, "contract_fields_excluded", None)
    binding_method = getattr(loaded, "binding", None)
    if excluded is None and callable(binding_method):
        adapter_binding = binding_method()
        if isinstance(adapter_binding, Mapping):
            excluded = adapter_binding.get("contract_fields_excluded")
    if excluded is not True:
        raise common.StageCError("loaded BASELINE adapter lacks contract_fields_excluded: true")
    before = common.file_sha256(checkpoint, field="BASELINE checkpoint")
    from mcrl.env.step_types import ActionMask, UserState

    access = np.zeros(28, dtype=np.float32)
    access[4] = 1.0
    state = UserState(
        access_vector=access,
        channel_quality=np.linspace(0.0, 2.0, 28, dtype=np.float32),
        beam_offsets=np.linspace(-0.2, 0.2, 28, dtype=np.float32),
        beam_loads=np.full(28, 4.0, dtype=np.float32),
    )
    mask = np.zeros(28, dtype=bool)
    mask[[0, 7, 19]] = True
    actions = loaded.select_actions([state, state], [ActionMask(mask=mask), ActionMask(mask=mask)])
    repeated = loaded.select_actions([state, state], [ActionMask(mask=mask), ActionMask(mask=mask)])
    if not np.array_equal(actions, repeated) or not all(mask[int(action)] for action in actions):
        raise common.StageCError("BASELINE deployment invariance/mask check failed")
    if common.file_sha256(checkpoint, field="BASELINE checkpoint") != before:
        raise common.StageCError("BASELINE bytes changed during invariance check")
    return {"checkpoint_sha256": before, "actions_sha256": hashlib.sha256(actions.tobytes()).hexdigest()}


def preflight(
    bindings_path: Path, *, admission_supplement: Path,
    acceptance_bundle: Path, output_override: Path | None = None,
) -> dict[str, object]:
    bindings = common.verify_bindings(bindings_path)
    supplement = common.verify_stage_ab_supplement(
        admission_supplement, bindings_path, bindings
    )
    acceptance = common.verify_acceptance_bundle(
        acceptance_bundle,
        {**bindings, "bindings_sha256": common.file_sha256(bindings_path)},
    )
    bindings = common.materialize_stage_ab(bindings, supplement)
    common.verify_runtime_identity(bindings)
    bindings_sha = common.file_sha256(bindings_path, field="execution bindings")
    _reject_circular_digest(bindings, bindings_sha)
    if bindings.get("trained_arms") != list(common.LEARNED_ARMS) or bindings.get("arms") != list(common.ARMS):
        raise common.StageCError("the four arms are not exactly FULL2, DROP_C1, DROP_C2, BASELINE")
    common.forbid_policy_tokens(
        {"arms": bindings["arms"], "trained_arms": bindings["trained_arms"]},
        field="bound arm topology",
    )
    stage_a = bindings.get("stage_a")
    if not isinstance(stage_a, Mapping):
        raise common.StageCError("Stage-A binding is missing")
    exports = stage_a.get("exports")
    if not isinstance(exports, list) or [entry.get("arm") for entry in exports if isinstance(entry, Mapping)] != list(common.LEARNED_ARMS):
        raise common.StageCError("Stage-A exports are not exactly the three learned arms")
    for entry in exports:
        if not isinstance(entry, Mapping):
            raise common.StageCError("malformed Stage-A export binding")
        path = Path(str(stage_a["root"])) / str(entry["path"])
        if common.file_sha256(path, field=f"{entry['arm']} export") != entry["sha256"]:
            raise common.StageCError(f"bound learned export drifted: {entry['arm']}")
    common.forbid_policy_tokens(exports, field="Stage-A export bindings")
    pass_receipt = stage_a.get("pass_receipt")
    if not isinstance(pass_receipt, Mapping):
        raise common.StageCError("Stage-A PASS receipt binding is missing")
    stage_a_root = Path(str(stage_a["root"]))
    if common.file_sha256(stage_a_root / str(pass_receipt.get("path")), field="Stage-A PASS receipt") != pass_receipt.get("sha256"):
        raise common.StageCError("Stage-A PASS receipt drifted")
    common.forbid_policy_tokens(
        common.read_json(stage_a_root / str(pass_receipt.get("path")), field="Stage-A PASS receipt"),
        field="Stage-A PASS receipt",
    )
    if common.file_sha256(stage_a_root / "MANIFEST.sha256", field="Stage-A manifest") != stage_a.get("manifest_sha256"):
        raise common.StageCError("Stage-A manifest drifted")
    code_sha, _entries = common.verify_code_manifest()
    code = bindings.get("code")
    if not isinstance(code, Mapping) or code.get("external_manifest_sha256") != code_sha:
        raise common.StageCError("bound code manifest drifted")
    plan_binding = bindings.get("world_plan")
    if not isinstance(plan_binding, Mapping):
        raise common.StageCError("world-plan binding is missing")
    plan_path = Path(str(plan_binding.get("path")))
    builder = _import_from(common.PHYSICAL / "build_v023_c1c2_successor_world_plan.py")
    if builder.read_world_plan(plan_path)["plan_sha256"] != common.PLAN_SHA256:
        raise common.StageCError("9000-world plan drifted")
    if common.file_sha256(plan_path, field="world plan") != plan_binding.get("file_sha256"):
        raise common.StageCError("world-plan file digest drifted")
    common.forbid_policy_tokens(builder.read_world_plan(plan_path), field="world plan")
    physical = bindings.get("physical_inputs")
    if not isinstance(physical, Mapping):
        raise common.StageCError("physical input bindings are missing")
    if common.file_sha256(physical.get("prereg_path"), field="PREREG") != physical.get("prereg_sha256"):
        raise common.StageCError("PREREG drifted")
    tle_rows, tle_sha = common.tree_manifest(Path(str(physical.get("tle_root"))))
    if tle_sha != physical.get("tle_manifest_sha256") or tle_rows != physical.get("tle_manifest"):
        raise common.StageCError("frozen TLE manifest drifted")
    configured_output = output_override
    if configured_output is None:
        configured = bindings.get("stage_c_output_root")
        if not isinstance(configured, str):
            # Version 1 stores absence authority in the caller/launcher; the
            # concrete preflight command must therefore provide the root.
            raise common.StageCError("Stage-C output root must be explicit")
        configured_output = Path(configured)
    if configured_output.exists() or configured_output.is_symlink():
        raise common.StageCError("Stage-C output root must be absent")
    baseline_check = _baseline_invariance(bindings)
    return {
        "schema": "multi-catfish-mcrl-v023-c1c2-successor-stagec-preflight-v1",
        "status": PASS,
        "formal": True,
        "bindings_path": str(bindings_path.resolve()),
        "bindings_sha256": bindings_sha,
        "plan_sha256": common.PLAN_SHA256,
        "arms": list(common.ARMS),
        "baseline_invariance": baseline_check,
        "output_root_absent": str(configured_output.resolve(strict=False)),
        "forbidden_topology_opened": False,
        "stage_ab_supplement_sha256": supplement["supplement_sha256"],
        "acceptance_evidence_sha256": acceptance["acceptance_bundle_sha256"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--admission-supplement", type=Path, required=True)
    parser.add_argument("--acceptance-bundle", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = preflight(
            args.bindings,
            admission_supplement=args.admission_supplement,
            acceptance_bundle=args.acceptance_bundle,
            output_override=args.output,
        )
        common.write_once(args.receipt, payload)
        common.write_digest_sidecar(args.receipt)
    except Exception as error:
        print(f"STAGEC_PREFLIGHT_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"{PASS} receipt={args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
