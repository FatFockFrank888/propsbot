"""DraftKings, FanDuel, BetMGM m.fl. (USA) som extra referens för NBA-props (via The Odds API).

bet365 finns inte i The Odds API (testat 2/11 i alla regioner). DraftKings och FanDuel
är de största marknaderna för amerikanska spelarprops och ger en tvåsidig referens
utöver Pinnacle. De används bara som jämförelse – aldrig som spelbolag.

Krediter: ett anrop kostar 1 kredit per marknad (bookmakers=draftkings,fanduel räknas
som en region). Boten hämtar varje match EN gång, nära start (fönstret
nba_us_fetch_window minuter före), sparar oddsen och återanvänder dem i senare
skanningar. Antalet marknader per match styrs av en dagsbudget:
    dagsbudget = kvarvarande krediter / dagar kvar i månaden (minus en reserv)
så kvoten räcker hela månaden, oavsett om det är gratiskvoten (500) eller en betalplan.

Nyckeln läses ur miljövariabeln ODDS_API_KEY (GitHub-secret). Saknas den hoppas allt över.
"""
from __future__ import annotations

import calendar
import json
import os
import time
from pathlib import Path

from ..models import OddsQuote
from .props_text import same_match
from .the_odds_api import TheOddsApi, normalize_name

SPORT = "basketball_nba"
# Upp till 10 bolag i samma anrop kostar som EN region – fler bolag är alltså gratis.
# BetRivers är Kambi (samma prissättning som Unibet) och tas inte med. bet365 finns inte i API:t.
BOOKS = ["draftkings", "fanduel", "betmgm", "williamhill_us", "fanatics", "espnbet",
         "hardrockbet", "betonlineag"]
# Prioritetsordning: marknaderna där vi spelar mest först.
MARKETS = [
    ("player_points", "points"), ("player_threes", "threes"), ("player_assists", "assists"),
    ("player_rebounds", "rebounds"), ("player_points_rebounds_assists", "pra"),
    ("player_points_rebounds", "pr"), ("player_rebounds_assists", "ra"),
    ("player_steals", "steals"), ("player_blocks", "blocks"),
]
OURS = dict(MARKETS)
SIDES = {"over": "over", "under": "under"}


def _days_left(now: float) -> int:
    t = time.gmtime(now)
    return calendar.monthrange(t.tm_year, t.tm_mon)[1] - t.tm_mday + 1


def parse(event: dict, match_id: str, fetch_ts: float) -> tuple[list[OddsQuote], dict[str, str]]:
    quotes, names = [], {}
    for bm in event.get("bookmakers", []):
        for m in bm.get("markets", []):
            ours = OURS.get(m.get("key"))
            if not ours:
                continue
            for o in m.get("outcomes", []):
                side = SIDES.get(str(o.get("name", "")).lower())
                player = o.get("description") or ""
                price, point = o.get("price"), o.get("point")
                if not side or not player or point is None or not price or price <= 1.0:
                    continue
                pid = normalize_name(player)
                names.setdefault(pid, player)
                # us_-prefix: amerikanska BetMGM får aldrig blandas ihop med svenska BetMGM (Kambi).
                quotes.append(OddsQuote(book="us_" + bm["key"], match_id=match_id, player_id=pid, market=ours,
                                        line=float(point), side=side, odds=float(price), ts=fetch_ts,
                                        provider="oddsapi", variant=m["key"]))
    return quotes, names


def add_us_books(root: Path, per: dict, settings: dict, diag) -> int:
    """Lägger DraftKings/FanDuel-odds i per[event_id] = (evd, quotes, names). Returnerar antal odds."""
    if not settings.get("nba_us_books", True) or not os.environ.get("ODDS_API_KEY"):
        diag.log("DK/FD: av (ingen ODDS_API_KEY)")
        return 0
    state_path = root / "nba_usodds.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}
    store: dict = state.setdefault("matcher", {})
    spent: dict = state.setdefault("forbrukat_per_dag", {})
    now = time.time()
    today = time.strftime("%Y-%m-%d", time.gmtime(now))
    api = TheOddsApi(cache_dir=root / ".cache_odds", cache_ttl_s=0)

    # Gratis anrop: matchlistan (ger också kvarvarande krediter i svarshuvudet).
    events = api._get(f"/sports/{SPORT}/events", {}, ttl=0) or []
    remaining = int(api.usage.remaining) if api.usage.remaining not in (None, "") else 0
    reserve = settings.get("nba_us_reserve", 20)
    day_budget = max(0, (remaining - reserve)) // max(1, _days_left(now))
    left_today = max(0, day_budget - spent.get(today, 0))
    lo, hi = settings.get("nba_us_fetch_window", [40, 240])

    n_quotes = n_calls = 0
    for ev_id, (evd, qs_all, names) in per.items():
        mid = evd["id"]
        oe = next((e for e in events if same_match(
            evd["home_team"], evd["away_team"], evd["commence_time"], e["home_team"], e["away_team"],
            calendar.timegm(time.strptime(e["commence_time"], "%Y-%m-%dT%H:%M:%SZ")))), None)
        if not oe:
            continue
        mins = (evd["commence_time"] - now) / 60
        if mid not in store and lo <= mins <= hi and left_today > 0:
            # Lika många marknader per match som dagsbudgeten räcker till (minst 1, högst alla).
            games_left = sum(1 for v in per.values()
                             if v[0]["id"] not in store and 0 < (v[0]["commence_time"] - now) / 60 <= 24 * 60)
            n_mk = max(1, min(len(MARKETS), left_today // max(1, games_left)))
            mks = [k for k, _ in MARKETS[:n_mk]]
            data = api.event_odds(SPORT, oe["id"], mks, bookmakers=BOOKS)
            cost = int(api.usage.last_cost or len(mks))
            spent[today] = spent.get(today, 0) + cost
            left_today -= cost
            n_calls += 1
            store[mid] = {"ts": now, "avspark": evd["commence_time"], "marknader": mks, "svar": data or {}}
        if mid in store:
            q, nm = parse(store[mid]["svar"], mid, store[mid]["ts"])
            qs_all += q
            names.update(nm)
            n_quotes += len(q)
    # Städa: matcher som startat för mer än ett dygn sedan, dagräknare äldre än 40 dagar.
    state["matcher"] = {k: v for k, v in store.items() if now - v.get("avspark", now) < 86400}
    state["forbrukat_per_dag"] = dict(sorted(spent.items())[-40:])
    state["kvar"] = api.usage.remaining
    state_path.write_text(json.dumps(state), encoding="utf-8")
    diag.log(f"DK/FD: {n_calls} nya hämtningar, {n_quotes} odds i bruk, krediter kvar {api.usage.remaining}, "
             f"dagsbudget {day_budget}, förbrukat idag {spent.get(today, 0)}")
    return n_quotes
