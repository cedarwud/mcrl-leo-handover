# PROGRESS-B (lane B: method owner + independent readout)

Started 2026-09-12. Worktree `/home/u24/papers/mcrl-leo-handover-mc2`, branch `mc2/judge-override-20260912`, base `6136c514`. Contract commit `67e175bd`.

## Status (updated ~05:55Z)
- **r2 co-signed.** `CONTRACT-COSIGN.md` first line is `STATUS: COSIGNED r2` (r1 line kept below it). r2 = commit `b6573b58`, blob `37b3404e`. r2 adopts R1-1 to R1-4, F-1 to F-3, the N-items, my §4 and citation corrections, and adds test (11). One nit only: "B-null's approval rate is expected to be far lower" should read "expected to differ (direction measured by the P0 probe)".
- **`b_readout.py` is now r2-exact**: clauses (i)–(vi) with their numbers, score = mean_k min(own A-only, D3-T0, B-only), primary with the 0.10 pp tie to v1, the ep-300 gate with `--primary` / `--other-qualified` for F-2, a refusal to read k = 15–17 without `--fallback-authorised`, and the "reported beside" block. `selftest` covers the R1-1 case, ties, pending, (vi) and F-2. The k8 regression still gives −4.120 %.
- **`CODE-READ.md` written** against the sha-pinned working tree: no loss or data-causality defect; D-1 = test (11) and v2 test coverage before the v2 cells are counted; D-2 to D-4 are nits.
- Lane A's code is still uncommitted (only contracts r0/r1/r2 are committed).

## Status (earlier, ~05:20Z)
- **r1 co-sign: DONE.** `CONTRACT-COSIGN.md` first line is now `STATUS: COSIGNED r1`. It covers commit `9d3625c4`; the blob sha `62e8c209` equals the reviewed text.
  - No INVALIDATES.
  - R1-1 (v2 must also beat D3-T0; the selection score takes the min including D3-T0) changes a decision and must be closed before the ep-100 read.
  - R1-2 to R1-4, F-1 and F-3 are text items.
- `b_readout.py` was extended to r1:
  - it has 8 cells and v1/v2 versions;
  - it computes qualification and selection twice, once as written and once with R1-1;
  - the fallback note is printed;
  - the `selftest` subcommand passes and demonstrates R1-1;
  - the k8 regression still gives −4.120 %.
- A monitor (task b86ui7cjp, 60 min) waits for lane A's code commit. HEAD is `9d3625c4` = contract r1.
- Answered the controller's r2 list and the agy r1 review in `CONTRACT-COSIGN.md`:
  - I agree with all 7 points; none is INVALIDATES.
  - agy #1: I tightened the trigger to "v2 committed before any ep-100 file of any selection cell".
  - R1-1, R1-2, R1-3, F-1 and F-3 are reading-rule changes, not documentation-only. They must be in r2 before the read.

## Status (earlier)
- **Task 1 (co-sign): DONE.** `CONTRACT-COSIGN.md` first line is `STATUS: COSIGNED r0`. `LITERATURE-DELTA.md` is written.
  - No INVALIDATES.
  - F-1 to F-3 must be closed before the ep-100 read.
  - V2-1 blocks v2 only.
  - N-items are text and disclosure fixes.
- **Task 2 (code read): WAITING.** Lane A has an untracked `src/mcrl/algorithms/cf_judge.py` in progress and no commit yet. Poll `git log --oneline` / `git diff 6136c514`.
- **Task 3 (readout tooling): mostly done.**
  - The k8 files are fetched to `B/k8/` and sha256-verified against sat.
  - `b_readout.py` **reproduces k8** FULL/A-only = **−4.120 %**, paired 0/24, with 18/18 identity checks per file, including the recomputed payload hash. Output is in `k8/b_readout-k8.json`.
  - The override fields are set to lane A's `judge_overrides` / `judge_decision_rows`.
  - The mc2 preset regexes assume arm names `E0-10-…-{A+B|B|A+R}-…-k{k}`. Confirm them at lane A's commit.
  - `b_output_change.py` is written and has not been run (it is for sat, read-only).
- **Task 2 prep.** Lane A's uncommitted `cf_judge.py` and the `cf_dev.py` diff are read preliminarily:
  - the judge is placed before `env.step` with `_env_rng`, inside `frozen_driver_positions`;
  - the loss is `(per_row*w).mean()`;
  - the null draws from `(9_243_000, k)` on its own stream, and B/R abstain at T−1.
  - To verify at commit:
    - the `_judge_null_rng` save/restore in `training_state_dict`;
    - `jlog.as_log()` merged into the episode log;
    - the `JudgeSpec` in `arm_config_payload`;
    - `policy_payload` provenance;
    - the gate-shut test hook;
    - that arms 1–9 hashes are unchanged.

## Read so far
- Contract r0.
- `cf_dev.py`, `cf_teacher.py`, `cf_tnext.py` (sha `86f0d6ee` ok), `cf_multi_sources.py`, `cf_credit.py`, `cf_ratio.py` (481-900).
- `step.py` 480-1460; `service.py::resolve_service`.
- `dev_e0_common.py`, `run_dev_e0.py`, `dev_e0_aggregate.py`.
- Explainer 00/07, CATFISH-MECHANISM-FACTS, DQFD grounding.
- Lit agent: Cheng / Liu / Nair citations verified (Liu et al. = Liu, Yoneda, Wang, Walter, Chen; Cheng is not an author).

## Key facts (for resume)
- The judge's CRN is exact. The physics fading draw is over the candidate-window satellites (`step.py:891-904`), and segments are restored (`step.py:700-705`). Energy and served do not depend on fading; bits do.
- There is no beam cap in service, so Δn_served is u's own feasibility.
- The observation fading and the physics fading are different draws. The judge sees information the learner cannot.
- No prior sat runs at k = 10..19.
- The DEVVAL JSON stores pooled p10 only, not per-episode p10.
- k8 dirs on sat: `/home/sat/mcrl-v025-cf2s-multi-ws/runs-k8/{E0-1-D0-equal_share-k8, E0-4-D3-T0-equal_share-k8, E0-8-D3-multi-T0+T_NEXT-equal_share-k8, E0-8-D3-multi-T_NEXT-equal_share-k8, E0-9-...bernoulli...-k8}`.
- The MC2 root on sat (`/home/sat/mcrl-v025-mc2-ws/runs-ep100/`) does not exist yet.
