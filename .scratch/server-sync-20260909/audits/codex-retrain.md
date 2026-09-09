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

## A defect found after this task was written; you must handle it
An audit found `PILOT_PRIMITIVE_SOURCE_FALLBACK = True` at `scripts/run_v025_pilot_c3.py:89`. Under that flag the per-user components are **not** trained on their contracted exact targets: C1 is labelled from a bounded log link-gain ratio, C2 from three such ratios or an outage constant, and off-axis alternatives are labelled zero. The exact evaluator path immediately below is dead code while the flag is set.

Measured on ten saved decisions, exact C1 averaged `+34.990` and exact C2 `-151.063`, total `-116.073`; the learned values were `+15.962`, `+90.539` and `+106.501`. **C2 has the wrong sign**, the total misses the exact cancellation by `+222.573`, and eight of ten totals have the wrong sign.

The flag exists only in the pilot script; the engine workspace does not contain it and the formal matrix path uses the exact `network_objective` and `c1_difference_surplus`. So this is a pilot-only cost compromise, not a defect of the production path. **But your workspace is a copy of the pilot tree, so you inherit it.**

**What to do.** Run the measurement **both ways** and report them side by side:
* **exact targets**, with the flag disabled, which is the contracted definition;
* **proxy targets**, with the flag as inherited, which is what every previous pilot result used.

If exact targets are too expensive at the full corpus, reduce the anchor count rather than falling back to proxies, and say what you reduced. Report the cost per exact C1/C2 label so the compromise is quantified rather than assumed. If you cannot run the exact arm at all, say so plainly and report only the proxy arm labelled as such; do not present a proxy result as the measurement.

This matters more than the coalition-size change: with C2 carrying the wrong sign, the additive score that the selector maximises is wrong before the interaction head contributes anything.
