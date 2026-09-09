"""Fresh-seed and cluster-split contracts for claim-bearing E1 data."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from ..algorithms.ee_axis_pairwise import ROUTE_NAMES
from ..errors import MCRLContractError


E1_SPLIT_SCHEMA = "multi-catfish-mcrl-v03-e1-seed-cluster-split-v1"
E1_SPLIT_NAMES = ("train", "validation", "test")


class E1SplitContractError(MCRLContractError):
    """Fresh-seed E1 data violate their sealed split or cluster geometry."""


@dataclass(frozen=True)
class E1PairIndexRow:
    """Outcome-free routing fields needed to verify an E1 source row."""

    route: str
    source_seed: int
    anchor_sha256: str
    inference_anchor_sha256: str
    focal_user: int
    reference_action: int
    candidate_action: int
    action_mask: tuple[bool, ...]

    @property
    def cluster_key(self) -> tuple[str, int, str, int]:
        """Intervention cluster: one focal intervention plus all siblings."""

        return (self.route, self.source_seed, self.anchor_sha256, self.focal_user)

    @property
    def inference_cluster_key(self) -> tuple[str, int, str]:
        """Inference block: all focal interventions sharing one world state."""

        return (self.route, self.source_seed, self.inference_anchor_sha256)

    def verify(self) -> None:
        if self.route not in ROUTE_NAMES:
            raise E1SplitContractError(f"route must be one of {ROUTE_NAMES}")
        if type(self.source_seed) is not int or self.source_seed < 0:
            raise E1SplitContractError("source_seed must be a nonnegative integer")
        if (
            not isinstance(self.anchor_sha256, str)
            or len(self.anchor_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.anchor_sha256)
        ):
            raise E1SplitContractError("anchor_sha256 must be lowercase SHA-256")
        if (
            not isinstance(self.inference_anchor_sha256, str)
            or len(self.inference_anchor_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.inference_anchor_sha256
            )
        ):
            raise E1SplitContractError(
                "inference_anchor_sha256 must be lowercase SHA-256"
            )
        if self.route in {"C1", "C3"} and self.inference_anchor_sha256 != self.anchor_sha256:
            raise E1SplitContractError(
                "C1/C3 inference anchor must equal the physical opening anchor"
            )
        if type(self.focal_user) is not int or self.focal_user < 0:
            raise E1SplitContractError("focal_user must be a nonnegative integer")
        if not self.action_mask or any(type(value) is not bool for value in self.action_mask):
            raise E1SplitContractError("action_mask must be a nonempty boolean tuple")
        for name, action in (
            ("reference_action", self.reference_action),
            ("candidate_action", self.candidate_action),
        ):
            if type(action) is not int or not 0 <= action < len(self.action_mask):
                raise E1SplitContractError(f"{name} lies outside action_mask")
            if not self.action_mask[action]:
                raise E1SplitContractError(f"{name} is illegal under action_mask")
        if self.reference_action == self.candidate_action:
            raise E1SplitContractError("candidate action must differ from reference action")


@dataclass(frozen=True)
class E1RouteCoverage:
    route: str
    train_clusters: int
    validation_clusters: int
    test_clusters: int
    train_inference_anchors: int
    validation_inference_anchors: int
    test_inference_anchors: int
    train_rows: int
    validation_rows: int
    test_rows: int

    def as_dict(self) -> dict[str, str | int]:
        return asdict(self)


@dataclass(frozen=True)
class E1SplitReceipt:
    seed_split: dict[int, str]
    coverage: tuple[E1RouteCoverage, E1RouteCoverage, E1RouteCoverage]
    rows: int
    schema: str = E1_SPLIT_SCHEMA

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "seed_split": {str(seed): split for seed, split in sorted(self.seed_split.items())},
            "coverage": [item.as_dict() for item in self.coverage],
            "rows": self.rows,
        }


def verify_e1_seed_split(
    seed_split: Mapping[int, str],
    *,
    burned_seeds: Sequence[int],
) -> dict[int, str]:
    """Verify the frozen six-seed 3/1/2 partition before source outcomes."""

    if not isinstance(seed_split, Mapping):
        raise E1SplitContractError("seed_split must be a mapping")
    normalized: dict[int, str] = {}
    for seed, split in seed_split.items():
        if type(seed) is not int or seed < 0:
            raise E1SplitContractError("E1 source seeds must be nonnegative integers")
        if split not in E1_SPLIT_NAMES:
            raise E1SplitContractError(f"split must be one of {E1_SPLIT_NAMES}")
        normalized[seed] = split
    expected_counts = {"train": 3, "validation": 1, "test": 2}
    observed_counts = {
        split: sum(value == split for value in normalized.values())
        for split in E1_SPLIT_NAMES
    }
    if observed_counts != expected_counts:
        raise E1SplitContractError(
            f"E1 requires a six-seed 3/1/2 split, got {observed_counts}"
        )
    burned = set(burned_seeds)
    if any(type(seed) is not int or seed < 0 for seed in burned):
        raise E1SplitContractError("burned seeds must be nonnegative integers")
    overlap = sorted(set(normalized) & burned)
    if overlap:
        raise E1SplitContractError(f"E1 source seeds overlap burned seeds: {overlap}")
    return normalized


def verify_full_sibling_groups(rows: Sequence[E1PairIndexRow], *, route: str) -> None:
    """Require complete legal-alternative enumeration for C1 or C3 clusters."""

    if route not in ("C1", "C3"):
        raise E1SplitContractError("full sibling verification applies only to C1/C3")
    selected = [row for row in rows if row.route == route]
    if not selected:
        raise E1SplitContractError(f"{route} has no rows")
    groups: dict[tuple[str, int, str, int], list[E1PairIndexRow]] = {}
    for row in selected:
        row.verify()
        groups.setdefault(row.cluster_key, []).append(row)
    for cluster, siblings in groups.items():
        reference = siblings[0].reference_action
        mask = siblings[0].action_mask
        if any(
            sibling.reference_action != reference or sibling.action_mask != mask
            for sibling in siblings
        ):
            raise E1SplitContractError(
                f"{route} cluster {cluster} mixes reference actions or masks"
            )
        expected = {action for action, legal in enumerate(mask) if legal and action != reference}
        observed = [sibling.candidate_action for sibling in siblings]
        if len(observed) != len(set(observed)):
            raise E1SplitContractError(f"{route} cluster {cluster} repeats a candidate")
        if set(observed) != expected:
            raise E1SplitContractError(
                f"{route} cluster {cluster} is not a full legal-alternative sibling group"
            )


def verify_e1_partition(
    rows: Sequence[E1PairIndexRow],
    *,
    seed_split: Mapping[int, str],
    burned_seeds: Sequence[int],
    minimum_clusters: Mapping[str, int] | None = None,
    minimum_inference_anchors: Mapping[str, Mapping[str, int]] | None = None,
) -> E1SplitReceipt:
    """Verify seed isolation plus intervention and inference-unit coverage."""

    split = verify_e1_seed_split(seed_split, burned_seeds=burned_seeds)
    minimum = dict(minimum_clusters or {"train": 30, "validation": 10, "test": 20})
    if set(minimum) != set(E1_SPLIT_NAMES) or any(
        type(value) is not int or value < 1 for value in minimum.values()
    ):
        raise E1SplitContractError("minimum_clusters must define positive train/validation/test counts")
    inference_minimum: dict[str, dict[str, int]] | None = None
    if minimum_inference_anchors is not None:
        if set(minimum_inference_anchors) != set(ROUTE_NAMES):
            raise E1SplitContractError(
                "minimum_inference_anchors must define C1/C2/C3"
            )
        inference_minimum = {
            route: dict(minimum_inference_anchors[route]) for route in ROUTE_NAMES
        }
        if any(
            set(route_minimum) != set(E1_SPLIT_NAMES)
            or any(type(value) is not int or value < 1 for value in route_minimum.values())
            for route_minimum in inference_minimum.values()
        ):
            raise E1SplitContractError(
                "minimum_inference_anchors must define positive split counts"
            )
    if not rows:
        raise E1SplitContractError("E1 partition has no source rows")
    for row in rows:
        row.verify()
        if row.source_seed not in split:
            raise E1SplitContractError("source row seed is absent from the sealed split")
    anchor_owner: dict[str, str] = {}
    inference_anchor_owner: dict[str, str] = {}
    for row in rows:
        split_name = split[row.source_seed]
        previous_physical = anchor_owner.setdefault(row.anchor_sha256, split_name)
        previous_inference = inference_anchor_owner.setdefault(
            row.inference_anchor_sha256, split_name
        )
        if previous_physical != split_name or previous_inference != split_name:
            raise E1SplitContractError(
                "one anchor_sha256 appears across train/validation/test splits"
            )
    verify_full_sibling_groups(rows, route="C1")
    verify_full_sibling_groups(rows, route="C3")

    coverage: list[E1RouteCoverage] = []
    for route in ROUTE_NAMES:
        route_rows = [row for row in rows if row.route == route]
        if not route_rows:
            raise E1SplitContractError(f"{route} has no rows")
        cluster_sets = {
            split_name: {
                row.cluster_key
                for row in route_rows
                if split[row.source_seed] == split_name
            }
            for split_name in E1_SPLIT_NAMES
        }
        inference_sets = {
            split_name: {
                row.inference_cluster_key
                for row in route_rows
                if split[row.source_seed] == split_name
            }
            for split_name in E1_SPLIT_NAMES
        }
        row_counts = {
            split_name: sum(
                split[row.source_seed] == split_name for row in route_rows
            )
            for split_name in E1_SPLIT_NAMES
        }
        insufficient = {
            split_name: len(cluster_sets[split_name])
            for split_name in E1_SPLIT_NAMES
            if len(cluster_sets[split_name]) < minimum[split_name]
        }
        if insufficient:
            raise E1SplitContractError(
                f"{route} has insufficient intervention-cluster coverage: {insufficient}"
            )
        if inference_minimum is not None:
            insufficient_inference = {
                split_name: len(inference_sets[split_name])
                for split_name in E1_SPLIT_NAMES
                if len(inference_sets[split_name])
                < inference_minimum[route][split_name]
            }
            if insufficient_inference:
                raise E1SplitContractError(
                    f"{route} has insufficient inference-anchor coverage: "
                    f"{insufficient_inference}"
                )
        coverage.append(
            E1RouteCoverage(
                route=route,
                train_clusters=len(cluster_sets["train"]),
                validation_clusters=len(cluster_sets["validation"]),
                test_clusters=len(cluster_sets["test"]),
                train_inference_anchors=len(inference_sets["train"]),
                validation_inference_anchors=len(inference_sets["validation"]),
                test_inference_anchors=len(inference_sets["test"]),
                train_rows=row_counts["train"],
                validation_rows=row_counts["validation"],
                test_rows=row_counts["test"],
            )
        )
    return E1SplitReceipt(
        seed_split=dict(split),
        coverage=tuple(coverage),  # type: ignore[arg-type]
        rows=len(rows),
    )


__all__ = [
    "E1PairIndexRow",
    "E1RouteCoverage",
    "E1_SPLIT_NAMES",
    "E1_SPLIT_SCHEMA",
    "E1SplitContractError",
    "E1SplitReceipt",
    "verify_e1_partition",
    "verify_e1_seed_split",
    "verify_full_sibling_groups",
]
