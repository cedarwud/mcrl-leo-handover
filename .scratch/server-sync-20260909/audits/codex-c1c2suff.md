# Prove or disprove that Q1 and Q2 can represent what they are named for

`DIAGNOSTIC_NOT_CLAIM`. Budget 2 hours. No training. This is the test that does not exist and whose absence let a defect survive.

## Why
An audit established three things by reading the code. The per-user heads receive only a **16-scalar Q1 vector** and a **22-scalar Q2 vector**; they are not given action identity, the background association graph, per-interferer cross gains, the coupled-power solution, or the projected network outcome. Meanwhile the contracted C1 target depends on **whole-network bits, joules and the preference term**, and the contracted C2 target depends on **complete future projected outcomes**.

And **every acceptance test answers "none"** to the question "which wrong C1 or C2 label would this reject". T1 labels its own fixture and recovers those labels. T2 never compares production labels against exact evaluator singletons. T3's fixture evaluator hard-codes bits and energy per arm and never calls C1 or C2 scoring at all.

The same compression defect was proved for the interaction head earlier today by constructing a collision. Do the same here.

## Task 1: construct a collision, or prove one cannot exist
Find two physically admissible states whose **complete encoded inputs are identical** — every one of the 16 Q1 scalars and every one of the 22 Q2 scalars, plus any auxiliary input branch the head actually receives — but whose **exact** C1 or C2 targets differ, computed through the production definitions in `src/mcrl/physics_v025/targets.py`.

Vary what the encoders discard: the identity and geometry of background users, per-interferer cross gains, which beams are shared, the coupled power solution, and the projected future outcome for C2. Hold every encoded scalar fixed.

* **If a collision exists**, report the two states, the identical encoded vectors byte for byte, and the two exact target values with their difference. That is a proof of insufficiency requiring no training, and it bounds the achievable error at `(difference/2)^2` in squared loss.
* **If you cannot construct one**, say so plainly and state what you varied and how exhaustively. Failing to find a collision is weak evidence, not a sufficiency proof, and it must be reported as such.

Report separately for C1 and for C2. They may differ: C2 depends on future projections, which is a larger hidden space.

## Task 2: write the acceptance test that is missing
Add a test that compares **production-generated C1 and C2 labels against exact evaluator singletons** on a small set of real anchors, with a tolerance stated and justified. It must **fail** on the proxy-label path (`PILOT_PRIMITIVE_SOURCE_FALLBACK = True` at `scripts/run_v025_pilot_c3.py:89`, where C1 becomes a bounded log link-gain ratio, C2 becomes three such ratios or an outage constant, and off-axis alternatives are labelled zero) and **pass** on the exact path.

Demonstrate the regression witness explicitly: fails with the flag set, passes with it cleared, fails again when it is restored. Report the assertion text that fires.

## Task 3: measure how much of the exact target the features can explain
On existing rows, fit a flexible model from Q1 alone to exact C1, and from Q2 alone to exact C2, and report held-out explained variance. Compare against a model given the discarded structure. A large gap bounds what any architecture on these features can achieve; a small gap says the compression is not the binding constraint here even if a collision exists.

## Constraints
Workspace `/home/sat/mcrl-v025-c1c2suff-ws`: `cp -a /home/sat/mcrl-v025-c1c2-ws` if it exists, else from `/home/sat/mcrl-v025-pilot-ws`; then `rm -rf .git`, `git init`, commit. Never modify any other workspace; several jobs are editing them. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, or `/home/sat/mcrl-v025-codex-ws-engine`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Large files under `/home/sat/bigtmp`, never `/tmp`, a RAM-backed tmpfs here. Two processes maximum, `nice -n 15`.

Change no threshold, sign, seed, horizon, price, service guard or acceptance rule. Adding a test that can fail is not a change to the acceptance criteria; it is the enforcement the criteria already assume.

Write `C1C2-SUFFICIENCY-2026-09-09.md` in the workspace root and print it as your final message. Lead with whether a collision was found for C1 and for C2, then the regression witness result.

## Report file name, restated because a previous attempt did not produce it
Write your findings to a file named **exactly** `C1C2-SUFFICIENCY-2026-09-09.md` in the workspace root. That workspace was copied from an earlier audit and may contain unrelated reports; **do not edit or extend any of them**, and do not treat any existing file as your output. Create the named file fresh. If you finish without creating it, the run counts as failed regardless of what you print.
