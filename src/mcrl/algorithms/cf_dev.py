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
* the mechanisms ``D0`` / ``D2-T0`` / ``D2-null`` / ``D3-T0`` / ``D3-null``, and the
  generic N-teacher set-valued ``D3-multi`` with its matched ``D3-multi-null``
  (Amendment 15 section 6; see :class:`MultiD3Spec` and
  :func:`mcrl.algorithms.cf_teacher.d3_set_margin_loss`).  With one teacher the
  multi path is bit-identical to ``D3-T0`` -- loss tensor AND gradient -- and it
  changes no inference or deployment path: a deployed policy is still the three Q
  networks and ``eta``, and no teacher source has to exist to run it;
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
from . import cf_judge as cfj
from . import cf_s1_lane as s1l
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
    (9_251_000, 9_253_999, "S1-TRAIN triples"),
    (9_261_000, 9_261_999, "S1-NULL"),
    (9_263_000, 9_263_999, "S1-NULL-MC2 (the formal B-null stream)"),
)
"""Amendment 6 section 3: no development path may produce any of these.  The S1
namespaces (Amendment 13) were already refused as undeclared; the MC2 contract
section 6 names them, so they are refused by name as well."""

ALLOWED_SEED_RANGES: tuple[tuple[int, int, str], ...] = (
    (9_201_000, 9_201_999, "DEV train"),
    (9_202_000, 9_202_999, "DEV env"),
    (9_203_000, 9_203_999, "DEV mobility"),
    (9_211_000, 9_211_999, "DEVVAL env"),
    (9_212_000, 9_212_999, "DEVVAL mobility"),
    (9_221_000, 9_221_999, "DEVVAL RANDOM draws"),
    (9_231_000, 9_231_999, "DEV-NULL D2 permutations"),
    (9_241_000, 9_241_999, "DEV-NULL D3/D4 random actions"),
    (9_243_000, 9_243_999, "DEV-NULL MC2 proposal-replacement uniform legal actions"),
    (9_271_000, 9_271_999, "derived: train + 70_001 (catfish sampling)"),
    (9_281_000, 9_281_999, "derived: train + 80_000 + k (NULL sources)"),
    (9_291_000, 9_291_999, "derived: train + 90_211 (inherited penalty generator)"),
)
"""The only seed values a development run may construct (Amendment 6 section 3)."""


DEV_NULL_KEY_BASES: tuple[int, ...] = (9_231_000, 9_241_000, 9_243_000)
"""Amendment 6 section 3: the DEV-NULL generators are the COMPOSITE identities
``default_rng((9_231_000, k))`` (D2-null permutations) and
``default_rng((9_241_000, k))`` (D3/D4-null random actions); MC2 contract section 6
adds ``default_rng((9_243_000, k))`` (the B-null's proposal replacement)."""

MAX_DEV_SEED_INDEX: int = 19
"""DEV triples are declared for k = 0..19 (MC2 contract section 6 raised 9 -> 19:
selection k = 10, 11; confirmation 12-14; reserve 15-17; k = 9 stays unused), so a
DEV-NULL key's index is one of those."""


def _null_generator(key) -> np.random.Generator:
    """A FRESH DEV-NULL generator at the declared composite identity ``(base, k)``.

    One arm, one stream: nothing is cached and no state is shared between arms, so
    an arm's null draws are a function of its own declared key alone.  (Pattern
    taken from the closed ``TDELTA-CANARY-PREP`` lane, commit ``ef8c866f``.)
    """
    return np.random.default_rng(key)


D3_MECHANISMS: tuple[str, ...] = ("D3-T0", "D3-null")
"""Every mechanism carried by the SAME single-action unconditional large-margin
loss.  Adding a teacher identity here must never change the loss, the margin or
the weight -- only which legal action ``a_T`` points at.  (Pattern taken from the
closed ``TDELTA-CANARY-PREP`` lane; ``D3-T_DELTA`` is not carried over, T_DELTA
being closed by adjudication ``f747de86``.)"""

EXPECTED_TEACHER: dict[str, str] = {
    "D0": "none",
    "D3-null": "random",
    "D3-multi": "multi",
    "D3-multi-null": "random-set",
    cfj.MECHANISM_NAME: "judge",
}
"""Mechanism -> the only teacher label it may carry (default: ``T0``)."""

JUDGE_MECHANISMS: tuple[str, ...] = (cfj.MECHANISM_NAME,)
"""The MC2 judge arm's mechanism (``MC2``, arm 10).  Its identity -- versioned rule
id (``MC2-JGO-v1`` / ``MC2-ARB-v2`` / the rule-independent shared B-only), source
set, judge id + eta0, null id + key -- lives in :class:`JudgeSpec`, never in
:class:`DevSettings`, so no field of the single-teacher arms changes."""

ALL_MECHANISMS: tuple[str, ...] = cft.MECHANISMS + JUDGE_MECHANISMS
ALL_TEACHERS: tuple[str, ...] = cft.TEACHERS + ("judge",)

NULL_BASE_FOR: dict[str, int] = {
    "D2-null": 9_231_000,
    "D3-null": 9_241_000,
    "D3-multi-null": 9_241_000,
}
"""Mechanism -> its declared DEV-NULL namespace (Amendment 6 section 3).

The set-valued null draws from the same declared D3/D4 random-action namespace as
the one-action ``D3-null``; the two are told apart by the mechanism identity and by
``MultiD3Spec.null_id``, both of which are in the configuration hash.
"""


