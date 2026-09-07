#!/usr/bin/env python3
"""Run the sealed E1 train/validation ladder without opening test data."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (HERE, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_v03_e1_fresh_sources as sources  # noqa: E402
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairwiseConfig  # noqa: E402
from mcrl.env.action_contract import NUM_ACTIONS  # noqa: E402
from mcrl.runtime.ee_axis_e1_ladder import (  # noqa: E402
    E1LadderBatches,
    E1LadderSpec,
    learner_config_sha256,
    run_e1_validation_ladder,
)
from mcrl.runtime.ee_axis_opening_dataset import read_opening_dataset  # noqa: E402
from mcrl.runtime.ee_axis_opening_pairs import build_opening_route_batch  # noqa: E402
from mcrl.runtime.ee_axis_state import EE_AXIS_STATE_DIM  # noqa: E402
from mcrl.runtime.ee_axis_temporal_dataset import read_temporal_dataset  # noqa: E402
from mcrl.runtime.ee_axis_temporal_pairs import build_temporal_route_batch  # noqa: E402


LADDER_AUTHORITY_SCHEMA = "multi-catfish-mcrl-v03-e1-ladder-authority-v1"
LADDER_RESULT_SCHEMA = "multi-catfish-mcrl-v03-e1-ladder-result-v1"
LADDER_RESULT_SEAL_SCHEMA = "multi-catfish-mcrl-v03-e1-ladder-result-seal-v1"
CLAIM_CEILING = "NO_EE_INSTRUMENT_VALIDITY_ONLY"


class E1ValidationLadderDriverError(RuntimeError):
    """The sealed train/validation-only ladder boundary was violated."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _training_code_manifest() -> dict[str, Any]:
    paths = (
        Path(__file__),
        REPO / "src" / "mcrl" / "algorithms" / "ee_axis_pairwise.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_e1_ladder.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_instrument_validity.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_opening_pairs.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_temporal_pairs.py",
        REPO / "src" / "mcrl" / "runtime" / "q_network.py",
        REPO / "src" / "mcrl" / "runtime" / "finiteness.py",
    )
    if any(not path.is_file() for path in paths):
        raise E1ValidationLadderDriverError("ladder code closure is incomplete")
    rows = [
        {
            "path": str(path.resolve().relative_to(REPO.resolve())),
            "sha256": _sha256_file(path),
        }
        for path in sorted(paths, key=lambda value: str(value))
    ]
    body = {
        "schema": "multi-catfish-mcrl-v03-e1-ladder-code-manifest-v1",
        "files": rows,
    }
    return {**body, "manifest_sha256": sources._canonical_sha256(body)}


