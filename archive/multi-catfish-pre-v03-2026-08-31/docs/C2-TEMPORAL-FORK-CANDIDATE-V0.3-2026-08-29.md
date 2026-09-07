# C2 Temporal-Fork Candidate V0.3A (policy-aligned revision)

Date: 2026-08-30  
Public method: **Multi-Catfish MCRL**  
Status: **core, policy-aligned real TLE forecast backend, K0/K1/K>=2 selection,
live option runner, Q2F/Main joint transaction, and formal training-step seam
implemented; a four-seed fresh-start bounded gate produced replicated K>=2
opportunity and one Q2F/Main joint dose; the shared carrier's episode-boundary
split/resume and artifact-history seams were verified in an earlier bounded
two-episode execution, while matched V0.3A EE efficacy, formal long-run cadence,
and Chapter-5 results remain unverified**

> **Current synchronization boundary (2026-08-30).** This revision describes
> the implemented C2 V0.3A semantics used by the current code and tests. It is
> sufficient for structural figures and non-result method prose, but it is not
> an empirical claim. A fixed-manifest Sol Ultra review selected
> `KEEP_H3_FIX_POLICY_ALIGNMENT`: fixed `H=3` remains, forecast and live now use
> the same branch-local Main/focal-hold compositor, and pre-fix certificates are
> segregated. Four sealed two-episode receipts pass the opportunity/mechanics
> gate; the matched-efficacy and long-run carriers remain gated. The
> drawing-start gate is open for editable structural
> drafts, but camera-ready and manuscript-final release remain closed. No
> 1500/3000/9000-episode V0.3A result exists.

## 1. Decision

C2 V0.2 is not edited in place. The completed 100-episode V0.2 pilot remains
diagnostic evidence for that frozen design only. A separate policy-aligned
V0.3A candidate was started because the V0.2 mechanism has two plausible structural failure
paths that a longer run cannot repair by itself:

1. its observable support excludes Main's cold destination and offers the
   incumbent plus warm alternatives; unchanged canonical `r2` therefore
   strongly prefers avoiding a handover without an EE non-inferiority guard;
2. it emits per-step focal donors while a fixed `H=3` commitment can move the
   eventual release handover outside the opening transition's learning target.

The selected V0.3A design is a **bounded temporal fork with complete
hold-plus-release accounting**. It retains the unchanged reward
`r2=-Psi`, the diagonal `C2 -> Q_2^M` mapping, and Main-only deployment.

This is a design candidate, not a claim that C2 now improves EE.

## 2. Verified V0.2 facts motivating the candidate

- `observable_c2_supports` opens when Main changes to a cold destination and
  returns the incumbent plus currently warm alternatives, deliberately
  excluding the cold Main action
  (`.scratch/smc-er-short-ep/smc_er_roles.py:487-531`).
- the eligible focal user is sampled before `Q_2^F` selects within that user's
  support (`smc_er_roles.py:350-360`);
- an open option forces the bound physical action while it remains remappable,
  without re-evaluating an EE condition (`smc_er_roles.py:330-346`);
- C2 sets `specialist_rewards=None`, so its private learner receives canonical
  column 2 only (`run_short_ep.py:1245-1260` and
  `smc_er_core.py:406-422`);
- each current donor is a focal-row one-step target and is mixed only into
  Main objective index 1 with scheduled `beta=0.25`
  (`run_short_ep.py:1490-1497` and `smc_er_core.py:752-767`).

The completed 10-episode diagnostic is not efficacy evidence. It does show
that C2 had nonzero dose (63 routed bundles in F111), so the observed negative
EE marginal cannot be explained solely as a zero-dose plumbing failure. Its
epsilon was still near one, so neither sign nor magnitude is treated as a
converged C2 result.

## 3. Alternatives considered

### A. Observable-score guard on V0.2

Interface: `filter_support(state, main_action) -> actions`.

Strengths: smallest patch, no model forecast, low runtime cost.  Weaknesses:
the interface is shallow; it leaves per-step donor semantics and delayed
release credit unchanged, and a hand-written SNR/load proxy can be a poor
system-EE surrogate.

### B. Temporal-fork SMDP core — selected

Interface:

```python
certificate = certify_temporal_fork(preoutcome_trace)
donor_plan = close_temporal_option(certificate, executed_steps, gamma)
```

