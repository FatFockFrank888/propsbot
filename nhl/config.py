"""Runtime configuration loaded from environment variables and an optional .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path) -> None:
    """Minimal .env loader: KEY=VALUE lines and '#' comments. Existing env vars win."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].strip()
        if key:
            os.environ.setdefault(key, value)


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be a number, got {raw!r}") from exc


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer, got {raw!r}") from exc


def _list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _path(name: str, default: Path) -> Path:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    p = Path(raw)
    return p if p.is_absolute() else PROJECT_ROOT / p


def season_for(d: date) -> str:
    """NHL season id (e.g. '20262027') that contains the given date."""
    start = d.year if d.month >= 7 else d.year - 1
    return f"{start}{start + 1}"


def previous_season(season: str) -> str:
    start = int(season[:4]) - 1
    return f"{start}{start + 1}"


@dataclass(frozen=True)
class Settings:
    # --- Odds sources -------------------------------------------------------
    odds_api_key: str = ""
    # Books you actually bet at. Picks are only produced for these.
    bet_books: tuple[str, ...] = ("unibet", "atg", "svenskaspel")
    # Odds API bookmaker keys for the books above.
    odds_api_bet_books: tuple[str, ...] = ("unibet_se", "atg_se", "svenskaspel_se")
    # Odds API bookmaker keys used only as a market reference (de-vigged consensus).
    odds_api_reference_books: tuple[str, ...] = ("draftkings", "fanduel", "betmgm", "williamhill_us")
    odds_api_markets: tuple[str, ...] = ("player_shots_on_goal",)
    odds_dir: Path = PROJECT_ROOT / "odds"

    # --- Storage ------------------------------------------------------------
    cache_dir: Path = PROJECT_ROOT / ".cache"
    output_dir: Path = PROJECT_ROOT / "output"
    http_workers: int = 8

    # --- Model --------------------------------------------------------------
    lookback_games: int = 25
    rate_half_life: float = 10.0
    toi_lookback_games: int = 10
    toi_half_life: float = 4.0
    prior_minutes: float = 40.0
    forward_prior_rate: float = 0.120  # shots on goal per minute of TOI
    defense_prior_rate: float = 0.068
    forward_default_toi: float = 13.0
    defense_default_toi: float = 18.0
    dispersion: float = 0.05  # negative binomial alpha: Var = mu + alpha * mu^2
    home_edge: float = 0.02
    opp_shrink_games: float = 10.0
    opp_factor_floor: float = 0.85
    opp_factor_cap: float = 1.15

    # --- Betting ------------------------------------------------------------
    min_edge: float = 0.03
    min_ev: float = 0.03
    min_games: int = 8
    min_odds: float = 1.40  # decimal
    max_odds: float = 5.00  # decimal
    bankroll: float = 1000.0
    currency: str = "SEK"
    kelly_fraction: float = 0.25
    max_stake_pct: float = 0.02

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "Settings":
        load_dotenv(env_file or PROJECT_ROOT / ".env")
        d = cls()
        return cls(
            odds_api_key=os.environ.get("ODDS_API_KEY", "").strip(),
            bet_books=tuple(b.lower() for b in _list("BET_BOOKS", d.bet_books)),
            odds_api_bet_books=_list("ODDS_API_BET_BOOKS", d.odds_api_bet_books),
            odds_api_reference_books=_list("ODDS_API_REFERENCE_BOOKS", d.odds_api_reference_books),
            odds_api_markets=_list("ODDS_API_MARKETS", d.odds_api_markets),
            odds_dir=_path("ODDS_DIR", d.odds_dir),
            cache_dir=_path("CACHE_DIR", d.cache_dir),
            output_dir=_path("OUTPUT_DIR", d.output_dir),
            http_workers=max(1, _int("HTTP_WORKERS", d.http_workers)),
            lookback_games=_int("LOOKBACK_GAMES", d.lookback_games),
            rate_half_life=_float("RATE_HALF_LIFE", d.rate_half_life),
            toi_lookback_games=_int("TOI_LOOKBACK_GAMES", d.toi_lookback_games),
            toi_half_life=_float("TOI_HALF_LIFE", d.toi_half_life),
            prior_minutes=_float("PRIOR_MINUTES", d.prior_minutes),
            forward_prior_rate=_float("FORWARD_PRIOR_RATE", d.forward_prior_rate),
            defense_prior_rate=_float("DEFENSE_PRIOR_RATE", d.defense_prior_rate),
            forward_default_toi=_float("FORWARD_DEFAULT_TOI", d.forward_default_toi),
            defense_default_toi=_float("DEFENSE_DEFAULT_TOI", d.defense_default_toi),
            dispersion=max(0.0, _float("DISPERSION", d.dispersion)),
            home_edge=_float("HOME_EDGE", d.home_edge),
            opp_shrink_games=_float("OPP_SHRINK_GAMES", d.opp_shrink_games),
            opp_factor_floor=_float("OPP_FACTOR_FLOOR", d.opp_factor_floor),
            opp_factor_cap=_float("OPP_FACTOR_CAP", d.opp_factor_cap),
            min_edge=_float("MIN_EDGE", d.min_edge),
            min_ev=_float("MIN_EV", d.min_ev),
            min_games=_int("MIN_GAMES", d.min_games),
            min_odds=_float("MIN_ODDS", d.min_odds),
            max_odds=_float("MAX_ODDS", d.max_odds),
            bankroll=_float("BANKROLL", d.bankroll),
            currency=os.environ.get("CURRENCY", d.currency).strip() or d.currency,
            kelly_fraction=_float("KELLY_FRACTION", d.kelly_fraction),
            max_stake_pct=_float("MAX_STAKE_PCT", d.max_stake_pct),
        )
