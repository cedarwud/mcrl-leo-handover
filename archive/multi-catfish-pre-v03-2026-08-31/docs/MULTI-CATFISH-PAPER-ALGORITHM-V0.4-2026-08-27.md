# Multi-Catfish MCRL — paper algorithm v0.4-R5 working synchronization

> **Current synchronization boundary (2026-08-30).** Publicly call the method
> **Multi-Catfish MCRL**. The active topology is strictly diagonal:
> `C1 -> Q_1^M`, `C2 -> Q_2^M`, and `C3 -> Q_3^M`; every executed specialist
> bundle still retains the complete canonical reward vector for audit. C2 uses
> the implemented policy-aligned Temporal Fork V0.3A semantics in
> `C2-TEMPORAL-FORK-CANDIDATE-V0.3-2026-08-29.md`. This is a synchronized
> algorithm draft for figures, slides, runner integration, and non-result paper
> text. It is not an efficacy, novelty, or Chapter 5 result claim.

## Status

Current working paper-method synchronization; C2 now has one successful
trained-checkpoint K>=2 joint-dose mechanics receipt and a policy-aligned
four-seed fresh-start gate. Two of four seeds reached K>=2; the aggregate has
three options, one Q2F update, and one joint commit. Its two-episode
episode-boundary split/resume and merged-history parity checks pass, but a
matched full/no-C2 EE screen, opportunity frequency at training scale, and a
formal every-100-episode long-run carrier remain open; C3 promotion from shadow
also remains incomplete.
This document has no authority to alter the corrected MODQN baseline, lift
G-6, change the primary geometry, or claim that any Catfish is effective.

Role maturity is intentionally explicit: C1's earlier all-head composite had a
negative directional screen and the present Q1-only route remains unverified;
C2 V0.3A has real K=4 trained-checkpoint support and policy-aligned fresh-start
K>=2 opportunities in two independent seeds. The four-seed gate proves bounded
mechanics, replicated reachability, and one real optimizer dose only—not a
training trend or EE effect;
C3 V3 remains shadow-only. The algorithm below defines the proposed experiment,
not three already effective mechanisms.

The v0.3 full review receipts are
`FABLE-MAX-SMC-ER-V03-REVIEW-2026-08-27.md` and
`SOL-ULTRA-SMC-ER-V03-REVIEW-2026-08-27.md`. V0.4 closes their implementation
blockers; it does not convert either review into empirical evidence.

The v0.4-R2 reward/source decisions are recorded in
`.scratch/catfish-cross-model-audit/OPUS-MAX-C3-R3-C1-SOURCE-DECISION-2026-08-27.md`.
This revision aligns C3 with canonical `r3`, confines offline EXP to C1 replay,
and makes the unresolved Main-consumer mismatch explicit.

Last synchronized: 2026-08-30

## One-sentence method

Multi-Catfish MCRL trains three independent objective specialists that create
three different kinds of **executed, complete experience**—energy-frontier,
temporal-continuity, and spatial load-balancing trajectories—and conditionally
routes their unchanged environment reward vectors into one Main MODQN after a
consumer gate; only Main is used at evaluation and deployment.

## Why v0.4 replaces the earlier variants

- C1 remains the RIS-lineage EXP/ACRM adaptation with canonical `r1`.
- The C2 time-only EE ledger passed engineering and algebra checks but was
  rejected as an EE-specialist direction at the live 30.08-s clock. C2 V0.3A
  therefore targets the canonical `r2` continuity objective directly; temporal
  EE is diagnostic only.
- The frozen C3 median spatial-power rule failed its support and seed-robustness
  criteria and remains retired. C3 v0.4-R2 instead learns unchanged canonical
  `r3` and restricts its behavior support with an exact one-user load-transfer
  identity plus separate persistent power/service safeguards.
- A generic private load-potential reward remains closed. The present C3 is
  different: `r_{3,u}(t)=-U_{s,v}(t)` is already the environment reward for a
  user served by beam `(s,v)`, and its
  support condition is derived exactly from the system P3 objective.

## Scientific objects

Let Main interact with the canonical vector-reward environment. Reusing the
active Chapter 3 notation exactly,

```text
overrightarrow R_u(t, boldsymbol theta, theta_{3dB}) =
    [r_{1,u}(t, boldsymbol theta, theta_{3dB}),
     r_{2,u}(t),
     r_{3,u}(t)],

r_{1,u}(t, boldsymbol theta, theta_{3dB}) =
    [sum_{s in \mathcal{S}} sum_{v in \mathcal{V}}
       x_{u,s,v}(t) R_{u,s,v}(t, theta_{u,s,v}, theta_{3dB})]
    / P^N(t, boldsymbol theta, theta_{3dB}),

r_{2,u}(t) = -Psi_u(t) in {0, -varphi_1, -varphi_2},

r_{3,u}(t) = -U_{b_u(t)}(t).
```

The first identity remains exact, with the same required arguments understood
on every `r_{1,u}` and `P^N` term:

```text
sum_u r_{1,u}
  = [sum_u sum_s sum_v x_{u,s,v} R_{u,s,v}] / P^N.
```

C1 may use an ACRM-shaped reward only for its own update. C2 and C3 learn their
unchanged canonical rewards `r2` and `r3`. A transition sent to Main always
carries the branch's original `overrightarrow R_u` exactly once. Routing
preserves that raw canonical vector exactly. After admission, Main applies only
the unchanged baseline calibration `bar r_{j,u}=r_{j,u}/c_j`; this fixed
baseline scaling is not specialist reward shaping. No private shaping value,
power certificate, or diagnostic may enter Main reward, evaluation, checkpoint
selection, or the headline metric.

