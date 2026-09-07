from __future__ import annotations

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_relational_zr_c3_head import (
    RelationalZRC3NetworkConfig,
    RelationalZRC3QNetwork,
)


ACTION_DIM = 28


def _inputs() -> dict[str, torch.Tensor]:
    context = torch.zeros((1, ACTION_DIM, 7), dtype=torch.float32)
    tokens = torch.zeros((1, ACTION_DIM, 3, 6), dtype=torch.float32)
    mask = torch.zeros((1, ACTION_DIM), dtype=torch.bool)
    mask[0, :2] = True
    victims = torch.zeros((1, ACTION_DIM, 3), dtype=torch.bool)
    victims[0, 0, 1] = True
    victims[0, 1, 1:] = True
    compatible = torch.zeros((1, ACTION_DIM), dtype=torch.bool)
    compatible[0, 0] = True
    references = torch.tensor([0], dtype=torch.int64)
    return {
        "action_context": context,
        "victim_tokens": tokens,
        "action_mask": mask,
        "victim_mask": victims,
        "positive_credit_compatible": compatible,
        "reference_actions": references,
    }


def _constant_network(value: float, *, kappa_bits: float = 2.0) -> RelationalZRC3QNetwork:
    network = RelationalZRC3QNetwork(
        RelationalZRC3NetworkConfig(
            action_dim=ACTION_DIM,
            action_context_dim=7,
            victim_token_dim=6,
            hidden_layers=(),
            activation="tanh",
            kappa_bits=kappa_bits,
        )
    )
    linear = network.victim_scorer[0]
    assert isinstance(linear, torch.nn.Linear)
    with torch.no_grad():
        linear.weight.zero_()
        linear.bias.fill_(value)
    return network


def test_positive_credit_is_gated_but_negative_credit_always_counts() -> None:
    values = _inputs()
    positive = _constant_network(2.0)
    q_positive_blocked = positive(**values)
    assert q_positive_blocked[0, 0].item() == 0.0
    assert q_positive_blocked[0, 1].item() == -1.0

    values["positive_credit_compatible"][0, 1] = True
    q_positive_allowed = positive(**values)
    assert q_positive_allowed[0, 1].item() == 1.0

    values["positive_credit_compatible"][0, 1] = False
    negative = _constant_network(-2.0)
    q_negative = negative(**values)
    assert q_negative[0, 0].item() == 0.0
    assert q_negative[0, 1].item() == -1.0


def test_victim_permutation_and_masked_padding_do_not_change_q3() -> None:
    network = _constant_network(-0.5, kappa_bits=1.0)
    values = _inputs()
    values["victim_tokens"][0, 0, 1, 0] = 2.0
    values["victim_tokens"][0, 1, 1, 0] = 3.0
    values["victim_tokens"][0, 1, 2, 0] = 4.0
    expected = network(**values)

    permutation = torch.tensor([2, 0, 1], dtype=torch.int64)
    permuted = dict(values)
    permuted["victim_tokens"] = values["victim_tokens"][:, :, permutation]
    permuted["victim_mask"] = values["victim_mask"][:, :, permutation]
    torch.testing.assert_close(network(**permuted), expected, rtol=0.0, atol=0.0)

    padded = dict(values)
    padded["victim_tokens"] = values["victim_tokens"].clone()
    padded["victim_tokens"][~values["victim_mask"]] = 1.0e9
    torch.testing.assert_close(network(**padded), expected, rtol=0.0, atol=0.0)


def test_reference_is_exact_zero_and_illegal_actions_are_zero() -> None:
    q3 = _constant_network(-1.0)(**_inputs())
    assert q3.shape == (1, ACTION_DIM)
    assert q3[0, 0].item() == 0.0
    assert torch.count_nonzero(q3[0, 2:]).item() == 0
    assert bool(torch.isfinite(q3).all())


def test_public_surface_is_differentiable_through_the_shared_victim_scorer() -> None:
    network = _constant_network(-1.0)
    q3 = network(**_inputs())
    q3[0, 1].square().backward()
    gradients = [parameter.grad for parameter in network.parameters()]
    assert all(gradient is not None for gradient in gradients)
    assert any(bool(torch.any(gradient != 0.0)) for gradient in gradients if gradient is not None)


def test_invalid_reference_and_nonfinite_inputs_fail_closed() -> None:
    network = _constant_network(-1.0)
    values = _inputs()
    values["reference_actions"] = torch.tensor([2], dtype=torch.int64)
    with pytest.raises(ValueError, match="reference"):
        network(**values)

    values = _inputs()
    values["victim_tokens"][0, 1, 1, 0] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        network(**values)


def test_no_environment_or_action_decoder_dependency() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "mcrl"
        / "algorithms"
        / "ee_axis_relational_zr_c3_head.py"
    )
    text = source.read_text(encoding="utf-8")
    for forbidden in (
        "StepEnvironment",
        "ActionEvaluation",
        "evaluate_actions",
        "KeyedFadingField",
        "np.random",
        "argmax",
    ):
        assert forbidden not in text
