"""Representation-collapse penalties, ported from the sibling reproduction repo.

PORT PROVENANCE (smallest faithful port; no redesign)
----------------------------------------------------
Source file, read 2026-09-11:
    /home/u24/papers/modqn-paper-reproduction/src/modqn_paper_reproduction/
    shared_q_isolation/penalties.py

Two functions are ported verbatim in behaviour:

  ``srank_penalty(Phi)``  -- Kumar, Agarwal, Ghosh, Levine, "Implicit
      Under-Parameterization Inhibits Data-Efficient Deep Reinforcement
      Learning", arXiv:2010.14498v2 (ICLR 2021), Section 5, p.9, Eq. (6):

          L_p(Phi) = sigma_max(Phi)^2 - sigma_min(Phi)^2

      Phi = the PENULTIMATE-layer activations over a minibatch.  NOT
      mean-centered (the paper defines L_p on Phi itself).
      Coefficient, verbatim from the paper as quoted by the sibling's own
      docstring: "add the resulting value of L_p as a penalty to the TD error
      objective, with a tradeoff factor alpha = 0.001".  -> KUMAR_ALPHA = 0.001.

  ``q_row_decorrelation_penalty(Q)`` -- mean |off-diagonal Pearson| between the
      ROWS of Q.  The sibling invented this one; it is not from a paper and the
      sibling's code carries NO coefficient for it.  See the UNSPECIFIED note.

  ``srank_diagnostic(Phi)`` -- the NON-differentiable Kumar effective rank at
      delta = 0.01 on the MEAN-CENTERED Phi.  READ-ONLY readout, never a loss
      term.  The sibling's docstring is emphatic that the penalty and the
      diagnostic are different objects with different units and must never be
      reported as one another; that separation is preserved here.

WHAT THE SIBLING'S OWN EVIDENCE ACTUALLY IS (audited 2026-09-11, [V] by file)
-----------------------------------------------------------------------------
The premise this port was commissioned under -- "the one mechanism in the
sibling project with a measured positive effect" -- DOES NOT SURVIVE READING
THE SIBLING'S OWN RECORDS.  Verbatim, repeated in six config files and two
source files: **"READINESS-ONLY. No effectiveness claim."**
(``penalties.py:53``, ``trainer_penalty.py:44``, all six ``tier1b/*.yaml``.)

* The 12-run Tier-1b experiment these penalties were built for was **never
  dispatched**.  ``NEXT-SESSION-HANDOFF-2026-07-12-EVENING.md:113`` heads a
  section "BUILT, TESTED, NOT DISPATCHED (do not rebuild)"; ``:21`` marks
  Tier-1b HELD because the hypothesis it was built to discriminate ("the
  inversion") was refuted in the meantime.  There is no ``penalty_log.json``
  anywhere in the sibling repo and no run metadata stamped with a penalty.
* **There is no performance claim of any kind** -- no return, no reward, no EE.
  Every number that exists is diagnostic-on-diagnostic, from a 3-episode smoke
  (~29 updates, seed count unrecorded) or from a toy optimizer probe with no
  TD loss and no environment.
* The only quantitative *srank* "engagement" number was **self-corrected to
  null**: against a first-decile baseline ``TB-SRANK-nudge`` reported
  "PENALTY-FELL -61.2%"; against the true init the same arm was **+20.9%, the
  penalty ROSE**.  The sibling now hardcodes ``informative=None`` and
  ``in_run_verdict_is_authoritative=False`` for every srank arm
  (``trainer_penalty.py:408-421``).
* The one sibling sentence that does pair a penalty with EE --
  "the penalty changed training; coverage and EE improved together"
  (``CLOSURE-M4-RESULT-2026-07-18.md:106``) -- is about the sibling's
  capacity-side penalty (its own separate module, L_cap), a DIFFERENT
  mechanism that the sibling's own runner forbids stacking with these
  (``runner_concat.py:368-370``).  Do not conflate them.

So this port is a port of an UNTESTED mechanism.  That is stated here so no
later reader infers a pedigree from the fact that it was ported.

WHAT THE SIBLING DID SPECIFY, AND IS TAKEN FROM IT RATHER THAN FROM JUDGEMENT
-----------------------------------------------------------------------------
* **PER-HEAD IS THE SIBLING'S OWN CHOICE, NOT MINE.**  The sibling faces the
  same three-head shape and resolves it the same way: one penalty term per
  objective, each added inside that head's own backward on its own
  parameter-disjoint net, three times per update, DELIBERATELY NOT scalarized
  (``trainer_penalty.py:192-195, 279-303``).  This port reproduces that.  It
  is still a choice and is still stated; it is simply the sibling's.
* **ADDED AFTER THE TD REDUCTION**, to the already-reduced scalar MSE
  (``trainer_penalty.py:285, 292``).  Reproduced.
* **THE LOGGED TD LOSS STAYS TD-ONLY**, captured before the penalty is added
  (``trainer_penalty.py:286``), so a convergence gate never sees a
  penalty-inflated number.  Reproduced.
* **NON-FINITE PENALTY IS SKIPPED ENTIRELY**, not zeroed, because ``0.0*NaN``
  poisons the backward (``trainer_penalty.py:291-295``).  Reproduced.
* **NO SCHEDULE.**  Every one of the six presets is ``interval: 1``,
  ``log_every: 10``, constant coefficient, no warmup, no ramp, no on/off
  episode.  Reproduced: constant, from update 0.
* **SIX NAMED PRESETS**, ported verbatim as ``SIBLING_PRESETS`` below.
* **coef = 0.0 is the sibling's byte-identity negative control** (term not
  built at all).  Reproduced as ``kind="none"``.

DECLARED CHOICES THAT ARE MINE (made before any run)
-----------------------------------------------------
* **WHICH PRESET RUNS.**  One PENALTY arm is authorised, so one preset is run:
  ``TB-SRANK-kumar``, alpha = 1e-3 -- Kumar's paper value verbatim and the
  sibling's own code default ``KUMAR_ALPHA_DEFAULT``.  The other five are
  ported and named but NOT run.  No sweeping.
  Disclosed: on the sibling's substrate alpha = 1e-3 put the penalty at 9.9x
  the TD loss at init.  That ratio is substrate-specific; it is MEASURED and
  reported for this substrate rather than assumed.
* **``decorr`` IS PORTED BUT NOT RUNNABLE FAITHFULLY HERE.**  The sibling's Q
  rows are "the U=100 users of ONE env step", taken from a step-context
  snapshot it keeps alongside the minibatch (``trainer_penalty.py:200-211``).
  This trainer's ``update()`` has only a 128-transition replay minibatch
  spanning many users AND many timesteps; its rows are not the same object.
  The ``decorr`` branch here therefore computes the Pearson over the replay
  minibatch's rows, which is a DIFFERENT QUANTITY from the sibling's, and it
  is not run.  A faithful decorr arm needs a per-step Q batch this trainer
  does not have.
* **``null_grad``** is NOT a sibling mechanism.  It is this study's control
  arm.  See ``PenaltyConfig`` below.

OFF BY DEFAULT.  ``PenaltyConfig.kind == "none"`` is the default and the
trainer's penalised branch is entered only when the kind is not "none", so the
unpenalised path is bit-identical to the pre-port trainer.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn

# arXiv:2010.14498 p.9, verbatim: "a tradeoff factor alpha = 0.001".
KUMAR_ALPHA = 0.001

# Sibling ``penalties.py`` DEFAULT_EPS, ported verbatim with its reasoning:
# ``clamp_min`` (not ``+ eps``) so a non-degenerate row's denominator is
# returned UNCHANGED and the torch Pearson stays comparable with a NumPy
# ``np.corrcoef`` readout.
DEFAULT_EPS = 1e-12

# "none" is the OFF arm.  "srank"/"decorr" are the two sibling kinds.
# "null_grad" is this study's control (not a sibling mechanism).
PENALTY_KINDS = ("none", "srank", "decorr", "null_grad")

# The sibling's six named presets, ported verbatim from
# modqn-paper-reproduction/configs/shared_q_isolation/tier1b/*.yaml (all dated
# 2026-07-12; all interval=1, log_every=10, no schedule).  The "ratio to TD at
# init" column is the SIBLING's measurement on the SIBLING's substrate and is
# carried only as provenance -- it is not a prediction for this project.
#
#   name                 kind     coefficient   sibling ratio-to-TD @ init
SIBLING_PRESETS: dict[str, tuple[str, float, str]] = {
    "TB-DECORR-lo": ("decorr", 1e-3, "0.049x  'nudge'"),
    "TB-DECORR-hi": ("decorr", 1e-2, "0.49x   'approaching parity'"),
    "TB-DECORR-escape": ("decorr", 1e-1, "4.9x   'escape-or-bust'"),
    "TB-SRANK-nudge": ("srank", 5e-6, "0.049x  near-null NEGATIVE CONTROL"),
    "TB-SRANK-parity": ("srank", 1e-4, "0.99x   'the rung srank should be judged on'"),
    "TB-SRANK-kumar": ("srank", 1e-3, "9.9x    Kumar alpha verbatim"),
}


def preset_config(name: str, *, diagnostics: bool = False) -> "PenaltyConfig":
    """Build a ``PenaltyConfig`` from one of the sibling's six named presets."""
    if name not in SIBLING_PRESETS:
        raise ValueError(
            f"unknown sibling preset {name!r}; known: {sorted(SIBLING_PRESETS)}"
        )
    kind, coefficient, _ = SIBLING_PRESETS[name]
    return PenaltyConfig(
        kind=kind,
        coefficient=coefficient,
        diagnostics=diagnostics,
        preset=name,
    )