def assert_dev_null_key(key: Any, what: str = "") -> tuple[int, int]:
    """Validate a COMPOSITE DEV-NULL generator identity ``(base, k)``.

    The pair is ONE declared generator identity, not two seeds: the base must be a
    declared DEV-NULL namespace and ``k`` a legal development seed index
    (``0 <= k <= MAX_DEV_SEED_INDEX``); the index is never checked as though it were a standalone
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


# ------------------------------------------------------------------ lanes
DEV_LANE: str = s1l.DEV_LANE
"""This kernel's own lane.  A settings object without a ``lane`` attribute IS the
development lane: :class:`DevSettings` has no such field, so adding the S1 lane
(:mod:`mcrl.algorithms.cf_s1`) changed no development configuration hash."""


def lane_of(dev: Any) -> str:
    """The seed contract a settings object runs under (default: development)."""
    return str(getattr(dev, "lane", DEV_LANE))


def assert_lane_seed(seed: Any, what: str = "", *, lane: str = DEV_LANE) -> int:
    """Dispatch to the lane's seed guard, fail closed on an unknown lane.

    ``assert_dev_seed`` stays the DEVELOPMENT entry point (so a test or mutant that
    neutralises it still neutralises the development path); every other lane is
    guarded by :mod:`mcrl.algorithms.cf_s1_lane`.
    """
    if lane == DEV_LANE:
        return assert_dev_seed(seed, what)
    return s1l.assert_lane_seed(seed, what, lane=lane)


def assert_lane_seed_pairs(seeds: Sequence[tuple[int, int]], what: str = "", *,
                           lane: str = DEV_LANE) -> None:
    if lane == DEV_LANE:
        assert_dev_seed_pairs(seeds, what)
        return
    s1l.assert_lane_seed_pairs(seeds, what, lane=lane)


# ------------------------------------------------------------------ MULTI-D3
@dataclass(frozen=True)
class MultiD3Spec:
    """Identity of a generic N-teacher set-valued MULTI-D3 arm or its matched null.

    Amendment 15 section 6.  Everything the mechanism's identity depends on lives
    here and nowhere else, so that :func:`dev_e0_common.arm_config_payload` can put
    all of it in the configuration hash: the versioned mechanism identity, the
    CANONICAL teacher set (sorted, duplicate-free -- ``{T0,Ti}`` and ``{Ti,T0}`` are
    the same configuration), and, for the matched null, the null's own rule identity
    and its cardinality.  The margin ``m`` and the weight ``lambda_E`` are NOT here:
    they stay in :class:`DevSettings`, frozen and unchanged at ``0.15`` and ``1.0``.

    A ``FULL`` arm names its teachers.  A matched ``2-null`` names no teacher at all
    -- it is matched to a CARDINALITY, not to an identity, which is exactly why one
    physical ``n = 2`` null run is shared by every two-teacher candidate
    (Amendment 15 section 7, "shared arms are physically run once").
    """

    mechanism_id: str = cft.MULTI_MECHANISM_ID
    teachers: tuple[str, ...] = ()
    n_proposals: int = 0
    null_id: str | None = None
    p_singleton: float | None = None
    p_singleton_numerator: int | None = None
    p_singleton_denominator: int | None = None
    p_singleton_rational: str | None = None
    p_singleton_source: str | None = None
    """Provenance of the frozen marginal: the source identity and the P0 artefact
    digest it was counted on.  It is in the configuration hash so that a run can
    never be re-read as though a different collection had produced the number."""

    def __post_init__(self) -> None:
        if self.mechanism_id != cft.MULTI_MECHANISM_ID:
            raise MCRLContractError(
                f"unknown MULTI-D3 mechanism identity {self.mechanism_id!r}; the "
                f"declared mechanism is {cft.MULTI_MECHANISM_ID!r}"
            )
        if self.null_id is None:
            if not self.teachers:
                raise MCRLContractError("a FULL MULTI-D3 arm must name its teachers")
            if tuple(self.teachers) != cft.canonical_teacher_set(self.teachers):
                raise MCRLContractError(
                    f"teacher set {tuple(self.teachers)} is not canonical; use "
                    "cft.canonical_teacher_set()"
                )
            if int(self.n_proposals) != 0:
                raise MCRLContractError("only the matched null carries n_proposals")
            if any(x is not None for x in (self.p_singleton,
                                           self.p_singleton_numerator,
                                           self.p_singleton_denominator,
                                           self.p_singleton_rational,
                                           self.p_singleton_source)):
                raise MCRLContractError("only a matched null carries p_singleton")
        else:
            if self.null_id not in (cft.MULTI_NULL_ID, cft.MULTI_NULL_BERNOULLI_ID):
                raise MCRLContractError(
                    f"unknown matched-null identity {self.null_id!r}; the declared "
                    f"rule is {cft.MULTI_NULL_ID!r}"
                )
            if (self.p_singleton is None) != (self.null_id == cft.MULTI_NULL_ID):
                raise MCRLContractError(
                    f"{cft.MULTI_NULL_BERNOULLI_ID!r} needs its declared p_singleton "
                    f"and {cft.MULTI_NULL_ID!r} must not carry one"
                )
            if self.p_singleton is not None:
                if not 0.0 <= float(self.p_singleton) <= 1.0:
                    raise MCRLContractError("p_singleton must be a probability")
                num, den = self.p_singleton_numerator, self.p_singleton_denominator
                if num is None or den is None or int(den) <= 0:
                    raise MCRLContractError(
                        "the Bernoulli-matched null's p_singleton must be frozen as an "
                        "exact numerator / denominator, not only as a float"
                    )
                if float(self.p_singleton) != int(num) / int(den):
                    raise MCRLContractError(
                        f"p_singleton {self.p_singleton!r} is not {num}/{den}"
                    )
                if self.p_singleton_rational != f"{int(num)}/{int(den)}":
                    raise MCRLContractError(
                        f"p_singleton_rational must be '{int(num)}/{int(den)}'"
                    )
                if not self.p_singleton_source:
                    raise MCRLContractError(
                        "p_singleton must carry the source identity and the P0 "
                        "artefact digest it was counted on"
                    )
            elif any(x is not None for x in (self.p_singleton_numerator,
                                             self.p_singleton_denominator,
                                             self.p_singleton_rational,
                                             self.p_singleton_source)):
                raise MCRLContractError(
                    "p_singleton provenance without a p_singleton"
                )
            if self.teachers:
                raise MCRLContractError(
                    "the matched set-valued null names no teacher: it is matched to a "
                    "CARDINALITY, so that one null run is shared across candidates"
                )
            if int(self.n_proposals) < 1:
                raise MCRLContractError("the matched null needs n_proposals >= 1")

    @property
    def is_null(self) -> bool:
        return self.null_id is not None

    @property
    def n_slots(self) -> int:
        """Proposals per state: one per teacher, or the null's declared cardinality."""
        return int(self.n_proposals) if self.is_null else len(self.teachers)

    @property
    def mechanism(self) -> str:
        return "D3-multi-null" if self.is_null else "D3-multi"

    @property
    def is_bernoulli_null(self) -> bool:
        return self.null_id == cft.MULTI_NULL_BERNOULLI_ID

    def label(self) -> str:
        """Short run-directory tag: the teacher set, or the null's identity.

        The two nulls MUST NOT collide: the Bernoulli-matched null carries its
        exact frozen ``p_singleton`` in the tag as well as in the hash, so its
        run directory, manifest key and config hash are all distinct from the
        rejected fixed two-proposal null's (controller record ``716f104e`` section 4).
        """
        if not self.is_null:
            return "+".join(self.teachers)
        if self.is_bernoulli_null:
            return (f"n{self.n_proposals}-bernoulli-"
                    f"p{self.p_singleton_numerator}_{self.p_singleton_denominator}")
        return f"n{self.n_proposals}"


