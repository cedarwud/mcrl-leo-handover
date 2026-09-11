#!/usr/bin/env bash
# Start the mutant re-run against the engineering-core commit as soon as the
# evaluator-eta0 lane frees a process slot (keeps <= 2 local compute processes).
set -u
while pgrep -f 'b1_lp_credit_rule\.py --kind evaluator --eta eta0' >/dev/null; do sleep 20; done
exec /home/u24/papers/mcrl-leo-handover/.scratch/b1-credit/run_mutants.sh \
     /home/u24/papers/mcrl-leo-handover/.scratch/b1-credit/mutants-63b02dc0.log
