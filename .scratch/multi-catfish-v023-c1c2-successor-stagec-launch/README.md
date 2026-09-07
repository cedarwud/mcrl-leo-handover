# V0.23 C1/C2 successor Stage-B/C formal launch bundle

This directory is the execution-only bundle for contract sections 5–9. It
does not train a learner, open `TEST`, introduce a fourth learned arm, or
authorize computation by itself. The fixed physical arm order is `FULL2`,
`DROP_C1`, `DROP_C2`, `BASELINE`; `BASELINE` always has `routes=[]`.

The bundle composes the producer-owned physical runner and plumbing diagnostic
from `../multi-catfish-v023-c1c2-successor-physical-evaluation/`. Stage B must
publish `PASS_PLUMBING_INTEGRITY` before any Stage-C controller can start.
Stage C uses one 9,000-world plan identity, writes checkpoints and rung
receipts every 100 matched worlds, and pauses cumulatively at 100, 500, 1,500,
and 3,000. Only the 3,000 boundary writes `result.json` and the single
`C1C2_DEVELOPMENT_PREDICTION_HELD`/`...FALSIFIED` token with all applicable
non-exclusive reasons.

## Freeze order

1. Seal Stage A with `PASS_SOURCE_TRAINING_INTEGRITY`, `MANIFEST.sha256`,
   `COMPLETE`, the canonical receipt, and exactly three epoch-100 producer
   exports in `FULL2`, `DROP_C1`, `DROP_C2` order.
2. Install the post-fix baseline adapter that explicitly exposes
   `contract_fields_excluded: true`. The binder intentionally fails closed if
   that assertion is absent even when the checkpoint and status authenticate.
3. Build and externally pin the code closure:

   ```bash
   /home/sat/mcrl-leo-handover/.venv/bin/python build_v023_c1c2_successor_stagec_manifest.py --write
   ```

4. Run `bind_v023_c1c2_successor_stagec_freeze.py`. It authenticates Stage A,
   the baseline, PREREG, the frozen TLE tree, git commit/tree, physical package,
   bundle, and transitive closure; builds the world plan write-once; checks its
   semantic digest is
   `866d28e05b04a361041f829e424a2417f49987239b7771ee94f43022d35e01bb`;
   and publishes `V023-C1C2-SUCCESSOR-STAGEC-EXECUTION-BINDINGS.json` plus its
   external `.sha256` sidecar. The JSON never embeds its own digest.
5. Run `preflight_v023_c1c2_successor_stagec.py` against an absent output root.
   It reconstructs the baseline adapter, repeats a deterministic masked-policy
   invariance check, authenticates the plan and closure, rejects circular
   bindings and forbidden topology/split tokens, and writes a preflight receipt
   plus sidecar.
6. Run `run_v023_c1c2_successor_stage_b.sh`; retain its formal gate and plumbing
   receipt.
7. Launch the 100 rung in tmux through
   `sync_launch_v023_c1c2_successor_stagec_server.sh`. Resume explicitly from
   checkpoint 100 to 500, 500 to 1,500, and 1,500 to 3,000. Earlier rungs never
   emit or select a scientific disposition.
8. Independently run `verify_v023_c1c2_successor_stagec.py` after 3,000. Any
   inconsistency is `STOP_PHYSICAL_EVALUATION_INTEGRITY`, never a scientific
   result.
9. A held 3,000 result may continue to 9,000 only with both a separate
   continuation-authority file and a formal owner-notification JSON containing:

   ```json
   {
     "formal": true,
     "status": "OWNER_NOTIFIED_FOR_9000_CONTINUATION",
     "authority_sha256": "<digest of the separate authority file>",
     "bindings_sha256": "<digest of the execution bindings file>",
     "plan_sha256": "866d28e05b04a361041f829e424a2417f49987239b7771ee94f43022d35e01bb"
   }
   ```

   The continuation preserves the original 3,000 `result.json` and emits
   `continuation-009000.json` with `new_scientific_token_emitted=false`.

## Server launch and resume

`--dry-run` performs no SSH, rsync, tmux, simulator, or artifact write beyond
local temporary bookkeeping. It prints the exact remote bind, preflight,
Stage-B, tmux, acknowledgement, and log locations:

```bash
./sync_launch_v023_c1c2_successor_stagec_server.sh --dry-run
```

The formal launcher synchronizes the manifest closure plus this bundle into a
fresh checkout, runs the bind/preflight/Stage-B gates, starts the 100 rung in a
named tmux session, and waits at most 120 seconds for both a write-once startup
marker and a live tmux session.

Subsequent cumulative calls use the same bindings, preflight receipt, Stage-B
root, output root, and plan. For example, the 500 call adds:

```text
--pause-at 500 --resume-checkpoint <output>/checkpoints/checkpoint-000100.json
```

The corresponding predecessor checkpoints are `000500` for 1,500 and
`001500` for 3,000. The 9,000 call must use checkpoint `003000` and add both
`--continuation-authority` and `--owner-notification-marker`.

## Independent verification and tests

The verifier recomputes episode and pooled endpoints from additive bits,
positive energy, served counts, and pooled opportunities; checks matched world,
plan, field, policy, arm-order, cadence, rung, and result identities; and
rejects any path or receipt marked `REHEARSAL-NONFORMAL` or `formal:false`.

Unit-only test command from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 \
PYTHONPATH=/home/sat/mcrl-v023-codex-ws-stagec-20260907/src \
TMPDIR=/home/sat/mcrl-v023-codex-ws-stagec-20260907/.tmp \
/home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q \
.scratch/multi-catfish-v023-c1c2-successor-stagec-launch
```

The fixtures use the source model's own checkpoint writer and the physical
runner's own receipt/rung writers. Mutation tests cover a fifth arm,
non-formal/rehearsal roots, plan drift, missing owner notification, and a
circular binding digest. They do not run the simulator.
