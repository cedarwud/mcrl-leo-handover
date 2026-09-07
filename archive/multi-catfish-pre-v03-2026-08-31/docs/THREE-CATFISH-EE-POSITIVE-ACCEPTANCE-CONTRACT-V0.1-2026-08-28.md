# Three-Catfish EE-positive acceptance contract V0.1

Date: 2026-08-28  
Status: design and falsification contract; **formal training remains NO-GO**  
Method name in this contract: **Multi-Catfish MCRL**. `SMC-ER` is not required.

> **2026-08-29 supersession boundary.** Keep this document's diagonal routing,
> unchanged-reward, direct-objective, fresh-seed Main-only EE, and C123
> acceptance rules. Its Activation-Churn C2 mechanism and C2-specific control
> arms are superseded by `C2-TEMPORAL-FORK-CANDIDATE-V0.3-2026-08-29.md` and
> must not be used to draw, implement, or describe the current C2.

## Controller ruling

The target architecture is now fixed at the conceptual level:

```text
C1 Energy-Frontier specialist   -> Main Q_1 only
C2 Temporal-Continuity specialist  -> Main Q_2 only
C3 Spatial-Load specialist      -> Main Q_3 only
                                   |
                                   v
                    scalarized Main-only action
```

The three Catfish roles are independent experience generators and learners.
They never vote, fuse actions, coordinate, auction, or override Main at
evaluation or deployment. Each role must improve its own direct canonical
objective **and** fresh-seed Main-only system EE when activated alone. The
three-role treatment must be the best preregistered treatment. These are hard
acceptance conditions, not properties that the design can guarantee before
training.

The current all-head carrier is rejected. A C1 bundle must not update Main
`Q_2` or `Q_3`; the same diagonal rule applies to C2 and C3. The canonical EE
definition and canonical `r_1/r_2/r_3` rewards remain unchanged.

## Cross-model adjudication

Independent Fable Max and fresh-context Sol Ultra reviews agreed on the
diagonal Main interface, unchanged rewards, C1's narrowly bounded private
Phase-I exception, C3's strict-load role, and formal-training NO-GO. Their
substantive disagreement concerned C2:

- Fable rejected generic persistence as an EE mechanism because this simulator
  has no handover interruption time or handover energy, and holding can increase
  recurrence power.
- Sol accepted only a narrower Stage-0 candidate whose `r_2 -> EE` pathway is
  avoidance of short-lived beam/satellite activation and complete-system-energy
  churn, not the handover event itself.
- Both rejected any claim that a fading-off useful-bits proxy guarantees the
  realised stochastic result.

The controller therefore retains the user's hard three-positive target but
adopts the activation-churn-aware C2 below. It receives only Stage-0/shadow
authorization. If its support or singleton EE gate fails, it is rejected; the
claim is not weakened to "three roles, only one or two EE-positive."

## What is fixed and what is still empirical

### Fixed design commitments

1. Main remains one MODQN with three parallel objective DQNs
   `Q_1^M,Q_2^M,Q_3^M` and the existing scalarized action rule.
2. Each Catfish owns one private DQN `Q_j^F`, target network, optimizer, RNG,
   replay, and collection branch.
3. C1 learns canonical `r_1`, with its RIS-lineage EXP/ACRM mechanisms confined
   to the private C1 learner.
4. C2 learns unchanged canonical `r_2=-Psi`.
5. C3 learns unchanged canonical `r_3=-U_b`.
6. Main always learns from the exact canonical Main replay batch. Specialist
   data are an additional role-targeted source, not a replacement for the
   sampled Main batch.
7. All online executed bundles, including adverse outcomes, are retained.
8. At evaluation and deployment all Catfish doses are zero; Main alone acts.

### Conditional or empirical claims

- C3 has a conditional algebraic strict-`r_3` improvement identity inside its
  declared one-user load-gap fork.
- C2/C3 pre-outcome useful-bits and EE-surplus tests are deterministic forecast
  proxies. They can filter support but do not establish stochastic
  non-degradation.
