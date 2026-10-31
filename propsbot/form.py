"""Dagsform utan brus: viktade snitt med halveringstid i spelade minuter,
hierarkisk krympning mot positions-/ligaprior och snabbare minne vid rollbyte.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .config import SHOT_TYPES, FormConfig
from .models import MinutesModel, OpponentProfile, PlayerProfile

# Startvärden per position (ungefärliga, ska skattas om på er egen liga-data).
# share = andel av lagets skott av typen medan spelaren är på plan.
POSITION_PRIOR: dict[str, dict] = {
    "ST": {"share": {"box": 0.26, "distance": 0.10, "header": 0.22, "setpiece": 0.14,
                     "counter": 0.30, "freekick": 0.05}, "xa": 0.10},
    "W":  {"share": {"box": 0.13, "distance": 0.14, "header": 0.06, "setpiece": 0.07,
                     "counter": 0.20, "freekick": 0.12}, "xa": 0.15},
    "AM": {"share": {"box": 0.11, "distance": 0.17, "header": 0.04, "setpiece": 0.08,
                     "counter": 0.12, "freekick": 0.22}, "xa": 0.17},
    "CM": {"share": {"box": 0.06, "distance": 0.13, "header": 0.05, "setpiece": 0.09,
                     "counter": 0.05, "freekick": 0.12}, "xa": 0.09},
    "DM": {"share": {"box": 0.03, "distance": 0.08, "header": 0.05, "setpiece": 0.08,
                     "counter": 0.02, "freekick": 0.05}, "xa": 0.05},
    "WB": {"share": {"box": 0.04, "distance": 0.05, "header": 0.04, "setpiece": 0.05,
                     "counter": 0.06, "freekick": 0.03}, "xa": 0.10},
    "FB": {"share": {"box": 0.03, "distance": 0.05, "header": 0.04, "setpiece": 0.05,
                     "counter": 0.04, "freekick": 0.03}, "xa": 0.08},
    "CB": {"share": {"box": 0.03, "distance": 0.02, "header": 0.16, "setpiece": 0.15,
                     "counter": 0.00, "freekick": 0.01}, "xa": 0.02},
    "GK": {"share": {t: 0.0 for t in SHOT_TYPES}, "xa": 0.0},
}
ON_TARGET_PRIOR = {"box": 0.38, "distance": 0.27, "header": 0.30, "setpiece": 0.32,
                   "counter": 0.42, "freekick": 0.28, "penalty": 0.83}
XG_PRIOR = {"box": 0.14, "distance": 0.035, "header": 0.10, "setpiece": 0.09,
            "counter": 0.20, "freekick": 0.06, "penalty": 0.76}


@dataclass
class PlayerMatchRow:
    """En match för en spelare (från händelsedata)."""
    date: str
    minutes: float
    position: str
    shots: dict[str, float] = field(default_factory=dict)       # per typ
    sot: dict[str, float] = field(default_factory=dict)
    xg: dict[str, float] = field(default_factory=dict)
    xa: float = 0.0
    team_shots: dict[str, float] = field(default_factory=dict)  # lagets totalt per typ
    team_xa: float = 0.0
    manager: str = ""
    distorted: bool = False  # rött kort, tidig skada, storseger etc.


def _decay_weights(rows: list[PlayerMatchRow], half_life: float, cfg: FormConfig) -> list[float]:
    """Vikt per match: 0.5^(ålder/halveringstid), där ålder mäts i spelade
    90-minutersekvivalenter efter matchen (nyast = 0)."""
    w = [0.0] * len(rows)
    age = 0.0
    for i in range(len(rows) - 1, -1, -1):
        r = rows[i]
        d = cfg.distorted_match_weight if r.distorted else 1.0
        w[i] = (0.5 ** (age / half_life)) * d
        age += r.minutes / 90.0
    return w


def role_changed(rows: list[PlayerMatchRow], lookback: int = 3) -> bool:
    """Ny position i ≥2 av de senaste 3 matcherna, eller tränarbyte nyligen."""
    if len(rows) <= lookback:
        return False
    recent, older = rows[-lookback:], rows[:-lookback]
    main_old = Counter(r.position for r in older).most_common(1)[0][0]
    new_pos = sum(r.position != main_old for r in recent) >= 2
    new_manager = bool(recent[-1].manager) and recent[-1].manager != older[-1].manager
    return new_pos or new_manager


def build_player_profile(player_id: str, name: str, team: str, position: str,
                         rows: list[PlayerMatchRow], minutes: MinutesModel,
                         cfg: FormConfig | None = None, pen_order: int | None = None,
                         share_override: dict[str, float] | None = None) -> PlayerProfile:
    """Bygg en spelarprofil ur matchhistorik (äldst först)."""
    cfg = cfg or FormConfig()
    prior = POSITION_PRIOR.get(position, POSITION_PRIOR["CM"])
    rows = [r for r in rows if r.minutes > 0]
    mult = cfg.role_change_half_life_mult if role_changed(rows) else 1.0
    w_share = _decay_weights(rows, cfg.half_life_share * mult, cfg)
    w_qual = _decay_weights(rows, cfg.half_life_quality * mult, cfg)

    share, on_target, xg = {}, {}, {}
    for t in SHOT_TYPES:
        if t == "penalty":
            share[t] = 0.0
        else:
            num = sum(w * r.shots.get(t, 0.0) for w, r in zip(w_share, rows))
            den = sum(w * r.team_shots.get(t, 0.0) * r.minutes / 90.0 for w, r in zip(w_share, rows))
            # Prior-vikt i lagets skott av typen: prior_weight_share matcher × lagsnitt per 90.
            team_rate = (sum(r.team_shots.get(t, 0.0) for r in rows) / len(rows)) if rows else 1.0
            k = cfg.prior_weight_share * max(team_rate, 0.3)
            p0 = prior["share"].get(t, 0.05)
            share[t] = (num + p0 * k) / (den + k)
        n_shots = sum(w * r.shots.get(t, 0.0) for w, r in zip(w_qual, rows))
        n_sot = sum(w * r.sot.get(t, 0.0) for w, r in zip(w_qual, rows))
        xg_sum = sum(w * r.xg.get(t, 0.0) for w, r in zip(w_qual, rows))
        k_ot = cfg.prior_weight_on_target
        on_target[t] = (n_sot + ON_TARGET_PRIOR[t] * k_ot) / (n_shots + k_ot)
        k_q = cfg.prior_weight_quality
        xg[t] = (xg_sum + XG_PRIOR[t] * k_q) / (n_shots + k_q)

    xa_num = sum(w * r.xa for w, r in zip(w_share, rows))
    xa_den = sum(w * r.team_xa * r.minutes / 90.0 for w, r in zip(w_share, rows))
    k_xa = cfg.prior_weight_share * 1.2
    xa_share = (xa_num + prior["xa"] * k_xa) / (xa_den + k_xa)

    if share_override:
        share.update(share_override)
    return PlayerProfile(player_id=player_id, name=name, team=team, position=position,
                         minutes=minutes, share=share, on_target=on_target,
                         xg_per_shot=xg, xa_share=xa_share, pen_order=pen_order)


# ------------------------------------------------------------------ lagprofiler
@dataclass
class TeamMatchRow:
    date: str
    shots_for: dict[str, float]
    shots_against: dict[str, float]
    xg_for: dict[str, float]
    def_action_height: float = 0.0   # meter från egen mållinje (snitt)
    ppda: float = 10.0
    pens_against: float = 0.0
    distorted: bool = False
    manager: str = ""


def _team_weights(rows: list[TeamMatchRow], half_life: float, cfg: FormConfig) -> list[float]:
    w = []
    n = len(rows)
    for i, r in enumerate(rows):
        age = n - 1 - i
        w.append((0.5 ** (age / half_life)) * (cfg.distorted_match_weight if r.distorted else 1.0))
    return w


def build_team_attack(rows: list[TeamMatchRow], league_mix: dict[str, float],
                      league_xg: dict[str, float], cfg: FormConfig | None = None
                      ) -> tuple[dict[str, float], dict[str, float]]:
    """Lagets normala skottmix och xG per skott per typ (krympt mot liga)."""
    cfg = cfg or FormConfig()
    rows = _since_manager(rows)
    w = _team_weights(rows, cfg.half_life_profile, cfg)
    k = cfg.prior_weight_profile
    tot = {t: sum(wi * r.shots_for.get(t, 0.0) for wi, r in zip(w, rows)) for t in SHOT_TYPES}
    sw = sum(w)
    mix = {}
    for t in SHOT_TYPES:
        if t == "penalty":
            continue
        per_match = tot[t] / sw if sw else 0.0
        mix[t] = (per_match * sw + league_mix.get(t, 0.0) * k) / (sw + k)
    s = sum(mix.values())
    mix = {t: v / s for t, v in mix.items()}
    xg = {}
    for t in SHOT_TYPES:
        xg_sum = sum(wi * r.xg_for.get(t, 0.0) for wi, r in zip(w, rows))
        kq = cfg.prior_weight_quality
        xg[t] = (xg_sum + league_xg.get(t, XG_PRIOR[t]) * kq) / (tot[t] + kq)
    return mix, xg


def build_defence_profile(rows: list[TeamMatchRow], league_against: dict[str, float],
                          league_height: float, league_height_sd: float,
                          league_ppda: float, league_ppda_sd: float,
                          league_pens: float = 0.13, cfg: FormConfig | None = None
                          ) -> OpponentProfile:
    """Hur laget försvarar sig relativt ligasnitt (används som motståndarprofil)."""
    cfg = cfg or FormConfig()
    rows = _since_manager(rows)
    w = _team_weights(rows, cfg.half_life_profile, cfg)
    sw = sum(w)
    k = cfg.prior_weight_profile
    allowed = {}
    for t in SHOT_TYPES:
        obs = sum(wi * r.shots_against.get(t, 0.0) for wi, r in zip(w, rows))
        exp = league_against.get(t, 0.0) * sw
        allowed[t] = (obs + league_against.get(t, 0.0) * k) / (exp + league_against.get(t, 0.0) * k) \
            if league_against.get(t, 0.0) > 0 else 1.0
    def wavg(f):
        return sum(wi * f(r) for wi, r in zip(w, rows)) / sw if sw else 0.0
    height = (wavg(lambda r: r.def_action_height) * sw + league_height * k) / (sw + k)
    ppda = (wavg(lambda r: r.ppda) * sw + league_ppda * k) / (sw + k)
    pens = (wavg(lambda r: r.pens_against) * sw + league_pens * k) / (sw + k)
    return OpponentProfile(
        allowed_mult=allowed,
        block_height=(height - league_height) / league_height_sd,
        ppda_z=(ppda - league_ppda) / league_ppda_sd,
        pens_conceded_mult=pens / league_pens if league_pens else 1.0,
    )


def _since_manager(rows: list):
    """Vid tränarbyte: använd bara matcher under nuvarande tränare om det finns ≥3,
    annars allt (krympningen tar hand om resten)."""
    if not rows or not rows[-1].manager:
        return rows
    cur = rows[-1].manager
    recent = [r for r in rows if r.manager == cur]
    return recent if len(recent) >= 3 else rows
