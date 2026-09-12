# Controller ruling — what counts as the CURRENT physics, and the MC2 paper symbols

Date 2026-09-12. Raised by lane C (paper) against a wrong line in my own brief. Recorded because the same error would
otherwise propagate into the thesis rewrite.

## 1. The current physics is what the code runs — segment-anchored recurrence power is NOT legacy

My lane-C brief listed "legacy physics (segment-anchored recurrence power as the current model, old service rule)" among
the things not to port. **That is wrong about the power model.** In force, and used by every E0 / E1 / k8 number:

- segment-anchored recurrence link power (`src/mcrl/env/link_budget.py:213`, `src/mcrl/env/step.py:135-142`);
- service = a legal chosen action with a feasible link (`p ≤ p⁺`), **no beam cap** (`src/mcrl/env/service.py:221-254`);
- the physical finding behind it still stands (`.scratch/…/segment-anchored-power-finding-2026-09-08`, with the 09-11
  anchor ablation showing the 19.8 % gap is not a reconnection premium).

What **is** legacy and must not be ported:

1. the **frozen demo simulator** `~/demo/leo-beam-sim` — per the single-authority register §3 it implements the old
   service rule, the LC-SRS C3 and its own power model, and it is the thing that must be labelled legacy if shown;
2. the **closed V0.25 stage-C route's** capacity penalty and its objective `F = B − η_ref·E − Φ` / `G = F + κ·Φ`;
3. the old `C1/C2/C3` head narrative as a *route* (the three value heads in the code stay).

Consequence: nothing needs regenerating, and the MC2 paper deltas describe the physics exactly as the code runs it.

## 2. MC2 paper symbols (delta-level; the owner still merges into the one symbol table)

- deployed score stays `S = Q̃_B − η̃ Q̃_E − λ Q̃_H` (λ = 0) — matches the code and the E0/E1 records;
- the two specialists are `π^A` (anchor, T0) and `π^F` (foresight, T_NEXT), with actions `a^A` and **`a^F`**;
  `a^B` is rejected because `B` already denotes bits and would collide on the judge line;
- the judge key stays `κ = (n_served, B − η₀E)` and may not be re-scoped in this delta;
- code and cell names keep the letter `B` for the foresight source (`{A,B}`, `B-only`, `B-null`); the mapping
  `code B ↔ π^F` is stated once in `SYMBOL-DELTA.md`;
- `§10.7`'s "112 維" is corrected to 113 (112 + normalised remaining steps); `§10.15` is left open for the owner.

## 3. Two contract text corrections made at the same time (no rule changed)

- §0 no longer states "the stronger teacher stopped binding" as fact: the k8 ordering is the measurement, the dilution
  mechanism is the proposed explanation and was never causally isolated.
- §1 labels the two k8 numbers that are not in the adjudication table (`T_NEXT-only` joules ×0.856, 53.4 vs 62.6 beams
  against `D0`) with their real source, `LANE-M-K8-RESULT.json`, and with "one seed, ep 100".
