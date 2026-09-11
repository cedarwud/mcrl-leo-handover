# E1 freeze, and the S1 configuration proposal — **requires owner sign-off before any S1 run**

Date 2026-09-12. Follows `.scratch/dev-training/E1-RESULT-2026-09-12.md` (`1dd29ab5`) and Amendment 10 §5.

## Part I — E1 freeze (controller, no owner decision needed)

E1 passed and neither reopen condition fired, so the development line closes here. What is frozen, unchanged from the
E0 freeze and now confirmed on fresh seeds k = 3, 4, 5:

**B1 execution contract + the current ratio learner + T0 = LP-prev(c = 1, m = 0) + D3 large-margin injection
(`m = 0.15`, `λ_E = 1.0`)**, with `equal_share` credit, `η` fixed at `η₀`, the 113-dim observation, and Adam / replay /
target-sync / network untouched. `D2-T0 τ = 0.3` remains the strongest soft comparator under Amendment 8 §3b's
outcome-independent tie-break, with no superiority claim.

**No further development runs are authorised on this line.** DEV seeds k = 6…9 stay reserved for Catfish-2 and
multi-teacher work. The next training on this line is S1, and S1 is formal.

## Part II — why S1's shape needs a decision rather than execution

Two documents disagree, and the disagreement is not mine to resolve.

1. **Amendment 6 line 74** says *"formal review of all nine arms remains mandatory before S1"*. That sentence was
   written when S1 was the D0–D4 ladder of Amendment 5 §I.5.
2. **Amendment 8** then converged the line deliberately: one primary mechanism, no new experiment family, D3-T0 as
   champion. Nine arms no longer exist to review.

So S1's arm list must be re-declared. Below is what I propose; **I have launched nothing.**

## Part III — the one-way door

S1 is the **frozen formal short screen** and it spends the **formal evaluation episodes** (`9_111_000+i` /
`9_112_000+i`), which Amendment 6 forbids ever using for development tuning. Once S1 runs, that set has been used.
`CONFIRM` (`9_311_000+i` / `9_312_000+i`) stays reserved behind it. This is why I am asking rather than proceeding.

## Part IV — the asymmetry you need to rule on: the baseline's training budget

The project's only win gate is **beat baseline MODQN eq. (16)** (standing ruling). But:

- the frozen MODQN eq-(16) checkpoint `e6b063ef…` was trained for **9,000 episodes**
  (`.scratch/RESULTS-REGISTRY.md:75`);
- S1's declared budget is **1000 episodes × 3 seeds** (Amendment 6).

The causal claim is unaffected — that is `D3-T0` vs `D0`, same tree, same budget, catfish on versus off. The **win
gate** is what the asymmetry touches. Three ways to handle it:

| option | what it means | cost |
|---|---|---|
| **A (proposed)** | Train **MODQN eq-(16) at the same 1000-episode budget** in the same tree as a same-budget win gate, **and** report the frozen 9,000-episode checkpoint as the published reference. Both numbers, stated separately. | +3 runs |
| B | Compare only against the frozen 9,000-episode checkpoint. Beating it at 1/9 the budget would be the stronger claim — and losing to it would be ambiguous, because budget and method are confounded. | +0 runs |
| C | Train `D3-T0` to 9,000 episodes for a budget-matched comparison at the baseline's depth. | ≈ 9 × the compute, and the E1 depth-decay note says the gap may be smaller there |

I propose **A**: it is three extra runs, it removes the confound, and it lets the paper say both "same budget, same
tree" and "against the published 9,000-episode baseline". Development evidence already points the right way —
`D3-T0` at ep 300 on DEVVAL is **+19.21 %** over the frozen baseline's DEVVAL figure (94.4 M) — but that is
development only and decides nothing.

## Part V — the proposed S1 arm list (6 trained arms + 1 rolled reference)

| # | arm | role | authority |
|---|---|---|---|
| 1 | `D0` | control, catfish off — the paired causal comparator | Amendment 4 |
| 2 | **`D3-T0`** | the frozen primary | E1 freeze, Part I |
| 3 | `D3-null` | matched hard null: same loss, margin, `λ_E`, schedule, masks, gradient path; target = seeded uniform random **legal** action | Amendment 4 conjunctive gate |
| 4 | `D3-XEP` | plausible-but-uninformative null: cross-episode T0 | **Amendment 12** |
| 5 | `D2-T0 τ = 0.3` | strongest soft comparator, no superiority claim | Amendment 8 §3b |
| 6 | `MODQN eq-(16)` @ 1000 | same-budget win gate | **Part IV, pending your ruling** |
| — | frozen `e6b063ef…` | rolled once, no training: the published 9,000-episode reference | Part IV |

3 seeds × 1000 episodes × 6 arms = 18 runs. From E1's measured rate (300 episodes ≈ 18 min at 9-way concurrency),
this is roughly **2.5–3 hours** in two batches. Cheap enough that the arm list should be decided on scientific
grounds, not cost.

## Part VI — what I am doing while you decide (no formal episodes touched)

1. Implement `T0-XEP` per Amendment 12: cross-episode T0, reference trajectory recorded once under **DEV-NULL**, its
   identity and sha256 recorded before any S1 run, plus the residual-leakage diagnostic (`t0_agreement` against the
   real T0).
2. Verify the `D3-null` and `MODQN eq-(16)` arms are wired and reproducible in the frozen tree.
3. Clean tests green, every newly named mutant individually red.
4. The **mandatory fresh-context review** of the S1 harness delta — required whatever the final arm list is.
5. Preflight everything at DEV depth only. **Nothing runs on the formal evaluation set until you sign off.**

## Part VII — the reading rules, all already fixed and none of them mine to move

- Amendment 4's conjunctive gate: `ρ ≥ 0.5 × R_repr`, 2/3 seed direction, service / rate floor, matched null, beyond
  seed noise — **screening / continue-eligibility only, not a paper claim**.
- Amendment 12 §3: `ρ_info` decides **how the claim is worded**, and only `ρ_info ≤ 0` triggers review.
- Amendment 12 §4: `T0-XEP` must earn the word "plausible" (`served ≥ 0.99`, `EE ≥ 0.98 × D0`) or the low-bar caveat
  stands unresolved and is reported as such.
- The E1 record's prospective note: a materially smaller gap at 1000 episodes is a legitimate outcome, not a bug.
