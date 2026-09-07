# Stage-A formal run 2026-09-08 — STOP at operator step 2b (charter rule 1 gate red)

Outcome: **STOP_OFFLINE_CHAIN_GATE_FAIL**. No freeze, no bind, no launch, no commit.
Steps 3–8 of the controller sequence were not started. Nothing was written into any
sealed root. Server worktree `/home/sat/mcrl-leo-handover-wip` remains clean at HEAD.

## Identity

- Local HEAD `c5b74645c661a9669bd7c9ade9c4f0ee669eccee` == server worktree HEAD
  `c5b74645c661a9669bd7c9ade9c4f0ee669eccee`, branch `wip/multi-catfish-v023-20260907`.
- `git status --porcelain` on the server worktree: 0 entries, before and after all work.
- `/home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1` and
  `…-r1-checkout`: both absent (confirmed after the STOP).
- Environment exported for every server command exactly as briefed, plus
  `TMPDIR=/home/sat/mcrl-leo-handover-wip/.tmp` (created; git-excluded, porcelain stayed 0).

## Step 1 — preconditions: PASS

- r8 sealed root `/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8`: `COMPLETE` contains
  `8e1bd59e83d48c15ebc50054f2197936864f12f9c749225680a100c389f4bffd  MANIFEST.sha256`;
  independently `sha256sum MANIFEST.sha256` = `8e1bd59e83d4…f4bffd` (authenticates);
  `receipt.json` = `e9f8452646a3acc2cc96262501f3894dfc28558b73d191777c46f7c91a6f2376`.
  32 shard files (8 worlds × {c1,c2} × {informed,neutral}).
- `build_v023_c1c2_successor_stagec_manifest.py --check` →
  `STAGEC_CODE_MANIFEST_CURRENT entries=270 sha256=675431fa4c7132af35f9c62c49c3265bc434aa9daaeee2afa2cdae1bccb68ad8`, exit 0.
  Frozen pin `V023-C1C2-SUCCESSOR-STAGEC-CODE-MANIFEST-FROZEN.sha256` carries the same digest.
- Addendum sidecar present:
  `.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-07.md.sha256`
  = `9673928f20fae6d347b848e09d351ddd9bf0197a71b975ddc0106d0bdbf74d1e` = actual file digest.
  Addendum line 61 pins acceptance-procedure `b6d6ab8baa07011d3d72ea6b54efa9f25d6f666ca47c837af75cc359c10b17ff`
  = current `ACCEPTANCE-SERVER-EQUIVALENCE.md`.
- `build_v023_c1c2_successor_launch_manifest.py --check` →
  `SUCCESSOR_LAUNCH_MANIFEST_CURRENT sha256=e603106ddad8854ebf3fcc9244a42db6de5611e3a17a9ccb0a9ef16cdd1d02ee`, exit 0.
  No drift of any kind.

## Step 2 — post-seal load check: PASS

Command (2nd argument corrected from the briefed directory to the adapter file the
script's own signature requires — `ADAPTER = Path(sys.argv[2])  # target_batch_adapter.py`;
the directory form raises `AttributeError: 'NoneType' object has no attribute 'loader'`):

```
/home/sat/mcrl-v023-postseal-target-check-20260907/postseal_target_load_check.py \
  /home/sat/mcrl-leo-handover-wip/src \
  /home/sat/mcrl-leo-handover-wip/.scratch/multi-catfish-v023-target-batch-adapter/target_batch_adapter.py \
  /home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8
```

exit 0, 3m53s. `all_checks_pass: true`; all six checks true (c1 dim 228, c2 dim 448,
`EEAxisV014NormalizedPairBatch`, unit `normalized-repriced-ops3-delta-over-kappa`,
c2 rows match files, both modes load). adapter sha256
`3b8a2268e301970945254aedb5724fb2099a50d041b93493f7d29b08825907b8`; manifest sha256
`8e1bd59e…f4bffd`; `mcrl_src=/home/sat/mcrl-leo-handover-wip/src/mcrl/__init__.py`;
`receipt_status=TARGETS_MATERIALIZED_TRAIN`, `receipt_schema=multi-catfish-mcrl-v023-c1c2-target-generation-v1`,
`claim_ceiling=TRAIN_PHYSICAL_TARGET_GENERATION_ONLY_NO_LEARNER_NO_EPISODE_TRAINING_NO_EFFICACY_NO_TEST`.
Per mode: c1 49422 rows, c2 4330 rows, masks (·,28); 8 c1 + 8 c2 files each.

