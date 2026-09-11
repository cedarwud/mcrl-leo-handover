"""Identify a TLE archive: root, file list, per-file sha256, file-set hash, and
compare against the frozen R2 prereg's ephemeris.frozen_files."""
import hashlib, json, sys
from pathlib import Path
repo = Path(sys.argv[1]); root = Path(sys.argv[2]).expanduser()
sys.path.insert(0, str(repo / "src"))
from mcrl.env.ephemeris import TleArchive
from mcrl.runtime.prereg import read_prereg
arc = TleArchive(root)
dates = list(arc.dates)
rows = arc.manifest_rows(dates)
from mcrl.runtime.training_pipeline import file_set_hash
rec = read_prereg(repo / "artifacts/PREREG-FROZEN-2026-08-25-R2.json")
fz = rec.sections["ephemeris"]
frozen_rows = fz["frozen_files"]
all_files = sorted(p.name for p in root.iterdir() if p.is_file())
blob = "".join(f"{hashlib.sha256((root/n).read_bytes()).hexdigest()}  {n}\n" for n in all_files)
print(json.dumps({
  "root": str(root.resolve()),
  "files_on_disk": len(all_files),
  "first": all_files[0], "last": all_files[-1],
  "archive_dates_used": len(dates),
  "live_file_set_sha256": file_set_hash(rows),
  "frozen_file_set_sha256": fz["file_set_sha256"],
  "matches_frozen_file_set": file_set_hash(rows) == fz["file_set_sha256"],
  "rows_equal_frozen_rows": rows == frozen_rows,
  "whole_dir_sha256_of_sha256sum_listing": hashlib.sha256(blob.encode()).hexdigest(),
  "frozen_archive": fz["archive"],
}, indent=1, default=str))
print("ROW0", json.dumps(rows[0], default=str)[:300])
