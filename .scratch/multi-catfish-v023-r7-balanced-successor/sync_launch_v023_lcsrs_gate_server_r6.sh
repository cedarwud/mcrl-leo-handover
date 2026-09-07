#!/usr/bin/env bash
set -Eeuo pipefail

# Retained filename only so stale callers fail closed inside the isolated R7
# package. The draft successor has no sync, SSH, tmux, or launch authority.
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
exec bash "${script_dir}/r7_launch_blocker.sh"
