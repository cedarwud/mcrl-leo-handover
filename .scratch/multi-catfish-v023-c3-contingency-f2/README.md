# V0.23 C3 contingency F2 implementation

This directory implements only the pre-outcome ladder's shared four-world F2
oracle screen. It does not authorize a local simulator run, learner update,
TEST evaluation, efficacy claim, F3, or F4. Heavy unit execution belongs on
the Ubuntu server after a separately frozen launch authority admits the exact
survivors of a sealed F1 receipt.

## Frozen panel and mechanics

- TRAIN worlds: `2026121721`, `2026121722`, `2026121723`, `2026121724`.
- Frozen Q1+Q2 lineages: `2026092101`, `2026092102`, `2026092103`.
- Exactly ten canonical decision steps `0..9` per world x lineage unit.
- Exactly 100 users. An all-false native mask selects `NO_OP_ACTION` and emits
  no unilateral candidate.
- Matched keyed fields:
  `KeyedFadingField.from_components("MCRL_V023_LCSRS_C3_OBSERVABILITY_V1", world)`.
  Candidate and lineage do not enter the field key.
- BASE is masked `argmax(Q1+Q2)`. An admitted candidate is masked
  `argmax(Q1+Q2+z/kappa)`, where `z` is the raw-bit D or F target returned by
  F0 and `kappa = 10097071012.757404` bits.
- One immutable unilateral physical tape supplies both D and F targets. Only
  F1 survivors receive a candidate deployment evaluation; a non-survivor is
  recorded as a non-evaluated BASE placeholder, never screened as F2 evidence.
- The BASE joint action advances the shared trajectory after every step.

The runner imports the corrected F1 runner normally. It reuses F1's physical
runtime setup, Q1+Q2 surface builder, unilateral enumerator, profile writer,
F0 `compute_c3_targets`, `masked_argmax_q12_plus_z`, and
`evaluate_kill_rules`. It neither copies nor modifies those implementations
and performs no `sys.modules` aliasing. The existing V0.20 multi-lineage head
loader is also imported normally because the later physical adapter is
intentionally fixed to lineage `2026092101`.

## Frozen Q1+Q2 authorities

F2 authenticates each lineage exactly as F1 authenticates `2026092101`: one
and only one matching rung-003000 checkpoint, exact checkpoint bytes, exact
authority-file bytes, recomputed authority body seal, and the expected
lineage/Q2-initialization/update/contract/no-TEST semantics.

| lineage | Q2 init | checkpoint sha256 | authority body sha256 | authority file sha256 |
| --- | ---: | --- | --- | --- |
| `2026092101` | `2026108101` | `d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc` | `50d32dae11b2906bb23a25893f4ba5c11d0f88197ee94fe7cd216677e8703d48` | `a05ee801c8f9d640b55f8ec984d874f149c30b868d1706d998f7e2053520078e` |
| `2026092102` | `2026108102` | `bb45bed30465f8be0ea9a1463c3b6e958d8f8b90cf11b4cd8e5d56a71f4b7057` | `3b50f66bf3cf3f26adce15935adefd5751954cfffe79c72e7a02150c851bfc1f` | `5a5bed3617437bbc981afc4de0b5880a3a5c91d3e3d857ac825527ae728ce64f` |
| `2026092103` | `2026108103` | `32b5accfa1595ff19ddc11779402b5c86e115b883d04c6c5cbf90434ee32d44c` | `503122a09c0c02ccd52aec55b50448950de00b8a194cd83ed4dda37f3f82a30f` | `20f7ed79b1797e4ff8e6d2dc6de086b44341a0d0c6e7725a110027b062ff50c0` |

If any lineage has zero or multiple matching checkpoints, any digest differs,
or any authority seal/semantic check differs, preflight and execution fail
closed. There is no fallback lineage or checkpoint selection.

## F1 admission

