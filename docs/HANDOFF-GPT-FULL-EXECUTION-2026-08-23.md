# GPT full handoff execution record (2026-08-23)

This record distinguishes deterministic closure from permission to start an
empirical run.  It is the execution companion to the controller handoff; it
does not replace the frozen pre-registration artifact or a controller ruling.

## 2026-08-24 post-run completion addendum

The Ubuntu pipeline completed at 2026-08-24 17:35:21 Asia/Taipei after
15 h 47 min 23 s. All three finite P6 arms completed 9,000 episodes and ten
shared final-policy evaluations. The frozen selector chose `alpha=0.001`
(mean calibrated scalar reward `0.503674`, versus `0.353003` for `0.003` and
`-0.995032` for `0.01`), and the independent main run completed 9,000/9,000
episodes with the declared seed triplet. Fresh server guards pass; all four
episode logs and all four final checkpoints match their recorded SHA-256.

The controller-format analysis is
`docs/POST-RUN-VALIDATION-2026-08-24.md`. Its bounded B17 result is that the
selected/main policy does not reproduce `alpha=0.01`'s near-single-beam
catastrophic collapse, but retains substantial concentration. No frozen
numeric collapse cutoff exists, so the report does not manufacture one after
seeing the data. This closes the run and controller evidence request; it does
not itself authorize Chapter 5 edits or a catfish contribution claim.

## 2026-08-24 closure addendum — current authority

This addendum supersedes every `pending` or `unresolved` execution statement
below; those sections remain as an audit trail of what was blocked before the
controller said `直接按照你的建議進`.

- Phase A was transferred to the shared `pptx-craft` checkout, all seven
  formal deck pipelines and twin checks passed, the seven review exports were
  byte-verified, and the exact-path commit is `a332f0e` (no push).
- Phase E was merged into the shared thesis checkout.  The formal build reports
  `DOCX STRUCTURE PARITY -> PASS`, `COHERENCE -> PASS`, and source-set digest
  `f840ff44fd7ae8de72b8e72c25fa8838b631188007147a9a6eb953f914b8c7ad`.
  An independent semantic scan of the exact 18 authorized sources found no
  active 125-state, 2.05-degree, or `m^e` residue; layout-number matches were
  classified separately.
- B6 now freezes the four NORAD slot identities at dwell boundaries while
  refreshing live D2/geometry state and masking any temporarily ineligible
  cached row.  Re-entry, all-four-invalid no-op, and missed-boundary guards
  have behavior tests.
- P6 is executable and predeclared: three matched 9000-episode arms, ten shared
  train-split final-policy evaluation seeds, mean calibrated scalar reward as
  the sole primary selector, declared sweep order for exact ties, and
  diagnostic-only near-tie/perturbation/cross-seed statistics.
- The server path now fails closed on live TLE/SGP4, frozen seed, reward-scale,
  source-byte, dependency, and TrainerConfig drift.  A nominally complete arm
  is reusable only with matching hashed checkpoint/log/evaluation artifacts.
  Atomic 100-episode resume checkpoints carry networks, optimizers, replay,
  all trainer RNGs, the persistent segment-age RNG, and contiguous logs; the
  resumed trajectory has an interrupted-vs-uninterrupted equality test.
- The post-reliability local suite is `792 passed, 1 skipped` in 514.60 s.
  The independent live launcher validation rebuilt the 373-file ephemeris
  contract and passed with corrected digest `01b0d85c...c022`.
- Historical server launch receipt: the synchronized Ubuntu checkout passed
  `792 passed, 1 skipped` in 191.50 s and the same live digest/TLE guard.
  tmux `mcrl-p6-main-20260824` entered `phase=P6/status=running` at
  2026-08-24 01:48 Asia/Taipei; the first declared `alpha=0.01` arm began
  with fingerprint `59505af5...c2925`. This historical line is launch evidence
  only, not a
  P6 result, selected learning rate, main-run result, or Chapter 5 authority.
