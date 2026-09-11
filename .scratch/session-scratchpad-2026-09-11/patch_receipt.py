from pathlib import Path

report = Path('/home/sat/mcrl-v025-specprofile-ws/SPECIALIST-QOS-PROFILE-2026-09-11.md')
s = report.read_text()

old = ("- Runners `.scratch/specprofile/run_specprofile.py`, "
       "`.scratch/specprofile/run_specprofile2.py`;\n"
       "  mergers `.scratch/specprofile/merge_specprofile.py`, "
       "`.scratch/specprofile/merge_declared.py`;\n"
       "  launcher `.scratch/specprofile/launch.sh`.")
new = ("- Runners `.scratch/specprofile/run_specprofile.py`, "
       "`.scratch/specprofile/run_specprofile2.py`;\n"
       "  mergers `.scratch/specprofile/merge_specprofile.py`, "
       "`.scratch/specprofile/merge_declared.py`;\n"
       "  launcher `.scratch/specprofile/launch.sh`.\n"
       "- Interruption verification `.scratch/specprofile/verify_treatment.py` (read-only, no\n"
       "  physics, one short process; it enumerates the 31 declared settings, prints the\n"
       "  `_blackouts` selecting condition, the dense-path signature and the "
       "`evaluate_many` gate)\n"
       "  and `.scratch/specprofile/blackout_scale.py` (arithmetic on the frozen merged receipts;\n"
       "  produces no EE).")
assert old in s
s = s.replace(old, new)
report.write_text(s)
print('receipt patched')
