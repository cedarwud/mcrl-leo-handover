# CATFISHFACT progress

Working dir: /home/u24/papers/mcrl-leo-handover/.scratch/catfish-facts/
Output: CATFISH-MECHANISM-FACTS-2026-09-11.md

## Steps
- [x] 0. Create working dir; confirm sibling explainer package (12 files) + three server reports exist.
- [x] 1. Read sibling explainer 00, 02, 07, 99 (Q1, Q2, Q3 confound list) — all primary, read in full.
- [x] 2. Read server collapse diagnoses (probe-ws BASE, mqcollapse-ws MODQN) in full (Q3).
- [x] 3. Read V025-STAGES-6-8-CONTRACT-v1 in full + stage-C code (learner.py, deployment.py); read
       ee_axis_c1_selector.py / ee_axis_source_selectors.py headers (Q4).
- [x] 4. Q5 RESOLVED: frozen ckpt e6b063ef… == archived
       /home/sat/mcrl-leo-handover-20260825-corrected/artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt
       (sha verified by me). Its embedded trainer_config records
       r1_reward_label="system-energy-efficiency", provenance "paper eq. (3.25)", and NO r1_reward_mode key
       (PATCH P-20 already applied in the hash-bound source tree). => trained AFTER the switch. EE, not throughput.
- [x] 5. Q6 inventory (both projects' code).
- [x] 6. Report written.

## Detached processes
(none — no training, no new experiment was run; only file reads + one torch.load of a read-only ckpt)

## Key facts established
- Frozen ckpt trainer_config: r1 label = system-energy-efficiency; calibration ON,
  scales (2029238.4328742754, 1.0, 6.0); last_episode_log r1_mean = 9,635,190.20 (bit/J order).
- Archived tree step_types.py:168 "r1_system_ee_contribution: bit/J, R_u/P^N — **this is r1**";
  "r1_throughput: bit/s, R_u ... **Not r1.**"; modqn.py:614-620 builds the reward vector from
  [r1_system_ee_contribution, r2_handover, r3_load_balance].
- C1/C2/C3 = score decomposition of F = B − η_ref·E − Φ (contract B4) / source-selection rules.
  Not M1/M2/M3/ACRM. Stage-C learner has no reward/discount/bootstrap at all (learner.py:279-280).
- Correction to explainer 07 §7.5.4: presets.py:110-120 `acrm_full()` DOES set acrm_enabled=True
  (also :138-150 `acrm_annealed()`), contradicting "no config in the whole repo turns it on".
