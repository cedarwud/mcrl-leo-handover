"""W-107 -- result-blind V0.6 T1 formal-verdict writer.

The source fixture is synthetic and deliberately fails G-E.  It exercises the
writer boundary without constructing or emitting an AUTHORIZE artifact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mcrl.runtime import ee_axis_v06_c2_k1_formal_verdict_writer as writer
from mcrl.runtime.ee_axis_v06_c2_k1_learner_contract_v2 import (
    FORMAL_VERDICT_ARTIFACT_SCHEMA,
    FORMAL_VERDICT_SEAL_SCHEMA,
    SOURCE_FALSIFIED_VERDICT,
    T1_ALGORITHM_SCHEMA,
    T1_SOURCE_RULE,
    T1_SOURCE_SCHEMA,
    canonical_bytes,
    canonical_sha256,
    verify_authenticated_formal_verdict,
)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, object]) -> str:
    path.write_bytes(canonical_bytes(payload))
    return _file_sha256(path)


def _fake_runner(tmp_path: Path) -> Path:
    """Create a content-addressed runner with the two required callables."""

    path = tmp_path / "synthetic-frozen-t1-runner.py"
    path.write_text(
        """
import hashlib
import json
from pathlib import Path

from mcrl.runtime.ee_axis_v06_c2_k1_learner_contract_v2 import (
    SOURCE_FALSIFIED_VERDICT,
    T1_SOURCE_SEAL_SCHEMA,
    canonical_bytes,
    canonical_sha256,
)

SOURCE_SEAL_SCHEMA = T1_SOURCE_SEAL_SCHEMA

def _canonical_read(path):
    path = Path(path)
    raw = path.read_bytes()
    payload = json.loads(raw.decode("ascii"))
    if raw != canonical_bytes(payload) or not isinstance(payload, dict):
        raise RuntimeError("noncanonical synthetic JSON")
    return payload

def _source_payload_sha256(payload):
    body = dict(payload)
    body.pop("source_sha256", None)
    return canonical_sha256(body)

def _read_formal_prepare(prepare_path, t1_prereg_path):
    prepare_path = Path(prepare_path)
    t1_prereg_path = Path(t1_prereg_path)
    payload = _canonical_read(prepare_path)
    seal = _canonical_read(prepare_path.with_name("prepare-live-seal.json"))
    if payload.get("prepare_sha256") != canonical_sha256({
        key: value for key, value in payload.items() if key != "prepare_sha256"
    }):
        raise RuntimeError("prepare digest")
    if seal.get("prepare_sha256") != payload["prepare_sha256"]:
        raise RuntimeError("prepare seal payload")
    if seal.get("prepare_file_sha256") != hashlib.sha256(
        prepare_path.read_bytes()
    ).hexdigest():
        raise RuntimeError("prepare seal file")
    if payload.get("t1_prereg_file_sha256") != hashlib.sha256(
        t1_prereg_path.read_bytes()
    ).hexdigest():
        raise RuntimeError("T1 prereg digest")
    return payload

def verify_source(payload, prepare):
    if payload.get("prepare_sha256") != prepare.get("prepare_sha256"):
        raise RuntimeError("source prepare")
    if payload.get("source_sha256") != _source_payload_sha256(payload):
        raise RuntimeError("source digest")
    return {
        "status": "VERIFIED",
        "disposition": SOURCE_FALSIFIED_VERDICT,
        "gates": payload["gates"],
        "pairs": 1008,
        "controls": 36,
    }

def _code_authority_manifest():
    return {"sha256": "c" * 64}
