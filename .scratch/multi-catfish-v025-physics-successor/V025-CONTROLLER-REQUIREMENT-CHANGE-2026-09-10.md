# Requirement change — the bar moves from three individual gains to the joint span

**2026-09-10, ~07:00 UTC. Recorded by the controller. This is an owner decision about what
the paper claims, not a change to any estimand, formula, sign, threshold, seed, horizon,
price, guard or acceptance rule. Nothing sealed is modified.**

## The owner's words

> "應該是說3個加起來要有明顯的提升，如果真的有1、2個是提升的比較少也只能接受，最好是只有1個
> 或沒有，但是不能3個加起來還提升很少，那就感覺沒什麼意義了"

**The bar is now `FULL - BASELINE` substantial.** One or two routes contributing little is
acceptable; ideally at most one does. What is not acceptable is all three together amounting
to very little.

## The sequence, recorded in full because the timing matters

| When | Bar |
|---|---|
| earlier | each of C1, C2, C3 must individually raise EE; a "C3 negative result" is not acceptable |
| then | the **ordering**: baseline + each of C1/C2/C3 individually positive, and FULL > any pair > control |
| then | "如果只能提升1% 那就沒有什麼意義" — 1% is not a meaningful result |
| then | "不用超過古典搜尋也沒關係" — the full system need not beat classical search |
| **now** | **the three together must be substantial; individual positivity is preferred, not required** |

**This change was made after `RESIDTOGGLE` reported.** The owner had the residual-ceiling
number, `+5.62%` demand-capped, in hand. I record that plainly.

It is nonetheless not outcome-selection in the sense the non-negotiables forbid, and the
distinction is worth stating precisely:

- **What is forbidden** is tuning a formula, sign, threshold, seed, horizon, price or
  acceptance rule against an observed result, or selecting a rerun by its outcome. None of
  those has happened. No estimand has changed; every measurement already taken stands exactly
  as reported, under the reading rule declared before it ran.
- **What changed** is which claim the paper makes. That is the owner's to set, and it was set
  by narrowing an ambition, not by moving a pass mark on a fixed test. The pre-declared 10%
  and 5% screens for the residual **still stand as stated**, and `RESIDTOGGLE` is still
  reported against them: `+5.62%`, below astra's 10%, above fable's 5%, with fable's second
  half still pending.

I am recording the timing because a reader is entitled to it, not because I think the change
is improper.

## What this changes in the work

**Load-bearing before, much less so now:**
- Whether C3 alone clears a screen. It is now a component of a span, not a gate.
- Whether each route can independently change a committed decision. Still worth knowing —
  `C3REACH` continues — but no longer decisive.
- The panel spine's move set (erratum 16). Still a real design defect that must be re-declared
  before any panel, but it no longer determines whether the claim survives.

**Load-bearing now:**
- **`FULL - BASELINE` on the reported numerator.** Not measured. `FULLSPAN` dispatched at
  07:01 UTC to measure it on `RESIDTOGGLE`'s own catalogue, anchors, guard, tie-break,
  provisioning and pooling, adding only the committed nearest-eligible incumbent as a third
  selector, so the span decomposes as
  `BASELINE -> ADDITIVE_ONLY -> WITH_RESIDUAL`.
- The **exact/oracle-to-learned gap**. Every span measured this way is a **ceiling**: it hands
  the selector exact terms rather than predictions. What learned heads recover from that
  ceiling is a separate measurement and must never be conflated with it.
- Whether the corpus can carry the declared targets at all (`EXACTGEN`, `C1REAL`).

**Unchanged:**
- `ALL_NEUTRAL_CONTROL` is never relabelled `BASELINE`. The span's reference is the committed
  nearest-eligible incumbent; the all-neutral arm is a different object and keeps its name.
- No TEST split. No tuning against results. No outcome-selected rerun. Sealed artefacts and
  frozen manifests are not rewritten.
- Every finding recorded today stands unchanged, including the ones that make the work harder.
