#!/usr/bin/env bash
set -euo pipefail

learn_root=/home/sat/mcrl-catfish-oracle-gate-20260826
learn_python=/home/sat/mcrl-leo-handover/.venv/bin/python
learn_tle=/home/sat/mcrl-runtime/tle-frozen-20260820
learn_dir="$learn_root/.scratch/catfish-oracle-gate"
learn_output="$learn_dir/state-learnability-development-seeds-10-k10-v3.1.json"
learn_log="$learn_dir/state-learnability-development-seeds-10-k10-v3.1.log"
learn_verify="$learn_dir/state-learnability-development-seeds-10-k10-v3.1.verify.json"
learn_terminal="$learn_dir/state-learnability-development-seeds-10-k10-v3.1.terminal.txt"

for learn_target in "$learn_output" "$learn_log" "$learn_verify" "$learn_terminal"; do
    if [[ -e "$learn_target" ]]; then
        echo "refusing to overwrite existing receipt: $learn_target" >&2
        exit 73
    fi
done

exec > >(tee "$learn_terminal") 2>&1

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

cd "$learn_root"
echo "started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
"$learn_python" --version
verify_digest 8c2ac86ea93e6e4b2f433afdf8643d286aaaa909af15c01c31a4ef281663f7fd "$learn_dir/SPEC-v3-HELDOUT-STATE-LEARNABILITY.md"
verify_digest e31227e740f8663b3f55bc534827642a34c2e3920c90b2cf39af52a500f14d8e "$learn_dir/SPEC-v3.1-INDEPENDENT-AUDIT-AMENDMENT.md"
verify_digest feabafcf3f707446062296fc98a0e01ecc45ea534cf645d2ad4d4cb21cddb547 "$learn_dir/run_state_learnability_dataset.py"
verify_digest 6f8eca4c31a23d926d366e4dde971f9b0c25374de654087ddac1b10f1f882479 "$learn_dir/verify_state_learnability_dataset.py"
verify_digest f6edd7d2cb4acce33b72c3e78807baba7dc87c2a7f5e12910f5d666772b15076 "$learn_dir/test_state_learnability_gate.py"
verify_digest 7f26af5e56460ff297f16cd2de4bf208cbe0a51e7b94091529bd547e623b7b63 "$learn_dir/run_state_observable_gate.py"
verify_digest 2548f1c02dd9dc215dd3409e2d465f8c3cf85ecb3fd3525df4de3c63b68437b4 "$learn_dir/verify_state_observable_receipt.py"
verify_digest b50c396ea344d444e5db704aea05db613f9d6e29930524185d0f33f3cee338cb "$learn_dir/run_oracle_gate.py"
verify_digest cd88d8c5b17d163a957d8c2e56c2995080c4bb1636cbcc93fae13b234ba50658 "$learn_dir/state-only-confirmation-seeds-10-k10-v2.json"

"$learn_python" -m pytest -q \
    "$learn_dir/test_oracle_gate.py" \
    "$learn_dir/test_state_observable_gate.py" \
    "$learn_dir/test_state_learnability_gate.py" \
    "$learn_root/tests/test_w32_counterfactual_step.py" \
    "$learn_root/tests/test_w32_head_pivotality.py"
echo "focused_exit=0"

set +e
/usr/bin/time -v "$learn_python" "$learn_dir/run_state_learnability_dataset.py" \
    --partition development \
    --tle-root "$learn_tle" \
    --source-v2-receipt "$learn_dir/state-only-confirmation-seeds-10-k10-v2.json" \
    --output "$learn_output" 2>&1 | tee "$learn_log"
runner_exit=${PIPESTATUS[0]}
set -e
echo "runner_exit=$runner_exit"
if [[ "$runner_exit" -ne 0 ]]; then
    exit "$runner_exit"
fi

"$learn_python" "$learn_dir/verify_state_learnability_dataset.py" \
    --expect-partition development "$learn_output" | tee "$learn_verify"
echo "verify_exit=0"
sha256sum "$learn_output" "$learn_log" "$learn_verify"
echo "finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
