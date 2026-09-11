# r2 / r3 — change history, coupling, and design premises

**No change to r2 or r3 was ever made to serve the stage-C C1/C2/C3 work: every commit that altered either reward's computed value landed 2026-08-21 … 2026-08-23, before the frozen checkpoint (2026-08-25) and before stage-C existed, and no stage-C module imports `PHI1`, `PHI2`, `HANDOVER_COST`, `r3_counting`, `user_beam_load`, or `mcrl.runtime.reward_calibration` at all.**

Audit date 2026-09-11. Read-only. Repo `/home/u24/papers/mcrl-leo-handover`,
branch `wip/multi-catfish-v023-20260907`.

Every "Verified" claim below carries a file:line I read in this session.
"Inferred" claims are arithmetic or reasoning over those reads and are
segregated per section.

---

## Q1 — Current definitions

### r2 — negative handover cost

**Computed at** `/home/u24/papers/mcrl-leo-handover/src/mcrl/env/step.py:1101`,
inside `StepEnvironment._rewards` (`step.py:1051-1104`):

```python
rewards.append(
    RewardComponents(
        r1_system_ee_contribution=float(r1[uid]),
        r1_throughput=float(rate[uid]),
        r2_handover=-HANDOVER_COST[handover],
        r3_load_balance=float(r3[uid]),
    )
)
```

The `handover` label comes from `step.py:1084-1089`:

```python
ledger = self._ledgers[uid]
handover = (
    ledger.observe(realised)
    if commit
    else classify_handover(ledger.previous, realised)
)
```

**Coefficients** — `/home/u24/papers/mcrl-leo-handover/src/mcrl/env/action_contract.py:408-418`:

```python
PHI1: float = 0.5
"""**S** — the paper gives only ``0 < φ1 < φ2``."""

PHI2: float = 1.0
"""**S** — same."""

HANDOVER_COST: dict[HandoverClass, float] = {
    HandoverClass.NONE: 0.0,
    HandoverClass.INTRA_SATELLITE: PHI1,
    HandoverClass.INTER_SATELLITE: PHI2,
}
```

**The three branches** — `HandoverClass`, `action_contract.py:399-406`, priced
by the table above and assigned by `classify_handover`
(`action_contract.py:421-455`):

| branch | meaning | price | r2 |
|---|---|---|---|
| `NONE` | episode start, **or** current step unserved, **or** same satellite *and* same cell | `0.0` | `0.0` |
| `INTRA_SATELLITE` (`φ1`) | same satellite, **different cell** | `PHI1 = 0.5` | `−0.5` |
| `INTER_SATELLITE` (`φ2`) | **different satellite**, *including re-entry after an outage* | `PHI2 = 1.0` | `−1.0` |

Decision order, verbatim from `action_contract.py:445-455`:

```python
if isinstance(current, _Unserved):
    return HandoverClass.NONE
if previous is None:
    return HandoverClass.NONE
if isinstance(previous, _Unserved):
    return HandoverClass.INTER_SATELLITE
if previous.norad_id != current.norad_id:
    return HandoverClass.INTER_SATELLITE
if previous.cell_id != current.cell_id:
    return HandoverClass.INTRA_SATELLITE
return HandoverClass.NONE
```

Mutually exclusive by construction — a step that changes both satellite and
cell is `φ2`, never `φ1 + φ2` (`action_contract.py:442-444`). Re-entry after
outage is `φ2` deliberately, to close the "go offline to clear the handover
cost" hole (`action_contract.py:437-441`).

**Units / normalisation.** r2 is dimensionless
(`src/mcrl/env/step_types.py:176`: "dimensionless penalty (0, −φ1, or −φ2)").
No normalisation at source. The trainer divides by
`C2_SCALE` at `/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/reward_calibration.py:63`:

```python
C2_SCALE: float = PHI2
```

i.e. `c_2 = φ2 = 1.0`, an analytic bound, not a measured p95 — the module
states at `reward_calibration.py:24-29` that r2's signed p95 is 0 (most steps
have no handover), so the p95 rule used for `c_1` and `c_3` would divide by
zero.

### r3 — negative beam occupancy

**Computed at** `/home/u24/papers/mcrl-leo-handover/src/mcrl/env/step.py:1072`
(`r3 = r3_counting(resolution)`), defined at
`/home/u24/papers/mcrl-leo-handover/src/mcrl/env/service.py:264-277`:

```python
def r3_counting(resolution: ServiceResolution) -> np.ndarray:
    """B13: ``r3,u(t) = −U_{b_u}(t)``.
    ...
    """
    return -resolution.user_beam_load()
```

`user_beam_load` — `/home/u24/papers/mcrl-leo-handover/src/mcrl/env/service.py:164-182`:

```python
loads = np.zeros(self.served.size, dtype=np.float64)
for uid in range(self.served.size):
    if self.served[uid]:
        loads[uid] = float(
            self.eligible_load_by_beam[
                (int(self.serving_satellite[uid]), int(self.serving_cell[uid]))
            ]
        )
return loads
```

So **r3,u = −(number of served users on the beam that serves u)**, and
**r3,u = 0 for an unserved user** (`service.py:167-169`). The load key is
`(norad_id, cell_id)` — a beam, not a cell (PATCH P-17). "Eligible" load is the
count **after** the per-link power-feasibility check (`service.py:240-252`).

There is **no coefficient** in r3 — it is a raw head count, in whole users
(`step_types.py:176-179`). Normalisation is trainer-side only:
`C3_SCALE = float(R3_CALIBRATION_SCALE) = 6`
(`reward_calibration.py:75-76`), the p95 of `|r3|` over served steps rounded
to the nearest integer, frozen by probe P3 / question Q-D.

### How the three heads reach training

