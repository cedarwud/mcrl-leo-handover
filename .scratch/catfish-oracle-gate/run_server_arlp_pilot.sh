#!/usr/bin/env bash
set -euo pipefail

gate_root=/home/sat/mcrl-catfish-oracle-gate-20260826
gate_python=/home/sat/mcrl-leo-handover/.venv/bin/python
gate_tle=/home/sat/mcrl-runtime/tle-frozen-20260820
gate_dir="$gate_root/.scratch/catfish-oracle-gate"
gate_output="$gate_dir/arlp-shadow-pilot-seed-2026082401-k2-v4.json"
gate_log="$gate_dir/arlp-shadow-pilot-seed-2026082401-k2-v4.log"
gate_verify="$gate_dir/arlp-shadow-pilot-seed-2026082401-k2-v4.verify.json"
gate_terminal="$gate_dir/arlp-shadow-pilot-seed-2026082401-k2-v4.terminal.txt"

for gate_target in "$gate_output" "$gate_log" "$gate_verify" "$gate_terminal"; do
    if [[ -e "$gate_target" ]]; then
        echo "refusing to overwrite existing receipt: $gate_target" >&2
        exit 73
    fi
done

exec > >(tee "$gate_terminal") 2>&1

verify_digest() {
    local expected_digest=$1
    local target_path=$2
    local actual_digest
    actual_digest=$(sha256sum "$target_path" | cut -d ' ' -f 1)
    if [[ "$actual_digest" != "$expected_digest" ]]; then
        echo "digest mismatch: $target_path" >&2
        echo "expected=$expected_digest actual=$actual_digest" >&2
        exit 74
    fi
    echo "digest_ok=$actual_digest path=$target_path"
}

cd "$gate_root"
echo "started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
"$gate_python" --version
verify_digest a5400b970812eaf2a8489f5ff70e083e78a28eef6cc78794ae3a2e6ffe6f4f2d "$gate_dir/SPEC-v4-ARLP-SHADOW.md"
verify_digest 35219a1353c44644d0f1acf7e78f3277497aa447fab7f3be01b3383779e2a82e "$gate_dir/run_arlp_shadow_gate.py"
verify_digest 0b2dc162bf94cdaf85a69d583c64247e5eafb014936ac63fe7f48befd55248a4 "$gate_dir/verify_arlp_shadow_receipt.py"
verify_digest 83f925a17902b42f8799708b2fca78d795c530db7b4f5cb7600c0bf8766729a3 "$gate_dir/test_arlp_shadow_gate.py"
verify_digest b50c396ea344d444e5db704aea05db613f9d6e29930524185d0f33f3cee338cb "$gate_dir/run_oracle_gate.py"

"$gate_python" -m pytest -q \
    "$gate_dir/test_oracle_gate.py" \
    "$gate_dir/test_state_observable_gate.py" \
    "$gate_dir/test_state_learnability_gate.py" \
    "$gate_dir/test_arlp_shadow_gate.py" \
    "$gate_root/tests/test_w32_counterfactual_step.py" \
    "$gate_root/tests/test_w32_head_pivotality.py"
echo "focused_exit=0"

set +e
/usr/bin/time -v "$gate_python" "$gate_dir/run_arlp_shadow_gate.py" \
    --stage pilot \
    --tle-root "$gate_tle" \
    --output "$gate_output" 2>&1 | tee "$gate_log"
runner_exit=${PIPESTATUS[0]}
set -e
echo "runner_exit=$runner_exit"
if [[ "$runner_exit" -ne 0 ]]; then
    exit "$runner_exit"
fi

"$gate_python" "$gate_dir/verify_arlp_shadow_receipt.py" \
    "$gate_output" --expect-stage pilot | tee "$gate_verify"
echo "verify_exit=0"
sha256sum "$gate_output" "$gate_log" "$gate_verify"
echo "finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
