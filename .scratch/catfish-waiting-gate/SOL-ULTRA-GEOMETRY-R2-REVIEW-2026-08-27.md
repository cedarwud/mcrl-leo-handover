# Sol Ultra geometry/R2 independent review receipt

## Material Passport

- Reviewer route: fresh-context Sol Ultra sub-session
- Review date: 2026-08-27
- Reviewed ADR SHA-256: `1498bfff678f2a63d79a4a69153c5f0d4aa5e84c797ea2a54dba91fe394e2869`
- Reviewed R2 matrix SHA-256: `32a82678ca734438f2dad0dec9d2dea7b7e723712bc60c27d36e4c2a0f9065b1`
- Verdict: `REVISE_BEFORE_FABLE`
- Scientific/training authority: none

## Required revisions

1. `G0 = 500` was not provenance-closed. HOBS's `10c/f_c rad` field is
   ambiguous, and the exact efficiency used by the draft was back-computed
   rather than sourced. Treat 500 only as an approximate conditional candidate
   and leave the primary gain unresolved.
2. The proposed 13-cell set had no defined live-runtime semantics. Arithmetic
   for the 37-cell lattice and 12/13 coverage threshold was reproducible, but a
   coverage receipt is not automatically a runtime candidate filter.
3. The R2 illustration incorrectly assigned inter-satellite timing to eight
   re-entry events even though the event matrix correctly classified re-entry
   timing as unsourced.

## Minor corrections and upheld boundaries

- Describe `0.640 s` as the simulator measurement/triggering clock, not a
  sourced physical measurement scale.
- Preserve the distinction between HOBS's literal equation/table values and
  the derived one-sided interpretation.
- The audited TS 38.133 meanings and numerical timing anchors were otherwise
  reproduced.
- `R2_PHYS` remains not closed, `E_HO` remains unsourced, legacy evidence stays
  sensitivity-only, and the review grants no implementation or training
  authority.

This receipt preserves the first-pass result. Acceptance, if any, requires a
new review of revised target hashes.

## Targeted re-read

- Revised ADR SHA-256: `ea31937c806bbe1b52786706cd43d5f56c62fe5bc71298e5e71a24554e29f500`
- Revised R2 matrix SHA-256: `1c2fee6656ca6013c150a137d92ac84aa0b76d714ef1392e5452be5923c80e84`
- Verdict: `PASS_TARGETED_REREAD`

The reviewer independently confirmed that `G0 ~= 500` is only a conditional
candidate with `G0_primary = UNRESOLVED`; the 13-cell set is receipt-only while
runtime retains the full 37-cell lattice; and the R2 illustration correctly
excludes eight re-entry events and reproduces both timing calculations. No new
internal contradiction was found in the immediately affected passages.

This pass does not close gain provenance, `R2_PHYS`, `E_HO`, runtime/reward
authority, or training authority.
