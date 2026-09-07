# Evidence copies and limits

> **PROVISIONAL_V0.18_NO_LEARNED_OR_EFFICACY_CLAIM**

The JSON files here are copied evidence, not a new authority. Their original
paths and SHA-256 values are listed in `PACKAGE-MANIFEST.md` and authenticated
by this package's `MANIFEST.sha256`.

## Analytic panel

`analytic-panel-result.json` is the finalized V0.18 four-world, three-lineage
TRAIN analytic diagnostic. Its mechanical decision is
`PASS_ANALYTIC_DIAGNOSTIC`. It compares BASE, EXACT_ZR, and NOMINAL_ZR under
the frozen learned Q1+Q2 background. It used no optimizer, learned Q3,
episode-policy training, or TEST split. The headline ratios are diagnostic
support for the next learner attempt only.

## Old-seed smoke

`old-seed-smoke-metadata.json`, `old-seed-smoke-bridge.json`,
`old-seed-smoke-harvest.json`, and the completion/log files are a real TLE
source-wiring smoke. It completed with 1,000 source rows and exit code 0. It
was run before the final code-manifest provenance fields were propagated, so
it must not be described as the final V0.18 provenance closure, a learner
result, or EE efficacy evidence. The raw `source.npz` is intentionally not
bundled here; its metadata and digests are sufficient for authoring status.

## Pending evidence

There is intentionally no learned-Q3 result, no 100-update gate result, no
physical five-arm result, and no long-episode result in this package. Do not
manufacture any of them from historical artifacts.