`/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/modqn.py:590-620`
reads the three fields directly (no selector since P-20), and
`modqn.py:1269` applies `apply_reward_calibration(reward_vec, cfg)` before
pushing to replay. Calibration is **on by default since 2026-08-23**
(`src/mcrl/runtime/trainer_spec.py:94-105`), mode
`"divide-by-fixed-scales"`, scales `REWARD_SCALES = (C1_SCALE, C2_SCALE, C3_SCALE)`
= `(2029238.4328742754, 1.0, 6.0)` (`reward_calibration.py:42, 63, 75, 79`).

---

## Q2 — Change history

### r3

| # | commit | date | summary | what changed in the computation | stated reason |
|---|---|---|---|---|---|
| 1 | `f5d0f1fe` | 2026-08-22 | W-07: counting-form r3 and the execution mask, plus B10's revision | **The formula itself**: normalised gap ratio → `−U_{b_u}` head count. Introduced `r3_counting` in `env/service.py`. | Commit message: *"G-4 holds: r3 depends only on the user's own beam load, with no global scalar… The sum identity and the even-spread minimum are tested, and **the old form's load-blindness is demonstrated rather than asserted**."* The current docstring restates it (`service.py:274-276`): *"the old form was blind to load because `U_{s,v}` cancelled out of it entirely."* Also: *"B13 changed r3's units from a normalised gap to a raw head count, so the old calibration scale is meaningless for it."* |
| 2 | `7fe3e83f` | 2026-08-22 | Ruling 2026-08-22: delete the per-satellite beam-count cap | touched `service.py`; removed the beam-count ceiling that would have darkened beams | keeps r3's load quantity free of a count cap; no change to `r3_counting`'s return |
| 3 | `fd021f26` | 2026-08-22 | W-17: wire the interference sums and the StepEnvironment | PATCH **P-17**: load keys changed from `cell_id` to `(norad_id, cell_id)`; `eligible_load_by_cell` → `eligible_load_by_beam`. This **does** change r3's value (two satellites illuminating the same cell no longer pool). | `docs/PATCH-LEDGER.md:213+` (P-17): the load quantity must be per **beam**, because one beam is one amplifier |
| 4 | `d6ba4a23` | 2026-08-22 | Apply the controller's rulings C-1 … C-15 | touched `service.py`; C-11 deleted `m^e`, C-2 deleted the load-based PA surface | ruling compliance; the `r3_counting` body is unchanged |
| 5 | `a8e293c4` / `1655048c` | 2026-08-22 | W-16 / W-03 | earlier scaffolding of the load accounting | — |
| 6 | `1f4d9dab` | 2026-08-23 | P3 closes Q-D at scale 6, and theta^R_min is derived not literal | **Not the reward** — froze `R3_CALIBRATION_SCALE = 6`, i.e. `c_3`. Changes the *training-side* effective weight `ω_3/c_3`, not `r3` itself. | probe P3 answered the pre-registered Q-D |
| 7 | `5d484f80` | 2026-08-23 | Null baselines for P3, and c_1/c_2 frozen so scalarisation is not degenerate | froze `c_1`, `c_2`; again calibration, not `r3` | `reward_calibration.py:31-36`: uncalibrated, the `ω_1 r_1` term is ~10^5× the `ω_3 r_3` term |

**On P-13 specifically.** P-13 is *not* the formula change. `docs/PATCH-LEDGER.md:166-176`
records P-13 as a **docstring / typed-contract fix**: `RewardComponents`'s
description still said "dimensionless ratio (negative gap / num_users)" after
B13 had made the value a raw head count. Source line `env/step_types.py:613`
(now `step_types.py:176-179`). Discovered by an external audit
(`codex gpt-5.6-luna`, `docs/AUDIT-external-luna-2026-08-22.md`). The formula
change is **B13, landed in `f5d0f1fe` (W-07)**.

### r2

| # | commit | date | summary | what changed | stated reason |
|---|---|---|---|---|---|
| 1 | `23d97cff` | 2026-08-21 | W-01: port frozen MODQN algorithm + interface types byte-for-byte | `r2_handover` field arrives with the port | byte-for-byte port |
| 2 | `1655048c` | 2026-08-22 | W-03: action index contract and environment-side accounting | **Defines r2 as it stands today**: `PHI1`, `PHI2`, `HANDOVER_COST`, `HandoverClass`, `classify_handover`, `HandoverLedger` | SDD §4A.4; the identity-based (not index-based) handover contract, and the re-entry-is-`φ2` rule (`action_contract.py:437-441`) |
| 3 | `fd021f26` | 2026-08-22 | W-17 | wires `HANDOVER_COST` into `StepEnvironment._rewards` | integration |
| 4 | `5388acfd` | 2026-08-22 | W-09 + W-10 + W-08 | PATCH **P-05**: removed a PopArt standardisation branch that would have rescaled r2 and r3. **Dead code** — `popart_enabled` was always `False` and `runtime/popart_online.py` was never ported. No value changed. | in-diff comment: *"the branch was unreachable code holding an import the tree could not satisfy"* |
| 5 | `facda718` | 2026-08-22 | W-18: trainer adapter, PREREG draft, ruling C-8 | prints `phi1=…, phi2=…` into the PREREG manifest (`runtime/prereg.py:528`) | disclosure |
| 6 | `14174d60` | 2026-09-07 | WIP snapshot 2026-09-07 | See below. | content-addressed snapshot of the working tree |

