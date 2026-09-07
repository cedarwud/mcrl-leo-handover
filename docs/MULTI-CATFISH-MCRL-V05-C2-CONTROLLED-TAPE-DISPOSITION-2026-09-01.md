# Multi-Catfish MCRL V0.5 controlled-tape disposition

Date: 2026-09-01  
Status: `CONTROLLED_TAPE_NATIVE_SUPPORT_INVALID`  
Claim ceiling: diagnostic only; no learning, training, TEST, or EE-efficacy claim

## Decision

The V0.5 exact common-physical-action tape is closed as a learning source.
The 41 completed shards are retained only as diagnostic evidence, and the
seven failed shards are retained as measured native-support failures.  No
completed V0.5 row may enter Q2 training, and the seven missing shards must
not be retried with the same program.

The sealed disposition receipt is:

- artifact:
  `artifacts/multi-catfish-v05-c2-controlled-tape-support-failure-20260901-r1/receipt.json`;
- file SHA-256:
  `4810d56e3bf1b6a10ccd55582d94fc1b3801732e0ebe2037accdb5b2b7ea5c95`;
- completed shards: 41/48;
- deterministic support failures: 7/48;
- persisted rows: 1,107 of the preregistered 1,296;
- target values inspected by the disposition seal: no;
- TEST opened: no;
- training performed: no.

## Why the tape is not repaired

The tape assumes that every non-focal physical action produced in reference
support \(A_M(k)\) also has one legal representation in candidate support
\(A_C(k)\).  A focal intervention can change coupled service and incumbent
state.  At a later dwell boundary the branch-local four-satellite window can
therefore differ, and a physical action in \(A_M(k)\) can be absent from
\(A_C(k)\).  The seven failures are deterministic examples of this
post-treatment support loss, not timeouts, memory pressure, random flakes, or
target-sign failures.

Skipping those rows, replacing their actions, or choosing a branch-specific
fallback would change the preregistered estimand after observing its support.
Forcing the physical action below the native 28-action contract would require
a new simulator-level intervention and would no longer be a small repair.

## Estimand correction

The deployment-relevant temporal estimand is a total effect under one frozen
continuation policy.  After the focal opening intervention, both branches use
the same frozen policy bytes and matched exogenous randomness, but each policy
acts on its own contemporaneous state and legal mask.  Branch-local downstream
action differences are causal mediators of the opening intervention; they are
not source contamination.

The V0.5 tape instead targets a controlled direct effect by pinning those
mediators to the reference branch.  Its common-support assumption does not
hold under the native environment, and even successful tape rows do not
represent the policy response that deployment would realize.

## Successor boundary

The only current successor hypothesis is a preregistered `C2-k1` total-policy
effect:

\[
\zeta_{2,u}^{(1)}=
\Delta t\sum_{i\in\mathcal U}\left[R_i^C(1)-R_i^M(1)\right]
-\lambda_0\Delta t\left[P_C^N(1)-P_M^N(1)\right].
\]

Both branches use the same frozen \(Q_1+Q_3\) continuation policy on their own
legal support.  The canonical ratio-of-sums EE, \(\lambda_0\), \(\kappa\),
three independent Q networks, direct unweighted \(Q_1+Q_2+Q_3\), one common
safe mask, and one argmax remain unchanged.

This successor is a hypothesis, not an authorized learner or an efficacy
claim.  Existing artifacts must first independently reproduce and seal its
continuation-invariance and scale evidence.  A fresh, outcome-blind,
source-only falsification gate must then pass before Q2 training is allowed.

## Cross-model review boundary

A fresh-context Sol Ultra review and an independent Opus Max review agreed
that the exact tape has a treatment-induced support problem and that the
deployment-relevant quantity is the total effect under a frozen policy.  Opus
Max further identified the first downstream offset as the only existing-data
candidate with materially better continuation invariance and lower target
scale.  Those model findings remain reviewer claims until the local T-0
recomputation receipt is sealed.

