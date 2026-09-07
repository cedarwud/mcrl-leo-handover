#!/usr/bin/env bash
set -euo pipefail

gate_root=/home/sat/mcrl-catfish-oracle-gate-20260826
gate_python=/home/sat/mcrl-leo-handover/.venv/bin/python
gate_tle=/home/sat/mcrl-runtime/tle-frozen-20260820
gate_dir="$gate_root/.scratch/catfish-oracle-gate"
gate_output="$gate_dir/state-only-confirmation-seeds-10-k10-v2.json"
gate_log="$gate_dir/state-only-confirmation-seeds-10-k10-v2.log"
gate_verify="$gate_dir/state-only-confirmation-seeds-10-k10-v2.verify.json"
gate_terminal="$gate_dir/state-only-confirmation-seeds-10-k10-v2.terminal.txt"

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
echo "gate_root=$gate_root"
echo "python=$gate_python"
"$gate_python" --version

verify_digest 9a0a70dac4f8f892a29a5162692b0464406899d7deb6b8ea6327a17ac369a760 "$gate_dir/SPEC-v2-STATE-ONLY.md"
verify_digest 7f26af5e56460ff297f16cd2de4bf208cbe0a51e7b94091529bd547e623b7b63 "$gate_dir/run_state_observable_gate.py"
verify_digest 17462e47d3a09d2345203221802b78ab44af73b1469f4750af768e1624a76ba6 "$gate_dir/test_state_observable_gate.py"
verify_digest c705b709d3189dd948bb8d317f0dae1be63917f782ee56c030694bfd7b5ad88a "$gate_dir/verify_state_observable_receipt.py"
verify_digest b50c396ea344d444e5db704aea05db613f9d6e29930524185d0f33f3cee338cb "$gate_dir/run_oracle_gate.py"
verify_digest e0395bd7735649074fb4993e4a2ef4c6e42f9639b831cb8b4d88e7fef8de835b "$gate_dir/SPEC-v1-FROZEN-PILOT.md"
verify_digest 9435fd70a65cd26bd529656e8607c1847e75c8054d882b073d0c93c250b9f7ad "$gate_dir/test_oracle_gate.py"
verify_digest 45ea3251b3728112c85b4177fecc502870ce44c816033a271f66ba74bf0e3789 "$gate_root/tests/test_w32_counterfactual_step.py"
verify_digest 09656ed58978592e361edd9947dc5fe313fcc20c28a3c2773b7d0f54a4f737c8 "$gate_root/tests/test_w32_head_pivotality.py"

"$gate_python" -m pytest -q \
    "$gate_dir/test_oracle_gate.py" \
    "$gate_dir/test_state_observable_gate.py" \
    "$gate_root/tests/test_w32_counterfactual_step.py" \
    "$gate_root/tests/test_w32_head_pivotality.py"
echo "focused_exit=0"

set +e
/usr/bin/time -v "$gate_python" "$gate_dir/run_state_observable_gate.py" \
    --tle-root "$gate_tle" \
    --focal-users-per-step 10 \
    --seeds \
        2026082401 2026082402 2026082403 2026082404 2026082405 \
        2026082406 2026082407 2026082408 2026082409 2026082410 \
    --output "$gate_output" 2>&1 | tee "$gate_log"
runner_exit=${PIPESTATUS[0]}
set -e
echo "runner_exit=$runner_exit"
if [[ "$runner_exit" -ne 0 ]]; then
    exit "$runner_exit"
fi

"$gate_python" "$gate_dir/verify_state_observable_receipt.py" \
    --expect-confirmation "$gate_output" | tee "$gate_verify"
echo "verify_exit=0"
sha256sum "$gate_output" "$gate_log" "$gate_verify"
echo "finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
