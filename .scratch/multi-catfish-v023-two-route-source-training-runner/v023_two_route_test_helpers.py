"""Shared test access to the authenticated successor model configuration."""

from __future__ import annotations

from pathlib import Path

from ee_axis_two_route_model import EEAxisTwoRouteConfig


HERE = Path(__file__).resolve().parent
MODEL_CONFIG_PATH = (
    HERE.parents[1]
    / ".scratch/multi-catfish-v023-c1c2-successor/"
    "V023-C1C2-SUCCESSOR-MODEL-CONFIG.json"
)


def model_config() -> EEAxisTwoRouteConfig:
    """Load the byte-authenticated producer authority instead of literals."""

    from v023_two_route_source_training_runner import _load_model_config

    return _load_model_config(MODEL_CONFIG_PATH)


__all__ = ["MODEL_CONFIG_PATH", "model_config"]