- No local identity or forecast proxy guarantees that training changes the
  scalarized Main policy in the desired direction on fresh seeds.
- C1-only, C2-only, C3-only, and C123 EE gains are all empirical hypotheses.

### Current implementation and metric boundary

The current `MODQNTrainer.update()` is a canonical baseline updater, not this
new carrier. It samples one row minibatch, updates all three objective DQNs,
and has no specialist source, atomic-bundle, quota, age, or duplicate contract.
The archived scratch `update_main_with_source_quota()` is also not reusable as
authority: its routed mode consumes and discards the canonical replay sample
and backpropagates each donor reward column through all three Main DQNs.

The current trainer evaluation field `r1_mean` is not the formal EE endpoint.
It averages accumulated per-step `r_1` contributions; in general this differs
from the required episode ratio of sums. The scratch sweep evaluator already
implements and tests a fail-closed `ratio_of_sums`; before any new efficacy
screen it must be bound to the new arm receipt and independently replayed for
each evaluation seed:

```text
EE = (sum_t B_t) / (sum_t E_t),
```

where `B_t` is system useful bits and `E_t` is system consumed joules during
the same interval. The receipt must also report the two sums, served fraction,
and zero-power/zero-energy handling. Never substitute `r1_mean` for this
endpoint or pool numerators and denominators across training seeds.

## Common Main-consumer interface

For role `j` with frozen donor fraction `beta_j`, update only the corresponding
Main objective network:

```text
L_j = (1-beta_j) L_MainReplay,j + beta_j L_Cj,j
L_k = L_MainReplay,k                              for k != j
```

When all three roles are active, each `Q_j^M` receives only its matching
Catfish term. The next developmental candidate freezes `beta_j=0.25`; it is
not a dose sweep. An absent, unsupported, or shadowed role has effective
`beta_j=0`.

The production implementation must satisfy all of the following before an
outcome-bearing screen:

- the exact batch returned by canonical Main replay sampling enters
  `L_MainReplay,j`;
- zero dose is byte-exact with the canonical Main update, including parameters,
  optimizer, replay, and RNG state;
- one combined loss produces one optimizer step for each affected objective
  network; no sequential donor double-step is allowed;
- a specialist perturbation changes gradients only in its matching Main DQN;
- the complete unmodified reward vector is retained in the atomic bundle, but
  non-target donor TD losses are computed under `no_grad` for audit only;
- atomic bundle row averaging gives each bundle total sample weight one;
- source age, quota, behavior probability, bundle identity, and duplicate
  rejection are receipted; and
- observational-alias, focal-versus-atomic credit, off-support, and scalarized
  action-pivotality gates pass separately for C1, C2, and C3.

The role-targeted interface improves attribution. It does not itself prove an
EE gain: the other two DQNs may still extrapolate on a donor-origin action, and
the final action remains a scalarization of all three estimates.

## C1: Energy-Frontier Catfish for Q1

### Mechanism retained

C1 is the RIS-lineage role. Its private learner retains separable EXP and ACRM
components:

1. a LEO-native, executed `local_snr_greedy` source with a dose-matched
   `masked_uniform` source control;
2. a sealed high/mid EE-stratified EXP corpus that prefills only `D_1^F`;
3. private ACRM shaping inside the C1 specialist only; and
4. Phase-II masked epsilon-greedy C1 collection whose executed, unshaped
   canonical `r_1` bundles may enter Main `Q_1^M` after the consumer gate.

### Unique Phase-I exception

C1's realised-EE corpus stratification is the only permitted exception to the
general ban on outcome-conditioned selection. It is valid only if all of the
following are frozen before treatment and evaluation:

- source/corpus seeds are disjoint from treatment and evaluation seeds;
- source generator, strata thresholds, quotas, residency, eviction, and
  update budget are hash-bound;
- every raw source outcome is archived before mechanical strata selection;
- the informed and neutral corpora use the same rules and budget;
- the corpus enters only private `D_1^F`, never Main replay, Main quota,
  checkpoint selection, evaluation, or headline metrics; and
