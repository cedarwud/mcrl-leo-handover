#!/usr/bin/env python3
"""Run the single pre-registered V0.4 C3 learnability gate.

This runner deliberately sits *after* the V0.4 source runner.  It consumes
only a completed and independently verified 4/3/0 source publication and a
sealed V0.3 masked-mean/max checkpoint set.  The validation byte boundary is
explicit: source receipts, schedule metadata, split membership, physical
keys, and the gate authority are sealed before this module opens any C3
dataset, in particular a validation dataset.

The gate trains one fresh local Q3 for each initialization and rung.  Q1 and
Q2 are loaded from the exact sealed V0.3 head-0/head-1 checkpoints and remain
frozen.  Every rung is saved and strictly reloaded.  After deterministic
rung selection, one exactly-three-network hybrid is saved and reloaded for
each initialization.  No TEST bytes, EE endpoint, episode trajectory, or
500-epoch screen is opened here.
"""

import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (HERE, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v04_c3_source as source_runner  # noqa: E402
from mcrl.algorithms.ee_axis_action_shared import (  # noqa: E402
    EEAxisActionSharedConfig,
)
from mcrl.algorithms.ee_axis_action_shared_meanmax import (  # noqa: E402
    EEAxisMaskedMeanMaxConfig,
)
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch  # noqa: E402
from mcrl.algorithms.ee_axis_v04_hybrid import (  # noqa: E402
    EEAxisV04HybridTrainer,
    FrozenMeanMaxCheckpointSpec,
)
from mcrl.errors import MCRLContractError  # noqa: E402
from mcrl.runtime.ee_axis_v04_c3_dataset import (  # noqa: E402
    V04C3OpeningDataset,
    read_v04_c3_dataset,
)
from mcrl.runtime.ee_axis_v04_c3_learnability import (  # noqa: E402
    C3V04BalancedGeneralization,
    C3V04LearnabilityMetricError,
    compute_anchor_seed_balanced_generalization,
)


# Frozen protocol ----------------------------------------------------------

GATE_SCHEMA = "multi-catfish-mcrl-v04-c3-learnability-gate-v1"
AUTHORITY_SCHEMA = "multi-catfish-mcrl-v04-c3-learnability-authority-v1"
AUTHORITY_SEAL_SCHEMA = (
    "multi-catfish-mcrl-v04-c3-learnability-authority-seal-v1"
)
RESULT_SCHEMA = "multi-catfish-mcrl-v04-c3-learnability-result-v1"
RESULT_SEAL_SCHEMA = "multi-catfish-mcrl-v04-c3-learnability-result-seal-v1"
Q3_CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v04-c3-q3-rung-checkpoint-v1"
HYBRID_CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v04-c3-hybrid-checkpoint-v1"

SUCCESS_STATUS = "GO_500EP_SCREEN_ONLY"
FAILURE_STATUS = "STOP_V04_C3"
CLAIM_CEILING = (
    "V04_C3_LEARNABILITY_ONLY_NO_TEST_NO_EE_NO_EPISODE_TRAINING"
)
SUCCESS_CLAIM_CEILING = (
    "V04_C3_LEARNABILITY_ONLY_AUTHORIZE_ONE_500EP_SCREEN_NO_TEST_NO_EE_CLAIM"
)

STATE_DIM = 228
ACTION_DIM = 28
HIDDEN_LAYERS = (100, 50, 50)
ACTIVATION = "tanh"
LEARNING_RATE = 0.001
KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")
BETA = 0.1
LOSS_WEIGHTS = (1.0, 1.0, 1.0)
UPDATE_RUNGS = (3, 10, 30, 100, 300)
INITIALIZATION_SEEDS = (2026092101, 2026092102, 2026092103)
TRAIN_SOURCE_SEEDS = (2026092301, 2026092302, 2026092303, 2026092304)
VALIDATION_SOURCE_SEEDS = (2026092305, 2026092306, 2026092307)
EXPECTED_SEED_SPLIT = {
    **{str(seed): "train" for seed in TRAIN_SOURCE_SEEDS},
    **{str(seed): "validation" for seed in VALIDATION_SOURCE_SEEDS},
}
EXPECTED_V03_AUTHORITY_SHA256 = (
    "71f339d840bf999642f9392baa0e0325459672419d5e5e21e2de0731ad2b1755"
)
EXPECTED_V03_RESULT_FILE_SHA256 = (
    "25069d5c546a892218949ebddcf77d15209f1c7e685dd9b2776c80003660021e"
)
EXPECTED_V03_RESULT_SEAL_FILE_SHA256 = (
    "aa44ddcb17376b7467d1ab090772adbe4c32a7d26dad64e802dcc7014171dcaf"
)
EXPECTED_V03_CHECKPOINT_SHA256 = {
    2026092101: (
        "f26aab2fab6d31d6f3e4acd97782beeb0bba055ec94611dc9f3ed47038a231f0"
    ),
    2026092102: (
        "6930534d90840807c4dda1eda9c0ecf58793175053a37a43b75e38a7b6d310ba"
    ),
    2026092103: (
        "507b871f2536097b400b099b9dcb666e8445e9aee921001d61e70ff6042646b2"
    ),
}

DEFAULT_SOURCE_DIR = (
    REPO / "artifacts" / "multi-catfish-v04-c3-source-20260901"
)
DEFAULT_V03_ROOT = (
    REPO / "artifacts" / "multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"
)
DEFAULT_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
DEFAULT_OUTPUT_DIR = (
    REPO / "artifacts" / "multi-catfish-v04-c3-learnability-20260901"
)


class C3V04LearnabilityGateError(RuntimeError):
    """A source, model, metric, or gate contract failed closed."""


def _canonical_bytes(payload: object) -> bytes:
    try:
        return (
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise C3V04LearnabilityGateError(
            "payload is not finite canonical JSON"
        ) from error


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)[:-1]).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C3V04LearnabilityGateError(f"{field} must be lowercase SHA-256")
    return value


