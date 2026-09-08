# V0.25 `LegacyWorldProvider` pre-audit — fresh-context, read-only (Claude Opus, 2026-09-08)

Scope: the traps in bridging the legacy LEO handover geometry to the V0.25 primitive engine, plus a
review of the provider code that exists. Nothing on `sat` was modified; no simulation was run.

**Snapshot audited** (the codex `gpt-5.6-sol` session was *still running* throughout; the file moved
three times under me — 489 → 578 → 602 lines):

| item | value |
|---|---|
| `src/mcrl/physics_v025/provider_legacy.py` | 602 lines, 24 109 B, mtime 2026-09-08 16:54:19 UTC, sha256 `2ae94c7bbf42a350693ada2eb838b640226c0f53040417aed7885b66cea7b067` |
| `tests/physics_v025/test_provider_legacy.py` | sha256 `3546fb35f419c6f82c9707c604a5b9fb067f903ae70fa1f2c3e93e1ee9619494` |
| `V025-PROVIDER-REPORT-2026-09-08.md` | **absent** |
| git | both files **untracked**; no commit |
| KAT run | **not observed**; no pytest evidence exists yet |

All line numbers below are against that snapshot and will drift. Legacy paths are relative to
`/home/sat/mcrl-v025-codex-ws-provider/`.

---

## A. Ranked traps

### T1 — Interference boresight: the aggressor must point at *its own* served cell (VERIFIED)
Legacy `interference.py:214-218` computes `G^T` from `beam_off_axis_deg(user, aggressor_sat,
radiating.cell_centre_ecef_km)` where the centre is the **aggressor's own** served cell
(`interference.py:149`, fed from `step.py:892-894`). Docstring `interference.py:16-19` is explicit.
Pointing every aggressor at the *victim's* cell makes its off-axis angle ≈ 0 and radiates peak
`G^T = 2000` at the victim unconditionally: **+7 to +10 dB at one cell of separation, +32 to +35 dB
at two** (measured, pitch 24.24 km, `THETA_3DB_DEG = 3.32`). It also deletes the aggressor's pointing
from the model — precisely the channel through which a set-level scheduler could reduce interference,
i.e. the C3 research question is defined away.

### T2 — Scintillation ownership is split between the two stacks (VERIFIED)
Legacy `total_path_loss_db` = `L_f + L_g + L_c + L_s` **includes scintillation** (`link_budget.py:357`);
`L_s` (shadow) is caller-supplied and defaults to 0 (`link_budget.py:348-352`). The V0.25
`keyed_fading_gain` returns `rician · 10^(−(shadow_db + scintillation_loss_db)/10)`
(`channel.py:242-244`) — it **also** carries scintillation. Composing legacy `link_power_factor`
with v025 `keyed_fading_gain` applies `L_c` twice: 1.08 → 2.16 dB at 10°, 0.48 → 0.96 dB at 20°
(table `constants_v025`/`link_budget` identical). Elevation-dependent, so it biases handover choice,
not just level. The engine's own reference (`tapes.py:496-503`) treats `nominal` as scintillation-free.

