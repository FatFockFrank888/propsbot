"""F2 (docs/PLAN_FOOTBALL_PROPS.md): takt per 90 med Empirical Bayes mot positions- och ligaprior.

    μ̂90 = (M_spelare · x̄90 + M_prior · μ90_pos) / (M_spelare + M_prior)

M_spelare = viktade minuter (vikt 0,5^(ålder i matcher / halveringstid), förra säsongen × prev_season_weight,
nollställd vid lag- eller ligabyte). λ = μ̂90 · E[min] / 90.
"""
from __future__ import annotations

import math
from collections import defaultdict

M_PRIOR = {"shots": 450.0, "shots_on_target": 630.0, "fouls": 450.0, "cards": 630.0, "tackles": 450.0}
GROUPS = ("GK", "CB", "FB", "DM_CM", "AM_W", "ST")

_POS = {
    "G": "GK", "GK": "GK",
    "CD": "CB", "CD-L": "CB", "CD-R": "CB", "CB": "CB", "SW": "CB",
    "LB": "FB", "RB": "FB", "LWB": "FB", "RWB": "FB", "WB": "FB", "D": "FB",
    "DM": "DM_CM", "CM": "DM_CM", "CM-L": "DM_CM", "CM-R": "DM_CM", "M": "DM_CM",
    "AM": "AM_W", "AM-L": "AM_W", "AM-R": "AM_W", "LM": "AM_W", "RM": "AM_W", "LW": "AM_W", "RW": "AM_W",
    "F": "ST", "CF": "ST", "CF-L": "ST", "CF-R": "ST", "ST": "ST", "LF": "ST", "RF": "ST", "FW": "ST",
}


def position_group(abbr: str | None) -> str | None:
    """ESPN-förkortning -> grupp. 'SUB'/okänd -> None (använd spelarens vanliga position)."""
    return _POS.get((abbr or "").upper())


def shrunk_rate(rows: list[dict], prior_rate90: float, m_prior: float, half_life_matches: float = 13.0,
                prev_season_weight: float = 0.3, reset_prev: bool = False) -> tuple[float, float]:
    """rows: {"min", "n" (antal), "age" (matcher sedan, 0 = senaste), "prev" (förra säsongen)}.
    Returnerar (μ̂90, viktade minuter M_spelare)."""
    m_w = x_w = 0.0
    for r in rows:
        mins = r.get("min") or 0.0
        if mins <= 0 or (r.get("prev") and reset_prev):
            continue
        w = 0.5 ** (r.get("age", 0) / half_life_matches) * (prev_season_weight if r.get("prev") else 1.0)
        m_w += w * mins
        x_w += w * (r.get("n") or 0.0)
    rate = (x_w * 90.0 + m_prior * prior_rate90) / (m_w + m_prior) if (m_w + m_prior) > 0 else prior_rate90
    return float(rate), float(m_w)


def lambda_base(rate90: float, exp_min: float) -> float:
    return rate90 * exp_min / 90.0


def positional_priors(rows: list[dict], stat: str, min_minutes: float = 900.0) -> dict:
    """Per (liga, grupp): Σ antal · 90 / Σ minuter. Grupper med för få minuter faller tillbaka på ligasnittet
    (alla utespelare), och därefter på snittet över alla ligor. rows: {"liga", "grupp", "min", stat}."""
    acc = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        if r.get("grupp") in (None, "GK") or not r.get("min"):
            continue
        for key in ((r["liga"], r["grupp"]), (r["liga"], "*"), ("*", r["grupp"]), ("*", "*")):
            acc[key][0] += r.get(stat, 0.0) or 0.0
            acc[key][1] += r["min"]
    out = {}
    for (lg, g), (x, m) in acc.items():
        if m >= min_minutes:
            out[(lg, g)] = x * 90.0 / m
    return out


def prior_for(priors: dict, league: str, group: str | None) -> float:
    for key in ((league, group), ("*", group), (league, "*"), ("*", "*")):
        if key in priors and key[1] is not None:
            return priors[key]
    return math.nan
