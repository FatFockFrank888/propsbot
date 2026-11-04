"""Odds sources: The Odds API and a manual CSV you fill from Unibet / ATG / Svenska Spel."""

from __future__ import annotations

import csv
import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from .config import Settings
from .http import JsonClient
from .model import line_probs
from .names import normalize_book, normalize_name
from .nhl_api import Game
from .pricing import fair_odds, parse_odds

if TYPE_CHECKING:
    from .slate import Projection

log = logging.getLogger(__name__)

ODDS_API = "https://api.the-odds-api.com/v4"
SPORT = "icehockey_nhl"
TTL_ODDS = 5 * 60

CSV_COLUMNS = ["book", "player", "team", "line", "over", "under"]
TEMPLATE_HINT_COLUMNS = ["model_mu", "fair_over", "fair_under"]


@dataclass(frozen=True)
class PropQuote:
    book: str  # normalised, e.g. 'unibet', 'svenskaspel', 'draftkings'
    player: str
    line: float
    over: float | None  # decimal odds
    under: float | None
    source: str  # 'odds_api' or 'csv'
    team: str = ""  # optional tri-code hint
    game_id: int | None = None  # set when the quote is tied to a specific game


@dataclass(frozen=True)
class OddsEvent:
    event_id: str
    home_team: str
    away_team: str
    commence: datetime | None


# ============================================================== The Odds API
class OddsApi:
    def __init__(self, client: JsonClient, settings: Settings) -> None:
        if not settings.odds_api_key:
            raise ValueError("ODDS_API_KEY is not set")
        self.client = client
        self.settings = settings
        self.requests_remaining: str | None = None

    def _track_quota(self, headers: dict[str, str]) -> None:
        remaining = headers.get("x-requests-remaining")
        if remaining is not None:
            self.requests_remaining = remaining

    def events(self) -> list[OddsEvent]:
        data, headers = self.client.get(
            f"{ODDS_API}/sports/{SPORT}/events",
            {"apiKey": self.settings.odds_api_key, "dateFormat": "iso"},
            ttl=TTL_ODDS,
        )
        self._track_quota(headers)
        events = []
        for ev in data or []:
            commence = None
            if ev.get("commence_time"):
                try:
                    commence = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
                except ValueError:
                    commence = None
            events.append(OddsEvent(str(ev["id"]), ev.get("home_team", ""), ev.get("away_team", ""), commence))
        return events

    def props(self, event_id: str, game_id: int | None = None) -> list[PropQuote]:
        books = list(dict.fromkeys(self.settings.odds_api_bet_books + self.settings.odds_api_reference_books))
        data, headers = self.client.get(
            f"{ODDS_API}/sports/{SPORT}/events/{event_id}/odds",
            {
                "apiKey": self.settings.odds_api_key,
                "bookmakers": ",".join(books),
                "markets": ",".join(self.settings.odds_api_markets),
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            },
            ttl=TTL_ODDS,
        )
        self._track_quota(headers)
        return parse_event_odds(data, game_id)


def parse_event_odds(data: dict, game_id: int | None = None) -> list[PropQuote]:
    grouped: dict[tuple[str, str, float], dict[str, float]] = {}
    for bm in (data or {}).get("bookmakers", []):
        book = normalize_book(str(bm.get("key", "")))
        for market in bm.get("markets", []):
            for outcome in market.get("outcomes", []):
                side = str(outcome.get("name", "")).lower()
                player = outcome.get("description")
                point = outcome.get("point")
                price = outcome.get("price")
                if side not in ("over", "under") or not player or point is None or price is None:
                    continue
                try:
                    dec = float(price)
                except (TypeError, ValueError):
                    continue
                if dec <= 1.0:
                    continue
                grouped.setdefault((book, str(player), float(point)), {})[side] = dec
    return [
        PropQuote(book=b, player=p, line=ln, over=s.get("over"), under=s.get("under"), source="odds_api", game_id=game_id)
        for (b, p, ln), s in grouped.items()
    ]


def match_events(games: Iterable[Game], events: Iterable[OddsEvent], abbrev_by_name: dict[str, str]) -> dict[int, str]:
    """NHL game id -> Odds API event id, matched on teams and start time."""
    nickname_map: dict[str, str] = {}
    for full, tri in abbrev_by_name.items():
        nickname_map.setdefault(full.split()[-1], tri)

    def resolve(name: str) -> str | None:
        norm = normalize_name(name)
        if norm in abbrev_by_name:
            return abbrev_by_name[norm]
        return nickname_map.get(norm.split()[-1]) if norm else None

    events = list(events)
    result: dict[int, str] = {}
    for game in games:
        for ev in events:
            if resolve(ev.home_team) != game.home or resolve(ev.away_team) != game.away:
                continue
            if game.start_utc and ev.commence and abs(ev.commence - game.start_utc) > timedelta(hours=12):
                continue
            result[game.game_id] = ev.event_id
            break
    return result


# ================================================================ Manual CSV
def odds_csv_path(settings: Settings, day: date) -> Path:
    return settings.odds_dir / f"{day.isoformat()}.csv"


def load_odds_csv(path: Path) -> list[PropQuote]:
    """Read manually entered odds. Rows with no book or no price are skipped."""
    if not path.is_file():
        return []
    quotes: list[PropQuote] = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(fh, dialect=dialect)
        missing = {"book", "player", "line"} - {c.strip().lower() for c in reader.fieldnames or []}
        if missing:
            raise ValueError(f"{path}: missing required column(s): {', '.join(sorted(missing))}")
        for lineno, raw in enumerate(reader, start=2):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
            if not row.get("book") or not row.get("player"):
                continue
            if not row.get("over") and not row.get("under"):
                continue
            try:
                line = float(row["line"].replace(",", "."))
                over = parse_odds(row["over"]) if row.get("over") else None
                under = parse_odds(row["under"]) if row.get("under") else None
            except (ValueError, KeyError) as exc:
                raise ValueError(f"{path}:{lineno}: {exc}") from None
            quotes.append(
                PropQuote(
                    book=normalize_book(row["book"]),
                    player=row["player"],
                    line=line,
                    over=over,
                    under=under,
                    source="csv",
                    team=row.get("team", "").upper(),
                )
            )
    return quotes


def suggested_line(mu: float) -> float:
    return max(1.5, math.floor(mu) + 0.5) if mu >= 1.0 else 0.5


def write_odds_template(path: Path, projections: Iterable["Projection"], alpha: float) -> bool:
    """Write a fill-in sheet for the day. Never overwrites an existing file. Returns True if written."""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted((p for p in projections if p.active), key=lambda p: -p.mu)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS + TEMPLATE_HINT_COLUMNS)
        for p in rows:
            line = suggested_line(p.mu)
            probs = line_probs(line, p.mu, alpha)
            fo, fu = fair_odds(probs.over), fair_odds(probs.under)
            writer.writerow(
                ["", p.skater.name, p.skater.team, f"{line:.1f}", "", "", f"{p.mu:.2f}",
                 f"{fo:.2f}" if fo else "", f"{fu:.2f}" if fu else ""]
            )
    return True
