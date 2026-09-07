# Multi-Catfish MCRL V0.12 zero-energy-supported C3 oracle preregistration

Status: **FROZEN BEFORE OUTCOME ACCESS**  
Scope: TRAIN-development oracle only; no learner, no optimizer, no TEST, and
no efficacy claim  
Decision: test two nested C3 teachers in a frozen order while keeping C1 and
OPS3-C2 fixed

## 1. Why this gate exists

V0.11 failed closed for both joint-C3 candidates.  Relative to the shared
`Q1 + O2` comparator, AP-MONE changed pooled EE by `-4.443940%`, M1-D by
`-1.489437%`, and the exact-O1 diagnostic by `-1.196711%`.  Each C3 view
increased delivered bits, but it increased total energy more strongly.

The mechanism receipt is specific.  Pooled active-beam steps rose from
`1195` for `DROP_C3` to `1711` for AP and `1770` for M1-D.  In the exact-O1
diagnostic they rose from `1460` to `1941`.  Among exposed anchors, the
executed joint profile had a positive current-slot energy difference in
`28/30` AP cases, `22/22` M1-D cases, and `21/21` exact-O1 cases.

This motivates one falsifiable change: C3 may always penalize non-focal
victim loss, but it may positively credit a spatial alternative only when
that unilateral alternative has exactly the same current network-energy
support as the C3-free reference.  Energy is a Boolean support condition;
it is never added numerically to the C3 target.

Prior V0.9 PNFE remains adverse evidence: its full arm changed EE by
`-11.0636%`, bits by `-5.3951%`, and energy by `+6.3736%` with `0/3`
positive lineages.  Therefore a plain or corrected PNFE rerun is not a live
candidate in this gate.

## 2. Immutable architecture and ownership

The production architecture remains exactly three independent 28-action Q
functions, one common safe mask, the left-to-right unweighted sum
`Q1 + Q2 + Q3`, one smallest-native-index masked argmax, and one executed
Main action.  There is no deployed sweep, second mask, coordinator, auction,
vote, route weight, sign flip, mixer, or post-training override.

The final metric remains canonical ratio-of-sums energy efficiency,

\[
\eta=\frac{\sum_{e,t,u}\Delta t\,R_{e,t,u}}
           {\sum_{e,t}\Delta t\,P^N_{e,t}}.
\]

C1 and corrected execution-equivalent OPS3-C2 are immutable in this gate:

- C1 owns focal current-slot delivered bits and the complete current-slot
  network-energy difference;
- C2 owns focal projected persistence at offsets `h=1,2,3`, including its
  marginal projected network-energy term;
- C3 may use current-slot non-focal delivered-bit effects only.  It contains
  no focal rate, numerical power or energy, `lambda0`, outage penalty,
  handover reward, or future term.

The three frozen Q1 checkpoints, OPS3 formula/runtime, `lambda0`, `kappa`,
`Delta t`, TLE archive, physics, masks, action semantics, and keyed-fading
rules remain byte-identical to V0.11.  Q1 and O2 are read-only.

## 3. Shared C3-free reference and physical signature

At every arm-owned state, compute frozen Q1 and exact OPS3 `O2` once and
define, independently for each user,

\[
b^0_u=\min\arg\max_{a\in\mathcal A_u^{\rm safe}}
      \{Q_{1,u}(a)+O_{2,u}(a)\}.
\]

For focal user `u` and legal action `a`, let

\[
c^a=b^0_{-u}\oplus a.
\]

Evaluate `b0` and every `c^a` with the exact canonical current-slot simulator
under one keyed common-random field.  Let `Gamma(c)` contain all of:

1. the post-feasibility served-user Boolean vector;
2. the ordered post-feasibility active `(satellite, beam)` set;
3. the ordered active-satellite set;
4. the per-beam RF-power vector in the same canonical beam-key order; and
5. canonical total network power `P^N(c)`.

The compatibility indicator is