@dataclass(frozen=True)
class PenaltyConfig:
    """Configuration for the training-time collapse penalty. OFF by default.

    kind:
        "none"       -- no penalty term, no perturbation.  Bit-identical to the
                        pre-port trainer.
        "srank"      -- Kumar Eq. (6) on each head's penultimate features.
        "decorr"     -- mean |off-diagonal row Pearson| of each head's Q batch.
                        Coefficient UNSPECIFIED in the sibling; see module doc.
        "null_grad"  -- CONTROL.  No loss term at all.  After the TD gradient
                        is computed, a random isotropic vector of a DECLARED
                        norm is added to each parameter's ``.grad``.  Adam sees
                        only ``.grad``, so this is exactly equivalent to having
                        had an additive loss term of that gradient magnitude,
                        while carrying zero information about row redundancy or
                        spectral structure.  The norm per head is supplied in
                        ``null_grad_norms`` and is MEASURED from the PENALTY
                        arm's own logged penalty-gradient norms -- matched to
                        the measured term, not to a coefficient.

    coefficient:
        alpha.  For "srank" the sourced value is ``KUMAR_ALPHA`` = 0.001.

    null_grad_norms:
        Per-head target L2 norm of the injected random gradient.  Only read
        when kind == "null_grad".
    """

    kind: str = "none"
    coefficient: float = 0.0
    null_grad_norms: tuple[float, float, float] = (0.0, 0.0, 0.0)
    # READ-ONLY collapse readouts (srank_delta and mean |row Pearson|).  These
    # consume NO RNG and mutate nothing, so enabling them on the OFF arm does
    # not break its bit-identity with the pre-port trainer -- only its wall
    # time.  Enabled for all three arms so the readouts are comparable.
    diagnostics: bool = False
    # The sibling preset this configuration reproduces, for the record.
    preset: str = ""

    def __post_init__(self) -> None:
        if self.kind not in PENALTY_KINDS:
            raise ValueError(
                f"penalty kind must be one of {PENALTY_KINDS}, got {self.kind!r}"
            )
        if self.kind == "srank" and self.coefficient <= 0.0:
            raise ValueError("srank penalty needs a positive coefficient")
        if self.kind == "null_grad" and not any(
            n > 0.0 for n in self.null_grad_norms
        ):
            raise ValueError(
                "null_grad control needs at least one positive per-head target "
                "gradient norm, measured from the PENALTY arm"
            )

    @property
    def active(self) -> bool:
        return self.kind != "none"

    @property
    def is_loss_term(self) -> bool:
        """True when the mechanism adds a differentiable term to the loss."""
        return self.kind in ("srank", "decorr")


