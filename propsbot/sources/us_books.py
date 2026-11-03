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


FOOTBALL_SPORTS = ["soccer_epl", "soccer_spain_la_liga", "soccer_germany_bundesliga", "soccer_italy_serie_a",
                   "soccer_france_ligue_one", "soccer_uefa_champs_league", "soccer_uefa_europa_league",
                   "soccer_sweden_allsvenskan", "soccer_efl_champ", "soccer_netherlands_eredivisie",
                   "soccer_portugal_primeira_liga", "soccer_belgium_first_div", "soccer_spl",
                   "soccer_turkey_super_league", "soccer_denmark_superliga", "soccer_norway_eliteserien",
                   "soccer_uefa_europa_conference_league", "soccer_usa_mls", "soccer_germany_bundesliga2",
                   "soccer_italy_serie_b", "soccer_france_ligue_two", "soccer_austria_bundesliga",
                   "soccer_switzerland_superleague", "soccer_brazil_campeonato"]
FOOTBALL_MARKETS = [("player_shots_on_target", "shots_on_target"), ("player_shots", "shots")]
# Bolag med fotbollsprops i The Odds API (testat 2/11) + börser/nordiska bolag ifall de lägger ut props.
# Kambi-bolagen (unibet_*, leovegas_*) tas inte med – de är redan våra egna odds.
FOOTBALL_BOOKS = ["williamhill", "onexbet", "fanduel", "betfair_sb_uk", "betfair_ex_uk", "matchbook",
                  "coolbet", "betsson", "nordicbet", "paddypower"]
BUDGET_FILE = "oddsapi_lage.json"


def _ts(s: str) -> float:
    return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def _fetch_budgeted(root: Path, items, settings: dict, diag, *, sport_key: str, sports: list[str],
                    markets: list, books: list[str], window, share: float, label: str, parser) -> int:
    """Gemensam kreditbudget för NBA och fotboll. items = lista av (evd, quotes, names).
    Varje match hämtas en gång inom tidsfönstret; svaret sparas och återanvänds."""
    if not os.environ.get("ODDS_API_KEY"):
        diag.log(f"{label}: av (ingen ODDS_API_KEY)")
        return 0
    path = root / BUDGET_FILE
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}
    store: dict = state.setdefault(sport_key, {})
    spent: dict = state.setdefault("forbrukat_per_dag", {})
    now = time.time()
    today = time.strftime("%Y-%m-%d", time.gmtime(now))
    day = spent.setdefault(today, {})
    api = TheOddsApi(cache_dir=root / ".cache_odds", cache_ttl_s=0)
    events = []
    for sp in sports:                                   # matchlistor är gratis
        try:
            events += [dict(e, _sport=sp) for e in (api._get(f"/sports/{sp}/events", {}, ttl=0) or [])]
        except Exception:
            continue
    remaining = int(api.usage.remaining) if api.usage.remaining not in (None, "") else 0
    reserve = settings.get("oddsapi_reserve", 20)
    day_budget = max(0, remaining + sum(day.values()) - reserve) // max(1, _days_left(now))
    left = max(0, int(day_budget * share) - day.get(sport_key, 0))
    lo, hi = window
    n_quotes = n_calls = 0
    for evd, qs_all, names in items:
        mid = evd["id"]
        ko = float(evd["commence_time"])
        if mid not in store:
            mins = (ko - now) / 60
            if not (lo <= mins <= hi) or left <= 0:
                continue
            oe = next((e for e in events if same_match(evd["home_team"], evd["away_team"], ko,
                                                       e["home_team"], e["away_team"], _ts(e["commence_time"]))), None)
            if not oe:
                continue
            waiting = sum(1 for v in items if v[0]["id"] not in store
                          and 0 < (float(v[0]["commence_time"]) - now) / 60 <= hi)
            n_mk = max(1, min(len(markets), left // max(1, waiting)))
            mks = [k for k, _ in markets[:n_mk]]
            data = api.event_odds(oe["_sport"], oe["id"], mks, bookmakers=books)
            cost = int(api.usage.last_cost or len(mks))
            day[sport_key] = day.get(sport_key, 0) + cost
            left -= cost
            n_calls += 1
            store[mid] = {"ts": now, "avspark": ko, "marknader": mks, "svar": data or {}}
        q, nm = parser(store[mid]["svar"], mid, store[mid]["ts"])
        qs_all += q
        names.update(nm)
        n_quotes += len(q)
    state[sport_key] = {k: v for k, v in store.items() if now - v.get("avspark", now) < 86400}
    state["forbrukat_per_dag"] = dict(sorted(spent.items())[-40:])
    state["kvar"] = api.usage.remaining
    path.write_text(json.dumps(state), encoding="utf-8")
    diag.log(f"{label}: {n_calls} nya hämtningar, {n_quotes} odds i bruk, krediter kvar {api.usage.remaining}, "
             f"dagsbudget {day_budget} (andel {share:.0%}), förbrukat idag {day.get(sport_key, 0)}")
    return n_quotes


def add_us_books(root: Path, per: dict, settings: dict, diag) -> int:
    """NBA: DraftKings, FanDuel m.fl. in i per[event_id] = (evd, quotes, names)."""
    if not settings.get("nba_us_books", True):
        return 0
    return _fetch_budgeted(root, list(per.values()), settings, diag, sport_key="nba", sports=[SPORT],
                           markets=MARKETS, books=BOOKS, window=settings.get("nba_us_fetch_window", [40, 240]),
                           share=settings.get("oddsapi_share_nba", 0.6), label="DK/FD", parser=parse)


def parse_football(event: dict, match_id: str, fetch_ts: float):
    from dataclasses import replace
    from .the_odds_api import parse_props
    if not event or "bookmakers" not in event:
        return [], {}
    ev = dict(event, id=match_id)
    qs, names = parse_props(ev)
    out = [replace(q, book="oa_" + q.book, match_id=match_id, ts=fetch_ts, provider="oddsapi")
           for q in qs if q.market in ("shots", "shots_on_target")]
    return out, names


def add_football_books(root: Path, data: list, settings: dict, diag) -> int:
    """Fotboll: William Hill, 1xBet, FanDuel, Betfair, Matchbook, Coolbet m.fl. (bara referens)."""
    if not settings.get("football_extra_books", True):
        return 0
    return _fetch_budgeted(root, data, settings, diag, sport_key="fotboll", sports=FOOTBALL_SPORTS,
                           markets=FOOTBALL_MARKETS, books=FOOTBALL_BOOKS,
                           window=settings.get("football_fetch_window", [45, 300]),
                           share=settings.get("oddsapi_share_football", 0.4), label="Fotboll extra bolag",
                           parser=parse_football)
