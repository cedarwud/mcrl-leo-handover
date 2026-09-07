from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "freeze_c2_scalarized_stage0", HERE / "freeze_c2_scalarized_stage0.py"
)
assert SPEC is not None and SPEC.loader is not None
F = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = F
SPEC.loader.exec_module(F)


def test_seed_derivation_is_repeatable_and_uint32():
    first = [F._derive_candidate(index) for index in range(8)]
    second = [F._derive_candidate(index) for index in range(8)]
    assert first == second
    assert len(set(first)) == len(first)
    assert all(0 <= value < 2**32 for value in first)


def test_known_prior_set_contains_all_formal_c1_seed_namespaces():
    prior = F._known_prior_seeds()
    for path in F.KNOWN_SEED_FILES:
        import json

        values = json.loads(path.read_text(encoding="utf-8"))["seeds"]
        assert set(values).issubset(prior)


def test_repository_search_covers_hidden_ignored_scratch_authority():
    import json

    authority = F.KNOWN_SEED_FILES[0]
    seed = json.loads(authority.read_text(encoding="utf-8"))["seeds"][0]
    matches = {Path(path).resolve() for path in F._repo_matches(seed)}
    assert authority.resolve() in matches


def test_freeze_output_directory_must_be_outside_repository():
    import pytest

    with pytest.raises(RuntimeError, match="outside the repository"):
        F.c2._validate_freeze_output_directory(
            F.c2.REPO / ".scratch" / "c2-freeze-inside-repo"
        )
