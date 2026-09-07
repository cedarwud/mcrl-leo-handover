#!/usr/bin/env bash
set -Eeuo pipefail

# Fetch/finalization is disabled while the successor remains NO_LAUNCH; there
# can be no authorized remote result to poll or copy in this revision.
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
exec bash "${script_dir}/r7_launch_blocker.sh"
