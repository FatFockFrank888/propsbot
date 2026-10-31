"""Kambis öppna oddsflöde (samma JSON som Unibet, Paf, ATG m.fl. visar på sina sajter).

Ingen nyckel, inga krediter. Varje Kambi-bolag har en egen "offering"-kod.
Odds anges i tusendelar (1850 = 1,85) och linjer likaså (1500 = 1,5).

OBS: inofficiellt flöde. Formatet kan ändras utan förvarning; parsningen är
därför defensiv och självdiagnosen sparar råsvar i mappen diagnos/.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime

from ..models import OddsQuote
from .http import JsonClient, SourceError
from .props_text import market_from_label, name_key, person_name

BASES = ("https://eu-offering-api.kambicdn.com/offering/v2018",
         "https://eu-offering.kambicdn.org/offering/v2018")


@dataclass
class KambiEvent:
    event_id: int
    home: str
    away: str
    start: float
    league: str


def _ts(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


class KambiPublic:
    def __init__(self, client: JsonClient, market: str = "SE", lang: str = "en_GB"):
        self.c = client
        self.market = market
        self.lang = lang
        self.base_for: dict[str, str] = {}

    def _get(self, offering: str, path: str, params: dict | None = None):
        p = {"lang": self.lang, "market": self.market, **(params or {})}
        bases = [self.base_for[offering]] if offering in self.base_for else list(BASES)
        last_err = None
        for b in bases:
            try:
                data = self.c.get(f"{b}/{offering}/{path}", p)
            except SourceError as e:
                last_err = e
                continue
            if data is not None:
                self.base_for[offering] = b
                return data
        if last_err:
            raise last_err
        return None

    def football_events(self, offering: str, hours_ahead: float, league_words: list[str]
                        ) -> tuple[list[KambiEvent], dict | None]:
        raw = self._get(offering, "listView/football/all/all/all/matches.json",
                        {"useCombined": "true"})
        if not raw:
            return [], raw
        now = time.time()
        out = []
        for item in raw.get("events", []):
            ev = item.get("event", item)
            try:
                start = _ts(ev["start"])
            except (KeyError, ValueError):
                continue
            if not (now - 600 < start < now + hours_ahead * 3600):
                continue
            if ev.get("state") not in (None, "NOT_STARTED"):
                continue
            path = " / ".join(p.get("englishName", p.get("name", "")) for p in ev.get("path", []))
            if league_words and not any(w.lower() in path.lower() for w in league_words):
                continue
            home = ev.get("homeName") or ev.get("name", " - ").split(" - ")[0]
            away = ev.get("awayName") or ev.get("name", " - ").split(" - ")[-1]
            out.append(KambiEvent(int(ev["id"]), home, away, start, path))
        return out, raw

    def event_props(self, offering: str, book: str, ev: KambiEvent, match_id: str
                    ) -> tuple[list[OddsQuote], dict[str, str], dict | None]:
        raw = self._get(offering, f"betoffer/event/{ev.event_id}.json",
                        {"includeParticipants": "true"})
        if not raw:
            return [], {}, raw
        quotes, names = parse_betoffers(raw, book, match_id)
        return quotes, names, raw


def parse_betoffers(raw: dict, book: str, match_id: str) -> tuple[list[OddsQuote], dict[str, str]]:
    quotes: list[OddsQuote] = []
    names: dict[str, str] = {}
    now = time.time()
    for bo in raw.get("betOffers", []):
        crit = bo.get("criterion", {})
        label = crit.get("englishLabel") or crit.get("label") or ""
        mk = market_from_label(label)
        if not mk:
            continue
        market, fixed_line = mk
        for o in bo.get("outcomes", []):
            if o.get("status", "OPEN") != "OPEN" or not o.get("odds"):
                continue
            odds = o["odds"] / 1000.0
            if odds <= 1.0:
                continue
            olabel = (o.get("englishLabel") or o.get("label") or "").strip()
            player = o.get("participant") or ""
            otype = (o.get("type") or "").upper()
            low = olabel.lower()
            if low in ("over", "under") or otype in ("OT_OVER", "OT_UNDER"):
                side = "under" if (low == "under" or otype == "OT_UNDER") else "over"
            elif low in ("yes", "no"):
                side = "over" if low == "yes" else "under"
            else:
                side = "over"            # utfallet är själva spelaren (t.ex. målskytt)
                player = player or olabel
            if not player:
                continue
            if o.get("line") is not None:
                line = o["line"] / 1000.0
            elif fixed_line is not None:
                line = fixed_line
            else:
                line = 0.5
            pid = name_key(player)
            names.setdefault(pid, person_name(player))
            quotes.append(OddsQuote(book=book, match_id=match_id, player_id=pid, market=market,
                                    line=line, side=side, odds=odds, ts=now, provider="kambi"))
    return quotes, names
