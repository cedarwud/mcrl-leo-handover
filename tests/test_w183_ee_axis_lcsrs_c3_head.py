"""W-183 -- V0.23 shared LC-SRS C3 token scorer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from mcrl.algorithms.ee_axis_lcsrs_c3_head import LCSRSC3QNetwork
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view


def _inputs(*, requires_grad: bool = False) -> dict[str, torch.Tensor]:
    users, actions = 2, 28
    context = torch.zeros((users, actions, 29), dtype=torch.float32, requires_grad=requires_grad)
    tokens = torch.zeros((users, actions, users + 1, 38), dtype=torch.float32)
    mask = torch.zeros((users, actions), dtype=torch.bool)
    mask[:, :2] = True
    token_mask = torch.zeros((users, actions, users + 1), dtype=torch.bool)
    token_mask[:, :, users] = mask
    # User 0/action 1 has two ordinary tokens plus its required pair token;
    # its reference has the pair token only.
    token_mask[0, 1, 0] = True
    token_mask[0, 1, 1] = True
    tokens[0, 1, 0, 0] = 1.0
    tokens[0, 1, 1, 0] = 1.0
    tokens[:, :, users, 1][mask] = 1.0
    if requires_grad:
        tokens.requires_grad_()
    return {
        "action_context": context,
        "tokens": tokens,
        "token_mask": token_mask,
        "action_mask": mask,
        "reference_actions": torch.zeros(users, dtype=torch.int64),
    }


def _constant_network(value: float) -> LCSRSC3QNetwork:
    network = LCSRSC3QNetwork()
    with torch.no_grad():
        for module in network.token_scorer:
            if isinstance(module, torch.nn.Linear):
                module.weight.zero_()
                module.bias.zero_()
        final = network.token_scorer[-1]
        assert isinstance(final, torch.nn.Linear)
        final.bias.fill_(value)
    return network


def test_fixed_67_64_64_1_scorer_reference_centering_and_illegal_zeroes() -> None:
    network = _constant_network(1.5)
    layers = [module for module in network.token_scorer if isinstance(module, torch.nn.Linear)]
    assert [(layer.in_features, layer.out_features) for layer in layers] == [
        (67, 64),
        (64, 64),
        (64, 1),
    ]
    output = network(**_inputs())
    assert output.shape == (2, 28)
    assert output[0, 0].item() == 0.0
    assert output[0, 1].item() == 3.0  # (three tokens - one reference token) * 1.5
    assert torch.count_nonzero(output[:, 2:]).item() == 0


def test_positive_and_negative_contributions_survive_without_a_compatibility_gate() -> None:
    values = _inputs()
    assert _constant_network(2.0)(**values)[0, 1].item() == 4.0
    assert _constant_network(-2.0)(**values)[0, 1].item() == -4.0
    source = Path(__file__).resolve().parents[1] / "src/mcrl/algorithms/ee_axis_lcsrs_c3_head.py"
    assert "positive_credit" not in source.read_text(encoding="utf-8")


def test_ordinary_token_permutation_is_invariant_and_masked_padding_is_ignored() -> None:
    network = _constant_network(0.75)
    values = _inputs()
    expected = network(**values)
    permuted = dict(values)
    permutation = torch.tensor([1, 0, 2], dtype=torch.int64)
    permuted["tokens"] = values["tokens"][:, :, permutation]
    permuted["token_mask"] = values["token_mask"][:, :, permutation]
    torch.testing.assert_close(network(**permuted), expected, rtol=0.0, atol=0.0)

    padded = dict(values)
    padded["tokens"] = values["tokens"].clone()
    padded["tokens"][~values["token_mask"]] = 1.0e20
    # The state contract rejects nonzero masked padding; the pure scorer also
    # rejects it rather than letting accidental padding affect a surface.
    try:
        network(**padded)
    except ValueError as error:
        assert "zero" in str(error)
    else:  # pragma: no cover - fail visibly if the integrity guard disappears
        raise AssertionError("masked padding must fail closed")


def test_detached_q12_descriptors_cannot_receive_q3_gradients() -> None:
    values = _inputs(requires_grad=True)
    network = _constant_network(1.0)
    network(**values)[0, 1].square().backward()
    assert values["action_context"].grad is None
    assert values["tokens"].grad is None
    assert any(parameter.grad is not None for parameter in network.parameters())


def test_selected_cell_scorer_matches_full_surface_and_retains_gradients() -> None:
    network = LCSRSC3QNetwork()
    values = _inputs()
    view = assemble_c3_view(
        action_context=values["action_context"].numpy(),
        tokens=values["tokens"].numpy(),
        token_mask=values["token_mask"].numpy(),
        action_mask=values["action_mask"].numpy(),
        reference_actions=values["reference_actions"].numpy(),
    )
    selected = network.score_cells_view(
        view,
        np.asarray([0, 1, 0], dtype=np.int64),
        np.asarray([1, 1, 0], dtype=np.int64),
    )
    full = network.forward_view(view)
    torch.testing.assert_close(selected, full[[0, 1, 0], [1, 1, 0]])
    selected.square().sum().backward()
    assert any(parameter.grad is not None for parameter in network.parameters())
