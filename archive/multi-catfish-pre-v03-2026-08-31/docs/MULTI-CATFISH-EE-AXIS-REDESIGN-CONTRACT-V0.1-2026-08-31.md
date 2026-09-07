# Multi-Catfish EE-axis redesign contract V0.1

Date: 2026-08-31  
Status: **superseded candidate; see V0.2; no efficacy claim**

> Superseded on 2026-08-31 after the Opus Max co-design review found that a
> window-local multiplier does not align with the episode ratio-of-sums
> endpoint, `Full - noT` is causally mixed, and `Full - noS` conflicts with the
> simulator's single-load-semantics guard. The binding user constraint remains
> valid; the candidate targets below do not.

## 1. Controller ruling

The only scientific objective that remains fixed is the canonical energy
efficiency (EE). Everything else may be redesigned, including the definitions
of `r2` and `r3`, state features, Catfish proposals, learning targets,
bootstrap rule, target calibration, and scalarization weights.

The method must contain exactly three objective routes:

```text
C1 -> Q1: direct EE
C2 -> Q2: temporal EE effect
C3 -> Q3: spatial EE externality
```

The legacy handover and beam-load quantities may increase or decrease. They are
diagnostics and safety explanations, not optimization endpoints and not
acceptance gates.

At evaluation and deployment, all Catfish mechanisms are removed. The Main
policy selects one action from the three Main Q values. There is no auction,
voting, pair negotiation, decoder, coordinator, or post-training override.
Training-time counterfactual branches may use joint system information, but a
Q3 effect that cannot transfer to independent Main execution is a failure.

This ruling supersedes the unchanged-canonical-`r2/r3` semantics in the R6
authoring documents. The old R6 runs remain engineering evidence for their
frozen implementation only; they cannot validate or falsify this redesign.

## 2. Fixed EE quantity

For any equal-horizon trace \(\tau\), retain the current canonical physics and
EE accounting:

\[
\eta(\tau)=\frac{B(\tau)}{E(\tau)},\qquad
B(\tau)=\sum_{t\in\tau}R_t\Delta t,\qquad
E(\tau)=\sum_{t\in\tau}P_t^N\Delta t.
\]

The existing per-step additive decomposition also remains unchanged:

\[
r_{1,u}(t)=\frac{R_u(t)}{P_t^N},\qquad
\sum_u r_{1,u}(t)=\eta_t.
\]

Let \(M\) be a matched Main reference trace and \(C\) a candidate trace, with
\(\lambda=B^M/E^M\). Define the exact EE surplus

\[
g_\lambda(C,M)
=\bigl(B^C-B^M\bigr)-\lambda\bigl(E^C-E^M\bigr).
\]

Because

\[
\frac{g_\lambda(C,M)}{E^C}
=\frac{B^C}{E^C}-\frac{B^M}{E^M},
\]

the sign of \(g_\lambda\) is exactly the sign of the canonical EE change. No
legacy reward sign is needed for this identity.

## 3. Three distinct EE roles

### 3.1 C1 and Q1: direct EE

C1 retains the RIS-lineage EXP/ACRM idea, adapted to executed LEO experience.
Its labels use the unchanged \(r_1\) formula. Its job is to improve the direct
link/service-versus-system-power decision visible in the current state.

C1 must not receive temporal-fork or joint spatial-externality labels. EXP and
ACRM remain C1-private training mechanisms; neither modifies the EE formula.

### 3.2 C2 and Q2: temporal EE residual

C2 must learn the portion of an association decision's EE effect that exists
because the system evolves over time: segment continuation/reset, dwell and
handover timing, future geometry/availability, recurrence power, activation
churn, or ping-pong.

Preferred path-specific target over a bounded option of length \(H\):

\[
z_2=
\frac{
g_\lambda\!\left(C_{\mathrm{full}},M_{\mathrm{full}}\right)
-g_\lambda\!\left(C_{\neg T},M_{\neg T}\right)
}{c_2}.
\]

Here \(\neg T\) is a structural counterfactual that executes the same action
trace and exogenous draws while erasing only temporal memory, such as segment
continuation and handover/interruption state. If a physically coherent
\(\neg T\) evaluator cannot be defined, use the smaller matched-residual target

\[
z_2=
\frac{
g_\lambda^{1:H}(C,M)
}{c_2},
\]

where the current-slot contribution \(k=0\) is excluded. This deliberately
allows an immediately costly action whose later effect makes the combined EE
advantage positive.

The old \(r_2=-\Psi\) is retained only as a reported handover diagnostic.

### 3.3 C3 and Q3: spatial EE externality

C3 must learn the EE effect transmitted through shared spatial mediators:
beam load, bandwidth sharing, active-beam/satellite sets, shared maximum beam
power, PA efficiency, and co-channel interference.

Preferred path-specific target over a one-step or short window:

\[
z_3=
\frac{
g_\lambda\!\left(C_{\mathrm{full}},M_{\mathrm{full}}\right)
-g_\lambda\!\left(C_{\neg S},M_{\neg S}\right)
}{c_3}.
\]

