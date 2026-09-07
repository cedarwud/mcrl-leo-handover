# SMC-ER developmental short-episode EE-sweep and ablation specification

Date: 2026-08-27  
Status: draft freeze for rapid engineering data; seed values remain unrevealed
until runner and tests are closed.

## 1. Purpose and claim ceiling

This experiment is the fastest matched test of the complete proposed SMC-ER
carrier in the same visual form as the Chapter 5 sensitivity figures: the
x-axis is an environment parameter and the y-axis is held-out system EE. It is
designed to answer:

1. can one Main MODQN and three independent objective specialists execute,
   update, gate, route complete bundles, checkpoint, resume, and evaluate
   without violating baseline semantics;
2. after each independent consumer gate, does removing C1, C2, or C3 from the
   full carrier change held-out Main-only EE across the user-count sweep; and
3. is Full directionally best, neutral, or harmful relative to the unchanged
   MODQN baseline at this deliberately short horizon?

The outputs are **developmental short-EP data**. They may eliminate a broken
role, reveal implementation defects, or motivate a longer pilot. They are not
Chapter 5 evidence, do not establish convergence, effectiveness, novelty, or
statistical superiority, and may not rescue a failed gate.

## 2. Authority and isolation

The runner must bind exact SHA-256 values for:

- `docs/MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md`;
- `docs/MULTI-CATFISH-CONCEPT-ALGORITHM-FREEZE-V0.1-2026-08-27.md`;
- `docs/MULTI-CATFISH-NONRESULTS-PAPER-AUTHORING-CONTRACT-V0.1-2026-08-27.md`;
- the corrected baseline checkpoint and frozen R2 preregistration;
- every Python source, test, manifest, TLE input, and dependency version used
  by the developmental carrier.

All new carrier code lives under `.scratch/smc-er-short-ep/`. It may import the
canonical environment and baseline learner but may not add Catfish vocabulary
or reachability under `src/mcrl`, alter the corrected checkpoint, change the
three reward definitions, change geometry, or lift G-6.

The unchanged Main behavior for reference collection, evaluation, and
deployment is the frozen masked-greedy **scalarized** MODQN policy. A Q1-only
policy is not an alias for Main and may appear only as an explicitly named
diagnostic arm if separately authorized.

## 3. Two-stage execution

### S0 -- deterministic and zero-dose engineering closure

Before any development seed is revealed:

- exact canonical reward and reward-calibration fixtures pass;
- four learner states and six online Q functions plus target copies are
  distinct by object, optimizer, RNG, replay, checkpoint, and resume metadata;
- complete joint bundles retain every user row and the natural `U x 3` reward
  matrix exactly once;
- source dose and sample weight are counted per bundle, never per unfolded row;
- all adverse source outcomes remain retained;
- source-specific consumer gates fail closed and do not share one verdict;
- a gate-fail source routes zero bundles and remains observable in shadow
  receipts;
- Main-origin bundles enter Main replay directly under the Main quota;
- Main applies only the frozen baseline calibration after admission;
- zero-specialist-dose execution is bitwise or tolerance-defined equivalent to
  the corrected baseline over deterministic fixtures;
- G-6 remains green; and
- checkpoint/resume reproduces the next action, update, replay sample, and RNG
  receipts.

Run a one-seed, two-episode all-cell CLI smoke only after these checks pass.
This smoke is engineering output and cannot decide a role.

### S1 -- rapid matched short-EP sweep

- nominal training environment: `U=100` users for every arm;
- training seeds: three new development seeds shared across all arms;
- training horizon: 20 episodes per arm and seed;
- short-horizon schedule: epsilon decays linearly from `1.0` to `0.01` over
  episodes 0--15 and targets hard-sync every 5 episodes in every arm; these are
  diagnostic time compressions and are never substituted for the 9,000-episode
  Chapter 5 schedule;
- evaluation: freeze the final checkpoint, then evaluate it Main-only at
  `U in {60, 80, 100, 120, 140}` with three shared held-out evaluation seeds
  per user-count point;
- checkpoint selection: final episode only; no best-on-development selection;
- evaluation dose: C1=C2=C3=0, with Main masked-greedy scalarized actions;
- all arms use identical environment budgets, baseline initialization,
  optimizer/update counts, epsilon collection index, replay capacity, source
  quotas, bundle weights, and source-age limits.

Before the three-seed S1 is complete, one explicitly labelled engineering
preview may run the same five arms for 10 episodes with the first development
seed, epsilon decay over episodes 0--7, target sync every 2 episodes, and the
same five-point held-out sweep. It is released only as
`ONE-SEED-10EP-PREVIEW`; it cannot select a role, tune a parameter, or replace
the matched three-seed result.

The formal Stage-0 seed namespaces remain disjoint. S1 development outcomes
cannot be reused as later gate, pilot, training, or thesis evaluation seeds.