- The server's live TLE directory had advanced to 375 files by adding
  2026-08-21/22.  Nothing was deleted: this run consumes an exact 373-file
  hard-link view at `/home/sat/mcrl-runtime/tle-frozen-20260820`.  The
  host-specific root path is normalized only for source-digest portability;
  per-file hashes/dates, the aggregate hash, split/sampling, and SGP4 remain
  exact live gates.
- `artifacts/PREREG-FROZEN-2026-08-24.json` is canonical with self-digest
  `01b0d85cedbd67f80a24c2adf7ff4181c728070111d06334e8dc55f07f52c022`.
  The 2026-08-23 artifact remains byte-preserved and independently verifiable.
- Q-C and G-5 remain authority/coverage gaps, not fabricated runtime gates.
  The active gate sets remain Q-D/E/F/G and G-1–G-4/G-6–G-12.

The controller record for these choices is
`docs/CONTROLLER-RULINGS-GPT-CLOSURE-2026-08-24.md`.

## Historical pre-closure gate state

- `artifacts/PREREG-FROZEN-2026-08-23.json` verifies with record digest
  `d35ddaffda580c8c109f758372956d41aa947b9eb3915d742f3f5f9b7aaecf08`.
- `assert_ready_to_train()` passes for Q-D/Q-E/Q-F/Q-G.  This is a
  selection-mapping gate, not proof that the full P6 protocol is operational.
- The post-edit full suite passed: 755 passed, 1 skipped in 362.51 s.
- The frozen artifact has not been edited.
- Digest validity is not semantic consistency: the sealed artifact has
  `dwell.steps = 4` and Q-E `resolved = 4`, but its P2 note still says Q-E was
  closed at `N = 3` (JSON lines 114, 2874 and 3094).  Runtime selection is
  unambiguous, but the sealed record is internally contradictory.

## Phase B: eight-axis audit

| Axis | Verdict | Evidence boundary |
|---|---|---|
| Frozen artifact vs code | Executable values match; the sealed P2 note contradicts its own N=4 fields; P6 is declared but has no runner | Live constants match the resolved mappings; `probe_grid.P6` still carries unimplemented obligations. Digest verification alone did not catch the narrative contradiction. |
| Q-A through Q-G | Q-D/E/F/G closed; Q-C has no current owner in the permitted authority set | `assert_ready_to_train()` intentionally checks D/E/F/G only. |
| Controller rulings | Mostly implemented | C-13 still relies on callers to pass learning rate explicitly; no training CLI currently enforces that obligation. |
| G-1 through G-12 | G-1–G-4 and G-6–G-12 have behavioral tests; no current G-5 definition/test was found | This is an acceptance-coverage gap, not evidence that a known runtime behavior is wrong. |
| Forbidden list and `m^e` | Verified | Live path uses two-gate `x = a*z`; auction, capacity penalty, `v_max`/`k_cap`, default chi/z-score, shared scalar action and catfish are forbidden. |
| Deviation register | Substantive deviations recorded; P6 operational gap and B6 cadence risk were not represented | Do not convert an implementation gap into a scientific deviation. |
| B1 through B17 | B4 is implemented; B6 timing conflicts with the decision record | B17 has candidate-level diagnostics only, not a trained-policy conclusion. |
| Contribution line | Open by design | A non-collapsed baseline is a valid go/no-go result and must not be tuned away. |

The handoff says there are 22 `CONTROLLER-RULINGS-*` files; the current
checkout contains 15.  The audit used the files actually present and did not
substitute the superseded SDD.

## Phase C: deterministic fixes already safe to make

- Corrected stale `N = 3` prose to the W-28 resolution `N = 4` in the dwell
  and P2 implementation documentation.
- Corrected the G-9 map: live state is 112 dimensions; the 13-field contract
  block is an ablation-only extension to 125.
- Corrected README gate/test status and removed the superseded SDD as an
  execution authority.