**The only post-freeze touch of the reward code: `14174d60`.** It added
`commit: bool = True` to `_rewards` (`step.py:1051-1056`) and a non-mutating
branch (`step.py:1084-1093`), plus `evaluate_actions` /
`evaluate_actions_without_user` / `_evaluate_selected_actions`
(`step.py:643-727` in the current tree). On the committed path
(`commit=True`) the code is byte-equivalent to before: `ledger.observe(realised)`,
`self._previous_association[uid] = …`, `r2_handover=-HANDOVER_COST[handover]`,
`r3_load_balance=float(r3[uid])`. **No coefficient, branch price, or formula
moved.** The same snapshot changed `C1_SCALE` from `2471140.576` to
`2029238.4328742754` — that is `c_1` (r1's scale), not r2 or r3.

Commits `c3d0d34c` and `cbe80a8e` (2026-09-10) match a pickaxe on
`r3_counting` only through `.scratch/` and `artifacts/` payloads; they change
no file under `src/`.

---

## Q3 — Was any of it done for C1/C2/C3?

| change | classification | evidence |
|---|---|---|
| r3 formula, ratio → `−U_{b_u}` (`f5d0f1fe`, 2026-08-22) | **(i) defect fix in the reward itself** | The commit message and `service.py:274-276` state the old form was *load-blind* — `U_{s,v}` cancelled out, so the "load balance" head did not depend on load. Dated 6 days before the first stage-C construct (the C1 STOP redesign review is 2026-08-28). |
| r3 load key cell → beam, P-17 (`fd021f26`) | **(i) defect fix** | `docs/PATCH-LEDGER.md` P-17; one beam is one amplifier, so pooling two satellites' users in one cell was wrong. |
| `c_3 = 6` frozen (`1f4d9dab`), `c_1`/`c_2` frozen (`5d484f80`) | **(i)/(ii)** — calibration, driven by pre-registered probe P3 questions Q-D/Q-F/Q-G | `reward_calibration.py:1-36`; `service.py` `R3_CALIBRATION_SCALE`. Both 2026-08-23, before the frozen checkpoint. |
| r2 definition (`1655048c`) | **(ii) change to match a paper/spec** | `action_contract.py:399-406` — "The three mutually exclusive branches of paper eq. (3.27)"; SDD §4A.4. |
| PopArt branch removal, P-05 (`5388acfd`) | **(i) dead-code removal, no value change** | in-diff comment quoted above. |
| P-13 docstring fix | **(i) contract/implementation mismatch** | `docs/PATCH-LEDGER.md:166-176`; external audit finding D-10. |
| `_rewards(commit=False)` + `evaluate_actions*` (`14174d60`) | **(iii) made to serve stage-C — but it changed no reward value** | Callers are all stage-C: `runtime/ee_axis_joint_c3.py:231,241,563,564`; `runtime/ee_axis_opening_source.py:614-615`; `runtime/ee_axis_c1_dull_source.py:163`; `runtime/ee_axis_v04_c3_opening_source.py:636-637`; `runtime/ee_axis_zero_marginal_c3_live.py:483,517,538`; `runtime/head_pivotality.py:243`. What it added is a **read-only** evaluation path that classifies a handover without advancing the ledger. r2's price table, r3's count, and the committed path are untouched. |

**Plain answer.** None of r2's or r3's coefficients, branches, formulas or
normalisations were ever changed for C1/C2/C3. They are different subsystems,
and that shows up structurally as well as historically: a grep over
`src/mcrl/runtime/ee_axis_*.py` and `src/mcrl/algorithms/ee_axis_*.py` for
`HANDOVER_COST`, `PHI1`, `PHI2`, `r3_counting`, `user_beam_load`,
`reward_calibration` returns **zero hits**. The single stage-C-motivated edit
to the reward *file* is the `commit=False` read-only branch, which by
construction produces the same numbers the committed path does.

---

## Q4 — The coupling that actually exists

### r2 vs the stage-C handover price

`PHI1 = 0.5` and `PHI2 = 1.0` (`action_contract.py:408, 411`) are
**dimensionless preference weights**, declared "**S**" (stipulated) — the
paper gives only `0 < φ1 < φ2`.

Complete consumer list for `HANDOVER_COST` / `PHI1` / `PHI2` across `src/` and
`scripts/`:

| file:line | role |
|---|---|
| `src/mcrl/env/step.py:1064, 1101` | the only live use — `r2_handover = -HANDOVER_COST[handover]` |
| `src/mcrl/env/action_contract.py:498-500` | `HandoverLedger.cost()` — convenience wrapper returning `-r2`, same table |
| `src/mcrl/runtime/reward_calibration.py:40, 63` | `C2_SCALE = PHI2` |
| `src/mcrl/runtime/prereg.py:400-401, 528` | prints `phi1=…, phi2=…` into the PREREG manifest |
| `scripts/analyze_corrected_postrun.py:34, 601` | read-only replay audit that re-derives expected r2 |
| `src/mcrl/env/step_types.py:56` | comment mapping paper symbols to code names |

Nothing else. **No stage-C module is on that list.**

### Where `F = B − eta_ref·E − Phi` actually lives — and its `Phi`

**It is not on this branch.** `physics_v025/` and `stagec_v025/` exist only on
non-HEAD branches (`server/v025/stagec`, tip `d695e612`;
`origin/server/v025/synth`, tip `16e3d486`). HEAD is
`wip/multi-catfish-v023-20260907`, which has neither.

`d695e612:src/mcrl/physics_v025/targets.py:129-150` (read directly):

```python
def network_objective(outcome, *, lambda_bits_per_j, eta_ref, kappa_bits_per_user_s):
    """Return the v1 objective ``F = B - eta_ref E - Phi_cost``.

    ``NetworkOutcome.phi`` is the pre-existing dimensionless *signed
    preference* (handover costs are negative).  Therefore
    ``Phi_cost = -kappa * outcome.phi`` and the executable form is
    ``B - eta_ref E + kappa * phi``.
    """
    ...
    return outcome.bits - eta * outcome.joules + kappa * outcome.phi
```

`Phi` is `phi_qos` (`16e3d486:src/mcrl/physics_v025/targets.py:72-82`), which
subtracts one constant per handover event, and the constants are
`16e3d486:src/mcrl/physics_v025/constants_v025.py:70-71` (read directly):

```python
PHI_SAME_SATELLITE = 0.5   # Provenance: round-3 §2.23 retained benchmark preference; not joules or seconds.
PHI_SATELLITE_CHANGE = 1.0 # Provenance: round-3 §2.23 retained benchmark preference; not joules or seconds.
```

**These are numerically identical to r2's `PHI1 = 0.5` / `PHI2 = 1.0`, but they
are a restated literal, not a derivation.** `targets.py` imports only
`mcrl.errors`, `.calibration`, `.constants_v025`, `.endpoint`
(`d695e612:src/mcrl/physics_v025/targets.py:11-20`) — nothing from
`mcrl.env.action_contract`. `constants_v025.py` gives them their own
provenance line ("round-3 §2.23"), not a reference to eq. (3.27).

**So: same numbers, different definition sites, no dependency.** Editing
`PHI1`/`PHI2` would leave `PHI_SAME_SATELLITE`/`PHI_SATELLITE_CHANGE`
untouched, and vice versa — the two would silently diverge. That is the one
real coupling hazard this audit found, and it is a *duplication* hazard, not a
shared-coefficient one.

Two further differences that matter if either is changed:
- **Units.** `Phi` is dimensionless and is multiplied by `kappa` to enter `F`
  in **bits** (`+ kappa * outcome.phi`). r2 is a raw reward-vector component
  divided by `C2_SCALE = φ2 = 1.0`.
- **Coverage.** `phi_qos` charges only `satellite_change` and `beam_change`;
  `initial_entry`, `reentry` and a same-satellite cell rekey fall through both
  branches and are charged **nothing**. r2 charges re-entry after outage `φ2`
  deliberately (`action_contract.py:437-441`). **The two handover prices do not
  price the same events.**
- The engine branch `16e3d486:src/mcrl/physics_v025/targets.py:130-147` returns
  `bits - eta*joules` with **no Phi at all**; only the stage-C branch
  `d695e612` puts Phi inside `F`. Which of the two is the deployed engine was
  not resolvable from anything on HEAD.

### kappa

**v025 (`physics_v025`):** `kappa = B_ref / (U · N_ref)` — a formula, not a
literal, enforced at `16e3d486:src/mcrl/physics_v025/calibration.py:130-133`;
frozen value `6139555101440083/7500000 = 818 607 346.8586777` bit/user-step,
and `eta_ref = lambda = B_ref/E_ref = 19 720 681.0017` bit/J
(`calibration.py:128-129`, `assert_same_energy_price` at `:197-212`). Neither
derives from `Phi`; the dependency runs the other way — `Phi` is converted into
bits by multiplying by `kappa`.

**v023 working tree (`ee_axis_*`):**
`OPS3_KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")` =
**10 097 071 012.757404 bits**, at
`/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_ops3.py:67`
(re-declared bit-identically at `ee_axis_v07_c2_d2.py:72`,
`ee_axis_v06_c2_k1_learner_contract_v2.py:76`,
`ee_axis_v06_c2_k1_state_authority.py:54`).

The companion `OPS3_LAMBDA_BITS_PER_J = float.fromhex("0x1.443a8f481639ap+26")`
= **84 994 621.12635651 bits/J** (`ee_axis_ops3.py:66`) is the `eta_ref`-role
constant.

`ee_axis_ops3.py` imports from `..env.action_contract` **only `NUM_ACTIONS`**
(`ee_axis_ops3.py:46`), and from `..env.link_budget` the physics helpers
(`ee_axis_ops3.py:48-56`). It does **not** import `PHI1`, `PHI2`, or
`HANDOVER_COST`.

**Verdict:** `kappa` and r2's `φ` are **independently defined and
dimensionally different** — `kappa` is a service-loss normaliser in
*bits per user-step*, `φ1/φ2` are unitless preference weights in `[0, 1]`.
Neither derives from the other. There is no shared coefficient.

### r3 vs any occupancy term in the stage-C objective

Same grep: no stage-C module imports `r3_counting`, `user_beam_load`, or
`R3_CALIBRATION_SCALE`. The stage-C objective is built from
`env.link_budget`'s power helpers directly (`ee_axis_ops3.py:48-56`), and beam
occupancy enters that path only the way it enters the physics — through which
beams radiate and through `max`-per-beam power (see Q7).

### Would changing r2 or r3 change F, Phi, kappa, or a sealed stage-C label?

- **`kappa`, `lambda` / `eta_ref`:** no. Formula-derived from the frozen a-r0
  calibration rollout (v025) or independently declared hex constants (v023).
- **`Phi`:** no — **and that is the problem.** `PHI_SAME_SATELLITE = 0.5` /
  `PHI_SATELLITE_CHANGE = 1.0` are separate literals in
  `physics_v025/constants_v025.py:70-71` with their own provenance. Changing
  `PHI1`/`PHI2` changes r2 and leaves `F` alone; changing `Phi` changes `F` and
  leaves r2 alone. They agree today only because someone typed the same two
  numbers twice.
- **The stage-C objective / its labels:** no, *provided* the change is confined
  to the reward table. r2 and r3 are outputs of `_rewards`; the stage-C
  evaluators read `ActionEvaluation.resolution / energy / rate / system_power_w`,
  not `RewardComponents.r2_handover` / `.r3_load_balance`. And no stage-C
  module — v023 `ee_axis_*` or v025 `physics_v025`/`stagec_v025` — imports
  `PHI1`, `PHI2`, `HANDOVER_COST`, `r3_counting`, `user_beam_load`,
  `R3_CALIBRATION_SCALE`, or `reward_calibration`. The only `mcrl.env.action_contract`
  imports in either lane are `NO_OP_ACTION` / `NUM_ACTIONS` / `SlotTable` /
  `NUM_BEAM_SLOTS` / `NUM_SATELLITE_SLOTS`, i.e. action-space geometry.
- **What a change to r2 *would* touch:** `C2_SCALE = PHI2`
  (`reward_calibration.py:63`) → `REWARD_SCALES` → `trainer_spec` default
  (`trainer_spec.py:99-106`) → `run_fingerprint.reward_calibration_scales` and
  `trainer_config_sha256`. See Q6.

---

## Q5 — Is either reward defective on its own terms?

### Defect 1 (structural, r2 **and** r3) — an outage is the best possible value of both heads

For an unserved user:

- r3 = 0 (`service.py:167-171` — the zero row of `user_beam_load`), and every
  served user has r3 ≤ −1. **0 is the maximum of r3's range.**
- r2 = 0, because `classify_handover` returns `NONE` when `current` is
  `UNSERVED` (`action_contract.py:445-446`), and 0 is the maximum of r2's range.

So both bounded heads are *maximised* by going dark. This is documented, not
hidden — `src/mcrl/runtime/outage_gate.py:10-27` states it explicitly:

```
r1 ≈ 0   (no throughput, so no energy-efficiency credit)
r2  = 0   (§4A.4: an unserved step is no association change)
r3  = 0   (the user is on no beam, so U_{b_u} contributes nothing)
```

Two mitigations exist and both are partial:
1. re-entry is charged `φ2` on the step service resumes
   (`action_contract.py:433-441`) — a *deferred, discounted* cost;
2. the outage gate `outage_gate.py:120-141` raises if the dropped-transition
   rate exceeds `OUTAGE_RATE_NEGLIGIBLE_DEFAULT = 1e-3`
   (`outage_gate.py:39-47`), which is flagged **"S, PROPOSED — Not yet frozen"**.

Note the gate only covers *dropped* transitions (no-op actions,
`modqn.py:1260-1266`). A user whose chosen link fails the power-feasibility
test is **not** a no-op: that transition is pushed to replay with r2 = 0 and
r3 = 0, i.e. with the best attainable value of two of the three heads.

### Defect 2 (reporting, not computation) — the logged `scalar_reward` is uncalibrated and therefore degenerate

`modqn.py:1302` logs `scalarize_objectives(avg_reward, cfg.objective_weights)`
on the **raw** vector, while `modqn.py:1269` trains on the **calibrated** one.
At the frozen run's final episode
(`artifacts/training-2026-08-25-rerun01/main/episode-logs.json`, episode 8999):

```
r1_mean = 9635190.202980565   r1_mean_calibrated = 4.748180424186519
r2_mean = -2.48               r2_mean_calibrated = -2.48
r3_mean = -21.29              r3_mean_calibrated = -3.5483333333333333
scalar_reward = 4817590.099490282
```

`0.5·r1 + 0.3·r2 + 0.2·r3 = 4817595.10 − 5.00 = 4817590.10` — r2 and r3
together move the headline metric by 1 part in 10^6. The docstring at
`modqn.py:1303-1305` says both scalings are logged on purpose, so this is
disclosed; but the field named `scalar_reward` and the run-status field
`last_scalar_reward_raw` are, numerically, `0.5 × r1`.

### Defect 3 (unreachable branch — r1's power model, reported for completeness)

`pa_efficiency` (`link_budget.py:491-493`) is
`min(ξ_max, ξ_max·√(p/p_sat))`. Beam power is capped at
`BEAM_POWER_MAX_W = 1.65 W` by the feasibility test
(`link_budget.py:414-438`, applied at `step.py:812-820`), while
`PA_SATURATION_POWER_W = 1.65·10^0.5 = 5.218 W` (`link_budget.py:260-262`).
`√(1.65/5.218) = 0.562 < 1`, so **the `ξ_max` arm of the `min` can never be
selected on the live path**. This matters for Q7, not for r2/r3.

### Not defects

- **Signs.** r2 ≤ 0 (`step.py:1101`, negation of a non-negative table),
  r3 ≤ 0 (`service.py:277`, negation of a non-negative count). Correct.
- **Units.** r1 bit/J, r2 dimensionless, r3 whole users
  (`step_types.py:167-179`). Calibration divides each by a scale in its own
  units, so all three enter training dimensionless
  (`reward_calibration.py:42-79`).
- **Scale comparability.** At the frozen run's last episode the calibrated
  magnitudes are 4.748 / 2.48 / 3.548 and the `ω`-weighted contributions
  2.374 / 0.744 / 0.710 — within ~3.3× of one another. Not degenerate.
- **Unreachable r2 branch.** All three fire. `total_handovers = 278` and
  `r2_mean = −2.48` at episode 8999 over 100 users ⇒ `0.5·n₁ + 1.0·n₂ = 248`
  with `n₁ + n₂ = 278` ⇒ n₁ = 60 intra (`φ1`), n₂ = 218 inter (`φ2`).
  *(Inferred — arithmetic over the logged fields.)*

### Observed magnitude ranges (frozen run, all 9 000 episodes; per-user episode sums)

| head | min | max | final (episode 8999) |
|---|---|---|---|
| `r1_mean` | 4 813 127.10 | 11 204 100.07 | 9 635 190.20 |
| `r2_mean` | −7.93 | −1.46 | **−2.48** |
| `r3_mean` | −31.31 | −12.14 | **−21.29** ✔ matches the brief |

Source: `artifacts/training-2026-08-25-rerun01/main/episode-logs.json`
(9 000 rows), the run whose `status.json` carries
`checkpoint_sha256 = e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`
and `run_fingerprint.code_sha256 = 544fcf078f7e0d74c38e79288081c60357bc64b59540120dbe4e30bffe014ec4`.

---

## Q6 — Blast radius of changing r2 or r3 today

**Invalidated immediately**

1. **The frozen checkpoint as a comparator.**
   `artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt`
   (`checkpoint_sha256 = e6b063ef…1b09c28b`) was trained on these exact reward
   values under these exact calibration scales. A policy trained on a different
   r2 or r3 is not comparable to it on `scalar_reward`, on `r2_mean`/`r3_mean`,
   or on `total_handovers`.
2. **`run_fingerprint.code_sha256 = 544fcf07…`** — the hash-bound source tree.
   Editing `env/step.py`, `env/action_contract.py` or `env/service.py` breaks
   it, and with it every artefact that asserts the binding.
3. **`run_fingerprint.trainer_config_sha256 = b69f6f46add80619178a650026b5de2fae8402f2bb9f809995727ac580a2d654`**
   — changing `PHI2` changes `C2_SCALE` (`reward_calibration.py:63`), which
   changes `REWARD_SCALES`, which is a `trainer_spec` default
   (`trainer_spec.py:99-106`) and is recorded as
   `run_fingerprint.reward_calibration_scales`.
4. **`prereg_digest = 3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4`**
   — `runtime/prereg.py:526-539` freezes r2 as
   `f"identity-based handover, phi1={PHI1}, phi2={PHI2}"` and r3 as
   `"count-based -U_{b_u}"`, plus the load-semantics paragraph. Any change
   re-digests the PREREG.
5. **The frozen calibration scales themselves.** `c_3 = 6` closes
   pre-registered question **Q-D** and `c_1`/`c_2` close **Q-F**/**Q-G**
   (`reward_calibration.py:79-86`, `REWARD_SCALES_ARE_FROZEN = True` since
   2026-08-23). A new r3 with different units re-opens Q-D — this is exactly
   what happened at B13, and `runtime/trainer_config_validation.py:158-160`
   refuses calibration while the r3 scale is unfrozen.
6. **Declared gates that read the reward:** the §4A.5a(4) outage gate
   (`runtime/outage_gate.py:120-141`) reasons from "r2 = 0, r3 = 0 during an
   outage"; probe P3 / `runtime/probe_p3.py` (whose whole subject is `r3`'s
   discriminability and Q-D scale); `runtime/corrected_probes.py:426, 452`
   which re-checks the frozen `"Q-D r3 calibration scale"` mapping; and
   `scripts/analyze_corrected_postrun.py:601` which re-derives expected r2.

**Not invalidated**

7. **Stage-C C1/C2/C3 sealed labels and receipts.** No stage-C module imports
   r2's or r3's constants or functions (Q4). Stage-C reads physics — rate,
   power, service — through `ActionEvaluation`, and its own `lambda`/`kappa`
   are independent hex constants. A pure reward-table change leaves them
   bit-identical.
   **Caveat:** if the change touches `env/step.py`, `env/service.py` or
   `env/link_budget.py` as *files*, any stage-C artefact sealed by a per-file
   `code_sha256` (the R7 factory hashes 169 file-level bindings) breaks on the
   hash even though the numbers are unchanged. That is a sealing-mechanism
   consequence, not a scientific one.

---

## Q7 — Design premises

### r3 = −U_{b_u} — premise **FAILS**

**Premise under test:** spreading load across beams saves power and therefore
raises EE.

**Does adding a user to an already-active beam change system power at all?**
**No — by exactly zero, unless that user's own link needs more power than the
beam is already radiating.**

The whole of `P^N` is two terms
(`/home/u24/papers/mcrl-leo-handover/src/mcrl/env/link_budget.py:549-587`):

```python
return fixed_power_w(counts) + float(supply.sum())
```

- `fixed_power_w` (`link_budget.py:521-546`) reads only
  `radiating_beams_by_satellite`, a **count of radiating beams per satellite**:
  `P^f = Σ_s N^act_s · 0.338 W + 0.200 W · #{s : N^act_s > 0}`
  (`CIRCUIT_POWER_PER_BEAM_W = 0.338`, `link_budget.py:270`;
  `BASEBAND_POWER_PER_SATELLITE_W = 0.200`, `link_budget.py:273`).
  **No user count appears.**
- `supply_power_w` (`link_budget.py:496-518`) is `p_{s,v}/ξ_{s,v}`, one draw
  per beam. Its docstring is explicit: *"一支已啟用的波束以單一功率發射,不論
  其上載有幾位使用者"* — **one beam, one power, regardless of how many users
  it carries** (`link_budget.py:502-503`).
- The beam's radiated power is a **max**, not a sum
  (`beam_power_w`, `link_budget.py:439-466`):
  ```python
  out[beam] = max(out[beam], value)
  ```
  *"the aggregation is a max over served users, never a sum or a mean"*
  (`link_budget.py:444-447`).

So occupancy `U_b` enters `P^N` **nowhere**. Adding user *u* to a radiating
beam *b* changes system power by

  `ΔP = (√p_sat / ξ_max) · (√p_b^new − √p_b^old)`, and `ΔP = 0` whenever
  `p_u ≤ p_b^old`,

using `ξ = ξ_max√(p/p_sat)` unsaturated (Defect 3 above), i.e.
`P^p = √(p·p_sat)/ξ_max = 6.5265·√p` W with `p_sat = 5.218 W`,
`ξ_max = 0.35`. Since every link power lies in `[p⁰, p_max] = [0.825, 1.65] W`
(`SEGMENT_START_POWER_W = 0.825`, `link_budget.py:213`;
`BEAM_POWER_MAX_W = 1.65`, `link_budget.py:175`; feasibility test at
`link_budget.py:414-438`):

| event | ΔP^N |
|---|---|
| user joins an already-radiating beam, `p_u ≤ p_b` | **exactly 0 W** |
| user joins an already-radiating beam, worst case `p_b: 0.825 → 1.65` | `6.5265·(1.2845 − 0.9083)` = **+2.455 W** (upper bound) |
| user lights a **new** beam on an already-active satellite | `0.338 + 6.5265·√p` ≥ **+6.267 W** |
| user lights a new beam on a newly active satellite | ≥ **+6.467 W** |

*(The ΔP figures are inferred arithmetic over the verified constants and
formulas above.)*

**Consequence.** Reducing `Σ_b U_b²` — which is exactly what maximising
`Σ_u r3` does (`service.py:270-272`: `Σ_u U_{b_u} = Σ_b U_b²`) — is achieved
either (a) by moving a user between two already-radiating beams, which changes
power by 0 to ±2.455 W and is *usually exactly 0*, or (b) by lighting a new
beam, which **strictly increases** system power by at least 6.267 W. The
largest possible power *saving* from de-crowding a beam (2.455 W) is smaller
than the smallest possible power *cost* of the extra beam it requires
(6.267 W). **Spreading load never saves power in this model; it costs
power.**

And the numerator does not rescue it: `shannon_rate_bps`
(`link_budget.py:590-606`) is `R_u = (B^w / U_{s,v})·log₂(1+γ_u)`, so a beam's
*total* rate is `B^w · mean_u log₂(1+γ_u)` — **independent of `U` to first
order**. Bandwidth sharing cancels the head count in the numerator exactly as
the `max` cancels it in the denominator. Meanwhile every extra radiating beam
adds a co-channel interferer: `co_channel_interference`
(`src/mcrl/env/interference.py:349-364`) sums over the `radiating` set, so
`γ` falls as beams are added.

**The codebase already says this in one place.** `system_power_w`'s docstring
(`link_budget.py:562-566`) records that the *previous* per-link triple-sum
power form was removed **because** it made power rise with occupancy:

> "The extra term rises monotonically with occupancy and sits in `r1`'s
> **denominator**, so 'a busier beam is less efficient' — **which is `r3`'s
> job**."

That is, ruling F-2 deliberately removed the only occupancy→power channel in
the model and reassigned occupancy to r3 — without establishing that occupancy
has any remaining EE consequence. After F-2 it does not.

**Did any r3 variant move pooled EE in the direction r3 rewards?**
No r3 *reward* variant has ever been trained: `r3_counting` has had exactly one
form since 2026-08-22 (`service.py:264-277`), and every trained run in
`artifacts/` uses it. So the answer is "no variant was tested", not "a variant
was tested and failed". *(Verified by Q2's change history plus the absence of
any second `r3_*` reward function in `src/`.)*

**Verdict: r3's premise FAILS.** Occupancy has no term in the power model
(`link_budget.py:521-546, 496-518, 549-587`), the beam-power aggregation is a
max (`link_budget.py:439-466`), and moving in r3's direction beyond a
zero-power reshuffle requires lighting beams that strictly cost power.

### r2 — premise **FAILS** (handover costs zero joules)

**Premise under test:** a handover costs something.

**It costs nothing in the physics.** The handover class is computed at
`step.py:1084-1089`, *after* the entire physics dict is assembled
(`step.py:1030-1049`), and is consumed at exactly one place:
`r2_handover = -HANDOVER_COST[handover]` (`step.py:1101`). Neither
`system_power_w`'s fixed term nor its supply term reads the previous
association, the handover class, or any "did the user switch" flag
(`link_budget.py:521-546, 496-518, 549-587`). `grep -ci handover` returns **0**
for `env/link_budget.py`, `runtime/energy_efficiency.py`, `env/interference.py`,
`env/antenna.py` and `env/service.py`. There is no `handover_energy`,
`hoEnergy`, `switching_energy` or `signalling` symbol anywhere under
`src/mcrl/env/`.

**Handover energy is exactly zero. r2 is a pure preference term, not a
physical cost.**

**Worse: the one physical coupling has the opposite sign.** Link power follows
the segment recurrence `p(t) = p⁰·G^T(θ(τ))/G^T(θ(t))`
(`recurrence_power_w`, `link_budget.py:379-408`), and power only ever *rises*
inside a segment because the gain falls (`link_budget.py:216-220`). A handover
**breaks the segment**: at `step.py:825-862` a non-continuing segment sets
`start_gain = transmit_gain[uid]` (`step.py:800-803`), so
`p = p⁰·G/G = p⁰ = 0.825 W` — the floor — on the very next step. In supply
terms that is 5.928 W versus up to 8.383 W for an aged segment. **In this
simulator a handover *reduces* the link's energy draw.** *(Inferred from the
verified code above; no comment states it as a handover-energy claim. It is
the same mechanism recorded in the 2026-09-08 "segment-anchored power /
zero-energy handover" note.)*

**Sibling reference point (reference-only project, not evidence about this
model).** `/home/u24/papers/modqn-paper-reproduction/system-model-refs/simulator-parameter-spec.md:133`,
entry **E1**, `hoEnergyJoules` (`E_{u,HO}`): *"Per-handover-event energy cost,
J, **scenario parameter — no default**, HEA thesis sensitivity grid: 3, 30,
100, 130, 150, 200"*, source type `assumption`, mode "Sensitivity only";
listed at line 241 under "Parameters Reserved for Advanced / Sensitivity Mode
Only". Companion E2 `lambdaHo = 0.2` at line 134. So even the sibling treats
handover energy as an unsourced scenario assumption with no default — it does
not supply a number this project could adopt.

**A physically-grounded handover cost already exists — in the v025 successor
engine, and it is bits, not joules.**
`16e3d486:src/mcrl/physics_v025/constants_v025.py:68-69`:

```python
SAME_SATELLITE_INTERRUPTION_S = 0.062   # round-3 §2.16 conditional ADR-004 electronic handover proxy (VERIFY_SOURCE).
SATELLITE_CHANGE_INTERRUPTION_S = 0.142 # round-3 §2.16 conditional ADR-004 electronic handover proxy (VERIFY_SOURCE).
```

used at `16e3d486:src/mcrl/physics_v025/integration.py:79-88` to black out that
user's rate integral for the interruption window (`_blackouts`). So in the
successor engine a handover costs **lost service seconds → lost bits → lower
EE**, through the numerator, with no reward-side coefficient at all.
`initial_entry` and `reentry` are exempted (`integration.py:78-79`). Both
constants carry a `VERIFY_SOURCE` marker in their own provenance table
(`constants_v025.py:220-221`). None of this exists in the v023 environment that
the frozen checkpoint was trained in.

**Verdict: r2's premise FAILS** in the sense the question asks — in *this*
simulator a handover consumes zero joules and zero seconds, so r2 prices a
preference, not a cost. Whether that preference should be priced anyway
(service continuity, signalling load, paper eq. 3.27 fidelity) is a modelling
decision, not a physics fact.

### Quantities in this physics that *do* have a demonstrated causal link to `P^N`

Named, with the code that demonstrates each. **Not ranked, not recommended.**

1. **Number of radiating beams, `Σ_s N^act_s`.** Enters `P^f` linearly at
   0.338 W each (`link_budget.py:521-546`) *and* contributes one full PA
   supply draw of 5.93–8.38 W each (`link_budget.py:496-518`, `549-587`)
   *and* adds one co-channel interferer to every co-coloured victim
   (`interference.py:349-364`). This is the single largest controllable term in
   the denominator. Note it is the **opposite direction** to r3.
2. **Number of active satellites.** `P_BB = 0.200 W` charged once per satellite
   with any radiating beam (`link_budget.py:543-546`).
3. **Per-beam max link power, `p_{s,v} = max_u p_u`.** The only
   assignment-dependent term inside the PA draw
   (`link_budget.py:439-466`), entering as `6.5265·√p` — range 5.93 W at
   `p⁰ = 0.825` to 8.38 W at `p_max = 1.65`, i.e. a 2.455 W spread per beam
   that a scheduler can actually move by co-locating users with similar
   required power. Unlike occupancy, this *is* a load-shaping quantity with a
   real power derivative.
4. **Segment age / start-gain anchoring.** `p = p⁰·G^T(θ(τ))/G^T(θ(t))`
   (`link_budget.py:379-408`) means a link's power is determined by how far its
   pointing gain has decayed since the segment began. Resetting a segment
   returns it to `p⁰`. This is a demonstrated power lever — and it is the
   mechanism by which handovers currently *lower* power, so pricing it is the
   same modelling decision as r2's.
5. **Spectral efficiency per beam, `mean_u log₂(1+γ_u)`.** The numerator side:
   `R_u = (B^w/U)·log₂(1+γ_u)` (`link_budget.py:590-606`), so a beam's total
   rate is `B^w` times the mean SE of its users. Raising mean SE (better
   pointing, lower co-channel collision) raises EE with no denominator cost.
6. **Handover interruption time — only if the v025 channel is adopted.**
   `SAME_SATELLITE_INTERRUPTION_S = 0.062` / `SATELLITE_CHANGE_INTERRUPTION_S = 0.142`
   (`16e3d486:src/mcrl/physics_v025/constants_v025.py:68-69`) with the blackout
   integral at `integration.py:79-88`. This is the one candidate that would give
   r2 a physical basis, it is already implemented in the successor engine, and
   both constants are marked `VERIFY_SOURCE` — i.e. unsourced today.

---

## Verified vs inferred — index

**Verified (read this session).** Every file:line in Q1, Q4, Q5, Q6 and Q7;
all commit hashes, dates and messages in Q2 (via `git log`/`git show`); the
`episode-logs.json` and `status.json` field values; the zero-hit greps for
stage-C imports of reward constants.

**Inferred (reasoning/arithmetic over the above).**
- The `ΔP^N` table in Q7 (arithmetic over `6.5265·√p`, the constants, and the
  feasibility bound).
- "The `ξ_max` arm of `pa_efficiency`'s `min` is unreachable" (from
  `p ≤ 1.65 < 5.218 = p_sat`).
- The 60 intra / 218 inter handover split at episode 8999.
- "A handover resets the link to `p⁰` and therefore lowers its power" (from
  `step.py:800-803` + `link_budget.py:379-408, 216-220`).
- "Beam total rate is independent of `U` to first order" (algebra on
  `link_budget.py:596`).
- The classification of `14174d60`'s `commit=False` branch as
  stage-C-motivated (from its exclusively stage-C caller list).

**Verified via `git show` of non-HEAD branches** (`physics_v025` is not checked
out on `wip/multi-catfish-v023-20260907`): `network_objective`
(`d695e612:src/mcrl/physics_v025/targets.py:129-150`), its import list
(`:11-20`), `PHI_SAME_SATELLITE` / `PHI_SATELLITE_CHANGE` /
`SAME_SATELLITE_INTERRUPTION_S` / `SATELLITE_CHANGE_INTERRUPTION_S`
(`16e3d486:src/mcrl/physics_v025/constants_v025.py:68-71`), and `_blackouts`
(`16e3d486:src/mcrl/physics_v025/integration.py:69-98`).

**Relayed, not personally read** (from a delegated read-only search; treat as
second-hand until re-checked): the frozen numeric values
`kappa = 6139555101440083/7500000` and
`eta_ref = 491164408115206640000000/24906057152504541`, quoted in
`.scratch/server-sync-20260909/sealed/V025-ENGINE-STAGE4H-REPORT-2026-09-09.md:80`;
the sealed manifest itself lives on the server and is not in this checkout.

**Open / unresolved.**
- **Which v025 branch is the deployed engine.** `d695e612` puts `Phi` inside
  `F`; `16e3d486` returns `bits − eta·joules` with no `Phi`. Nothing on HEAD
  resolves it. If the Phi-free variant is what runs, then `Phi` is not in the
  deployed objective at all and the r2-vs-`F` coupling question is moot.
- **The duplicated 0.5 / 1.0.** `PHI1`/`PHI2` and
  `PHI_SAME_SATELLITE`/`PHI_SATELLITE_CHANGE` are two independent literals that
  happen to agree. Nothing in the tree asserts they must.
- The C3 oracle-marginal probe that would give a *measured* EE response to
  moving in r3's direction exists only as a runner in
  `.scratch/multi-catfish-v023-c3-probe-oracle-marginals/` — its outputs were
  written on the server
  (`/home/sat/mcrl-v023-c3-probe-marginals-20260908-r1`) and are not in this
  checkout, so I did not verify them. The Q7 verdict above does not rest on
  them.
