#!/usr/bin/env bash
set -Eeuo pipefail

export V023_ACCELERATOR_LOG_ROOT=/home/sat/mcrl-v023-lcsrs-gate-20260906-r6/composition-middle-queue-r4-20260906
export PYTHON=/home/sat/mcrl-leo-handover/.venv/bin/python
exec bash /home/sat/mcrl-v023-lcsrs-gate-20260906-r6/.scratch/multi-catfish-v023-r6-composition-middle-queue/launch_v023_r6_composition_accelerator.sh \
  --controller-pid 1060152 \
  --memory-proof /home/sat/mcrl-v023-lcsrs-gate-20260906-r6/.scratch/multi-catfish-v023-r6-composition-middle-queue/memory-proof-r6-six-workers-20260906.json
