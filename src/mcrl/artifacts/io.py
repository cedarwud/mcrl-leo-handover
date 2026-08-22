"""Checkpoint serialisation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import torch

from .models import CheckpointPayloadV1


def write_checkpoint(path: Path, payload: CheckpointPayloadV1) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload.to_dict(), target)
    return target


def read_checkpoint(
    path: Path, *, map_location: Any = "cpu"
) -> CheckpointPayloadV1:
    """Load a checkpoint.

    ``weights_only=False`` is required: the payload is a dict of metadata as
    well as tensors.  These files are produced by this project's own training
    runs and are not an untrusted input, but the flag is stated rather than
    inherited so the trust assumption is visible.
    """
    payload = torch.load(
        Path(path), map_location=map_location, weights_only=False
    )
    return CheckpointPayloadV1.from_dict(payload)
