The isolated-model interior occupancy optimum survives these attacks; its claimed mechanism identification and practical geometry-dependent interpretation do not.

`DIAGNOSTIC_NOT_CLAIM` — adversarial review, 2026-09-10. No training or policy run. No production constant, threshold, sign, seed, horizon, price, service guard, acceptance rule, or original report was changed. All counterfactuals are separate diagnostic calculations. MARGIN remains a constructed diagnostic provisioner, not a second sealed production implementation.

I could not eliminate the existence of an interior occupancy optimum under every tested formulation. I did overturn the specific preferred partition, demonstrate that the zero-fixed-cost test does not identify the claimed mechanism, and substantially narrow the geometry claim. Verdicts below distinguish those subclaims from the weaker existence statement.

The original generator reproduces the report byte for byte. Independent partition enumeration and production `AngleRateTPC_TDM`, ACM decoding, and energy receipts reproduce the reference arithmetic. Independently checked gain is `1.425834619886e-11`, noise is `5.575393264517e-13 W`, and diagnostic q10 is `0.513683388684`. Actual solver RF differs from the analytic threshold demand by approximately `2e-9` relatively, consistent with its clearance nudge. That numerical detail cannot explain the findings below.

**A1. The numerator — `WEAKENS_IT`.**

I retained production powers, modes, caps, and target eligibility, and changed only the diagnostic numerator to the contracted `N × 50 Mbit/s`. For N=24:

| Fixed costs | Credited numerator | Optimum, both rules | SEALED Mbit/J | MARGIN Mbit/J |
|---|---|---|---:|---:|
| Original | ACM capacity | `3+7+7+7` | 81.661632 | 60.239512 |
| Original | Contracted rate | `8+8+8` | 79.263370 | 58.129886 |
| Zero | ACM capacity | `3+7+7+7` | 90.763174 | 65.051518 |
| Zero | Contracted rate | `4+4+4+4+4+4` | 87.769478 | 62.905885 |

With the original accounting, `3+7+7+7` delivers 1263.875972 Mbit/s using 15.476987 W under SEALED; `8+8+8` delivers 1236.136667 Mbit/s using 15.139402 W. Both exceed the identical 1200 Mbit/s contract. Crediting that contract makes the original winner's EE only 77.534474 Mbit/J, versus 79.263370 for `8+8+8`: a 2.230% improvement. The corresponding MARGIN improvement is 1.635%. The original SEALED capacity-EE advantage over `8+8+8` was only 0.013879% of the winning EE.

The surplus is rung-dependent: occupancies 3, 7, and 8 receive 10.028%, 4.651%, and 3.011% above their contracts. The single-beam peak moves from occupancy 7 to 8 with fixed costs, and from 7 to 4 without them. Across N=1..24, changing the numerator changes 8 partitions with fixed costs and 5 without, under each rule.

There is a further boundary problem: maximum target-feasible loads are 11 SEALED and 9 MARGIN, so N=24 requires at least three beams. The corrected primary optimum is therefore the **minimum feasible beam-count boundary**, although occupancy 8 remains interior to the feasible per-beam load range. The reported four-beam recommendation is sensitive to crediting unrequested capacity. This attack does not eliminate all interior occupancy optima; it does eliminate a robust occupancy-7 recommendation and the primary N=24 interior beam-count result.

**A2. Zero interference — `WEAKENS_IT`.**

I constructed an equal-reference-link diagnostic with reuse 3: three beams can use distinct colors; four require one cochannel pair. I swept that pair's symmetric cross/direct gain ratio through the unchanged production coupled solver, tested all pair placements, and certified the conditional N=24 optimum by exhaustive isolated-EE upper bounds over 1,380 mode-eligible integer partitions. Full production TDM schedules and energy receipts verified the winners. For MARGIN, the separate design-geometry copy applies the same q10 multiplier to direct and cross gains, representing a coherent fade; this is one explicit interference extension of that diagnostic rule.

The optimum changes `3+7+7+7 → 8+8+8` at coupling **0.000163311 (−37.87 dB)** under SEALED and **0.006732557 (−21.72 dB)** under MARGIN. The production antenna gives coupling 0.000282160 (−35.50 dB) at 5.75° separation, already enough to defeat the SEALED winner. Its replacement achieves 81.650298 Mbit/J, only 0.013879% below the interference-free headline value. This particular partition choice is extremely fragile.

