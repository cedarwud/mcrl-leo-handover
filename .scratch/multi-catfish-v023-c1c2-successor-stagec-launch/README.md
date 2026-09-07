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

The execution binding also pins the scheduling addendum byte digest. The binder
publishes `early_baseline_admission.json` and its named sidecar; that admission
binds the plan, addendum, BASELINE checkpoint/status/adapter closure, code
manifest, execution configuration, TLE, PREREG, and prospective authority. It
admits only `BASELINE` episodes 1--3,000 with
`execution_mode: "arm_decoupled"`. It carries no fabricated Stage-A export or
Stage-B PASS receipt. Learned-arm chunks continue to require the existing
Stage-A/B runtime admission.

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
   receipt. Both record the sealed runtime-admission path/digest, the exact
   Stage-A PASS receipt, and the three admitted Stage-A export paths/digests.
7. Launch the 100 rung in tmux through
   `sync_launch_v023_c1c2_successor_stagec_server.sh`. Resume explicitly from
   checkpoint 100 to 500, 500 to 1,500, and 1,500 to 3,000. Earlier rungs never
   emit or select a scientific disposition.
8. Independently run `verify_v023_c1c2_successor_stagec.py` after 3,000. Any
   inconsistency is `STOP_PHYSICAL_EVALUATION_INTEGRITY`, never a scientific
   result.
9. A held 3,000 result may continue to 9,000 only after the controller notifies
   the owner and writes a formal owner-notification marker quoting the owner's
   literal reply, then writes a separate continuation-authority file plus its
   `.sha256` sidecar. The marker contains:

   ```json
   {
     "formal": true,
     "status": "OWNER_NOTIFIED_FOR_9000_CONTINUATION",
     "owner_reply_verbatim": "<owner's literal reply, at least 20 characters>",
     "notification_sent_utc": "<ISO-8601 UTC timestamp>",
     "owner_reply_received_utc": "<ISO-8601 UTC timestamp>",
     "notification_channel": "<channel used>",
     "recorded_by": "<controller session id>",
     "result_3000_sha256": "<digest of the preserved 3000 result.json>",
     "bindings_sha256": "<digest of the execution bindings file>",
     "plan_sha256": "866d28e05b04a361041f829e424a2417f49987239b7771ee94f43022d35e01bb"
   }
   ```

   The marker itself has a named `.sha256` sidecar. The authority is written
   after the marker and embeds the marker's path/SHA-256, the SHA-256 of the
   literal reply, the controller session id, the preserved result/checkpoint
   digests, the policy-map digest, the bindings digest, and the plan digest.
   Its external named `.sha256` sidecar authenticates the authority.

   ```json
   {
     "schema": "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1-continuation-authority-v1",
     "status": "AUTHORIZED_CONTINUATION_TO_9000",
     "continuation_from_episode": 3000,
     "continuation_to_episode": 9000,
     "owner_notification": {"status": "OWNER_NOTIFIED", "path": "<absolute marker path>", "sha256": "<marker digest>"},
     "owner_reply_sha256": "<SHA-256 of the exact UTF-8 reply>",
     "recorded_by": "<controller session id>",
     "bindings_sha256": "<digest of the execution bindings file>",
     "plan_sha256": "866d28e05b04a361041f829e424a2417f49987239b7771ee94f43022d35e01bb",
     "policy_bindings_sha256": "<digest of exact four-arm policy bindings>",
     "held_terminal_token_sha256": "<digest of C1C2_DEVELOPMENT_PREDICTION_HELD>",
     "result_3000_sha256": "<digest of preserved result.json>",
     "checkpoint_3000_sha256": "<digest of checkpoint-003000.json>"
   }
   ```

   This is deliberately a **procedural control**, not cryptographic owner
   verification: an auditor with write access can fabricate the quoted string.
   The handoff report must separately log the notification exchange (channel,
   sent time, reply time, verbatim reply, and recording controller session).
   No receipt may claim cryptographic verification of the owner's identity.

   The launcher refuses any missing field and prints a banner quoting the
   verbatim reply before starting 9,000. The core runner then authenticates the
   authority file, its sidecar and embedded digests, revalidates the complete
   3,000 history (including any sealed repair authority), preserves the original
   `result.json`, and emits `continuation-result.json` without a second
   scientific disposition.

## Server launch and resume

