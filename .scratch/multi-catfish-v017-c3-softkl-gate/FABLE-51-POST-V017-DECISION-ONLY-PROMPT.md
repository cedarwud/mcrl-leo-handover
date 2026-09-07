Act as a fresh scientific adjudicator. Do not use tools, read files, edit, run,
train, or ask questions. Judge only from the verified facts below.

Goal: exactly three independent Q heads, one native safe mask, unweighted
Q1+Q2+Q3, one final argmax, one executed action. C1 and learned C2 stay frozen.

Facts:
1. Exact ZR C3 oracle in integrated Q1+exact-Q2 context produced
FULL-minus-DROP-C3 +0.9383% ratio-of-sums EE on four fresh TRAIN worlds; every
world was positive, service equal, bits -5.70%, energy -6.57%.
2. V0.17 kept the same ZR target but trained a B402 action-set MLP using masked
full-action SoftKL. All three frozen initialisations failed: pivotal agreement
.149/.217/.429, stable preservation .978/.974/.894, supported-change agreement
.782/.743/.577. The frozen stop closes retry, tuning, seed/rung selection,
rescaling, threshold relaxation, support masking, and further B402 expansion.
3. B402 scores each candidate from its local action features plus mean/max over
the legal ACTION set. The ZR teacher instead aggregates candidate-specific
effects over a VICTIM USER set, counts all victim harm, and counts victim benefit
only when a physical compatibility condition holds.
4. A predecision detached Q1+Q2 joint reference is already allowed by contract;
it is a non-executed context pass. The environment still receives only the one
final action vector.
5. Exact realised victim effects are unavailable before action because the
observation and physics keyed fading fields differ. A deployable learner may
estimate conditional expected victim effects from current geometry, nominal
fading=1/shadow=0 coefficients, reference loads, required-power headrooms, and
observed SINR proxies. It may not receive realised ActionEvaluation outputs,
oracle targets, future data, or the physics fading draw.
6. Exact compatibility may be reconstructed from predecision opening bits,
physical reference/candidate beam keys, peer maximum required powers, active
beam sets, and recurrence-power algebra, but this equivalence must first pass
an every-legal-action exact-match gate.
7. A prior PNFE target produced -11.06% C3 direction, with bits -5.40% and energy
+6.37%; its gate also had two contract defects. It must not be casually retried.

Candidate A: one victim-relational Q3. A shared scorer predicts d_hat(u,a,v),
then the fixed ZR algebra sums min(d_hat,0)+g(u,a)max(d_hat,0) across victims and
centres on the detached reference. It remains one Q3 and one optimizer.
Candidate B: context-gated scalar Q3 without explicit victim aggregation.
Candidate C: analytic decision-time oracle-like Q3.
Candidate D: change the C3 target.
Candidate E: stop the three-head method structurally.

Return a compact ranking and answer three questions: Did V0.17 falsify ZR or
only B402? Is Candidate A scientifically coherent without becoming a
coordinator? What is the single smallest pre-outcome gate before any new learner?
The gate must use fresh TRAIN only, no optimizer, no episode training, no TEST,
and hard-stop on any exact compatibility mismatch. Do not propose forbidden
tuning, route weights, sign flips, a second executed decoder, or two-head fallback.

End with exactly one token on its own line:
GO_RELATIONAL_ZR_GATE
GO_CONTEXT_GATED_C3_GATE
GO_ANALYTIC_C3_GATE
GO_NEW_TARGET_C3_GATE
STOP_THREE_HEAD_STRUCTURALLY
