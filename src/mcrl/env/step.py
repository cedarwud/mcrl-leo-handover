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
      -> capacity R = (B^w/U)·log2(1+gamma)           (3.14)
      -> delivered B = min(dt·R, dt·d)                (V0.24 regime B)
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
from .demand import DemandModel
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
    NativeObservationProvenance,
    build_native_observation_provenance,
    numpy_rng_state_sha256,
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
    shadow_fading_db,
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

    segment_warm_start: str = "uniform-episode-length"
    """How old a link's power segment already is when the episode opens.

    ⚠ **Not a nicety.**  Without it every episode has ``p(0) = p⁰`` for
    every user — measured at 100.0% of segments before this existed — and
    that is an artefact of the episode boundary, not a property of the
    geometry.  It is the same defect W-04 fixed for the D2 latches by
    priming them before step 0, and the same argument settles it.

    ``uniform-episode-length`` (**the main arm**): the age is drawn
    ``Uniform{0, …, H−1}``, so step 0 looks like a uniformly random step of
    an ongoing episode.  Parameter-free — it reuses ``H`` — and ``a = 0``
    keeps positive probability, so a genuinely fresh segment still occurs;
    it just stops being certain.

    ``uniform-segment-length`` (**the frozen sensitivity arm**): the age is
    drawn ``Uniform{0, …, L−1}`` with ``L`` the frozen median segment
    length.  This is the renewal-equilibrium age distribution and is
    theoretically the more correct one, but ``L`` is measured **under the
    reference policy**, which is how a policy gets back into the initial
    state distribution — the reason (d1) was rejected.

    ⚠ The main arm's bias is **not** conservative.  At ``Δt = 30.08 s`` the
    measured ``L`` is 5 steps against ``H = 10``, so drawing over ``H``
    ages segments *beyond* their typical life and pushes ``p`` further from
    ``p⁰`` — i.e. it makes the mechanism look **more** active, in exactly
    the direction we are trying to establish.  That is why the second arm
    is frozen alongside it rather than discussed: if the two arms disagree
    on a headline, the disagreement is the finding.

    ``none`` exists only for tests that need ``p(0) = p⁰`` deterministically.
    """

    segment_age_steps: int = 0
    """``L`` for ``uniform-segment-length``.  Ignored by the other modes."""

    fading_enabled: bool = True
    """Rician fading is a **random draw** and belongs to the frozen seed set.

    Turning it off makes a step deterministic given the ephemeris, which is
    what the equivalence and identity tests need; it is not a modelling
    option and no reported run may use it.
    """

    def __post_init__(self) -> None:
        if self.segment_warm_start not in {
            "uniform-episode-length",
            "uniform-segment-length",
            "none",
        }:
            raise ValueError(
                "segment_warm_start must be one of {'uniform-episode-length', "
                "'uniform-segment-length', 'none'}, got "
                f"{self.segment_warm_start!r}"
            )
        if (
            self.segment_warm_start == "uniform-segment-length"
            and self.segment_age_steps < 1
        ):
            raise ValueError(
                "uniform-segment-length needs a frozen segment_age_steps (L)"
            )
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
    age_steps: int = 0

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
    observation_provenance: NativeObservationProvenance | None = None
    """Receipt-only native RNG/event ancestry; never a learner feature."""

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
    interference_terms_w: np.ndarray
    """``(U, B)`` — ``p·G^T·H`` per radiating beam, before the colour mask."""
    separation_deg: np.ndarray
    """``(U, B)`` — the at-user angle (3.10c) is evaluated at.  For P5."""

    link_power_w: np.ndarray
    """``(U,)`` — ``p_{u,s,v}`` for the chosen link, 0 when unserved."""
    link_sinr: np.ndarray
    """``(U,)`` — the realised (3.13), 0 when unserved."""
    link_rate_bps: np.ndarray
    """``(U,)`` — delivered goodput rate, 0 when unserved.

    It equals the realised (3.14) capacity in the default G0 full-buffer
    regime. ``capacity_bits`` retains the uncapped interval numerator.
    """
    handovers: tuple[HandoverClass, ...]
    system_power_w: float
    fixed_power_w: float
    diagnostics: dict[str, object] = field(default_factory=dict)
    capacity_bits: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.float64)
    )
    """``(U,)`` uncapped Shannon capacity delivered by the interval."""
    delivered_bits: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.float64)
    )
    """``(U,)`` demand-capped goodput delivered by the interval."""

    @property
    def reward_matrix(self) -> np.ndarray:
        """``(U, 3)`` of ``(r1, r2, r3)`` in natural units, unscaled.

        ``r1`` is the energy efficiency of (3.25), in bit/J — not the
        throughput.  ``throughput_bps`` below carries ``R_u`` separately.
        """
        return np.array(
            [
                (
                    reward.r1_system_ee_contribution,
                    reward.r2_handover,
                    reward.r3_load_balance,
                )
                for reward in self.rewards
            ],
            dtype=np.float64,
        )

    @property
    def throughput_bps(self) -> np.ndarray:
        """``(U,)`` delivered-goodput rate — r1's G-8 numerator."""
        return np.array(
            [reward.r1_throughput for reward in self.rewards], dtype=np.float64
        )