- Corrected the live pre-registration draft narrative without changing the
  sealed artifact or any frozen value.  The corresponding N=3 sentence remains
  inside the sealed artifact and cannot be changed without a controller ruling
  on correction versus re-freeze.
- Removed the stale `p0 = 2 W / serves nobody` module narrative from
  `env/step.py`; the replacement states the live derived 0.825 W start and the
  existing fail-loud feasibility gate.  The focused step-environment test file
  exited zero after this documentation-only change.

## Phase A: historical isolated closure before shared transfer

The shared `pptx-craft` project was not safe to edit because another Codex
session had an unresolved write call against the same deck/thesis scope.  To
avoid losing that work, the approved restoration was completed in the isolated
snapshot `/tmp/mcrl-phase-a.Af1Dan/project` first.  This is validation evidence,
not a claim that the shared checkout has already been repaired or committed.

- Restored the controller-approved Part 1 system-model, MODQN §4.1, and reward
  calibration pages, plus the Part 2 rule-limits page; the five pages that the
  handoff says should remain deleted were not restored.
- The A/B/C English and Chinese-notes source twins have zero structural diff
  under both the handoff normalization and a normalized-AST comparison.
- Full isolated pipelines passed for A, B, C, D and all three Chinese-notes
  twins.  Each process exited zero, emitted its delivered artifact line, and
  reported zero structural/language/native-math failures and zero geometry
  findings.

| Isolated pipeline | Slides including cover | Native math | `FAIL` lines | Delivered lines |
|---|---:|---:|---:|---:|
| `deck_a` / `deck_a_zh_notes` | 33 / 33 | 127 / 127 | 0 / 0 | 1 / 1 |
| `deck_b` / `deck_b_zh_notes` | 15 / 15 | 32 / 32 | 0 / 0 | 1 / 1 |
| `deck_c` / `deck_c_zh_notes` | 12 / 12 | 49 / 49 | 0 / 0 | 1 / 1 |
| `deck_d` | 13 | 55 | 0 | 1 |

- A fresh-eye render review found no clipping, collision, or visual gate
  blocker on the restored or formula-signature pages.  The remaining tiny
  labels inside two imported source charts are non-blocking source-image text.

Before transfer, the shared source hashes and writer session must be checked
again.  Only the seven deck source paths may receive the validated delta; the
mixed existing `edu_kit.py`, `latex_unicode.py`, `pipeline.py`, and HOBS asset
work must be preserved and committed only with an exact pathspec as the
handoff requires.

## Phase E: historical isolated synchronization before shared transfer

The thesis/document delta was prepared in `/tmp/mcrl-phase-e.dg71Ep`, again
without writing the occupied shared checkout.  Eight of the eleven document
targets changed; the ZH/EN/bilingual CH4 sources were audited and already
matched the adopted contract.

| Conflict | Adopted authority and resolution |
|---|---|
| Receive-pattern lower angle | Later implementation/ruling value: `theta^R_min = 2.498 deg`, replacing 2.05 deg in all three CH3 variants. |
| Active decision interval | Frozen implementation contract: 30.08 s in the CH5 experiment table; the 1 s occurrence remains only as an explicitly labeled sensitivity arm. |
| Reward scales | Frozen P3/analytic outputs `(2471140.576, 1.0, 6)` replace pending/legacy values. Effective shares were open at Phase E and are now measured in the post-run report, without automatic thesis promotion. |
| Loss and power surface | Later controller/runtime contract: `L_f/L_g/L_c/L_s`, elevation arguments on the last three, `p_max = 1.65 W`, and `p^0 = 0.825 W`. Old HOBS names remain only where the source notation is explicitly mapped to the active names. |
| Fixed power | Runtime and later ruling: exact `P^f` mapping with `P_cir = 0.338 W` and once-per-active-satellite `P_BB = 0.200 W`; the aggregate remains state-dependent, not calibration-pending. |
| Connection gates | Later user ruling and live runtime: delete active `m^e`; use `x = a*z`, with link feasibility carried by the per-beam power gate. Historical/deletion rows remain explanatory only. |
| Function arity | Handoff equality-left rule and cleaned deck surface: definitions carry `theta_3dB` through `G^T`, `F`, power, SINR, throughput, system power and displayed EE signatures. |

