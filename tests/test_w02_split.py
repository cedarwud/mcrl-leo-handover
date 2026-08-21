"""W-02 — the block-alternating split with embargo (author ruling 2026-08-22).

F3's original contiguous cut avoids leakage but puts two measured trends —
constellation growth and falling altitude — straight onto the train/test
axis.  The alternating scheme is supposed to remove the shift **without**
reintroducing leakage.  Both halves of that claim are checked here.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.ephemeris import (
    EMBARGO,
    TEST,
    TRAIN,
    BlockAlternatingSplit,
    ContiguousDateSplit,
    EpisodeStartSampler,
)
from mcrl.env.tle import TleArchive
from mcrl.errors import MCRLContractError

_ARCHIVE_ROOT = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE_ROOT.is_dir(), reason=f"TLE archive not present at {_ARCHIVE_ROOT}"
)

FIRST = dt.date(2026, 1, 1)
LAST = dt.date(2026, 12, 31)


@pytest.fixture(scope="module")
def archive() -> TleArchive:
    return TleArchive(_ARCHIVE_ROOT)


def _split(**overrides) -> BlockAlternatingSplit:
    return BlockAlternatingSplit(
        first_date=FIRST, last_date=LAST, **overrides
    )


# -- block pattern ---------------------------------------------------------


def test_the_cycle_is_block_embargo_block_embargo():
    split = _split(block_days=7, embargo_days=1)
    assert split.cycle_days == 16
    pattern = [
        split.part_for(FIRST + dt.timedelta(days=offset))
        for offset in range(split.cycle_days)
    ]
    assert pattern == [TRAIN] * 7 + [EMBARGO] + [TEST] * 7 + [EMBARGO]


def test_the_pattern_repeats_every_cycle():
    split = _split()
    for offset in range(60):
        assert split.part_for(FIRST + dt.timedelta(days=offset)) == split.part_for(
            FIRST + dt.timedelta(days=offset + split.cycle_days)
        )


def test_first_block_part_can_be_flipped():
    split = _split(first_block_part=TEST)
    assert split.part_for(FIRST) == TEST
    assert split.part_for(FIRST + dt.timedelta(days=8)) == TRAIN


def test_a_zero_embargo_is_refused():
    with pytest.raises(MCRLContractError, match="embargo_days must be >= 1"):
        _split(embargo_days=0)


def test_dates_outside_the_range_are_refused():
    split = _split()
    with pytest.raises(MCRLContractError, match="outside the split range"):
        split.part_for(FIRST - dt.timedelta(days=1))


def test_block_and_embargo_lengths_are_configurable():
    split = _split(block_days=14, embargo_days=3)
    assert split.cycle_days == 34
    assert split.part_for(FIRST + dt.timedelta(days=13)) == TRAIN
    assert split.part_for(FIRST + dt.timedelta(days=14)) == EMBARGO
    assert split.part_for(FIRST + dt.timedelta(days=16)) == EMBARGO
    assert split.part_for(FIRST + dt.timedelta(days=17)) == TEST


# -- no leakage ------------------------------------------------------------


@requires_archive
def test_train_and_test_dates_are_disjoint(archive):
    split = BlockAlternatingSplit.for_archive(archive)
    train = set(split.available_dates(archive, TRAIN))
    test = set(split.available_dates(archive, TEST))
    assert train and test
    assert not (train & test)


@requires_archive
def test_every_file_is_train_test_or_embargo_exactly_once(archive):
    split = BlockAlternatingSplit.for_archive(archive)
    counts = (
        len(split.available_dates(archive, TRAIN))
        + len(split.available_dates(archive, TEST))
        + len(split.embargoed_dates(archive))
    )
    assert counts == len(archive.dates)


@requires_archive
def test_the_embargo_keeps_the_halves_two_days_apart(archive):
    """One embargo day means the nearest train and test dates differ by two.

    That is four orders of magnitude above the 10 s episode, and above the
    ground-track repeat of every Starlink shell — the leak F3 guarded
    against was episodes *minutes* apart.
    """
    split = BlockAlternatingSplit.for_archive(archive)
    assert split.minimum_gap_days(archive) >= split.embargo_days + 1
    assert split.minimum_gap_days(archive) == 2


@requires_archive
def test_a_longer_embargo_widens_the_gap(archive):
    split = BlockAlternatingSplit.for_archive(archive, embargo_days=3)
    assert split.minimum_gap_days(archive) >= 4


@requires_archive
def test_both_halves_get_a_comparable_share_of_the_corpus(archive):
    split = BlockAlternatingSplit.for_archive(archive)
    train = len(split.available_dates(archive, TRAIN))
    test = len(split.available_dates(archive, TEST))
    assert abs(train - test) / max(train, test) < 0.1


# -- the trends must not land on the train/test axis -----------------------


def _trend_balance(split, archive) -> float:
    """Mean normalised calendar position of each half; equal means balanced.

    Both measured trends (constellation growth, falling altitude) are
    monotone in calendar time, so if the two halves sit at the same average
    position in the corpus, neither trend can separate them.
    """
    first, last = archive.date_range
    span = (last - first).days
    means = []
    for part in (TRAIN, TEST):
        positions = [
            (date - first).days / span
            for date in split.available_dates(archive, part)
        ]
        means.append(float(np.mean(positions)))
    return means[1] - means[0]


@requires_archive
def test_alternating_blocks_balance_the_calendar_trend(archive):
    alternating = BlockAlternatingSplit.for_archive(archive)
    contiguous = ContiguousDateSplit.chronological(archive)

    assert abs(_trend_balance(alternating, archive)) < 0.02
    # The superseded scheme puts the two halves 0.5 of the corpus apart.
    assert _trend_balance(contiguous, archive) > 0.4


@requires_archive
def test_alternating_blocks_interleave_across_the_whole_corpus(archive):
    """Neither half may be confined to one end of the calendar."""
    split = BlockAlternatingSplit.for_archive(archive)
    first, last = archive.date_range
    for part in (TRAIN, TEST):
        dates = split.available_dates(archive, part)
        assert (dates[0] - first).days < split.cycle_days
        assert (last - dates[-1]).days < split.cycle_days


# -- sampler ---------------------------------------------------------------


@requires_archive
def test_sampler_only_draws_dates_from_its_own_blocks(archive):
    split = BlockAlternatingSplit.for_archive(archive)
    rng = np.random.default_rng(3)
    for part in (TRAIN, TEST):
        sampler = EpisodeStartSampler.for_archive(archive, split, part)
        allowed = set(split.available_dates(archive, part))
        for _ in range(200):
            drawn = sampler.draw(rng)
            assert drawn.date() in allowed
            assert split.part_for(drawn.date()) == part


@requires_archive
def test_sampler_never_draws_an_embargoed_date(archive):
    split = BlockAlternatingSplit.for_archive(archive)
    embargoed = set(split.embargoed_dates(archive))
    assert embargoed
    rng = np.random.default_rng(4)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    for _ in range(300):
        assert sampler.draw(rng).date() not in embargoed


def test_sampler_rejects_an_unsorted_or_empty_date_list():
    with pytest.raises(MCRLContractError, match="no available dates"):
        EpisodeStartSampler(TRAIN, available_dates=())
    with pytest.raises(MCRLContractError, match="sorted and unique"):
        EpisodeStartSampler(
            TRAIN, available_dates=(dt.date(2026, 1, 2), dt.date(2026, 1, 1))
        )


def test_sampler_rejects_an_unknown_part():
    with pytest.raises(ValueError, match="unknown split part"):
        EpisodeStartSampler("holdout", available_dates=(FIRST,))


# -- freeze surface --------------------------------------------------------


def test_split_reports_everything_the_prereg_must_freeze():
    payload = _split().as_dict()
    assert payload["scheme"] == "block-alternating-with-embargo"
    assert payload["block_days"] == 7
    assert payload["embargo_days"] == 1
    assert payload["cycle_days"] == 16
    assert payload["first_block_part"] == TRAIN


def test_superseded_scheme_is_labelled_as_such():
    payload = ContiguousDateSplit(
        train_start=FIRST,
        train_end=dt.date(2026, 6, 1),
        test_start=dt.date(2026, 6, 2),
        test_end=LAST,
    ).as_dict()
    assert "SUPERSEDED" in payload["scheme"]
