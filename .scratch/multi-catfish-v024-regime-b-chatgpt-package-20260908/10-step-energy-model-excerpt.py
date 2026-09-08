"""``StepEnvironment`` — the whole chain, from ephemeris to reward vector.

Everything below this file was already built and tested in isolation; this
is where the pieces are wired into one step function and where the physics
finally produces numbers instead of interfaces.

The order inside one step is not arbitrary, and getting it wrong is the
classic way to build an environment that looks right and is not::

    actions (validated against the DECISION-time mask)
      -> per-link recurrence power p_{u,s,v}          (3.11)/(3.12)
      -> per-link feasibility, p > p_max              -> outage
      -> service resolution, x = a·z                  (3.1)-(3.4), C-11
      -> loads U_{s,v}, activation z = 1{U > 0}       (3.3)/(3.4)
      -> beam power p_{s,v} = max over served users   (3.12a preamble)
      -> interference I^intra + I^inter               (3.12a)/(3.12b)
      -> SINR gamma                                   (3.13)
      -> rate R = (B^w/U)·log2(1+gamma)               (3.14)
      -> supply power P^p = p/xi, fixed P^f, total P^N (3.15)-(3.16a)
      -> r1 = R/P^N, r2 = -Psi, r3 = -U_{b_u}         (3.25)/(3.27)/(3.28)

**There is no fixed point in that chain, and that is a property worth
knowing.**  ``p`` depends only on the off-axis angle, never on load or on
interference, so the power model cannot chase the SINR it produces.  An
implementation that made ``p`` depend on ``γ`` — a target-SINR inversion,
say — would need to iterate, and ruling C-2 forbids exactly that.

**Two SINRs, deliberately different, never interchangeable.**  The realised
link SINR of (3.13) is what the reward is built from.  The state's ``γ``
block (4.1) is a *pre-action* quantity over all 28 candidates and cannot see
this step's activations, so it is built against the previous step's
radiating set under a named provenance
(:data:`~mcrl.env.interference.CANDIDATE_SINR_PROVENANCE`).  Quoting one as
the other would be a leak of post-action information into the state.

Each served segment starts at ``p⁰ = p_max/2 = 0.825 W``, leaving the frozen
3 dB in-segment gain budget below ``p_max = 1.65 W``.  Link feasibility still
fails loudly whenever the angle recurrence requires more than the ceiling;
:meth:`StepEnvironment.assert_ready_to_train` verifies the adopted mapping
before a training run.
"""

from __future__ import annotations

import datetime as dt
import copy
from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np

from ..errors import MCRLContractError
from ..runtime.energy_efficiency import (
    SystemEnergyEfficiency,
    additive_system_ee,
    r1_energy_efficiency,
)
from ..runtime.state_encoding import (
    assert_incumbent_is_recoverable,
    encode_state,
)
from ..runtime.trainer_spec import TrainerConfig
from .action_contract import (
    NO_OP_ACTION,
    NUM_ACTIONS,
    NUM_BEAM_SLOTS,
    Association,
    HandoverClass,
    HandoverLedger,
    assert_selected_actions_valid,
    decode_action,
)
from .antenna import RX_GAIN_MAX_DBI, transmit_gain_linear
from .geometry import angle_between_deg
from .candidates import StepCandidates
from .interference import (
    CANDIDATE_SINR_PROVENANCE,
    boresight_separation_deg,
    InterferenceBreakdown,
    RadiatingBeams,
    beam_field_at_users,
    build_radiating_beams,
    candidate_interference_w,
    candidate_received_power_terms,
    co_channel_interference,
    empty_radiating_beams,
    received_power_terms,
)
from .keyed_fading import KeyedFadingField
from .observation_provenance import (
