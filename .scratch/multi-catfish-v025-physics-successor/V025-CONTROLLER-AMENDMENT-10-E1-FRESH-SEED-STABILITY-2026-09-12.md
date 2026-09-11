# Amendment 10 to Ruling 2 — E1 declared: a fresh-seed stability screen, not a second E0

Date: 2026-09-11 23:35 UTC. **Owner decision.** E1 starts now. It opens no design search, changes no Amendment 4 or 5 gate, and
produces development evidence only.

## 1. What E1 is

A stability screen of the already frozen provisional algorithm on **clean development seeds**. It is not a second exploration
round: no sweep, no new mechanism, no new null family, no architecture change.

## 2. The declaration

- **Seeds: DEV k = 3, 4, 5.** k = 0, 1, 2 took part in E0's development and selection and are not reused. k = 6…9 stay reserved
  for Catfish-2, multi-teacher work, or genuinely necessary later development.
- **300 episodes per run, fresh start.** Not 500 or 1000: the exploration schedule is derived from the total episode budget, so
  changing the length would move the ε decay with it and silently change a hyperparameter. 300 keeps the frozen learner schedule
  exactly.
- **Three arms only**: `D0`; `D3-T0`, the frozen provisional primary; `D2-T0 τ = 0.3`, the strongest soft comparator.
- **`D3-null` is not re-run.** Its causal task is finished on k = 0, 1, 2 with extremely consistent results (−39 to −55 %, 0/24 on
  every seed); repeating it would only re-show that a random hard teacher is bad. The **plausible-but-uninformative second null**
  is declared before S1, not improvised inside E1.
- **The backbone is frozen**: the current 113-dim observation, `equal_share` credit, `eta` fixed at `eta_0`, the current ratio
  learner, D3 with `m = 0.15` and `λ_E = 1.0`, D2 with `τ = 0.3`, and Adam, replay, target-sync and network untouched. B2 stays
  closed, exact-DR stays closed, and no Dinkelbach update is slipped in.
- **Readouts at 100 / 200 / 300, but only ep 300 is the decision checkpoint.** The earlier readouts exist to catch divergence,
  a bug or a catastrophic QoS failure. No configuration may change because an intermediate reading looks good: no checkpoint
  shopping.

## 3. The E1 reading rule (development; no formal claim, no confidence interval)

Reusing the screening philosophy that already existed in Amendment 4, without making a formal claim:
- **Direction**: `D3-T0` beats `D0` on at least **2 of the 3 fresh seeds** with the seed mean in the same direction.
- **QoS floors**, the existing numbers: served not worse than the comparison arm by more than **−0.5 pp**, `p10 ≥ 0.5 ×` the
  comparison arm's, `bits ratio ≥ 0.95`.
- `D2-T0 τ = 0.3` is read the same way, as the strongest soft comparator.
- **No retuning on a small D2-versus-D3 difference.** D3 is the pre-frozen primary; E1's first purpose is to confirm it is stable
  on fresh seeds.

## 4. The only two conditions that reopen the design

1. `D3-T0` fails even the Amendment-4-style continuation direction or the QoS floors on the fresh seeds; or
2. `D2` shows a very consistent, substantive, across-the-board advantage on all three fresh seeds, large enough to mean the
   primary was chosen wrongly rather than a seed fluctuation.

In either case the next step is a **controller review**, not inferring new hyperparameters from the result.

## 5. Expected path, and what runs beside it

The normal path is `k3/k4/k5 × 300 → E1 freeze → S1 preparation`, not `E1 → sweep → E1`.

**Catfish-2 does not wait for E1.** Its Stage-0 discovery runs in its own lane, worktree and workspace. If a second qualified
source is found, it becomes a **separate versioned multi-teacher integration branch**; it may not retroactively change this
single-source E1's definition. That keeps one quickly converged trainable backbone and one exploration line for the second
catfish running at the same time.
