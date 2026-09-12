"""S1 formal screen, MC2 round: the frozen cell table, namespaces and hashes.

Governing documents, in order of precedence:

* ``.scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md``
  (the MC2 Catfish identity + intervention contract, r2 at the time of writing) --
  which cells exist, what each one ablates, and the declared readings;
* ``docs/dev-e0/V025-CONTROLLER-AMENDMENT-13-S1-FROZEN-CONFIGURATION-2026-09-12.md``
  (Amendment 13) -- the S1 namespaces, the 1000-episode depth, the same-budget MODQN
  win gate, the rolled 9000-episode reference, and "the complete matrix or nothing";
* ``docs/dev-e0/V025-CONTROLLER-AMENDMENT-12-S1-SECOND-NULL-2026-09-12.md``
  (Amendment 12) -- the OPTIONAL ``D3-XEP`` cell and its reading rule.

**FORMAL LANE.**  Unlike the development harness this spends the formal evaluation
episodes ``9_111_000+i / 9_112_000+i``.  Everything here is frozen before a single
number exists: the cell list, three seeds, 1000 episodes, one terminal evaluation
read per run.

**Nothing here decides which MC2 version runs.**  The whole table is a function of the
frozen ``mechanism_id`` (``MC2-JGO-v1`` or the declared alternative ``MC2-ARB-v2``),
because the two versions differ in what the drop-one of B *is*: under v1, removing B
gives the frozen ``D3-T0`` arm, so A-only and the single-Catfish baseline are ONE
cell; under v2, removing B gives the judge-gated ``A-only-v2`` cell (``{x_u, a^A}``)
and ``D3-T0`` is then only the baseline.  :func:`cells` encodes exactly that and
nothing else.

Seed isolation (Amendment 13 sections 4 and 5, MC2 contract section 6), enforced by
:mod:`mcrl.algorithms.cf_s1_lane`:

* ``S1-TRAIN`` train / env / mobility ``9_251_000 / 9_252_000 / 9_253_000 + k``,
  k = 0, 1, 2 -- the SAME index triple for every cell.  No DEV stream is reused.
* ``S1-NULL`` ``default_rng((9_261_000, k))`` for the optional ``D3-null``.
* ``S1-NULL-MC2`` ``default_rng((9_263_000, k))`` for the MC2 ``B-null``'s proposal
  replacement -- declared in ``cf_s1_lane``, unused anywhere else in the project.
* ``T0-XEP`` is the one declared exception: it keeps the sealed DEV-NULL reference
  trajectory of Amendment 12 and is never regenerated.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import cf3_common as C
import dev_e0_common as D

from mcrl.algorithms import cf_dev as cfd
from mcrl.algorithms import cf_s1 as cfs1
from mcrl.algorithms import cf_s1_lane as s1l
from mcrl.algorithms.cf_ratio import CFRatioSettings, episode_seeds

REPO = C.REPO

# ---------------------------------------------------------------- namespaces
S1_LANE, DEV_LANE = s1l.S1_LANE, s1l.DEV_LANE
EVAL_ENV_BASE, EVAL_MOB_BASE = s1l.FORMAL_EVAL_ENV_BASE, s1l.FORMAL_EVAL_MOB_BASE
SEED_INDICES = (0, 1, 2)
N_EVAL = 24

# ---------------------------------------------------------------- budget
EPISODES = 1000
CHECKPOINT_EVERY = 100
CREDIT_MODE = "equal_share"
ALPHA0, TAU_S0, MARGIN0, LAMBDA_E0 = D.ALPHA0, D.TAU_S0, D.MARGIN0, D.LAMBDA_E0
D2_TAU = 0.3
ETA0_EXPECTED = D.ETA0_EXPECTED
TLE_FILE_SET_SHA256 = D.TLE_FILE_SET_SHA256
FROZEN_MODQN_SHA256 = (
    "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
)
"""The published 9000-episode MODQN eq-(16) reference, ROLLED ONCE, never trained."""

# ---------------------------------------------------------------- T0-XEP (optional)
XEP_REFERENCE_PATH = REPO / "artifacts" / "dev-e0" / "t0-xep-reference.json"
XEP_REFERENCE_SHA256 = "9bb0c01efdd403fb0e765bd133d718f7b07273a188c9f173b39fbb112ae1900c"
XEP_REF_ENV_SEED, XEP_REF_MOB_SEED = 9_241_500, 9_241_501
XEP_REF_POLICY = "T0"
"""SEALED 2026-09-12, before any S1 run, and carried over byte for byte from the
accepted single-T0 harness (commit ``a24b90b2``): same file, same sha256, same
DEV-NULL seeds, same rolling policy.  It is NEVER regenerated."""


def load_xep_reference(path=None):
    """The declared T0-XEP reference trajectory, verified against its sha256."""
    from mcrl.algorithms import cf_xep as cfx

    return cfx.load_reference(Path(path or XEP_REFERENCE_PATH), XEP_REFERENCE_SHA256)


# ---------------------------------------------------------------- mechanisms
JGO_MECHANISM_ID = "MC2-JGO-v1"
ARB_MECHANISM_ID = "MC2-ARB-v2"
MECHANISM_IDS: tuple[str, ...] = (JGO_MECHANISM_ID, ARB_MECHANISM_ID)
"""The two declared MC2 versions (contract sections 3 and 7).  At most two, each with
its own reason; S1 runs exactly ONE of them, the one the owner / controller freezes
after the DEV screen.  No third version and no sweep."""

RULE_PREFIX: dict[str, str] = {JGO_MECHANISM_ID: "v1", ARB_MECHANISM_ID: "v2"}
"""The frozen version -> the cell-label prefix the development lane uses.

