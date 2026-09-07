# V0.23 LC-SRS gate launch decision

Status: **FROZEN EXECUTION GO — V0.23 GATE ONLY**  
Date: 2026-09-05 (Asia/Taipei)  
Compute class: heavy CPU; execute only on the Ubuntu server.

## Decision

Authorize exactly one fresh execution of the frozen V0.23 LC-SRS
source-to-learner and composition gate. This decision does not authorize TEST,
episode-policy training, 100/500/1500/3000/9000 episodes, method rescue, or a
paper efficacy claim.

The gate remains bound to:

- method contract SHA-256
  `1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a`;
- execution addendum SHA-256
  `486568d017de84bfba5aa8bb65f634998446ac4b3ad471795b9055085e8f5070`;
- eight TRAIN-development worlds `2026121705` through `2026121712`;
- student seeds `2026135101`, `2026135102`, and `2026135103`;
- 32 common-field draws, 48 fixed 2000-update fits, and 48 literal
  compositions; and
- the final post-decision `PREFLIGHT-MANIFEST.sha256` generated after this
  decision document is added as a manifest binding. The launcher must reject
  any digest or file mismatch.

## Pre-launch evidence

- The implementation snapshot immediately before this decision was sealed as
  preflight SHA-256
  `224f35c7f4d292a42068e354621e26c6c324b606f321feb356c90a68429f74c1`.
- The complete non-simulator W190--W204 plus scaffold/source-adapter suite
  passed on those bytes.
- A fresh GPT-6 Astra Ultra closure audit checked the five previously reported
  blockers and returned the exact token `LAUNCH_READY`. It verified the
  placebo literal, cross-arm learned-role boundary, full learner configuration
  and initialization hashes, immutable result closure, and reachable
  mechanics/INSUFFICIENT_PAIRS decisions.
- The server precheck confirmed 20 logical CPUs, 82 GiB available RAM,
  approximately 2.1 TiB free disk, the Python environment, and the frozen TLE
  root.

These are execution-readiness facts, not scientific evidence that C3 or the
full Multi-Catfish policy improves EE.

## Execution boundary

Launch only through
`.scratch/multi-catfish-v023-c3-observability/sync_launch_v023_lcsrs_gate_server.sh`
using the fresh server root and tmux identity declared there. The launcher must
run local and remote preflight, the bound non-heavy tests, source generation,
the source-stage decision, fixed fits only when coverage permits, literal
composition, independent verification, and immutable result sealing.

Accept only the frozen Section-14 tokens. `INVALID_RUN` requires a new
pre-outcome execution contract; no in-place repair is allowed. A valid C3 GO
still does not authorize episode training unless `context_status` also permits
the separately frozen next-stage contract.

## Controller token

`GO_V023_LCSRS_GATE_ON_UBUNTU_SERVER`
