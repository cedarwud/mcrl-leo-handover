#!/usr/bin/env python3
"""Read-only attestation for the V0.23 Q1/Q2 background artifacts.

This module deliberately stops at source/checkpoint authentication.  It does
not import a simulator, call a source selector, sample a neutral source, or
fit a learner.  Its purpose is to make the V0.20 bytes that V0.23 binds to
easy to reopen and to report why those bytes are not yet V0.23 pre-decision
C1/C2 source selections.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

V023_CONTRACT = REPO / "docs" / "MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md"
V023_CONTRACT_SHA256 = "1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"

V020_ROOT = REPO / ".scratch" / "multi-catfish-v020-c3-source-audit"
V020_EXECUTION_CONTRACT = V020_ROOT / "Q1-Q2-REPRICED-SUPERVISED-EXECUTION-CONTRACT-2026-09-04.md"
V020_EXECUTION_CONTRACT_SHA256 = "ea36414aac87b3ef5ba48dbe753e73ff21a0e164d54cdb3edbb899b509edd48c"
V020_REPRICING_CONTRACT = V020_ROOT / "Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md"
V020_REPRICING_CONTRACT_SHA256 = "34732dd3f65ffebf760313c2ffd235e0ecbd406ba6065dbce5635778550ef4a9"

Q1_REPRICE_ROOT = V020_ROOT / "q1-repricing"
Q1_RECEIPT = Q1_REPRICE_ROOT / "receipt.json"
Q1_RECEIPT_SHA256 = "31f86b100fd5defabc9443e9c80e1e1c533993269be6f3ea3840d06c70f3b08c"
Q1_MANIFEST = Q1_REPRICE_ROOT / "MANIFEST.sha256"
Q1_MANIFEST_SHA256 = "77bc791a09b613116ad440d56bedb5d94485867eeb3d7a2485ff12832666223c"

E1_ARTIFACT = REPO / "artifacts" / "multi-catfish-v03-e1-action-shared-supplement-20260901"
E1_SOURCE_ROOT = E1_ARTIFACT / "source-data"
E1_SOURCE_RECEIPT = E1_SOURCE_ROOT / "receipt.json"
E1_SOURCE_MANIFEST = E1_ARTIFACT / "source-manifest.json"
E1_SOURCE_MANIFEST_SHA256 = "9ec832c71b29ad84e37856db1f5d237f07d177c62cc93fbb66de06d808184a0a"

Q2_BATCH_ROOT = V020_ROOT / "q2-batch-repricing"
Q2_BATCH_RESULT = Q2_BATCH_ROOT / "result.json"
Q2_BATCH_RESULT_SHA256 = "4095380579d91661a40ae37f64a0c05fccdbe26f01f1cbb546f41a7e55234733"
Q2_BATCH_RESULT_SEAL = Q2_BATCH_ROOT / "result.sha256"
Q2_SOURCE_ROOT = REPO / "artifacts" / "multi-catfish-v014-learnability-20260903-r1" / "server-run" / "source-panel" / "shards"

LINEAGE_ROOT = V020_ROOT / "repriced-q1-q2-fit" / "lineage-2026092101"
AUTHORITY = LINEAGE_ROOT / "authority.json"
AUTHORITY_FILE_SHA256 = "a05ee801c8f9d640b55f8ec984d874f149c30b868d1706d998f7e2053520078e"
AUTHORITY_BODY_SHA256 = "50d32dae11b2906bb23a25893f4ba5c11d0f88197ee94fe7cd216677e8703d48"
FIT_RESULT = LINEAGE_ROOT / "result.json"
FIT_RESULT_SHA256 = "2c855edbf1157f12c158fae61728c5d385a82e6856feb280a900fc8ad8e70b99"
FIT_STATUS = LINEAGE_ROOT / "status.json"
FIT_STATUS_SHA256 = "cf088fb962b4085fee3c2791fff4a3cbcf501729bad984a8bb6d7712188a0a82"
Q1_Q2_REFERENCE_ACTIONS = LINEAGE_ROOT / "repriced-q1-q2-reference-actions.npz"
Q1_Q2_REFERENCE_ACTIONS_SHA256 = "b9697389d282c088c48bb380a16dc28f0675a29706313b6a91cb6bee342cbcc0"
DEPLOYMENT_CHECKPOINT_SHA256 = "d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc"
Q1_RUNG_10_CHECKPOINT_SHA256 = "c6c358555d23b8e45f6c5a31e11b2395526e5cbd95c7a31a4d266c9aa6b90028"

LINEAGE = 2026092101
Q2_INITIALIZATION = 2026108101
Q1_SEEDS = tuple(range(2026092001, 2026092008))
Q1_TRAIN_SEEDS = tuple(range(2026092001, 2026092005))
Q1_VALIDATION_SEEDS = tuple(range(2026092005, 2026092008))
Q2_WORLDS = tuple(range(2026108001, 2026108008))
Q2_TRAIN_WORLDS = tuple(range(2026108001, 2026108005))
Q2_VALIDATION_WORLDS = tuple(range(2026108005, 2026108008))
Q2_LINEAGES = (2026092101, 2026092102, 2026092103)
NEW_LAMBDA_HEX = "0x1.c3c0a7b6b86d3p+26"
NEW_KAPPA_HEX = "0x1.2cea89d260f2ap+33"

Q1_SOURCE_SCHEMA = "multi-catfish-mcrl-v03-opening-dataset-v3"
Q1_RAW_SCHEMA = "multi-catfish-mcrl-v03-opening-source-v2"
Q1_SOURCE_RULE = "c1-exp-dull-rollout-lower-frontier-v1"
Q2_SOURCE_SCHEMA = "multi-catfish-mcrl-v014-compact-source-shard-v1"
CLAIM_CEILING = "SOURCE_ONLY_NO_SIMULATOR_NO_TEST_NO_EPISODE_EE"

Q1_CODE_HASHES = {
    ".scratch/multi-catfish-v020-c3-source-audit/q1-repricing/reprice_c1.py": "a0acfe53b59b91281dbdd3d9ec813f35f3ea5461c835274edb54869489cd54fe",
    ".scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_q1_q2.py": "f55b882149ce49505c694423520a6a807d6a90babcbce340cb5ba449adea1814",
    ".scratch/multi-catfish-v014-learner/run_v014_learner_gate.py": "c38f3cc662333465b4c1da01f2774a4904340466a5366bda5635ef9fcd64c750",
    ".scratch/multi-catfish-v015-c3-learned-context/run_v015_c3_learned_context_oracle.py": "0d71fdcf5fdf831dacb616bf8533bd8b68c6dcdb9365d0542ac146d0212a50e1",
}


class LiveArtifactError(RuntimeError):
    """An expected live artifact or digest is missing or has drifted."""


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise LiveArtifactError(f"expected a regular file: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path: Path, expected: str, *, label: str | None = None) -> str:
    actual = file_sha256(path)
    if actual != expected:
        name = label or str(path)
        raise LiveArtifactError(f"{name} hash mismatch: expected {expected}, got {actual}")
    return actual


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise LiveArtifactError(f"cannot read JSON object: {path}") from error
    if not isinstance(value, dict):
        raise LiveArtifactError(f"JSON value must be an object: {path}")
    return value


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise LiveArtifactError(message)


def _hash_manifest(path: Path) -> list[dict[str, str]]:
    """Verify a sha256sum-style manifest without treating it as self-authenticating."""

    entries: list[dict[str, str]] = []
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as error:
        raise LiveArtifactError(f"cannot read hash manifest: {path}") from error
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise LiveArtifactError(f"malformed hash manifest line {line_number}: {path}")
        expected, relative = parts
        target = path.parent / relative
        verify_file(target, expected, label=f"{path.name}:{relative}")
        entries.append({"path": relative, "sha256": expected})
    if not entries:
        raise LiveArtifactError(f"hash manifest is empty: {path}")
    return entries


def _attest_contracts() -> dict[str, str]:
    return {
        "v023_contract": verify_file(V023_CONTRACT, V023_CONTRACT_SHA256),
        "v020_execution_contract": verify_file(
            V020_EXECUTION_CONTRACT, V020_EXECUTION_CONTRACT_SHA256
        ),
        "v020_repricing_contract": verify_file(
            V020_REPRICING_CONTRACT, V020_REPRICING_CONTRACT_SHA256
        ),
    }


def _attest_q1() -> dict[str, Any]:
    receipt_hash = verify_file(Q1_RECEIPT, Q1_RECEIPT_SHA256)
    manifest_hash = verify_file(Q1_MANIFEST, Q1_MANIFEST_SHA256)
    manifest_entries = _hash_manifest(Q1_MANIFEST)
    receipt = read_json(Q1_RECEIPT)
    _expect(receipt.get("schema") == "multi-catfish-mcrl-v03-q1-c1-lambda-repricing-receipt-v1", "Q1 receipt schema drifted")
    _expect(receipt.get("status") == "PASS", "Q1 repricing receipt is not PASS")
    _expect(receipt.get("claim_ceiling") == "DEVELOPMENT_SOURCE_REPRICING_ONLY_NO_LEARNER_OR_EE_EFFICACY", "Q1 claim ceiling drifted")
    scope = receipt.get("scope")
    counts = receipt.get("counts")
    _expect(isinstance(scope, dict) and isinstance(counts, dict), "Q1 receipt scope/counts are malformed")
    _expect(scope.get("source_root") == "artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data", "Q1 source root drifted")
    _expect(scope.get("source_manifest_sha256") == E1_SOURCE_MANIFEST_SHA256, "Q1 source manifest binding drifted")
    _expect(scope.get("source_seed_split") == {str(seed): ("train" if seed in Q1_TRAIN_SEEDS else "validation") for seed in Q1_SEEDS}, "Q1 source split drifted")
    _expect(scope.get("test_source_opened") is False and scope.get("simulator_or_training_run") is False, "Q1 execution boundary drifted")
    _expect(counts.get("source_files") == 7 and counts.get("source_rows_total") == 3542, "Q1 source counts drifted")
    _expect(counts.get("admitted_c1_rows") == 1680 and counts.get("train_rows") == 968 and counts.get("validation_rows") == 712, "Q1 admitted counts drifted")
    _expect(len(receipt.get("records", [])) == 1680, "Q1 receipt records do not cover all admitted rows")

    source_receipt_hash = file_sha256(E1_SOURCE_RECEIPT)
    source_receipt = read_json(E1_SOURCE_RECEIPT)
    _expect(source_receipt.get("schema") == "multi-catfish-mcrl-v03-e1-action-shared-source-receipt-v1", "E1 source receipt schema drifted")
    _expect(source_receipt.get("status") == "PASS" and source_receipt.get("training") is False, "E1 source receipt boundary drifted")
    _expect(source_receipt.get("held_out_ee_evaluated") is False, "E1 source receipt opened held-out EE")
    _expect(source_receipt.get("source_manifest_sha256") == E1_SOURCE_MANIFEST_SHA256, "E1 source receipt manifest drifted")
    coverage_by_seed = {
        str(item["source_seed"]): item
        for item in source_receipt.get("coverage_by_seed", [])
        if isinstance(item, dict) and "source_seed" in item
    }
    _expect(set(coverage_by_seed) == {str(seed) for seed in Q1_SEEDS}, "E1 source coverage receipt drifted")
    source_manifest_hash = file_sha256(E1_SOURCE_MANIFEST)
    source_manifest = read_json(E1_SOURCE_MANIFEST)
    _expect(source_manifest.get("source_manifest_sha256") == E1_SOURCE_MANIFEST_SHA256, "E1 source manifest field drifted")
    manifest_body = {key: value for key, value in source_manifest.items() if key != "source_manifest_sha256"}
    _expect(canonical_sha256(manifest_body) == E1_SOURCE_MANIFEST_SHA256, "E1 source manifest body digest drifted")

    file_entries = receipt.get("files")
    _expect(isinstance(file_entries, list) and len(file_entries) == 7, "Q1 explicit source file list drifted")
    source_rows: list[dict[str, Any]] = []
    c1_fields: set[str] | None = None
    route_counts: dict[str, int] = {}
    for entry in file_entries:
        _expect(isinstance(entry, dict), "Q1 source file receipt entry is malformed")
        seed = int(entry["seed"])
        _expect(seed in Q1_SEEDS, f"Q1 source seed is unexpected: {seed}")
        path = REPO / str(entry["path"])
        _expect(path.resolve() == (E1_SOURCE_ROOT / f"opening-{seed}.json").resolve(), f"Q1 source path drifted for {seed}")
        verify_file(path, str(entry["byte_sha256"]), label=f"Q1 opening {seed}")
        payload = read_json(path)
        _expect(payload.get("schema") == Q1_SOURCE_SCHEMA, f"Q1 opening schema drifted for {seed}")
        _expect(payload.get("source_manifest_sha256") == E1_SOURCE_MANIFEST_SHA256, f"Q1 opening manifest drifted for {seed}")
        body = {key: value for key, value in payload.items() if key != "dataset_sha256"}
        _expect(payload.get("dataset_sha256") == entry["dataset_sha256"], f"Q1 dataset digest receipt drifted for {seed}")
        _expect(canonical_sha256(body) == payload.get("dataset_sha256"), f"Q1 dataset body digest drifted for {seed}")
        rows = payload.get("rows")
        _expect(isinstance(rows, list) and len(rows) == int(entry["total_rows"]), f"Q1 row count drifted for {seed}")
        _expect(payload.get("dataset_sha256") == source_receipt["opening_dataset_sha256s"][str(seed)], f"Q1 source receipt dataset digest drifted for {seed}")
        counts_for_seed: dict[str, int] = {}
        c1_count = 0
        for row in rows:
            _expect(isinstance(row, dict), f"Q1 row is malformed for {seed}")
            route = row.get("admitted_route")
            counts_for_seed[route] = counts_for_seed.get(route, 0) + 1
            if route != "C1":
                continue
            c1_count += 1
            _expect(row.get("routes", {}).get("C1", {}).get("source_rule") == Q1_SOURCE_RULE, f"Q1 C1 source rule drifted for {seed}")
            raw = row.get("raw")
            _expect(isinstance(raw, dict), f"Q1 C1 raw object missing for {seed}")
            _expect(raw.get("schema") == Q1_RAW_SCHEMA and raw.get("source_manifest_sha256") == E1_SOURCE_MANIFEST_SHA256, f"Q1 C1 raw lineage drifted for {seed}")
            _expect(raw.get("lambda_bits_per_j") == "0x1.443a8f481639ap+26", f"Q1 C1 old lambda payload drifted for {seed}")
            _expect(isinstance(raw.get("state"), list) and len(raw["state"]) == 228, f"Q1 C1 state shape drifted for {seed}")
            _expect(isinstance(raw.get("action_mask"), list) and len(raw["action_mask"]) == 28, f"Q1 C1 action mask shape drifted for {seed}")
            _expect(isinstance(row.get("targets"), dict) and "zeta1_focal_surplus_bits" in row["targets"], f"Q1 C1 target missing for {seed}")
            if c1_fields is None:
                c1_fields = set(raw)
            else:
                _expect(set(raw) == c1_fields, f"Q1 C1 raw field set drifted for {seed}")
        _expect(counts_for_seed == entry["admitted_route_counts"], f"Q1 route counts drifted for {seed}")
        _expect(c1_count == int(entry["admitted_c1_rows_used"]), f"Q1 admitted C1 count drifted for {seed}")
        _expect(c1_count == coverage_by_seed[str(seed)]["c1_rows"], f"Q1 coverage receipt drifted for {seed}")
        route_counts.update({route: route_counts.get(route, 0) + count for route, count in counts_for_seed.items()})
        source_rows.append({"seed": seed, "split": entry["split"], "total_rows": len(rows), "c1_rows": c1_count, "byte_sha256": entry["byte_sha256"], "dataset_sha256": entry["dataset_sha256"]})

    _expect(sum(row["c1_rows"] for row in source_rows) == 1680, "Q1 source row closure does not sum to 1680")
    _expect(route_counts.get("C3") == 1862, "Q1 excluded C3 row count drifted")
    _expect(c1_fields is not None and "frontier_score" not in c1_fields and "user_frontier_scores" not in c1_fields and "slot_tables" not in c1_fields, "Q1 rows unexpectedly expose predecision selector fields")
    return {
        "receipt": str(Q1_RECEIPT.relative_to(REPO)),
        "receipt_sha256": receipt_hash,
        "manifest": str(Q1_MANIFEST.relative_to(REPO)),
        "manifest_sha256": manifest_hash,
        "manifest_entries_authenticated": len(manifest_entries),
        "source_receipt": str(E1_SOURCE_RECEIPT.relative_to(REPO)),
        "source_receipt_sha256": source_receipt_hash,
        "source_manifest": str(E1_SOURCE_MANIFEST.relative_to(REPO)),
        "source_manifest_file_sha256": source_manifest_hash,
        "source_manifest_body_sha256": E1_SOURCE_MANIFEST_SHA256,
        "source_files": source_rows,
        "source_rows_total": 3542,
        "admitted_c1_rows": 1680,
        "train_rows": 968,
        "validation_rows": 712,
        "excluded_c3_rows": 1862,
        "repriced_lambda_hex": NEW_LAMBDA_HEX,
        "q1_predecision_selector_fields_present": False,
    }


def _q2_result_entries(result: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    entries = result.get("per_shard")
    _expect(isinstance(entries, list) and len(entries) == 21, "Q2 repricing shard receipt count drifted")
    keyed: dict[str, Mapping[str, Any]] = {}
    for entry in entries:
        _expect(isinstance(entry, dict) and isinstance(entry.get("shard"), str), "Q2 repricing shard entry is malformed")
        shard = str(entry["shard"])
        _expect(shard not in keyed, f"duplicate Q2 repricing shard: {shard}")
        keyed[shard] = entry
    return keyed


def _parse_source_sha256(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition("=")
        _expect(separator == "=" and key and value, f"malformed Q2 source seal: {path}")
        values[key] = value
    return values


def _attest_q2() -> dict[str, Any]:
    result_hash = verify_file(Q2_BATCH_RESULT, Q2_BATCH_RESULT_SHA256)
    seal_text = Q2_BATCH_RESULT_SEAL.read_text(encoding="ascii").strip()
    _expect(seal_text == f"{Q2_BATCH_RESULT_SHA256}  result.json", "Q2 result seal drifted")
    result = read_json(Q2_BATCH_RESULT)
    _expect(result.get("schema") == "multi-catfish-mcrl-v020-q2-batch-repricing-result-v1", "Q2 repricing result schema drifted")
    _expect(result.get("status") == "PASS_OFFLINE_Q2_REPRICING", "Q2 repricing result is not PASS")
    _expect(result.get("claim_ceiling") == "SOURCE_REUSE_ONLY_NO_SIMULATOR_NO_TRAINING_NO_TEST_NO_EFFICACY", "Q2 repricing claim ceiling drifted")
    _expect(result.get("simulator_run") is False and result.get("episode_training") is False and result.get("learner_update") is False and result.get("test_split_opened") is False, "Q2 repricing boundary drifted")
    panel = result.get("panel")
    _expect(panel == {"lineages": list(Q2_LINEAGES), "shard_count": 21, "train_worlds": list(Q2_TRAIN_WORLDS), "validation_worlds": list(Q2_VALIDATION_WORLDS), "worlds": list(Q2_WORLDS)}, "Q2 source panel declaration drifted")
    _expect(result.get("lambda", {}).get("new_bits_per_j_hex") == NEW_LAMBDA_HEX, "Q2 repriced lambda drifted")
    _expect(result.get("contract", {}).get("sha256") == V020_REPRICING_CONTRACT_SHA256, "Q2 repricing contract binding drifted")

    entries = _q2_result_entries(result)
    expected_shards = {f"{world}-{lineage}" for world in Q2_WORLDS for lineage in Q2_LINEAGES}
    _expect(set(entries) == expected_shards, "Q2 repricing shard identities drifted")
    source_paths = sorted(Q2_SOURCE_ROOT.glob("*-*/"))
    _expect(len(source_paths) == 21 and {path.name for path in source_paths} == expected_shards, "Q2 source panel directories drifted")

    selected_receipts: list[dict[str, Any]] = []
    all_shards: list[dict[str, Any]] = []
    for shard_path in source_paths:
        shard = shard_path.name
        world_text, lineage_text = shard.split("-", maxsplit=1)
        world, lineage = int(world_text), int(lineage_text)
        entry = entries[shard]
        metadata_path = shard_path / "metadata.json"
        source_path = shard_path / "source.npz"
        seal_path = shard_path / "source.sha256"
        metadata = read_json(metadata_path)
        _expect(metadata.get("schema") == Q2_SOURCE_SCHEMA, f"Q2 source schema drifted: {shard}")
        _expect(metadata.get("world_seed") == world and metadata.get("lineage") == lineage, f"Q2 source identity drifted: {shard}")
        _expect(metadata.get("row_count") == 1000 and metadata.get("split") == "TRAIN", f"Q2 source row/split drifted: {shard}")
        _expect(metadata.get("test_split_opened") is False and metadata.get("episode_training") is False and metadata.get("learner_update") is False, f"Q2 source boundary drifted: {shard}")
        metadata_body = {key: value for key, value in metadata.items() if key != "metadata_sha256"}
        _expect(canonical_sha256(metadata_body) == metadata.get("metadata_sha256"), f"Q2 metadata body digest drifted: {shard}")
        source_hash = verify_file(source_path, str(entry["source_npz_sha256"]), label=f"Q2 source {shard}")
        _expect(metadata.get("npz_sha256") == source_hash, f"Q2 metadata NPZ digest drifted: {shard}")
        seal = _parse_source_sha256(seal_path)
        _expect(seal.get("schema") == Q2_SOURCE_SCHEMA, f"Q2 source seal schema drifted: {shard}")
        _expect(seal.get("npz_sha256") == source_hash, f"Q2 source seal NPZ digest drifted: {shard}")
        _expect(seal.get("metadata_sha256") == file_sha256(metadata_path), f"Q2 source seal metadata digest drifted: {shard}")
        _expect(seal.get("arrays_sha256") == metadata.get("arrays_sha256"), f"Q2 source array digest drifted: {shard}")
        with np.load(source_path, allow_pickle=False) as arrays:
            keys = set(arrays.files)
            _expect("q2_states" in keys and "q2_masks" in keys and "q2_reference_actions" in keys and "q2_target_bits" in keys, f"Q2 source arrays are incomplete: {shard}")
            _expect(arrays["q2_states"].shape == (1000, 448), f"Q2 state shape drifted: {shard}")
            _expect(arrays["q2_masks"].shape == (1000, 28) and arrays["q2_target_bits"].shape == (1000, 28), f"Q2 surface shape drifted: {shard}")
        target_path = Q2_BATCH_ROOT / "shards" / shard / "q2_target_bits_repriced.npy"
        target_hash = verify_file(target_path, str(entry["repriced_npy_sha256"]), label=f"Q2 repriced target {shard}")
        target = np.load(target_path, allow_pickle=False)
        _expect(target.shape == (1000, 28) and target.dtype == np.dtype("float64") and bool(np.all(np.isfinite(target))), f"Q2 repriced target shape/finiteness drifted: {shard}")
        audit_path = Q2_BATCH_ROOT / "shards" / shard / "audit.json"
        audit_hash = verify_file(audit_path, str(entry["audit_json_sha256"]), label=f"Q2 audit {shard}")
        row = {"shard": shard, "world": world, "lineage": lineage, "source_npz_sha256": source_hash, "metadata_file_sha256": file_sha256(metadata_path), "repriced_npy_sha256": target_hash, "audit_json_sha256": audit_hash, "row_count": 1000}
        all_shards.append(row)
        if lineage == LINEAGE:
            selected_receipts.append({
                "path": str(shard_path.resolve()),
                "world_seed": world,
                "lineage": lineage,
                "split": "train" if world in Q2_TRAIN_WORLDS else "validation",
                "row_count": 1000,
                "arrays_sha256": metadata["arrays_sha256"],
                "field_root_digest": metadata["field_root_digest"],
            })
    selected_receipts.sort(key=lambda row: (row["world_seed"], row["lineage"]))
    source_closure_sha256 = canonical_sha256(selected_receipts)
    _expect(source_closure_sha256 == "c6b6b93b36dbbda5123ff7603c675dc5f95e6d4b6c2cb1fa03b1e7b73c853736", "Q2 lineage source closure digest drifted")
    selected_target_hashes = {row["shard"]: row["repriced_npy_sha256"] for row in all_shards if row["lineage"] == LINEAGE}
    _expect(len(selected_target_hashes) == 7, "Q2 selected lineage target closure is incomplete")
    _expect({row["shard"]: entries[row["shard"]]["repriced_npy_sha256"] for row in all_shards if row["lineage"] == LINEAGE} == selected_target_hashes, "Q2 target receipt closure drifted")
    selected_metadata = [read_json(Q2_SOURCE_ROOT / shard / "metadata.json") for shard in sorted(selected_target_hashes)]
    _expect(all("slot_tables" not in metadata and "frontier_score" not in metadata for metadata in selected_metadata), "Q2 compact source unexpectedly exposes C1-style selector fields")
    _expect(all(metadata.get("row_semantics") == "one-user-anchor-no-legal-action-expansion" for metadata in selected_metadata), "Q2 source row semantics drifted")
    return {
        "batch_result": str(Q2_BATCH_RESULT.relative_to(REPO)),
        "batch_result_sha256": result_hash,
        "batch_result_seal": str(Q2_BATCH_RESULT_SEAL.relative_to(REPO)),
        "source_panel_root": str(Q2_SOURCE_ROOT.relative_to(REPO)),
        "all_source_shards": all_shards,
        "source_panel_shards": 21,
        "selected_lineage": LINEAGE,
        "selected_source_shards": [row for row in all_shards if row["lineage"] == LINEAGE],
        "selected_source_closure_sha256": source_closure_sha256,
        "selected_target_count": len(selected_target_hashes),
        "repriced_lambda_hex": NEW_LAMBDA_HEX,
        "q2_predecision_selector_fields_present": False,
    }


def _attest_fit() -> dict[str, Any]:
    authority_file_hash = verify_file(AUTHORITY, AUTHORITY_FILE_SHA256)
    authority = read_json(AUTHORITY)
    body = {key: value for key, value in authority.items() if key != "authority_sha256"}
    _expect(authority.get("authority_sha256") == AUTHORITY_BODY_SHA256 and canonical_sha256(body) == AUTHORITY_BODY_SHA256, "V0.20 authority body digest drifted")
    _expect(authority.get("schema") == "multi-catfish-mcrl-v020-repriced-q1-q2-source-fit-v1-authority", "V0.20 authority schema drifted")
    _expect(authority.get("lineage") == LINEAGE and authority.get("q2_initialization") == Q2_INITIALIZATION, "V0.20 lineage identity drifted")
    _expect(authority.get("claim_ceiling") == CLAIM_CEILING and authority.get("simulator_run") is False and authority.get("test_split_opened") is False and authority.get("episode_training") is False, "V0.20 fit boundary drifted")
    _expect(authority.get("lambda_bits_per_j_hex") == NEW_LAMBDA_HEX, "V0.20 fit lambda drifted")
    _expect(authority.get("q1_updates") == 10 and authority.get("q2_rungs") == [3, 10, 30, 100, 300, 1000, 3000], "V0.20 update schedule drifted")
    _expect(authority.get("fixed_deployment_rungs") is None, "authority unexpectedly carries result-only deployment field")
    code_hashes: dict[str, str] = {}
    for relative, expected in Q1_CODE_HASHES.items():
        code_hashes[relative] = verify_file(REPO / relative, expected, label=f"fit code {relative}")
    result_hash = verify_file(FIT_RESULT, FIT_RESULT_SHA256)
    status_hash = verify_file(FIT_STATUS, FIT_STATUS_SHA256)
    result = read_json(FIT_RESULT)
    status = read_json(FIT_STATUS)
    _expect(result.get("schema") == "multi-catfish-mcrl-v020-repriced-q1-q2-source-fit-v1-result" and result.get("status") == "COMPLETE_SOURCE_ONLY", "V0.20 fit result status/schema drifted")
    _expect(result.get("authority_file_sha256") == AUTHORITY_FILE_SHA256 and result.get("authority_sha256") == AUTHORITY_BODY_SHA256, "V0.20 result authority binding drifted")
    _expect(result.get("fixed_deployment_rungs") == {"q1": 10, "q2": 3000}, "V0.20 deployment rung declaration drifted")
    _expect(result.get("simulator_run") is False and result.get("test_split_opened") is False and result.get("episode_training") is False, "V0.20 result boundary drifted")
    _expect(status.get("result_file_sha256") == FIT_RESULT_SHA256 and status.get("authority_file_sha256") == AUTHORITY_FILE_SHA256, "V0.20 status seal drifted")
    checkpoint_hashes = result.get("checkpoint_file_sha256s")
    _expect(isinstance(checkpoint_hashes, dict) and checkpoint_hashes.get("10") == Q1_RUNG_10_CHECKPOINT_SHA256 and checkpoint_hashes.get("3000") == DEPLOYMENT_CHECKPOINT_SHA256, "V0.20 checkpoint declaration drifted")
    checkpoints: dict[str, str] = {}
    for rung, expected in checkpoint_hashes.items():
        path = LINEAGE_ROOT / "checkpoints" / f"lineage-2026092101-q2init-2026108101-rung-{int(rung):06d}.pt"
        checkpoints[rung] = verify_file(path, expected, label=f"checkpoint rung {rung}")
    reference_hash = verify_file(Q1_Q2_REFERENCE_ACTIONS, Q1_Q2_REFERENCE_ACTIONS_SHA256)
    authority_target_hashes = authority.get("q2_repriced_target_file_sha256s")
    _expect(isinstance(authority_target_hashes, dict) and len(authority_target_hashes) == 7, "V0.20 Q2 target closure declaration drifted")
    return {
        "authority": str(AUTHORITY.relative_to(REPO)),
        "authority_file_sha256": authority_file_hash,
        "authority_body_sha256": AUTHORITY_BODY_SHA256,
        "result": str(FIT_RESULT.relative_to(REPO)),
        "result_sha256": result_hash,
        "status": str(FIT_STATUS.relative_to(REPO)),
        "status_sha256": status_hash,
        "code_file_sha256s": code_hashes,
        "q1_updates": 10,
        "q2_rungs": [3, 10, 30, 100, 300, 1000, 3000],
        "fixed_deployment_rungs": {"q1": 10, "q2": 3000},
        "checkpoints": checkpoints,
        "deployment_checkpoint_sha256": checkpoints["3000"],
        "q1_rung_10_checkpoint_sha256": checkpoints["10"],
        "reference_actions_sha256": reference_hash,
        "source_sha256_from_authority": authority["source_sha256"],
        "q2_repriced_target_file_sha256s": authority_target_hashes,
    }


def attest(repo: Path | None = None) -> dict[str, Any]:
    """Authenticate current V0.20 Q1/Q2 bytes and report V0.23 readiness."""

    if repo is not None:
        supplied = Path(repo).resolve()
        _expect(supplied == REPO.resolve(), f"loader is pinned to this checkout: {REPO}")
    contracts = _attest_contracts()
    q1 = _attest_q1()
    q2 = _attest_q2()
    fit = _attest_fit()
    target_hashes = {
        f".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/{row['shard']}/q2_target_bits_repriced.npy": row["repriced_npy_sha256"]
        for row in q2["selected_source_shards"]
    }
    _expect(fit["q2_repriced_target_file_sha256s"] == target_hashes, "V0.20 authority/result Q2 target closure disagrees")
    _expect(fit["source_sha256_from_authority"] == q2["selected_source_closure_sha256"], "V0.20 authority/source closure disagrees")
    blockers = [
        "Q1 opening C1 rows are post-evaluation target-bearing rows; they lack C1DullRolloutRecord frontier scores and contemporaneous slot tables.",
        "Q2 compact V0.14 shards are one-user anchor surfaces; they lack C2PredecisionAnchor current slot-table opportunities and the V0.23 temporal source universe.",
        "No V0.23 source artifacts for worlds 2026121705-2026121712 are present, so informed C1/C2 selector objects cannot be authenticated from current bytes.",
        "Existing neutral selector APIs must not be called here: doing so would generate new neutral outcomes, which is outside this read-only attestation.",
    ]
    return {
        "schema": "multi-catfish-mcrl-v023-c1c2-live-artifact-attestation-v1",
        "status": "VERIFIED_V020_BACKGROUND_ONLY",
        "claim_ceiling": CLAIM_CEILING,
        "contracts": contracts,
        "lineage": LINEAGE,
        "q2_initialization": Q2_INITIALIZATION,
        "lambda_hex": NEW_LAMBDA_HEX,
        "kappa_hex": NEW_KAPPA_HEX,
        "q1": q1,
        "q2": q2,
        "fit": fit,
        "c1_informed_selector_ready": False,
        "c2_informed_selector_ready": False,
        "equal_budget_neutral_materialization": "BLOCKED_UNTIL_V023_PREDECISION_SOURCE_CAPTURE",
        "blockers": blockers,
        "side_effects": {
            "simulator_imported": False,
            "selector_called": False,
            "neutral_source_generated": False,
            "learner_run": False,
            "files_written": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    args = parser.parse_args()
    print(json.dumps(attest(args.repo), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
