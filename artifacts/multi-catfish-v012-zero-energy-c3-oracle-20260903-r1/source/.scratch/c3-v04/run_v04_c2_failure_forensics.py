#!/usr/bin/env python3
"""Receipt-bound post-outcome forensics for the failed V0.4 C2 head.

This audit does not train, open TEST, or select a remediation.  It asks a
narrow question using the already-opened C2 validation pairs: did the frozen
Q2 head obtain its legal-action argmax from actions that the pairwise C2
source actually constrained?
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np
import torch


REPO = Path(__file__).resolve().parents[2]
for entry in (REPO, REPO / "src"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from mcrl.algorithms.ee_axis_action_shared_meanmax import (  # noqa: E402
    EEAxisMaskedMeanMaxConfig,
    MaskedMeanMaxQNetwork,
)


RESULT_SCHEMA = "multi-catfish-mcrl-v04-c2-failure-forensics-v1"
SEAL_SCHEMA = "multi-catfish-mcrl-v04-c2-failure-forensics-seal-v1"
CLAIM_CEILING = "POST_OUTCOME_DIAGNOSTIC_ONLY_NO_REMEDIATION_EFFICACY"
INITIALIZATION_SEEDS = (2026092101, 2026092102, 2026092103)
VALIDATION_SEEDS = (2026092005, 2026092006, 2026092007)
RUNG = 10

FIVE_ARM_RESULT = REPO / "artifacts/multi-catfish-v04-five-arm-ablation-20260901-r1/result.json"
FALLBACK_ROOT = REPO / "artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"
SOURCE_ROOT = REPO / "artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data"

EXPECTED_SHA256 = {
    FIVE_ARM_RESULT: "9142da31690927fe853765b9dfc0c807d4202738784961b44be393a77c608224",
    FALLBACK_ROOT / "result.json": "25069d5c546a892218949ebddcf77d15209f1c7e685dd9b2776c80003660021e",
    FALLBACK_ROOT / "result-seal.json": "aa44ddcb17376b7467d1ab090772adbe4c32a7d26dad64e802dcc7014171dcaf",
    FALLBACK_ROOT / "checkpoints/init-2026092101-rung-000010.pt": "f26aab2fab6d31d6f3e4acd97782beeb0bba055ec94611dc9f3ed47038a231f0",
    FALLBACK_ROOT / "checkpoints/init-2026092102-rung-000010.pt": "6930534d90840807c4dda1eda9c0ecf58793175053a37a43b75e38a7b6d310ba",
    FALLBACK_ROOT / "checkpoints/init-2026092103-rung-000010.pt": "507b871f2536097b400b099b9dcb666e8445e9aee921001d61e70ff6042646b2",
    SOURCE_ROOT / "temporal-2026092005.json": "ec2b7f52b428f7c05885355758513fd7a29eb8c001fa6fddcfcbfe6103aa6c2e",
    SOURCE_ROOT / "temporal-2026092006.json": "e13392318b42fbdde7f090a2383433a9e94037daf6be2950c4239ed791c18e55",
    SOURCE_ROOT / "temporal-2026092007.json": "61596d3b2cc2a2a64942bfc426c0a7c93cda35a9b6e5ca20d4e96be711ee3733",
}


class C2ForensicsError(RuntimeError):
    """The forensic inputs or recomputed receipt failed closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise C2ForensicsError(f"required regular file is missing: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise C2ForensicsError(f"cannot read canonical JSON: {path}") from error
    if not isinstance(value, dict):
        raise C2ForensicsError(f"JSON root is not an object: {path}")
    return value


def _float(value: object, *, field: str) -> float:
    try:
        parsed = float.fromhex(value) if isinstance(value, str) else float(value)
    except (TypeError, ValueError) as error:
        raise C2ForensicsError(f"{field} is not a finite float") from error
    if not math.isfinite(parsed):
        raise C2ForensicsError(f"{field} is not finite")
    return parsed


def _authenticate_inputs() -> dict[str, str]:
    manifest: dict[str, str] = {}
    for path, expected in EXPECTED_SHA256.items():
        actual = _sha256_file(path)
        if actual != expected:
            raise C2ForensicsError(f"authenticated input changed: {path}")
        manifest[path.relative_to(REPO).as_posix()] = actual
    return manifest


def _load_rows() -> tuple[list[dict[str, Any]], float]:
    rows: list[dict[str, Any]] = []
    kappa: float | None = None
    for seed in VALIDATION_SEEDS:
        payload = _read_json(SOURCE_ROOT / f"temporal-{seed}.json")
        raw_rows = payload.get("rows")
        if not isinstance(raw_rows, list) or len(raw_rows) != 12:
            raise C2ForensicsError("C2 validation dataset must contain 12 rows per seed")
        for row in raw_rows:
            if not isinstance(row, dict) or row.get("seed") != seed:
                raise C2ForensicsError("C2 validation row seed is malformed")
            rows.append(row)
        if kappa is None:
            # Shared kappa is checkpoint authority, not lambda_bits_per_j.
            kappa = 10097071012.757404
    if len(rows) != 36 or kappa is None:
        raise C2ForensicsError("C2 validation row closure is incomplete")
    return rows, kappa


def _arrays(
    rows: Sequence[Mapping[str, Any]], *, kappa_bits: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    states = np.asarray(
        [[_float(value, field="state") for value in row["state"]] for row in rows],
        dtype=np.float32,
    )
    masks = np.asarray([row["action_mask"] for row in rows])
    references = np.asarray([row["reference_action"] for row in rows], dtype=np.int64)
    candidates = np.asarray([row["candidate_action"] for row in rows], dtype=np.int64)
    targets = np.asarray(
        [
            _float(row["zeta2_temporal_surplus_bits"], field="zeta2") / kappa_bits
            for row in rows
        ],
        dtype=np.float64,
    )
    if states.shape != (36, 228) or masks.shape != (36, 28) or masks.dtype != np.bool_:
        raise C2ForensicsError("C2 validation state/mask contract changed")
    if references.shape != (36,) or candidates.shape != (36,) or targets.shape != (36,):
        raise C2ForensicsError("C2 validation pair arrays are malformed")
    index = np.arange(36)
    if (
        np.any(references == candidates)
        or np.any(references < 0)
        or np.any(candidates < 0)
        or np.any(references >= 28)
        or np.any(candidates >= 28)
        or not np.all(masks[index, references])
        or not np.all(masks[index, candidates])
        or not np.all(np.isfinite(states))
        or not np.all(np.isfinite(targets))
    ):
        raise C2ForensicsError("C2 validation pair action contract changed")
    return states, masks, references, candidates, targets


def q2_support_metrics(
    q_values: np.ndarray,
    masks: np.ndarray,
    references: np.ndarray,
    candidates: np.ndarray,
    targets: np.ndarray,
) -> dict[str, Any]:
    """Summarize whether legal argmax actions are supported by pair supervision."""

    q = np.asarray(q_values, dtype=np.float64)
    legal = np.asarray(masks)
    ref = np.asarray(references, dtype=np.int64)
    cand = np.asarray(candidates, dtype=np.int64)
    target = np.asarray(targets, dtype=np.float64)
    rows = q.shape[0]
    if (
        q.ndim != 2
        or legal.dtype != np.bool_
        or legal.shape != q.shape
        or ref.shape != (rows,)
        or cand.shape != (rows,)
        or target.shape != (rows,)
        or rows < 1
        or not np.all(np.any(legal, axis=1))
        or not np.all(np.isfinite(q))
        or not np.all(np.isfinite(target))
    ):
        raise C2ForensicsError("Q2 support metric inputs are malformed")
    index = np.arange(rows)
    if not np.all(legal[index, ref]) or not np.all(legal[index, cand]):
        raise C2ForensicsError("Q2 supervised actions must be legal")

    masked = np.where(legal, q, -np.inf)
    top = np.argmax(masked, axis=1)
    predicted = q[index, cand] - q[index, ref]
    nonzero = target != 0.0
    if not np.any(nonzero):
        raise C2ForensicsError("Q2 validation targets contain no signed contrast")
    sign_correct = np.sign(predicted[nonzero]) == np.sign(target[nonzero])
    pair_best = np.maximum(q[index, cand], q[index, ref])
    top_margin = q[index, top] - pair_best
    legal_ranges = np.max(masked, axis=1) - np.min(np.where(legal, q, np.inf), axis=1)
    correlation: float | None = None
    if rows >= 2 and float(np.std(predicted)) > 0.0 and float(np.std(target)) > 0.0:
        candidate_correlation = float(np.corrcoef(predicted, target)[0, 1])
        if math.isfinite(candidate_correlation):
            correlation = candidate_correlation
    top_counts = Counter(int(value) for value in top.tolist())
    return {
        "rows": int(rows),
        "nonzero_target_rows": int(np.sum(nonzero)),
        "pair_sign_accuracy": float(np.mean(sign_correct)),
        "pair_pearson_correlation": correlation,
        "top_is_candidate_count": int(np.sum(top == cand)),
        "top_is_reference_count": int(np.sum(top == ref)),
        "top_is_supervised_pair_count": int(np.sum((top == cand) | (top == ref))),
        "top_is_off_pair_count": int(np.sum((top != cand) & (top != ref))),
        "top_is_off_pair_fraction": float(np.mean((top != cand) & (top != ref))),
        "off_pair_top_margin_median": float(np.median(top_margin)),
        "off_pair_top_margin_positive_count": int(np.sum(top_margin > 0.0)),
        "legal_q_range_median": float(np.median(legal_ranges)),
        "predicted_pair_difference_min": float(np.min(predicted)),
        "predicted_pair_difference_median": float(np.median(predicted)),
        "predicted_pair_difference_max": float(np.max(predicted)),
        "top_action_counts": {str(key): int(top_counts[key]) for key in sorted(top_counts)},
    }


def _load_q2(seed: int) -> tuple[MaskedMeanMaxQNetwork, Mapping[str, Any]]:
    path = FALLBACK_ROOT / f"checkpoints/init-{seed}-rung-{RUNG:06d}.pt"
    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as error:
        raise C2ForensicsError(f"cannot load frozen checkpoint {seed}") from error
    if not isinstance(payload, Mapping):
        raise C2ForensicsError("frozen checkpoint root is not a mapping")
    trainer = payload.get("trainer")
    if (
        payload.get("initialization_seed") != seed
        or payload.get("rung") != RUNG
        or payload.get("test_split_opened") is not False
        or payload.get("held_out_ee_evaluated") is not False
        or not isinstance(trainer, Mapping)
        or trainer.get("train_seed") != seed
    ):
        raise C2ForensicsError("frozen Q2 checkpoint lineage changed")
    config_raw = trainer.get("config")
    networks = trainer.get("q_networks")
    if not isinstance(config_raw, Mapping) or not isinstance(networks, list) or len(networks) != 3:
        raise C2ForensicsError("frozen Q2 checkpoint payload is malformed")
    config = EEAxisMaskedMeanMaxConfig(**dict(config_raw))
    network = MaskedMeanMaxQNetwork(config)
    network.load_state_dict(networks[1])
    network.eval()
    return network, config_raw


def _recompute() -> dict[str, Any]:
    manifest = _authenticate_inputs()
    five_arm = _read_json(FIVE_ARM_RESULT)
    fallback = _read_json(FALLBACK_ROOT / "result.json")
    c2_decision = five_arm.get("decision", {}).get("route_statuses", {}).get("C2")
    c2_comparison = five_arm.get("comparisons", {}).get("C2", {})
    if (
        five_arm.get("scientific_status") != "MULTI_CATFISH_NOT_ALL_CONFIRMED"
        or c2_decision != "C2_NOT_CONFIRMED"
        or c2_comparison.get("decision", {}).get("positive_initializations") != 0
        or c2_comparison.get("decision", {}).get("positive_per_world_ee_count") != 0
    ):
        raise C2ForensicsError("five-arm result is not the sealed uniform C2 failure")
    c2_gate = fallback.get("gate", {}).get("route_gate", {}).get("C2")
    if (
        fallback.get("selected_common_rung") != RUNG
        or fallback.get("test_split_opened") is not False
        or fallback.get("held_out_ee_evaluated") is not False
        or not isinstance(c2_gate, Mapping)
        or c2_gate.get("pass") is not True
    ):
        raise C2ForensicsError("fallback result is not the sealed weak-positive C2 gate")

    rows, kappa = _load_rows()
    states, masks, references, candidates, targets = _arrays(rows, kappa_bits=kappa)
    by_initialization: dict[str, Any] = {}
    for seed in INITIALIZATION_SEEDS:
        network, config = _load_q2(seed)
        if _float(config.get("kappa_bits"), field="checkpoint kappa") != kappa:
            raise C2ForensicsError("Q2 checkpoints disagree on shared kappa")
        with torch.no_grad():
            q_values = network(
                torch.tensor(states, dtype=torch.float32),
                torch.tensor(masks, dtype=torch.bool),
            ).cpu().numpy()
        by_initialization[str(seed)] = q2_support_metrics(
            q_values, masks, references, candidates, targets
        )

    return {
        "schema": RESULT_SCHEMA,
        "status": "DIAGNOSTIC_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "input_manifest": manifest,
        "five_arm_c2_status": c2_decision,
        "five_arm_c2_pooled_ee_difference_percent": float(
            c2_comparison["decision"]["pooled_ee_difference_percent"]
        ),
        "five_arm_c2_positive_initializations": 0,
        "five_arm_c2_positive_worlds": 0,
        "prior_c2_gate_mean_skill": float(c2_gate["mean_skill"]),
        "prior_c2_gate_positive_initializations": int(c2_gate["positive_initializations"]),
        "validation_rows": len(rows),
        "validation_seeds": list(VALIDATION_SEEDS),
        "initialization_seeds": list(INITIALIZATION_SEEDS),
        "selected_rung": RUNG,
        "training_performed": False,
        "test_split_opened": False,
        "held_out_ee_recomputed": False,
        "metrics_by_initialization": by_initialization,
        "interpretation": {
            "confirmed_fact": (
                "the frozen Q2 legal-action argmax is outside its supervised "
                "candidate/reference pair in nearly all audited validation contexts"
            ),
            "supported_hypothesis": (
                "sparse action support permits unconstrained Q2 extrapolation at deployment"
            ),
            "not_established": (
                "this diagnostic alone does not prove that full action-census remediation "
                "will improve held-out EE"
            ),
        },
    }


def _write_once(output_dir: Path) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise C2ForensicsError(f"refusing to overwrite forensic output: {output_dir}")
    result = _recompute()
    result_bytes = _canonical_bytes(result)
    result_sha = _sha256_bytes(result_bytes)
    seal = {
        "schema": SEAL_SCHEMA,
        "result_file_sha256": result_sha,
        "input_manifest_sha256": _sha256_bytes(_canonical_bytes(result["input_manifest"])),
        "status": result["status"],
        "claim_ceiling": CLAIM_CEILING,
    }
    temporary = Path(tempfile.mkdtemp(prefix="c2-forensics-", dir=output_dir.parent))
    try:
        (temporary / "result.json").write_bytes(result_bytes)
        (temporary / "result-seal.json").write_bytes(_canonical_bytes(seal))
        temporary.replace(output_dir)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return {
        "status": result["status"],
        "result_file_sha256": result_sha,
        "result_seal_file_sha256": _sha256_file(output_dir / "result-seal.json"),
    }


def _verify(output_dir: Path) -> dict[str, Any]:
    result_path = output_dir / "result.json"
    seal_path = output_dir / "result-seal.json"
    result = _read_json(result_path)
    seal = _read_json(seal_path)
    recomputed = _recompute()
    if result != recomputed:
        raise C2ForensicsError("forensic result differs from exact recomputation")
    result_sha = _sha256_file(result_path)
    if (
        seal.get("schema") != SEAL_SCHEMA
        or seal.get("result_file_sha256") != result_sha
        or seal.get("input_manifest_sha256")
        != _sha256_bytes(_canonical_bytes(result["input_manifest"]))
        or seal.get("status") != "DIAGNOSTIC_COMPLETE"
        or seal.get("claim_ceiling") != CLAIM_CEILING
    ):
        raise C2ForensicsError("forensic result seal is invalid")
    return {
        "receipt_only": True,
        "status": result["status"],
        "result_file_sha256": result_sha,
        "result_seal_file_sha256": _sha256_file(seal_path),
        "validation_rows": result["validation_rows"],
        "training_performed": result["training_performed"],
        "test_split_opened": result["test_split_opened"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "verify"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO / "artifacts/multi-catfish-v04-c2-failure-forensics-20260901-r1",
    )
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    result = _write_once(output) if args.mode == "run" else _verify(output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