`--dry-run` performs no SSH, rsync, tmux, simulator, or artifact write beyond
local temporary bookkeeping. It prints the exact remote bind, preflight,
Stage-B, tmux, acknowledgement, and log locations:

```bash
./sync_launch_v023_c1c2_successor_stagec_server.sh --dry-run
```

Before Stage A exists, the prospectively bound early-BASELINE route is:

```bash
./sync_launch_v023_c1c2_successor_stagec_server.sh \
  --dry-run --early-baseline-only
./sync_launch_v023_c1c2_successor_stagec_server.sh \
  --early-baseline-only
```

This omits `--stage-a-output`, runs the early-BASELINE preflight, and starts
only BASELINE 100-episode chunks. It does not run Stage B or a learned arm.

The formal launcher first requires the seed checkout's commit/tree to match the
local bound commit/tree, synchronizes the manifest closure into a fresh copy,
then verifies the copied checkout's commit/tree again before binding. It never
overlays a seed checkout from a different tree. It runs the
bind/preflight/Stage-B gates, starts the 100 rung in a
named tmux session, and waits at most 120 seconds for both a write-once startup
marker and a live tmux session.

Subsequent cumulative calls use the same bindings, preflight receipt, Stage-B
root, output root, and plan. For example, the 500 call adds:

```text
--pause-at 500 --resume-checkpoint <output>/checkpoints/checkpoint-000100.json
```

The corresponding predecessor checkpoints are `000500` for 1,500 and
`001500` for 3,000. The 9,000 call must use checkpoint `003000` and add
`--continuation-authority`, `--owner-notification-marker`, and
`--controller-session-id`. A resume following an integrity STOP additionally
requires `--repair-authority`; that sealed authority is passed to the core
runner rather than bypassing its history/repair checks.

Every checkpoint, rung and terminal receipt carries the admission mapping:
learned arm to authenticated Stage-A export and exact frozen policy binding,
and `BASELINE` to its checkpoint/status/adapter binding. A terminal falsified
root, or the completed authorized 9,000 continuation, is sealed with
`FORMAL-ADMISSION.json` plus sidecar and whole-tree `MANIFEST.sha256`/`COMPLETE`
for the renderer. A held 3,000 root remains intentionally unsealed while the
declared continuation decision is pending.

## Arm-decoupled chunk execution

`launch_stage_c_chunks.sh` fans one fixed-plan arm into contiguous 100-episode
chunks. It caps tmux workers at `cores-2`, pins OMP/OpenBLAS/MKL/NumExpr to one
thread, skips chunks carrying a complete authenticated receipt, resumes only a
contiguous write-once prefix, and refuses a duplicate completed chunk or live
duplicate tmux session. Use `--early-baseline-admission` only for `BASELINE`;
use `--runtime-admission` for a learned arm. A second invocation with `--merge`
requires all 30 chunks and creates the per-arm ordered merge.

`run_v023_c1c2_successor_stage_c_chunks.py merge-four` refuses a missing arm.
It assembles episode records in the frozen `FULL2, DROP_C1, DROP_C2, BASELINE`
order, recomputes every cumulative pool with `math.fsum` over individual
episode totals, and emits four-arm checkpoints/rungs only from complete arm
coverage. No boundary below 3,000 emits a scientific disposition; early
BASELINE cannot continue above 3,000.

The independent verifier accepts `--arm ARM` for a chunk root and recomputes
the plan identity, persisted age stream, exact boundary states, episode
coverage, ordered file digest, provenance, and binary64 pool values. Formal use
remains gated on all four server equivalence receipts in
`ACCEPTANCE-SERVER-EQUIVALENCE.md`; those runs are intentionally not launched
by the bundle.

## Independent verification and tests

The verifier reconstructs the frozen policies from their authenticated files,
recomputes episode and pooled endpoints from additive bits,
positive energy, served counts, and pooled opportunities; checks matched world,
plan, field, policy, arm-order, cadence, rung, and result identities; and
rejects any path or receipt marked `REHEARSAL-NONFORMAL` or `formal:false`, any
STOP token, rewritten cumulative prefix, or invalid policy/admission digest.
Preflight, Stage B, every Stage-C launch/resume and final verification also
require the live checkout commit/tree and deterministic process/resource
configuration to equal the frozen execution binding.

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
