# Multi-Catfish MCRL V0.23 LC-SRS R7 launch decision

Status: `FROZEN_PRE_OUTCOME / AUTHORIZED_ONE_SHOT`

This control document authorizes exactly one TRAIN-development LC-SRS R7
observability Gate. It does not authorize episode-policy training, the
five-arm learner screen, TEST, an efficacy claim, a paper conclusion, or a
second metric revision.

## Frozen decision

R6 remains failed under its original raw informed-minus-placebo sign-accuracy
predicate. `R6_FAILURE_RETAINED` is not recomputed or rescued here. R7 keeps
the same LC-SRS teacher, four matched profiles, deterministic C3View, physical
composition, service and leakage predicates, and one-shot rule. Only the
prospectively declared eligible-set metric is changed: balanced accuracy is
the primary R7 learner metric; raw sign accuracy is recomputed and reported as
a mandatory secondary, non-veto diagnostic. The LC-SRS formula, thresholds,
world panel, learner seeds, and all other contract predicates are frozen.

The only physical worlds are `2026121801` through `2026121808`; the only
learner seeds are `2026135201`, `2026135202`, and `2026135203`. The frozen
initial-network digests are:

```text
2026135201 106d23119468eb472babffe78a49c439296a232d8c5481d2aa8cb2890ec08a6f
2026135202 c726537fd8a309249cbb9eb674ab6c22e663925400112fd01c7a4f790398f56b
2026135203 016cebc7d0b69a6938a1547c4e400ce3afb2b1cf6e16ce8b6ca72408db427080
```

The exact base contract is
`docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md`
with SHA-256
`027e09a75a2e775b81b570cd49f6637dd10d55220d3ace2cf26a5b37ab002be5`.
The frozen executable/dependency code manifest is
`.scratch/multi-catfish-v023-r7-launch-ready/R7-LAUNCH-CODE-MANIFEST.json`.
Its SHA-256 is `c8347dc8d908f5dfcd4b015cdae7fdb900517001d27bce5c083e320bf9bd9f42` and must be present in the
launch manifest before any source, fit, or composition process starts.

The external TRAIN TLE root is exactly
`/home/sat/mcrl-runtime/tle-frozen-20260820`, with frozen file-set digest
`427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`. The
server output root for the infrastructure repair is exactly
`/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1` and the controller session is
`mcrl-v023-lcsrs-gate-20260906-r7-i1`. The launch uses
`OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, and
`NUMEXPR_NUM_THREADS=1`, with eight source, eight fit, and eight composition
workers on the dedicated Ubuntu server.
The fresh remote checkout root is exactly
`/home/sat/mcrl-v023-r7-launch-ready-20260906-r4`; prior base, `-r1`, `-r2`,
and `-r3` checkout roots are not reused.  The `-r3` pre-root consumer smoke
proved that the server editable install would otherwise shadow the frozen
checkout; the repaired controller binds `PYTHONPATH` to `-r4/src` and `-r4`.

The first R7 infrastructure attempt is retained as `INVALID_RUN`, not hidden
or treated as a scientific result.  Its exact inventory and hashes are bound
by `.scratch/multi-catfish-v023-r7-launch-ready/R7-INVALID-RUN-I0.json`.  All
eight source workers stopped before TLE admission because the validated
preflight receipt omitted the configuration and binding table required by
its consumers.  It wrote zero source artifacts, no fit or composition output,
and opened no scientific outcome.  The repair only restores those validated
receipt fields, aligns the existing source-adapter role name, adds a
pre-source consumer smoke, and advances checkout/run/session identities; no
world, seed, formula, target, metric, threshold, learner, or physics changes.

The selected D40 checkpoint remains frozen Gate background provenance only;
it is not a current five-arm learner initialization. Current R7 fit workers
must use the three fresh initial-network digests above. Any prior R6 run root,
R6 world/seed, TEST world, or replacement checkpoint blocks launch.

## Claim and boundary

The claim ceiling is
`TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY`.
The Gate may emit only the frozen R7 decision tokens from the contract, after
independent integrity verification. A GO token means only that this fixed
source is mechanically valid, observable under the balanced/raw estimands,
and composable under the Gate. It does not establish that C3, C1, C2, FULL,
or Multi-Catfish improves EE. Any later five-arm or episode experiment needs
its own frozen authority.

The R7 run is `one-shot`: no outcome-dependent threshold, sign, seed, world,
horizon, outage term, lambda, metric, or candidate change is allowed. A
failed integrity check may repair only a demonstrated infrastructure defect
before an unopened unit; it may not alter the scientific predicate or discard
a valid outcome. `NO_TEST`, `NO_EPISODE_TRAINING`, and `NO_EFFICACY` remain
hard boundaries in every source, fit, composition, finalizer, and result
receipt.

## Authority chain

The launch-ready preflight manifest binds this document, the exact code
manifest, every executable/dependency byte, the contract, TLE file-set digest,
initial-network digests, process environment, output root, tmux session, and
the independent final verifier. The launch manifest and code manifest are
separate digest domains: the code manifest excludes both manifests and this
decision document, so there is no circular digest.

The authorized launcher must first authenticate the local manifest and then
create a fresh server root and tmux session only after verifying that neither
exists. It must verify the frozen TLE root and file set, scan remote prior
MCRL run roots for the new R7 world/seed identities, and refuse any collision.
The result tree is write-once and is complete only after the independent final
verifier and result sealer succeed. The read-only fetcher must authenticate
the remote manifest before copying any bytes locally.

This decision is an execution authorization, not a scientific acceptance.
