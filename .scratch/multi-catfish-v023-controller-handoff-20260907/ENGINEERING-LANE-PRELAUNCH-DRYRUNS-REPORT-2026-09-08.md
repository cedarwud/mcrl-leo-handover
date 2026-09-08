TASK_EXIT=BLOCKED

The clone was left unchanged. It is nine commits behind the reviewed tree, and the Stage-A dry-run is blocked by missing/drifted frozen files.

## Clone state

```console
$ git -C /home/sat/mcrl-leo-handover-stagec rev-parse HEAD
10791b539a994fed5bf3c8f4c763197db70f6a32

$ git -C /home/sat/mcrl-leo-handover rev-parse review/stagec-r3
704878e3eee05a60e7ab14f4ccc831b431d93641

$ git -C /home/sat/mcrl-leo-handover rev-list --left-right --count \
    10791b539a994fed5bf3c8f4c763197db70f6a32...704878e3eee05a60e7ab14f4ccc831b431d93641
0	9

$ test -d .git
# exit 0

$ git status --short --branch
## stagec/attempt3
```

No pull, fetch, edit, or repository write was performed.

## 1. Stage-A local-host dry-run

Help confirms the flag:

```console
$ bash .scratch/multi-catfish-v023-c1c2-successor-launch/sync_launch_v023_c1c2_successor_server.sh --help
Usage: sync_launch_v023_c1c2_successor_server.sh [--dry-run]
       sync_launch_v023_c1c2_successor_server.sh --check-diagnostic-receipt PATH
# exit 0
```

Exact invocation:

```console
$ env \
  V023_SUCCESSOR_SERVER_HOST=local \
  V023_SUCCESSOR_LOCAL_PYTHON=/home/sat/mcrl-leo-handover/.venv/bin/python \
  PYTHONPATH=/home/sat/mcrl-leo-handover-stagec/src \
  PYTHONDONTWRITEBYTECODE=1 \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  bash .scratch/multi-catfish-v023-c1c2-successor-launch/sync_launch_v023_c1c2_successor_server.sh --dry-run

SUCCESSOR_EXECUTION_BINDINGS_FAIL: frozen file drifted: /home/sat/mcrl-leo-handover-stagec/.scratch/multi-catfish-v023-c1c2-successor-launch/V023-C1C2-SUCCESSOR-LEARNER-MANIFEST.json
SUCCESSOR_LAUNCH_REFUSED: execution bindings are not current
# exit 2
```

The named learner manifest is actually absent:

```console
$ test -e .scratch/multi-catfish-v023-c1c2-successor-launch/V023-C1C2-SUCCESSOR-LEARNER-MANIFEST.json
# exit 1
```

The second local gate also fails independently:

```console
$ /home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/multi-catfish-v023-c1c2-successor-launch/build_v023_c1c2_successor_launch_manifest.py \
  --repo /home/sat/mcrl-leo-handover-stagec --check

SUCCESSOR_LAUNCH_MANIFEST_FAIL: frozen file drifted: /home/sat/mcrl-leo-handover-stagec/.scratch/multi-catfish-v023-c1c2-successor-launch/V023-C1C2-SUCCESSOR-LAUNCH-MANIFEST.json
# exit 3
```

Consequently, the wrapper exits before printing any planned phases. Runtime confirmation that every server-side phase prints `LOCAL bash -c …` was therefore impossible.

Source inspection establishes what it would print after the gates pass:

- Server-side phases use `LOCAL bash -c …`.
- The two local integrity gates use `LOCAL <python> …`, not `LOCAL bash -c …`.
- Transport uses an `RSYNC (cd … && rsync …)` line, not `LOCAL bash -c …`.
- Local-host transport ends in the plain local checkout path, with no `host:` target.
- No local-host execution branch invokes `ssh`.

Resolved paths:

```text
transported checkout:
  /home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1-checkout

formal output root:
  /home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1

diagnostic output:
  /home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1-checkout/successor-one-epoch-diagnostic-scratch

tmux session:
  mcrl-v023-c1c2-successor-100e-r1
```

