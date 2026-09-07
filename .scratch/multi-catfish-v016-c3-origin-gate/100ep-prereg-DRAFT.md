# Multi-Catfish MCRL V0.16 — 100EP five-arm physical screen

**Status: DRAFT / UNFROZEN / NOT AUTHORIZED**

This file is an implementation/SDD draft only. It is not a binding
preregistration, has no contract SHA-256, creates no artifact contract, and
does not authorize a simulator run, episode training, or TEST access. It must
be reviewed and frozen separately after the V0.16 B402 source gate outcome is
known.

## 1. Purpose and prerequisite

The proposed screen evaluates the current frozen-head V0.16 deployment
composition on fresh TRAIN worlds:

* C1/Q1: frozen V0.3 Q1 head;
* C2/Q2: frozen V0.14 Q2 head at rung 3000;
* C3/Q3: the V0.16 B402 origin-aware Q3 head, but only if all three B402
  initializations pass `PASS_ORIGIN_GATE`.

The screen is inference-only. It does not update any Q network, optimizer, or
replay buffer. A B402 PASS authorizes preparation of this separate screen but
does not itself freeze this draft or authorize longer episode training.

If B402 does not pass for all three initializations, this draft remains
unusable and no five-arm trajectory screen is opened.

## 2. Proposed fresh TRAIN world panel

The proposed evaluation world seeds are the inclusive range
`2026120101..2026120200` (exactly 100 seeds):

```text
2026120101 2026120102 2026120103 2026120104 2026120105 2026120106 2026120107 2026120108 2026120109 2026120110
2026120111 2026120112 2026120113 2026120114 2026120115 2026120116 2026120117 2026120118 2026120119 2026120120
2026120121 2026120122 2026120123 2026120124 2026120125 2026120126 2026120127 2026120128 2026120129 2026120130
2026120131 2026120132 2026120133 2026120134 2026120135 2026120136 2026120137 2026120138 2026120139 2026120140
2026120141 2026120142 2026120143 2026120144 2026120145 2026120146 2026120147 2026120148 2026120149 2026120150
2026120151 2026120152 2026120153 2026120154 2026120155 2026120156 2026120157 2026120158 2026120159 2026120160
2026120161 2026120162 2026120163 2026120164 2026120165 2026120166 2026120167 2026120168 2026120169 2026120170
2026120171 2026120172 2026120173 2026120174 2026120175 2026120176 2026120177 2026120178 2026120179 2026120180
2026120181 2026120182 2026120183 2026120184 2026120185 2026120186 2026120187 2026120188 2026120189 2026120190
2026120191 2026120192 2026120193 2026120194 2026120195 2026120196 2026120197 2026120198 2026120199 2026120200
```

These are proposed only and are not yet sealed. They were selected after a
static repository seed census:

* the census searched visible repository text-like files for whole-word
  ten-digit `2026xxxxxx` tokens using `rg`, excluding model/binary and image
  formats (`.pt`, `.pth`, `.npz`, `.png`, `.jpg`, `.jpeg`, `.pdf`, `.pptx`,
  `.docx`, `.svg`, fonts, and `.pyc`);
* 444 distinct matching tokens were found;
* no token in the proposed inclusive range was found;
* a hidden-file check also found no `2026120101` or `2026120200` occurrence.

The census is only a static exclusion, not proof that a remote server or an
untracked binary has never used a seed. Before freezing, rerun the census
against the exact server checkout and all source/receipt manifests. In
particular, do not reuse known panels such as the old V0.4 physical seeds
`2026109001..2026109100`, B402 source worlds `2026111001..2026111006`, or
B402 C3 initialization seeds `2026111101..2026111103`.

### Proposed fixed environment fields

These values must be replaced by the exact values in the final contract and
sealed before outcome inspection:

```text
split                 = TRAIN
users                 = 100
steps_per_episode     = 10
episode_interval      = canonical simulator interval
field_component       = MCRL_V016_C3_ORIGIN_100EP_FIVE_ARM_SCREEN_V1
field_key             = (field_component, world_seed)
field_excludes        = (arm, source_lineage, c3_initialization, policy,
                         action, target, outcome)
```

Each world must use one canonical keyed fading field, shared by all arms and
lineages. Every arm/lineage row must use a fresh environment reset while
retaining the same world identity and field digest.

## 3. World-level sharding and row cardinality

