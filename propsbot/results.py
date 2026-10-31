"""Rättning: hämta spelarstatistik efter matchen från ESPN:s öppna API.

site.api.espn.com/apis/site/v2/sports/soccer/{liga}/scoreboard?dates=YYYYMMDD
site.api.espn.com/apis/site/v2/sports/soccer/{liga}/summary?event={id}

Ingen nyckel. Inofficiellt – parsningen är defensiv och allt som inte går att
rätta ligger kvar som "öppen" och försöks igen vid nästa körning.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from .ledger import Ledger
from .sources.http import JsonClient, SourceError
from .sources.props_text import same_match, same_person

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
LEAGUES = ["eng.1", "esp.1", "ger.1", "ita.1", "fra.1", "uefa.champions", "uefa.europa",
           "uefa.europa.conf", "swe.1", "eng.2", "esp.2", "ger.2", "ita.2", "fra.2",
           "ned.1", "por.1", "eng.fa", "esp.copa_del_rey", "ger.dfb_pokal", "ita.coppa_italia",
           "fra.coupe_de_france", "eng.league_cup"]

STAT_NAMES = {
    "goal": ("totalGoals", "goals"),
    "assist": ("goalAssists", "assists"),
    "shots_on_target": ("shotsOnTarget", "shotsOnGoal"),
    "shots": ("totalShots", "shots"),
}


def _stats(athlete_entry: dict) -> dict[str, float]:
    out = {}
    for s in athlete_entry.get("stats", []) or []:
        name = s.get("name") or s.get("abbreviation")
        try:
            out[name] = float(s.get("value", s.get("displayValue")))
        except (TypeError, ValueError):
            continue
    return out


def _played(entry: dict, st: dict) -> bool:
    if entry.get("starter") or entry.get("subbedIn"):
        return True
    for k in ("appearances", "minutesPlayed", "minutes"):
        if st.get(k, 0) > 0:
            return True
    return False


class EspnResults:
    def __init__(self, client: JsonClient):
        self.c = client
        self._board: dict[tuple[str, str], list] = {}

    def find_event(self, home: str, away: str, start: float) -> tuple[str, str] | None:
        day = datetime.fromtimestamp(start, timezone.utc).strftime("%Y%m%d")
        for lg in LEAGUES:
            key = (lg, day)
            if key not in self._board:
                try:
                    raw = self.c.get(f"{BASE}/{lg}/scoreboard", {"dates": day}, ttl=1800) or {}
                except SourceError:
                    raw = {}
                self._board[key] = raw.get("events", [])
            for ev in self._board[key]:
                comp = (ev.get("competitions") or [{}])[0]
                teams = {c.get("homeAway"): c.get("team", {}).get("displayName", "")
                         for c in comp.get("competitors", [])}
                try:
                    st = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).timestamp()
                except (KeyError, ValueError):
                    continue
                if same_match(home, away, start, teams.get("home", ""), teams.get("away", ""), st):
                    done = ev.get("status", {}).get("type", {}).get("completed", False)
                    return (lg, ev["id"]) if done else (lg, "")
        return None

    def player_stats(self, league: str, event_id: str) -> list[tuple[str, dict, bool]]:
        raw = self.c.get(f"{BASE}/{league}/summary", {"event": event_id}, ttl=3600) or {}
        out = []
        for team in raw.get("rosters", []) or []:
            for e in team.get("roster", []) or []:
                name = (e.get("athlete") or {}).get("displayName", "")
                st = _stats(e)
                out.append((name, st, _played(e, st)))
        return out


def settle_open(ledger: Ledger, client: JsonClient, now: float | None = None,
                min_hours_after: float = 2.5) -> list[str]:
    now = now or time.time()
    espn = EspnResults(client)
    log = []
    cache: dict[str, list] = {}
    for b in ledger.bets:
        if b["status"] != "öppen" or not b.get("avspark") or now < b["avspark"] + min_hours_after * 3600:
            continue
        mkey = b["match_id"]
        if mkey not in cache:
            try:
                hit = espn.find_event(b["hemma"], b["borta"], b["avspark"])
                cache[mkey] = espn.player_stats(*hit) if hit and hit[1] else None
            except SourceError as e:
                log.append(f"Rättning {b['match']}: FEL {e}")
                cache[mkey] = None
        roster = cache[mkey]
        if not roster:
            if now > b["avspark"] + 72 * 3600:
                log.append(f"Rättning {b['match']}: hittar inte matchen hos ESPN – rätta manuellt")
            continue
        player = next(((st, pl) for n, st, pl in roster if same_person(n, b["spelare"])), None)
        if player is None:
            ledger.settle(b, None, played=False)
            log.append(f"Struken: {b['spelare']} ({b['match']}) – fanns inte i truppen")
            continue
        st, played = player
        names = STAT_NAMES[b["marknad"]]
        val = next((st[n] for n in names if n in st), None)
        if played and val is None:
            log.append(f"Rättning {b['spelare']}: statistik saknas ({', '.join(sorted(st))[:120]})")
            continue
        ledger.settle(b, int(val) if val is not None else None, played)
        log.append(f"Rättad: {b['spelare']} {b['marknad']} över {b['linje']} -> {b['status']} ({val})")
    return log