""",
        encoding="utf-8",
    )
    return path


def _bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    runner_path = _fake_runner(tmp_path)
    monkeypatch.setattr(writer, "RUNNER_PATH", runner_path)

    t1_prereg_path = tmp_path / "t1-prereg.json"
    t1_prereg_path.write_bytes(b"synthetic-t1-prereg")
    t1_prereg_sha = _file_sha256(t1_prereg_path)

    prepare_path = tmp_path / "prepare-live.json"
    prepare_body: dict[str, object] = {
        "schema": "synthetic-prepare-live-v2",
        "t1_prereg_file_sha256": t1_prereg_sha,
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
    }
    prepare_body["prepare_sha256"] = canonical_sha256(prepare_body)
    prepare_file_sha = _write_json(prepare_path, prepare_body)
    _write_json(
        tmp_path / "prepare-live-seal.json",
        {
            "schema": "multi-catfish-mcrl-v06-c2-k1-t1-prepare-live-seal-v2",
            "prepare_sha256": prepare_body["prepare_sha256"],
            "prepare_file_sha256": prepare_file_sha,
            "training": False,
            "test_split_opened": False,
            "outcome_selection": False,
        },
    )

    source_path = tmp_path / "source.json"
    source_body: dict[str, object] = {
        "schema": T1_SOURCE_SCHEMA,
        "algorithm_schema": T1_ALGORITHM_SCHEMA,
        "source_rule": T1_SOURCE_RULE,
        "prepare_sha256": prepare_body["prepare_sha256"],
        "counts": {
            "anchors": 12,
            "lineages": 3,
            "opening_actions": 28,
            "pairs": 1008,
            "controls": 36,
        },
        "gates": {
            "G-M": {"passed": True},
            "G-E": {"passed": False},
            "G-S": {"passed": True},
            "launchable": False,
        },
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "q2_consulted": False,
    }
    source_body["source_sha256"] = canonical_sha256(source_body)
    source_file_sha = _write_json(source_path, source_body)
    source_seal_path = tmp_path / "source-seal.json"
    _write_json(
        source_seal_path,
        {
            "schema": "multi-catfish-mcrl-v06-c2-k1-t1-source-seal-v1",
            # The runner's seal records the complete source-object digest;
            # source.json.source_sha256 itself excludes its own field.
            "source_sha256": canonical_sha256(source_body),
            "source_file_sha256": source_file_sha,
            "prepare_sha256": source_body["prepare_sha256"],
            "training": False,
            "test_split_opened": False,
            "outcome_selection": False,
        },
    )
    return {
        "runner": runner_path,
        "prepare": prepare_path,
        "t1_prereg": t1_prereg_path,
        "source": source_path,
        "source_seal": source_seal_path,
        "output": tmp_path / "verdict-output",
    }


def test_writer_dynamically_verifies_and_writes_nonauthorising_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _bundle(tmp_path, monkeypatch)
    paths["output"].mkdir()

    receipt = writer.write_formal_verdict(
        paths["prepare"],
        paths["t1_prereg"],
        paths["source"],
        paths["output"],
        source_seal_path=paths["source_seal"],
    )

    assert receipt["status"] == "WRITTEN"
    assert receipt["disposition"] == SOURCE_FALSIFIED_VERDICT
    assert receipt["artifact"]["schema"] == FORMAL_VERDICT_ARTIFACT_SCHEMA
    assert receipt["seal"]["schema"] == FORMAL_VERDICT_SEAL_SCHEMA
    assert set(receipt["artifact"]) == writer.contract._ARTIFACT_FIELDS
    assert set(receipt["seal"]) == writer.contract._SEAL_FIELDS
    assert receipt["schema_gap"] == []
    assert receipt["artifact"]["t1_prereg_file_sha256"] == _file_sha256(
        paths["t1_prereg"]
    )
    assert receipt["artifact"]["verifier_code_authority_sha256"] == "c" * 64
    assert receipt["t1_prereg_file_sha256"] == _file_sha256(paths["t1_prereg"])
    assert receipt["verifier_code_authority_sha256"] == "c" * 64
    assert receipt["source_seal_payload_sha256"] == canonical_sha256(
        json.loads(paths["source_seal"].read_text(encoding="ascii"))
    )

    authenticated = verify_authenticated_formal_verdict(
        paths["output"] / "formal-verdict.json",
        paths["output"] / "formal-verdict-seal.json",
        expected_source_path=paths["source"],
        expected_source_seal_path=paths["source_seal"],
    )
    assert authenticated["disposition"] == SOURCE_FALSIFIED_VERDICT
    assert not (paths["output"] / "writer-receipt.json").exists()


def test_writer_has_no_caller_disposition_parameter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _bundle(tmp_path, monkeypatch)
    paths["output"].mkdir()
    with pytest.raises(TypeError):
        writer.write_formal_verdict(  # type: ignore[call-arg]
            paths["prepare"],
            paths["t1_prereg"],
            paths["source"],
            paths["output"],
            disposition=SOURCE_FALSIFIED_VERDICT,
        )


def test_writer_recomputes_source_seal_file_hash_and_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _bundle(tmp_path, monkeypatch)
    paths["output"].mkdir()
    source_seal = json.loads(paths["source_seal"].read_text(encoding="ascii"))
    source_seal["source_file_sha256"] = "f" * 64
    paths["source_seal"].write_bytes(canonical_bytes(source_seal))

    with pytest.raises(writer.FormalVerdictWriterError, match="source-seal file digest"):
        writer.write_formal_verdict(
            paths["prepare"],
            paths["t1_prereg"],
            paths["source"],
            paths["output"],
        )
    assert not (paths["output"] / "formal-verdict.json").exists()
    assert not (paths["output"] / "formal-verdict-seal.json").exists()


def test_writer_is_write_once_and_does_not_retry_or_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _bundle(tmp_path, monkeypatch)
    paths["output"].mkdir()
    writer.write_formal_verdict(
        paths["prepare"],
        paths["t1_prereg"],
        paths["source"],
        paths["output"],
    )
    artifact_before = (paths["output"] / "formal-verdict.json").read_bytes()
    seal_before = (paths["output"] / "formal-verdict-seal.json").read_bytes()

    with pytest.raises(writer.FormalVerdictWriterError, match="write-once"):
        writer.write_formal_verdict(
            paths["prepare"],
            paths["t1_prereg"],
            paths["source"],
            paths["output"],
        )
    assert (paths["output"] / "formal-verdict.json").read_bytes() == artifact_before
    assert (paths["output"] / "formal-verdict-seal.json").read_bytes() == seal_before
