#!/usr/bin/env bash
set -Eeuo pipefail

# Wait for the one authorized R4 replay, independently reopen its source
# artifact, and only then invoke the already sealed full-R4 sync/launcher.
# This is a one-shot process handoff, not the retired conversation-capacity
# monitor and not a scientific rescue ladder.

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
exec >"${repo_root}/.scratch/multi-catfish-v023-c3-observability/auto-promote-r4-20260906-r1.log" 2>&1
server_host="sat"
replay_session="mcrl-v023-lcsrs-debug-20260906-r4-1706"
replay_root="/home/sat/mcrl-v023-lcsrs-debug-20260906-r4-1706"
replay_source="${replay_root}/replay/world-2026121706.json"
remote_python="/home/sat/mcrl-leo-handover/.venv/bin/python"
remote_validator="${replay_root}/.scratch/multi-catfish-v023-c3-observability/verify_v023_r4_world_1706_replay.py"
full_root="/home/sat/mcrl-v023-lcsrs-gate-20260906-r4"
full_session="mcrl-v023-lcsrs-gate-20260906-r4"
launcher="${repo_root}/.scratch/multi-catfish-v023-c3-observability/sync_launch_v023_lcsrs_gate_server.sh"

while ssh "${server_host}" "tmux has-session -t '${replay_session}' 2>/dev/null"; do
  sleep 30
done

ssh "${server_host}" "test -f '${replay_source}' && test ! -L '${replay_source}'"
ssh "${server_host}" \
  "cd '${replay_root}' && PYTHONPATH=src '${remote_python}' '${remote_validator}' '${replay_source}'"
ssh "${server_host}" "test ! -e '${full_root}' && test ! -L '${full_root}'"
ssh "${server_host}" "! tmux has-session -t '${full_session}' 2>/dev/null"

cd "${repo_root}"
V023_SERVER_HOST="${server_host}" \
V023_SERVER_ROOT="${full_root}" \
V023_TMUX_SESSION="${full_session}" \
bash "${launcher}"

printf 'AUTO_PROMOTION_PASS full_session=%s full_root=%s\n' \
  "${full_session}" "${full_root}"
