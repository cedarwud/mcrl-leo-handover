#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""C2TARGET — the sealed TIE-BREAK reading of oracle C2 (declaration v1.6 s2, v1.9 s5).

Under that reading C2 ranks only among the maximisers of the immediate score,
ties defined by a 1e-9 relative tolerance.  This pass rebuilds the identical
catalogue and exact-label scores used by oracle_ee.py and reports, per anchor,
the size of the C1 tie set and whether the C2 tie-break changes the selected
configuration.  If it never changes the configuration, the tie-break arm is
the C1_ONLY configuration and its realised EE is already measured; no physics
evaluator is constructed here, so there is no evaluate path to stub.
"""

from __future__ import annotations

import gc
import importlib.util
import json
import math
from pathlib import Path
import resource
import sys
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("c2target_oracle_ee", HERE / "oracle_ee.py")
oe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oe)

REL_TOL = 1e-9


def main() -> int:
    oe.enforce()
    corpus = Path(sys.argv[1])
    worker, workers = int(sys.argv[2]), int(sys.argv[3])
    out_name = sys.argv[4]
    pilot = oe.load_pilot()
    engine = pilot.ENGINE
    setting = engine._setting("a-r0")
    run_setting = engine.run_setting_for("a-r0")
    calibration = oe.load_calibration(pilot)
    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
    from mcrl.physics_v025.tapes import build_world_tape

    every = sorted(
        corpus.glob("views/world-*/BUILD_NOT_CLAIM-exact-source-anchor-*.jsonl"),
        key=lambda p: (p.parent.name, p.name),
    )
    shards = [path for index, path in enumerate(every) if index % workers == worker]
    tape, tape_world = None, None
    records = []
    for shard in shards:
        header, labels, _incumbent = oe.read_anchor_labels(shard)
        world_index = int(header["world_index"])
        if tape_world != world_index:
            tape = None
            gc.collect()
            tape = build_world_tape(
                domain=pilot.TRAIN_WORLDS[world_index - 1],
                provider=LegacyWorldProvider(role="pilot-source"),
                steps=33, start_time_s=0.0,
            )
            tape_world = world_index
        step_index = int(header["step_index"])
        base = engine._base_configuration(tape, step_index, header["carrier"])
        catalogue, _census = engine._catalogue_with_census(
            tape, step_index, base,
            setting=setting, calibration=calibration, run_setting=run_setting,
        )
        base_map = base.mapping
        b1 = {u: labels[(u, base_map[u])]["c1"] for u in base_map}
        b2 = {u: labels[(u, base_map[u])]["c2"] for u in base_map}
        rows = []
        for config in catalogue:
            m = config.mapping
            if not all((u, m[u]) in labels for u in m):
                continue
            d1 = math.fsum(labels[(u, m[u])]["c1"] - b1[u] for u in m)
            d2 = math.fsum(labels[(u, m[u])]["c2"] - b2[u] for u in m)
            rows.append((d1, d2, config.configuration_id))
        c1_pick = min(rows, key=lambda r: (-r[0], r[2]))
        top = c1_pick[0]
        tol = REL_TOL * abs(top)
        tie_set = [r for r in rows if abs(r[0] - top) <= tol]
        tb_pick = min(tie_set, key=lambda r: (-r[1], r[2]))
        ordered = sorted(r[0] for r in rows)
        runner_up = ordered[-2] if len(ordered) > 1 else None
        records.append({
            "world_index": world_index,
            "global_anchor_index": int(header["global_anchor_index"]),
            "c1_max": top,
            "c1_runner_up": runner_up,
            "c1_tie_set_size": len(tie_set),
            "c1_only_pick": c1_pick[2],
            "tie_break_pick": tb_pick[2],
            "tie_break_changes_pick": tb_pick[2] != c1_pick[2],
        })
        print(json.dumps({k: records[-1][k] for k in ("global_anchor_index", "c1_tie_set_size", "tie_break_changes_pick")}), flush=True)
    result = {
        "status": "DIAGNOSTIC_NOT_CLAIM",
        "rel_tol": REL_TOL,
        "records": records,
        "peak_rss_kb": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
    }
    (oe.OUTDIR / out_name).write_text(json.dumps(result, indent=1, sort_keys=True))
    print(f"PEAK_RSS_KB={result['peak_rss_kb']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
