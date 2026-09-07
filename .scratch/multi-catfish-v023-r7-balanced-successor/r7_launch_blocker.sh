#!/usr/bin/env bash
set -Eeuo pipefail

# The contract is DRAFT_PRE_OUTCOME / NO_LAUNCH.  This deliberate entrypoint
# prevents copied R6 server scripts from being mistaken for R7 authorization.
printf '%s\n' 'R7_NO_LAUNCH: successor scaffold is draft-only; use no physical stage.' >&2
exit 2
