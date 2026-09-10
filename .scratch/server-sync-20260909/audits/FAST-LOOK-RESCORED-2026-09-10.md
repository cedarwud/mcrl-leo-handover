**Demand-capped pooled efficiency improves only +0.273%, versus +113.412% under raw capacity; of the 377.349 Gbit raw-capacity increment, 315.709 Gbit went to the 142 user-anchors already at target, while 61.640 Gbit went to the 58 baseline non-attainers—only 3.400 Gbit brought them to target and 58.240 Gbit was surplus beyond target.**

`DIAGNOSTIC_NOT_CLAIM` · `FAST_LOOK_TWO_ANCHORS`

# Fast look rescored

The same fixed-assignment coarse search is reproducible and its raw-capacity result is unchanged. Once delivered bits are capped at each user's contracted demand, the apparent two-anchor gain deflates from +113.412% to +0.273%. This is a diagnostic on a copy: no learner or training was run, and no sealed constant, threshold, sign, seed, horizon, price, guard, acceptance rule, declared control law, assignment, search grid, or optimizer setting was changed.

## Pooled result under three numerators

All three efficiencies use the policy's own pooled energy: 7214.867369 J for the declared law and 7277.510669 J for the best-found settings (+0.868%).

| Numerator | Declared credited bits (Gbit) | Best-found credited bits (Gbit) | Declared efficiency (Mbit/J) | Best-found efficiency (Mbit/J) | Relative gain |
|---|---:|---:|---:|---:|---:|
| `CAPACITY` | 327.376 | 704.725 | 45.375 | 96.836 | +113.412% |
| `DEMAND_CAPPED` | 297.400 | 300.800 | 41.220 | 41.333 | +0.273% |
| `ATTAINMENT_ONLY` | 243.544 | 704.725 | 33.756 | 96.836 | +186.872% |

Definitions:

- `CAPACITY` is delivered ACM-capacity bits after the unchanged 48-boundary, 47-interval trapezoidal integration. It is the prior headline numerator.

- `DEMAND_CAPPED` first performs that integration separately for every user over the full 30.08 s endpoint, then applies `min(user integrated delivery, 50 Mbit/s × 30.08 s)`—a 1.504 Gbit cap per user-anchor—and only then pools users and anchors. This placement is faithful to the field convention because demand is contracted per user over the endpoint: it allows one user's delivery to vary across rational subslots and boundaries, while preventing surplus capacity for that user from satisfying another user's unmet demand.

- `ATTAINMENT_ONLY` credits the integrated ACM-capacity bits of a user-anchor only when that user reaches 1.504 Gbit over the endpoint. It does not cap surplus for an attainer. Since all 200 best-found user-anchors attain, its best-found numerator equals `CAPACITY`.

## Where the extra capacity went

The split below classifies each user-anchor by its attainment under the declared law, then sums `best-found delivery − declared delivery` within the two fixed cohorts.

| Declared-law cohort | User-anchors | Raw-capacity increment (Gbit) | Share of raw increment | Demand-capped increment (Gbit) |
|---|---:|---:|---:|---:|
| Already attained | 142 | 315.709 | 83.665% | 0.000 |
| Did not attain | 58 | 61.640 | 16.335% | 3.400 |
| Total | 200 | 377.349 | 100.000% | 3.400 |

Thus 315.709 Gbit of the extra raw capacity was entirely unrequested by users already at target. The 58 non-attainers received 61.640 Gbit extra, but their pooled shortfall was only 3.400 Gbit; after filling it, 58.240 Gbit was additional unrequested capacity.

## Capacity-parity check and attainment

The rerun reproduces the prior pooled capacity-efficiency headline exactly at binary64: 45.375 → 96.836 Mbit/J, +113.412%. Integrated capacity bits rise +115.265%, while joules rise +0.868%.

| Anchor | Declared → best-found target attainers | Declared → best-found capacity (Gbit) | Declared → best-found energy (J) | Power/mode comparisons |
|---|---:|---:|---:|---:|
| Step 0 | 72 → 100 | 164.371 → 359.764 | 3518.587 → 3571.681 | 3,593,726 |
| Step 1 | 70 → 100 | 163.005 → 344.961 | 3696.280 → 3705.830 | 1,333,070 |

