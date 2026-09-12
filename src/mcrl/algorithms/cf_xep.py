"""The fixed reference trajectory behind ``T0-XEP`` (Amendment 12).

Governing: ``.scratch/multi-catfish-v025-physics-successor/
V025-CONTROLLER-AMENDMENT-12-S1-SECOND-NULL-2026-09-12.md`` section 2.
**Development lane**: nothing here is formal screening evidence.

``T0-XEP`` is T0's ordinary frozen score (``log2(1 + gamma_a) - c [beam a unlit]``,
``c = 1``, ``m = 0``, unmodified -- :func:`mcrl.algorithms.cf_teacher.t0_score_matrix`)
evaluated on the state recorded at step ``t`` of ONE pre-recorded reference episode,
with the argmax restricted to the learner's CURRENT legal action mask.  This module
owns that reference episode: how it is recorded (once), how it is stored, and how a
run proves it is using the declared one and not a regenerated one.

**The reference is recorded once and never again.**  :func:`record_reference` writes a
file that :func:`write_reference` refuses to overwrite, and every consumer loads it
through :func:`load_reference`, which fails closed unless the file's sha256 is the
declared one.  The sha256 rides in the run's configuration hash
(``cf_dev.DevSettings.xep_reference_sha256`` -> ``dev_e0_common.arm_config_payload``),
so a different reference is a different version, exactly as the D3-null contract
requires of its null key.

The stored file is fully determined by ``(schema, policy, env seed, mobility seed,
users, steps, data)``: re-recording on the pinned TLE archive reproduces it byte for
byte.  Volatile provenance (wall clock, host, commit) goes in a separate sidecar so it
can never move the identity.

What is stored per step, per user: the two RAW ``UserState`` quantities T0 reads --
``channel_quality`` (28 nominal SINRs) and ``beam_loads`` (28 previous-step user
counts).  Nothing else: the reference's own mask is deliberately NOT stored, because
the argmax must use the learner's current mask and a stored reference mask would be
an invitation to use the wrong one.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError

SCHEMA: str = "t0-xep-reference-v1"
"""``steps x users x 2 x 28`` float64, little-endian; plane 0 = ``channel_quality``,
plane 1 = ``beam_loads``."""

IDENTITY_FIELDS: tuple[str, ...] = (
    "schema", "policy", "env_seed", "mobility_seed", "users", "steps",
    "num_actions", "dtype", "byte_order", "layout", "data_sha256", "data_b64",
)
"""Every field the reference file may carry.  A file with anything else is refused:
the identity is the whole file, so nothing may sneak in beside these."""


# ------------------------------------------------------------------ states
@dataclass(frozen=True)
class RawT0State:
    """The two RAW ``UserState`` fields T0 scores with, and nothing else.

    Duck-typed for :func:`mcrl.algorithms.cf_teacher.t0_score_matrix`, so the
    reference is scored by literally the same expression as the live state.
    """

    channel_quality: np.ndarray
    beam_loads: np.ndarray


class Reference:
    """One loaded, verified, immutable reference trajectory."""

    def __init__(self, payload: dict[str, Any], sha256: str) -> None:
        self._meta = {k: payload[k] for k in IDENTITY_FIELDS if k != "data_b64"}
        self.sha256 = str(sha256)
        data = decode_block(payload)
        data.flags.writeable = False
        self._data = data
        self._steps: tuple[tuple[RawT0State, ...], ...] = tuple(
            tuple(
                RawT0State(channel_quality=data[t, u, 0], beam_loads=data[t, u, 1])
                for u in range(data.shape[1])
            )
            for t in range(data.shape[0])
        )

    # -- identity -------------------------------------------------------
    @property
    def steps(self) -> int:
        return int(self._data.shape[0])

    @property
    def users(self) -> int:
        return int(self._data.shape[1])

    @property
    def policy(self) -> str:
        return str(self._meta["policy"])

    @property
    def key(self) -> tuple[int, int]:
        """The DEV-NULL ``(env seed, mobility seed)`` the episode was rolled on."""
        return (int(self._meta["env_seed"]), int(self._meta["mobility_seed"]))

    def identity(self) -> dict[str, Any]:
        return dict(self._meta, sha256=self.sha256)

    # -- use ------------------------------------------------------------
    def states_at(self, step: int) -> tuple[RawT0State, ...]:
        """The reference episode's raw user states at step ``step`` (0-based).

        Fails closed past the end of the reference episode: there is no wraparound
        and no clamping, because either would silently change the teacher.
        """
        t = int(step)
        if not 0 <= t < self.steps:
            raise MCRLContractError(
                f"T0-XEP: learner step {t} has no reference state "
                f"(the reference episode is {self.steps} steps long)"
            )
        return self._steps[t]


# ------------------------------------------------------------------ codec
def encode_block(data: np.ndarray) -> dict[str, Any]:
    arr = np.ascontiguousarray(np.asarray(data, dtype="<f8"))
    if arr.ndim != 4 or arr.shape[2] != 2 or arr.shape[3] != NUM_ACTIONS:
        raise MCRLContractError(f"reference block has shape {arr.shape}")
    raw = arr.tobytes(order="C")
    return {
        "users": int(arr.shape[1]), "steps": int(arr.shape[0]),
        "num_actions": NUM_ACTIONS, "dtype": "float64", "byte_order": "little",
        "layout": "steps x users x 2 x 28 (0 = channel_quality, 1 = beam_loads)",
        "data_sha256": hashlib.sha256(raw).hexdigest(),
        "data_b64": base64.b64encode(raw).decode("ascii"),
    }


def decode_block(payload: dict[str, Any]) -> np.ndarray:
    if payload.get("schema") != SCHEMA:
        raise MCRLContractError(f"not a {SCHEMA} reference: {payload.get('schema')!r}")
    if payload.get("dtype") != "float64" or payload.get("byte_order") != "little":
        raise MCRLContractError("the reference block must be little-endian float64")
    if int(payload.get("num_actions", -1)) != NUM_ACTIONS:
        raise MCRLContractError("the reference block is not on the 28-action contract")
    raw = base64.b64decode(payload["data_b64"], validate=True)
    if hashlib.sha256(raw).hexdigest() != payload["data_sha256"]:
        raise MCRLContractError("the reference block's own sha256 does not match")
    steps, users = int(payload["steps"]), int(payload["users"])
    expect = steps * users * 2 * NUM_ACTIONS * 8
    if len(raw) != expect:
        raise MCRLContractError(f"reference block is {len(raw)} bytes, expected {expect}")
    arr = np.frombuffer(raw, dtype="<f8").reshape(steps, users, 2, NUM_ACTIONS)
    return np.array(arr, dtype=np.float64, copy=True)


def serialise(payload: dict[str, Any]) -> str:
    """The one canonical on-disk form (so the sha256 is reproducible)."""
    extra = set(payload) - set(IDENTITY_FIELDS)
    if extra:
        raise MCRLContractError(f"a reference file may not carry {sorted(extra)}")
    missing = set(IDENTITY_FIELDS) - set(payload)
    if missing:
        raise MCRLContractError(f"a reference file is missing {sorted(missing)}")
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ record
def record_reference(env_factory, *, env_seed: int, mobility_seed: int,
                     policy, policy_name: str) -> dict[str, Any]:
    """Roll ONE episode and return the reference payload.  No optimizer, no learner.

    ``policy(enc, masks, states) -> actions`` is the ``pooled_rollout`` policy
    signature; ``enc`` is passed as ``None`` because a reference policy may read only
    the raw states (T0 does).  The caller is responsible for the seed namespace --
    :func:`mcrl.algorithms.cf_dev.assert_dev_seed` is applied here as well, so a
    formal seed can never reach a reference trajectory.
    """
    from . import cf_dev as cfd

    cfd.assert_dev_seed(env_seed, "T0-XEP reference env")
    cfd.assert_dev_seed(mobility_seed, "T0-XEP reference mobility")
    env = env_factory()
    env_rng = np.random.default_rng(int(env_seed))
    mobility_rng = np.random.default_rng(int(mobility_seed))
    states, masks, _ = env.reset(env_rng, mobility_rng)
    users, steps = env.config.num_users, env.config.steps_per_episode
    block = np.zeros((steps, users, 2, NUM_ACTIONS), dtype=np.float64)
    recorded = 0
    for t in range(steps):
        for u in range(users):
            block[t, u, 0] = np.asarray(states[u].channel_quality, dtype=np.float64)
            block[t, u, 1] = np.asarray(states[u].beam_loads, dtype=np.float64)
        recorded += 1
        result = env.step(policy(None, masks, states), env_rng)
        states, masks = result.user_states, result.action_masks
        if result.done:
            break
    if recorded != steps:
        raise MCRLContractError(
            f"the reference episode ended after {recorded} of {steps} steps"
        )
    payload = {"schema": SCHEMA, "policy": str(policy_name),
               "env_seed": int(env_seed), "mobility_seed": int(mobility_seed)}
    payload.update(encode_block(block))
    return payload


def write_reference(path: Path, payload: dict[str, Any]) -> str:
    """Write the reference ONCE and return its file sha256.

    Refuses to overwrite: Amendment 12 says the reference "may not be regenerated
    afterwards", so the recorder cannot silently produce a second one.
    """
    path = Path(path)
    if path.exists():
        raise MCRLContractError(
            f"{path} already exists; the T0-XEP reference is recorded once and never "
            "regenerated (Amendment 12 section 2)"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(serialise(payload))
    tmp.replace(path)
    return file_sha256(path)


def load_reference(path: Path, expected_sha256: str) -> Reference:
    """Load the declared reference; fail closed on any other file.

    ``expected_sha256`` is the declaration -- it comes from the run's configuration
    (``DevSettings.xep_reference_sha256``), not from the file.
    """
    path = Path(path)
    if not path.is_file():
        raise MCRLContractError(f"no T0-XEP reference trajectory at {path}")
    digest = file_sha256(path)
    if not expected_sha256:
        raise MCRLContractError("T0-XEP: no declared reference sha256 to check against")
    if digest != str(expected_sha256):
        raise MCRLContractError(
            f"T0-XEP reference {path} has sha256 {digest}, not the declared "
            f"{expected_sha256}"
        )
    payload = json.loads(path.read_text())
    if serialise(payload) != path.read_text():
        raise MCRLContractError(f"{path} is not in the canonical reference form")
    return Reference(payload, digest)
