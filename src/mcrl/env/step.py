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

⚠ **This environment does not currently serve anybody.**  ``p⁰ = 2 W``
exceeds ``p_max = 1.65 W``, so every segment start is infeasible; see
:data:`mcrl.env.link_budget.SEGMENT_START_EXCEEDS_BEAM_CEILING`.  The
environment runs and measures it rather than hiding it, and
:meth:`StepEnvironment.assert_ready_to_train` refuses to start training
while it stands.
"""

from __future__ import annotations

import datetime as dt
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
from .candidates import StepCandidates
from .interference import (
    CANDIDATE_SINR_PROVENANCE,
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
from .link_budget import (
    BEAM_BANDWIDTH_HZ,
    BEAM_POWER_MAX_W,
    PA_MAX_EFFICIENCY,
    PA_SATURATION_POWER_W,
    RICIAN_K_FACTOR_DB,
    SEGMENT_START_POWER_W,
    beam_power_w,
    classify_link_power_feasibility,
    fixed_power_w,
    link_power_factor,
    noise_power_w,
    pa_efficiency,
    recurrence_power_w,
    rician_fading_gain,
    segment_start_feasibility_report,
    shannon_rate_bps,
    supply_power_w,
    system_power_w,
)
from .scenario import ScenarioDriver
from .service import ServiceResolution, r3_counting, resolve_service
from .step_types import RewardComponents, UserState

_RX_GAIN_MAX_LINEAR: float = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
"""``G^R`` on boresight — what the wanted link always gets (3.10c)."""


@dataclass(frozen=True)
class PhysicsConfig:
    """The physical constants a run may vary, all defaulting to the frozen set.

    Every field defaults to the value in ``env/link_budget.py``, so the
    dataclass adds no new numbers to the project.  It exists because two of
    them currently contradict each other (``p⁰`` and ``p_max``) and a test
    or a resolved run has to be able to state a consistent pair explicitly
    rather than editing a frozen constant in place.
    """

    segment_start_power_w: float = SEGMENT_START_POWER_W
    beam_power_max_w: float = BEAM_POWER_MAX_W
    beam_bandwidth_hz: float = BEAM_BANDWIDTH_HZ
    pa_max_efficiency: float = PA_MAX_EFFICIENCY
    pa_saturation_power_w: float = PA_SATURATION_POWER_W
    rician_k_factor_db: float = RICIAN_K_FACTOR_DB
    fading_enabled: bool = True
    """Rician fading is a **random draw** and belongs to the frozen seed set.

    Turning it off makes a step deterministic given the ephemeris, which is
    what the equivalence and identity tests need; it is not a modelling
    option and no reported run may use it.
    """

    def __post_init__(self) -> None:
        for name in (
            "segment_start_power_w",
            "beam_power_max_w",
            "beam_bandwidth_hz",
            "pa_max_efficiency",
            "pa_saturation_power_w",
        ):
            if getattr(self, name) <= 0.0:
                raise ValueError(f"{name} must be positive")

    @property
    def noise_power_w(self) -> float:
        """``σ² = k_B·T_sys·B^w`` — per beam, independent of its load."""
        return noise_power_w(self.beam_bandwidth_hz)

    @property
    def segment_start_is_feasible(self) -> bool:
        return self.segment_start_power_w <= self.beam_power_max_w


@dataclass(frozen=True)
class Segment:
    """One served link's power segment (3.12).

    ``start_transmit_gain`` is ``G^T(θ(τ))``, the *only* thing carried across
    a step.  The closed form is a telescoped identity over (3.11), not stored
    state, so nothing else about ``τ`` may be remembered — and the moment the
    association changes or service breaks, this object is dropped rather than
    updated.
    """

    norad_id: int
    cell_id: int
    start_transmit_gain: float

    def continues(self, association: Association) -> bool:
        return (
            association.norad_id == self.norad_id
            and association.cell_id == self.cell_id
        )


@dataclass(frozen=True)
class StepObservation:
    """What the agent sees **before** choosing — (4.1) and (4.2)."""

    step_index: int
    candidates: StepCandidates
    user_states: tuple[UserState, ...]
    state_matrix: np.ndarray
    """``(U, 112)`` — the flat network input, one row per user."""
    masks: np.ndarray
    """``(U, 28)`` boolean — ``m_u(t)``."""
    candidate_sinr: np.ndarray
    """``(U, 28)`` linear — the state's ``γ`` block, before encoding."""
    sinr_provenance: str = CANDIDATE_SINR_PROVENANCE

    @property
    def num_users(self) -> int:
        return len(self.user_states)

    @property
    def starved_users(self) -> np.ndarray:
        return self.masks.sum(axis=1) == 0