### T3 — "Beam-chain" enumeration and inventory cardinality (VERIFIED)
`(NORAD, cell_id)` **is** the legacy beam identity (`interference.py:57-101`, `service.py:132-148`,
`step_types.py:204-211`), so that choice is faithful. But there is **no per-satellite beam or RF-chain
count anywhere in `env/`, by explicit ruling** — `link_budget.py:276-284`
(`BEAM_TO_RF_CHAIN_IS_SOURCED = False`, "must never be used to argue a beam-count or per-satellite
chain-count ceiling") and `action_contract.py:64-66`. The legacy never materialises a satellite × cell
product: `RadiatingBeams` holds only beams that actually radiate, length varying per step.
A frozen cross product is a new construct, and it is load-bearing downstream: `energy.interval_energy`
charges `idle_power_w · duration` for **every** inventory chain with zero RF
(`energy.py:112-118`). With `PRIMARY_IDLE_POWER_W = 0.0` the primary settings are spared, but the
standby-sensitivity setting (`standby == "f"`, `SENSITIVITY_IDLE_POWER_W = 0.6986 W`,
`adapter.py:142`) is one of the 31 — a 51 282-chain inventory puts **≈ 1 078 kJ/step** of fictitious
standby into the EE denominator and reduces that arm to noise.

### T4 — `slot_occupied` / `cell_reachable` are tautologically true once you filter on `cell_id ≥ 0` (VERIFIED)
`SlotTable.cell_ids[a] ≥ 0` ⟺ `mask[a]` ⟺ `occupied[l] ∧ cell_exists[j] ∧ reachable[l,j]`
(`action_contract.py:333, 351-368`). So any provider that emits only rows with `cell ≥ 0` gets
`occupied = reachable = True` on 100 % of rows (verified over 30 steps: 0 exceptions), and a
D2-**in**eligible slot is *silently dropped* rather than emitted with `d2_eligible = False`. The
legacy D2 signal never reaches the primitive. Read `d2` / `D2Snapshot.eligible` (`candidates.py:100`,
`d2.py:215-227`) or `slot_occupied` **before** the mask filter.

### T5 — Sub-boundary window direction and the prime seam (VERIFIED)
Legacy: 47 samples spanning **46** sub-intervals = 29.44 s, running **backward** and *ending* at the
decision instant (`scenario.py:318-323, 343-350`, comment "The sub-steps END at the decision point").
V0.25: **48** samples / 47 sub-intervals = 30.08 s running **forward** from it (`tapes.py:199`,
`integration.py:175-176`). Same numeral 47, opposite meaning and opposite direction. Consequence: a
forward-propagated D2 latch for step *k* covers roughly the legacy's step *k+1* measurement block, so
it is never the legacy's own step-*k* sequence. Separately, `scenario.py:184-205` primes the tracker
at *t*−1.28/−0.64 s using indices −2/−1 while step 0's own block already covers *t*−29.44…*t* at
indices 0…46: index advances +1 while time jumps **backward 28.80 s**, and TTT credit carries across
the seam (measured: `ttt_elapsed = 2` already banked at substep 0 of decision 0).

### T6 — `steps_per_episode` silently changes the world (VERIFIED)
`ScenarioDriver.reset` feeds `duration_s = steps_per_episode · 30.08` into `shortlist_visible`
(`scenario.py:161-168`), so the tracked universe — and therefore every candidate table, mask and
digest — depends on it. `ScenarioConfig` defaults to **10**; C3-S hard-rejects anything but **30**
(`run_v023_c3s_screen.py:610-611`). Any KAT or manifest path that builds the provider with
`steps=1` or `steps=3` is describing a *different world* from the one the units will run.

### T7 — Intra-satellite co-colour interference is unrepresentable in a NORAD-keyed cross map (VERIFIED)
Legacy eq. (3.12a) sums same-satellite, different-cell, same-colour beams and gives them **peak**
receive gain via the P-10 override (`interference.py:390, 314-316`; `antenna.py:224-260`) — the
single strongest interference term. `PrimitiveCandidate.*_cross_gain_by_norad` is keyed by NORAD
only (`tapes.py:118-120`) and `_masked_coupling` reads `cross[victim, aggressor]` by NORAD
(`architectures.py:305-315`), so a same-satellite aggressor resolves to `.get(...) → 0.0`. Also, one
satellite serving two different cells collapses to one scalar; the legacy computes a distinct `G^T`
per beam. This is a genuine `CONTROLLER_DECIDE`, not a code slip — but it must be *declared*, not
absorbed.

### T8 — The 10° floor is a V0.25 invention; the legacy screens at 0° (VERIFIED)
`SCREEN_MIN_ELEVATION_DEG = 0.0` (`scenario.py:61`, minus a further 5° margin in
`ephemeris.py:629,649`) and `CELL_VISIBILITY_MIN_ELEVATION_DEG = 0.0` (`candidates.py:51`).
`EphemerisConfig.min_elevation_deg = 10.0` (`ephemeris.py:667`) is **dead** — its only consumer is
`as_dict()`. So legacy legality is D2's call alone; `visible ⇔ elev ≥ 10` is a new constraint, and
`PrimitiveCandidate.__post_init__` (`tapes.py:125`) enforces it as an invariant.

### T9 — `require_all_healthy=False` returns NaN *and* finite garbage (VERIFIED)
Measured on sgp4 2.27: error codes 1-4 → `NaN`; **code 6 ("decayed") → a finite sub-surface position**
(|r| ≈ 4635 km, i.e. altitude ≈ −1736 km). NaN slant trips
`PrimitiveCandidate.__post_init__`'s finiteness check and crashes; code 6 does **not** and yields a
nonsense `d2_entry_elevation_deg`. Neither case is filtered by the provider.

### T10 — Units and apexes (VERIFIED)
`angle_between_deg(vertex, first, second)` takes the **vertex first**, positionally, and the same
signature serves a satellite-apex consumer (`pointing.py:62-73`, transmit off-axis) and a user-apex
consumer (`interference.py:270-274`, S.465 separation) — a transposition is silent.
`link_power_factor(slant_km, elevation_deg, receive_gain_linear)`: km in (×1000 internally at
`link_budget.py:326`), degrees, **linear** receive gain, **linear** power factor out, transmit gain
*excluded*. FSPL is the λ/4πd form at 20.0 GHz (`link_budget.py:18, 320-326`); no 92.45 constant.

### T11 — Legacy and V0.25 transmit gain are not bit-identical (VERIFIED)
The `|μ| ≤ 34` ascending Bessel series lives in `runtime/bessel.py:47, 101, 150-152, 177, 197`;
`physics_v025/channel.py:109-113` switches to Miller recursion from `|μ| ≥ 20`. Agreement is exact
outside `μ ∈ [20, 34]`, up to **0.5 %** inside it (θ ≈ 27°). Wanted-link off-axis angles stay ≲ 6°
(μ ≲ 8) so it should not fire, but a `rel=1e-9` parity assertion is fragile by construction.
Related, non-blocking: legacy `RX_ENVELOPE_MIN_DEG = 2.4983°` (`antenna.py:172-175`) applies the
`D/λ ≥ 50` S.465-6 branch to a terminal with `D/λ = 40.03`; the correct value is **2.0433°**
(`constants_v025.py:82`). Neither implementation actually holds the gain at `G_R,max` below θ_min —
measured max |Δ| between the two receive patterns over [0°, 180°] is **0.0 dB**, so the "corrected
branch" in `channel.py:141-145` is algebraically inert. The wrong constant does leak into
`runtime/prereg.py:428` and `runtime/probe_p5.py`.

### T12 — TRAIN/TEST split, seeds, and a self-check that cannot fail (VERIFIED)
`BlockAlternatingSplit`: `block_days=7`, `embargo_days=1`, cycle 16, phase anchored on the archive's
**first file date** (`ephemeris.py:230-266`). On the 373-file corpus (2025-07-27 … 2026-08-20):
**166 TRAIN / 160 TEST / 47 EMBARGO**, min gap 2 days. Assert with
`split.part_for(d) == ephemeris.TRAIN` (`TRAIN == "train"`). `EpisodeStartSampler.draw` consumes
exactly two `rng.integers` calls and returns date **plus** an intra-day offset snapped to 30.08 s
(`ephemeris.py:421-427`) — a provider that compares only the *date* will not notice a wrong offset.
`_evaluation_rngs(seed) = SeedSequence(seed).spawn(4)` returns **fresh, unconsumed** streams on every
call (`training_pipeline.py:868-872`); child 0 = epoch/env, child 1 = mobility. Therefore drawing
twice from two fresh child-0 streams *must* agree — a "replay drifted" guard built that way can never
fire. World seed = `sha256(ascii domain)[:8] & (2^63−1)`; the V0.25 domains are `V025_PROBE/world/n`,
**not** the C3-S `C3S_SCREEN/world/n`, so the recipe is reproduced, not the C3-S worlds themselves.

### T13 — Users move; the layout and the forward horizon do not (VERIFIED)
`RandomWanderingUsers.step` advances 0.2507 km per decision with a ±π/4 turn (`mobility.py:117-135`)
— ~7.5 km of path over 30 steps. A layout taken from step 0 is not the layout at step 29. A
remaining-visibility integral that freezes the user for 900-1800 s carries the same error.

### T14 — TLE selection rule, and tape scale (VERIFIED)
`select_elements` (`ephemeris.py:97-159`): **nearest epoch per NORAD** over `date−1/date/date+1`
(`epoch_search_days = 1`), absolute age ≤ `MAX_TLE_AGE_H = 24.0`; stale NORADs are **silently
dropped** per-satellite and only an all-stale set raises. Selected **once** in `reset`, never
re-selected (`scenario.py:154-173`). Scale: 100 users × 28 slot entries × 48 boundaries = **134 400
candidate rows per step**; at 30 steps that is **4.03 M** `PrimitiveCandidate` objects and a
`tape_digest` JSON of order 1.6 GB.

---

## B. Parity KATs that would actually bite

| # | KAT | Oracle |
|---|---|---|
| K1 | Interference parity against `interference.py` | Build one legacy served configuration, call `build_radiating_beams` + the legacy interference sum, and compare the tape's per-victim aggregate. This is the **only** test that catches T1, T3-collapse and T7. Non-negotiable. |
| K2 | Aggressor-pointing discriminator | For a victim and an aggressor serving a cell ≥ 2 pitches away, assert the cross gain is ≥ 25 dB **below** the same aggressor's on-boresight gain. Passes only if the aggressor points at its own cell. |
| K3 | Co-colour zero | Assert cross gain is **exactly 0.0** for an aggressor beam whose `grid.colors[cell]` differs from the victim's. |
| K4 | Fade-ratio identity | `realised/nominal == rician · 10^(−shadow/10)` for a known key — recompute the two components directly. Catches T2; a `realised == nominal * keyed_fading_gain(...)` assertion cannot. |
| K5 | Direct sgp4 at k > 0 | Independent `Satrec` propagation at `t + k·0.640` for k = 17, 47, ≤ 1 m. Genuine — the tape's positions come from a separate `step_times` grid. |
| K6 | Hand-computed FSPL | One geometry, `(λ/4πd)²` with λ = c/20 GHz computed in the test, ≤ 1e-12 rel. Genuine absolute anchor. |
| K7 | S.465 anchors | `receive_gain_dbi(1°, 2.0433°, 5°) = 32.0, 24.2417, 14.5258` dBi; `transmit_gain_linear(0°) = 2000`, `(1.66°) ≈ 1000`. Already covered by `test_channel_legacy.py:32-46`. |
| K8 | D2 non-vacuity | Assert the boundary carries **at least one** row with `d2_eligible = False`. Catches T4 directly. |
| K9 | Inventory cardinality bound | Assert `len(inventory) ≤ c ·` (identities realisable by any user at any boundary). Catches T3. |
| K10 | Determinism across **processes** | Two separate interpreter invocations must print the same `digest`. An in-process repeat is defeated by any module- or class-level cache. |
| K11 | Epoch identity | Assert the full `start_utc` (not just the date) equals an independently drawn `EpisodeStartSampler` value, and that `part_for(date) == TRAIN`. |
| K12 | Unhealthy-satellite handling | Force an sgp4 code-6 NORAD into the tracked set and assert it is excluded rather than emitted with a −1736 km altitude. |
| K13 | TEST-date rejection | Construct on `split.available_dates(archive, TEST)[0]`; expect a raise before any file load. Genuine (already present). |

**Tautological — do not count these as evidence.**
(a) `realised == nominal * keyed_fading_gain(...)` — restates the implementation.
(b) `nominal == transmit_gain_linear(θ) * link_power_factor(...)` where θ is taken from the same
legacy array the provider used — restates the implementation (the *elevation/slant* half of the same
test is genuine, because those come from an independent propagation grid).
(c) `d2_eligible == slot_occupied[user, norad, cell]` filtered by `cell ≥ 0` — both sides are
identically `True` (T4). Currently `True == True` on 100 % of rows.
(d) `cross_gain ≤ aggressor_direct_gain` — guaranteed by construction whenever the cross term reuses
the direct term's transmit gain and `rx(sep) ≤ rx_peak`.
(e) "Symmetric construction for two users on the same cell" implemented by selecting the pair whose
NORAD tuples are already equal and then asserting they are equal.
(f) `inventory ⊇ {legal identities}` when the inventory is the cross product of the same
visible-satellite scan and the same cell set the candidates are drawn from.
(g) An in-process re-draw of `EpisodeStartSampler.draw` on a second fresh `_evaluation_rngs(seed)`
child-0 stream (T12).
(h) `absolute_time_s == step·DECISION_INTERVAL_S + k·D2_MEASUREMENT_STEP_S` when the caller computed
the argument with that identical expression.

---

## C. Defects in the code as it stands

`P:` = `src/mcrl/physics_v025/provider_legacy.py` @ sha256 `2ae94c7b…`; `T:` = its KAT file.

| # | sev | defect |
|---|---|---|
| D1 | **blocker** | Aggressor pointed at the **victim's** cell centre: `P:429-436` (`cross_angles` vertex = aggressor, first = `centres[:, None, :]` = victim's cell). Legacy points it at its own (T1). +7…+35 dB. |
| D2 | **blocker** | Scintillation double-counted: legacy `link_power_factor` imported at `P:42`, used at `P:418, 445`, then multiplied by v025 `keyed_fading_gain` at `P:512` and in the cross rows (T2). |
| D3 | **blocker** | Cross gains computed over **all** `candidate_norads` with no colour filter (`P:427-457`); the legacy mask is `co_colour & …` (`interference.py:387-392`). Downstream `_masked_coupling` re-applies colour, so the error is silent rather than fatal — but the precomputation is not the legacy quantity. |
| D4 | **blocker** | Inventory is the full cross product `sorted(visible_satellites) × chains`, `P:272-284`. Measured on the canonical 30-step world: **693 × 74 = 51 282** pairs vs **2 760** realisable (18.6×). Drives the standby-sensitivity EE denominator (T3) and a 74 M-op energy loop per arm-world. |
| D5 | **blocker** | Class-level `_STATE_CACHE` / `_BOUNDARY_CACHES` (`P:125-128`, populated `P:309-310`, read `P:184-189`) are process-global and never evicted. Two consequences: (i) unbounded retention of ~4 M `PrimitiveCandidate` objects plus the `(S, 2818, 3)` position array per world → OOM across the 4 probe worlds; (ii) it **invalidates the determinism KAT** — `T:221-235` builds two providers with the same key, so the second returns the *same object*; `gc.collect()` cannot help against a class attribute. Determinism must be proven across processes (K10). |
| D6 | high | `d2_eligible` at boundary 0 is unconditionally `True`: the identity filter `if int(norad) >= 0 and int(cell) >= 0` (`P:384`) selects exactly the mask-true set, so `occupied0`/`reachable0` are always `True` (T4). The KAT at `T:139-140` therefore asserts `True == True`. |
| D7 | high | `d2_distance_km` is set to the slant range — `P:507-508` passes `slant, slant`. The protocol keeps the two fields distinct (`tapes.py:112-113`; the reference provider gives them different values, `tapes.py:534-536`). Whether they coincide under the legacy candidate-side-only D2 is a declaration the report must make explicitly. |
| D8 | high | `_d2_at` omits the `min_altitude_km ≥ 300` floor that `D2Tracker.update` applies (`d2.py:374, 392`), and hard-codes the TTT as the literal `2` at `P:589` instead of `D2_TTT_S / D2_MEASUREMENT_STEP_S`. |
| D9 | med | `_remaining` (`P:527-557`): the forward horizon is the remainder of the propagated array (`P:535`), so it **shrinks from 1802.88 s at step 0 to 900.48 s at step 29**; a never-failing mask returns `(len−1)·0.640` — right-censoring indistinguishable from a real expiry. Pooling `remaining_*` across steps mixes censoring regimes. The user is held stationary over the whole horizon (T13). |
| D10 | med | `user_layout` is derived from `decisions[0].user_xy_km` only (`P:293-301`); users move ~250 m/step (T13), so the published layout describes step 0 alone. |
| D11 | med | The "legacy TRAIN epoch replay drifted" guard (`P:196-203`) is a tautology — both draws use fresh `_evaluation_rngs(seed)` child-0 streams (T12). It cannot detect a wrong archive, split, or child index. |
| D12 | med | The boundary-time contract at `P:354-356` re-derives `expected` from `step_index`/`boundary_index` and ignores `build_world_tape`'s `start_time_s` (`tapes.py:433-437`). It happens to pass only because every call site uses `start_time_s=0.0`; a non-zero start raises. Also assertion-tautological (B(h)). |
| D13 | med | No handling of `require_all_healthy=False` outcomes at `P:255` — NaN rows crash `PrimitiveCandidate.__post_init__`, and sgp4 code-6 rows pass the finiteness check with a −1736 km altitude feeding `elevation_for_slant_range` (T9). |
| D14 | low | `100` and `7` are hard-coded (`P:215, 226-236, 371, 294-301`) instead of `MobilityConfig.num_users` / `NUM_BEAM_SLOTS`. |
| D15 | low | The module docstring and the `chains` identifier (`P:5, 272`) use "RF chain" vocabulary that `link_budget.py:276-284` and `action_contract.py:64-66` explicitly forbid. The `(NORAD, cell_id)` *identity* is faithful; only the name is invented. |
| D16 | low | `T:41-53` builds the oracle **and** the provider with `steps=3`, and `T:221-243` with `steps=1` — neither is the canonical 30-step world (T6). Parity is demonstrated on a world the units will not run. |

