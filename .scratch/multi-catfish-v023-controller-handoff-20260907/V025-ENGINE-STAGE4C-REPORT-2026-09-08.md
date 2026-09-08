# V0.25 engine stage-4c report — 2026-09-08

## Disposition

**HOLD / CONTROLLER_DECIDE.** The first real `a-r0` anchor does not fit the
sealed coordinator budget. The attempt was stopped before producing a receipt:
selection reached 59.698331280 s and then failed closed because FULL selected
a 100-user proposal, whose exact v1.5 Shapley certificate requires the
complete 2^100 coalition game. This is over the 10 s selection budget and it
leaves no room under the <=60 s complete-anchor budget. Per the stage-4c stop
rule, no additional selection approximation was introduced and calibration,
formal manifests, rehearsal, stride sealing, and smoke were not opened.

No formal R2 unit outcome exists. No q, projection, stride, calibration value,
or smoke number is fabricated below.

## Implemented before the real-anchor gate

- The large-world catalogue uses at most eight live actions per user, ranked
  by decision-instant nominal single-link decoding margin. It reports excluded
  counts and the best excluded margin. Pair users are ranked by the best exact
  nonlinear nominal unilateral surplus on the decision snapshot.
- Selection uses boundaries `{0,12,24,36,47}`; the committed validation and
  endpoint evaluator remain the 48-boundary path. Stage 2 uses sealed `M=64`
  plus BASE, the matching incumbent, and S0/evacuation rows.
- The three forecast offsets are dispatched through a shared batched helper.
  Forecast rows carry required-power, cap, cap margin, decoding margin, mean
  ACM spectral efficiency, and a schema stamp.
- Configuration scores own their C3 residual; no per-(user, action) maximum is
  reused across coalitions. The committed coalition enters the exact v1.5
  powerset/Shapley helper and fails closed when that certificate is not
  deployable.
- Zero-legal users are made NULL in the opening BASE and every derived row.
  All set-level arms use the served-count guard; the receipt states the exact
  applied and non-applied arm lists.
- The batch solver now implements absolute-or-relative convergence,
  `CONVERGED_SLOW`, monotonic/non-finite invalidation, iteration/status output,
  coarse grids, and forecast margin output.
- Anchor receipts carry an explicit opening-state/dependency certificate,
  per-anchor and per-unit A/I fields, certificate distributions, per-arm
  required-power and ACM-mode distributions, full embedded arm payloads for
  re-aggregation, and a shared conformance check.
- The controller-owned attempt-registry path is
  `/home/sat/mcrl-records/ATTEMPT-REGISTRY-2026-09.jsonl`.
- `_calibrate` is implemented as two complete 30-step reference rollouts
  (`decision_steps_ref=60`), not a one-step or provisional path.
- R7 is exposed as exploratory `r*=25 Mbit/s`, ordered after R6. R1 remains
  exploratory `r*=100 Mbit/s`; primary `a-r0` remains `50 Mbit/s`.
- Explicit KAT, synthetic-real, and smoke domain namespaces were added.

These changes are development code under HOLD. The failed real gate means they
are not represented as sealed or launch-ready.

## Verification

```text
PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q tests/physics_v025
159 passed (exit 0)
```

`python -m py_compile` passed for the modified runner and physics modules.
The existing suite remains green. The requested replacement of all 15
tautological KATs was **not completed before the mandatory stop**; therefore no
independent-oracle name list is claimed. This remains an explicit blocker, not
a paper closure.

## Real-anchor timing gate

Development namespace: quarantined world 1. Setting: `a-r0`. Carrier:
`nearest-eligible`. Arms declared: 14. Worker count: 1. The diagnostic provider
tape contained the anchor plus its three offsets; its construction was timed
separately. Because selection already failed, the required 33-step world tape
was not constructed merely to obtain an amortisation number.

| Phase | Seconds | Gate note |
|---|---:|---|
| provider, four-step diagnostic tape | 17.989771711 | separate; not a valid 33-step amortised-world number |
| catalogue | 3.045519408 | includes top-8 and exact nominal unilateral ranking |
| stage-1 scores | 36.475540816 | dominant completed phase |
| stage-2 forecasts | 17.759278750 | second dominant phase |
| selection | 0.011712220 | argmax only |
| validation before Shapley expansion | 2.405937545 | then fail-closed at changed_users=100 |
| ledger and receipts | NOT_REACHED | no receipt emitted |
| selection total to failure | **59.698283185** | **FAIL >10 s** |
| observed process interval to failure | **59.698331280** | incomplete anchor; therefore **FAIL <=60 s** |

The completed phase sum is 59.698283185 s (rounding difference below 1 us).
Stage 1 dominates. Stage 2 is also individually over the coordinator budget.
Exact large-coalition Shapley validation is unbounded at the selected 100-user
proposal and would dominate if allowed to expand.

## Rehearsal, manifests, stride, and smoke

| Item | Result |
|---|---|
| six immutable R2 manifests | `NOT_RUN_REAL_ANCHOR_GATE` |
| exact a-r0 calibration | `NOT_RUN_REAL_ANCHOR_GATE` |
| three-anchor rehearsal | `NOT_RUN_REAL_ANCHOR_GATE` |
| rehearsal q | `NOT_RUN_NO_RECEIPT` |
| 4 x 90 projection at concurrency 20 | `NOT_RUN_NO_Q` |
| sealed stride | `NOT_RUN_NO_Q` |
| development smoke | `NOT_RUN_REAL_ANCHOR_GATE` |
| smoke receipt location | none |
| SMOKE numbers table | unavailable; no smoke receipt exists |

## Audit-closure status

The implementation work above addresses parts of prior items 2, 10, 12, 13,
18, 20, 23, 25, 26, 28, 32, 35, and 36. It does not claim closure of every
CONTRADICTS/NOT DONE/PARTIAL audit row: independent KAT replacement, the live
boundary-17/10-degree fixtures, a-gamma twin, reciprocal reuse fixture,
five-event three-step fixture, pairwise-distinct 31-setting executed receipts,
and complete field-by-field independent re-aggregation remain unsealed. Formal
items 6–8 also remain unopened by the compute stop.

## CONTROLLER_DECIDE

1. Specify a deployable, prospective rule for v1.5 Shapley attribution when a
   selected coalition has more than ten changed users. Exact powerset
   evaluation for the observed 100-user FULL proposal is not computationally
   meaningful. No approximation is assumed here.
2. Decide whether stage-1 and stage-2 computation may receive another sealed
   approximation or implementation redesign. Their measured 36.48 s and
   17.76 s phases cannot satisfy a 10 s one-worker coordinator as written.
3. After a new controller decision and a passing complete-anchor measurement,
   resume with the missing independent KAT closures, six immutable manifests,
   exact calibration, rehearsal/q/projection, stride, and bounded smoke.

