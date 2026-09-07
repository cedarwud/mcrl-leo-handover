# V0.23 100-epoch pre-outcome screen bundle

This directory freezes the first current five-arm source-to-learner screen
before either running prerequisite was opened.  It contains no result and
does not authorize a non-GO branch.

Files:

- `V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md`: frozen parameters,
  admission, arm mapping, integrity decision, and next boundary.
- `V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.sha256`: contract digest.
- `V023-100E-MODEL-CONFIG.json`: exact runner-compatible current model config.
- `V023-100E-MODEL-CONFIG.sha256`: model-config digest.
- `V023-100E-POST-R7-PROVIDER-CONFIG.json`: canonical zero-argument provider
  factory input for the two currently running server roots.
- `V023-100E-POST-R7-PROVIDER-CONFIG.sha256`: provider-config byte digest.
- `V023-100E-LAUNCH-MANIFEST.sha256`: current contract/config/code/test closure
  for the conditional server launch.

A code/input manifest and server launcher are intentionally generated only
after the post-R7 factory passes independent review.  They must bind this
contract, the unchanged model config, and the eventual sealed input digests;
they may not change any parameter frozen here.
