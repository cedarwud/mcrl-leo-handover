"""The S1 FORMAL lane's seed contract -- namespaces, guards, the S1-TRAIN triple.

Governing: ``docs/dev-e0/V025-CONTROLLER-AMENDMENT-13-S1-FROZEN-CONFIGURATION-2026-09-12.md``
(Amendment 13 sections 4 and 5) plus this round's MC2 contract
(``.scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md``) for the
judge-gated arm's matched null.

**Why this is its own module.**  It is a LEAF: it imports nothing from
:mod:`mcrl.algorithms.cf_dev`, so ``cf_dev`` can import it at module scope and the
development kernel keeps exactly one new dependency and three new call sites instead
of a second copy of the seed contract.  Everything S1 adds to the development lane
lives here or in :mod:`mcrl.algorithms.cf_s1`; the DEVELOPMENT namespaces, the DEV
guard and every development arm's configuration hash are untouched by design (the
MC2 development lane is being launched from the same tree).

The S1 lane spends the formal evaluation episodes ``9_111_000+i / 9_112_000+i``.  Its
whitelist is the S1-TRAIN triple, those formal evaluation episodes and the trainer's
derived substreams -- nothing else.  Every DEV / DEVVAL / DEV-NULL / calibration /
CONFIRM value is named in :data:`S1_FORBIDDEN_SEED_RANGES` so that a reused
development stream reports as *seed isolation broken* rather than as "outside every
namespace", which is the difference between a diagnosis and a puzzle.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ..errors import MCRLContractError

# ---------------------------------------------------------------- lanes
DEV_LANE: str = "E0-development"
S1_LANE: str = "S1-formal"
LANES: tuple[str, ...] = (DEV_LANE, S1_LANE)
"""The two seed contracts.  ``DevSettings`` (development) carries no lane field at
all and is therefore always ``DEV_LANE``; :class:`mcrl.algorithms.cf_s1.S1DevSettings`
carries one, so that adding the S1 lane changed no development configuration hash."""

# ---------------------------------------------------------------- namespaces
FORMAL_EVAL_ENV_BASE, FORMAL_EVAL_MOB_BASE = 9_111_000, 9_112_000
"""The formal evaluation episodes (Amendment 6 section 3).  Spent by S1, once."""

S1_TRAIN_BASE, S1_ENV_BASE, S1_MOB_BASE = 9_251_000, 9_252_000, 9_253_000
MAX_S1_SEED_INDEX: int = 2
"""Amendment 13 section 4: the same-index S1-TRAIN triple for every arm, k = 0, 1, 2."""

S1_NULL_BASE: int = 9_261_000
"""Amendment 13 section 5: ``D3-null`` at S1 draws from ``default_rng((9_261_000, k))``.
The development ``(9_241_000, k)`` stream may not be reused."""

S1_NULL_MC2_BASE: int = 9_263_000
"""The MC2 B-null's S1 stream: ``default_rng((9_263_000, k))``.

DECLARED HERE, BEFORE ANY S1 RUN.  The MC2 contract section 6 gives the development
B-null the DEV-NULL key ``(9_243_000, k)``; the S1 lane may not reuse a development
stream (Amendment 13 section 5), so the formal B-null gets the same +20_000 offset
that takes the development ``D3-null`` key ``9_241_000`` to its formal ``9_261_000``.
``9_263_000`` is used by nothing else in this project (checked across every worktree,
in both the ``9_263_000`` and ``9263000`` spellings).

One numpy subtlety that this declaration has to survive, because it is silent:
``default_rng((B, 0))`` is the SAME stream as ``default_rng(B)`` (``SeedSequence``
pads entropy with zeros, so ``[B]`` and ``[B, 0]`` mix identically).  Every composite
key's ``k = 0`` member therefore aliases the integer seed ``B``.  That can never
collide here because no declared namespace makes ``9_261_000`` or ``9_263_000`` a
legal INTEGER seed -- :func:`assert_s1_seed` refuses both -- and
``tests/test_s1_harness.py`` asserts it stream by stream rather than by argument."""

S1_NULL_BASES: tuple[int, ...] = (S1_NULL_BASE, S1_NULL_MC2_BASE)

S1_NULL_BASE_FOR: dict[str, int] = {
    "D3-null": S1_NULL_BASE,
    "MC2-B-null": S1_NULL_MC2_BASE,
}
"""Which S1 null namespace each matched null draws from.  ``MC2-B-null`` is the
judge-gated arm's proposal-replacement null (source set ``A+R``); its key lives in
the arm's ``JudgeSpec``, not in ``DevSettings``, exactly as in the development lane."""

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
"""The only INTEGER seed values an S1 run may construct.  The two S1 null namespaces
are deliberately absent: they are COMPOSITE generator identities ``(base, k)`` and are
validated by :func:`assert_s1_null_key`, never as standalone seeds."""

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
    (9_243_000, 9_243_999, "DEV-NULL MC2 B-null (MC2 contract section 6: not reusable)"),
    (9_271_000, 9_291_999, "DEV derived substreams (not reusable)"),
)
"""An S1 run that builds one of these is a seed-isolation failure, not a near miss.

``9_241_000..999`` is forbidden as an S1 SEED even though ``T0-XEP``'s reference
episode was recorded on ``9_241_500 / 9_241_501``: S1 never rolls that episode again,
it loads the sealed file, so no S1 run has any reason to construct those values."""


