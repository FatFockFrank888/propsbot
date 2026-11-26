"""Fas 7: mått (log-loss, Brier, ECE, CLV), bootstrap per match och befordringsregel."""
from __future__ import annotations

import math
import random

import numpy as np

from .devig import EPS


def logloss(p, y) -> float:
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    y = np.asarray(y, float)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def brier(p, y) -> float:
    p, y = np.asarray(p, float), np.asarray(y, float)
    return float(((p - y) ** 2).mean())


def ece(p, y, bins: int = 10) -> float:
    p, y = np.asarray(p, float), np.asarray(y, float)
    idx = np.minimum((p * bins).astype(int), bins - 1)
    tot = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            tot += m.sum() * abs(p[m].mean() - y[m].mean())
    return float(tot / len(p))


def clv_pp(p_close: float, odds: float) -> float | None:
    """Samma som skarp_clv._pp: (p_stängning − 1/odds) i procentenheter."""
    if p_close is None or not odds or odds <= 1 or p_close != p_close:
        return None
    return (p_close - 1.0 / odds) * 100


def boot_ci(values, groups, stat=np.mean, n: int = 2000, seed: int = 7) -> tuple[float, float]:
    """95 % bootstrap-intervall med omdragning av hela grupper (match/dag)."""
    by: dict = {}
    for v, g in zip(values, groups):
        by.setdefault(g, []).append(v)
    keys = list(by)
    if not keys:
        return (math.nan, math.nan)
    rnd = random.Random(seed)
    res = []
    for _ in range(n):
        xs = [v for _ in keys for v in by[keys[rnd.randrange(len(keys))]]]
        res.append(float(stat(xs)))
    res.sort()
    return res[int(0.025 * n)], res[int(0.975 * n) - 1]


def promote(n_settled: int, clv_ci: tuple[float, float], fold_ll_better: list[bool], min_n: int = 150) -> bool:
    """Skugga -> förslag om skarpt läge: ≥ min_n avgjorda, CLV-intervallet över 0 och bättre log-loss i ≥ 2/3 av vecken."""
    if n_settled < min_n or not fold_ll_better:
        return False
    return clv_ci[0] > 0 and sum(fold_ll_better) >= math.ceil(2 * len(fold_ll_better) / 3)
