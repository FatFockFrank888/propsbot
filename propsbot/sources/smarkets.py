"""Smarkets – betting-börs med öppet API (ingen nyckel): https://api.smarkets.com/v3/

Börspriser är skarpa: köp- och säljkurser från andra spelare, ingen bookmaker-marginal (bara kommission).
Används som andra skarp referens bredvid Pinnacle för sides/totals:
  * Full-time result (1X2), Over/under X.5, Asian Handicap (hela, halva och kvartslinjer).
  * Pris = mitten av bästa köp och bästa sälj (i baspunkter: 909 = 9,09 %). Bara när båda sidor finns
    och spreaden är högst SPREAD_MAX – annars är marknaden för tunn för att vara en referens.
  * Sannolikheterna normaliseras inom marknaden (1X2 summerar till 1, tvåvägsmarknader till 1).
Spelarmarknader (målskytt, skott på mål) finns också men är nästan alltid utan likviditet (7/11: 2 av 38
spelare hade pris på skott på mål) – de används inte.
"""
from __future__ import annotations

import re
import time
from datetime import datetime

from .http import JsonClient, SourceError

BASE = "https://api.smarkets.com/v3"
SPREAD_MAX = 400          # 4 procentenheter mellan köp och sälj
_NUM = re.compile(r"([+-]?\d+(?:\.\d+)?)\s*(?:goals|corners)?\s*$", re.I)


def _ts(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


class SmarketsPublic:
    def __init__(self, client: JsonClient):
        self.c = client
        self._events: list[tuple[str, str, str, float]] | None = None

    def events(self, hours: float = 24.0, max_pages: int = 40) -> list[tuple[str, str, str, float]]:
        """[(event_id, hemma, borta, start)] för fotbollsmatcher som startar inom `hours` (50 per sida)."""
        if self._events is not None:
            return self._events
        from datetime import timedelta, timezone
        now = datetime.now(timezone.utc)
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        url = f"{BASE}/events/"
        params = {"type": "football_match", "state": "upcoming", "limit": 200,
                  "start_datetime_min": now.strftime(fmt),
                  "start_datetime_max": (now + timedelta(hours=hours)).strftime(fmt)}
        out = []
        for _ in range(max_pages):
            try:
                raw = self.c.get(url, params, ttl=600) or {}
            except SourceError:
                break
            evs = raw.get("events", []) or []
            for e in evs:
                name = e.get("name", "")
                if " vs " in name and e.get("start_datetime"):
                    h, a = name.split(" vs ", 1)
                    out.append((str(e["id"]), h.strip(), a.strip(), _ts(e["start_datetime"])))
            nxt = (raw.get("pagination") or {}).get("next_page")
            if not evs or not nxt:
                break
            url, params = f"{BASE}/events/{nxt}", None
        self._events = out
        return out

    def find(self, home: str, away: str, start: float) -> str | None:
        from .props_text import same_match
        for eid, h, a, st in self.events():
            if same_match(home, away, start, h, a, st):
                return eid
        return None

    def main(self, event_id: str) -> dict:
        """{(marknad, linje, sida): (p_mitt, spread_bp)} – samma nycklar som sides.pinnacle_main."""
        try:
            mk = (self.c.get(f"{BASE}/events/{event_id}/markets/", ttl=600) or {}).get("markets", []) or []
        except SourceError:
            return {}
        want = {}
        for m in mk:
            n = (m.get("name") or "").strip()
            if n == "Full-time result":
                want[m["id"]] = "1x2"
            elif re.fullmatch(r"Over/under \d+\.5", n):
                want[m["id"]] = "total"
            elif n.startswith("Asian Handicap "):
                want[m["id"]] = "ah"
            elif re.fullmatch(r"Over/under \d+\.5 corners", n):
                want[m["id"]] = "corners"
        if not want:
            return {}
        ids = ",".join(list(want)[:40])
        try:
            cons = (self.c.get(f"{BASE}/markets/{ids}/contracts/", ttl=600) or {}).get("contracts", []) or []
            quotes = self.c.get(f"{BASE}/markets/{ids}/quotes/", ttl=90) or {}
        except SourceError:
            return {}
        by_market: dict[str, list] = {}
        for c in cons:
            q = quotes.get(str(c["id"])) or {}
            bids, offers = q.get("bids") or [], q.get("offers") or []
            if not bids or not offers:
                by_market.setdefault(c["market_id"], []).append(None)
                continue
            b, o = max(x["price"] for x in bids), min(x["price"] for x in offers)
            if o - b > SPREAD_MAX or o <= b:
                by_market.setdefault(c["market_id"], []).append(None)
                continue
            by_market.setdefault(c["market_id"], []).append((c, (b + o) / 2 / 10000, o - b))
        out: dict = {}
        for mid, items in by_market.items():
            if any(x is None for x in items):
                continue                      # hela marknaden måste ha priser, annars kan den inte normaliseras
            tot = sum(p for _c, p, _s in items)
            if tot <= 0:
                continue
            kind = want.get(mid)
            for c, p, spread in items:
                side = c.get("slug")
                if kind == "1x2" and side in ("home", "draw", "away"):
                    out[("1x2", 0.0, side)] = (p / tot, spread)
                elif kind in ("total", "corners") and side in ("over", "under"):
                    m = _NUM.search(c.get("name", ""))
                    if m:
                        out[(kind, float(m.group(1)), side)] = (p / tot, spread)
                elif kind == "ah" and side in ("home", "away"):
                    m = _NUM.search(c.get("name", ""))
                    if m:
                        out[("ah", float(m.group(1)), side)] = (p / tot, spread)
        return out
