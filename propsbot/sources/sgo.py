"""SportsGameOdds (https://sportsgameodds.com) – amerikanska bolags NBA-props som extra referens.

Gratisnivån ("amateur"): 10 anrop/minut. Ett anrop ger alla kommande NBA-matcher med odds
(events?leagueID=NBA&oddsAvailable=true), så boten gör ett anrop per skanning (cache 5 min).
Bolag: FanDuel, DraftKings, ESPN BET, Caesars, BetMGM, Bovada – används bara som jämförelse, aldrig som
spelbolag. Bolagsnamnen blir "us_<bolag>" (samma som us_books.py via The Odds API), så samma bolag aldrig
räknas två gånger. Regler:
  * bara tvåsidiga över/under på halvlinjer (heltal = push, används inte),
  * bara priser som är "available" och uppdaterade senast SGO_MAX_AGE_S före hämtningen,
  * marginalen tas bort inom varje bolags eget par i konsensus (scan.group_fair_prob) – aldrig bästa över
    från ett bolag och bästa under från ett annat.
Fotboll ingår inte i gratisnivån med bolagspriser (bara MLS/Champions League, utan bolag – testat 11/11).
Nyckeln läses ur SGO_API_KEY (GitHub-hemlighet). Saknas den hoppas allt över.
"""
from __future__ import annotations

import os
import time
from datetime import datetime

from ..models import OddsQuote
from .pinnacle_public import american_to_decimal
from .props_text import name_key, person_name, same_match

URL = "https://api.sportsgameodds.com/v2/events"
STAT = {"points": "points", "rebounds": "rebounds", "assists": "assists", "threePointersMade": "threes",
        "steals": "steals", "blocks": "blocks", "points+rebounds+assists": "pra", "points+rebounds": "pr",
        "rebounds+assists": "ra"}
BOOK = {"caesars": "williamhill_us"}           # samma namn som The Odds API använder för Caesars
SGO_MAX_AGE_S = 1800


def _ts(s: str | None) -> float | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError):
        return None


def fetch(cache_dir) -> list[dict]:
    """Alla kommande NBA-matcher med odds i ett anrop (cache 5 min). Tom lista utan nyckel eller vid fel."""
    from .http import JsonClient, SourceError
    key = os.environ.get("SGO_API_KEY", "").strip()
    if not key:
        return []
    c = JsonClient(cache_dir, ttl_s=300, min_interval_s=7.0, headers={"x-api-key": key})
    try:
        raw = c.get(URL, {"leagueID": "NBA", "oddsAvailable": "true", "limit": 50}, ttl=300) or {}
    except SourceError:
        return []
    return raw.get("data", []) or []


def quotes_for(events: list[dict], evd: dict, now: float) -> tuple[list[OddsQuote], dict[str, str]]:
    ev = next((e for e in events if same_match(
        evd["home_team"], evd["away_team"], evd["commence_time"],
        ((e.get("teams") or {}).get("home") or {}).get("names", {}).get("long", ""),
        ((e.get("teams") or {}).get("away") or {}).get("names", {}).get("long", ""),
        _ts((e.get("status") or {}).get("startsAt")) or 0)), None)
    if not ev:
        return [], {}
    players = ev.get("players") or {}
    qs, names = [], {}
    for o in (ev.get("odds") or {}).values():
        if not o.get("playerID") or o.get("betTypeID") != "ou" or o.get("sideID") not in ("over", "under"):
            continue
        mk = STAT.get(o.get("statID"))
        if not mk or o.get("periodID") not in (None, "game"):
            continue
        pl = players.get(o["playerID"]) or {}
        name = pl.get("name") or f"{pl.get('firstName', '')} {pl.get('lastName', '')}".strip()
        if not name:
            continue
        pid = name_key(name)
        names.setdefault(pid, person_name(name))
        for bk, b in (o.get("byBookmaker") or {}).items():
            if not b.get("available") or b.get("odds") is None or b.get("overUnder") is None:
                continue
            t = _ts(b.get("lastUpdatedAt"))
            if t is None or now - t > SGO_MAX_AGE_S:
                continue
            try:
                line, am = float(b["overUnder"]), float(str(b["odds"]).replace("+", ""))
            except ValueError:
                continue
            if abs(line - round(line)) < 1e-9:
                continue                                   # heltal: push möjlig – används inte
            qs.append(OddsQuote(book="us_" + BOOK.get(bk, bk), match_id=evd["id"], player_id=pid, market=mk,
                                line=line, side=o["sideID"], odds=round(american_to_decimal(am), 3), ts=t,
                                provider="sgo", variant=mk))
    # bara tvåsidiga par per bolag och linje
    have = {}
    for q in qs:
        have.setdefault((q.book, q.player_id, q.market, q.line), set()).add(q.side)
    qs = [q for q in qs if have[(q.book, q.player_id, q.market, q.line)] == {"over", "under"}]
    return qs, names


def add_sgo(root, per: dict, diag) -> int:
    events = fetch(root / ".cache_odds")
    if not events:
        return 0
    now = time.time()
    n = 0
    for evd, qs_all, names in per.values():
        have = {(q.book, q.player_id, q.market, q.line, q.side) for q in qs_all}
        qs, nm = quotes_for(events, evd, now)
        qs = [q for q in qs if (q.book, q.player_id, q.market, q.line, q.side) not in have]
        qs_all += qs
        names.update(nm)
        n += len(qs)
    diag.log(f"SportsGameOdds NBA: {len(events)} matcher, {n} spelarodds från amerikanska bolag (referens)")
    return n