Two independent isolated `bash thesis-mc/tools/build_all.sh` runs exited zero.
The second reported `DOCX STRUCTURE PARITY -> PASS`, source-set digest
`fafdf69850171ef1913fe454b9cf0fa8e230f961d044db80fbafad5f94e5bf54`,
and `COHERENCE -> PASS`.  Targeted scans found no active stale 2.05-degree,
one-second-main-arm, legacy reward-scale, 2 W segment-start, or old-loss-name
claim. At this Phase E checkpoint the two handoff-approved post-training
empirical quantities remained unfilled. The effective-share quantity is now
measured in the post-run report; no thesis insertion is implied.

A subsequent fresh-eye audit passed the semantic delta and found one citation
typo: the symbol-table row for `L_(u,s,v)` pointed to (3.9) instead of its
definition at (3.10b).  The isolated source now cites (3.10b); this does not
change the already-passing thesis build inputs.

This is not yet a claim about the shared thesis checkout.  Its exact eleven
target hashes were captured before transfer and must be rechecked after the
overlapping session is stopped; any intervening delta must be merged rather
than overwritten, followed by a formal build from the shared checkout.

## Historical blockers resolved by the 2026-08-24 closure ruling

### The sealed record contains a Q-E narrative contradiction

`artifacts/PREREG-FROZEN-2026-08-23.json` simultaneously records
`dwell.steps = 4`, Q-E `resolved = 4`, and a P2 note saying Q-E closed at
`N = 3`.  The first two fields and W-28 make the executable choice clear, so
this is not permission to run N=3.  It is nevertheless an internally
inconsistent pre-registration record, and editing it in place would change the
sealed bytes/digest.  The controller must either declare the P2 sentence a
non-normative clerical error while preserving the seal, or authorize one
corrected re-freeze.  Since P6 also lacks operational frozen fields, a single
controller-authorized re-freeze could close both defects without pretending
that the current digest already did so.

### P6 controls are named but not operationally frozen

The frozen P6 entry requires all of the following: normalized Q margin, the
four G-3 collapse metrics, scalar reward, a random near-tie control,
perturbation stability and cross-seed ranking consistency.  The permitted
current authorities do not define:

1. the near-tie threshold or the randomization rule;
2. the perturbation target, magnitude/distribution, statistic or pass rule;
3. the ranked objects, seed matrix, aggregation or consistency threshold.

An alpha-only runner would silently narrow the frozen P6 obligation.  Adding
those choices now would be a post-freeze protocol change.  Therefore no P6
runner or server job may claim compliance until a controller ruling supplies
the missing definitions or explicitly narrows the obligation and re-freezes
the protocol.

### B6 runtime cadence conflicts with the adopted decision record

The scenario decision record says satellite candidate identities are rebuilt
at a dwell boundary and remain stable within the dwell.  The current runtime
updates D2 and rebuilds slot assignments at every decision.  No later ruling
explicitly supersedes B6.

The repair direction is a boundary cache, but the permitted authority does not
say whether D2 eligibility/mask also freezes, whether the D2 latch continues
updating for deferred application, or how an incumbent that leaves eligibility
behaves before the next boundary.  Those choices change the training process.
They must not be invented merely to make the suite green.

## Earliest valid next gate

A controller ruling must resolve the sealed Q-E sentence, P6 operational
semantics, and B6 within-dwell semantics.  After that ruling, implement
behavior-first tests, fix the runtime, rerun all three local guards,
synchronize the server, rerun the three guards there, and launch the heavy P6
sweep inside `tmux` on the Ubuntu server.
