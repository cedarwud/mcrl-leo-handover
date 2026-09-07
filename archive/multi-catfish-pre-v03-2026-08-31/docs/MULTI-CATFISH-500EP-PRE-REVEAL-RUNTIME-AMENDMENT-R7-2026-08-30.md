# Multi-Catfish MCRL 500-EP pre-reveal runtime amendment R7

Date: 2026-08-30  
Decision timestamp: `2026-08-30T13:55:19Z`  
Status: **pre-reveal frozen planning overlay; not active-run authority; not a result**

## 1. Material Passport

| Field | Value |
|---|---|
| Document ID | `MC-R7-500EP-PRE-REVEAL-20260830` |
| Material type | outcome-blind experiment/runtime amendment |
| Applies to | preliminary 500-episode route and runtime governance only |
| Does not alter | C1/C2/C3 mechanisms, rewards, Main topology, R2/R5 run inputs, or R6 authoring text |
| Evidence used to make this amendment | process state, checkpoint timestamps, CPU/thread observations, and bounded runtime probes only |
| Outcome evidence used | none; no EE, reward, service, or ablation result was inspected to choose this route |
| Highest permitted claim | preliminary direction for one trained policy under frozen held-out evaluation |
| Formal Chapter 5 status | not eligible |
| Heavy-compute authorization | none; a separate executable authority is required before a new training process starts |

This document records the computational decision before the 500-episode EE
endpoint is revealed. Its purpose is to avoid choosing an episode count,
learning rate, ablation order, or stopping rule after observing favourable
outcomes.

## 2. Precedence and non-interference

1. The two R2 1500-episode authorities and every R5 file pinned by them remain
   immutable active-run reproduction inputs.
2. `MULTI-CATFISH-ALGORITHM-DOCSET-R6-2026-08-30.md` and its R6 component
   documents remain the current authority for algorithm explanation, figures,
   slides, and non-result manuscript text.
3. R7 overlays only the preliminary experiment route, runtime estimates, and
   claim ceiling that were previously described as a complete two-learning-rate
   1500-episode matrix.
4. R7 does not cancel, pause, kill, resume, or rewrite either running
   1500-episode process. A process-control decision requires a separate explicit
   execution record.
5. R7 does not authorize a 3000- or 9000-episode run. The user must be told
   before any 9000-episode process is launched.

The active 1500-episode work therefore remains valid as launched. The
500-episode route is a separate preliminary screen, not a retroactive change to
the declared endpoint of those runs.

## 3. Mechanism and figure invariants

R7 makes no change to the Multi-Catfish mechanism:

- C1 Energy-Frontier learns canonical `r1`, uses the RIS-lineage EXP/ACRM
  adaptation, and may route specialist-origin TD influence only to `Q_1^M`.
- C2 Policy-Aligned Forecast-Certified Temporal Fork learns canonical `r2` and
  may route only to `Q_2^M`.
- C3 Spatial Load-Balancing learns canonical `r3` and may route only to
  `Q_3^M`; its Main-consumer path remains subject to its declared gate.
- Evaluation executes Main only. Specialists neither fuse deployment actions
  nor act at evaluation time.

Consequently, the system architecture, three-role overview, learner topology,
C1/C2/C3 mechanism diagrams, routing diagram, and training/deployment boundary
do not require a structural redraw. Only experiment-flow labels and future
result placeholders may show the R7 preliminary route.

## 4. Outcome-blind runtime evidence

The following measurements motivated the amendment. They are engineering
observations, not scientific outcomes.

| Route | Observed checkpoint cadence | Relative to B000 | Interpretation |
|---|---:|---:|---|
| `B000` | about `1050 s / 100 EP` | `1.0x` | Main-only training reference |
| `F111`, `lr=0.001` | about `3425--3510 s / 100 EP` | about `3.3x` | declared full arm; each consumer route obeys its frozen gate |
| `F111`, `lr=0.01` | about `4655--4809 s / 100 EP` | about `4.5x` | declared full arm under concurrent contention; frozen gates still apply |

At the observation boundary, the Ubuntu server exposed 20 logical CPUs while
the two F111 processes each owned 43 threads. Aggregate user CPU was about
`86--87%`, idle CPU about `13--14%`, load about `24--26`, and the runnable queue
about `39--40`. Available RAM was about 77 GiB. This supports two narrow
conclusions only:

1. adding a third normal heavy process was not a safe throughput assumption;
2. elapsed-time estimates based on the earlier `3--4 h / 1500 EP / arm`
   assumption were invalid for F111.

Checkpoint serialization was approximately four seconds per 100 episodes in a
bounded F111 observation and is not the dominant slowdown.

