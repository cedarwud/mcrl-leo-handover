#!/usr/bin/env python3
"""Produce or independently verify the target-free C2-k1 state sidecar.

This command never reads T1 source rows.  It authenticates PREPARE_LIVE,
replays frozen Main to each sealed opening anchor, encodes the common 228-D
predecision state, and stops before any counterfactual branch or optimizer.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_v04_c3_state import (  # noqa: E402
    encode_ee_axis_v04_c3_state,
)
from mcrl.runtime.ee_axis_v06_c2_k1_q13 import (  # noqa: E402
    q13_surfaces_without_q2,
)
from mcrl.runtime.ee_axis_v06_c2_k1_state_authority import (  # noqa: E402
    C2K1StateAuthorityError,
    build_state_sidecar,
    canonical_sha256,
    capture_code_authority,
    file_sha256,
    live_verification_receipt,
    live_verification_seal,
    read_exact_json,
    sidecar_seal,
    verify_formal_prepare_files,
    verify_sidecar_file_seal,
    verify_state_sidecar,
    write_once_json,
)


class StateAuthorityRunnerError(RuntimeError):
    """The production replay cannot authenticate the requested authority."""


def _load_t1_runner() -> Any:
    path = HERE / "run_v06_c2_k1_t1.py"
    name = "v06_c2_k1_t1_for_state_" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise StateAuthorityRunnerError("cannot load frozen T1 runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _load_simulator_baseline_helper() -> Any:
    path = HERE / "v06_c2_k1_simulator_baseline.py"
    name = "v06_c2_k1_baseline_for_state_" + hashlib.sha256(
        path.read_bytes()
    ).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise StateAuthorityRunnerError("cannot load simulator baseline verifier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _learner_extension_sha256() -> dict[str, str]:
    helper = _load_simulator_baseline_helper()
    return {
        path: file_sha256(REPO / path)
        for path in helper.LEARNER_EXTENSION_PATHS
    }


def _code_authority() -> dict[str, Any]:
    return capture_code_authority(
        {
            "state_runner": Path(__file__).resolve(),
            "state_authority": REPO
            / "src/mcrl/runtime/ee_axis_v06_c2_k1_state_authority.py",
            "state_encoder": REPO / "src/mcrl/runtime/ee_axis_state.py",
            "c3_state_encoder": REPO / "src/mcrl/runtime/ee_axis_v04_c3_state.py",
            "q13_without_q2": REPO
            / "src/mcrl/runtime/ee_axis_v06_c2_k1_q13.py",
            "t1_runner": HERE / "run_v06_c2_k1_t1.py",
            "live_adapter": HERE / "v06_c2_k1_live_adapter.py",
            "v06_runtime": REPO / "src/mcrl/runtime/ee_axis_v06_c2_k1.py",
            "q2_only_trainer": REPO
            / "src/mcrl/algorithms/ee_axis_v06_c2_k1.py",
            "learner_data": REPO
            / "src/mcrl/runtime/ee_axis_v06_c2_k1_learner.py",
            "learner_contract": REPO
            / "src/mcrl/runtime/ee_axis_v06_c2_k1_learner_contract_v2.py",
            "learner_prep": REPO
            / "src/mcrl/runtime/ee_axis_v06_c2_k1_learner_prep.py",
            "formal_verdict_writer": REPO
            / "src/mcrl/runtime/ee_axis_v06_c2_k1_formal_verdict_writer.py",
            "simulator_baseline_helper": HERE
            / "v06_c2_k1_simulator_baseline.py",
        }
    )


def _candidate_mapping(observation: Any, *, focal: int) -> tuple[Any, ...]:
    candidates = getattr(observation, "candidates", None)
    tables = tuple(getattr(candidates, "slot_tables", ()))
    if not 0 <= focal < len(tables):
        raise StateAuthorityRunnerError("focal user is outside live slot tables")
    table = tables[focal]
    norads = np.asarray(getattr(table, "norad_ids", None))
    cells = np.asarray(getattr(table, "cell_ids", None))
    mask = np.asarray(getattr(table, "mask", None))
    if (
        norads.shape != (28,)
        or cells.shape != (28,)
        or mask.shape != (28,)
        or mask.dtype != np.bool_
    ):
        raise StateAuthorityRunnerError("live focal slot table is malformed")
    return tuple((int(norads[action]), int(cells[action])) for action in range(28))


def _capture_states(
    *,
    authority: Mapping[str, Any],
    tle_root: Path,
    simulator_prereg: Path,
    main_dir: Path,
    gate_dir: Path,
    q13_source_dir: Path,
    v03_root: Path,
    simulator_baseline: Path,
    simulator_baseline_seal: Path,
) -> dict[str, dict[str, Any]]:
    """Replay all twelve anchors without opening a counterfactual outcome."""

    t1 = _load_t1_runner()
    prepare = authority["prepare"]
    # Reuse the source runner's exact current-file and PREPARE seal checks in
    # addition to this command's independent exact-schema verifier.
    formal = t1._read_formal_prepare(
        Path(authority["prepare_path"]), Path(authority["t1_prereg_path"])
    )
    if formal != prepare:
        raise StateAuthorityRunnerError("T1 and state verifiers disagree on PREPARE")
    support = t1._support_census_loader()
    baseline = _load_simulator_baseline_helper()
    baseline_receipt = baseline.verify_baseline_extension(
        support=support,
        prepare_path=Path(authority["prepare_path"]),
        baseline_path=Path(simulator_baseline),
        baseline_seal_path=Path(simulator_baseline_seal),
        expected_extension_sha256=_learner_extension_sha256(),
    )
    simulator_manifest_sha = baseline_receipt[
        "simulator_source_manifest_sha256"
    ]
    if simulator_manifest_sha != prepare["simulator_source_manifest_sha256"]:
        raise StateAuthorityRunnerError("simulator baseline disagrees with PREPARE")
    if file_sha256(simulator_prereg) != prepare["simulator_prereg_file_sha256"]:
        raise StateAuthorityRunnerError("current simulator prereg drifted")
    live = t1._live_adapter_loader()
    captured: dict[str, dict[str, Any]] = {}
    with live.authenticated_runtime(
        tle_root=Path(tle_root),
        prereg_path=Path(simulator_prereg),
        main_dir=Path(main_dir),
        gate_dir=Path(gate_dir),
        source_dir=Path(q13_source_dir),
        v03_root=Path(v03_root),
    ) as runtime:
        if runtime.checkpoint_sha256 != prepare["main_checkpoint_sha256"]:
            raise StateAuthorityRunnerError("loaded Main checkpoint drifted")
        if runtime.prereg_file_sha256 != prepare["simulator_prereg_file_sha256"]:
            raise StateAuthorityRunnerError("loaded simulator prereg drifted")
        if (
            runtime.q13_gate_source_manifest_sha256
            != prepare["q13_gate_source_manifest_sha256"]
        ):
            raise StateAuthorityRunnerError("loaded Q13 gate authority drifted")
        expected_hybrid_hashes = {
            lineage: {
                cell[lineage]["hybrid_sha256"]
                for cell in prepare["lineage_bindings"].values()
            }
            for lineage in ("q13-a", "q13-b", "q13-c")
        }
        if any(len(values) != 1 for values in expected_hybrid_hashes.values()):
            raise StateAuthorityRunnerError(
                "PREPARE hybrid authority is inconsistent"
            )
        if runtime.hybrid_hashes != {
            lineage: next(iter(values))
            for lineage, values in expected_hybrid_hashes.items()
        }:
            raise StateAuthorityRunnerError(
                "loaded selected hybrid digests drifted from PREPARE"
            )
        for anchor in prepare["anchors"]:
            key = (
                f"{anchor['pool']}:{anchor['world_id']}:{anchor['step']}:"
                f"{anchor['focal_user']}"
            )
            seed = int(anchor["world_id"])
            field = t1._physical_world_field(
                checkpoint_sha256=runtime.checkpoint_sha256,
                source_manifest_sha256=simulator_manifest_sha,
                simulator_prereg_file_sha256=runtime.prereg_file_sha256,
                source_seed=seed,
            )
            wrapped, history, observation = live.replay_main_to_anchor(
                runtime,
                runtime.archive,
                runtime.trainer,
                source_seed=seed,
                target_step=int(anchor["step"]),
                field=field,
            )
            if int(observation.step_index) != int(anchor["step"]):
                raise StateAuthorityRunnerError(f"live step drifted for {key}")
            reference = np.asarray(history[-1], dtype=np.int64)
            focal = int(anchor["focal_user"])
            if reference.shape != (100,) or int(reference[focal]) != int(
                anchor["reference_action"]
            ):
                raise StateAuthorityRunnerError(f"live Main reference drifted for {key}")
            mapping = _candidate_mapping(observation, focal=focal)
            reference_action = int(anchor["reference_action"])
            if list(mapping[reference_action]) != anchor["reference_physical_key"]:
                raise StateAuthorityRunnerError(
                    f"live reference physical identity drifted for {key}"
                )
            for action, expected in zip(
                anchor["candidate_actions"],
                anchor["candidate_physical_keys"],
                strict=True,
            ):
                if list(mapping[int(action)]) != expected:
                    raise StateAuthorityRunnerError(
                        f"live candidate physical identity drifted for {key}/{action}"
                    )
            environment = getattr(wrapped, "environment", wrapped)
            encoded = encode_ee_axis_state(environment, observation)
            encoded.verify()
            state = np.asarray(encoded.state_matrix[focal], dtype=np.float32)
            mask = np.asarray(encoded.action_masks[focal])
            if mask.tolist() != anchor["legal_action_mask"]:
                raise StateAuthorityRunnerError(f"live action mask drifted for {key}")
            cell = prepare["lineage_bindings"][key]
            crn_values = {item["crn_sha256"] for item in cell.values()}
            if crn_values != {field.root_digest}:
                raise StateAuthorityRunnerError(f"live CRN root drifted for {key}")
            # Before any DESIGN-EVAL seed can be opened, independently prove
            # that the exact DROP_C2 deployment seam still reproduces all 36
            # target-free PREPARE Q1+Q3 surfaces/actions.  This dedicated
            # path never invokes the resident legacy Q2 network.
            c3 = encode_ee_axis_v04_c3_state(
                environment,
                observation,
                interval_s=float(t1.T1_FORMULA_CONTRACT["interval_s"]),
                kappa_bits=float(t1.KAPPA_BITS),
            )
            for lineage in ("q13-a", "q13-b", "q13-c"):
                q1, q3, q13_masks = q13_surfaces_without_q2(
                    runtime.hybrids[lineage],
                    encoded.state_matrix,
                    c3.state_matrix,
                    np.asarray(observation.masks),
                )
                focal_mask = np.asarray(q13_masks[focal])
                if not np.array_equal(focal_mask, mask):
                    raise StateAuthorityRunnerError(
                        f"DROP_C2 mask drifted for {key}/{lineage}"
                    )
                scores = np.asarray(q1[focal] + q3[focal], dtype=np.float64)
                binding = cell[lineage]
                sealed_scores = np.asarray(
                    binding["q13_score_vector"], dtype=np.float64
                )
                if not np.array_equal(scores, sealed_scores):
                    raise StateAuthorityRunnerError(
                        f"DROP_C2 Q1+Q3 surface drifted for {key}/{lineage}"
                    )
                action = min(
                    range(28), key=lambda candidate: (-float(scores[candidate]), candidate)
                )
                if action != int(binding["a_D"]):
                    raise StateAuthorityRunnerError(
                        f"DROP_C2 action drifted for {key}/{lineage}"
                    )
            captured[key] = {
                "state": state,
                "action_mask": mask,
                "crn_sha256": field.root_digest,
                "all_user_encoder_sha256": encoded.state_sha256,
                "main_reference_vector_sha256": canonical_sha256(
                    {"users": 100, "actions": reference.tolist()}
                ),
            }
    return captured


def _authority_from_args(args: argparse.Namespace) -> dict[str, Any]:
    authority = verify_formal_prepare_files(
        prepare_path=args.prepare,
        prepare_seal_path=args.prepare_seal,
        t1_prereg_path=args.t1_prereg,
    )
    return authority | {
        "prepare_path": str(Path(args.prepare).resolve()),
        "t1_prereg_path": str(Path(args.t1_prereg).resolve()),
    }


def _refuse_output_dir(path: Path) -> None:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise StateAuthorityRunnerError(f"refusing to overwrite output dir: {destination}")


def _common_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prepare", type=Path, required=True)
    parser.add_argument("--prepare-seal", type=Path, required=True)
    parser.add_argument("--t1-prereg", type=Path, required=True)
    parser.add_argument("--learner-prereg", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--simulator-prereg", type=Path, required=True)
    parser.add_argument("--main-dir", type=Path, required=True)
    parser.add_argument("--gate-dir", type=Path, required=True)
    parser.add_argument("--q13-source-dir", type=Path, required=True)
    parser.add_argument("--v03-root", type=Path, required=True)
    parser.add_argument("--simulator-baseline", type=Path, required=True)
    parser.add_argument("--simulator-baseline-seal", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture = subparsers.add_parser("capture")
    _common_runtime_args(capture)
    verify = subparsers.add_parser("verify-live")
    _common_runtime_args(verify)
    verify.add_argument("--sidecar", type=Path, required=True)
    verify.add_argument("--sidecar-seal", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        _refuse_output_dir(args.output_dir)
        authority = _authority_from_args(args)
        learner_sha = file_sha256(args.learner_prereg)
        code = _code_authority()
        captures = _capture_states(
            authority=authority,
            tle_root=args.tle_root,
            simulator_prereg=args.simulator_prereg,
            main_dir=args.main_dir,
            gate_dir=args.gate_dir,
            q13_source_dir=args.q13_source_dir,
            v03_root=args.v03_root,
            simulator_baseline=args.simulator_baseline,
            simulator_baseline_seal=args.simulator_baseline_seal,
        )
        if args.command == "capture":
            sidecar = build_state_sidecar(
                authority=authority,
                learner_prereg_file_sha256=learner_sha,
                code_authority=code,
                captures=captures,
            )
            sidecar_path = args.output_dir / "state-sidecar.json"
            seal_path = args.output_dir / "state-sidecar-seal.json"
            write_once_json(sidecar_path, sidecar)
            write_once_json(seal_path, sidecar_seal(sidecar, sidecar_path=sidecar_path))
            print(
                json.dumps(
                    {
                        "status": "STATE_SIDECAR_CAPTURED_TARGET_FREE",
                        "anchors": 12,
                        "sidecar_sha256": sidecar["sidecar_sha256"],
                        "training": False,
                    },
                    sort_keys=True,
                )
            )
            return 0
        sidecar = read_exact_json(args.sidecar)
        verify_state_sidecar(
            sidecar,
            authority=authority,
            learner_prereg_file_sha256=learner_sha,
            code_authority=code,
            live_captures=captures,
        )
        verify_sidecar_file_seal(
            sidecar=sidecar,
            sidecar_path=args.sidecar,
            seal_path=args.sidecar_seal,
        )
        receipt = live_verification_receipt(
            sidecar=sidecar,
            sidecar_path=args.sidecar,
            sidecar_seal_path=args.sidecar_seal,
        )
        receipt_path = args.output_dir / "state-live-verification.json"
        seal_path = args.output_dir / "state-live-verification-seal.json"
        write_once_json(receipt_path, receipt)
        write_once_json(
            seal_path,
            live_verification_seal(receipt, receipt_path=receipt_path),
        )
        print(
            json.dumps(
                {
                    "status": "STATE_SIDECAR_LIVE_REPLAY_VERIFIED",
                    "anchors": 12,
                    "verification_sha256": receipt["verification_sha256"],
                    "training": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except (C2K1StateAuthorityError, StateAuthorityRunnerError, ValueError) as error:
        print(json.dumps({"status": "INVALID_NO_TRAINING", "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
