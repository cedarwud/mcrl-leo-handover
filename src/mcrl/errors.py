"""Typed fail-closed errors for `mcrl` runtime and environment contracts.

New file (W-16).  Mirrors the role of the source project's
``family_b_r3/errors.py`` without importing any of its r3-specific contract
vocabulary.  Every guard added by a declared patch in
``docs/PATCH-LEDGER.md`` raises one of these, so a training run can never
continue past a violated contract.
"""

from __future__ import annotations


class MCRLContractError(ValueError):
    """Base error for a violated mcrl runtime/environment contract."""


class NonFiniteTrainingError(MCRLContractError):
    """Loss, gradient, or network parameter left the finite domain.

    SDD §3.7 P-3 / §6 G-11: training must abort loudly rather than continue
    silently on NaN, because the G-3 collapse metrics would otherwise be
    computed on a NaN policy and read as a valid result.
    """


class SelectedActionInvalidError(MCRLContractError):
    """A selected action is invalid under its own decision mask.

    SDD §3.7 P-4.  ``NO_OP_ACTION`` is not an invalid action: it is the
    declared outcome of an empty mask (§4A.5a(1)).
    """