Strengths: one deep module owns the forecast-EE frontier, complete
hold-plus-release validation, retain-all realised learning path, and the
intended Q2-only donor plan. The interface is small,
the scientific invariant is local, and the Main consumer does not need to know
how the forecast or option was produced. Weaknesses: a canonical forecast
adapter adds runtime cost and still requires prospective support measurement.

### C. Three-port temporal router with private reward shaping

Interfaces separately inject selection, potential-shaped private credit, and
Main routing. Strengths: maximum experimental flexibility and easy control
arms. Weaknesses: more parameters and more seams; an early result would not
identify whether focal selection, option termination, or shaping caused the
effect. It also changes the statement that C2 privately learns unchanged
canonical `r2` unless potential shaping is very carefully qualified.

The designs are not mixed in V0.3A. Alternative B was selected because it has
greater module depth and leverage while preserving locality of the two
scientific rules that matter most.

## 4. V0.3A algorithm

At a Main handover boundary for focal user `u`, C2 creates a matched physical
fork from the same pre-decision state:

- `M`: detached scalarized Main changes now;
- `F`: one temporal alternative is held for the frozen `H=3` intervals and is
  released to a contemporaneous detached-Main re-decision at interval four.

The reference and candidate are allowed to reach different counterfactual
states. At every offset, each branch first evaluates the same frozen Main
policy on its **own** contemporaneous state, mask, and action table. The
candidate compositor then changes only focal user `u` during the three hold
offsets and changes nobody at release:

```text
reference[k] = Main(reference_state[k])
candidate_main[k] = Main(candidate_state[k])
candidate[k, v != u] = candidate_main[k, v]
candidate[k, u] = incumbent(u)       for k = 0,1,2
candidate[3, :] = candidate_main[3, :]
```

Thus C2 owns one focal temporal intervention, not a privileged future joint
script. Non-focal physical actions may legitimately differ between the two
counterfactual branches if their states cause Main to decide differently. The
gate requires each non-focal candidate action to equal candidate-branch Main,
not to equal the reference branch's realised action.

This fork is the **certificate comparison**, not automatically a learned
two-action support. A failed alternative falls back to Main. One passing
alternative is a usable certified experience opportunity; only when multiple
alternatives pass does `Q_2^F` have a genuine within-certificate ranking task.
This wording deliberately avoids claiming that `Q_2^F` must relearn the
certificate's already-known Main-versus-alternative ordering.

The certificate is a training-time privileged, model-based behaviour policy.
It uses fresh domain-separated twins before the realised outcome, never the
live future RNG, and is absent during evaluation and deployment. Forecast
energy is exact conditional on the geometry/action path used by the current
power model. Forecast bits, service, and any outage-dependent `r2` term are
fading-off mean-channel estimates, not guarantees for the realised fading
draw. Therefore "EE-safe" below means **forecast-EE-safe**, not realised-EE
safe.

Let `B^M,B^C` be the reference and candidate full-window forecast useful bits,
and let `E^M,E^C` be their positive forecast energies. With
`eta^M=B^M/E^M`, candidate `C` is certified only if:

```text
B^M >= 1 bit
B^C >= B^M
S_EE = (B^C - B^M) - eta^M (E^C - E^M) > delta_EE
Delta G_{2,h}^{sys} > 0
Delta G_{2,f}^{sys} > 0
```

Here `delta_EE` is the frozen numerical robustness floor: the maximum of the
relative surplus floor and a 64-ULP arithmetic floor. With positive energies,
`B^C >= B^M`, and `S_EE > delta_EE > 0`, strict
`B^C/E^C > B^M/E^M` follows algebraically. A separate `E^C <= E^M` rule is
therefore neither necessary nor desirable: a throughput-dominant candidate may
consume slightly more energy and still improve forecast bits per joule. An
activation-pulse/resource-path flag remains hash-bound diagnostic provenance,
not an additional admission gate.

`Delta G_{2,h}^{sys}` is the system-total canonical-`r2` margin over the three
holds; `Delta G_{2,f}^{sys}` adds the first release. These system admission
margins must not be confused with the focal-row return learned later. Requiring
both margins prevents C2 from merely moving the same handover cost past its
visible hold. The forecast must also preserve focal service, create no new
non-focal outage, and prove branch-local non-focal Main policy alignment. A
branch that fails this pre-outcome certificate never enters the selectable
support.

