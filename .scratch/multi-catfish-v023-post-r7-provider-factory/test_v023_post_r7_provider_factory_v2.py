"""Focused synthetic checks for the Decision-A post-R7 provider factory v2."""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "v023_post_r7_provider_factory_v2_under_test",
    HERE / "v023_post_r7_provider_factory_v2.py",
)
assert SPEC is not None and SPEC.loader is not None
FACTORY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FACTORY
SPEC.loader.exec_module(FACTORY)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii") + b"\n"


def _config_payload(tmp_path: Path, code_root: Path) -> dict[str, object]:
    return {
        "schema": FACTORY.CONFIG_SCHEMA,
        "r7_root": str(tmp_path / "r7"),
        "target_root": str(tmp_path / "target"),
        "epoch_budget": 100,
        "schedule_seed": 2026090701,
        "r7_code_root": str(code_root),
    }


@pytest.mark.parametrize(
    "mutation",
    (
        lambda payload, tmp_path: payload.pop("r7_code_root"),
        lambda payload, tmp_path: payload.__setitem__(
            "schema", "multi-catfish-mcrl-v023-post-r7-provider-factory-config-v1"
        ),
        lambda payload, tmp_path: payload.__setitem__("unknown", True),
        lambda payload, tmp_path: payload.__setitem__("r7_code_root", "relative/root"),
        lambda payload, tmp_path: payload.__setitem__(
            "r7_code_root", str(tmp_path / "missing-code-root")
        ),
    ),
)
def test_config_rejects_non_v2_or_unusable_code_root(tmp_path, mutation):
    code_root = tmp_path / "code-root"
    code_root.mkdir()
    payload = _config_payload(tmp_path, code_root)
    mutation(payload, tmp_path)
    with pytest.raises(FACTORY.V023PostR7ProviderFactoryError):
        FACTORY.PostR7ProviderConfig.from_payload(payload)


def test_config_accepts_exact_v2_schema_and_preserves_existing_fields(tmp_path):
    code_root = tmp_path / "code-root"
    code_root.mkdir()
    parsed = FACTORY.PostR7ProviderConfig.from_payload(
        _config_payload(tmp_path, code_root)
    )
    assert FACTORY.CONFIG_SCHEMA == (
        "multi-catfish-mcrl-v023-post-r7-provider-factory-config-v2"
    )
    assert FACTORY.FACTORY_SCHEMA.endswith("-v2")
    assert FACTORY.IDENTITY_SCHEMA.endswith("-v2")
    assert parsed.r7_code_root == code_root
    assert parsed.epoch_budget == 100
    assert parsed.schedule_seed == 2026090701