The demand-capped anchor-local efficiency changes are −0.238% at step 0 and +0.759% at step 1. Pooling credited bits and joules—not averaging those two percentages—gives +0.273%.

## Serialized records and digests

The aggregate-and-record artifact is `.scratch/control-law-rescored/fast-look-rescored.json` (37,804,472 bytes in this run). For both `declared` and `best_found`, each anchor stores:

- every boundary and exact rational subslot start/end, plus its endpoint trapezoid weight;

- for every active beam: fixed beam identity, user ID, chosen radiated power, transmitted ACM mode (including `NO_TRANSMISSION`), delivered bits for one 0.640 s boundary interval after the rational TDM fraction, and the user's endpoint attainment flag;

- per-user integrated endpoint delivery and attainment, from which all three numerators are rescored.

| Anchor/policy record payload | SHA-256 |
|---|---|
| Step 0, declared | `a9dc462ca194f3aac3f04cb9b074a35c20b13f59a87ed024c85f2670cf5fd56a` |
| Step 0, best found | `d0851bef21514a10f2daf1dfda4baaf668dadad5af7af1f98e3cbe91467a0b4d` |
| Step 1, declared | `d686e8f42fdbf8d10efc7e3421b513c86c0051079cd4cc1f94c5ba3c35a85ac5` |
| Step 1, best found | `72aae007053650ccd8f1c83da72288952f5fa0ff9071442a5d25702ba8e0aec3` |
| Digest manifest | `b02a163d77828da063b83cd3a930d4bbc8732e96506ce28c2f98de3b90d6e5f0` |

The verifier recomputes every digest, checks rational subslots partition every boundary, reconstructs all 200 user-anchor endpoint deliveries from subslot records, recomputes the three numerators and cohort split, and confirms prior aggregate/search-count parity.

## Search identity and provenance

The wrapper imports and executes the prior search functions unchanged. Its only hooks annotate the slots and replace aggregate-only integration output with aggregate-plus-record output. The prior script and corrected receipt/runner remain read-only in the prior workspace.

| Item | Value |
|---|---|
| Prior search script SHA-256 | `8067cfaf58331cb015df533c5c017267d96f1cdf0fd01d99b48cdc7017666f22` |
| Prior aggregate result SHA-256 | `ef1bb3875583ca44d18440210ca35f400af570d7f3483bfbea42b0159da0bbf1` |
| World SHA-256 | `cb1c594d852a5aba1bda7ce26b2b1604c97d77ae5a6908048cd3ea5c7dda8e1b` |
| Training seed (unchanged provenance; no training run) | `1914058825465947281` |
| Step-0 fixed assignment SHA-256 | `b23418c436871d9cc193e15d052079fd9d77902a9947461207d193e267ce735a` |
| Step-1 fixed assignment SHA-256 | `fbbb05709a5018b3111b8555bef9e73f05a62c81e88ef302821b53fd27db70cc` |
| Recorded-search wall time | 131.235 s |
| Concurrency | One process; numerical-library threads pinned to one |

The unchanged power grid is `0, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0, 1.125, 1.25, 1.5, 2.0 × declared power`, clipped to 1.65 W with 1.65 W explicitly included. The same 28 ACM modes plus no transmission, four coordinate sweeps per subslot, three efficiency-ratio updates per anchor, fixed `ORACLE_SET` assignment, full coupled interference recomputation, service guard, and no-below-declared per-slot spectral-efficiency acceptance condition were reused.

## Exact reproduction commands

Run from `/home/sat/mcrl-v025-floor-ws`:

```bash
nice -n 15 env PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/control-law-rescored/fast_look_rescored.py
nice -n 15 env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/control-law-rescored/verify_rescored.py
nice -n 15 env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/control-law-rescored/render_report.py
```

Expected verifier line:

```text
PASS: prior aggregates/search counts match; 4 record digests verify; all 48-boundary rational subslots reconstruct 200 per-user endpoints; three numerators and the 142/58 split reconcile
```