# ---------------------------------------------------------------------------
# (1) Kumar et al. Eq. (6) spectral penalty on the penultimate features
# ---------------------------------------------------------------------------
def penultimate_features(net: nn.Module, x: torch.Tensor) -> torch.Tensor:
    """Phi = penultimate-layer activations of a ``DQNNetwork`` on inputs ``x``.

    ``DQNNetwork.net`` (runtime/q_network.py) is an ``nn.Sequential`` ending in
    the output ``nn.Linear``, so ``net.net[:-1]`` is everything up to and
    including the last hidden activation.  With this project's default
    ``hidden_layers = (100, 50, 50)`` and ``batch_size = 128`` that is a
    (128, 50) matrix -- the same shape class as the sibling's (128, 50).
    """
    return net.net[:-1](x)


def srank_penalty(features: torch.Tensor, eps: float = DEFAULT_EPS) -> torch.Tensor:
    """Kumar Eq. (6):  L_p(Phi) = sigma_max(Phi)^2 - sigma_min(Phi)^2.

    Ported verbatim from the sibling.  NOT mean-centered.  Differentiable via
    ``torch.linalg.svdvals``.  Returns a 0-d tensor >= 0.
    """
    if features.dim() != 2:
        raise ValueError(
            f"srank_penalty expects a 2-D (batch, hidden) Phi, got "
            f"{tuple(features.shape)}"
        )
    if min(features.shape) < 2:
        raise ValueError(
            f"srank_penalty needs Phi with >=2 rows and >=2 columns, got "
            f"{tuple(features.shape)}"
        )
    s = torch.linalg.svdvals(features)
    return s[0] ** 2 - s[-1] ** 2


