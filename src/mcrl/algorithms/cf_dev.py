"""DEVHARNESS: the minimum E0 development-training surface on the ratio learner.

Governing: ``docs/dev-e0/V025-CONTROLLER-AMENDMENT-6-DEVELOPMENT-FIRST-TRAINING-2026-09-12.md``
(sections 2, 3, 5, 6, 7).  **Development lane.**  Runs made with this module are
E0 engineering runs: they are not Amendment 4 screening evidence, they support no
statistical claim, and they may never touch the formal evaluation (9_111_000+i /
9_112_000+i), calibration (9_121_000+i / 9_122_000+i) or CONFIRM (9_311_000+i /
9_312_000+i) episodes.  :func:`assert_dev_seed` enforces that at every seed this
module constructs, and ``tests/test_cf_dev.py`` fails if any development path
produces one of those seeds.

What it adds to :class:`~mcrl.algorithms.cf_ratio.CFRatioTrainer` (which is NOT
edited):

* the teacher labels of :mod:`mcrl.algorithms.cf_teacher` (T0 action + the 28-score
  vector), computed from the RAW user state at collection time and stored with the
  transition in :class:`TeacherReplayBuffer`;
* the mechanisms ``D0`` / ``D2-T0`` / ``D2-null`` / ``D3-T0`` / ``D3-null`` /
  ``D3-XEP`` (Amendment 12's plausible-but-uninformative second null, whose fixed
  reference trajectory lives in :mod:`mcrl.algorithms.cf_xep`);
* DEVVAL evaluation (24 episodes, fresh env per episode, greedy, no training RNG);
* a training loop that never calls ``quarter_update`` / ``measure_on_calibration``
  (in E0 ``eta`` is fixed at ``eta_0`` and ``lambda = 0``; an eta update would need
  an episode set and development may not use the calibration episodes).

``D0`` runs the inherited :meth:`CFRatioTrainer.update` unchanged, so the teacher
path is the only difference between arm 1 and arms 2-4; with the teacher weight at
zero the teacher path reproduces ``D0`` bit-identically (tested).
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch

from ..env.action_contract import HandoverClass, is_no_op
from ..errors import MCRLContractError
from ..runtime.finiteness import (
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)
from ..runtime.replay_buffer import ReplayBuffer
from . import cf_teacher as cft
from .cf_credit import DEFAULT_CREDIT_MODE, PowerModel, credit_matrix, difference_context
from .cf_ratio import (
    DT_S,
    CFRatioTrainer,
    cf_reward_matrix,
    episode_seeds,
)
from .cf_sources import HEAD_B, HEAD_E, HEAD_H

# ------------------------------------------------------------------ seeds
FORBIDDEN_SEED_RANGES: tuple[tuple[int, int, str], ...] = (
    (9_111_000, 9_111_999, "formal evaluation env"),
    (9_112_000, 9_112_999, "formal evaluation mobility"),
    (9_121_000, 9_121_999, "calibration env"),
    (9_122_000, 9_122_999, "calibration mobility"),
    (9_301_000, 9_303_999, "CONFIRM training triples"),
    (9_311_000, 9_311_999, "CONFIRM evaluation env"),
    (9_312_000, 9_312_999, "CONFIRM evaluation mobility"),
)
"""Amendment 6 section 3: no development path may produce any of these."""

ALLOWED_SEED_RANGES: tuple[tuple[int, int, str], ...] = (
    (9_201_000, 9_201_999, "DEV train"),
    (9_202_000, 9_202_999, "DEV env"),
    (9_203_000, 9_203_999, "DEV mobility"),
    (9_211_000, 9_211_999, "DEVVAL env"),
    (9_212_000, 9_212_999, "DEVVAL mobility"),
    (9_221_000, 9_221_999, "DEVVAL RANDOM draws"),
    (9_231_000, 9_231_999, "DEV-NULL D2 permutations"),
    (9_241_000, 9_241_999, "DEV-NULL D3/D4 random actions"),
    (9_271_000, 9_271_999, "derived: train + 70_001 (catfish sampling)"),
    (9_281_000, 9_281_999, "derived: train + 80_000 + k (NULL sources)"),
    (9_291_000, 9_291_999, "derived: train + 90_211 (inherited penalty generator)"),
)
"""The only seed values a development run may construct (Amendment 6 section 3)."""


FORMAL_EVAL_ENV_BASE, FORMAL_EVAL_MOB_BASE = 9_111_000, 9_112_000
"""The S1 formal evaluation episodes (Amendment 6 section 3, spent by S1 only)."""

S1_TRAIN_BASE, S1_ENV_BASE, S1_MOB_BASE = 9_251_000, 9_252_000, 9_253_000
S1_NULL_BASE = 9_261_000
MAX_S1_SEED_INDEX: int = 2
"""Amendment 13 sections 4 and 5: fresh FORMAL namespaces for S1, k = 0, 1, 2.

DEV training streams may not be reused for S1; ``T0-XEP``'s reference trajectory is
the single declared exception (section 5) and stays in the DEV-NULL namespace."""

S1_ALLOWED_SEED_RANGES: tuple[tuple[int, int, str], ...] = (
    (9_251_000, 9_251_999, "S1-TRAIN train"),
    (9_252_000, 9_252_999, "S1-TRAIN env"),
    (9_253_000, 9_253_999, "S1-TRAIN mobility"),
    (9_111_000, 9_111_999, "formal evaluation env"),
    (9_112_000, 9_112_999, "formal evaluation mobility"),
    (9_321_000, 9_321_999, "derived: S1 train + 70_001 (catfish sampling)"),
    (9_331_000, 9_331_999, "derived: S1 train + 80_000 (NULL sources)"),
    (9_341_000, 9_341_999, "derived: S1 train + 90_211 (inherited penalty generator)"),
)
"""The only seed values an S1 run may construct."""

S1_FORBIDDEN_SEED_RANGES: tuple[tuple[int, int, str], ...] = (
    (9_121_000, 9_121_999, "calibration env"),
    (9_122_000, 9_122_999, "calibration mobility"),
    (9_301_000, 9_303_999, "CONFIRM training triples"),
    (9_311_000, 9_311_999, "CONFIRM evaluation env"),
    (9_312_000, 9_312_999, "CONFIRM evaluation mobility"),
    (9_201_000, 9_203_999, "DEV training triples (Amendment 13 section 4: not reusable)"),
    (9_211_000, 9_212_999, "DEVVAL (Amendment 13 section 4: not reusable)"),
    (9_221_000, 9_221_999, "DEVVAL RANDOM (Amendment 13 section 4: not reusable)"),
    (9_231_000, 9_231_999, "DEV-NULL D2 (Amendment 13 section 5: not reusable)"),
    (9_241_000, 9_241_999, "DEV-NULL D3 (Amendment 13 section 5: not reusable)"),
    (9_271_000, 9_291_999, "DEV derived substreams (not reusable)"),
)
"""An S1 run that builds one of these is a seed-isolation failure, not a near miss.

