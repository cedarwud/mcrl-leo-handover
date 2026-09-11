"""The four collapse indicators of SDD §6 G-3 (W-12).

G-3: "任何『是否崩潰』的判定,必須同時報告 ``active_beam_count``、
``argmax_agreement``、``q_margin``、``q_entropy``,且 ``q_margin`` **必須以
Q 值域正規化後**呈現。**缺任一項即不通過**".

**Why all four, and why the normalisation.**  The source project's own
ablation (`artifacts/step3-cause-ablation-2026-06-15/`) found that dropping
the learning rate from 0.01 to 0.001 moved active beams from 1.00 to 4.39
and argmax agreement from 1.000 to 0.484 — which reads as "the collapse was
fixed".  It also moved ``q_margin`` from 0.0057 to 0.00055.  The file's own
headline says it plainly::

    escape is argmax-dispersion under near-flat Q, not a discriminative Q

So the first two indicators alone say "not collapsed" about a policy whose Q
values are nearly tied.  The margin is what distinguishes a policy that
*chose* from one that is picking between indistinguishable options — and it
only means anything **normalised**, because an unnormalised margin shrinks
whenever the Q scale does, for reasons that have nothing to do with
discrimination.

The r2 adjudication is worth carrying: normalising by the calibrated Q scale
left a 10-29x gap, so "Q got relatively flatter" **stands**.  What did not
stand is "that small margin is noise rather than a weak learned ordering" —
SDD §2.3 is explicit that this SDD claims only the former, and P6 decides
the latter.  Nothing here should be read as settling it.

This module therefore refuses to hand back a partial report.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..errors import MCRLContractError

REQUIRED_G3_FIELDS: tuple[str, ...] = (
    "active_beam_count",
    "argmax_agreement",
    "q_margin",
    "q_entropy",
)
"""All four, always.  G-3 fails on a missing one, not on a bad value."""


@dataclass(frozen=True)
class CollapseMetrics:
    """One evaluation's G-3 report.  There is no partial form of this object."""

    active_beam_count: float
    """Distinct relative action slots selected (legacy frozen field name).

    An action index identifies one of the 28 relative candidate slots.  It
    is not a physical ``(norad_id, cell_id)`` beam identity, so this field
    must never be presented as a count of physically lit beams.
    """

    argmax_agreement: float
    """Fraction of users choosing the single most popular action."""

    q_margin: float
    """Top-1 minus top-2, **normalised by the Q range**.  Dimensionless."""

    q_margin_raw: float
    """The same gap before normalisation, reported alongside so the scale is visible."""

    q_entropy: float
    """Entropy of the softmax over the masked scalarised row, normalised to [0, 1]."""

    q_range: float
    """The scale the margin was divided by; carried so it can be audited."""

    num_users: int
    num_actions: int

    @property
    def active_action_slot_count(self) -> float:
        """Semantically explicit alias for legacy ``active_beam_count``."""
        return self.active_beam_count

    def as_dict(self) -> dict[str, float]:
        return {
            "active_beam_count": self.active_beam_count,
            "argmax_agreement": self.argmax_agreement,
            "q_margin": self.q_margin,
            "q_margin_raw": self.q_margin_raw,
            "q_entropy": self.q_entropy,
            "q_range": self.q_range,
            "num_users": float(self.num_users),
            "num_actions": float(self.num_actions),
        }

    def format_report(self) -> str:
        """Render all four indicators.  There is no way to render fewer."""
        return (
            f"active_beam_count={self.active_beam_count:.3f} "
            "(legacy name; distinct_action_slots)  "
            f"argmax_agreement={self.argmax_agreement:.4f}  "
            f"q_margin={self.q_margin:.6f} (normalised; raw "
            f"{self.q_margin_raw:.3e} over range {self.q_range:.3e})  "
            f"q_entropy={self.q_entropy:.4f}"
        )


