# Multi-Catfish MCRL V0.3 C2 post-gate design decision

Date: 2026-08-31  
Status: **V0.3B implementation/test complete; fresh preregistration and
scientific gate pending; training NO-GO**

## 1. Decision

Retain the C2/Q2 temporal EE-surplus route and its current target formula, but
replace the fixed-length candidate hold with this source policy:

`hold-while-legal, then monotone branch-local Main release`

The isolated V0.3B implementation and targeted-test gate are complete; the
fresh physical-headroom gate remains pending.

This is a V0.3 source-grammar amendment, not a new objective and not a
re-adjudication of the sealed 2026-08-31 gate. That gate remains
`INDETERMINATE`.

The decision is supported independently by:

- the sealed C2 result and exact replay audit;
- a fresh-context audit of every gate hash, target, service receipt, and
  support rejection;
- a Claude Opus Max post-gate design review comparing additional seeds,
  shorter fixed hold, reactive release, and abandoning C2.

Both independent reviews identify the same mechanism: all 14 censored branches
are genuine candidate-side `focal_hold_expired` events at offset 1 or 2. The
instrument is sound; the fixed hold grammar is the defect.

## 2. Formula remains unchanged

For focal user \(u\), fixed TRAIN-only multiplier \(\lambda_0\), interval
\(\Delta t\), and matched horizon \(H^c=4\):

\[
\zeta_{2,u}
=
\sum_{k=1}^{H^c-1}
\left[
\Delta t\sum_{i\in\mathcal U}
\left(R_i^C(k)-R_i^M(k)\right)
-
\lambda_0\Delta t
\left(P_C^N(k)-P_M^N(k)\right)
\right].
\]

The opening split, exact identity, shared \(\kappa\), pairwise Q2 loss, three-Q
deployment sum, and ablation definitions do not change.

## 3. Prospective C2 policy

### 3.1 Opening rule

At a sealed Main departure anchor:

1. use the focal incumbent when it is legal in the opening action table;
2. otherwise use the legal non-Main rival with maximum predecision
   `candidate_sinr`, evaluated against the previous radiating set;
3. resolve ties by physical NORAD ID, cell ID, and action ID.

The opening decision reads no future state and no outcome.

### 3.2 Reactive release rule

Let \(k^\star\) be the first downstream offset at which the held physical key is no
longer uniquely executable in the focal user's **candidate-branch
contemporaneous predecision action table**. If no such event occurs, use the
planned horizon release.

- before \(k^\star\): hold the opening candidate;
- at and after \(k^\star\): execute complete contemporaneous branch-local Main;
- release is monotone and latched; the held key is never reacquired;
- the trigger cannot read a future offset, the reference branch, \(\zeta_2\), a
  service outcome, or any post-hoc score.

This makes expiry a measured temporal consequence instead of an informatively
censored row. `focal_hold_expired` becomes `release_reason=support_expired`,
not a support rejection.

### 3.3 Required row bindings

Every new \(D^t\) row must bind at least:

- `release_offset`;
- `release_reason` in `{horizon, support_expired}`;
- held physical key and per-offset match count;
- opening source rule;
- anchor/seed/schedule/source/checkpoint/random-field digests;
- raw per-user rates, system power, served vectors, and per-offset surplus.

Positive, zero, and negative complete targets are all retained.

## 4. Fresh evidence design

Use a fresh non-overlapping seed block. The old gate seeds and smoke seed are
burned for decision purposes. Before outcome generation, seal:

- one fixed \(\lambda_0\) and its hexadecimal representation;
- \(H^c=4\) and offsets 0--3;
- all schedules, source versions, release semantics, and service guards;
- an anchor-level decision rule, because focal rows within an anchor are
  clustered;
- an elective/epochal departure-mass coverage report, defined only from
  Main's predecision proposed departures;
- an explicit release-offset census so a route that degenerates to almost
  one-step behavior cannot pass merely because it completes;
- the handling of an unexercised max-SINR fallback branch.

The new physical-headroom gate must require zero instrument/non-mutation
violations, near-total expected completion under the release policy, service
receipts, and positive replication across multiple distinct anchors and fresh
seed worlds. Exact quotas and seed IDs must be sealed before results are
revealed.

Even a physical-headroom `GO` authorizes only a separately preregistered
bounded learnability pilot. It does not authorize short-EP ablation or an EE
efficacy claim.

## 5. Paper and figure consequence

The overall Multi-Catfish story remains unchanged:

- C1/Q1: focal now;
- C2/Q2: everyone later;
- C3/Q3: non-focal now;
- three independent Q functions, one masked Main action.

Only the C2 temporal-fork depiction changes: show a hold segment followed by
either planned release or an earlier support-triggered release, both returning
to branch-local Main. Keep all result values and efficacy statements `TBD`.
