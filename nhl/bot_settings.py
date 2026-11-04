"""Edge-bot rules, loaded from settings.json (mirrors the NBA bot's parameters)."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from .config import PROJECT_ROOT

log = logging.getLogger(__name__)

SETTINGS_PATH = PROJECT_ROOT / "settings.json"


@dataclass
class BotSettings:
    # ---- LIVE bets (the only ones that send notifications) ------------------
    live_on: bool = True
    live_min_edge: float = 0.06
    live_model_min_edge: float = 0.03
    live_min_groups: int = 2
    live_odds_min: float = 1.60
    live_odds_max: float = 3.00
    live_max_units: int = 5
    live_max_per_match: int = 2
    live_max_per_day: int = 8
    live_max_units_day: int = 25
    live_require_active: bool = True

    # ---- Shared rules (all ledgers) ----------------------------------------
    min_edge_all: float = 0.05
    odds_min_all: float = 1.60
    odds_max_all: float = 6.00
    shadow_min_edge: float = 0.02
    max_odds_drop: float = 0.03
    sharp_against_pp: float = 2.0
    sharp_with_pp: float = 1.5
    sharp_min_age_min: float = 30.0
    max_plausible_edge: float = 0.25
    max_dev_from_consensus: float = 0.18
    max_odds_age_s: float = 180.0
    extra_edge_without_sharp: float = 0.03
    min_groups_without_sharp: int = 3
    pre_match_cutoff_min: float = 2.0

    # ---- Stakes -------------------------------------------------------------
    bankroll: float = 10000.0
    currency: str = "SEK"
    unit_pct: float = 0.002
    kelly_fraction: float = 0.25
    max_units_per_bet: int = 10
    max_stake_per_match_pct: float = 0.05

    # ---- Books & sources ------------------------------------------------------
    playable_books: list[str] = field(default_factory=lambda: ["svenskaspel", "betmgm", "expekt", "atg", "unibet"])
    kambi_offerings: dict[str, str] = field(default_factory=lambda: {
        "ubse": "unibet", "paf": "paf", "atg": "atg", "leose": "leovegas",
        "svenskaspel": "svenskaspel", "expektse": "expekt", "betmgmse": "betmgm",
    })
    kambi_market: str = "SE"
    use_pinnacle: bool = False
    pinnacle_api_key: str = ""
    pinnacle_league_id: int = 1456
    use_bovada: bool = True
    bovada_ttl_s: float = 120.0
    sharp_weight: float = 2.0
    one_sided_margin: float = 0.08
    max_interp_distance: float = 1.0
    us_books: list[str] = field(default_factory=lambda: [
        "draftkings", "fanduel", "betmgm", "williamhill_us", "fanatics", "espnbet", "hardrockbet", "betonlineag",
    ])
    us_fetch_window_min: list[float] = field(default_factory=lambda: [40.0, 240.0])
    odds_api_monthly_credits: int = 500
    odds_api_share: float = 0.25
    odds_api_reserve: int = 20

    # ---- Model ----------------------------------------------------------------
    model_weight: float = 0.3
    model_min_games: int = 8
    test_markets: bool = True  # points/assists/goals at Kambi vs our own model, data only

    # ---- Scanning ---------------------------------------------------------------
    hours_ahead: float = 30.0
    max_events: int = 15
    scan_interval_min: float = 8.0
    quiet_hours_utc: list[int] = field(default_factory=lambda: [4, 6])
    quiet_interval_min: float = 55.0

    # ---- Notifications & storage ------------------------------------------------
    ntfy_topic: str = ""
    daily_recap: bool = True
    recap_hour_local: int = 10
    health_alert_after_failures: int = 3
    data_dir: str = "data"

    @property
    def data_path(self) -> Path:
        p = Path(os.environ.get("NHL_DATA_DIR") or self.data_dir)
        return p if p.is_absolute() else PROJECT_ROOT / p

    def unit_value(self) -> float:
        return self.bankroll * self.unit_pct

    @classmethod
    def load(cls, path: Path = SETTINGS_PATH, *, create: bool = True) -> "BotSettings":
        if not path.is_file():
            s = cls()
            if create:
                s.save(path)
                log.info("Wrote default settings to %s", path)
            return s
        try:
            raw = json.loads(path.read_text(encoding="utf-8-sig"))  # tolerate Notepad's BOM
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path} is not valid JSON: {exc}") from None
        # The merged bot keeps every sport in one settings.json; NHL reads its own "nhl" section.
        if isinstance(raw.get("nhl"), dict):
            raw = raw["nhl"]
        known = {f.name: f for f in fields(cls)}
        unknown = sorted(set(raw) - set(known))
        if unknown:
            log.warning("Ignoring unknown settings keys: %s", ", ".join(unknown))
        defaults = cls()
        kwargs = {}
        for name in known:
            if name not in raw:
                continue
            default = getattr(defaults, name)
            value = raw[name]
            if isinstance(default, bool):
                if not isinstance(value, bool):
                    raise ValueError(f"settings.json: {name} must be true/false")
            elif isinstance(default, (int, float)) and not isinstance(default, bool):
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise ValueError(f"settings.json: {name} must be a number")
                value = type(default)(value) if isinstance(default, float) else int(value)
            elif isinstance(default, list) and not isinstance(value, list):
                raise ValueError(f"settings.json: {name} must be a list")
            elif isinstance(default, dict) and not isinstance(value, dict):
                raise ValueError(f"settings.json: {name} must be an object")
            kwargs[name] = value
        # Secrets come from the environment (.env locally, GitHub Secrets in Actions) and win over the file.
        for name, env in (("ntfy_topic", "NTFY_TOPIC"), ("pinnacle_api_key", "PINNACLE_API_KEY")):
            value = os.environ.get(env, "").strip()
            if value:
                kwargs[name] = value
        s = cls(**kwargs)
        s.validate()
        return s

    def validate(self) -> None:
        if not (1.0 < self.odds_min_all <= self.odds_max_all):
            raise ValueError("settings.json: odds_min_all/odds_max_all invalid")
        if not (1.0 < self.live_odds_min <= self.live_odds_max):
            raise ValueError("settings.json: live_odds_min/live_odds_max invalid")
        if not (0.0 <= self.model_weight <= 1.0):
            raise ValueError("settings.json: model_weight must be within 0..1")
        if len(self.us_fetch_window_min) != 2 or self.us_fetch_window_min[0] > self.us_fetch_window_min[1]:
            raise ValueError("settings.json: us_fetch_window_min must be [min, max]")
        if self.unit_pct <= 0 or self.bankroll <= 0:
            raise ValueError("settings.json: bankroll and unit_pct must be positive")

    def save(self, path: Path = SETTINGS_PATH) -> None:
        data = asdict(self)
        if path.is_file():  # shared settings.json: only touch the "nhl" section
            try:
                whole = json.loads(path.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError:
                whole = None
            if isinstance(whole, dict) and "nhl" in whole:
                whole["nhl"] = data
                data = whole
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
