Implemented and documented the training runner.

- Runner: [run_stagec_training.py](/home/sat/mcrl-v025-retrain-ws/scripts/run_stagec_training.py)
- Fixture: [stagec-training-arm-difference-v1.json](/home/sat/mcrl-v025-retrain-ws/tests/fixtures/stagec-training-arm-difference-v1.json)
- Report: [TRAINING-RUNNER-2026-09-10.md](/home/sat/mcrl-v025-retrain-ws/TRAINING-RUNNER-2026-09-10.md)
- Tests: 13 passed.
- Fixture gate: PASS for all four required pairs.
- 16-seed, 2-epoch synthetic smoke: `0.000707288 s/epoch/arm`; peak RSS `134,258,688` bytes.
- Epoch-100 checkpoint KAT: checkpoint written and sealed-loader readback PASS.
- `run_server_training.py` was assessed and is not an appropriate base; it belongs to the older P6 pipeline.
- The live EXACTGEN2 prefix validates through its 13 C1/C2 shards and 12,760 rows, then correctly fails closed because no authenticated C3 coalition view exists yet.

No sealed file or external handover workspace was modified.
