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

The prospective execution binding pins the sealed scheduling addendum, the
acceptance-procedure digest, code closure, baseline, PREREG, TLE, configuration,
plan, and predetermined Stage-A/B/C roots before Stage A. Stage A and Stage B
are later imported by the separately sealed, append-only
`STAGE-AB-ADMISSION-SUPPLEMENT.json`. All four arms use that supplement and one
authenticated runtime admission; the withdrawn early-BASELINE mode does not
exist. Formal chunks additionally require the sealed all-four-arm acceptance
bundle.

## Freeze order

1. Install the post-fix baseline adapter that explicitly exposes
   `contract_fields_excluded: true`. The binder intentionally fails closed if
   that assertion is absent even when the checkpoint and status authenticate.
2. Complete (but let the controller seal) scheduling-addendum section 2 and
   the acceptance procedure. Build and externally pin the code closure:

   ```bash
   /home/sat/mcrl-leo-handover/.venv/bin/python build_v023_c1c2_successor_stagec_manifest.py --write
   ```

3. Run `bind_v023_c1c2_successor_stagec_freeze.py` before Stage A. It binds the
   predetermined Stage-A root and authenticates the baseline, PREREG, TLE,
   sealed addendum, acceptance procedure, git commit/tree, physical package,
   bundle, and transitive closure; builds the world plan write-once; checks its
   semantic digest is
   `866d28e05b04a361041f829e424a2417f49987239b7771ee94f43022d35e01bb`;
   and publishes `V023-C1C2-SUCCESSOR-STAGEC-EXECUTION-BINDINGS.json` plus its
   external `.sha256` sidecar. The JSON never embeds its own digest.
4. Run and seal Stage A, then run Stage B with the prospectively bound Stage-A
   root. Import both PASS receipts with the binder's `--import-bindings` mode.
5. Run the four server equivalence acceptances and build the sealed acceptance
   bundle. Run `preflight_v023_c1c2_successor_stagec.py` against an absent root.
   It reconstructs the baseline adapter, repeats a deterministic masked-policy
   invariance check, authenticates the plan and closure, rejects circular
   bindings and forbidden topology/split tokens, and writes a preflight receipt
   plus sidecar.
6. Use `launch_stage_c_chunks.sh --barrier 100`, then 500, 1500, and 3000.
   Each invocation schedules only that interval; merge and independently verify
   the cumulative arm roots before releasing the next barrier.
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
local temporary bookkeeping. It prints only checkout preparation, closure
verification, and prospective binding:

```bash
./sync_launch_v023_c1c2_successor_stagec_server.sh --dry-run
```

The formal launcher first requires the seed checkout's commit/tree to match the
local bound commit/tree, synchronizes the manifest closure into a fresh copy,
then verifies the copied checkout's commit/tree again before binding. It never
overlays a seed checkout from a different tree. It runs the
prospective bind. It starts no Stage-B or Stage-C process; preparation and
launch are separate operator actions.

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

`launch_stage_c_chunks.sh` requires a current cumulative barrier, the Stage-A/B
supplement, runtime admission, and all-four-arm acceptance bundle. Capacity is
allocated under a shared lock as `(cores-2)-occupied Stage-C workers`, across
arms and sessions. Every worker attests OMP/OpenBLAS/MKL/NumExpr = 1. `--merge`
authenticates every chunk with the independent verifier before publishing a
cumulative arm merge; indexed file hashes, checkpoints, boundary states,
attempt dates, and chunk provenance are retained.

`run_v023_c1c2_successor_stage_c_chunks.py merge-four` refuses a missing arm.
It assembles episode records in the frozen `FULL2, DROP_C1, DROP_C2, BASELINE`
order, recomputes every cumulative pool with `math.fsum` over individual
episode totals, and emits four-arm checkpoints/rungs only from complete arm
coverage. No boundary below 3,000 emits a scientific disposition; early
BASELINE cannot continue above 3,000.

Before the first `merge-four`, run `build_stage_c_admission_mapping.py` once
per ladder with the bindings, Stage-A/B supplement, all-four-arm acceptance
bundle, runtime admission, and Stage-B root, then pass its write-once output to
every `merge-four` as `--admission-mapping`. This mapping records arm-policy
identity; it is not a scientific choice.

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