The library is the authority for both (``cf_judge.RULE_OF`` /
``dev_e0_common.JUDGE_CELLS``); this table exists so the S1 cell names map onto the
development cell labels, and the test suite asserts the mapping against the library
rather than trusting it."""

BONLY_RULE_ID: str = "MC2-B-ONLY-SHARED-v1"
"""The SHARED, rule-independent identity of the B-only cell (``cf_judge``'s own
``BONLY_MECHANISM_ID``).  ``B-only``'s labels and target are identical under both
versions, so it carries ONE identity with no version in it -- the method owner's
co-sign requires exactly that, and it means the cell is the same configuration
whichever version S1 freezes."""


def judge_mechanism_name() -> str:
    """``DevSettings.mechanism`` of every MC2 judge cell (the rule is in JudgeSpec)."""
    from mcrl.algorithms import cf_judge as cfj

    return cfj.MECHANISM_NAME

DROP_ONE_OF_B: dict[str, str] = {
    JGO_MECHANISM_ID: "D3-T0",
    ARB_MECHANISM_ID: "A-only-v2",
}
"""Which cell is "FULL with B removed" under each version (contract section 1,
"disable semantics", and section 6).  Under v1 that cell IS the frozen ``D3-T0``
arm -- one cell, not two.  Under v2 it is the judge-gated ``{x_u, a^A}`` cell, and
``D3-T0`` stays in the matrix as the single-Catfish baseline (R1-1)."""


# ---------------------------------------------------------------- cells
@dataclass(frozen=True)
class S1Cell:
    """One S1 cell: what it is, what it ablates, and which readings it serves."""

    name: str
    kind: str                       # "cf" | "judge" | "modqn"
    role: str
    mechanism: str | None = None    # DevSettings mechanism ("cf" cells)
    sources: tuple[str, ...] = ()   # judge cells: ("A","B") / ("B",) / ("A","R") / ("A",)
    tau: float | None = None
    null_role: str | None = None    # key into cf_s1_lane.S1_NULL_BASE_FOR
    optional: bool = False
    rule_independent: bool = False  # judge cells: carries the SHARED rule identity
    serves: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_judge(self) -> bool:
        return self.kind == "judge"

    def rule_id(self, mechanism_id: str) -> str:
        """The versioned RULE identity this cell runs under.

        Every judge cell but ``B-only`` runs the frozen version's rule; ``B-only`` is
        rule-independent and carries the shared identity in both, so its
        configuration -- and therefore its hash -- does not depend on which version
        S1 freezes.
        """
        if not self.is_judge:
            raise SystemExit(f"cell {self.name} has no rule identity")
        return BONLY_RULE_ID if self.rule_independent else str(mechanism_id)

    def cell_label(self, mechanism_id: str) -> str:
        """The development lane's canonical cell label (``v1-A+B``, ``v2-A``, ``B``)."""
        if self.rule_independent:
            return "+".join(self.sources)
        return f"{RULE_PREFIX[str(mechanism_id)]}-{'+'.join(self.sources)}"

    @property
    def uses_xep(self) -> bool:
        return self.mechanism == cfs1.XEP_MECHANISM