## 4. Primary five-arm leave-one-Catfish-out design

The first plot contains exactly five manuscript-facing curves. Engineering IDs
remain outside manuscript notation.

| ID | Plot label | C1 lane | C2 lane | C3 lane |
|---|---|---|---|---|
| `B000` | Baseline MODQN | off | off | off |
| `F111` | Full SMC-ER | on | on | on |
| `A011` | Full - C1 | neutral control | informed | informed |
| `A101` | Full - C2 | informed | neutral control | informed |
| `A110` | Full - C3 | informed | informed | neutral control |

`B000` is the unchanged corrected MODQN implementation, not a neutral
specialist carrier. It detects carrier overhead through the separately required
zero-dose parity fixture before S1.

For each leave-one-out arm, the informed Catfish mechanism is removed but a
dose-matched neutral lane remains as the experimental control required by the
method authority. It uses uniform selection from the same post-safety support,
the same rollout/update schedule, and the same consumer quota, but it has no
informed Q ranking, no C1 EXP/ACRM, and no specialist-specific preference. This
is what the concise plot label `Full - Cj` means. It is not an extra Catfish.
Attempted, admitted, and control dose are reported separately. No lane borrows
dose from another specialist.

The complete `2^3` factorial and C1-only/C2-only/C3-only arms are deferred
supplementary experiments. They are not needed for the first Chapter 5-style
trend plot and must not delay it.

### 4.1 C1 factor

- informed: frozen LEO-native source-quality rule, C1-only EXP prefill, online
  `Q_1^F`, and C1-private ACRM;
- neutral: masked-uniform neutral source/control at identical support, strata,
  prefill capacity/residency/eviction, online bundle count, update count, and
  epsilon schedule, with no informed selection or ACRM shaping;
- offline prefill enters only `D_1^F` in every cell and never Main replay;
- only later actually executed C1 or C1-control bundles can be considered by
  the C1 consumer gate.

This first matrix treats the complete C1 mechanism as one factor. EXP-only,
ACRM-only, source, and stratum sub-ablations are deferred until the composite
survives the short-EP screen.

### 4.2 C2 factor

- informed: `Q_2^F` chooses from the hard-safe physical-association option
  support, then holds the physical ID for the frozen horizon with explicit
  termination and release;
- neutral: uniform safe physical association under the identical trigger,
  horizon, physical-ID remapping, termination, and release rules;
- both branches receive the unchanged canonical `r2=-Psi`; no EE proxy or
  private time reward enters the learner or Main;
- the neutral branch executes the same number of source and learner updates,
  but its behavior action is uniform rather than Q-ranked.

### 4.3 C3 factor

- informed: `Q_3^F` ranks the frozen hard-safe, strict-load, persistent-power
  joint support; ties use the declared deterministic order;
- neutral: uniform selection from the same joint-certified support;
- log the non-learning maximum-load-gap rule as a diagnostic comparator, not a
  rescue arm and not a training label;
- both branches learn unchanged canonical `r3=-U`; system power is a separate
  certificate/diagnostic and never a reward;
- C3 remains shadow-only unless its own representation and atomic-bundle
  consumer gate passes before the matrix launch.

If the C3 gate fails, every C3 source outcome is still retained and its
direct `r3`, support, power, service, and EE diagnostics are reported, but zero
C3 bundles enter Main. The resulting `F111` versus `A110` Main contrast is then
expected to be zero apart from independently diagnosed carrier defects; this is
a valid gate result,
not permission to force routing or add an outcome-informed state feature.

## 5. Independent consumer-gate contract

For each source separately, before any source bundle reaches Main:

1. construct pre-outcome paired observations sharing the same canonical Main
   state/action but differing in the specialist trigger or bottleneck status;
2. measure whether the source's one-step and short-horizon canonical TD target
   ordering is representable without systematic credit reversal;
3. compare focal-only and atomic-complete-bundle updates for sign reversal,
   loss magnitude, and downstream action ordering;
4. freeze one verdict: `route` or `shadow`; and
5. record the gate dataset, code hash, thresholds, and result independently.

No gate can pass because another source passes. No all-stream majority, vote,
auction, or coordination rule exists. A gate verdict is frozen across all arms
so an ablation cannot change admission semantics.

## 6. Atomic dose matching

Every enabled source lane has the same preregistered bundle quota. Main
minibatches contain fixed counts of:

- Main-origin bundles;
- C1-lane gate-pass bundles;
- C2-lane gate-pass bundles; and
- C3-lane gate-pass bundles.

When a lane lacks enough fresh gate-pass bundles, the minibatch does not borrow
from another specialist lane. It uses the frozen fail-closed shortage rule and
logs the shortfall. Rows unfolded from one bundle have losses averaged so the
bundle's total sample weight is one. The same bundle can enter Main at most
once.