For a physically grounded magnitude check, I used production hexagonal cell centers and colors, and a spherical-Earth satellite position consistent with the central 750 km slant and 30° elevation: derived altitude 406.196 km. Four nearby cells have colors `[0,2,1,1]`; the repeated-color pair has 2.665906° separation and coupling 0.149401. Across all distinct assignments of `3+7+7+7` to these cells, the best SEALED EE falls from 80.870675 without coupling to **63.438251 Mbit/J with coupling**, a **21.556% loss**, while all 24 meet their contracts. Every MARGIN assignment fails all-user target attainment; its best-EE assignment attains 17/24 targets. Three nearby distinct-color beams with `8+8+8` attain all 24 targets at 80.701952 SEALED and 59.168934 MARGIN Mbit/J.

The physical comparison clusters users at each layout's cell centers, so it authenticates plausible interference damage, not a global association optimum for one fixed population. The exact pair sweep is likewise a controlled input sensitivity. Neither justifies a universal direction of spreading. In these tests interference favors **fewer beams**: production TDM already removes simultaneous within-beam interference, while extra cochannel beams add interference. I failed to produce the proposed reversal toward singleton spreading. The exact four-beam optimum breaks; interior occupancy still exists in the controlled example.

**A3. Satellite placement and beam ceilings — `WEAKENS_IT`.**

I assigned explicit physical beam identities, charged baseband once per active satellite through production energy receipts, and imposed separate diagnostic beam ceilings. Extra satellites were available with the same isolated link gains. At N=24:

| Beams allowed per satellite | Winning partition | Active satellites | SEALED Mbit/J | MARGIN Mbit/J |
|---:|---|---:|---:|---:|
| 1 | `8+8+8` | 3 | 79.548536 | 58.742177 |
| 2 | `3+7+7+7` | 2 | 80.619829 | 59.670701 |
| 3 | `8+8+8` | 1 | 81.650298 | 59.880402 |
| 4, 12, or 39 | `3+7+7+7` | 1 | 81.661632 | 60.239512 |

One satellite per beam lowers optimum EE by 2.588% SEALED and 2.486% MARGIN, and changes four beams to three. A three-chain ceiling alone also changes the winner. A 12-chain ceiling does nothing at this population. Production's 39-beam reference is explicitly not a ceiling; its 12-chain census belongs to idle-power sensitivity accounting, not the primary admission contract.

With exactly one available satellite and at most two chains, serving all 24 at 50 Mbit/s is infeasible under either rule. That is an inventory constraint, not an efficiency optimum. Where additional satellites are available, these ceilings do not remove intermediate occupancies. The attack breaks placement-independent recommendations, but fails to explain away the entire interior phenomenon.

**A4. The feasibility filter — `SURVIVES` for reference optimum; production-admissibility explanation is wrong.**

I evaluated occupancies 1..24 through production radiation and resolution, then enumerated all partitions under three distinct admissions: the report's uncapped-demand filter, actual target attainment, and production complete PHY service. Production explicitly forces cap transmission when no target mode exists. Its complete-service flag requires decoding throughout the allocated slots; 50 Mbit/s attainment is a separate field. Thus “excluded because all users must be served” silently substitutes contract attainment for production service.

At the reference geometry:

| Rule | Occupancy | RF W | Per-user delivered Mbit/s | PHY-complete users | Users attaining 50 Mbit/s |
|---|---:|---:|---:|---:|---:|
| SEALED | 12 | 1.65 | 47.679861 | 12/12 | 0/12 |
| SEALED | 24 | 1.65 | 23.839931 | 24/24 | 0/24 |
| MARGIN design fade | 10 | 1.65 | 45.835889 | 10/10 | 0/10 |
| MARGIN design fade | 24 | 1.65 | 19.098287 | 24/24 | 0/24 |

These are valid capped-but-degraded production outcomes. Nevertheless, admitting them leaves the reference capacity-EE optimum `3+7+7+7` unchanged. One beam of 24 achieves only 64.133840 SEALED or 51.377939 MARGIN Mbit/J, respectively 21.464% and 14.711% below the winners.

Across all 216 geometry-by-population cells per rule, replacing the report's filter with production PHY service changes **0 SEALED** optima and **5 MARGIN** optima. The five are at 0.83°/1000 km, N={8,15,16,22,23}; improvements are only 0.203–0.376%, with some users receiving 40.698 Mbit/s. Requiring actual target attainment reproduces all the original filtered optima. A separately labelled analytic cap-removal counterfactual changes 5/216 SEALED partitions, all at the worst edge/range corner; it leaves the reference optimum unchanged.

