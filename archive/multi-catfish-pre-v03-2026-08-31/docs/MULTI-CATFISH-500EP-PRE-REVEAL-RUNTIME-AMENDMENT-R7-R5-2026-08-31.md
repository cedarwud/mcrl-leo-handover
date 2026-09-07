# Multi-Catfish MCRL R7-r5 Pre-Reveal Runtime Amendment

Status: **PRE-EXECUTION CANDIDATE; NO SCIENTIFIC OUTCOME INSPECTED**  
Date: `2026-08-31`  
Supersedes: the executable r4 route only  
Preserves: the R7 scientific endpoint, Catfish mechanisms, reward functions,
seeds, TLE authority, training configuration, and claim ceiling

## 1. Decision

R7-r5 retains the source-prefix-reuse design:

1. the two already-running 1500-episode matrices remain the only training;
2. after both matrices are verified complete, the fixed EP500 checkpoints for
   `B000`, `F111`, `A101`, `A011`, and `A110` at learning rates `0.001` and
   `0.01` are bridged as one exact ordered 2-by-5 grid;
3. only `B000` and `F111` are evaluated before learning-rate selection;
4. only the selected-learning-rate A-arm checkpoints permitted by the frozen
   decision are exposed to the ablation evaluator; and
5. no new R7 training, resume, checkpoint selection, or 9000-episode run is
   authorized.

The scientific protocol and formulas remain those in
`MULTI-CATFISH-500EP-PRE-REVEAL-RUNTIME-AMENDMENT-R7-2026-08-30.md`, except
where this amendment states a stricter executable rule.

## 2. Why r5 exists

The frozen r4 candidate was reviewed independently by fresh-context Sol ultra
and Claude Opus max before server deployment. Both retained the source-reuse
design and found no S0 scientific defect, but they identified execution-control
gaps. R4 is therefore rejected for execution and must not be used as a result
authority.

R5 closes the following findings before any EE, reward, service, episode, or
ablation outcome is inspected:

- full outcome-bearing `status.json` files are not copied into the bridge;
- the automated extractor emits only a whitelisted structural sidecar;
- nested trainer/runtime objects are closed-world projections, and source
  Python, NumPy, Torch, preregistration, and TLE identities are reconciled;
- a neither-eligible route is visibly labelled `FAILURE-ANALYSIS-ONLY` in its
  standalone SVG as well as its JSON receipt;
- the selection receipt and its complete two-LR input graph are revalidated
  immediately before ablation publication;
- active-process detection consumes real argv records, recognizes wrappers
  such as `env`, and resolves relative source/output paths from `/proc/PID/cwd`;
- a losing directory-reservation writer cannot remove the winning writer's
  empty reservation;
- reconciliation is published create-only in its own immutable path rather
  than mutating the already-finalized bridge directory;
- handled evaluation failures release only their own authority-bound lock while
  preserving the incomplete output directory; and
- the ablation raw grid is independently reconstructed before its summary and
  Catfish contrasts are accepted.

## 3. Exact outcome-access statement

`outcome_values_used_to_freeze=false` remains literal: no outcome influenced
the authority, route, learning-rate rule, reveal order, or acceptance rule.

After both source matrices complete, the bridge's automated whitelist extractor
must parse each source status object once to obtain structural completion and
checkpoint identity. It must not access outcome metric keys for a decision,
must not copy or emit outcome metrics, and must not admit or reject a checkpoint
on their values. The bridge stores only:

- source/status identity and SHA-256;
- planned/executed episode counts and run mode;
- seeds, closed-world runtime identity, and closed-world trainer configuration;
- checkpoint cadence/count; and
- the minimal periodic-checkpoint identity rows required to bind EP500.

This is **outcome-independent structural extraction**, not a claim that the
source JSON file contains no outcomes or that a JSON parser reads no bytes from
it. Human review of source outcome files remains prohibited until the frozen
route produces its declared artifacts.

## 4. Failure-only presentation

If neither learning rate passes the fixed `F111` versus `B000` gate, only
`A101` may be evaluated. Every corresponding JSON and standalone SVG must carry
the conspicuous phrase:

`FAILURE-ANALYSIS-ONLY C2 DIAGNOSTIC`

Such an artifact cannot be described as a successful, positive, or effective
Multi-Catfish result even if an individual load-wise contrast is positive.

## 5. Publication and lineage rules

Immediately before any ablation receipt is atomically published, the runtime
must:

1. re-read and fully validate the frozen LR-selection receipt;
2. reproduce its decision from both raw B000/F111 evaluation graphs;
3. require the selection SHA and decision to equal their pre-evaluation values;
4. re-hash the authority, bridge, reconciliation, and every used checkpoint;
5. reconstruct the exact A-arm raw grid and pooled summary; and
6. reproduce every reported Catfish contrast from that reconstructed summary.

Any mismatch leaves the output visibly incomplete and publishes no admissible
receipt.

## 6. Host and process gate

Execution remains restricted to Ubuntu hostname `5090`, Python `3.13.3`, NumPy
`2.5.2`, SGP4 `2.27`, and Torch distribution metadata `2.13.0`. A read-only live
query on `2026-08-31` confirmed these exact four server values; no scientific
artifact was opened.

The process gate must reject any active source matrix/arm or R7 evaluator even
when Python is wrapped by `env`, arguments use relative paths, or the script
token is not among the first three argv entries. Process cwd is resolved from
`/proc/PID/cwd`. Both matrices must also carry complete five-arm verification
receipts before evaluation.

## 7. Failure and recovery runbook

Normal Python exceptions and interrupts release only the lock owned by the
current PID and exact authority-bound work item. Private staging is removed;
the visible `.R7-INCOMPLETE.json` directory is retained. It is never silently
reused or treated as a result.

An uncatchable termination such as `SIGKILL` or host loss may leave both a stale
lock and an incomplete directory. Recovery is a human-audited, non-scientific
operation:

1. confirm there is no active source or R7 process and the recorded lock PID no
   longer exists;
2. validate the r5 master and record SHA-256 for the lock and every incomplete
   directory entry;
3. move, never delete, the stale lock and the entire incomplete output directory
   into a timestamped recovery folder outside the authority's expected output
   paths;
4. record the reason and operator in a recovery receipt; and
5. rerun the same pinned stage only after the expected create-only path is free.

No automated stale-lock deletion is authorized.

## 8. Claim ceiling

Every output retains all five labels:

- `500-EP PRELIMINARY`;
- `ONE TRAINED POLICY`;
- `MAIN-ONLY HELD-OUT TEST EVALUATION`;
- `NOT A CHAPTER 5 RESULT`; and
- `NOT FORMAL EFFICACY`.

R5 may establish only a preliminary direction for one trained policy. It does
not establish robustness, statistical efficacy, generalization, or a Chapter 5
result.

## 9. Execution checklist

- [x] R4 reviewed without inspecting scientific outcomes.
- [x] Source-prefix reuse retained; redundant A-arm retraining remains removed.
- [x] Ubuntu runtime identity checked read-only.
- [ ] R5 code and control-plane tests complete.
- [ ] R5 master frozen and all pins revalidated.
- [ ] Fresh Sol ultra and Opus max accept the exact R5 bytes.
- [ ] Pin-derived allowlist synced to the isolated Ubuntu snapshot.
- [ ] Both existing source matrices verified complete before bridge/evaluation.
- [ ] Results reported without sign filtering and within the claim ceiling.