Report attempted lane dose, admitted lane dose, and informed-versus-control
status. An ablation contrast is uninterpretable if total Main batch size or
update count differs across arms.

## 7. Endpoints

### 7.1 Held-out Main-only primary dashboard

For every arm, training seed, evaluation seed, and user-count point report
separately:

- ratio-of-sums system EE in bit/J;
- useful bits and system energy in J;
- mean system total power in W;
- served-user fraction and zero-power/zero-service guards;
- cumulative canonical `r1`, `r2`, and `r3` in natural and calibrated units;
- `varphi_1` and `varphi_2` event counts, reversal/ping-pong counts, and tenure;
- per-beam eligible-load distribution, `sum_b U_b^2`, maximum load, and active
  beam/satellite counts; and
- Main action diversity, per-head pivotality, scalarized action agreement, and
  collapse diagnostics.

The plotted EE is never the arithmetic mean of per-step EE. At each user-count
point it is the ratio of pooled useful bits to pooled system energy over the
complete held-out episode. The CSV retains per-evaluation-seed numerators and
denominators. No EE value is reported without its useful bits, system
energy/power, and service denominator guards.

### 7.2 Source and gate dashboard

For each lane and treatment/control variant report:

- triggers, supported actions, attempted/executed/retained bundles;
- gate-pass/gate-fail counts and admitted bundle quotas;
- focal and complete-bundle canonical reward endpoints;
- C1 source strata, ACRM residuals, prefill exposure/residency/eviction;
- C2 option opens, holds, early termination, release, event displacement, and
  cumulative `r2` through release and episode end;
- C3 hard-safe/load/power/joint waterfall, exact `r3` identity failures,
  system-power sign, service guards, and C3-GAP redundancy; and
- every negative outcome, shortage, remapping failure, RNG/lineage failure,
  and non-focal divergence.

## 8. Plot and developmental contrasts

The primary artifact is `ee-vs-users-short-ep.png` plus its source CSV/JSON:

- x-axis: integer number of users `60, 80, 100, 120, 140`;
- y-axis: held-out ratio-of-sums system EE in `Mbits/J`;
- curves: Baseline MODQN, Full SMC-ER, Full - C1, Full - C2, Full - C3;
- each thick line: equal-weight mean across training seeds of each seed's
  ratio-of-sums EE;
- visible markers at every measured point and faint per-training-seed traces or
  min--max whiskers; no smoothing, fitted curve, or confidence claim.

Compute seed-paired descriptive contrasts at every user-count point:

- Full minus Baseline;
- C1 contribution: Full minus Full - C1;
- C2 contribution: Full minus Full - C2;
- C3 contribution: Full minus Full - C3; and
- direct source endpoints even when a lane remains shadow-only.

Also report the five-point area-under-curve contrast only as a compact
descriptive summary. Show every seed value, mean, median, range, and direction
count. Do not report p-values, confidence claims, or rank a winner from three
development seeds.

## 9. Terminal interpretation

- **ENGINEERING_FAIL:** any parity, identity, RNG, lineage, bundle atomicity,
  dose, checkpoint/resume, finiteness, or G-6 violation. Stop before S1 or mark
  all affected data unusable.
- **ROLE_DROP_SIGNAL:** an informed lane lacks support, loses its own canonical
  endpoint to the matched neutral source, breaks service/power safeguards, or
  remains non-representable to Main. Keep and report the failure.
- **SHORT_EP_DIRECTIONAL:** engineering passes and a role's own endpoint plus
  held-out Main dashboard move consistently enough to justify a longer matched
  pilot. This is not effectiveness.
- **FULL_NOT_BEST:** Full need not win. Report conflicts and interactions; do
  not retune a role from the same outcomes.

The full method is not promoted from this experiment. Any next 200--300
episode pilot requires a new preregistration, new seed namespace, and a
separate cross-model review of the frozen short-EP receipt.

## 10. Compute route and expected wall time

Implementation, fixtures, and the two-episode CLI smoke are non-heavy and stay
in the current environment. The `5 arms x 3 training seeds x 20 episodes`
training matrix plus `5 user points x 3 held-out seeds` frozen-checkpoint
evaluation sweep is heavy compute and must run unattended on the Ubuntu server,
not the WSL/browser workstation.

Target timing after code closure:

- server parity smoke: 15--45 minutes;
- one-seed 10-episode five-arm preview plus sweep: approximately 45--120
  minutes after runner closure;
- complete three-seed 20-episode sweep: approximately 3--7 hours, with a longer ceiling
  if C2/C3 forecast forks dominate;
- receipt aggregation and independent read-only adjudication: 30--90 minutes.

The server worker prompt must include repository/artifact sync, Python
environment verification, detached session/log paths, status receipts, and a
strict instruction not to edit the canonical baseline or expose formal gate
seeds.
