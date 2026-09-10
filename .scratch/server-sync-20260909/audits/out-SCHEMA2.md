Implemented Q1 schema v2 without modifying sealed artifacts.

- New schema: `mcrl-v025-stagec-q1-action-v2`
- Digest: `66ed4a3f9222ac7f20f4334ffab92f6164d2dad203cbac7f7d4e1728ae4ad654`
- Serialized dimension: 15
- Effective dimension: **14**, up from 12
- Old/new matrix rank: 14 / 14
- `missing_incumbent` retained and documented as structurally constant: 0 missing across 18,000 incumbent mappings
- Elevation/visibility correlation: `0.930012` overall; `0.857463` on non-null links
- All 1,302 sealed files opened during execution had identical before/after digests
- Four regression tests passed
- No learner or EE endpoint ran

Deliverables:

- [Q1-SCHEMA-V2-2026-09-10.md](/home/sat/mcrl-v025-design-ws/Q1-SCHEMA-V2-2026-09-10.md)
- [census.json](/home/sat/mcrl-v025-design-ws/.scratch/schema-v2/census.json)
- [q1_schema_v2.py](/home/sat/mcrl-v025-design-ws/q1_schema_v2.py)
- [validation script](/home/sat/mcrl-v025-design-ws/.scratch/schema-v2/validate.py)

`PEAK_RSS_KB=1740436`; watchdog limit `4194304 KiB`, not triggered.
