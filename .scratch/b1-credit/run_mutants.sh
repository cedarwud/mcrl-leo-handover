#!/usr/bin/env bash
# B1-CREDIT: each named mutant against the test it must turn red (run from the b1 worktree).
# Records, per run: mutant | selector | first failure line (file:line: error) | pytest summary.
set -u
cd /home/u24/papers/mcrl-leo-handover-b1
export MCRL_TLE_ROOT=/home/u24/mcrl-runtime/tle-pinned-427e6a91 OMP_NUM_THREADS=1
PY=/home/u24/papers/mcrl-leo-handover/.venv/bin/python
LOG=${1:-/home/u24/papers/mcrl-leo-handover/.scratch/b1-credit/mutants.log}
dirty=$(git status --porcelain -- src tests | wc -l)
echo "# mutant run $(date -Is) HEAD $(git rev-parse --short HEAD) dirty-files-in-src/tests=$dirty" > "$LOG"
run() {  # mutant  test-selector
  out=$(CREDIT_MUTANT="$1" timeout 1800 nice -n 16 "$PY" -m pytest tests/test_cf_credit.py -q --tb=line -k "$2" 2>&1)
  rc=$?
  first=$(printf '%s\n' "$out" | grep -m1 -E "^/.*: [A-Za-z]*(Error|Exception)" || true)
  summary=$(printf '%s\n' "$out" | grep -E "^[0-9]+ (passed|failed)|[0-9]+ failed|[0-9]+ passed" | tail -1)
  verdict=RED; [ "$rc" = 0 ] && verdict=GREEN
  echo "${1:-<baseline>} | -k $2 | $verdict (exit $rc) | ${summary:-no summary} | ${first:-no failure line}" >> "$LOG"
}
run "" "cf3 or trajectory or alone_on_beam or lighting_price_equals or outage_is_never or not_additive or without_u or pool_credit or resume"
run default_credit_difference equal_share_is_bit_identical
run e_share_over_served equal_share_is_bit_identical
run cf_live_rng trajectory_bit_identical
run cf_commits_segments trajectory_bit_identical
run ed_supply_only alone_on_beam
run ed_per_link_power alone_on_beam
run lp_no_baseband lighting_price_equals
run lp_tie_as_max lighting_price_equals
run no_outage_charge outage_is_never
run bd_own_bits not_additive
run physics_bandwidth_not_shared without_u
run trainer_ignores_pool_credit pool_credit
run resume_requires_flag resume
echo "# done $(date -Is)" >> "$LOG"
