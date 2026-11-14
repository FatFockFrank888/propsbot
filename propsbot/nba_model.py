"""NBA-spelarmodell (testläge): minuter × takt per minut, justerat för skador,
motståndarens försvar och back-to-back.

Data (ESPN:s öppna API, fungerar från GitHub):
  scoreboard  – hitta matchen och lagens id
  teams/{id}/schedule – lagets senaste avslutade matcher (insläppta poäng, back-to-back)
  summary     – boxscore per match: MIN, PTS, REB, AST, 3PT, STL, BLK, startspelare
  injuries    – skadestatus (Out / Doubtful / Questionable / Day-To-Day)

Avslutade matchers boxscore cachas permanent (små utdrag).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .sources.http import JsonClient, SourceError
from .sources.props_text import name_key, same_match, same_person

ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
STATS = ("points", "rebounds", "assists", "threes", "steals", "blocks")
LABEL = {"points": "PTS", "rebounds": "REB", "assists": "AST", "threes": "3PT", "steals": "STL",
         "blocks": "BLK"}
COMBO = {"pra": ("points", "rebounds", "assists"), "pr": ("points", "rebounds"),
         "ra": ("rebounds", "assists")}
# Matchup-känslighet mot motståndarens insläppta poäng (elasticitet).
OPP_ELASTICITY = {"points": 0.8, "threes": 0.6, "assists": 0.5, "rebounds": 0.3,
                  "steals": 0.0, "blocks": 0.0}
OUT_STATUS = ("out", "doubtful", "suspension", "inactive")


def _ts(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def _num(v) -> float | None:
    if v is None:
        return None
    v = str(v).strip()
    if "-" in v and not v.startswith("-"):
        v = v.split("-")[0]               # "3-7" -> 3 (träffar)
    if ":" in v:
        m, s = v.split(":")[:2]           # "34:12" -> 34,2 min
        try:
            return float(m) + float(s) / 60
        except ValueError:
            return None
    try:
        return float(v)
    except ValueError:
        return None


@dataclass
class NbaPlayer:
    name: str
    team_id: str
    games: int
    starts: int
    minutes: float                         # viktat snitt (bara matcher där han spelade)
    per_min: dict[str, float] = field(default_factory=dict)
    min_sd: float = 0.0                    # viktad standardavvikelse för minuterna (nba_minutes)


@dataclass
class NbaTeam:
    team_id: str
    name: str
    players: dict[str, NbaPlayer]
    allowed: float                         # insläppta poäng per match (viktat)
    last_game: float | None


class NbaModel:
    def __init__(self, client: JsonClient, cache_dir: Path, n_games: int = 12,
                 half_life: float = 6.0, prior_minutes: float = 60.0):
        self.c = client
        self.dir = cache_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.n = n_games
        self.hl = half_life
        self.prior_min = prior_minutes
        self.fetched = 0
        self._boards: dict[str, list] = {}
        self._teams: dict[str, NbaTeam] = {}
        self._injuries: dict[str, str] | None = None

    # ------------------------------------------------------------ hämtning
    def board(self, day: str) -> list:
        if day not in self._boards:
            try:
                self._boards[day] = (self.c.get(f"{ESPN}/scoreboard", {"dates": day}, ttl=1800) or {}).get("events", [])
            except SourceError:
                self._boards[day] = []
        return self._boards[day]

    def find_event(self, home: str, away: str, start: float) -> tuple[str, str] | None:
        for d in (0, -1):
            day = (datetime.fromtimestamp(start, timezone.utc) + timedelta(days=d)).strftime("%Y%m%d")
            for ev in self.board(day):
                comp = (ev.get("competitions") or [{}])[0]
                t = {x.get("homeAway"): x.get("team", {}) for x in comp.get("competitors", [])}
                if "home" in t and "away" in t and same_match(
                        home, away, start, t["home"].get("displayName", ""), t["away"].get("displayName", ""),
                        _ts(ev["date"])):
                    return str(t["home"].get("id")), str(t["away"].get("id"))
        return None

    def box(self, event_id: str) -> dict | None:
        f = self.dir / f"{event_id}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        raw = self.c.get(f"{ESPN}/summary", {"event": event_id}, ttl=86400)
        if not raw:
            return None
        out = {"teams": {}, "score": {}}
        for comp in ((raw.get("header") or {}).get("competitions") or [])[:1]:
            for c in comp.get("competitors", []):
                out["score"][str(c.get("id") or (c.get("team") or {}).get("id"))] = _num(c.get("score"))
        for team in (raw.get("boxscore") or {}).get("players", []) or []:
            tid = str((team.get("team") or {}).get("id", ""))
            rows = []
            for grp in team.get("statistics", []) or []:
                labels = grp.get("labels") or grp.get("names") or []
                for a in grp.get("athletes", []) or []:
                    st = a.get("stats") or []
                    if a.get("didNotPlay") or not st:
                        continue
                    vals = {lab: _num(v) for lab, v in zip(labels, st)}
                    if not vals.get("MIN"):
                        continue
                    rows.append({"n": (a.get("athlete") or {}).get("displayName", ""),
                                 "s": bool(a.get("starter")), "min": vals.get("MIN"),
                                 **{k: vals.get(LABEL[k]) or 0.0 for k in STATS}})
            out["teams"][tid] = rows
        if out["teams"]:
            f.write_text(json.dumps(out), encoding="utf-8")
            self.fetched += 1
        return out

    def injuries(self) -> dict[str, str]:
        """name_key -> status (gemener). Tom vid fel."""
        if self._injuries is not None:
            return self._injuries
        self._injuries = {}
        try:
            raw = self.c.get(f"{ESPN}/injuries", ttl=900) or {}
        except SourceError:
            return self._injuries
        for team in raw.get("injuries", []) or []:
            for inj in team.get("injuries", []) or []:
                name = (inj.get("athlete") or {}).get("displayName", "")
                status = (inj.get("status") or inj.get("type", {}).get("description") or "").lower()
                if name:
                    self._injuries[name_key(name)] = status
        return self._injuries

    # ------------------------------------------------------------ lagmodell
    def team(self, team_id: str, before: float) -> NbaTeam | None:
        if team_id in self._teams:
            return self._teams[team_id]
        sched = self.c.get(f"{ESPN}/teams/{team_id}/schedule", ttl=6 * 3600) or {}
        done = []
        for ev in sched.get("events", []) or []:
            comp = (ev.get("competitions") or [{}])[0]
            st = (comp.get("status") or ev.get("status") or {}).get("type", {})
            try:
                t = _ts(ev["date"])
            except (KeyError, ValueError):
                continue
            if st.get("completed") and t < before:
                done.append((t, str(ev["id"])))
        done.sort(reverse=True)
        last_game = done[0][0] if done else None
        done = done[: self.n]
        if not done:
            return None
        acc: dict[str, dict] = {}
        allowed, wsum = 0.0, 0.0
        for age, (_, eid) in enumerate(done):
            bx = self.box(eid)
            if not bx or team_id not in bx["teams"]:
                continue
            w = 0.5 ** (age / self.hl)
            opp = [v for k, v in bx["score"].items() if k != team_id and v is not None]
            if opp:
                allowed += w * opp[0]
                wsum += w
            for p in bx["teams"][team_id]:
                a = acc.setdefault(name_key(p["n"]), {"name": p["n"], "w": 0.0, "wmin": 0.0, "wmin2": 0.0, "g": 0, "s": 0,
                                                     **{k: 0.0 for k in STATS}})
                a["w"] += w
                a["wmin"] += w * p["min"]
                a["wmin2"] += w * p["min"] ** 2
                a["g"] += 1
                a["s"] += int(p["s"])
                for k in STATS:
                    a[k] += w * p[k]
        if not acc:
            return None
        tot_min = sum(a["wmin"] for a in acc.values())
        team_rate = {k: sum(a[k] for a in acc.values()) / tot_min for k in STATS} if tot_min else {}
        players = {}
        for k, a in acc.items():
            per_min = {s: (a[s] + team_rate.get(s, 0) * self.prior_min) / (a["wmin"] + self.prior_min)
                       for s in STATS}
            m_avg = a["wmin"] / a["w"]
            var = max(0.0, a["wmin2"] / a["w"] - m_avg ** 2) * (a["g"] / (a["g"] - 1) if a["g"] > 1 else 1.0)
            # få matcher: krymp mot en typisk spridning (6 min) så att 2 likadana matcher inte ger sd 0
            sd = math.sqrt((a["g"] * var + 3 * 36.0) / (a["g"] + 3))
            players[k] = NbaPlayer(a["name"], team_id, a["g"], a["s"], m_avg, per_min, sd)
        tm = NbaTeam(team_id, (sched.get("team") or {}).get("displayName", team_id), players,
                     allowed / wsum if wsum else 114.0, last_game)
        self._teams[team_id] = tm
        return tm

    # ------------------------------------------------------------ prognos
    def expected(self, team: NbaTeam, opp: NbaTeam | None, start: float, league_allowed: float,
                 spread_home: float | None = None) -> dict[str, dict[str, float]]:
        """name_key -> {marknad: väntat värde} inkl. kombinationer.
        spread_home (Pinnacle, valfritt) ger minuter efter utklassningsrisk i _min_bo (skuggläge, nba_minutes)."""
        inj = self.injuries()
        out_keys = {k for k in team.players if any(s in inj.get(k, "") for s in OUT_STATUS)}
        # Speltid från skadade fördelas på friska spelare i proportion till deras minuter.
        missing = sum(team.players[k].minutes for k in out_keys)
        healthy = {k: p for k, p in team.players.items() if k not in out_keys and p.minutes >= 8}
        hm = sum(p.minutes for p in healthy.values()) or 1.0
        b2b = team.last_game is not None and start - team.last_game < 30 * 3600
        opp_ratio = (opp.allowed / league_allowed) if opp and league_allowed else 1.0
        res = {}
        for k, p in healthy.items():
            mins = min(42.0, p.minutes + missing * p.minutes / hm * 0.8)
            if b2b:
                mins *= 0.97
            if "questionable" in inj.get(k, "") or "day-to-day" in inj.get(k, ""):
                mins *= 0.9
            e = {}
            for s in STATS:
                adj = opp_ratio ** OPP_ELASTICITY[s]
                e[s] = mins * p.per_min[s] * min(max(adj, 0.92), 1.08)
            for c, parts in COMBO.items():
                e[c] = sum(e[x] for x in parts)
            e["_min"] = mins
            e["_min_sd"] = p.min_sd
            e["_g"] = p.games          # datakvalitet: antal matcher i underlaget
            res[k] = e
        from .nba_minutes import blowout_minutes
        bo = blowout_minutes({k: e["_min"] for k, e in res.items()}, spread_home)
        for k, e in res.items():
            e["_min_bo"] = bo[k]
        return res


def match_model_player(models: dict[str, dict], key: str) -> str | None:
    if key in models:
        return key
    return next((k for k in models if same_person(k, key)), None)
