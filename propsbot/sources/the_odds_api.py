"""Koppling till The Odds API (v4).

Endpoints som används:
  GET /v4/sports                                     – lista sporter/ligor
  GET /v4/sports/{sport}/events                      – kommande matcher
  GET /v4/sports/{sport}/events/{event_id}/odds      – odds för en match
      (matchlinjer: h2h, totals, team_totals; props: player_shots,
       player_shots_on_target, player_goal_scorer_anytime, player_assists)

Kostnad i The Odds API = antal marknader × antal regioner per anrop
(en lista med upp till 10 bolag räknas som en region). Kvarvarande krediter
läses ur svarshuvudet x-requests-remaining och skrivs ut.

Nyckeln läses ur miljövariabeln ODDS_API_KEY och skrivs aldrig till disk.
Svar cachas på disk i några minuter så att omkörningar inte kostar krediter.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from ..models import OddsQuote

BASE_URL = "https://api.the-odds-api.com/v4"

# The Odds API-marknad -> (vår marknad, standardlinje för Ja/Nej-marknader)
PROP_MARKETS = {
    "player_shots": "shots",
    "player_shots_on_target": "shots_on_target",
    "player_goal_scorer_anytime": "goal",
    "player_assists": "assist",
}
MATCH_MARKETS = ("h2h", "totals")


class OddsApiError(RuntimeError):
    pass


def normalize_name(name: str) -> str:
    """'Martin Ødegaard' -> 'martin odegaard'. Används som player_id."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("ø", "o").replace("Ø", "o").replace("æ", "ae").replace("ß", "ss")
    s = "".join(c if c.isalnum() or c == " " else " " for c in s.lower())
    return " ".join(s.split())


@dataclass
class Usage:
    remaining: str | None = None
    used: str | None = None
    last_cost: str | None = None
    calls: int = 0
    cached: int = 0


@dataclass
class TheOddsApi:
    api_key: str | None = None
    cache_dir: Path = Path(".cache_odds")
    cache_ttl_s: float = 240.0
    timeout_s: float = 20.0
    usage: Usage = field(default_factory=Usage)

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.environ.get("ODDS_API_KEY")
        if not self.api_key:
            raise OddsApiError("ODDS_API_KEY saknas. Kör start.bat eller sätt miljövariabeln.")
        self.cache_dir = Path(self.cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    # ------------------------------------------------------------------ http
    def _get(self, path: str, params: dict | None = None, ttl: float | None = None):
        params = {k: v for k, v in (params or {}).items() if v not in (None, "")}
        key_src = path + "?" + urllib.parse.urlencode(sorted(params.items()))
        cache_file = self.cache_dir / (hashlib.sha1(key_src.encode()).hexdigest() + ".json")
        ttl = self.cache_ttl_s if ttl is None else ttl
        if cache_file.exists() and time.time() - cache_file.stat().st_mtime < ttl:
            self.usage.cached += 1
            return json.loads(cache_file.read_text(encoding="utf-8"))

        q = dict(params, apiKey=self.api_key)
        url = f"{BASE_URL}{path}?{urllib.parse.urlencode(q)}"
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=self.timeout_s) as resp:
                    body = resp.read().decode("utf-8")
                    h = resp.headers
                    self.usage.remaining = h.get("x-requests-remaining", self.usage.remaining)
                    self.usage.used = h.get("x-requests-used", self.usage.used)
                    self.usage.last_cost = h.get("x-requests-last", self.usage.last_cost)
                    self.usage.calls += 1
                    data = json.loads(body)
                    cache_file.write_text(body, encoding="utf-8")
                    return data
            except urllib.error.HTTPError as e:
                msg = e.read().decode("utf-8", "replace")[:300]
                if e.code == 429 and attempt < 3:
                    time.sleep(2 ** (attempt + 1))
                    continue
                if e.code == 401:
                    raise OddsApiError("Nyckeln avvisades (401). Kontrollera ODDS_API_KEY.") from e
                if e.code == 422:
                    # Ogiltig marknad/sport för just den här matchen – inte ett fatalt fel.
                    return None
                raise OddsApiError(f"HTTP {e.code} från The Odds API: {msg}") from e
            except urllib.error.URLError as e:
                if attempt < 3:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise OddsApiError(f"Kunde inte nå The Odds API: {e.reason}") from e
        raise OddsApiError("Gav upp efter flera försök")

    # ------------------------------------------------------------- endpoints
    def sports(self, all_sports: bool = False) -> list[dict]:
        """Gratis anrop (kostar inga krediter)."""
        return self._get("/sports", {"all": "true" if all_sports else None}, ttl=3600) or []

    def soccer_sports(self) -> list[dict]:
        return [s for s in self.sports() if s.get("key", "").startswith("soccer_")
                and not s.get("has_outrights")]

    def events(self, sport: str, hours_ahead: float = 48) -> list[dict]:
        """Kommande matcher (gratis anrop)."""
        now = time.time()
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        return self._get(f"/sports/{sport}/events", {
            "commenceTimeFrom": time.strftime(fmt, time.gmtime(now)),
            "commenceTimeTo": time.strftime(fmt, time.gmtime(now + hours_ahead * 3600)),
        }, ttl=600) or []

    def event_odds(self, sport: str, event_id: str, markets: list[str],
                   regions: str | None = "eu", bookmakers: list[str] | None = None) -> dict | None:
        params = {
            "markets": ",".join(markets),
            "oddsFormat": "decimal",
            "dateFormat": "unix",
        }
        if bookmakers:
            params["bookmakers"] = ",".join(bookmakers)
        else:
            params["regions"] = regions
        return self._get(f"/sports/{sport}/events/{event_id}/odds", params)