## Shared Multi-Catfish carrier

There are four independent learner states during treatment training:

```text
Main, C1, C2, C3.
```

In paper notation, Main retains the original objective DQNs `Q_j^M`,
`j in {1,2,3}`. Independent specialist `F_j` owns exactly one corresponding
online/target DQN `Q_j^F`; it is not a second three-objective MODQN. C1/C2/C3
are prose role names for `F_1/F_2/F_3`, not multi-letter mathematical
superscripts. Thus there are six online objective Q functions during treatment
(plus their target copies), but four logical learner states. A
specialist-origin bundle still carries the complete unmodified `(r1,r2,r3)`
vector for audit, while its real TD gradient enters only the matching Main
objective DQN. Cross-objective consequences reach the other Main heads through
canonical Main-origin experience, not specialist-origin cross-head gradients.

Each owns online/target parameters, optimizer, RNG, replay view, checkpoint,
and resume metadata. A source transition carries at least:

```text
(source_id, source_policy_version, block_id, bundle_id,
 s_t, joint_action_t, focal_user, behavior_probability,
 r_env_t, s_{t+1}, mask_{t+1}, done,
 trigger_class, option_age, safety_certificate_hash).
```

The parenthesized field names above are implementation-receipt fields only and
must not appear as manuscript symbols or figure labels.

One environment step yields one **logical atomic joint audit bundle**. The
canonical bundle owns the complete joint action, the `U x 3` environment reward
matrix, every user state/mask/successor row, and shared lineage. This data-bundle
boundary is distinct from rollback atomicity: only the narrow C2 Q2F/Main
transaction currently rolls back. Dose, source quota, source age, and injection
probability are counted by bundle, never by unfolded row.

When Main consumes a bundle, all admissible user rows are unfolded atomically
in one update group and their losses are averaged so the bundle's total sample
weight is one. The same bundle may be routed to Main at most once. C2 and C3
update only the declared focal row with unchanged canonical `r2` or `r3`; C1
updates the complete bundle with the mean of its per-user C1 losses, optionally
using ACRM inside that learner only. No non-focal row receives a focal reward.

The common Catfish operator is:

1. **Trigger** from pre-outcome state, masks, physical IDs, detached policy
   surfaces, and a source-specific RNG.
2. **Propose** one valid focal intervention or one source-specific option. No
   realised reward, fading outcome, successor, or oracle EE label is read.
3. **Execute and retain** the complete branch. A bad outcome is logged and
   learned from; it is never removed because its sign is inconvenient.
4. **Route experience**, not actions. The specialist receives its declared
   objective view; after the consumer gate, Main retains the exact unshaped
   full environment vector but applies specialist-origin TD loss only to the
   matching `Q_j^M` head.

The Main minibatch uses fixed, preregistered bundle quotas and a frozen
zero-block maximum specialist source age. An off specialist is replaced by a dose-matched uniform-random action
from the same post-safety support, not by extra dose for another specialist.

Behavior provenance stores the initial joint log-probability and each focal
conditional log-probability. During a committed option continuation the focal
behavior probability is exactly one conditional on the augmented option state.

Before any specialist-origin bundle enters Main, a consumer gate must compare
canonical observations that share an action but differ in hidden trigger or
bottleneck status, and compare focal-only with atomic-complete-bundle TD
updates. If the unchanged Main observation/action consumer cannot represent
the intervention without credit reversal, that source remains shadow-only or
requires separately authorized state changes.

This is a current, concrete limitation for C3 rather than a generic warning.
The environment distinguishes pre-admission ungated demand `n_{s,v}` from
post-feasibility eligible load `U_{s,v}`. Main's base state exposes
previous-step normalized `n_{s,v}`, while the C3 certificate and canonical `r3`
use current-step `U_{s,v}`. Therefore C3's gate is testable but not passed; no
C3-to-Main arrow is unconditional in the present method. C1 and C2 must pass
their own consumer tests as well.

At evaluation and deployment:

```text
C1 dose = C2 dose = C3 dose = 0
executed action = Main MODQN masked-greedy/scalarized action.
```

There is no Catfish vote, auction, coordinator, intent exchange, action fusion,
or post-training override.

## Gate order and role authority

The stages are sequential and fail closed:

Source-build, Source-Gate-A, C2/C3 role-gate, calibration, training, and
evaluation seed namespaces are pairwise disjoint. A seed revealed at an
earlier gate is never recycled to promote a later learner.

0. **Non-training source/role gates.** Hash the specifications before revealing
   disjoint gate seeds. C1 must pass Source Gate A for `local_snr_greedy`
   against `masked_uniform`; no C1 learning may start before that source-quality
   screen. C2 must show at least one real `K>=2` forecast-certified anchor and
   one complete retained hold-plus-release execution before runner integration.
   The earlier trained-checkpoint K=4 smoke supplies engineering support; the
   current policy-aligned four-seed V0.3A gate supplies replicated fresh-start
   opportunity evidence. Neither is efficacy evidence.
   C3 must show nontrivial joint load-and-power support and extended-horizon `r3`
   benefit under the sealed shadow below. A failed source/role is removed; its
   short-pilot arm is not run.