- every later online C1 bundle is retained regardless of outcome.

C2 and C3 may not reuse this exception.

### EE pathway and controls

At a step, the sum of per-user canonical `r_1` contributions is the canonical
system EE for that step. This gives C1 the direct pathway:

```text
EXP/ACRM -> Q_1^F energy-frontier behavior -> Q_1-only donor TD
         -> improved Main Q_1 action ranking -> Main-only EE
```

The last two arrows remain empirical. Required controls are `C1-U`,
`C1-SRC-R`, `C1-STRAT-R`, `C1-EXP`, `C1-ACRM`, `C1-BOTH`, zero-dose Main, and a
direct local-SNR Q1-only anchor. The primary fixed C1 treatment is
`C1-BOTH`; controls explain failure and cannot be inspected and substituted
post hoc as a new treatment.

## C2: Activation-Churn-Aware Temporal-Continuity Catfish for Q2

### Why pure persistence is insufficient

Canonical `r_2` penalizes handover events, not lost useful bits or energy. A
pure persistence option could reduce recorded events by accepting a weak link,
outage, or delayed handover. Therefore fewer handovers alone is not an EE
pathway.

### Minimum mechanism

C2 remains a physical-ID short-horizon persistence option, but it does not
trigger on generic handovers. It intervenes only at a temporal boundary where
a frozen-Main forecast would leave the incumbent and either create short-lived
beam/satellite activation churn or consume more complete system energy than a
stable candidate. The declared maximum churn lifetime, hold window, and first
release interval are frozen before outcome reveal.

Before stochastic execution, an independent fading-off common-anchor forecast
compares each stable candidate with the frozen Main reference. A candidate may
be the incumbent or one declared relocation followed by persistence. It enters
the C2 learning support only when:

1. the focal physical ID remains remappable, action-valid, and service-feasible
   for the full declared window, with no hidden fallback;
2. all non-focal physical actions are identical in candidate and reference
   forks;
3. the Main reference leaves its current association and shows either an
   `off -> on -> off` active-beam/satellite event or greater complete system
   energy, including fixed, baseband, PA, and recurrence terms;
4. through first release, the candidate has strict system-total canonical
   `r_2` improvement and no delayed-event, re-entry, or service-loss surge;
5. forecast accumulated useful bits satisfy a frozen non-inferiority floor;
6. let `B^M,E^M` be same-window accumulated reference useful bits and joules,
   `B^C,E^C` the candidate values, and `eta^M=B^M/E^M`; require the
   pre-outcome EE-surplus inequality

   ```text
   (B^C-B^M) - eta^M (E^C-E^M) >= 0
   ```

   holds strictly over the declared window; and
7. `E^M>0` and `E^C>0`; a zero-energy or `0/0` window fails closed rather than
   entering certified support; and
8. at the role-gate level, a frozen minimum count of anchors exposes at least
   two certified stable choices; otherwise the mechanism is only a deterministic
   stay/control rule and not evidence for a learned Q2 specialist.

The forecast uses a sealed RNG namespace independent of eventual mobility and
fading RNGs. Useful bits and the EE-surplus inequality are binary forecast
screening proxies, not guarantees about the stochastic execution. They, system
energy, and forecast event counts define pre-outcome support only. They are
never rewards, TD labels, replay weights, realised-outcome admission rules, or
ranking tie-breakers. Within this support, `Q_2^F` ranks actions and learns only
canonical `r_2`. Realised useful bits, energy, service, and ratio-of-sums EE are
reported again as independent harm/efficacy endpoints.

### Distinct causal path and controls

```text
activation-churn-aware physical-ID persistence -> fewer avoidable events
 -> better Q_2^F temporal ranking -> Q_2-only donor TD
 -> Main avoids short-lived active-resource/power churn -> Main-only EE
```

Required equal-budget controls are:

- `C2-PERSIST-R`: uniform persistence from the broader hard-safe support;
- `C2-CHURN-CERT-R`: uniform persistence from the identical certified support;
- `C2-STAY`: stay on the incumbent when valid, with the frozen fallback; and
- `C2-I`: learned `Q_2^F` ranking within the certified support.

