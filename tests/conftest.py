"""Pytest bootstrap.

There used to be a ``_port_shim`` here.  W-01 ported ``algorithms/modqn.py``
byte-for-byte along with five module-level imports the repo did not have, so
the tree could not be imported at all and every test ran against stand-ins
installed into ``sys.modules``.

All five are gone:

======================================  ==========================================
``mcrl.env.step``                       W-10 repointed the container types to
                                        ``env.step_types``; ``StepEnvironment`` is
                                        a ``TYPE_CHECKING``-only import
``mcrl.runtime.popart_online``          W-09 removed the import entirely
``mcrl.runtime.angle_aware_ee``         W-06 ported the per-UE eta closure into
                                        ``runtime/energy_efficiency.py``
``mcrl.runtime.trainer_config_validation``  written fresh, not ported — and the
                                        permissive stand-in had been MASKING it
``mcrl.artifacts``                      W-12 ported the checkpoint payloads
======================================  ==========================================

``test_no_shim_remains.py`` keeps it that way.
"""