_BASE_CELLS: tuple[S1Cell, ...] = (
    S1Cell("D0", "cf", "control, catfish off -- the paired causal comparator",
           mechanism="D0", serves=("FULL_vs_D0", "D3T0_vs_D0")),
    S1Cell("D3-T0", "cf",
           "the frozen single-Catfish arm: E1's primary, the single-Catfish baseline "
           "every MC2 version must beat (R1-1), and under v1 also FULL's A-only "
           "drop-one (one cell, not two)",
           mechanism="D3-T0",
           serves=("FULL_vs_D3T0", "D3T0_vs_D0", "FULL_vs_A_only[v1]")),
    S1Cell("B-only", "judge",
           "drop-one of A: the foresight challenger alone, no anchor; its incumbent "
           "is the learner's own executed action. RULE-INDEPENDENT: identical labels "
           "and target under both versions, so ONE identity and one cell",
           sources=("B",), rule_independent=True, serves=("FULL_vs_B_only",)),
    S1Cell("FULL", "judge",
           "the MC2 method under test: both specialists, judge-gated",
           sources=("A", "B"),
           serves=("FULL_vs_A_only", "FULL_vs_B_only", "FULL_vs_B_null",
                   "FULL_vs_D0", "FULL_vs_D3T0", "FULL_vs_MODQN_eq16",
                   "FULL_vs_D2T0", "FULL_vs_REF9000")),
    S1Cell("B-null", "judge",
           "matched null of B with A kept: the same anchor, judge, gate and "
           "abstention, with a content-free uniform legal proposal from its own "
           "stream (NOT dose-matched -- contract section 7)",
           sources=("A", "R"), null_role="MC2-B-null",
           serves=("FULL_vs_B_null",)),
    S1Cell("D2-T0-tau0p3", "cf",
           "strongest soft comparator, reported, no superiority claim",
           mechanism="D2-T0", tau=D2_TAU, serves=("FULL_vs_D2T0",)),
    S1Cell("MODQN-eq16", "modqn",
           "same-budget win gate (Amendment 13 section 2): the project's only "
           "success gate is beating this baseline learner at the same budget",
           serves=("FULL_vs_MODQN_eq16", "D3T0_vs_MODQN_eq16")),
)

_V2_ONLY_CELL = S1Cell(
    "A-only-v2", "judge",
    "v2 ONLY: drop-one of B under competitive arbitration -- the judge-gated "
    "{x_u, a^A} cell. Under v2 this, not D3-T0, is 'FULL with B removed'",
    sources=("A",), serves=("FULL_vs_A_only[v2]",),
)

OPTIONAL_CELLS: tuple[S1Cell, ...] = (
    S1Cell("D3-null", "cf",
           "matched hard null of the anchor A (Amendment 4's conjunctive gate): the "
           "same D3 loss aimed at a seeded uniform random legal action",
           mechanism="D3-null", null_role="D3-null", optional=True,
           serves=("D3T0_vs_D3_null",)),
    S1Cell("D3-XEP", "cf",
           "plausible-but-uninformative second null of the anchor A (Amendment 12): "
           "T0's own score on a fixed pre-recorded reference episode; decides how "
           "the single-Catfish claim is WORDED (rho_info), adds no pass/fail gate",
           mechanism=cfs1.XEP_MECHANISM, optional=True,
           serves=("D3T0_vs_D3_XEP",)),
)
"""The two accepted single-T0 nulls.  They are OPTIONAL in the MC2 matrix: they test
the ANCHOR's content (an E1 / single-Catfish question), not the second source, so the
controller decides at freeze whether S1 carries them.  Cost: 3 runs each, ~35-40 min
per run on sat (they are not judge cells), i.e. one extra 8-wide wave for both."""

ROLLED_REFERENCE = {
    "label": "BASELINE_MODQN_eq16_frozen_9000ep",
    "checkpoint_sha256": FROZEN_MODQN_SHA256,
    "training": "none -- rolled once under the same formal evaluation protocol",
    "role": ("published / frozen reference; NOT a conjunctive S1 veto "
             "(Amendment 13 section 2)"),
    "serves": ["FULL_vs_REF9000"],
}


def cells(mechanism_id: str, *, optional: tuple[str, ...] = ()) -> dict[str, S1Cell]:
    """The frozen cell table for ``mechanism_id``, in launch order.

    ``optional`` names the OPTIONAL cells the controller chose to include at freeze
    (``()`` = neither).  Nothing else is parameterised: no cell may be added or
    dropped here without changing this function and the manifest hash.
    """
    mid = str(mechanism_id)
    if mid not in MECHANISM_IDS:
        raise SystemExit(
            f"unknown MC2 mechanism id {mid!r}; the declared versions are "
            f"{MECHANISM_IDS}"
        )
    table: list[S1Cell] = []
    for cell in _BASE_CELLS:
        table.append(cell)
        if cell.name == "D3-T0" and mid == ARB_MECHANISM_ID:
            table.append(_V2_ONLY_CELL)
    wanted = tuple(optional)
    known = {c.name: c for c in OPTIONAL_CELLS}
    for name in wanted:
        if name not in known:
            raise SystemExit(
                f"{name!r} is not an optional S1 cell {tuple(known)}"
            )
    table.extend(known[name] for name in wanted)
    out: dict[str, S1Cell] = {}
    for cell in table:
        if cell.name in out:
            raise SystemExit(f"duplicate S1 cell {cell.name!r}")
        out[cell.name] = cell
    return out


def cell(mechanism_id: str, name: str, *, optional: tuple[str, ...] = ()) -> S1Cell:
    table = cells(mechanism_id, optional=optional)
    if name not in table:
        raise SystemExit(f"{name!r} is not an S1 cell of {mechanism_id}: {tuple(table)}")
    return table[name]


