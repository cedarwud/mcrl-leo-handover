# Declaration — the successor study's endpoint is constrained pooled EE

Date: 2026-09-11. **Owner decision**, recorded before any constrained-endpoint run exists.

## Owner decisions, verbatim

1. *"不改的話沒辦法工作也只能改了吧?"* — adopt the constrained endpoint.
2. *"就先沿用 c1/c2/c3 等最終定案再來改敘事"* — keep the names C1/C2/C3 for now, with the
   redefinition in `V025-CONTROLLER-PLAN-THREE-CATFISH-ON-THREE-HEADS-2026-09-11.md`
   (C1 → `Q_B` bits, C2 → `Q_H` handover constraint, C3 → `Q_E` energy). Final naming deferred.
3. *"如果已經沒必要是佔用資源的話就殺掉"* — executed, see below.

## Framing, fixed now

This is a **new prospective study**, not a rescue of the old endpoint — the condition both
cross-model reviews (agy, astra) attached to PROCEED WITH CHANGES. Therefore:

- The **unconstrained** pooled-EE result — `MAX_NOMINAL_GAIN` beats the trained checkpoint by
  19.8% (22.2% after anchor ablation; 1.1916 under TDM accounting) — is **reported as a
  negative control**, never re-labelled.
- No figure measured before this declaration is re-scored as evidence *for* the new endpoint.

## Endpoint

**Primary:** pooled EE = pooled decoded bits / pooled system joules (ratio of sums, full-buffer
numerator, no demand cap), **subject to**:

- **C-H (handover cap):** inter-satellite handover rate `H_inter <= 0.6016` per user-step.
  Source: Sun, Zhu & Peng 2024 set `H̄ = 0.004` per 0.2 s epoch as an inter-satellite
  handover-frequency budget; `0.004 / 0.2 s * 30.08 s = 0.6016`. **The conversion is derived;
  the original ceiling is a stipulated policy budget, and is cited as such.** Applied to
  inter-satellite events because that is what the source constrains (DR-2 / ASK-2).
- **C-S (service):** complete-service availability non-inferior to the no-catfish reference,
  95% cluster-bootstrap interval of the difference above **−0.5 pp** — the sealed guard's margin,
  unchanged.

**Always reported alongside, not constrained:** `H_intra` per user-step, `H_total`, handovers
per user-minute, served fraction, mean active beams, and the Dinkelbach residual.

**Declared sensitivity (secondary, reported whatever it shows):** a total-rate cap
`H_total <= 0.40` per user-step (`1/15` pass-scale magnitude + `1/3` stipulated beam-switch
budget; ASK-2 classifies the whole value as stipulated). It cannot replace C-H after results.

## Why these numbers are not outcome-fitted

Neither cap is derived from any evaluated policy's operating point (learner 0.2796 total,
`MAX_NOMINAL_GAIN` 0.7117 total; inter-satellite splits not yet read). C-H is a unit conversion
of a published study's budget; C-S is the pre-existing sealed margin. **Neither may be changed
after a constrained-endpoint result is seen.**

## Resource action executed

All current-design trainings killed per `V025-CONTROLLER-RULING-C1VSGAIN-KILL-ALL-2026-09-11.md`
row 3, with the owner's explicit authorisation after the permission classifier had refused:
44 SIGSTOPped processes in seedpar / exacttrain / q1v3 workspaces, **plus PID 3131678** — the
SEEDPAR "sequential" stage-C training (`run_stagec_training_v2.py`, 16-seed x 4000 epochs on the
exact-93 corpus). **Correction:** the earlier ruling excluded PID 3131678 as "a stray not named by
the rule"; it was named (it is SEEDPAR's sequential run) and was missed only because its working
directory is `exact93-ws`, which the cwd filter did not include. Server memory in use 23 → 7 GB;
zero stopped processes remain.