@dataclass
class StepOutcome:
    """One step's realised physics and rewards."""

    step_index: int
    done: bool
    observation: StepObservation
    """The **next** observation; ``done`` marks it as terminal."""

    rewards: tuple[RewardComponents, ...]
    resolution: ServiceResolution
    energy: SystemEnergyEfficiency
    interference: InterferenceBreakdown
    radiating: RadiatingBeams

    link_power_w: np.ndarray
    """``(U,)`` — ``p_{u,s,v}`` for the chosen link, 0 when unserved."""
    link_sinr: np.ndarray
    """``(U,)`` — the realised (3.13), 0 when unserved."""
    link_rate_bps: np.ndarray
    """``(U,)`` — the realised (3.14), 0 when unserved."""
    handovers: tuple[HandoverClass, ...]
    system_power_w: float
    fixed_power_w: float
    diagnostics: dict[str, object] = field(default_factory=dict)

    @property
    def reward_matrix(self) -> np.ndarray:
        """``(U, 3)`` of ``(r1, r2, r3)`` in natural units, unscaled."""
        return np.array(
            [
                (reward.r1_throughput, reward.r2_handover, reward.r3_load_balance)
                for reward in self.rewards
            ],
            dtype=np.float64,
        )


class StepEnvironment:
    """The MODQN environment: one decision per user per slot.

    Built on a :class:`~mcrl.env.scenario.ScenarioDriver`, which owns the
    ephemeris, mobility, D2 and dwell state.  This class owns only what the
    physics and the reward need: the handover ledgers, the power segments,
    and the previous step's radiating set.
    """

    def __init__(
        self,
        driver: ScenarioDriver,
        *,
        physics: PhysicsConfig | None = None,
        trainer: TrainerConfig | None = None,
    ) -> None:
        self.driver = driver
        self.physics = physics or PhysicsConfig()
        self.trainer = trainer or TrainerConfig()
        self.num_users = driver.config.mobility.num_users
        self._ledgers: list[HandoverLedger] = [
            HandoverLedger() for _ in range(self.num_users)
        ]
        self._segments: list[Segment | None] = [None] * self.num_users
        self._previous_radiating: RadiatingBeams = empty_radiating_beams()
        self._previous_demand: dict[tuple[int, int], int] = {}
        self._previous_association: list[Association | None] = [None] * self.num_users
        self._candidates: StepCandidates | None = None
        self._step_index = 0
        self._started = False

    # -- gates ------------------------------------------------------------

    def assert_ready_to_train(self) -> None:
        """Refuse to start training while a frozen constant is contradictory.

        Probes may still run: measuring a 100% outage rate is exactly the
        evidence the open decision needs.  Training on it would burn 9,000
        episodes on an environment in which no action is ever executed.
        """
        if not self.physics.segment_start_is_feasible:
            report = segment_start_feasibility_report(
                p0_w=self.physics.segment_start_power_w,
                max_power_w=self.physics.beam_power_max_w,
                saturation_power_w=self.physics.pa_saturation_power_w,
            )
            raise MCRLContractError(
                "p0 = {segment_start_power_w} W exceeds p_max = "
                "{beam_power_max_w} W, so {consequence}.  Resolve the two "
                "ch5 table 5-2 values before training.".format(**report)
            )
        if not self.physics.fading_enabled:
            raise MCRLContractError(
                "fading_enabled=False is a test affordance; Rician fading is "
                "part of the frozen seed set and a reported run keeps it on"
            )

    # -- episode ----------------------------------------------------------

    def reset(
        self, start_utc: dt.datetime, rng: np.random.Generator
    ) -> StepObservation:
        """Begin an episode and return the step-0 observation.

        Every carried quantity is cleared, not merely reset to a plausible
        value: at ``t = 0`` there is no previous association (so ``x(t−1)``
        is all zero), no previous demand (``N(t−1)`` likewise), and nothing
        radiating (so ``I = 0``, which is a fact about an idle system rather
        than a missing term).
        """
        for ledger in self._ledgers:
            ledger.reset()
        self._segments = [None] * self.num_users
        self._previous_radiating = empty_radiating_beams()
        self._previous_demand = {}
        self._previous_association = [None] * self.num_users
        self._step_index = 0
        self._started = True

        candidates = self.driver.reset(
            start_utc, rng, incumbent_norads=self._incumbent_norads()
        )
        self._candidates = candidates
        return self._observe(candidates, rng)

    def step(
        self, actions: np.ndarray, rng: np.random.Generator
    ) -> StepOutcome:
        """Execute one slot's actions and return its physics and rewards."""
        if not self._started or self._candidates is None:
            raise MCRLContractError("the environment has not been reset")
        decision = self._candidates
        selected = assert_selected_actions_valid(actions, decision.slot_tables)

        physics = self._resolve_physics(decision, selected, rng)
        rewards, handovers = self._rewards(decision, selected, physics)

        self._previous_radiating = physics["radiating"]
        self._previous_demand = physics["resolution"].demand_by_beam
        self._step_index += 1
        done = self._step_index >= self.driver.config.steps_per_episode

        if done:
            following = decision
        else:
            following = self.driver.step(
                rng, incumbent_norads=self._incumbent_norads()
            )
            self._candidates = following
        observation = self._observe(following, rng, terminal=done)

        return StepOutcome(
            step_index=self._step_index - 1,
            done=done,
            observation=observation,
            rewards=rewards,
            resolution=physics["resolution"],
            energy=physics["energy"],
            interference=physics["interference"],
            radiating=physics["radiating"],
            link_power_w=physics["link_power_w"],
            link_sinr=physics["sinr"],
            link_rate_bps=physics["rate"],
            handovers=handovers,
            system_power_w=physics["system_power_w"],
            fixed_power_w=physics["fixed_power_w"],
            diagnostics=self._diagnostics(physics),
        )

    # -- physics ----------------------------------------------------------

    def _resolve_physics(
        self,
        decision: StepCandidates,
        actions: np.ndarray,
        rng: np.random.Generator,
    ) -> dict[str, object]:
        users = self.num_users
        grid = self.driver.grid
        physics = self.physics

        associations: list[Association | None] = []
        chosen_theta = np.zeros(users, dtype=np.float64)
        chosen_slot = np.full(users, -1, dtype=np.int64)
        for uid in range(users):
            action = int(actions[uid])
            if action == NO_OP_ACTION:
                associations.append(None)
                continue
            slot, beam = decode_action(action)
            associations.append(decision.slot_tables[uid].association(action))
            chosen_theta[uid] = decision.off_axis_deg[uid, slot, beam]
            chosen_slot[uid] = slot

        transmit_gain = np.where(
            chosen_slot >= 0, transmit_gain_linear(chosen_theta), 0.0
        )

        # (3.11)/(3.12): the recurrence, and the one ceiling outside it.
        link_power = np.zeros(users, dtype=np.float64)
        null_pointing = np.zeros(users, dtype=bool)
        for uid in range(users):
            if associations[uid] is None:
                continue
            if transmit_gain[uid] <= 0.0:
                # (3.11) needs G^T > 0.  A link pointed exactly into a
                # pattern null cannot be served at any finite power, so it is
                # infeasible rather than an error.
                null_pointing[uid] = True
                link_power[uid] = np.inf
                continue
            segment = self._segments[uid]
            continuing = (
                segment is not None
                and segment.continues(associations[uid])
                and self._previous_association[uid] is not None
            )
            start_gain = (
                segment.start_transmit_gain
                if continuing and segment is not None
                else float(transmit_gain[uid])
            )
            link_power[uid] = float(
                recurrence_power_w(
                    start_gain,
                    transmit_gain[uid],
                    p0_w=physics.segment_start_power_w,
                )
            )

        infeasible = np.where(
            null_pointing,
            True,
            classify_link_power_feasibility(
                np.where(null_pointing, 0.0, link_power),
                max_power_w=physics.beam_power_max_w,
            ),
        )
        link_power = np.where(null_pointing, 0.0, link_power)

        resolution = resolve_service(actions, decision.slot_tables, infeasible)

        # Commit the segments only now: feasibility is part of "served".
        for uid in range(users):
            if resolution.served[uid]:
                association = associations[uid]
                assert association is not None
                segment = self._segments[uid]
                continuing = (
                    segment is not None
                    and segment.continues(association)
                    and self._previous_association[uid] is not None
                )
                self._segments[uid] = Segment(
                    norad_id=association.norad_id,
                    cell_id=association.cell_id,
                    start_transmit_gain=(
                        segment.start_transmit_gain
                        if continuing and segment is not None
                        else float(transmit_gain[uid])
                    ),
                )
            else:
                self._segments[uid] = None

        # (3.12a) preamble: one beam, one power, max over its served users.
        serving_cell = resolution.serving_cell
        beam_keys = sorted(
            {
                (int(resolution.serving_satellite[uid]), int(serving_cell[uid]))
                for uid in range(users)
                if resolution.served[uid]
            }
        )
        beam_index_of_key = {key: index for index, key in enumerate(beam_keys)}
        beam_index = np.array(
            [
                beam_index_of_key.get(
                    (int(resolution.serving_satellite[uid]), int(serving_cell[uid])),
                    -1,
                )
                if resolution.served[uid]
                else -1
                for uid in range(users)
            ],
            dtype=np.int64,
        )
        beam_power = beam_power_w(
            link_power, resolution.served, beam_index, len(beam_keys)
        )

        user_ecef = self.driver.user_ecef_km()
        satellite_ecef = _satellite_positions(decision)
        radiating = build_radiating_beams(
            beam_norad_ids=np.array([key[0] for key in beam_keys], dtype=np.int64),
            beam_cell_ids=np.array([key[1] for key in beam_keys], dtype=np.int64),
            beam_power_w=beam_power,
            satellite_ecef_by_norad=satellite_ecef,
            grid=grid,
        )
        fading = self._draw_fading(satellite_ecef, rng)

        field_now = beam_field_at_users(
            user_ecef_km=user_ecef, radiating=radiating, fading_by_norad=fading
        )
        boresight_ecef, boresight_ids = _boresight(
            resolution, satellite_ecef, user_ecef
        )
        terms = received_power_terms(
            field_now,
            radiating,
            user_ecef_km=user_ecef,
            boresight_satellite_ecef_km=boresight_ecef,
            boresight_norad_ids=boresight_ids,
        )
        wanted_colors = np.where(
            resolution.served, grid.colors[np.maximum(serving_cell, 0)], -1
        )
        interference = co_channel_interference(
            terms,
            radiating,
            wanted_norad_ids=np.where(
                resolution.served, resolution.serving_satellite, -1
            ),
            wanted_cell_ids=serving_cell,
            wanted_colors=wanted_colors,
        )

        # (3.13): the wanted term uses each user's own link power, and the
        # beam it sits on is in the radiating set, so its H is read back from
        # the same matrix the interference used rather than recomputed.
        wanted = np.zeros(users, dtype=np.float64)
        for uid in range(users):
            if not resolution.served[uid]:
                continue
            column = int(beam_index[uid])
            wanted[uid] = (
                link_power[uid]
                * field_now.transmit_gain[uid, column]
                * field_now.path_gain[uid, column]
                * field_now.fading_gain[uid, column]
                * _RX_GAIN_MAX_LINEAR
            )
        sinr = np.where(
            resolution.served,
            wanted / (interference.total_w + physics.noise_power_w),
            0.0,
        )

        load = resolution.user_beam_load()
        rate = np.where(
            resolution.served,
            shannon_rate_bps(
                sinr, beam_load=load, bandwidth_hz=physics.beam_bandwidth_hz
            ),
            0.0,
        )

        # (3.15)-(3.16a): consumed power.
        power_of_served_beam = (
            beam_power[np.maximum(beam_index, 0)]
            if beam_keys
            else np.zeros(users, dtype=np.float64)
        )
        efficiency = pa_efficiency(
            np.where(resolution.served, power_of_served_beam, 0.0),
            max_efficiency=physics.pa_max_efficiency,
            saturation_power_w=physics.pa_saturation_power_w,
        )
        supply = supply_power_w(link_power * resolution.served, efficiency)
        beams_by_satellite = np.array(
            [
                sum(1 for key in beam_keys if key[0] == norad)
                for norad in sorted({key[0] for key in beam_keys})
            ],
            dtype=np.float64,
        )
        fixed = fixed_power_w(beams_by_satellite)
        total_power = system_power_w(supply, resolution.served, beams_by_satellite)

        # (3.16) is a triple sum over u', s', v' of x·P^p — once per served
        # LINK.  But "一支已啟用的波束以單一功率發射,不論其上載有幾位使用者":
        # one beam, one amplifier, one supply draw.  Charging it once per beam
        # instead gives the figure below, and the ratio between the two is
        # reported every step rather than argued about.  (3.16) is implemented
        # verbatim; this is the disclosure beside it.
        beam_efficiency = pa_efficiency(
            beam_power,
            max_efficiency=physics.pa_max_efficiency,
            saturation_power_w=physics.pa_saturation_power_w,
        )
        beam_charged_power = fixed + float(
            supply_power_w(beam_power, beam_efficiency).sum()
        )

        serving_beam = np.where(resolution.served, beam_index, -1)
        beam_load_b = np.array(
            [
                float(resolution.eligible_load_by_beam[key])
                for key in beam_keys
            ],
            dtype=np.float64,
        )
        energy = additive_system_ee(
            rate,
            total_power,
            serving_beam_u=serving_beam,
            beam_load_b=beam_load_b,
            beam_active_b=beam_load_b > 0.0,
        )

        return {
            "associations": associations,
            "resolution": resolution,
            "radiating": radiating,
            "interference": interference,
            "energy": energy,
            "link_power_w": link_power,
            "transmit_gain": transmit_gain,
            "sinr": sinr,
            "rate": rate,
            "supply_power_w": supply,
            "system_power_w": total_power,
            "fixed_power_w": fixed,
            "null_pointing": null_pointing,
            "beam_keys": beam_keys,
            "beam_charged_power_w": beam_charged_power,
        }

    def _rewards(
        self,
        decision: StepCandidates,
        actions: np.ndarray,
        physics: dict[str, object],
    ) -> tuple[tuple[RewardComponents, ...], tuple[HandoverClass, ...]]:
        """(3.25) ``r1``, (3.27) ``r2``, (3.28) ``r3``."""
        from .action_contract import HANDOVER_COST, UNSERVED

        resolution: ServiceResolution = physics["resolution"]  # type: ignore[assignment]
        rate: np.ndarray = physics["rate"]  # type: ignore[assignment]
        total_power = float(physics["system_power_w"])  # type: ignore[arg-type]
        associations = physics["associations"]

        r1 = r1_energy_efficiency(rate, total_power)
        r3 = r3_counting(resolution)

        rewards: list[RewardComponents] = []
        classes: list[HandoverClass] = []
        for uid in range(self.num_users):
            association = associations[uid]  # type: ignore[index]
            realised = (
                association
                if association is not None and resolution.served[uid]
                else UNSERVED
            )
            handover = self._ledgers[uid].observe(realised)
            classes.append(handover)
            self._previous_association[uid] = (
                realised if isinstance(realised, Association) else None
            )
            rewards.append(
                RewardComponents(
                    r1_throughput=float(r1[uid]),
                    r2_handover=-HANDOVER_COST[handover],
                    r3_load_balance=float(r3[uid]),
                    r1_system_ee_contribution=float(r1[uid]),
                )
            )
        return tuple(rewards), tuple(classes)

    # -- observation ------------------------------------------------------

    def _observe(
        self,
        candidates: StepCandidates,
        rng: np.random.Generator,
        *,
        terminal: bool = False,
    ) -> StepObservation:
        """Build (4.1)'s four blocks over the 28-wide candidate table."""
        users = self.num_users
        grid = self.driver.grid

        norad_ids = np.stack([table.norad_ids for table in candidates.slot_tables])
        cell_ids = np.stack([table.cell_ids for table in candidates.slot_tables])
        masks = candidates.masks

        # Block 1 — x_u(t-1) in the CURRENT candidate ordering (4.1).
        access = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
        for uid in range(users):
            previous = self._previous_association[uid]
            if previous is None:
                assert_incumbent_is_recoverable(access[uid], None)
                continue
            here = np.flatnonzero(
                (norad_ids[uid] == previous.norad_id)
                & (cell_ids[uid] == previous.cell_id)
            )
            if here.size:
                access[uid, here[0]] = 1.0
                assert_incumbent_is_recoverable(access[uid], int(here[0]))
            else:
                # (4.1): "若該波束已離開候選表,則本步無論選哪一格都構成換手".
                # The all-zero row is the honest encoding of that.
                assert_incumbent_is_recoverable(access[uid], None)

        # Block 3 — theta, in RADIANS (the state's contract; G-7).
        theta_deg = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
        for slot in range(candidates.off_axis_deg.shape[1]):
            block = slice(slot * NUM_BEAM_SLOTS, (slot + 1) * NUM_BEAM_SLOTS)
            angles = candidates.off_axis_deg[:, slot, :]
            theta_deg[:, block] = np.where(np.isnan(angles), 0.0, angles)

        # Block 2 — gamma over every candidate, previous-step interference.
        sinr = self._candidate_sinr(candidates, theta_deg, norad_ids, cell_ids, rng)

        # Block 4 — N_u(t-1): the previous step's UNGATED demand (P-5/P-6).
        loads = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
        for uid in range(users):
            for action in range(NUM_ACTIONS):
                cell = int(cell_ids[uid, action])
                norad = int(norad_ids[uid, action])
                if cell >= 0 and norad >= 0:
                    # (4.1) reads n_{s,v}(t-1) through b_u(c,t), so the
                    # lookup is by BEAM: the same cell under a different
                    # satellite is a different beam with its own demand.
                    loads[uid, action] = float(
                        self._previous_demand.get((norad, cell), 0)
                    )
        del grid

        states: list[UserState] = []
        rows: list[np.ndarray] = []
        for uid in range(users):
            state = UserState(
                access_vector=access[uid],
                channel_quality=sinr[uid],
                beam_offsets=np.radians(theta_deg[uid]),
                beam_loads=loads[uid],
                contract_fields=candidates.contract_fields[uid],
            )
            states.append(state)
            rows.append(encode_state(state, users, self.trainer))

        del terminal
        return StepObservation(
            step_index=candidates.dwell.step_index,
            candidates=candidates,
            user_states=tuple(states),
            state_matrix=np.stack(rows),
            masks=masks,
            candidate_sinr=sinr,
        )

    def _candidate_sinr(
        self,
        candidates: StepCandidates,
        theta_deg: np.ndarray,
        norad_ids: np.ndarray,
        cell_ids: np.ndarray,
        rng: np.random.Generator,
    ) -> np.ndarray:
        """(4.1)'s ``γ`` block: current geometry, previous-step interference.

        The wanted power is ``p⁰`` at every candidate — connecting to any of
        them starts a segment, and (3.12) puts a segment's first step at
        exactly ``p⁰``.  The incumbent is the one exception in principle, but
        it is not made one here: the state would then mix two power
        provenances across its 28 entries with nothing marking which is
        which, and the difference is the segment's accumulated compensation,
        which the angle block already carries.
        """
        users = self.num_users
        grid = self.driver.grid
        physics = self.physics
        radiating = self._previous_radiating

        user_ecef = self.driver.user_ecef_km()
        satellite_ecef = _satellite_positions(candidates)
        fading = self._draw_fading(satellite_ecef, rng)

        transmit = transmit_gain_linear(theta_deg)
        slant = np.repeat(candidates.slant_range_km, NUM_BEAM_SLOTS, axis=1)
        elevation = np.repeat(candidates.elevation_deg, NUM_BEAM_SLOTS, axis=1)
        usable = (norad_ids >= 0) & (cell_ids >= 0) & np.isfinite(slant)
        path = np.where(
            usable,
            link_power_factor(
                np.where(usable, slant, 1.0),
                np.where(usable, elevation, 0.0),
                np.full(slant.shape, _RX_GAIN_MAX_LINEAR),
            ),
            0.0,
        )
        fade = np.ones((users, NUM_ACTIONS), dtype=np.float64)
        for uid in range(users):
            for action in range(NUM_ACTIONS):
                norad = int(norad_ids[uid, action])
                if norad >= 0:
                    fade[uid, action] = fading[norad][uid]

        wanted = physics.segment_start_power_w * transmit * path * fade
        wanted = np.where(usable, wanted, 0.0)

        if radiating.count == 0:
            interference = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
        else:
            previous_ecef = {
                int(norad): radiating.satellite_ecef_km[index]
                for index, norad in enumerate(radiating.norad_ids.tolist())
            }
            field_previous = beam_field_at_users(
                user_ecef_km=user_ecef,
                radiating=radiating,
                fading_by_norad=self._draw_fading(previous_ecef, rng),
            )
            window_ecef = np.where(
                np.isnan(candidates.window_satellite_ecef_km),
                user_ecef[:, None, :],
                candidates.window_satellite_ecef_km,
            )
            terms = candidate_received_power_terms(
                field_previous,
                radiating,
                user_ecef_km=user_ecef,
                candidate_satellite_ecef_km=window_ecef,
                candidate_norad_ids=candidates.window_norad_ids,
            )
            interference = candidate_interference_w(
                terms,
                radiating,
                candidate_norad_ids=norad_ids,
                candidate_cell_ids=cell_ids,
                candidate_colors=np.where(
                    cell_ids >= 0, grid.colors[np.maximum(cell_ids, 0)], -1
                ),
            )

        return np.where(
            usable, wanted / (interference + physics.noise_power_w), 0.0
        )

    # -- helpers ----------------------------------------------------------

    def _incumbent_norads(self) -> np.ndarray:
        return np.array(
            [
                -1 if ledger.incumbent_norad is None else ledger.incumbent_norad
                for ledger in self._ledgers
            ],
            dtype=np.int64,
        )

    def _draw_fading(
        self, satellite_ecef: dict[int, np.ndarray], rng: np.random.Generator
    ) -> dict[int, np.ndarray]:
        """One Rician draw per (user, satellite), keyed by NORAD id.

        Per satellite rather than per beam: fading is a property of the
        propagation path, and every beam of one satellite reaches a given
        user over the same one.  Drawing per beam would let a wanted link
        and its own co-satellite interferers fade independently, which adds
        variance to the SINR without modelling anything.

        Iteration is over sorted NORAD ids so the draw order — and therefore
        the whole episode — is reproducible from the seed alone.
        """
        if not self.physics.fading_enabled:
            return {
                int(norad): np.ones(self.num_users, dtype=np.float64)
                for norad in satellite_ecef
            }
        return {
            int(norad): rician_fading_gain(
                rng,
                (self.num_users,),
                k_factor_db=self.physics.rician_k_factor_db,
            )
            for norad in sorted(satellite_ecef)
        }

    def _diagnostics(self, physics: dict[str, object]) -> dict[str, object]:
        resolution: ServiceResolution = physics["resolution"]  # type: ignore[assignment]
        interference: InterferenceBreakdown = physics["interference"]  # type: ignore[assignment]
        radiating: RadiatingBeams = physics["radiating"]  # type: ignore[assignment]
        served = resolution.served
        report = segment_start_feasibility_report(
            p0_w=self.physics.segment_start_power_w,
            max_power_w=self.physics.beam_power_max_w,
            saturation_power_w=self.physics.pa_saturation_power_w,
        )
        return {
            "served": resolution.served_count,
            "no_op_users": int(np.count_nonzero(resolution.no_op_users)),
            "outage_infeasible": int(
                np.count_nonzero(resolution.outage_infeasible)
            ),
            "null_pointing": int(
                np.count_nonzero(physics["null_pointing"])  # type: ignore[arg-type]
            ),
            "radiating_beams": radiating.count,
            "intra_interference_fraction": (
                float(np.mean(interference.intra_fraction[served]))
                if np.any(served)
                else 0.0
            ),
            "system_power_w": float(physics["system_power_w"]),  # type: ignore[arg-type]
            "fixed_power_w": float(physics["fixed_power_w"]),  # type: ignore[arg-type]
            # (3.16) charges P^p once per served LINK; one beam draws one
            # amplifier's supply.  The ratio is the size of that gap.
            "beam_charged_power_w": float(
                physics["beam_charged_power_w"]  # type: ignore[arg-type]
            ),
            "link_over_beam_power_ratio": (
                float(physics["system_power_w"])  # type: ignore[arg-type]
                / float(physics["beam_charged_power_w"])  # type: ignore[arg-type]
                if float(physics["beam_charged_power_w"]) > 0.0  # type: ignore[arg-type]
                else 1.0
            ),
            "sinr_provenance_state_block": CANDIDATE_SINR_PROVENANCE,
            "segment_start_feasibility": report,
        }