def srank_diagnostic(features: torch.Tensor, delta: float = 0.01) -> int:
    """READ-ONLY Kumar effective rank srank_delta(Phi) on the MEAN-CENTERED Phi.

    NEVER a loss term.  Ported verbatim from the sibling, which is emphatic
    that this integer and ``srank_penalty`` are different objects.
    """
    with torch.no_grad():
        f = features - features.mean(dim=0, keepdim=True)
        s = torch.linalg.svdvals(f)
        total = float(s.sum())
        if total <= 0.0:
            return 0
        c = torch.cumsum(s, dim=0) / total
        idx = torch.searchsorted(
            c, torch.tensor(1.0 - float(delta), device=c.device, dtype=c.dtype)
        )
        return int(idx.item()) + 1


# ---------------------------------------------------------------------------
# (2) cross-row Q de-correlation
# ---------------------------------------------------------------------------
def _row_pearson_offdiag(
    mat: torch.Tensor, eps: float = DEFAULT_EPS
) -> torch.Tensor:
    """Off-diagonal (i<j) Pearson correlations between the ROWS of ``mat``.

    Ported verbatim from the sibling, including its handling of degenerate
    rows: a zero-variance row has an UNDEFINED correlation and is DROPPED.
    """
    if mat.dim() != 2:
        raise ValueError(
            f"row-Pearson expects a 2-D (rows, cols) tensor, got "
            f"{tuple(mat.shape)}"
        )
    if mat.shape[0] < 2 or mat.shape[1] < 2:
        return mat.new_zeros(0)
    centered = mat - mat.mean(dim=1, keepdim=True)
    norms = centered.norm(dim=1)
    keep = norms > 0.0
    if int(keep.sum()) < 2:
        return mat.new_zeros(0)
    centered = centered[keep]
    norms = norms[keep].clamp_min(eps).unsqueeze(1)
    unit = centered / norms
    corr = unit @ unit.t()
    iu = torch.triu_indices(
        corr.shape[0], corr.shape[0], offset=1, device=corr.device
    )
    return corr[iu[0], iu[1]]