## 5. C2 cost anatomy

The principal algorithm-dependent cost is the C2 temporal fork, not the
100-episode checkpoint cadence:

- an episode may expose up to `K=9` departing focal candidates;
- each candidate evaluates one reference branch and one candidate branch;
- `H=3` means four detached environment offsets per branch;
- the uncached worst case is therefore `K x 2 x 4 = 72` detached forecast
  steps per episode;
- bounded probes measured approximately `4.48--5.03 s` per candidate at the
  observed workload.

The reference branch is candidate-invariant but is currently recomputed for
each candidate. Reusing it could reduce branch work from `8K` to `4+4K`, or
from 72 to 40 detached steps at `K=9`. This is only a future implementation
proposal. It is not part of the current R2 run and may not be used without:

1. exact reference/candidate output parity tests;
2. detached-state and RNG-isolation tests;
3. new source and executable hashes;
4. a separately frozen run authority; and
5. output isolation from every current R2/R5 artifact.

Data produced by cached and uncached implementations must not be pooled,
compared as one matched matrix, or used together to support one scientific
claim merely because their implementation labels are disclosed. A new
parity-tested authority must explicitly permit and define any cross-version
bridge first.

## 6. Evidence ladder

| Endpoint | Permitted use | Prohibited interpretation |
|---:|---|---|
| 10 EP | engineering smoke | trend or efficacy |
| 100 EP | mechanics and checkpoint gate | useful EE direction |
| 300 EP | weak trajectory diagnostic | stable selection or Chapter 5 evidence |
| 500 EP | shortest preliminary EE trend for one trained policy | formal efficacy, robustness, or final algorithm validation |
| 1500 EP | original R2 developmental endpoint | formal statistical generalization |
| 3000 EP | fresh selected-route developmental confirmation only if separately authorized | continuation from a favourable checkpoint |
| 9000 EP | possible Chapter 5 candidate only after a new multi-seed protocol and explicit user notice | automatic promotion from R7 |

The epsilon schedule remains `1.0 -> 0.01` over 2000 episodes. At EP500 the
training policy is still substantially exploratory, so Main-only masked-greedy
evaluation can show an early direction but cannot establish convergence.

## 7. Frozen 500-episode preliminary route

### 7.1 Common protocol

All comparisons use:

- training users `U=100`;
- the existing training, environment, and mobility seeds;
- checkpoints every 100 episodes;
- the declared canonical TLE file set and environment source;
- final EP500 Main-only masked-greedy evaluation on held-out `TEST`;
- user sweep `U in {60, 80, 100, 120, 140}`;
- frozen evaluation seeds `2026082904` through `2026082908`;
- system EE as pooled useful bits divided by pooled system energy within each
  arm/load cell;
- served fraction, zero-power, zero-service, finite-value, checkpoint-load,
  authority-hash, and environment-provenance safeguards.

The five evaluation seeds characterize environment variation for one trained
policy. They are not five independent training replications and cannot support
conventional inferential significance or training-stability claims.

### 7.2 Prefix admissibility

After both 1500-episode R2 matrices finish, the provenance bridge snapshots all
ten fixed EP500 checkpoints: five arms at each of the two learning rates. No
R7 training is launched. The bridge and completion reconciliation jointly
verify every B000/F111/A101/A011/A110 checkpoint while reading no EE, reward,
or service outcome:

1. exact R2 authority and source hashes;
2. declared learning rate and all three frozen seeds;
3. absolute episode index `500`, not a local resume counter;
4. matching Main policy digest between the periodic snapshot and its training
   receipt;
5. loadable checkpoint and finite parameters;
6. identical evaluator, TEST partition, TLE set, and environment source across
   compared arms; and
7. no branch selected, restarted, or discarded because of an observed EE
   value.

The completion reconciliation must reproduce the complete source
matrix, source status, journal, EP500 periodic checkpoint identity, and online
Main-policy digest. A running matrix, a partially populated five-arm matrix, or
an active source-matrix process fails closed. Routing may inspect only the
B000/F111 evaluation rows. The selected-learning-rate A101/A011/A110 snapshots
are not evaluated or exposed to the contrast stage until a valid LR selection
receipt exists.

The EP100/200/300/400 snapshots may be plotted as a diagnostic trajectory, but
EP500 is the only selection endpoint. No intermediate checkpoint may replace
it because its curve looks better.

### 7.3 Learning-rate routing gate

First evaluate matched `B000` and `F111` EP500 prefixes at both `lr=0.001` and
`lr=0.01`. For learning rate `l`, define at `U=100`:

```text
D_full(l) = 100 * [EE_F111(l) - EE_B000(l)] / EE_B000(l).
```