def _satellite_positions(candidates: StepCandidates) -> dict[int, np.ndarray]:
    """Every tracked satellite that appears in some user's window.

    The interference sum of (3.12b) is global, and this is the whole of it:
    a beam radiates only if a user selected it, and a user can only select
    from their own window, so the union of the windows contains every
    radiating satellite by construction.
    """
    positions: dict[int, np.ndarray] = {}
    norads = candidates.window_norad_ids
    ecef = candidates.window_satellite_ecef_km
    for uid in range(norads.shape[0]):
        for slot in range(norads.shape[1]):
            norad = int(norads[uid, slot])
            if norad >= 0 and norad not in positions:
                positions[norad] = ecef[uid, slot]
    return positions


def _boresight(
    resolution: ServiceResolution,
    satellite_ecef: dict[int, np.ndarray],
    user_ecef: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Where each terminal is pointed, and a finite placeholder when nowhere.

    An unserved user has no boresight.  Their row still has to be finite —
    NaN would propagate through the arccos into every other user's gain
    matrix — so it is filled with their own position and their NORAD id left
    at ``-1``, which is what stops the row being read as a wanted link.
    """
    users = resolution.served.size
    ecef = np.array(user_ecef, dtype=np.float64, copy=True)
    ids = np.full(users, -1, dtype=np.int64)
    for uid in range(users):
        if not resolution.served[uid]:
            continue
        norad = int(resolution.serving_satellite[uid])
        ecef[uid] = satellite_ecef[norad]
        ids[uid] = norad
    return ecef, ids
