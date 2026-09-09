#!/usr/bin/env python3
"""Receipt loading and the CH5 field contract.

Every field this module names is a hard requirement.  A missing field raises
`ReceiptFieldError` carrying the full dotted path of the field and the file it
was expected in.  Nothing is defaulted, substituted or dropped: the sealed
rules forbid a figure that silently omits a series, and a figure that silently
omits a series is indistinguishable from a figure whose series was zero.

The contract is split in three:

  * `merged-receipt.json` — intervals, admission certificates, claim scope.
    Written by `run_v025_matrix_probe.py --merge`.
  * `units/<cell>/world-<n>.json` — per-world canonical receipts, from which
    the additive diagnostics and the per-anchor mechanism rows are read.
  * the interval-reporting block required on every interval by the v1.7
    erratum item 6.

Where the current matrix probe does not yet emit a field that the sealed
reporting rules require, the field is named here anyway and the loader fails
loudly.  Those fields are listed in `CH5-FIGURE-PIPELINE-README.md` under
"required probe extensions" — the correct fix is to emit them, never to relax
this contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# --------------------------------------------------------------------------
# Sealed vocabulary.  These strings are identifiers, not paper symbols, and
# stay upright Latin per the symbol table's rule.
# --------------------------------------------------------------------------

PRIMARY_SETTING = "a-r0"

ARM_CARRIER_BASELINE = "ALL_NEUTRAL_CONTROL"
ARM_S0 = "S0_DEPLOYABLE"
ARM_S_UNI = "S_UNI"
ARM_U1 = "E1_U1"
ARM_J1 = "E1_J1"
ARM_U_ALL = "UNION_CATALOGUE_OPTIMUM"
ARM_FULL = "FULL"

FACTORS = ("C1", "C2", "C3")

#: Contrast keys Figure 3 reads out of ``uncertainty.per_cell[cell].contrasts``.
CONTRAST_U1_VS_BASE = "U1_VS_BASE"
CONTRAST_S0_VS_BASE = "S0_VS_BASE"
CONTRAST_S0_VS_S_UNI = "S0_VS_CERTIFIED_S_UNI"
CONTRAST_J1_MINUS_U_ALL = "J1_MINUS_U_ALL"

LABELS = ("PILOT_NOT_CLAIM", "MATRIX", "CONFIRMATORY")


class ReceiptFieldError(RuntimeError):
    """A required receipt field is absent, null, or the wrong shape."""


# --------------------------------------------------------------------------
# Field access.  `pluck` is the only way this pipeline reads a receipt.
# --------------------------------------------------------------------------


def pluck(node: Any, dotted: str, *, where: str, kind: type | tuple[type, ...] | None = None) -> Any:
    """Read `dotted` out of `node`, naming the full path on failure.

    `where` identifies the receipt file so the operator can go straight to it.
    A `None` value is treated as absent: the reporting rules have no notion of
    a null interval bound, only of a recorded undefined draw, which is a
    different field.
    """

    cursor: Any = node
    walked: list[str] = []
    for part in dotted.split("."):
        walked.append(part)
        here = ".".join(walked)
        if isinstance(cursor, Mapping):
            if part not in cursor:
                raise ReceiptFieldError(
                    f"{where}: missing required receipt field '{here}' "
                    f"(available at '{'.'.join(walked[:-1]) or '<root>'}': "
                    f"{sorted(map(str, cursor))[:24]})"
                )
            cursor = cursor[part]
        elif isinstance(cursor, Sequence) and not isinstance(cursor, (str, bytes)):
            try:
                cursor = cursor[int(part)]
            except (ValueError, IndexError) as exc:
                raise ReceiptFieldError(
                    f"{where}: missing required receipt field '{here}' ({exc})"
                ) from exc
        else:
            raise ReceiptFieldError(
                f"{where}: cannot read required receipt field '{here}' — "
                f"'{'.'.join(walked[:-1])}' is {type(cursor).__name__}, not a mapping"
            )
        if cursor is None:
            raise ReceiptFieldError(
                f"{where}: required receipt field '{here}' is null; "
                "the pipeline never substitutes a value for a missing measurement"
            )
    if kind is not None and not isinstance(cursor, kind):
        names = kind.__name__ if isinstance(kind, type) else "/".join(k.__name__ for k in kind)
        raise ReceiptFieldError(
            f"{where}: required receipt field '{dotted}' is "
            f"{type(cursor).__name__}, expected {names}"
        )
    return cursor


def pluck_float(node: Any, dotted: str, *, where: str) -> float:
    value = pluck(node, dotted, where=where, kind=(int, float))
    if isinstance(value, bool):
        raise ReceiptFieldError(
            f"{where}: required receipt field '{dotted}' is a bool, expected a number"
        )
    return float(value)


# --------------------------------------------------------------------------
# The v1.7 erratum item 6 interval-reporting block.
# --------------------------------------------------------------------------

#: Every interval is printed with its contrast, endpoint, units, decision
#: margin, method, sidedness, nominal level, whether coverage is marginal or
#: simultaneous, the number of dates and learner seeds, the panel scope, and
#: the measured calibration coverage with its Monte-Carlo uncertainty.
INTERVAL_REPORTING_FIELDS = (
    "contrast",
    "endpoint",
    "units",
    "decision_margin",
    "method",
    "sidedness",
    "nominal_level",
    "coverage_type",
    "n_tle_dates",
    "n_learner_seeds",
    "panel_scope",
    "measured_coverage_two_sided",
    "measured_coverage_two_sided_mc",
    "measured_coverage_one_sided",
    "measured_coverage_one_sided_mc",
)


@dataclass(frozen=True)
class IntervalReport:
    """The erratum item 6 disclosure that travels with every plotted interval."""

    contrast: str
    endpoint: str
    units: str
    decision_margin: str
    method: str
    sidedness: str
    nominal_level: float
    coverage_type: str
    n_tle_dates: int
    n_learner_seeds: int
    panel_scope: str
    measured_coverage_two_sided: float
    measured_coverage_two_sided_mc: float
    measured_coverage_one_sided: float
    measured_coverage_one_sided_mc: float

    @classmethod
    def load(cls, contrast_node: Any, *, where: str, contrast_key: str) -> "IntervalReport":
        block = pluck(
            contrast_node,
            "interval_reporting",
            where=f"{where} [contrast '{contrast_key}']",
            kind=Mapping,
        )
        scope = f"{where} [contrast '{contrast_key}'.interval_reporting]"
        values: dict[str, Any] = {}
        for field in INTERVAL_REPORTING_FIELDS:
            values[field] = pluck(block, field, where=scope)
        if str(values["coverage_type"]) not in {"marginal", "simultaneous"}:
            raise ReceiptFieldError(
                f"{scope}: 'coverage_type' is {values['coverage_type']!r}; the erratum "
                "requires it to state whether coverage is 'marginal' or 'simultaneous'"
            )
        if str(values["sidedness"]) not in {"one_sided", "two_sided"}:
            raise ReceiptFieldError(
                f"{scope}: 'sidedness' is {values['sidedness']!r}; expected "
                "'one_sided' or 'two_sided'"
            )
        return cls(
            contrast=str(values["contrast"]),
            endpoint=str(values["endpoint"]),
            units=str(values["units"]),
            decision_margin=str(values["decision_margin"]),
            method=str(values["method"]),
            sidedness=str(values["sidedness"]),
            nominal_level=float(values["nominal_level"]),
            coverage_type=str(values["coverage_type"]),
            n_tle_dates=int(values["n_tle_dates"]),
            n_learner_seeds=int(values["n_learner_seeds"]),
            panel_scope=str(values["panel_scope"]),
            measured_coverage_two_sided=float(values["measured_coverage_two_sided"]),
            measured_coverage_two_sided_mc=float(values["measured_coverage_two_sided_mc"]),
            measured_coverage_one_sided=float(values["measured_coverage_one_sided"]),
            measured_coverage_one_sided_mc=float(values["measured_coverage_one_sided_mc"]),
        )

    def banner_zh(self) -> str:
        """The one-line disclosure printed adjacent to the intervals."""

        return (
            f"區間：{self.method}｜{'單側' if self.sidedness == 'one_sided' else '雙側'}"
            f"｜名目 {self.nominal_level:.2f}"
            f"｜{'邊際覆蓋' if self.coverage_type == 'marginal' else '同時覆蓋'}"
            f"｜{self.n_tle_dates} 日期 × {self.n_learner_seeds} 學習種子"
            f"｜面板 {self.panel_scope}\n"
            f"覆蓋率實測：雙側 {self.measured_coverage_two_sided:.3f}"
            f"±{self.measured_coverage_two_sided_mc:.3f}、"
            f"單側 {self.measured_coverage_one_sided:.3f}"
            f"±{self.measured_coverage_one_sided_mc:.3f}"
            f"（名目 {self.nominal_level:.2f}）；未做事後加寬。"
        )

    def as_csv_columns(self) -> dict[str, Any]:
        return {
            "interval_contrast": self.contrast,
            "endpoint": self.endpoint,
            "interval_units": self.units,
            "decision_margin": self.decision_margin,
            "method": self.method,
            "sidedness": self.sidedness,
            "nominal_level": self.nominal_level,
            "coverage_type": self.coverage_type,
            "n_tle_dates": self.n_tle_dates,
            "n_learner_seeds": self.n_learner_seeds,
            "panel_scope": self.panel_scope,
            "measured_coverage_two_sided": self.measured_coverage_two_sided,
            "measured_coverage_two_sided_mc": self.measured_coverage_two_sided_mc,
            "measured_coverage_one_sided": self.measured_coverage_one_sided,
            "measured_coverage_one_sided_mc": self.measured_coverage_one_sided_mc,
        }


# --------------------------------------------------------------------------
# Plotted quantities.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Interval:
    """One plotted point with its interval and its full disclosure."""

    key: str
    label_zh: str
    unit: str               # "pct_rel" | "pp" | "bits"
    point: float
    lo: float
    hi: float
    margin: float | None
    margin_pass: bool | None
    decisive: bool
    report: IntervalReport

    def __post_init__(self) -> None:
        if self.lo > self.hi:
            raise ReceiptFieldError(
                f"contrast '{self.key}': interval bounds are inverted "
                f"(lo={self.lo!r} > hi={self.hi!r})"
            )


@dataclass(frozen=True)
class QuantitySpec:
    key: str
    label_zh: str
    unit: str
    point_field: str
    lo_field: str
    hi_field: str
    margin_field: str | None
    pass_field: str | None
    decisive: bool
    #: v1.6 §4 / v1.9: informative quantities that must not be read as decisive.
    note_zh: str = ""


#: Figure 3, the physics-certificate regime map.  Order is the plotting order,
#: top to bottom, within each setting block.
FIG3_QUANTITIES: tuple[QuantitySpec, ...] = (
    QuantitySpec(
        CONTRAST_U1_VS_BASE, "U1 相對載波基準", "pct_rel",
        "contrast_relative", "contrast_lower_95_relative", "contrast_upper_95_relative",
        None, None, decisive=False,
        note_zh="天花板臂，僅為上界",
    ),
    QuantitySpec(
        CONTRAST_S0_VS_BASE, "S0 相對載波基準", "pct_rel",
        "contrast_relative", "contrast_lower_95_relative", "contrast_upper_95_relative",
        "decision_threshold_relative", "threshold_pass", decisive=True,
    ),
    QuantitySpec(
        CONTRAST_S0_VS_S_UNI, "S0 相對已認證 S_UNI", "pct_rel",
        "contrast_relative", "contrast_lower_95_relative", "contrast_upper_95_relative",
        "certified_numerical_error_relative", "threshold_pass", decisive=True,
    ),
    QuantitySpec(
        "C1", "C1 因子神諭邊際", "pct_rel",
        "contrast_relative", "contrast_lower_95_relative", "contrast_upper_95_relative",
        "prespecified_margin_relative", "ee_margin_pass", decisive=True,
    ),
    QuantitySpec(
        "C2", "C2 因子神諭邊際", "pct_rel",
        "contrast_relative", "contrast_lower_95_relative", "contrast_upper_95_relative",
        "prespecified_margin_relative", "ee_margin_pass", decisive=True,
    ),
    QuantitySpec(
        "C3", "C3 因子神諭邊際", "pct_rel",
        "contrast_relative", "contrast_lower_95_relative", "contrast_upper_95_relative",
        "prespecified_margin_relative", "ee_margin_pass", decisive=True,
    ),
)

#: Plotted on its own axis: different units, and explicitly not decisive.
FIG3_J1_QUANTITY = QuantitySpec(
    CONTRAST_J1_MINUS_U_ALL, "J1 − U_all", "bits",
    "margin_bits", "margin_lower_95_bits", "margin_upper_95_bits",
    None, None, decisive=False,
    note_zh="資訊性，不具決策性（v1.6 §4）",
)

#: Figure 5, the learned contrasts.
FIG5_QUANTITIES: tuple[QuantitySpec, ...] = tuple(
    QuantitySpec(
        factor, f"FULL vs DROP_{factor}", "pct_rel",
        "contrast_relative", "contrast_lower_95_relative", "contrast_upper_95_relative",
        "prespecified_margin_relative", "ee_margin_pass", decisive=True,
    )
    for factor in FACTORS
)


@dataclass(frozen=True)
class QosSpec:
    key: str
    label_zh: str
    axis_zh: str
    unit: str
    point_field: str
    bound_field: str
    margin_field: str
    #: "higher_is_better" compares the lower bound against the margin;
    #: "lower_is_better" compares the upper bound.
    direction: str


#: Figure 5 panel (b).  Three co-primaries, three units, three axes — never
#: one shared axis (FIG4-SPEC §3, unit discipline).
QOS_CO_PRIMARIES: tuple[QosSpec, ...] = (
    QosSpec(
        "availability", "完整服務可用度", "完整服務可用度差（百分點）", "pp",
        "qos_availability_delta", "qos_availability_lower_95",
        "availability_margin_fraction", "higher_is_better",
    ),
    QosSpec(
        "handover_rate", "換手率", "換手率相對差（%）", "pct_rel",
        "handover_rate_relative_change", "handover_rate_relative_upper_95",
        "relative_cost_margin", "lower_is_better",
    ),
    QosSpec(
        "phi_cost", "Φ 計價換手成本", "Φ 計價換手成本相對差（%）", "pct_rel",
        "phi_priced_handover_cost_relative_change",
        "phi_priced_handover_cost_relative_upper_95",
        "relative_cost_margin", "lower_is_better",
    ),
)


# --------------------------------------------------------------------------
# Loaders.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SettingCertificates:
    """The admission certificate block for one setting."""

    setting: str
    decision: str                    # ADMIT / NOT_ADMITTED / ADMIT_IN_REGIME / ...
    trichotomy: str                  # ADMIT_FULL / ADMIT_C1C2 / NOT_ADMITTED
    trichotomy_reason_zh: str
    rows: Mapping[str, Mapping[str, Any]]
    claim_classification: str
    is_primary: bool


@dataclass(frozen=True)
class MergeReceipt:
    path: Path
    payload: Mapping[str, Any]
    cell_order: tuple[str, ...]

    @property
    def where(self) -> str:
        return str(self.path)


def load_merge(receipts_dir: Path) -> MergeReceipt:
    path = receipts_dir / "merged-receipt.json"
    if not path.is_file():
        raise ReceiptFieldError(
            f"{path}: the matrix merge output is required; run "
            "`run_v025_matrix_probe.py --merge --output <dir>` first"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    where = str(path)
    schema = pluck(payload, "schema", where=where, kind=str)
    if "merge-receipt" not in schema:
        raise ReceiptFieldError(
            f"{where}: 'schema' is {schema!r}, which is not a matrix merge receipt"
        )
    status = pluck(payload, "status", where=where, kind=str)
    if status != "COMPLETE":
        raise ReceiptFieldError(
            f"{where}: 'status' is {status!r}; the pipeline refuses to plot an "
            "incomplete merge"
        )
    for field in (
        "cell_order",
        "anchor_stride",
        "catalogue_definition_sha256",
        "test_split_opened",
        "receipt_sha256",
        "summary_sha256",
    ):
        pluck(payload, field, where=where)
    if bool(pluck(payload, "test_split_opened", where=where)) is not False:
        raise ReceiptFieldError(
            f"{where}: 'test_split_opened' is true; CH5 figures are TRAIN-only "
            "and must never render a TEST-split quantity"
        )
    pluck(payload, "uncertainty.per_cell", where=where, kind=Mapping)
    pluck(payload, "training_admission.certificates", where=where, kind=Mapping)
    cells = tuple(str(cell) for cell in pluck(payload, "cell_order", where=where, kind=Sequence))
    return MergeReceipt(path=path, payload=payload, cell_order=cells)


def load_units(receipts_dir: Path, cells: Iterable[str]) -> dict[str, list[Mapping[str, Any]]]:
    """Load every per-world canonical receipt, keyed by cell.

    The merge output does not embed `failure_analysis`, so the additive
    diagnostics and the per-anchor mechanism rows come from here.
    """

    units_dir = receipts_dir / "units"
    if not units_dir.is_dir():
        raise ReceiptFieldError(
            f"{units_dir}: per-world unit receipts are required; the merge output "
            "carries only their digest, not their additive fields"
        )
    out: dict[str, list[Mapping[str, Any]]] = {}
    for cell in cells:
        safe = cell.replace("′", "prime").replace("γ", "gamma")
        cell_dir = units_dir / safe
        if not cell_dir.is_dir():
            raise ReceiptFieldError(
                f"{cell_dir}: unit receipts for cell '{cell}' are missing; the "
                "pipeline never drops a setting from the regime map"
            )
        rows: list[Mapping[str, Any]] = []
        for path in sorted(cell_dir.glob("world-*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            where = str(path)
            schema = pluck(payload, "schema", where=where, kind=str)
            if "unit-receipt" not in schema:
                raise ReceiptFieldError(
                    f"{where}: 'schema' is {schema!r}, which is not a unit receipt"
                )
            if pluck(payload, "status", where=where, kind=str) != "COMPLETE":
                raise ReceiptFieldError(f"{where}: unit 'status' is not COMPLETE")
            for field in (
                "cell",
                "world_index",
                "claim_classification",
                "provider_source_sha256",
                "code_authority_sha256",
                "calibration_sha256",
                "world_manifest_sha256",
                "canonical_step_rows_sha256",
                "attempt_id",
                "energy_boundary_sentence",
                "endpoint_boundaries",
            ):
                pluck(payload, field, where=where)
            boundaries = int(pluck(payload, "endpoint_boundaries", where=where, kind=int))
            if boundaries != 48:
                raise ReceiptFieldError(
                    f"{where}: 'endpoint_boundaries' is {boundaries}, expected 48 — "
                    "the endpoint is realised pooled EE over all 48 boundaries"
                )
            pluck(payload, "failure_analysis.arms", where=where, kind=Mapping)
            rows.append(payload)
        if not rows:
            raise ReceiptFieldError(
                f"{cell_dir}: no 'world-*.json' unit receipts found for cell '{cell}'"
            )
        out[cell] = rows
    return out


def load_interval(
    merge: MergeReceipt, cell: str, spec: QuantitySpec
) -> Interval:
    """Read one contrast out of the merge output, with its full disclosure."""

    where = merge.where
    contrasts = pluck(
        merge.payload, f"uncertainty.per_cell.{cell}.contrasts",
        where=where, kind=Mapping,
    )
    if spec.key not in contrasts:
        raise ReceiptFieldError(
            f"{where}: missing required receipt field "
            f"'uncertainty.per_cell.{cell}.contrasts.{spec.key}' — the figure "
            f"plots '{spec.label_zh}' for every setting and never drops a series "
            f"(present: {sorted(map(str, contrasts))})"
        )
    node = contrasts[spec.key]
    scope = f"{where} [uncertainty.per_cell.{cell}.contrasts.{spec.key}]"
    point = pluck_float(node, spec.point_field, where=scope)
    lo = pluck_float(node, spec.lo_field, where=scope)
    hi = pluck_float(node, spec.hi_field, where=scope)
    margin = pluck_float(node, spec.margin_field, where=scope) if spec.margin_field else None
    passed = (
        bool(pluck(node, spec.pass_field, where=scope, kind=bool))
        if spec.pass_field else None
    )
    report = IntervalReport.load(node, where=where, contrast_key=f"{cell}.{spec.key}")
    return Interval(
        key=spec.key,
        label_zh=spec.label_zh,
        unit=spec.unit,
        point=point,
        lo=lo,
        hi=hi,
        margin=margin,
        margin_pass=passed,
        decisive=spec.decisive,
        report=report,
    )


def load_qos(merge: MergeReceipt, cell: str, contrast_key: str, spec: QosSpec) -> Interval:
    where = merge.where
    node = pluck(
        merge.payload, f"uncertainty.per_cell.{cell}.contrasts.{contrast_key}",
        where=where, kind=Mapping,
    )
    scope = f"{where} [uncertainty.per_cell.{cell}.contrasts.{contrast_key}]"
    point = pluck_float(node, spec.point_field, where=scope)
    bound = pluck_float(node, spec.bound_field, where=scope)
    margin = pluck_float(node, spec.margin_field, where=scope)
    if spec.direction == "higher_is_better":
        lo, hi, passed = bound, point + (point - bound), bound > margin
    else:
        lo, hi, passed = point - (bound - point), bound, bound < margin
    report = IntervalReport.load(node, where=where, contrast_key=f"{cell}.{contrast_key}")
    return Interval(
        key=f"{contrast_key}:{spec.key}",
        label_zh=spec.label_zh,
        unit=spec.unit,
        point=point,
        lo=lo,
        hi=hi,
        margin=margin,
        margin_pass=passed,
        decisive=True,
        report=report,
    )


# --------------------------------------------------------------------------
# Admission trichotomy.
# --------------------------------------------------------------------------

#: The probe's `training_admission` emits a binary ADMIT / NOT_ADMITTED.  The
#: sealed trichotomy (declaration v1.9 item 6) distinguishes ADMIT_C1C2, which
#: is *not* a C3 failure, and which the probe's binary decision cannot express.
#: The figure derives it from the same certificate rows the probe evaluated.
C3_CERTIFICATE_KEYS = ("retained_factor_marginals",)
C1_AND_GATE_KEYS = (
    "physics_integrity",
    "u1_complete_certified",
    "j1_beyond_base_and_u_all",
    "s0_relative_gain",
    "usable_energy_opportunity",
)


def derive_trichotomy(
    rows: Mapping[str, Mapping[str, Any]],
    *,
    c3_decision_relevant: bool,
    where: str,
) -> tuple[str, str]:
    """Map the certificate rows onto ADMIT_FULL / ADMIT_C1C2 / NOT_ADMITTED.

    ADMIT_C1C2 is identical to ADMIT_FULL except that the C3 conditions are not
    met.  It is not a C3 failure: the learned FULL-vs-DROP_C3 test still runs,
    because a learned coordinator and an oracle removal are different estimands.
    """

    for key in (*C1_AND_GATE_KEYS, *C3_CERTIFICATE_KEYS):
        if key not in rows:
            raise ReceiptFieldError(
                f"{where}: admission certificate row '{key}' is missing; the "
                "trichotomy cannot be annotated without it"
            )
        pluck(rows[key], "pass", where=f"{where} [certificates.{key}]", kind=bool)

    gate = all(bool(rows[key]["pass"]) for key in C1_AND_GATE_KEYS)
    c3 = all(bool(rows[key]["pass"]) for key in C3_CERTIFICATE_KEYS) and c3_decision_relevant
    if not gate:
        failed = [k for k in C1_AND_GATE_KEYS if not bool(rows[k]["pass"])]
        return "NOT_ADMITTED", "未通過：" + "、".join(failed)
    if c3:
        return "ADMIT_FULL", "全部載重證書通過"
    if not bool(rows["retained_factor_marginals"]["pass"]):
        return "ADMIT_C1C2", "C3 條件未達成；C3 作為已評估層帶入，非 C3 失敗"
    return "ADMIT_C1C2", "C3 非加性不具決策相關性；C3 作為已評估層帶入，非 C3 失敗"


def load_certificates(merge: MergeReceipt, cell: str) -> SettingCertificates:
    where = merge.where
    admission = pluck(merge.payload, "training_admission", where=where, kind=Mapping)
    primary_setting = str(pluck(admission, "source_setting", where=where, kind=str))
    if cell == primary_setting:
        rows = pluck(admission, "certificates", where=where, kind=Mapping)
        decision = str(pluck(admission, "decision", where=where, kind=str))
    else:
        sensitivities = pluck(
            admission, "regime_sensitivity_certificates", where=where, kind=Mapping,
        )
        key = _regime_key_for(sensitivities, cell, where=where)
        rows = pluck(
            sensitivities, f"{key}.certificates",
            where=f"{where} [training_admission.regime_sensitivity_certificates]",
            kind=Mapping,
        )
        decision = str(
            pluck(
                sensitivities, f"{key}.decision",
                where=f"{where} [training_admission.regime_sensitivity_certificates]",
                kind=str,
            )
        )
    per_cell = pluck(merge.payload, f"uncertainty.per_cell.{cell}", where=where, kind=Mapping)
    classification = str(
        pluck(per_cell, "claim_classification", where=where, kind=str)
    )
    relevance = pluck(
        per_cell, "level_b.c3_decision_relevant",
        where=f"{where} [uncertainty.per_cell.{cell}]", kind=bool,
    )
    trichotomy, reason = derive_trichotomy(
        rows,
        c3_decision_relevant=bool(relevance),
        where=f"{where} [cell '{cell}']",
    )
    return SettingCertificates(
        setting=cell,
        decision=decision,
        trichotomy=trichotomy,
        trichotomy_reason_zh=reason,
        rows=rows,
        claim_classification=classification,
        is_primary=(cell == primary_setting),
    )


def _regime_key_for(sensitivities: Mapping[str, Any], cell: str, *, where: str) -> str:
    """Regime blocks are keyed by regime, not by run id; resolve either."""

    if cell in sensitivities:
        return cell
    for key, block in sensitivities.items():
        if isinstance(block, Mapping) and str(block.get("run_id", "")) == cell:
            return str(key)
    raise ReceiptFieldError(
        f"{where}: missing required receipt field "
        f"'training_admission.regime_sensitivity_certificates.{cell}' — every "
        f"setting in the regime map carries its own certificates "
        f"(present: {sorted(map(str, sensitivities))})"
    )


# --------------------------------------------------------------------------
# Additive diagnostics, pooled from the unit receipts.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Diagnostics:
    setting: str
    arm: str
    availability: float          # served / opportunities, pooled additively
    availability_served: float
    availability_opportunities: float
    cap_hit_share: float         # cap hits / transmission observations, pooled
    cap_hits: float
    transmission_observations: float


def load_diagnostics(units: Sequence[Mapping[str, Any]], cell: str, arm: str) -> Diagnostics:
    """Pool the two diagnostics over worlds as ratios of sums.

    `rf_cap_share` alone cannot be pooled across worlds — averaging shares is a
    mean of ratios, which the endpoint rule forbids — so the additive numerator
    and denominator are required.
    """

    served = opportunities = hits = observations = 0.0
    for payload in units:
        where = f"units/{cell}/world-{payload.get('world_index')}"
        node = pluck(payload, f"failure_analysis.arms.{arm}", where=where, kind=Mapping)
        served += pluck_float(node, "qos_additive.availability_served", where=where)
        opportunities += pluck_float(
            node, "qos_additive.availability_opportunities", where=where
        )
        hits += pluck_float(node, "rf_cap_hits", where=where)
        observations += pluck_float(node, "rf_transmission_observations", where=where)
    if opportunities <= 0.0:
        raise ReceiptFieldError(
            f"units/{cell}: pooled 'availability_opportunities' for arm '{arm}' is "
            f"{opportunities}; a zero denominator is FAIL_UNDEFINED_DENOMINATOR and "
            "is recorded, never substituted"
        )
    if observations <= 0.0:
        raise ReceiptFieldError(
            f"units/{cell}: pooled 'rf_transmission_observations' for arm '{arm}' is "
            f"{observations}; the cap-hit share is undefined and is recorded, never "
            "substituted"
        )
    return Diagnostics(
        setting=cell,
        arm=arm,
        availability=served / opportunities,
        availability_served=served,
        availability_opportunities=opportunities,
        cap_hit_share=hits / observations,
        cap_hits=hits,
        transmission_observations=observations,
    )


# --------------------------------------------------------------------------
# Mechanism: the per-anchor decomposition Figure 4 reads.
# --------------------------------------------------------------------------

#: Per-anchor row fields.  `matched_anchor_decomposition.by_anchor` already
#: carries A_bits / I_bits / delta_joint_bits / g_A / g_I; the collision-
#: avoidance decomposition, the reversal flag and the nominal/realised pair are
#: the v1.6 §3 mechanism statistics and are required alongside them.
ANCHOR_FIELDS = (
    "anchor_index",
    "A_bits",
    "I_bits",
    "delta_joint_bits",
    "g_A",
    "g_I",
    "collision_avoidance_value_kappa",
    "interaction_loss_avoided_kappa",
    "singleton_value_sacrificed_kappa",
    "additive_reversal",
    "nominal_predicted_gain_kappa",
    "realised_gain_kappa",
    "decomposition_basis",
)


@dataclass(frozen=True)
class Anchor:
    setting: str
    world_index: int
    anchor_index: int
    collision_avoidance_value: float
    interaction_loss_avoided: float
    singleton_value_sacrificed: float
    additive_reversal: bool
    nominal_predicted_gain: float
    realised_gain: float
    decomposition_basis: str
    g_interaction: float


@dataclass(frozen=True)
class Mechanism:
    setting: str
    anchors: tuple[Anchor, ...]
    #: Reported twice: anchored at the carrier a0 and re-anchored at the S_UNI
    #: local optimum (declaration v1.6 §3).
    totals_by_anchoring: Mapping[str, Mapping[str, float]]
    reversal_fraction: Interval
    kappa_bits_per_user_step: float


ANCHORINGS = ("carrier_a0", "reanchored_at_s_uni")


def load_mechanism(
    merge: MergeReceipt, units: Sequence[Mapping[str, Any]], cell: str
) -> Mechanism:
    anchors: list[Anchor] = []
    totals: dict[str, dict[str, float]] = {
        anchoring: {
            "collision_avoidance_value_kappa": 0.0,
            "interaction_loss_avoided_kappa": 0.0,
            "singleton_value_sacrificed_kappa": 0.0,
        }
        for anchoring in ANCHORINGS
    }
    kappas: set[float] = set()
    for payload in units:
        world = int(payload.get("world_index", -1))
        where = f"units/{cell}/world-{world}"
        block = pluck(
            payload, "failure_analysis.collision_avoidance", where=where, kind=Mapping
        )
        kappas.add(pluck_float(block, "kappa_bits_per_user_step", where=where))
        for anchoring in ANCHORINGS:
            node = pluck(
                block, anchoring,
                where=f"{where} [failure_analysis.collision_avoidance]", kind=Mapping,
            )
            for field in totals[anchoring]:
                totals[anchoring][field] += pluck_float(
                    node, field,
                    where=f"{where} [failure_analysis.collision_avoidance.{anchoring}]",
                )
        rows = pluck(
            payload, "failure_analysis.matched_anchor_decomposition.by_anchor",
            where=where, kind=Sequence,
        )
        if not rows:
            raise ReceiptFieldError(
                f"{where}: 'failure_analysis.matched_anchor_decomposition.by_anchor' "
                "is empty; the mechanism panel plots one point per anchor and never "
                "renders an empty series as a passing one"
            )
        for index, row in enumerate(rows):
            scope = (
                f"{where} "
                f"[failure_analysis.matched_anchor_decomposition.by_anchor[{index}]]"
            )
            for field in ANCHOR_FIELDS:
                pluck(row, field, where=scope)
            basis = str(row["decomposition_basis"])
            if basis not in {"F_m_selection_time", "F_realised_endpoint"}:
                raise ReceiptFieldError(
                    f"{scope}: 'decomposition_basis' is {basis!r}; the erratum item 2 "
                    "requires every mechanism statistic to name which F it came from "
                    "('F_m_selection_time' or 'F_realised_endpoint')"
                )
            anchors.append(
                Anchor(
                    setting=cell,
                    world_index=world,
                    anchor_index=int(row["anchor_index"]),
                    collision_avoidance_value=float(row["collision_avoidance_value_kappa"]),
                    interaction_loss_avoided=float(row["interaction_loss_avoided_kappa"]),
                    singleton_value_sacrificed=float(row["singleton_value_sacrificed_kappa"]),
                    additive_reversal=bool(row["additive_reversal"]),
                    nominal_predicted_gain=float(row["nominal_predicted_gain_kappa"]),
                    realised_gain=float(row["realised_gain_kappa"]),
                    decomposition_basis=basis,
                    g_interaction=float(row["g_I"]),
                )
            )
    if len(kappas) != 1:
        raise ReceiptFieldError(
            f"units/{cell}: 'kappa_bits_per_user_step' differs across worlds "
            f"({sorted(kappas)}); the mechanism panel refuses a mixed price"
        )
    reversal = load_interval(
        merge, cell,
        QuantitySpec(
            "ADDITIVE_REVERSAL_FRACTION", "加性反轉頻率", "fraction",
            "fraction", "fraction_lower_95", "fraction_upper_95",
            None, None, decisive=False,
        ),
    )
    return Mechanism(
        setting=cell,
        anchors=tuple(anchors),
        totals_by_anchoring=totals,
        reversal_fraction=reversal,
        kappa_bits_per_user_step=next(iter(kappas)),
    )
