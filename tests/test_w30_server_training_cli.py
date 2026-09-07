"""W-30 — the server launcher cannot invent a main learning rate."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_launcher():
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_server_training.py"
    spec = importlib.util.spec_from_file_location("run_server_training", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pipeline_is_the_default_and_has_no_learning_rate_override():
    launcher = _load_launcher()
    args = launcher.parse_args([])
    assert args.mode == "pipeline"
    assert args.learning_rate is None
    assert args.probe_summary == launcher.CORRECTED_PROBE_SUMMARY

    with pytest.raises(SystemExit):
        launcher.parse_args(["pipeline", "--learning-rate", "0.003"])


def test_manual_main_requires_an_explicit_declared_learning_rate():
    launcher = _load_launcher()
    with pytest.raises(SystemExit):
        launcher.parse_args(["main"])

    args = launcher.parse_args(["main", "--learning-rate", "0.003"])
    assert args.learning_rate == pytest.approx(0.003)

    with pytest.raises(SystemExit):
        launcher.parse_args(["main", "--learning-rate", "0.004"])


def test_manual_main_never_reports_a_noncomplete_result_as_success(
    monkeypatch, tmp_path, capsys
):
    launcher = _load_launcher()
    from mcrl.runtime import training_pipeline

    monkeypatch.setattr(
        training_pipeline,
        "validate_server_setup",
        lambda _path, **_kwargs: object(),
    )
    monkeypatch.setattr(
        training_pipeline,
        "run_main_training",
        lambda *_args, **_kwargs: {
            "status": "nonfinite",
            "learning_rate": 0.003,
            "prereg_digest": "test",
        },
    )

    exit_code = launcher.main(
        [
            "main",
            "--learning-rate",
            "0.003",
            "--out-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code != 0
    assert "main complete" not in captured.out
    assert "status=nonfinite" in captured.err
