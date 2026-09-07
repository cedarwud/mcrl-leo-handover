from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest


MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from training_decision_context import (  # noqa: E402
    SIDECAR_ARRAY_NAMES,
    TRAINING_ARRAY_NAMES,
    TrainingDecisionContextBinding,
    TrainingDecisionContextError,
    convert_evaluation_sidecar,
    load_training_decision_context,
)


ROWS = 1000
ACTIONS = 28
WORLD = 2026120701
LINEAGE = 2026092102


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _arrays_digest(arrays: dict[str, np.ndarray]) -> str:
    return hashlib.sha256(
        json.dumps(
            {name: _array_digest(value) for name, value in arrays.items()},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    ).hexdigest()


def _canonical(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _base_arrays() -> dict[str, np.ndarray]:
    background = np.full((ROWS, ACTIONS), -100.0, dtype=np.float64)
    background[:, 0] = np.linspace(0.0, 1.0, ROWS, dtype=np.float64)
    background[:, 1] = background[:, 0] - 1.0
    background[:, 2] = background[:, 0] - 2.0
    mask = np.zeros((ROWS, ACTIONS), dtype=np.bool_)
    mask[:, :3] = True
    references = np.zeros(ROWS, dtype=np.int64)
    steps = np.repeat(np.arange(10, dtype=np.int64), 100)
    users = np.tile(np.arange(100, dtype=np.int64), 10)
    return {
        "background_q12": background,
        "action_mask": mask,
        "reference_actions": references,
        "step_indices": steps,
        "user_indices": users,
    }


def _make_sidecar(
    root: Path,
    *,
    split: str = "TRAIN",
    arrays: dict[str, np.ndarray] | None = None,
    metadata_overrides: dict[str, object] | None = None,
    extra_npz: dict[str, np.ndarray] | None = None,
) -> tuple[Path, TrainingDecisionContextBinding]:
    root.mkdir()
    values = _base_arrays() if arrays is None else arrays
    npz_values = dict(values)
    if extra_npz:
        npz_values.update(extra_npz)
    npz_path = root / "decision-context.npz"
    with npz_path.open("wb") as handle:
        np.savez_compressed(handle, **npz_values)

    body: dict[str, object] = {
        "array_names": list(SIDECAR_ARRAY_NAMES),
        "array_sha256": {
            name: _array_digest(values[name]) for name in SIDECAR_ARRAY_NAMES
        },
        "arrays_sha256": _arrays_digest(
            {name: values[name] for name in SIDECAR_ARRAY_NAMES}
        ),
        "background_semantics": "detached-Q1-plus-learned-Q2-native-surface",
        "code_manifest_sha256": _digest("code"),
        "config_sha256": _digest("config"),
        "contract_sha256": _digest("contract"),
        "declared_lineages": [LINEAGE],
        "declared_worlds": [WORLD],
        "evaluation_only": True,
        "field_root_digest": _digest("field-root"),
        "kappa_bits_hex": "0x1.2cea89d260f2ap+33",
        "learner_loadable": False,
        "learner_update": False,
        "lineage": LINEAGE,
        "npz_filename": "decision-context.npz",
        "npz_sha256": _file_digest(npz_path),
        "rows": ROWS,
        "schema": "multi-catfish-mcrl-v018-relational-zr-decision-context-v1",
        "schema_version": 1,
        "source_arrays_sha256": _digest("source-arrays"),
        "split": split,
        "status": "IMPLEMENTATION_ONLY_NO_OUTCOME",
        "steps": 10,
        "test_split_opened": False,
        "users": 100,
        "world_seed": WORLD,
        "episode_training": False,
        "row_identity_sha256": _arrays_digest(
            {
                "step_indices": values["step_indices"],
                "user_indices": values["user_indices"],
            }
        ),
    }
    if metadata_overrides:
        body.update(metadata_overrides)
    # These fields are deliberately calculated after overrides so malformed
    # identity/order cases retain internally consistent cryptographic receipts.
    body["decision_context_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    metadata_path = root / "decision-context.json"
    metadata_path.write_bytes(_canonical(body))
    receipt = (
        "schema=multi-catfish-mcrl-v018-relational-zr-decision-context-v1\n"
        f"metadata_sha256={_file_digest(metadata_path)}\n"
        f"npz_sha256={body['npz_sha256']}\n"
        f"arrays_sha256={body['arrays_sha256']}\n"
        f"decision_context_sha256={body['decision_context_sha256']}\n"
    )
    (root / "decision-context.sha256").write_text(receipt, encoding="ascii")
    return root, TrainingDecisionContextBinding(
        source_arrays_sha256=str(body["source_arrays_sha256"]),
        decision_context_metadata_sha256=_file_digest(metadata_path),
        decision_context_npz_sha256=str(body["npz_sha256"]),
        decision_context_arrays_sha256=str(body["arrays_sha256"]),
        decision_context_sha256=str(body["decision_context_sha256"]),
        row_identity_sha256=str(body["row_identity_sha256"]),
        field_root_digest=str(body["field_root_digest"]),
        kappa_bits_hex=str(body["kappa_bits_hex"]),
        world_seed=WORLD,
        lineage=LINEAGE,
        contract_sha256=str(body["contract_sha256"]),
        config_sha256=str(body["config_sha256"]),
        code_manifest_sha256=str(body["code_manifest_sha256"]),
    )


def test_train_conversion_is_loss_only_and_round_trips(tmp_path: Path) -> None:
    source, binding = _make_sidecar(tmp_path / "sidecar")
    output = tmp_path / "training-context"

    context = convert_evaluation_sidecar(source, output, binding=binding)
    loaded = load_training_decision_context(output)

    assert tuple(context.metadata["array_names"]) == TRAINING_ARRAY_NAMES
    assert tuple(loaded.metadata["array_names"]) == TRAINING_ARRAY_NAMES
    np.testing.assert_array_equal(context.background_q12, _base_arrays()["background_q12"])
    np.testing.assert_array_equal(loaded.action_mask, _base_arrays()["action_mask"])
    np.testing.assert_array_equal(loaded.reference_actions, np.zeros(ROWS, dtype=np.int64))
    assert context.world_seed == WORLD
    assert context.lineage == LINEAGE
    for name in TRAINING_ARRAY_NAMES:
        assert not getattr(context, name).flags.writeable
    assert context.metadata["source_arrays_sha256"] == binding.source_arrays_sha256
    assert context.metadata["source_context_sha256"] == binding.decision_context_sha256
    assert context.metadata["gradient_input"] is False
    assert context.metadata["model_input"] is False
    assert context.metadata["state_input"] is False
    assert context.metadata["model_forward_loadable"] is False
    assert context.metadata["loss_context_loadable"] is True
    assert context.metadata["loss_only"] is True
    assert context.metadata["forward_input_fields"] == []
    assert context.kappa_bits == float.fromhex("0x1.2cea89d260f2ap+33")


@pytest.mark.parametrize("split", ["VALIDATION", "TEST"])
def test_non_train_sidecars_are_rejected(tmp_path: Path, split: str) -> None:
    source, binding = _make_sidecar(tmp_path / "sidecar", split=split)
    with pytest.raises(TrainingDecisionContextError, match="TRAIN"):
        convert_evaluation_sidecar(source, tmp_path / "out", binding=binding)


def test_conversion_requires_explicit_digest_binding(tmp_path: Path) -> None:
    source, _ = _make_sidecar(tmp_path / "sidecar")
    with pytest.raises(TypeError):
        convert_evaluation_sidecar(source, tmp_path / "out")  # type: ignore[call-arg]

    _, binding = _make_sidecar(tmp_path / "sidecar-2")
    bad = replace(binding, source_arrays_sha256=_digest("wrong-source"))
    with pytest.raises(TrainingDecisionContextError, match="source_arrays_sha256"):
        convert_evaluation_sidecar(
            tmp_path / "sidecar-2", tmp_path / "out-2", binding=bad
        )


def test_context_digest_binding_rejects_context_mismatch(tmp_path: Path) -> None:
    source, binding = _make_sidecar(tmp_path / "sidecar")
    bad = replace(binding, decision_context_sha256=_digest("wrong-context"))
    with pytest.raises(TrainingDecisionContextError, match="decision_context_sha256"):
        convert_evaluation_sidecar(source, tmp_path / "out", binding=bad)


def test_kappa_binding_rejects_unit_mismatch(tmp_path: Path) -> None:
    source, binding = _make_sidecar(tmp_path / "sidecar")
    bad = replace(binding, kappa_bits_hex=float(2.0).hex())
    with pytest.raises(TrainingDecisionContextError, match="kappa_bits_hex"):
        convert_evaluation_sidecar(source, tmp_path / "out", binding=bad)


def test_row_identity_is_exact_not_merely_digest_bound(tmp_path: Path) -> None:
    arrays = _base_arrays()
    arrays["step_indices"] = arrays["step_indices"].copy()
    arrays["step_indices"][0], arrays["step_indices"][1] = 1, 0
    source, binding = _make_sidecar(tmp_path / "sidecar", arrays=arrays)
    with pytest.raises(TrainingDecisionContextError, match="row ordering"):
        convert_evaluation_sidecar(source, tmp_path / "out", binding=binding)


def test_reference_must_be_the_native_masked_background_argmax(tmp_path: Path) -> None:
    arrays = _base_arrays()
    arrays["reference_actions"] = np.ones(ROWS, dtype=np.int64)
    source, binding = _make_sidecar(tmp_path / "sidecar", arrays=arrays)
    with pytest.raises(TrainingDecisionContextError, match="masked argmax"):
        convert_evaluation_sidecar(source, tmp_path / "out", binding=binding)


def test_empty_legal_rows_and_nonfinite_context_are_rejected(tmp_path: Path) -> None:
    arrays = _base_arrays()
    arrays["action_mask"] = arrays["action_mask"].copy()
    arrays["action_mask"][17] = False
    source, binding = _make_sidecar(tmp_path / "empty", arrays=arrays)
    with pytest.raises(TrainingDecisionContextError, match="legal"):
        convert_evaluation_sidecar(source, tmp_path / "out-empty", binding=binding)

    arrays = _base_arrays()
    arrays["background_q12"] = arrays["background_q12"].copy()
    arrays["background_q12"][3, 1] = np.nan
    source, binding = _make_sidecar(tmp_path / "nan", arrays=arrays)
    with pytest.raises(TrainingDecisionContextError, match="finite"):
        convert_evaluation_sidecar(source, tmp_path / "out-nan", binding=binding)


def test_closed_sidecar_rejects_model_state_or_gradient_payloads(tmp_path: Path) -> None:
    source, binding = _make_sidecar(
        tmp_path / "sidecar",
        extra_npz={"victim_tokens": np.zeros((ROWS, ACTIONS, 1, 6), dtype=np.float64)},
    )
    with pytest.raises(TrainingDecisionContextError, match="closed"):
        convert_evaluation_sidecar(source, tmp_path / "out", binding=binding)


def test_training_context_requires_exact_file_closure(tmp_path: Path) -> None:
    source, binding = _make_sidecar(tmp_path / "sidecar")
    output = tmp_path / "training-context"
    convert_evaluation_sidecar(source, output, binding=binding)
    (output / "undeclared.bin").write_bytes(b"extra")
    with pytest.raises(TrainingDecisionContextError, match="file closure"):
        load_training_decision_context(output)


def test_conversion_refuses_nonempty_output_root(tmp_path: Path) -> None:
    source, binding = _make_sidecar(tmp_path / "sidecar")
    output = tmp_path / "training-context"
    output.mkdir()
    (output / "existing.txt").write_text("occupied", encoding="ascii")
    with pytest.raises(TrainingDecisionContextError, match="must be empty"):
        convert_evaluation_sidecar(source, output, binding=binding)
