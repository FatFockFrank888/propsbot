"""Lagvolym: Pinnacles väntade mål -> väntade skott per skottyp i just den här matchen.

Här sitter volymfaktorn och matchupjusteringen (motståndarprofil + matchbild).
"""
from __future__ import annotations

import math

from .config import SHOT_TYPES, MatchupConfig
from .models import MatchContext, TeamContext


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def matchup_multipliers(team: TeamContext, fav_share: float,
                        cfg: MatchupConfig) -> dict[str, float]:
    """Multiplikator per skottyp utifrån motståndarens profil och matchbild.

    fav_share = lagets andel av matchens väntade mål (0.5 = jämnt).
    """
    opp = team.opponent
    out: dict[str, float] = {}
    fav = fav_share - 0.5  # >0 = favorit
    for t in SHOT_TYPES:
        m = opp.allowed_mult.get(t, 1.0)
        # Lågt block (negativ block_height) + favorit -> fler distansskott/inlägg,
        # färre kontringar.
        low_block = max(0.0, -opp.block_height)
        if t == "distance":
            m *= 1.0 + 0.08 * low_block + cfg.favourite_distance_slope * fav * 0.5
        elif t == "header":
            m *= 1.0 + 0.05 * low_block + 0.3 * fav * 0.5
        elif t == "counter":
            high_line = max(0.0, opp.block_height)
            m *= 1.0 + 0.10 * high_line + cfg.favourite_counter_slope * fav * 0.5
        elif t == "box":
            m *= 1.0 - 0.04 * low_block
        elif t == "penalty":
            m *= opp.pens_conceded_mult
        lo, hi = 1.0 - cfg.max_effect, 1.0 + cfg.max_effect
        if t == "penalty":
            lo, hi = 0.5, 1.6  # straff styrs främst av domare/motstånd, eget tak
        out[t] = _clip(m, lo, hi)
    return out


def weather_multipliers(match: MatchContext) -> tuple[dict[str, float], float]:
    """(volymmultiplikator per typ, träffprocentmultiplikator)."""
    w = match.weather
    vol = {t: 1.0 for t in SHOT_TYPES}
    acc = 1.0
    if w.wind_ms > 8:
        acc *= 1.0 - min(0.10, 0.01 * (w.wind_ms - 8))
    if w.heavy_rain:
        vol["distance"] *= 1.05
        acc *= 0.97
    return vol, acc


def team_type_rates(match: MatchContext, team: TeamContext, cfg: MatchupConfig
                    ) -> dict[str, float]:
    """Väntade skott per typ (per 90 min) så att väntade mål = Pinnacles linje.

    Straffar modelleras separat; resten av lagets väntade mål fördelas på
    skottyper enligt (lagets mix × matchup) och översätts till skott via xG/skott.
    """
    other = match.away if team is match.home else match.home
    total = team.exp_goals + other.exp_goals
    fav_share = team.exp_goals / total if total > 0 else 0.5
    mm = matchup_multipliers(team, fav_share, cfg)
    wv, _ = weather_multipliers(match)

    pen_rate = team.pens_per_match * match.referee.pen_mult * mm["penalty"]
    pen_xg = team.xg_per_shot_type.get("penalty", 0.76)
    open_goals = max(0.05, team.exp_goals - pen_rate * pen_xg)

    raw = {}
    for t in SHOT_TYPES:
        if t == "penalty":
            continue
        mult = mm[t] * wv[t]
        if t == "freekick":
            mult *= match.referee.freekick_mult
        raw[t] = team.base_mix.get(t, 0.0) * mult
    s = sum(raw.values())
    mix = {t: v / s for t, v in raw.items()} if s > 0 else raw
    xg_per_shot = sum(mix[t] * team.xg_per_shot_type.get(t, 0.1) for t in mix)
    total_open_shots = open_goals / max(xg_per_shot, 1e-6)
    rates = {t: total_open_shots * mix[t] for t in mix}
    rates["penalty"] = pen_rate
    if any(math.isnan(v) for v in rates.values()):
        raise ValueError(f"NaN i lagvolym för {team.name}")
    return rates
