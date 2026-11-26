"""Fas 4b: kalibrering. Platt (a + b·logit p) med ridge mot (0, 1) som standard; isotonisk (PAV) bara vid stort n."""
from __future__ import annotations

import numpy as np

from .devig import EPS

ISOTONIC_MIN_N = 2000


class NotEnoughData(ValueError):
    pass


def _logit(p):
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def logistic_offset_fit(X, y, offset=None, prior=None, l2=None, iters: int = 50):
    """Logistisk regression (Newton/IRLS) med offset och ridge mot prior. y får vara mjuk (0..1).
    l2: vektor eller skalär – straff λ_j·(β_j − prior_j)²/2 (λ i 'observationer')."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    n, k = X.shape
    off = np.zeros(n) if offset is None else np.asarray(offset, float)
    b0 = np.zeros(k) if prior is None else np.asarray(prior, float)
    lam = np.zeros(k) if l2 is None else np.broadcast_to(np.asarray(l2, float), (k,)).astype(float)
    beta = b0.copy()
    for _ in range(iters):
        eta = np.clip(X @ beta + off, -30, 30)
        mu = 1 / (1 + np.exp(-eta))
        w = np.maximum(mu * (1 - mu), 1e-9)
        g = X.T @ (y - mu) - lam * (beta - b0)
        H = (X * w[:, None]).T @ X + np.diag(lam) + 1e-9 * np.eye(k)
        step = np.linalg.solve(H, g)
        beta = beta + step
        if np.max(np.abs(step)) < 1e-10:
            break
    return beta


def platt_fit(p, y, prior=(0.0, 1.0), prior_n: float = 0.0) -> tuple[float, float]:
    p = np.asarray(p, float)
    X = np.column_stack([np.ones(len(p)), _logit(p)])
    a, b = logistic_offset_fit(X, y, prior=prior, l2=prior_n)
    return float(a), float(b)


def platt_apply(params: tuple[float, float], p):
    a, b = params
    z = a + b * _logit(p)
    return 1 / (1 + np.exp(-z))


def isotonic_fit(p, y, min_n: int = ISOTONIC_MIN_N):
    """Pool-adjacent-violators. Returnerar (x-trösklar, nivåer). Kastar NotEnoughData under min_n."""
    p = np.asarray(p, float)
    y = np.asarray(y, float)
    if len(p) < min_n:
        raise NotEnoughData(f"isotonisk kräver minst {min_n} rader (fick {len(p)})")
    o = np.argsort(p, kind="mergesort")
    xs, ys = p[o], y[o]
    lv, wt, lo = [], [], []
    for x, v in zip(xs, ys):
        lv.append(v); wt.append(1.0); lo.append(x)
        while len(lv) > 1 and lv[-2] > lv[-1]:
            w = wt[-2] + wt[-1]
            v2 = (lv[-2] * wt[-2] + lv[-1] * wt[-1]) / w
            lv[-2:], wt[-2:], lo[-2:] = [v2], [w], [lo[-2]]
    return np.array(lo), np.clip(np.array(lv), EPS, 1 - EPS)


def isotonic_apply(model, p):
    lo, lv = model
    i = np.searchsorted(lo, np.asarray(p, float), side="right") - 1
    return lv[np.clip(i, 0, len(lv) - 1)]
