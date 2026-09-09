# The first valid C3 measurement: retrain on the repaired features and the rebuilt corpus

`PILOT_NOT_CLAIM`. Budget 90 minutes. **Completion beats completeness.** Every previous learned C3 result was measured under at least two confirmed defects and none of them counts. This is the first run where the interaction head can both see the mechanism and has been trained on the sizes where it lives.

## What changed since the last run
1. **Features.** The pairwise cross-gain terms now reach the encoder as an ordered 32-pair block with an explicit residual, instead of being summed into a scalar the contract forbids. Schema is `...-coalition-context-v2`.
2. **Corpus.** The previous corpus was 180 rows, every one of coalition size two, one per anchor. The rebuild adds occupancy-activation, aggressor-relief, beam-evacuation and nested-subset families across sizes 2 to 6 with several coalitions per anchor.

## What to run
Use the rebuilt corpus in `/home/sat/mcrl-v025-coalgen-ws`. Train the interaction head on it, then evaluate at the same minimal scale that has already been shown to complete: world 3, 5 anchors, nearest-eligible carrier, 2 learner seeds, arms FULL, DROP_C3 and BASELINE, plus S0 and the iterated unilateral optimum. Reuse the tape-prefix truncation that made the last evaluation finish, since a full 33-step tape build did not complete in 19 minutes.

Evaluate at **several checkpoints, not one**: at minimum epochs 200, 1000 and 2000. The previous run's headline came from epoch 200 and reversed sign by epoch 1000, so a single checkpoint is not interpretable.

## Report, leading with energy efficiency
1. **Pooled EE per arm at each checkpoint**, and FULL minus DROP_C3 as a relative difference. This is the number that matters.
2. **Availability per arm at each checkpoint.** The previous run's apparent gain coincided with FULL carrying the lowest availability of any arm, so an efficiency gain bought by serving fewer users must be visible immediately and must not be reported as a gain.
3. **The selected coalition size distribution**, since the mechanism lives at sizes 2 to 3 and the previous run selected 100 at epoch 200 and 3 at epoch 2000.
4. **A direct before-and-after against the old corpus.** Train an otherwise identical head on the original 180-row size-two corpus with the same repaired features, and report both. That isolates the corpus change from the feature change, which no measurement so far has done.
5. The interaction head's predicted versus exact `Psi` at the selected coalitions, since the previous head predicted `+2206.9` where the exact value was `-440.1`.

## Honest reporting
If the result is negative or flat, say so plainly and early. A clean negative on repaired machinery is worth far more than the four defective positives this project has already produced. Do not tune anything to improve it: change no threshold, sign, seed, horizon, price, service guard or acceptance rule.

## Constraints
Workspace `/home/sat/mcrl-v025-retrain-ws`, copied from the coalgen workspace once its corpus exists. Never modify any other workspace. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, or `/home/sat/mcrl-v025-codex-ws-engine`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Large files under `/home/sat/bigtmp`, never `/tmp`, a RAM-backed tmpfs here. At most 4 processes, `nice -n 10`.

Write `RETRAIN-RESULT-2026-09-09.md` in the workspace root and print it as your final message. Lead with one line: the FULL minus DROP_C3 relative difference at epoch 2000, and whether availability held.
