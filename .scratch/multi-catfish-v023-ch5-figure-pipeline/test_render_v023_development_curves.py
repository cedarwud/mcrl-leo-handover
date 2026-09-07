from __future__ import annotations

import copy
import hashlib
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
    else:
        _seal_formal_root(root, plan.plan_sha256, adapter.policy_bindings)
    return root


def _seal_formal_root(root: Path, plan_sha256: str, policy_bindings) -> None:
    admission = {
        "schema": figures.FORMAL_ADMISSION_SCHEMA,
        "status": "FORMAL_STAGE_C_ADMITTED",
        "formal": True,
        "integrity_status": "VERIFIED",
        "split": runner.SPLIT,
        "arms": list(runner.ARMS),
        "plan_sha256": plan_sha256,
        "policy_bindings_sha256": figures.canonical_sha256(policy_bindings),
        "prereg_sha256": runner.canonical_sha256("prereg"),
        "tle_manifest_sha256": runner.canonical_sha256("tle"),
        "execution_configuration_sha256": runner.canonical_sha256("config"),
        "stage_a_pass_receipt_sha256": runner.canonical_sha256("stage-a"),
        "stage_b_pass_receipt_sha256": runner.canonical_sha256("stage-b"),
    }
    admission_path = root / figures.FORMAL_ADMISSION_NAME
    runner._write_once(admission_path, admission)
    admission_digest = runner.file_sha256(admission_path)
    (root / f"{figures.FORMAL_ADMISSION_NAME}.sha256").write_text(
        f"{admission_digest}  {figures.FORMAL_ADMISSION_NAME}\n", encoding="ascii"
    )
    _write_tree_seal(root)


def _write_tree_seal(root: Path) -> None:
    files = {
        path.relative_to(root).as_posix(): runner.file_sha256(path)
        for path in root.rglob("*")
        if path.is_file()
        and path.relative_to(root).as_posix()
        not in {figures.TREE_MANIFEST_NAME, figures.COMPLETE_NAME}
    }
    manifest = "".join(f"{digest}  {path}\n" for path, digest in sorted(files.items()))
    manifest_path = root / figures.TREE_MANIFEST_NAME
    manifest_path.write_text(manifest, encoding="ascii")
    manifest_digest = hashlib.sha256(manifest.encode("ascii")).hexdigest()
    (root / figures.COMPLETE_NAME).write_text(
        f"{manifest_digest}  {figures.TREE_MANIFEST_NAME}\n", encoding="ascii"
    )


def _rewrite_tree_seal(root: Path) -> None:
    (root / figures.TREE_MANIFEST_NAME).unlink()
    (root / figures.COMPLETE_NAME).unlink()
    _write_tree_seal(root)


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
    _seal_formal_root(target, checkpoint["plan_sha256"], checkpoint["policy_bindings"])
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


def test_current_schema_rejects_extra_fifth_arm(tmp_path: Path, plan) -> None:
    four = _write_producer_root(tmp_path / "four", plan)
    five = _write_five_arm_variant(four, tmp_path / "five")
    with pytest.raises(figures.FigurePipelineError, match="schema-specific arm"):
        figures.render([five], tmp_path / "out")


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
    with pytest.raises(figures.FigurePipelineError, match="manifest closure|checkpoint digest"):
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


def test_renderer_pool_is_bit_for_bit_runner_terminal_reduction(tmp_path: Path, plan) -> None:
    root = _write_producer_root(tmp_path / "producer-aggregated", plan)
    data = figures.load_root(root)
    rows = data.rungs[-1].receipts
    for arm in runner.ARMS:
        expected = runner.pool_receipts(
            [row for row in rows if row["arm"] == arm], arm=arm
        )
        assert figures.canonical_sha256(figures._pool(rows, arm)) == runner.canonical_sha256(expected)


def test_service_limits_include_every_arm_and_margin(tmp_path: Path, plan) -> None:
    root = _write_producer_root(tmp_path / "service-limits", plan)
    data = figures.load_root(root)
    mutated_rungs = []
    for rung in data.rungs:
        pooled = copy.deepcopy(rung.pooled)
        pooled["BASELINE"]["service_fraction"] = 1.0
        pooled["FULL2"]["service_fraction"] = 0.5
        mutated_rungs.append(figures.Rung(rung.completed, pooled, rung.receipts))
    display = figures.RootData(
        data.root,
        data.root_sha256,
        data.arms,
        data.claim_ceiling,
        data.formal,
        tuple(mutated_rungs),
        data.authenticated_files,
    )
    fig = figures.build_service_figure(display)
    low, high = fig.axes[0].get_ylim()
    assert low < 0.5 < high
    assert low < 0.999 <= high
    figures.plt.close(fig)


def test_formal_root_requires_external_manifest(tmp_path: Path, plan) -> None:
    root = _write_producer_root(tmp_path / "missing-seal", plan)
    (root / figures.COMPLETE_NAME).unlink()
    with pytest.raises(figures.FigurePipelineError, match="external manifest/COMPLETE"):
        figures.load_root(root)


@pytest.mark.parametrize("mutation", ["repeated-world", "wrong-denominator"])
def test_frozen_world_and_opportunity_denominator_are_enforced(
    tmp_path: Path, plan, mutation: str
) -> None:
    root = _write_producer_root(tmp_path / mutation, plan)
    checkpoint_path = root / "checkpoints" / "checkpoint-000300.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="ascii"))
    checkpoint.pop("checkpoint_sha256")
    if mutation == "repeated-world":
        previous = checkpoint["receipts"][-2 * len(runner.ARMS) : -len(runner.ARMS)]
        current = checkpoint["receipts"][-len(runner.ARMS) :]
        for source, target in zip(previous, current, strict=True):
            for field in ("world_id", "world_seed", "field_root_digest", "initial_world_sha256"):
                target[field] = source[field]
    else:
        row = checkpoint["receipts"][-1]
        row["service_opportunities"] = 1
        row["served_user_steps"] = 1
        row["service_fraction"] = 1.0
        rung_path = root / "rungs" / "rung-000300.json"
        rung = json.loads(rung_path.read_text(encoding="ascii"))
        rung["pooled_by_arm"] = {
            arm: figures._pool(checkpoint["receipts"], arm) for arm in runner.ARMS
        }
        rung_path.write_text(
            json.dumps(rung, sort_keys=True, separators=(",", ":")), encoding="ascii"
        )
    checkpoint["checkpoint_sha256"] = runner.canonical_sha256(checkpoint)
    checkpoint_path.write_text(
        json.dumps(checkpoint, sort_keys=True, separators=(",", ":")), encoding="ascii"
    )
    _rewrite_tree_seal(root)
    with pytest.raises(figures.FigurePipelineError, match="frozen world plan|service counts"):
        figures.load_root(root)


def test_integrity_stop_root_is_never_rendered(tmp_path: Path, plan) -> None:
    root = _write_producer_root(tmp_path / "stopped", plan)
    runner._write_once(
        root / "integrity-stop.json",
        {"overall_token": runner.INTEGRITY_STOP},
    )
    with pytest.raises(figures.FigurePipelineError, match="integrity STOP"):
        figures.load_root(root)