1. **Implementation fixtures and zero-dose parity.** Only surviving roles may
   enter deterministic path fixtures. C3 receives a separate explicit
   implementation ruling after its shadow pass; the present document alone
   does not authorize C3 code.
2. **Main-consumer representation and atomic-bundle gate.** No specialist
   transfer precedes this gate.
3. **10–50 episode carrier/throughput smoke.** This is engineering evidence only.
4. **1500/3000 episode matched developmental trend pilot on Ubuntu.** This is
   directional evidence only and uses checkpoints every 100 episodes.
5. **Long matched factorial.** This is separately preregistered and is not
   authorized here.

For the new C3 shadow, count the filter waterfall separately: hard-safe
same-satellite opportunities, strict-load certificates, persistent-power
certificates, and their intersection. Require at least one joint-certified
anchor in each of five new seeds and at least 20 paired anchors total; no
zero-support mean is imputed. The exact within-certificate `r3` identity is not a
statistical result and receives no t-test. Instead, the preregistered
non-learning policy `C3-GAP` chooses the largest load gap and is compared with
uniform certified selection and the unchanged reference through the first
post-release interval and episode total. Its seed-mean canonical `r3` difference
must be positive on average and in at least four seeds, with every service,
power, RNG, and artifact safeguard passing. Also report the trivial
`max load-gap` reference during later learning because a learned Q ranker may
be redundant. Any support or safeguard failure permanently removes C3 under
the current gate budget; there is no further guard variant.

For C2, report the fixed-schedule candidate count, forecast-complete count,
`K0/K1/K>=2` anchor counts, selected behavior probability, actual option length,
adverse-outcome count, forecast wall time, and committed source units. Compare
learned `Q_2^F` ranking only on `K>=2` supports with uniform matched-random
selection over the exact same support. The direct endpoint is cumulative
canonical R2; the EE endpoint is fresh-seed Main-only ratio-of-sums EE for
`full - no-C2`. Forecast certification and a nonempty K>=2 support establish a
learnable opportunity, not that Q2 learns it or that realised EE improves.

## C1 — Energy-Frontier Catfish

### Role

C1 is designed to expose Main to experience on the immediate
rate/system-power frontier. It directly aligns with unchanged canonical `r1`;
fresh-seed Main-only system EE remains empirical. Source Gate A still has to establish that
the named source is measurably better than its neutral control.

### Mechanism

C1 keeps the RIS-lineage EXP/ACRM pair but uses a LEO-native source:

1. **EXP:** execute `local_snr_greedy` on disjoint source seeds, score each
   complete joint bundle by canonical step-level system EE, and freeze the
   resulting strata before treatment training. The matched source control is
   executed `masked_uniform`. Counterfactual alternatives cannot enter either
   replay corpus.
2. **Catfish-only ACRM:** compare an executed C1 branch with a frozen Main
   comparator under copied RNG state. For user `u`,

```text
r_{1,u}^S = r_{1,u}^F - r_{1,u}^{M|F},
r_{1,u}^C = r_{1,u}^F + eta_w * r_{1,u}^S.
```

Here superscript `C` denotes the existing competitive-reward symbol, not a
Catfish learner role. `eta_w`, comparator refresh, quantiles, ties, zero cases,
block length, and mixture ratio are frozen before outcome-bearing evaluation.
Main receives original `r_{1,u}^F`, never `r_{1,u}^C`.

Source Gate A freezes and compares `local_snr_greedy` with `masked_uniform`
before any learning run. A failure is reported; it does not authorize threshold
retuning, favourable seed selection, frozen-Main self-distillation, or a silent
replacement generator. The source manifest seals seeds, state/action/RNG
lineage, strata, and exact bundle IDs. This is a **LEO-native Phase-I analogue**,
not RIS-faithful DFT/WMMSE Phase-I and not an oracle.

The immutable high/mid EXP prefill enters only specialist replay `D_1^F`
before training. It never enters `D_M`, Main source quotas, Main evaluation,
checkpoint selection, or the headline metric. Only later actually executed C1
branch bundles may pass the consumer gate and route their exact canonical
reward vectors to Main. Prefill capacity, residency, sampling, gradient
exposure, FIFO eviction, and exact eviction step are recorded. After complete
eviction, any remaining effect is initialization persistence rather than
continuing offline replay pressure.

C1's online behavior is masked epsilon-greedy from `Q_1^F` with its own RNG and
the same preregistered collection-index epsilon schedule as its dose-matched
control. EXP membership never changes behavior probability after collection.
All C1 learning uses ordinary one-step TD; DQfD, RLPD, margin, n-step,
priority, and demonstration-pretraining losses are deferred.

C1 is not evaluated only as a composite. Equal-budget arms separately test:

```text
C1-EXP       frozen EXP corpus injection, no ACRM shaping
C1-ACRM      online C1 collection with Catfish-only ACRM, no EXP injection
C1-BOTH      EXP plus ACRM at their frozen split
C1-SRC-R     masked_uniform source, with the same strata and prefill budget
C1-STRAT-R   uniform selection within local_snr_greedy source opportunities
C1-U         no informed source selection and unshaped C1 at matched dose
```

The controls match environment bundles, update count, replay capacity, source
quota, source age, epsilon schedule, prefill timing, residency, and eviction.
`C1-SRC-R` isolates generator quality; `C1-STRAT-R` isolates stratification
within the named generator; `C1-U` is the uninformed carrier reference. These
cells distinguish source, stratum selection, ACRM learning, and interaction.