``9_241_000..999`` is forbidden as a SEED here even though ``T0-XEP``'s reference
episode was recorded on ``9_241_500 / 9_241_501``: S1 never rolls that episode again,
it loads the sealed file, so no S1 run has any reason to construct those values."""

DEV_NULL_KEY_BASES: tuple[int, ...] = (9_231_000, 9_241_000)
"""Amendment 6 section 3: the DEV-NULL generators are the COMPOSITE identities
``default_rng((9_231_000, k))`` (D2-null permutations) and
``default_rng((9_241_000, k))`` (D3/D4-null random actions)."""

MAX_DEV_SEED_INDEX: int = 9
"""DEV triples are declared for k = 0..9, so a DEV-NULL key's index is one of those."""


def assert_dev_null_key(key: Any, what: str = "") -> tuple[int, int]:
    """Validate a COMPOSITE DEV-NULL generator identity ``(base, k)``.

    The pair is ONE declared generator identity, not two seeds: the base must be a
    declared DEV-NULL namespace and ``k`` a legal development seed index
    (``0 <= k <= 9``); the index is never checked as though it were a standalone
    seed.  A formal namespace may still appear nowhere in the key -- neither in the
    base nor in the index.
    """
    if isinstance(key, (tuple, list)) and len(key) == 2:
        base, index = key
    else:
        raise MCRLContractError(
            f"development path {what!r} used {key!r} as a DEV-NULL key; the declared "
            "identity is the pair (base, k)"
        )
    if isinstance(base, (tuple, list)) or isinstance(index, (tuple, list)):
        raise MCRLContractError(f"nested DEV-NULL key {key!r} in {what!r}")
    base_value, index_value = int(base), int(index)
    for lo, hi, name in FORBIDDEN_SEED_RANGES:
        for part in (base_value, index_value):
            if lo <= part <= hi:
                raise MCRLContractError(
                    f"development path {what!r} built the DEV-NULL key {key!r}, whose "
                    f"component {part} belongs to the FORMAL namespace {name!r}"
                )
    if base_value not in DEV_NULL_KEY_BASES:
        raise MCRLContractError(
            f"development path {what!r} built the DEV-NULL key {key!r}: {base_value} is "
            f"not a declared DEV-NULL base {DEV_NULL_KEY_BASES}"
        )
    if not 0 <= index_value <= MAX_DEV_SEED_INDEX:
        raise MCRLContractError(
            f"development path {what!r} built the DEV-NULL key {key!r}: the seed index "
            f"must be an integer in 0..{MAX_DEV_SEED_INDEX}"
        )
    return base_value, index_value


def assert_dev_seed(seed: Any, what: str = "") -> int:
    """Fail closed unless ``seed`` is an integer in a declared DEV namespace.

    A tuple / list is a composite DEV-NULL generator identity and is validated by
    :func:`assert_dev_null_key` (declared base namespace + legal seed index).
    """
    if isinstance(seed, (tuple, list)):
        assert_dev_null_key(seed, what)
        return -1
    value = int(seed)
    for lo, hi, name in FORBIDDEN_SEED_RANGES:
        if lo <= value <= hi:
            raise MCRLContractError(
                f"development path {what!r} produced seed {value}, which belongs to "
                f"the FORMAL namespace {name!r}"
            )
    if not any(lo <= value <= hi for lo, hi, _n in ALLOWED_SEED_RANGES):
        raise MCRLContractError(
            f"development path {what!r} produced seed {value}, outside every declared "
            "DEV / DEVVAL / DEV-NULL namespace"
        )
    return value


def assert_dev_seed_pairs(seeds: Sequence[tuple[int, int]], what: str = "") -> None:
    for env_seed, mob_seed in seeds:
        assert_dev_seed(env_seed, f"{what} env")
        assert_dev_seed(mob_seed, f"{what} mobility")


# ------------------------------------------------------------------ S1 lane
DEV_LANE: str = "E0-development"
S1_LANE: str = "S1-formal"
LANES: tuple[str, ...] = (DEV_LANE, S1_LANE)


def assert_s1_seed(seed: Any, what: str = "") -> int:
    """The S1 lane's fail-closed seed guard (Amendment 13 sections 4 and 5).

    Same shape as :func:`assert_dev_seed` against a different whitelist: the S1-TRAIN
    triple, the formal evaluation episodes and the trainer's derived substreams, and
    nothing else.  Calibration, CONFIRM and every DEVELOPMENT stream are named
    explicitly so a reused development seed reports as seed isolation broken rather
    than as "outside every namespace".
    """
    if isinstance(seed, (tuple, list)):
        assert_s1_null_key(seed, what)
        return -1
    value = int(seed)
    for lo, hi, name in S1_FORBIDDEN_SEED_RANGES:
        if lo <= value <= hi:
            raise MCRLContractError(
                f"S1 path {what!r} produced seed {value}, which belongs to {name!r}"
            )
    if not any(lo <= value <= hi for lo, hi, _n in S1_ALLOWED_SEED_RANGES):
        raise MCRLContractError(
            f"S1 path {what!r} produced seed {value}, outside every declared S1 "
            "namespace"
        )
    return value


def assert_s1_null_key(key: Any, what: str = "") -> tuple[int, int]:
    """Validate the S1 null generator identity ``(9_261_000, k)``, k = 0, 1, 2."""
    if isinstance(key, (tuple, list)) and len(key) == 2:
        base, index = key
    else:
        raise MCRLContractError(
            f"S1 path {what!r} used {key!r} as a null key; the declared identity is "
            "the pair (9_261_000, k)"
        )
    if isinstance(base, (tuple, list)) or isinstance(index, (tuple, list)):
        raise MCRLContractError(f"nested S1 null key {key!r} in {what!r}")
    base_value, index_value = int(base), int(index)
    for lo, hi, name in S1_FORBIDDEN_SEED_RANGES:
        for part in (base_value, index_value):
            if lo <= part <= hi:
                raise MCRLContractError(
                    f"S1 path {what!r} built the null key {key!r}, whose component "
                    f"{part} belongs to {name!r}"
                )
    if base_value != S1_NULL_BASE:
        raise MCRLContractError(
            f"S1 path {what!r} built the null key {key!r}: {base_value} is not the "
            f"declared S1-NULL base {S1_NULL_BASE} (Amendment 13 section 5; the "
            "development (9_241_000, k) streams may not be reused)"
        )
    if not 0 <= index_value <= MAX_S1_SEED_INDEX:
        raise MCRLContractError(
            f"S1 path {what!r} built the null key {key!r}: the seed index must be an "
            f"integer in 0..{MAX_S1_SEED_INDEX}"
        )
    return base_value, index_value


def assert_lane_seed(seed: Any, what: str = "", *, lane: str = DEV_LANE) -> int:
    """Dispatch to the lane's guard.  ``assert_dev_seed`` stays the DEV entry point
    (so a test that neutralises it still neutralises the development path)."""
    if lane == DEV_LANE:
        return assert_dev_seed(seed, what)
    if lane == S1_LANE:
        return assert_s1_seed(seed, what)
    raise MCRLContractError(f"unknown lane {lane!r}")


