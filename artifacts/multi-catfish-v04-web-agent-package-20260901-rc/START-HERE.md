# Multi-Catfish MCRL V0.4 Web-agent package

**Snapshot:** 2026-09-01 · **Purpose:** explain the current algorithm, write
the method/paper, and plan figures/decks. This package contains no five-arm
outcome and authorizes no training.

## Read this first

1. `CLAIM-STATUS.md` — the single source of truth for confirmed, pending, and
   prohibited claims.
2. `SUPERSESSION-MAP.md` — which V0.3 statements remain invariant and which
   C3/status statements V0.4 replaces.
3. `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` — source authority snapshot.

Then follow the smallest relevant path:

| Need | Read |
|---|---|
| Understand the method | `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md`, then `docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md` |
| Write the paper/method section | the V0.3 algorithm spec, paper-authoring contract, and presentation layer |
| Draw system/algorithm figures or slides | the figure-deck handoff, presentation layer, and active symbol table |
| Understand current C3 | the V0.4 victim-burden decision, screen result, confirmatory preregistration, and confirmatory result |
| Prepare the next experiment | the V0.4 five-arm preregistration only; its outcome is intentionally absent |

## Invariant algorithm in one page

The endpoint is the canonical system ratio of sums

\[
\eta=\frac{\sum B}{\sum E}.
\]

One sealed physical anchor creates a candidate/reference pair that differs in
one focal user's action. The same intervention is decomposed into three
non-overlapping EE-surplus views: **C1/Q1** focal-now, **C2/Q2**
everyone-later, and **C3/Q3** non-focal-now. These are training views of one
physical intervention, not three competing deployment agents and not three
independent final objectives.

There are exactly three independent Q networks. Each route learns its own
pairwise zero-bootstrap surplus target. Deployment computes

\[
\Phi(s,a)=Q_1(s_1,a)+Q_2(s_2,a)+Q_3(s_3,a),
\]

then applies one common safe-action mask and one masked `argmax`, executing
one Main action. There is no auction, coordinator, vote, joint decoder,
second argmax, or post-training override.

V0.4 changes only the C3 causal observation/source. C1 retains the EXP/ACRM
lineage; C2 retains the temporal-fork role and target; Q1/Q2 remain the
authenticated V0.3 rung-10 heads. C3 uses lagged action-aligned victim-rate
and satellite burdens, a fresh local scorer, and the sealed gate-selected
rung-100 Q3. The production candidate still has exactly three networks and
the same direct-sum deployment rule.

## Evidence boundary

The V0.4 C3 learnability gate passed and the frozen rung-100 C3 head passed
the preregistered fresh TRAIN-only FULL-versus-DROP-C3 confirmatory endpoint;
the exact receipts are under `evidence/c3-confirmatory/`. This confirms the
declared marginal C3 result under that block. It does **not** confirm C1, C2,
or FULL versus the frozen Main MODQN baseline. The separately preregistered
five-arm evaluation (FULL, DROP_C1, DROP_C2, DROP_C3, MAIN) has no result in
this package. Do not turn the confirmed C3 result into a claim about the full
three-Catfish system.

All snapshots and receipts are listed in `PACKAGE-MANIFEST.md` and verified by
`MANIFEST.sha256`. The checkable completion criterion is: a fresh reader who
starts here can state the three-route algorithm, the V0.4 C3 change, the
confirmed-versus-pending claim boundary, and the required paper/figure
authority without opening an archived V0.3 package.