def mean_offdiag_row_pearson_torch(
    mat: torch.Tensor, eps: float = DEFAULT_EPS, *, absolute: bool = False
) -> torch.Tensor:
    """Mean off-diagonal row-Pearson of ``mat``, differentiable.

    NaN when fewer than 2 non-degenerate rows exist (matching the sibling).
    """
    off = _row_pearson_offdiag(mat, eps=eps)
    if off.numel() == 0:
        return mat.new_tensor(float("nan"))
    return off.abs().mean() if absolute else off.mean()


def q_row_decorrelation_penalty(
    q_values: torch.Tensor, eps: float = DEFAULT_EPS
) -> torch.Tensor:
    """Mean |off-diagonal Pearson| between the rows of ``q_values``.

    Ported verbatim.  DISCLOSED HAZARD, carried over from the sibling's own
    docstring because it decides how a null on this arm may be read: rho = 1 is
    a STATIONARY POINT of this penalty, so the gradient VANISHES exactly where
    the pathology is worst.  A null therefore has two readings -- "the
    mechanism does not help" and "the penalty never escaped its own flat
    corner" -- distinguished only by the LOGGED penalty trajectory, never by
    the endpoint metric.  The sibling measured Adam escaping the corner where
    plain SGD did not; this trainer also uses Adam.
    """
    return mean_offdiag_row_pearson_torch(q_values, eps=eps, absolute=True)


# ---------------------------------------------------------------------------
# (3) the control: matched-magnitude structureless gradient perturbation
# ---------------------------------------------------------------------------
def inject_matched_random_gradient(
    parameters: list[torch.nn.Parameter],
    target_norm: float,
    generator: torch.Generator,
) -> float:
    """Add an isotropic random vector of L2 norm ``target_norm`` to ``.grad``.

    NOT a sibling mechanism.  This is the NULL_PENALTY control: the same
    magnitude of gradient perturbation as the PENALTY arm's measured penalty
    gradient, carrying no information whatever about row redundancy or the
    feature spectrum.

    STATED LIMITATION: matching the NORM does not match the DIRECTION
    distribution.  In a ~20k-parameter space an isotropic random vector is
    nearly orthogonal to any fixed direction, whereas the penalty's gradient is
    not.  So this control bounds the "a perturbation of this size would have
    done it" reading; it does not reproduce the penalty's gradient geometry.
    Returns the norm actually injected.
    """
    if target_norm <= 0.0:
        return 0.0
    grads = [p.grad for p in parameters if p.grad is not None]
    if not grads:
        return 0.0
    noise = [
        torch.randn(g.shape, generator=generator, dtype=g.dtype, device=g.device)
        for g in grads
    ]
    total = torch.sqrt(sum((n * n).sum() for n in noise))
    if float(total) <= 0.0:
        return 0.0
    scale = float(target_norm) / float(total)
    for g, n in zip(grads, noise):
        g.add_(n * scale)
    return float(target_norm)


def gradient_norm(
    loss_term: torch.Tensor, parameters: list[torch.nn.Parameter]
) -> float:
    """L2 norm of d(loss_term)/d(parameters), without touching ``.grad``.

    Used by the PENALTY arm to MEASURE the magnitude the NULL arm must match.
    """
    grads = torch.autograd.grad(
        loss_term, parameters, retain_graph=True, allow_unused=True
    )
    total = 0.0
    for g in grads:
        if g is not None:
            total += float((g * g).sum())
    return total ** 0.5
