"""SportsGameOdds (https://sportsgameodds.com) – amerikanska bolags NBA-props som extra referens.

Gratisnivån ("amateur"): 10 anrop/minut och 2 500 objekt (= matcher) per rullande 30 dagar – se budgeten
nedan. Ett anrop ger alla NBA-matcher med odds som startar inom SGO_WINDOW_H.
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


# Gratisnivån: 2 500 objekt per rullande 30 dagar, och varje match i svaret är ett objekt (även ett tomt svar
# kostar 1). Utan budget tog boten 48 matcher per skanning och slut på hela månadskvoten på en dag (11/11).
# Nu: bara matcher som startar inom SGO_WINDOW_H, högst SGO_DAY_BUDGET objekt per dygn (UTC), ett nytt
# anrop först när förra svaret är SGO_MIN_GAP_S gammalt, och efter HTTP 429 vilar källan SGO_PAUSE_S.
SGO_WINDOW_H = 14
SGO_DAY_BUDGET = 80
SGO_MIN_GAP_S = 5400
SGO_PAUSE_S = 24 * 3600


def _state(path):
    import json
    try:
        st = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        st = {}
    st.setdefault("objekt", {})
    return st


def fetch(cache_dir, state_path=None, now: float | None = None, client=None) -> tuple[list[dict], str]:
    """(matcher, orsak) – matcher som startar inom SGO_WINDOW_H i ett anrop, inom dagsbudgeten.

    orsak är tom när anropet gjordes, annars varför det hoppades över eller misslyckades."""
    import json
    from .http import JsonClient, SourceError
    key = os.environ.get("SGO_API_KEY", "").strip()
    if not key:
        return [], "ingen nyckel (SGO_API_KEY)"
    now = now or time.time()
    st = _state(state_path) if state_path else {"objekt": {}}
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    used = st["objekt"].get(day, 0)

    def save():
        if state_path:
            st["objekt"] = dict(sorted(st["objekt"].items())[-35:])
            st["manad"] = sum(st["objekt"].values())
            state_path.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")

    if now < st.get("paus_till", 0):
        return [], f"vilar efter kvotfel till {time.strftime('%d/%m %H:%M', time.gmtime(st['paus_till']))} UTC"
    if now - st.get("senast", 0) < SGO_MIN_GAP_S:
        return [], "väntar (sparar kvoten, ett anrop var 90:e minut)"
    if used >= SGO_DAY_BUDGET:
        return [], f"dagsbudgeten {SGO_DAY_BUDGET} objekt är slut ({used})"
    c = client or JsonClient(cache_dir, ttl_s=300, min_interval_s=7.0, headers={"x-api-key": key})
    before = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + SGO_WINDOW_H * 3600))
    st["senast"] = now
    try:
        raw = c.get(URL, {"leagueID": "NBA", "oddsAvailable": "true", "startsBefore": before,
                          "limit": max(1, min(20, SGO_DAY_BUDGET - used))}, ttl=300) or {}
    except SourceError as e:
        msg = str(e)
        st["objekt"][day] = used + 1
        if "429" in msg:
            st["paus_till"] = now + SGO_PAUSE_S
            save()
            return [], "HTTP 429 – kvoten slut (gratisnivån 2 500 objekt/30 dagar); vilar ett dygn"
        save()
        return [], f"fel från API:t: {msg[:120]}"
    data = raw.get("data", []) or []
    st["objekt"][day] = used + max(1, len(data))
    save()
    return data, "" if data else "inga matcher med odds i svaret"


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
    events, why = fetch(root / ".cache_odds", root / "sgo_lage.json")
    if not events:
        diag.log("SportsGameOdds NBA: " + why)
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
