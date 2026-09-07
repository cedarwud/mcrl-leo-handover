"""Focused synthetic checks for the post-R7 provider factory seam."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "v023_post_r7_provider_factory_under_test",
    HERE / "v023_post_r7_provider_factory.py",
)
assert SPEC is not None and SPEC.loader is not None
FACTORY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FACTORY
SPEC.loader.exec_module(FACTORY)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii") + b"\n"


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _payload(digest_seed: str) -> str:
    return hashlib.sha256(digest_seed.encode("ascii")).hexdigest()


def _config(path: Path, *, epoch_budget: int = 100) -> tuple[Path, str]:
    payload = {
        "schema": FACTORY.CONFIG_SCHEMA,
        "r7_root": str(path / "r7"),
        "target_root": str(path / "target"),
        "epoch_budget": epoch_budget,
        "schedule_seed": 2026090701,
    }
    config = path / "post-r7-provider.json"
    config.write_bytes(_canonical(payload))
    return config, hashlib.sha256(config.read_bytes()).hexdigest()


def test_make_provider_requires_both_narrow_environment_bindings(monkeypatch):
    monkeypatch.delenv(FACTORY.CONFIG_PATH_ENV, raising=False)
    monkeypatch.delenv(FACTORY.CONFIG_SHA256_ENV, raising=False)
    with pytest.raises(FACTORY.V023PostR7ProviderFactoryError, match="both required"):
        FACTORY.make_provider()


def test_config_hash_and_schema_are_authenticated_before_build(monkeypatch, tmp_path):
    config, expected = _config(tmp_path)
    monkeypatch.setenv(FACTORY.CONFIG_PATH_ENV, str(config))
    monkeypatch.setenv(FACTORY.CONFIG_SHA256_ENV, "0" * 64)
    with pytest.raises(FACTORY.V023PostR7ProviderFactoryError, match="SHA-256 disagrees"):
        FACTORY.make_provider()

    monkeypatch.setenv(FACTORY.CONFIG_SHA256_ENV, expected)
    monkeypatch.setattr(
        FACTORY,
        "build_provider",
        lambda value: value,
    )
    parsed = FACTORY.make_provider()
    assert parsed.epoch_budget == 100
    assert parsed.schedule_seed == 2026090701


def _make_sealed_r7_root(root: Path) -> tuple[Path, dict[str, object]]:
    root.mkdir()
    authority = root / "authority"
    authority.mkdir()
    preflight = json.loads(
        (
            FACTORY.REPO
            / ".scratch/multi-catfish-v023-r7-launch-ready/R7-PREFLIGHT-MANIFEST.json"
        ).read_text(encoding="ascii")
    )
    preflight_path = authority / "R7-PREFLIGHT-MANIFEST.json"
    preflight_path.write_bytes(_canonical(preflight))
    preflight_sha = hashlib.sha256(preflight_path.read_bytes()).hexdigest()
    (authority / "R7-PREFLIGHT-MANIFEST.sha256").write_text(
        f"{preflight_sha}  R7-PREFLIGHT-MANIFEST.json\n", encoding="ascii"
    )
    for relative, source in (
        (
            FACTORY.R7_AUTHORITY_CONTRACT,
            FACTORY.REPO
            / "docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md",
        ),
        (
            FACTORY.R7_AUTHORITY_EXECUTION_ADDENDUM,
            FACTORY.REPO
            / "docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md",
        ),
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    authority_entries = {
        "contract": {
            "path": FACTORY.R7_AUTHORITY_CONTRACT,
            "sha256": hashlib.sha256(
                (root / FACTORY.R7_AUTHORITY_CONTRACT).read_bytes()
            ).hexdigest(),
        },
        "execution_addendum": {
            "path": FACTORY.R7_AUTHORITY_EXECUTION_ADDENDUM,
            "sha256": hashlib.sha256(
                (root / FACTORY.R7_AUTHORITY_EXECUTION_ADDENDUM).read_bytes()
            ).hexdigest(),
        },
        "preflight_manifest": {
            "path": FACTORY.R7_ROOT_PREFLIGHT,
            "sha256": preflight_sha,
        },
        "preflight_manifest_digest": {
            "path": FACTORY.R7_ROOT_PREFLIGHT_DIGEST,
            "sha256": hashlib.sha256(
                (authority / "R7-PREFLIGHT-MANIFEST.sha256").read_bytes()
            ).hexdigest(),
        },
    }
    (authority / "AUTHORITY.json").write_bytes(
        _canonical(
            {
                "schema": FACTORY.R7_AUTHORITY_SCHEMA,
                "contract_sha256": FACTORY._SCHEDULE.R7_CONTRACT_SHA256,
                "execution_addendum_sha256": FACTORY._SCHEDULE.R7_EXECUTION_ADDENDUM_SHA256,
                "preflight_manifest_sha256": preflight_sha,
                "entries": authority_entries,
                "test_split_opened": False,
                "episode_training": False,
            }
        )
    )

    source_manifest_path = root / FACTORY.R7_ROOT_SOURCE_MANIFEST
    source_manifest_path.write_bytes(_canonical({"synthetic": True}))
    source_sha = _payload("source-manifest")
    common: dict[str, object] = {
        "schema": FACTORY._SCHEDULE.R7_FINAL_SCHEMA,
        "status": FACTORY._SCHEDULE.R7_FINAL_STATUS,
        "integrity_status": FACTORY._SCHEDULE.R7_INTEGRITY_STATUS,
        "c3_decision": FACTORY._SCHEDULE.R7_GO_DECISION,
        "context_status": "CONTEXT_DIAGNOSTICS_PASS",
        "claim_ceiling": FACTORY._SCHEDULE.R7_CLAIM_CEILING,
        "source_count": 8,
        "fit_count": 48,
        "composition_count": 48,
        "contract_sha256": FACTORY._SCHEDULE.R7_CONTRACT_SHA256,
        "execution_addendum_sha256": FACTORY._SCHEDULE.R7_EXECUTION_ADDENDUM_SHA256,
        "launch_decision_sha256": _payload("launch-decision"),
        "code_manifest_sha256": hashlib.sha256(
            (
                FACTORY.REPO
                / ".scratch/multi-catfish-v023-r7-launch-ready/R7-LAUNCH-CODE-MANIFEST.json"
            ).read_bytes()
        ).hexdigest(),
        "preflight_manifest_sha256": preflight_sha,
        "launch_manifest_sha256": preflight_sha,
        "source_manifest_sha256": source_sha,
        "test_split_opened": False,
        "episode_training": False,
        "scientific_claim": False,
        "no_rescue": True,
        "no_scientific_token_before_integrity": True,
    }
    result_path = root / FACTORY.R7_ROOT_RESULT
    verification_path = root / FACTORY.R7_ROOT_VERIFICATION
    result_path.write_bytes(_canonical(common))
    verification_path.write_bytes(_canonical(common))
    (root / "LAUNCH-METADATA.json").write_bytes(
        _canonical(
            {
                "schema": "multi-catfish-mcrl-v023-lcsrs-r7-balanced-server-run-v1",
                "contract_sha256": common["contract_sha256"],
                "launch_decision_sha256": common["launch_decision_sha256"],
                "code_manifest_sha256": common["code_manifest_sha256"],
                "preflight_manifest_sha256": common["preflight_manifest_sha256"],
                "split": FACTORY._SCHEDULE.R7_SPLIT,
                "test_split_opened": False,
                "episode_training": False,
            }
        )
    )
    return root, common


def _seal_tree(root: Path) -> None:
    entries = []
    for path in sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix(),
    ):
        relative = path.relative_to(root).as_posix()
        entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}\n")
    manifest = root / "MANIFEST.sha256"
    manifest.write_text("".join(entries), encoding="ascii")
    manifest_sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
    (root / "COMPLETE").write_text(
        f"{manifest_sha}  MANIFEST.sha256\n", encoding="ascii"
    )


def test_authenticate_r7_requires_seal_then_computes_record_panel_digest(
    monkeypatch, tmp_path
):
    root, result = _make_sealed_r7_root(tmp_path / "r7")
    _seal_tree(root)

    worlds = FACTORY._SCHEDULE.R7_WORLDS
    panel = SimpleNamespace(
        source_manifest_sha256=result["source_manifest_sha256"],
        records_by_world={world: (object(),) for world in worlds},
    )
    record_panel_sha = _payload("record-panel")
    monkeypatch.setattr(FACTORY._FIT, "load_v023_source_panel", lambda **_: panel)
    monkeypatch.setattr(
        FACTORY._SCHEDULE,
        "canonical_record_panel_sha256",
        lambda records: record_panel_sha,
    )

    authenticated = FACTORY.authenticate_r7_go(root)
    assert authenticated.result_sha256 == hashlib.sha256(
        (root / "result.json").read_bytes()
    ).hexdigest()
    assert authenticated.binding.record_panel_sha256 == record_panel_sha
    assert authenticated.binding.gate_result_sha256 == authenticated.result_sha256
    assert authenticated.binding.source_manifest_sha256 == result["source_manifest_sha256"]
    assert authenticated.binding.split == FACTORY._SCHEDULE.R7_SPLIT

    (root / "COMPLETE").unlink()
    with pytest.raises(FACTORY.V023PostR7ProviderFactoryError, match="COMPLETE"):
        FACTORY.authenticate_r7_go(root)


def test_authenticate_r7_rejects_missing_authority_snapshot(
    monkeypatch, tmp_path
):
    root, result = _make_sealed_r7_root(tmp_path / "r7-missing-authority")
    (root / FACTORY.R7_ROOT_AUTHORITY).unlink()
    _seal_tree(root)
    worlds = FACTORY._SCHEDULE.R7_WORLDS
    panel = SimpleNamespace(
        source_manifest_sha256=result["source_manifest_sha256"],
        records_by_world={world: (object(),) for world in worlds},
    )
    monkeypatch.setattr(FACTORY._FIT, "load_v023_source_panel", lambda **_: panel)
    monkeypatch.setattr(
        FACTORY._SCHEDULE,
        "canonical_record_panel_sha256",
        lambda records: _payload("record-panel"),
    )
    with pytest.raises(
        FACTORY.V023PostR7ProviderFactoryError,
        match="AUTHORITY",
    ):
        FACTORY.authenticate_r7_go(root)


@dataclass(frozen=True)
class _FakeSchedule:
    receipt: dict[str, object]
    receipt_sha256: str
    epoch_budget: int = 100
    surfaces: tuple[object, ...] = ()
    informed_batches: tuple[object, ...] = ()
    neutral_batches: tuple[object, ...] = ()
    informed_targets_by_anchor: tuple[object, ...] = ()
    neutral_targets_by_anchor: tuple[object, ...] = ()
    informed_source_id: str = "c3-informed-source"
    neutral_source_id: str = "c3-neutral-source"


@pytest.fixture(scope="module")
def current_schedule():
    schedule_test_path = (
        FACTORY.REPO
        / ".scratch/multi-catfish-v023-c3-source-schedule/test_v023_c3_source_schedule.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v023_c3_schedule_fixture_for_post_r7_factory", schedule_test_path
    )
    assert spec is not None and spec.loader is not None
    schedule_test = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = schedule_test
    spec.loader.exec_module(schedule_test)
    records = schedule_test._records()
    binding = FACTORY._SCHEDULE.R7GoDecisionBinding(
        **schedule_test._binding(records).to_payload()
    )
    schedule = FACTORY._SCHEDULE.build_v023_c3_source_schedule(
        records,
        r7_go=binding,
        epoch_budget=100,
        schedule_seed=2026090701,
    )
    return records, binding, schedule


def test_build_provider_binds_target_manifest_schedule_and_source_ids(monkeypatch, tmp_path):
    r7_root = tmp_path / "r7"
    target_root = tmp_path / "target"
    target_root.mkdir()
    (target_root / "MANIFEST.sha256").write_bytes(b"synthetic-target-manifest\n")
    target_manifest_sha = hashlib.sha256(
        (target_root / "MANIFEST.sha256").read_bytes()
    ).hexdigest()

    r7 = SimpleNamespace(records=(object(),), binding=object())
    monkeypatch.setattr(FACTORY, "authenticate_r7_go", lambda _: r7)
    target_artifact = object()
    monkeypatch.setattr(
        FACTORY._BRIDGE,
        "load_completed_target_artifact",
        lambda _: target_artifact,
    )
    receipt_body = {
        "schema": "synthetic-c3",
        "source_training_epoch_budget": 100,
        "sources": {
            "neutral": {"source_id": "c3-neutral-source"},
            "informed": {"source_id": "c3-informed-source"},
        },
    }
    receipt_sha = FACTORY._SCHEDULE.canonical_sha256(receipt_body)
    schedule = _FakeSchedule(
        receipt={**receipt_body, "receipt_sha256": receipt_sha},
        receipt_sha256=receipt_sha,
    )
    monkeypatch.setattr(
        FACTORY._SCHEDULE,
        "build_v023_c3_source_schedule",
        lambda *args, **kwargs: schedule,
    )
    identity_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        FACTORY,
        "_schedule_receipt_identity",
        lambda value, **kwargs: identity_calls.append(
            {"schedule": value, **kwargs}
        )
        or receipt_sha,
    )
    c3_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        FACTORY._BRIDGE,
        "load_lcsrs_c3_inputs",
        lambda surfaces, batches, **kwargs: c3_calls.append(kwargs) or object(),
    )

    class FakeDelegate:
        def next_batch(self, **kwargs):
            return kwargs

        def sampler_state(self):
            return {"state": "synthetic"}

        def load_sampler_state(self, state):
            self.loaded = state

    delegate = FakeDelegate()
    monkeypatch.setattr(
        FACTORY._BRIDGE,
        "V023ProviderOrchestratorBridge",
        lambda *args, **kwargs: delegate,
    )

    provider = FACTORY.build_provider(
        FACTORY.PostR7ProviderConfig(
            r7_root=r7_root,
            target_root=target_root,
            epoch_budget=100,
            schedule_seed=2026090701,
        )
    )
    assert isinstance(provider, FACTORY._BRIDGE.DeterministicRouteBatchProvider)
    payload = provider.provider_identity_payload
    assert payload["target_manifest_sha256"] == target_manifest_sha
    assert payload["c3_schedule_receipt_sha256"] == receipt_sha
    assert payload["epoch_budget"] == 100
    assert payload["c3_source_ids"] == {
        "neutral": "c3-neutral-source",
        "informed": "c3-informed-source",
    }
    assert provider.planned_epoch_budget == 100
    assert provider.provider_identity.startswith(FACTORY.FACTORY_SCHEMA + ":")
    assert identity_calls == [
        {
            "schedule": schedule,
            "expected_epoch_budget": 100,
            "expected_schedule_seed": 2026090701,
            "expected_gate": r7.binding,
            "expected_records": r7.records,
        }
    ]
    assert provider.next_batch(route="C1", source="neutral", update_cursor=0)["route"] == "C1"
    assert provider.sampler_state() == {"state": "synthetic"}
    assert len(c3_calls) == 2


def test_schedule_receipt_rejects_thin_synthetic_receipt():
    receipt_body = {
        "schema": "synthetic-c3",
        "source_training_epoch_budget": 100,
        "sources": {
            "neutral": {"source_id": "c3-neutral-source"},
            "informed": {"source_id": "c3-informed-source"},
        },
    }
    receipt_sha = FACTORY._SCHEDULE.canonical_sha256(receipt_body)
    schedule = _FakeSchedule(
        receipt={**receipt_body, "receipt_sha256": receipt_sha},
        receipt_sha256=receipt_sha,
    )
    with pytest.raises(
        FACTORY.V023PostR7ProviderFactoryError,
        match="field set",
    ):
        FACTORY._schedule_receipt_identity(schedule, expected_epoch_budget=100)


def _stub_source_panel(monkeypatch, result):
    worlds = FACTORY._SCHEDULE.R7_WORLDS
    panel = SimpleNamespace(
        source_manifest_sha256=result["source_manifest_sha256"],
        records_by_world={world: (object(),) for world in worlds},
    )
    monkeypatch.setattr(FACTORY._FIT, "load_v023_source_panel", lambda **_: panel)
    monkeypatch.setattr(
        FACTORY._SCHEDULE,
        "canonical_record_panel_sha256",
        lambda records: _payload("record-panel"),
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("schema", "synthetic-authority", "authority snapshot crossed"),
        ("test_split_opened", True, "authority snapshot crossed"),
        ("episode_training", True, "authority snapshot crossed"),
    ),
)
def test_authority_snapshot_rejects_frozen_boundary_drift(
    monkeypatch, tmp_path, field, value, message
):
    root, result = _make_sealed_r7_root(tmp_path / f"r7-authority-{field}")
    authority_path = root / FACTORY.R7_ROOT_AUTHORITY
    authority = json.loads(authority_path.read_text(encoding="ascii"))
    authority[field] = value
    authority_path.write_bytes(_canonical(authority))
    _seal_tree(root)
    _stub_source_panel(monkeypatch, result)
    with pytest.raises(
        FACTORY.V023PostR7ProviderFactoryError,
        match=message,
    ):
        FACTORY.authenticate_r7_go(root)


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda payload: payload.__setitem__("schema", "synthetic"), "schema/status"),
        (lambda payload: payload.__setitem__("status", "PASS"), "schema/status"),
        (
            lambda payload: payload.__setitem__(
                "worlds", list(reversed(payload["worlds"]))
            ),
            "schema/status/world/seed",
        ),
        (
            lambda payload: payload.__setitem__(
                "student_seeds", [2026135200, *payload["student_seeds"][1:]]
            ),
            "schema/status/world/seed",
        ),
        (
            lambda payload: payload["configuration"].__setitem__("users", 101),
            "configuration.users",
        ),
        (
            lambda payload: payload["configuration"].__setitem__(
                "test_split_opened", True
            ),
            "configuration.test_split_opened",
        ),
        (
            lambda payload: payload["bindings"][0].__setitem__("sha256", "0" * 64),
            "base_contract",
        ),
        (
            lambda payload: payload["code_manifest"].__setitem__(
                "sha256", "0" * 64
            ),
            "code-manifest",
        ),
        (
            lambda payload: next(
                item
                for item in payload["bindings"]
                if item["role"] == "code_manifest"
            ).__setitem__("sha256", "0" * 64),
            "code_manifest binding",
        ),
    ),
)
def test_preflight_rejects_schema_boundary_and_relevant_binding_drift(
    tmp_path, mutation, message
):
    root, result = _make_sealed_r7_root(tmp_path / "r7-preflight")
    preflight_path = root / FACTORY.R7_ROOT_PREFLIGHT
    preflight = json.loads(preflight_path.read_text(encoding="ascii"))
    mutation(preflight)
    preflight_path.write_bytes(_canonical(preflight))
    preflight_sha = hashlib.sha256(preflight_path.read_bytes()).hexdigest()
    (root / FACTORY.R7_ROOT_PREFLIGHT_DIGEST).write_text(
        f"{preflight_sha}  R7-PREFLIGHT-MANIFEST.json\n", encoding="ascii"
    )
    with pytest.raises(
        FACTORY.V023PostR7ProviderFactoryError,
        match=message,
    ):
        FACTORY._verify_r7_preflight(
            root,
            expected_sha256=preflight_sha,
            expected_code_manifest_sha256=result["code_manifest_sha256"],
        )


def _reseal_schedule(schedule, mutation):
    receipt = schedule.receipt
    mutation(receipt)
    body = dict(receipt)
    body.pop("receipt_sha256")
    receipt_sha = FACTORY._SCHEDULE.canonical_sha256(body)
    receipt["receipt_sha256"] = receipt_sha
    return replace(
        schedule,
        canonical_receipt_bytes=FACTORY._SCHEDULE.canonical_bytes(receipt),
        receipt_sha256=receipt_sha,
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (
            lambda receipt: receipt.__setitem__("schema", "synthetic"),
            "schema/status/claim/budget",
        ),
        (
            lambda receipt: receipt["gate_decision"].__setitem__(
                "binding_sha256", "0" * 64
            ),
            "gate binding",
        ),
        (
            lambda receipt: receipt.__setitem__(
                "worlds", list(reversed(receipt["worlds"]))
            ),
            "worlds",
        ),
        (
            lambda receipt: receipt.__setitem__("record_panel_sha256", "0" * 64),
            "record panel",
        ),
        (
            lambda receipt: receipt["sampling"].__setitem__("explicit_seed", 77),
            "sampling seed",
        ),
        (
            lambda receipt: receipt["batch_schedule"]["batch_count_by_source"].__setitem__(
                "informed", 99
            ),
            "batch count",
        ),
        (
            lambda receipt: receipt["sources"]["neutral"].__setitem__(
                "source_sha256", "0" * 64
            ),
            "source hash",
        ),
        (
            lambda receipt: receipt.__setitem__("source_training_epoch_budget", 500),
            "budget",
        ),
    ),
)
def test_schedule_receipt_rejects_resealed_boundary_drift(
    current_schedule, mutation, message
):
    records, binding, schedule = current_schedule
    drifted = _reseal_schedule(schedule, mutation)
    with pytest.raises(
        FACTORY.V023PostR7ProviderFactoryError,
        match=message,
    ):
        FACTORY._schedule_receipt_identity(
            drifted,
            expected_epoch_budget=100,
            expected_schedule_seed=2026090701,
            expected_gate=binding,
            expected_records=records,
        )


def test_schedule_receipt_binds_current_schedule_and_gate(current_schedule):
    records, binding, schedule = current_schedule
    assert (
        FACTORY._schedule_receipt_identity(
            schedule,
            expected_epoch_budget=100,
            expected_schedule_seed=2026090701,
            expected_gate=binding,
            expected_records=records,
        )
        == schedule.receipt_sha256
    )