EE and the system `r2` margins filter **which experience is admitted**. They do
not become a reward, rank multiple admitted alternatives, or enter `Q_1`.
Targets remain unchanged canonical `r2=-Psi`; C2 can therefore change finite-
training coverage but does not redefine Main `Q_2^M`'s reward fixed point.

All candidate forecasts in the fixed schedule complete before live selection.
Let `K` be the number that pass the certificate:

```text
K = 0   Main fallback; no C2 live option and no C2 update
K = 1   forced single-candidate control; no learned ranking claim
K >= 2  Q_2^F epsilon-greedy ranking inside the certified support
```

The selection receipt binds the complete support, selected object, behavior
probability, anchor context, Q2F policy version, and online-network hash. For a
learned `K>=2` choice, the policy version and network hash are checked again
immediately before the sole live execution seam.

After admission and real execution, every valid realised sequence is retained,
including service loss and other adverse outcomes. A normal nonterminal option
contains the three holds plus the first release. A true environment terminal
uses only its actual one-to-four-step prefix with no fabricated padding. A
bound focal key that disappears inside the detached forecast is failed support
and must remain in the sealed schedule outcome. The same disappearance after
live selection is a runner-integrity error, not a favourable zero-dose
conversion. Broken chains or lineage hashes fail closed rather than creating a
learning object.

For a retained sequence of actual length `L in {1,2,3,4}`, private `Q_2^F`
uses the observed focal option return

```text
G_{2,t}^{(L)} = sum_{k=0}^{L-1} gamma^k r_{2,u}(t+k),
```

with **zero bootstrap in every case**. The opening action means "initiate this
bounded option." Its logged behaviour probability is the exact opening
selection probability; continuation and release are conditional forced steps
with probability one.

Main `Q_2^M` never receives the option return as a primitive label. It receives
the same `L` executed intervals as primitive one-step canonical-`r2`
transitions. Their primitive TD losses are averaged into **one C2 source-unit**,
then mixed once:

```text
L_C2 = (1/L) sum_{k=0}^{L-1} L_{2,k}^{primitive}
L_2  = (1-beta_2) L_2^Main + beta_2 L_C2.
```

The Q2F update and the combined Main update are one at-most-once joint
transaction. Within that narrow transaction, parameters, target networks,
optimizers, gradients, RNG states, counters, consumed ledgers, the option
ledger, and the joint ledger roll back together on failure; the durable joint
record is committed last. Surrounding environment/replay/carrier atomicity is
a separate open gate. Source age is frozen at zero blocks. Thus a longer C2
option still contributes one source unit, the Main consumer remains diagonal
(`C2 -> Q_2^M` only), and no C2 network acts during evaluation or deployment.

## 5. Module boundary

The append-only candidate route is:

```text
.scratch/c2-v03/c2_temporal_fork_core.py
.scratch/c2-v03/c2_temporal_fork_forecast_adapter.py
.scratch/c2-v03/c2_temporal_fork_chronology.py          # runtime order/RNG gate
.scratch/c2-v03/c2_temporal_fork_trainer_backend.py      # real TLE/Main adapter
.scratch/c2-v03/c2_temporal_fork_selection.py            # K0/K1/K>=2 choice
.scratch/c2-v03/c2_temporal_fork_option_runner.py         # sole live option seam
.scratch/c2-v03/c2_temporal_fork_learning_adapter.py      # retained target/sequence
.scratch/c2-v03/c2_temporal_fork_torch_adapter.py         # Q2F/Main optimizer seam
.scratch/c2-v03/c2_temporal_fork_combined_carrier.py      # diagonal source-unit mix
.scratch/c2-v03/c2_temporal_fork_joint_transaction.py     # atomic at-most-once update
.scratch/c2-v03/c2_temporal_fork_training_step.py         # formal orchestration seam
.scratch/c2-v03/c2_stage0_receipt_adapter.py              # compatibility only
.scratch/c2-v03/c2_temporal_fork_runtime_adapter.py       # legacy frontier only
```

The pure core owns finite EE arithmetic, the fixed three-hold/one-release rule,
28-action/physical-ID binding, complete U-by-3 canonical reward validation,
joint-action and state/mask chains, realised service, and admission. The
exact-payload producer derives all
metrics from complete reference/candidate traces and recomputes anchor, RNG,
request, branch, and forecast-payload digests. The committed-step producer
then recomputes the same focal arrays and full joint actions from actual
execution before closure.

