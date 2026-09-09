# Controller adjudication — what belongs in the paper, and reversing the validity-certificate ruling
Recorded 2026-09-09, on the owner's challenge that the narrative is growing more complicated and that training detail may not belong in the paper or the deck. The challenge is correct and this document acts on it.

## 1. The test
A thing belongs in the paper only if a reader needs it to **understand the system, reproduce the result, or judge how far to trust it**. Everything else is internal, however carefully it was produced.

Being able to show that we were careful is not a reason to print something. The registers exist so that care is recorded **without** the paper carrying it.

## 2. Reversal: the ACM correction is not printed
Earlier today I ruled that the paired before-and-after verification of the adaptive-coding correction was a validity certificate and could appear in the paper, and the thesis merge opened a new section 5.2.4 to hold it. **That ruling is withdrawn.**

The reasoning that supported it fails its own test. The condition for printing a correction is that a reader would otherwise be misled, which happens when some published number came from the defective version. No number in the paper does: the audit of the paper lane found no stale result anywhere, and the drafted text already describes the corrected semantics. With nothing misleading to correct, printing the correction is development history in a results chapter.

**Ruling.** Section 5.2.4 is removed. The paper describes causal mode selection as the design, in the system model, once. The correction, its paired verification and its timing go to the internal deviation register, which is where the project's care is recorded. The register entry stays; the chapter section goes.

## 3. The general line, applied to the current merge
**In the paper.** The physics as it stands. The three components and how each is measured. The comparator contract. The results. The limitations that change how a result should be read.

**Not in the paper.** Defects found and fixed during development. Version numbers, amendment and erratum labels of internal declarations. Probe arms, workspaces, quarantined worlds and internal labels. Controller decision records. Any table row whose only function is to show that a distinction was considered.

**The deck carries less again.** A teaching deck needs the problem, the mechanism, the result and one honest slide on what the result does not show. It does not carry registers, conventions, or the reasoning behind conventions.

## 4. What this cuts from the drafted merge, concretely
* Section 5.2.4 and its four placeholder rows: **removed**.
* The deviation-register entry recording the correction: **kept, internal only**.
* Table I row B14, that a failed frame still consumes energy: **kept**, because it changes how the energy number is read and a reader cannot infer it.
* The fifth availability field, the transmitted-mode clearing rate: **kept as a definition**, because without it "availability" is ambiguous, but reported as one number rather than as a discussion of why four fields were not enough.
* The reconciliation of the service predicate with the crediting predicate: **kept**, because a reader who does not have it will misread every service figure.

The distinction running through those five: a reader needs the **rules** that govern how to read a number. A reader does not need the **history** of how we arrived at them.

## 5. Standing
This changes presentation only. No threshold, sign, seed, horizon, price, acceptance rule or claim condition moves, no run is authorised, and no gate is created. It reverses one presentation ruling made earlier the same day and records the reversal rather than quietly dropping it.
