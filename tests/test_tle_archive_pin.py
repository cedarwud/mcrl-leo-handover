"""Host pin (controller ruling 2026-09-11, item 4): one TLE archive, by hash.

sat's ``~/demo/tle_data/starlink/tle`` held the frozen 373-file archive; the
local one held the same 373 files plus 19 later days.  Same seed, different
epochs, different random arm.  ``MCRL_TLE_ROOT`` selects the root and
``assert_tle_archive_pinned`` refuses any archive whose file-set hash is not
the frozen R2 record's ``ephemeris.file_set_sha256``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.errors import MCRLContractError
from mcrl.runtime import training_pipeline as tp


def test_unset_override_keeps_the_old_root(monkeypatch):
    monkeypatch.delenv(tp.TLE_ROOT_ENV_VAR, raising=False)
    assert tp.resolve_tle_root() == Path(TLE_ROOT_DEFAULT).expanduser()


def test_the_override_is_honoured(monkeypatch, tmp_path):
    monkeypatch.setenv(tp.TLE_ROOT_ENV_VAR, str(tmp_path))
    assert tp.resolve_tle_root() == tmp_path


def test_the_pinned_hash_is_the_frozen_records_own():
    assert tp.pinned_tle_file_set_sha256() == (
        "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"
    )


def test_an_archive_that_is_not_the_pinned_one_is_refused(tmp_path):
    source = Path(TLE_ROOT_DEFAULT).expanduser()
    files = sorted(source.glob("starlink_*.tle"))[:3] if source.is_dir() else []
    if len(files) < 3:
        pytest.skip("no TLE archive on this host to build a partial copy from")
    for path in files:
        shutil.copy2(path, tmp_path / path.name)
    with pytest.raises(MCRLContractError, match="pinned frozen archive"):
        tp.assert_tle_archive_pinned(tmp_path)
