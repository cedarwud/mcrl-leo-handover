# C3-S diagnostic + V-E implementation report

Status: implementation and synthetic verification complete. No archive-backed unit,
merge, or scientific result was run or inspected.

## Implemented

### A. Same-state shadow replay

- `run_v023_c3s_shadow_replay.py` replays any coordinator declared by the variant
  config (including disabled V-E) with the imported matrix/v1 policy and the screen's
  TRAIN seeds, initial state, keyed fading field, and closed-loop transitions.
- Each decision records the pre-decision state digest, frozen BASE proposal, committed
  configuration, nominal bits/energy/served for both configurations, realised committed
  endpoints, and a discarded clone's realised same-state BASE endpoints.
- The live environment and RNG receive structural digests before and after the shadow
  evaluation. Replay additionally refuses unless initial state, action trace, committed
  step metrics, and the screen unit path/digest bound by the terminal receipt all match.
- Merge reads pooled `eta_BASE` from the completed screen terminal, records its SHA-256,
  and emits `SHADOW-REPLAY-DECOMPOSITION.json` and `.md`. Both contain exact Fraction
  accounting `(a) + (b) == total`, physical totals, nominal/realised paired gains at
  frozen `eta_ref`, separated price/model gaps, BASE-equality counts, world/lineage
  tables, and 30-step cumulative curves.
- The runner refuses unless every coordinator recorded by the completed panel is
  `NO_SUPPORT`. Outputs state that the decomposition is accounting, not causal proof.
- `build_shadow_launch_authority.py` creates the required exact-invocation, sealed
  authority for each detached unit/merge process.

### B. V-E expected scoring

- `variants_config.json` declares disabled optional arm `V-E`, `K=4`, the provenance,
  scenario domain template, seed rule, channel distribution, and unchanged realised
  execution. The original config projection remains digest-bound as
  `1aec5e842244913a97760a139d2e7d382c20b03156b5234a752224ec8b06b551`.
- Scenario seeds are derived only from `C3S_VE/scenario/{1..4}` by the repository
  SHA-256/int63 rule: `6018382882959041944`, `817005370450305563`,
  `1936779116122867599`, and `908075962035052284`.
- V-E retains the exact LITE catalog and deterministic nominal service guard. It ranks
  eligible candidates by the exact mean of `B_k - eta_ref E_k` over four simulator
  scenarios using the configured Rician K-factor and elevation-dependent shadowing.
- Each scenario uses a detached path-keyed field. Event/step/NORAD/user draws therefore
  remain common across candidates even when candidate satellite sets differ. The world
  keyed field and realised committed evaluation are unchanged.
- `--enable-ve` is required to extend the default nine arms to ten. The flag, ten-arm
  panel, scenario declaration, and seeds are authority-bound. Without the flag, the
  default panel serialization and execution order are unchanged.
- The unsealed 86-line `ADDENDUM-B-VE-EXPECTED-SCORING-DRAFT-2026-09-08.md` records the
  unchanged kill rule, multiplicity/exposure obligations, costs, and reporting list.

## Verification

Command:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest \
  .scratch/multi-catfish-v023-c3s-screen/test_c3s_screen.py \
  .scratch/multi-catfish-v023-c3s-variants/test_variant_matrix.py \
  .scratch/multi-catfish-v023-c3s-variants/test_variant_ve.py \
  .scratch/multi-catfish-v023-c3s-variants/test_shadow_replay.py
```

Pytest summary line (verbatim):

```text
57 passed in 1.79s
```

`py_compile` and `git diff --check` also passed. Default and opt-in dry runs reported,
respectively, nine arms and ten arms. The sealed contract and its SHA-256 sidecars remain
mode 0444 and were not edited.

## Estimates

Commands:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/multi-catfish-v023-c3s-variants/run_v023_c3s_shadow_replay.py \
  --estimate --estimate-units 12 --arm LITE

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/multi-catfish-v023-c3s-variants/run_v023_c3s_variants.py \
  --estimate --estimate-units 12 --enable-ve
```

- LITE shadow replay: 12 policy episodes plus exactly 360 extra physical evaluations;
  projected policy replay `1.4260229474047532` worker-hours, extra shadow work
  `0.004755496959459162`, total `1.4307784443642124` worker-hours.
- V-E: projected scenario evaluations `2159052/5` (431,810.4) plus 360 BASE nominal
  evaluations for origin membership, total `2160852/5` (432,170.4) physics evaluations;
  projected V-E work `5.708847286578472` worker-hours. The complete opt-in ten-arm
  estimate sums to `17.59237184828475` worker-hours. These are declared planning
  estimates from the existing v1 timing basis, not measured runtime promises.

## Exact unit launch pattern

The following enumerates all 12 units. Set the three controller-owned absolute paths
before use. `PREFLIGHT` must be sealed; `SCREEN_RUN` must be the completed all-NO_SUPPORT
matrix root; output and authority roots must be new and inside this variant directory.

