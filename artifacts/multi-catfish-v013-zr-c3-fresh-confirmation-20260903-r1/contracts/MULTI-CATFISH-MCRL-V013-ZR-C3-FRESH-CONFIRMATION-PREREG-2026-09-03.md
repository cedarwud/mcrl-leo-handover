# Multi-Catfish MCRL V0.13 ZR-C3 fresh-world confirmation preregistration

Status: **FROZEN BEFORE OUTCOME ACCESS**  
Executable contract receipt SHA-256: `92787a29ff7639fc1f75af9c35e263195537c2b6fbbd9d7ff1263937d0c02742`
Scope: TRAIN-development oracle confirmation only; no learner, no optimizer,
no TEST, no episode training, and no efficacy claim  
Decision: confirm the unchanged V0.12 ZR teacher against `DROP_C3` on four
new worlds under a prospectively revised acceptance structure

## 1. Prior evidence and purpose

V0.12 remains formally
`STOP_C3_ORACLE_REDESIGN_REVIEW_SEAM`. Its frozen ZR gate failed because
active-satellite steps increased from 304 to 310, pooled and within both
worlds. That decision is not reopened here.

The same V0.12 panel nevertheless produced the following verified TRAIN-world
oracle-development evidence for `FULL_ZR` relative to `DROP_C3`:

- ratio-of-sums EE: `+0.631955529%`;
- total bits: `-4.424547737%`;
- total trajectory energy: `-5.024749087%`;
- service: unchanged at `6000/6000` user-steps;
- active-beam steps: `-129`;
- active-satellite steps: `+6`;
- EE was positive in both worlds, with two of three positive Q1 lineages in
  each world; and
- all formula, mechanics, support, exposure, and current-slot joint-support
  checks passed.

Fresh-context Fable 5.1 Max and Sol Ultra independently recommended the same
prospective treatment: preserve the V0.12 STOP, keep ZR unchanged, retire HR
from active candidate selection, and replace the two trajectory proxy-count
hard stops symmetrically with an exact trajectory-energy hard stop. Beam-step
and satellite-step totals remain reported diagnostics.

This gate asks only whether the unchanged ZR oracle direction reproduces on
fresh TRAIN worlds under that revised acceptance structure. V0.12 worlds are
consumed development evidence and do not enter this decision.

## 2. Immutable architecture and objective

The architecture remains exactly three independent 28-action functions, one
common safe mask, the left-to-right unweighted sum `Q1 + Q2 + Q3`, one
smallest-native-index masked argmax, and one executed Main action. There is no
coordinator, auction, voting rule, learned or fixed head weight, sign flip,
mixer, second mask, or post-training override.

The only final objective remains canonical ratio-of-sums energy efficiency,

\[
\eta=\frac{\sum_{e,t,u}\Delta t\,R_{e,t,u}}
           {\sum_{e,t}\Delta t\,P^N_{e,t}}.
\]

C1/Q1 and execution-equivalent OPS3 C2/O2 are read-only and unchanged. The
three Q1 checkpoints, OPS3 formula/runtime, `lambda0`, `kappa`, `Delta t`, TLE
archive, simulator physics, safe mask, action semantics, tie breaking, and
keyed-fading rules are identical to V0.12. No learner or optimizer is present.

## 3. Frozen C3-free reference and unchanged ZR target

At every arm-owned state, compute Q1 and exact OPS3 O2 once and define for each
user

\[
b^0_u=\min\arg\max_{a\in\mathcal A_u^{\rm safe}}
\{Q_{1,u}(a)+O_{2,u}(a)\}.
\]

For focal user `u` and legal action `a`, let

\[
c^a=b^0_{-u}\oplus a.
\]

Evaluate `b0` and every `c^a` using exact canonical current-slot physics under
one keyed common-random field. The V0.12 compatibility signature
`Gamma(c)`—served-user Boolean vector, ordered active-beam set, ordered
active-satellite set, canonical per-beam RF-power vector, and total network
power `P^N(c)`—is byte-for-byte unchanged. Define

\[
g_u(a)=\mathbf 1\{\Gamma(c^a)\equiv\Gamma(b^0)\}.
\]

For every non-focal user `v`, define

\[
d_{uv}(a)=\Delta t\,[R_v(c^a)-R_v(b^0)].
\]

The only active C3 oracle is the unchanged V0.12 ZR target

\[
z^{R}_{3,u}(a)=
\sum_{v\ne u}\min\{0,d_{uv}(a)\}
+g_u(a)\sum_{v\ne u}\max\{0,d_{uv}(a)\},
\qquad
O^{R}_{3,u}(a)=\frac{z^{R}_{3,u}(a)}{\kappa}.
\]

The reference entry is exact zero; illegal entries are zero behind the one
common mask. Victim loss always counts. Positive spatial redistribution counts
only under exact current-slot zero-marginal-energy support. ZR contains no
focal rate, numerical power or energy, future term, `lambda0`, outage reward,
or handover reward.

The production-form arm actions are

\[
a^{D}_u=b^0_u,
\qquad
a^{Z}_u=\min\arg\max_{a\in\mathcal A_u^{\rm safe}}
\{Q_{1,u}(a)+O_{2,u}(a)+O^{R}_{3,u}(a)\}.
\]

HR is not an arm, fallback, alternative, or selection opportunity in V0.13.
It is retained only in the archived V0.12 record and is not evaluated here.