def assert_lane_seed_pairs(seeds: Sequence[tuple[int, int]], what: str = "", *,
                           lane: str = DEV_LANE) -> None:
    if lane == DEV_LANE:
        assert_dev_seed_pairs(seeds, what)
        return
    for env_seed, mob_seed in seeds:
        assert_lane_seed(env_seed, f"{what} env", lane=lane)
        assert_lane_seed(mob_seed, f"{what} mobility", lane=lane)


def s1_triple(k: int) -> tuple[int, int, int]:
    """The S1-TRAIN triple for seed index ``k`` (Amendment 13 section 4)."""
    if not 0 <= int(k) <= MAX_S1_SEED_INDEX:
        raise MCRLContractError(f"S1 seed index {k} is not 0..{MAX_S1_SEED_INDEX}")
    triple = (S1_TRAIN_BASE + int(k), S1_ENV_BASE + int(k), S1_MOB_BASE + int(k))
    for seed in triple:
        assert_s1_seed(seed, "S1-TRAIN triple")
    return triple


# ------------------------------------------------------------------ settings
@dataclass(frozen=True)
class DevSettings:
    """The E0 development kernel's teacher settings (Amendment 6 section 6)."""

    mechanism: str = "D0"
    teacher: str = "none"          # none | T0 | random | T0-XEP
    alpha: float = 1.0             # D2 weight
    tau: float = 3.0               # teacher temperature (T0REPR VAL selection)
    tau_s: float = 1.0             # student temperature
    margin: float = 0.15           # D3 large margin, heads' units
    lambda_e: float = 1.0          # D3 weight (DQfD default)
    null_key: tuple[int, int] | None = None   # DEV-NULL: (9_231_000, k)
    devval_env_base: int = 9_211_000
    devval_mobility_base: int = 9_212_000
    devval_episodes: int = 24
    lane: str = DEV_LANE
    """Which seed contract this configuration runs under.

    ``E0-development`` (default): DEV / DEVVAL / DEV-NULL only, the E0 and E1 lane.
    ``S1-formal`` (Amendment 13): the S1-TRAIN triple, the S1-NULL generator and the
    FORMAL EVALUATION episodes -- ``devval_env_base`` / ``devval_mobility_base`` are
    then the formal evaluation bases ``9_111_000`` / ``9_112_000``, not DEVVAL's."""
    # -- T0-XEP (Amendment 12): the FIXED reference trajectory's identity.  These
    # three fields ARE the second null's null key: they ride in the configuration
    # hash exactly as ``null_key`` does for D3-null, so a different (or regenerated)
    # reference is a different version.  The reference FILE PATH is deliberately not
    # here -- a path is a host fact, not an identity.
    xep_reference_sha256: str | None = None
    xep_reference_key: tuple[int, int] | None = None   # DEV-NULL (env, mobility)
    xep_reference_policy: str | None = None

    def __post_init__(self) -> None:
        if self.mechanism not in cft.MECHANISMS:
            raise MCRLContractError(f"mechanism must be one of {cft.MECHANISMS}")
        if self.teacher not in cft.TEACHERS:
            raise MCRLContractError(f"teacher must be one of {cft.TEACHERS}")
        expected_teacher = {"D0": "none", "D3-null": "random",
                            "D3-XEP": "T0-XEP"}.get(self.mechanism, "T0")
        if self.teacher != expected_teacher:
            raise MCRLContractError(
                f"mechanism {self.mechanism!r} requires teacher {expected_teacher!r}"
            )
        xep = (self.xep_reference_sha256, self.xep_reference_key,
               self.xep_reference_policy)
        if self.mechanism == "D3-XEP":
            if any(x is None for x in xep):
                raise MCRLContractError(
                    "D3-XEP needs its reference identity (sha256, DEV-NULL key, policy)"
                )
            if not (isinstance(self.xep_reference_sha256, str)
                    and len(self.xep_reference_sha256) == 64):
                raise MCRLContractError("xep_reference_sha256 must be a sha256 hex digest")
            if (not isinstance(self.xep_reference_key, (tuple, list))
                    or len(self.xep_reference_key) != 2):
                raise MCRLContractError(
                    "xep_reference_key is the (env seed, mobility seed) pair the "
                    "reference episode was rolled on"
                )
            for seed in self.xep_reference_key:
                base = assert_dev_seed(seed, "T0-XEP reference seed")
                if not any(lo <= base <= hi for lo, hi in
                           ((b, b + 999) for b in DEV_NULL_KEY_BASES)):
                    raise MCRLContractError(
                        f"the T0-XEP reference seed {seed} is not in a declared "
                        f"DEV-NULL namespace {DEV_NULL_KEY_BASES} (Amendment 12 "
                        "section 2: never DEV, DEVVAL or CONFIRM)"
                    )
        elif any(x is not None for x in xep):
            raise MCRLContractError(
                "only D3-XEP may carry a reference-trajectory identity"
            )
        if self.lane not in LANES:
            raise MCRLContractError(f"lane must be one of {LANES}")
        if self.lane == S1_LANE and self.mechanism == "D2-null":
            raise MCRLContractError(
                "D2-null is not an S1 arm (Amendment 13 section 3: six trained arms)"
            )
        # The null generator's declared base is a LANE fact: the development screen
        # draws from (9_241_000, k), the formal screen from (9_261_000, k).  Reusing
        # the development stream in S1 is a seed-isolation failure (Amendment 13
        # section 5) and is refused here, not merely discouraged.
        null_base = (
            {"D3-null": S1_NULL_BASE} if self.lane == S1_LANE
            else {"D2-null": 9_231_000, "D3-null": 9_241_000}
        ).get(self.mechanism)
        if null_base is None and self.null_key is not None:
            raise MCRLContractError("only the matched nulls may carry a null key")
        if null_base is not None:
            if self.null_key is None:
                raise MCRLContractError(
                    f"{self.mechanism} needs its null key ({null_base}, k)"
                )
            checker = (assert_s1_null_key if self.lane == S1_LANE
                       else assert_dev_null_key)
            base, _index = checker(self.null_key, f"{self.lane} {self.mechanism} key")
            if base != null_base:
                raise MCRLContractError(
                    f"{self.mechanism} in lane {self.lane!r} draws from "
                    f"({null_base}, k), not {self.null_key}"
                )
        for name in ("tau", "tau_s"):
            value = float(getattr(self, name))
            if not (np.isfinite(value) and value > 0):
                raise MCRLContractError(f"{name} must be finite and positive")
        for name in ("alpha", "margin", "lambda_e"):
            value = float(getattr(self, name))
            if not (np.isfinite(value) and value >= 0):
                raise MCRLContractError(f"{name} must be finite and >= 0")
        if int(self.devval_episodes) < 0:
            raise MCRLContractError("devval_episodes must be >= 0")
        bases = (int(self.devval_env_base), int(self.devval_mobility_base))
        if self.lane == S1_LANE:
            if bases != (FORMAL_EVAL_ENV_BASE, FORMAL_EVAL_MOB_BASE):
                raise MCRLContractError(
                    f"the S1 lane evaluates on the formal evaluation episodes "
                    f"{(FORMAL_EVAL_ENV_BASE, FORMAL_EVAL_MOB_BASE)}, not {bases}"
                )
        else:
            for base in bases:
                assert_dev_seed(base, "DEVVAL base")

    @property
    def eval_env_base(self) -> int:
        """The lane's evaluation env base: DEVVAL's, or S1's formal evaluation set."""
        return int(self.devval_env_base)

    @property
    def eval_mobility_base(self) -> int:
        return int(self.devval_mobility_base)

    @property
    def uses_teacher(self) -> bool:
        return self.mechanism != "D0"

    @property
    def teacher_weight(self) -> float:
        """The weight actually multiplying this mechanism's teacher loss."""
        if self.mechanism in ("D2-T0", "D2-null"):
            return float(self.alpha)
        if self.mechanism in ("D3-T0", "D3-null", "D3-XEP"):
            return float(self.lambda_e)
        return 0.0


