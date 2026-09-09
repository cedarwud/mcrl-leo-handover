# Stage-C training cost rehearsal (Claude Opus 5): measure the learner and evaluation cost so the post-admission timeline is real

You are running headless in `/home/sat/mcrl-v025-stagec-costcopy` (a snapshot copy of the stage-C workspace; the live workspace is busy — do not touch it). Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Synthetic data only; no real worlds; no TEST; compute budget ≤ 45 core-minutes total, ≤ 4 concurrent.

Read `V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md` and `V025-STAGES-6-8-CONTRACT-v1.1-AMENDMENT-2026-09-09.md` (16 learner seeds; 6 arms; ≈ 160 dates × 2 worlds per date × seed; ≈ 30 steps per world) and the build-3 report, then measure with the code as it stands:
1. **Row and shard cost:** seconds and bytes per 1 000 source rows through the production builder and shard writer (synthetic fixture), and the projected size and time for the full claim panel.
2. **Learner cost:** seconds per source epoch for one lineage at the sealed batch size and schema dimensions, and per 100-epoch checkpoint; then the projection for 96 lineages (6 arms × 16 seeds), with and without the 4-worker parallelism the server allows.
3. **Evaluation cost:** seconds per world-arm-seed evaluation at 30 steps with the coordinator's declared budget, and the projection for the full panel; plus merge time for the resulting receipt count.
4. **Memory:** peak RSS for the largest single step of each phase.
Report `V025-STAGEC-COST-REHEARSAL-2026-09-09.md` as your final message: a table of measured unit costs, the projected total core-hours and wall time at 20 cores for (a) source generation, (b) training, (c) evaluation, (d) merge, the assumptions behind each projection, and the three cheapest levers if the total exceeds one day of wall time. State clearly that these are engineering measurements on synthetic fixtures, not scientific results.
