#!/usr/bin/env python3
"""Build the sealed a-r0 off-axis required-power / pooled-EE figure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))

from mcrl.physics_v025.adapter import build_shared_tape, score_setting  # noqa: E402
from mcrl.physics_v025.architectures import Geometry, Link  # noqa: E402
from mcrl.physics_v025.channel import transmit_gain_linear  # noqa: E402
from mcrl.physics_v025.energy import HardwareInventory  # noqa: E402
from mcrl.physics_v025.matrix import MATRIX_SETTINGS, run_setting_for  # noqa: E402
from mcrl.physics_v025.tapes import canonical_bytes, digest_payload  # noqa: E402


ANGLES_DEG = (0.0, 0.5, 1.0, 1.5, 2.0)
PATH_FACTOR_WITHOUT_TX_GAIN = 5.0e-16
BEAM = (99_999, 0)


def off_axis_rows() -> list[dict[str, object]]:
    setting = next(row for row in MATRIX_SETTINGS if row.label == "a-r0")
    rows = []
    for angle in ANGLES_DEG:
        gain = float(transmit_gain_linear(angle)) * PATH_FACTOR_WITHOUT_TX_GAIN
        geometry = Geometry(
            (Link(0, BEAM, 0, gain, gain),),
            np.zeros((1, 1), dtype=np.float64),
            np.zeros((1, 1), dtype=np.float64),
        )
        tape = build_shared_tape(
            "a-r",
            tuple((index * 0.640, geometry) for index in range(48)),
            HardwareInventory.fixed((BEAM,)),
            roster=(0,),
        )
        score = score_setting(tape, setting)
        power = max(
            transmission.rf_power_w
            for boundary in tape.integrated
            for slot in boundary.radiation.slots
            for transmission in slot.transmissions
        )
        rows.append(
            {
                "off_axis_deg": angle,
                "required_power_w": power,
                "pooled_ee_bits_per_j": sum(score.bits.values()) / score.joules,
                "rate_target_feasible": all(score.rate_target_feasible.values()),
            }
        )
    if not all(
        left["required_power_w"] < right["required_power_w"]
        and left["pooled_ee_bits_per_j"] > right["pooled_ee_bits_per_j"]
        for left, right in zip(rows, rows[1:])
    ):
        raise RuntimeError("a-r0 off-axis KAT is not strictly power/EE discriminating")
    return rows


def _points(values: list[float], *, x0: float, y0: float, width: float, height: float) -> str:
    low, high = min(values), max(values)
    return " ".join(
        f"{x0 + index * width / (len(values) - 1):.2f},{y0 + height - (value - low) * height / (high - low):.2f}"
        for index, value in enumerate(values)
    )


def _path(values: list[float], *, x0: float, y0: float, width: float, height: float) -> str:
    return "M" + " L".join(_points(values, x0=x0, y0=y0, width=width, height=height).split())


def _filled_segments(
    values: list[float], *, x0: float, y0: float, width: float, height: float, color: str
) -> str:
    points = [tuple(float(part) for part in point.split(",")) for point in _points(
        values, x0=x0, y0=y0, width=width, height=height
    ).split()]
    return "".join(
        f'<polygon points="{ax:.2f},{ay-1.5:.2f} {bx:.2f},{by-1.5:.2f} {bx:.2f},{by+1.5:.2f} {ax:.2f},{ay+1.5:.2f}" fill="{color}"/>'
        for (ax, ay), (bx, by) in zip(points, points[1:])
    )


def svg(rows: list[dict[str, object]]) -> str:
    power = [float(row["required_power_w"]) for row in rows]
    ee = [float(row["pooled_ee_bits_per_j"]) / 1.0e6 for row in rows]
    angle_labels = "".join(
        f'<text x="{95 + i * 290 / 4:.2f}" y="424" text-anchor="middle">{angle:g}</text>'
        for i, angle in enumerate(ANGLES_DEG)
    )
    angle_labels += "".join(
        f'<text x="{535 + i * 290 / 4:.2f}" y="424" text-anchor="middle">{angle:g}</text>'
        for i, angle in enumerate(ANGLES_DEG)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="500" viewBox="0 0 900 500">
  <rect id="background" width="900" height="500" fill="#ffffff"/>
  <g id="title" font-family="DejaVu Sans, sans-serif" fill="#172033">
    <text x="450" y="32" text-anchor="middle" font-size="18" font-weight="700">a-r0 off-axis physics KAT</text>
    <text x="450" y="54" text-anchor="middle" font-size="11">Single-user controlled fixture; all inputs fixed except transmit off-axis angle</text>
  </g>
  <g id="axes" fill="#25324a">
    <rect x="94.5" y="90" width="1" height="310"/><rect x="95" y="399.5" width="290" height="1"/>
    <rect x="534.5" y="90" width="1" height="310"/><rect x="535" y="399.5" width="290" height="1"/>
  </g>
  <g id="grid" fill="#d8dee9">
    <rect x="95" y="244.5" width="290" height="1"/><rect x="535" y="244.5" width="290" height="1"/>
  </g>
  <g id="power-series" fill="none">
    {_filled_segments(power, x0=95, y0=105, width=290, height=280, color="#b6422c")}
  </g>
  <g id="ee-series" fill="none">
    {_filled_segments(ee, x0=535, y0=105, width=290, height=280, color="#176b87")}
  </g>
  <g id="data-points" fill="#ffffff" stroke-width="2.5">
    {''.join(f'<circle cx="{95+i*290/4:.2f}" cy="{105+280-(value-min(power))*280/(max(power)-min(power)):.2f}" r="4" fill="#b6422c"/>' for i, value in enumerate(power))}
    {''.join(f'<circle cx="{535+i*290/4:.2f}" cy="{105+280-(value-min(ee))*280/(max(ee)-min(ee)):.2f}" r="4" fill="#176b87"/>' for i, value in enumerate(ee))}
  </g>
  <g id="labels" font-family="DejaVu Sans, sans-serif" fill="#172033" font-size="11">
    <text x="240" y="80" text-anchor="middle" font-size="14" font-weight="700">Required RF power</text>
    <text x="680" y="80" text-anchor="middle" font-size="14" font-weight="700">Realised pooled EE</text>
    <text x="240" y="452" text-anchor="middle">Off-axis angle (deg)</text>
    <text x="680" y="452" text-anchor="middle">Off-axis angle (deg)</text>
    <text transform="translate(28 245) rotate(-90)" text-anchor="middle">Required power (W)</text>
    <text transform="translate(468 245) rotate(-90)" text-anchor="middle">Pooled EE (Mbit/J)</text>
    {angle_labels}
    <text x="103" y="112">{max(power):.3f}</text><text x="103" y="382">{min(power):.3f}</text>
    <text x="543" y="112">{max(ee):.2f}</text><text x="543" y="382">{min(ee):.2f}</text>
  </g>
  <g id="caption" font-family="DejaVu Sans, sans-serif" fill="#4a5568" font-size="10">
    <text x="450" y="482" text-anchor="middle">Quantitative positions are generated from the sealed a-r0 rate-target power solve and endpoint energy accounting.</text>
  </g>
</svg>'''


def main() -> int:
    output = HERE / "figures"
    output.mkdir(parents=True, exist_ok=True)
    rows = off_axis_rows()
    svg_path = output / "a-r0-off-axis-power-ee.svg"
    svg_path.write_text(svg(rows), encoding="utf-8")
    svg_digest = hashlib.sha256(svg_path.read_bytes()).hexdigest()
    receipt = {
        "schema": "mcrl-v025-a-r0-off-axis-kat-v1",
        "status": "PASS",
        "setting": run_setting_for("a-r0").payload(),
        "setting_sha256": run_setting_for("a-r0").digest,
        "controlled": {
            "users": 1,
            "beam": list(BEAM),
            "path_factor_without_tx_gain": PATH_FACTOR_WITHOUT_TX_GAIN,
            "boundaries": 48,
            "interference": "none",
        },
        "varied": "transmit_off_axis_angle_deg",
        "rows": rows,
        "identities": {
            "required_power_strictly_increases": True,
            "pooled_ee_strictly_decreases": True,
        },
        "figure": str(svg_path.relative_to(REPO)),
        "figure_sha256": svg_digest,
        "figure_status": "TECHNICAL_PRECHECK_COMPLETE_HUMAN_VISUAL_PENDING",
    }
    receipt["receipt_sha256"] = digest_payload(receipt)
    receipt_path = output / "a-r0-off-axis-kat.json"
    receipt_path.write_bytes(canonical_bytes(receipt) + b"\n")
    for path in (svg_path, receipt_path):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        Path(str(path) + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