Hashes prove payload equality, not chronology. The single-use chronology gate
enforces `anchor -> all detached forecasts -> live-RNG non-advancement check ->
one selected live option` and emits an immutable ordering receipt. The real
backend, option runner, and bounded combined episode loop exercise this path.
The combined carrier advances the outer C2 trajectory by the actual one-to-four-
step live successor and suppresses the ordinary Main carrier only after a joint
transaction commits. Before the policy-alignment revision, a fresh-start two-
episode U=10 run reached K0 in episode 0 and K1 in episode 1; the K1 path
executed four live primitive steps, admitted and updated Q2F once, and committed
exactly one joint Q2F/Main transaction. This historical run validates the shared
carrier path only; it cannot enter V0.3A learning or establish current support.
The current V0.3A reachability evidence is the four-seed policy-aligned gate in
Section 6.

The Stage-0 and legacy-frontier adapters are measurement bridges only. They
accept no historical certified row without lossless replay lineage for the
opening state/mask and both branch traces, never rescue a failed row, and skip
a physical self-row. The old JSON omitted not only bits and energy but also the
payloads required for these hashes, so it cannot authorize training by itself.

The old rule discarded a focal unless at least two alternatives certified.
V0.3A instead exposes explicit `K=0`, `K=1`, and `K>=2` semantics. The following
three-anchor census is a **historical pre-V0.3A diagnostic**, superseded for
current policy authority by the four-seed gate later in Section 6. That census
completed 10 of 11 scheduled forecasts: the
first anchor produced four passing candidates (`K=4`), while two later anchors
produced `K=0`. This establishes that a genuine within-certificate ranking task
can occur, but it is not an opportunity-frequency estimate for training.

The frozen prospective schedule scans at most nine departing focal users in
ascending user order and never stops after finding a pass. The measured census
cost averaged about 4.48 seconds per completed candidate on the current host.
That cost must be benchmarked inside the episode loop before estimating the
wall time of 1500/3000 episodes.

## 6. Executable invariants and present claim ceiling

Current executable checks include:

- exact `H=3`, exactly 28 actions, distinct Main/alternative physical actions;
- evidence-sensitive option IDs: changing a metric, flag, or forecast lineage
  changes both the evidence digest and option ID;
- full action-table, joint-physical-action, opening-state/mask, subsequent
  state/mask-chain, reward-source, U-by-3 reward, bundle, and option binding;
- canonical realised `r2` restricted to `{0,-0.5,-1.0}`;
- strict forecast EE surplus and strict hold/full system-`r2` margins;
- one shared forecast/live compositor, branch-local non-focal Main alignment,
  focal-only hold override, and complete contemporaneous Main release;
- retain-all realised outcomes after pre-outcome admission, including adverse
  service; true terminal prefixes contain only actual steps and no padding;
- detached-forecast focal expiry is explicit failed support, while
  expiry after live selection is a hard orchestration error;
- K0 fallback, K1 forced-control, and K>=2 Q2F selection with a complete
  pre-live support/selection/policy receipt;
- an ordered candidate-schedule seal that hash-binds every completed
  certificate, failed certificate, forecast support rejection, and contract
  error into the selection receipt and therefore into any later joint receipt;
- one private observed-return target with zero bootstrap and one one-to-four
  transition Main source-unit, with opening behaviour probability followed by
  unit-probability continuation;
- objective index 1 only, with the option return barred from primitive Main TD.
- an actual Q2F optimizer step with one calibrated observed option return and
  no target-network bootstrap;
- one canonical Main replay sample, baseline-identical Q1/Q3 optimizer steps,
  and a single-beta Q2 blend of the mean actual primitive losses;
- atomic one-to-four-bundle/one-option ledger commit, warm-up deferral, full
  rollback of the narrow Q2F/Main joint transaction, zero-block source age,
  and checkpoint round-trip of that transaction state.
- bounded runner checks that the live transaction uses the exact current Main
  object and a digest refreshed immediately before selection, that true early
  terminal prefixes are legal only on live execution, and that the sealed
  served-user/reward-source payload matches the committed transition bundle.
- the bounded runner atomically records `running`, `complete`, or Python-level
  `failed` status in `run-journal.json`; an abrupt process kill remains
  distinguishable as a journal left in `running` state.