## 4. Frozen mechanics and current-slot support

The runner must fail closed unless every V0.12 identity and purity condition
remains true, including:

- the common mask, exact reference zero, illegal zero, finite surfaces, and
  smallest-native-index argmax;
- focal-only unilateral replacement;
- immutable keyed field, environment, RNG, Q1, and O2;
- every positive ZR entry has `g=1`;
- every changed production action has strictly positive ZR credit and `g=1`;
- formula-identity residuals are no larger than
  `1024 eps * max(1, |left|, |right|)`; and
- no arm consumes an outcome or another arm's action.

At every exposed anchor, compare the production joint action to `b0` using
exact current-slot physics. It must add no active beam or active satellite and
must satisfy `P^N(a^Z) <= P^N(b0)` under the same floating identity tolerance.
These are mechanism-support checks at a matched current state. They are not
the trajectory-level beam/satellite count diagnostics defined below.

## 5. Frozen TRAIN panel

- split: TRAIN only;
- fresh world seeds: `2026104901`, `2026104902`, `2026104903`,
  `2026104904`;
- seed freshness: before this draft was created, a repository-wide text search
  found no prior occurrence of any of the four seeds;
- frozen Q1 lineages: `2026092101`, `2026092102`, `2026092103`;
- users: 100;
- steps: 10 per episode;
- arms: `DROP_C3`, `FULL_ZR`;
- 24 episodes total: four worlds times three lineages times two arms;
- one keyed field per world, shared across both arms and all lineages;
- field component: `MCRL_V013_ZR_ACCEPTANCE_CONFIRMATION_V1` plus world seed;
- field key excludes arm, lineage, policy label, action, target, and outcome;
- no result from V0.12 contributes to a V0.13 contrast or threshold.

This is heavy no-browser oracle work. It must run as isolated shards on the
Ubuntu server, with a bounded parallelism that does not oversubscribe the
server. The run may begin only after this document and the complete executable
authority are frozen and independently authenticated.

## 6. Frozen acceptance gate

`PASS_ZR_CONFIRMATION` requires every condition below:

1. all contract, runner, source, runtime, checkpoint, base-preregistration, and
   TLE hashes authenticate before every shard and at merge;
2. TRAIN-only status and the absence of learner, optimizer, target network,
   TEST access, future rollout, or external policy query authenticate;
3. every formula, mechanics, purity, and current-slot support condition in
   section 4 passes;
4. supported-positive target spread is nonzero and production action exposure
   is nonzero;
5. pooled ratio-of-sums EE across all four worlds is strictly greater than
   `DROP_C3`;
6. ratio-of-sums EE is strictly greater than `DROP_C3` separately in every
   world;
7. at least two of three lineage EE contrasts are positive in every world;
8. served user-steps are noninferior pooled and separately in every world,
   with at least two of three nonnegative lineage service contrasts in every
   world;
9. exact total trajectory energy is no greater than `DROP_C3`, pooled; and
10. exact total trajectory energy is no greater than `DROP_C3` separately in
    every world.

One user-step service shortfall fails the corresponding condition. Equality is
allowed only for energy and service; EE must be strictly positive. No pooled
magnitude can rescue a failed per-world or lineage-count condition. No
confidence interval, rescaling, sign change, added seed, changed horizon, or
diagnostic can rescue a failed binding condition.

The acceptance structure is prospectively fixed for V0.13. A failure does not
authorize another guard revision or another ZR oracle confirmation.

## 7. Required receipts and nonbinding diagnostics

Required raw receipts include all V0.12 per-step authority, action, mask,
Q1/O2/O3, compatibility, support, identity, environment/RNG, bits, energy,
service, and action-exposure fields, plus every lineage, world, and pooled
contrast needed to recompute section 6 independently.

The following trajectory quantities must be reported but never enter
`PASS_ZR_CONFIRMATION`:

- total bits and its FULL-versus-DROP change;
- active-beam steps;
- active-satellite steps;
- per-step and per-world beam/satellite deltas;
- changed-action rate; and
- decomposition of EE direction into bits and energy changes.

Beam-step and satellite-step totals are intentionally demoted together. They
are proxies already priced through exact canonical trajectory energy, unless a
future study preregisters a separate non-EE operational objective.

## 8. Frozen decision and claim ceiling

| Frozen condition | Decision |
|---|---|
| every condition in section 6 passes | `GO_ZR_C3_LEARNABILITY_PREREG_ONLY` |
| any condition fails | `STOP_ZR_C3_ORACLE` |

A GO authorizes only the drafting and pre-outcome review of a separate
state-only Q3 learnability gate on disjoint TRAIN worlds. It does not authorize
Q3 learner updates, 100/500/1500/3000/9000-episode training, TEST access,
held-out claims, or paper/deck updates.

A STOP ends this ZR oracle route under the fixed three-head architecture. It
does not permit post-outcome formula, threshold, seed, horizon, support, energy,
service, or acceptance-rule tuning.

Any later learnability gate must freeze the decision-time state features,
state sufficiency claim, Q1-lineage pairing, Q3 architecture, optimizer,
training budget, world split, fit and transfer thresholds, and unweighted
deployment scale before observing learner outcomes. Passing V0.13 would show
only that the oracle target has repeated its TRAIN-world direction under this
contract; it would not establish that Q3 can learn it or improve a trained
policy.
