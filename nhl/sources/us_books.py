"""US sportsbook shots-on-goal odds via The Odds API: reference only, never playable.

Each game is fetched at most once, inside a window before puck drop, and only when
the daily credit budget allows. Results are cached on disk per game.
"""

from __future__ import annotations

import calendar
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from ..http import JsonClient
from ..market import US_GROUPS, Quote
from ..odds import ODDS_API, SPORT, OddsEvent, parse_event_odds

log = logging.getLogger(__name__)

MARKET = "player_shots_on_goal"


class Budget:
    """Daily Odds API budget: (credits left - reserve) / days left in month x this bot's share.

    The key may be shared with other bots (NBA, football), so the remaining count comes
    from the API's own response headers, and this bot only tracks what it spent today.
    """

    def __init__(self, path: Path, monthly: int, share: float, reserve: int) -> None:
        self.path = path
        self.monthly = monthly
        self.share = share
        self.reserve = reserve
        self.state = self._load()

    def _load(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, indent=1), encoding="utf-8")

    def _today(self, now: datetime) -> str:
        return now.strftime("%Y-%m-%d")

    def observe(self, headers: dict[str, str]) -> None:
        remaining = headers.get("x-requests-remaining")
        if remaining is not None:
            try:
                self.state["remaining"] = int(float(remaining))
            except ValueError:
                pass
            self._save()

    def daily_budget(self, now: datetime) -> int:
        remaining = self.state.get("remaining", self.monthly)
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        days_left = days_in_month - now.day + 1
        return max(0, int((remaining - self.reserve) / days_left * self.share))

    def spent_today(self, now: datetime) -> int:
        return int(self.state.get("spent", {}).get(self._today(now), 0))

    def can_spend(self, cost: int, now: datetime) -> bool:
        return self.spent_today(now) + cost <= self.daily_budget(now)

    def spend(self, cost: int, now: datetime) -> None:
        spent = self.state.setdefault("spent", {})
        today = self._today(now)
        spent[today] = spent.get(today, 0) + cost
        for day in sorted(spent)[:-14]:
            spent.pop(day, None)
        self._save()


class UsBooks:
    def __init__(self, client: JsonClient, api_key: str, books: list[str], cache_dir: Path, budget: Budget) -> None:
        self.client = client
        self.api_key = api_key
        self.books = books
        self.cache_dir = cache_dir
        self.budget = budget

    def events(self) -> list[OddsEvent]:
        data, headers = self.client.get(
            f"{ODDS_API}/sports/{SPORT}/events", {"apiKey": self.api_key, "dateFormat": "iso"}, ttl=600
        )
        self.budget.observe(headers)
        out = []
        for ev in data or []:
            try:
                commence = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                commence = None
            out.append(OddsEvent(str(ev["id"]), ev.get("home_team", ""), ev.get("away_team", ""), commence))
        return out

    def _cache_path(self, game_id: int) -> Path:
        return self.cache_dir / f"{game_id}.json"

    def cached(self, game_id: int) -> list[Quote] | None:
        path = self._cache_path(game_id)
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        return [Quote(**q) for q in payload.get("quotes", [])]

    def fetch(self, game_id: int, event_id: str, now: datetime) -> list[Quote] | None:
        """Fetch once (1 credit: one market, <= 10 books = one region). None if over budget."""
        cost = 1
        if not self.budget.can_spend(cost, now):
            log.info("Odds API daily budget reached (%d/%d)", self.budget.spent_today(now), self.budget.daily_budget(now))
            return None
        data, headers = self.client.get(
            f"{ODDS_API}/sports/{SPORT}/events/{event_id}/odds",
            {
                "apiKey": self.api_key,
                "bookmakers": ",".join(self.books[:10]),
                "markets": MARKET,
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            },
        )
        self.budget.observe(headers)
        self.budget.spend(cost, now)
        ts = time.time()
        quotes = [
            Quote(
                source=f"us:{pq.book}",
                group=US_GROUPS.get(pq.book, pq.book),
                player=pq.player,
                line=pq.line,
                over=pq.over,
                under=pq.under,
                ts=ts,
            )
            for pq in parse_event_odds(data, game_id)
        ]
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path(game_id).write_text(
            json.dumps({"event_id": event_id, "fetched": ts, "quotes": [q.__dict__ for q in quotes]}, ensure_ascii=False),
            encoding="utf-8",
        )
        return quotes