**Correct, and worth keeping:** the hysteresis sign at `P:495-497`
(`elevation_for_slant_range(D2_THRESHOLD_KM − D2_HYSTERESIS_KM, alt)` reproduces
19.6865 / 23.3959 / 27.6465° at 426/485/550 km, matching `d2.py:158-160`); the `(NORAD, cell_id)`
identity; the vertex-first `angle_between_deg` usage for both the transmit off-axis and the receive
separation; peak receive gain for the wanted link (matching `step.py:120, 956`); `time_step_s=
DECISION_INTERVAL_S` on the sampler; the TEST-date rejection before any file load; and the
D2-release-condition mask (1150 km) used for `remaining_d2_s`.

---

VERDICT: PROVIDER_STATE=PARTIAL | TRAPS=14 | DEFECTS_FOUND=16 | BLOCKERS=D1 aggressor-boresight (+7…+35 dB, deletes the C3 lever); D2 scintillation double-count (0.5–1.1 dB, elevation-dependent); D3 no co-colour filter in the cross precomputation; D4 51 282-pair cross-product inventory vs 2 760 realisable (breaks standby-sensitivity EE); D5 process-global world/boundary caches (OOM + determinism KAT invalidated); plus PROCESS: report absent, files untracked, KATs never observed to pass, codex session still writing
