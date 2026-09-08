# C3-S closed-loop kill screen v1 — result record (controller, 2026-09-08 11:55 UTC)

**Outcome: `C3S_FULL_SCREEN_SUPPORT` and `C3S_LITE_SCREEN_SUPPORT`.** Predeclared progression (Addendum A §C): both SUPPORT → **LITE proceeds**.
Claim ceiling (from the receipt): `TRAIN_DEVELOPMENT_C3S_CLOSED_LOOP_KILL_SCREEN_NO_LEARNER_NO_EFFICACY_NO_TEST`. `efficacy_claim = false`, `test_split_opened = false`, `integrity = true`.

## Bindings
- Contract: `V023-C3S-SET-LEVEL-COORDINATOR-KILL-SCREEN-CONTRACT-2026-09-08.md` sha256 `1b19e0f4c6c5f1591e3ca670da368fea0e785ec70fc51af5a9fe9edfdbfc7a7f` (with Addendum A).
- Run: server worktree `/home/sat/mcrl-v023-c3s-run` (branch `c3s/run-v1`, v1 runner commit 4abe9da), output `runs/c3s-20260908-r1`; 12 units launched 10:38 UTC detached, all `EXIT=0` by 11:41 UTC; merge 11:47 UTC.
- Terminal receipt sha256 `a66b481303a28c31b49f127e302d304ac1ef34de5eb526dd2e3949bb5196ea69` (copied to `runs/c3s-20260908-r1/terminal/`; unit receipts under `runs/c3s-20260908-r1/units/`).
- η_ref = `0x1.d94fb72305d6ap+26` bits/J (E1 η_BASE), unchanged.

## Pooled result (exact fractions in the receipt; floats here)
| Arm | pooled EE (bits/J) | vs BASE | served / 36 000 |
|---|---|---|---|
| BASE | 117 419 389.19 | — | 35 971 |
| FULL | 120 804 786.83 | **+2.883 %** | 35 971 |
| LITE | 120 850 121.10 | **+2.922 %** | 35 971 |

Per world (FULL / LITE vs BASE): 5887834234954284271 +2.460 / +2.556 %; 7305539127129390835 +3.356 / +3.138 %; 7691130988233444596 +2.693 / +2.809 %; 8464287092499831892 +3.040 / +3.205 %. Per lineage: 2026092101 +2.763 / +2.909 %; 2026092102 +2.767 / +2.769 %; 2026092103 +3.127 / +3.096 %. Service identical across arms in every world and lineage.
Both coordinators deviated from BASE at all 360 decisions (4 worlds × 3 lineages × 30 steps). Full-vs-lite difference: LITE − FULL ≈ +0.04 % (non-decisional, reported only).

## Latency (12 units single-threaded, run 12-way parallel on 20 cores, i.e. under contention)
| Arm | mean decision wall | median | p95 | max |
|---|---|---|---|---|
| BASE | 1.88 s | 1.84 s | 3.0 s | 3.9 s |
| LITE | 49.4 s | 43.1 s | 57.2 s | 254 s |
| FULL | 66.8 s | 56.3 s | 72.9 s | 420 s |

LITE phase means: enumeration 0.012 s, q_inference 1.9 s, nominal_evaluation 12.9 s (catalog mean 917 configurations, unique nominal evaluations mean 901). FULL: catalog mean 3 218, unique evaluations mean 2 813, nominal_evaluation mean 30.6 s. The 30.08 s control interval is exceeded by both arms as measured; an uncontended re-measure and a decision-preserving engineering speed-up are engineering-lane items (dispatched 11:58 UTC), not scientific changes.

## What this is and is not
- It is the first closed-loop positive C3 result on this line: the one-step deployable gain (S0 +1.81 %) did not erode over 30 steps; it grew.
- It is a TRAIN-split development kill screen on four world clusters with dependent contrasts, against a frozen learned BASE, using the simulator's nominal physics as the coordinator's model (model privilege). It authorises progression to the confirmatory ladder (FULL2 + C3-S vs FULL2 on fresh worlds), nothing more. No efficacy claim, no paper claim.
- Independent red-team reviews (fresh context: Claude Opus, Gemini 3.8 Flash High) and an astra sealing review of the confirmatory plan were commissioned at 11:58 UTC before any further step.

## Next (predeclared or engineering)
1. Nine-arm variant matrix (sealed, running since 11:47 UTC) → lowest-latency SUPPORTer per its own rule; LITE is replicated inside it.
2. Confirmatory plan sealing (astra review first), arm binding per the adjudication; ladder needs stage-A attempt #3 FULL2 exports.
3. Latency engineering with proven bit-identical decisions (codex sol) before any deployability sentence is written.
4. Shadow-replay decomposition and V-E remain pre-built tools; they are not needed for progression now.

## Correction 2026-09-08 12:30 UTC (controller, after the independent harness audit)
- **Latency attribution was wrong in the table above.** The harness audit (`HARNESS-AUDIT-C3S-V1-CLAUDE-OPUS-2026-09-08.md`, check 8) found that the two `_live_neutrality_fingerprint` structural hashes sit inside the coordinator arms' measured decision window and not inside BASE's: 51.3 % (FULL) and 69.9 % (LITE) of the reported per-arm decision wall is audit instrumentation. On the comparable measure LITE's mean decision wall is **14.88 s, below the 30.08 s control interval**; FULL ≈ 32.5 s. The sentence "the 30.08 s control interval is exceeded by both arms" is withdrawn; an uncontended, instrumentation-free re-measure remains an obligation before any deployability sentence.
- **Independent recomputation**: pooled bits, joules, η and served for all three arms, per world and per lineage, reproduce bit-exactly from the 12 unit receipts without the runner's merge code (relative error 0); mean-of-ratios pooling gives +2.885 % / +2.927 % (not the estimand; reported for robustness).
- **Open artifact question (from the fresh-context red-team, H1)**: the endpoint charges no energy for a handover while the training reward does, and the transmit-gain factor of each user's received power is anchored at association-segment start, so re-anchoring is a free option BASE was trained to avoid; the EE advantage grows monotonically with segment age (+1.35 / +1.75 / +3.92 / +9.26 % by dwell phase). Until the instrumented churn-null replay (NULL, RANDOM_RENEW, BASE_FORCED_RENEW_4 arms with handover / lit-beam / segment-age counts) and the physics audit of the anchored power model return, the SUPPORT is treated as **mechanism-unattributed**, and the confirmatory plan is not sealed.
- **Service tie** (35 971 in all arms) is near-certain by construction (nominal guard + saturation at 100/100 on 352/360 BASE steps; all 29 unserved user-steps at step 0); it is not corroborating evidence.