def cell_index(mechanism_id: str, name: str, *, optional: tuple[str, ...] = ()) -> int:
    return list(cells(mechanism_id, optional=optional)).index(name) + 1


def run_name(mechanism_id: str, name: str, *, optional: tuple[str, ...] = ()) -> str:
    return f"S1-{cell_index(mechanism_id, name, optional=optional)}-{name}"


def specs(mechanism_id: str, *, optional: tuple[str, ...] = (),
          cell_names: tuple[str, ...] | None = None) -> tuple[str, ...]:
    """Every run of the complete matrix, as ``CELL:k``.

    ``cell_names`` restricts the list to those cells.  It exists for the DEVELOPMENT
    -lane preflight only -- a formal declaration is always the complete matrix
    (Amendment 13 section 7), which :func:`declared_manifest` enforces.
    """
    table = cells(mechanism_id, optional=optional)
    names = list(table) if cell_names is None else list(cell_names)
    for name in names:
        if name not in table:
            raise SystemExit(f"{name!r} is not a cell of {mechanism_id}")
    return tuple(f"{name}:{k}" for name in names for k in SEED_INDICES)


# ---------------------------------------------------------------- comparisons
COMPARISONS: tuple[dict[str, str], ...] = (
    {"id": "FULL_vs_A_only", "numerator": "FULL", "denominator": "<drop-one of B>",
     "reads": "does the second source add anything over the anchor alone",
     "authority": "contract section 7 (i)"},
    {"id": "FULL_vs_D3T0", "numerator": "FULL", "denominator": "D3-T0",
     "reads": "the two-Catfish method against the frozen single-Catfish arm "
              "(identical to FULL_vs_A_only under v1)",
     "authority": "contract section 7 (ii), R1-1"},
    {"id": "FULL_vs_B_only", "numerator": "FULL", "denominator": "B-only",
     "reads": "does the anchor still matter once the challenger is there",
     "authority": "contract section 7 (iii)"},
    {"id": "FULL_vs_B_null", "numerator": "FULL", "denominator": "B-null",
     "reads": "are T_NEXT's SPECIFIC proposals, filtered by this judge on top of the "
              "same anchor, better than content-free proposals filtered the same way "
              "(not dose-matched; identifies nothing about the judge itself)",
     "authority": "contract section 7 (iv) and its disclosure paragraph"},
    {"id": "FULL_vs_D0", "numerator": "FULL", "denominator": "D0",
     "reads": "the headline causal comparison: catfish on vs off, same tree, same "
              "budget, paired seeds",
     "authority": "win-gate / QoS floors, contract section 7 (v)"},
    {"id": "FULL_vs_MODQN_eq16", "numerator": "FULL", "denominator": "MODQN-eq16",
     "reads": "the SAME-BUDGET win gate -- the project's only success gate",
     "authority": "Amendment 13 section 2"},
    {"id": "FULL_vs_D2T0", "numerator": "FULL", "denominator": "D2-T0-tau0p3",
     "reads": "the strongest soft comparator; reported, never a superiority claim",
     "authority": "Amendment 13 section 3"},
    {"id": "D3T0_vs_D0", "numerator": "D3-T0", "denominator": "D0",
     "reads": "the headline DECOMPOSITION: how much of the gain is the single-Catfish "
              "anchor before any second source",
     "authority": "E1 / the 2026-09-12 split finding"},
    {"id": "D3T0_vs_MODQN_eq16", "numerator": "D3-T0", "denominator": "MODQN-eq16",
     "reads": "the single-Catfish arm against the same-budget baseline",
     "authority": "Amendment 13 section 2"},
    {"id": "FULL_vs_REF9000", "numerator": "FULL",
     "denominator": "BASELINE_MODQN_eq16_frozen_9000ep",
     "reads": "the published 9000-episode reference; a DIFFERENT budget, so a "
              "reference and never a veto",
     "authority": "Amendment 13 section 2"},
    {"id": "D3T0_vs_D3_null", "numerator": "D3-T0", "denominator": "D3-null",
     "reads": "OPTIONAL: Amendment 4's matched hard null of the anchor",
     "authority": "Amendment 4, Amendment 8 section 3b"},
    {"id": "D3T0_vs_D3_XEP", "numerator": "D3-T0", "denominator": "D3-XEP",
     "reads": "OPTIONAL: rho_info -- how much of the anchor's gain survives a "
              "well-formed teacher that is wrong about the current state; decides "
              "WORDING, not pass/fail",
     "authority": "Amendment 12 section 3"},
)


