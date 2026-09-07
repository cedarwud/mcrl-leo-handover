# V0.23 current C1/Q1 and C2/Q2 live-artifact audit

Date: 2026-09-06
Status: **`VERIFIED_V020_BACKGROUND_ONLY`**
Claim ceiling: `SOURCE_ONLY_NO_SIMULATOR_NO_TEST_NO_EPISODE_EE`

This is a read-only audit. It hashes and parses the currently present V0.20
repriced source/fit closure. It does not import the simulator, call a selector,
sample a neutral source, run a learner, open TEST, or write an artifact.

## Binding correction

The frozen V0.23 contract binds Q1/Q2 background to **V0.20 repriced lineage
`2026092101`, rung `003000`**, checkpoint
`d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc`.
It does not bind to an R4 C3 output. R4/C3 source generation therefore cannot
be used as evidence that C1/C2 source objects exist.

| object | path | SHA-256 |
|---|---|---|
| V0.23 contract | `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` | `1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a` |
| V0.20 Q1/Q2 execution contract | `.scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-REPRICED-SUPERVISED-EXECUTION-CONTRACT-2026-09-04.md` | `ea36414aac87b3ef5ba48dbe753e73ff21a0e164d54cdb3edbb899b509edd48c` |
| V0.20 repricing contract | `.scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md` | `34732dd3f65ffebf760313c2ffd235e0ecbd406ba6065dbce5635778550ef4a9` |
| Q1 repricing receipt | `.scratch/multi-catfish-v020-c3-source-audit/q1-repricing/receipt.json` | `31f86b100fd5defabc9443e9c80e1e1c533993269be6f3ea3840d06c70f3b08c` |
| Q1 repricing manifest | `.scratch/multi-catfish-v020-c3-source-audit/q1-repricing/MANIFEST.sha256` | `77bc791a09b613116ad440d56bedb5d94485867eeb3d7a2485ff12832666223c` |
| Q2 repricing result | `.scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/result.json` | `4095380579d91661a40ae37f64a0c05fccdbe26f01f1cbb546f41a7e55234733` |
| V0.20 lineage authority | `.scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/authority.json` | `a05ee801c8f9d640b55f8ec984d874f149c30b868d1706d998f7e2053520078e` (body field: `50d32dae11b2906bb23a25893f4ba5c11d0f88197ee94fe7cd216677e8703d48`) |
| V0.20 fit result | `.scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/result.json` | `2c855edbf1157f12c158fae61728c5d385a82e6856feb280a900fc8ad8e70b99` |
| V0.20 fit status | `.scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/status.json` | `cf088fb962b4085fee3c2791fff4a3cbcf501729bad984a8bb6d7712188a0a82` |
| V0.20 deployed checkpoint | `.../lineage-2026092101-q2init-2026108101-rung-003000.pt` | `d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc` |

The frozen multiplier and normalization were also checked: lambda
`0x1.c3c0a7b6b86d3p+26` and kappa `0x1.2cea89d260f2ap+33`.

## C1/Q1 source bytes

The informed Q1 source is the seven E1 opening JSON files below. The source
manifest body digest is
`9ec832c71b29ad84e37856db1f5d237f07d177c62cc93fbb66de06d808184a0a`; the
manifest file itself hashes to
`57af6439de83d02b34923f77f3434e9c923c306fe3f3384a7ea21f7d7fafdc23`, and
`source-data/receipt.json` hashes to
`43fbb662badc8dac69c9203e537994072c3588f9f8130e03df2f2997936bced1`.
The source receipt and all seven explicit file entries agree.

| source path | split | total rows | C1 rows | file SHA-256 | dataset SHA-256 |
|---|---:|---:|---:|---|---|
| `artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/opening-2026092001.json` | TRAIN | 512 | 242 | `8c34b97c661b79569f1b5f4aca54187da0554f41baf06036bb95950e84dc0fd1` | `493029bca45d8328c58a684d77d363ac5045f79eab582e928491ac5de72507af` |
| `artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/opening-2026092002.json` | TRAIN | 491 | 235 | `35a1d7a3fc07fd3b28e6ae414b8a22ff5635d99656728ff43fe8bd74c860fed0` | `ceb821fa1316dc96f95a18d903c82054773083d9f0240ca2b1a51c28e347b52f` |
| `artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/opening-2026092003.json` | TRAIN | 526 | 256 | `fb4cc3d090b0f0db8daa355627021056423648f5275556e4126ad7f143282378` | `6c271173578d60d3764972dde47ce55639a4347ffa639635c807f0a4dccb3238` |
| `artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/opening-2026092004.json` | TRAIN | 491 | 235 | `265553bf8c917074b12abdaef1df50637ddf904a0a01e87ceb4d87237e9f8680` | `4c338d187305d7c54d5915633a7e243b854a2a8ee979decff38bcdf40d1ab79e` |
| `artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/opening-2026092005.json` | validation | 512 | 242 | `d17105376629205d8a75863e8ad5d568e4b68f8448241db33d1d8c3ad80d9933` | `c90f549eea3d2affcb60945cb360de599de65a13678240371818ad05dda103e8` |
| `artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/opening-2026092006.json` | validation | 512 | 242 | `2955d9de3ff889c888ea76ba571261ac94ba97609d26a101f10a151f58e7dd00` | `9be13300f9bd3d3a4d2ef933d1eb4b1dc61a965b73966eb209b8f7ed35b02820` |
| `artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/opening-2026092007.json` | validation | 498 | 228 | `80dca48e337f6e816fa45bfd0f47f4cce512b4f9534d87273db4487a03aec5ed` | `ee1cc093cc385ea2dd8939de99290fe3bbe666da54e3c19e3d7a60465dd95495` |

