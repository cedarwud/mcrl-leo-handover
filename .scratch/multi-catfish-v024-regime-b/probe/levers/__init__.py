"""Declared Track-B iteration-2 physics levers.

Import :mod:`registry` for lookup.  No module installs a process-global
override; every physics change is an explicit detached call.
"""

from .registry import LEVER_PRIORITY, LEVERS, apply_profile, get_lever

__all__ = ["LEVER_PRIORITY", "LEVERS", "apply_profile", "get_lever"]