# ------------------------------------------------------------------ replay
class TeacherReplayBuffer(ReplayBuffer):
    """FIFO replay that carries each transition's teacher labels.

    Three labels per transition: ``t0_action`` (T0's own action, DIAGNOSTICS ONLY
    -- no loss ever reads it), ``teacher_action`` and ``teacher_scores`` (what the
    loss sees; for ``D2-null`` the scores are T0's permuted among the legal actions
    and the action is that permuted vector's masked argmax).  Labels ride the same
    FIFO positions as the transitions and are sampled at the same indices.
    """

    _TEACHER_STATE_FORMAT_VERSION = 1

    def __init__(self, capacity: int) -> None:
        super().__init__(capacity)
        self._labels: deque[tuple[int, int, np.ndarray]] = deque(maxlen=capacity)
        self._last: dict[str, np.ndarray] | None = None

    # -- writing --------------------------------------------------------
    def push(self, *args, **kwargs):  # noqa: D102 - fail closed
        raise MCRLContractError(
            "the development replay stores teacher labels: use push_labeled()"
        )

    def push_labeled(
        self, state, action, reward_3, next_state, mask, next_mask, done,
        *, t0_action: int, teacher_action: int, teacher_scores: np.ndarray,
    ) -> None:
        mask = np.asarray(mask, dtype=bool)
        if not (0 <= int(teacher_action) < mask.size and bool(mask[int(teacher_action)])):
            raise MCRLContractError("teacher action is illegal in the stored state")
        if not (0 <= int(t0_action) < mask.size and bool(mask[int(t0_action)])):
            raise MCRLContractError("T0 action is illegal in the stored state")
        scores = np.asarray(teacher_scores, dtype=np.float64)
        if scores.shape != (mask.size,):
            raise MCRLContractError("teacher scores must be one value per action")
        super().push(state, action, reward_3, next_state, mask, next_mask, done)
        self._labels.append((int(t0_action), int(teacher_action), scores.copy()))

    # -- reading --------------------------------------------------------
    def sample(self, batch_size: int, rng: np.random.Generator):
        """``ReplayBuffer.sample`` statement for statement, plus the labels.

        The generator is consumed by exactly the same single ``rng.choice`` call,
        so a development run draws the same minibatch indices as the pilot
        learner would (tested against :class:`ReplayBuffer`).
        """
        indices = rng.choice(len(self._buf), size=batch_size, replace=False)
        batch = [self._buf[i] for i in indices]

        states = np.array([b[0] for b in batch], dtype=np.float32)
        actions = np.array([b[1] for b in batch], dtype=np.int64)
        rewards = np.array([b[2] for b in batch], dtype=np.float32)
        next_states = np.array([b[3] for b in batch], dtype=np.float32)
        masks = np.array([b[4] for b in batch])
        next_masks = np.array([b[5] for b in batch])
        dones = np.array([b[6] for b in batch], dtype=np.float32)

        labels = [self._labels[i] for i in indices]
        self._last = {
            "t0_action": np.array([x[0] for x in labels], dtype=np.int64),
            "teacher_action": np.array([x[1] for x in labels], dtype=np.int64),
            "teacher_scores": np.array([x[2] for x in labels], dtype=np.float64),
            "masks": masks,
        }
        return states, actions, rewards, next_states, masks, next_masks, dones

    def last_teacher(self) -> dict[str, np.ndarray]:
        if self._last is None:
            raise MCRLContractError("no sample has been drawn yet")
        return self._last

    # -- persistence ----------------------------------------------------
    def state_dict(self) -> dict[str, Any]:
        state = super().state_dict()
        state["teacher_format_version"] = self._TEACHER_STATE_FORMAT_VERSION
        state["teacher_labels"] = [
            (int(a0), int(a1), np.array(s, copy=True)) for a0, a1, s in self._labels
        ]
        return state

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        if state.get("teacher_format_version") != self._TEACHER_STATE_FORMAT_VERSION:
            raise MCRLContractError(
                "replay state has no development teacher labels; refusing to resume"
            )
        labels = state.get("teacher_labels")
        if not isinstance(labels, (list, tuple)):
            raise MCRLContractError("teacher_labels must be a sequence")
        super().load_state_dict(state)
        if len(labels) != len(self._buf):
            raise MCRLContractError(
                f"{len(labels)} teacher labels for {len(self._buf)} transitions"
            )
        restored: deque[tuple[int, int, np.ndarray]] = deque(maxlen=self._capacity)
        for item in labels:
            a0, a1, scores = item
            restored.append((int(a0), int(a1), np.array(scores, copy=True)))
        self._labels = restored
        self._last = None


# ------------------------------------------------------------------ rollout
def _rate_stats(rates: list[float]) -> dict[str, Any]:
    """Per-served-user-step rate mean / p10 / min, as ``lp_common._rate_stats``."""
    arr = np.asarray(rates, dtype=np.float64)
    if arr.size == 0:
        return {"per_served_user_rate_mean_bps": float("nan"),
                "per_served_user_rate_p10_bps": float("nan"),
                "per_served_user_rate_min_bps": float("nan"),
                "served_user_steps": 0}
    return {"per_served_user_rate_mean_bps": float(arr.mean()),
            "per_served_user_rate_p10_bps": float(np.percentile(arr, 10)),
            "per_served_user_rate_min_bps": float(arr.min()),
            "served_user_steps": int(arr.size)}


LP_GRID_DT_S = 30.08
"""``lp_grid.py``'s literal, used ONLY for the derived ho_per_user_min display."""