def assert_g3_complete(report: dict[str, float]) -> dict[str, float]:
    """G-3 — refuse a collapse verdict that omits any of the four.

    Reporting only ``active_beam_count`` and ``argmax_agreement`` is the
    documented way to mistake "Q got flatter" for "it stopped collapsing".
    """
    missing = [field for field in REQUIRED_G3_FIELDS if field not in report]
    if missing:
        raise MCRLContractError(
            f"G-3 requires all four indicators; missing {missing}. "
            "Reporting only the first two reads a flattened Q as a "
            "de-collapsed policy."
        )
    non_finite = [
        field
        for field in REQUIRED_G3_FIELDS
        if not np.isfinite(float(report[field]))
    ]
    if non_finite:
        raise MCRLContractError(
            f"G-3 indicators must be finite; {non_finite} are not"
        )
    return dict(report)


def compute_collapse_metrics(
    scalarized_q: np.ndarray,
    masks: np.ndarray,
    selected_actions: np.ndarray,
) -> CollapseMetrics:
    """Compute all four indicators from one step's decision surface.

    ``scalarized_q`` is ``(U, A)``, ``masks`` is ``(U, A)`` boolean, and
    ``selected_actions`` is ``(U,)`` with ``-1`` for a user who had no valid
    action (``NO_OP_ACTION``).
    """
    q = np.asarray(scalarized_q, dtype=np.float64)
    valid = np.asarray(masks, dtype=bool)
    actions = np.asarray(selected_actions, dtype=np.int64)
    if q.ndim != 2 or valid.shape != q.shape:
        raise MCRLContractError("scalarized_q and masks must both be (U, A)")
    if actions.shape != (q.shape[0],):
        raise MCRLContractError("selected_actions must be (U,)")
    if not np.all(np.isfinite(q[valid])):
        raise MCRLContractError("scalarised Q must be finite on the mask")

    num_users, num_actions = q.shape
    served = actions >= 0

    # -- 1. how many distinct relative action slots the policy uses --------
    active_beam_count = float(np.unique(actions[served]).size) if served.any() else 0.0

    # -- 2. how concentrated the choice is --------------------------------
    if served.any():
        counts = np.bincount(actions[served], minlength=num_actions)
        argmax_agreement = float(counts.max()) / float(np.count_nonzero(served))
    else:
        argmax_agreement = 0.0

    # -- 3. top-1 minus top-2, normalised --------------------------------
    margins_raw: list[float] = []
    ranges: list[float] = []
    margins_normalised: list[float] = []
    entropies: list[float] = []
    for uid in range(num_users):
        row_mask = valid[uid]
        if int(np.count_nonzero(row_mask)) < 2:
            # A single candidate has no margin to speak of, and a degenerate
            # entropy of 0; including it would report certainty the policy
            # never exercised.
            continue
        row = q[uid][row_mask]
        ordered = np.sort(row)[::-1]
        margin_raw = float(ordered[0] - ordered[1])
        q_range_user = float(ordered[0] - ordered[-1])
        margins_raw.append(margin_raw)
        ranges.append(q_range_user)
        # The frozen definition says *per-user* Q-range normalisation.
        # Average those user-level ratios; dividing the two population
        # means would silently weight users in proportion to their Q range.
        # A fully tied row has no discrimination and therefore contributes
        # zero rather than an undefined 0/0.
        margins_normalised.append(
            margin_raw / q_range_user if q_range_user > 0.0 else 0.0
        )

        # Softmax entropy over the valid actions, normalised by log(n) so it
        # is comparable across users with different numbers of candidates.
        shifted = row - row.max()
        weights = np.exp(shifted)
        weights /= weights.sum()
        positive = weights[weights > 0.0]
        entropy = float(-(positive * np.log(positive)).sum())
        entropies.append(entropy / float(np.log(row.size)))

    q_margin_raw = float(np.mean(margins_raw)) if margins_raw else 0.0
    q_range = float(np.mean(ranges)) if ranges else 0.0
    q_margin = (
        float(np.mean(margins_normalised)) if margins_normalised else 0.0
    )
    q_entropy = float(np.mean(entropies)) if entropies else 0.0

    return CollapseMetrics(
        active_beam_count=active_beam_count,
        argmax_agreement=argmax_agreement,
        q_margin=q_margin,
        q_margin_raw=q_margin_raw,
        q_entropy=q_entropy,
        q_range=q_range,
        num_users=num_users,
        num_actions=num_actions,
    )