This separates the value of persistence, the EE-safe envelope, and learned
Q2 ranking. C2 must report first-release and episode-total handover cost,
reversal/ping-pong counts, useful bits, energy, service, and EE.

The posthoc legacy one-step diagnostic in
`C2-ACTIVATION-CHURN-POSTHOC-SUPPORT-DIAGNOSTIC-2026-08-28.md` found nonzero
but sparse active-resource/EE-positive support. It authorizes only a
prospective Stage-0 census and must not set a result-selected tolerance.

## C3: EE-safeguarded Spatial-Load Catfish for Q3

### Strict direct-objective support

C3 proposes one focal same-satellite relocation from a more loaded source beam
to a less loaded already-active destination beam. With all non-focal physical
associations fixed, a candidate must satisfy

```text
U_src >= U_dst + 2.
```

The corresponding one-user fork has the exact identity

```text
Delta sum_u r_3,u = 2 (U_src-U_dst-1) > 0.
```

This establishes a strict local `r_3` opportunity inside the certified fork;
it does not establish learned or episode-level EE efficacy.

### Minimum EE safeguard

There is no unconditional structural power-nonincreasing theorem for the
initial relocation. Under the canonical recurrence, an already-active
destination can currently have a beam maximum below `p^0`; adding the focal
user at a new-segment value of `p^0` can therefore raise that maximum. Removing
the focal user from the source also need not offset the increase. The
already-active grammar avoids a new fixed activation charge, but complete
system power must still be measured explicitly in both forks.

The persistent load/power certificate is therefore retained and strengthened.
Over a fading-off,
pre-outcome, common-anchor relocation-and-hold forecast, require:

1. source/destination actions remain valid and service-feasible;
2. non-focal physical actions, served-user set, active-beam set, and
   active-satellite set are identical between reference and candidate;
3. the strict load-gap identity persists for the declared certificate window;
4. complete system power is no greater at every interval; equality throughout
   the window is allowed;
5. forecast useful bits do not decrease and the same window-level EE-surplus
   inequality is strictly positive, so a power-tied candidate must obtain its
   strict forecast EE advantage from useful bits rather than a hidden power
   increase;
6. only the declared initial intra-satellite event occurs, with no hidden
   fallback or additional service failure; and
7. all eventual stochastic outcomes are retained after execution.

Power, useful bits, and the EE-surplus inequality define binary forecast
support/safeguards only. The strict surplus is algebraically equivalent to a
strict improvement in the four-interval forecast ratio-of-sums EE, but it is
not a realised stochastic EE guarantee. `Q_3^F` ranks within that support and
learns only canonical `r_3`; it receives no private power or EE reward.
Realised useful bits, energy, service, and ratio-of-sums EE remain independent
endpoints.

### Distinct causal path and controls

```text
strict high-to-low load relocation + power-nonincreasing EE-safe support
 -> improved canonical r_3 trajectories within a useful-bits-safe support
 -> Q_3-only donor TD -> Main learns spatial load/EE opportunities
 -> Main-only EE
```

This is spatial redistribution, not C1's immediate energy-frontier ranking and
not C2's temporal stay option. Required controls remain
`C3-SAFE-R -> C3-LOAD-R -> C3-CERT-R -> C3-GAP -> C3-I`. `C3-I` must beat both
the uniform certified control and the non-learning maximum-gap control; if it
does not, the certificate may be useful but the learned Q3 Catfish has not
shown added value. Within one frozen certificate window, maximizing `C3-GAP`
is algebraically the same ordering as maximizing the canonical system-`r_3`
gain. Therefore the learned `C3-I` can demonstrate added value over `C3-GAP`
only through its extended or episode-total canonical-`r_3` return, not by
relabeling a larger power, useful-bit, or EE-surplus margin as learning.

