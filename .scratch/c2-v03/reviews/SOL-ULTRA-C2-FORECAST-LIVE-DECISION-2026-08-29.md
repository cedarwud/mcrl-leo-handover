# Fresh-context C2 design decision — fixed manifest, read only

Act as a fresh-context scientific-mechanism reviewer. Do not edit files, do not
launch any training or rollout, do not browse the web, and do not spawn agents.
Inspect only the manifest below plus directly imported definitions needed to
interpret these functions. Stop once the requested JSON verdict is supported.

## Single decision

Before a matched short pilot, choose exactly one:

- `KEEP_H3_FIX_POLICY_ALIGNMENT`: retain fixed H=3, but make forecast and live
  non-focal policies identical and retest opportunity.
- `SUPPORT_ONLY_ADAPTIVE_H`: replace fixed H=3 by a pre-outcome support-only
  sealed H in {1,2,3}, while keeping the EE and both r2 gates unchanged.
- `WARMUP_FIRST`: keep the mechanism unchanged but activate C2 after a
  preregistered Main warm-up.
- `REDESIGN_TEMPORAL_ALTERNATIVE`: fixed incumbent-hold is not a defensible
  primary alternative.
- `HOLD`: evidence is insufficient for any of the above.

## Current receipts

Four comparable fresh-start F111/U10/Kmax9/2EP seeds contain 8 schedules and
32 candidates in total: certificate pass 6, certificate fail 10, physical
support rejection 16, contract error 0; K>=2=3, K1=0, K0=5; three live options,
12 primitive steps, one Q2F update and one joint Main-Q2 commit. Two of four
seeds reached K>=2. These establish reachability and heterogeneity, not EE
efficacy.

A separate fresh F111/U10/Kmax9/10EP seed has 90 candidates: 74
`focal_hold_expired`, 13 `opening_incumbent_unavailable`, three certificate
failures, zero pass, K0=10, and zero C2 dose. Its corrected taxonomy rerun has
the same final Main checkpoint, bits, energy and descriptive EE as the original.

The current forecast candidate pins non-focal users to the detached reference
physical actions during hold offsets. The live option instead recomputes Main
and overrides only the focal user. Determine whether that is a result-validity
blocker and what exact alignment is scientifically preferable. Do not choose an
option merely because it increases pass rate. Treat adaptive H chosen using EE
or r2 as forbidden horizon shopping; only support-derived sealing is eligible.

## Fixed manifest and SHA-256

- `c2_temporal_fork_trainer_backend.py`
  `0c1625540e6d9d899633a1fd05c801ff1f20580595f1c97b0ebe89d6916e16db`
- `c2_temporal_fork_option_runner.py`
  `973294fdecdddf9d55d9370388e1a67cd264076d8319ebb48cb6e8a3894db8a2`
- `c2_temporal_fork_forecast_adapter.py`
  `f5ff2c35f8227ddee5c9a044062376564de66fe0d16a17249c3be65f37a243c6`
- `c2_temporal_fork_core.py`
  `b0e3a2c8634618618140083d74218db78743ee0791452c86a833468046e0f0aa`
- `artifacts/c2-v03-known-k1-u10-k9-f111-2ep-20260829-r1.json`
  `ad5b04e799183d05c24d05b00be8fac852bb3374d5419936d1f0080f792b065d`
- `artifacts/c2-v03-multiseed-u10-k9-f111-2ep-seed31-20260829-r1.json`
  `6bba669ce6155b069be1460473a242b55b2d54c5921f090f8f7ecbf2a5348c10`
- `artifacts/c2-v03-multiseed-u10-k9-f111-2ep-seed41-20260829-r1.json`
  `52ba7a46a0e685a0e916353dc539dcd4568d6cc2aebc361463e013ede6208cb4`
- `artifacts/c2-v03-multiseed-u10-k9-f111-2ep-seed51-20260829-r1.json`
  `969dba5112c0034afbebd778c1fb85aae7fc49fdb3e21ddb10af179fb0719716`
- `artifacts/c2-v03-opportunity-dose-u10-k9-f111-10ep-20260829-r2-taxonomy.json`
  `a41b9a592d87a163529b8f1c36dd4def157bb68e9b068b2c7fc87069a671815a`

Rehash these files immediately before the verdict. If any differs, return
`STALE` and stop.

## Output

Return one compact JSON object only, at most 1200 words, with keys:

- `verdict`: one allowed choice or `STALE`
- `forecast_live_alignment_finding`
- `h3_adjudication`
- `warmup_adjudication`
- `minimum_exact_changes_before_matched_pilot`
- `one_bounded_postfix_probe`
- `stop_rule`
- `claim_limits`

This review cannot authorize 1500/3000/9000 EP and cannot claim EE efficacy.
