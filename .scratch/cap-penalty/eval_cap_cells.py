"""CAPPENALTY greedy evaluation of every cell, capped and uncapped.

Extends PENALTYARM's ``penalty-arm/eval_pooled_ee.py`` WITHOUT changing its
estimand or its RNG consumption: same fresh env per cell (``_age_rng``
matched), same 24 episodes, same seeds, greedy eps = 0, unpenalised trainer,
``update()`` never called.  The only new ingredient in the rollout loop is
the environment's cap flag; everything else added is read-only:

* pooled EE = sum(bits) / sum(joules), divided once; bits and joules reported;
* served, cap-darkened and physical-outage fractions;
* handover rate (intra / inter satellite), per user-step;
* mean physically active beams, active satellites, beams per active satellite;
* G-3 four (``compute_collapse_metrics`` on the greedy scalarised Q, every
  step, averaged; step-0 and last-step means kept separately as the trainer
  does);
* srank_delta per head (PENALTYARM's estimator: delta = 0.01, mean-centred
  penultimate features, 128-state batches), on (a) the cell's own greedy
  states and (b) a COMMON PROBE of states from the uncapped OFF checkpoint's
  greedy rollouts.  Forward passes consume no numpy RNG.

A harness-integrity check is built in: OFF and PENALTY uncapped must reproduce
PENALTYARM's published endpoint EE (88,894,962.36 and 85,996,841.88 bit/J).

**500 EPISODES IS NOT CONVERGENCE.**  Capped cells are a DIFFERENT MDP.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
import time
from pathlib import Path


def _find_src() -> Path:
    for base in Path(__file__).resolve().parents:
        if (base / "src" / "mcrl").is_dir():
            return base / "src"
    raise SystemExit("could not locate src/mcrl above this script")


sys.path.insert(0, str(_find_src()))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import HandoverClass
from mcrl.env.constants import DECISION_STEP_S
from mcrl.runtime.collapse_metrics import compute_collapse_metrics
from mcrl.runtime.collapse_penalty import (
    PenaltyConfig,
    penultimate_features,
    srank_diagnostic,
)
from mcrl.runtime.trainer_spec import TrainerConfig

from beam_cap import active_beams_per_satellite, make_capped_training_environment

DT = float(DECISION_STEP_S)
N_EP = 24
TRAIN_SEED, ENV_SEED, MOBILITY_SEED = 42, 1337, 7
SRANK_BATCH = 128
SRANK_NBATCH = 20
SRANK_INDEX_SEED = 20260911
PENALTYARM_RUNS = Path("/home/sat/mcrl-v025-penalty-arm-ws/runs")


def srank_on(trainer: MODQNTrainer, states: np.ndarray) -> list[float]:
    """Mean srank_delta per head over fixed 128-state batches."""
    rng = np.random.default_rng(SRANK_INDEX_SEED)
    batches = [rng.choice(states.shape[0], size=SRANK_BATCH, replace=False)
               for _ in range(SRANK_NBATCH)]
    out = []
    with torch.no_grad():
        for head in range(3):
            vals = []
            for idx in batches:
                x = torch.as_tensor(states[idx], dtype=torch.float32)
                vals.append(srank_diagnostic(
                    penultimate_features(trainer.q_nets[head], x)))
            out.append(float(np.mean(vals)))
    return out


def evaluate(checkpoint: Path | None, beam_cap: int | None,
             n_ep: int = N_EP, probe: np.ndarray | None = None) -> tuple[dict, np.ndarray]:
    env = make_capped_training_environment(users=100, beam_cap=beam_cap)
    cfg = TrainerConfig(learning_rate=0.001, episodes=1)
    trainer = MODQNTrainer(
        env, cfg,
        train_seed=TRAIN_SEED, env_seed=ENV_SEED, mobility_seed=MOBILITY_SEED,
        penalty_config=PenaltyConfig(),
    )
    assert not trainer._penalty.active, "evaluation must be unpenalised"
    if checkpoint is not None:
        trainer.load_checkpoint(str(checkpoint), load_optimizers=False)

    users = env.config.num_users
    steps = env.config.steps_per_episode
    w = cfg.objective_weights

    bits = joules = 0.0
    served = darkened = outage = usersteps = 0
    ho_intra = ho_inter = 0
    beams = sats = 0.0
    max_per_sat = 0
    beam_steps = 0
    ee_ep: list[float] = []
    g3_all: list[dict] = []
    g3_first: list[dict] = []
    g3_last: list[dict] = []
    own_states: list[np.ndarray] = []

    for _ in range(n_ep):
        states, masks, _ = env.reset(trainer._env_rng, trainer._mobility_rng)
        enc = trainer._encode_states(states)
        eb = ej = 0.0
        for t in range(steps):
            actions = trainer.select_actions(enc, masks, 0.0)  # GREEDY
            # read-only G-3 on the same decision surface
            scal = trainer.scalarized_q_values(enc, objective_weights=w)
            g3 = compute_collapse_metrics(
                scal, np.stack([m.mask for m in masks]), actions).as_dict()
            g3_all.append(g3)
            if t == 0:
                g3_first.append(g3)
            if t == steps - 1:
                g3_last.append(g3)
            own_states.append(np.array(enc, dtype=np.float32, copy=True))

            result = env.step(actions, trainer._env_rng)
            outcome = env.last_outcome
            e = outcome.energy
            eb += float(e.system_throughput_bps) * DT
            ej += float(e.system_consumed_power_w) * DT
            res = outcome.resolution
            served += int(e.served)
            cap_dark = getattr(res, "cap_darkened", None)
            darkened += int(np.count_nonzero(cap_dark)) if cap_dark is not None else 0
            outage += int(np.count_nonzero(res.outage_infeasible))
            usersteps += users
            for cls in outcome.handovers:
                if cls is HandoverClass.INTRA_SATELLITE:
                    ho_intra += 1
                elif cls is HandoverClass.INTER_SATELLITE:
                    ho_inter += 1
            per_sat = active_beams_per_satellite(res)
            beams += float(len(res.active_beams))
            sats += float(len(per_sat))
            max_per_sat = max(max_per_sat, max(per_sat.values(), default=0))
            beam_steps += 1
            states = result.user_states
            enc = trainer._encode_states(states)
            masks = result.action_masks
            if result.done:
                break
        bits += eb
        joules += ej
        ee_ep.append(eb / ej if ej > 0 else float("nan"))

    def mean_g3(rows):
        keys = ("active_beam_count", "argmax_agreement", "q_margin", "q_entropy",
                "q_margin_raw", "q_range")
        return {k: float(np.mean([r[k] for r in rows])) for k in keys}

    own = np.concatenate(own_states, axis=0)
    out = {
        "checkpoint": str(checkpoint) if checkpoint else "untrained-init",
        "beam_cap": beam_cap,
        "episodes": n_ep,
        "pooled_bits": bits,
        "pooled_joules": joules,
        "pooled_ee_bit_per_j": bits / joules,
        "pooled_ee_sem": st.pstdev(ee_ep) / len(ee_ep) ** 0.5,
        "served_fraction": served / usersteps,
        "cap_darkened_fraction": darkened / usersteps,
        "outage_infeasible_fraction": outage / usersteps,
        "handover_rate_total": (ho_intra + ho_inter) / usersteps,
        "handover_rate_intra_satellite": ho_intra / usersteps,
        "handover_rate_inter_satellite": ho_inter / usersteps,
        "mean_active_beams": beams / beam_steps,
        "mean_active_satellites": sats / beam_steps,
        "mean_beams_per_active_satellite": beams / sats if sats else 0.0,
        "max_beams_on_one_satellite": int(max_per_sat),
        "g3_greedy_all_steps": mean_g3(g3_all),
        "g3_greedy_step0": mean_g3(g3_first),
        "g3_greedy_last_step": mean_g3(g3_last),
        "srank_own_states": srank_on(trainer, own),
        "srank_common_probe": srank_on(trainer, probe) if probe is not None else None,
    }
    return out, own


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--checkpoint", default="checkpoint-ep00500.pt")
    ap.add_argument("--cells", default="main",
                    help="'main' (endpoint + cross + floors) or 'traj'")
    ap.add_argument("--probe", default="runs/common-probe-OFF-nocap.npy")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    runs = Path(args.runs_dir)
    ck = args.checkpoint
    off = PENALTYARM_RUNS / "OFF" / ck
    pen = PENALTYARM_RUNS / "PENALTY" / ck
    c_off = runs / "CAP3_OFF" / ck
    c_pen = runs / "CAP3_PENALTY" / ck
    if args.cells == "main":
        cells = [
            ("OFF", off, None),
            ("PENALTY", pen, None),
            ("CAP3_OFF", c_off, 3),
            ("CAP3_PENALTY", c_pen, 3),
            ("xOFF_policy_in_CAP3_env", off, 3),
            ("xCAP3_OFF_policy_in_nocap_env", c_off, None),
            ("UNTRAINED_in_CAP3_env", None, 3),
        ]
    else:
        cells = [("CAP3_OFF", c_off, 3), ("CAP3_PENALTY", c_pen, 3)]

    probe_path = Path(args.probe)
    probe = np.load(probe_path) if probe_path.is_file() else None

    print(f"# pooled EE = sum(bits)/sum(joules). {N_EP} ep/cell, seeds 42/1337/7, "
          f"dt={DT}s, greedy, unpenalised, fresh env per cell. checkpoint={ck}")
    print("# CAPPED CELLS ARE A DIFFERENT MDP. 500 EPISODES IS NOT CONVERGENCE.\n",
          flush=True)
    results: dict[str, dict] = {}
    t0 = time.time()
    for name, path, cap in cells:
        if path is not None and not path.is_file():
            print(f"{name:32s} MISSING {path}", flush=True)
            continue
        res, own = evaluate(path, cap, probe=probe)
        if probe is None and name == "OFF" and cap is None:
            # The common probe IS the uncapped OFF checkpoint's own greedy
            # states; save it and fill in this cell's probe srank from it.
            probe = own
            np.save(probe_path, probe)
            res["srank_common_probe"] = res["srank_own_states"]
            print(f"# saved common probe {probe_path} shape={probe.shape}",
                  flush=True)
        results[name] = res
        g = res["g3_greedy_all_steps"]
        print(
            f"{name:32s} cap={cap} bits={res['pooled_bits']:.6e} "
            f"J={res['pooled_joules']:.6e} EE={res['pooled_ee_bit_per_j']:,.2f} "
            f"sem={res['pooled_ee_sem']:,.1f} served={res['served_fraction']:.4f} "
            f"dark={res['cap_darkened_fraction']:.4f} "
            f"outage={res['outage_infeasible_fraction']:.4f} "
            f"ho={res['handover_rate_total']:.4f} "
            f"(intra {res['handover_rate_intra_satellite']:.4f} / "
            f"inter {res['handover_rate_inter_satellite']:.4f}) "
            f"beams={res['mean_active_beams']:.2f} sats={res['mean_active_satellites']:.2f} "
            f"b/sat={res['mean_beams_per_active_satellite']:.2f} "
            f"maxb/sat={res['max_beams_on_one_satellite']} | "
            f"G3 slots={g['active_beam_count']:.2f} agree={g['argmax_agreement']:.4f} "
            f"margin={g['q_margin']:.5f} entropy={g['q_entropy']:.4f} | "
            f"srank_own={[round(x, 2) for x in res['srank_own_states']]} "
            f"srank_probe={[round(x, 2) for x in res['srank_common_probe']] if res['srank_common_probe'] else None}",
            flush=True,
        )
        Path(args.out).write_text(json.dumps(results, indent=2) + "\n")

    # Harness integrity: PENALTYARM's published endpoint values.
    if args.cells == "main" and ck == "checkpoint-ep00500.pt":
        for name, ref in (("OFF", 88_894_962.36), ("PENALTY", 85_996_841.88)):
            if name in results:
                got = round(results[name]["pooled_ee_bit_per_j"], 2)
                print(f"# integrity {name}: got {got:,.2f} ref {ref:,.2f} "
                      f"{'MATCH' if got == ref else 'MISMATCH'}", flush=True)
    print(f"\n# wall {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
