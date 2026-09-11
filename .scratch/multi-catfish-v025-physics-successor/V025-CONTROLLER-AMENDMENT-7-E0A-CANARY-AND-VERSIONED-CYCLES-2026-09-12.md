# Amendment 7 to Ruling 2 — shorten time-to-first-gradient: the E0a canary, versioned development cycles, MCRL-Dev-v0

Date: 2026-09-11 20:15 UTC (2026-09-12 04:15 Asia/Taipei). **Owner direction** (`gpt8.md`, copied to
`.scratch/reviews/external-gpt/gpt8.md`). It changes the **execution granularity of E0 only**. No Amendment 4 or 5 gate is
relaxed, S1 is untouched, and no development result is formal evidence.

## 1. Verified state before acting (controller re-checked the filesystem, git and processes at 20:07 UTC, not the progress files)

The owner's warning is recorded: `.scratch/dev-training/PROGRESS.md` was behind the filesystem after the quota interruption.
What is actually true:
- B1 engineering core is `63b02dc0`; the dev worktree `/home/u24/papers/mcrl-leo-handover-dev` exists at that base with
  **uncommitted** `cf_dev.py`, `cf_teacher.py`, `run_dev_e0.py`, `dev_e0_common.py`, `dev_e0_launch.py`, `dev_e0_proctest.py`,
  `dev_e0_refs.py`, `tests/test_cf_dev.py`, `docs/dev-e0/`.
- `tests/test_cf_dev.py`: **14 passed, 5 failed**, reproduced by the controller. Root cause confirmed: `assert_dev_seed`
  recurses into the composite DEV-NULL key `(9_231_000, k)` (`cf_dev.py:144 → :92 → :102`) and rejects the component `0`.
  The fix keeps the declared composite identity of Amendment 6 §3 and validates *base namespace + legal index*; seed semantics
  do not change; a leakage test for formal namespaces inside composite keys is added.
- No DEV training process exists on `sat`. A-real-floor R1 evaluation, B-real-floor R1 evaluation and B-real-floor R1
  calibration are all **24/24**; no oracle process is alive. T0 representability is complete and its lane is closed. Ceiling
  compute is complete.

## 2. E0a — the first-gradient canary (supersedes Amendment 6 §6's single batch)

The 300-episode budget stays as the **E0 ceiling**, but the first wave is smaller:
- Arms: **`D0/equal_share`, `D2-T0/equal_share`, `D2-null/equal_share`** only, paired DEV seed k = 0, **100 episodes each**,
  with a full 24-episode DEVVAL at episode 100.
- It answers exactly three questions: does the learner learn at all; does D2 teacher injection beat D0; does T0's information
  beat its matched null.
- `D3-T0` remains the required hard-imitation comparator but is **not** a first-gradient blocker; the lighting-price pair stays
  a labelled development diagnostic and is not scheduled ahead of E0a. Exact-DR learner arms keep their formal restriction.
- **E0b** decides, on DEVVAL evidence only: continuing to 300, adding `D3-T0`, and any change to α, τ, learning rate, gradient
  clipping or target cadence.

## 3. Rolling development = versioned immutable short cycles

Never hot-patch a running trajectory. The cycle is `MCRL-Dev-v0.1 → DEVVAL → v0.2 → DEVVAL → …`; each version records a new
config hash, its code commit or digest, the reason, the DEV/DEVVAL evidence behind it, the paired seed, and whether it is a
fresh start or an intentional resume from a checkpoint. No config is silently overwritten.

## 4. MCRL-Dev-v0 — the provisional algorithm, so development stops waiting for the final one

Frozen for development: the current ratio learner with three Q-heads; the existing 113-dim base input; the 28-action contract;
a **pluggable credit**; a **pluggable observation adapter**; the teacher interface (masked action + 28-score/advantage vector);
T0 = LP-prev(1,0) as the non-privileged anchor teacher; D2 soft on-student-state distillation as primary; D3 as the required
hard-imitation comparator; D0 and the matched nulls as controls. Still open and pluggable later, and **not** E0 blockers: the
B1 vs B2 observation and execution contract; the final credit; T_DR / T_SEQ / T_JOINT; the final catfish count.

## 5. B2 representability runs in parallel, blocking nothing

Dispatched now (the floored calibration cells are 24/24 and their npz carry `obs`, `mask`, `action`, `ref_action`, `adv`,
`adv_disallowed`, `adv_disallowed_floor`, `episode`, `step`, `user`; the JSONs carry `order`, `joint_ref`, `joint_chosen`).
The B2 screen decides the final observation / execution instantiation; E0a decides whether the shared learner and
teacher-injection kernel work. The two are never serialised again.

## 6. Measurement lanes close out

- Oracle: the three floored datasets it needed are complete; it re-derives the evaluation numbers, writes a **minimal branch
  adjudication artefact**, and holds A-floor calibration, R2, reverse order and the unfloored tie-ins. It no longer gates the
  learner.
- B1: finishes the lighting-price screen and its PASS/FAIL, re-runs the 13 mutants against `63b02dc0`, commits. Its verdict does
  not block the equal-share canary, and harness ownership stays with DEVHARNESS.
- Ceiling and T0: complete; no compute is restarted.

## 7. Launch policy for E0a

Launch as soon as: `tests/test_cf_dev.py` is fully green; the minimum E0 diff is committed; the fresh-context engineering review
of that diff is 0 INVALIDATES / 0 BIASES or its findings are fixed; the launcher smoke and the stop/resume identity test pass.
No new scientific gate, literature review, report polish or complete formal harness is a precondition of the first optimizer
step. S1 keeps every requirement of Amendments 4–5, including the complete formal review of all nine arms.