Post-checks:

```console
$ test ! -e /home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1
# exit 0

$ tmux has-session -t mcrl-v023-c1c2-successor-100e-r1
# exit 1: absent
```

All commands the wrapper intends to invoke exist. Their actual help accepts the flags used by the wrapper:

- Binder: `--repo`, `--target-root`, `--check`, `--verify-learner-manifest-only`.
- Manifest builder: `--repo`, `--check`, `--paths`.
- Preflight: `--repo`, `--bindings`, `--manifest`, `--provider-config`, `--model-config`, `--declaration`, `--output-root`, `--receipt`, `--target-root`, `--formal`, diagnostic receipt flags.
- Diagnostic: `--repo`, `--provider-config`, `--model-config`, `--output-root`.
- Formal runner: `--output-root`, `--epochs`, `--provider-factory`, `--model-config-json`, `--train-seed`, `--preflight-receipt`, `--execute`.
- Verifier: `--repo`, `--output-root`, `--provider-config`, `--model-config`, `--preflight-receipt`, `--write`.

## 2. Engineering Stage-B/C chain

The checked-out spec contains no Stage-A artifact declaration, so no `--artifact` override was applicable. Its sole BLOCKED step is the deliberately disabled real-world step, not a missing Stage-A consumer.

```console
$ env \
  V023_SUCCESSOR_LOCAL_PYTHON=/home/sat/mcrl-leo-handover/.venv/bin/python \
  PYTHONPATH=/home/sat/mcrl-leo-handover-stagec/src \
  PYTHONDONTWRITEBYTECODE=1 \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/multi-catfish-v023-engineering-lane/offline_realartifact_dryrun.py \
  --spec .scratch/multi-catfish-v023-engineering-lane/specs/successor_stage_bc_chain.json \
  --output /home/sat/mcrl-v023-prelaunch-dryruns-20260908/stage-bc-20260908T101924Z

WORLD_PLAN_OK plan_sha256=866d28e05b04a361041f829e424a2417f49987239b7771ee94f43022d35e01bb
DRYRUN_successor_stage_bc_BLOCKED
# exit 3
```

Per-step results:

| Step | Status | Wall time |
|---|---:|---:|
| `fresh_exports` | PASS | 1.327660117 s |
| `load_exports_both_paths` | PASS | 0.108389246 s |
| `baseline_admission` | PASS | 0.012881269 s |
| `world_plan_build_check` | PASS | 0.299608916 s |
| `simulate_off_deployment` | PASS | 0.000128245 s |
| `receipt_cadence_resume` | PASS | 0.825135558 s |
| `optional_real_world` | BLOCKED | 0.000029567 s |

BLOCKED reason:

```text
StepBlocked: spec flag run_real_world is False; requires True
```

Overall report:

```text
verdict=BLOCKED
passed=6
blocked=1
failed=0
wall_s=3.1011368189938366
scientific_output=false
```

All ten input-integrity comparisons report `PASS`. Full generated report: [dryrun-report.json](/home/sat/mcrl-v023-prelaunch-dryruns-20260908/stage-bc-20260908T101924Z/dryrun-report.json).

## 3. Stage-C bundle sanity

Manifest check:

```console
$ /home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/multi-catfish-v023-c1c2-successor-stagec-launch/build_v023_c1c2_successor_stagec_manifest.py \
  --check

STAGEC_CODE_MANIFEST_CURRENT entries=277 sha256=e290ef5059bd765a90e813c161fc4b97376aefd33d74ec3c20f23653454f7a67
# exit 0
```

Help results and skeleton comparison:

| Program | Help exit | Skeleton flags |
|---|---:|---|
| `bind_v023_c1c2_successor_stagec_freeze.py` | 0 | Shown step-1 flags accepted |
| `prepare_stage_c_runtime_admission.py` | 0 | Match |
| `accept_stage_c_chunk_equivalence.py` | 0 | Match |
| `build_stage_c_admission_mapping.py` | 0 | Match |
| `launch_stage_c_chunks.sh` | **2** | Usage flags match, but `--help` is not implemented |
| `run_v023_c1c2_successor_stage_c_chunks.py` | 0 | Top-level and `merge-four` flags match |
| `verify_v023_c1c2_successor_stagec.py` | 0 | Match |
| `seal_stage_c_declined_continuation.py` | 0 | Match |