Verified totals: 3,542 rows, 1,680 admitted C1 rows (968 TRAIN + 712 internal
validation), and 1,862 C3 rows excluded. The q1 repricing receipt is PASS,
uses only admitted C1 rows, reconstructs the old target within its recorded
tolerance, and invokes no simulator or learner.

Trace to the Q1 fit is explicit in
`.scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_q1_q2.py`:
`_load_q1_split` (line 206) reads these rows, `_train_q1` (line 269) performs
`Q1_UPDATES = 10` full-batch `update_route("C1", ...)` calls (line 274), and
the fit authority/result bind the resulting Q1 head to deployment rung 10.
The runner hash is
`f55b882149ce49505c694423520a6a807d6a90babcbce340cb5ba449adea1814`; the
repricing implementation hash is
`a0acfe53b59b91281dbdd3d9ec813f35f3ea5461c835274edb54869489cd54fe`.

## C2/Q2 source bytes

The Q2 batch result authenticates a 21-shard V0.14 panel (seven worlds x
three lineages). For the V0.23-bound lineage `2026092101`, the seven source
NPZs, metadata files, repriced target arrays, and repricing audit files are:

| shard | source `source.npz` SHA-256 | `metadata.json` SHA-256 | repriced target `.npy` SHA-256 | repricing `audit.json` SHA-256 |
|---|---|---|---|---|
| `2026108001-2026092101` | `f5f38dafaa2ab32f13a4b472d9ee5288734ff3f0edf916b116a5a2a925acc163` | `7f48eeabc464cdf58cf7706a8ef1e15925cbac34385dff162e02e2ffc8d859b0` | `6ea0b9bfbb0ce77bd53f0fd53523c656de26cd2bbc92ca93c2dff332459d9351` | `ab6e1baf03b38778ccdee415e638d23dbf01e94d5ab10b6b0d0403861dfcb58f` |
| `2026108002-2026092101` | `d9bc1594415658b8b91356123ef15cfcdc9bca93ff74d3c12bc67e8f74622146` | `3faad0a1f682073aeec18d76e5c3f4e37a72883b749d8b24a02c49781d3f7521` | `0ec5fb3de667710f8dcbc5b4c103e48765aa8cb2ba9b50b559efa06ff2a7cf81` | `db2cb4d19597f5b87f3bd4b232b52dbf4506f72e54e0042c96bf369fc5db771e` |
| `2026108003-2026092101` | `62fda31be46858ad51c62c0463e205113269b596b77d573dd95446144f3542d8` | `ca44d733f9475b6e12cfd2b51535b6cfd2f1dd2aa6076b936fde87c5276c0530` | `2957c36bab447d4bb38f60c75ee31ec3209234a0001d365b437007c9782a7856` | `9245050a7dd2ce8ffcf3e44123f9bfc835a5ef7b1afed4ab6aa19e8a3838c375` |
| `2026108004-2026092101` | `79fc65b99493c5b0e1b5376abdb3f5e7700941f6af5de752b732f9da8a876467` | `15befe5983a2aae80e48325de84b079a4efde294c1051dfd74685e7cc6315541` | `874ecda1937951043cc6598667c716ef15f531aa2f41ff8a93c9227b9dc7fd27` | `5eaebf578c88ac72f4614d5393aca232546c0cbfe87c36b2103197945318e2b8` |
| `2026108005-2026092101` | `6791e4a6254ed828387a9b804abbe6ddfddfd89edfb36310f7c620f8eea7b212` | `acedfb6885419e46049b339d0a76d02a26efd329c739777281bf0509996bb0af` | `3b02e426e1ea57b8b878df4f8d65ab4bf513fa5f1ec6c76960841ee47e61ca0b` | `4105199827f35d9e29030987ba2dd01733c02078a5e43451728a6ebf42a27de6` |
| `2026108006-2026092101` | `0ac56cbfbbbcda608074fadeadcad0f3f7e923d42e049fd480a04d0a6a74c92f` | `493985a2b41a72a0abb04f4bcaf6ec9995d73046456b88d4344d0d97d0f87a84` | `96c06fa0324705eeac41b0d64ecb5eb9dd9f3581bf06efd5ea9cf0e47609b4a6` | `e994382ff95bffaecb4e6b6dd71fe9ea9048b9097a93e1195e0a1e65e318650c` |
| `2026108007-2026092101` | `08a180a5d4358cf0a489cb7783e1376eed4579e55476d44996d17866e624de30` | `dc3f46908eb4ca1f9530a995a68f4d799a06ed915182d5a73bd85d0e733c29ee` | `02e602510d362e6d7c082f4798f03c6342edf03fc5d4d6bc2def6301c9e348ba` | `d87092ba98c3af5b576a76dd9a20e5497a8209260bad7953f713b40d2da2e066` |

