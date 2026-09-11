"""CF3PILOT memory check (coordinator review item 5), no training.

Loads an A2 episode-100 resume state (all four buffers full), warms the ONE
shared TleArchive with EVERY archive date (worst case for the parse cache),
then runs one ``measure_on_calibration()`` + one quarter update + one full
resume save, reporting VmRSS/VmHWM after each phase, wall time, and the
cgroup's ``memory.events``.  Run it under the same ``systemd-run --scope -p
MemoryMax=...`` as the pilot.

Usage: cf3_memtest.py RUN_DIR OUT_JSON
"""

from __future__ import annotations

import dataclasses
import json
import sys
import time
from pathlib import Path

import cf3_common as C

import torch

from mcrl.algorithms import cf_ratio as cfr


def mem() -> dict:
    out = {}
    for line in open("/proc/self/status"):
        if line.startswith(("VmRSS:", "VmHWM:")):
            out[line.split(":")[0]] = int(line.split()[1]) / 1024 / 1024
    return out


def cg_events() -> str | None:
    try:
        rel = [l for l in open("/proc/self/cgroup").read().splitlines() if l.startswith("0::")][0][3:]
        return Path(f"/sys/fs/cgroup{rel}/memory.events").read_text()
    except (OSError, IndexError):
        return None


def main() -> int:
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    torch.set_num_threads(1)
    phases = {"start": mem()}
    t0 = time.time()
    payload = torch.load(run / "resume.pt", map_location="cpu", weights_only=False)
    fp = payload["fingerprint"]
    from mcrl.runtime.trainer_spec import TrainerConfig
    cfgd = dict(fp["config"])
    for k in ("hidden_layers", "objective_weights", "reward_calibration_scales"):
        cfgd[k] = tuple(cfgd[k])
    st = cfr.CFRatioSettings(**fp["settings"])
    factory = C.env_factory()
    tr = cfr.CFRatioTrainer(factory(), TrainerConfig(**cfgd), st, env_factory=factory,
                            train_seed=fp["seeds"][0], env_seed=fp["seeds"][1],
                            mobility_seed=fp["seeds"][2])
    stored = payload["trainer_state"]["cf"]["settings"]
    now = dataclasses.asdict(st)
    assert all(now[k] == v for k, v in stored.items())
    payload["trainer_state"]["cf"]["settings"] = now
    tr.load_training_state_dict(payload["trainer_state"])
    logs = payload["logs"]
    del payload
    phases["loaded"] = mem()
    arch = C.shared_archive()
    t1 = time.time()
    for d in arch.dates:
        arch.load(d)
    phases["archive_all_dates_warm"] = mem()
    phases["archive_dates"] = len(arch.dates)
    t2 = time.time()
    row = tr.quarter_update(250)
    phases["after_calibration_and_quarter"] = mem()
    t3 = time.time()
    state = {"schema": "cf3-resume-v1", "next_episode": 100, "logs": logs,
             "trainer_state": tr.training_state_dict()}
    tmp = out.with_suffix(".pt.tmp")
    torch.save(state, tmp)
    phases["after_save"] = mem()
    t4 = time.time()
    size = tmp.stat().st_size
    tmp.unlink()
    res = {"phases_GB": phases, "wall_s": {"load": t1 - t0, "warm_archive": t2 - t1,
                                           "calibration_quarter": t3 - t2, "save": t4 - t3},
           "resume_file_bytes": size, "quarter_row_measured_ee": row["measured_ee"],
           "memory_events": cg_events(), "buffers": [len(s.buffer) for s in tr.sources],
           "main_replay": len(tr.replay)}
    C.write_json(out, res)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