def xep_leakage(xep_actions, t0_actions, legal, t0_scores) -> tuple[float, float, float, int]:
    """Amendment 12's residual-leakage counters for ONE step.

    ``(agreement, T0-score regret, expected uniform-legal agreement, decisions)``,
    summed over the rows that have a legal action.

    The FIRST argument is what ``T0-XEP`` advised and the SECOND is what the **REAL**
    T0 would have done on the same state: the diagnostic exists precisely because
    those are two different teachers, and scoring the null against itself would
    report a meaningless 1.0.  ``t0_scores`` are the REAL T0's scores on the current
    state, so the regret is measured in T0's own units.
    """
    agree = regret = random_expected = 0.0
    decisions = 0
    for u in range(len(t0_actions)):
        if not bool(legal[u].any()):
            continue
        decisions += 1
        agree += float(int(xep_actions[u]) == int(t0_actions[u]))
        random_expected += 1.0 / float(int(legal[u].sum()))
        if 0 <= int(xep_actions[u]) < t0_scores.shape[1]:
            regret += float(
                t0_scores[u, int(t0_actions[u])] - t0_scores[u, int(xep_actions[u])]
            )
    return agree, regret, random_expected, decisions


def dev_rollout(
    policy_factory, *, env_factory, encode, seeds, t0_agreement: bool = False,
    xep_probe=None, lane: str = DEV_LANE,
) -> dict[str, Any]:
    """``cf_ratio.pooled_rollout`` (seeds mode) + per-user rates and T0 agreement.

    Fresh environment per episode, per-episode reseeded, plain left-to-right
    accumulation divided once -- the same estimand as every other reading in this
    project.  Consumes no trainer generator.  ``t0_agreement`` additionally scores
    the rolled policy's action against T0's on the same raw states (observation
    only; it never touches the environment or a generator).

    ``xep_probe(legal, step) -> actions`` is the Amendment 12 residual-leakage probe:
    it is asked what ``T0-XEP`` would have advised on the SAME states, and its answer
    is scored against the REAL T0's action and score on those states.  It is a
    read-only observer -- its actions are never played, so the rollout's own numbers
    are bit-identical with and without it.
    """
    assert_lane_seed_pairs(seeds, "dev_rollout", lane=lane)
    rows: list[dict[str, Any]] = []
    rates: list[float] = []
    agree = regret = 0.0
    xep_agree = xep_regret = xep_random_agree = 0.0
    decisions = 0
    if xep_probe is not None and not t0_agreement:
        raise MCRLContractError("the T0-XEP probe is scored against T0: need t0_agreement")
    for i in range(len(seeds)):
        env = env_factory()
        env_rng = np.random.default_rng(seeds[i][0])
        mobility_rng = np.random.default_rng(seeds[i][1])
        users, steps = env.config.num_users, env.config.steps_per_episode
        policy = policy_factory(i)
        states, masks, _ = env.reset(env_rng, mobility_rng)
        enc = encode(states, 0)
        row = {"bits": 0.0, "joules": 0.0, "served": 0, "user_steps": 0,
               "h_inter": 0, "h_intra": 0, "beams": 0.0, "steps": 0,
               "epoch": str(getattr(env, "epoch", None)),
               "t0_obs112_sha256": hashlib.sha256(
                   np.ascontiguousarray(np.asarray(enc)[:, :112]).tobytes()
               ).hexdigest()}
        for t in range(steps):
            actions = policy(enc, masks, states)
            if t0_agreement:
                scores, t0_acts, legal = cft.t0_scores(states, masks)
                xep_acts = None if xep_probe is None else xep_probe(legal, t)
                for u in range(users):
                    if not bool(legal[u].any()):
                        continue
                    decisions += 1
                    agree += float(int(actions[u]) == int(t0_acts[u]))
                    if 0 <= int(actions[u]) < scores.shape[1]:
                        regret += float(scores[u, int(t0_acts[u])] - scores[u, int(actions[u])])
                if xep_acts is not None:
                    a_, r_, x_, _n = xep_leakage(xep_acts, t0_acts, legal, scores)
                    xep_agree += a_
                    xep_regret += r_
                    xep_random_agree += x_
            res = env.step(actions, env_rng)
            out = env.last_outcome
            e = out.energy
            row["bits"] += float(e.system_throughput_bps) * DT_S
            row["joules"] += float(e.system_consumed_power_w) * DT_S
            row["served"] += int(e.served)
            row["beams"] += float(e.eff_beams)
            row["steps"] += 1
            row["user_steps"] += users
            for cls in out.handovers:
                row["h_inter"] += int(cls is HandoverClass.INTER_SATELLITE)
                row["h_intra"] += int(cls is HandoverClass.INTRA_SATELLITE)
            if res.served is not None:
                for uid in range(users):
                    if bool(res.served[uid]):
                        rates.append(float(res.rewards[uid].r1_throughput))
            states, masks = res.user_states, res.action_masks
            enc = encode(states, t + 1)
            if res.done:
                break
        rows.append(row)
    bits = joules = beams_total = 0.0
    for r in rows:
        bits += r["bits"]
        joules += r["joules"]
        beams_total += r["beams"]
    us = sum(r["user_steps"] for r in rows)
    out_d = {
        "bits": bits,
        "joules": joules,
        "ee": bits / joules,
        "h_inter": sum(r["h_inter"] for r in rows) / us,
        "h_intra": sum(r["h_intra"] for r in rows) / us,
        "served": sum(r["served"] for r in rows) / us,
        "beams": beams_total / sum(r["steps"] for r in rows),
        "user_steps": us,
        "ee_ep": [r["bits"] / r["joules"] if r["joules"] > 0 else float("nan") for r in rows],
        "n_episodes": len(rows),
        "episodes": rows,
    }
    out_d.update(_rate_stats(rates))
    out_d["ho_per_user_min"] = (out_d["h_inter"] + out_d["h_intra"]) * 60.0 / LP_GRID_DT_S
    if t0_agreement:
        out_d["t0_agreement"] = agree / max(decisions, 1)
        out_d["t0_score_regret"] = regret / max(decisions, 1)
        out_d["t0_decisions"] = decisions
    if xep_probe is not None:
        # Amendment 12's residual-leakage diagnostic, on the SAME states as
        # ``t0_agreement``: if T0-XEP's agreement with the real T0 sits materially
        # above ``t0xep_random_legal_agreement_expected`` (the EXACT uniform-legal
        # expectation, 1/|legal| averaged over the same decisions, no draw), the null
        # carries residual information and the measured contrast is a LOWER BOUND.
        out_d["t0xep_agreement"] = xep_agree / max(decisions, 1)
        out_d["t0xep_score_regret"] = xep_regret / max(decisions, 1)
        out_d["t0xep_random_legal_agreement_expected"] = (
            xep_random_agree / max(decisions, 1)
        )
        out_d["t0xep_decisions"] = decisions
    return out_d