- episode-boundary runtime snapshots restore Main and all specialists,
  optimizers, replay, source trajectories/environments, RNGs, consumed/option/
  joint ledgers, and the absolute episode cursor; a two-episode full-versus-
  split/resume check produced a byte-identical final Main checkpoint.
- the segment merger validates contiguous absolute episode/step identities,
  frozen config and authority identity, status/artifact hashes, chronology
  preimages, Main receipts, C2 dose, and ratio-of-sums telemetry before
  publishing a merged history; the merged history matches the uninterrupted
  history after only declared real-clock/hash variance and floating summation
  tolerance.
- a bounded real-trained-checkpoint harness loads the checkpoint's original
  Main optimizer states, fills replay only through the unchanged canonical
  per-user admission helper, seals all scheduled candidate outcomes, and has
  completed exactly one K>=2 selection/option/Q2F-Main joint transaction.

Still not claimed from these tests and bounded executions alone:

- adequate opportunity frequency or acceptable forecast wall time;
- a long run that resumes at the formal every-100-episode cadence and preserves
  the same parity across multiple checkpoints;
- atomic rollback of surrounding source environments, replay, and carrier
  state after a crash inside an episode, outside the narrow Q2F/Main joint
  transaction and the verified episode-boundary snapshot;
- matched baseline/treatment ratio-of-sums EE, useful-bit, energy, service,
  dose, and forecast-cost telemetry for long runs;
- any realised EE improvement.

The prior `55 passed`, `162 tests`, `167 tests`, `173 tests`, `174 tests`,
`175 tests`, `177 tests`, `180 tests`, `214 tests`, `227 tests`, and `228 tests`
statements are superseded. The current C2 V0.3A suite passes **230 tests**, and
the retained V0.2 core/role/runner
regressions pass **100 tests**. A real K=4 matched-random smoke executed and
retained four live steps while leaving Main networks and replay unchanged, as
intended for a no-optimizer mechanism smoke. These are engineering evidence
for the named seams, not an EE result.

Three fresh-start combined-runner diagnostics are also deliberately kept below
the claim ceiling. A two-episode `U=10, K_max=9` smoke reached no admission
because its candidate/reference physical-action binding failed closed. A
two-episode `U=100, K_max=1` smoke completed two candidate forecasts, but both
failed the useful-bit/EE certificate and therefore produced K0 fallback and
zero C2 dose. The subsequent one-episode `U=100, K_max=9` smoke completed with
K0/zero dose: two eligible forecasts failed the useful-bit/EE certificate and
one failed closed on an action-remap error. The subsequent v11 receipt classifies
that case as explicit `focal_hold_expired` support rejection at forecast offset
2 for user 72 and physical key `(62917,40)`. The former reference-script
non-focal remap diagnostic belongs only to the segregated pre-V0.3A mechanism;
V0.3A never injects those privileged future reference actions. Neither version
substitutes another focal action or weakens the EE/R2 certificate. These diagnostics
show bounded fail-closed behavior; they neither prove nor refute C2 efficacy or
usable K>=2 frequency.

The subsequent v12 one-episode receipt additionally seals all three ordered
outcomes under candidate-schedule SHA-256
`6ee1b8bc25fa5b40bcf09f824ba4656f40d394d03b3ca8616009125a9d6856ff`,
which changes the enclosing selection receipt. It remained K0/zero dose and is
receipt-integrity evidence only.

The bounded trained-checkpoint joint smoke at
`.scratch/c2-v03/real-checkpoint-joint-smoke-20260829.json` then closed the
previously missing optimizer seam without launching a training run. It loaded
checkpoint `e6b063ef...09c28b` at episode 8999 with all three original Main
optimizer states, admitted 1000 real rows from one complete ten-step canonical
100-user episode with zero prefill optimizer updates and no synthetic labels,
and sealed nine scheduled candidates with K=4 under schedule SHA-256
`fa9ff5a9...06c4f3`. One learned Q2F choice executed a four-step option, made
exactly one Q2F update and one combined Main update, changed both network
digests, and committed exactly one C2 option record and one joint record. The
receipt SHA-256 is `ab88354e...306c19`. This is trained-checkpoint mechanism
and feasibility evidence only; it is not a fresh-start combined-runner dose or
an EE result.

