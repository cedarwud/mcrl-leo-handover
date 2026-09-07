#!/usr/bin/env python3
"""Fail-closed V0.19 TRAIN-only learner preflight.

This runner is deliberately narrower than the V0.19 learned-Q3 gate.  It is
an implementation preflight for the normalized output parameterization: one
development initialization, one declared batch schedule, and exactly 100
TRAIN updates.  It never opens VALIDATION or TEST, never starts a simulator or
source harvester, and never updates Q1 or Q2.

The intended invocation is on the Ubuntu server, where the already-opened
V0.18 TRAIN source closures live.  The local checkout contains only synthetic
unit tests for this file; no real preflight is run locally.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch


PREFLIGHT_SCHEMA = "multi-catfish-mcrl-v019-relational-q3-train-preflight-v1"
PREFLIGHT_VERSION = 1
CONTRACT_STATUS = "FROZEN_BEFORE_PREFLIGHT_OUTCOME"

# This is intentionally the exact V0.18 TRAIN closure.  A different checkout,
# a copied shard, a VALIDATION directory, or a TEST directory is not accepted.
EXPECTED_SOURCE_ROOT = Path(
    "/home/sat/mcrl-v018-relational-learner-20260904-r1/"
    "learned-q3-panel-r1/sources/TRAIN"
)
EXPECTED_SOURCE_SCHEMA = "multi-catfish-mcrl-v018-relational-zr-source-v1"
EXPECTED_SOURCE_COUNT = 12
EXPECTED_TRAIN_WORLDS = (2026120501, 2026120502, 2026120503, 2026120504)
EXPECTED_LINEAGES = (2026092101, 2026092102, 2026092103)
EXPECTED_ROWS_PER_SOURCE = 1000
# Production Q3 initializations are each bound to one Q1/Q2 lineage.  The
# preflight authenticates the complete twelve-shard rectangle, but must not
# train one learner across three different background lineages.
SELECTED_SOURCE_LINEAGE = 2026092101
EXPECTED_SELECTED_SOURCE_COUNT = len(EXPECTED_TRAIN_WORLDS)

DEV_INITIALIZATION_SEED = 2026120491
DEV_SCHEDULE_SEED = 2026120492

EXPECTED_ACTION_DIM = 28
EXPECTED_ACTION_CONTEXT_DIM = 7
EXPECTED_VICTIM_TOKEN_DIM = 6
EXPECTED_HIDDEN_LAYERS = (100, 50, 50)
EXPECTED_ACTIVATION = "tanh"
EXPECTED_LEARNING_RATE = 0.001
EXPECTED_BATCH_SIZE = 512
EXPECTED_UPDATE_COUNT = 100
EXPECTED_BETA = 0.0
EXPECTED_KAPPA_HEX = "0x1.2cea89d260f2ap+33"
EXPECTED_KAPPA_BITS = float.fromhex(EXPECTED_KAPPA_HEX)
EXPECTED_OUTPUT_UNIT_MODE = "normalized_bits_per_kappa"

# The first predicate is deliberately 1000 * Adam's default epsilon.  It is a
# fixed conditioning check, not a threshold selected after seeing an outcome.
ADAM_EPS = 1e-8
FIRST_GRADIENT_RMS_THRESHOLD = 1000.0 * ADAM_EPS
FINAL_WINDOW = 20

_PREFLIGHT_ROOT = Path(__file__).resolve().parent
_V019_ROOT = _PREFLIGHT_ROOT.parent
_REPO_ROOT = _V019_ROOT.parents[1]
_LEARNER_ROOT = _V019_ROOT / "learner"
if str(_LEARNER_ROOT) not in sys.path:
    sys.path.insert(0, str(_LEARNER_ROOT))
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from relational_q3_learner_v019 import (  # noqa: E402
    NORMALIZED_BITS_PER_KAPPA,
    RelationalZRC3LearnerConfig,
    RelationalZRC3PairwiseLearner,
)
from relational_source_bridge import read_source_closure  # noqa: E402
from relational_source_schema import RelationalZRC3Source  # noqa: E402


class PreflightError(ValueError):
    """A source, contract, profile, or preflight receipt boundary failed."""


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise PreflightError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def file_sha256(path: str | Path) -> str:
    value = Path(path)
    if value.is_symlink() or not value.is_file():
        raise PreflightError(f"expected a regular file: {value}")
    digest = hashlib.sha256()
    with value.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _finite_float(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise PreflightError(f"{field} must be finite") from error
    if not math.isfinite(result):
        raise PreflightError(f"{field} must be finite")
    return result


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PreflightError(f"{field} must be a lowercase SHA-256 digest")
    return value


def validate_fixed_profile(profile: Mapping[str, object]) -> None:
    """Check the preflight profile without opening a source or learner."""

    expected = {
        "action_dim": EXPECTED_ACTION_DIM,
        "action_context_dim": EXPECTED_ACTION_CONTEXT_DIM,
        "victim_token_dim": EXPECTED_VICTIM_TOKEN_DIM,
        "hidden_layers": list(EXPECTED_HIDDEN_LAYERS),
        "activation": EXPECTED_ACTIVATION,
        "optimizer": "Adam",
        "learning_rate": EXPECTED_LEARNING_RATE,
        "batch_size": EXPECTED_BATCH_SIZE,
        "update_count": EXPECTED_UPDATE_COUNT,
        "beta": EXPECTED_BETA,
        "kappa_bits_hex": EXPECTED_KAPPA_HEX,
        "output_unit_mode": EXPECTED_OUTPUT_UNIT_MODE,
    }
    if set(profile) != set(expected):
        raise PreflightError("fixed profile has unknown or missing fields")
    for field, expected_value in expected.items():
        actual = profile[field]
        if field == "learning_rate":
            if _finite_float(actual, field=field) != expected_value:
                raise PreflightError(f"fixed profile {field} disagrees")
        elif field == "beta":
            if _finite_float(actual, field=field) != expected_value:
                raise PreflightError(f"fixed profile {field} disagrees")
        elif actual != expected_value:
            raise PreflightError(f"fixed profile {field} disagrees")


def validate_source_root(source_root: str | Path) -> Path:
    """Reject every source location except the already-opened V0.18 TRAIN root."""

    root = Path(source_root)
    if root.is_symlink() or not root.is_dir():
        raise PreflightError(f"TRAIN source root is not a regular directory: {root}")
    if root.absolute() != EXPECTED_SOURCE_ROOT:
        raise PreflightError(
            "source root is not the declared V0.18 TRAIN root; refusing to open it"
        )
    if root.name != "TRAIN":
        raise PreflightError("source root basename must be TRAIN")
    upper_parts = {part.upper() for part in root.parts}
    if "VALIDATION" in upper_parts or "TEST" in upper_parts:
        raise PreflightError("source root crosses VALIDATION or TEST boundary")
    return root


@dataclass(frozen=True)
class TrainSource:
    path: Path
    source: RelationalZRC3Source
    bridge: Mapping[str, object]

    @property
    def identity(self) -> tuple[int, int]:
        return int(self.source.world_seed), int(self.source.lineage)

    def hashes(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "relative_path": self.path.name,
            "world_seed": int(self.source.world_seed),
            "lineage": int(self.source.lineage),
            "rows": int(self.source.rows),
            "source_npz_sha256": file_sha256(self.path / "source.npz"),
            "source_metadata_sha256": file_sha256(self.path / "metadata.json"),
            "source_receipt_sha256": file_sha256(self.path / "source.sha256"),
            "source_arrays_sha256": self.source.arrays_sha256(),
            "bridge_metadata_sha256": _digest(
                self.bridge.get("bridge_metadata_sha256"),
                field="bridge_metadata_sha256",
            ),
            "bridge_receipt_sha256": file_sha256(self.path / "bridge.sha256"),
        }


def discover_train_sources(source_root: str | Path) -> tuple[TrainSource, ...]:
    """Authenticate exactly the declared twelve V0.18 TRAIN closures."""

    root = validate_source_root(source_root)
    children = tuple(
        sorted(
            (child for child in root.iterdir() if child.is_dir()),
            key=lambda value: value.name,
        )
    )
    if len(children) != EXPECTED_SOURCE_COUNT:
        raise PreflightError(
            f"expected exactly {EXPECTED_SOURCE_COUNT} TRAIN source closures"
        )
    found: list[TrainSource] = []
    for path in children:
        if path.is_symlink():
            raise PreflightError(f"source closure is a symlink: {path}")
        try:
            source, bridge = read_source_closure(path)
        except Exception as error:
            if isinstance(error, PreflightError):
                raise
            raise PreflightError(f"cannot authenticate TRAIN source closure: {path}") from error
        if source.schema != EXPECTED_SOURCE_SCHEMA:
            raise PreflightError("source schema is not the declared V0.18 schema")
        if source.split != "TRAIN":
            raise PreflightError("a non-TRAIN source was opened")
        if source.rows != EXPECTED_ROWS_PER_SOURCE:
            raise PreflightError("source row count disagrees with V0.18 closure")
        if float(source.kappa_bits).hex() != EXPECTED_KAPPA_HEX:
            raise PreflightError("source kappa disagrees with the fixed kappa")
        expected_name = f"{source.world_seed}-{source.lineage}"
        if path.name != expected_name:
            raise PreflightError("source directory name disagrees with its identity")
        found.append(TrainSource(path=path, source=source, bridge=bridge))
    ordered = tuple(sorted(found, key=lambda item: item.identity))
    expected = {
        (world, lineage)
        for world in EXPECTED_TRAIN_WORLDS
        for lineage in EXPECTED_LINEAGES
    }
    if {item.identity for item in ordered} != expected:
        raise PreflightError("TRAIN source identities are not the declared rectangle")
    if any(item.source.split != "TRAIN" for item in ordered):
        raise PreflightError("TRAIN-only source invariant failed")
    return ordered


def select_preflight_lineage(
    sources: Sequence[TrainSource],
    *,
    lineage: int = SELECTED_SOURCE_LINEAGE,
) -> tuple[TrainSource, ...]:
    """Select the predeclared single background lineage after full census."""

    if lineage != SELECTED_SOURCE_LINEAGE:
        raise PreflightError("preflight source lineage is not the declared development lineage")
    selected = tuple(item for item in sources if item.source.lineage == lineage)
    expected = {
        (world, SELECTED_SOURCE_LINEAGE) for world in EXPECTED_TRAIN_WORLDS
    }
    if {item.identity for item in selected} != expected:
        raise PreflightError("selected TRAIN lineage is not a complete four-world rectangle")
    return tuple(sorted(selected, key=lambda item: item.identity))


@dataclass(frozen=True)
class ScheduledBatch:
    update: int
    source_index: int
    row_indices: tuple[int, ...]

    def as_dict(self, *, source: TrainSource) -> dict[str, object]:
        return {
            "update": self.update,
            "source_relative_path": source.path.name,
            "world_seed": int(source.source.world_seed),
            "lineage": int(source.source.lineage),
            "row_indices_sha256": hashlib.sha256(
                np.asarray(self.row_indices, dtype=np.int64).tobytes(order="C")
            ).hexdigest(),
            "row_count": len(self.row_indices),
        }


def build_schedule(
    *,
    source_count: int = EXPECTED_SELECTED_SOURCE_COUNT,
    rows_per_source: int = EXPECTED_ROWS_PER_SOURCE,
    update_count: int = EXPECTED_UPDATE_COUNT,
    batch_size: int = EXPECTED_BATCH_SIZE,
    schedule_seed: int = DEV_SCHEDULE_SEED,
    selected_lineage: int = SELECTED_SOURCE_LINEAGE,
) -> tuple[ScheduledBatch, ...]:
    """Build one deterministic, source-balanced, no-replacement schedule."""

    if source_count != EXPECTED_SELECTED_SOURCE_COUNT:
        raise PreflightError(
            "source_count disagrees with the selected single-lineage TRAIN closure"
        )
    if rows_per_source != EXPECTED_ROWS_PER_SOURCE:
        raise PreflightError("rows_per_source disagrees with the V0.18 closure")
    if update_count != EXPECTED_UPDATE_COUNT or batch_size != EXPECTED_BATCH_SIZE:
        raise PreflightError("preflight update or batch count is not fixed")
    if schedule_seed != DEV_SCHEDULE_SEED:
        raise PreflightError("schedule seed is not the declared development seed")
    if selected_lineage != SELECTED_SOURCE_LINEAGE:
        raise PreflightError("selected source lineage is not the declared development lineage")
    rng = np.random.default_rng(schedule_seed)
    batches: list[ScheduledBatch] = []
    for update in range(1, update_count + 1):
        source_index = (update - 1) % source_count
        indices = tuple(
            int(index)
            for index in rng.choice(rows_per_source, size=batch_size, replace=False)
        )
        batches.append(
            ScheduledBatch(
                update=update,
                source_index=source_index,
                row_indices=indices,
            )
        )
    return tuple(batches)


def global_gradient_rms(parameters: Sequence[torch.Tensor]) -> float:
    """Return RMS over every finite gradient element, before Adam.step()."""

    sum_sq = 0.0
    count = 0
    for gradient in parameters:
        if gradient.grad is None:
            continue
        value = gradient.grad.detach().to(dtype=torch.float64)
        if not bool(torch.isfinite(value).all()):
            raise PreflightError("non-finite learner gradient")
        sum_sq += float(torch.sum(value * value).cpu())
        count += int(value.numel())
    if count == 0:
        raise PreflightError("first batch produced no gradients")
    result = math.sqrt(sum_sq / count)
    if not math.isfinite(result):
        raise PreflightError("gradient RMS is non-finite")
    return result


def zero_null_pair_mse(
    source: RelationalZRC3Source,
    indices: Sequence[int],
) -> float:
    """Compute the same legal non-reference pair MSE for an all-zero Q3."""

    selected = np.asarray(indices, dtype=np.int64)
    targets = np.asarray(source.target_surface_bits)[selected] / EXPECTED_KAPPA_BITS
    references = np.asarray(source.reference_actions, dtype=np.int64)[selected]
    legal = np.asarray(source.action_mask, dtype=np.bool_)[selected].copy()
    rows = np.arange(selected.size, dtype=np.int64)
    legal[rows, references] = False
    residual = targets - targets[rows, references, None]
    values = residual[legal]
    if values.size == 0:
        raise PreflightError("source batch contains no legal non-reference comparisons")
    result = float(np.mean(np.square(values, dtype=np.float64)))
    if not math.isfinite(result):
        raise PreflightError("ZERO-null MSE is non-finite")
    return result


def _update_with_diagnostics(
    learner: RelationalZRC3PairwiseLearner,
    source: RelationalZRC3Source,
    indices: Sequence[int],
) -> dict[str, float | int]:
    """Perform one update while exposing the pre-step gradient condition."""

    _validated, arrays = learner._arrays(source, indices)  # intentional seam use
    learner.q3.train()
    loss, pair_mse, gauge_mse, comparisons = learner._surface_loss(arrays)
    learner.optimizer.zero_grad(set_to_none=True)
    loss.backward()
    gradient_rms = global_gradient_rms(tuple(learner.q3.parameters()))
    learner._finite_parameters(learner.q3)
    with torch.no_grad():
        output = learner.q3(*(
            torch.tensor(arrays[name], dtype=dtype)
            for name, dtype in (
                ("action_context", torch.float32),
                ("victim_tokens", torch.float32),
                ("action_mask", torch.bool),
                ("victim_mask", torch.bool),
                ("positive_credit_compatible", torch.bool),
                ("reference_actions", torch.int64),
            )
        ))
        output_std = float(output.std().cpu())
    learner.optimizer.step()
    learner._finite_parameters(learner.q3)
    learner.update_count += 1
    return {
        "pair_mse": float(pair_mse.detach().cpu()),
        "zero_null_pair_mse": zero_null_pair_mse(source, indices),
        "gauge_mse": float(gauge_mse.detach().cpu()),
        "loss": float(loss.detach().cpu()),
        "comparisons": int(comparisons),
        "gradient_rms": gradient_rms,
        "output_std": output_std,
        "update_count": learner.update_count,
    }


def _profile_payload() -> dict[str, object]:
    return {
        "action_dim": EXPECTED_ACTION_DIM,
        "action_context_dim": EXPECTED_ACTION_CONTEXT_DIM,
        "victim_token_dim": EXPECTED_VICTIM_TOKEN_DIM,
        "hidden_layers": list(EXPECTED_HIDDEN_LAYERS),
        "activation": EXPECTED_ACTIVATION,
        "optimizer": "Adam",
        "learning_rate": EXPECTED_LEARNING_RATE,
        "batch_size": EXPECTED_BATCH_SIZE,
        "update_count": EXPECTED_UPDATE_COUNT,
        "beta": EXPECTED_BETA,
        "kappa_bits_hex": EXPECTED_KAPPA_HEX,
        "output_unit_mode": EXPECTED_OUTPUT_UNIT_MODE,
    }


def _read_preflight_files() -> tuple[str, str]:
    contract = _PREFLIGHT_ROOT / "MULTI-CATFISH-MCRL-V019-TRAIN-PREFLIGHT-CONTRACT-2026-09-04.md"
    census = _PREFLIGHT_ROOT / "SEED-CENSUS-DEV-2026-09-04.md"
    for path in (contract, census):
        if path.is_symlink() or not path.is_file():
            raise PreflightError(f"required pre-outcome file is missing: {path}")
    text = contract.read_text(encoding="utf-8")
    if f"Status: `{CONTRACT_STATUS}`" not in text:
        raise PreflightError("preflight contract is not marked pre-outcome draft")
    if (
        str(DEV_INITIALIZATION_SEED) not in text
        or str(DEV_SCHEDULE_SEED) not in text
        or str(SELECTED_SOURCE_LINEAGE) not in text
        or str(EXPECTED_SOURCE_ROOT) not in text
    ):
        raise PreflightError("development seeds are not declared in the contract")
    return file_sha256(contract), file_sha256(census)


def _base_receipt(*, contract_sha256: str | None, census_sha256: str | None) -> dict[str, object]:
    return {
        "schema": PREFLIGHT_SCHEMA,
        "schema_version": PREFLIGHT_VERSION,
        "status": "ABORTED",
        "decision": "ABORT",
        "claim_ceiling": "IMPLEMENTATION_TRAIN_ONLY_CONDITIONING_PREFLIGHT_NO_EFFICACY_CLAIM",
        "preflight_contract_sha256": contract_sha256,
        "seed_census_sha256": census_sha256,
        "source_root": str(EXPECTED_SOURCE_ROOT),
        "source_split": "TRAIN",
        "source_count": 0,
        "source_hashes": [],
        "selected_source_lineage": SELECTED_SOURCE_LINEAGE,
        "selected_source_count": 0,
        "development_seeds": {
            "initialization_seed": DEV_INITIALIZATION_SEED,
            "schedule_seed": DEV_SCHEDULE_SEED,
        },
        "fixed_hyperparameters": _profile_payload(),
        "predicates": {
            "first_valid_batch_gradient_rms_threshold": FIRST_GRADIENT_RMS_THRESHOLD,
            "final_window_updates": FINAL_WINDOW,
            "first_valid_batch_gradient_rms": None,
            "first_gradient_rms_pass": False,
            "last20_mean_train_pair_mse": None,
            "last20_mean_zero_null_pair_mse": None,
            "last20_pair_mse_below_zero_null": False,
        },
        "diagnostics": {"updates": [], "parameter_move_l2": None},
        "updates_completed": 0,
        "q1_q2": {"loaded": False, "updated": False},
        "boundary": {
            "opened_splits": [],
            "validation_read": False,
            "test_split_opened": False,
            "simulator_run": False,
            "source_harvest_run": False,
            "episode_training": False,
        },
    }


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise PreflightError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def _write_receipt(output_root: Path, body: Mapping[str, object]) -> dict[str, object]:
    # Keep two distinct identities: the JSON field authenticates the receipt
    # body before the field is added, while the companion file authenticates
    # the exact bytes written to receipt.json (the value accepted by
    # ``sha256sum -c``).
    payload = {**dict(body), "receipt_body_sha256": canonical_sha256(body)}
    encoded = _canonical_bytes(payload)
    _write_once(output_root / "receipt.json", encoded)
    receipt_file_sha256 = hashlib.sha256(encoded).hexdigest()
    _write_once(
        output_root / "receipt.sha256",
        f"{receipt_file_sha256}  receipt.json\n".encode("ascii"),
    )
    return payload


def run_preflight(
    *,
    source_root: str | Path = EXPECTED_SOURCE_ROOT,
    output_root: str | Path,
) -> dict[str, object]:
    """Run the fixed 100-update TRAIN-only preflight and write one receipt."""

    destination = Path(output_root)
    if destination.exists() or destination.is_symlink():
        raise PreflightError(f"refusing to overwrite preflight output: {destination}")
    destination.mkdir(parents=True, exist_ok=False)

    contract_sha256: str | None = None
    census_sha256: str | None = None
    body = _base_receipt(contract_sha256=None, census_sha256=None)
    try:
        contract_sha256, census_sha256 = _read_preflight_files()
        body["preflight_contract_sha256"] = contract_sha256
        body["seed_census_sha256"] = census_sha256
        validate_fixed_profile(body["fixed_hyperparameters"])  # type: ignore[arg-type]
        if DEV_INITIALIZATION_SEED == DEV_SCHEDULE_SEED:
            raise PreflightError("development initialization and schedule seeds must differ")
        # Materialise the fixed schedule before opening any persisted target
        # surface.  It depends only on the predeclared source cardinality and
        # the development schedule seed, never on source outcomes.
        schedule = build_schedule(
            source_count=EXPECTED_SELECTED_SOURCE_COUNT,
            schedule_seed=DEV_SCHEDULE_SEED,
            selected_lineage=SELECTED_SOURCE_LINEAGE,
        )
        sources = discover_train_sources(source_root)
        body["source_count"] = len(sources)
        body["source_hashes"] = [item.hashes() for item in sources]
        selected_sources = select_preflight_lineage(sources)
        body["selected_source_count"] = len(selected_sources)
        body["boundary"] = {
            "opened_splits": ["TRAIN"],
            "validation_read": False,
            "test_split_opened": False,
            "simulator_run": False,
            "source_harvest_run": False,
            "episode_training": False,
        }
        if len(selected_sources) != len({batch.source_index for batch in schedule}):
            raise PreflightError("selected source rectangle disagrees with the fixed schedule")
        config = RelationalZRC3LearnerConfig(
            action_dim=EXPECTED_ACTION_DIM,
            action_context_dim=EXPECTED_ACTION_CONTEXT_DIM,
            victim_token_dim=EXPECTED_VICTIM_TOKEN_DIM,
            hidden_layers=EXPECTED_HIDDEN_LAYERS,
            activation=EXPECTED_ACTIVATION,
            learning_rate=EXPECTED_LEARNING_RATE,
            kappa_bits=EXPECTED_KAPPA_BITS,
            beta=EXPECTED_BETA,
            output_unit_mode=NORMALIZED_BITS_PER_KAPPA,
        )
        learner = RelationalZRC3PairwiseLearner(
            config,
            train_seed=DEV_INITIALIZATION_SEED,
            device="cpu",
        )
        initial_parameters = {
            name: value.detach().clone()
            for name, value in learner.q3.state_dict().items()
        }
        updates: list[dict[str, object]] = []
        for batch in schedule:
            source = selected_sources[batch.source_index].source
            report = _update_with_diagnostics(
                learner,
                source,
                batch.row_indices,
            )
            updates.append(
                {
                    **batch.as_dict(source=selected_sources[batch.source_index]),
                    **report,
                }
            )
        if learner.update_count != EXPECTED_UPDATE_COUNT:
            raise PreflightError("learner did not complete exactly 100 updates")
        first_gradient = float(updates[0]["gradient_rms"])
        final_updates = updates[-FINAL_WINDOW:]
        final_pair = float(np.mean([float(item["pair_mse"]) for item in final_updates]))
        final_zero = float(
            np.mean([float(item["zero_null_pair_mse"]) for item in final_updates])
        )
        first_pass = first_gradient >= FIRST_GRADIENT_RMS_THRESHOLD
        final_pass = final_pair < final_zero
        moved_sq = 0.0
        for name, value in learner.q3.state_dict().items():
            delta = value.detach().to(dtype=torch.float64) - initial_parameters[name].to(dtype=torch.float64)
            moved_sq += float(torch.sum(delta * delta).cpu())
        body["status"] = "COMPLETED"
        body["decision"] = "GO_FRESH_GATE" if first_pass and final_pass else "ABORT"
        body["predicates"] = {
            "first_valid_batch_gradient_rms_threshold": FIRST_GRADIENT_RMS_THRESHOLD,
            "final_window_updates": FINAL_WINDOW,
            "first_valid_batch_gradient_rms": first_gradient,
            "first_gradient_rms_pass": first_pass,
            "last20_mean_train_pair_mse": final_pair,
            "last20_mean_zero_null_pair_mse": final_zero,
            "last20_pair_mse_below_zero_null": final_pass,
        }
        body["diagnostics"] = {
            "updates": updates,
            "parameter_move_l2": math.sqrt(moved_sq),
            "final_output_std": float(updates[-1]["output_std"]),
        }
        body["updates_completed"] = learner.update_count
        return _write_receipt(destination, body)
    except Exception as error:
        if isinstance(error, PreflightError):
            message = str(error)
        else:
            message = f"{type(error).__name__}: {error}"
        body["status"] = "ABORTED"
        body["decision"] = "ABORT"
        body["error"] = message
        body["preflight_contract_sha256"] = contract_sha256
        body["seed_census_sha256"] = census_sha256
        return _write_receipt(destination, body)


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        default=str(EXPECTED_SOURCE_ROOT),
        help="the exact already-opened V0.18 TRAIN source root",
    )
    parser.add_argument("--output", required=True, help="new receipt directory")
    arguments = parser.parse_args(argv)
    try:
        result = run_preflight(
            source_root=arguments.source_root,
            output_root=arguments.output,
        )
    except (OSError, PreflightError) as error:
        parser.error(str(error))
    return 0 if result["decision"] == "GO_FRESH_GATE" else 2


__all__ = [
    "ADAM_EPS",
    "DEV_INITIALIZATION_SEED",
    "DEV_SCHEDULE_SEED",
    "EXPECTED_KAPPA_BITS",
    "EXPECTED_KAPPA_HEX",
    "EXPECTED_OUTPUT_UNIT_MODE",
    "EXPECTED_SOURCE_ROOT",
    "SELECTED_SOURCE_LINEAGE",
    "FINAL_WINDOW",
    "FIRST_GRADIENT_RMS_THRESHOLD",
    "PreflightError",
    "ScheduledBatch",
    "TrainSource",
    "build_schedule",
    "canonical_sha256",
    "discover_train_sources",
    "file_sha256",
    "global_gradient_rms",
    "run_preflight",
    "select_preflight_lineage",
    "validate_fixed_profile",
    "validate_source_root",
    "zero_null_pair_mse",
]


if __name__ == "__main__":  # pragma: no cover - server entry point
    raise SystemExit(_main())
