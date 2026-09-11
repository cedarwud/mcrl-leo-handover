#!/usr/bin/env python3
"""C3REACH timing probe: cost of full-48 realised dense evaluate_many batches."""
from __future__ import annotations
import gc, importlib.util, os, resource, sys, time
from pathlib import Path

PANEL_RUNNER = Path("/home/sat/mcrl-v025-ceiling30-ws/.scratch/panelceil/run_panelceil.py")
CROWD_RUNNER = Path("/home/sat/mcrl-v025-crowd-ws/.scratch/crowding-cost/run_crowding_cost.py")
COORD_RUNNER = Path("/home/sat/mcrl-v025-coord-ws/.scratch/coordvalue/run_coordvalue.py")


def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 / 2**30


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


panel = load("c3r_panel", PANEL_RUNNER)
crowd = load("c3r_crowd", CROWD_RUNNER)
coord = load("c3r_coord", COORD_RUNNER)
pilot = panel.load_pilot()
runner = pilot.ENGINE
run_setting = runner.run_setting_for("a-r0")
calls = {"n": 0}
def forbidden(*a, **k):
    calls["n"] += 1
    raise AssertionError("scalar evaluate forbidden")
runner.StepEvaluator.evaluate = forbidden
from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
from mcrl.physics_v025.tapes import build_world_tape
t0 = time.perf_counter()
tape = build_world_tape(domain=pilot.TRAIN_WORLDS[0], provider=LegacyWorldProvider(role="pilot-source"), steps=33, start_time_s=0.0)
print(f"tape {time.perf_counter()-t0:.1f}s rss {rss():.3f}", flush=True)
step = int(sys.argv[1]) if len(sys.argv) > 1 else 3
options, _ = runner._legal_options(tape, step)
bases = [runner._base_configuration(tape, step, c) for c in panel.CARRIERS]
print("distinct base mappings", len({b.configuration_id for b in bases}), [b.configuration_id[:12] for b in bases])
rep = bases[0]
rss_cfg = coord.rss_configuration(runner, tape, step, rep)
cache = {}
crowded = coord.crowded_configuration(runner, crowd, rep, options, cache, step)
print("options per user", sum(len(v) for v in options.values()), len(options))
singles = coord.single_candidates(runner, rep, rss_cfg, options, "rss")
print("singles", len(singles))
ev = coord.fresh_evaluator(runner, tape, step, bases[0], run_setting, "realised", tuple(range(48)))
t0 = time.perf_counter()
ev.evaluate_many(coord.dedupe(tuple(bases) + (rss_cfg, crowded)))
print(f"parity batch {time.perf_counter()-t0:.2f}s rss {rss():.3f}")
for b in (rss_cfg, crowded, *bases):
    p = coord.profile(ev, b)
    print(b.configuration_id[:12], p.bits, p.joules, p.bits / p.joules / 1e6, panel.served(p),
          sum(bool(v) for v in p.score.rate_target_attained.values()))
for size in (16, 32, 64, 128):
    configs = [row[0] for row in singles[:size]]
    t0 = time.perf_counter()
    ev.evaluate_many(configs)
    dt = time.perf_counter() - t0
    print(f"batch {size}: {dt:.2f}s = {dt/size:.3f}s/cand rss {rss():.3f}", flush=True)
    for c in configs:
        ev._evaluated.pop(c.configuration_id, None)
    gc.collect()
# boundary-subset cost
ev1 = coord.fresh_evaluator(runner, tape, step, bases[0], run_setting, "realised", (0,))
configs = [row[0] for row in singles[:64]]
t0 = time.perf_counter(); ev1.evaluate_many(configs); dt = time.perf_counter() - t0
print(f"boundary0 batch 64: {dt:.2f}s", flush=True)
print("scalar calls", calls["n"], "peak rss", rss())