The execution unit is one world, not one arm. A world shard evaluates all of
the following before it is released:

* `FULL`, `DROP_C1`, `DROP_C2`, and `DROP_C3` for each of the three frozen
  Q1/Q2/C3 lineage pairs: 12 route episodes;
* one independent frozen `MAIN` episode: 1 episode.

Thus the proposed panel has:

```text
route rows per arm       = 100 worlds * 3 lineages = 300
MAIN rows                = 100 worlds
all episode rows         = 4*300 + 100 = 1,300
simulator steps          = 1,300 * 10 = 13,000
user-action decisions    = 13,000 * 100 = 1,300,000
```

The shard controller may run independent world shards in bounded parallelism
(for example, no more than the server's declared CPU budget, with `P<=18` as
an implementation ceiling). The merge must be deterministic by ascending
world seed and must verify one field digest per world, exactly one MAIN row per
world, and exactly one route row for every `(world, source_lineage, arm)`.
Running arms independently with different fields is forbidden because it
breaks the paired-world comparison.

The `episode_index` is the fixed ordinal 1..100 of the world panel and is
shared by all five arms. The final route-arm checkpoint therefore contains 300
route rows (three lineages at index 100); the MAIN checkpoint contains 100
rows. This convention follows the existing V0.14 physical evaluator and must
not be silently changed to mean 100 rows across all arms.

## 4. Frozen panel and lineage mapping

The final preparation receipt must explicitly bind the B402 result, receipt,
and all three rung-3000 C3 checkpoint hashes. The proposed C3-to-source
mapping is:

| C3 initialization | Q1/Q2 source lineage | Q1 source | Q2 source |
| --- | --- | --- | --- |
| 2026111101 | 2026092101 | V0.3 Q1 rung 10 | V0.14 Q2 rung 3000 |
| 2026111102 | 2026092102 | V0.3 Q1 rung 10 | V0.14 Q2 rung 3000 |
| 2026111103 | 2026092103 | V0.3 Q1 rung 10 | V0.14 Q2 rung 3000 |

The C3 initialization ID and Q1/Q2 source-lineage ID must both be recorded;
they are not interchangeable. All loaded networks are `eval()` and no-grad;
parameter and optimizer digests must be unchanged before and after each
episode.

## 5. Five arms and one-action semantics

At each user decision, all route arms use the same native legal mask and one
final masked argmax. The detached reference is materialized before the C3
state is encoded:

```text
FULL:     c^12 = argmax(Q1 + Q2); select argmax(Q1 + Q2 + Q3(s^12))
DROP_C1:  c^2  = argmax(Q2);     select argmax(Q2 + Q3(s^2))
DROP_C2:  c^1  = argmax(Q1);     select argmax(Q1 + Q3(s^1))
DROP_C3:  select argmax(Q1 + Q2); do not evaluate Q3
MAIN:     independent canonical frozen Main baseline
```

For the three route lineages, Q3 uses the V0.16 402-D origin-aware state
(`14` local features, `10` globals). No V0.15 371-D state, second decoder,
route normalization, coordinator, auction, vote, or post-action override is
allowed.

## 6. Episode receipts and ratio-of-sums EE

Each episode receipt must include at least:

* arm, world/episode index, world seed, C3 initialization, and Q1/Q2 source
  lineage;
* field-root digest, action-trace digest, start-world digest, and code/gate
  provenance;
* finite nonnegative delivered bits, finite positive total energy, decision
  count, and served user-step count;
* `evaluation_split=TRAIN`, `test_split_opened=false`,
  `held_out_ee_evaluated=false`, and `episode_training=false`.

For every arm (A), pool additive totals first:

```text
B_A   = fsum(total_bits_e)
E_A   = fsum(total_energy_j_e)
eta_A = B_A / E_A
S_A   = fsum(served_user_steps_e) / fsum(decision_count_e)
```

`eta_A` is the only EE endpoint. The arithmetic mean of per-episode EE is a
descriptive statistic only. Report pooled values, each source-lineage pooled
value, per-world paired deltas, and descriptive per-episode distributions.

Because route arms have three times as many rows as MAIN, compare service by
the normalized fraction (S_A); raw served-count differences against MAIN
are diagnostic only.

## 7. Proposed service guard

This is a proposed pre-outcome guard and must be reviewed before freezing:

For each (i\in\{1,2,3\}):