def _config_from_prereg(prereg: dict[str, Any]) -> EEAxisPairwiseConfig:
    learner = prereg.get("learner")
    if not isinstance(learner, dict):
        raise E1ValidationLadderDriverError("E1 prereg lacks learner contract")
    try:
        config = EEAxisPairwiseConfig(
            state_dim=EE_AXIS_STATE_DIM,
            action_dim=NUM_ACTIONS,
            hidden_layers=tuple(int(value) for value in learner["hidden_layers"]),
            activation=str(learner["activation"]),
            learning_rate=float.fromhex(learner["learning_rate_hex"]),
            kappa_bits=float.fromhex(learner["kappa_bits_hex"]),
            beta=float.fromhex(learner["beta_hex"]),
            loss_weights=tuple(
                float.fromhex(value) for value in learner["loss_weights_hex"]
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise E1ValidationLadderDriverError("E1 learner contract is malformed") from error
    expected = sources._learner_contract(
        checkpoint_sha256=prereg["checkpoint_sha256"]
    )
    if learner != expected:
        raise E1ValidationLadderDriverError("E1 learner contract changed after sealing")
    return config


def _canonical_dataset_path(*, data_root: Path, raw: object, expected: str) -> Path:
    """Resolve one sealed dataset basename without traversal or symlinks."""

    if type(raw) is not str or raw != expected:
        raise E1ValidationLadderDriverError("ladder dataset path changed")
    path = data_root / raw
    if path.is_symlink() or not path.is_file():
        raise E1ValidationLadderDriverError(
            "ladder dataset path is missing, non-regular, or a symlink"
        )
    try:
        if path.resolve(strict=True).parent != data_root.resolve(strict=True):
            raise E1ValidationLadderDriverError("ladder dataset resolved outside source-data")
    except OSError as error:
        raise E1ValidationLadderDriverError("ladder dataset path cannot be resolved") from error
    return path


def _checkpoint_file_receipt(
    *, run_root: Path, spec: E1LadderSpec, selected_rung: int
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """Bind every sealed rung file and the three selected checkpoints."""

    checkpoint_root = run_root / "checkpoints"
    if checkpoint_root.is_symlink() or not checkpoint_root.is_dir():
        raise E1ValidationLadderDriverError(
            "E1 checkpoint root must be a regular directory"
        )
    expected = {
        f"init-{seed}-rung-{rung:06d}.pt"
        for seed in spec.initialization_seeds
        for rung in spec.update_rungs
    }
    actual = {path.name for path in checkpoint_root.iterdir()}
    if actual != expected:
        raise E1ValidationLadderDriverError(
            "E1 checkpoint files are missing or contain unexpected entries"
        )
    digests: dict[str, str] = {}
    for filename in sorted(expected):
        path = checkpoint_root / filename
        if path.is_symlink() or not path.is_file():
            raise E1ValidationLadderDriverError(
                f"E1 checkpoint is non-regular: {filename}"
            )
        digests[filename] = _sha256_file(path)
    selected = {
        str(seed): {
            "path": f"checkpoints/init-{seed}-rung-{selected_rung:06d}.pt",
            "file_sha256": digests[
                f"init-{seed}-rung-{selected_rung:06d}.pt"
            ],
        }
        for seed in spec.initialization_seeds
    }
    return digests, selected


def _load_ladder_batches(
    *,
    source_root: Path,
    prereg: dict[str, Any],
    config: EEAxisPairwiseConfig,
    expected_source_receipt_sha256: str,
) -> tuple[E1LadderBatches, dict[str, Any]]:
    if source_root.is_symlink() or not source_root.is_dir():
        raise E1ValidationLadderDriverError(
            "E1 source root must be a regular directory, not a symlink"
        )
    data_root = source_root / "source-data"
    if data_root.is_symlink() or not data_root.is_dir():
        raise E1ValidationLadderDriverError(
            "E1 source-data must be a regular directory, not a symlink"
        )
    index_path = data_root / "ladder-index.json"
    index = sources._read_canonical_json(index_path)
    if index.get("schema") != "multi-catfish-mcrl-v03-e1-ladder-source-index-v1":
        raise E1ValidationLadderDriverError("ladder source index schema is stale")
    if index.get("test_split_opened") is not False:
        raise E1ValidationLadderDriverError("ladder source index claims test was opened")
    expected_split = {
        str(seed): split
        for seed, split in sorted(sources.SOURCE_SEED_SPLIT.items())
        if split in {"train", "validation"}
    }
    if index.get("seed_split") != expected_split:
        raise E1ValidationLadderDriverError("ladder index contains test or wrong seeds")
    if index.get("source_manifest_sha256") != prereg["source_manifest_sha256"]:
        raise E1ValidationLadderDriverError("ladder index source manifest changed")
    if index.get("checkpoint_sha256") != prereg["checkpoint_sha256"]:
        raise E1ValidationLadderDriverError("ladder index checkpoint changed")
    dataset_rows = index.get("datasets")
    if not isinstance(dataset_rows, dict) or set(dataset_rows) != set(expected_split):
        raise E1ValidationLadderDriverError("ladder index datasets are incomplete")
    receipt_path = data_root / "receipt.json"
    expected_receipt_sha256 = sources._digest(
        expected_source_receipt_sha256,
        field="expected_source_receipt_sha256",
    )
    if _sha256_file(receipt_path) != expected_receipt_sha256:
        raise E1ValidationLadderDriverError(
            "source receipt differs from the externally captured generation digest"
        )
    receipt = sources._read_canonical_json(receipt_path)
    try:
        authenticated_index = sources._validate_published_index(
            data_root=data_root,
            prereg=prereg,
            receipt=receipt,
            kind="ladder",
        )
    except sources.E1FreshSourceError as error:
        raise E1ValidationLadderDriverError(
            "ladder index is not authenticated by the source receipt"
        ) from error
    if authenticated_index != index:
        raise E1ValidationLadderDriverError("ladder index changed during authentication")

    opening_by_split: dict[str, dict[str, list[Any]]] = {
        "train": {"C1": [], "C3": []},
        "validation": {"C1": [], "C3": []},
    }
    temporal_by_split: dict[str, list[Any]] = {"train": [], "validation": []}
    opened_paths: list[str] = []
    lambda_values: set[float] = set()
    for seed_text, split in expected_split.items():
        entry = dataset_rows[seed_text]
        if not isinstance(entry, dict):
            raise E1ValidationLadderDriverError("ladder dataset entry is malformed")
        seed = int(seed_text)
        opening_path = _canonical_dataset_path(
            data_root=data_root,
            raw=entry.get("opening_path"),
            expected=f"opening-{seed}.json",
        )
        temporal_path = _canonical_dataset_path(
            data_root=data_root,
            raw=entry.get("temporal_path"),
            expected=f"temporal-{seed}.json",
        )
        opening = read_opening_dataset(opening_path)
        temporal = read_temporal_dataset(temporal_path)
        opened_paths.extend([opening_path.name, temporal_path.name])
        if opening.verify() != entry["opening_dataset_sha256"]:
            raise E1ValidationLadderDriverError("ladder opening dataset digest changed")
        if temporal.verify() != entry["temporal_dataset_sha256"]:
            raise E1ValidationLadderDriverError("ladder temporal dataset digest changed")
        if (
            opening.source_manifest_sha256 != prereg["source_manifest_sha256"]
            or temporal.source_manifest_sha256 != prereg["source_manifest_sha256"]
            or opening.checkpoint_sha256 != prereg["checkpoint_sha256"]
            or temporal.checkpoint_sha256 != prereg["checkpoint_sha256"]
        ):
            raise E1ValidationLadderDriverError("ladder dataset lineage changed")
        opening_by_split[split]["C1"].extend(opening.c1_pairs)
        opening_by_split[split]["C3"].extend(opening.c3_pairs)
        temporal_by_split[split].extend(temporal.rows)
        lambda_values.add(float(opening.rows[0].raw_pair.lambda_bits_per_j))
        lambda_values.add(float(temporal.lambda_bits_per_j))
    if len(lambda_values) != 1:
        raise E1ValidationLadderDriverError("ladder datasets mix lambda0")
    sealed_lambda = float.fromhex(prereg["learner"]["lambda_bits_per_j_hex"])
    if next(iter(lambda_values)) != sealed_lambda:
        raise E1ValidationLadderDriverError("ladder source lambda0 changed")

    train_c1 = build_opening_route_batch(opening_by_split["train"]["C1"])
    train_c2 = build_temporal_route_batch(temporal_by_split["train"])
    train_c3 = build_opening_route_batch(opening_by_split["train"]["C3"])
    validation_c1 = build_opening_route_batch(opening_by_split["validation"]["C1"])
    validation_c2 = build_temporal_route_batch(temporal_by_split["validation"])
    validation_c3 = build_opening_route_batch(opening_by_split["validation"]["C3"])
    batches = E1LadderBatches(
        train=(train_c1.pair_batch, train_c2.pair_batch, train_c3.pair_batch),
        validation=(
            validation_c1.pair_batch,
            validation_c2.pair_batch,
            validation_c3.pair_batch,
        ),
    )
    batches.verify(config)
    return batches, {
        "ladder_index_file_sha256": _sha256_file(index_path),
        "source_receipt_file_sha256": expected_receipt_sha256,
        "opened_dataset_paths": opened_paths,
        "test_dataset_paths_opened": [],
        "test_split_opened": False,
    }


def run(
    *,
    source_root: Path,
    output_dir: Path,
    device: str,
    expected_source_receipt_sha256: str,
) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite E1 ladder authority: {output_dir}")
    if device != "cpu":
        raise E1ValidationLadderDriverError(
            "claim-bearing E1 ladder is sealed to deterministic CPU execution"
        )
    _manifest, prereg, _schedule_seals = sources._load_authority(source_root)
    config = _config_from_prereg(prereg)
    batches, access_receipt = _load_ladder_batches(
        source_root=source_root,
        prereg=prereg,
        config=config,
        expected_source_receipt_sha256=expected_source_receipt_sha256,
    )
    code_manifest = _training_code_manifest()
    batch_digests = batches.digests()
    train_source_seeds = tuple(
        seed
        for seed, split in sorted(sources.SOURCE_SEED_SPLIT.items())
        if split == "train"
    )
    validation_source_seeds = tuple(
        seed
        for seed, split in sorted(sources.SOURCE_SEED_SPLIT.items())
        if split == "validation"
    )
    spec = E1LadderSpec(
        run_id="multi-catfish-v03-e1-validation-ladder-20260901",
        initialization_seeds=tuple(prereg["initialization_seeds"]),
        source_prereg_sha256=prereg["prereg_sha256"],
        source_manifest_sha256=prereg["source_manifest_sha256"],
        checkpoint_sha256=prereg["checkpoint_sha256"],
        source_receipt_file_sha256=access_receipt[
            "source_receipt_file_sha256"
        ],
        ladder_index_file_sha256=access_receipt["ladder_index_file_sha256"],
        learner_config_sha256=learner_config_sha256(config),
        train_source_seeds=train_source_seeds,
        validation_source_seeds=validation_source_seeds,
        train_batch_sha256s=tuple(
            batch_digests["train"][route] for route in ("C1", "C2", "C3")
        ),
        validation_batch_sha256s=tuple(
            batch_digests["validation"][route]
            for route in ("C1", "C2", "C3")
        ),
        update_rungs=tuple(prereg["update_rungs_per_head"]),
    )
    spec.verify()
    output_dir.mkdir(parents=True, exist_ok=False)
    authority = {
        "schema": LADDER_AUTHORITY_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "source_prereg_sha256": prereg["prereg_sha256"],
        "source_manifest_sha256": prereg["source_manifest_sha256"],
        "ladder_code_manifest": code_manifest,
        "ladder_spec": asdict(spec),
        "learner_config": asdict(config),
        "batch_digests": batch_digests,
        "source_access_receipt": access_receipt,
        "execution_device": "cpu",
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    authority["authority_sha256"] = sources._canonical_sha256(authority)
    sources._write_once_json(output_dir / "authority.json", authority)
    result = run_e1_validation_ladder(
        config=config,
        batches=batches,
        spec=spec,
        output_dir=output_dir / "run",
        device=device,
    )
    if _training_code_manifest() != code_manifest:
        raise E1ValidationLadderDriverError("ladder code changed while training")
    checkpoint_digests, selected_checkpoints = _checkpoint_file_receipt(
        run_root=output_dir / "run",
        spec=spec,
        selected_rung=int(result["selected_common_rung"]),
    )
    final = {
        "schema": LADDER_RESULT_SCHEMA,
        "status": "PASS_VALIDATION_SELECTION_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "authority_sha256": authority["authority_sha256"],
        "selected_common_rung": result["selected_common_rung"],
        "checkpoint_file_sha256s": checkpoint_digests,
        "selected_checkpoint_files": selected_checkpoints,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "run_status_file_sha256": _sha256_file(output_dir / "run" / "status.json"),
    }
    result_file_sha256 = sources._write_once_json(output_dir / "result.json", final)
    result_seal = {
        "schema": LADDER_RESULT_SEAL_SCHEMA,
        "result_file_sha256": result_file_sha256,
        "authority_sha256": authority["authority_sha256"],
    }
    result_seal_file_sha256 = sources._write_once_json(
        output_dir / "result-seal.json", result_seal
    )
    return {
        **final,
        "result_file_sha256": result_file_sha256,
        "result_seal_file_sha256": result_seal_file_sha256,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=REPO / "artifacts" / "multi-catfish-v03-e1-instrument-validity-20260901",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--expected-source-receipt-sha256", required=True)
    parser.add_argument("--device", choices=("cpu",), default="cpu")
    args = parser.parse_args(argv)
    output = args.output_dir or args.source_root / "ladder-authority"
    payload = run(
        source_root=args.source_root,
        output_dir=output,
        device=args.device,
        expected_source_receipt_sha256=args.expected_source_receipt_sha256,
    )
    print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
