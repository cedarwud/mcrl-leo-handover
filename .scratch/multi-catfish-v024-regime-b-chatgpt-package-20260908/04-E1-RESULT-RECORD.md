# E1 existence screen — result record (controller, 2026-09-08 06:05 UTC)

Sealed contract: `V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md` (sha256 b908dcb4aa791cfc49426923b8c26a0008b66cdb94c759241069288bcdfb7338).
Run: server E1 checkout `/home/sat/mcrl-leo-handover-e1` (branch e1/multi-catfish-v023-20260908, HEAD a99e6f4 at launch), preflight `E1-PREFLIGHT-MANIFEST.json`,
13 launch authorities, 12 units launched 05:31 UTC (tmux `mcrl-v023-e1`), all `COMPLETE` by 05:49 UTC; `--merge` 05:57–05:59 UTC.
Output root: `/home/sat/mcrl-v023-c3-existence-e1-20260908-r1` (units 4.4 GB; `terminal-receipt.json` 119 602 620 bytes,
sha256 `0bc54fad23c8cdac2ce789c49ee37880f4df6e32110576c7a800443df0e7c4a6`, mode 0444). Not committed to git (size); server-resident.

| field | value |
|---|---|
| status | COMPLETE; integrity true; efficacy_claim false; episode_training false; learner_update false; test_split_opened false |
| claim ceiling | `TRAIN_DEVELOPMENT_C3_EXISTENCE_SCREEN_E1_NO_LEARNER_NO_EFFICACY_NO_TEST` |
| panel | 4 derived worlds × 3 lineages × 10 steps = 120 anchors, 100 users, N = 12 000 opportunities |
| η_BASE | 124 075 740.547 bits/J (hex `0x1.d94fb72305d6ap+26`); BASE served 11 975 / 12 000; minimum served 11 963 |
| U₁ (≤ 1 changed user per anchor, certified) | 126 547 715.769 bits/J = **+1.992 %** over η_BASE; served 11 974 (feasible); Dinkelbach 3 iterations; `global_upper_bound_proved` present |
| J₁ (fixed evacuation catalog, certified) | 126 832 819.837 bits/J = **+2.222 %** over η_BASE; served 11 972 (feasible); 3 iterations |
| outcome (contract §3, δ = 0) | **`E1_UNILATERAL_HEADROOM`** and **`E1_JOINT_HEADROOM`** |

What this is: an exact finite-panel oracle ceiling with realised information; it establishes physical headroom on this TRAIN panel for both
declared classes. What it is not: deployability, learnability, additive composition, efficacy, or TEST evidence. Per §3 the (HEADROOM,
HEADROOM) cell authorises declaring a candidate's kill screen in either family: C-C (unilateral, from the tape) and C-A (joint catalog);
C-B (unilateral, H = 3) also admissible. Nothing else is authorised by this result.
