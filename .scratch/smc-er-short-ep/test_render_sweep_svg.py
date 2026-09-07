from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "smc_er_render_sweep_svg", HERE / "render_sweep_svg.py"
)
assert SPEC is not None and SPEC.loader is not None
R = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = R
SPEC.loader.exec_module(R)


SCHEMA = "multi-catfish-mcrl-short-ep-ee-users-sweep-v2"
ARMS = (
    "Baseline MODQN",
    "Full Multi-Catfish MCRL",
    "Full - C1",
    "Full - C2",
    "Full - C3",
)
USERS = (60, 80, 100, 120, 140)


def _payload() -> dict:
    rows = []
    for arm_index, arm in enumerate(ARMS):
        for user_index, users in enumerate(USERS):
            rows.append(
                {
                    "arm": arm,
                    "users": users,
                    "mean_ee_bits_per_j": (1.5 + arm_index * 0.1 + user_index * 0.02)
                    * 1_000_000,
                }
            )
    return {"schema": SCHEMA, "users": list(USERS), "summary": rows}


def _write_payload(tmp_path: Path, payload: dict, name: str = "sweep-summary.json") -> Path:
    source = tmp_path / name
    source.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return source


def test_valid_summary_renders_five_data_owned_curves(tmp_path):
    source = _write_payload(tmp_path, _payload())
    output = tmp_path / "ee-vs-users-short-ep.svg"

    result = R.render_sweep(source, output)

    assert result == output
    text = output.read_text(encoding="utf-8")
    assert text.startswith("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
    assert sum(
        text.count(f'<g id="curve-{R._slug(arm)}"') for arm in ARMS
    ) == 5
    assert text.count('id="point-') == 25
    assert "10EP engineering smoke — not efficacy evidence" in text
    assert "EE (Mbit/J)" in text
    assert "Number of users" in text
    assert 'font-family: "Times New Roman", Times, serif' in text
    assert 'data-ee-mbit-per-j="1.5"' in text
    assert 'data-ee-mbit-per-j="1.52"' in text
    for arm in ARMS:
        assert arm in text
    assert "NaN" not in text
    assert "Infinity" not in text
    assert "undefined" not in text


def test_render_is_byte_deterministic_for_same_source(tmp_path):
    source = _write_payload(tmp_path, _payload())
    first = tmp_path / "one.svg"
    second = tmp_path / "nested" / "two.svg"

    R.render_sweep(source, first)
    R.render_sweep(source, second)

    assert first.read_bytes() == second.read_bytes()


def test_output_is_not_overwritten(tmp_path):
    source = _write_payload(tmp_path, _payload())
    output = tmp_path / "existing.svg"
    output.write_text("keep this file", encoding="utf-8")

    with pytest.raises(R.OutputExistsError, match="output already exists"):
        R.render_sweep(source, output)

    assert output.read_text(encoding="utf-8") == "keep this file"


@pytest.mark.parametrize(
    ("label", "mutate", "message"),
    [
        ("schema", lambda p: p.update(schema="wrong-schema"), "schema"),
        (
            "arm count",
            lambda p: p["summary"].__setitem__(0, {**p["summary"][0], "arm": "only"}),
            "exactly 5 arms",
        ),
        (
            "point count",
            lambda p: p.__setitem__("summary", p["summary"][:-1]),
            "exactly 5 points",
        ),
        (
            "user mismatch",
            lambda p: p["summary"].__setitem__(0, {**p["summary"][0], "users": 61}),
            "users grid",
        ),
        (
            "nonfinite value",
            lambda p: p["summary"].__setitem__(
                0, {**p["summary"][0], "mean_ee_bits_per_j": float("nan")}
            ),
            "finite",
        ),
        (
            "missing value",
            lambda p: p["summary"][0].pop("mean_ee_bits_per_j"),
            "mean_ee_bits_per_j",
        ),
        (
            "duplicate user grid",
            lambda p: p.__setitem__("users", [60, 80, 80, 120, 140]),
            "unique",
        ),
    ],
)
def test_invalid_summary_fails_closed(tmp_path, label, mutate, message):
    payload = _payload()
    mutate(payload)
    source = _write_payload(tmp_path, payload, f"{label}.json")

    with pytest.raises(R.SweepRenderError, match=message):
        R.render_sweep(source, tmp_path / f"{label}.svg")


def test_duplicate_arm_rows_fail_closed(tmp_path):
    payload = _payload()
    payload["summary"][5]["arm"] = payload["summary"][0]["arm"]
    source = _write_payload(tmp_path, payload)

    with pytest.raises(R.SweepRenderError, match="duplicate arm/user point"):
        R.render_sweep(source, tmp_path / "duplicate.svg")


def test_duplicate_user_rows_fail_closed(tmp_path):
    payload = _payload()
    payload["summary"][1]["users"] = payload["summary"][0]["users"]
    source = _write_payload(tmp_path, payload)

    with pytest.raises(R.SweepRenderError, match="duplicate arm/user point"):
        R.render_sweep(source, tmp_path / "duplicate-user.svg")


def test_source_is_not_modified(tmp_path):
    payload = _payload()
    source = _write_payload(tmp_path, payload)
    before = source.read_bytes()

    R.render_sweep(source, tmp_path / "out.svg")

    assert source.read_bytes() == before
