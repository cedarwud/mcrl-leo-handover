#!/usr/bin/env python3
"""Render a measured EE sweep as a deterministic, editable SVG.

The renderer intentionally has no scientific-simulation or plotting-library
dependencies.  It consumes the already-produced sweep summary, validates the
small schema used by that receipt, and makes only the declared unit conversion
from bits/J to Mbit/J.  It is therefore suitable for a portable draft plot,
not for creating or imputing experiment data.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping, Sequence
from xml.sax.saxutils import escape, quoteattr


EXPECTED_SCHEMA = "multi-catfish-mcrl-short-ep-ee-users-sweep-v2"
EXPECTED_ARM_COUNT = 5
EXPECTED_POINT_COUNT = 5
EE_FIELD = "mean_ee_bits_per_j"
BITS_PER_MBIT = 1_000_000.0

SVG_WIDTH = 1600
SVG_HEIGHT = 920
PLOT_LEFT = 170.0
PLOT_TOP = 190.0
PLOT_RIGHT = 1160.0
PLOT_BOTTOM = 770.0
LEGEND_LEFT = 1210.0
LEGEND_TOP = 192.0
LEGEND_WIDTH = 345.0
COLOURS = (
    "#4E79A7",
    "#E15759",
    "#59A14F",
    "#B07AA1",
    "#F28E2B",
)


class SweepRenderError(ValueError):
    """Raised when a summary cannot be rendered without guessing."""


class OutputExistsError(SweepRenderError):
    """Raised when rendering would overwrite an existing path."""


@dataclass(frozen=True)
class SweepPoint:
    arm: str
    users: int
    ee_bits_per_j: float

    @property
    def ee_mbit_per_j(self) -> float:
        return self.ee_bits_per_j / BITS_PER_MBIT


def _is_existing_path(path: Path) -> bool:
    """Return true for regular paths and dangling symlinks alike."""

    return os.path.lexists(os.fspath(path))


def _finite_number(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SweepRenderError(f"{field} must be a finite number")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise SweepRenderError(f"{field} must be a finite number") from exc
    if not math.isfinite(number):
        raise SweepRenderError(f"{field} must be a finite number")
    return number


def _user_grid(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SweepRenderError(f"{field} must be a positive integer")
    return value


def _mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SweepRenderError(f"{field} must be an object")
    return value


def _parse_summary(payload: Any) -> tuple[tuple[int, ...], tuple[SweepPoint, ...]]:
    root = _mapping(payload, field="summary payload")
    schema = root.get("schema")
    if schema != EXPECTED_SCHEMA:
        raise SweepRenderError(
            f"schema must be {EXPECTED_SCHEMA!r}; got {schema!r}"
        )

    raw_users = root.get("users")
    if not isinstance(raw_users, list) or len(raw_users) != EXPECTED_POINT_COUNT:
        raise SweepRenderError(
            f"users must contain exactly {EXPECTED_POINT_COUNT} points"
        )
    users = tuple(
        _user_grid(value, field=f"users[{index}]")
        for index, value in enumerate(raw_users)
    )
    if len(set(users)) != len(users):
        raise SweepRenderError("users must be unique")
    # A numeric axis must run left-to-right even if the JSON list was emitted
    # in a different order.  The values themselves remain exclusively
    # data-owned; this only normalizes their plotting order.
    users = tuple(sorted(users))

    raw_rows = root.get("summary")
    expected_rows = EXPECTED_ARM_COUNT * EXPECTED_POINT_COUNT
    if not isinstance(raw_rows, list) or len(raw_rows) != expected_rows:
        raise SweepRenderError(
            "summary must contain exactly "
            f"{expected_rows} rows for {EXPECTED_ARM_COUNT} arms with "
            f"exactly {EXPECTED_POINT_COUNT} points each"
        )

    arm_points: dict[str, dict[int, SweepPoint]] = {}
    arm_order: list[str] = []
    for index, raw_row in enumerate(raw_rows):
        row = _mapping(raw_row, field=f"summary[{index}]")
        arm = row.get("arm")
        if not isinstance(arm, str) or not arm.strip():
            raise SweepRenderError(f"summary[{index}].arm must be a non-empty string")
        row_users = _user_grid(row.get("users"), field=f"summary[{index}].users")
        if row_users not in users:
            raise SweepRenderError(
                f"summary[{index}].users is not present in the users grid"
            )
        ee = _finite_number(row.get(EE_FIELD), field=f"summary[{index}].{EE_FIELD}")
        point = SweepPoint(arm=arm, users=row_users, ee_bits_per_j=ee)
        points_for_arm = arm_points.setdefault(arm, {})
        if arm not in arm_order:
            arm_order.append(arm)
        if row_users in points_for_arm:
            raise SweepRenderError(f"duplicate arm/user point: {arm!r}, {row_users}")
        points_for_arm[row_users] = point

    if len(arm_points) != EXPECTED_ARM_COUNT:
        raise SweepRenderError(
            f"summary must contain exactly {EXPECTED_ARM_COUNT} arms; "
            f"got {len(arm_points)}"
        )
    for arm in arm_order:
        points_for_arm = arm_points[arm]
        if len(points_for_arm) != EXPECTED_POINT_COUNT:
            raise SweepRenderError(
                f"arm {arm!r} must contain exactly {EXPECTED_POINT_COUNT} points"
            )
        if set(points_for_arm) != set(users):
            raise SweepRenderError(f"arm {arm!r} does not cover the users grid")

    ordered_points = tuple(
        point
        for arm in arm_order
        for point in (arm_points[arm][user] for user in users)
    )
    return users, ordered_points


def _load_summary(path: Path) -> tuple[tuple[int, ...], tuple[SweepPoint, ...]]:
    if not path.is_file():
        raise SweepRenderError(f"summary input is not a file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SweepRenderError(f"cannot read summary JSON: {path}: {exc}") from exc
    return _parse_summary(payload)


def _fmt(value: float, *, digits: int = 6) -> str:
    if not math.isfinite(value):
        raise SweepRenderError("non-finite value reached SVG renderer")
    text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def _fmt_compact(value: float) -> str:
    if not math.isfinite(value):
        raise SweepRenderError("non-finite value reached SVG renderer")
    text = format(value, ".12g")
    return "0" if text == "-0" else text


def _attr(name: str, value: Any) -> str:
    return f" {name}={quoteattr(str(value))}"


def _text(value: str) -> str:
    return escape(value)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not slug:
        raise SweepRenderError(f"arm label cannot produce an SVG id: {value!r}")
    return f"arm-{slug}"


def _nice_step(span: float, tick_count: int = 6) -> float:
    raw = span / max(tick_count - 1, 1)
    if not math.isfinite(raw) or raw <= 0:
        return 1.0
    exponent = math.floor(math.log10(raw))
    scale = 10.0**exponent
    normalised = raw / scale
    if normalised <= 1.0:
        factor = 1.0
    elif normalised <= 2.0:
        factor = 2.0
    elif normalised <= 5.0:
        factor = 5.0
    else:
        factor = 10.0
    return factor * scale


def _axis_ticks(values: Sequence[float], tick_count: int = 6) -> tuple[float, ...]:
    low = min(values)
    high = max(values)
    if low == high:
        padding = max(abs(low) * 0.05, 1.0)
        low -= padding
        high += padding
    span = high - low
    if not math.isfinite(span) or span <= 0:
        raise SweepRenderError("axis values have an unusable finite range")
    step = _nice_step(span, tick_count)
    start = math.floor(low / step)
    stop = math.ceil(high / step)
    ticks = tuple(i * step for i in range(start, stop + 1))
    if not ticks:
        raise SweepRenderError("could not construct finite axis ticks")
    return ticks


def _linear_map(value: float, low: float, high: float, pixel_low: float, pixel_high: float) -> float:
    if high == low:
        return (pixel_low + pixel_high) / 2.0
    return pixel_low + (value - low) / (high - low) * (pixel_high - pixel_low)


def _build_svg(users: Sequence[int], points: Sequence[SweepPoint]) -> str:
    arms: list[str] = []
    by_arm: dict[str, list[SweepPoint]] = {}
    for point in points:
        if point.arm not in by_arm:
            arms.append(point.arm)
            by_arm[point.arm] = []
        by_arm[point.arm].append(point)

    slugs = [_slug(arm) for arm in arms]
    if len(set(slugs)) != len(slugs):
        raise SweepRenderError("arm labels collide after SVG id normalization")

    y_values = tuple(point.ee_mbit_per_j for point in points)
    y_ticks = _axis_ticks(y_values)
    y_low, y_high = y_ticks[0], y_ticks[-1]
    try:
        x_values = tuple(float(user) for user in users)
    except (OverflowError, ValueError) as exc:
        raise SweepRenderError("users grid cannot be represented on a finite axis") from exc
    if not all(math.isfinite(value) for value in x_values):
        raise SweepRenderError("users grid cannot be represented on a finite axis")
    x_low, x_high = min(x_values), max(x_values)
    if x_low == x_high:
        padding = max(abs(x_low) * 0.05, 1.0)
        x_low -= padding
        x_high += padding

    x_px = {
        user: _linear_map(float(user), x_low, x_high, PLOT_LEFT, PLOT_RIGHT)
        for user in users
    }

    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg"'
            f'{_attr("width", SVG_WIDTH)}{_attr("height", SVG_HEIGHT)}'
            f'{_attr("viewBox", f"0 0 {SVG_WIDTH} {SVG_HEIGHT}")}'
            f'{_attr("role", "img")}{_attr("aria-labelledby", "plot-title plot-description")}>'
        ),
        '<title id="plot-title">Short-EP energy-efficiency sweep</title>',
        '<desc id="plot-description">',
        _text(
            "Five measured arms across the users grid. "
            "Values are the summary field mean_ee_bits_per_j converted from bits/J to Mbit/J."
        ),
        '</desc>',
        '<style><![CDATA[',
        '  .figure-text { font-family: "Times New Roman", Times, serif; fill: #1F2933; }',
        '  .axis-text { font-size: 20px; }',
        '  .tick-text { font-size: 18px; }',
        '  .title-text { font-size: 30px; font-weight: 700; }',
        '  .subtitle-text { font-size: 21px; }',
        '  .note-text { font-size: 16px; fill: #52606D; }',
        '  .grid-line { stroke: #CBD2D9; stroke-width: 1; stroke-dasharray: 3 7; }',
        '  .axis-line { stroke: #52606D; stroke-width: 2; }',
        '  .curve-line { fill: none; stroke-width: 3.5; stroke-linejoin: round; stroke-linecap: round; }',
        ']]></style>',
        '<g id="background" aria-label="Figure background">',
        f'<rect id="canvas"{_attr("x", 0)}{_attr("y", 0)}{_attr("width", SVG_WIDTH)}{_attr("height", SVG_HEIGHT)}{_attr("fill", "#FFFFFF")}/>',
        '</g>',
        '<g id="header" class="figure-text" aria-label="Figure heading">',
        f'<text id="heading" class="title-text"{_attr("x", 80)}{_attr("y", 70)}>Short-EP EE sweep</text>',
        f'<text id="engineering-warning" class="subtitle-text"{_attr("x", 80)}{_attr("y", 108)}>{_text("10EP engineering smoke — not efficacy evidence")}</text>',
        f'<text id="data-note" class="note-text"{_attr("x", 80)}{_attr("y", 136)}>{_text("Summary field: mean_ee_bits_per_j; conversion: bits/J ÷ 10^6")}</text>',
        '</g>',
        '<g id="plot-panel" aria-label="Energy-efficiency plot">',
        f'<rect id="plot-background"{_attr("x", PLOT_LEFT)}{_attr("y", PLOT_TOP)}{_attr("width", PLOT_RIGHT - PLOT_LEFT)}{_attr("height", PLOT_BOTTOM - PLOT_TOP)}{_attr("fill", "#F8FAFC")}{_attr("stroke", "#D9E2EC")}{_attr("stroke-width", 1)}/>',
        '<g id="grid" aria-label="Plot grid">',
    ]

    for index, tick in enumerate(y_ticks):
        y = _linear_map(tick, y_low, y_high, PLOT_BOTTOM, PLOT_TOP)
        lines.append(
            f'<line id="grid-y-{index}" class="grid-line"'
            f'{_attr("x1", _fmt(PLOT_LEFT, digits=3))}{_attr("y1", _fmt(y, digits=3))}'
            f'{_attr("x2", _fmt(PLOT_RIGHT, digits=3))}{_attr("y2", _fmt(y, digits=3))}/>'
        )
    for index, user in enumerate(users):
        x = x_px[user]
        lines.append(
            f'<line id="grid-x-{index}" class="grid-line"'
            f'{_attr("x1", _fmt(x, digits=3))}{_attr("y1", _fmt(PLOT_TOP, digits=3))}'
            f'{_attr("x2", _fmt(x, digits=3))}{_attr("y2", _fmt(PLOT_BOTTOM, digits=3))}/>'
        )
    lines.extend([
        '</g>',
        '<g id="axes" aria-label="Plot axes">',
        f'<line id="x-axis" class="axis-line"{_attr("x1", PLOT_LEFT)}{_attr("y1", PLOT_BOTTOM)}{_attr("x2", PLOT_RIGHT)}{_attr("y2", PLOT_BOTTOM)}/>',
        f'<line id="y-axis" class="axis-line"{_attr("x1", PLOT_LEFT)}{_attr("y1", PLOT_TOP)}{_attr("x2", PLOT_LEFT)}{_attr("y2", PLOT_BOTTOM)}/>',
        '</g>',
        '<g id="tick-labels" class="figure-text" aria-label="Axis tick labels">',
    ])
    for index, tick in enumerate(y_ticks):
        y = _linear_map(tick, y_low, y_high, PLOT_BOTTOM, PLOT_TOP)
        lines.append(
            f'<text id="y-tick-{index}" class="tick-text" text-anchor="end"'
            f'{_attr("x", _fmt(PLOT_LEFT - 16, digits=3))}{_attr("y", _fmt(y + 6, digits=3))}>'
            f'{_text(_fmt_compact(tick))}</text>'
        )
    for index, user in enumerate(users):
        x = x_px[user]
        lines.append(
            f'<text id="x-tick-{index}" class="tick-text" text-anchor="middle"'
            f'{_attr("x", _fmt(x, digits=3))}{_attr("y", _fmt(PLOT_BOTTOM + 34, digits=3))}>'
            f'{_text(str(user))}</text>'
        )
    lines.extend([
        '</g>',
        '<g id="axis-labels" class="figure-text" aria-label="Axis labels">',
        f'<text id="axis-label-x" class="axis-text" text-anchor="middle"{_attr("x", _fmt((PLOT_LEFT + PLOT_RIGHT) / 2, digits=3))}{_attr("y", _fmt(PLOT_BOTTOM + 82, digits=3))}>Number of users</text>',
        f'<text id="axis-label-y" class="axis-text" text-anchor="middle" transform="rotate(-90)"{_attr("x", _fmt(-(PLOT_TOP + PLOT_BOTTOM) / 2, digits=3))}{_attr("y", 56)}>EE (Mbit/J)</text>',
        '</g>',
        '<g id="curves" aria-label="Measured energy-efficiency curves">',
    ])

    for colour, arm, slug in zip(COLOURS, arms, slugs):
        arm_rows = by_arm[arm]
        coordinates = [
            (
                x_px[point.users],
                _linear_map(point.ee_mbit_per_j, y_low, y_high, PLOT_BOTTOM, PLOT_TOP),
            )
            for point in arm_rows
        ]
        path_data = " ".join(
            ("M" if index == 0 else "L")
            + _fmt(x, digits=3)
            + " "
            + _fmt(y, digits=3)
            for index, (x, y) in enumerate(coordinates)
        )
        lines.extend([
            f'<g id="curve-{slug}" aria-label={quoteattr(arm)}>',
            f'<title id="curve-{slug}-title">{_text(arm)}</title>',
            f'<path id="curve-{slug}-line" class="curve-line"{_attr("d", path_data)}{_attr("stroke", colour)}{_attr("data-arm", arm)}/>',
            f'<g id="curve-{slug}-points" aria-label={quoteattr(arm + " measured points")}>',
        ])
        for point in arm_rows:
            x = x_px[point.users]
            y = _linear_map(point.ee_mbit_per_j, y_low, y_high, PLOT_BOTTOM, PLOT_TOP)
            point_id = f"point-{slug}-u-{point.users}"
            lines.append(
                f'<circle id="{point_id}"{_attr("cx", _fmt(x, digits=3))}'
                f'{_attr("cy", _fmt(y, digits=3))}{_attr("r", 7)}'
                f'{_attr("fill", colour)}{_attr("stroke", "#FFFFFF")}{_attr("stroke-width", 2)}'
                f'{_attr("data-arm", arm)}{_attr("data-users", point.users)}'
                f'{_attr("data-ee-bits-per-j", _fmt_compact(point.ee_bits_per_j))}'
                f'{_attr("data-ee-mbit-per-j", _fmt_compact(point.ee_mbit_per_j))}/>'
            )
        lines.extend(['</g>', '</g>'])
    lines.extend([
        '</g>',
        '</g>',
        '<g id="legend" class="figure-text" aria-label="Experiment arm legend">',
        f'<rect id="legend-background"{_attr("x", LEGEND_LEFT)}{_attr("y", LEGEND_TOP)}{_attr("width", LEGEND_WIDTH)}{_attr("height", 310)}{_attr("rx", 10)}{_attr("fill", "#FFFFFF")}{_attr("stroke", "#D9E2EC")}{_attr("stroke-width", 1)}/>',
        f'<text id="legend-title" class="axis-text"{_attr("x", LEGEND_LEFT + 24)}{_attr("y", LEGEND_TOP + 38)}>Experiment arms</text>',
    ])
    for index, (colour, arm, slug) in enumerate(zip(COLOURS, arms, slugs)):
        y = LEGEND_TOP + 78 + index * 42
        lines.extend([
            f'<line id="legend-swatch-{slug}" class="curve-line"{_attr("x1", LEGEND_LEFT + 24)}{_attr("y1", _fmt(y - 6, digits=3))}{_attr("x2", LEGEND_LEFT + 66)}{_attr("y2", _fmt(y - 6, digits=3))}{_attr("stroke", colour)}/>',
            f'<circle id="legend-marker-{slug}"{_attr("cx", LEGEND_LEFT + 45)}{_attr("cy", _fmt(y - 6, digits=3))}{_attr("r", 6)}{_attr("fill", colour)}{_attr("stroke", "#FFFFFF")}{_attr("stroke-width", 1.5)}/>',
            f'<text id="legend-label-{slug}" class="axis-text"{_attr("x", LEGEND_LEFT + 84)}{_attr("y", _fmt(y, digits=3))}>{_text(arm)}</text>',
        ])
    lines.extend([
        '</g>',
        '<g id="footer" class="figure-text" aria-label="Figure scope note">',
        f'<text id="footer-note" class="note-text"{_attr("x", 80)}{_attr("y", 855)}>{_text("Draft visualization only; the 10EP engineering smoke is not efficacy evidence.")}</text>',
        '</g>',
        '</svg>',
    ])
    return "\n".join(lines) + "\n"


def _atomic_write_new(path: Path, content: str) -> None:
    """Create ``path`` atomically without ever replacing an existing path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if _is_existing_path(path):
        raise OutputExistsError(f"output already exists: {path}")
    temporary: str | None = None
    try:
        fd, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=os.fspath(path.parent)
        )
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        try:
            # A hard link is an atomic no-replace operation on the same
            # filesystem; unlike os.replace it cannot clobber a race-created
            # destination.
            os.link(temporary, os.fspath(path))
        except FileExistsError as exc:
            raise OutputExistsError(f"output already exists: {path}") from exc
        try:
            directory_fd = os.open(
                os.fspath(path.parent), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            )
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def render_sweep(summary_path: Path | str, output_path: Path | str) -> Path:
    """Validate ``summary_path`` and atomically create one editable SVG."""

    source = Path(summary_path)
    output = Path(output_path)
    if _is_existing_path(output):
        raise OutputExistsError(f"output already exists: {output}")
    users, points = _load_summary(source)
    svg = _build_svg(users, points)
    _atomic_write_new(output, svg)
    return output


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True, help="sweep-summary.json")
    parser.add_argument("--output", type=Path, required=True, help="new SVG path")
    args = parser.parse_args(argv)
    try:
        output = render_sweep(args.summary, args.output)
    except (SweepRenderError, OSError) as exc:
        parser.error(str(exc))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
