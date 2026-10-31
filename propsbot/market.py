"""Marknadssidan: marginalborttagning, Pinnacles matchlinjer -> väntade mål,
ensidiga Unibet/Kambi-priser -> sannolikhet, och marknadskonsensus för props.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from .config import MarketConfig


def logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def inv_logit(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


# ------------------------------------------------------------ marginalborttagning
def devig_proportional(odds: Sequence[float]) -> list[float]:
    imp = [1 / o for o in odds]
    s = sum(imp)
    return [x / s for x in imp]


def devig_power(odds: Sequence[float]) -> list[float]:
    """p_i = (1/o_i)^k med k så att summan = 1. Tar hänsyn till favorit/outsider."""
    imp = np.array([1 / o for o in odds])
    lo, hi = 0.5, 3.0
    for _ in range(80):
        k = (lo + hi) / 2
        s = (imp ** k).sum()
        if s > 1:
            lo = k
        else:
            hi = k
    p = imp ** ((lo + hi) / 2)
    return list(p / p.sum())


def devig_shin(odds: Sequence[float]) -> list[float]:
    """Shins metod (insiderandel z). Bra för 1X2 med tydlig favorit."""
    imp = np.array([1 / o for o in odds])
    booksum = imp.sum()
    n = len(imp)

    def probs(z: float) -> np.ndarray:
        return (np.sqrt(z ** 2 + 4 * (1 - z) * imp ** 2 / booksum) - z) / (2 * (1 - z))

    lo, hi = 0.0, 0.4
    for _ in range(80):
        z = (lo + hi) / 2
        if probs(z).sum() > 1:
            lo = z
        else:
            hi = z
    p = probs((lo + hi) / 2)
    return list(p / p.sum()) if n else []


# ------------------------------------------------- Pinnacle -> lagens väntade mål
def _pois_pmf(lam: float, kmax: int = 15) -> np.ndarray:
    k = np.arange(kmax + 1)
    logp = -lam + k * math.log(max(lam, 1e-9)) - np.array([math.lgamma(i + 1) for i in k])
    return np.exp(logp)


def _outcome_probs(lh: float, la: float) -> tuple[float, float, float, np.ndarray]:
    ph, pa = _pois_pmf(lh), _pois_pmf(la)
    grid = np.outer(ph, pa)
    home = np.tril(grid, -1).sum()
    away = np.triu(grid, 1).sum()
    draw = np.trace(grid)
    return home, draw, away, grid


def _p_over_total(grid: np.ndarray, line: float) -> float:
    k = grid.shape[0]
    tot = np.add.outer(np.arange(k), np.arange(k))
    return float(grid[tot > line].sum())


def lambdas_from_1x2_total(p_home: float, p_away: float, p_over: float,
                           total_line: float = 2.5) -> tuple[float, float]:
    """Hitta (λ_hemma, λ_borta) så att Poisson-modellen matchar Pinnacles
    marginalfria 1X2 och över/under."""
    target_sup = p_home - p_away

    def split_for_mu(mu: float) -> tuple[float, float]:
        lo, hi = -0.98, 0.98  # andel: lh = mu*(1+s)/2
        for _ in range(60):
            s = (lo + hi) / 2
            h, _, a, _ = _outcome_probs(mu * (1 + s) / 2, mu * (1 - s) / 2)
            if h - a < target_sup:
                lo = s
            else:
                hi = s
        s = (lo + hi) / 2
        return mu * (1 + s) / 2, mu * (1 - s) / 2

    lo, hi = 0.3, 7.0
    for _ in range(60):
        mu = (lo + hi) / 2
        lh, la = split_for_mu(mu)
        _, _, _, grid = _outcome_probs(lh, la)
        if _p_over_total(grid, total_line) < p_over:
            lo = mu
        else:
            hi = mu
    return split_for_mu((lo + hi) / 2)


def lambda_from_team_total(p_over: float, line: float) -> float:
    """λ för ett lag ur Pinnacles lagtotal (över line)."""
    lo, hi = 0.02, 6.0
    for _ in range(60):
        lam = (lo + hi) / 2
        pmf = _pois_pmf(lam)
        po = pmf[int(math.floor(line)) + 1:].sum()
        if po < p_over:
            lo = lam
        else:
            hi = lam
    return (lo + hi) / 2


def team_lambdas_from_pinnacle(odds_1x2: tuple[float, float, float],
                               odds_total: tuple[float, float], total_line: float = 2.5,
                               team_totals: dict | None = None) -> tuple[float, float]:
    """odds_1x2 = (hemma, oavgjort, borta), odds_total = (över, under).

    team_totals (valfritt) = {"home": (line, over_odds, under_odds), "away": (...)}.
    Lagtotaler är mer direkta och vägs in med 50 % om de finns.
    """
    ph, _, pa = devig_shin(odds_1x2)
    po, _ = devig_power(odds_total)
    lh, la = lambdas_from_1x2_total(ph, pa, po, total_line)
    if team_totals:
        if "home" in team_totals:
            line, o, u = team_totals["home"]
            lh = 0.5 * lh + 0.5 * lambda_from_team_total(devig_power((o, u))[0], line)
        if "away" in team_totals:
            line, o, u = team_totals["away"]
            la = 0.5 * la + 0.5 * lambda_from_team_total(devig_power((o, u))[0], line)
    return lh, la


# --------------------------------------------------------- ensidiga priser (Kambi)
def one_sided_margin(market: str, odds: float, cfg: MarketConfig) -> float:
    base, slope = cfg.one_sided_margin.get(market, (0.08, 0.015))
    m = base + slope * (odds - 2.0)
    return float(min(max(m, 0.0), cfg.max_one_sided_margin))


def fair_prob_one_sided(market: str, odds: float, cfg: MarketConfig) -> float:
    """Marknadens sannolikhet ur ett ensidigt pris: 1 / (odds × (1 + m(odds)))."""
    return 1.0 / (odds * (1.0 + one_sided_margin(market, odds, cfg)))


def estimate_one_sided_margin(pairs: Iterable[tuple[float, float]],
                              prior: tuple[float, float], prior_n: float = 50.0
                              ) -> tuple[float, float]:
    """Skatta (base, slope) för m(odds) ur par (ensidigt odds, Pinnacles marginalfria p).

    Varje par ger m_i = 1/(odds_i·p_i) − 1. Viktad minsta kvadrat med prior som
    motsvarar prior_n observationer (ridge mot priorvärdet).
    """
    pairs = [(o, p) for o, p in pairs if o > 1 and 0 < p < 1]
    if not pairs:
        return prior
    x = np.array([o - 2.0 for o, _ in pairs])
    y = np.array([1.0 / (o * p) - 1.0 for o, p in pairs])
    X = np.column_stack([np.ones_like(x), x])
    lam = np.diag([prior_n, prior_n * 4.0])
    beta0 = np.array(prior)
    beta = np.linalg.solve(X.T @ X + lam, X.T @ y + lam @ beta0)
    return float(beta[0]), float(beta[1])


# ------------------------------------------------------------- marknadskonsensus
@dataclass
class PropMarketView:
    p_pinnacle: float | None
    p_kambi: float | None
    p_market: float | None
    pinnacle_present: bool


def prop_market_prob(market: str, cfg: MarketConfig,
                     pinnacle_over: float | None = None,
                     pinnacle_under: float | None = None,
                     kambi_master_over: float | None = None) -> PropMarketView:
    """Kombinera Pinnacle (helst tvåsidigt) och Kambis huvudpris till en sannolikhet.

    Kambi-gruppen räknas som EN röst, oavsett hur många Kambi-bolag som finns.
    """
    p_pin = None
    if pinnacle_over and pinnacle_under:
        p_pin = devig_power((pinnacle_over, pinnacle_under))[0]
    elif pinnacle_over:
        p_pin = 1.0 / (pinnacle_over * 1.04)  # Pinnacle ensidigt: liten marginal
    p_k = fair_prob_one_sided(market, kambi_master_over, cfg) if kambi_master_over else None

    if p_pin is not None and p_k is not None:
        w = cfg.pinnacle_weight / (cfg.pinnacle_weight + cfg.kambi_weight)
        p = inv_logit(w * logit(p_pin) + (1 - w) * logit(p_k))
    else:
        p = p_pin if p_pin is not None else p_k
    return PropMarketView(p_pin, p_k, p, p_pin is not None)
