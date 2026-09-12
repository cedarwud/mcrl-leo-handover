"""Registration of the admitted candidate Catfish sources for MULTI-D3.

The MULTI-D3 mechanism is agnostic to what produced an action
(:mod:`mcrl.algorithms.cf_teacher`), so a candidate reaches it through one thin
adapter and nothing else.  This module holds those adapters.  It imports the
sources lazily, so a tree that has no candidate module still imports ``cf_dev``.

**Nothing here is a source definition.**  ``T_NEXT`` is the exact committed Lane N
module ``cf_tnext.py`` (Amendment 15 section 2A, Lane N commit ``25448632``); the
adapter only forwards the live training context and returns the actions verbatim.
The ``A_repr`` clone is an admission instrument and is NEVER substituted for the
teacher, and ``T_NEXT`` is never inferred from the 113-dim observation.
"""

from __future__ import annotations

import numpy as np

from . import cf_teacher as cft

T_NEXT_ID: str = "T_NEXT"


def _tnext_source(states, masks, *, context: cft.TeacherContext) -> np.ndarray:
    """``T_NEXT``'s action per user, straight from the committed Lane N source."""
    from . import cf_tnext as cftn

    actions, _diag, _geometry = cftn.tnext_actions(
        states,
        masks,
        driver=context.driver,
        candidates=context.candidates,
        is_final_step=bool(context.is_final_step),
    )
    return np.asarray(actions, dtype=np.int64)


def tnext_identity() -> dict[str, object]:
    """The committed source's own canonical identity payload, for the config hash."""
    from . import cf_tnext as cftn

    return dict(cftn.source_identity())


def register_candidate_sources(*, replace: bool = False) -> tuple[str, ...]:
    """Register every admitted candidate source and return what is now available."""
    cft.register_teacher_source(
        T_NEXT_ID, _tnext_source, replace=replace, needs_context=True
    )
    return cft.registered_teachers()