# ---------------------------------------------------------------- config
def s1_config(record, spec: S1Cell, episodes: int):
    """The trainer config for one cell.

    ``cf`` / ``judge`` cells: the frozen E0/E1 kernel -- shared-continuation
    bootstrap, gamma 1.  ``modqn``: the frozen eq-(16) recipe -- per-head max
    bootstrap, the prereg's own discount.  BOTH get the same budget-scaled epsilon
    schedule ``round(2000 N / 9000)`` (222 at N = 1000), so the same-budget
    comparison is not confounded by a different exploration schedule (the frozen
    9000-episode run's own 2000-episode decay would leave a 1000-episode baseline
    still exploring at the end).
    """
    pilot_arm = "A0" if spec.kind == "modqn" else "A1"
    cfg = C.pilot_config(record, pilot_arm, int(episodes))
    return dataclasses.replace(
        cfg, epsilon_decay_episodes=D.epsilon_decay_episodes(episodes)
    )


def s1_cf_settings(calib: dict) -> CFRatioSettings:
    """CF-ratio settings: eta fixed at eta_0, lambda 0, no source pools, no
    calibration reading (the calibration episodes stay untouched at S1 too)."""
    return CFRatioSettings(
        source_kind="none", rho=1.0 / 9.0, alpha=1.0, h_cap_inter=0.6016,
        quarter_episodes=10**9, eta_first_update_episode=10**9,
        catfish_buffer_capacity=50_000,
        eta0=float(calib["eta0_bit_per_J"]),
        bits_scale=float(calib["bits_scale"]),
        joules_scale=float(calib["joules_scale"]),
        lambda0=0.0, dual_ascent=False,
        calibration_env_seed_base=0, calibration_mobility_seed_base=0,
        calibration_episodes=0, credit_mode=CREDIT_MODE,
    )


def train_triple(k: int, *, lane: str = S1_LANE) -> tuple[int, int, int]:
    """The training triple of seed index ``k`` in this lane.

    ``S1-formal``: the S1-TRAIN triple (Amendment 13 section 4).  ``E0-development``:
    the DEV triple -- the harness's own preflight runs the S1 code path on
    development seeds, and the guards refuse every formal value on it.
    """
    if lane == S1_LANE:
        return s1l.s1_triple(k)
    if lane == DEV_LANE:
        if int(k) not in SEED_INDICES:
            raise SystemExit(f"the preflight runs seed index {SEED_INDICES}, not {k}")
        return D.dev_triple(int(k))
    raise SystemExit(f"unknown lane {lane!r}")


def eval_bases(lane: str = S1_LANE) -> tuple[int, int]:
    return ((EVAL_ENV_BASE, EVAL_MOB_BASE) if lane == S1_LANE
            else (D.DEVVAL_ENV_BASE, D.DEVVAL_MOB_BASE))


def eval_seeds(n: int = N_EVAL, *, lane: str = S1_LANE):
    env_base, mob_base = eval_bases(lane)
    seeds = episode_seeds(env_base, mob_base, n)
    cfd.assert_lane_seed_pairs(seeds, f"{lane} evaluation", lane=lane)
    return seeds


def eval_at(episodes: int) -> tuple[int, ...]:
    """ONE terminal read.  No intermediate peeking at the formal evaluation set, and
    therefore no checkpoint to shop for: a single checkpoint is the only one there
    is."""
    return (int(episodes),)


def null_key(spec: S1Cell, k: int, *, lane: str = S1_LANE):
    """The declared matched-null generator identity of a cell, or ``None``.

    ``D3-null`` carries it in its ``DevSettings``; the MC2 ``B-null`` carries it in
    its ``JudgeSpec`` (same as the development lane).  The S1 lane's bases are fresh
    (``9_261_000`` / ``9_263_000``); a development-lane preflight uses the development
    bases, and the lane guards refuse the other lane's stream outright.
    """
    if spec.null_role is None:
        return None
    if lane == S1_LANE:
        return s1l.s1_null_key(spec.null_role, k)
    dev_base = {"D3-null": D.DEV_NULL_D3_BASE,
                "MC2-B-null": getattr(D, "DEV_NULL_MC2_BASE", None)}[spec.null_role]
    if dev_base is None:
        raise SystemExit(
            "the development MC2 B-null namespace is not in this tree yet "
            "(dev_e0_common.DEV_NULL_MC2_BASE); merge the mechanism commit first"
        )
    key = (int(dev_base), int(k))
    cfd.assert_dev_null_key(key, f"preflight null key for {spec.name}")
    return key


