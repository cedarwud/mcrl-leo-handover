from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
from pathlib import Path

import pytest
import torch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "run_c1_consumer_gate", HERE / "run_c1_consumer_gate.py"
)
assert SPEC is not None and SPEC.loader is not None
G = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = G
SPEC.loader.exec_module(G)


def write_schedule_fixture(root: Path, *, label: str = "informed"):
    branch = root / label
    branch.mkdir()
    receipts = []
    specialist = []
    episodes = []
    for episode in range(G.EPISODES):
        comparator = f"{episode + 1:064x}"
        episodes.append(
            {
                "episode": episode,
                "main_update_count": 10,
                "gate_ledger": {"C1": "route", "C2": "shadow", "C3": "shadow"},
                "frozen_main_comparator_sha256": comparator,
            }
        )
        for step in range(10):
            index = episode * 10 + step
            main_id = f"{label}-main-{index}"
            c1_id = f"{label}-c1-{index}"
            warmup = index == 0
            quota = {
                "mode": "warmup_no_update" if warmup else "source_unit_mean",
                "source_units": [] if warmup else ["Main", "C1"],
                "specialist_bundle_ids": [] if warmup else [c1_id],
                "requested_source_units": ["Main", "C1"],
                "main_bundle_id": main_id,
                "admitted_specialist_bundle_ids": [c1_id],
                "main_replay_size_before_update": (index + 1) * 100,
                "main_batch_size": G.MAIN_BATCH_SIZE,
                "canonical_replay_rng_sample_consumed": not warmup,
                "missing_source_ids": [],
                "unusable_specialist_bundle_ids": [],
            }
            if not warmup:
                quota["unit_definition"] = "one_complete_atomic_bundle_per_source"
            receipts.append(
                {
                    "episode": episode,
                    "step": step,
                    "main_bundle_id": main_id,
                    "quota_receipt": quota,
                }
            )
            specialist.append(
                {
                    "episode": episode,
                    "step": step,
                    "source": "C1",
                    "collected_bundle_id": c1_id,
                    "comparator_block": episode,
                    "frozen_main_comparator_sha256": comparator,
                }
            )
    (branch / "main-update-receipts.json").write_text(
        json.dumps(receipts), encoding="utf-8"
    )
    (branch / "episode-logs.json").write_text(
        json.dumps(episodes), encoding="utf-8"
    )
    (branch / "specialist-replay-receipts.json").write_text(
        json.dumps(specialist), encoding="utf-8"
    )
    result = {
        "source_dashboard": {
            "C1": {"routed_bundles": 40},
            "C2": {"routed_bundles": 0},
            "C3": {"routed_bundles": 0},
        },
        "consumed_specialist_bundle_count": 40,
    }
    return branch, result, receipts


