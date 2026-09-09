# Circuit-power sensitivity of the coordination headroom — 2026-09-09

Status: **`DIAGNOSTIC_NOT_CLAIM`**

## Finding

**With per-chain circuit power set to 0.0 W and the declared 0.200 W
per-satellite term retained, ORACLE_SET is +6.514881% more energy-efficient
than UNILATERAL.** Its pooled EE is 32,919,158.575 bit/J versus
30,905,689.570 bit/J. The served totals remain 1,957 versus 1,939; BASELINE
serves 826.

The coordination headroom therefore survives the critical shared-amplifier
case. It is slightly larger than the current-constant result of +6.359000%,
not smaller. Under this fixed panel, the declared per-chain accounting
**dilutes** the relative gain by 0.155881 percentage points rather than
creating it.

Across all 18 requested combinations, the fixed ORACLE_SET configuration
remains more efficient than the fixed UNILATERAL configuration. The gain
ranges from +4.844512% at 15.0/2.0 W to +6.594628% at 0.0/0.0 W. This is a
rescore only: it does not say which configurations a selector using the
changed accounting would choose.

## Full pooled sweep

Energy efficiency is the ratio of pooled decoded bits to pooled modelled
partial-payload joules. `Served B/U/O` is BASELINE / UNILATERAL / ORACLE_SET.
Bits, assignments, decode outcomes, and served counts are fixed at every
sweep point.

| Per-chain W | Per-satellite W | BASELINE EE (bit/J) | UNILATERAL EE (bit/J) | ORACLE_SET EE (bit/J) | ORACLE over U | Served B/U/O |
|---:|---:|---:|---:|---:|---:|---:|
| 0.000 | 0.000 | 3,964,032.833 | 31,100,670.460 | 33,151,643.960 | +6.594628% | 826 / 1939 / 1957 |
| **0.000** | **0.200** | **3,953,842.657** | **30,905,689.570** | **32,919,158.575** | **+6.514881%** | **826 / 1939 / 1957** |
| 0.000 | 2.000 | 3,864,435.355 | 29,255,001.793 | 30,964,812.161 | +5.844506% | 826 / 1939 / 1957 |
| 0.338 | 0.000 | 3,733,866.275 | 28,636,291.473 | 30,477,978.120 | +6.431303% | 826 / 1939 / 1957 |
| **0.338** | **0.200** | **3,724,823.754** | **28,470,904.273** | **30,281,369.063** | **+6.359000%** | **826 / 1939 / 1957** |
| 0.338 | 2.000 | 3,645,369.913 | 27,064,138.366 | 28,619,770.805 | +5.747947% | 826 / 1939 / 1957 |
| 1.000 | 0.000 | 3,352,600.300 | 24,789,130.729 | 26,320,437.916 | +6.177333% | 826 / 1939 / 1957 |
| 1.000 | 0.200 | 3,345,308.362 | 24,665,100.358 | 26,173,680.596 | +6.116254% | 826 / 1939 / 1957 |
| 1.000 | 2.000 | 3,281,080.915 | 23,602,272.157 | 24,922,991.570 | +5.595730% | 826 / 1939 / 1957 |
| 3.000 | 0.000 | 2,562,189.949 | 17,632,490.058 | 18,638,970.008 | +5.708099% | 826 / 1939 / 1957 |
| 3.000 | 0.200 | 2,557,928.819 | 17,569,646.533 | 18,565,253.517 | +5.666631% | 826 / 1939 / 1957 |
| 3.000 | 2.000 | 2,520,207.034 | 17,023,586.423 | 17,927,142.383 | +5.307671% | 826 / 1939 / 1957 |
| 7.000 | 0.000 | 1,741,185.030 | 11,178,187.686 | 11,769,341.322 | +5.288457% | 826 / 1939 / 1957 |
| 7.000 | 0.200 | 1,739,216.130 | 11,152,898.026 | 11,739,906.687 | +5.263284% | 826 / 1939 / 1957 |
| 7.000 | 2.000 | 1,721,694.392 | 10,930,337.735 | 11,481,474.454 | +5.042266% | 826 / 1939 / 1957 |
| 15.000 | 0.000 | 1,061,140.528 | 6,453,576.223 | 6,775,182.512 | +4.983381% | 826 / 1939 / 1957 |
| 15.000 | 0.200 | 1,060,408.932 | 6,445,138.669 | 6,765,417.844 | +4.969314% | 826 / 1939 / 1957 |
| 15.000 | 2.000 | 1,053,869.683 | 6,370,181.967 | 6,678,786.204 | +4.844512% | 826 / 1939 / 1957 |

