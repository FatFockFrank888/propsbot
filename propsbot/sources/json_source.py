"""Läs en match (lag, spelare, Pinnacles matchlinjer) och odds från JSON.

Formatet är medvetet enkelt så att vilken datakälla som helst (odds-API,
händelsedata-API) kan skriva det. Se examples/match.json.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..config import SHOT_TYPES
from ..form import ON_TARGET_PRIOR, POSITION_PRIOR, XG_PRIOR
from ..market import team_lambdas_from_pinnacle
from ..models import (MatchContext, MinutesModel, OddsQuote, OpponentProfile, PlayerProfile,
                      Referee, TeamContext, Weather)

LEAGUE_MIX = {"box": 0.42, "distance": 0.30, "header": 0.12, "setpiece": 0.07,
              "counter": 0.06, "freekick": 0.03}


def _player(d: dict, team: str) -> PlayerProfile:
    pos = d["position"]
    prior = POSITION_PRIOR.get(pos, POSITION_PRIOR["CM"])
    share = {t: prior["share"].get(t, 0.0) for t in SHOT_TYPES}
    share.update(d.get("share", {}))
    return PlayerProfile(
        player_id=d["id"], name=d["name"], team=team, position=pos,
        minutes=MinutesModel(**d.get("minutes", {"p_start": 1.0})),
        share=share,
        on_target={**ON_TARGET_PRIOR, **d.get("on_target", {})},
        xg_per_shot={**XG_PRIOR, **d.get("xg_per_shot", {})},
        xa_share=d.get("xa_share", prior["xa"]),
        pen_order=d.get("pen_order"),
    )


def _team(d: dict, exp_goals: float, is_home: bool) -> TeamContext:
    opp = d.get("opponent_profile", {})
    return TeamContext(
        name=d["name"],
        players=[_player(p, d["name"]) for p in d["players"]],
        exp_goals=exp_goals,
        base_mix={**LEAGUE_MIX, **d.get("base_mix", {})},
        xg_per_shot_type={**XG_PRIOR, **d.get("xg_per_shot_type", {})},
        opponent=OpponentProfile(
            allowed_mult={**{t: 1.0 for t in SHOT_TYPES}, **opp.get("allowed_mult", {})},
            block_height=opp.get("block_height", 0.0),
            ppda_z=opp.get("ppda_z", 0.0),
            pens_conceded_mult=opp.get("pens_conceded_mult", 1.0),
            keeper_save_skill=opp.get("keeper_save_skill", 0.0),
        ),
        pens_per_match=d.get("pens_per_match", 0.13),
        is_home=is_home,
    )


def load_match(path: str | Path) -> tuple[MatchContext, list[OddsQuote]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    pin = raw["pinnacle_match_odds"]
    lh, la = team_lambdas_from_pinnacle(
        tuple(pin["1x2"]), tuple(pin["total"]["odds"]), pin["total"]["line"],
        pin.get("team_totals"))
    match = MatchContext(
        match_id=raw["match_id"],
        home=_team(raw["home"], lh, True),
        away=_team(raw["away"], la, False),
        kickoff_utc=raw["kickoff_utc"],
        lineup_confirmed=raw.get("lineup_confirmed", False),
        referee=Referee(**raw.get("referee", {})),
        weather=Weather(**raw.get("weather", {})),
        competition=raw.get("competition", ""),
    )
    quotes = [OddsQuote(match_id=raw["match_id"], **q) for q in raw.get("quotes", [])]
    return match, quotes