### RIS/CDRL lineage boundary

| Original ingredient | Multi-Catfish MCRL treatment | Figure/manuscript ruling |
|---|---|---|
| RIS Phase-I DFT codebook + WMMSE + max-EE exemplars | replaced by the explicitly non-faithful LEO-native source/control gate above | call it a Phase-I analogue, never RIS solver fidelity |
| M1 experience stratification | retained inside C1 after executed source construction | stratification affects `D_1^F`; offline prefill never enters `D_M` |
| M2 asymmetric discount | retired | no active method block or figure |
| M3 randomized periodic replay mixing | retired | replaced by preregistered complete-bundle quotas after the consumer gate |
| ACRM | retained in C1 only | shaped value updates C1 only; original environment reward reaches Main |
| dual rollout | applies to independent Phase-II collection branches | never use it to describe Phase-I source preparation |

### Direct endpoint

For the developmental pilot, report fresh-seed Main-only ratio-of-sums system
EE on the canonical `TRAIN` partition, with throughput, system total power,
service, and zero-power guards separately. Held-out EE requires a separately
frozen evaluator and preregistration.

## C2 — Policy-Aligned Forecast-Certified Temporal-Fork Catfish

### Role

C2 directly targets the original R2 objective: fewer avoidable intra-satellite
and inter-satellite association changes across a bounded hold-plus-release
window. It is a continuity specialist whose certified behavior support is
required to be forecast-EE-improving; it is not a renamed Q1 learner.

### Direct specialist reward

C2 trains on the unchanged per-user event reward:

```text
r_{2,u}(t) = -Psi_u(t) in {0, -varphi_1, -varphi_2}.
```

No time constant, event-energy estimate, private alias, or amplification
coefficient is inserted. The rejected time-only EE ledger may be reported as a
sensitivity but cannot select transitions or scale `r2`.

### New mechanism: bounded temporal fork

At a detached-Main handover boundary, C2 prospectively evaluates a fixed,
pre-outcome schedule of incumbent-hold alternatives. Each candidate uses a
fresh, fading-disabled, domain-separated twin and is compared with the
contemporaneous detached-Main reference for three holds and the first release.
Forecast work cannot advance or read the eventual live future RNG.

Reference and candidate may reach different counterfactual states. At every
offset, both first evaluate the same frozen Main policy on their own current
state, mask, and action table. The candidate then overrides only the focal user
with the incumbent during hold offsets 0--2; all non-focal users execute
candidate-branch Main, and release offset 3 executes complete candidate-branch
Main. Forecast and live execution call the same compositor. Consequently C2
does not replay privileged future actions from the reference branch, and
cross-branch equality of non-focal realised actions is not required.

Let `B^M,E^M` and `B^C,E^C` be full-window reference and candidate useful bits
and energy. With `eta^M=B^M/E^M`, an alternative enters the certified support
only when

```text
B^M >= 1,  B^C >= B^M,
(B^C-B^M) - eta^M(E^C-E^M) > delta_EE,
Delta G_{2,h}^{sys} > 0,  Delta G_{2,f}^{sys} > 0.
```

`delta_EE` is a frozen relative-plus-ULP numerical floor. The first two lines
imply strict forecast `B^C/E^C > B^M/E^M`; they do not require candidate energy
to be nonincreasing. The fork also binds focal service, no-new-non-focal-outage,
branch-local non-focal Main policy alignment, action/state/mask chains, and
source lineage. Activation and resource path fields are diagnostic provenance
rather than redundant admission gates.

The method requires all scheduled forecasts and their pass/fail/error outcomes
to be sealed before selection. The bounded runner now hash-binds the ordered
complete outcome set into the selection receipt; any later C2 transaction is
transitively bound through that selection digest. If `K=0`, C2 falls back to
Main and creates no C2 update. If `K=1`, the only candidate is an explicit
forced control. Only `K>=2` creates a genuine learned choice, ranked by masked
epsilon-greedy `Q_2^F`. Every receipt binds the support, selected object, and
behavior probability. For a learned `K>=2` choice only, it also binds and
rechecks the exact Q2F policy/network snapshot immediately before the sole live
seam. K0 fallback and K1 forced control do not claim learned Q2F ranking.

The selected physical association is held for three intervals and released to
the contemporaneous detached Main at the fourth. Every valid realised outcome,
including adverse service, is retained. A true episode terminal contributes
only its actual one-to-four-step prefix without padding. A focal hold that
expires inside a detached forecast is an explicit failed-support outcome; an
expiry after live selection is a runner-integrity error and cannot be converted
to favourable zero dose. For an actual length `L`, Q2F learns

```text
G_{2,t}^{(L)} = sum_{k=0}^{L-1} gamma^k r_{2,u}(t+k)
```

with zero bootstrap. Main `Q_2^M` receives the same `L` primitive canonical-R2
transitions, whose losses are averaged into one C2 source unit. Q2F and Main
then update through one at-most-once joint transaction; source age is zero and
the mutable optimizer, RNG, counter, and ledger state owned by that narrow
Q2F/Main transaction rolls back together on failure. Atomic rollback of the
surrounding source environment, replay, and episode carrier is a remaining
mid-episode engineering gate. Complete episode-boundary snapshots now restore
Main/specialists, optimizers, replay, environments, RNGs, ledgers, and cursor;
a two-episode split/resume produces an identical final Main checkpoint and
normalized-exact history outside declared clock provenance, but the carrier-state
files themselves retain four chronology-bound hash differences and are not
byte- or semantically exact. No C2 state or network exists at
evaluation/deployment.

