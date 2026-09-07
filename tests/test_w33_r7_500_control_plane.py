"""Expose the pinned R7 control-plane suite to the repository pytest runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SOURCE = (
    Path(__file__).resolve().parents[1]
    / ".scratch"
    / "c2-v03a-trend"
    / "test_r7_500_control_plane.py"
)
if not SOURCE.is_file():
    raise FileNotFoundError(f"pinned R7 control-plane suite is missing: {SOURCE}")
SPEC = importlib.util.spec_from_file_location("_r7_500_control_plane_tests", SOURCE)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import invariant
    raise RuntimeError(f"cannot load pinned R7 tests from {SOURCE}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

_EXPORTED_TESTS = {
    name: getattr(MODULE, name) for name in dir(MODULE) if name.startswith("test_")
}
globals().update(_EXPORTED_TESTS)


def test_project_pytest_wrapper_collects_r7_control_plane_regressions():
    assert {
        "test_bridge_materializes_exact_two_lr_by_five_arm_grid",
        "test_reconciled_source_grid_is_exactly_ten_and_routing_exposes_only_b_f",
        "test_routing_fails_closed_if_reconciliation_lacks_an_unselected_a_arm",
        "test_router_recomputes_summary_from_raw_and_carries_raw_lineage",
        "test_router_requires_exact_b000_f111_pair_and_ubuntu_gate_metadata",
        "test_source_completion_gate_requires_all_five_arms_in_both_matrices",
        "test_output_reservation_is_create_only_under_a_two_writer_race",
        "test_atomic_rename_noreplace_collision_preserves_foreign_receipt_and_marker",
        "test_publish_unlock_finalize_lifecycle_helpers_are_explicit_and_ordered",
        "test_required_five_labels_are_exact_and_present_in_the_svg_and_claim_artifacts",
        "test_runtime_closure_has_55_unique_source_reuse_files_and_package_initializers",
    }.issubset(_EXPORTED_TESTS)