This attack exposes the extra service assumption and the invalid one-beam comparator in the strict-contract search, but does not make the reference optimum disappear when production-admissible degraded beams are restored.

**A5. Zero fixed costs and mechanism identification — `BREAKS_IT` for identification, not existence.**

Independent production PA receipts confirm that deleting only diagnostic chain/baseband charges preserves the original delivered-capacity optimum `3+7+7+7`. Its PA totals are 13.924987 W SEALED and 19.428847 W MARGIN. But the contracted-rate optimum becomes six beams of four users, with PA totals 13.672179 and 19.076117 W.

I then removed the ACM rungs in a separate smooth diagnostic copy. Its required SINR is

`Gamma(n) = max(SINR_MIN, 10^(1.7/10) × (2^(0.3n) − 1))`.

This retains the sealed rate, bandwidth, implementation margin, service floor, noise, gain, RF cap, and square-root PA function; the replacement rate–power relationship is explicitly not sealed ACM. With zero fixed costs and contracted-rate credit, it gives **`8+8+8` under both rules**, using 9.739134 and 13.588534 W. There are no mode-table rungs to select.

Away from the inactive service-floor constraint, efficiency is proportional to `n / sqrt(2^(0.3n) − 1)`. Its nonzero stationary point satisfies `x = 2(1 − exp(−x))`, giving `x=1.593624260` and **continuous occupancy n=7.663712723**. The RF cap does not bind at this optimum. Replacing the square-root cost with a separately labelled linear RF cost moves the zero-fixed discrete optimum to twelve beams of two users, near the retained service-floor boundary.

Concavity alone is not sufficient for an arbitrary demand law: if RF demand were proportional to n, square-root supply would favor increasing occupancy monotonically. But square-root supply combined with a smooth exponential rate–power requirement produces the interior optimum without any ACM table. Therefore the report's discriminator identifies only that fixed costs are unnecessary. It does **not** identify discrete modes as the cause. Moreover, MARGIN multiplies every uncapped RF demand by `1/q10`, hence every PA cost by `1/sqrt(q10)`; identical zero-fixed rankings on the common feasible set are algebraically forced, not independent corroboration.

I also checked actual discrete curvature. SEALED PA-cost second differences are +0.177040 W at n=2, −0.041531 W at n=3, and −0.300045 W at n=5. The production occupancy-cost sequence is not discretely convex; an interior ratio maximum should not be presented as a convexity result.

**A6. Geometry dependence and decision value — `WEAKENS_IT`.**

I independently reproduced the 8/144 SEALED off-axis switches, computed alternative-partition regret, removed the cap in a labelled analytic copy, and perturbed the angle/range inputs.

Seven switches occur at 1.66°/1000 km for N={8,13,15,16,20,22,23}, where the previous boresight optimum contains an eight-user beam. Its uncapped requirement becomes **1.798590 W**, 9.005% above the cap. The only switch with the previous solution still feasible is N=9 at 500 km: `9 → 4+5`, improving EE by **0.831437%**. Seven excluded previous winners does not mean seven switches caused solely by the cap: removing the cap eliminates five switches, while N=16 and 23 still change through PA/fixed-cost scaling, with gains of only 0.133498% and 0.075890%.

The single-beam SEALED occupancy peak is **7 at all nine geometry cells**. With zero fixed costs, SEALED has **0/144 angle switches and 0/144 range switches**. This follows from the mathematics: at fixed elevation, geometry multiplies all PA costs by one common positive scalar, preserving every feasible partition ranking. MARGIN has 26 angle switches: 24 exclude the previous optimum and only two compare feasible alternatives, with gains 0.038045% and 0.505023%. Contracted-rate credit still leaves only one feasible-to-feasible angle switch per rule, worth 0.074852% SEALED and 0.074173% MARGIN.

These changes are not floating-point noise: all eight SEALED changed endpoints retain their winners under separate ±0.05° and ±10 km perturbations. Yet the headline reference N=24 winner crosses over at approximately 744.851 km, only 5.149 km from the chosen 750 km reference, with its 0.013879% advantage. Integer remainders make its beam count look more decisive than its objective value.

