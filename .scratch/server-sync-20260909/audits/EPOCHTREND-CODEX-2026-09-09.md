# Epoch trend from existing checkpoints — 2026-09-09

> **PILOT_NOT_CLAIM — critical limitation:** These checkpoints were trained with a coalition feature path that has since been found defective: the pairwise cross-gain terms were summed into a single scalar before the head saw them, which the contract forbids. **This trend therefore describes a model that could not see the mechanism.** It is quarantined engineering evidence, not claim evidence.

## Result

The requested table uses the existing report's `P-a0` catalogue anchor. Pooled energy efficiency (EE) is total bits divided by total joules across 5 world-3 anchors and 2 learner seeds. Availability and FULL coalition size are means across the corresponding 10 anchor-seed receipts.

| Epoch | FULL EE (bit/J) | DROP_C3 EE (bit/J) | BASELINE EE (bit/J) | FULL − DROP_C3 (relative) | FULL availability | DROP_C3 availability | BASELINE availability | FULL mean selected coalition size |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 200 | 34,250,712 | 23,517,487 | 16,987,632 | +45.64% | 74.379% | 79.250% | 76.317% | 100.0 |
| 600 | 24,135,506 | 23,453,085 | 16,987,632 | +2.91% | 76.440% | 79.212% | 76.317% | 61.1 |
| 1000 | 17,459,627 | 23,453,085 | 16,987,632 | −25.56% | 76.716% | 79.212% | 76.317% | 3.1 |
| 1400 | 17,459,627 | 23,453,085 | 16,987,632 | −25.56% | 76.716% | 79.212% | 76.317% | 3.1 |
| 2000 | 17,605,756 | 23,551,095 | 16,987,632 | −25.24% | 76.819% | 79.199% | 76.317% | 3.0 |

The existing `P-u` catalogue-anchor sensitivity check gives the same conclusion:

| Epoch | FULL EE (bit/J) | DROP_C3 EE (bit/J) | BASELINE EE (bit/J) | FULL − DROP_C3 (relative) | FULL availability | DROP_C3 availability | BASELINE availability | FULL mean selected coalition size |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 200 | 34,250,712 | 23,466,451 | 16,987,632 | +45.96% | 74.379% | 79.173% | 76.317% | 100.0 |
| 600 | 24,058,790 | 23,566,053 | 16,987,632 | +2.09% | 76.274% | 79.110% | 76.317% | 61.2 |
| 1000 | 17,315,579 | 23,549,719 | 16,987,632 | −26.47% | 76.454% | 79.180% | 76.317% | 2.8 |
| 1400 | 17,371,733 | 23,503,672 | 16,987,632 | −26.09% | 76.546% | 79.127% | 76.317% | 3.0 |
| 2000 | 17,332,219 | 23,549,719 | 16,987,632 | −26.40% | 76.626% | 79.180% | 76.317% | 3.0 |

## Answers

1. **The contrast trends down.** It falls from +45.64% at epoch 200 to +2.91% at epoch 600, reverses to −25.56% at epoch 1000, and then stays roughly flat near −25% through epoch 2000. The epoch-200 FULL advantage does not survive training; within this defective model, it was noise or an early-training artefact. This small evaluation cannot distinguish those two explanations.

2. **Yes, selected coalition size changes sharply with training.** At epoch 200, all 10 FULL decisions select size 100. At epoch 600, 6 of 10 still select size 100, while the other 4 select sizes 2 or 5. From epoch 1000 onward, no decision selects size 100: sizes are 2–5, and the mean is 3.0 at epoch 2000. The all-users behavior does not persist and is therefore a warm-up/early-training artefact for this model, not a stable endpoint behavior.

3. **Yes, FULL availability moves upward; the other arms are essentially flat.** On `P-a0`, FULL rises from 74.379% at epoch 200 to 76.440% at epoch 600 and 76.819% at epoch 2000. It is the lowest-availability arm only at epoch 200; from epoch 600 onward it slightly exceeds BASELINE, although it remains below DROP_C3. On `P-u`, FULL is still just 0.043 percentage point below BASELINE at epoch 600, then rises above it. DROP_C3 stays near 79.2%, and BASELINE stays at 76.317%. Thus the epoch-200 efficiency gain coincides with FULL serving fewer users, while the later availability recovery coincides with the EE advantage over DROP_C3 disappearing and reversing.

## Coalition-size detail (`P-a0`)

| Epoch | FULL selected-size counts across 10 decisions |
|---:|---|
| 200 | size 100: 10 |
| 600 | size 2: 3; size 5: 1; size 100: 6 |
| 1000 | size 2: 5; size 3: 1; size 4: 2; size 5: 2 |
| 1400 | size 2: 5; size 3: 1; size 4: 2; size 5: 2 |
| 2000 | size 2: 6; size 4: 2; size 5: 2 |

## Scope and validation

- No training was run. The evaluation restored the existing epoch 200, 600, 1000, 1400, and 2000 checkpoints for 2 seeds × {FULL, DROP_C3}; BASELINE remained the fixed external policy.
- Scope was world `V025_PROBE/world/3`, 5 anchors, nearest-eligible carrier, and the same 8-step tape prefix (`5 + 3`) that allowed the minimal evaluation to complete. Both existing catalogue anchors, `P-a0` and `P-u`, were retained.
- Evaluation used `/home/sat/mcrl-leo-handover/.venv/bin/python` with `PYTHONPATH` pointing to an isolated clean snapshot of Git commit `857b4bd1c1cc05f5bca0f883af9e028ff825d6df`. This kept the run on the defective path used by the checkpoints and isolated it from the concurrent coalition-path repair.
- The targeted evaluator shared the tape, catalogues, and physics cache across checkpoint epochs. It ran as one `nice -n 10` process, finished in 161.19 wall seconds, and emitted 300 receipts.
- Epoch-200 pooled EE, FULL availability, and FULL − DROP_C3 contrast match the already-completed minimal summary exactly for both `P-a0` and `P-u` (all checked deltas were zero).
- Statistical power remains minimal: 5 anchors × 2 seeds gives 10 FULL decisions per epoch. No confidence interval or generalization claim is warranted.

Artefacts: [report](/home/sat/mcrl-v025-pilot-ws/EPOCH-TREND-2026-09-09.md), [summary](/home/sat/mcrl-v025-pilot-ws/artifacts/v025-pilot-epoch-trend-20260909-PILOT_NOT_CLAIM/PILOT_NOT_CLAIM-epoch-trend-summary.json), [receipts](/home/sat/mcrl-v025-pilot-ws/artifacts/v025-pilot-epoch-trend-20260909-PILOT_NOT_CLAIM/PILOT_NOT_CLAIM-epoch-trend-receipts.jsonl). The summary and receipts have adjacent SHA-256 sidecars that pass verification.

---

**PILOT_NOT_CLAIM. This report must not be used as paper evidence or as evidence for or against C3.**