A separate pre-policy-alignment fresh-start U=10 two-episode execution supplied
the first bounded combined-runner dose and exercised the shared resume carrier.
Its full and split/resumed executions both end at
Main checkpoint SHA-256 `213ffc1b...ad1`; the clock-aware resume receipt
`artifacts/c2-v03-resume-parity-clock-aware-u10-2ep-20260829.json` reports
`training_result_equivalent=true`, zero unexpected state differences, and four
allowed chronology-bound ledger-hash differences caused by intentionally real
monotonic timestamps. Consequently the complete carrier-state files are not
byte- or semantically exact, and must not be described that way. The validated
segment merger and independent uninterrupted-history comparison are recorded at
`artifacts/c2-v03-resume-merged-history-u10-2ep-20260829/merge-receipt.json`
and `artifacts/c2-v03-merged-history-parity-clock-aware-u10-2ep-20260829.json`;
the latter has SHA-256 `656c6355...beebe26`, zero unexpected normalized
differences, and Main EE reconstruction relative error
`1.921876808921452e-16`. This bounded smoke used `checkpoint_every=1` to expose
the seam quickly. It is not evidence for the formal every-100-episode cadence,
an EE comparison, a training trend, or a V0.3A policy-authority receipt.

The policy-aligned V0.3A postfix gate then reran four fixed fresh-start
`F111/U=10/K_max=9/2EP` seed triples. Across eight schedules and 32 candidate
attempts it recorded six certificate passes, ten certificate failures, sixteen
physical-support rejections, zero contract errors, `K0=5`, `K1=0`, and
`K>=2=3`. Two of four independent seeds reached at least one K>=2 schedule;
three options executed, with one Q2F update and one Q2F/Main joint commit. All
four receipts pass schedule, execution-dose, checkpoint, episode-step, status,
and policy-code-authority validation under code-authority SHA-256
`6d6311a7...7cc4b`. Their paths are:

- `artifacts/c2-v03a-bound-u10-k9-f111-2ep-seed11-20260830-r2.json`;
- `artifacts/c2-v03a-bound-u10-k9-f111-2ep-seed31-20260830-r2.json`;
- `artifacts/c2-v03a-bound-u10-k9-f111-2ep-seed41-20260830-r2.json`;
- `artifacts/c2-v03a-bound-u10-k9-f111-2ep-seed51-20260830-r2.json`.

For each seed, all Main telemetry, all non-wall-time C2 counts, and the final
Main checkpoint are exactly equal to the immediately preceding policy-aligned
run. This establishes noninterference of the added code-authority receipt. It
does not compare C2 against a no-C2 arm and therefore says nothing about EE
efficacy.

No frozen V0.2 source, runner, authority, checkpoint, or Ubuntu checkout was
modified by V0.3A.

## 7. Remaining gates

1. **Replicated fresh-start opportunity and dose:** the fixed four-seed V0.3A
   gate is closed: two seeds contain K>=2, three options executed, and one
   Q2F/Main joint update committed. This authorizes only a matched short
   efficacy screen; it does not establish opportunity frequency at training
   scale and does not authorize adaptive H or warm-up.
2. **Outer-state integrity gate:** the runner journal now durably distinguishes
   normal completion, Python-level failure, and an interrupted run left in
   `running`. Add rollback or an explicit recoverable boundary for source
   environments, replay, and carrier state outside the already-atomic narrow
   Q2F/Main transaction. Preserve the current replay-batch warm-up accounting:
   an admitted live exposure may have zero C2 optimizer dose/commit while the
   ordinary combined Main carrier still owns that decision's single Main
   update. This is not delayed C2 activation or a Main pretraining warm-up.
3. **Long-run checkpoint/resume and telemetry gate:** full episode-boundary
   state persistence and a clock-aware two-episode split/resume smoke now pass.
   Verify the formal every-100-episode cadence across a longer run and matched
   baseline/treatment schemas for ratio-of-sums EE, bits, energy, service, dose,
   and forecast cost.
4. **Bounded matched screen:** run the fixed full/no-C2 pair for at most the
   developmental runner's 24-episode ceiling, with identical seed/config
   schedules and no mechanism changes. A separate 10--24-episode forecast-cost
   run may still estimate throughput without changing the
   frozen nine-user candidate schedule; record K0/K1/K>=2 counts, forecast wall
   time, actual option lengths, warm-up, and dose. This estimates the Ubuntu
   1500/3000 wall time; it is not an efficacy screen.