def test_wrong_environment_config_sha_fails_before_provider_construction(
    monkeypatch, tmp_path
):
    code_root = tmp_path / "code-root"
    code_root.mkdir()
    config_path = tmp_path / "provider-v2.json"
    config_path.write_bytes(_canonical(_config_payload(tmp_path, code_root)))
    monkeypatch.setenv(FACTORY.CONFIG_PATH_ENV, str(config_path))
    monkeypatch.setenv(FACTORY.CONFIG_SHA256_ENV, "0" * 64)
    monkeypatch.setattr(
        FACTORY,
        "build_provider",
        lambda _: pytest.fail("provider construction must not run"),
    )
    with pytest.raises(
        FACTORY.V023PostR7ProviderFactoryError, match="SHA-256 disagrees"
    ):
        FACTORY.make_provider()

    monkeypatch.setenv(
        FACTORY.CONFIG_SHA256_ENV,
        hashlib.sha256(config_path.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(FACTORY, "build_provider", lambda config: config)
    parsed = FACTORY.make_provider()
    assert parsed.r7_code_root == code_root


@pytest.mark.parametrize("kind", ("equal", "symlink", "subdirectory"))
def test_authentication_rejects_code_root_inside_learner_checkout(
    monkeypatch, tmp_path, kind
):
    result_root = tmp_path / "r7-result"
    result_root.mkdir()
    if kind == "equal":
        code_root = FACTORY.REPO
    elif kind == "symlink":
        code_root = tmp_path / "learner-alias"
        code_root.symlink_to(FACTORY.REPO, target_is_directory=True)
    else:
        code_root = FACTORY.HERE
    monkeypatch.setattr(
        FACTORY,
        "_verify_result_manifest",
        lambda _: pytest.fail("result authentication must not start"),
    )
    with pytest.raises(
        FACTORY.V023PostR7ProviderFactoryError, match="separate"
    ):
        FACTORY.authenticate_r7_go(result_root, r7_code_root=code_root)


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def historical_preflight_fixture(monkeypatch, tmp_path):
    """Build a disposable outer R7 closure from the local bound file set.

    The two adjudicated historical source bytes are unavailable in this checkout.
    The nested code-manifest byte loop is therefore isolated, while the unchanged
    outer ``validate_manifest`` still hashes all 169 preflight bindings.
    """

    source_path = (
        FACTORY.REPO
        / ".scratch/multi-catfish-v023-r7-launch-ready/R7-PREFLIGHT-MANIFEST.json"
    )
    payload = json.loads(source_path.read_text(encoding="ascii"))
    code_root = tmp_path / "historical-code-root"
    for binding in payload["bindings"]:
        source = FACTORY.REPO / binding["path"]
        target = code_root / binding["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        binding["sha256"] = _sha_file(target)

    launch_dir = code_root / ".scratch/multi-catfish-v023-r7-launch-ready"
    code_preflight = launch_dir / "R7-PREFLIGHT-MANIFEST.json"
    code_preflight.write_bytes(_canonical(payload))
    preflight_sha = _sha_file(code_preflight)
    code_preflight_sidecar = launch_dir / "R7-PREFLIGHT-MANIFEST.sha256"
    code_preflight_sidecar.write_text(
        f"{preflight_sha}  R7-PREFLIGHT-MANIFEST.json\n", encoding="ascii"
    )

    result_root = tmp_path / "sealed-result"
    authority = result_root / "authority"
    authority.mkdir(parents=True)
    sealed_preflight = authority / "R7-PREFLIGHT-MANIFEST.json"
    sealed_preflight.write_bytes(code_preflight.read_bytes())
    sealed_sidecar = authority / "R7-PREFLIGHT-MANIFEST.sha256"
    sealed_sidecar.write_bytes(code_preflight_sidecar.read_bytes())

    def validate_nested_manifest_bytes(path, digest_path, repo):
        nested_payload, raw = FACTORY._PREFLIGHT._canonical_json(path)
        digest = hashlib.sha256(raw).hexdigest()
        FACTORY._PREFLIGHT._digest_sidecar(digest_path, digest, path.name)
        return nested_payload, digest

    monkeypatch.setattr(
        FACTORY._PREFLIGHT,
        "_validate_code_manifest",
        validate_nested_manifest_bytes,
    )
    return {
        "root": result_root,
        "code_root": code_root,
        "preflight_sha": preflight_sha,
        "code_manifest_sha": payload["code_manifest"]["sha256"],
        "bindings": payload["bindings"],
        "code_preflight": code_preflight,
        "code_preflight_sidecar": code_preflight_sidecar,
    }


@pytest.mark.parametrize(
    "relative",
    (
        "src/mcrl/algorithms/ee_axis_lcsrs_three_route.py",
        "docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md",
    ),
)
def test_historical_code_root_drift_fails_full_preflight_closure(
    historical_preflight_fixture, relative
):
    fixture = historical_preflight_fixture
    assert (
        FACTORY._verify_r7_preflight(
            fixture["root"],
            expected_sha256=fixture["preflight_sha"],
            expected_code_manifest_sha256=fixture["code_manifest_sha"],
            r7_code_root=fixture["code_root"],
        )
        == FACTORY._SCHEDULE.R7_BASE_CONTRACT_SHA256
    )
    (fixture["code_root"] / relative).write_bytes(b"drifted\n")
    with pytest.raises(
        FACTORY.V023PostR7ProviderFactoryError,
        match="authoritative validation failed",
    ) as caught:
        FACTORY._verify_r7_preflight(
            fixture["root"],
            expected_sha256=fixture["preflight_sha"],
            expected_code_manifest_sha256=fixture["code_manifest_sha"],
            r7_code_root=fixture["code_root"],
        )
    assert isinstance(caught.value.__cause__, FACTORY._PREFLIGHT.R7PreflightError)
    assert relative in str(caught.value.__cause__)


@pytest.mark.parametrize("copy_name", ("manifest", "sidecar"))
def test_code_root_preflight_copy_must_equal_sealed_authority(
    historical_preflight_fixture, copy_name
):
    fixture = historical_preflight_fixture
    target = fixture[
        "code_preflight" if copy_name == "manifest" else "code_preflight_sidecar"
    ]
    target.write_bytes(target.read_bytes() + b"drift")
    with pytest.raises(
        FACTORY.V023PostR7ProviderFactoryError, match="authority copy"
    ):
        FACTORY._verify_r7_preflight(
            fixture["root"],
            expected_sha256=fixture["preflight_sha"],
            expected_code_manifest_sha256=fixture["code_manifest_sha"],
            r7_code_root=fixture["code_root"],
        )


def _sealed_preflight_bindings() -> list[dict[str, str]]:
    path = (
        FACTORY.REPO
        / ".scratch/multi-catfish-v023-r7-launch-ready/R7-PREFLIGHT-MANIFEST.json"
    )
    return json.loads(path.read_text(encoding="ascii"))["bindings"]


def _binding_sha_by_path() -> dict[str, str]:
    return {
        item["path"]: item["sha256"]
        for item in _sealed_preflight_bindings()
    }


def _launch_sha_by_path() -> dict[str, str]:
    path = (
        FACTORY.REPO
        / ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2"
        / "V023-100E-LAUNCH-MANIFEST.sha256"
    )
    return {
        relative: digest
        for digest, relative in (
            line.split("  ", 1)
            for line in path.read_text(encoding="ascii").splitlines()
        )
    }


def test_authentication_runtime_list_is_ordered_and_canonically_bound(tmp_path):
    code_root = tmp_path / "historical-code-root"
    code_root.mkdir()
    checked, digest = FACTORY._verify_r7_authentication_runtime(
        FACTORY.REPO,
        code_root,
        _sealed_preflight_bindings(),
    )
    assert [item["path"] for item in checked] == list(
        FACTORY.R7_AUTHENTICATION_RUNTIME_PATHS
    )
    assert all(
        set(item) == {"path", "sha256", "module", "loaded_from"}
        for item in checked
    )
    assert [item["module"] for item in checked] == list(
        FACTORY.R7_AUTHENTICATION_RUNTIME_MODULES.values()
    )
    assert all(
        Path(item["loaded_from"]).resolve()
        == (FACTORY.REPO / item["path"]).resolve()
        for item in checked
    )
    r7_bindings = _binding_sha_by_path()
    assert all(item["sha256"] == r7_bindings[item["path"]] for item in checked)
    assert digest == FACTORY._runtime_list_sha256(checked)


def test_bound_learner_runtime_is_explicit_sorted_observed_and_launch_bound():
    checked, digest = FACTORY._verify_r7_bound_learner_runtime(
        FACTORY.REPO,
        _sealed_preflight_bindings(),
    )
    expected_pairs = sorted(
        FACTORY.R7_BOUND_LEARNER_RUNTIME_MODULES.items(),
        key=lambda item: (item[0], item[1]),
    )
    assert [(item["path"], item["module"]) for item in checked] == expected_pairs
    assert len(checked) == 33
    assert all(
        set(item) == {"path", "module", "loaded_from", "sha256"}
        for item in checked
    )
    assert all(
        item["loaded_from"] == str(FACTORY.REPO / item["path"])
        for item in checked
    )
    launch_bindings = _launch_sha_by_path()
    assert all(item["sha256"] == launch_bindings[item["path"]] for item in checked)
    assert digest == FACTORY._runtime_list_sha256(checked)
    compact = json.dumps(
        checked,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    assert digest == hashlib.sha256(compact).hexdigest()
    assert digest != hashlib.sha256(compact + b"\n").hexdigest()


def test_loaded_mcrl_module_from_foreign_path_fails_closed(
    monkeypatch, tmp_path
):
    code_root = tmp_path / "historical-code-root"
    code_root.mkdir()
    relative = "src/mcrl/errors.py"
    module_name = FACTORY.R7_AUTHENTICATION_RUNTIME_MODULES[relative]
    foreign = tmp_path / "foreign" / "errors.py"
    foreign.parent.mkdir()
    shutil.copyfile(FACTORY.REPO / relative, foreign)
    module = importlib.import_module(module_name)
    monkeypatch.setattr(module, "__file__", str(foreign))

    with pytest.raises(
        FACTORY.V023PostR7ProviderFactoryError,
        match=r"origin disagrees.*mcrl\.errors",
    ):
        FACTORY._verify_r7_authentication_runtime(
            FACTORY.REPO,
            code_root,
            _sealed_preflight_bindings(),
        )


def test_loaded_bound_learner_module_from_foreign_path_fails_before_filtering(
    monkeypatch, tmp_path
):
    relative = "src/mcrl/algorithms/ee_axis_lcsrs_three_route.py"
    module_name = FACTORY.R7_BOUND_LEARNER_RUNTIME_MODULES[relative]
    foreign = tmp_path / "foreign" / "ee_axis_lcsrs_three_route.py"
    foreign.parent.mkdir()
    shutil.copyfile(FACTORY.REPO / relative, foreign)
    module = importlib.import_module(module_name)
    monkeypatch.setattr(module, "__file__", str(foreign))

    with pytest.raises(
        FACTORY.V023PostR7ProviderFactoryError,
        match=r"origin disagrees.*ee_axis_lcsrs_three_route",
    ):
        FACTORY._verify_r7_bound_learner_runtime(
            FACTORY.REPO,
            _sealed_preflight_bindings(),
        )


def test_fresh_process_r7_bound_import_closure_is_exactly_declared():
    program = r'''
import importlib.util
import json
from pathlib import Path
import sys

repo = Path.cwd().resolve()
factory_path = repo / ".scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory_v2.py"
spec = importlib.util.spec_from_file_location(
    "v023_post_r7_provider_factory_v2_fresh_process", factory_path
)
factory = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = factory
spec.loader.exec_module(factory)
manifest = json.loads(
    (repo / ".scratch/multi-catfish-v023-r7-launch-ready/R7-PREFLIGHT-MANIFEST.json")
    .read_text(encoding="ascii")
)
bound = {item["path"] for item in manifest["bindings"]}
roots = (
    repo / "src/mcrl",
    repo / ".scratch/multi-catfish-v023-r7-launch-ready",
)
loaded = []
for module_name, module in tuple(sys.modules.items()):
    module_file = getattr(module, "__file__", None)
    if not isinstance(module_file, str):
        continue
    try:
        origin = Path(module_file).resolve(strict=True)
    except OSError:
        continue
    if any(origin.is_relative_to(root) for root in roots):
        relative = origin.relative_to(repo).as_posix()
        if relative in bound:
            loaded.append([relative, module_name])
discovered = sorted(loaded)
declared_a = list(factory.R7_AUTHENTICATION_RUNTIME_MODULES.items())
declared_l = sorted(
    factory.R7_BOUND_LEARNER_RUNTIME_MODULES.items(),
    key=lambda item: (item[0], item[1]),
)
print(json.dumps({
    "declared_a": declared_a,
    "declared_l": declared_l,
    "discovered": discovered,
}, sort_keys=True))
'''
    environment = os.environ.copy()
    environment["PYTHONPATH"] = "src"
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=FACTORY.REPO,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    closure = json.loads(completed.stdout)
    declared_a = [tuple(item) for item in closure["declared_a"]]
    declared_l = [tuple(item) for item in closure["declared_l"]]
    discovered = [tuple(item) for item in closure["discovered"]]
    paths_a = [path for path, _ in declared_a]
    paths_l = [path for path, _ in declared_l]
    discovered_paths = [path for path, _ in discovered]
    assert len(declared_a) == 18
    assert len(declared_l) == 33
    assert len(paths_a) == len(set(paths_a))
    assert len(paths_l) == len(set(paths_l))
    assert set(paths_a).isdisjoint(paths_l)
    assert len(discovered_paths) == len(set(discovered_paths))
    assert set(discovered_paths) == set(paths_a) | set(paths_l)
    observed = dict(discovered)
    assert [(path, observed[path]) for path in paths_a] == declared_a
    assert sorted(
        ((path, observed[path]) for path in paths_l),
        key=lambda item: (item[0], item[1]),
    ) == declared_l


def test_fresh_authentication_only_import_closure_is_exactly_a():
    program = r'''
import importlib.util
import json
from pathlib import Path
import sys

repo = Path.cwd().resolve()

def load(name, relative):
    path = repo / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

load(
    "v023_fit_adapter_for_post_r7_provider_factory",
    ".scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_fit_adapter.py",
)
gate = load(
    "r7_balanced_successor_gate",
    ".scratch/multi-catfish-v023-r7-launch-ready/r7_balanced_successor_gate.py",
)
sys.modules["r7_balanced_successor_gate"] = gate
load(
    "v023_r7_preflight_for_post_r7_provider_factory",
    ".scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py",
)
load(
    "v023_c3_schedule_for_post_r7_provider_factory",
    ".scratch/multi-catfish-v023-c3-source-schedule/v023_c3_source_schedule.py",
)
manifest = json.loads(
    (repo / ".scratch/multi-catfish-v023-r7-launch-ready/R7-PREFLIGHT-MANIFEST.json")
    .read_text(encoding="ascii")
)
bound = {item["path"] for item in manifest["bindings"]}
roots = (
    repo / "src/mcrl",
    repo / ".scratch/multi-catfish-v023-r7-launch-ready",
)
loaded = []
for module_name, module in tuple(sys.modules.items()):
    module_file = getattr(module, "__file__", None)
    if not isinstance(module_file, str):
        continue
    try:
        origin = Path(module_file).resolve(strict=True)
    except OSError:
        continue
    if any(origin.is_relative_to(root) for root in roots):
        relative = origin.relative_to(repo).as_posix()
        if relative in bound:
            loaded.append([relative, module_name])
print(json.dumps(sorted(loaded), sort_keys=True))
'''
    environment = os.environ.copy()
    environment["PYTHONPATH"] = "src"
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=FACTORY.REPO,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    observed = [tuple(item) for item in json.loads(completed.stdout)]
    expected = list(FACTORY.R7_AUTHENTICATION_RUNTIME_MODULES.items())
    assert len(observed) == len({path for path, _ in observed}) == 18
    assert dict(observed) == dict(expected)


def test_every_fresh_factory_project_module_is_launch_manifest_bound():
    program = r'''
import importlib.util
import json
from pathlib import Path
import sys

repo = Path.cwd().resolve()
factory_path = repo / ".scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory_v2.py"
spec = importlib.util.spec_from_file_location("v023_factory_manifest_probe", factory_path)
factory = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = factory
spec.loader.exec_module(factory)
loaded = []
for module_name, module in tuple(sys.modules.items()):
    module_file = getattr(module, "__file__", None)
    if not isinstance(module_file, str):
        continue
    try:
        origin = Path(module_file).resolve(strict=True)
    except OSError:
        continue
    if origin.is_relative_to(repo / "src/mcrl") or origin.is_relative_to(repo / ".scratch"):
        loaded.append([origin.relative_to(repo).as_posix(), module_name])
print(json.dumps(sorted(loaded), sort_keys=True))
'''
    environment = os.environ.copy()
    environment["PYTHONPATH"] = "src"
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=FACTORY.REPO,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    observed = [tuple(item) for item in json.loads(completed.stdout)]
    launch_bindings = _launch_sha_by_path()
    uncovered = sorted({path for path, _ in observed} - set(launch_bindings))
    mismatched = sorted(
        path
        for path, _ in observed
        if path in launch_bindings
        and _sha_file(FACTORY.REPO / path) != launch_bindings[path]
    )
    assert not uncovered and not mismatched, json.dumps(
        {"uncovered": uncovered, "hash_mismatches": mismatched},
        indent=2,
        sort_keys=True,
    )


def test_r7_hash_divergences_are_learner_runtime_only(tmp_path):
    code_root = tmp_path / "separate-historical-code-root"
    code_root.mkdir()
    bindings = _sealed_preflight_bindings()
    r7_bindings = _binding_sha_by_path()
    launch_bindings = _launch_sha_by_path()
    authentication, _ = FACTORY._verify_r7_authentication_runtime(
        FACTORY.REPO,
        code_root,
        bindings,
    )
    learner, _ = FACTORY._verify_r7_bound_learner_runtime(FACTORY.REPO, bindings)
    assert all(
        record["sha256"] == r7_bindings[record["path"]]
        == launch_bindings[record["path"]]
        for record in authentication
    )
    assert all(
        record["sha256"] == launch_bindings[record["path"]]
        for record in learner
    )
    divergent = {
        record["path"]
        for record in learner
        if record["sha256"] != r7_bindings[record["path"]]
    }
    expected_divergent = {
        "src/mcrl/algorithms/ee_axis_lcsrs_three_route.py",
        "src/mcrl/algorithms/ee_axis_v014_head.py",
    }
    assert divergent == expected_divergent
    assert expected_divergent <= set(FACTORY.R7_BOUND_LEARNER_RUNTIME_PATHS)
    assert expected_divergent.isdisjoint(FACTORY.R7_AUTHENTICATION_RUNTIME_PATHS)


def test_drifted_executing_authentication_file_fails_closed(
    historical_preflight_fixture, monkeypatch
):
    fixture = historical_preflight_fixture
    assert FACTORY._verify_r7_preflight(
        fixture["root"],
        expected_sha256=fixture["preflight_sha"],
        expected_code_manifest_sha256=fixture["code_manifest_sha"],
        r7_code_root=fixture["code_root"],
    ) == FACTORY._SCHEDULE.R7_BASE_CONTRACT_SHA256
    real_file_sha256 = FACTORY._file_sha256

    def drifted_file_sha256(path, *, field="file"):
        if Path(path) == FACTORY.REPO / "src/mcrl/runtime/finiteness.py":
            return "0" * 64
        return real_file_sha256(path, field=field)

    monkeypatch.setattr(FACTORY, "_file_sha256", drifted_file_sha256)
    with pytest.raises(
        FACTORY.V023PostR7ProviderFactoryError, match="finiteness.py"
    ):
        FACTORY._verify_r7_authentication_runtime(
            FACTORY.REPO,
            fixture["code_root"],
            fixture["bindings"],
        )


class _FakeSchedule:
    epoch_budget = 100
    schedule_seed = 2026090701
    surfaces = ()
    neutral_batches = ()
    informed_batches = ()
    neutral_targets_by_anchor = ()
    informed_targets_by_anchor = ()
    neutral_source_id = "c3-neutral-source"
    informed_source_id = "c3-informed-source"


def _digest_seed(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def test_authentication_receipt_type_carries_all_v2_provenance():
    field_names = set(FACTORY.R7GoAuthentication.__dataclass_fields__)
    assert {
        "root",
        "result_path",
        "result_sha256",
        "result",
        "source_panel",
        "records",
        "binding",
        "r7_code_root",
        "r7_preflight_manifest_sha256",
        "r7_code_manifest_sha256",
        "r7_result_manifest_sha256",
        "r7_gate_result_sha256",
        "r7_authentication_runtime",
        "r7_authentication_runtime_sha256",
        "r7_bound_learner_runtime",
        "r7_bound_learner_runtime_sha256",
    } <= field_names


def test_identity_contains_v2_provenance_and_binds_resolved_code_root(
    monkeypatch, tmp_path
):
    target_root = tmp_path / "target"
    target_root.mkdir()
    target_manifest = target_root / "MANIFEST.sha256"
    target_manifest.write_bytes(b"synthetic-target-manifest\n")
    code_roots = (tmp_path / "historical-a", tmp_path / "historical-b")
    for path in code_roots:
        path.mkdir()

    runtime = [{
        "path": "src/mcrl/runtime/finiteness.py",
        "sha256": _digest_seed("finite"),
        "module": "mcrl.runtime.finiteness",
        "loaded_from": str(
            (FACTORY.REPO / "src/mcrl/runtime/finiteness.py").resolve()
        ),
    }]
    runtime_sha = FACTORY._runtime_list_sha256(runtime)
    learner_runtime = [{
        "path": "src/mcrl/algorithms/ee_axis_lcsrs_three_route.py",
        "sha256": _digest_seed("learner"),
        "module": "mcrl.algorithms.ee_axis_lcsrs_three_route",
        "loaded_from": str(
            (
                FACTORY.REPO
                / "src/mcrl/algorithms/ee_axis_lcsrs_three_route.py"
            ).resolve()
        ),
    }]
    learner_runtime_sha = FACTORY._runtime_list_sha256(learner_runtime)

    def authenticate(_, *, r7_code_root):
        return SimpleNamespace(
            records=(object(),),
            binding=object(),
            r7_code_root=Path(r7_code_root).resolve(),
            r7_preflight_manifest_sha256=_digest_seed("preflight"),
            r7_code_manifest_sha256=_digest_seed("code-manifest"),
            r7_result_manifest_sha256=_digest_seed("result-manifest"),
            r7_gate_result_sha256=_digest_seed("gate-result"),
            r7_authentication_runtime=runtime,
            r7_authentication_runtime_sha256=runtime_sha,
            r7_bound_learner_runtime=learner_runtime,
            r7_bound_learner_runtime_sha256=learner_runtime_sha,
        )

    monkeypatch.setattr(FACTORY, "authenticate_r7_go", authenticate)
    monkeypatch.setattr(
        FACTORY._BRIDGE, "load_completed_target_artifact", lambda _: object()
    )
    schedule = _FakeSchedule()
    monkeypatch.setattr(
        FACTORY._SCHEDULE,
        "build_v023_c3_source_schedule",
        lambda *args, **kwargs: schedule,
    )
    monkeypatch.setattr(
        FACTORY, "_schedule_receipt_identity", lambda *args, **kwargs: _digest_seed("schedule")
    )
    monkeypatch.setattr(
        FACTORY._BRIDGE, "load_lcsrs_c3_inputs", lambda *args, **kwargs: object()
    )

    class FakeDelegate:
        def next_batch(self, **kwargs):
            return kwargs

        def sampler_state(self):
            return {"state": "synthetic"}

        def load_sampler_state(self, state):
            self.loaded = state

    monkeypatch.setattr(
        FACTORY._BRIDGE,
        "V023ProviderOrchestratorBridge",
        lambda *args, **kwargs: FakeDelegate(),
    )

    providers = []
    for code_root in code_roots:
        providers.append(
            FACTORY.build_provider(
                FACTORY.PostR7ProviderConfig(
                    r7_root=tmp_path / "r7",
                    target_root=target_root,
                    epoch_budget=100,
                    schedule_seed=2026090701,
                    r7_code_root=code_root,
                )
            )
        )

    first_payload = providers[0].provider_identity_payload
    assert first_payload == {
        "schema": FACTORY.IDENTITY_SCHEMA,
        "target_manifest_sha256": _sha_file(target_manifest),
        "c3_schedule_receipt_sha256": _digest_seed("schedule"),
        "epoch_budget": 100,
        "c3_source_ids": {
            "neutral": "c3-neutral-source",
            "informed": "c3-informed-source",
        },
        "r7_code_root": str(code_roots[0].resolve()),
        "r7_preflight_manifest_sha256": _digest_seed("preflight"),
        "r7_code_manifest_sha256": _digest_seed("code-manifest"),
        "r7_result_manifest_sha256": _digest_seed("result-manifest"),
        "r7_gate_result_sha256": _digest_seed("gate-result"),
        "r7_authentication_runtime": runtime,
        "r7_authentication_runtime_sha256": runtime_sha,
        "r7_bound_learner_runtime": learner_runtime,
        "r7_bound_learner_runtime_sha256": learner_runtime_sha,
    }
    assert runtime_sha == FACTORY._runtime_list_sha256(
        first_payload["r7_authentication_runtime"]
    )
    assert learner_runtime_sha == FACTORY._runtime_list_sha256(
        first_payload["r7_bound_learner_runtime"]
    )
    assert providers[0].provider_identity == (
        f"{FACTORY.FACTORY_SCHEMA}:"
        f"{FACTORY._SCHEDULE.canonical_sha256(first_payload)}"
    )
    assert providers[0].provider_identity != providers[1].provider_identity

    moved_payload = dict(first_payload)
    moved_runtime = [dict(item) for item in first_payload["r7_authentication_runtime"]]
    moved_runtime[0]["loaded_from"] = str(
        tmp_path / "moved-checkout/src/mcrl/runtime/finiteness.py"
    )
    moved_payload["r7_authentication_runtime"] = moved_runtime
    moved_payload["r7_authentication_runtime_sha256"] = (
        FACTORY._runtime_list_sha256(moved_runtime)
    )
    moved_identity = (
        f"{FACTORY.FACTORY_SCHEMA}:"
        f"{FACTORY._SCHEDULE.canonical_sha256(moved_payload)}"
    )
    assert moved_identity != providers[0].provider_identity
