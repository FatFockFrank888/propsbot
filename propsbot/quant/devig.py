"""Fas 1: marginalborttagning med power-metoden (returnerar k), proportionell, Shin och ensidiga priser.

power: p_i = (1/o_i)^k med k så att Σ p_i = 1. k > 1 vid positiv marginal, k < 1 vid negativ (arb).
"""
from __future__ import annotations

import math
from typing import Sequence

from ..market import devig_shin

EPS = 1e-4


def _check(odds: Sequence[float], n_min: int = 2) -> list[float]:
    o = [float(x) for x in odds]
    if len(o) < n_min:
        raise ValueError(f"minst {n_min} utfall krävs (fick {len(o)}); ensidigt pris -> one_sided()")
    if any(not math.isfinite(x) or x <= 1.0 for x in o):
        raise ValueError(f"odds måste vara > 1: {o}")
    return o


def power(odds: Sequence[float], tol: float = 1e-12) -> tuple[list[float], float]:
    """(sannolikheter, k). Σ (1/o_i)^k = 1 löses med bisektion i log-k."""
    imp = [1.0 / x for x in _check(odds)]
    f = lambda k: sum(q ** k for q in imp) - 1.0          # avtagande i k (alla q < 1)
    lo, hi = 1e-3, 1.0
    while f(hi) > 0:
        hi *= 2.0
        if hi > 1e4:
            raise ValueError("power-devig konvergerar inte")
    while f(lo) < 0:
        lo /= 2.0
        if lo < 1e-9:
            raise ValueError("power-devig konvergerar inte")
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
        if hi / lo - 1.0 < tol:
            break
    k = math.sqrt(lo * hi)
    p = [q ** k for q in imp]
    s = sum(p)
    return [x / s for x in p], k


def proportional(odds: Sequence[float]) -> list[float]:
    imp = [1.0 / x for x in _check(odds)]
    s = sum(imp)
    return [x / s for x in imp]


def shin(odds: Sequence[float]) -> list[float]:
    return devig_shin(_check(odds))


def margin(odds: Sequence[float]) -> float:
    """Bokens marginal (overround − 1)."""
    return sum(1.0 / x for x in _check(odds, 1)) - 1.0


def one_sided(odds: float, margin_: float) -> float:
    """Ensidigt pris med antagen/skattad marginal m: p = 1 / (odds · (1 + m))."""
    o = _check([odds], 1)[0]
    if not -0.5 < margin_ < 1.0:
        raise ValueError(f"orimlig marginal {margin_}")
    return min(1.0 - EPS, 1.0 / (o * (1.0 + margin_)))


def clip(p: float, eps: float = EPS) -> float:
    return min(max(float(p), eps), 1.0 - eps)


def base_logit(p: float, eps: float = EPS) -> float:
    """logit(clip(p)) – marknadens ankare (motsvarar init_score)."""
    q = clip(p, eps)
    return math.log(q / (1.0 - q))


def sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)