## Step 2b — offline real-artifact chain gate: **FAIL → STOP**

```
.scratch/multi-catfish-v023-engineering-lane/offline_realartifact_dryrun.py \
  --spec .scratch/multi-catfish-v023-engineering-lane/specs/successor_stage_a_chain.json \
  --repo /home/sat/mcrl-leo-handover-wip \
  --artifact target_root=/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8 \
  --output /home/sat/mcrl-v023-stageA-OFFLINE-GATE-NONFORMAL-20260907T234617Z
```

`DRYRUN_SUCCESSOR_STAGE_A_FAIL`, exit 2. Summary `{"blocked": 14, "failed": 1, "passed": 5}`.
Report preserved at `…-20260907T234617Z/dryrun-report.json`.
PASS: `authenticate`, `load`, `model_config`, `orchestrator_config`, `authority_digests`.

Two independent, structural spec defects (neither curable by re-running, by ordering, or
by `--artifact` overrides):

1. **`runner_config` FAIL — exact line:**
   `TypeError: FrozenSourceTrainingConfig.__init__() missing 1 required positional argument: 'provider_config_sha256'`
   raised at `offline_realartifact_dryrun.py:418`. `FrozenSourceTrainingConfig`
   (`.scratch/multi-catfish-v023-two-route-source-training-runner/v023_two_route_source_training_runner.py:436-442`)
   declares `provider_config_sha256: str` with no default. The spec's `runner_config` step
   supplies only `epoch_budget`, `orchestrator_config`, `provider_factory_spec`,
   `authority_digests`. The string `provider_config_sha256` appears in **no** engineering-lane
   spec or script. Nine downstream steps stay BLOCKED behind it (`runner`, `begin_new`,
   `one_epoch`, `one_epoch_state`, `export_one_epoch_state`, `reload_one_epoch_state`,
   `resumed_runner`, `resume`, `resume_one_epoch`).

2. **`learner_manifest` MISSING → 4 BLOCKED** (`factory_config`, `provider_probe`,
   `provider_next_batch`, `provider_for_runner`). The spec declares
   `.scratch/multi-catfish-v023-two-route-source-training-runner/LEARNER-MANIFEST.json`.
   The binder writes `V023-C1C2-SUCCESSOR-LEARNER-MANIFEST.json` into
   `.scratch/multi-catfish-v023-c1c2-successor-launch/` (`successor_launch_common.py:49`,
   `bind_v023_c1c2_successor_freeze.py:436,441`). No file named `LEARNER-MANIFEST.json`
   exists anywhere under `.scratch`; the briefed path is never produced.

Origin: the spec was last aligned at `7a5658e` (2026-09-07 16:20 UTC); the runner gained
`provider_config_sha256` in later commits (`dca2e2a` stage-A fix pass 6, `d0afd18`). The
formal chain is self-consistent — `verify_v023_c1c2_successor.py:940-947` does pass
`provider_config_sha256=provider_config_sha`. The stale artifact is the **gate spec only**.
All seven copies of `successor_stage_a_chain.json` on `sat` hash identically to
`2c1bde8aed240d7d0e96c414a0d3bb02a51683f33087e869d414e3f60e9f2680`; no corrected version exists.

Charter rule 1 ("no launcher runs before its offline real-artifact dry-run is green") plus
the briefed "all PASS required" make this a hard STOP. Repairing it requires editing
`successor_stage_a_chain.json`, which the operator mandate forbids.

## Preservation

Gate report `input_integrity` all PASS, before == after:
target_root `94326228eb0c1ec74d5c80a109f125c8da06d378be2d3d898a633490b732b58d`,
successor_contract `989b374f7913b08daef2a6354aaf287e750ff2b3f08127f2f8c32dd7afacb73a`,
model_config `9eafcd184bd0ec015498832be61b5c95a71373e98f63ab804c9654775a8b1d5d`,
factory_code `87a1e9805642018ba81aef344dcbf6752c09ad859ae11e2565aa8b05d5936d5a`.
`claim_ceiling=ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`, `scientific_output=false`.

Writes made, total: `/home/sat/mcrl-v023-stageA-OFFLINE-GATE-NONFORMAL-20260907T234617Z/`
and `/home/sat/mcrl-leo-handover-wip/.tmp/` (git-excluded). This file was **not** written
into the server worktree: with the freeze not performed, an untracked file there would make
the binder's whole-repository scan report dirty and invalidate the next freeze attempt.