def s1_dev_settings(mechanism_id: str, name: str, k: int, *,
                    eval_episodes: int = N_EVAL, lane: str = S1_LANE,
                    optional: tuple[str, ...] = ()) -> cfs1.S1DevSettings:
    """The teacher settings of one ``cf`` / ``judge`` cell."""
    spec = cell(mechanism_id, name, optional=optional)
    if spec.kind == "modqn":
        raise SystemExit(f"cell {name} has no teacher settings")
    mech = judge_mechanism_name() if spec.is_judge else spec.mechanism
    teacher = ("judge" if spec.is_judge
               else {"D0": "none", "D3-null": "random",
                     cfs1.XEP_MECHANISM: cfs1.XEP_TEACHER}.get(mech, "T0"))
    xep = spec.uses_xep
    env_base, mob_base = eval_bases(lane)
    return cfs1.S1DevSettings(
        lane=lane,
        mechanism=mech,
        teacher=teacher,
        alpha=ALPHA0, tau=(D.TAU0 if spec.tau is None else float(spec.tau)),
        tau_s=TAU_S0, margin=MARGIN0, lambda_e=LAMBDA_E0,
        null_key=(null_key(spec, k, lane=lane) if spec.mechanism == "D3-null"
                  else None),
        devval_env_base=env_base, devval_mobility_base=mob_base,
        devval_episodes=int(eval_episodes),
        xep_reference_sha256=(XEP_REFERENCE_SHA256 if xep else None),
        xep_reference_key=((XEP_REF_ENV_SEED, XEP_REF_MOB_SEED) if xep else None),
        xep_reference_policy=(XEP_REF_POLICY if xep else None),
    )


def judge_spec(mechanism_id: str, name: str, k: int, *, lane: str = S1_LANE,
               optional: tuple[str, ...] = ()):
    """The ``JudgeSpec`` of one MC2 judge cell (contract sections 1-3, 5, 6).

    The identity -- versioned mechanism id, canonical source set, source identities,
    judge id + its frozen ``eta0``, and the B-null's own null id + key -- is built by
    the library's own dataclass, so the S1 harness cannot declare an MC2 arm the
    development lane would not accept.
    """
    spec = cell(mechanism_id, name, optional=optional)
    if not spec.is_judge:
        return None
    try:
        from mcrl.algorithms import cf_judge as cfj
    except ImportError as err:                # pragma: no cover - pre-merge trees
        raise SystemExit(
            "the MC2 judge module is not in this tree yet: merge the mechanism "
            f"commit before declaring a judge cell ({err})"
        ) from err
    if not hasattr(cfd, "JudgeSpec"):         # pragma: no cover - pre-merge trees
        raise SystemExit("cf_dev.JudgeSpec is not in this tree yet (merge required)")
    mid = str(mechanism_id)
    # The DEVELOPMENT lane's own parser is the authority for what a cell label means,
    # so an S1 cell cannot be a (rule, source set) pair the development screen would
    # not accept -- and the rule id it returns is checked against this cell's own.
    label = spec.cell_label(mid)
    rule_id, srcs = D.judge_cell(label)
    if rule_id != spec.rule_id(mid) or srcs != tuple(spec.sources):
        raise SystemExit(
            f"S1 cell {spec.name} declares {spec.rule_id(mid)} / {spec.sources} but "
            f"the development label {label!r} means {rule_id} / {srcs}"
        )
    if srcs not in cfj.DECLARED_CELLS.get(rule_id, ()):
        raise SystemExit(
            f"{srcs} is not a declared cell of {rule_id}: "
            f"{cfj.DECLARED_CELLS.get(rule_id, ())}"
        )
    if "B" in srcs:
        sha = C.sha256_file(REPO / "src/mcrl/algorithms/cf_tnext.py")
        if sha != D.TNEXT_FILE_SHA256:
            raise SystemExit(
                f"cf_tnext.py sha256 {sha} is not the committed Lane N source "
                f"{D.TNEXT_FILE_SHA256}"
            )
    return cfd.JudgeSpec(
        mechanism_id=rule_id, sources=srcs,
        source_a=(cfj.SOURCE_A_ID if "A" in srcs else None),
        source_b=(cfj.SOURCE_B_ID if "B" in srcs else None),
        null_id=(cfj.NULL_ID if "R" in srcs else None),
        null_key=(null_key(spec, k, lane=lane) if "R" in srcs else None),
    )


def judge_source_identities(spec) -> dict:
    """The enabled sources' canonical identities, from the development lane's own
    table (one authority for both lanes)."""
    fn = getattr(D, "judge_source_identities", None)
    if fn is None:                            # pragma: no cover - pre-merge trees
        raise SystemExit(
            "dev_e0_common.judge_source_identities is not in this tree yet "
            "(merge lane A's mechanism commit)"
        )
    return fn(spec)


