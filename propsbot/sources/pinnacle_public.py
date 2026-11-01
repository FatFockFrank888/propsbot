"""Pinnacles öppna gäst-API (samma JSON som pinnacle.com använder utan inloggning).

Ingen egen nyckel krävs; sajtens publika gästnyckel skickas i huvudet.
Priser anges i amerikanskt format och räknas om till decimalodds.
Spelarprops ligger som "special"-matchups kopplade till matchen.

OBS: inofficiellt flöde, kan vara geoblockerat i vissa länder och kan ändras.
Självdiagnosen visar om det fungerar från er uppkoppling.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime

from ..models import OddsQuote
from .http import JsonClient
from .props_text import market_from_label, name_key, person_name

BASE = "https://guest.api.arcadia.pinnacle.com/0.1"
GUEST_KEY = "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"
SOCCER = 29


def american_to_decimal(p: float) -> float:
    return 1 + p / 100.0 if p > 0 else 1 + 100.0 / abs(p)


@dataclass
class PinEvent:
    matchup_id: int
    home: str
    away: str
    start: float
    league: str


def _ts(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


class PinnaclePublic:
    def __init__(self, client: JsonClient):
        self.c = client
        self.c.headers.update({"X-API-Key": GUEST_KEY, "Referer": "https://www.pinnacle.com/",
                               "Origin": "https://www.pinnacle.com"})

    def leagues(self, words: list[str]) -> list[dict]:
        raw = self.c.get(f"{BASE}/sports/{SOCCER}/leagues", {"all": "false"}, ttl=3600) or []
        return [lg for lg in raw if not words or any(w.lower() in lg.get("name", "").lower()
                                                     for w in words)]

    def events(self, league: dict, hours_ahead: float) -> list[PinEvent]:
        raw = self.c.get(f"{BASE}/leagues/{league['id']}/matchups") or []
        now = time.time()
        out = []
        for m in raw:
            if m.get("type") != "matchup" or m.get("parent"):
                continue
            try:
                start = _ts(m["startTime"])
            except (KeyError, ValueError):
                continue
            if not (now < start < now + hours_ahead * 3600):
                continue
            parts = {p.get("alignment"): p.get("name") for p in m.get("participants", [])}
            if "home" in parts and "away" in parts:
                out.append(PinEvent(int(m["id"]), parts["home"], parts["away"], start,
                                    league.get("name", "")))
        return out

    def event_props(self, ev: PinEvent, match_id: str
                    ) -> tuple[list[OddsQuote], dict[str, str], dict]:
        related = self.c.get(f"{BASE}/matchups/{ev.matchup_id}/related") or []
        markets = self.c.get(f"{BASE}/matchups/{ev.matchup_id}/markets/related/straight") or []
        quotes, names = parse_specials(related, markets, match_id)
        return quotes, names, {"related": related, "markets": markets}


SEEN_SPECIALS: dict[str, str] = {}  # beskrivning -> vår tolkning (för diagnos)


def parse_specials(related: list, markets: list, match_id: str
                   ) -> tuple[list[OddsQuote], dict[str, str]]:
    """Specials: description t.ex. 'Bukayo Saka (Shots On Target)', deltagare Over/Under
    eller Yes/No; priserna kopplas via participantId."""
    now = time.time()
    specials: dict[int, tuple[str, str, float | None, dict[int, str]]] = {}
    for m in related:
        if m.get("type") != "special":
            continue
        sp = m.get("special", {})
        desc = sp.get("description") or ""
        units = m.get("units") or sp.get("units") or ""
        mk = market_from_label(f"{desc} {units}")
        if len(SEEN_SPECIALS) < 300:
            key = f"{desc} | units={units} | kategori={sp.get('category')} | deltagare=" + \
                ",".join(str(p.get("name")) for p in m.get("participants", []))
            is_team = "team" in (sp.get("category") or "").lower()
            SEEN_SPECIALS.setdefault(key, "används inte (lagmarknad)" if is_team else
                                     (f"{mk[0]} {mk[1]}" if mk else "används inte"))
        if not mk or "team" in (sp.get("category") or "").lower():
            continue
        player = desc.split("(")[0].strip()
        for sep in (" Total ", " To ", " - "):
            if sep in player:
                player = player.split(sep)[0].strip()
        if not player:
            continue
        pmap = {p["id"]: (p.get("name") or "").lower() for p in m.get("participants", [])
                if "id" in p}
        specials[int(m["id"])] = (player, mk[0], mk[1], pmap)

    quotes: list[OddsQuote] = []
    names: dict[str, str] = {}
    for mkt in markets:
        sid = mkt.get("matchupId")
        if sid not in specials or mkt.get("isAlternate"):
            continue
        player, market, fixed_line, pmap = specials[sid]
        for pr in mkt.get("prices", []):
            pname = pmap.get(pr.get("participantId"), pr.get("designation", "") or "")
            if pname in ("over", "yes"):
                side = "over"
            elif pname in ("under", "no"):
                side = "under"
            else:
                continue
            if pr.get("price") is None:
                continue
            line = pr.get("points")
            line = float(line) if line is not None else (fixed_line if fixed_line is not None else 0.5)
            pid = name_key(player)
            names.setdefault(pid, person_name(player))
            quotes.append(OddsQuote(book="pinnacle", match_id=match_id, player_id=pid,
                                    market=market, line=line, side=side,
                                    odds=round(american_to_decimal(float(pr["price"])), 3),
                                    ts=now, provider="pinnacle"))
    return quotes, names
