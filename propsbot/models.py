"""Datatyper som flödar genom kedjan."""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import SHOT_TYPES


def _zeros() -> dict[str, float]:
    return {t: 0.0 for t in SHOT_TYPES}


@dataclass
class MinutesModel:
    """Speltid. Alla sannolikheter gäller *innan* villkoret 'spelar'."""
    p_start: float                  # 1.0/0.0 när startelvan är bekräftad
    p_full_if_start: float = 0.55   # spelar hela matchen givet start
    sub_off_mean: float = 70.0      # snittminut för byte ut (givet byte)
    sub_off_sd: float = 12.0
    p_sub_on_if_bench: float = 0.35
    sub_on_mean: float = 68.0
    sub_on_sd: float = 12.0
    p_red_card: float = 0.01        # per match, ger tidigt utgång


@dataclass
class PlayerProfile:
    player_id: str
    name: str
    team: str
    position: str                   # GK, CB, FB, WB, DM, CM, AM, W, ST
    minutes: MinutesModel
    # Vikt för spelarens andel av lagets skott per typ när spelaren är på plan.
    share: dict[str, float] = field(default_factory=_zeros)
    on_target: dict[str, float] = field(default_factory=_zeros)
    xg_per_shot: dict[str, float] = field(default_factory=_zeros)
    xa_share: float = 0.0           # vikt för att bli assistgivare
    pen_order: int | None = None    # 1 = förste straffläggare


@dataclass
class OpponentProfile:
    """Hur motståndaren försvarar sig, relativt ligasnitt (1.0 = snitt)."""
    allowed_mult: dict[str, float] = field(
        default_factory=lambda: {t: 1.0 for t in SHOT_TYPES})
    block_height: float = 0.0       # standardiserad, negativ = lågt block
    ppda_z: float = 0.0             # standardiserad, positiv = passivt
    pens_conceded_mult: float = 1.0
    keeper_save_skill: float = 0.0  # >0 = räddar mer än väntat (påverkar bara mål)


@dataclass
class TeamContext:
    name: str
    players: list[PlayerProfile]
    exp_goals: float                # från Pinnacle (marginalfri)
    base_mix: dict[str, float]      # lagets normala skottfördelning per typ
    xg_per_shot_type: dict[str, float]  # lagets snitt-xG per skott och typ
    opponent: OpponentProfile = field(default_factory=OpponentProfile)
    pens_per_match: float = 0.13
    is_home: bool = False


@dataclass
class Referee:
    name: str = "okänd"
    added_time: float | None = None  # snitt total tilläggstid
    pen_mult: float = 1.0
    freekick_mult: float = 1.0


@dataclass
class Weather:
    wind_ms: float = 0.0
    heavy_rain: bool = False
    artificial_turf: bool = False


@dataclass
class MatchContext:
    match_id: str
    home: TeamContext
    away: TeamContext
    kickoff_utc: str
    lineup_confirmed: bool = False
    referee: Referee = field(default_factory=Referee)
    weather: Weather = field(default_factory=Weather)
    competition: str = ""


@dataclass
class OddsQuote:
    book: str
    match_id: str
    player_id: str
    market: str            # shots, shots_on_target, goal, assist
    line: float            # 0.5, 1.5 ...
    side: str              # "over" / "under"
    odds: float
    ts: float              # unix-tid då priset hämtades
    provider: str | None = None  # t.ex. "kambi"; fylls i av grupperingen


@dataclass
class PlayerMarketProb:
    match_id: str
    player_id: str
    market: str
    line: float
    p_model: float
    p_market: float | None = None
    p_final: float | None = None
    n_played_sims: int = 0
