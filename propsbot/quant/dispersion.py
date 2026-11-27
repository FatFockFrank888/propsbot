"""Fas 5: negativ binomial – form r skattad ur (väntat μ, utfall y) med momentmetod, krympt mot prior.

Var(y) = μ + μ²/r  =>  1/r ≈ Σ[(y − μ)² − μ] / Σ μ². Prior: prior_n observationer med 1/r = 1/prior_r.
"""
from __future__ import annotations

import numpy as np

R_MIN, R_MAX = 1.0, 200.0


def fit_nb_r(mu, y, prior_r: float = 10.0, prior_n: float = 0.0, r_bounds=(R_MIN, R_MAX)) -> float:
    mu = np.asarray(mu, float)
    y = np.asarray(y, float)
    ok = np.isfinite(mu) & np.isfinite(y) & (mu > 0)
    mu, y = mu[ok], y[ok]
    if len(mu) == 0:
        return float(prior_r)
    m2 = mu ** 2
    num = float(((y - mu) ** 2 - mu).sum()) + prior_n * float(m2.mean()) / prior_r
    den = float(m2.sum()) + prior_n * float(m2.mean())
    inv = num / den
    lo, hi = r_bounds
    inv = min(max(inv, 1.0 / hi), 1.0 / lo)
    return 1.0 / inv
