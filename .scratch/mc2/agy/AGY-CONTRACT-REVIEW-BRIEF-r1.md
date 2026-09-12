You are an independent reviewer from a different model family, reading a research design with a fresh context. You have
file access. Read the artefacts themselves, not summaries. Report in English.

PROJECT: a multi-user LEO satellite beam-assignment reinforcement-learning study. One main learner (a three-head DQN
variant, deployed as each user's masked argmax of S = Q_B − η̃·Q_E) is trained with "Catfish" specialists that intervene
only during training. The study wants a genuine two-specialist ("multi-catfish") method: two sources with distinct
roles, each removable by retraining, each with a measurable contribution. A previous attempt put both specialists'
actions into one set-valued large-margin loss and the combined arm scored below both single-specialist arms (one training
seed, 24 evaluation episodes); that result stands.

READ, in this order:
1. /home/u24/papers/mcrl-leo-handover-mc2/.scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md
   (the design under review, revision r1)
2. /home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_teacher.py (T0, the large-margin losses)
3. /home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_tnext.py (T_NEXT, the second specialist)
4. /home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_credit.py (first 130 lines: what the counterfactual
   evaluator does) and /home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/env/step.py, method `evaluate_actions`
5. /home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_dev.py (the training loop `train_cf`, `_teacher_loss`)
6. /home/u24/papers/mcrl-leo-handover/.scratch/catfish2-successor/CONTROLLER-K8-FAIL-AND-SEARCH-EXHAUSTED-2026-09-12.md
   (the failed set-valued attempt)

ANSWER, each point with file:line evidence where possible:
A. Is this genuinely two specialists with distinct roles and information, or one policy renamed? Is each removable by a
   clean retrained drop-one?
B. Loss: does every margin row have exactly one target chosen by something other than the learner's own score? Can the
   second specialist dilute or cancel the first in either rule (v1, v2)? Is v1's "A-only" really identical to the frozen
   single-teacher arm?
C. Judge causality: is κ = (served count, B − η₀E) evaluated with the other users' executed actions a physically
   correct counterfactual? Can it misattribute reward or next state, advance or copy-contaminate the live RNG, or reward
   shedding users? Is it honestly labelled a fixed-price surrogate and not an EE claim?
D. Nulls and identification: what exactly does FULL-vs-B-null identify (T_NEXT's content vs the judge's own filtering),
   and what does it not? Is the null fair in compute and structure?
E. Forking paths: does running v1 and v2 concurrently with the declared selection rule (§7) and the fixed-order fallback
   inflate the chance of a false "survives" at the 3-fresh-seed confirmation? Is anything chosen after seeing data?
F. Claims: does §4 (relation to the original catfish method) claim anything that is not actually retained?
G. Anything that would make a positive DEV result uninterpretable.

FORMAT: first line exactly `VERDICT: NO-INVALIDATES` or `VERDICT: INVALIDATES-FOUND`. Then a numbered list of findings,
each tagged INVALIDATES (must change before the first counted run; give the smallest concrete fix) or NON-BLOCKING. Do
not propose new specialists, parameter sweeps, or extra versions. Keep it under 1,200 words.