# ---------------------------------------------------------------- guards
def assert_s1_seed(seed: Any, what: str = "") -> int:
    """Fail closed unless ``seed`` is an integer in a declared S1 namespace.

    A tuple / list is a COMPOSITE null generator identity and goes to
    :func:`assert_s1_null_key`, which validates the pair as one identity.
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


def assert_s1_null_key(key: Any, what: str = "", *,
                       base: int | None = None) -> tuple[int, int]:
    """Validate an S1 null generator identity ``(base, k)``, k = 0, 1, 2.

    ``base`` pins the expected namespace (``S1_NULL_BASE_FOR[...]``); without it any
    declared S1 null base is accepted, which is what the generic seed guard needs.
    """
    if isinstance(key, (tuple, list)) and len(key) == 2:
        base_raw, index_raw = key
    else:
        raise MCRLContractError(
            f"S1 path {what!r} used {key!r} as a null key; the declared identity is "
            f"the pair (base, k) with base in {S1_NULL_BASES}"
        )
    if isinstance(base_raw, (tuple, list)) or isinstance(index_raw, (tuple, list)):
        raise MCRLContractError(f"nested S1 null key {key!r} in {what!r}")
    base_value, index_value = int(base_raw), int(index_raw)
    for lo, hi, name in S1_FORBIDDEN_SEED_RANGES:
        for part in (base_value, index_value):
            if lo <= part <= hi:
                raise MCRLContractError(
                    f"S1 path {what!r} built the null key {key!r}, whose component "
                    f"{part} belongs to {name!r}"
                )
    if base is not None and base_value != int(base):
        raise MCRLContractError(
            f"S1 path {what!r} built the null key {key!r}: {base_value} is not the "
            f"declared base {int(base)} for this null (Amendment 13 section 5 / MC2 "
            "contract section 6: a development stream may not be reused at S1)"
        )
    if base_value not in S1_NULL_BASES:
        raise MCRLContractError(
            f"S1 path {what!r} built the null key {key!r}: {base_value} is not a "
            f"declared S1 null base {S1_NULL_BASES}"
        )
    if not 0 <= index_value <= MAX_S1_SEED_INDEX:
        raise MCRLContractError(
            f"S1 path {what!r} built the null key {key!r}: the seed index must be an "
            f"integer in 0..{MAX_S1_SEED_INDEX}"
        )
    return base_value, index_value


def assert_lane_seed(seed: Any, what: str = "", *, lane: str = S1_LANE) -> int:
    """The non-development lanes' guard, dispatched by lane name.

    :func:`mcrl.algorithms.cf_dev.assert_lane_seed` keeps ``DEV_LANE`` for itself (so
    a test that neutralises ``assert_dev_seed`` still neutralises the development
    path) and sends every other lane here.  An unknown lane is refused, never
    silently unguarded.
    """
    if lane == S1_LANE:
        return assert_s1_seed(seed, what)
    raise MCRLContractError(f"unknown lane {lane!r} (declared: {LANES})")


def assert_lane_seed_pairs(seeds: Sequence[tuple[int, int]], what: str = "", *,
                           lane: str = S1_LANE) -> None:
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


def s1_null_key(role: str, k: int) -> tuple[int, int]:
    """The declared S1 null identity of ``role`` at seed index ``k``."""
    base = S1_NULL_BASE_FOR.get(str(role))
    if base is None:
        raise MCRLContractError(
            f"{role!r} has no declared S1 null namespace {tuple(S1_NULL_BASE_FOR)}"
        )
    key = (base, int(k))
    assert_s1_null_key(key, f"S1 null key for {role!r}", base=base)
    return key
