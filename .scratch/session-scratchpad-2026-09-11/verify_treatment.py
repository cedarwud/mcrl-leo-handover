"""Verify how the declared interruption treatment is selected and whether the
mandated dense a-r0 evaluator path can express it.  Read-only, no physics."""
import importlib.util
import inspect
import sys

SOURCE_ROOT = '/home/sat/mcrl-v025-c1c2suff-ws'
sys.path.insert(0, SOURCE_ROOT + '/src')

from mcrl.physics_v025.matrix import MATRIX_SETTINGS  # noqa: E402
from mcrl.physics_v025 import batch, integration, adapter  # noqa: E402
from mcrl.physics_v025.constants_v025 import (  # noqa: E402
    SAME_SATELLITE_INTERRUPTION_S, SATELLITE_CHANGE_INTERRUPTION_S,
)

print('=== declared constants ===')
print('SAME_SATELLITE_INTERRUPTION_S =', SAME_SATELLITE_INTERRUPTION_S)
print('SATELLITE_CHANGE_INTERRUPTION_S =', SATELLITE_CHANGE_INTERRUPTION_S)

print()
print('=== every declared matrix setting, label -> interruption code ===')
on = []
for s in MATRIX_SETTINGS:
    flag = s.interruption
    if flag == 'on':
        on.append(s.label)
print('total settings:', len(MATRIX_SETTINGS))
print('settings with interruption == "on":', len(on))
print(sorted(on))
print('settings with interruption == "off":',
      len([s for s in MATRIX_SETTINGS if s.interruption == 'off']))
print('label of the a-r treatment-0 cell:',
      [s.label for s in MATRIX_SETTINGS
       if s.architecture == 'a-r' and s.treatment == '0'])
print('label of the a-r treatment-H cell:',
      [s.label for s in MATRIX_SETTINGS
       if s.architecture == 'a-r' and s.treatment == 'H'])

print()
print('=== batch.evaluate_ar_tdm_catalogue signature (the mandated dense path) ===')
sig = inspect.signature(batch.evaluate_ar_tdm_catalogue)
print(sig)
print('has an interruption parameter:',
      any('interrupt' in p.lower() for p in sig.parameters))

print()
print('=== integration._blackouts: the condition that selects 0.062 vs 0.142 ===')
src, start = inspect.getsourcelines(integration._blackouts)
for i, line in enumerate(src):
    print('integration.py:%d: %s' % (start + i, line.rstrip()))

print()
print('=== adapter: how interruption_enabled is set ===')
src, start = inspect.getsourcelines(adapter.score_setting)
for i, line in enumerate(src):
    if 'interruption' in line or 'integrate_47' in line:
        print('adapter.py:%d: %s' % (start + i, line.rstrip()))

print()
print('=== probe StepEvaluator: dense-path gate and useful-time handling ===')
spec = importlib.util.spec_from_file_location(
    'probe',
    SOURCE_ROOT + '/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py')
probe = importlib.util.module_from_spec(spec)
sys.modules['probe'] = probe
spec.loader.exec_module(probe)
src, start = inspect.getsourcelines(probe.StepEvaluator.evaluate_many)
for i, line in enumerate(src):
    text = line.rstrip()
    if ('label !=' in text or 'a-r0' in text or 'self.evaluate(' in text
            or 'dict(decoding)' in text or 'evaluate_ar_tdm_catalogue' in text):
        print('run_v025_matrix_probe.py:%d: %s' % (start + i, text))

print()
print('=== run_setting_for: which labels have a sealed run setting ===')
for label in ('a-r0', 'a-rH', 'a-rSH'):
    try:
        rs = probe.run_setting_for(label)
        print(label, '-> OK', 'rate_target_bps=%r' % getattr(rs, 'rate_target_bps', None))
    except Exception as error:
        print(label, '-> %s: %s' % (type(error).__name__, error))

print()
print('=== scalar path availability on the frozen exact (arrays) panel ===')
from mcrl.physics_v025.tapes import ExogenousWorldTape  # noqa: E402
src, start = inspect.getsourcelines(ExogenousWorldTape.geometry_for)
for i, line in enumerate(src[:30]):
    print('tapes.py:%d: %s' % (start + i, line.rstrip()))

print()
print('=== discontinuities_from_event_ledger (scalar path only) ===')
src, start = inspect.getsourcelines(probe.discontinuities_from_event_ledger)
for i, line in enumerate(src):
    print('run_v025_matrix_probe.py:%d: %s' % (start + i, line.rstrip()))
