from pathlib import Path

report = Path('/home/sat/mcrl-v025-specprofile-ws/SPECIALIST-QOS-PROFILE-2026-09-11.md')
section = Path('/home/sat/mcrl-v025-specprofile-ws/.scratch/specprofile/interruption_section.md')

s = report.read_text()

head = (
    '**No interruption-scored EE exists for the `CAP_050` search winner, for the budgeted version, '
    'or for any other arm: the declared handover interruption is matrix treatment `H`/`SH` '
    '(10 of the 31 declared settings), this panel is the single cell `a-r0` whose treatment code is '
    '`interruption == "off"`, and the mandated dense evaluator `batch.evaluate_ar_tdm_catalogue` '
    'has no interruption parameter at all while `StepEvaluator.evaluate_many` takes the dense path '
    'only when the label is exactly `a-r0` (`run_v025_matrix_probe.py:798`) — so "dense batch" and '
    '"interruption on" are mutually exclusive in this engine, scoring the treatment would require '
    'the scalar path that the mandatory evaluator rule replaces with a raising stub, and the '
    '62.502712 → 17.257910 trade-off therefore cannot be tested on this panel; every figure below '
    'is `a-r0`, interruption off, and stands unchanged.**\n\n'
)

marker = '**The `CAP_050` search winner (62.502712'
assert s.startswith(marker), s[:80]
if not s.startswith(head[:60]):
    s = head + s

body = section.read_text()
assert '## Under the declared handover interruption' in body
if '## Under the declared handover interruption' not in s:
    s = s.rstrip('\n') + '\n' + body

report.write_text(s)
print('patched, lines =', len(s.splitlines()))
