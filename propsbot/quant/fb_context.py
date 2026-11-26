"""F4 (docs/PLAN_FOOTBALL_PROPS.md): matchkontext för fotbollens spelarprops.

Varje faktor är en multiplikator på väntat antal (1,0 = ingen effekt), krympt mot 1 vid litet underlag och
klippt till ett intervall. Saknad data ger 1,0. Elasticiteterna (exponenterna) skattas i backtesten
(tools/backtest_per90.py --context) och används bara om de förbättrar utanför urvalet.

  opp_factor    motståndarens medgivna antal per match / ligans snitt (krympt mot 1 med prior_n matcher)
  home_factor   hemma/borta: konstant (1 + h) hemma, 1/(1 + h) borta
  rest_days     dagar sedan lagets senaste match FÖRE avspark (alla tävlingar), aldrig efter
  rest_factor   1 − s vid kort vila (≤ short_days), annars 1
  team_goal_factor  (lagets väntade mål / lagets snitt) – samma som player_model.model_probs (ratio)
"""
from __future__ import annotations

import math

OPP_CLIP = (0.8, 1.25)
TEAM_CLIP = (0.6, 1.7)


def _clip(x: float, lo: float, hi: float) -> float:
    return min(max(x, lo), hi)


def opp_factor(conceded: list[float], league_avg: float, prior_n: float = 5.0, clip=OPP_CLIP) -> float:
    """conceded: motståndarens medgivna antal (t.ex. skott) per match, senaste först."""
    xs = [x for x in conceded if x is not None and not (isinstance(x, float) and math.isnan(x))]
    if not league_avg or league_avg <= 0 or not xs:
        return 1.0
    ratio = (sum(xs) + prior_n * league_avg) / ((len(xs) + prior_n) * league_avg)
    return _clip(ratio, *clip)


def home_factor(is_home: bool | None, h: float) -> float:
    if is_home is None:
        return 1.0
    return (1.0 + h) if is_home else 1.0 / (1.0 + h)


def rest_days(match_times: list[float], kickoff: float) -> float | None:
    """Dagar sedan senaste match strikt före avspark (minst 12 h före, så samma match aldrig räknas)."""
    prev = [t for t in match_times if t is not None and t < kickoff - 12 * 3600]
    if not prev:
        return None
    return (kickoff - max(prev)) / 86400.0


def rest_factor(days: float | None, s: float, short_days: float = 3.5) -> float:
    if days is None:
        return 1.0
    return 1.0 - s if days <= short_days else 1.0


def team_goal_factor(exp_goals: float | None, team_avg: float | None, clip=TEAM_CLIP) -> float:
    if not exp_goals or not team_avg or team_avg <= 0:
        return 1.0
    return _clip(exp_goals / max(team_avg, 0.3), *clip)


def apply(mu: float, factors: dict[str, float], elasticity: dict[str, float]) -> float:
    """mu · Π faktor^elasticitet (faktorer utan elasticitet ignoreras)."""
    out = mu
    for k, f in factors.items():
        e = elasticity.get(k, 0.0)
        if e and f and f > 0:
            out *= f ** e
    return out