# ------------------------------------------------------------------ parsning
_SIDE_WORDS = {"over": "over", "under": "under", "yes": "over", "no": "under"}


def _ts(v) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        from datetime import datetime
        return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
    return time.time()


def parse_props(event: dict) -> tuple[list[OddsQuote], dict[str, str]]:
    """Gör om ett event-odds-svar till OddsQuote för spelarmarknaderna.

    Returnerar (quotes, player_id -> visningsnamn). Klarar båda varianterna:
      {"name": "Over", "description": "Spelare", "point": 1.5}
      {"name": "Spelare", "description": "Over", "point": 1.5}
    och Ja/Nej-marknader (målskytt) som tolkas som över/under 0.5.
    """
    quotes: list[OddsQuote] = []
    names: dict[str, str] = {}
    eid = event["id"]
    for bm in event.get("bookmakers", []):
        book = bm["key"]
        for m in bm.get("markets", []):
            ours = PROP_MARKETS.get(m.get("key"))
            if not ours:
                continue
            mts = _ts(m.get("last_update", bm.get("last_update")))
            for o in m.get("outcomes", []):
                name, desc = o.get("name", ""), o.get("description", "")
                if name.lower() in _SIDE_WORDS:
                    side, player = _SIDE_WORDS[name.lower()], desc
                elif desc.lower() in _SIDE_WORDS:
                    side, player = _SIDE_WORDS[desc.lower()], name
                else:
                    side, player = "over", name or desc  # ensidig lista med bara spelarnamn
                if not player:
                    continue
                price = o.get("price")
                if not price or price <= 1.0:
                    continue
                line = float(o["point"]) if o.get("point") is not None else 0.5
                pid = normalize_name(player)
                names.setdefault(pid, player)
                quotes.append(OddsQuote(book=book, match_id=eid, player_id=pid, market=ours,
                                        line=line, side=side, odds=float(price), ts=mts))
    return quotes, names


@dataclass
class MatchLines:
    home: str
    away: str
    source: str                         # "pinnacle" eller "konsensus"
    odds_1x2: tuple[float, float, float]
    total_line: float
    odds_total: tuple[float, float]
    ts: float


def parse_match_lines(event: dict, sharp_book: str = "pinnacle") -> MatchLines | None:
    """Plocka 1X2 och total ur ett event-svar. Pinnacle i första hand; annars
    medianen av alla bolags marginalfria sannolikheter (omvandlat till odds)."""
    from statistics import median

    from ..market import devig_power, devig_shin

    home, away = event["home_team"], event["away_team"]

    def lines_for(bm: dict):
        h2h = tot = None
        for m in bm.get("markets", []):
            if m["key"] == "h2h":
                d = {o["name"]: o["price"] for o in m.get("outcomes", [])}
                if home in d and away in d and "Draw" in d:
                    h2h = (d[home], d["Draw"], d[away])
            elif m["key"] == "totals":
                pts: dict[float, dict[str, float]] = {}
                for o in m.get("outcomes", []):
                    if o.get("point") is not None:
                        pts.setdefault(float(o["point"]), {})[o["name"].lower()] = o["price"]
                full = {p: v for p, v in pts.items() if "over" in v and "under" in v}
                if full:
                    # linjen närmast jämna odds
                    p = min(full, key=lambda x: abs(full[x]["over"] - full[x]["under"]))
                    tot = (p, (full[p]["over"], full[p]["under"]))
        return h2h, tot, _ts(bm.get("last_update"))

    books = event.get("bookmakers", [])
    for bm in books:
        if bm["key"] == sharp_book:
            h2h, tot, ts = lines_for(bm)
            if h2h and tot:
                return MatchLines(home, away, sharp_book, h2h, tot[0], tot[1], ts)

    # Konsensus: devig per bolag, median per utfall, tillbaka till "rättvisa odds".
    p1x2, ptot, ts_list = [], {}, []
    for bm in books:
        h2h, tot, ts = lines_for(bm)
        if h2h:
            p1x2.append(devig_shin(h2h))
            ts_list.append(ts)
        if tot:
            ptot.setdefault(tot[0], []).append(devig_power(tot[1])[0])
    if not p1x2 or not ptot:
        return None
    line = max(ptot, key=lambda k: len(ptot[k]))
    ph, pd, pa = (median(p[i] for p in p1x2) for i in range(3))
    s = ph + pd + pa
    po = median(ptot[line])
    return MatchLines(home, away, "konsensus", (s / ph, s / pd, s / pa), line,
                      (1 / po, 1 / (1 - po)), max(ts_list))
