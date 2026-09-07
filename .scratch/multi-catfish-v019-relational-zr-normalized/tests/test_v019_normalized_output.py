"""Pure tests for the isolated V0.19 normalized-output parameterization.

These tests use synthetic tensors/source rows only.  They do not open a
simulator, harvest a world, read TEST, or launch a learner gate.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import torch


HERE = Path(__file__).resolve()
V019 = HERE.parents[1]
REPO = V019.parents[1]
sys.path.insert(0, str(V019 / "learner"))
sys.path.insert(0, str(REPO / "src"))

from mcrl.algorithms.ee_axis_relational_zr_c3_head import (  # noqa: E402
    RelationalZRC3NetworkConfig as LegacyNetworkConfig,
    RelationalZRC3QNetwork as LegacyNetwork,
)
from mcrl.algorithms.ee_axis_relational_zr_c3_head_v019 import (  # noqa: E402
    NORMALIZED_BITS_PER_KAPPA,
    RAW_BITS,
    RelationalZRC3NetworkConfig,
    RelationalZRC3QNetwork,
)
from relational_q3_learner_v019 import (  # noqa: E402
    RelationalLearnerError,
    RelationalZRC3LearnerConfig,
    RelationalZRC3PairwiseLearner,
)
import relational_learner_runner_v019 as runner  # noqa: E402
from relational_source_schema import (  # noqa: E402
    ACTION_CONTEXT_DIM,
    ACTION_DIM,
    RelationalZRC3Source,
    VICTIM_TOKEN_DIM,
)


KAPPA = 64.0


def _inputs(*, rows: int = 2, actions: int = 4, victims: int = 2):
    generator = torch.Generator().manual_seed(19)
    context = torch.randn(
        rows, actions, 2, generator=generator, dtype=torch.float32
    )
    tokens = torch.randn(
        rows, actions, victims, 2, generator=generator, dtype=torch.float32
    )
    action_mask = torch.ones(rows, actions, dtype=torch.bool)
    victim_mask = torch.ones(rows, actions, victims, dtype=torch.bool)
    compatible = torch.ones(rows, actions, dtype=torch.bool)
    references = torch.zeros(rows, dtype=torch.int64)
    return context, tokens, action_mask, victim_mask, compatible, references


def _config(mode: str, *, kappa: float = KAPPA) -> RelationalZRC3NetworkConfig:
    return RelationalZRC3NetworkConfig(
        action_dim=4,
        action_context_dim=2,
        victim_token_dim=2,
        hidden_layers=(5,),
        activation="tanh",
        kappa_bits=kappa,
        output_unit_mode=mode,
    )


def _forward(network: RelationalZRC3QNetwork) -> torch.Tensor:
    return network(*_inputs())


def _scale_final_layer(
    source: RelationalZRC3QNetwork,
    target: RelationalZRC3QNetwork,
    *,
    factor: float,
) -> None:
    """Copy hidden weights and scale the final scorer by ``factor``."""

    source_state = source.state_dict()
    target_state = target.state_dict()
    final_prefix = "victim_scorer." + str(len(source.victim_scorer) - 1) + "."
    for name, value in source_state.items():
        target_state[name] = value.clone()
        if name.startswith(final_prefix):
            target_state[name].mul_(factor)
    target.load_state_dict(target_state, strict=True)


def test_final_layer_scaling_is_algebraically_equivalent() -> None:
    raw = RelationalZRC3QNetwork(_config(RAW_BITS))
    normalized = RelationalZRC3QNetwork(_config(NORMALIZED_BITS_PER_KAPPA))
    # A normalized scorer emits the raw scorer contribution divided by kappa.
    _scale_final_layer(raw, normalized, factor=1.0 / KAPPA)
    raw_values = _forward(raw)
    normalized_values = _forward(normalized)
    torch.testing.assert_close(normalized_values, raw_values, rtol=0.0, atol=1e-7)


def test_normalized_mode_removes_final_one_over_kappa_gradient_suppression() -> None:
    raw = RelationalZRC3QNetwork(_config(RAW_BITS))
    normalized = RelationalZRC3QNetwork(_config(NORMALIZED_BITS_PER_KAPPA))
    _scale_final_layer(raw, normalized, factor=1.0 / KAPPA)
    with torch.no_grad():
        # Keep every contribution on the positive-compatible branch so the
        # final-layer gradient comparison isolates the output parameterization.
        for network, bias in ((raw, 16.0), (normalized, 16.0 / KAPPA)):
            final = network.victim_scorer[-1]
            final.weight.mul_(0.01)
            final.bias.fill_(bias)
    raw.victim_scorer[-1].weight.grad = None
    normalized.victim_scorer[-1].weight.grad = None
    raw_loss = _forward(raw)[:, 1].sum()
    normalized_loss = _forward(normalized)[:, 1].sum()
    raw_loss.backward()
    normalized_loss.backward()
    raw_grad = raw.victim_scorer[-1].weight.grad
    normalized_grad = normalized.victim_scorer[-1].weight.grad
    assert raw_grad is not None and normalized_grad is not None
    torch.testing.assert_close(
        normalized_grad,
        raw_grad * KAPPA,
        rtol=2e-5,
        atol=2e-6,
    )
    assert float(torch.linalg.vector_norm(normalized_grad)) > float(
        torch.linalg.vector_norm(raw_grad)
    ) * (KAPPA / 2.0)


def test_raw_mode_matches_the_unchanged_v018_head() -> None:
    legacy_config = LegacyNetworkConfig(
        action_dim=4,
        action_context_dim=2,
        victim_token_dim=2,
        hidden_layers=(5,),
        activation="tanh",
        kappa_bits=KAPPA,
    )
    legacy = LegacyNetwork(legacy_config)
    current = RelationalZRC3QNetwork(_config(RAW_BITS))
    current.load_state_dict(legacy.state_dict(), strict=True)
    legacy_values = legacy(*_inputs())
    current_values = current(*_inputs())
    assert torch.equal(current_values, legacy_values)


def _source() -> RelationalZRC3Source:
    rng = np.random.default_rng(23)
    rows = 2
    context = rng.normal(size=(rows, ACTION_DIM, ACTION_CONTEXT_DIM)).astype(np.float64)
    tokens = rng.normal(
        size=(rows, ACTION_DIM, 2, VICTIM_TOKEN_DIM)
    ).astype(np.float64)
    action_mask = np.ones((rows, ACTION_DIM), dtype=np.bool_)
    victim_mask = np.ones((rows, ACTION_DIM, 2), dtype=np.bool_)
    compatible = np.ones((rows, ACTION_DIM), dtype=np.bool_)
    references = np.zeros(rows, dtype=np.int64)
    target = rng.normal(size=(rows, ACTION_DIM)).astype(np.float64)
    target[~action_mask] = 0.0
    target[np.arange(rows), references] = 0.0
    context[~action_mask] = 0.0
    tokens[~victim_mask] = 0.0
    return RelationalZRC3Source(
        action_context=context,
        victim_tokens=tokens,
        action_mask=action_mask,
        victim_mask=victim_mask,
        positive_credit_compatible=compatible,
        reference_actions=references,
        target_surface_bits=target,
        world_seed=101,
        lineage=1,
        split="TRAIN",
        field_root_digest="a" * 64,
        kappa_bits=KAPPA,
    )


def _learner_config(mode: str) -> RelationalZRC3LearnerConfig:
    return RelationalZRC3LearnerConfig(
        hidden_layers=(4,),
        learning_rate=0.001,
        kappa_bits=KAPPA,
        beta=0.0,
        output_unit_mode=mode,
    )


def _run_config(mode: str) -> runner.RelationalLearnerRunConfig:
    schedule = tuple(
        runner.LearnerBatchSpec(31, 101, 41, (0, 1)) for _ in range(100)
    )
    return runner.RelationalLearnerRunConfig(
        contract_sha256="a" * 64,
        code_manifest_sha256="b" * 64,
        train_worlds=(101,),
        validation_worlds=(201,),
        initialization_lineages=((31, 41),),
        q1_checkpoint_sha256_by_lineage=((41, "c" * 64),),
        q2_checkpoint_sha256_by_lineage=((41, "d" * 64),),
        batch_schedule=schedule,
        batch_size=2,
        update_count=100,
        action_dim=ACTION_DIM,
        action_context_dim=ACTION_CONTEXT_DIM,
        victim_token_dim=VICTIM_TOKEN_DIM,
        hidden_layers=(4,),
        activation="tanh",
        learning_rate=0.001,
        kappa_bits=KAPPA,
        beta=0.0,
        output_unit_mode=mode,
    )


def test_v019_run_config_requires_and_authenticates_mode(tmp_path: Path) -> None:
    config = _run_config(NORMALIZED_BITS_PER_KAPPA)
    body = config.as_dict()
    body.update(
        {
            "schema": runner.CONFIG_SCHEMA,
            "schema_version": runner.CONFIG_VERSION,
            "train_source_paths": ["train/101-41"],
            "validation_source_paths": ["validation/201-41"],
        }
    )
    path = tmp_path / "run-config.json"
    path.write_bytes(runner._canonical_bytes(body))
    loaded, train_paths, validation_paths = runner.read_run_config(path)
    assert loaded.output_unit_mode == NORMALIZED_BITS_PER_KAPPA
    assert train_paths == (str((tmp_path / "train/101-41").absolute()),)
    assert validation_paths == (str((tmp_path / "validation/201-41").absolute()),)

    drift = dict(body)
    drift["output_unit_mode"] = RAW_BITS
    drift_path = tmp_path / "run-config-drift.json"
    drift_path.write_bytes(runner._canonical_bytes(drift))
    with pytest.raises(runner.RelationalLearnerRunnerError, match="output_unit_mode"):
        runner.read_run_config(drift_path)

    missing = dict(body)
    del missing["output_unit_mode"]
    missing_path = tmp_path / "run-config-missing-mode.json"
    missing_path.write_bytes(runner._canonical_bytes(missing))
    with pytest.raises(runner.RelationalLearnerRunnerError, match="unknown or missing"):
        runner.read_run_config(missing_path)


def test_checkpoint_rejects_unit_mode_drift_and_receipts_name_mode(tmp_path: Path) -> None:
    source = _source()
    normalized = RelationalZRC3PairwiseLearner(
        _learner_config(NORMALIZED_BITS_PER_KAPPA), train_seed=7
    )
    for _ in range(100):
        normalized.update(source)
    checkpoint = normalized.checkpoint_state(
        contract_sha256="e" * 64,
        source_sha256="f" * 64,
        code_manifest_sha256="1" * 64,
    )
    assert checkpoint["output_unit_mode"] == NORMALIZED_BITS_PER_KAPPA
    assert checkpoint["config"]["output_unit_mode"] == NORMALIZED_BITS_PER_KAPPA
    raw = RelationalZRC3PairwiseLearner(_learner_config(RAW_BITS), train_seed=7)
    with pytest.raises(RelationalLearnerError, match="config mismatch"):
        raw.load_checkpoint_state(
            checkpoint,
            contract_sha256="e" * 64,
            source_sha256="f" * 64,
            code_manifest_sha256="1" * 64,
        )
    tampered = dict(checkpoint)
    tampered["output_unit_mode"] = RAW_BITS
    with pytest.raises(RelationalLearnerError, match="output_unit_mode"):
        normalized.load_checkpoint_state(
            tampered,
            contract_sha256="e" * 64,
            source_sha256="f" * 64,
            code_manifest_sha256="1" * 64,
        )


def test_old_v018_frozen_receipt_is_not_rewritten() -> None:
    frozen = (
        REPO
        / ".scratch/multi-catfish-v018-relational-zr/next-learner-r2/contracts"
        / "MULTI-CATFISH-MCRL-V018-RELATIONAL-Q3-LEARNER-PREREG-FROZEN-2026-09-04.md"
    )
    if not frozen.is_file():
        pytest.skip("V0.18 frozen receipt is not present in this checkout")
    expected = "1b3952a47547fdc61854e8f153d643c5d83573c3a3e15d44a7e489682b1c76d5"
    before = hashlib.sha256(frozen.read_bytes()).hexdigest()
    assert before == expected
    # The assertion is deliberately read-only: V0.19 introduces a new path and
    # never rewrites the historical V0.18 receipt.
    after = hashlib.sha256(frozen.read_bytes()).hexdigest()
    assert after == expected