Here \(\neg S\) holds the reference spatial mediators fixed while retaining the
candidate focal direct-link and temporal state. If such a structural freeze is
not physically coherent, use the unilateral difference-reward fallback:

\[
d_{3,u}(a)=
g_\lambda\!\left((a,\mathbf a_{-u}),
(a_u^M,\mathbf a_{-u})\right)-d_{1,u}^{\mathrm{iso}}(a),
\]

followed by within-state centering across valid actions. The isolated direct
term removes the part already attributable to C1. Both load balancing and load
consolidation must be eligible; the sign of legacy \(r_3=-U_b\) cannot select
or reject an outcome.

## 4. Common learning and action rule

The deployed Main action remains a masked scalarization:

\[
a_u^*=\arg\max_{a\in\mathcal A_u(s)}
\sum_{j=1}^{3}\omega_jQ_j(s_u^{(j)},a).
\]

The three Q routes may use role-specific observations. At minimum:

- Q1: current access, channel, angle, load, and direct power information;
- Q2: previous physical association, segment age/start state, recurrence power,
  dwell/TTT, remaining interruption state, and motion/history information;
- Q3: predecision load/activation, beam power marginal-cost summaries,
  co-channel occupancy/interference, and source/destination spatial context.

All bootstrapped heads must evaluate the same next action selected by the
deployed scalarized policy:

\[
a'_\omega=\arg\max_{a'}\sum_{j=1}^{3}\omega_jQ_j^-(s',a'),
\]

\[
y_j=z_j+\gamma^{h_j}(1-d)Q_j^-(s',a'_\omega).
\]

The former independent `max Q_j` bootstrap is not retained because it mixes
returns from three different hypothetical policies while deployment uses one
scalarized policy.

Catfish may use private training-time scorers or counterfactual oracles, but
the scientific topology has exactly three deployed objective Q values and one
Catfish-to-Q route per value. Private scorers are not additional objectives.

## 5. Pre-outcome and data rules

1. Trigger and proposal may read only pre-outcome state, masks, physical IDs,
   frozen models, and domain-separated RNG.
2. Counterfactual outcomes may create learning labels only after every
   scheduled candidate is sealed; realised outcomes cannot retrospectively
   decide which rows exist.
3. All valid favourable and unfavourable outcomes are retained.
4. Reference and candidate use equal horizons and common random numbers.
5. No Catfish-origin target may enter a nonmatching Main Q route.
6. Legacy \(\Psi\), \(U_b\), throughput, energy, service, active beams, and
   interference are recorded for explanation, not reward-direction gates.

## 6. Formula-first no-training gates

Before another short or long training run, test frozen anchors with the real
physics and copied RNG.

### C2 gate

- Enumerate stay, switch, and release-time alternatives in both directions.
- Measure full-window \(g_\lambda\), the temporal residual \(z_2\), service,
  useful bits, energy, and legacy handovers.
- Require held-out, service-safe positive temporal residuals that are not a
  fixed affine copy of the direct C1 score.
- If identical deployment observations and actions have opposite-sign \(z_2\)
  because of hidden segment history, expand the state before training.

### C3 gate

- Enumerate unilateral balancing, unilateral consolidation, already-active,
  newly-active, and reciprocal diagnostic cases.
- Measure full-window \(g_\lambda\), spatial residual \(z_3\), service, useful
  bits, energy, active resources, power, and interference.
- Require service-safe positive unilateral spatial effects beyond a
  dose-matched C1 proposal.
- Pair-positive but unilateral-negative opportunities fail the no-deployment-
  coordination requirement; they cannot be relabelled as a local Q3 Catfish.

For both roles, fail if the axis target is always zero, is indistinguishable
from Q1, is unobservable from the deployment state, or cannot change the final
scalarized action at any reasonable preregistered scale.

## 7. Empirical acceptance

The legacy `r2/r3` values do not appear in the success matrix. With matched
training seeds, equal environment steps, equal updates, equal replay budgets,
Main-only evaluation, and fresh held-out seeds, require both:

1. singleton EE contribution:

\[
C100>B000,\qquad C010>B000,\qquad C001>B000;
\]

2. leave-one-out EE contribution:

\[
F111>A011,\qquad F111>A101,\qquad F111>A110.
\]

The preferred result is also \(F111\) strictly best among all preregistered
arms. Every comparison uses ratio-of-sums EE and reports useful bits, energy,
service, active beams/satellites, and zero-power guards. A role that improves
its private target but not held-out Main-only EE has failed.

## 8. Current decision and next gate

The redesign is a **formula-level conditional GO**:

- C1 is directly EE-aligned by the frozen formula.
- C2 has a valid temporal EE target once temporal history is observable.
- C3 has a valid spatial EE target only if unilateral effects survive local
  execution; reciprocal-only benefit is not enough.

No new 1500-, 3000-, or 9000-episode run is authorized from the old R6 reward
definitions. The immediate next step is the bounded no-training oracle gate,
then an independent review of the formulas. A 9000-episode run still requires
explicit notice to the user before launch.