The policy-aligned implementation is versioned
`C2_V0.3A_POLICY_ALIGNED_TEMPORAL_FORK`. Each anchor binds the Main checkpoint,
objective weights, Main-policy/compositor versions, per-offset inputs and
outputs, forecast traces, and a 79-file code-authority manifest. Legacy
pre-alignment certificates are diagnostic only and cannot enter V0.3A learning.

### Causal path to overall performance

C2 improves the direction of its pre-outcome support by construction only in
the forecast model: admitted candidates have positive forecast EE surplus and
positive hold/through-release system-R2 margins. Realised R2 and EE remain
empirical because fading and subsequent training change the trajectory.

### Direct endpoint and falsifier

Primary: cumulative weighted R2 penalty and `varphi_1/varphi_2` event incidence.
Report `K0/K1/K>=2` opportunity counts, actual option lengths, dose, forecast
cost, service, throughput, power, and Main-only ratio-of-sums EE separately.

C2 fails as an EE-helpful Catfish if `full - no-C2` does not improve fresh-seed
Main-only EE, even if its direct R2 endpoint improves. A zero/near-zero `K>=2`
dose or failure to beat matched-random ranking is a learnability failure, not a
reason to relabel a forced `K=1` option as learned.

Current non-result evidence is deliberately narrower. The V0.3A suite passes
230 tests and the retained V0.2 core/role/runner suite passes 100. Four fixed
`F111/U=10/K_max=9/2EP` receipts contain eight schedules and 32 candidates:
six pass, ten fail the certificate, sixteen fail physical support, and zero are
contract errors; `K0=5`, `K1=0`, `K>=2=3`, with two independent seeds reaching
K>=2. This satisfies the preregistered bounded opportunity gate only. Because
there is no matched no-C2 comparator in these receipts, their Main EE values are
descriptive and must not appear as Chapter-5 efficacy results.

## C3 — Spatial Load-Balancing Catfish with Power/Service Safeguard

### Role

C3 directly targets the original load-balancing reward. It creates
same-satellite relocation trajectories that transfer one served user from a
more loaded source beam to a less loaded, already-active destination beam. A
separate power safeguard selects the subset most plausibly helpful to EE. C3
may pay one initial intra-satellite handover and therefore intentionally
opposes C2's preference for persistence.

### Direct specialist reward and exact R3 identity

C3 uses no private power reward. Its focal one-step TD reward is exactly

```text
r_{3,u}(t) = -U_{s,v}(t)
```

for the physical beam serving focal user `u` after execution. Because every
served user on beam `(s,v)` receives the same negative load, the system total
is

```text
sum_u r_{3,u}(t) = -sum_{s,v} U_{s,v}(t)^2.
```

Consider one same-satellite move from source beam `v` to destination beam
`v'`. Let `U_{s,v}` and `U_{s,v'}` be the reference-fork eligible loads before
the move. The source load includes the focal user and the destination load
excludes it. With every non-focal association fixed,

```text
Delta sum_u r_{3,u}
  = -[(U_{s,v}-1)^2 + (U_{s,v'}+1)^2]
    +[U_{s,v}^2 + U_{s,v'}^2]
  = 2 * (U_{s,v} - U_{s,v'} - 1).
```

Loads are integers, so strict total-R3 improvement is necessary and sufficient
under this one-user fork exactly when

```text
U_{s,v} >= U_{s,v'} + 2.
```

This identity is the reason for C3's support; it is not an empirical result.

### Persistent load-and-power certificate

C3 considers a one-focal same-satellite relocation from `(s,v)` to an
already-active `(s,v')`. A candidate enters the joint C3 mask only when a fixed
short-horizon, deterministic, fading-off, pre-outcome reference/candidate fork
certifies all of the following at every certified interval `h`:

1. the focal reference action continues on `(s,v)`, while the candidate holds
   physical association `(s,v')` after the initial move;
2. both focal actions remain mask-valid and service-feasible, and every
   non-focal physical action is identical between the two forks;
3. reference-fork pre-move eligible loads satisfy
   `U_{s,v}(h) >= U_{s,v'}(h) + 2`, with the inclusion convention above;
4. served-user, active-beam, and active-satellite sets are unchanged;
5. let `Delta P^N(h)` denote the reference-fork value of system total power
   `P^N` minus the candidate-fork value at interval `h`; require
   `Delta P^N(h) >= 0` at every interval and `Delta P^N(h) > 0` for at least
   one interval; and
6. the candidate introduces only the declared initial `varphi_1` event, no hidden
   fallback, and no additional event or service failure inside the certificate.

The load and power tests are recorded separately as well as jointly. Their
statistics have different units and are never summed. The stricter
intersection may have little or zero support; that is a valid failure, not
permission to weaken the filter after seeing outcomes.

`Delta P^N(h)` is logged as a system-power certificate,
shadow-ranking tie-breaker, recurrence/identity check, and supporting realised
diagnostic only. It has no user subscript, is not an additive per-user power
decomposition, and never becomes a TD reward. The filter waterfall separately
reports load-only, power-only, joint-pass, and load/power sign-disagreement
counts.

The roll-forward may read current masks, association/segment state, eligible
loads, exact recurrence, physical link powers, and its independent forecast
outcomes. It may not read or copy the eventual future mobility/fading RNG,
realised fading, reward, EE, or a successor from the eventual stochastic
execution.