\[
g_u(a)=\mathbf 1\{\Gamma(c^a)\equiv\Gamma(b^0)\}.
\]

Every equality in `g` is bit-exact, including the floating arrays and
`P^N`.  The tolerance is zero.  An evaluation-order defect is a mechanics
failure, not permission to widen the tolerance.  `g` is teacher-target
support, not a second deployment mask; all 28 entries remain controlled only
by the common safe mask.

## 4. Candidate ZR: zero-energy-supported spatial redistribution

For each non-focal user `v`, define the exact current-slot replacement effect

\[
d_{uv}(a)=\Delta t\,[R_v(c^a)-R_v(b^0)].
\]

The raw C3 target is

\[
z^{R}_{3,u}(a)=
\sum_{v\ne u}\min\{0,d_{uv}(a)\}
+g_u(a)\sum_{v\ne u}\max\{0,d_{uv}(a)\},
\qquad
O^{R}_{3,u}(a)=\frac{z^{R}_{3,u}(a)}{\kappa}.
\]

The reference entry `a=b0_u` is exact zero.  Illegal entries are zero behind
the common mask.  Victim loss always counts; positive spatial redistribution
counts only on exact zero-marginal-energy support.

ZR is the first candidate because it is the smallest direct repair of the
observed V0.11 activation-expansion mechanism.  Its worst-case teacher cost
is one reference plus at most `sum_u(|A_u|-1) <= 2700` unilateral current-slot
evaluations per anchor.

## 5. Candidate HR: zero-energy-supported insertion-harm relief

For focal user `u`, let `c^{-u}` be `b0` with only user `u` removed through
the dedicated non-committing focal-removal evaluator.  Define

\[
e_{uv}(a)=\Delta t\,[R_v(c^{-u}\oplus a)-R_v(c^{-u})],
\qquad
L_u(a)=\sum_{v\ne u}[-e_{uv}(a)]_+,
\]

and the Main-centered harm relief

\[
r_u(a)=L_u(b^0_u)-L_u(a).
\]

The second target is

\[
z^{H}_{3,u}(a)=\min\{0,r_u(a)\}
+g_u(a)\max\{0,r_u(a)\},
\qquad
O^{H}_{3,u}(a)=\frac{z^{H}_{3,u}(a)}{\kappa}.
\]

Reference and illegal entries are exact zero.  Raw positive insertion effects
are discarded; only reduction of non-focal insertion harm can become positive,
and then only under `g=1`.  HR adds exactly one focal-removed reference per
user and costs at most 2801 current-slot evaluations per anchor.

HR is not V0.9 PNFE: it has no `h>0` term, clips raw insertion gains, and
gates positive relative relief on exact zero-marginal-energy support.  It is
second because the adverse V0.9 direction remains relevant prior evidence.

## 6. Production-form actions and mandatory identities

Every arm uses exactly one production-form decoder:

\[
a^X_u=\min\arg\max_{a\in\mathcal A_u^{\rm safe}}
\{Q_{1,u}(a)+O_{2,u}(a)+O^X_{3,u}(a)\},
\]

where `X` is `R` for ZR or `H` for HR.  The `DROP_C3` action is exactly `b0`.

Because `b0_u` already maximizes `Q1+O2` and its C3 entry is zero, every
changed focal action must have strictly positive C3 value and therefore
`g_u(a)=1`.  This implication is asserted at runtime.  Also assert:

- common mask, reference zero, illegal zero, finite surfaces, and one
  smallest-index argmax;
- only the focal action changes in every unilateral branch;
- keyed field, environment, RNG, Q1, and O2 remain immutable;
- every positive ZR/HR entry has `g=1`;
- formula-identity residuals are at most
  `1024 eps * max(1, |left|, |right|)`; and
- no candidate consumes its arm outcome or another arm's action.

For each exposed production joint action, compare it to `b0` with exact
current-slot physics.  It must introduce no new active beam or active
satellite, and `P^N(a^X) <= P^N(b0)` under the same floating identity
tolerance.  A decrease is allowed; any increase is a hard failure.