# ------------------------------------------------------------------ trainer
class CFDevTrainer(CFRatioTrainer):
    """The E0 development learner: the CF-ratio learner plus a teacher mechanism."""

    def __init__(self, env, config, settings, dev: DevSettings, *,
                 env_factory=None, train_seed: int = 9_201_000,
                 env_seed: int = 9_202_000, mobility_seed: int = 9_203_000,
                 device: str = "cpu", xep_reference=None) -> None:
        lane = dev.lane
        assert_lane_seed(train_seed, f"{lane} train seed", lane=lane)
        assert_lane_seed(env_seed, f"{lane} env seed", lane=lane)
        assert_lane_seed(mobility_seed, f"{lane} mobility seed", lane=lane)
        super().__init__(env, config, settings, env_factory=env_factory, pools=None,
                         train_seed=train_seed, env_seed=env_seed,
                         mobility_seed=mobility_seed, device=device)
        if self.sources:
            raise MCRLContractError("the E0 surface runs without source pools")
        self.dev = dev
        # Replace the inherited replay with the label-carrying one (same capacity,
        # same sampling arithmetic, same generator).
        self.replay = TeacherReplayBuffer(config.replay_capacity)
        self._null_rng = (
            np.random.default_rng(dev.null_key) if dev.null_key is not None else None
        )
        self._xep_ref = self._bind_xep_reference(xep_reference)
        self._last_teacher_loss: float = 0.0
        self._teacher_updates: int = 0

    def _bind_xep_reference(self, reference):
        """Bind the ONE fixed reference trajectory, or refuse.

        Amendment 12 section 2: the reference is recorded once, before the first S1
        run, and may not be regenerated.  It is therefore bound here, ONCE, for the
        lifetime of the trainer -- never inside an episode -- and it must be the
        reference the configuration declares.
        """
        if self.dev.mechanism != "D3-XEP":
            if reference is not None:
                raise MCRLContractError(
                    "only D3-XEP takes a T0-XEP reference trajectory"
                )
            return None
        if reference is None:
            raise MCRLContractError(
                "D3-XEP needs its pre-recorded reference trajectory "
                "(cf_xep.load_reference)"
            )
        d = self.dev
        if reference.sha256 != d.xep_reference_sha256:
            raise MCRLContractError(
                f"the loaded T0-XEP reference is {reference.sha256}, the configuration "
                f"declares {d.xep_reference_sha256}"
            )
        if tuple(reference.key) != tuple(d.xep_reference_key):
            raise MCRLContractError(
                f"the T0-XEP reference was rolled on {reference.key}, the configuration "
                f"declares {tuple(d.xep_reference_key)}"
            )
        if reference.policy != d.xep_reference_policy:
            raise MCRLContractError(
                f"the T0-XEP reference policy is {reference.policy!r}, the configuration "
                f"declares {d.xep_reference_policy!r}"
            )
        if reference.users != self.num_users:
            raise MCRLContractError(
                f"the T0-XEP reference has {reference.users} users, this environment "
                f"has {self.num_users}"
            )
        if reference.steps < self.env.config.steps_per_episode:
            raise MCRLContractError(
                f"the T0-XEP reference is {reference.steps} steps, the episode is "
                f"{self.env.config.steps_per_episode}"
            )
        return reference

    @property
    def xep_reference_sha256(self) -> str | None:
        """The bound reference's sha256 -- the null key of the second null."""
        return None if self._xep_ref is None else self._xep_ref.sha256

    # -- the formal sets are out of bounds ------------------------------
    def measure_on_calibration(self):  # noqa: D102
        raise MCRLContractError(
            "development runs may not read the calibration episodes (Amendment 6 section 3)"
        )

    def quarter_update(self, episode_done: int, *, final: bool = False):  # noqa: D102
        raise MCRLContractError(
            "E0 holds eta at eta_0 and lambda at 0: there is no quarter update"
        )

    # -- teacher --------------------------------------------------------
    def teacher_labels(self, states, masks, *, step: int | None = None):
        """``(t0_action, teacher_action, teacher_scores, legal, t0_scores)``.

        T0's scores and action come from the RAW user state.  ``D2-null`` permutes
        the score vector among that state's legal actions with the DEV-NULL
        generator (one permutation per state, at collection time) and re-derives
        the teacher action from the permuted vector, so no T0 action information
        survives in anything the null's loss reads.  ``D3-XEP`` scores the FIXED
        reference episode's state at the same step ``step`` and takes its argmax over
        the CURRENT legal mask.  ``t0_scores`` is returned for the episode diagnostics
        only (never stored in the loss inputs).
        """
        scores, t0_acts, legal = cft.t0_scores(states, masks)
        if self.dev.mechanism == "D2-null":
            used = cft.permute_scores_among_legal(scores, legal, self._null_rng)
            used_acts = cft.masked_argmax_rows(used, legal)
        elif self.dev.mechanism == "D3-null":
            # The margin loss reads ONLY the action, so the null replaces the action
            # with a seeded uniform legal draw and stores NO T0 quantity at all: the
            # scores it carries are zeros.
            used = np.zeros_like(scores)
            used_acts = cft.random_legal_actions(legal, self._null_rng)
        elif self.dev.mechanism == "D3-XEP":
            if step is None:
                raise MCRLContractError(
                    "D3-XEP labels are step-indexed: step t of the learner's episode "
                    "is matched to step t of the fixed reference episode"
                )
            used, used_acts = cft.t0_xep_labels(self._xep_ref.states_at(step), legal)
        else:
            used, used_acts = scores, t0_acts
        return t0_acts, used_acts, used, legal, scores

    def _assemble_batch(self):
        batch = super()._assemble_batch()
        if batch is None:
            return None
        labels = self.replay.last_teacher()
        if len(labels["teacher_action"]) != len(batch["actions"]):
            raise MCRLContractError("teacher labels are not aligned with the batch")
        batch.update(masks=labels["masks"], t0_action=labels["t0_action"],
                     teacher_action=labels["teacher_action"],
                     teacher_scores=labels["teacher_scores"])
        return batch

    def _teacher_loss(self, batch, q_all) -> torch.Tensor | None:
        """The weighted teacher loss on the replay minibatch (student states)."""
        d = self.dev
        if not d.uses_teacher:
            return None
        mask = torch.tensor(np.asarray(batch["masks"], dtype=bool),
                            dtype=torch.bool, device=self.device)
        scores = cft.student_scores(q_all[HEAD_B], q_all[HEAD_E], q_all[HEAD_H],
                                    self.eta_tilde, self.lam)
        if d.mechanism in ("D2-T0", "D2-null"):
            target = cft.soft_targets(batch["teacher_scores"], batch["masks"], d.tau)
            p = torch.tensor(target, dtype=torch.float32, device=self.device)
            return d.alpha * cft.d2_ce_loss(scores, mask, p, d.tau_s)
        if d.mechanism in ("D3-T0", "D3-null", "D3-XEP"):
            a_t = torch.tensor(np.asarray(batch["teacher_action"], dtype=np.int64),
                               dtype=torch.long, device=self.device)
            return d.lambda_e * cft.d3_margin_loss(scores, mask, a_t, d.margin)
        raise MCRLContractError(f"no teacher loss for mechanism {d.mechanism!r}")

    def update(self) -> tuple[float, float, float]:
        """One update.  ``D0`` is the inherited CF-ratio update, untouched."""
        if not self.dev.uses_teacher:
            self._last_teacher_loss = 0.0
            return super().update()
        batch = self._assemble_batch()
        self._last_batch = batch
        if batch is None:
            self._last_teacher_loss = 0.0
            return (0.0, 0.0, 0.0)
        st = torch.tensor(batch["states"], dtype=torch.float32, device=self.device)
        act = torch.tensor(batch["actions"], dtype=torch.long,
                           device=self.device).unsqueeze(1)
        targets = [self.head_targets(batch, head) for head in range(3)]
        q_all = [self.q_nets[head](st) for head in range(3)]
        td_losses = []
        for head in range(3):
            q_current = q_all[head].gather(1, act).squeeze(1)
            loss = self._loss_fn(q_current, targets[head])
            assert_finite_loss(loss, objective=head)
            td_losses.append(loss)
        teacher_loss = self._teacher_loss(batch, q_all)
        assert_finite_loss(teacher_loss, objective=HEAD_B)
        total = td_losses[0] + td_losses[1] + td_losses[2] + teacher_loss
        for opt in self.optimizers:
            opt.zero_grad()
        total.backward()
        for head in range(3):
            assert_finite_gradients(self.q_nets[head].parameters(), objective=head)
            self.optimizers[head].step()
        assert_finite_parameters(self.q_nets)
        self._last_teacher_loss = float(teacher_loss.item())
        self._teacher_updates += 1
        return tuple(float(x.item()) for x in td_losses)

    # -- DEVVAL ---------------------------------------------------------
    def devval_seeds(self) -> list[tuple[int, int]]:
        """The lane's evaluation episodes: DEVVAL, or S1's formal evaluation set."""
        d = self.dev
        seeds = episode_seeds(d.devval_env_base, d.devval_mobility_base,
                              d.devval_episodes)
        assert_lane_seed_pairs(seeds, f"{d.lane} evaluation", lane=d.lane)
        return seeds

    def xep_probe(self):
        """The read-only ``T0-XEP`` observer for DEVVAL, or ``None``.

        It advises; it never acts.  It reads the SAME fixed reference trajectory the
        loss uses, at the same step index, so what DEVVAL reports is the agreement of
        the teacher actually in the loss with the real T0.
        """
        if self._xep_ref is None:
            return None

        def probe(legal, step):
            return cft.t0_xep_labels(self._xep_ref.states_at(step), legal)[1]

        return probe

    def devval(self) -> dict[str, Any]:
        """Greedy deployed rule on the DEVVAL episodes.  Consumes no training RNG."""
        if self._env_factory is None:
            raise MCRLContractError("DEVVAL needs an env_factory")
        greedy = lambda enc, masks, states: self.greedy_actions(enc, masks)  # noqa: E731
        res = dev_rollout(lambda i: greedy, env_factory=self._env_factory,
                          encode=self.encode_at, seeds=self.devval_seeds(),
                          t0_agreement=True, xep_probe=self.xep_probe(),
                          lane=self.dev.lane)
        if self._xep_ref is not None:
            res["xep_reference"] = self._xep_ref.identity()
        return res

    # -- training loop ---------------------------------------------------
    def train_cf(self, *, start_episode: int = 0, initial_logs: list[dict] | None = None,
                 episode_callback: Callable[[dict], None] | None = None,
                 progress_every: int = 50) -> list[dict]:
        """``CFRatioTrainer.train_cf`` with teacher labels and no quarter update.

        Everything else -- the epsilon schedule, the P-03 filter, one update per
        decision step, the target sync, the credit dispatch, the episode log -- is
        the pilot loop unchanged; ``tests/test_cf_dev.py`` asserts that a ``D0``
        development run reproduces the pilot A1 learner bit-identically.
        """
        cfg, s, d = self.config, self.settings, self.dev
        logs = list(initial_logs or [])
        if len(logs) != start_episode or any(
            row["episode"] != i for i, row in enumerate(logs)
        ):
            raise MCRLContractError("initial_logs must be episodes 0..start-1")
        users = self.num_users
        for ep in range(start_episode, cfg.episodes):
            eps = self.epsilon(ep)
            eta_ep, lam_ep = self.eta, self.lam
            states, masks, _ = self.env.reset(self._env_rng, self._mobility_rng)
            t = 0
            encoded = self.encode_at(states, t)
            tot = np.zeros(3)
            served = h_intra = outages = 0
            beams = 0.0
            ep_losses = np.zeros(3)
            teacher_loss_sum = 0.0
            n_upd = 0
            n_steps = 0
            sys_bits = sys_joules = 0.0
            t0_greedy_agree = t0_behaviour_agree = 0.0
            t0_greedy_regret = 0.0
            used_agree_t0 = used_regret_t0 = random_agree_t0 = 0.0
            t0_decisions = 0
            for _t in range(self.env.config.steps_per_episode):
                actions = self.select_actions(encoded, masks, eps)
                (t0_acts, used_acts, used_scores, legal,
                 t0_scores_raw) = self.teacher_labels(states, masks, step=_t)
                greedy = self.greedy_actions(encoded, masks)   # diagnostic, no RNG
                for u in range(users):
                    if not bool(legal[u].any()):
                        continue
                    t0_decisions += 1
                    t0_greedy_agree += float(int(greedy[u]) == int(t0_acts[u]))
                    t0_behaviour_agree += float(int(actions[u]) == int(t0_acts[u]))
                    # Residual-leakage diagnostics (Amendment 12): how much of the
                    # REAL T0 the teacher actually in the loss reproduces, against
                    # the exact uniform-random-legal expectation on the same rows.
                    used_agree_t0 += float(int(used_acts[u]) == int(t0_acts[u]))
                    random_agree_t0 += 1.0 / float(int(legal[u].sum()))
                    if 0 <= int(used_acts[u]) < t0_scores_raw.shape[1]:
                        used_regret_t0 += float(
                            t0_scores_raw[u, int(t0_acts[u])]
                            - t0_scores_raw[u, int(used_acts[u])]
                        )
                    if 0 <= int(greedy[u]) < t0_scores_raw.shape[1]:
                        t0_greedy_regret += float(
                            t0_scores_raw[u, int(t0_acts[u])]
                            - t0_scores_raw[u, int(greedy[u])]
                        )
                ctx = (difference_context(self.env, actions, masks, self._env_rng,
                                          model=self._power_model)
                       if s.credit_mode == "difference" else None)
                result = self.env.step(actions, self._env_rng)
                outcome = self.env.last_outcome
                if s.credit_mode == DEFAULT_CREDIT_MODE:
                    raw = cf_reward_matrix(result, outcome)
                else:
                    raw = credit_matrix(s.credit_mode, result, outcome,
                                        model=self._power_model, ctx=ctx)
                    sys_bits += float(outcome.energy.system_throughput_bps) * DT_S
                    sys_joules += float(outcome.energy.system_consumed_power_w) * DT_S
                tot += raw.sum(axis=0)
                served += int(outcome.energy.served)
                beams += float(outcome.energy.eff_beams)
                h_intra += sum(
                    int(c is HandoverClass.INTRA_SATELLITE) for c in outcome.handovers
                )
                outages += int(sum(1 for x in result.served if not x))
                n_steps += 1
                t += 1
                next_encoded = self.encode_at(result.user_states, t)
                for uid in range(users):
                    self._decision_steps_seen += 1
                    if is_no_op(int(actions[uid])):
                        self._no_op_transitions_skipped += 1
                        continue
                    next_mask = result.action_masks[uid].mask
                    if not bool(result.done) and not bool(next_mask.any()):
                        self._all_invalid_next_transitions_skipped += 1
                        continue
                    self.replay.push_labeled(
                        encoded[uid], int(actions[uid]), raw[uid].copy(),
                        next_encoded[uid], masks[uid].mask.copy(),
                        next_mask.copy(), bool(result.done),
                        t0_action=int(t0_acts[uid]),
                        teacher_action=int(used_acts[uid]),
                        teacher_scores=used_scores[uid],
                    )
                step_losses = self.update()
                if self._last_batch is not None:
                    ep_losses += step_losses
                    teacher_loss_sum += self._last_teacher_loss
                    n_upd += 1
                states, masks, encoded = (
                    result.user_states, result.action_masks, next_encoded
                )
                if result.done:
                    break
            if (ep + 1) % cfg.target_update_every_episodes == 0:
                self.sync_targets()
            us = n_steps * users
            norm = tot / self._units / us
            log = {
                "episode": ep,
                "epsilon": eps,
                "eta": eta_ep,
                "lambda": lam_ep,
                "eta_tilde": eta_ep * s.joules_scale / s.bits_scale,
                "bits": float(tot[HEAD_B]),
                "joules": float(tot[HEAD_E]),
                "ee_behaviour": float(tot[HEAD_B] / tot[HEAD_E]),
                "h_inter": float(tot[HEAD_H] / us),
                "h_intra": h_intra / us,
                "served": served / us,
                "beams": beams / n_steps,
                "outage_user_steps": outages,
                "head_reward_means_normalised": [float(x) for x in norm],
                "objective_per_user_step": float(
                    norm[HEAD_B] - (eta_ep * s.joules_scale / s.bits_scale) * norm[HEAD_E]
                    - lam_ep * norm[HEAD_H]
                ),
                "losses": [float(x) for x in (ep_losses / max(n_upd, 1))],
                "updates": n_upd,
                "replay_size": len(self.replay),
                "mechanism": d.mechanism,
                "teacher": d.teacher,
                "teacher_loss": float(teacher_loss_sum / max(n_upd, 1)),
                "t0_agree_greedy": float(t0_greedy_agree / max(t0_decisions, 1)),
                "t0_agree_behaviour": float(t0_behaviour_agree / max(t0_decisions, 1)),
                "t0_score_regret_greedy": float(t0_greedy_regret / max(t0_decisions, 1)),
                "teacher_action_agrees_with_t0": float(used_agree_t0 / max(t0_decisions, 1)),
                "teacher_action_t0_score_regret": float(
                    used_regret_t0 / max(t0_decisions, 1)
                ),
                "random_legal_agrees_with_t0_expected": float(
                    random_agree_t0 / max(t0_decisions, 1)
                ),
                "t0_decisions": t0_decisions,
            }
            if d.mechanism == "D3-XEP":
                log["xep_reference_sha256"] = self.xep_reference_sha256
            if s.credit_mode != DEFAULT_CREDIT_MODE:
                log.update(bits=sys_bits, joules=sys_joules,
                           ee_behaviour=sys_bits / sys_joules,
                           credit_mode=s.credit_mode,
                           credit_sums=[float(x) for x in tot])
            for k, v in log.items():
                if isinstance(v, float) and not np.isfinite(v):
                    raise FloatingPointError(f"non-finite {k} in episode {ep}")
            logs.append(log)
            if episode_callback is not None:
                episode_callback(log)
            if progress_every and (ep + 1) % progress_every == 0:
                print(
                    f"[ep {ep + 1:5d}/{cfg.episodes}] {d.mechanism} eps={eps:.3f} "
                    f"ee_beh={log['ee_behaviour']:.4e} served={log['served']:.4f} "
                    f"loss={log['losses'][0]:.3e},{log['losses'][1]:.3e},{log['losses'][2]:.3e} "
                    f"teach={log['teacher_loss']:.3e} agreeT0={log['t0_agree_greedy']:.3f} "
                    f"buf={len(self.replay)}",
                    flush=True,
                )
        return logs

    # -- persistence -----------------------------------------------------
    def training_state_dict(self) -> dict[str, Any]:
        state = super().training_state_dict()
        state["dev"] = {
            "settings": dataclasses.asdict(self.dev),
            "null_rng": (None if self._null_rng is None
                         else copy.deepcopy(self._null_rng.bit_generator.state)),
            "teacher_updates": int(self._teacher_updates),
            "xep_reference_sha256": self.xep_reference_sha256,
        }
        return state

    def load_training_state_dict(self, state) -> None:
        dev = state.get("dev")
        if not isinstance(dev, Mapping):
            raise MCRLContractError("resume state carries no development block")
        if dev["settings"] != dataclasses.asdict(self.dev):
            raise MCRLContractError("resume state development settings do not match")
        super().load_training_state_dict(state)
        if (dev["null_rng"] is None) != (self._null_rng is None):
            raise MCRLContractError("resume state DEV-NULL generator does not match")
        if self._null_rng is not None:
            self._null_rng.bit_generator.state = copy.deepcopy(dev["null_rng"])
        if dev.get("xep_reference_sha256") != self.xep_reference_sha256:
            raise MCRLContractError(
                "resume state was written against a different T0-XEP reference "
                f"({dev.get('xep_reference_sha256')} vs {self.xep_reference_sha256})"
            )
        self._teacher_updates = int(dev["teacher_updates"])

    def policy_payload(self, episode: int) -> dict[str, Any]:
        payload = super().policy_payload(episode)
        payload["schema"] = "cf-dev-policy-v1"
        payload["dev_settings"] = dataclasses.asdict(self.dev)
        return payload

    def load_policy(self, path):  # noqa: D102
        payload = torch.load(path, map_location="cpu", weights_only=False)
        if payload.get("schema") != "cf-dev-policy-v1":
            raise MCRLContractError("not a cf-dev policy checkpoint")
        for net, sd in zip(self.q_nets, payload["q_networks"]):
            net.load_state_dict(sd)
        for net, sd in zip(self.target_nets, payload["target_networks"]):
            net.load_state_dict(sd)
        self.eta = float(payload["eta"])
        self.lam = float(payload["lambda"])
        return payload


def dev_settings_from_payload(payload: Mapping[str, Any]) -> DevSettings:
    raw = dict(payload["dev_settings"])
    if raw.get("null_key") is not None:
        raw["null_key"] = tuple(int(x) for x in raw["null_key"])
    return DevSettings(**raw)
