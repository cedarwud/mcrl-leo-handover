"""LANE-M source-identity receipt: the seam reproduces the ADMITTED ``T_NEXT``.

Controller record ``CONTROLLER-K8-NULL-AND-READY-2026-09-12.md`` (``716f104e``)
section 7.  **Before any k = 8 learner process exists**, the admitted source must be
reproduced through the new training-only seam on the frozen P0 environment, with:

* action identity on **every** tested decision,
* identical legality,
* identical final-step fallback,
* **no RNG mutation** by the seam,
* **no environment-state mutation** by the seam,

and the resulting shared-trajectory action trace must reproduce the authoritative
Lane N digest ``0568b222...``.  **If it does not, the SEAM is repaired -- ``T_NEXT``
is not changed.**

The loop is Lane N's ``tnext_p0.py`` shared-trajectory loop verbatim in structure
(same P0 seeds, same T0-rolled trajectory, same t >= 1 accounting, same trace
ordering).  The only difference is that the Lane-M column is obtained through
``cf_teacher.teacher_action_slots(("T_NEXT",), ..., context=TeacherContext(...))``
-- exactly the call the training loop makes -- instead of calling ``tnext_actions``
directly.

Usage::

    lane_m_source_receipt.py --episodes 24 --out RECEIPT.json
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

TREE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(TREE / "src"))
sys.path.insert(0, str(TREE / "scripts"))

import numpy as np  # noqa: E402

import cf3_common as C  # noqa: E402
import dev_e0_common as D  # noqa: E402
from mcrl.algorithms import cf_dev as cfd  # noqa: E402
from mcrl.algorithms import cf_multi_sources as cfmulti  # noqa: E402
from mcrl.algorithms import cf_teacher as cft  # noqa: E402
from mcrl.algorithms import cf_tnext as tn  # noqa: E402

P0_ENV_BASE, P0_MOB_BASE = 9_202_500, 9_203_500
LANE_N_TRACE_SHA256 = D.TNEXT_ACTION_TRACE_SHA256
FORBIDDEN = (9_111_000, 9_112_000, 9_121_000, 9_122_000, 9_311_000, 9_312_000)


def p0_seeds(n: int) -> list[tuple[int, int]]:
    seeds = [(P0_ENV_BASE + i, P0_MOB_BASE + i) for i in range(int(n))]
    for env_seed, mob_seed in seeds:
        for base in FORBIDDEN:
            if base <= env_seed < base + 1000 or base <= mob_seed < base + 1000:
                raise SystemExit(f"formal namespace touched: {env_seed}/{mob_seed}")
    cfd.assert_dev_seed_pairs(seeds, "LANE-M source receipt")
    return seeds


def _env_fingerprint(env) -> str:
    """A digest of everything the seam is forbidden to move."""
    driver = env.environment.driver
    h = hashlib.sha256()
    h.update(str(getattr(driver, "_step_index", None)).encode())
    h.update(str(getattr(driver, "_start_utc", None)).encode())
    h.update(np.ascontiguousarray(driver.user_ecef_km()).tobytes())
    pos = driver.satellite_ecef_at(0)
    for norad in sorted(pos):
        h.update(str(norad).encode())
        h.update(np.ascontiguousarray(pos[norad]).tobytes())
    return h.hexdigest()


def run(episodes: int) -> dict:
    tle = D.assert_environment()
    cfmulti.register_candidate_sources(replace=True)
    if not cft.teacher_needs_context(cfmulti.T_NEXT_ID):
        raise SystemExit("T_NEXT must be registered as a context-needing source")

    seeds = p0_seeds(episodes)
    factory = C.env_factory()
    probe = factory()
    users, steps = probe.config.num_users, probe.config.steps_per_episode
    del probe

    started = time.time()
    trace: list[int] = []
    n_dec = n_final = n_legal_violation = 0
    mismatch: list[dict] = []
    rng_moved = env_moved = 0
    per_step = np.zeros(steps, dtype=np.int64)

    for i, (env_seed, mob_seed) in enumerate(seeds):
        env = factory()
        env_rng = np.random.default_rng(env_seed)
        mob_rng = np.random.default_rng(mob_seed)
        states, masks, observation = env.reset(env_rng, mob_rng)
        driver = env.environment.driver
        for t in range(steps):
            _scores, t0_acts, legal = cft.t0_scores(states, masks)
            is_final = t >= steps - 1

            # --- the Lane N path, verbatim -------------------------------
            lane_n_acts, diag, _geom = tn.tnext_actions(
                states, masks, driver=driver,
                candidates=observation.candidates, is_final_step=is_final,
            )

            # --- the Lane M training-time path ---------------------------
            before_env = copy.deepcopy(env_rng.bit_generator.state)
            before_mob = copy.deepcopy(mob_rng.bit_generator.state)
            before_fp = _env_fingerprint(env)
            ctx = cft.TeacherContext(
                driver=driver, candidates=observation.candidates,
                step_index=t, is_final_step=is_final,
            )
            slots = cft.teacher_action_slots(
                (cfmulti.T_NEXT_ID,), states, masks, context=ctx
            )
            lane_m_acts = np.asarray(slots[:, 0], dtype=np.int64)
            rng_moved += int(env_rng.bit_generator.state != before_env)
            rng_moved += int(mob_rng.bit_generator.state != before_mob)
            env_moved += int(_env_fingerprint(env) != before_fp)

            # A_CF built the way training builds it: legality is structural.
            member = cft.membership_from_slots(slots, legal)

            for u in range(users):
                if not bool(legal[u].any()):
                    continue
                a_n, a_m = int(lane_n_acts[u]), int(lane_m_acts[u])
                if a_n != a_m:
                    mismatch.append({"episode": i, "t": t, "user": u,
                                     "lane_n": a_n, "lane_m": a_m})
                if not bool(masks[u].mask[a_m]):
                    n_legal_violation += 1
                if not bool(member[u, a_m]):
                    n_legal_violation += 1
                if is_final and a_m != int(t0_acts[u]):
                    mismatch.append({"episode": i, "t": t, "user": u,
                                     "final_step_fallback_not_t0": a_m,
                                     "t0": int(t0_acts[u])})
                if is_final:
                    n_final += 1
                n_dec += 1
                per_step[t] += 1
                if t >= 1:
                    trace.append(a_m)      # Lane N's trace ordering exactly

            if diag["fallback_final_step"] and not is_final:
                raise SystemExit("final-step fallback fired off the final step")

            res = env.step(t0_acts, env_rng)
            observation = env.last_outcome.observation
            states, masks = res.user_states, res.action_masks
            if res.done:
                break

    digest = hashlib.sha256(np.asarray(trace, dtype=np.int64).tobytes()).hexdigest()
    return {
        "lane": "CF2S-LANE-M source-identity receipt (development lane)",
        "governing": "CONTROLLER-K8-NULL-AND-READY-2026-09-12.md section 7 (716f104e)",
        "episodes": int(episodes),
        "seeds": {"env_base": P0_ENV_BASE, "mobility_base": P0_MOB_BASE},
        "steps_per_episode": int(steps),
        "users": int(users),
        "source": cfmulti.tnext_identity(),
        "cf_tnext_sha256": C.sha256_file(TREE / "src/mcrl/algorithms/cf_tnext.py"),
        "decisions_total": int(n_dec),
        "decisions_t1_t9": int(len(trace)),
        "decisions_per_step": [int(x) for x in per_step],
        "final_step_decisions": int(n_final),
        "action_mismatches": mismatch[:50],
        "action_mismatch_count": len(mismatch),
        "legal_violations": int(n_legal_violation),
        "seam_rng_mutations": int(rng_moved),
        "seam_env_mutations": int(env_moved),
        "action_trace_sha256": digest,
        "lane_n_action_trace_sha256": LANE_N_TRACE_SHA256,
        "trace_matches_lane_n": digest == LANE_N_TRACE_SHA256,
        "tle_file_set_sha256": tle,
        "wall_s": time.time() - started,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=24)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    result = run(a.episodes)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("source", "action_mismatches",
                                   "decisions_per_step")}, indent=2, default=str))
    ok = (result["trace_matches_lane_n"] and result["action_mismatch_count"] == 0
          and result["legal_violations"] == 0
          and result["seam_rng_mutations"] == 0
          and result["seam_env_mutations"] == 0)
    print("RECEIPT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