## Decomposition of the current +6.359000%

At zero for both disputed activation terms, the denominator contains only the
recorded PA-supply energy; standby and bus energy are zero in this endpoint.
The pooled fixed-configuration comparison is:

| Quantity | UNILATERAL | ORACLE_SET | ORACLE change |
|---|---:|---:|---:|
| Decoded bits | 1,660,779,577,104.985 | 1,694,404,970,756.872 | +2.024675% |
| PA-supply energy (J) | 53,400.121365 | 51,110.737458 | -4.287226% |
| EE with both activation terms zero (bit/J) | 31,100,670.460 | 33,151,643.960 | **+6.594628%** |

Restoring the current fixed charges gives:

| Current fixed-energy component | UNILATERAL (J) | ORACLE_SET (J) | O minus U (J) |
|---|---:|---:|---:|
| 0.338 W per active chain | 4,595.502080 | 4,483.664640 | -111.837440 |
| 0.200 W per active satellite | 336.896000 | 360.960000 | +24.064000 |
| Total fixed activation energy | 4,932.398080 | 4,844.624640 | -87.773440 |

Although ORACLE_SET saves 87.773440 fixed joules, that is only a 1.779529%
reduction in the fixed component—smaller than its 4.287226% reduction in PA
energy. Adding the fixed component therefore dilutes the total relative EE
gain.

An exact percentage-point counterfactual decomposition, restoring the terms
in the order shown, is:

1. credited bits plus PA energy, with both activation terms zero:
   **+6.594628%**;

2. restore 0.200 W per satellite while the chain term remains zero:
   **-0.079747 percentage points**;

3. restore 0.338 W per chain at the current satellite term:
   **-0.155881 percentage points**;

4. current result: **+6.359000%**.

Thus the part attributable to the two current activation-accounting terms is
**-0.235628 percentage points** in total. The per-chain term alone contributes
**-0.155881 points** under the critical comparison. Because EE is a nonlinear
ratio, an alternative restoration order changes the allocation between the
chain and satellite subparts, but not the combined -0.235628-point fixed-term
effect or the +6.594628% bits-plus-PA residual.

## Mechanism-family split

The authoritative 20-anchor receipt contains 12 anchors labelled
`complete-beam-evacuation` and 8 labelled `beam-occupant-subset`, not 7 and 3.
The split below follows the original report's selected-family convention: the
first recorded alias labels the configuration. One W4/A1 configuration has
both aliases, and is therefore in the `other`/subset group as in the original
report.

Pooled ORACLE-over-UNILATERAL gains within each restricted anchor group are:

| Per-chain W | Per-satellite W | Evacuation, 12 anchors | Other/subset, 8 anchors |
|---:|---:|---:|---:|
| 0.000 | 0.000 | +7.590801% | +5.142199% |
| **0.000** | **0.200** | **+7.471584%** | **+5.118029%** |
| 0.000 | 2.000 | +6.472428% | +4.913957% |
| 0.338 | 0.000 | +7.273712% | +5.199707% |
| **0.338** | **0.200** | **+7.166050%** | **+5.177168%** |
| 0.338 | 2.000 | +6.258781% | +4.985893% |
| 1.000 | 0.000 | +6.779068% | +5.288726% |
| 1.000 | 0.200 | +6.688720% | +5.268837% |
| 1.000 | 2.000 | +5.920770% | +5.098707% |
| 3.000 | 0.000 | +5.860096% | +5.451908% |
| 3.000 | 0.200 | +5.799603% | +5.437276% |
| 3.000 | 2.000 | +5.277018% | +5.310259% |
| 7.000 | 0.000 | +5.032630% | +5.596445% |
| 7.000 | 0.200 | +4.996437% | +5.586902% |
| 7.000 | 2.000 | +4.679102% | +5.502958% |
| 15.000 | 0.000 | +4.427709% | +5.700703% |
| 15.000 | 0.200 | +4.407725% | +5.695084% |
| 15.000 | 2.000 | +4.230572% | +5.645178% |

