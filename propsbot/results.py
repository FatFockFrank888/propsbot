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
from difflib import SequenceMatcher

from .sources.props_text import same_match, same_person, team_key

# Ord som inte skiljer lag åt (finns i många lagnamn) – räknas inte som träff på egen hand.
_GENERIC = {"united", "city", "real", "sporting", "athletic", "atletico", "deportivo", "town", "county", "rovers",
            "wanderers", "st", "saint", "de", "del", "la", "los", "club", "cd", "ca", "sd", "ud", "cf", "fc", "ac",
            "sc", "u21", "u23", "ii", "b", "women", "fk", "nk", "sk", "if", "bk", "ff", "inter", "dynamo", "olympique"}


def team_similarity(a: str, b: str) -> float:
    """0–1. Klarar att ena namnet är en del av det andra ("Ajax" / "Ajax Amsterdam", "Rennes" / "Stade Rennais")."""
    ka, kb = team_key(a), team_key(b)
    if not ka or not kb:
        return 0.0
    if ka == kb:
        return 1.0
    r = SequenceMatcher(None, ka, kb).ratio()
    ta = [w for w in ka.split() if w not in _GENERIC and len(w) >= 4]
    tb = [w for w in kb.split() if w not in _GENERIC and len(w) >= 4]
    if ta and tb and max(SequenceMatcher(None, x, y).ratio() for x in ta for y in tb) >= 0.75:
        r = max(r, 0.85)
    return r


def espn_match(home_a: str, away_a: str, start_a: float, home_b: str, away_b: str, start_b: float) -> bool:
    """Samma match i ESPN:s resultat: vanliga regeln, eller avspark inom 20 min och båda lagen liknar varandra."""
    if same_match(home_a, away_a, start_a, home_b, away_b, start_b):
        return True
    if abs(start_a - start_b) > 20 * 60:
        return False
    return min(team_similarity(home_a, home_b), team_similarity(away_a, away_b)) >= 0.75

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
LEAGUES = ["eng.1", "esp.1", "ger.1", "ita.1", "fra.1", "uefa.champions", "uefa.europa",
           "uefa.europa.conf", "swe.1", "eng.2", "esp.2", "ger.2", "ita.2", "fra.2",
           "ned.1", "por.1", "eng.fa", "esp.copa_del_rey", "ger.dfb_pokal", "ita.coppa_italia",
           "fra.coupe_de_france", "eng.league_cup", "bel.1", "sco.1", "tur.1", "den.1", "nor.1", "aut.1",
           "sui.1", "gre.1", "usa.1", "bra.1", "arg.1", "aus.1", "mex.1", "bra.copa_do_brazil"]

STAT_NAMES = {
    "goal": ("totalGoals", "goals"),
    "assist": ("goalAssists", "assists"),
    "shots_on_target": ("shotsOnTarget", "shotsOnGoal"),
    "shots": ("totalShots", "shots"),
    "fouls": ("foulsCommitted", "fouls", "FC"),
    "cards": ("cards",),          # gula + röda, räknas i player_stats
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

    def _events(self, lg: str, day: str) -> list:
        key = (lg, day)
        if key not in self._board:
            params = {"dates": day, "limit": 1000} if lg == "all" else {"dates": day}
            try:
                raw = self.c.get(f"{BASE}/{lg}/scoreboard", params, ttl=1800) or {}
            except SourceError:
                raw = {}
            self._board[key] = raw.get("events", [])
        return self._board[key]

    def find_any(self, home: str, away: str, start: float) -> tuple[str, dict] | None:
        """(liga, ESPN-händelse) oavsett status.

        ESPN sorterar matcher på amerikanskt datum: en match kl. 00:00–05:00 UTC (MLS, Liga MX, Sydamerika)
        ligger på föregående dags tavla. Därför provas både UTC-dagen och dagen fem timmar tidigare.
        """
        days = list(dict.fromkeys(datetime.fromtimestamp(t, timezone.utc).strftime("%Y%m%d")
                                  for t in (start, start - 5 * 3600)))
        for lg in ["all"] + LEAGUES:   # "all" = ESPN:s samlade tavla (alla ligor den täcker), först
            for day in days:
                for ev in self._events(lg, day):
                    comp = (ev.get("competitions") or [{}])[0]
                    teams = {c.get("homeAway"): c.get("team", {}).get("displayName", "")
                             for c in comp.get("competitors", [])}
                    try:
                        st = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).timestamp()
                    except (KeyError, ValueError):
                        continue
                    if espn_match(home, away, start, teams.get("home", ""), teams.get("away", ""), st):
                        return lg, ev
        return None

    def find_event(self, home: str, away: str, start: float) -> tuple[str, str] | None:
        """(liga, id) om matchen är klar, (liga, "") om den inte är klar, None om den saknas."""
        hit = self.find_any(home, away, start)
        if not hit:
            return None
        lg, ev = hit
        done = ev.get("status", {}).get("type", {}).get("completed", False)
        return (lg, ev["id"]) if done else (lg, "")

    def final_score(self, home: str, away: str, start: float) -> tuple[int, int] | None:
        """(hemmamål, bortamål) efter full tid (90 min + tillägg), eller None om inte klar/hittad."""
        hit = self.find_any(home, away, start)
        if not hit:
            return None
        lg, ev = hit
        st = (ev.get("status") or {}).get("type", {}) or {}
        if not st.get("completed"):
            return None
        # Förlängning/straffar räknas inte i 90-minutersmarknader – hoppa över (rättas manuellt).
        if (st.get("name") or "").upper() in ("STATUS_FINAL_AET", "STATUS_FINAL_PEN", "STATUS_FINAL_ET"):
            return None
        comp = (ev.get("competitions") or [{}])[0]
        sc = {c.get("homeAway"): c.get("score") for c in comp.get("competitors", [])}
        try:
            return int(sc["home"]), int(sc["away"])
        except (KeyError, TypeError, ValueError):
            return None

    def player_stats(self, league: str, event_id: str) -> list[tuple[str, dict, bool]]:
        raw = self.c.get(f"{BASE}/{league}/summary", {"event": event_id}, ttl=3600) or {}
        out = []
        for team in raw.get("rosters", []) or []:
            for e in team.get("roster", []) or []:
                name = (e.get("athlete") or {}).get("displayName", "")
                st = _stats(e)
                yc = next((st[k] for k in ("yellowCards", "YC") if k in st), None)
                rc = next((st[k] for k in ("redCards", "RC") if k in st), None)
                if yc is not None or rc is not None:
                    st["cards"] = (yc or 0.0) + (rc or 0.0)
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
