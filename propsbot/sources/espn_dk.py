"""DraftKings NBA-spelarodds via ESPN:s öppna API (ingen nyckel) – en extra oberoende referens.

  site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=YYYYMMDD   -> matcher (event-id)
  sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{id}/competitions/{id}/odds/100/propBets
                                                                                    -> DraftKings (provider 100)

Varje "Total …"-marknad kommer som två rader med samma linje: över och under. ESPN anger inte sidan, men
ordningen är över först (stämde i 17 av 19 par mot DraftKings egna "N+"-milstolpar 12/11). När milstolpen
för linjen + 0,5 finns används den för att avgöra vilken rad som är över; annars ordningen. Par med orimlig
marginal (summan av sannolikheterna utanför 1,00–1,15) slängs.

Spelarna anges som länk till ESPN:s athlete-id. Namnen kostar ett anrop per spelare, så de sparas för gott i
läget (espn_athletes.json) och högst MAX_NEW_ATHLETES nya slås upp per skanning.
Bolaget heter "us_draftkings" – samma namn som SportsGameOdds och The Odds API använder, så DraftKings aldrig
räknas två gånger.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from ..models import OddsQuote
from .props_text import name_key, person_name, same_match

SB = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
CORE = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
MARKETS = {"Total Points": "points", "Total Rebounds": "rebounds", "Total Assists": "assists",
           "Total 3-Point Field Goals": "threes", "Total Points, Rebounds, and Assists": "pra",
           "Total Points and Rebounds": "pr", "Total Assists and Rebounds": "ra"}
MILESTONE = {"points": "Points Milestones", "rebounds": "Rebounds Milestones", "assists": "Assists Milestones",
             "threes": "3-Point Field Goals Milestones", "pra": "Points + Assists + Rebounds Milestones",
             "pr": "Points + Rebounds Milestones", "ra": "Rebounds + Assists Milestones"}
MAX_NEW_ATHLETES = 120
MAX_AGE_S = 3 * 3600


def _ts(s: str | None) -> float | None:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _aid(item: dict) -> str | None:
    ref = (item.get("athlete") or {}).get("$ref") or ""
    return ref.split("/athletes/")[1].split("?")[0] if "/athletes/" in ref else None


def _dec(item: dict) -> float | None:
    try:
        return float(item["odds"]["decimal"]["value"])
    except (KeyError, TypeError, ValueError):
        return None


def _line(item: dict) -> float | None:
    try:
        return float(str(item["odds"]["total"]["value"]).rstrip("+"))
    except (KeyError, TypeError, ValueError):
        return None


def parse(items: list[dict], now: float) -> list[tuple[str, str, float, str, float, float]]:
    """[(athlete_id, marknad, linje, sida, odds, ts)] – bara tvåsidiga halvlinjer med rimlig marginal."""
    groups: dict[tuple, list[dict]] = {}
    for it in items:
        aid, name = _aid(it), (it.get("type") or {}).get("name")
        if aid and name:
            groups.setdefault((aid, name), []).append(it)
    out = []
    for (aid, name), xs in groups.items():
        mk = MARKETS.get(name)
        if not mk:
            continue
        by_line: dict[float, list[dict]] = {}
        for x in xs:
            ln = _line(x)
            if ln is not None:
                by_line.setdefault(ln, []).append(x)
        miles = {_line(m): _dec(m) for m in groups.get((aid, MILESTONE[mk]), [])}
        for ln, pair in by_line.items():
            if len(pair) != 2 or abs(ln - round(ln)) < 1e-9:      # heltal = push möjlig – används inte
                continue
            a, b = _dec(pair[0]), _dec(pair[1])
            t = _ts(pair[0].get("lastUpdated")) or now
            if not a or not b or a <= 1 or b <= 1 or now - t > MAX_AGE_S:
                continue
            if not (1.0 <= 1 / a + 1 / b <= 1.15):
                continue
            over, under = a, b
            m = miles.get(ln + 0.5)
            if m and abs(b - m) < abs(a - m) - 0.02:              # milstolpen säger att andra raden är över
                over, under = b, a
            out += [(aid, mk, ln, "over", over, t), (aid, mk, ln, "under", under, t)]
    return out


class Athletes:
    """ESPN athlete-id -> namn, sparat i läget."""

    def __init__(self, path: Path, client):
        self.path, self.c = path, client
        try:
            self.names: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            self.names = {}
        self.new = 0

    def get(self, aid: str, season_ref: str) -> str | None:
        if aid in self.names:
            return self.names[aid]
        if self.new >= MAX_NEW_ATHLETES:
            return None
        self.new += 1
        from .http import SourceError
        try:
            d = self.c.get(f"{CORE}/seasons/{season_ref}/athletes/{aid}", {"lang": "en", "region": "us"}, ttl=86400) or {}
        except SourceError:
            return None
        n = d.get("displayName") or d.get("fullName")
        if n:
            self.names[aid] = n
        return n

    def save(self) -> None:
        self.path.write_text(json.dumps(self.names, ensure_ascii=False), encoding="utf-8")


def add_espn_dk(root: Path, per: dict, diag, client=None) -> int:
    """Lägg DraftKings-odds från ESPN i per[event_id] = (evd, quotes, names). Returnerar antal odds."""
    from .http import JsonClient, SourceError
    c = client or JsonClient(root / ".cache_odds", ttl_s=300, min_interval_s=0.2)
    now = time.time()
    days = sorted({time.strftime("%Y%m%d", time.gmtime(evd["commence_time"] - 6 * 3600)) for evd, _q, _n in per.values()})
    events = []
    for day in days:
        try:
            events += (c.get(SB, {"dates": day}, ttl=900) or {}).get("events", [])
        except SourceError:
            continue
    ath = Athletes(root / "espn_athletes.json", c)
    n = n_games = 0
    for evd, qs_all, names in per.values():
        ev = None
        for e in events:
            comp = (e.get("competitions") or [{}])[0]
            t = {x.get("homeAway"): (x.get("team") or {}).get("displayName", "") for x in comp.get("competitors", [])}
            if same_match(evd["home_team"], evd["away_team"], evd["commence_time"], t.get("home", ""), t.get("away", ""),
                          _ts(e.get("date")) or 0):
                ev = e
                break
        if not ev:
            continue
        season = str((ev.get("season") or {}).get("year") or "")
        try:
            raw = c.get(f"{CORE}/events/{ev['id']}/competitions/{ev['id']}/odds/100/propBets", {"limit": 1000}, ttl=300) or {}
        except SourceError:
            continue
        rows = parse(raw.get("items", []) or [], now)
        if not rows:
            continue
        n_games += 1
        have = {(q.book, q.player_id, q.market, q.line, q.side) for q in qs_all}
        for aid, mk, ln, side, odds, t in rows:
            nm = ath.get(aid, season)
            if not nm:
                continue
            pid = name_key(nm)
            key = ("us_draftkings", pid, mk, ln, side)
            if key in have:
                continue
            names.setdefault(pid, person_name(nm))
            qs_all.append(OddsQuote(book="us_draftkings", match_id=evd["id"], player_id=pid, market=mk, line=ln,
                                    side=side, odds=round(odds, 3), ts=t, provider="espn_dk", variant=mk))
            have.add(key)
            n += 1
    ath.save()
    diag.log(f"DraftKings via ESPN: {n_games} matcher, {n} spelarodds (referens)"
             + (f", {ath.new} nya spelarnamn" if ath.new else ""))
    return n