The certificate consists of two deterministic fading-off forks from one copied
current anchor state. Future mobility uses sealed, domain-labelled reference
and candidate RNG objects derived only from a frozen namespace, checkpoint hash,
and pre-outcome anchor lineage. The two objects start from equal states as
matched common-random-number streams; neither aliases nor advances the eventual
environment mobility/fading RNGs. At
every interval, the same frozen Main policy version independently generates
all non-focal masked-greedy physical actions in each fork. The reference focal
user holds `(s,v)`; the candidate focal user relocates to `(s,v')` at `h=0` and
then holds it. Geometry, candidate tables, physical-ID
remapping, and exact recurrence advance normally in each fork. The candidate
is rejected before stochastic execution if any non-focal physical action
differs between forks, either focal hold becomes invalid, service or active
sets differ, an unexpected event occurs, or any identity/safeguard above
fails. Thus the certificate never repairs an invalid future path with a
hidden fallback action.

The non-learning `C3-GAP` policy chooses the largest certified load gap,
breaking ties by larger cumulative forecast power relief and then physical ID.
It is retained as a simple greedy reference because learned Q ranking may add
no value once the certificate is imposed. Learned C3 selects within the same
joint certified mask using `Q_3^F` and trains only on executed canonical `r3`.
Forecast power relief remains a certificate and diagnostic, never a replay
reward or post-outcome acceptance filter.

C3 retains the canonical manuscript state `s_u(t)` and action `a_u(t)`.
Specialist-private receipt state records whether the option is open, the bound
physical association, and its remaining steps; it does not introduce a new
tilde-state symbol into the paper.

At stochastic collection, the focal user relocates to the certified physical
destination and holds it while the option remains valid; every non-focal user
follows the frozen Main behavior policy on C3's realised trajectory. A
continuation has conditional behavior probability one given the augmented
option state. Invalidity, service failure, episode end, or horizon exhaustion
terminates the option explicitly, and every realised outcome is retained.

Main sees only its canonical base state, not the current eligible load or C3
certificate. Because Main instead receives lagged ungated demand, the named
observational-alias/consumer gate must pass before any C3 bundle is routed.
Until then C3 is a shadow specialist, not an unconditional third Main source.

Controls isolate the support and ranking effects:

```text
C3-SAFE-R   uniform relocation from the broader hard-safe support
C3-LOAD-R   uniform relocation from the strict-load support, before power
C3-CERT-R   uniform relocation from the joint load-and-power certificate
C3-GAP      non-learning maximum-load-gap policy inside the joint certificate
C3-I        learned Q_3^F ranking inside the joint certificate
```

All controls use the same physical-ID commitment, stochastic horizon,
termination, dose, behavior provenance, and logging contracts. A zero-size
mask is valid shadow evidence, never imputed as a zero effect.

Potential-based shaping is not used: it does not prove persistence and the
current Main observation omits exact bottleneck variables.

### Causal path to EE

C3 directly targets canonical R3. The certified one-user fork has a strict
within-window R3 improvement by construction. Persistent forecast power relief
is a support/safeguard mechanism intended to increase the chance that
the same trajectories also help the EE denominator. Realised useful bits,
service, power, and EE remain empirical supporting endpoints; no load identity
guarantees an EE gain.

### Direct endpoint and falsifier

Primary: cumulative canonical R3 through the first post-release interval and
over the episode, compared with matched controls. The within-certificate R3
gain is reported only as a construction check. Supporting endpoints are
system energy, ratio-of-sums EE, useful bits, service, and additional
`varphi_1/varphi_2` event counts.

C3 fails if joint support is below the frozen count, any gate seed has zero
support, extended-horizon R3 does not beat its matched controls in the frozen
directional rule, any power/service/RNG identity fails, or the Main-consumer
gate rejects routing. A power or EE gain without the direct R3 result does not
rescue the role. An R3 pass with neutral/negative EE remains a load-balancing
result, not an EE claim. The failed median rule is never reopened.

## Why the roles are coherent and non-duplicative

| Specialist | Axis | Specialist learning signal | Characteristic experience |
|---|---|---|---|
| C1 | immediate energy frontier | canonical R1 plus Catfish-only ACRM | high-EE and matched competitive transitions |
| C2 | temporal continuity | canonical R2 event penalty | multi-step association commitment |
| C3 | spatial load balance with power safeguard | canonical R3 load reward | persistent same-satellite high-to-low-load relocation |

C1 prefers a better rate/power ratio now. C2 may keep an association to avoid
future switching. C3 may intentionally accept one `varphi_1` event to improve load
balance while satisfying a separate power safeguard. The conflict is visible
in complete reward vectors; no Catfish hides or resolves it. After each source
passes its consumer gate, Main can learn whether the trajectory is useful
under the deployed scalarization.

Distinct role names are not evidence of distinct support. Before the pilot,
report by seed the opportunity counts that are C1-only, C3-only, or eligible
for both; action agreement inside the overlap; and the resulting complete
reward-vector correlation. If C3 almost entirely duplicates C1 support and
adds no separate `r3` endpoint, it cannot be credited as an independent third
mechanism. The analogous C2/C3 readout reports how often the persistence and
relocation recommendations oppose one another.

## Algorithm 1 — Multi-Catfish MCRL training