The source root is
`artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/source-panel/shards`;
the repriced targets and audit files are under
`.scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards`.
Each source NPZ is shape `(1000, 448)` for Q2 state and `(1000, 28)` for mask,
reference, and target surfaces; each repriced target is finite float64 shape
`(1000, 28)`. All 21 source/repriced/audit entries, not just the seven listed
above, were hash-checked by the loader.

The seven lineage-`2026092101` source receipts were canonicalized with the
same absolute-path receipt rule used by the V0.14 loader. Their aggregate is
`c6b6b93b36dbbda5123ff7603c675dc5f95e6d4b6c2cb1fa03b1e7b73c853736`, exactly
the V0.20 authority `source_sha256`.

Trace to the Q2 fit is explicit in
`.scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_q1_q2.py`:
`_all_q2_source_paths` (line 394) requires all 21 shards,
`_repriced_q2_targets` (line 401) selects the seven worlds for the current
lineage, and the loop at lines 518--547 performs the fixed rungs
`3,10,30,100,300,1000,3000`. The deployed combined checkpoint is rung 3000;
its Q1 head has update count 10 and its Q2 head has update count 3000.

## Sufficiency decision

Verified fact: these bytes are sufficient to reopen the **V0.20 repriced
Q1/Q2 background fit** required by the V0.23 preflight. The authority,
result/status, code hashes, seven-shard source closure, seven repriced targets,
and all seven checkpoint hashes agree. The Q1/Q2 reference-action NPZ is also
present and hashes to
`b9697389d282c088c48bb380a16dc28f0675a29706313b6a91cb6bee342cbcc0`.

Verified fact: these bytes are **not sufficient** to materialize the V0.23
five-arm C1/C2 source-ablation inputs with the existing selector APIs:

* C1 selector input is `C1DullRolloutRecord` in
  `src/mcrl/runtime/ee_axis_c1_selector.py`. It requires predecision
  `frontier_score`, `user_frontier_scores`, reference actions, and current
  `slot_tables`. The E1 C1 rows instead contain evaluated rates/powers and
  target labels; those selector fields are absent. Relabeling the rows would
  be an unsupported causal conversion.
* C2 neutral selection starts from `C2PredecisionAnchor` and
  `predecision_anchor_from_observation` in
  `src/mcrl/runtime/ee_axis_c2_neutral_source.py`, which require a
  contemporaneous candidate slot table and a physical reference action. The
  V0.14 source NPZ is explicitly `row_semantics =
  one-user-anchor-no-legal-action-expansion`; it contains compact states,
  masks, references, and surfaces, not the V0.23 temporal predecision
  opportunity universe.
* No source artifacts for the eight V0.23 worlds
  `2026121705`--`2026121712` are present. The current R4/C3 materials are
  implementation/scaffold files, not C1/C2 informed source objects.
* The existing neutral functions
  `sample_c1_cluster_matched_neutral_source` and
  `sample_c2_neutral_source` would create new neutral selections. They were
  not called, and no neutral outcomes were generated.

Inference: the current Q1/Q2 fit is valid as the pinned background, but a
future true five-arm V0.23 source ablation still needs a new source-stage
capture that materializes typed informed C1/C2 predecision selections before
any learner fit. This audit does not qualify C1/C2 or make an EE claim.

## Blockers and minimal next step

Blockers are therefore source-shape/lineage blockers, not hash failures:

1. No V0.23 predecision C1 dull-rollout records/current slot tables.
2. No V0.23 predecision C2 temporal anchor/opportunity universe.
3. No eight-world V0.23 source artifact/manifest from which equal-budget
   neutral controls could be derived without generating new data.

Minimal next implementation step, after separate source-stage authorization:
add a bridge to `run_v023_lcsrs_source_server.py` that persists, per TRAIN
world, the typed C1 `C1DullRolloutRecord` and C2
`C2PredecisionAnchor`/informed selection from contemporaneous predecision
inputs; then authenticate that receipt before invoking the existing neutral
selectors. Do not substitute the E1/V0.14 target-bearing bytes or an R4 C3
receipt for this bridge.

## Local validation

The isolated implementation and tests are:

* `live_artifact_loader.py` — read-only hash/manifest/source/checkpoint
  attestation; no selector/simulator/training imports.
* `test_live_artifact_loader.py` — four focused tests, including fail-closed
  hash drift and no-side-effect assertions.

Commands run:

```text
python3 .scratch/multi-catfish-v023-c1c2-live-artifact-audit/live_artifact_loader.py
python3 -m py_compile .scratch/multi-catfish-v023-c1c2-live-artifact-audit/live_artifact_loader.py
pytest -q .scratch/multi-catfish-v023-c1c2-live-artifact-audit/test_live_artifact_loader.py
```

Result: attestation completed in about 1.1 seconds; `4 passed`; no source,
authority, runtime, TEST, episode, simulator, or other scratch directory was
modified by this audit.