The launch authority must carry the absolute path and SHA-256 of the immutable
F1 result plus the complete ordered survivor set: `["D"]`, `["F"]`, or
`["D", "F"]`. F2 reopens and authenticates the F1 receipt and derives the
survivor set from both D/F rule bundles. A declared set that differs from the
receipt is rejected. If neither survived, the runner exits with
`F2_NOT_ADMITTED`; no unit or terminal receipt is created.

Minimal launch-authority shape (values must exactly match the generated F2
preflight and authenticated F1 result):

```json
{
  "schema": "multi-catfish-mcrl-v023-c3-contingency-f2-v1-launch-authority",
  "status": "FROZEN_LAUNCH_AUTHORITY",
  "claim_ceiling": "TRAIN_DEVELOPMENT_C3_CONTINGENCY_F2_ORACLE_SCREEN_NO_EFFICACY_NO_TEST",
  "preflight_manifest": {
    "path": ".scratch/multi-catfish-v023-c3-contingency-f2/F2-PREFLIGHT-MANIFEST.json",
    "sha256": "<sha256>"
  },
  "f1_result": {
    "path": "/absolute/path/to/sealed/f1/receipt.json",
    "sha256": "<sha256>",
    "surviving_candidates": ["D", "F"]
  },
  "bindings": "<exact bindings object from F2 preflight>",
  "test_split_opened": false,
  "episode_training": false,
  "learner_update": false
}
```

## Unit publication, resume, and merge

Build the immutable preflight after code review:

```bash
./.venv/bin/python .scratch/multi-catfish-v023-c3-contingency-f2/build_f2_preflight_manifest.py
./.venv/bin/python .scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py --dry-run
```

The controller may dispatch the twelve heavy units in parallel on the Ubuntu
server:

```bash
./.venv/bin/python .scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py \
  --unit 2026121721:2026092101 \
  --preflight-manifest .scratch/multi-catfish-v023-c3-contingency-f2/F2-PREFLIGHT-MANIFEST.json \
  --launch-authority /absolute/path/to/f2-launch-authority.json \
  --tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 \
  --output /absolute/path/to/f2-output
```

Each successful unit is assembled in a private staging directory and then
atomically published as `units/<world>-<lineage>/`. Its tape, tape manifest,
and receipt are mode `0444`. A repeated unit command authenticates and skips a
complete unit; it never regenerates or overwrites it. A killed incomplete
staging directory is not a complete unit and is ignored by resume.

After all twelve units exist:

```bash
./.venv/bin/python .scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py \
  --merge \
  --preflight-manifest .scratch/multi-catfish-v023-c3-contingency-f2/F2-PREFLIGHT-MANIFEST.json \
  --launch-authority /absolute/path/to/f2-launch-authority.json \
  --output /absolute/path/to/f2-output
```

Merge authenticates all twelve tapes, manifests, and receipts against their
contents, code/formula bindings, preflight, F1 result, unit identity, and file
modes. Any missing, malformed, non-finite, writable, or inconsistent unit
propagates globally to one write-once `INVALID_RUN` terminal receipt.

## Pass rule and outcomes

For each admitted candidate, merge pools interval bits and network joules over
all 120 candidate/base step profiles, then separately pools the three lineages
within each world and the four worlds within each lineage. Passing requires
all of the following:

1. candidate pooled ratio-of-sums EE is strictly above BASE;
2. candidate direction is strictly positive in at least 3/4 worlds;
3. candidate direction is strictly positive in at least 2/3 lineages;
4. pooled service fraction is at least `BASE - 0.001`; and
5. every mechanics and provenance receipt is complete and valid.

D is adjudicated first. Outcomes are `F2_PASS_D`, `F2_PASS_F` only when D did
not pass and F independently passes, `F2_NO_SUPPORT`, or globally
`INVALID_RUN`. Every receipt carries the claim ceiling
`TRAIN_DEVELOPMENT_C3_CONTINGENCY_F2_ORACLE_SCREEN_NO_EFFICACY_NO_TEST`.

## Tests

The suite uses producer-built synthetic tapes and does not open a TLE archive
or simulator:

```bash
./.venv/bin/python -m pytest -q .scratch/multi-catfish-v023-c3-contingency-f2
```
