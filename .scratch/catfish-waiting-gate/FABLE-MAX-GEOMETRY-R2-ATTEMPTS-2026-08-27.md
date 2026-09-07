# Fable Max geometry/R2 review attempts

## Material Passport

- Requested model alias: `fable`
- Canonical expected model: `claude-fable-5`
- Requested effort: `max`
- Origin Date: 2026-08-27
- Verification Status: `NO_REVIEW_RESULT_PROVIDER_TIMEOUT`
- Scientific verdict: none
- Review credit: none

## Locked targets

- `docs/decisions/ADR-002-proposed-hobs-primary-geometry.md`
  - SHA-256: `1498bfff678f2a63d79a4a69153c5f0d4aa5e84c797ea2a54dba91fe394e2869`
- `docs/R2-PHYS-PROVENANCE-MATRIX-2026-08-26.md`
  - SHA-256: `32a82678ca734438f2dad0dec9d2dea7b7e723712bc60c27d36e4c2a0f9065b1`

## Attempts after the reported 00:10 Asia/Taipei reset

| Route | Returned session ID | Wall duration | Input/output tokens | Terminal result |
|---|---|---:|---:|---|
| fresh XML prompt | `192f32d4-5869-469a-9560-b66422b3bc71` | 179,519 ms | `0 / 0` | `api_error: Request timed out` |
| clean fresh retry | `1e85e308-c2d6-4cfd-bdd5-f0f860275889` | 181,207 ms | `0 / 0` | `api_error: Request timed out` |
| resume saved v0.2 session `51ba0c45-e9fc-473f-8882-87f07c0b2a16` | `51ba0c45-e9fc-473f-8882-87f07c0b2a16` | 186,866 ms | `0 / 0` | `api_error: Request timed out` |

All three calls used `--model fable --effort max --output-format json` through
the native Claude CLI. None reached model input, produced review text, or
consumed billable model tokens. They therefore provide no approval or rejection
of the targets.

## Stop rule and fallback

The identical zero-token failure repeated across fresh and resumed routes, so
the same call will not be retried again in this gate. A Claude Opus Max review
may be collected as explicitly labelled fallback evidence, but it cannot satisfy
or be reported as the pending Fable review. Fable may be retried later only
after an external provider-state change.

The attempted Opus Max fallback on the same saved session also returned
`api_error: Request timed out` after 180,369 ms with zero input/output tokens
(UUID `f139400f-7c58-4ee5-b5f5-6a3c00b35eb4`). This indicates a current Claude
provider/session path failure rather than a model-specific Fable verdict. No
further Claude retry is authorised until provider state changes.