def write_seed_authority(root: Path, monkeypatch):
    bindings = {"runner_sha256": "a" * 64}
    inventory_path = root / "inventory.json"
    inventory = {
        "schema": G.INVENTORY_SCHEMA,
        "status": "CAPTURED_BEFORE_SEED_DERIVATION",
        "claim_ceiling": G.CLAIM_CEILING,
        "numeric_token_set_sha256": "b" * 64,
        "numeric_token_count": 17,
    }
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    closure_path = root / "closure.json"
    normalized = "tests passed in <elapsed>s"
    closure = {
        "schema": G.CLOSURE_SCHEMA,
        "status": "CLOSED_BEFORE_SEED_DERIVATION",
        "claim_ceiling": G.CLAIM_CEILING,
        "bindings": bindings,
        "pre_reveal_inventory": {
            "path": str(inventory_path),
            "sha256": G.sha256_file(inventory_path),
            "numeric_token_set_sha256": "b" * 64,
            "numeric_token_count": 17,
        },
        "test_receipt": {
            "exit_code": 0,
            "normalised_stdout": normalized,
            "normalised_stdout_sha256": hashlib.sha256(
                normalized.encode("utf-8")
            ).hexdigest(),
            "wall_clock_text_excluded_from_seed_material": True,
        },
    }
    closure_path.write_text(json.dumps(closure), encoding="utf-8")
    closure_sha = G.sha256_file(closure_path)
    selected = []
    attempts = []
    runtime = {}
    counter = 0
    while len(selected) < 8:
        candidate = G._derive_candidate(closure_sha, counter)
        proposed = G._runtime_derived_seeds(candidate) if not selected else {}
        accepted = bool(
            candidate not in selected
            and candidate not in set(runtime.values())
            and not (set(proposed.values()) & set(selected))
            and len(set(proposed.values())) == len(proposed)
        )
        attempts.append(
            {
                "counter": counter,
                "candidate": candidate,
                "accepted": accepted,
                "known_prior_collision": False,
                "selected_collision": candidate in selected,
                "runtime_derived_collision": candidate in set(runtime.values()),
                "repository_matches": [],
                "proposed_runtime_derived_seeds": proposed,
                "proposed_runtime_derived_repository_matches": {
                    name: [] for name in proposed
                },
            }
        )
        if accepted:
            selected.append(candidate)
            if len(selected) == 1:
                runtime = proposed
        counter += 1
    search_path = root / "search.json"
    search = {
        "schema": G.DISJOINTNESS_SCHEMA,
        "status": "PASS",
        "seed_namespace": G.SEED_NAMESPACE,
        "closure_manifest_sha256": closure_sha,
        "selected_seeds": selected,
        "runtime_derived_seeds": runtime,
        "known_prior_seed_values": [],
        "known_prior_seed_values_sha256": hashlib.sha256(b"[]").hexdigest(),
        "pre_reveal_inventory_path": str(inventory_path),
        "pre_reveal_inventory_sha256": G.sha256_file(inventory_path),
        "all_selected_have_zero_pre_reveal_matches": True,
        "candidate_attempts": attempts,
    }
    search_path.write_text(json.dumps(search), encoding="utf-8")
    seed_path = root / "seeds.json"
    campaign_path = root / "campaign.json"
    execution_path = root / "execution.json"
    campaign = {
        "schema": G.CAMPAIGN_SCHEMA,
        "status": "SEALED_SINGLE_CAMPAIGN_BEFORE_SEED_REVEAL",
        "claim_ceiling": G.CLAIM_CEILING,
        "closure_manifest_path": str(closure_path),
        "closure_manifest_sha256": closure_sha,
        "seed_manifest_path": str(seed_path),
        "execution_ledger_path": str(execution_path),
        "no_second_freeze_or_execution_is_authorised": True,
    }
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
    manifest = {
        "schema": G.SEED_SCHEMA,
        "status": "frozen",
        "seed_namespace": G.SEED_NAMESPACE,
        "seed_count": 8,
        "derivation": "first eight collision-free uint32 values from closure-bound counter-separated SHA-256",
        "repository_disjointness_checked_before_reveal": True,
        "forbidden_checkpoint_seeds": [],
        "forbidden_gate1_seeds": [],
        "training_seed": selected[0],
        "environment_seed": selected[1],
        "mobility_seed": selected[2],
        "evaluation_seeds": selected[3:],
        "runtime_derived_seeds": runtime,
        "closure_manifest_path": str(closure_path),
        "closure_manifest_sha256": closure_sha,
        "pre_reveal_inventory_path": str(inventory_path),
        "pre_reveal_inventory_sha256": G.sha256_file(inventory_path),
        "disjointness_search_receipt_path": str(search_path),
        "disjointness_search_receipt_sha256": G.sha256_file(search_path),
        "campaign_ledger_path": str(campaign_path),
        "campaign_ledger_sha256": G.sha256_file(campaign_path),
        "execution_ledger_path": str(execution_path),
        **bindings,
    }
    seed_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(G, "CAMPAIGN_LEDGER", campaign_path)
    monkeypatch.setattr(G, "EXECUTION_LEDGER", execution_path)
    monkeypatch.setattr(G, "_numeric_inventory", lambda: ("b" * 64, 17))
    monkeypatch.setattr(G, "_repo_matches", lambda _seed: ())
    return seed_path, bindings, search_path