def multi_spec_from_payload(payload: Mapping[str, Any] | None) -> MultiD3Spec | None:
    if payload is None:
        return None
    raw = dict(payload)
    raw["teachers"] = tuple(str(x) for x in raw.get("teachers", ()))
    return MultiD3Spec(**raw)


# ------------------------------------------------------------------ MC2 judge arms
@dataclass(frozen=True)
class JudgeSpec:
    """Identity of one MC2 judge-gated cell (contract r1 sections 1-3, 5 item 7, 6).

    Everything the cell's identity depends on lives here so that
    ``dev_e0_common.arm_config_payload`` can hash all of it: the versioned RULE id
    (``MC2-JGO-v1``, ``MC2-ARB-v2``, or the rule-independent
    ``MC2-B-ONLY-SHARED-v1``), the CANONICAL source set, the source identities,
    the judge id + its frozen ``eta0``, and, for a B-null, the null's rule id and
    its composite DEV-NULL key ``(9_243_000, k)``.  The margin ``m`` and
    ``lambda_E`` stay in :class:`DevSettings`, frozen at ``0.15`` and ``1.0``.

    Declared cells (``cfj.DECLARED_CELLS``): v1 ``{A,B}``, ``{A,R}``; v2 ``{A}``,
    ``{A,B}``, ``{A,R}``; shared ``{B}``.  ``A-only-v1`` is refused (it IS arm 4,
    ``D3-T0``), and ``{B}`` exists only under the rule-independent shared id.
    """

    mechanism_id: str = cfj.JGO_MECHANISM_ID
    sources: tuple[str, ...] = ()
    source_a: str | None = None
    source_b: str | None = None
    judge_id: str = cfj.JUDGE_ID
    judge_definition: str = cfj.JUDGE_DEFINITION
    judge_eta0: float = cfj.ETA0_JUDGE
    null_id: str | None = None
    null_key: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        if self.mechanism_id not in cfj.DECLARED_CELLS:
            raise MCRLContractError(
                f"unknown MC2 rule identity {self.mechanism_id!r}; declared: "
                f"{tuple(cfj.DECLARED_CELLS)}"
            )
        srcs = tuple(str(s) for s in self.sources)
        if srcs not in cfj.DECLARED_CELLS[self.mechanism_id]:
            raise MCRLContractError(
                f"source set {srcs} is not a declared {self.mechanism_id} cell "
                f"{cfj.DECLARED_CELLS[self.mechanism_id]} (canonical order; A-only-v1 "
                "is arm 4; {B} is the shared cell)"
            )
        if ("A" in srcs) != (self.source_a is not None) or self.source_a not in (
                None, cfj.SOURCE_A_ID):
            raise MCRLContractError(f"Catfish-A must be {cfj.SOURCE_A_ID!r} iff A is enabled")
        if ("B" in srcs) != (self.source_b is not None) or self.source_b not in (
                None, cfj.SOURCE_B_ID):
            raise MCRLContractError(f"Catfish-B must be {cfj.SOURCE_B_ID!r} iff B is enabled")
        if self.judge_id != cfj.JUDGE_ID or self.judge_definition != cfj.JUDGE_DEFINITION:
            raise MCRLContractError("the judge identity is frozen: MC2-KAPPA-LEX-v1")
        if float(self.judge_eta0) != cfj.ETA0_JUDGE:
            raise MCRLContractError(
                f"the judge price is frozen at eta0 = {cfj.ETA0_JUDGE!r}, not {self.judge_eta0!r}"
            )
        if "R" in srcs:
            if self.null_id != cfj.NULL_ID or self.null_key is None:
                raise MCRLContractError(
                    f"the B-null needs null_id {cfj.NULL_ID!r} and its key (9_243_000, k)"
                )
            # The B-null's stream is a LANE fact: the development screen draws from
            # (9_243_000, k), the formal screen from (9_263_000, k) -- a development
            # stream may not be reused at S1 (Amendment 13 section 5).  Each base is
            # validated by its own lane's guard, and the TRAINER additionally refuses
            # a key from the other lane (see CFDevTrainer.__init__), so neither lane
            # can silently draw the other's null.
            base = int(tuple(self.null_key)[0]) if isinstance(
                self.null_key, (tuple, list)) and len(self.null_key) == 2 else None
            if base == s1l.S1_NULL_MC2_BASE:
                s1l.assert_s1_null_key(self.null_key, "MC2 B-null key (S1 lane)",
                                       base=s1l.S1_NULL_MC2_BASE)
            else:
                base, _k = assert_dev_null_key(self.null_key, "MC2 B-null key")
                if base != cfj.NULL_BASE:
                    raise MCRLContractError(
                        f"the B-null draws from ({cfj.NULL_BASE}, k) in the "
                        f"development lane or ({s1l.S1_NULL_MC2_BASE}, k) at S1, "
                        f"not {self.null_key}"
                    )
        elif self.null_id is not None or self.null_key is not None:
            raise MCRLContractError("only the B-null (A+R) carries a null identity / key")

    @property
    def mechanism(self) -> str:
        return cfj.MECHANISM_NAME

    @property
    def rule(self) -> str:
        return cfj.RULE_OF[self.mechanism_id]

    @property
    def uses_a(self) -> bool:
        return "A" in self.sources

    @property
    def uses_b(self) -> bool:
        return "B" in self.sources

    @property
    def uses_r(self) -> bool:
        return "R" in self.sources

    @property
    def challenger_tag(self) -> int:
        if self.uses_b:
            return cfj.TAG_B
        if self.uses_r:
            return cfj.TAG_R
        return cfj.TAG_NONE

    def label(self) -> str:
        """Run tag: ``v1-A+B``, ``v2-A``, ... and ``B`` for the shared cell."""
        if self.mechanism_id == cfj.BONLY_MECHANISM_ID:
            return cfj.source_set_label(self.sources)
        return f"{self.rule}-{cfj.source_set_label(self.sources)}"