## 7. Frozen TRAIN panel

- split: TRAIN only;
- fresh world seeds: `2026104801`, `2026104802`;
- seed freshness: a repository-wide text search before this draft found no
  prior occurrence of either seed;
- frozen Q1 lineages: `2026092101`, `2026092102`, `2026092103`;
- users: 100;
- steps: 10 per episode;
- arms: `DROP_C3`, `FULL_ZR`, `FULL_HR`;
- 18 episodes total: two worlds times three lineages times three arms;
- one keyed field per world, shared across its arms and lineages;
- field component: `MCRL_V012_ZERO_ENERGY_C3_ORACLE_V1` plus world seed;
- field key excludes arm, lineage, policy label, action, target, and outcome.

The 12 candidate episodes require at most 330120 current-slot
counterfactual evaluations.  This is heavy no-browser oracle work.  Run it
as independent shards on the Ubuntu server, with an estimated 20--40 minute
parallel wall time plus verification.

## 8. Frozen candidate gates

For `X` in `{ZR, HR}`, `PASS_X` requires every condition below:

1. all contract/source/runtime/checkpoint/TLE hashes authenticate;
2. TRAIN-only status and the absence of learner, optimizer, target network,
   TEST access, future rollout, or policy query are authenticated;
3. every mechanics and formula identity in section 6 passes;
4. supported-positive target spread is nonzero and the production action has
   nonzero C3 exposure;
5. every changed action has `g=1`;
6. at every exposed anchor, the production joint action adds no active beam
   or satellite and does not increase current `P^N` over `b0`;
7. pooled ratio-of-sums EE across both worlds is strictly above `DROP_C3`;
8. ratio-of-sums EE is strictly above `DROP_C3` within each world;
9. at least two of three lineage EE contrasts are positive within each world;
10. served user-steps are noninferior pooled and within each world, with at
    least two of three nonnegative lineage service contrasts per world; and
11. active-beam-steps and active-satellite-steps are not above `DROP_C3`
    pooled or within either world.

One user-step service shortfall fails.  No surrogate, confidence interval,
pooled magnitude, or diagnostic can rescue a failed binding condition.

Required raw receipts include per-step actions, bits, energy, service,
active beam/satellite counts, Q1/O2/O3/mask hashes, compatibility counts,
positive-support counts, changed-action compatibility, exact joint support
comparison, environment/RNG digest, and every lineage/world/pooled contrast.

## 9. Frozen ordered decision

Magnitude never selects between candidates.

| Frozen condition | Decision |
|---|---|
| `PASS_ZR` | `GO_ZR_C3_LEARNABILITY_PREREG_ONLY` |
| `not PASS_ZR and PASS_HR` | `GO_HR_C3_LEARNABILITY_PREREG_ONLY` |
| neither passes | `STOP_C3_ORACLE_REDESIGN_REVIEW_SEAM` |

ZR is selected whenever it passes, regardless of the HR magnitude.  There is
no post-outcome scale, sign, threshold, tolerance, support, seed, horizon,
feature, or acceptance-rule change.  Do not add worlds after opening results.

## 10. Claim ceiling and next action

A GO permits only a separately preregistered state-only Q3 learnability and
production-reproduction gate.  It does not establish a learned Q3, held-out
performance, C3 efficacy, three-head efficacy, or permission for
100/500/1500/3000/9000-episode training.

A later learner may consume decision-time action/focal geometry, segment
status, lagged beam/satellite activation, lagged load/rate burden and RF
headroom, cochannel victim/interference summaries, contender pressure, and
the common safe mask.  It must not consume `g`, any counterfactual rate,
power or signature, `b0`, Q1/O2 values or ranks, selected actions, outcomes,
future information, arm identity, or target signs.

If both candidates fail, stop.  A full-horizon coalition/residual target is
not authorized by this contract because it would reopen the C1/C2 ownership
seam and require a separate adjudication before implementation.