Served totals are invariant at every row of this table:

| Restricted anchors | BASELINE | UNILATERAL | ORACLE_SET |
|---|---:|---:|---:|
| Evacuation (12) | 503 | 1,169 | 1,181 |
| Other/subset (8) | 323 | 770 | 776 |

The proposed “subset should be unaffected” implication is **refuted for total
EE**, while its narrower bits/PA claim is confirmed. Since assignments are
fixed, decode-threshold outcomes, credited bits, PA energy, and served counts
do not change. But every one of the eight subset-labelled selections also
produces a net one-beam reduction for the full 30.08-s endpoint. Together they
reduce ORACLE_SET exposure by 240.64 active-chain-seconds versus UNILATERAL,
so their pooled EE gain necessarily changes with the per-chain constant:
+5.118029% at 0.0/0.2 W versus +5.177168% at 0.338/0.2 W.

The evacuation label also does not imply a net chain saving. Only 3 of the 12
evacuation-labelled selections reduce active-chain exposure; the other 9
activate a destination beam as they empty the source beam. The restricted
total is 7,790.72 chain-seconds for UNILATERAL and 7,700.48 for ORACLE_SET, a
90.24 chain-second reduction. ORACLE_SET simultaneously adds 120.32 active-
satellite-seconds in this family, which is why the satellite sweep lowers its
gain.

Across all 20 anchors, ORACLE_SET saves 330.88 active-chain-seconds
(13,596.16 to 13,265.28) but adds 120.32 active-satellite-seconds (1,684.48 to
1,804.80). These are accounting exposures, not evidence that a logical beam
maps to an independently switchable hardware domain.

## Method and integrity

This is a fixed-configuration algebraic rescore of the completed oracle
receipt. For each recorded assignment and each of its 48 already-declared
boundary times, the script counted unique physical beam identities and unique
satellite identities that remained live under the immutable tape masks. It
integrated those counts with the endpoint's existing trapezoid convention,
subtracted `0.338 * active-chain-seconds` and
`0.200 * active-satellite-seconds` from recorded joules, held the remainder
fixed, and added each swept pair. It did not solve propagation, interference,
power control, ACM, decoding, selection, or acceptance again.

Integrity checks passed:

- source oracle embedded receipt SHA-256:
  `07c120297370f2b1a4826fce723950bccaf9e1a4e81007cda4ae30fae975fc29`;

- all four reconstructed immutable tape digests matched the oracle receipt;

- the 0.338/0.200 W rescore reproduced the source pooled bits, joules, EE, and
  served totals for all three selectors;

- sensitivity receipt SHA-256:
  `7bda9e10e7cce995219372fbba534790e3194af308822c5ac18d6cee5bd63ff9`.

The completed oracle workspace was copied into this workspace as directed.
The execution environment mounted the pre-existing `.git` directory
read-only and busy, so it could not be removed or reinitialized in place. A
fresh root commit for the imported tree plus this sensitivity work is stored
in the workspace-local `.sensitivity-git` directory instead; this affects no
analysis artifact.

Reproducible artifacts:

- rescorer: [`.scratch/circuit-sensitivity/rescore_circuit_sensitivity.py`](.scratch/circuit-sensitivity/rescore_circuit_sensitivity.py)

- raw sensitivity receipt: [`.scratch/circuit-sensitivity/circuit-sensitivity-result.json`](.scratch/circuit-sensitivity/circuit-sensitivity-result.json)

- source oracle receipt: [`.scratch/oracle-ceiling/oracle-ceiling-result.json`](.scratch/oracle-ceiling/oracle-ceiling-result.json)

The sealed constants remain 0.338 W and 0.200 W. This diagnostic changes no
constant, threshold, sign, seed, horizon, price, service guard, or acceptance
rule, and it establishes no hardware switching semantics. Its narrow result
is that the measured fixed-panel coordination headroom does **not** depend on
crediting per-beam chain shutdown: it is +6.514881% when that credit is zero.
