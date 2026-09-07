#!/usr/bin/env bash
set -Eeuo pipefail

# A one-world launcher boundary.  Dry-run is the default and makes no network,
# TLE, simulator, or training call.  A real launch can proceed only after the
# required real inputs and the fail-closed bindings below are available.

launch=0
tle_root=""
d40_checkpoint=""
while (($#)); do
  case "$1" in
    --launch) launch=1; shift ;;
    --tle-root)
      (($# >= 2)) || { printf '%s\n' 'E2E_VERTICAL_SLICE_ERROR: --tle-root needs a path' >&2; exit 2; }
      tle_root=$2; shift 2 ;;
    --d40-checkpoint)
      (($# >= 2)) || { printf '%s\n' 'E2E_VERTICAL_SLICE_ERROR: --d40-checkpoint needs a path' >&2; exit 2; }
      d40_checkpoint=$2; shift 2 ;;
    --help|-h)
      printf '%s\n' 'Usage: run_v023_e2e_vertical_slice_server.sh [--launch --tle-root PATH --d40-checkpoint PATH]'
      exit 0 ;;
    *) printf 'E2E_VERTICAL_SLICE_ERROR: unknown argument %s\n' "$1" >&2; exit 2 ;;
  esac
done

if (( ! launch )); then
  printf '%s\n' 'DRY_RUN: one TRAIN world, 100 users, 10 steps, five arms; no TLE or simulator opened.'
  printf '%s\n' 'STATUS: PLUMBING_ONLY_NOT_GATE_NOT_EFFICACY'
  exit 0
fi

[[ -n "$tle_root" && -d "$tle_root" && ! -L "$tle_root" ]] || { printf '%s\n' 'E2E_VERTICAL_SLICE_ERROR: --launch requires a real non-symlink TRAIN TLE root' >&2; exit 2; }
[[ -n "$d40_checkpoint" && -f "$d40_checkpoint" && ! -L "$d40_checkpoint" ]] || { printf '%s\n' 'E2E_VERTICAL_SLICE_ERROR: --launch requires the authenticated non-symlink d40 checkpoint' >&2; exit 2; }
expected_d40_sha256='d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc'
actual_d40_sha256=$(sha256sum -- "$d40_checkpoint")
[[ "${actual_d40_sha256%% *}" == "$expected_d40_sha256" ]] || { printf '%s\n' 'E2E_VERTICAL_SLICE_ERROR: --d40-checkpoint bytes are not the authenticated current d40 artifact' >&2; exit 2; }
printf '%s\n' 'E2E_VERTICAL_SLICE_BLOCKED: authenticated TLE/d40 supplied, but d40 is V0.20 split q1/q2 bytes rather than the action-shared payload required by the current LC-SRS loader; no world opened.' >&2
exit 2