A learning rate is preliminary-route eligible only if:

1. `D_full(l) > 0` at the fixed EP500/U100 endpoint;
2. F111 loses no more than 2.0 percentage points of served fraction against
   B000 at that endpoint; and
3. every identity, finite-value, zero-power, checkpoint, and provenance guard
   passes.

Each learning-rate receipt binds 50 raw episode-total rows: two policies, five
loads, and five held-out evaluation seeds. The router must load those raw rows,
verify their exact grid, seeds, checkpoint hashes, positive useful bits,
positive energy, zero-power guard, and physical ratio identities, then
recompute the ten pooled summary cells itself. A summary-only receipt or a
summary that does not reproduce byte-for-value from the raw episode totals is
inadmissible.

Routing is frozen as follows:

- if exactly one learning rate is eligible, use it;
- if both are eligible and
  `abs(D_full(0.001)-D_full(0.01)) / max(D_full(0.001),D_full(0.01)) <= 0.04`,
  use `lr=0.001`;
- if both are eligible but that relative difference exceeds 4.0%, use the
  learning rate with larger `D_full`;
- if neither is eligible, do not evaluate the full leave-one-out set. For
  failure diagnosis only, select the learning rate with the larger
  `D_full(l)` (prefer `0.001` on an exact tie) and permit only the A101 probe
  described below.

This gate routes compute; it does not establish that the selected learning
rate is statistically better.

### 7.4 Ablation order

At the routed learning rate, use this fixed reveal/reporting order; it is not a
new training order:

1. `A101` (`Full-C2`) first, because C2 is the dominant runtime cost and the
   most urgent individual-role uncertainty;
2. `A011` (`Full-C1`);
3. `A110` (`Full-C3`).

For Catfish role `Cj`, define the fixed EP500 load-wise contrast:

```text
D_Cj(U) = 100 * [EE_F111(U) - EE_Full-minus-Cj(U)]
                  / EE_Full-minus-Cj(U).
```

All five load-wise signs and the equal-weight mean across loads must be
reported, favourable or not. A role is only **preliminarily EE-positive** when
its mean contrast is strictly positive, at least four of five load-wise
contrasts are positive, and the declared safeguards pass. This phrase applies
only to this one-policy 500-episode screen; it is not an efficacy claim.

If neither learning rate passed the F111-versus-B000 gate, A101 is labelled
`failure-analysis-only`. In that branch, A011 and A110 remain blocked until a
new outcome-aware redesign decision is documented; the negative full route may
not be relabelled as a successful Multi-Catfish result.

The A-arm EP500 source snapshots were generated under the same pinned
authority, seeds, checkpoint cadence, trainer configuration, and mechanism
bytes as their B000/F111 peers. Reusing them is therefore a stronger matched
comparison than retraining three additional 500-episode arms after the LR gate,
and removes redundant compute without changing the evaluated policy state.

## 8. Runtime and acceleration governance

The current safe routing assumptions are:

1. do not add a third normal F111-class process while the two observed F111
   processes occupy the 20-core server;
2. after both active matrices finish and validate, evaluate only the selected
   learning-rate source checkpoints; do not launch replacement R7 training;
3. benchmark one-process versus bounded two-process/thread-capped throughput
   before claiming that concurrency accelerates total matrix completion;
4. retain the 100-episode checkpoint cadence because it is scientifically
   useful and not the dominant cost.

The executable R7 route is target-bound to Ubuntu host `5090`, Python `3.13.3`,
NumPy `2.5.2`, SGP4 `2.27`, and Torch distribution `2.13.0`. Before each heavy
evaluation it requires both complete source matrices, at least 20 logical CPUs,
at least 8 GiB available memory, no active source/R7 evaluation process, a live
host/runtime recheck, and an exclusive global evaluation lock. The R7 authority
sets `new_r7_training_authorized=false` and contains no capacity receipt or arm
runner in its executable closure.

The following are semantic or protocol changes and are prohibited within this
R7 screen: reducing `K`, shortening `H`, changing user count, changing seeds,
changing TLE data, changing epsilon decay, changing rewards, relaxing the
candidate certificate, or replacing the Main-only EE endpoint. Any such change
requires a new mechanism/protocol version and a new matched baseline.

## 9. Output labels and claim ceiling

Every R7 output must display all applicable labels:

- `500-EP PRELIMINARY`;
- `ONE TRAINED POLICY`;
- `MAIN-ONLY HELD-OUT TEST EVALUATION`;
- `NOT A CHAPTER 5 RESULT`;
- `NOT FORMAL EFFICACY`.

