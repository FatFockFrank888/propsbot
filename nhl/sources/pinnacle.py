"""Pinnacle player shots-on-goal specials (sharp reference). Disabled by default.

Enable with "use_pinnacle": true and your own "pinnacle_api_key" in settings.json.
Prices are American and converted to decimal. Player props are "special" matchups
linked to the game, with Over/Under participants priced in the related markets.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..http import JsonClient
from ..market import Quote
from ..pricing import american_to_decimal

log = logging.getLogger(__name__)

BASE = "https://guest.api.arcadia.pinnacle.com/0.1"


@dataclass(frozen=True)
class PinnacleGame:
    matchup_id: int
    home: str
    away: str
    start: datetime


class PinnacleClient:
    def __init__(self, client: JsonClient, api_key: str, league_id: int, diagnose_dir: Path | None = None) -> None:
        if not api_key:
            raise ValueError("pinnacle_api_key is empty in settings.json")
        self.client = client
        self.league_id = league_id
        self.diagnose_dir = diagnose_dir
        self.headers = {"X-API-Key": api_key, "Referer": "https://www.pinnacle.com/", "Origin": "https://www.pinnacle.com"}

    def games(self) -> list[PinnacleGame]:
        raw, _ = self.client.get(f"{BASE}/leagues/{self.league_id}/matchups", headers=self.headers)
        games = []
        for m in raw or []:
            if m.get("type") != "matchup" or m.get("parent"):
                continue
            parts = {p.get("alignment"): p.get("name") for p in m.get("participants", [])}
            try:
                start = datetime.fromisoformat(m["startTime"].replace("Z", "+00:00")).astimezone(timezone.utc)
            except (KeyError, ValueError):
                continue
            if parts.get("home") and parts.get("away"):
                games.append(PinnacleGame(int(m["id"]), parts["home"], parts["away"], start))
        return games

    def sog_quotes(self, matchup_id: int) -> list[Quote]:
        related, _ = self.client.get(f"{BASE}/matchups/{matchup_id}/related", headers=self.headers, ttl=60)
        markets, _ = self.client.get(f"{BASE}/matchups/{matchup_id}/markets/related/straight", headers=self.headers, ttl=60)
        quotes = parse_specials(related or [], markets or [])
        player_specials = [
            m for m in related or []
            if m.get("type") == "special" and "player" in ((m.get("special") or {}).get("category") or "").lower()
        ]
        if player_specials and not quotes and self.diagnose_dir:
            self.diagnose_dir.mkdir(parents=True, exist_ok=True)
            path = self.diagnose_dir / f"pinnacle_{matchup_id}.json"
            path.write_text(json.dumps({"related": related, "markets": markets}, indent=1), encoding="utf-8")
            log.warning("Pinnacle has %d player specials but no SOG parsed; raw saved to %s", len(player_specials), path)
        return quotes


_SUFFIX = re.compile(r"\s*[-:]?\s*(total\s+)?shots?\s+on\s+goal.*$", re.I)


def player_from_description(desc: str) -> str:
    """'Claude Giroux Total Shots On Goal' / 'Claude Giroux (Shots On Goal)' -> 'Claude Giroux'."""
    return _SUFFIX.sub("", desc.split("(")[0]).strip()


def parse_specials(related: list, markets: list, now: float | None = None) -> list[Quote]:
    now = now if now is not None else time.time()
    specials: dict[int, tuple[str, dict[int, str]]] = {}
    for m in related:
        if m.get("type") != "special":
            continue
        sp = m.get("special", {}) or {}
        text = f"{sp.get('description', '')} {m.get('units', '')} {sp.get('units', '')}".lower()
        if "shot" not in text or "team" in (sp.get("category") or "").lower():
            continue
        player = player_from_description(sp.get("description") or "")
        if not player:
            continue
        pmap = {int(p["id"]): (p.get("name") or "").lower() for p in m.get("participants", []) if "id" in p}
        specials[int(m["id"])] = (player, pmap)

    pairs: dict[tuple[str, float], dict[str, float]] = {}
    for mkt in markets:
        sid = mkt.get("matchupId")
        if sid not in specials or mkt.get("isAlternate"):
            continue
        player, pmap = specials[sid]
        for pr in mkt.get("prices", []):
            name = pmap.get(pr.get("participantId"), (pr.get("designation") or "").lower())
            side = "over" if name in ("over", "yes") else "under" if name in ("under", "no") else None
            if side is None or pr.get("price") is None or pr.get("points") is None:
                continue
            try:
                dec = american_to_decimal(float(pr["price"]))
            except ValueError:
                continue
            pairs.setdefault((player, float(pr["points"])), {})[side] = round(dec, 4)
    return [
        Quote(source="pinnacle", group="pinnacle", player=p, line=ln, over=s.get("over"), under=s.get("under"), ts=now)
        for (p, ln), s in pairs.items()
    ]