The current eligible-load versus lagged-demand observational-alias gap is
unresolved for both the specialist `Q_3^F` that must rank C3 choices and the
Main `Q_3^M` that must consume C3 donors. C3 stays shadow-only until both gates
pass on their exact executed decision surfaces. If either gate fails, the
three-Catfish target is not achieved; a separately matched and preregistered
state-observability revision is required rather than training or routing C3
anyway.

## Hard singleton acceptance matrix

All comparisons use matched training budgets, preregistered training seeds,
fresh nested evaluation seeds, Main-only evaluation, and the same scalarized
deployment policy. A developmental screen may use positive paired mean plus at
least four of five evaluation seeds in the same direction; this authorizes
only a longer pilot. Confirmatory effect claims require multiple training
seeds as the experimental units and preregistered confidence bounds and
multiplicity handling.

For direct endpoints, "first-release", "extended", and "episode-total" mean
the sum over all admissible users in every complete atomic bundle and over the
declared time window. The focal row remains the specialist training view for
C2/C3; it may not replace the system-level direct endpoint used for acceptance.

| Role | Direct canonical endpoint | Required Main-only EE contrasts | Service/physics guard | Distinctness/added-value guard |
|---|---|---|---|---|
| C1-I | canonical `r_1`/ratio-of-sums EE in the frozen C1 treatment direction | `C1-I > M0` and `C1-I > C1-U` | served fraction loss no more than 0.005; useful bits and energy reported | EXP/ACRM component arms fixed; overlap with C2/C3 reported |
| C2-I | first-release and episode-total `r_2` beat `C2-CHURN-CERT-R` and `C2-STAY`, with no delayed-event surge | `C2-I > M0` and `C2-I > C2-CHURN-CERT-R` | useful-bits non-inferiority, service guard, no outage/re-entry loophole | activation-churn temporal-only anchors meet frozen support and two-choice floors; learned ranking beats same-support random |
| C3-I | extended and episode-total `r_3` beat `C3-CERT-R` and `C3-GAP` | `C3-I > M0`, `C3-I > C3-CERT-R`, and `C3-I > C3-GAP` | power, useful bits, service, active-set, identity, and RNG guards pass | spatial-only anchors meet frozen floor; learned ranking is not reducible to gap/certificate control |

An EE increase without the matching direct objective fails role identity. A
direct-objective increase without EE improvement fails the user's EE-positive
Catfish requirement.

## Full factorial: when C123 may be called best

The full treatment is always the fixed `III=C1-I+C2-I+C3-I`, never a post-hoc
set of surviving roles. It is tested only after all three singleton gates pass.
At minimum compare:

```text
M0:   000
singles: I00, 0I0, 00I
pairs:   II0, I0I, 0II
full:    III
matched random/reference: RRR, RII, IRI, IIR
```

To say that all three together are best within the preregistered experiment,
`III` must improve Main-only EE over `000`, `RRR`, every informed singleton,
every informed pair, and `RII/IRI/IIR`; all direct endpoints must remain in the
accepted direction and every service/useful-bits guard must pass.

`III > RII/IRI/IIR` establishes each informed role's incremental value inside
the combination. `III > II0/I0I/0II` establishes that adding the third role is
beneficial. A synergy claim requires a separately preregistered interaction
contrast. Passing this matrix means best among the declared treatments, not
globally optimal.

### Budget and scheduling identity

The factorial must not reward `III` merely for receiving three times the
environment or optimization budget. Before reveal, freeze for every arm:

- total environment steps and stochastic physics calls;
- canonical Main replay insertions, Main update count, and evaluation calls;
- per-role collection opportunities, attempted and admitted atomic bundles,
  and per-DQN donor fraction;
- the missing-support rule (`beta_j=0` for that scheduled role, with no dose
  borrowing by another role);
- a fixed interleaving schedule for Main/C1/C2/C3 branches; and
- a deterministic priority/deferral rule when C2 and C3 are eligible from the
  same anchor, without action fusion or an extra trajectory.

`RRR`, `RII`, `IRI`, and `IIR` use the identical schedule, support, horizon,
and optimizer budget as the informed arm they replace. Realised opportunity
counts may differ and must be reported; they are never post-hoc dose matched.