@dataclass(frozen=True)
class ActionEvaluation:
    """Current-slot physics for an action vector, without committing state.

    This is deliberately smaller than :class:`StepOutcome`: a counterfactual
    has no next observation and never advances the scenario.  It uses a copy
    of the caller's random generator, so several action vectors can be scored
    against the same fading and shadowing draw (common random numbers).
    """

    rewards: tuple[RewardComponents, ...]
    resolution: ServiceResolution
    energy: SystemEnergyEfficiency
    interference: InterferenceBreakdown
    radiating: RadiatingBeams
    link_power_w: np.ndarray
    link_sinr: np.ndarray
    link_rate_bps: np.ndarray
    """Delivered-goodput rate; equal to capacity rate in default G0."""
    handovers: tuple[HandoverClass, ...]
    system_power_w: float
    fixed_power_w: float
    diagnostics: dict[str, object] = field(default_factory=dict)
    capacity_bits: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.float64)
    )
    """``(U,)`` uncapped Shannon capacity delivered by the interval."""
    delivered_bits: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.float64)
    )
    """``(U,)`` demand-capped goodput delivered by the interval."""

    @property
    def reward_matrix(self) -> np.ndarray:
        """``(U, 3)`` of ``(r1, r2, r3)`` in unscaled natural units."""
        return np.array(
            [
                (
                    reward.r1_system_ee_contribution,
                    reward.r2_handover,
                    reward.r3_load_balance,
                )
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
        fading_field: KeyedFadingField | None = None,
        demand: DemandModel | None = None,
    ) -> None:
        self.driver = driver
        self.physics = physics or PhysicsConfig()
        self.trainer = trainer or TrainerConfig()
        self._fading_field = fading_field
        self.demand = demand or DemandModel()
        self.num_users = driver.config.mobility.num_users
        self._ledgers: list[HandoverLedger] = [
            HandoverLedger() for _ in range(self.num_users)
        ]
        self._segments: list[Segment | None] = [None] * self.num_users
        self._previous_radiating: RadiatingBeams = empty_radiating_beams()
        self._previous_link_power_w = np.zeros(self.num_users, dtype=np.float64)
        # The last committed, realised served rate per user.  This is kept
        # beside the other previous-slot state so causal state encoders can
        # build lagged rate burdens without consulting a counterfactual.
        self._previous_served_rate_bps = np.zeros(
            self.num_users, dtype=np.float64
        )
        self._previous_demand: dict[tuple[int, int], int] = {}
        self._previous_association: list[Association | None] = [None] * self.num_users
        self._candidates: StepCandidates | None = None
        self._mobility_rng: np.random.Generator | None = None
        self._pending_segment_age: np.ndarray | None = None
        self._age_rng: np.random.Generator | None = None
        self._step_index = 0
        self._started = False

    # -- episode-boundary resume state -----------------------------------

    def training_state_dict(self) -> dict[str, object]:
        """Return the environment state that survives an episode reset.

        All physics state is intentionally episode-local and is rebuilt by
        :meth:`reset`.  The warm-start age stream is the one exception: it is
        spawned once and then reused across episodes, so losing its bit
        generator state changes every later episode's initial segment ages.
        Only that persistent stream crosses the resume boundary.
        """

        return {
            "format_version": 1,
            "age_rng_state": (
                None
                if self._age_rng is None
                else copy.deepcopy(self._age_rng.bit_generator.state)
            ),
        }

    def load_training_state_dict(self, state: Mapping[str, object]) -> None:
        """Restore the persistent age stream from an episode-boundary state."""

        if not isinstance(state, Mapping):
            raise TypeError("StepEnvironment training state must be a mapping")
        if state.get("format_version") != 1:
            raise ValueError(
                "unsupported StepEnvironment training state format_version "
                f"{state.get('format_version')!r}; expected 1"
            )
        age_state = state.get("age_rng_state")
        if age_state is None:
            self._age_rng = None
            return
        try:
            restored = np.random.default_rng()
            restored.bit_generator.state = copy.deepcopy(age_state)
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError("invalid StepEnvironment age_rng_state") from exc
        self._age_rng = restored

    # ``resume_*`` is an explicit alias for callers that want to name the
    # boundary rather than the broader training state.  Both routes carry
    # exactly the same minimal payload.
    def resume_state_dict(self) -> dict[str, object]:
        return self.training_state_dict()

    def load_resume_state_dict(self, state: Mapping[str, object]) -> None:
        self.load_training_state_dict(state)

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
        self,
        start_utc: dt.datetime,
        rng: np.random.Generator,
        *,
        mobility_rng: np.random.Generator | None = None,
    ) -> StepObservation:
        """Begin an episode and return the step-0 observation.

        Every carried quantity is cleared, not merely reset to a plausible
        value: at ``t = 0`` there is no previous association (so ``x(t−1)``
        is all zero), no previous demand (``N(t−1)`` likewise), and nothing
        radiating (so ``I = 0``, which is a fact about an idle system rather
        than a missing term).

        ``rng`` draws the Rician fading; ``mobility_rng`` places and moves
        the users.  Keeping them apart is what lets a fading ablation leave
        the population where it was — with one stream, turning fading off
        would silently re-seed everybody's starting position and the two
        effects could never be separated.  Defaulting to one stream keeps
        the single-generator call site legal for tests.
        """
        for ledger in self._ledgers:
            ledger.reset()
        self._segments = [None] * self.num_users
        self._previous_radiating = empty_radiating_beams()
        self._previous_link_power_w = np.zeros(self.num_users, dtype=np.float64)
        self._previous_served_rate_bps = np.zeros(
            self.num_users, dtype=np.float64
        )
        self._previous_demand = {}
        self._previous_association = [None] * self.num_users
        self._step_index = 0
        self._started = True
        self._mobility_rng = mobility_rng if mobility_rng is not None else rng
        # The warm-start ages get their OWN stream, spawned once from the
        # environment generator.  Sharing one stream with the fading looks
        # harmless and is not: the fading draws advance the stream, so
        # turning fading off shifts every subsequent episode's ages and a
        # "fading ablation" silently becomes a fading-and-entry-age
        # ablation.  Measured before the split: 95 outages with fading on
        # versus 106 with it off, from ages that were supposed to be
        # identical.  Same argument as the env_rng / mobility_rng split.
        if self._age_rng is None:
            self._age_rng = rng.spawn(1)[0]
        self._pending_segment_age = self._draw_segment_ages(self._age_rng)

        candidates = self.driver.reset(
            start_utc,
            self._mobility_rng,
            incumbent_norads=self._incumbent_norads(),
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

        return self._step_selected_actions(decision, selected, rng)

    def step_without_user(
        self,
        actions: np.ndarray,
        rng: np.random.Generator,
        *,
        focal_user: int,
    ) -> StepOutcome:
        """Commit one physics-only focal-removal counterfactual slot.

        ``actions`` must first be a fully valid native action vector.  The
        method then replaces exactly ``focal_user`` by ``NO_OP_ACTION`` behind
        the deployment action-contract boundary and commits the resulting
        physical transition.  This is a source-construction seam for a sealed
        counterfactual branch; it does not make no-op selectable by Main or by
        any Q surface.  Repeated removal across later offsets is a caller-owned
        absorbing policy.
        """

        if not self._started or self._candidates is None:
            raise MCRLContractError("the environment has not been reset")
        decision = self._candidates
        selected = assert_selected_actions_valid(actions, decision.slot_tables)
        focal = int(focal_user)
        if focal != focal_user or not 0 <= focal < self.num_users:
            raise MCRLContractError("focal_user must index the environment users")
        removed = np.array(selected, dtype=np.int64, copy=True)
        removed[focal] = NO_OP_ACTION
        removed.setflags(write=False)
        return self._step_selected_actions(decision, removed, rng)

    def _step_selected_actions(
        self,
        decision: StepCandidates,
        selected: np.ndarray,
        rng: np.random.Generator,
    ) -> StepOutcome:
        """Commit an already validated or dedicated counterfactual vector."""

        physics = self._resolve_physics(decision, selected, rng)
        rewards, handovers = self._rewards(decision, selected, physics)

        self._previous_radiating = physics["radiating"]
        resolution: ServiceResolution = physics["resolution"]  # type: ignore[assignment]
        link_power = np.asarray(physics["link_power_w"], dtype=np.float64)
        self._previous_link_power_w = np.where(
            resolution.served, link_power, 0.0
        ).astype(np.float64, copy=False)
        rate = np.asarray(physics["rate"], dtype=np.float64)
        if rate.shape != (self.num_users,):
            raise MCRLContractError("realised served rates have the wrong shape")
        self._previous_served_rate_bps = np.where(
            resolution.served, rate, 0.0
        ).astype(np.float64, copy=True)
        self._previous_demand = physics["resolution"].demand_by_beam
        self._step_index += 1
        done = self._step_index >= self.driver.config.steps_per_episode

        if done:
            following = decision
        else:
            following = self.driver.step(
                self._mobility_rng, incumbent_norads=self._incumbent_norads()
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
            interference_terms_w=physics["interference_terms_w"],
            separation_deg=physics["separation_deg"],
            link_power_w=physics["link_power_w"],
            link_sinr=physics["sinr"],
            link_rate_bps=physics["rate"],
            handovers=handovers,
            system_power_w=physics["system_power_w"],
            fixed_power_w=physics["fixed_power_w"],
            diagnostics=self._diagnostics(physics),
            capacity_bits=physics["capacity_bits"],
            delivered_bits=physics["delivered_bits"],
        )

    def evaluate_actions(
        self, actions: np.ndarray, rng: np.random.Generator
    ) -> ActionEvaluation:
        """Evaluate current-slot actions without advancing state or ``rng``.

        ``_resolve_physics`` normally commits only the link-power segment
        bookkeeping before :meth:`step` commits the remaining episode state.
        This method isolates that one write behind a snapshot/restore boundary
        and classifies handovers without observing them in the ledgers.
        """
        if not self._started or self._candidates is None:
            raise MCRLContractError("the environment has not been reset")
        decision = self._candidates
        selected = assert_selected_actions_valid(actions, decision.slot_tables)

        return self._evaluate_selected_actions(decision, selected, rng)

    def evaluate_actions_without_user(
        self,
        actions: np.ndarray,
        rng: np.random.Generator,
        *,
        focal_user: int,
    ) -> ActionEvaluation:
        """Evaluate one physics-only focal removal without committing state.

        ``actions`` must first be a fully valid deployment action vector.  The
        evaluator then replaces exactly ``focal_user`` by ``NO_OP_ACTION``
        behind the public action-contract boundary and keeps every other action
        byte-identical.  This dedicated counterfactual is used only to measure
        focal marginal power; it does not make a no-op legal for deployment.
        """

        if not self._started or self._candidates is None:
            raise MCRLContractError("the environment has not been reset")
        decision = self._candidates
        selected = assert_selected_actions_valid(actions, decision.slot_tables)
        focal = int(focal_user)
        if focal != focal_user or not 0 <= focal < self.num_users:
            raise MCRLContractError("focal_user must index the environment users")
        if int(selected[focal]) == NO_OP_ACTION:
            raise MCRLContractError(
                "focal removal requires an originally served-action candidate"
            )
        removed = np.array(selected, dtype=np.int64, copy=True)
        removed[focal] = NO_OP_ACTION
        removed.setflags(write=False)
        return self._evaluate_selected_actions(decision, removed, rng)

    def _evaluate_selected_actions(
        self,
        decision: StepCandidates,
        selected: np.ndarray,
        rng: np.random.Generator,
    ) -> ActionEvaluation:
        """Evaluate an already-validated or dedicated counterfactual vector."""

        local_rng = copy.deepcopy(rng)
        segments = self._segments.copy()
        try:
            physics = self._resolve_physics(decision, selected, local_rng)
        finally:
            self._segments = segments
        rewards, handovers = self._rewards(
            decision, selected, physics, commit=False
        )

        return ActionEvaluation(
            rewards=rewards,
            resolution=physics["resolution"],  # type: ignore[arg-type]
            energy=physics["energy"],  # type: ignore[arg-type]
            interference=physics["interference"],  # type: ignore[arg-type]
            radiating=physics["radiating"],  # type: ignore[arg-type]
            link_power_w=physics["link_power_w"],  # type: ignore[arg-type]
            link_sinr=physics["sinr"],  # type: ignore[arg-type]
            link_rate_bps=physics["rate"],  # type: ignore[arg-type]
            handovers=handovers,
            system_power_w=float(physics["system_power_w"]),
            fixed_power_w=float(physics["fixed_power_w"]),
            diagnostics=self._diagnostics(physics),
            capacity_bits=physics["capacity_bits"],  # type: ignore[arg-type]
            delivered_bits=physics["delivered_bits"],  # type: ignore[arg-type]
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

        # One propagation per distinct age, only at step 0 and only if the
        # warm start is on.  Ages are small integers over a small span, so
        # this is a handful of calls rather than one per user.
        historical: dict[tuple[int, int], np.ndarray] = {}
        if self._step_index == 0 and self._pending_segment_age is not None:
            for age in sorted(set(int(a) for a in self._pending_segment_age)):
                if age > 0:
                    historical.update(
                        {
                            (age, norad): position
                            for norad, position in self.driver.satellite_ecef_at(
                                -age
                            ).items()
                        }
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
            if continuing and segment is not None:
                start_gain = segment.start_transmit_gain
            else:
                # A NEW segment.  At step 0 it may nevertheless be an OLD
                # one -- the episode boundary is not a physical event, and
                # pinning p(0) = p0 for every user is the artefact the warm
                # start exists to remove.
                warm = (
                    self._warm_start_gain(uid, associations[uid], historical)
                    if self._step_index == 0
                    else None
                )
                start_gain = (
                    warm if warm is not None else float(transmit_gain[uid])
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
                if continuing and segment is not None:
                    start_gain = segment.start_transmit_gain
                    age_steps = segment.age_steps + 1
                else:
                    warm = (
                        self._warm_start_gain(uid, association, historical)
                        if self._step_index == 0
                        else None
                    )
                    start_gain = (
                        warm if warm is not None else float(transmit_gain[uid])
                    )
                    warm_age = (
                        int(self._pending_segment_age[uid])
                        if self._step_index == 0
                        and warm is not None
                        and self._pending_segment_age is not None
                        else 0
                    )
                    age_steps = warm_age + 1
                self._segments[uid] = Segment(
                    norad_id=association.norad_id,
                    cell_id=association.cell_id,
                    start_transmit_gain=start_gain,
                    age_steps=age_steps,
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
        fading, shadow = self._draw_fading(
            satellite_ecef,
            rng,
            _elevation_by_norad(decision),
            event="physics",
        )

        field_now = beam_field_at_users(
            user_ecef_km=user_ecef,
            radiating=radiating,
            fading_by_norad=fading,
            shadow_db_by_norad=shadow,
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
        # Kept rather than discarded: probe P5 owes (3.10c) a disclosure of
        # how much interference is evaluated below S.465-6's theta^R_min,
        # and that cannot be reported from a quantity thrown away here.
        separation = boresight_separation_deg(
            user_ecef_km=user_ecef,
            radiating=radiating,
            boresight_satellite_ecef_km=boresight_ecef,
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
        capacity_rate = np.where(
            resolution.served,
            shannon_rate_bps(
                sinr, beam_load=load, bandwidth_hz=physics.beam_bandwidth_hz
            ),
            0.0,
        )
        interval_s = float(self.driver.config.ephemeris.time_step_s)
        capacity_bits = capacity_rate * interval_s
        delivered_bits = self.demand.delivered_bits(
            capacity_rate, interval_s=interval_s
        )
        # Existing downstream seams consume a rate. Under finite demand it is
        # delivered goodput per second; under the default G0 it is byte-equal
        # to the pre-change Shannon-rate vector.
        rate = (
            capacity_rate
            if np.isinf(self.demand.demand_bits_per_s)
            else delivered_bits / interval_s
        )

        # (3.15)-(3.16a): consumed power, PER BEAM (ruling F-2).
        #
        # One beam, one amplifier, one supply draw.  The paper's (3.16) was a
        # triple sum over links, which charged one amplifier once per user
        # sitting on it; the over-count rose with occupancy and sat in r1's
        # denominator, quietly making the first objective do the third's job.
        efficiency = pa_efficiency(
            beam_power,
            max_efficiency=physics.pa_max_efficiency,
            saturation_power_w=physics.pa_saturation_power_w,
        )
        supply = supply_power_w(beam_power, efficiency)
        beams_by_satellite = np.array(
            [
                sum(1 for key in beam_keys if key[0] == norad)
                for norad in sorted({key[0] for key in beam_keys})
            ],
            dtype=np.float64,
        )
        fixed = fixed_power_w(beams_by_satellite)
        total_power = system_power_w(supply, beams_by_satellite)

        # An INDEPENDENT recomputation of the per-beam figure, so the
        # reported P^N can be checked against it rather than against itself,
        # plus the superseded per-link form for disclosure.
        beam_charged_power = fixed + float(
            supply_power_w(
                beam_power,
                pa_efficiency(
                    beam_power,
                    max_efficiency=physics.pa_max_efficiency,
                    saturation_power_w=physics.pa_saturation_power_w,
                ),
            ).sum()
        )
        link_charged_power = fixed + float(
            supply[beam_index[resolution.served]].sum()
            if beam_keys and np.any(resolution.served)
            else 0.0
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
            "capacity_bits": capacity_bits,
            "delivered_bits": delivered_bits,
            "supply_power_w": supply,
            "system_power_w": total_power,
            "fixed_power_w": fixed,
            "null_pointing": null_pointing,
            "beam_keys": beam_keys,
            "beam_charged_power_w": beam_charged_power,
            "link_charged_power_w": link_charged_power,
            "interference_terms_w": terms,
            "separation_deg": separation,
        }

    def _rewards(
        self,
        decision: StepCandidates,
        actions: np.ndarray,
        physics: dict[str, object],
        *,
        commit: bool = True,
    ) -> tuple[tuple[RewardComponents, ...], tuple[HandoverClass, ...]]:
        """(3.25) ``r1``, (3.27) ``r2``, (3.28) ``r3``.

        ``commit=False`` is the counterfactual path: it computes the exact
        handover class from the current ledger but does not advance it.
        """
        from .action_contract import HANDOVER_COST, UNSERVED, classify_handover

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
            ledger = self._ledgers[uid]
            handover = (
                ledger.observe(realised)
                if commit
                else classify_handover(ledger.previous, realised)
            )
            classes.append(handover)
            if commit:
                self._previous_association[uid] = (
                    realised if isinstance(realised, Association) else None
                )
            rewards.append(
                RewardComponents(
                    # r1 IS the energy efficiency (3.25).  The throughput
                    # beside it is its numerator, reported because G-8 will
                    # not accept an EE quoted without the service it bought.
                    r1_system_ee_contribution=float(r1[uid]),
                    r1_throughput=float(rate[uid]),
                    r2_handover=-HANDOVER_COST[handover],
                    r3_load_balance=float(r3[uid]),
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
        observation_rng_pre_sha256 = numpy_rng_state_sha256(rng)
        sinr = self._candidate_sinr(candidates, theta_deg, norad_ids, cell_ids, rng)
        observation_provenance = build_native_observation_provenance(
            step_index=self._step_index,
            candidate_sinr=sinr,
            rng=rng,
            rng_pre_state_sha256=observation_rng_pre_sha256,
            fading_field=self._fading_field,
            sinr_provenance=CANDIDATE_SINR_PROVENANCE,
        )

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
            observation_provenance=observation_provenance,
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
        fading, shadow = self._draw_fading(
            satellite_ecef,
            rng,
            _elevation_by_norad(candidates),
            event="observation",
        )

        transmit = transmit_gain_linear(theta_deg)
        slant = np.repeat(candidates.slant_range_km, NUM_BEAM_SLOTS, axis=1)
        elevation = np.repeat(candidates.elevation_deg, NUM_BEAM_SLOTS, axis=1)
        usable = (norad_ids >= 0) & (cell_ids >= 0) & np.isfinite(slant)

        # Both random terms first: L_s is a dB loss and so belongs inside
        # the path-loss sum, not multiplied onto it afterwards.
        fade = np.ones((users, NUM_ACTIONS), dtype=np.float64)
        shade_db = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
        for uid in range(users):
            for action in range(NUM_ACTIONS):
                norad = int(norad_ids[uid, action])
                if norad >= 0:
                    fade[uid, action] = fading[norad][uid]
                    shade_db[uid, action] = shadow[norad][uid]

        path = np.where(
            usable,
            link_power_factor(
                np.where(usable, slant, 1.0),
                np.where(usable, elevation, 0.0),
                np.full(slant.shape, _RX_GAIN_MAX_LINEAR),
                shadow_fading_db=shade_db,
            ),
            0.0,
        )

        wanted = physics.segment_start_power_w * transmit * path * fade
        wanted = np.where(usable, wanted, 0.0)

        if radiating.count == 0:
            interference = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
        else:
            previous_ecef = {
                int(norad): radiating.satellite_ecef_km[index]
                for index, norad in enumerate(radiating.norad_ids.tolist())
            }
            previous_only_ecef = {
                norad: position
                for norad, position in previous_ecef.items()
                if norad not in fading
            }
            previous_fading, previous_shadow = self._draw_fading(
                previous_only_ecef,
                rng,
                event="observation",
            )
            for norad in previous_ecef:
                if norad in fading:
                    previous_fading[norad] = fading[norad]
                    previous_shadow[norad] = shadow[norad]
            field_previous = beam_field_at_users(
                user_ecef_km=user_ecef,
                radiating=radiating,
                fading_by_norad=previous_fading,
                shadow_db_by_norad=previous_shadow,
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
        self,
        satellite_ecef: dict[int, np.ndarray],
        rng: np.random.Generator,
        elevation_by_norad: dict[int, np.ndarray] | None = None,
        *,
        event: str = "direct",
    ) -> tuple[dict[int, np.ndarray], dict[int, np.ndarray]]:
        """The model's **only two random terms**, drawn together.

        ``(rician_gain, shadow_loss_db)``, both per (user, satellite) and
        keyed by NORAD id.  Per satellite rather than per beam because both
        are properties of the propagation path, and every beam of one
        satellite reaches a given user over the same one: drawing per beam
        would let a wanted link and its own co-satellite interferers fade
        independently, which adds variance to the SINR without modelling
        anything.

        They are drawn in one pass, from one generator, in sorted NORAD
        order, so the PREREG can commit a single seed set for both (ruling
        C-8) and the whole episode is reproducible from it.

        ``L_s``'s σ depends on elevation (TR 38.811 Table 6.6.2-3), so the
        caller supplies it; without it the draw falls back to the table's
        10° row, which is its most pessimistic.
        """
        order = sorted(satellite_ecef)
        if not self.physics.fading_enabled:
            zero = {
                int(norad): np.zeros(self.num_users, dtype=np.float64)
                for norad in order
            }
            return (
                {
                    int(norad): np.ones(self.num_users, dtype=np.float64)
                    for norad in order
                },
                zero,
            )
        if self._fading_field is not None:
            return self._fading_field.draw(
                event=event,
                step_index=self._step_index,
                norad_ids=order,
                num_users=self.num_users,
                elevation_by_norad=elevation_by_norad,
                k_factor_db=self.physics.rician_k_factor_db,
            )
        rician: dict[int, np.ndarray] = {}
        shadow: dict[int, np.ndarray] = {}
        for norad in order:
            rician[int(norad)] = rician_fading_gain(
                rng,
                (self.num_users,),
                k_factor_db=self.physics.rician_k_factor_db,
            )
            elevation = (
                (elevation_by_norad or {}).get(
                    int(norad), np.full(self.num_users, 10.0)
                )
            )
            shadow[int(norad)] = shadow_fading_db(rng, np.asarray(elevation))
        return rician, shadow

    def _draw_segment_ages(self, rng: np.random.Generator) -> np.ndarray | None:
        """How many steps each user's segment has already run at step 0.

        Drawn from ``env_rng`` rather than the mobility stream: it is part
        of the environment's own randomness, alongside the fading and the
        epoch, and it must not move when a mobility ablation does.
        """
        mode = self.physics.segment_warm_start
        if mode == "none":
            return None
        span = (
            self.driver.config.steps_per_episode
            if mode == "uniform-episode-length"
            else self.physics.segment_age_steps
        )
        return rng.integers(0, max(span, 1), size=self.num_users)

    def _warm_start_gain(
        self,
        uid: int,
        association: Association,
        historical: dict[tuple[int, int], np.ndarray],
    ) -> float | None:
        """``G^T(θ(τ))`` for a segment that began before the episode did.

        The satellite is put back where it was ``a`` decision steps ago and
        the off-axis angle to the **same cell** is recomputed.  The user is
        left where they are now: they move 250 m per step, which subtends
        0.0297° at 483 km against a median per-step ``|Δθ|`` of 1.194° — a
        2.5% contribution, the same ratio that justifies leaving mobility on
        the decision clock.  Disclosed rather than assumed away, and it is a
        bound: the satellite moves 2,004 km over the same nine steps.
        """
        ages = self._pending_segment_age
        if ages is None:
            return None
        age = int(ages[uid])
        if age <= 0:
            return None
        position = historical.get((age, association.norad_id))
        if position is None:
            # The satellite was not tracked that far back; a cold start is
            # the honest fallback, not an extrapolated position.
            return None
        angle = angle_between_deg(
            position,
            self.driver.grid.centers_ecef_km[association.cell_id],
            self.driver.user_ecef_km()[uid],
        )
        gain = float(transmit_gain_linear(np.asarray([angle]))[0])
        return gain if gain > 0.0 else None

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
            # Ruling F-2 asked for this ratio to keep being reported and to
            # be identically 1.0 afterwards, as a live regression.  It is
            # ``reported P^N / independently recomputed per-beam P^N``, so it
            # was 2.28 while (3.16) was summed over links and is 1.0 now.
            # Kept rather than deleted: the defect it caught was invisible in
            # every other number the step reports.
            "link_over_beam_power_ratio": (
                float(physics["system_power_w"])  # type: ignore[arg-type]
                / float(physics["beam_charged_power_w"])  # type: ignore[arg-type]
                if float(physics["beam_charged_power_w"]) > 0.0  # type: ignore[arg-type]
                else 1.0
            ),
            # And what the superseded per-link form would have charged, so
            # the size of the correction stays quotable.
            "superseded_link_charged_power_w": float(
                physics["link_charged_power_w"]  # type: ignore[arg-type]
            ),
            "superseded_link_over_beam_ratio": (
                float(physics["link_charged_power_w"])  # type: ignore[arg-type]
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


def _elevation_by_norad(candidates: StepCandidates) -> dict[int, np.ndarray]:
    """``(U,)`` elevation per tracked satellite — what ``L_s``'s σ needs.

    Built from the candidate windows, which is the same union the
    interference sum draws its satellites from.  A satellite absent from
    every window radiates nothing, so it needs no draw.
    """
    users = candidates.window_norad_ids.shape[0]
    out: dict[int, np.ndarray] = {}
    for uid in range(users):
        for slot in range(candidates.window_norad_ids.shape[1]):
            norad = int(candidates.window_norad_ids[uid, slot])
            if norad < 0:
                continue
            column = out.setdefault(norad, np.full(users, 10.0))
            elevation = candidates.elevation_deg[uid, slot]
            if np.isfinite(elevation):
                column[uid] = float(elevation)
    return out
