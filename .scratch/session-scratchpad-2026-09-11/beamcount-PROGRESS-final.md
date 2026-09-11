# BEAMCOUNT — progress checkpoint (FINAL)

Last update: 2026-09-11T01:05Z. Design-phase measurement, not a claim.
**Report delivered: `/home/sat/mcrl-v025-beamcount-ws/BEAM-COUNT-CAP-2026-09-10.md`**
(sha256 `973e81e161042a5c518d71944671cd8818f1ef370f45145290d07c3d8ca18420`).
Host `sat`; interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`; nice 15; BLAS/OMP threads 1; at most 3 python procs; peak RSS 1.75 GiB per proc.
`D` = `/home/sat/mcrl-v025-beamcount-ws/.scratch/beamcount/`.

## Nothing is running. No detached process of mine remains.

PID 3266088 (the Part 3 projection pass) was verified by cmdline and cwd, then SIGTERM'd at
01:00Z on the controller's cost-control instruction, before it completed its first anchor.

## Completed and delivered

1. **Parity gate PASSED** — `RSS_MAX` 41.621560 Mbit/J (delta -1.83e-07) and crowded endpoint
   46,110,374.33774687 bit/J (delta -1.27e-07), both to 6 dp, 1200/1200 served.
2. **Evaluator rule PASSED** — raising stub installed; all three shards ended
   `scalar_evaluate_calls = 0`.
3. **Part 1 feasibility floor = 8** at all four steps (exact min legal-beam set cover; same 8
   beams each step; greedy bound 10; matching rank 100; 370 beams; 9 satellites).
   A 3-beam system-wide cap is **infeasible**. Per-satellite cap 1 infeasible, 2 -> 8, 3 -> 8.
4. **Part 2 cap sweep COMPLETE** for every feasible requested level {8,9,10,15,20,30,50};
   {4,5,6} skipped as below the floor. Pooled EE is monotone increasing and peaks at C = 50:
   62.502712 Mbit/J, 1200/1200 served, 354/1200 (29.500%) attaining, realised 23.25 active beams.
   Per-cap files `D/caps/cap-0NN.json`; merged `D/beamcount-partial.json` (status PARTIAL by
   design: the final receipt is only written when the stopped Part 3 pass completes).
5. **Key negative finding**: the CROWDCOST monotone decline reproduces exactly under its own
   coverage-first rule (46.110374 -> 17.478088) but reverses when only the within-set assignment
   changes to max-nominal-gain. The slope is an assignment-rule property, not a beam-count property.

## Deliberately not done

- **Part 3** (RSS_MAX and learned a0 projected onto capped beam sets) — stopped for cost control;
  reported as NOT COMPLETED in the report. Resume with:
  `cd D && BEAMCOUNT_SCRIPT=run_beamcount_project.py ./launch.sh project - project.log`
  (shards are final inputs; ~25-35 min at current load; writes `D/beamcount-receipt.json`).
- **Part 4** (differentiable penalty pricing) — omitted on controller instruction (six reviews
  rejected treating beam concentration as a relabelled route); the report says so explicitly.
- **Per-satellite constrained optimum** (best assignment with <=27 beams, <=3 per satellite) —
  unmeasured; flagged in the report as the one cheap open follow-up.

## Immutable inputs for any resumption

- Frozen sweep runner `D/run_beamcount_sweep_frozen.py` == `D/run_beamcount.py`,
  sha256 `0b9818f31a58a0b34acca50bc98379f9143af0867d04cbeae911ef1bb427fd58`. Do not edit
  `run_beamcount.py`: each shard receipt records this hash and the project pass verifies it.
- Shards: `D/beamcount-shard-nearest-eligible.json` `7ddb0f3e...`,
  `D/beamcount-shard-stay-if-possible.json` `e16cc5ec...`,
  `D/beamcount-shard-random-masked.json` `eaca616a...`.
- Tables: `cd D && /home/sat/mcrl-leo-handover/.venv/bin/python beamcount_tables.py <receipt>`
  (works on the partial receipt too).