A useful operational check is to freeze the reference `3+7+7+7` partition across the grid and evaluate it through production capped radiation. For SEALED, all 24 still attain the target at all nine cells, and the worst EE loss relative to adapting is **0.942783%**. For MARGIN, the worst corner is different: at 1.66°/1000 km, 21 users fall to 39.298333 Mbit/s, only 3 attain target, and EE is 3.538329% below the adaptive solution. Geometry therefore supplies a real feasibility warning in adverse conditions. This grid does not establish a useful general occupancy-control signal beyond cap management and small integer/fixed-cost effects.

**A7. Additional attack: unequal design points conceal channel performance — `WEAKENS_IT`.**

The report evaluates SEALED at nominal gain and MARGIN at its selected q10 fade. I instead integrated both provisioners' unchanged powers over the same production Rician × lognormal-shadow × scintillation distribution at 30°, using deterministic quadrature and production ACM decoding breakpoints. Original design-point eligibility was retained. This is an expected-rate diagnostic, not a new admission rule or an all-user reliability guarantee.

With fixed costs and expected ACM capacity credited, the N=24 optima become **`8+8+8`, 74.694681 Mbit/J for SEALED**, and **`4+5+5+5+5`, 75.085541 Mbit/J for MARGIN**. Crediting only expected delivered traffic up to each user's contract instead gives `8+8+8` under both, at **70.303038** and **57.351734 Mbit/J**. The identical original partition is therefore not preserved when both rules face the same fading distribution.

At their selected-mode thresholds, per-user target attainment is approximately **43.2% SEALED** versus **89.9% MARGIN**, not guaranteed target service. The latter uses the project's authenticated q10, whose CDF under the integrated engine distribution is 0.100967. Changing quadrature order from 128 to 192 changes every evaluated CDF by less than `9.2e-11`; probability normalization and contracted-credit upper bounds were checked. This does not destroy interior optima, but prevents interpreting the design-point ratios as expected operational efficiency or service reliability.

**Reproduction and audit trail.**

The independent scripts, JSON measurements, detailed attack notes, and this renderer are in [.scratch/convexity-adversarial](/home/sat/mcrl-v025-arch-ws/.scratch/convexity-adversarial). The decisive production distinctions are [mode selection and service floor](/home/sat/mcrl-v025-arch-ws/src/mcrl/physics_v025/acm.py:47), [coupling masks](/home/sat/mcrl-v025-arch-ws/src/mcrl/physics_v025/architectures.py:295), [cap and no-mode treatment](/home/sat/mcrl-v025-arch-ws/src/mcrl/physics_v025/architectures.py:620), [complete service versus target attainment](/home/sat/mcrl-v025-arch-ws/src/mcrl/physics_v025/resolution.py:140), and [PA and satellite accounting](/home/sat/mcrl-v025-arch-ws/src/mcrl/physics_v025/energy.py:33). The renderer checks production-module SHA-256 values against those captured during independent recomputation and verifies that the original report still matches its rerun.

From the workspace root, rerun all measurements and regenerate this report with:

```bash
for script in a15_numerator_discriminator a2_interference a34_feasibility_placement a6_geometry a7_common_fading; do
  nice -n 15 env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
    /home/sat/mcrl-leo-handover/.venv/bin/python \
    ".scratch/convexity-adversarial/${script}.py" \
    > ".scratch/convexity-adversarial/${script}.log" || exit 1
done
nice -n 15 env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  /home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/convexity-adversarial/render_report.py
```

The original result establishes a reproducible finite-partition optimum in a homogeneous, freely repartitionable, interference-free diagnostic under one sealed provisioner and one constructed margin rule, with a chosen numerator and target-feasibility constraint. Some interior per-beam occupancies persist after correcting the numerator, removing fixed costs, and adding the tested interference. It does not establish occupancy 7 or four beams as a robust recommendation, a strictly interior beam-count optimum under contracted-rate credit, an ACM-specific mechanism, convexity of the production cost curve, or an optimal assignment for fixed physical users and payload inventory. The geometry evidence mainly reflects cap feasibility and small partition/fixed-cost effects; the model gives every reassigned user the same prescribed gain without demonstrating realizable assignments to fixed beam centers. A paper can honestly present this as a conditional diagnostic observation requiring realistic fixed-user geometry and a declared traffic/service objective, but cannot promote it to an identified, geometry-driven physical law or validated operational control principle.
