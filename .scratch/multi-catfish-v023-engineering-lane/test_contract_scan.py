from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load_tool():
    path = HERE / "contract_scan.py"
    spec = importlib.util.spec_from_file_location("engineering_contract_scan", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SCAN = _load_tool()


def test_mutation_negative_detects_every_contract_category_with_locations():
    report = SCAN.scan_spec(HERE / "specs/selftest_contract.json", REPO)
    assert report["status"] == "MISMATCH"
    pair = report["pairs"][0]
    mismatches = {item["category"] for item in pair["items"] if item["status"] == "MISMATCH"}
    assert {
        "token.schema",
        "token.status",
        "token.claim_ceiling",
        "token.mode",
        "token.route",
        "token.unit",
        "npz_dtype",
        "npz_shape",
        "layout_constant",
        "numeric_constant",
    }.issubset(mismatches)
    statuses = {(item["category"], item["item"]): item["status"] for item in pair["items"]}
    assert statuses[("receipt_json_field", "producer_field")] == "PRODUCER_ONLY"
    assert statuses[("receipt_json_field", "consumer_field")] == "CONSUMER_ONLY"
    assert statuses[("npz_array", "mask")] == "PRODUCER_ONLY"
    assert statuses[("npz_array", "masks")] == "CONSUMER_ONLY"
    assert statuses[("npz_array", "states")] == "MATCH"
    for item in pair["items"]:
        for side in ("producer", "consumer"):
            for occurrence in item[side]:
                assert occurrence["line"] > 0
                assert occurrence["location"].endswith(f":{occurrence['line']}")


def test_positive_uses_producer_owned_writer_and_reader(tmp_path: Path):
    module_path = ".scratch/multi-catfish-v023-engineering-lane/fixtures/contract_producer.py"
    spec = {
        "schema": SCAN.SPEC_SCHEMA,
        "pairs": [{
            "name": "producer-owned-positive",
            "producer": {
                "path": module_path,
                "functions": ["write_artifact"],
                "constants": ["SCHEMA"],
            },
            "consumer": {
                "path": module_path,
                "functions": ["read_own_artifact"],
                "constants": ["SCHEMA"],
            },
            "bindings": [{
                "category": "token.schema", "name": "schema",
                "producer": "SCHEMA", "consumer": "SCHEMA",
            }],
        }],
    }
    path = tmp_path / "positive.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    report = SCAN.scan_spec(path, REPO)
    pair = report["pairs"][0]
    assert not [item for item in pair["items"] if item["status"] == "MISMATCH"]
    by_key = {(item["category"], item["item"]): item for item in pair["items"]}
    assert by_key[("npz_array", "states")]["status"] == "MATCH"
    assert by_key[("npz_dtype", "states")]["status"] == "MATCH"
    assert by_key[("npz_shape", "states")]["status"] == "MATCH"


def test_missing_concurrent_module_is_blocked_not_fatal(tmp_path: Path):
    spec = {
        "schema": SCAN.SPEC_SCHEMA,
        "pairs": [{
            "name": "concurrent-boundary",
            "producer": {"path": "missing-producer.py", "functions": ["write"]},
            "consumer": {"path": "missing-consumer.py", "functions": ["read"]},
        }],
    }
    path = tmp_path / "blocked.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    report = SCAN.scan_spec(path, REPO)
    assert report["status"] == "BLOCKED"
    assert report["pairs"][0]["status"] == "BLOCKED"
    assert len(report["pairs"][0]["missing"]) == 2
