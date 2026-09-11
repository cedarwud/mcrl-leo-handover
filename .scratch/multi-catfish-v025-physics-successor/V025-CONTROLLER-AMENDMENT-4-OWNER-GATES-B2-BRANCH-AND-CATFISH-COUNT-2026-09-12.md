# Amendment 4 to Ruling 2 — owner decisions: the screening gate, B2 as a conditional branch, the catfish-count definition; b0 cleanup

Date: 2026-09-12 ~01:30 Asia/Taipei (17:30 UTC 2026-09-11). **Owner decisions**, recorded before any learner training in the
new line and before B-real or the A-real rate-floor replay exists. Supersedes the pass criteria in Ruling 2 §3, Amendment 1
§4 and Amendment 3 §4, and the numeric thresholds in Ruling 2 §4 as definitions.

## 1. The learner gate is a screening gate, not a paper threshold

Owner: "同意 ρ ≥ 0.5 × R_repr，但只作為短 episode / mechanism screening 的『繼續資格』，不是最終論文成功標準。"

A mechanism arm **may continue** (to the next stage of the ladder, or to longer runs) only if **all** of the following hold on
the 24 evaluation episodes:
1. `ρ ≥ 0.5 × R_repr`, where `ρ = (EE(learner) − EE(rule)) / (EE(teacher) − EE(rule))` and `R_repr` is the teacher's
   representability (Amendment 3 §3). Reason: `R_repr` removes the part of the teacher's gain the student's observation cannot
   express; the learner is asked for half of what is expressible, not for the unreachable full gain.
2. **Direction**: the arm beats its comparison on ≥ 2 of 3 same-index seed pairs, with the seed-mean in the same direction.
3. **Service and rate floor**: served fraction non-inferior (−0.5 pp, cluster bootstrap) and the per-user rate floor preserved
   (no throughput-degenerate flag: p10 ≥ 50 % of the rule's p10 on the same set, and bits ratio ≥ 0.95).
4. **Matched null**: a teacher arm beats its matched random / null-teacher control under the same rule (items 2–3).
5. **Beyond seed noise**: an EE gain inside the between-seed spread is not a method success even if items 1–4 hold.

This is continue-eligibility for short-episode mechanism screening. **Paper claims** are made later from confirmation runs with
more seeds and confidence intervals; the 50 % screening gate is never quoted as a publication threshold.

## 2. B2 is a pre-approved conditional branch; B1 keeps priority

Owner: "現在不要直接進 B2；預先核准成『有條件分支』。優先維持 B1 的原 deployment contract。"

Reason recorded: a simultaneous, observation-only rule (LP-prev(1,0): eval +6.66 %, cal +4.75 %) already shows room under
the current execution contract, so there is no case for changing the contract before the numbers. **B2 may be entered only
if all hold**, read on the complete oracle table:
1. B-real exceeds A-real by ≥ **+3.3 percentage points** of pooled EE over `A m=2dB` (the declared threshold), **after** the
   rate-floor replay of both cells;
2. service and the rate floor are preserved in both cells;
3. the extra value is representable from the B2 student's observation (T_SEQ's `R_repr ≥ 0.5` for at least one clone trained on
   the augmented observation that includes earlier users' same-step choices).
When entered, B2 is declared explicitly as an **execution-contract change**, and B1 stays in the experiment as its comparator —
never silently replaced.

**Current oracle fact (verified, `.scratch/h4-probe/PROGRESS.md` §T2-11):** A-real(R1) on the 24 evaluation episodes, parity
max |Δ| = 0: pooled +5.93 % over `A m=2dB` (paired +5.67 ± 0.88 %, 23/24), served 0.99925, but per-user rate **p10 = 27.5
Mbit/s = 0.27 × the rule's** — throughput-degenerate; the simultaneous best response herds (66–99 of 100 users move per step,
~4-step oscillation). Its raw EE gain therefore authorises **neither B1 nor B2**; the decision waits for the rate-floor replay
and the complete B-real cells.

## 3. How many catfish: three conditions, measured; the numbers are diagnostics

Owner: "三層結構確認，但不要把 Ruling 2 §4 現在的數字門檻原封不動定成最終定義。"

A teacher is one catfish only if it satisfies all three:
- **(a) frontier non-dominance** on (pooled EE, served, per-user rate p10) against the other retained teachers;
- **(b) substantive distinctness** from every other retained teacher on shared student-observable states;
- **(c) an independent positive marginal value** once it is added.

For (b), the Ruling 2 §4 numbers (action disagreement ≥ 25 %, out-of-95th-percentile share ≥ 0.2) are **pre-screen
diagnostics only**, not the definition — a small number of high-value different decisions can matter. Distinctness is
measured with the saved 28-action advantage vectors as well: **value-weighted disagreement** — on shared states, the mean
advantage loss, under teacher *i*'s advantage vector, of taking teacher *j*'s action instead of *i*'s (and symmetrically),
normalised by the scale of *i*'s advantages — and **advantage separation** — the distance / rank correlation between the two
teachers' advantage vectors on the same states. Exact formulas are fixed in the multi-teacher declaration before any
multi-teacher arm runs.

**The count is decided by causal marginal value**: after the best multi-teacher arm is established, drop-one arms; each
teacher's removal must cause a **reproducible EE loss beyond the experiment's resolution** — at confirmation, a confidence
interval excluding zero, or a practical margin pre-specified in that declaration. No count is preset; 1, 2, 3 or 4 catfish are
all acceptable outcomes.

## 4. b0 cleanup (executed)

Owner authorised removing the worktree while keeping the branch and the archive tag. Executed 17:30 UTC:
`git worktree remove /home/u24/papers/mcrl-leo-handover-b0` (worktree was clean). Branch `b0/corrected-baseline-20260911`
and tag `archive/b0-corrected-baseline-20260911` remain (audit: `.scratch/b0-corrected/B0-BRANCH-EQUIVALENCE-AUDIT-2026-09-11.md`).