Actual `merge-four` required flags are:

```text
--bindings
--arm-roots ROOT ROOT ROOT ROOT
--admission-mapping
--admission-supplement
--acceptance-bundle
--output
```

Optional continuation flags are:

```text
--continuation-authority
--owner-notification-marker
--continuation-activity
--resume-continuation
```

Actual launcher usage output:

```text
usage: …/launch_stage_c_chunks.sh --bindings PATH --admission-supplement PATH --acceptance-bundle PATH --runtime-admission PATH --arm ARM --barrier 100|500|1500|3000|6000|9000 --chunks-root DIR --arm-merge-root DIR [--previous-arm-merge DIR] [--continuation-authority JSON --owner-notification-marker JSON] [--max-workers N] [--merge [--four-arm-roots FULL2 DROP_C1 DROP_C2 BASELINE --admission-mapping JSON --final-output DIR [--resume-continuation]]]
```

Two operational contract mismatches were also found:

- The skeleton defines `PY`, but the shell launcher ignores it. It reads `V023_STAGEC_PYTHON`, otherwise defaulting to `/home/sat/mcrl-leo-handover-stagec/.venv/bin/python`. That default is not executable in this clone.
- The launcher unconditionally assigns `TMPDIR="$repo/.tmp"` and runs `mkdir -p "$TMPDIR"` after argument validation. A real launcher invocation therefore writes into the repository despite an externally supplied `TMPDIR`.

## Proposed skeleton corrections

Do not apply automatically:

```diff
--- COMMAND-SKELETON.md
+++ COMMAND-SKELETON.md
@@ environment
 PY=/home/sat/mcrl-leo-handover/.venv/bin/python
+export V023_STAGEC_PYTHON="$PY"

@@ BINDINGS
-BINDINGS=".../V023-C1C2-SUCCESSOR-STAGEC-EXECUTION-BINDINGS.json" # stage-C freeze (bind --write in this clone if absent)
+BINDINGS=".../V023-C1C2-SUCCESSOR-STAGEC-EXECUTION-BINDINGS.json" # stage-C binder writes by default; it has no --write flag

@@ initial freeze, if BINDINGS is absent
+$PY $BUNDLE/bind_v023_c1c2_successor_stagec_freeze.py \
+  --stage-a-output "$STAGE_A" \
+  --plan-output "$RUN_ROOT/V023-C1C2-SUCCESSOR-9000-WORLD-PLAN.json" \
+  --stage-b-output "$STAGE_B" \
+  --stage-c-output "$STAGE_C"

@@ launcher help verification
-$BUNDLE/launch_stage_c_chunks.sh --help
+$BUNDLE/launch_stage_c_chunks.sh --help  # prints usage but exits 2 in HEAD 10791b5; inspect usage/source until launcher help is fixed

@@ launcher environment note
+The launcher requires V023_STAGEC_PYTHON; assigning shell variable PY alone does not select the controller Python.
+The current launcher also overrides TMPDIR to "$repo/.tmp" and creates it, so it is incompatible with a repository-read-only launch host.

@@ 9000 launcher merge
+At barrier 9000, --merge additionally requires:
+  --four-arm-roots FULL2_ROOT DROP_C1_ROOT DROP_C2_ROOT BASELINE_ROOT
+  --admission-mapping "$RUN_ROOT/stage-c-admission-mapping.json"
+  --final-output "$STAGE_C"
```

The explicit flag mismatch is the documented Stage-C binder `--write`, which does not exist. The remaining displayed commands use accepted flags, subject to the launcher help exit and environment/write-contract issues above.

I applied the strict fixed-write-boundary behavior from the `keep-scope-small` skill: only the designated dry-run root was created, and the repository remained untouched.