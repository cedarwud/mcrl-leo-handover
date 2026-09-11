"""Pure fixed V0.23 LC-SRS relational C3 token head."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn

from ..runtime.ee_axis_lcsrs_c3_state import (
    C3View,
    LCSRS_ACTION_CONTEXT_DIM,
    LCSRS_ACTION_DIM,
    LCSRS_C3_CONFIG_SHA256,
    LCSRS_TOKEN_DIM,
)


LCSRS_C3_HEAD_ALGORITHM = "multi-catfish-mcrl-v023-lcsrs-c3-head"
LCSRS_C3_HEAD_VERSION = 1


@dataclass(frozen=True)
class LCSRSC3HeadConfig:
    """Non-tunable architecture declaration for the frozen C3 head."""

    action_dim: int = LCSRS_ACTION_DIM
    action_context_dim: int = LCSRS_ACTION_CONTEXT_DIM
    token_dim: int = LCSRS_TOKEN_DIM
    hidden_layers: tuple[int, int] = (64, 64)
    activation: str = "relu"
    output_unit: str = "normalized_bits_per_kappa"
    config_sha256: str = LCSRS_C3_CONFIG_SHA256

    def __post_init__(self) -> None:
        if (
            self.action_dim != LCSRS_ACTION_DIM
            or self.action_context_dim != LCSRS_ACTION_CONTEXT_DIM
            or self.token_dim != LCSRS_TOKEN_DIM
            or self.hidden_layers != (64, 64)
            or self.activation != "relu"
            or self.output_unit != "normalized_bits_per_kappa"
            or self.config_sha256 != LCSRS_C3_CONFIG_SHA256
        ):
            raise ValueError("V0.23 LC-SRS C3 head configuration is frozen")


class LCSRSC3QNetwork(nn.Module):
    """Shared 67-to-1 scorer, masked token sum, and exact reference gauge."""

    def __init__(self, config: LCSRSC3HeadConfig | None = None) -> None:
        super().__init__()
        self.config = LCSRSC3HeadConfig() if config is None else config
        self.token_scorer = nn.Sequential(
            nn.Linear(67, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    @staticmethod
    def _validate(
        action_context: torch.Tensor,
        tokens: torch.Tensor,
        token_mask: torch.Tensor,
        action_mask: torch.Tensor,
        reference_actions: torch.Tensor,
    ) -> tuple[int, int]:
        values = (action_context, tokens, token_mask, action_mask, reference_actions)
        if not all(isinstance(value, torch.Tensor) for value in values):
            raise TypeError("LC-SRS C3 head inputs must be torch tensors")
        if len({value.device for value in values}) != 1:
            raise ValueError("LC-SRS C3 head inputs must share one device")
        if action_context.dtype != torch.float32 or action_context.ndim != 3:
            raise ValueError("action_context must be float32 shape (U,28,29)")
        users, actions, width = action_context.shape
        if users < 1 or actions != LCSRS_ACTION_DIM or width != LCSRS_ACTION_CONTEXT_DIM:
            raise ValueError("action_context shape disagrees with the frozen C3 contract")
        if tokens.dtype != torch.float32 or tokens.shape != (
            users,
            actions,
            users + 1,
            LCSRS_TOKEN_DIM,
        ):
            raise ValueError("tokens must be float32 shape (U,28,U+1,38)")
        if token_mask.dtype != torch.bool or token_mask.shape != (users, actions, users + 1):
            raise ValueError("token_mask must be Boolean shape (U,28,U+1)")
        if action_mask.dtype != torch.bool or action_mask.shape != (users, actions):
            raise ValueError("action_mask must be Boolean shape (U,28)")
        if reference_actions.dtype != torch.int64 or reference_actions.shape != (users,):
            raise ValueError("reference_actions must be int64 shape (U,)")
        if not bool(torch.isfinite(action_context).all()) or not bool(torch.isfinite(tokens).all()):
            raise ValueError("LC-SRS C3 features must be finite")
        if not bool(torch.any(action_mask, dim=1).all()):
            raise ValueError("each C3 row needs a legal action")
        if not bool(torch.equal(token_mask[:, :, users], action_mask)):
            raise ValueError("each legal C3 cell needs exactly one pair token")
        if bool(torch.any(token_mask[:, :, :users] & ~action_mask.unsqueeze(2))):
            raise ValueError("token_mask cannot widen the native action mask")
        if bool(torch.any(action_context[~action_mask] != 0.0)) or bool(
            torch.any(tokens[~action_mask] != 0.0)
        ):
            raise ValueError("illegal C3 action rows and tokens must be zero")
        if bool(torch.any(tokens[~token_mask] != 0.0)):
            raise ValueError("masked C3 token slots must be zero")
        rows = torch.arange(users, device=reference_actions.device)
        if (
            bool(torch.any(reference_actions < 0))
            or bool(torch.any(reference_actions >= actions))
            or not bool(action_mask[rows, reference_actions].all())
        ):
            raise ValueError("every C3 reference action must be legal")
        return users, actions

    def forward(
        self,
        action_context: torch.Tensor,
        tokens: torch.Tensor,
        token_mask: torch.Tensor,
        action_mask: torch.Tensor,
        reference_actions: torch.Tensor,
    ) -> torch.Tensor:
        users, actions = self._validate(
            action_context, tokens, token_mask, action_mask, reference_actions
        )
        # Interface A is immutable detached data.  In particular no Q3 loss can
        # backpropagate through descriptors that contain detached Q1+Q2 values.
        action_context = action_context.detach()
        tokens = tokens.detach()
        selected = torch.nonzero(token_mask, as_tuple=False)
        focal, action, token = selected.unbind(dim=1)
        features = torch.cat((action_context[focal, action], tokens[focal, action, token]), dim=1)
        contributions = self.token_scorer(features).squeeze(1)
        aggregate = contributions.new_zeros(users * actions).scatter_add_(
            0, focal * actions + action, contributions
        ).reshape(users, actions)
        rows = torch.arange(users, device=reference_actions.device)
        centred = aggregate - aggregate[rows, reference_actions].unsqueeze(1)
        return torch.where(action_mask, centred, torch.zeros_like(centred))

    def forward_view(
        self,
        view: C3View,
        *,
        device: torch.device | str | None = None,
    ) -> torch.Tensor:
        """Evaluate an authenticated immutable view without exposing array aliases."""

        view.verify()
        target = self.token_scorer[0].weight.device if device is None else torch.device(device)
        return self(
            torch.tensor(np.asarray(view.action_context), dtype=torch.float32, device=target),
            torch.tensor(np.asarray(view.tokens), dtype=torch.float32, device=target),
            torch.tensor(np.asarray(view.token_mask), dtype=torch.bool, device=target),
            torch.tensor(np.asarray(view.action_mask), dtype=torch.bool, device=target),
            torch.tensor(np.asarray(view.reference_actions), dtype=torch.int64, device=target),
        )

    def score_cells_view(
        self,
        view: C3View,
        user_indices: np.ndarray,
        action_indices: np.ndarray,
        *,
        device: torch.device | str | None = None,
    ) -> torch.Tensor:
        """Score selected cells and their references without densifying a batch.

        The result is the same reference-centred scalar returned by
        :meth:`forward_view`. Inputs remain detached; gradients flow only into
        the shared token scorer. Duplicate requested cells are retained.
        """

        view.verify()
        users = np.asarray(user_indices, dtype=np.int64)
        actions = np.asarray(action_indices, dtype=np.int64)
        if users.ndim != 1 or actions.ndim != 1 or users.shape != actions.shape:
            raise ValueError("selected users/actions must be equal-length vectors")
        if users.size == 0:
            raise ValueError("at least one LC-SRS C3 cell is required")
        total_users = int(view.action_context.shape[0])
        if np.any(users < 0) or np.any(users >= total_users):
            raise ValueError("selected LC-SRS C3 user is out of range")
        if np.any(actions < 0) or np.any(actions >= LCSRS_ACTION_DIM):
            raise ValueError("selected LC-SRS C3 action is out of range")
        if not np.all(view.action_mask[users, actions]):
            raise ValueError("selected LC-SRS C3 cell must be legal")

        references = np.asarray(view.reference_actions)[users]
        requested = list(zip(users.tolist(), actions.tolist(), strict=True))
        requested.extend(zip(users.tolist(), references.tolist(), strict=True))
        unique_cells = tuple(dict.fromkeys(requested))
        cell_lookup = {cell: index for index, cell in enumerate(unique_cells)}

        feature_rows: list[np.ndarray] = []
        cell_rows: list[int] = []
        for cell_index, (user, action) in enumerate(unique_cells):
            active = np.flatnonzero(view.token_mask[user, action])
            if active.size == 0:
                raise ValueError("every legal LC-SRS C3 cell needs a token")
            context = np.repeat(
                view.action_context[user, action][None, :],
                active.size,
                axis=0,
            )
            feature_rows.append(
                np.concatenate((context, view.tokens[user, action, active]), axis=1)
            )
            cell_rows.extend([cell_index] * int(active.size))

        target = self.token_scorer[0].weight.device if device is None else torch.device(device)
        features = torch.tensor(
            np.concatenate(feature_rows, axis=0),
            dtype=torch.float32,
            device=target,
        )
        contributions = self.token_scorer(features).squeeze(1)
        cell_index = torch.tensor(cell_rows, dtype=torch.int64, device=target)
        aggregate = contributions.new_zeros(len(unique_cells)).index_add(
            0,
            cell_index,
            contributions,
        )
        candidate_index = torch.tensor(
            [cell_lookup[cell] for cell in requested[: users.size]],
            dtype=torch.int64,
            device=target,
        )
        reference_index = torch.tensor(
            [cell_lookup[cell] for cell in requested[users.size :]],
            dtype=torch.int64,
            device=target,
        )
        return aggregate[candidate_index] - aggregate[reference_index]


__all__ = [
    "LCSRS_C3_HEAD_ALGORITHM",
    "LCSRS_C3_HEAD_VERSION",
    "LCSRSC3HeadConfig",
    "LCSRSC3QNetwork",
]
