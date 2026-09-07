"""Small serialization helpers for engineering-lane scratch outputs only."""

from __future__ import annotations

from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from typing import Any

import torch


def export_torch_mapping(value: Mapping[str, Any], path: Path) -> Path:
    if not isinstance(value, Mapping):
        raise TypeError("scratch checkpoint value must be a mapping")
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite scratch checkpoint: {destination}")
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise FileNotFoundError(f"scratch checkpoint parent is unavailable: {destination.parent}")
    stream = BytesIO()
    torch.save(dict(value), stream)
    destination.write_bytes(stream.getvalue())
    return destination


def reload_torch_mapping(path: Path) -> Mapping[str, Any]:
    source = Path(path)
    try:
        value = torch.load(source, map_location="cpu", weights_only=False)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise ValueError("scratch checkpoint cannot be reloaded") from error
    if not isinstance(value, Mapping):
        raise TypeError("reloaded scratch checkpoint must be a mapping")
    return value