def judge_spec_from_payload(payload: Mapping[str, Any] | None) -> JudgeSpec | None:
    if payload is None:
        return None
    raw = dict(payload)
    raw["sources"] = tuple(str(x) for x in raw.get("sources", ()))
    if raw.get("null_key") is not None:
        raw["null_key"] = tuple(int(x) for x in raw["null_key"])
    return JudgeSpec(**raw)


# ------------------------------------------------------------------ settings
@dataclass(frozen=True)
class DevSettings:
    """The E0 development kernel's teacher settings (Amendment 6 section 6)."""

    mechanism: str = "D0"
    teacher: str = "none"          # none | T0
    alpha: float = 1.0             # D2 weight
    tau: float = 3.0               # teacher temperature (T0REPR VAL selection)
    tau_s: float = 1.0             # student temperature
    margin: float = 0.15           # D3 large margin, heads' units
    lambda_e: float = 1.0          # D3 weight (DQfD default)
    null_key: tuple[int, int] | None = None   # DEV-NULL: (9_231_000, k)
    devval_env_base: int = 9_211_000
    devval_mobility_base: int = 9_212_000
    devval_episodes: int = 24

    def __post_init__(self) -> None:
        if self.mechanism not in ALL_MECHANISMS:
            raise MCRLContractError(f"mechanism must be one of {ALL_MECHANISMS}")
        if self.teacher not in ALL_TEACHERS:
            raise MCRLContractError(f"teacher must be one of {ALL_TEACHERS}")
        expected_teacher = EXPECTED_TEACHER.get(self.mechanism, "T0")
        if self.teacher != expected_teacher:
            raise MCRLContractError(
                f"mechanism {self.mechanism!r} requires teacher {expected_teacher!r}"
            )
        null_base = NULL_BASE_FOR.get(self.mechanism)
        if null_base is None and self.null_key is not None:
            raise MCRLContractError("only the matched nulls may carry a DEV-NULL key")
        if null_base is not None:
            if self.null_key is None:
                raise MCRLContractError(
                    f"{self.mechanism} needs its DEV-NULL key ({null_base}, k)"
                )
            base, _index = assert_dev_null_key(self.null_key, f"DEV-NULL {self.mechanism} key")
            if base != null_base:
                raise MCRLContractError(
                    f"{self.mechanism} draws from ({null_base}, k), not {self.null_key}"
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
        for base in (self.devval_env_base, self.devval_mobility_base):
            assert_dev_seed(base, "DEVVAL base")

    @property
    def uses_teacher(self) -> bool:
        return self.mechanism != "D0"

    @property
    def teacher_weight(self) -> float:
        """The weight actually multiplying this mechanism's teacher loss."""
        if self.mechanism in ("D2-T0", "D2-null"):
            return float(self.alpha)
        if self.mechanism in D3_MECHANISMS + cft.MULTI_MECHANISMS + JUDGE_MECHANISMS:
            return float(self.lambda_e)
        return 0.0

    @property
    def is_multi(self) -> bool:
        return self.mechanism in cft.MULTI_MECHANISMS


# ------------------------------------------------------------------ replay
class TeacherReplayBuffer(ReplayBuffer):
    """FIFO replay that carries each transition's teacher labels.

    Three labels per transition: ``t0_action`` (T0's own action, DIAGNOSTICS ONLY
    -- no loss ever reads it), ``teacher_action`` and ``teacher_scores`` (what the
    loss sees; for ``D2-null`` the scores are T0's permuted among the legal actions
    and the action is that permuted vector's masked argmax).  Labels ride the same
    FIFO positions as the transitions and are sampled at the same indices.
    """

    _TEACHER_STATE_FORMAT_VERSION = 2

    def __init__(self, capacity: int) -> None:
        super().__init__(capacity)
        self._labels: deque[tuple[int, int, np.ndarray, np.ndarray | None]] = deque(
            maxlen=capacity
        )
        self._last: dict[str, np.ndarray] | None = None

    # -- writing --------------------------------------------------------
    def push(self, *args, **kwargs):  # noqa: D102 - fail closed
        raise MCRLContractError(
            "the development replay stores teacher labels: use push_labeled()"
        )

    def push_labeled(
        self, state, action, reward_3, next_state, mask, next_mask, done,
        *, t0_action: int, teacher_action: int, teacher_scores: np.ndarray,
        teacher_member: np.ndarray | None = None,
    ) -> None:
        mask = np.asarray(mask, dtype=bool)
        if not (0 <= int(teacher_action) < mask.size and bool(mask[int(teacher_action)])):
            raise MCRLContractError("teacher action is illegal in the stored state")
        if not (0 <= int(t0_action) < mask.size and bool(mask[int(t0_action)])):
            raise MCRLContractError("T0 action is illegal in the stored state")
        scores = np.asarray(teacher_scores, dtype=np.float64)
        if scores.shape != (mask.size,):
            raise MCRLContractError("teacher scores must be one value per action")
        member: np.ndarray | None = None
        if teacher_member is not None:
            member = np.asarray(teacher_member, dtype=bool)
            if member.shape != (mask.size,):
                raise MCRLContractError("A_CF must be one flag per action")
            if not bool(member.any()):
                raise MCRLContractError("A_CF is empty in the stored state")
            if bool((member & ~mask).any()):
                raise MCRLContractError("A_CF holds an action illegal in the stored state")
            member = member.copy()
        super().push(state, action, reward_3, next_state, mask, next_mask, done)
        self._labels.append((int(t0_action), int(teacher_action), scores.copy(), member))

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
        if any(x[3] is not None for x in labels):
            if any(x[3] is None for x in labels):
                raise MCRLContractError("some sampled transitions carry no A_CF")
            self._last["teacher_member"] = np.array(
                [x[3] for x in labels], dtype=bool
            )
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
            (int(a0), int(a1), np.array(s, copy=True),
             None if m is None else np.array(m, dtype=bool, copy=True))
            for a0, a1, s, m in self._labels
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
        restored: deque[tuple[int, int, np.ndarray, np.ndarray | None]] = deque(
            maxlen=self._capacity
        )
        for item in labels:
            a0, a1, scores, member = item
            restored.append((
                int(a0), int(a1), np.array(scores, copy=True),
                None if member is None else np.array(member, dtype=bool, copy=True),
            ))
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


def dev_rollout(
    policy_factory, *, env_factory, encode, seeds, t0_agreement: bool = False,
    lane: str = DEV_LANE,
) -> dict[str, Any]:
    """``cf_ratio.pooled_rollout`` (seeds mode) + per-user rates and T0 agreement.

    Fresh environment per episode, per-episode reseeded, plain left-to-right
    accumulation divided once -- the same estimand as every other reading in this
    project.  Consumes no trainer generator.  ``t0_agreement`` additionally scores
    the rolled policy's action against T0's on the same raw states (observation
    only; it never touches the environment or a generator).
    """
    assert_lane_seed_pairs(seeds, "dev_rollout", lane=lane)
    rows: list[dict[str, Any]] = []
    rates: list[float] = []
    agree = regret = 0.0
    decisions = 0
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
                for u in range(users):
                    if not bool(legal[u].any()):
                        continue
                    decisions += 1
                    agree += float(int(actions[u]) == int(t0_acts[u]))
                    if 0 <= int(actions[u]) < scores.shape[1]:
                        regret += float(scores[u, int(t0_acts[u])] - scores[u, int(actions[u])])
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
    return out_d


# ------------------------------------------------------------------ trainer
class CFDevTrainer(CFRatioTrainer):
    """The E0 development learner: the CF-ratio learner plus a teacher mechanism."""

    def __init__(self, env, config, settings, dev: DevSettings, *,
                 multi: MultiD3Spec | None = None,
                 judge: JudgeSpec | None = None,
                 env_factory=None, train_seed: int = 9_201_000,
                 env_seed: int = 9_202_000, mobility_seed: int = 9_203_000,
                 device: str = "cpu") -> None:
        lane = lane_of(dev)
        assert_lane_seed(train_seed, f"{lane} train seed", lane=lane)
        assert_lane_seed(env_seed, f"{lane} env seed", lane=lane)
        assert_lane_seed(mobility_seed, f"{lane} mobility seed", lane=lane)
        super().__init__(env, config, settings, env_factory=env_factory, pools=None,
                         train_seed=train_seed, env_seed=env_seed,
                         mobility_seed=mobility_seed, device=device)
        if self.sources:
            raise MCRLContractError("the E0 surface runs without source pools")
        self.dev = dev
        if dev.is_multi:
            if multi is None:
                raise MCRLContractError(
                    f"{dev.mechanism} needs its MultiD3Spec (teacher identities / "
                    "null identity go into the configuration hash)"
                )
            if multi.mechanism != dev.mechanism:
                raise MCRLContractError(
                    f"MultiD3Spec describes {multi.mechanism!r}, not {dev.mechanism!r}"
                )
        elif multi is not None:
            raise MCRLContractError(
                f"mechanism {dev.mechanism!r} is not a MULTI-D3 arm but carries a spec"
            )
        self.multi = multi
        if dev.mechanism in JUDGE_MECHANISMS:
            if judge is None:
                raise MCRLContractError(
                    f"{dev.mechanism} needs its JudgeSpec (mechanism id, source set, "
                    "judge id and null identity go into the configuration hash)"
                )
            if judge.mechanism != dev.mechanism:
                raise MCRLContractError(
                    f"JudgeSpec describes {judge.mechanism!r}, not {dev.mechanism!r}"
                )
        elif judge is not None:
            raise MCRLContractError(
                f"mechanism {dev.mechanism!r} is not an MC2 judge arm but carries a spec"
            )
        self.judge = judge
        # TRAINING-ONLY teacher-context seam.  It is built at all only when a
        # declared teacher actually asks for it, so every existing arm -- D0, D2,
        # D3-T0, D3-null and any multi arm over context-free sources -- runs the
        # historical path untouched.
        self._needs_teacher_context: bool = bool(
            (multi is not None and not multi.is_null
             and cft.any_teacher_needs_context(multi.teachers))
            or (judge is not None and judge.uses_b
                and cft.teacher_needs_context(judge.source_b))
        )
        self._teacher_context: cft.TeacherContext | None = None
        # Replace the inherited replay with the label-carrying one (same capacity,
        # same sampling arithmetic, same generator).
        self.replay = (cfj.JudgeReplayBuffer(config.replay_capacity) if judge is not None
                       else TeacherReplayBuffer(config.replay_capacity))
        self._null_rng = (
            _null_generator(dev.null_key) if dev.null_key is not None else None
        )
        # MC2 B-null: its OWN fresh stream at the declared key -- (9_243_000, k) in
        # the development lane, (9_263_000, k) at S1.  The lane's guard decides which
        # one this run may build, so a development run can never draw the formal
        # null's stream and an S1 run can never reuse the development one.
        if judge is not None and judge.uses_r:
            assert_lane_seed(judge.null_key, f"{lane} MC2 B-null key", lane=lane)
        self._judge_null_rng = (
            _null_generator(judge.null_key)
            if judge is not None and judge.uses_r else None
        )
        self._last_teacher_loss: float = 0.0
        self._teacher_updates: int = 0
        self._last_tag_stats: dict | None = None

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
    def teacher_labels(self, states, masks):
        """``(t0_action, teacher_action, teacher_scores, legal, t0_scores)``.

        T0's scores and action come from the RAW user state.  ``D2-null`` permutes
        the score vector among that state's legal actions with the DEV-NULL
        generator (one permutation per state, at collection time) and re-derives
        the teacher action from the permuted vector, so no T0 action information
        survives in anything the null's loss reads.  ``t0_scores`` is returned for
        the episode diagnostics only (never stored in the loss inputs).
        """
        return self.teacher_labels_ext(states, masks)[:5]

    def teacher_labels_ext(self, states, masks):
        """:meth:`teacher_labels` plus ``(A_CF membership, teacher slot actions)``.

        The last two are ``None`` for every single-teacher mechanism, so the
        single-teacher path through this method is the frozen one statement for
        statement.  For a MULTI-D3 arm:

        * ``D3-multi`` asks each declared teacher source for its action on THIS raw
          state and builds ``A_CF = unique(...)`` restricted to the currently legal
          actions.  T0's column, when T0 is in the set, is the same array the
          diagnostics already computed -- a source is never evaluated twice.
        * ``D3-multi-null`` draws ``n_proposals`` DISTINCT legal actions without
          replacement from its own declared DEV-NULL stream and reads no teacher at
          all; the scores it carries are zeros, as for ``D3-null``.

        ``teacher_action`` for a MULTI-D3 arm is the LOWEST-index member of the set
        -- an order-free representative kept only so the stored label stays a legal
        action and the inherited diagnostics keep their meaning.  **No loss reads
        it**: the multi loss reads the membership mask alone.
        """
        scores, t0_acts, legal = cft.t0_scores(states, masks)
        mech = self.dev.mechanism
        if mech == "D2-null":
            used = cft.permute_scores_among_legal(scores, legal, self._null_rng)
            used_acts = cft.masked_argmax_rows(used, legal)
        elif mech == "D3-null":
            # The margin loss reads ONLY the action, so the null replaces the action
            # with a seeded uniform legal draw and stores NO T0 quantity at all: the
            # scores it carries are zeros.
            used = np.zeros_like(scores)
            used_acts = cft.random_legal_actions(legal, self._null_rng)
        elif mech == "D3-multi":
            slots = cft.teacher_action_slots(
                self.multi.teachers, states, masks, cache={"T0": t0_acts},
                context=self._teacher_context,
            )
            member = cft.membership_from_slots(slots, legal)
            used = scores if "T0" in self.multi.teachers else np.zeros_like(scores)
            used_acts = cft.masked_argmax_rows(member.astype(np.float64), legal)
            return t0_acts, used_acts, used, legal, scores, member, slots
        elif mech == "D3-multi-null":
            slots = cft.random_legal_action_slots(
                legal, self._null_rng, self.multi.n_proposals,
                p_singleton=self.multi.p_singleton,
            )
            member = cft.membership_from_slots(slots, legal)
            used = np.zeros_like(scores)
            used_acts = cft.masked_argmax_rows(member.astype(np.float64), legal)
            return t0_acts, used_acts, used, legal, scores, member, slots
        else:
            used, used_acts = scores, t0_acts
        return t0_acts, used_acts, used, legal, scores, None, None

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
        if "teacher_member" in labels:
            batch["teacher_member"] = labels["teacher_member"]
        for key in ("judge_target", "judge_tag", "judge_challenger", "judge_override"):
            if key in labels:
                batch[key] = labels[key]
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
        if d.mechanism in D3_MECHANISMS:
            a_t = torch.tensor(np.asarray(batch["teacher_action"], dtype=np.int64),
                               dtype=torch.long, device=self.device)
            return d.lambda_e * cft.d3_margin_loss(scores, mask, a_t, d.margin)
        if d.mechanism in cft.MULTI_MECHANISMS:
            # The SAME frozen weight (lambda_E = 1) and the SAME frozen margin
            # (m = 0.15) as the single-teacher D3.  The set carries no per-teacher
            # weight of any kind.
            if "teacher_member" not in batch:
                raise MCRLContractError("MULTI-D3 batch carries no A_CF")
            member = torch.tensor(np.asarray(batch["teacher_member"], dtype=bool),
                                  dtype=torch.bool, device=self.device)
            return d.lambda_e * cft.d3_set_margin_loss(scores, mask, member, d.margin)
        if d.mechanism in JUDGE_MECHANISMS:
            # MC2 contract section 3: ONE target per row, weight w = 1[target
            # exists], mean over the FULL batch -- a row without a target
            # contributes exactly 0 and the vacated dose is not refilled.  The
            # frozen m = 0.15 and lambda_E = 1.0.  A target-less row's a_T is only
            # a legal placeholder (its executed action) under weight 0.
            if "judge_target" not in batch:
                raise MCRLContractError("MC2 batch carries no judge targets")
            target = np.asarray(batch["judge_target"], dtype=np.int64)
            has = target != cfj.NO_TARGET
            a_t = torch.tensor(
                np.where(has, target, np.asarray(batch["actions"], dtype=np.int64)),
                dtype=torch.long, device=self.device,
            )
            w = torch.tensor(has.astype(np.float32), dtype=scores.dtype,
                             device=self.device)
            loss, per_row = cfj.weighted_margin_loss(scores, mask, a_t, w, d.margin)
            self._last_tag_stats = cfj.tag_breakdown(per_row, w, batch["judge_tag"],
                                                     d.lambda_e)
            return d.lambda_e * loss
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

    # -- MC2 judge ------------------------------------------------------
    def _challenger_actions(self, states, masks, legal, is_final: bool):
        """The challenger's proposal per user -- ``a^B`` (T_NEXT) or ``a^R`` (null) --
        or ``None`` = ABSTAIN.

        Both abstain at the final decision step (contract section 1): T_NEXT is not
        even asked there, so its frozen T0 fallback can never be injected by B, and
        the null draws nothing.  The null reads no T_NEXT quantity and draws exactly
        one uniform legal action per user with a legal action, from its own stream.
        """
        spec = self.judge
        if is_final:
            return None
        if spec.uses_b:
            slots = cft.teacher_action_slots(
                (spec.source_b,), states, masks, context=self._teacher_context
            )
            return np.asarray(slots[:, 0], dtype=np.int64)
        if spec.uses_r:
            return cft.random_legal_actions(legal, self._judge_null_rng)
        return None

    def _judge_step(self, actions, states, masks, legal, t0_acts, t: int,
                    n_steps: int, jlog):
        """Pre-step MC2 labels for every user.  Called after the behaviour action
        ``x`` and the teacher labels and BEFORE ``env.step(x, env_rng)``; it reads
        the environment through the judge only (deep-copied generator, frozen
        driver positions) and consumes no generator but the B-null's own."""
        spec = self.judge
        is_final = t >= n_steps - 1
        challenger = self._challenger_actions(states, masks, legal, is_final)
        labeller = cfj.labeller_for(spec.mechanism_id)
        with cfj.StepJudge(self.env, actions, self._env_rng,
                           eta0=spec.judge_eta0) as judge:
            judge.base()          # the parity guard and the exact x_u reuse
            labels = labeller(
                use_a=spec.uses_a, challenger_tag=spec.challenger_tag, legal=legal,
                x=actions, a_a=t0_acts, challenger=challenger, kappa=judge.kappa,
            )
        jlog.add_step(t, labels, judge, a_a=t0_acts, x=actions,
                      abstained=(challenger is None),
                      has_challenger_source=(spec.uses_b or spec.uses_r))
        return labels, judge

    # -- DEVVAL ---------------------------------------------------------
    def devval_seeds(self) -> list[tuple[int, int]]:
        d = self.dev
        seeds = episode_seeds(d.devval_env_base, d.devval_mobility_base,
                              d.devval_episodes)
        assert_lane_seed_pairs(seeds, f"{lane_of(d)} evaluation", lane=lane_of(d))
        return seeds

    def devval(self) -> dict[str, Any]:
        """Greedy deployed rule on the DEVVAL episodes.  Consumes no training RNG."""
        if self._env_factory is None:
            raise MCRLContractError("DEVVAL needs an env_factory")
        greedy = lambda enc, masks, states: self.greedy_actions(enc, masks)  # noqa: E731
        return dev_rollout(lambda i: greedy, env_factory=self._env_factory,
                           encode=self.encode_at, seeds=self.devval_seeds(),
                           t0_agreement=True, lane=lane_of(self.dev))

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
            states, masks, observation = self.env.reset(
                self._env_rng, self._mobility_rng
            )
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
            used_agree_t0 = 0.0
            t0_decisions = 0
            n_slots = 0 if self.multi is None else self.multi.n_slots
            card_hist = [0] * (n_slots + 1)
            dup_rows = card_rows = 0
            # Controller record 716f104e section 3: the realised |A_CF| = 1 rate is
            # reported PER STEP, not only as a marginal, because T_NEXT's mandatory
            # final-step T0 fallback makes the last step singleton by construction.
            step_rows = [0] * int(self.env.config.steps_per_episode)
            step_singletons = [0] * int(self.env.config.steps_per_episode)
            n_ep_steps = self.env.config.steps_per_episode
            jlog = (None if self.judge is None
                    else cfj.EpisodeJudgeLog(steps=int(n_ep_steps),
                                             challenger_tag=self.judge.challenger_tag))
            for _t in range(n_ep_steps):
                if self._needs_teacher_context:
                    # Training-only, read-only, additive.  The observation is the
                    # one TrainerEnvironment already produced and the loop already
                    # had; nothing is stepped, drawn or written to build this.
                    self._teacher_context = cft.TeacherContext(
                        driver=self.env.environment.driver,
                        candidates=observation.candidates,
                        step_index=_t,
                        is_final_step=(_t >= n_ep_steps - 1),
                    )
                actions = self.select_actions(encoded, masks, eps)
                (t0_acts, used_acts, used_scores, legal, t0_scores_raw,
                 member, slots) = self.teacher_labels_ext(states, masks)
                if member is not None:
                    hist = cft.cardinality_histogram(member, n_slots)
                    card_hist = [a + b for a, b in zip(card_hist, hist)]
                    live = int(sum(hist[1:]))
                    card_rows += live
                    dup_rows += int(round(
                        cft.duplicate_slot_fraction(slots, member) * live
                    ))
                    if _t < len(step_rows):
                        step_rows[_t] += live
                        step_singletons[_t] += int(hist[1])
                greedy = self.greedy_actions(encoded, masks)   # diagnostic, no RNG
                for u in range(users):
                    if not bool(legal[u].any()):
                        continue
                    t0_decisions += 1
                    t0_greedy_agree += float(int(greedy[u]) == int(t0_acts[u]))
                    t0_behaviour_agree += float(int(actions[u]) == int(t0_acts[u]))
                    used_agree_t0 += float(int(used_acts[u]) == int(t0_acts[u]))
                    if 0 <= int(greedy[u]) < t0_scores_raw.shape[1]:
                        t0_greedy_regret += float(
                            t0_scores_raw[u, int(t0_acts[u])]
                            - t0_scores_raw[u, int(greedy[u])]
                        )
                step_judge = jlab = None
                if self.judge is not None:
                    jlab, step_judge = self._judge_step(
                        actions, states, masks, legal, t0_acts, _t, n_ep_steps, jlog
                    )
                ctx = (difference_context(self.env, actions, masks, self._env_rng,
                                          model=self._power_model)
                       if s.credit_mode == "difference" else None)
                result = self.env.step(actions, self._env_rng)
                outcome = self.env.last_outcome
                if step_judge is not None:
                    step_judge.assert_committed_parity(outcome)
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
                    if jlab is not None:
                        self.replay.push_judged(
                            encoded[uid], int(actions[uid]), raw[uid].copy(),
                            next_encoded[uid], masks[uid].mask.copy(),
                            next_mask.copy(), bool(result.done),
                            a_a=int(t0_acts[uid]),
                            challenger=int(jlab.challenger[uid]),
                            target=int(jlab.target[uid]), tag=int(jlab.tag[uid]),
                            override=bool(jlab.override[uid]),
                            lead_served=int(jlab.lead_served[uid]),
                            lead_surrogate=float(jlab.lead_surrogate[uid]),
                        )
                        jlog.add_push(int(jlab.tag[uid]))
                        continue
                    self.replay.push_labeled(
                        encoded[uid], int(actions[uid]), raw[uid].copy(),
                        next_encoded[uid], masks[uid].mask.copy(),
                        next_mask.copy(), bool(result.done),
                        t0_action=int(t0_acts[uid]),
                        teacher_action=int(used_acts[uid]),
                        teacher_scores=used_scores[uid],
                        teacher_member=(None if member is None else member[uid]),
                    )
                step_losses = self.update()
                if self._last_batch is not None:
                    ep_losses += step_losses
                    teacher_loss_sum += self._last_teacher_loss
                    n_upd += 1
                    if jlog is not None:
                        jlog.add_update(self._last_tag_stats)
                states, masks, encoded = (
                    result.user_states, result.action_masks, next_encoded
                )
                if self._needs_teacher_context:
                    observation = self.env.last_outcome.observation
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
                "t0_decisions": t0_decisions,
            }
            if self.multi is not None:
                # Amendment 15 section 7 report fields.  Diagnostics only: no loss,
                # no gradient and no target reads any of them.
                log.update(
                    multi_mechanism_id=self.multi.mechanism_id,
                    multi_teachers=list(self.multi.teachers),
                    multi_null_id=self.multi.null_id,
                    multi_set_cardinality_hist=list(card_hist),
                    multi_set_cardinality_mean=float(
                        sum(c * n for c, n in enumerate(card_hist)) / max(card_rows, 1)
                    ),
                    multi_duplicate_fraction=float(dup_rows / max(card_rows, 1)),
                    multi_set_rows=int(card_rows),
                    multi_singleton_rate=float(card_hist[1] / max(card_rows, 1)),
                    multi_decisions_per_step=list(step_rows),
                    multi_singletons_per_step=list(step_singletons),
                    multi_singleton_rate_per_step=[
                        (float(a / b) if b else None)
                        for a, b in zip(step_singletons, step_rows)
                    ],
                    multi_p_singleton_declared=(
                        None if self.multi.p_singleton is None
                        else float(self.multi.p_singleton)
                    ),
                    multi_p_singleton_rational=self.multi.p_singleton_rational,
                )
            if jlog is not None:
                # MC2 contract sections 5-7 report fields.  Diagnostics only: no
                # loss, gradient or target reads any of them.
                log.update(judge_mechanism_id=self.judge.mechanism_id,
                           judge_sources=list(self.judge.sources),
                           judge_id=self.judge.judge_id,
                           **jlog.as_log())
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
            "multi": (None if self.multi is None else dataclasses.asdict(self.multi)),
            "null_rng": (None if self._null_rng is None
                         else copy.deepcopy(self._null_rng.bit_generator.state)),
            "teacher_updates": int(self._teacher_updates),
        }
        if self.judge is not None:
            state["dev"]["judge"] = {
                "spec": dataclasses.asdict(self.judge),
                "null_rng": (None if self._judge_null_rng is None
                             else copy.deepcopy(self._judge_null_rng.bit_generator.state)),
            }
        return state

    def load_training_state_dict(self, state) -> None:
        dev = state.get("dev")
        if not isinstance(dev, Mapping):
            raise MCRLContractError("resume state carries no development block")
        if dev["settings"] != dataclasses.asdict(self.dev):
            raise MCRLContractError("resume state development settings do not match")
        want_multi = None if self.multi is None else dataclasses.asdict(self.multi)
        have_multi = dev.get("multi")
        if have_multi is not None:
            have_multi = dict(have_multi)
            have_multi["teachers"] = tuple(str(x) for x in have_multi["teachers"])
        if have_multi != want_multi:
            raise MCRLContractError("resume state MULTI-D3 spec does not match")
        have_judge = dev.get("judge")
        if (have_judge is None) != (self.judge is None):
            raise MCRLContractError("resume state MC2 judge block does not match")
        if (self.judge is not None
                and judge_spec_from_payload(have_judge["spec"]) != self.judge):
            raise MCRLContractError("resume state MC2 judge spec does not match")
        super().load_training_state_dict(state)
        if (dev["null_rng"] is None) != (self._null_rng is None):
            raise MCRLContractError("resume state DEV-NULL generator does not match")
        if self._null_rng is not None:
            self._null_rng.bit_generator.state = copy.deepcopy(dev["null_rng"])
        self._teacher_updates = int(dev["teacher_updates"])
        if self.judge is not None:
            if (have_judge["null_rng"] is None) != (self._judge_null_rng is None):
                raise MCRLContractError("resume state MC2 B-null generator does not match")
            if self._judge_null_rng is not None:
                self._judge_null_rng.bit_generator.state = copy.deepcopy(
                    have_judge["null_rng"]
                )

    def policy_payload(self, episode: int) -> dict[str, Any]:
        payload = super().policy_payload(episode)
        payload["schema"] = "cf-dev-policy-v1"
        payload["dev_settings"] = dataclasses.asdict(self.dev)
        if self.multi is not None:
            # Provenance only.  A deployed checkpoint is the three Q networks and
            # eta; NOTHING in the inference path reads this block, and no teacher
            # source has to exist to load or run the policy.
            payload["multi_spec"] = dataclasses.asdict(self.multi)
        if self.judge is not None:
            # Provenance only, as multi_spec: nothing in the inference path reads
            # it, and neither a Catfish nor the judge has to exist to run a policy.
            payload["judge_spec"] = dataclasses.asdict(self.judge)
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
