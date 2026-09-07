from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
PRODUCER_DIR = HERE.parent / "multi-catfish-v023-c1c2-successor-physical-evaluation"
for path in (HERE, PRODUCER_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import render_v023_development_curves as figures
import test_cadence_resume as producer_fixture
import v023_c1c2_successor_physical_runner as runner


@pytest.fixture(scope="module")
def plan():
    return producer_fixture._plan()


def _write_producer_root(root: Path, plan, *, formal: bool = True) -> Path:
    root.mkdir()
    adapter = producer_fixture._StubEvaluationAdapter()
    evaluation = runner.FixedPolicyEvaluationRunner(adapter=adapter, plan=plan)
    receipts = []
    for world in plan.worlds[:300]:
        for arm in runner.ARMS:
            receipts.append(
                adapter.run_episode(
                    arm=arm,
                    world=world,
                    plan_sha256=plan.plan_sha256,
                    resume_state=adapter.resume_state_for(arm),
                )
            )
        if world.episode_index % runner.CHECKPOINT_EVERY == 0:
            runner._write_once(
                root / "checkpoints" / f"checkpoint-{world.episode_index:06d}.json",
                evaluation._checkpoint_payload(world.episode_index, receipts),
            )
            runner._write_once(
                root / "rungs" / f"rung-{world.episode_index:06d}.json",
                evaluation._rung_payload(world.episode_index, receipts),
            )
    if not formal:
        runner._write_once(root / "ROOT-METADATA.json", {"formal": False})
    return root


def _write_five_arm_variant(source: Path, target: Path) -> Path:
    """Derive a future-shape fixture from producer-written payloads, not literals."""

    target.mkdir()
    five_arms = (*runner.ARMS, "DROP_C3")
    for checkpoint_path in sorted((source / "checkpoints").glob("*.json")):
        checkpoint = json.loads(checkpoint_path.read_text(encoding="ascii"))
        checkpoint.pop("checkpoint_sha256")
        expanded = []
        for offset in range(0, len(checkpoint["receipts"]), len(runner.ARMS)):
            matched = checkpoint["receipts"][offset : offset + len(runner.ARMS)]
            extra = copy.deepcopy(matched[0])
            extra["arm"] = "DROP_C3"
            extra["policy_binding"]["arm"] = "DROP_C3"
            extra["action_trace_sha256"] = runner.canonical_sha256(
                {"arm": "DROP_C3", "episode": extra["episode_index"]}
            )
            expanded.extend((*matched, extra))
        checkpoint["arms"] = list(five_arms)
        checkpoint["receipts"] = expanded
        checkpoint["policy_bindings"]["DROP_C3"] = copy.deepcopy(
            checkpoint["policy_bindings"][runner.ARMS[0]]
        )
        checkpoint["policy_bindings"]["DROP_C3"]["arm"] = "DROP_C3"
        checkpoint["resume_states"]["DROP_C3"] = copy.deepcopy(
            checkpoint["resume_states"][runner.ARMS[0]]
        )
        checkpoint["resume_states"]["DROP_C3"]["arm"] = "DROP_C3"
        checkpoint["checkpoint_sha256"] = runner.canonical_sha256(checkpoint)
        runner._write_once(target / "checkpoints" / checkpoint_path.name, checkpoint)

        completed = checkpoint["completed_episode"]
        pooled = {arm: figures._pool(expanded, arm) for arm in five_arms}
        rung_path = source / "rungs" / f"rung-{completed:06d}.json"
        rung = json.loads(rung_path.read_text(encoding="ascii"))
        rung["arms"] = list(five_arms)
        rung["pooled_by_arm"] = pooled
        runner._write_once(target / "rungs" / rung_path.name, rung)
    return target


def _semantic_labels(fig) -> list[str]:
    return figures._axis_labels(fig)


def test_four_arm_300_episode_render_and_determinism(tmp_path: Path, plan) -> None:
    root = _write_producer_root(tmp_path / "formal-root", plan)
    first = tmp_path / "figures-a"
    second = tmp_path / "figures-b"
    manifest_a = figures.render([root], first, additive_panels=True)
    manifest_b = figures.render([root], second, additive_panels=True)

    binding = manifest_a["input_roots"][0]
    assert binding["arms"] == list(runner.ARMS)
    assert binding["rung_count"] == 3
    assert binding["rung_range"] == [100, 300]
    assert binding["receipt_count"] == 4 * 300
    assert len(manifest_a["figures"]) == 8
    assert manifest_a["figures"] == manifest_b["figures"]
    for record in manifest_a["figures"]:
        if record["path"].endswith(".png"):
            assert (first / record["path"]).read_bytes() == (second / record["path"]).read_bytes()


def test_five_arm_variant_reads_arm_order_from_receipts(tmp_path: Path, plan) -> None:
    four = _write_producer_root(tmp_path / "four", plan)
    five = _write_five_arm_variant(four, tmp_path / "five")
    manifest = figures.render([five], tmp_path / "out")
    assert manifest["input_roots"][0]["arms"] == [
        "FULL2",
        "DROP_C1",
        "DROP_C2",
        "BASELINE",
        "DROP_C3",
    ]
    assert manifest["input_roots"][0]["rung_count"] == 3
    assert manifest["input_roots"][0]["receipt_count"] == 5 * 300


def test_nonformal_requires_flag_and_watermarks_every_figure(tmp_path: Path, plan) -> None:
    root = _write_producer_root(tmp_path / "REHEARSAL-root", plan, formal=False)
    with pytest.raises(figures.FigurePipelineError, match="allow-nonformal"):
        figures.render([root], tmp_path / "refused")
    data = figures.load_root(root, allow_nonformal=True)
    for builder in (
        figures.build_ee_figure,
        figures.build_service_figure,
        figures.build_paired_figure,
        figures.build_additive_figure,
    ):
        fig = builder(data)
        assert figures.WATERMARK in [text.get_text() for text in fig.texts]
        figures.plt.close(fig)
    manifest = figures.render([root], tmp_path / "admitted", allow_nonformal=True)
    assert manifest["nonformal_watermark"] == figures.WATERMARK


def test_tampered_episode_receipt_is_refused(tmp_path: Path, plan) -> None:
    root = _write_producer_root(tmp_path / "tampered", plan)
    checkpoint = root / "checkpoints" / "checkpoint-000300.json"
    payload = json.loads(checkpoint.read_text(encoding="ascii"))
    payload["receipts"][-1]["total_bits"] += 1.0
    checkpoint.write_text(json.dumps(payload), encoding="ascii")
    with pytest.raises(figures.FigurePipelineError, match="checkpoint digest"):
        figures.load_root(root)


def test_no_forbidden_words_in_semantic_labels(tmp_path: Path, plan) -> None:
    root = _write_producer_root(tmp_path / "labels", plan)
    data = figures.load_root(root)
    for builder in (
        figures.build_ee_figure,
        figures.build_service_figure,
        figures.build_paired_figure,
        figures.build_additive_figure,
    ):
        fig = builder(data)
        joined = " ".join(_semantic_labels(fig)).lower()
        assert all(word.lower() not in joined for word in figures.FORBIDDEN_LABEL_WORDS)
        figures.plt.close(fig)


def test_output_directory_is_write_once(tmp_path: Path, plan) -> None:
    root = _write_producer_root(tmp_path / "input", plan)
    output = tmp_path / "exists"
    output.mkdir()
    with pytest.raises(figures.FigurePipelineError, match="must be absent"):
        figures.render([root], output)
