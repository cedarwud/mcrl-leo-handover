#!/usr/bin/env bash
set -euo pipefail

learn_root=/home/sat/mcrl-catfish-oracle-gate-20260826
learn_python=/home/sat/mcrl-leo-handover/.venv/bin/python
learn_tle=/home/sat/mcrl-runtime/tle-frozen-20260820
learn_dir="$learn_root/.scratch/catfish-oracle-gate"
learn_development="$learn_dir/state-learnability-development-seeds-10-k10-v3.1.json"
learn_heldout="$learn_dir/state-learnability-heldout-seeds-10-k10-v3.1.json"
learn_collect_log="$learn_dir/state-learnability-heldout-seeds-10-k10-v3.1.collect.log"
learn_dataset_verify="$learn_dir/state-learnability-heldout-seeds-10-k10-v3.1.verify.json"
learn_result="$learn_dir/state-learnability-result-v3.1.json"
learn_fit_log="$learn_dir/state-learnability-result-v3.1.fit.log"
learn_result_verify="$learn_dir/state-learnability-result-v3.1.verify.json"
learn_terminal="$learn_dir/state-learnability-heldout-v3.1.terminal.txt"

for learn_target in \
    "$learn_heldout" \
    "$learn_collect_log" \
    "$learn_dataset_verify" \
    "$learn_result" \
    "$learn_fit_log" \
    "$learn_result_verify" \
    "$learn_terminal"; do
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
verify_digest 9f471f25794689d40ffb091a8e246aa78d028d28e9dabe6a0326bf0bac16a013 "$learn_dir/run_state_learnability_gate.py"
verify_digest ead743f76eb3ba837c87390f2a9ab9676415778c5a2c8aad22edcc595abccd4c "$learn_dir/verify_state_learnability_result.py"
verify_digest dd206c5c5f19c82b897867076f3daec25df93bf8dd5b284bc13725de9b76de48 "$learn_dir/test_state_learnability_gate.py"
verify_digest 7f26af5e56460ff297f16cd2de4bf208cbe0a51e7b94091529bd547e623b7b63 "$learn_dir/run_state_observable_gate.py"
verify_digest 2548f1c02dd9dc215dd3409e2d465f8c3cf85ecb3fd3525df4de3c63b68437b4 "$learn_dir/verify_state_observable_receipt.py"
verify_digest b50c396ea344d444e5db704aea05db613f9d6e29930524185d0f33f3cee338cb "$learn_dir/run_oracle_gate.py"
verify_digest 27f62f2704f00d6fd53bd76ed3f6d1e4c747e5afd28b577ba6d265c179ce0693 "$learn_development"
verify_digest cd88d8c5b17d163a957d8c2e56c2995080c4bb1636cbcc93fae13b234ba50658 "$learn_dir/state-only-confirmation-seeds-10-k10-v2.json"

"$learn_python" -m pytest -q \
    "$learn_dir/test_oracle_gate.py" \
    "$learn_dir/test_state_observable_gate.py" \
    "$learn_dir/test_state_learnability_gate.py" \
    "$learn_root/tests/test_w32_counterfactual_step.py" \
    "$learn_root/tests/test_w32_head_pivotality.py"
echo "focused_exit=0"

"$learn_python" "$learn_dir/verify_state_learnability_dataset.py" \
    --expect-partition development "$learn_development"
echo "development_verify_exit=0"

set +e
/usr/bin/time -v "$learn_python" "$learn_dir/run_state_learnability_dataset.py" \
    --partition heldout \
    --tle-root "$learn_tle" \
    --output "$learn_heldout" 2>&1 | tee "$learn_collect_log"
collect_exit=${PIPESTATUS[0]}
set -e
echo "collect_exit=$collect_exit"
if [[ "$collect_exit" -ne 0 ]]; then
    exit "$collect_exit"
fi

"$learn_python" "$learn_dir/verify_state_learnability_dataset.py" \
    --expect-partition heldout "$learn_heldout" | tee "$learn_dataset_verify"
echo "heldout_verify_exit=0"

set +e
/usr/bin/time -v "$learn_python" "$learn_dir/run_state_learnability_gate.py" \
    --development "$learn_development" \
    --heldout "$learn_heldout" \
    --output "$learn_result" 2>&1 | tee "$learn_fit_log"
fit_exit=${PIPESTATUS[0]}
set -e
echo "fit_exit=$fit_exit"
if [[ "$fit_exit" -ne 0 ]]; then
    exit "$fit_exit"
fi

"$learn_python" "$learn_dir/verify_state_learnability_result.py" \
    "$learn_result" \
    --development "$learn_development" \
    --heldout "$learn_heldout" | tee "$learn_result_verify"
echo "result_verify_exit=0"
sha256sum \
    "$learn_heldout" \
    "$learn_collect_log" \
    "$learn_dataset_verify" \
    "$learn_result" \
    "$learn_fit_log" \
    "$learn_result_verify"
echo "finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