### Scalarized action-pivotality receipt

Qj-only gradients do not imply a Qj-only policy effect. For a fixed,
preregistered set of common pre-outcome anchors, record before and after the
candidate update:

1. each objective DQN's valid-action Q table;
2. the scalarized valid-action ranking under the frozen objective weights;
3. whether the matching donor changes its target DQN's preferred action or
   margin beyond a frozen numerical tolerance;
4. whether the final scalarized action changes in the same, opposite, or no
   direction; and
5. off-support disagreement of the two baseline-only DQNs on the donor action.

The gate fails if receipts are non-finite, action masks/anchors are not
identical, or the direction cannot be attributed mechanically. A zero
scalarized-pivotality rate is valid evidence that the role cannot influence
the current Main policy at the tested dose, not permission to tune `beta`.

### Confirmatory statistical unit

The training seed is the experimental unit. Fresh evaluation seeds are nested
paired measurements inside each trained policy. Each seed first produces its
own ratio-of-sums EE, direct endpoint, and guards; it does not contribute raw
steps to a pseudo-replicated pooled test. The preregistration must list the
C1, C2, C3, and factorial contrast families, pairing, simultaneous confidence
rule, practical margin, and multiplicity correction before confirmatory
training. The five-evaluation-seed directional rule remains developmental
only.

## Failure and anti-procurement rules

1. A role that improves `r_2` or `r_3` but fails fresh-seed EE is rejected as
   one of the three EE-positive Catfish roles. It may be reported only as a
   continuity/load ablation; it cannot be counted toward the final claim.
2. A role that improves EE but fails its canonical direct endpoint is also
   rejected because its claimed role is not identified.
3. Zero/rare certified support is a mechanism failure, not a zero-effect
   efficacy result and not permission to weaken the certificate after reveal.
4. A failed role may be redesigned only under a new version, hash, seed
   namespace, and preregistration. Thresholds, horizons, `beta`, sample
   admission, checkpoints, or controls cannot be tuned on revealed outcomes
   and reused as confirmatory evidence.
5. `ALL-I` never means "all surviving roles". Any confirmatory singleton
   failure rejects the three-positive hypothesis for that design version.
6. All failed variants, negative outcomes, campaign ledgers, and the existing
   C1 directional failure remain disclosed.
7. Development, role-gate, training, validation, and confirmatory seeds remain
   disjoint. No checkpoint or seed selection uses headline EE.
8. C1's sealed private Phase-I corpus is the only outcome-stratification
   exception. Online/Main admission, weighting, deletion, checkpoint choice,
   or routing by realised reward, EE, TD error, or successor is forbidden for
   all roles.

## Immediate authorization boundary

This contract authorizes the following non-outcome work:

1. implement the canonical-Main-preserving diagonal updater and its reference,
   isolation, zero-dose, and atomic-weight tests;
2. implement C2's pre-outcome useful-bits/EE-surplus support as a shadow gate;
3. add useful-bits/EE-surplus safeguards to C3's existing load/power shadow gate;
4. run deterministic fixtures and opportunity/support counts; and
5. revise figures and method text so every specialist arrow terminates only at
   its matching Main DQN.

It does **not** authorize formal training. A new outcome-bearing developmental
screen requires a frozen code/spec/seed receipt after all non-outcome gates
pass. Long training and factorial sweeps should run on the Ubuntu training
server after that freeze.

## Claim ceiling

Allowed now:

- this is one coherent and falsifiable three-role Multi-Catfish MCRL design;
- the roles have distinct direct objectives, behavior mechanisms, and
  one-to-one Main consumers;
- C2 and C3 now have explicit pre-outcome physical pathways intended to avoid
  trading their direct objective for worse EE; and
- all three roles and the full treatment have hard EE acceptance gates.

Not allowed now:

- any singleton improves fresh-seed or held-out EE;
- all three together are best;
- the pre-outcome certificates guarantee stochastic or trained-policy EE;
- C3 is routable before its consumer/observability gate passes; or
- the method is experimentally effective or globally novel.