```bash
VARIANT_DIR=/home/sat/mcrl-v023-codex-ws-c3s-diag/.scratch/multi-catfish-v023-c3s-variants
PYTHON=/home/sat/mcrl-leo-handover/.venv/bin/python
PREFLIGHT=/CONTROLLER/ABSOLUTE/C3S-VARIANTS-PREFLIGHT-MANIFEST.json
SCREEN_RUN=/CONTROLLER/ABSOLUTE/COMPLETED-VARIANT-SCREEN-RUN
SHADOW_OUTPUT="$VARIANT_DIR/shadow-replay-output-lite"
SHADOW_AUTH="$VARIANT_DIR/shadow-authorities-lite"
SHADOW_LOGS="$VARIANT_DIR/shadow-logs-lite"
mkdir -p "$SHADOW_AUTH" "$SHADOW_LOGS"
UNITS=(
  8464287092499831892:2026092101 8464287092499831892:2026092102 8464287092499831892:2026092103
  7305539127129390835:2026092101 7305539127129390835:2026092102 7305539127129390835:2026092103
  7691130988233444596:2026092101 7691130988233444596:2026092102 7691130988233444596:2026092103
  5887834234954284271:2026092101 5887834234954284271:2026092102 5887834234954284271:2026092103
)
for UNIT in "${UNITS[@]}"; do
  SLUG=${UNIT/:/-}
  AUTHORITY="$SHADOW_AUTH/$SLUG.json"
  LAUNCH=(--preflight-manifest "$PREFLIGHT" --launch-authority "$AUTHORITY"
          --screen-run "$SCREEN_RUN" --output "$SHADOW_OUTPUT" --horizon 30
          --arm LITE --unit "$UNIT")
  env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
    "$PYTHON" "$VARIANT_DIR/build_shadow_launch_authority.py" \
    --preflight-manifest "$PREFLIGHT" --screen-run "$SCREEN_RUN" \
    --output-root "$SHADOW_OUTPUT" --arm LITE --horizon 30 --output "$AUTHORITY" \
    --launch-arguments "${LAUNCH[@]}"
  nohup setsid env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 "$PYTHON" "$VARIANT_DIR/run_v023_c3s_shadow_replay.py" \
    "${LAUNCH[@]}" >"$SHADOW_LOGS/$SLUG.log" 2>&1 </dev/null &
done
```

For V-E, use the same `UNITS` array with a separately frozen preflight and new output
root. Each authority must bind `--enable-ve` exactly:

```bash
PREFLIGHT=/CONTROLLER/ABSOLUTE/VE-PREFLIGHT-BUILT-BEFORE-RESULT-EXPOSURE.json
VE_OUTPUT="$VARIANT_DIR/run-output-ve"
VE_AUTH="$VARIANT_DIR/ve-authorities"
VE_LOGS="$VARIANT_DIR/ve-logs"
CONTRACT="$VARIANT_DIR/V023-C3S-VARIANT-MATRIX-KILL-SCREEN-CONTRACT-2026-09-08.md"
mkdir -p "$VE_AUTH" "$VE_LOGS"
for UNIT in "${UNITS[@]}"; do
  SLUG=${UNIT/:/-}
  AUTHORITY="$VE_AUTH/$SLUG.json"
  LAUNCH=(--preflight-manifest "$PREFLIGHT" --launch-authority "$AUTHORITY"
          --output "$VE_OUTPUT" --horizon 30 --unit "$UNIT" --enable-ve)
  env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
    "$PYTHON" "$VARIANT_DIR/build_variant_launch_authority.py" \
    --preflight-manifest "$PREFLIGHT" --contract "$CONTRACT" \
    --output-root "$VE_OUTPUT" --output "$AUTHORITY" \
    --launch-arguments "${LAUNCH[@]}"
  nohup setsid env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 "$PYTHON" "$VARIANT_DIR/run_v023_c3s_variants.py" \
    "${LAUNCH[@]}" >"$VE_LOGS/$SLUG.log" 2>&1 </dev/null &
done
```

Merge uses the same authority builders with the unit flag replaced by `--merge`, followed
by the corresponding runner invocation. Shadow merge writes the required JSON and Markdown
filenames at `SHADOW_OUTPUT`.

## Open questions / controller actions

- Addendum B is deliberately unsealed. Before any V-E authority is built, the controller
  must record its declaration timestamp, authority timestamp, and the timestamp/identity
  of any nine-arm result exposure. If exposure came first, V-E must be disclosed as a
  separately timestamped second development screen.
- The controller must supply and seal the updated preflight/launch authorities and choose
  new output roots. No authority or heavy process was created here.
- Shadow replay is intentionally unavailable unless the completed terminal records every
  coordinator as NO_SUPPORT. There is no fallback approximation if replay actions,
  endpoints, initial state, or receipt bindings differ from the archived screen.