def _file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise C3V04LearnabilityGateError(
            f"expected a regular non-symlink file: {source}"
        )
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_canonical_json(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise C3V04LearnabilityGateError(
            f"sealed JSON is missing or non-regular: {source}"
        )
    try:
        raw = source.read_bytes()
        payload = json.loads(raw.decode("ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise C3V04LearnabilityGateError(
            f"cannot read sealed canonical JSON: {source}"
        ) from error
    if not isinstance(payload, dict):
        raise C3V04LearnabilityGateError(
            f"sealed JSON must contain an object: {source}"
        )
    if raw != _canonical_bytes(payload):
        raise C3V04LearnabilityGateError(
            f"sealed JSON is not canonical: {source}"
        )
    return payload


def _write_once_json(path: Path, payload: object) -> str:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite sealed gate file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_bytes(payload)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            raise FileExistsError(
                f"refusing to overwrite sealed gate file: {destination}"
            )
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(encoded).hexdigest()


def _write_once_torch(path: Path, payload: Mapping[str, Any]) -> str:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite sealed checkpoint: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        torch.save(dict(payload), temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            raise FileExistsError(
                f"refusing to overwrite sealed checkpoint: {destination}"
            )
    finally:
        temporary.unlink(missing_ok=True)
    return _file_sha256(destination)


def _config_pair() -> tuple[
    EEAxisMaskedMeanMaxConfig, EEAxisActionSharedConfig
]:
    common = {
        "state_dim": STATE_DIM,
        "action_dim": ACTION_DIM,
        "hidden_layers": HIDDEN_LAYERS,
        "activation": ACTIVATION,
        "learning_rate": LEARNING_RATE,
        "kappa_bits": KAPPA_BITS,
        "beta": BETA,
        "loss_weights": LOSS_WEIGHTS,
    }
    return EEAxisMaskedMeanMaxConfig(**common), EEAxisActionSharedConfig(**common)


def _relative(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(Path(path).resolve())


def _gate_code_manifest() -> dict[str, str]:
    """Bind the exact gate, metric, learner, and source-verifier code."""

    paths = (
        Path(__file__),
        HERE / "run_v04_c3_source.py",
        REPO / "src/mcrl/algorithms/ee_axis_pairwise.py",
        REPO / "src/mcrl/algorithms/ee_axis_action_shared.py",
        REPO / "src/mcrl/algorithms/ee_axis_action_shared_meanmax.py",
        REPO / "src/mcrl/algorithms/ee_axis_v04_hybrid.py",
        REPO / "src/mcrl/runtime/ee_axis_v04_c3_dataset.py",
        REPO / "src/mcrl/runtime/ee_axis_v04_c3_learnability.py",
    )
    return {_relative(path): _file_sha256(path) for path in paths}


@dataclass(frozen=True)
class SourceAuthority:
    """Receipt metadata authenticated before validation bytes are opened."""

    source_dir: Path
    source_manifest_sha256: str
    source_manifest_file_sha256: str
    prereg_file_sha256: str
    prereg_digest: str
    ephemeris_file_set_sha256: str
    main_status_file_sha256: str
    main_episode_logs_file_sha256: str
    main_checkpoint_sha256: str
    smoke_receipt_file_sha256: str
    smoke_receipt_seal_file_sha256: str
    prepare_receipt_file_sha256: str
    prepare_receipt_seal_file_sha256: str
    schedule_sha256: str
    schedule_file_sha256: str
    generate_receipt_file_sha256: str
    generate_receipt_seal_file_sha256: str
    dataset_file_sha256s: Mapping[str, str]
    dataset_sha256s: Mapping[str, str]
    seed_split: Mapping[str, str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_dir": _relative(self.source_dir),
            "source_manifest_sha256": self.source_manifest_sha256,
            "source_manifest_file_sha256": self.source_manifest_file_sha256,
            "prereg_file_sha256": self.prereg_file_sha256,
            "prereg_digest": self.prereg_digest,
            "ephemeris_file_set_sha256": self.ephemeris_file_set_sha256,
            "main_status_file_sha256": self.main_status_file_sha256,
            "main_episode_logs_file_sha256": self.main_episode_logs_file_sha256,
            "main_checkpoint_sha256": self.main_checkpoint_sha256,
            "smoke_receipt_file_sha256": self.smoke_receipt_file_sha256,
            "smoke_receipt_seal_file_sha256": self.smoke_receipt_seal_file_sha256,
            "prepare_receipt_file_sha256": self.prepare_receipt_file_sha256,
            "prepare_receipt_seal_file_sha256": self.prepare_receipt_seal_file_sha256,
            "schedule_sha256": self.schedule_sha256,
            "schedule_file_sha256": self.schedule_file_sha256,
            "generate_receipt_file_sha256": self.generate_receipt_file_sha256,
            "generate_receipt_seal_file_sha256": self.generate_receipt_seal_file_sha256,
            "dataset_file_sha256s": dict(self.dataset_file_sha256s),
            "dataset_sha256s": dict(self.dataset_sha256s),
            "seed_split": dict(self.seed_split),
        }


def _validate_digest_map(
    value: object, *, field: str, keys: Iterable[str]
) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise C3V04LearnabilityGateError(f"{field} must be a digest map")
    expected = {str(key) for key in keys}
    if set(value) != expected:
        raise C3V04LearnabilityGateError(f"{field} seed set drifted")
    return {
        str(key): _digest(item, field=f"{field}[{key}]")
        for key, item in value.items()
    }


def _validate_materialized_metadata(
    *,
    schedule: Any,
    receipt: Mapping[str, Any],
    source_seed: int,
    split: str,
) -> None:
    """Authenticate schedule/physical-key rows without opening dataset bytes."""

    rows = receipt.get("materialized_rows")
    if not isinstance(rows, Mapping):
        raise C3V04LearnabilityGateError("materialized_rows is not a seed map")
    rows_for_seed = rows.get(str(source_seed))
    if not isinstance(rows_for_seed, list):
        raise C3V04LearnabilityGateError(
            f"materialized rows missing for source seed {source_seed}"
        )
    expected_ids = source_runner._expected_materialized_identities(
        schedule, source_seed=source_seed
    )
    expected_keys = source_runner._expected_materialized_physical_keys(
        schedule, source_seed=source_seed
    )
    observed_ids: set[tuple[str, int, int, int, int]] = set()
    for row in rows_for_seed:
        if not isinstance(row, Mapping):
            raise C3V04LearnabilityGateError("materialized receipt row is malformed")
        identity = source_runner._row_identity(row)
        if identity in observed_ids:
            raise C3V04LearnabilityGateError(
                f"duplicate materialized identity for source seed {source_seed}"
            )
        observed_ids.add(identity)
        if row.get("source_seed") != source_seed or row.get("split") != split:
            raise C3V04LearnabilityGateError(
                "materialized receipt crossed the frozen seed split"
            )
        expected_reference_key, expected_candidate_key = expected_keys.get(identity, (None, None))
        if identity not in expected_keys:
            raise C3V04LearnabilityGateError(
                f"materialized identity is absent from sealed schedule: {identity}"
            )
        if (
            row.get("reference_physical_key") != expected_reference_key
            or row.get("candidate_physical_key") != expected_candidate_key
        ):
            raise C3V04LearnabilityGateError(
                "materialized physical key differs from sealed schedule"
            )
        _digest(row.get("comparison_sha256"), field="materialized.comparison_sha256")
    if observed_ids != expected_ids:
        raise C3V04LearnabilityGateError(
            f"materialized identity set differs for source seed {source_seed}"
        )


def authenticate_source(
    *, source_dir: Path, prereg_path: Path | None = DEFAULT_PREREG
) -> tuple[SourceAuthority, Any, dict[str, Any], dict[str, Any]]:
    """Authenticate completed source receipts before reading dataset bytes.

    The returned source datasets are intentionally not included.  This
    function only opens pre-outcome JSON receipts and the materialized-row
    metadata embedded in the generate receipt.  The caller seals the gate
    authority before calling ``source_runner.verify`` or reading C3 datasets.
    """

    destination = Path(source_dir)
    try:
        _manifest, prepare_receipt, schedule = source_runner._load_prepared_authority(
            destination,
            prereg_path=Path(prereg_path) if prereg_path is not None else None,
        )
    except Exception as error:
        raise C3V04LearnabilityGateError(
            f"prepared source authority failed: {error}"
        ) from error
    manifest_path = destination / "source-manifest.json"
    prepare_path = destination / "prepare-receipt.json"
    prepare_seal_path = destination / "prepare-receipt-seal.json"
    schedule_path = destination / "schedule.json"
    data_root = destination / "source-data"
    if data_root.is_symlink() or not data_root.is_dir():
        raise C3V04LearnabilityGateError("published source-data directory is missing")
    generate_path = data_root / "receipt.json"
    generate_seal_path = data_root / "receipt-seal.json"
    manifest = _read_canonical_json(manifest_path)
    generate_receipt = _read_canonical_json(generate_path)
    generate_seal = _read_canonical_json(generate_seal_path)
    source_manifest_sha256 = _digest(
        manifest.get("source_manifest_sha256"), field="source_manifest_sha256"
    )
    try:
        source_runner._validate_generate_receipt(
            generate_receipt,
            source_manifest_sha256=source_manifest_sha256,
            schedule=schedule,
        )
    except Exception as error:
        raise C3V04LearnabilityGateError(
            f"generate receipt failed independent validation: {error}"
        ) from error
    if (
        generate_seal.get("schema") != source_runner.GENERATE_SEAL_SCHEMA
        or generate_seal.get("receipt_file_sha256") != _file_sha256(generate_path)
    ):
        raise C3V04LearnabilityGateError("generate receipt seal is invalid")
    if generate_receipt.get("seed_split") != EXPECTED_SEED_SPLIT:
        raise C3V04LearnabilityGateError("source seed split is not exactly 4/3/0")
    if set(EXPECTED_SEED_SPLIT.values()) != {"train", "validation"}:
        raise C3V04LearnabilityGateError("gate seed split constant is malformed")
    for field in (
        "source_manifest_sha256",
        "checkpoint_sha256",
        "schedule_sha256",
        "schedule_file_sha256",
    ):
        _digest(generate_receipt.get(field), field=f"generate.{field}")
    dataset_file_sha256s = _validate_digest_map(
        generate_receipt.get("dataset_file_sha256s"),
        field="generate.dataset_file_sha256s",
        keys=EXPECTED_SEED_SPLIT,
    )
    dataset_sha256s = _validate_digest_map(
        generate_receipt.get("dataset_sha256s"),
        field="generate.dataset_sha256s",
        keys=EXPECTED_SEED_SPLIT,
    )
    if generate_receipt.get("source_manifest_sha256") != source_manifest_sha256:
        raise C3V04LearnabilityGateError("generate/source manifest lineage drifted")
    if generate_receipt.get("schedule_sha256") != schedule.schedule_sha256:
        raise C3V04LearnabilityGateError("generate/schedule lineage drifted")
    if generate_receipt.get("schedule_file_sha256") != _file_sha256(schedule_path):
        raise C3V04LearnabilityGateError("generate schedule file lineage drifted")
    if generate_receipt.get("schedule_file_sha256") != prepare_receipt.get(
        "schedule_file_sha256"
    ):
        raise C3V04LearnabilityGateError("prepare/generate schedule seal drifted")
    # Validate the recorded dataset paths and hashes without opening their
    # contents.  source_runner.verify performs the actual byte/hash check only
    # after the caller has written the gate authority seal.
    for seed in EXPECTED_SEED_SPLIT:
        dataset_path = data_root / f"c3-{seed}.json"
        if dataset_path.is_symlink() or not dataset_path.is_file():
            raise C3V04LearnabilityGateError(
                f"published dataset file is missing or non-regular: {dataset_path}"
            )
    for source_seed, split in sorted(EXPECTED_SEED_SPLIT.items(), key=lambda item: int(item[0])):
        _validate_materialized_metadata(
            schedule=schedule,
            receipt=generate_receipt,
            source_seed=int(source_seed),
            split=split,
        )
    authority = SourceAuthority(
        source_dir=destination,
        source_manifest_sha256=source_manifest_sha256,
        source_manifest_file_sha256=_file_sha256(manifest_path),
        prereg_file_sha256=_digest(
            prepare_receipt.get("prereg_file_sha256"),
            field="prepare.prereg_file_sha256",
        ),
        prereg_digest=_digest(
            prepare_receipt.get("prereg_digest"),
            field="prepare.prereg_digest",
        ),
        ephemeris_file_set_sha256=_digest(
            prepare_receipt.get("ephemeris_file_set_sha256"),
            field="prepare.ephemeris_file_set_sha256",
        ),
        main_status_file_sha256=_digest(
            prepare_receipt["main_authority"].get("status_file_sha256"),
            field="prepare.main.status_file_sha256",
        ),
        main_episode_logs_file_sha256=_digest(
            prepare_receipt["main_authority"].get("episode_logs_file_sha256"),
            field="prepare.main.episode_logs_file_sha256",
        ),
        main_checkpoint_sha256=_digest(
            prepare_receipt["main_authority"].get("checkpoint_file_sha256"),
            field="prepare.main.checkpoint_file_sha256",
        ),
        smoke_receipt_file_sha256=_digest(
            prepare_receipt["real_tle_smoke"].get("receipt_file_sha256"),
            field="prepare.smoke.receipt_file_sha256",
        ),
        smoke_receipt_seal_file_sha256=_digest(
            prepare_receipt["real_tle_smoke"].get(
                "receipt_seal_file_sha256"
            ),
            field="prepare.smoke.receipt_seal_file_sha256",
        ),
        prepare_receipt_file_sha256=_file_sha256(prepare_path),
        prepare_receipt_seal_file_sha256=_file_sha256(prepare_seal_path),
        schedule_sha256=schedule.schedule_sha256,
        schedule_file_sha256=_file_sha256(schedule_path),
        generate_receipt_file_sha256=_file_sha256(generate_path),
        generate_receipt_seal_file_sha256=_file_sha256(generate_seal_path),
        dataset_file_sha256s=dataset_file_sha256s,
        dataset_sha256s=dataset_sha256s,
        seed_split=EXPECTED_SEED_SPLIT,
    )
    return authority, schedule, prepare_receipt, generate_receipt


def build_gate_authority(
    *,
    source: SourceAuthority,
    v03_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Build the pre-validation authority document (without opening datasets)."""

    v03_authority = Path(v03_root) / "authority.json"
    v03_authority_seal = Path(v03_root) / "authority-seal.json"
    v03_result = Path(v03_root) / "result.json"
    v03_result_seal = Path(v03_root) / "result-seal.json"
    if v03_authority.is_symlink() or not v03_authority.is_file():
        raise C3V04LearnabilityGateError("sealed V0.3 authority.json is missing")
    if v03_authority_seal.is_symlink() or not v03_authority_seal.is_file():
        raise C3V04LearnabilityGateError("sealed V0.3 authority-seal.json is missing")
    if v03_result.is_symlink() or not v03_result.is_file():
        raise C3V04LearnabilityGateError("sealed V0.3 result.json is missing")
    if v03_result_seal.is_symlink() or not v03_result_seal.is_file():
        raise C3V04LearnabilityGateError("sealed V0.3 result-seal.json is missing")
    v03_authority_payload = _read_canonical_json(v03_authority)
    v03_seal_payload = _read_canonical_json(v03_authority_seal)
    v03_result_payload = _read_canonical_json(v03_result)
    v03_result_seal_payload = _read_canonical_json(v03_result_seal)
    v03_authority_file_sha = _file_sha256(v03_authority)
    v03_authority_seal_file_sha = _file_sha256(v03_authority_seal)
    # The sealed V0.3 artifact predates the convention of embedding its final
    # authority digest in authority.json.  Its authority seal deliberately
    # binds both authority_file_sha256 and authority_sha256 to the canonical
    # file digest, which is also carried by result.json/result-seal.json.
    # Authenticate that real sealed schema instead of reading a similarly
    # named digest from a nested predecessor receipt.
    v03_authority_sha = _digest(
        v03_authority_file_sha,
        field="v03.authority_file_sha256",
    )
    if v03_authority_sha != EXPECTED_V03_AUTHORITY_SHA256:
        raise C3V04LearnabilityGateError("sealed V0.3 authority file drifted")
    if (
        v03_seal_payload.get("schema")
        != "multi-catfish-mcrl-v03-e1-masked-meanmax-fallback-v1-authority-seal"
        or v03_seal_payload.get("authority_file_sha256") != v03_authority_file_sha
        or v03_seal_payload.get("authority_sha256") != EXPECTED_V03_AUTHORITY_SHA256
    ):
        raise C3V04LearnabilityGateError("sealed V0.3 authority seal is invalid")
    if (
        _file_sha256(v03_result) != EXPECTED_V03_RESULT_FILE_SHA256
        or _file_sha256(v03_result_seal) != EXPECTED_V03_RESULT_SEAL_FILE_SHA256
        or v03_result_seal_payload.get("schema")
        != "multi-catfish-mcrl-v03-e1-masked-meanmax-fallback-v1-result-seal"
        or v03_result_seal_payload.get("authority_sha256")
        != EXPECTED_V03_AUTHORITY_SHA256
        or v03_result_seal_payload.get("authority_seal_file_sha256")
        != v03_authority_seal_file_sha
        or v03_result_seal_payload.get("result_file_sha256")
        != EXPECTED_V03_RESULT_FILE_SHA256
    ):
        raise C3V04LearnabilityGateError("sealed V0.3 result seal is invalid")
    gate_payload = v03_result_payload.get("gate")
    route_gate = (
        gate_payload.get("route_gate", {})
        if isinstance(gate_payload, Mapping)
        else {}
    )
    if (
        v03_result_payload.get("schema")
        != "multi-catfish-mcrl-v03-e1-masked-meanmax-fallback-v1-result"
        or v03_result_payload.get("status") != "STOP_MASKED_MEANMAX_VALIDATION"
        or v03_result_payload.get("authority_sha256")
        != EXPECTED_V03_AUTHORITY_SHA256
        or v03_result_payload.get("selected_common_rung") != 10
        or not isinstance(route_gate, Mapping)
        or route_gate.get("C1", {}).get("pass") is not True
        or route_gate.get("C2", {}).get("pass") is not True
        or route_gate.get("C3", {}).get("pass") is not False
    ):
        raise C3V04LearnabilityGateError(
            "sealed V0.3 result does not authorize carrying only Q1/Q2"
        )
    checkpoint_receipts = v03_result_payload.get("checkpoint_file_sha256s")
    if not isinstance(checkpoint_receipts, Mapping) or any(
        checkpoint_receipts.get(f"init-{seed}-rung-000010.pt") != expected
        for seed, expected in EXPECTED_V03_CHECKPOINT_SHA256.items()
    ):
        raise C3V04LearnabilityGateError(
            "sealed V0.3 result does not bind the carried rung-10 checkpoints"
        )
    checkpoint_files = {
        str(seed): {
            "path": _relative(
                Path(v03_root) / "checkpoints" / f"init-{seed}-rung-000010.pt"
            ),
            "sha256": expected,
        }
        for seed, expected in sorted(EXPECTED_V03_CHECKPOINT_SHA256.items())
    }
    for seed, expected in EXPECTED_V03_CHECKPOINT_SHA256.items():
        checkpoint = Path(v03_root) / "checkpoints" / f"init-{seed}-rung-000010.pt"
        if _file_sha256(checkpoint) != expected:
            raise C3V04LearnabilityGateError(
                f"sealed V0.3 checkpoint hash drifted for initialization {seed}"
            )
    v03_manifest_sha = _digest(
        v03_authority_payload.get("source_manifest_sha256"),
        field="v03.source_manifest_sha256",
    )
    authority = {
        "schema": AUTHORITY_SCHEMA,
        "status": "SEALED_BEFORE_VALIDATION_DATASET_AND_METRICS",
        "claim_ceiling": CLAIM_CEILING,
        "source": source.as_dict(),
        "source_manifest_sha256": source.source_manifest_sha256,
        "source_seed_split": dict(EXPECTED_SEED_SPLIT),
        "train_source_seeds": list(TRAIN_SOURCE_SEEDS),
        "validation_source_seeds": list(VALIDATION_SOURCE_SEEDS),
        "test_source_seeds": [],
        "test_split_opened": False,
        "validation_dataset_bytes_opened": False,
        "validation_metrics_computed": False,
        "held_out_ee_evaluated": False,
        "training": False,
        "q3_pairwise_training_started": False,
        "episode_training_started": False,
        "episode_trajectory_opened": False,
        "config": {
            "state_dim": STATE_DIM,
            "action_dim": ACTION_DIM,
            "hidden_layers": list(HIDDEN_LAYERS),
            "activation": ACTIVATION,
            "learning_rate": LEARNING_RATE,
            "kappa_bits_hex": KAPPA_BITS.hex(),
            "beta": BETA,
            "loss_weights": list(LOSS_WEIGHTS),
            "update_rungs": list(UPDATE_RUNGS),
            "initialization_seeds": list(INITIALIZATION_SEEDS),
        },
        "v03_frozen": {
            "authority_sha256": EXPECTED_V03_AUTHORITY_SHA256,
            "authority_file_sha256": v03_authority_file_sha,
            "authority_seal_file_sha256": v03_authority_seal_file_sha,
            "result_file_sha256": EXPECTED_V03_RESULT_FILE_SHA256,
            "result_seal_file_sha256": EXPECTED_V03_RESULT_SEAL_FILE_SHA256,
            "result_status": "STOP_MASKED_MEANMAX_VALIDATION",
            "selected_common_rung": 10,
            "carried_routes": ["C1", "C2"],
            "discarded_route": "C3",
            "source_manifest_sha256": v03_manifest_sha,
            "checkpoint_rung": 10,
            "checkpoint_sha256s": checkpoint_files,
            "q1_head_index": 0,
            "q2_head_index": 1,
        },
        "source_schedule": {
            "schedule_sha256": source.schedule_sha256,
            "schedule_file_sha256": source.schedule_file_sha256,
            "max_contexts_per_anchor": source_runner.MAX_CONTEXTS_PER_ANCHOR,
        },
        "authority_order": [
            "source_receipts_and_schedule",
            "v03_frozen_lineage",
            "gate_authority_sealed",
            "validation_dataset_bytes",
            "validation_metrics",
        ],
        "output_dir": _relative(output_dir),
        "gate_code_manifest": _gate_code_manifest(),
    }
    authority["authority_sha256"] = _canonical_sha256(authority)
    return authority


@dataclass(frozen=True)
class C3DatasetSurface:
    batch: EEAxisPairBatch
    source_seeds: tuple[int, ...]
    anchor_sha256s: tuple[str, ...]
    comparison_sha256s: tuple[str, ...]


def combine_surfaces(*surfaces: C3DatasetSurface) -> C3DatasetSurface:
    """Combine authenticated TRAIN/validation views for collision census only."""

    if not surfaces or any(not isinstance(value, C3DatasetSurface) for value in surfaces):
        raise C3V04LearnabilityGateError(
            "collision census requires C3 dataset surfaces"
        )
    batches = [surface.batch for surface in surfaces]
    batch = EEAxisPairBatch(
        states=np.concatenate([value.states for value in batches], axis=0),
        reference_actions=np.concatenate(
            [value.reference_actions for value in batches], axis=0
        ),
        candidate_actions=np.concatenate(
            [value.candidate_actions for value in batches], axis=0
        ),
        target_surplus_bits=np.concatenate(
            [value.target_surplus_bits for value in batches], axis=0
        ),
        action_masks=np.concatenate([value.action_masks for value in batches], axis=0),
    )
    batch.validate(state_dim=STATE_DIM, action_dim=ACTION_DIM)
    return C3DatasetSurface(
        batch=batch,
        source_seeds=tuple(
            seed for surface in surfaces for seed in surface.source_seeds
        ),
        anchor_sha256s=tuple(
            anchor for surface in surfaces for anchor in surface.anchor_sha256s
        ),
        comparison_sha256s=tuple(
            digest
            for surface in surfaces
            for digest in surface.comparison_sha256s
        ),
    )


def _surface_from_datasets(
    datasets: Mapping[int, V04C3OpeningDataset],
    *,
    ordered_seeds: Sequence[int],
) -> C3DatasetSurface:
    rows = [row for seed in ordered_seeds for row in datasets[seed].rows]
    if not rows:
        raise C3V04LearnabilityGateError("C3 dataset surface is empty")
    states = np.stack([row.pair.state for row in rows]).astype(np.float32)
    references = np.asarray(
        [row.pair.reference_action for row in rows], dtype=np.int64
    )
    candidates = np.asarray(
        [row.pair.candidate_action for row in rows], dtype=np.int64
    )
    targets = np.asarray(
        [row.pair.route_target_surplus_bits for row in rows], dtype=np.float64
    )
    masks = np.stack([row.pair.action_mask for row in rows]).astype(np.bool_)
    for array in (states, references, candidates, targets, masks):
        array.setflags(write=False)
    batch = EEAxisPairBatch(
        states=states,
        reference_actions=references,
        candidate_actions=candidates,
        target_surplus_bits=targets,
        action_masks=masks,
    )
    batch.validate(state_dim=STATE_DIM, action_dim=ACTION_DIM)
    return C3DatasetSurface(
        batch=batch,
        source_seeds=tuple(
            int(seed) for seed in ordered_seeds for _row in datasets[seed].rows
        ),
        anchor_sha256s=tuple(row.pair.anchor_sha256 for row in rows),
        comparison_sha256s=tuple(row.comparison_sha256 for row in rows),
    )


def load_published_datasets(
    *,
    source: SourceAuthority,
    prereg_path: Path | None,
) -> tuple[C3DatasetSurface, C3DatasetSurface, dict[str, Any]]:
    """Open and independently verify datasets only after authority is sealed."""

    try:
        verified = source_runner.verify(
            output_dir=source.source_dir,
            prereg_path=Path(prereg_path) if prereg_path is not None else None,
        )
    except Exception as error:
        raise C3V04LearnabilityGateError(
            f"source dataset verification failed after authority seal: {error}"
        ) from error
    datasets: dict[int, V04C3OpeningDataset] = {}
    for seed in sorted(EXPECTED_SEED_SPLIT, key=int):
        path = source.source_dir / "source-data" / f"c3-{seed}.json"
        try:
            dataset = read_v04_c3_dataset(path)
        except Exception as error:
            raise C3V04LearnabilityGateError(
                f"cannot open authenticated C3 dataset {seed}: {error}"
            ) from error
        if dataset.verify() != source.dataset_sha256s[str(seed)]:
            raise C3V04LearnabilityGateError(
                f"C3 dataset digest differs from source receipt for {seed}"
            )
        datasets[int(seed)] = dataset
    train = _surface_from_datasets(datasets, ordered_seeds=TRAIN_SOURCE_SEEDS)
    validation = _surface_from_datasets(
        datasets, ordered_seeds=VALIDATION_SOURCE_SEEDS
    )
    return train, validation, verified


def collision_census(surface: C3DatasetSurface) -> dict[str, Any]:
    """Count exact input collisions and conflicting target groups.

    A duplicate is harmless when its target bytes agree.  A conflicting
    target for the same state/mask/action pair is a deterministic ambiguity
    and fails the gate.  The caller computes TRAIN, validation, and their
    combined cross-split census, never against TEST data.
    """

    groups: dict[bytes, list[float]] = defaultdict(list)
    batch = surface.batch
    for row in range(batch.states.shape[0]):
        key = b"".join(
            (
                np.asarray(batch.states[row], dtype=np.float32).tobytes(),
                np.asarray(batch.action_masks[row], dtype=np.bool_).tobytes(),
                np.asarray([batch.reference_actions[row]], dtype=np.int64).tobytes(),
                np.asarray([batch.candidate_actions[row]], dtype=np.int64).tobytes(),
            )
        )
        groups[key].append(float(batch.target_surplus_bits[row]))
    duplicate_rows = sum(max(0, len(values) - 1) for values in groups.values())
    conflicts: list[dict[str, Any]] = []
    for key, values in groups.items():
        target_hex = sorted({float(value).hex() for value in values})
        if len(target_hex) > 1:
            conflicts.append(
                {
                    "input_sha256": hashlib.sha256(key).hexdigest(),
                    "rows": len(values),
                    "target_hex": target_hex,
                    "target_floor_bits": max(values) - min(values),
                }
            )
    return {
        "rows": int(batch.states.shape[0]),
        "unique_inputs": len(groups),
        "duplicate_rows": int(duplicate_rows),
        "conflicting_target_groups": len(conflicts),
        "conflict_floor_bits": float(
            max((item["target_floor_bits"] for item in conflicts), default=0.0)
        ),
        "conflicts": conflicts,
        "pass": not conflicts,
    }


def _q3_surface(
    trainer: EEAxisV04HybridTrainer, surface: C3DatasetSurface
) -> np.ndarray:
    values = np.asarray(surface.batch.states, dtype=np.float32)
    with torch.no_grad():
        tensor = torch.tensor(values, dtype=torch.float32, device=trainer.device)
        result = trainer.q3(tensor).detach().cpu().numpy()
    if result.shape != (values.shape[0], ACTION_DIM) or not np.all(
        np.isfinite(result)
    ):
        raise C3V04LearnabilityGateError("Q3 produced an invalid validation surface")
    return np.asarray(result, dtype=np.float64)


def _network_state_equal(left: Any, right: Any) -> bool:
    left_state = left.state_dict()
    right_state = right.state_dict()
    if set(left_state) != set(right_state):
        return False
    return all(torch.equal(left_state[name], right_state[name]) for name in left_state)


def _checkpoint_payload(
    *,
    trainer: EEAxisV04HybridTrainer,
    authority_sha256: str,
    initialization_seed: int,
    rung: int,
    train_surface_sha256: str,
) -> dict[str, Any]:
    if trainer.initialization_seed != initialization_seed:
        raise C3V04LearnabilityGateError("trainer/checkpoint seed mismatch")
    if trainer.selected_q3_rung != rung or trainer.q3_update_count != rung:
        raise C3V04LearnabilityGateError("trainer/checkpoint rung mismatch")
    state = trainer.checkpoint_state()
    return {
        "schema": Q3_CHECKPOINT_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "authority_sha256": authority_sha256,
        "initialization_seed": initialization_seed,
        "rung": rung,
        "train_surface_sha256": train_surface_sha256,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "q3_pairwise_training": True,
        "episode_training": False,
        "hybrid": state,
    }


def _save_and_reload_rung(
    *,
    path: Path,
    trainer: EEAxisV04HybridTrainer,
    spec: FrozenMeanMaxCheckpointSpec,
    v03_config: EEAxisMaskedMeanMaxConfig,
    v04_config: EEAxisActionSharedConfig,
    authority_sha256: str,
    initialization_seed: int,
    rung: int,
    train_surface_sha256: str,
) -> tuple[str, dict[str, Any]]:
    payload = _checkpoint_payload(
        trainer=trainer,
        authority_sha256=authority_sha256,
        initialization_seed=initialization_seed,
        rung=rung,
        train_surface_sha256=train_surface_sha256,
    )
    file_sha = _write_once_torch(path, payload)
    try:
        loaded = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as error:
        raise C3V04LearnabilityGateError(
            f"saved Q3 rung checkpoint cannot be reloaded: {path}"
        ) from error
    # Tensor equality is intentionally handled by the hybrid loader below;
    # comparing two nested mappings directly can invoke an ambiguous NumPy /
    # Torch truth value.
    if not isinstance(loaded, Mapping):
        raise C3V04LearnabilityGateError("reloaded Q3 checkpoint is malformed")
    for field in (
        "schema",
        "authority_sha256",
        "initialization_seed",
        "rung",
        "train_surface_sha256",
    ):
        if loaded.get(field) != payload[field]:
            raise C3V04LearnabilityGateError(
                f"reloaded Q3 checkpoint field drifted: {field}"
            )
    restored = EEAxisV04HybridTrainer.from_sealed_checkpoint(
        spec,
        v03_config=v03_config,
        v04_config=v04_config,
        selected_q3_rung=rung,
    )
    if restored.load_checkpoint_state(loaded["hybrid"]) != rung:
        raise C3V04LearnabilityGateError("reloaded Q3 checkpoint update count drifted")
    if not _network_state_equal(trainer.q3, restored.q3):
        raise C3V04LearnabilityGateError("reloaded Q3 tensors are not bit-identical")
    if not _network_state_equal(trainer.q1, restored.q1) or not _network_state_equal(
        trainer.q2, restored.q2
    ):
        raise C3V04LearnabilityGateError(
            "reloaded checkpoint changed frozen Q1/Q2 tensors"
        )
    receipt = {
        "path": _relative(path),
        "file_sha256": file_sha,
        "strict_reload": True,
        "q3_update_count": rung,
        "exact_three_networks": len(restored.q_nets) == 3,
        "frozen_q1_q2_bit_identical": True,
    }
    return file_sha, receipt


def _trainer_for_rung(
    *,
    spec: FrozenMeanMaxCheckpointSpec,
    v03_config: EEAxisMaskedMeanMaxConfig,
    v04_config: EEAxisActionSharedConfig,
    train_surface: C3DatasetSurface,
    rung: int,
) -> EEAxisV04HybridTrainer:
    trainer = EEAxisV04HybridTrainer.from_sealed_checkpoint(
        spec,
        v03_config=v03_config,
        v04_config=v04_config,
        selected_q3_rung=rung,
    )
    for _ in range(rung):
        trainer.update_c3(train_surface.batch)
    if trainer.q3_update_count != rung:
        raise C3V04LearnabilityGateError("Q3 rung training count is not exact")
    return trainer


def select_q3_rung(
    reports: Mapping[int, Mapping[int, C3V04BalancedGeneralization]],
    *,
    initialization_seeds: Sequence[int] = INITIALIZATION_SEEDS,
    update_rungs: Sequence[int] = UPDATE_RUNGS,
) -> tuple[int, dict[int, float]]:
    """Select the minimum mean model/null ratio with deterministic ties."""

    expected_seeds = tuple(int(seed) for seed in initialization_seeds)
    expected_rungs = tuple(int(rung) for rung in update_rungs)
    if set(reports) != set(expected_seeds):
        raise C3V04LearnabilityGateError("Q3 reports do not contain exactly three inits")
    means: dict[int, float] = {}
    for rung in expected_rungs:
        values = []
        for seed in expected_seeds:
            report = reports[seed].get(rung)
            if not isinstance(report, C3V04BalancedGeneralization):
                raise C3V04LearnabilityGateError(
                    f"missing Q3 report for seed {seed}, rung {rung}"
                )
            value = float(report.model_to_strongest_null_mae_ratio)
            if not math.isfinite(value) or value < 0.0:
                raise C3V04LearnabilityGateError("Q3 model/null ratio is invalid")
            values.append(value)
        means[rung] = float(np.mean(values))
    selected = min(expected_rungs, key=lambda rung: (means[rung], rung))
    return selected, means


def adjudicate_gate(
    *,
    reports: Mapping[int, Mapping[int, C3V04BalancedGeneralization]],
    selected_q3_rung: int,
    collision_censuses: Mapping[str, Mapping[str, Any]],
    authority_authenticated: bool,
) -> dict[str, Any]:
    """Apply the fixed promotion rule without any fallback or test access."""

    if not authority_authenticated:
        return {
            "status": FAILURE_STATUS,
            "reason": "source/checkpoint authority authentication failed",
            "claim_ceiling": CLAIM_CEILING,
        }
    selected_reports = [
        reports[seed][selected_q3_rung] for seed in INITIALIZATION_SEEDS
    ]
    skills = [float(report.skill_vs_strongest_null) for report in selected_reports]
    mean_skill = float(np.mean(skills))
    positive_initializations = sum(skill > 0.0 for skill in skills)
    collision_ok = all(
        bool(census.get("pass"))
        and int(census.get("conflicting_target_groups", 1)) == 0
        and float(census.get("conflict_floor_bits", 1.0)) == 0.0
        for census in collision_censuses.values()
    )
    passed = (
        mean_skill > 0.0
        and positive_initializations >= 2
        and collision_ok
    )
    return {
        "status": SUCCESS_STATUS if passed else FAILURE_STATUS,
        "claim_ceiling": SUCCESS_CLAIM_CEILING if passed else CLAIM_CEILING,
        "selected_q3_rung": int(selected_q3_rung),
        "skills": {
            str(seed): float(reports[seed][selected_q3_rung].skill_vs_strongest_null)
            for seed in INITIALIZATION_SEEDS
        },
        "mean_q3_skill": mean_skill,
        "positive_initializations": positive_initializations,
        "positive_initializations_required": 2,
        "collision_census_pass": collision_ok,
        "reason": (
            "Q3 anchor-seed-balanced skill passed"
            if passed
            else "Q3 learnability promotion rule failed"
        ),
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "training": True,
        "training_scope": "Q3_PAIRWISE_LEARNABILITY_GATE_ONLY",
        "q3_pairwise_training_completed": True,
        "episode_training": False,
    }


def _surface_digest(surface: C3DatasetSurface) -> str:
    body = {
        "comparisons": list(surface.comparison_sha256s),
        "source_seeds": list(surface.source_seeds),
        "anchors": list(surface.anchor_sha256s),
        "states": [
            hashlib.sha256(np.asarray(row, dtype=np.float32).tobytes()).hexdigest()
            for row in np.asarray(surface.batch.states)
        ],
        "targets_hex": [
            float(value).hex()
            for value in np.asarray(surface.batch.target_surplus_bits).tolist()
        ],
    }
    return _canonical_sha256(body)


def _spec_for_seed(v03_root: Path, seed: int) -> FrozenMeanMaxCheckpointSpec:
    path = Path(v03_root) / "checkpoints" / f"init-{seed}-rung-000010.pt"
    return FrozenMeanMaxCheckpointSpec(
        path=path,
        sha256=EXPECTED_V03_CHECKPOINT_SHA256[seed],
        authority_sha256=EXPECTED_V03_AUTHORITY_SHA256,
        initialization_seed=seed,
    )


def _run_gate(
    *,
    source_dir: Path,
    v03_root: Path,
    output_dir: Path,
    prereg_path: Path | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    if Path(output_dir).exists():
        raise FileExistsError(f"refusing to overwrite existing gate output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        source, schedule, prepare_receipt, generate_receipt = authenticate_source(
            source_dir=Path(source_dir), prereg_path=prereg_path
        )
        authority = build_gate_authority(
            source=source, v03_root=Path(v03_root), output_dir=Path(output_dir)
        )
        authority_file_sha = _write_once_json(output_dir / "authority.json", authority)
        authority_seal_sha = _write_once_json(
            output_dir / "authority-seal.json",
            {
                "schema": AUTHORITY_SEAL_SCHEMA,
                "authority_file_sha256": authority_file_sha,
                "authority_sha256": authority["authority_sha256"],
                "validation_dataset_bytes_opened": False,
                "validation_metrics_computed": False,
                "test_split_opened": False,
            },
        )
        # This is the first operation allowed to read validation dataset
        # bytes.  The authority and its seal already exist at this point.
        train_surface, validation_surface, source_verify = load_published_datasets(
            source=source, prereg_path=prereg_path
        )
        v03_config, v04_config = _config_pair()
        train_surface_sha = _surface_digest(train_surface)
        validation_surface_sha = _surface_digest(validation_surface)
        collisions = {
            "train": collision_census(train_surface),
            "validation": collision_census(validation_surface),
            "combined_train_validation": collision_census(
                combine_surfaces(train_surface, validation_surface)
            ),
        }
        reports: dict[int, dict[int, C3V04BalancedGeneralization]] = {}
        metric_receipts: dict[str, dict[str, Any]] = {}
        rung_receipts: dict[str, dict[str, Any]] = {}
        checkpoint_root = output_dir / "checkpoints"
        for seed in INITIALIZATION_SEEDS:
            spec = _spec_for_seed(Path(v03_root), seed)
            reports[seed] = {}
            metric_receipts[str(seed)] = {}
            rung_receipts[str(seed)] = {}
            for rung in UPDATE_RUNGS:
                trainer = _trainer_for_rung(
                    spec=spec,
                    v03_config=v03_config,
                    v04_config=v04_config,
                    train_surface=train_surface,
                    rung=rung,
                )
                checkpoint_path = (
                    checkpoint_root / f"q3-{seed}-rung-{rung:06d}.pt"
                )
                _checkpoint_sha, checkpoint_receipt = _save_and_reload_rung(
                    path=checkpoint_path,
                    trainer=trainer,
                    spec=spec,
                    v03_config=v03_config,
                    v04_config=v04_config,
                    authority_sha256=authority["authority_sha256"],
                    initialization_seed=seed,
                    rung=rung,
                    train_surface_sha256=train_surface_sha,
                )
                q_surface = _q3_surface(trainer, validation_surface)
                report = compute_anchor_seed_balanced_generalization(
                    train_batch=train_surface.batch,
                    validation_batch=validation_surface.batch,
                    validation_source_seeds=validation_surface.source_seeds,
                    validation_anchor_sha256s=validation_surface.anchor_sha256s,
                    heldout_q_surface=q_surface,
                    state_dim=STATE_DIM,
                    action_dim=ACTION_DIM,
                    kappa_bits=KAPPA_BITS,
                )
                reports[seed][rung] = report
                metric_receipts[str(seed)][str(rung)] = report.as_dict()
                rung_receipts[str(seed)][str(rung)] = {
                    **checkpoint_receipt,
                    "model_to_strongest_null_mae_ratio": report.model_to_strongest_null_mae_ratio,
                    "skill_vs_strongest_null": report.skill_vs_strongest_null,
                }
        selected_rung, mean_ratios = select_q3_rung(reports)
        decision = adjudicate_gate(
            reports=reports,
            selected_q3_rung=selected_rung,
            collision_censuses=collisions,
            authority_authenticated=True,
        )
        hybrid_receipts: dict[str, Any] = {}
        hybrid_root = output_dir / "hybrids"
        if decision["status"] == SUCCESS_STATUS:
            for seed in INITIALIZATION_SEEDS:
                spec = _spec_for_seed(Path(v03_root), seed)
                selected_checkpoint = checkpoint_root / (
                    f"q3-{seed}-rung-{selected_rung:06d}.pt"
                )
                selected_payload = torch.load(
                    selected_checkpoint, map_location="cpu", weights_only=False
                )
                trainer = EEAxisV04HybridTrainer.from_sealed_checkpoint(
                    spec,
                    v03_config=v03_config,
                    v04_config=v04_config,
                    selected_q3_rung=selected_rung,
                )
                if trainer.load_checkpoint_state(selected_payload["hybrid"]) != selected_rung:
                    raise C3V04LearnabilityGateError(
                        "selected Q3 checkpoint failed strict hybrid load"
                    )
                frozen_before = [
                    {
                        name: tensor.detach().cpu().clone()
                        for name, tensor in network.state_dict().items()
                    }
                    for network in trainer.q_nets[:2]
                ]
                hybrid_state = trainer.checkpoint_state()
                hybrid_path = hybrid_root / (
                    f"hybrid-{seed}-selected-rung-{selected_rung:06d}.pt"
                )
                hybrid_payload = {
                    "schema": HYBRID_CHECKPOINT_SCHEMA,
                    "claim_ceiling": SUCCESS_CLAIM_CEILING,
                    "authority_sha256": authority["authority_sha256"],
                    "initialization_seed": seed,
                    "selected_q3_rung": selected_rung,
                    "test_split_opened": False,
                    "held_out_ee_evaluated": False,
                    "q3_pairwise_training": True,
                    "episode_training": False,
                    "hybrid": hybrid_state,
                }
                hybrid_file_sha = _write_once_torch(hybrid_path, hybrid_payload)
                restored = EEAxisV04HybridTrainer.from_sealed_checkpoint(
                    spec,
                    v03_config=v03_config,
                    v04_config=v04_config,
                    selected_q3_rung=selected_rung,
                )
                reloaded = torch.load(
                    hybrid_path, map_location="cpu", weights_only=False
                )
                restored.load_checkpoint_state(reloaded["hybrid"])
                frozen_same = all(
                    all(
                        torch.equal(before[name], network.state_dict()[name])
                        for name in before
                    )
                    for before, network in zip(
                        frozen_before, restored.q_nets[:2], strict=True
                    )
                )
                if not frozen_same or len(restored.q_nets) != 3:
                    raise C3V04LearnabilityGateError(
                        "selected hybrid reload failed exact-three/frozen-head proof"
                    )
                hybrid_receipts[str(seed)] = {
                    "path": _relative(hybrid_path),
                    "file_sha256": hybrid_file_sha,
                    "strict_reload": True,
                    "exact_three_networks": True,
                    "frozen_q1_q2_bit_identical": frozen_same,
                    "q1_head_index": 0,
                    "q2_head_index": 1,
                    "q3_trainable_only": all(
                        parameter.requires_grad for parameter in restored.q3.parameters()
                    ),
                }
        if _gate_code_manifest() != authority["gate_code_manifest"]:
            raise C3V04LearnabilityGateError(
                "gate code manifest changed after authority seal"
            )
        result = {
            "schema": RESULT_SCHEMA,
            "status": decision["status"],
            "claim_ceiling": decision["claim_ceiling"],
            "authority_sha256": authority["authority_sha256"],
            "authority_file_sha256": authority_file_sha,
            "authority_seal_file_sha256": authority_seal_sha,
            "source_verify": source_verify,
            "source_manifest_sha256": source.source_manifest_sha256,
            "schedule_sha256": source.schedule_sha256,
            "train_surface_sha256": train_surface_sha,
            "validation_surface_sha256": validation_surface_sha,
            "validation_dataset_bytes_opened": True,
            "validation_metrics_computed": True,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "training": True,
            "training_scope": "Q3_PAIRWISE_LEARNABILITY_GATE_ONLY",
            "q3_pairwise_training_completed": True,
            "episode_training": False,
            "selected_q3_rung": selected_rung,
            "mean_model_to_strongest_null_ratio_by_rung": {
                str(rung): float(value) for rung, value in mean_ratios.items()
            },
            "decision": decision,
            "collision_censuses": collisions,
            "metrics": metric_receipts,
            "rung_checkpoints": rung_receipts,
            "selected_hybrids": hybrid_receipts,
            "elapsed_s": time.perf_counter() - started,
        }
        result_file_sha = _write_once_json(output_dir / "result.json", result)
        result_seal_sha = _write_once_json(
            output_dir / "result-seal.json",
            {
                "schema": RESULT_SEAL_SCHEMA,
                "result_file_sha256": result_file_sha,
                "authority_sha256": authority["authority_sha256"],
                "authority_file_sha256": authority_file_sha,
                "test_split_opened": False,
                "held_out_ee_evaluated": False,
            },
        )
        return {
            "schema": RESULT_SCHEMA,
            "status": decision["status"],
            "claim_ceiling": decision["claim_ceiling"],
            "selected_q3_rung": selected_rung,
            "mean_q3_skill": decision["mean_q3_skill"],
            "positive_initializations": decision["positive_initializations"],
            "result_file_sha256": result_file_sha,
            "result_seal_file_sha256": result_seal_sha,
            "validation_dataset_bytes_opened": True,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "training": True,
            "training_scope": "Q3_PAIRWISE_LEARNABILITY_GATE_ONLY",
            "q3_pairwise_training_completed": True,
            "episode_training": False,
        }
    except Exception:
        # The authority itself is intentionally left sealed for forensic
        # inspection.  A result is not fabricated when a required source or
        # learner receipt fails; the caller receives the exception and no GO.
        raise


def run(
    *,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    v03_root: Path = DEFAULT_V03_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    prereg_path: Path | None = DEFAULT_PREREG,
) -> dict[str, Any]:
    """Run the gate once; all authority/result files are write-once."""

    return _run_gate(
        source_dir=Path(source_dir),
        v03_root=Path(v03_root),
        output_dir=Path(output_dir),
        prereg_path=Path(prereg_path) if prereg_path is not None else None,
    )


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--v03-root", type=Path, default=DEFAULT_V03_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    result = run(
        source_dir=args.source_dir,
        v03_root=args.v03_root,
        output_dir=args.output_dir,
        prereg_path=args.prereg,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "ACTION_DIM",
    "AUTHORITY_SCHEMA",
    "BETA",
    "CLAIM_CEILING",
    "C3DatasetSurface",
    "C3V04LearnabilityGateError",
    "DEFAULT_OUTPUT_DIR",
    "EXPECTED_SEED_SPLIT",
    "EXPECTED_V03_AUTHORITY_SHA256",
    "EXPECTED_V03_CHECKPOINT_SHA256",
    "FAILURE_STATUS",
    "HIDDEN_LAYERS",
    "INITIALIZATION_SEEDS",
    "KAPPA_BITS",
    "LEARNING_RATE",
    "STATE_DIM",
    "SUCCESS_STATUS",
    "TRAIN_SOURCE_SEEDS",
    "UPDATE_RUNGS",
    "VALIDATION_SOURCE_SEEDS",
    "adjudicate_gate",
    "authenticate_source",
    "build_gate_authority",
    "collision_census",
    "compute_anchor_seed_balanced_generalization",
    "load_published_datasets",
    "run",
    "select_q3_rung",
]