5. **Separate the design changes in the micro-screen:** compare
   Main-inclusive complete-window temporal credit without the forecast gate
   against the same carrier with the privileged forecast gate. This identifies
   whether completion, support, or certification creates the effect.
6. **Matched V0.3A short pilot:** heavy compute; run it on the Ubuntu server only
   after the correctness gates above. The planned 1500/3000 runs are
   developmental trend experiments. A 9000-episode run requires explicit user
   notice before launch.

The C2 role and its candidate mechanism are concrete. The unresolved questions
are empirical feasibility, opportunity frequency, and EE effect—not whether
the current V0.2 one-step design should simply be trained longer unchanged.

## 8. Historical intermediate review adjudication

The reviews in this section inspected moving intermediate snapshots and are
superseded for current policy authority by the fixed-manifest, rehashed decision
in Section 9. They explain why the design changed; they are not the current
launch verdict.

An Opus-Max adversarial review completed on 2026-08-29, but correctly reported
that it had pinned a moving intermediate snapshot rather than the final bytes.
Its verdict for that snapshot was `REVISE_CORE`, not rejection of the temporal-
fork direction. The review's critical findings were used as follows:

- unenforced joint action/opening state/mask fields: fixed in the current core
  and covered by adversarial tests;
- stale constructors and non-executable close path: fixed; the suite collects;
- failed/incomplete plans exposing live targets: fixed structurally with
  `None`/empty learning payloads and separate observed IDs;
- undefined four-transition dose: implemented as the mean primitive loss mixed
  once in the C2-only optimizer seam; one bounded fresh-start combined-runner
  dose now passes, while frequency and long-run use remain gated;
- privileged-information omission, binary-learning overclaim, mean-channel
  uncertainty, system-versus-focal `r2`, and realised-service ambiguity:
  corrected in Sections 4–6;
- forecast cost and low one-anchor certification rate: retained as a hard
  pre-pilot feasibility gate.

Because the review did not inspect the final hashes, it is evidence that the
direction survived adversarial scrutiny, not a final GO for training. A later
fresh-context Sol Ultra review returned `REVISE_BEFORE_RUNNER` on another
moving snapshot. Its result-corrupting findings—early-terminal handling, stale
Main digest, incorrect live successor ownership, and incomplete served/reward-
source validation—are repaired and regression-tested. Its remaining objections
are the opportunity/frequency, mid-episode recovery, and formal long-run carrier
gates listed in Section 7; bounded immutable history receipts now exist. A
later Opus-Max design audit completed against an earlier evidence snapshot. It
correctly exposed the forecast/live non-focal mismatch but lacked the later
four-seed positive receipts; its conditional adaptive-H recommendation was not
adopted as a final decision. A Fable-Max attempt that returned no verdict is not
represented as an approval.

## 9. Fixed-manifest V0.3A decision

A later fresh-context Sol Ultra review completed against nine rehashed source
and receipt files and returned `KEEP_H3_FIX_POLICY_ALIGNMENT`. It rejected
adaptive H and delayed warm-up as premature, identified the forecast/live
non-focal policy mismatch as a result-validity blocker, and selected the
deployable resolution now implemented in Section 4. The exact review receipt is
`.scratch/c2-v03/reviews/sol-ultra-c2-forecast-live-decision-20260829.json`.

The applied revision is versioned as
`C2_V0.3A_POLICY_ALIGNED_TEMPORAL_FORK`; its forecast authority schema is v3,
and its shared compositor is `candidate-local-main-focal-hold-v1`. Each anchor
binds the Main checkpoint, objective weights, Main-policy version, compositor
version, state/mask/action tables, branch-local Main outputs, composed outputs,
forecast traces, and the current 79-file code-authority manifest. Pre-V0.3A
certificates and legacy Stage-0 bridges fail the new policy-alignment gate and
cannot enter V0.3A learning.

This decision freezes the **mechanism core** for figures and non-result prose:
fixed H=3, candidate-local Main for all non-focals, focal incumbent hold, full
Main release, unchanged canonical R2 learning, strict EE/R2/service safeguards,
and diagonal `C2 -> Q_2^M` routing. Future empirical results may tune ordinary
training hyperparameters or reject C2 efficacy; they must not silently replace
these semantics under the same method label.
