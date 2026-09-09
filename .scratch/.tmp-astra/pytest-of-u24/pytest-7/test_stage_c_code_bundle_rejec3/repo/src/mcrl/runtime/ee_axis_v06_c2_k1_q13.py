"""Q1+Q3 inference seam that never evaluates the resident legacy Q2."""

from __future__ import annotations

import numpy as np
import torch


class C2K1Q13Error(ValueError):
    """The frozen Q1/Q3 container or route inputs are malformed."""


def q13_surfaces_without_q2(
    trainer: object,
    states_v03: np.ndarray,
    states_v04_c3: np.ndarray,
    masks: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Evaluate only frozen Q1 and Q3, including safe empty-mask rows.

    The function deliberately accesses ``trainer.q1`` and ``trainer.q3``
    directly.  It never reads ``trainer.q2`` and never invokes the hybrid
    three-route inference API, so a resident pre-V0.6 Q2 cannot affect or be
    consulted by the bounded C2-k1 learner/evaluation path.
    """

    networks = getattr(trainer, "q_nets", None)
    if (
        networks is None
        or len(networks) != 3
        or getattr(trainer, "selected_q3_rung", None) != 100
        or not isinstance(getattr(trainer, "initialization_seed", None), int)
    ):
        raise C2K1Q13Error("Q1/Q3 source must be one exact rung-100 hybrid")
    v03 = np.asarray(states_v03, dtype=np.float32)
    v04 = np.asarray(states_v04_c3, dtype=np.float32)
    legal = np.asarray(masks)
    if (
        v03.ndim != 2
        or v04.shape != v03.shape
        or legal.dtype != np.bool_
        or legal.ndim != 2
        or legal.shape[0] != v03.shape[0]
        or legal.shape[1] != 28
        or not np.all(np.isfinite(v03))
        or not np.all(np.isfinite(v04))
    ):
        raise C2K1Q13Error("Q1/Q3 route states or legal masks are malformed")
    rows = int(v03.shape[0])
    q1 = np.zeros((rows, 28), dtype=np.float64)
    q3 = np.zeros((rows, 28), dtype=np.float64)
    eligible = np.any(legal, axis=1)
    if not bool(np.any(eligible)):
        return q1, q3, np.array(legal, dtype=np.bool_, copy=True)
    device = getattr(trainer, "device", torch.device("cpu"))
    with torch.no_grad():
        state_v03 = torch.tensor(v03[eligible], dtype=torch.float32, device=device)
        state_v04 = torch.tensor(v04[eligible], dtype=torch.float32, device=device)
        mask = torch.tensor(legal[eligible], dtype=torch.bool, device=device)
        q1_values = trainer.q1(state_v03, mask).detach().cpu().numpy()
        q3_values = trainer.q3(state_v04).detach().cpu().numpy()
    if (
        q1_values.shape != (int(np.count_nonzero(eligible)), 28)
        or q3_values.shape != q1_values.shape
        or not np.all(np.isfinite(q1_values))
        or not np.all(np.isfinite(q3_values))
    ):
        raise C2K1Q13Error("Q1/Q3 surfaces are nonfinite or have the wrong shape")
    q1[eligible] = np.asarray(q1_values, dtype=np.float64)
    q3[eligible] = np.asarray(q3_values, dtype=np.float64)
    return q1, q3, np.array(legal, dtype=np.bool_, copy=True)


__all__ = ["C2K1Q13Error", "q13_surfaces_without_q2"]
