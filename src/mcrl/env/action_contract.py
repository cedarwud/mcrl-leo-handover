"""Action-index contract primitives shared by the trainer and the environment.

New file (W-16).  Holds only what W-16 needs; the rest of the SDD §4A
contract (slot tables, identity-based handover accounting, mask
construction) is W-03's and lands in this module later.

**The no-op action (SDD §4A.5a(1))**

When a user has no valid action at a decision step, the policy emits
``NO_OP_ACTION`` — never a fallback index.  ``NO_OP_ACTION`` is *not* a
beam index and is *not* maskable; it is the absence of a decision.

Obligations this places on the environment (W-02/W-03 must honour them):

1. ``env.step`` accepts ``NO_OP_ACTION`` for any user and leaves that user
   **unserved** for the step: no beam activation, no power draw, no
   contribution to ``beam_load_b`` and none to ``U_{b_u}`` (SDD §3.7 P-6,
   the single load semantics the counting-form ``r3`` depends on).
2. The handover accounting treats an unserved step as ``Ψ = 0`` and the
   following served step as ``Ψ = φ2`` re-entry (SDD §4A.4 boundary table,
   acceptance tests T5/T8).
3. ``NO_OP_ACTION`` never reaches replay (SDD §4A.5a(2); enforced trainer
   side, see ``docs/PATCH-LEDGER.md`` P-03).

The sentinel is negative on purpose: it is a hard trip-wire.  Any code path
that treats actions as array indices (``np.bincount``, ``gather``, direct
indexing) fails loudly instead of silently aliasing to the last beam.
"""

from __future__ import annotations

from typing import SupportsInt

import numpy as np

NO_OP_ACTION: int = -1
"""Sentinel emitted when a user's decision mask is empty (SDD §4A.5a(1))."""


def is_no_op(action: SupportsInt) -> bool:
    """Return True when ``action`` is the no-op sentinel."""
    return int(action) == NO_OP_ACTION


def no_op_actions(num_users: int) -> np.ndarray:
    """Return an all-no-op action vector of the trainer's action dtype."""
    return np.full(int(num_users), NO_OP_ACTION, dtype=np.int32)


def served_mask(actions: np.ndarray) -> np.ndarray:
    """Return a boolean mask of the users that hold a real action."""
    return np.asarray(actions) != NO_OP_ACTION