# ---------------------------------------------------------------- payload
def cell_config_payload(record, calib: dict, mechanism_id: str, name: str, k: int, *,
                        episodes: int, eval_episodes: int, calibration_sha256: str,
                        lane: str = S1_LANE,
                        optional: tuple[str, ...] = ()) -> dict:
    """Everything that defines one S1 run, for its configuration hash."""
    spec = cell(mechanism_id, name, optional=optional)
    train_seed, env_seed, mob_seed = train_triple(k, lane=lane)
    # NOTE: the cell's ROW POSITION in the table (``cell_index`` / ``run_name``) is
    # deliberately NOT hashed.  It is derived from which cells the frozen version and
    # the controller's optional choice happen to include, and a run's identity is what
    # it computes, not where it sits in a list.  Hashing it made the rule-INDEPENDENT
    # B-only cell hash differently under v1 and v2, which is exactly the claim that
    # cell exists to support; the position stays in the manifest, outside the payload.
    payload = {
        "lane": lane,
        "cell": spec.name,
        "kind": spec.kind, "role": spec.role, "serves": list(spec.serves),
        "optional": bool(spec.optional),
        "mechanism": (judge_mechanism_name() if spec.is_judge else spec.mechanism),
        "credit_mode": (CREDIT_MODE if spec.kind != "modqn" else None),
        "seed_index": int(k),
        "seeds": {"train": train_seed, "env": env_seed, "mobility": mob_seed},
        "eval_seeds": [list(x) for x in eval_seeds(eval_episodes, lane=lane)],
        "trainer_config": dataclasses.asdict(s1_config(record, spec, episodes)),
        "episodes": int(episodes),
        "eval_at": list(eval_at(episodes)),
        "calibration_sha256": calibration_sha256,
        "prereg_digest": record.digest,
        "tle_file_set_sha256": TLE_FILE_SET_SHA256,
    }
    if spec.kind != "modqn":
        payload["cf_settings"] = dataclasses.asdict(s1_cf_settings(calib))
        payload["dev_settings"] = dataclasses.asdict(
            s1_dev_settings(mechanism_id, name, k, eval_episodes=eval_episodes,
                            lane=lane, optional=optional)
        )
    if spec.is_judge:
        jspec = judge_spec(mechanism_id, name, k, lane=lane, optional=optional)
        payload["judge_spec"] = dataclasses.asdict(jspec)
        payload["judge_source_identities"] = judge_source_identities(jspec)
        payload["mc2_cell_label"] = spec.cell_label(str(mechanism_id))
        payload["rule_id"] = spec.rule_id(str(mechanism_id))
        payload["rule_independent"] = bool(spec.rule_independent)
    return payload


def config_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


# ---------------------------------------------------------------- manifest
MANIFEST_FILES = D.MANIFEST_FILES + (
    "src/mcrl/algorithms/cf_s1.py",
    "src/mcrl/algorithms/cf_s1_lane.py",
    "src/mcrl/algorithms/cf_xep.py",
    "scripts/s1_common.py",
    "scripts/run_s1.py",
    "scripts/s1_launch.py",
    "scripts/s1_reference.py",
    "scripts/s1_manifest.py",
    "scripts/s1_xep_reference.py",
    "artifacts/dev-e0/t0-xep-reference.json",
    "docs/dev-e0/V025-CONTROLLER-AMENDMENT-12-S1-SECOND-NULL-2026-09-12.md",
    "docs/dev-e0/V025-CONTROLLER-AMENDMENT-13-S1-FROZEN-CONFIGURATION-2026-09-12.md",
    ".scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md",
)
"""Every file whose bytes define this screen, including the two amendments and the
MC2 contract itself: the declaration is hashed together with the code that runs it."""


def code_manifest() -> dict:
    commit_file = REPO / "COMMIT"
    commit = (commit_file.read_text().strip() if commit_file.is_file()
              else "uncommitted-worktree")
    files = {f: C.sha256_file(REPO / f) for f in MANIFEST_FILES
             if (REPO / f).is_file()}
    missing = [f for f in MANIFEST_FILES if not (REPO / f).is_file()]
    if missing:
        raise SystemExit(f"the deployed tree is missing {missing}")
    h = hashlib.sha256()
    for p in sorted((REPO / "src").rglob("*.py")):
        h.update(str(p.relative_to(REPO)).encode())
        h.update(C.sha256_file(p).encode())
    return {"commit": commit, "files": files, "src_tree_sha256": h.hexdigest()}


def manifest_digest(code: dict) -> str:
    return hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest()


