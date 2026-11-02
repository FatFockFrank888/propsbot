"""Alla justerbara parametrar på ett ställe.

Värdena är startvärden. Trimma dem med walk-forward-backtest (log loss + CLV),
inte på känsla.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Skottyper som hela modellen räknar med.
SHOT_TYPES: tuple[str, ...] = (
    "box",        # inne i straffområdet, öppet spel
    "distance",   # utanför straffområdet
    "header",     # nickar (öppet spel + fasta)
    "setpiece",   # fot-avslut efter hörna/frispark (ej direkt frispark)
    "counter",    # kontring/djupled
    "freekick",   # direkt frispark
    "penalty",    # straff
)
OPEN_TYPES = ("box", "distance", "header", "setpiece", "counter", "freekick")

# Andel mål av typen som har en assist (Opta-liknande definition).
ASSIST_RATE = {
    "box": 0.80, "distance": 0.55, "header": 0.92, "setpiece": 0.65,
    "counter": 0.85, "freekick": 0.0, "penalty": 0.0,
}


@dataclass
class FormConfig:
    # Halveringstid i spelade 90-minutersekvivalenter.
    half_life_share: float = 7.0          # andel av lagets skott / xG / xA
    half_life_quality: float = 15.0       # xG per skott, skottypsmix
    half_life_profile: float = 12.0       # lagprofil (block, insläppt per typ)
    # Krympning (prior-vikt):
    prior_weight_share: float = 6.0       # i 90-minutersekvivalenter
    prior_weight_quality: float = 20.0    # i antal skott (xG per skott)
    prior_weight_on_target: float = 40.0  # i antal skott, träffprocent krymps hårt
    prior_weight_profile: float = 8.0     # i matcher (lagprofiler)
    # Rollbyte: halveringstiden multipliceras tillfälligt med denna faktor.
    role_change_half_life_mult: float = 0.4
    # Matcher som förvrängts (rött kort, tidig skada, storseger) viktas ned.
    distorted_match_weight: float = 0.35


@dataclass
class SimConfig:
    n_sims: int = 10_000
    seed: int | None = 7
    regulation_minutes: int = 90
    default_added_time: float = 8.0      # total tilläggstid (båda halvlekar)
    # Överspridning: gamma-multiplikator per match (lag) och per spelare.
    team_volume_shape: float = 12.0
    player_share_shape: float = 6.0
    # Ställningseffekter (multiplikator på eget tempo).
    leading_volume_mult: float = 0.85
    trailing_volume_mult: float = 1.15
    # Ledning/underläge flyttar mix: underläge -> fler distansskott/inlägg.
    trailing_distance_mult: float = 1.25
    trailing_header_mult: float = 1.20
    leading_counter_mult: float = 1.40
    # Antal kalibreringspass så att simulerade mål matchar Pinnacle.
    calibration_passes: int = 2


@dataclass
class MatchupConfig:
    max_effect: float = 0.18     # tak ±18 % på matchupjustering per skottyp
    # Hur mycket favoritskap (lagets andel av väntade mål) flyttar mixen.
    favourite_distance_slope: float = 0.6
    favourite_counter_slope: float = -0.8


@dataclass
class MarketConfig:
    # Unibet/Kambi ensidiga marginaler: m(odds) = base + slope*(odds-2), per marknad.
    one_sided_margin: dict = field(default_factory=lambda: {
        "shots": (0.07, 0.015),
        "shots_on_target": (0.08, 0.015),
        "goal": (0.10, 0.012),
        "assist": (0.12, 0.012),
    })
    max_one_sided_margin: float = 0.30
    # Vikt för Kambi-gruppen relativt Pinnacle i marknadssannolikheten.
    pinnacle_weight: float = 0.7
    kambi_weight: float = 0.3
    # Två bolag räknas som samma leverantör om odds-korrelationen är över:
    same_provider_corr: float = 0.985
    same_provider_max_mad: float = 0.02  # medel-abs-avvikelse i implied prob


@dataclass
class BlendConfig:
    w_model_pre_lineup: float = 0.30
    w_model_post_lineup: float = 0.50
    pinnacle_present_penalty: float = 0.10
    # Om |logit(model) - logit(market)| > disagree_start sänks w linjärt
    disagree_start: float = 0.35
    disagree_full: float = 1.20
    w_model_min: float = 0.10
    # Per marknad kan modellvikten skalas (mål/assist mindre beprövade).
    market_weight_mult: dict = field(default_factory=lambda: {
        "shots": 1.0, "shots_on_target": 1.0, "goal": 0.7, "assist": 0.6,
    })


@dataclass
class CalibrationConfig:
    shrink_k: float = 200.0       # nivåkalibrering, prior motsvarande k linjer
    max_abs_offset: float = 0.5   # tak i logit


@dataclass
class DecisionConfig:
    min_edge: float = 0.02
    min_edge_by_market: dict = field(default_factory=lambda: {
        "shots": 0.02, "shots_on_target": 0.02, "goal": 0.04, "assist": 0.04,
    })
    min_odds_play: float = 1.60
    min_odds_show: float = 1.60
    max_odds_play: float = 6.0       # spel över detta odds föreslås inte
    kelly_fraction: float = 0.25
    max_stake_per_bet: float = 0.02      # andel av bankrulle
    max_stake_per_match: float = 0.05
    max_legs_per_player_family: int = 1  # skott + skott på mål = samma familj
    max_odds_age_s: float = 180.0
    max_dev_from_consensus: float = 0.18  # spärra om bästa odds avviker mer
    lineup_required_minutes: float = 20.0  # okänd startelva < 20 min före avspark -> stopp


@dataclass
class Config:
    form: FormConfig = field(default_factory=FormConfig)
    sim: SimConfig = field(default_factory=SimConfig)
    matchup: MatchupConfig = field(default_factory=MatchupConfig)
    market: MarketConfig = field(default_factory=MarketConfig)
    blend: BlendConfig = field(default_factory=BlendConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    decision: DecisionConfig = field(default_factory=DecisionConfig)


MARKET_FAMILY = {
    "shots": "shots", "shots_on_target": "shots",
    "goal": "goal", "assist": "assist",
}