def test_runner_requires_exact_current_source_gate_verification(tmp_path, monkeypatch):
    source_gate = tmp_path / "source-gate.json"
    source_gate.write_text(json.dumps({"schema": "fixture"}), encoding="utf-8")
    addendum = tmp_path / "addendum.json"
    addendum.write_text("{}", encoding="utf-8")
    correction = tmp_path / "correction.json"
    correction.write_text("{}", encoding="utf-8")
    expected = {
        "schema": "verification",
        "status": "PASS",
        "failures": [],
        "corrective_replay_addendum_path": str(addendum),
        "corrective_replay_verification_path": str(correction),
    }
    verification = tmp_path / "verification.json"
    verification.write_text(json.dumps(expected), encoding="utf-8")
    monkeypatch.setattr(
        G,
        "verify_c1_source_gate",
        lambda _payload, **_kwargs: dict(expected),
    )

    assert G._validate_source_gate_verification(source_gate, verification) == expected

    tampered = dict(expected)
    tampered["failures"] = ["rehashed_tamper"]
    verification.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(RuntimeError, match="exact current-authority replay"):
        G._validate_source_gate_verification(source_gate, verification)


def test_parent_seed_authority_is_hash_authenticated_before_use(tmp_path):
    seeds = tmp_path / "parent-seeds.json"
    seeds.write_text(json.dumps({"seeds": [11, 22, 33]}), encoding="utf-8")
    parent = {
        "authority": {
            "seed_manifest_path": str(seeds),
            "seed_manifest_sha256": G.sha256_file(seeds),
        }
    }
    assert G._authenticated_parent_seed_values(parent, label="fixture") == {11, 22, 33}

    seeds.write_text(json.dumps({"seeds": [11, 22, 44]}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="seed manifest hash mismatch"):
        G._authenticated_parent_seed_values(parent, label="fixture")


def test_gate1_prior_seeds_are_read_from_authenticated_zero_dose_state(
    tmp_path, monkeypatch
):
    baseline = tmp_path / "baseline-state.pt"
    torch.save({"train_seed": 101, "env_seed": 202, "mobility_seed": 303}, baseline)
    parity = tmp_path / "parity.json"
    parity.write_text("{}", encoding="utf-8")
    gate2 = tmp_path / "gate2.json"
    gate2.write_text(
        json.dumps(
            {
                "authority": {
                    "zero_dose_parity_path": str(parity),
                    "zero_dose_parity_sha256": G.sha256_file(parity),
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        G,
        "validate_zero_dose_receipt",
        lambda _path: {
            "authority": {
                "baseline_state_path": str(baseline),
                "baseline_state_sha256": G.sha256_file(baseline),
            }
        },
    )

    assert G._gate1_prior_seeds(gate2) == {101, 202, 303}


def test_pretransfer_gate_must_bind_supplied_checkpoint_and_corpus(
    tmp_path, monkeypatch
):
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"checkpoint")
    corpus = tmp_path / "corpus.json"
    corpus.write_text("{}", encoding="utf-8")
    gate2 = tmp_path / "gate2.json"
    gate2.write_text(
        json.dumps(
            {
                "authority": {
                    "checkpoint_path": str(checkpoint),
                    "checkpoint_sha256": G.sha256_file(checkpoint),
                    "corpus_manifest_path": str(corpus),
                    "corpus_manifest_sha256": G.sha256_file(corpus),
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        G,
        "validate_c1_pretransfer_result",
        lambda _path: {"status": "PASS", "decision": "ROUTE"},
    )
    assert G._validate_pretransfer_lineage(
        gate2, checkpoint=checkpoint, corpus_manifest=corpus
    )["decision"] == "ROUTE"

    other = tmp_path / "other-corpus.json"
    other.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not bind the supplied corpus"):
        G._validate_pretransfer_lineage(
            gate2, checkpoint=checkpoint, corpus_manifest=other
        )


def row(seed: int, delta: float, service_delta: float = 0.0):
    neutral_ee = 10.0
    neutral_service = 0.95
    intervals = 1000
    return {
        "evaluation_seed": seed,
        "delta_ee_bits_per_j": delta,
        "neutral": {
            "system_ee_bits_per_j": neutral_ee,
            "useful_bits": neutral_ee * 100.0,
            "system_energy_j": 100.0,
            "served_user_intervals": int(neutral_service * intervals),
            "total_user_intervals": intervals,
        },
        "informed": {
            "system_ee_bits_per_j": neutral_ee + delta,
            "useful_bits": (neutral_ee + delta) * 100.0,
            "system_energy_j": 100.0,
            "served_user_intervals": int((neutral_service + service_delta) * intervals),
            "total_user_intervals": intervals,
        },
    }


def test_efficacy_screen_passes_only_all_frozen_checks():
    result = G.decide_c1_efficacy_screen(
        [row(index, delta) for index, delta in enumerate((2, 1, 3, 1, -0.5))],
        guard_failures=(),
    )
    assert result["status"] == "PASS"
    assert result["decision"] == "CONTINUE_10EP"
    assert result["metrics"]["positive_seed_count"] == 4


@pytest.mark.parametrize(
    ("rows", "guards", "failed_check"),
    [
        ([row(i, 1.0) for i in range(5)], ("hash",), "all_structural_guards"),
        ([row(i, -1.0) for i in range(5)], (), "mean_paired_delta_positive"),
        ([row(i, d) for i, d in enumerate((2, 2, 2, -1, -1))], (), "positive_on_at_least_four_seeds"),
        ([row(i, 1.0, -0.006) for i in range(5)], (), "served_fraction_guard"),
    ],
)
def test_efficacy_screen_fails_closed(rows, guards, failed_check):
    result = G.decide_c1_efficacy_screen(rows, guard_failures=guards)
    assert result["status"] == "FAIL"
    assert result["decision"] == "STOP_AND_REDESIGN_C1"
    assert not result["checks"][failed_check]


def test_efficacy_screen_rejects_wrong_or_duplicate_denominator():
    with pytest.raises(ValueError, match="exactly five"):
        G.decide_c1_efficacy_screen([row(i, 1.0) for i in range(4)], guard_failures=())
    with pytest.raises(ValueError, match="unique"):
        G.decide_c1_efficacy_screen([row(1, 1.0) for _ in range(5)], guard_failures=())


def test_efficacy_screen_rejects_missing_or_inconsistent_explicit_delta():
    rows = [row(index, 1.0) for index in range(5)]
    rows[0]["delta_ee_bits_per_j"] = 9.0
    with pytest.raises(ValueError, match="missing or inconsistent"):
        G.decide_c1_efficacy_screen(rows, guard_failures=())


def test_schedule_validator_derives_warmup_prefix_and_applied_denominator(tmp_path):
    branch, result, _ = write_schedule_fixture(tmp_path)
    failures, receipt = G._validate_branch_schedule(
        branch_dir=branch, result=result, label="informed"
    )

    assert failures == []
    assert receipt["warmup_indices"] == [0]
    assert receipt["source_unit_update_indices"] == list(range(1, 40))
    assert receipt["unique_admitted_c1_bundle_ids"] == 40
    assert receipt["unique_applied_c1_bundle_ids"] == 39


def test_schedule_validator_rejects_specialist_unit_applied_during_warmup(tmp_path):
    branch, result, receipts = write_schedule_fixture(tmp_path)
    receipts[0]["quota_receipt"]["specialist_bundle_ids"] = ["informed-c1-0"]
    (branch / "main-update-receipts.json").write_text(
        json.dumps(receipts), encoding="utf-8"
    )

    failures, _ = G._validate_branch_schedule(
        branch_dir=branch, result=result, label="informed"
    )
    assert "informed_warmup_schedule_0" in failures


def test_seed_manifest_rederives_search_and_rejects_rehashed_tampering(
    tmp_path, monkeypatch
):
    seed_path, bindings, search_path = write_seed_authority(tmp_path, monkeypatch)
    validated = G._validate_seed_manifest(
        seed_path,
        bindings=bindings,
        known_prior_seeds=set(),
        checkpoint_seeds=set(),
        gate1_seeds=set(),
    )
    assert validated["seed_count"] == 8

    search = json.loads(search_path.read_text(encoding="utf-8"))
    search["selected_seeds"] = list(reversed(search["selected_seeds"]))
    search_path.write_text(json.dumps(search), encoding="utf-8")
    manifest = json.loads(seed_path.read_text(encoding="utf-8"))
    manifest["disjointness_search_receipt_sha256"] = G.sha256_file(search_path)
    seed_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(RuntimeError, match="disjointness receipt"):
        G._validate_seed_manifest(
            seed_path,
            bindings=bindings,
            known_prior_seeds=set(),
            checkpoint_seeds=set(),
            gate1_seeds=set(),
        )