```text
Input: Main M; specialists F_1,F_2,F_3; fixed source quotas;
       matched random controls; intervention schedule; frozen safety masks

Pass C1 Source Gate A; generate immutable local_snr_greedy and
masked_uniform executed source corpora; freeze manifests, strata, and IDs
Prefill D_1^F only; never prefill D_M
Initialize independent parameters, targets, optimizers, RNGs, and replay views

for each collection block do
    freeze Main comparator/version and block provenance
    for source k in {Main, C1, C2, C3} according to fixed schedule do
        reset or resume source k's exact environment trajectory
        while block budget remains do
            observe canonical state s_u(t), mask, and source-local state
            compute Main reference action without committing it
            for C2, do not reuse this opening action at later candidate offsets;
            every branch and offset recomputes frozen Main locally

            if k = Main:
                execute Main behavior action
            else if k = C1:
                execute masked-epsilon-greedy Q_1^F using C1 RNG
                compute the Catfish-only ACRM comparator when enabled
            else if k = C2:
                at a detached-Main handover boundary, complete the fixed
                pre-outcome temporal-fork candidate schedule
                in each branch and offset, recompute frozen Main locally;
                override only the candidate focal action during H=3 holds;
                execute complete candidate-local Main at first release
                certify every candidate by forecast EE surplus, hold/full R2,
                focal service, no-new-non-focal-outage, branch-local Main
                policy alignment, and lineage
                if K = 0: execute Main fallback and create no C2 source unit
                if K = 1: execute the forced singleton control
                if K >= 2: select by epsilon-greedy Q_2^F using the sealed
                           policy/network/support receipt
                execute the selected three-hold/one-release option; retain
                adverse outcomes and true terminal prefixes without padding
            else if k = C3:
                if the option is open or the certified mask is non-empty:
                    select or continue the C3 physical-association option
                else:
                    execute the preregistered C3 fallback

            retain one atomic joint bundle regardless of outcome sign
            attach full U-by-3 reward, all rows, source/action/RNG/option/safety
            provenance, and behavior probabilities
            if k = Main:
                admit the Main-origin bundle to D_M under the Main quota
            else if k = C1:
                update F_1 from the complete bundle
                conditionally expose one C1 source unit only to Q_1^M after
                the F_1 consumer gate; retain the full vector for audit
            else if k = C2:
                build the observed one-to-four-step zero-bootstrap Q_2^F return
                average the same primitive Q_2^M losses as one C2 source unit
                if replay warm-up is active:
                    retain the admitted outcome; return warmup_no_update;
                    perform no optimizer step and no joint-ledger commit
                else:
                    let the C2 joint transaction own exactly one Q_2^F update
                    and exactly one combined Main update; commit its record last
                    and roll back only its owned state on failure
            else if k = C3:
                update F_3 from the declared focal row with canonical r_3
                conditionally expose one C3 source unit only to Q_3^M after
                the F_3 consumer gate; retain the full vector for audit
            on any specialist gate failure, retain shadow lineage and do not
            route that specialist-origin bundle to Main

    for each source decision not already owned by a committed C2 transaction:
        execute exactly one combined Main update from canonical Main replay
        plus only the matching specialist source unit
    record update receipts; do not issue a second Main optimizer step
    keep every full reward vector for audit
    enforce zero-block specialist source age and at-most-once bundle identity
    hard-sync targets on the frozen schedule; checkpoint full resumable state
    every 100 episodes

Evaluation/deployment: discard C1,C2,C3 and execute Main only
```

## Required causal experiment cells

Private shaping, support selection, and learned ranking must not be credited to
one another. The minimum isolated comparison for each specialist is:

```text
zero-dose Main
matched random carrier on the same safe support
informed specialist on the same safe support
```

For C1 this expands to `C1-U`, `C1-SRC-R`, `C1-STRAT-R`, `C1-EXP`,
`C1-ACRM`, and `C1-BOTH`. For C2, report K0 and K1 as exposure classes and
compare uniform random versus learned Q2F ranking only on the exact same K>=2
certified supports; a separate no-forecast temporal-credit arm isolates the
value of certification.
For C3, compare `C3-SAFE-R`, `C3-LOAD-R`, `C3-CERT-R`, `C3-GAP`, and `C3-I`
to distinguish hard-safe support, strict-load support, the joint power
safeguard, a trivial greedy ranker, and learned ranking.

If a specialist signal is ever promoted into Main reward semantics, add the
separate four-cell comparison:

```text
A old reward + Main only
B proposed reward + Main only
C proposed reward + matched random carrier
D proposed reward + informed Catfish.
```

Only specialists that beat their matched control and pass safeguards enter a
later fixed `2^3` informed-versus-random factorial.

## Short-episode implementation and pilot

### Carrier smoke — current environment, non-scientific

- Run a 10--50 episode integration/throughput smoke after the implementation
  gates pass. A removed role is not replaced with a favourable substitute.
- Verify zero-dose byte/numeric equivalence, exact reward-vector transfer,
  source quotas, one calibration only, option termination, next-state/mask,
  RNG, resume, and checkpoint parity. An earlier bounded U=10 two-episode
  carrier seam exercised K0 then K1 and verified split/resume history parity.
  The current policy-aligned four-seed gate instead records K0=5, K1=0 and
  K>=2=3, with two independent seeds reaching K>=2, three executed options and
  one Q2F/Main joint commit. The former is carrier/resume evidence and the
  latter is replicated opportunity/mechanics evidence; neither replaces the
  10--50 episode throughput smoke or the formal every-100-episode cadence.
