"""Checkpoint payloads and their serialisation (W-12).

Ported from the source project's ``artifacts/`` package, trimmed to the four
names ``algorithms/modqn.py`` actually imports.  The source package is 863
lines across five modules and carries run-metadata, training-log-row, and
compatibility-shim types for artifact formats this project does not produce.

The one behavioural addition is a **format-version guard on read**: the
source accepts whatever ``format_version`` a file declares and reconstructs
regardless.  A checkpoint written by a future format would then load with
fields silently missing, which is the wrong failure for the thing that
carries a trained policy.
"""

from __future__ import annotations

from .models import CheckpointPayloadV1, CheckpointRuleV1
from .io import read_checkpoint, write_checkpoint

__all__ = [
    "CheckpointPayloadV1",
    "CheckpointRuleV1",
    "read_checkpoint",
    "write_checkpoint",
]
