"""The frozen PREREG on disk, and the drift it exists to catch (W-29).

`artifacts/PREREG-FROZEN-2026-08-25-R2.json` is the post-probe corrective
canonical record.  The original, protocol-completion, and first runtime-
corrected records remain byte-preserved and independently verifiable: each
correction is a visible superseding freeze, never an in-place edit.  From a
freeze onward the risk changes shape: nobody will edit the JSON, they will edit
the **code** it describes, and the record will quietly become a description of
a system that no longer exists.

W-27 §5 named that the more dangerous of the two failure modes -- "描述錯而
行為對", because the PREREG outlives the program.  So these tests do not check
that the file parses.  They check that each value the record *resolved* still
equals the live constant that implements it, and they push the record into the
tampered state rather than waiting for it.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from mcrl.runtime.prereg import (
    PreregFreezeError,
    PreregRecord,
    read_prereg,
    write_prereg,
)

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
FROZEN = ARTIFACTS / "PREREG-FROZEN-2026-08-25-R2.json"
CORRECTIVE_R2_BYTE_SHA256 = (
    "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
)
CORRECTIVE_R2_RECORD_DIGEST = (
    "3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4"
)
RUNTIME_CORRECTED_FROZEN = ARTIFACTS / "PREREG-FROZEN-2026-08-25.json"
PROTOCOL_COMPLETE_FROZEN = ARTIFACTS / "PREREG-FROZEN-2026-08-24.json"
LEGACY_FROZEN = ARTIFACTS / "PREREG-FROZEN-2026-08-23.json"
RUNTIME_CORRECTED_BYTE_SHA256 = (
    "2f8377d73a1ae0190df13a2b59b7d02803dd5769a7d577d94e17e1b613a8c8c2"
)
RUNTIME_CORRECTED_RECORD_DIGEST = (
    "d469d81fab617485b86897180ff52bacc2c514ca604bb676ab1585c8b15560f6"
)
PROTOCOL_COMPLETE_BYTE_SHA256 = (
    "8c5603c94ecdebf65d5c5aee72fcd0c0feb0cfb94eeea6f0cfe6a0f11a3478b3"
)
PROTOCOL_COMPLETE_RECORD_DIGEST = (
    "01b0d85cedbd67f80a24c2adf7ff4181c728070111d06334e8dc55f07f52c022"
)
LEGACY_BYTE_SHA256 = "0deefc4473772bc8e512cd839a57a6d0a7838da766f17688dec19ab1fdc5877d"
LEGACY_RECORD_DIGEST = "d35ddaffda580c8c109f758372956d41aa947b9eb3915d742f3f5f9b7aaecf08"

requires_frozen = pytest.mark.skipif(
    not FROZEN.exists(), reason="PREREG has not been frozen in this checkout"
)


@pytest.fixture(scope="module")
def record():
    if not FROZEN.exists():
        pytest.skip("PREREG has not been frozen in this checkout")
    return read_prereg(FROZEN)


def test_the_corrective_r2_record_exists():
    assert FROZEN.exists(), "the deterministic Q-F corrective seal was not written"


def test_the_corrective_r2_bytes_and_record_digest_are_fixed(record):
    assert hashlib.sha256(FROZEN.read_bytes()).hexdigest() == CORRECTIVE_R2_BYTE_SHA256
    assert record.digest == CORRECTIVE_R2_RECORD_DIGEST


@requires_frozen
def test_the_frozen_record_still_hashes_to_its_own_digest(record):
    """`read_prereg` verifies on load; this states the guarantee out loud."""
    record.verify()
    assert len(record.digest) == 64


def test_the_superseded_record_is_byte_preserved_and_still_verifies():
    assert LEGACY_FROZEN.exists(), "the original sealed evidence was removed"
    payload = LEGACY_FROZEN.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == LEGACY_BYTE_SHA256
    legacy = read_prereg(LEGACY_FROZEN)
    legacy.verify()
    assert legacy.digest == LEGACY_RECORD_DIGEST


def test_the_protocol_complete_record_is_byte_preserved_and_still_verifies():
    assert PROTOCOL_COMPLETE_FROZEN.exists()
    payload = PROTOCOL_COMPLETE_FROZEN.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == PROTOCOL_COMPLETE_BYTE_SHA256
    protocol_complete = read_prereg(PROTOCOL_COMPLETE_FROZEN)
    protocol_complete.verify()
    assert protocol_complete.digest == PROTOCOL_COMPLETE_RECORD_DIGEST


def test_the_runtime_corrected_record_is_byte_preserved_and_still_verifies():
    assert RUNTIME_CORRECTED_FROZEN.exists()
    payload = RUNTIME_CORRECTED_FROZEN.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == RUNTIME_CORRECTED_BYTE_SHA256
    runtime_corrected = read_prereg(RUNTIME_CORRECTED_FROZEN)
    runtime_corrected.verify()
    assert runtime_corrected.digest == RUNTIME_CORRECTED_RECORD_DIGEST


@requires_frozen
def test_the_corrective_r2_record_matches_the_current_freeze_source(
    record, tmp_path
):
    """No implementation/protocol edit may slip in after the corrected seal.

    ``tle_root`` is a host mount location rather than scientific input.  The
    launcher independently verifies every TLE byte, date, split, sampling
    field, and SGP4 setting, so a server under ``/home/sat`` must normalize
    only that recorded path before comparing the source-derived digest.
    """
    from mcrl.env.ephemeris import EphemerisConfig
    from mcrl.runtime.prereg_draft import build_draft, freeze

    # The host mount is append-only and may contain dates acquired after the
    # seal.  Rebuild against the exact manifest committed by the record, so
    # the test detects changes to frozen files or implementation constants
    # without treating unrelated later dates as drift.
    recorded_root = Path(record.sections["ephemeris"]["config"]["tle_root"])
    for row in record.sections["ephemeris"]["frozen_files"]:
        source = recorded_root / row["file"]
        assert source.is_file(), f"frozen TLE file is missing: {source}"
        (tmp_path / row["file"]).symlink_to(source)

    rebuilt = freeze(
        build_draft(ephemeris=EphemerisConfig(tle_root=str(tmp_path)))
    )
    rebuilt_sections = copy.deepcopy(rebuilt.sections)
    rebuilt_sections["ephemeris"]["config"]["tle_root"] = record.sections[
        "ephemeris"
    ]["config"]["tle_root"]
    portable = PreregRecord(
        sections=rebuilt_sections,
        holdout=rebuilt.holdout,
        schema=rebuilt.schema,
    ).with_digest()

    assert portable.digest == record.digest
    assert portable.sections == record.sections


@requires_frozen
def test_r2_changes_only_qf_evidence_resolution_and_refreeze_provenance(record):
    prior = copy.deepcopy(read_prereg(RUNTIME_CORRECTED_FROZEN).sections)
    current = copy.deepcopy(record.sections)

    prior_qf = prior["selection_mappings"]["Q-F c1 calibration scale"]
    current_qf = current["selection_mappings"]["Q-F c1 calibration scale"]
    changed_qf_keys = {
        key
        for key in set(prior_qf) | set(current_qf)
        if prior_qf.get(key) != current_qf.get(key)
    }
    assert changed_qf_keys == {
        "probe",
        "resolved",
        "measured_r1_over_served_steps",
        "corrective_resolution",
    }

    current["selection_mappings"]["Q-F c1 calibration scale"] = prior_qf
    current.pop("refreeze_provenance")
    prior.pop("refreeze_provenance")

    assert current == prior


@requires_frozen
def test_r2_applies_the_full_raw_corrected_served_step_p95(record):
    qf = record.sections["selection_mappings"]["Q-F c1 calibration scale"]
    measured = qf["measured_r1_over_served_steps"]
    provenance = record.sections["refreeze_provenance"]

    assert qf["resolved"] == 2029238.4328742754
    assert measured["p95"] == qf["resolved"]
    assert measured["count"] == 198910.0
    assert measured["decision_steps"] == 200000
    assert provenance["applied_mapping"]["resolved"] == qf["resolved"]
    assert provenance["applied_mapping"]["representation"] == (
        "full raw continuous p95"
    )


@requires_frozen
def test_the_two_runtime_corrections_are_machine_readable(record):
    fading = record.sections["antenna_and_link_budget"]["fading_draw_grain"]
    assert fading["identity"] == ["user_id", "norad_id", "observation_step"]
    assert fading["same_satellite_beams_share_path"] is True
    assert fading["candidate_previous_overlap"] == "reuse_candidate_draw"

    warm_start = record.sections["segment_warm_start"]
    assert warm_start["historical_position_identity"] == [
        "segment_age_steps",
        "norad_id",
    ]


@requires_frozen
def test_an_edit_to_the_frozen_file_is_detected(tmp_path, record):
    """Push it into the state guarded against instead of trusting nobody edits.

    The threat is not a corrupted file -- it is a plausible, well-meant edit
    made after the numbers are in.  So the tamper here is exactly that: one
    threshold moved, everything else left intact.
    """
    payload = json.loads(FROZEN.read_text(encoding="utf-8"))
    payload["sections"]["selection_mappings"]["Q-E dwell N"]["resolved"] = 3
    edited = tmp_path / "prereg.json"
    edited.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(PreregFreezeError, match="edited after freezing"):
        read_prereg(edited)

    # And the control: an untouched round-trip through the same path passes,
    # so the failure above is the edit and not the copy.
    assert read_prereg(write_prereg(tmp_path / "clean.json", record)).digest == record.digest


@requires_frozen
def test_every_resolved_value_still_matches_the_code_that_implements_it(record):
    """The drift guard.  A post-freeze edit to any of these fails here.

    Each entry names its own `unfreezes` target; this asserts the value the
    record committed to is the value that target still holds.
    """
    from mcrl.env.dwell import DwellConfig
    from mcrl.env.service import R3_CALIBRATION_SCALE
    from mcrl.runtime.reward_calibration import REWARD_SCALES

    live = {
        "Q-D r3 calibration scale": float(R3_CALIBRATION_SCALE),
        "Q-E dwell N": float(DwellConfig().steps),
        "Q-F c1 calibration scale": float(REWARD_SCALES[0]),
        "Q-G c2 calibration scale": float(REWARD_SCALES[1]),
    }
    mappings = record.sections["selection_mappings"]
    assert set(mappings) == set(live), "an open question appeared or vanished"

    for question, value in live.items():
        assert float(mappings[question]["resolved"]) == pytest.approx(value), (
            f"{question}: the PREREG resolved "
            f"{mappings[question]['resolved']} but the code now holds {value}. "
            "Changing it after the freeze is a change made with knowledge of "
            "the data, which is what §7.1 exists to prevent."
        )
    # c_3 is the same number reached by a second route; if they ever disagree
    # the record is self-inconsistent regardless of what the code says.
    assert float(REWARD_SCALES[2]) == pytest.approx(float(R3_CALIBRATION_SCALE))


@requires_frozen
def test_the_collapse_sampling_the_record_promises_is_the_one_the_code_does(record):
    """Sampling point and action version are pre-registration items (W-28 app.).

    Prose can drift from behaviour silently, so each clause the record commits
    to is matched against the structure that has to deliver it.
    """
    from mcrl.env.constants import STEPS_PER_EPISODE
    from mcrl.runtime.trainer_spec import CollapseSample, EpisodeLog

    training = record.sections["training"]
    collapse = training["collapse_metrics"]

    # Two points, and both fields exist to hold them.
    assert "first and the last decision step" in collapse["sampled_at"]
    assert {"collapse_first", "collapse_last"} <= set(EpisodeLog.__dataclass_fields__)

    # The greedy reading answers B17 Q1, and the executed one is kept apart.
    assert "GREEDY" in collapse["actions_used"]
    assert "B17 Q1" in collapse["actions_used"]
    fields = set(CollapseSample.__dataclass_fields__)
    assert {"active_beam_count", "argmax_agreement"} <= fields
    assert {"active_beam_count_executed", "argmax_agreement_executed"} <= fields

    # The episode length the "last step" index is taken against.
    assert training["steps_per_episode"] == STEPS_PER_EPISODE
    # And the epsilon schedule the warning about the executed pair quantifies.
    assert training["epsilon_decay_episodes"] == 2000
    assert training["episodes"] == 9000