def declared_manifest(record, calib: dict, calibration_sha256: str, *,
                      mechanism_id: str, episodes: int = EPISODES,
                      eval_episodes: int = N_EVAL,
                      optional: tuple[str, ...] = (),
                      lane: str = S1_LANE,
                      cell_names: tuple[str, ...] | None = None,
                      reading_rules: dict | None = None) -> dict:
    """The whole frozen S1 declaration, in one hashable object.

    Amendment 13 section 7 item 7: the cell list, the namespaces, the depth, the
    frozen hyperparameters and the formal evaluation namespace, committed and hashed
    BEFORE any formal outcome exists.  ``reading_rules`` carries the controller's
    frozen reading rules (their text digest), so what the numbers will be read
    against is hashed at the same moment as the configuration.
    """
    mid = str(mechanism_id)
    table = cells(mid, optional=optional)
    if cell_names is not None and lane == S1_LANE:
        raise SystemExit(
            "a FORMAL S1 declaration is always the complete matrix (Amendment 13 "
            "section 7); a cell subset is a development-lane preflight only"
        )
    names = list(table) if cell_names is None else list(cell_names)
    code = code_manifest()
    payloads = {
        f"{name}:{k}": cell_config_payload(
            record, calib, mid, name, k, episodes=episodes,
            eval_episodes=eval_episodes, calibration_sha256=calibration_sha256,
            lane=lane, optional=optional)
        for name in names for k in SEED_INDICES
    }
    return {
        "declaration": "S1 frozen configuration (MC2 round)",
        "lane": lane,
        "authority": [
            ".scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md",
            "docs/dev-e0/V025-CONTROLLER-AMENDMENT-13-S1-FROZEN-CONFIGURATION-2026-09-12.md",
            "docs/dev-e0/V025-CONTROLLER-AMENDMENT-12-S1-SECOND-NULL-2026-09-12.md",
        ],
        "mechanism_id": mid,
        "mechanism": judge_mechanism_name(),
        "rule_ids": {name: spec.rule_id(mid) for name, spec in table.items()
                     if spec.is_judge},
        "cell_labels": {name: spec.cell_label(mid) for name, spec in table.items()
                        if spec.is_judge},
        "drop_one_of_B": DROP_ONE_OF_B[mid],
        "declared_versions": list(MECHANISM_IDS),
        "cells": {name: dataclasses.asdict(spec) for name, spec in table.items()},
        "declared_cells": names,
        "optional_cells_included": list(optional),
        "optional_cells_available": [c.name for c in OPTIONAL_CELLS],
        "rolled_reference": dict(ROLLED_REFERENCE),
        "comparisons": [dict(c) for c in COMPARISONS],
        "episodes": int(episodes),
        "seed_indices": list(SEED_INDICES),
        "specs": list(specs(mid, optional=optional, cell_names=cell_names)),
        "n_trained_runs": len(specs(mid, optional=optional, cell_names=cell_names)),
        "eval_at": list(eval_at(episodes)),
        "eval_episodes": int(eval_episodes),
        "namespaces": {
            "S1_TRAIN": {"train": s1l.S1_TRAIN_BASE, "env": s1l.S1_ENV_BASE,
                         "mobility": s1l.S1_MOB_BASE},
            "S1_NULL": [s1l.S1_NULL_BASE, "k"],
            "S1_NULL_MC2": [s1l.S1_NULL_MC2_BASE, "k"],
            "FORMAL_EVALUATION": {"env": EVAL_ENV_BASE, "mobility": EVAL_MOB_BASE},
            "T0_XEP_REFERENCE": {
                "env": XEP_REF_ENV_SEED, "mobility": XEP_REF_MOB_SEED,
                "note": ("DEV-NULL, sealed, never regenerated "
                         "(Amendment 13 section 5 exception)"),
            },
            "NEVER_TOUCHED_BY_S1": {
                "calibration": [9_121_000, 9_122_000],
                "CONFIRM": [9_301_000, 9_302_000, 9_303_000, 9_311_000, 9_312_000],
                "DEV/DEVVAL/DEV-NULL": [9_201_000, 9_202_000, 9_203_000, 9_211_000,
                                        9_212_000, 9_221_000, 9_231_000, 9_241_000,
                                        9_243_000],
            },
            "allowed": [list(r) for r in s1l.S1_ALLOWED_SEED_RANGES],
            "forbidden": [list(r) for r in s1l.S1_FORBIDDEN_SEED_RANGES],
        },
        "frozen_hyperparameters": {
            "learner": ("ratio learner, three heads, DQNNetwork (100, 50, 50) tanh, "
                        "113-dim observation, 28-action contract"),
            "deployed_score": "S = Q~_B - eta~ Q~_E, lambda = 0",
            "eta": "fixed at eta_0", "eta0_bit_per_J": ETA0_EXPECTED,
            "credit_mode": CREDIT_MODE,
            "anchor_A": "T0 = LP-prev(c = 1, m = 0), raw user state at collection time",
            "D3": {"margin": MARGIN0, "lambda_e": LAMBDA_E0},
            "D2": {"alpha": ALPHA0, "tau": D2_TAU, "tau_s": TAU_S0},
            "epsilon_decay_episodes": D.epsilon_decay_episodes(episodes),
            "batch_size_replay": "batch 128, replay 50 000 (unchanged)",
            "t0_xep_reference_sha256": XEP_REFERENCE_SHA256,
        },
        "calibration_sha256": calibration_sha256,
        "prereg_digest": record.digest,
        "tle_file_set_sha256": TLE_FILE_SET_SHA256,
        "code": code, "code_digest": manifest_digest(code),
        "arm_configs": {key: config_hash(p) for key, p in payloads.items()},
        "arm_payloads": payloads,
        "run_names": {f"{name}:{k}": f"{run_name(mid, name, optional=optional)}-k{k}"
                      for name in names for k in SEED_INDICES},
        "reading_rules": reading_rules or {
            "status": "NOT FROZEN -- s1_manifest.py --reading-rules FILE is required "
                      "for a formal manifest",
        },
    }


def assert_environment() -> str:
    return D.assert_environment()
