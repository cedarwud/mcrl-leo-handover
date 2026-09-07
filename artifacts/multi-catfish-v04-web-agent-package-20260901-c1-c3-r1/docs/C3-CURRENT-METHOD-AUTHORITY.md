# C3 current method authority

Date: 2026-09-01  
Status: **frozen V0.4 C3 paper-facing method and current evidence**

This document is the current C3 method authority for the narrow package. The
V0.4 victim-burden observation/source replaces the superseded V0.3 C3
observation/source. C3 remains unilateral and does not define a second
deployment policy.

## Role and physical target

C3/Q3 is the non-focal opening rate externality route. For the same sealed
candidate/reference pair as C1, its target is:

\[
\zeta_{3,u}=\Delta t\sum_{i\in\mathcal U\setminus\{u\}}
 [R_i^C(0)-R_i^M(0)].
\]

The target measures immediate rate changes for users other than the focal
mover. It is not a coordinated multi-user action.

## Frozen V0.4 observation

For legal action \(a\), \(b_u(a,t)\) is the physical satellite-beam pair
named by the action, \(a_i(t-1)\) is user \(i\)'s previous committed action,
and \(\rho\) returns a pair's satellite identity. The V0.4 action-aligned
victim burdens are:

\[
b^{\mathrm b}_{u,a}(t)=\frac{\Delta t}{\kappa}
\sum_{\substack{i\in\mathcal U\setminus\{u\}\\
 b_i(a_i(t-1),t-1)=b_u(a,t)}}R_i(t-1),
\]

\[
b^{\mathrm s}_{u,a}(t)=\frac{\Delta t}{\kappa}
\sum_{\substack{i\in\mathcal U\setminus\{u\}\\
 \rho(b_i(a_i(t-1),t-1))=\rho(b_u(a,t))}}R_i(t-1).
\]

Both blocks use committed previous-slot associations and served rates only;
the focal user's previous rate is excluded. They do not read current joint
actions, call a candidate evaluator, inspect a target, or introduce a
proposal pass. They replace the old C3-specific eligible-load and binary
satellite-active blocks. The frozen method retains state width 228 and the
local scorer shape `12 -> 100 -> 50 -> 50 -> 1`.

## Source and learner routing

The informed C3 source is selected from pre-outcome lagged metadata. It ranks
focal users by absolute beam-burden contrast and then beam victim pressure;
satellite contrast and pressure are auxiliary stable tie-breaks. It enumerates
unilateral legal opening actions at sealed anchors, retains every observed
target sign, caps emitted siblings at four per focal-state context and
selected contexts at eight per physical anchor, requires a connected
28-action TRAIN graph, and admits validation only on directed action pairs
supported by TRAIN. The production source uses four TRAIN seeds, three
validation seeds, and zero TEST seeds.

C3 rows belong to \(D^o\) and update only \(Q_3\). The C3 burden blocks are
observations, not action coordination. Opening shared activation and power
remain charged to C1's target; C3 does not duplicate them.

## Why there is no energy term in C3

There is intentionally no energy term in \(\zeta_{3,u}\). The focal action is
the sole opening intervention, so its complete shared opening energy change is
already assigned to C1. Adding that same energy difference to C3 would double
count it. Consequently C3 is invariant to \(\lambda_0\), while the physical
world may still change energy as an indirect consequence of the focal action.

## Current evidence and claim ceiling

The five-arm frozen-policy source in
`docs/MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-RESULT-2026-09-01.md` reports
`FULL` versus `DROP-C3` of **+21.970%**, with **2/3** positive initialization
contrasts and **30/30** positive physical-world contrasts.

The separate confirmatory source in
`docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-RESULT-2026-09-01.md` reports a
different `FULL` versus `DROP-C3` block at **+21.216%**, with all 30
physical-world contrasts positive and two of three initialization contrasts
positive. The two percentages are not merged or averaged. C3 is frozen; this
does not confirm C1, C2, the whole method, or `FULL` versus frozen Main.