1. pooled (S_{FULL}\ge S_{DROP\text{-}C_i});
2. at least two of the three paired source-lineage contrasts satisfy
   (S_{FULL,\ell}\ge S_{DROP\text{-}C_i,\ell}).

For the independent baseline:

3. pooled (S_{FULL}\ge S_{MAIN}).

No service improvement is required; the guard is non-inferiority protection
against an EE gain caused solely by serving fewer user steps. Invalid or
non-finite episode rows fail the run integrity check. The final contract must
state whether these proposed guards are hard decision clauses or reporting
diagnostics; that choice cannot be made after results are visible.

## 8. Pre-outcome ordering gate

The requested ranking gate is:

```text
eta_FULL > eta_DROP_C1
eta_FULL > eta_DROP_C2
eta_FULL > eta_DROP_C3
eta_DROP_C1 > eta_MAIN
eta_DROP_C2 > eta_MAIN
eta_DROP_C3 > eta_MAIN
```

Equivalently, `FULL` is strictly highest, `MAIN` is strictly lowest, and
every DROP arm lies strictly between them. The gate is evaluated on the pooled
ratio-of-sums values, not on rounded display values. The proposed decision is
`PASS_100EP_ORDERING_SCREEN` only when all six strict inequalities and the
service guard pass; otherwise it is `FAIL_100EP_ORDERING_SCREEN` and no longer
episode run is implied.

This ordering is a development screen, not a final efficacy claim. In
particular:

* `FULL` vs `DROP_C1` tests C1's marginal contribution while C2 and C3 are
  present;
* `FULL` vs `DROP_C2` tests C2's marginal contribution while C1 and C3 are
  present;
* `FULL` vs `DROP_C3` tests C3's marginal contribution while C1 and C2 are
  present;
* `DROP_Ci > MAIN` compares route configurations with the baseline but does
  not establish that C_i works as a standalone single-head policy.

There is no claim here that any Cj alone improves EE, nor that the three
individual marginal contributions are additive. Pairwise interaction can
consume part of another head's benefit; the required evidence is the complete
five-arm ordering on the same paired worlds.

## 9. Write-once progress checkpoint

The frozen-head screen has one required boundary at episode index 100. It must
write once, after all 100 world indices have been verified, for each arm:

```text
checkpoints/full-episode-000100.json
checkpoints/drop_c1-episode-000100.json
checkpoints/drop_c2-episode-000100.json
checkpoints/drop_c3-episode-000100.json
checkpoints/main-episode-000100.json
```

These are progress/aggregation receipts, not model checkpoints. Each contains
the arm, index, configured episode count, row count, pooled bits/energy/EE,
service summary, gate/checkpoint/code digests, and the explicit TRAIN-only
flags. The complete output is write-once and includes `prepare.json`, shard
receipts, `episode-receipts.json`, `episode-provenance.json`, `run.json`, and
`verify.json`.

Actual learner/episode training, if later authorized, requires a new contract
with model/optimizer/replay checkpoints at every 100 episodes. This draft does
not authorize that activity.

## 10. Risks and unresolved items

1. **B402 dependency:** there is no usable C3 panel until all three B402
   initializations pass and their result/receipt/checkpoint bytes are
   authenticated.
2. **Seed freshness:** the proposed range is clear in the current static
   census only. Remote, hidden, untracked, or binary receipts may change the
   result; rerun the census on the exact server checkout before freeze.
3. **100EP interpretation:** this draft explicitly chooses 100 world indices,
   yielding 1,300 episodes under the prior V0.14 convention. If “100EP” means
   100 total episodes across all five arms, the row count and scientific power
   change and require a new decision.
4. **MAIN authority:** the final contract must name and hash the canonical
   frozen Main loader and its environment path; MAIN cannot be reconstructed
   from Q1/Q2/Q3.
5. **Service acceptance:** the proposed pooled plus 2/3-lineage guard must be
   accepted before outcome inspection; no threshold may be tuned afterward.
6. **World shard merge:** deterministic merge order, one field per world, and
   duplicate/missing row rejection must be implemented and tested
   synthetically before a physical run.
7. **Claim ceiling:** even a passing ordering is TRAIN development evidence;
   it does not establish TEST efficacy or a publication-level generalization
   claim.
8. **No standalone interpretation:** the five-arm design intentionally tests
   marginal contributions in the presence of the other two Catfish, not three
   independent single-head policies.