Permitted wording includes `preliminary direction`, `screen`, `diagnostic`,
`designed to`, and `consistent with the hypothesis`. Prohibited wording
includes unqualified `improves`, `outperforms`, `effective`, `validated`,
`best`, `robust`, `generalizes`, `selected formal learning rate`, and
`Chapter 5 result`.

The first requested Chapter-5-style plot may therefore use EE on the vertical
axis and user count on the horizontal axis for B000, F111, and available
leave-one-out arms, but its title/caption must preserve the five R7 labels
above. It is a trend figure, not Chapter 5 evidence.

Machine-readable raw, summary, contrast, bridge, reconciliation, and gate
artifacts carry the same five-label bundle. Multi-file evaluation directories
are reserved create-only, retain an explicit incomplete marker while being
built, use atomic no-replace publication, and publish their receipt last. The
marker is removed only after the evaluation lock is released and the exact
directory membership is rechecked. A lock may be released only by its creating
process for the same authority-bound work item. An interrupted or concurrently modified
directory is not admissible as a completed result, and foreign bytes are never
overwritten or deleted during abort. Abort removes only the private staging
directory and deliberately leaves the visible incomplete marker for recovery.

## 10. Execution gate

This planning document performs no process mutation. Before any EP500 source
checkpoint is evaluated, a separate executable authority must freeze:

- exact code/input hashes;
- the two-LR routing arms and selected-LR ablation reveal rule;
- seeds, endpoint, checkpoint cadence, evaluator, and output directory;
- source-prefix provenance;
- target host/runtime and evaluation resource policy; and
- incomplete/failure publication behavior.

The R7-r4 executable candidate uses the fixed authority path
`artifacts/multi-catfish-v03a-r7-preliminary-authority-20260830-r4/master.json`,
the isolated bridge root
`artifacts/multi-catfish-v03a-r7-prefix-bridge-20260830-r4/`, and the isolated
ablation root
`artifacts/multi-catfish-v03a-r7-preliminary-500-20260830-r4/`. These paths do
not authorize execution until the frozen authority validates, project-collected
control-plane tests pass, both source matrices complete, and independent
pre-execution review accepts the exact pinned bytes.

No existing training process may be killed merely to enact this document.
Pausing at a checkpoint, changing concurrency, or launching replacement
A101/A011/A110 training is outside and prohibited by this authoring update.

## 11. Document synchronization map

R7 supersedes only the experiment-route statements in the following sections;
it does not rewrite their historical bytes:

| Historical document | R7 overlay scope |
|---|---|
| `MULTI-CATFISH-V02-INTERMEDIATE-TREND-PLAN-2026-08-28.md` | Stage 1 routing, timing, concurrency, and preliminary claim ceiling |
| `MULTI-CATFISH-ALGORITHM-DOCSET-R6-2026-08-30.md` | executable synchronization and post-run sequencing for the preliminary route |
| `C2-TEMPORAL-FORK-CANDIDATE-V0.3A-R6-2026-08-30.md` | measured runtime and A101-first diagnostic order |
| `MULTI-CATFISH-PAPER-ALGORITHM-V0.5-2026-08-30.md` | future experiment-method wording only |
| `THREE-CATFISH-EE-POSITIVE-ACCEPTANCE-CONTRACT-V0.2-2026-08-30.md` | 500-episode preliminary acceptance ceiling |

The R6 QA receipt, ADR-005, R2/R5 authority files, old prompts, preregistration
artifacts, and historical figure handoff remain unchanged.

## 12. Pre-execution checklist

- [x] Route recorded before inspecting EP500 EE outcomes.
- [x] Existing 1500-episode authority preserved.
- [x] Core C1/C2/C3 mechanisms and rewards unchanged.
- [x] EP500 fixed as endpoint; intermediate-checkpoint selection forbidden.
- [x] Two-LR gate and tie rule fixed.
- [x] A101-first reveal/reporting order fixed.
- [x] One-policy/five-evaluation-seed limitation stated.
- [x] C2 optimization separated from current data.
- [x] Figure impact limited to experiment-flow/result labels.
- [x] 9000-episode explicit-notice boundary retained.
- [x] Executable authority generator and control plane pass local pinned tests.
- [x] Prefix provenance bridge implemented and test-suite verified.
- [x] Redundant fresh 500-EP A-arm training removed before outcome inspection.
- [ ] R7-r4 master frozen and accepted by independent pre-execution review.
- [ ] Real prefix bridge and completion reconciliation receipts materialized.
- [ ] Scientific results evaluated and reported without sign filtering.

Do not edit this R7 snapshot to retrofit an observed outcome. Any change after
result reveal must be published as a later, explicitly outcome-aware revision.
