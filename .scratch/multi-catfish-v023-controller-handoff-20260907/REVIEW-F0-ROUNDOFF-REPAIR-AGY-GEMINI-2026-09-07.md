## VERIFIED

1. **F0 Change Scope ([`c3_contingency_f0.py:619–630`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency/c3_contingency_f0.py#L619-L630)):** Touches *only* the conservation identity check inside `CostShareResult.__post_init__` verifying `sealed["total_share_energy_j"]` against `beam_share_energy_j + satellite_share_energy_j`. Zero changes to `compute_cost_shares`, `compute_c3_targets`, `compute_d_target`, `compute_f_target`, the cost share formula, or the interval convention.
2. **Tolerance Derivation ([`c3_contingency_f0.py:243–247, 625–628`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency/c3_contingency_f0.py#L625-L628)):** Employs the existing scale-aware helper `_roundoff_tolerance` derived from the operand maximum magnitudes (`sealed["total_share_energy_j"]` and `expected_total_share_energy`), rather than a new constant or hand-picked relative epsilon.
3. **F1 Rebinding Scope ([`run_v023_c3_contingency_f1.py:143`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f1/run_v023_c3_contingency_f1.py#L143)):** Only updates `F0_SHA256` to `"9a8a97c02d2f0833cda6878a5327d5bd94662c95b662ee8b6c9aa138e0a806d2"`. Bindings, kill rules, deployment rule `MASKED_ARGMAX_Q1_PLUS_Q2_PLUS_Z_OVER_KAPPA` (`:754`), $\kappa$, world, lineage, steps, and field components are completely untouched.
4. **Discrepancy Assertion ([`test_run_v023_c3_contingency_f1.py:232–236`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f1/test_run_v023_c3_contingency_f1.py#L232-L236)):** The regression test evaluates a saved REAL anchor-0 BASE profile (100 users, 66 active beams, 6 satellites, $23.508$ W fixed power, $449.64$ W system power, $30.08$ s interval) and asserts the exact recorded discrepancy magnitude `2.842170943040401e-14` J against `_roundoff_tolerance` ($5.06 \times 10^{-11}$ J).
5. **No Downstream Semantic Drift:** In `c3_contingency_f0.py:619–630`, the check is strictly an assertion over immutable sealed arrays (`:637–641`). No data or targets are modified. The repair cannot change D/F/BASE selected actions or pooled EE in any way other than allowing execution to proceed past the IEEE-754 roundoff check.

## DEFECTS

- **[`.scratch/multi-catfish-v023-c3-contingency-f1/test_run_v023_c3_contingency_f1.py:186`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f1/test_run_v023_c3_contingency_f1.py#L186)**
  - **Severity:** High / Blocking (raises `FileNotFoundError` during `pytest`).
  - **Description:** Loads fixture from transient root path `Path(__file__).resolve().parents[2] / ".tmp" / "base-profile-anchor0.npz"` outside the package. The real fixture exists inside the package at `.scratch/multi-catfish-v023-c3-contingency-f1/fixtures-real-anchor/base-profile-anchor0.npz` (currently untracked).
  - **Exact Fix:**
    ```python
    # test_run_v023_c3_contingency_f1.py:186
    -    fixture_path = Path(__file__).resolve().parents[2] / ".tmp" / "base-profile-anchor0.npz"
    +    fixture_path = Path(__file__).resolve().parent / "fixtures-real-anchor" / "base-profile-anchor0.npz"
    ```
    and track `.scratch/multi-catfish-v023-c3-contingency-f1/fixtures-real-anchor/base-profile-anchor0.npz` in git.

## RULING

The repair strictly satisfies contingency ladder §4 for `INVALID_RUN`: it repairs only the demonstrated execution defect in `CostShareResult.__post_init__` without touching any formulas, targets, deployment rules, or kill gates. The test fixture loading defect in `test_run_v023_c3_contingency_f1.py:186` must be redirected to the packaged fixture before test execution passes cleanly.

AGY_F0_REPAIR_REVIEW=REPAIR_IS_INFRASTRUCTURE_ONLY
