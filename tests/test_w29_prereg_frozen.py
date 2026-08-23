"""The frozen PREREG on disk, and the drift it exists to catch (W-29).

`artifacts/PREREG-FROZEN-2026-08-23.json` is the sealed record.  Until now
every script built it in memory and threw it away; from the freeze onward the
file is the commitment, and the risk changes shape: nobody will edit the JSON,
they will edit the **code** it describes, and the record will quietly become a
description of a system that no longer exists.

W-27 §5 named that the more dangerous of the two failure modes -- "描述錯而
行為對", because the PREREG outlives the program.  So these tests do not check
that the file parses.  They check that each value the record *resolved* still
equals the live constant that implements it, and they push the record into the
tampered state rather than waiting for it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcrl.runtime.prereg import PreregFreezeError, read_prereg, write_prereg

FROZEN = Path(__file__).resolve().parents[1] / "artifacts" / "PREREG-FROZEN-2026-08-23.json"

requires_frozen = pytest.mark.skipif(
    not FROZEN.exists(), reason="PREREG has not been frozen in this checkout"
)


@pytest.fixture(scope="module")
def record():
    if not FROZEN.exists():
        pytest.skip("PREREG has not been frozen in this checkout")
    return read_prereg(FROZEN)


@requires_frozen
def test_the_frozen_record_still_hashes_to_its_own_digest(record):
    """`read_prereg` verifies on load; this states the guarantee out loud."""
    record.verify()
    assert len(record.digest) == 64


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