- Before stochastic smoke, deterministic fixtures must force every C1
  corpus/ACRM path, every C2 start/continue/release/invalid/service/end path,
  every C3 certificate rejection/acceptance/continue/terminate path, atomic
  bundle routing, duplicate rejection, and focal-only canonical C2/C3 update.
- Confirm C1/C2/C3 produce distinct trigger/support receipts. Zero stochastic
  C3 triggers in 24 episodes is a valid smoke receipt, not a fabricated
  success; fixtures verify reachability and the Stage-0 shadow decides role
  support.
- Any mismatch blocks all outcome interpretation.

### Matched short pilot — Ubuntu server

Use 1500 episodes for the first directional trend and extend unchanged arms to
3000 only after checkpoint and exposure receipts remain valid. Use one fixed
training seed for this developmental screen and five disjoint evaluation seeds.
Checkpoint every 100 episodes. The minimum user-facing ablation matrix is:

In the current developmental carrier, these are fresh seeds on the canonical
`TRAIN` partition, not a held-out test split. Any later test-partition result
requires a separately frozen evaluator and preregistration.

```text
M0                         zero-dose Main / baseline MODQN
FULL                       C1 + C2 + C3
FULL-C1                    full treatment without C1
FULL-C2                    full treatment without C2
FULL-C3                    full treatment without C3
C1-U / C1-SRC-R /
C1-STRAT-R / C1-EXP /
C1-ACRM / C1-BOTH          source, strata, ACRM, and integrated C1 mechanisms
C2-CERT-R / C2-I           random versus learned ranking on matched K>=2 support
C2-NF                      same temporal credit without forecast certification
C3-SAFE-R / C3-LOAD-R /
C3-CERT-R / C3-GAP /
C3-I                       support, power guard, greedy, and learned C3 arms
ALL-R / ALL-I              all-role controls / all informed fixed roles
```

Only exact counterfactual forks from a common anchor state may be described as
having identical trigger frames and realised support. Independent learning
arms instead match ex ante training/evaluation seeds, collection schedules,
environment budgets, learner updates, bundle quotas, epsilon schedules, and
opportunity strata. Their realised trigger/support divergence is an explicit
readout, never post-hoc dose matching.

Short-pilot readouts:

- C1 component arms and `C1-BOTH - C1-U`: fresh-seed Main-only system EE;
- `C2-I` minus both C2 controls: episode-total weighted R2 penalty, event
  incidence, post-release events, and fresh-seed EE interaction;
- C3 support waterfall plus `C3-I - C3-CERT-R` for learned ranking,
  `C3-I - C3-GAP` for added value beyond the trivial load-gap rule, and
  `C3-CERT-R - C3-LOAD-R` for the power safeguard; report extended canonical
  R3 as primary and system energy/EE as supporting endpoints;
- ALL-I minus ALL-R and M0: EE, service, every direct endpoint, and interaction
  warning signs.

The short-screen decision rule is frozen before training:

1. use five disjoint evaluation seeds; a directional pass requires positive
   mean paired difference and the same direction in at least four seeds;
2. served-user fraction may not decline by more than `0.5` percentage points
   versus the corresponding control, and no zero-power, physical-ID-remap,
   policy-alignment, or lineage guard may fail;
3. C1 must pass fresh-seed Main-only EE; C2 must pass episode-total canonical R2 against
   both controls; C3 must pass extended-horizon and episode-total canonical R3
   against its matched controls and must not fail its power/service safeguards;
4. to call C2 or C3 **EE-helpful**, its fresh-seed Main-only EE difference must separately
   pass rule 1; a direct-objective-only pass is not relabelled as EE gain;
5. ALL-I advances only if fresh-seed Main-only EE passes rule 1 against ALL-R, service
   passes rule 2, and no surviving role's direct endpoint reverses; and
6. one training seed supports no training-stability or generalization claim.

This pilot is an engineering/directional screen. It can reject a mechanism or
justify a longer matched experiment; it cannot establish final effectiveness,
generalization, or novelty.

## Paper contribution boundary

Established ingredients that cannot be claimed as novel include handover
hysteresis/commitment, load-aware association, joint handover/power
optimization, reward shaping, separate learners, and experience replay.

The narrow candidate contribution is their project-specific composition:

1. three objective-causal Catfish streams with independent learner state;
2. executed complete-transition routing into one vector-reward Main learner;
3. a forecast-certified canonical-R2 temporal fork and a canonical-R3 one-user
   load identity combined with separate EE/power safeguards, creating
   intentionally opposing temporal and spatial trajectories; and
4. zero Catfish actions at deployment, with matched random source controls and
   a fixed factorial attributing individual and joint effects.

Until a broader prior-art audit and positive experiments pass, the manuscript
may call Multi-Catfish MCRL a **proposed method** and the above a **candidate contribution**,
not a proven novel or effective algorithm.

## Current claim ceiling

Allowed now:

- Multi-Catfish MCRL is a coherent, falsifiable paper algorithm;
- C1/C2/C3 have distinct direct objectives and define distinct proposed
  support rules;
- the failed C2 time-only and C3 median variants are not used;
- the design excludes deployment-time coordination.

Not allowed now:

- any specialist improves fresh-seed or held-out EE;
- all three together are best;
- C2 is a direct EE specialist;
- C3's persistent support is sufficient;
- C3 is authorized to route into Main before the consumer gate passes;
- Multi-Catfish MCRL is globally novel; or
- short-episode pilot results are final evidence.
