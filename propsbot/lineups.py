"""Startelvor (fotboll) – gemensamt för sides/totals och spelarprops. Används när de finns, annars inte.

Källor: ESPN först, FotMob som reserv (169 ligor 7/11, även lägre divisioner; visar om elvan är
bekräftad – lineupType "standard" – eller bara förra matchens elva, plus skadade/avstängda).
X/Twitter (lagens egna konton) kräver betalt API och används inte.

ESPN:s matchsammanfattning har truppen redan före matchen, men spelarna markeras som
startande (`starter`) först när startelvorna släpps, normalt ca 60 min före avspark.
Skador och avstängningar: ESPN har ingen skadelista för fotboll, men frånvarande spelare
finns inte i startelvan – och Pinnacle har prisat in dem. Spärren nedan täcker därför båda.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .sources.http import SourceError
from .sources.props_text import name_key, same_person

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
FOTMOB = "https://www.fotmob.com/api/data"


@dataclass
class Lineup:
    published: bool                                   # båda lagens startelvor är ute
    starters: list[str] = field(default_factory=list)  # namn på alla startande (båda lagen)
    bench: list[str] = field(default_factory=list)
    source: str = "ESPN"
    unavailable: list[str] = field(default_factory=list)   # skadade/avstängda (FotMob)

    def starts(self, player: str) -> bool | None:
        """True/False när startelvan är ute, None om spelaren inte finns i truppen alls."""
        if any(same_person(player, n) for n in self.starters):
            return True
        if any(same_person(player, n) for n in self.bench):
            return False
        return None


class Lineups:
    def __init__(self, client):
        from .results import EspnResults
        self.espn = EspnResults(client)
        self.c = client
        self._cache: dict[str, Lineup | None] = {}

    def get(self, match_id: str, home: str, away: str, start: float) -> Lineup | None:
        """None = ESPN har inte matchen (då gäller tidsregeln i stället)."""
        if match_id in self._cache:
            return self._cache[match_id]
        out = None
        try:
            hit = self.espn.find_any(home, away, start)
            if hit:
                lg, ev = hit
                raw = self.c.get(f"{BASE}/{lg}/summary", {"event": ev["id"]}, ttl=480) or {}
                starters, bench, per_team = [], [], []
                for team in raw.get("rosters", []) or []:
                    n = 0
                    for e in team.get("roster", []) or []:
                        nm = (e.get("athlete") or {}).get("displayName", "")
                        if e.get("starter"):
                            starters.append(nm)
                            n += 1
                        else:
                            bench.append(nm)
                    per_team.append(n)
                out = Lineup(published=len(per_team) == 2 and min(per_team) >= 11,
                             starters=starters, bench=bench)
        except SourceError:
            out = None
        if out is None or not out.published:
            fm = self.fotmob(home, away, start)
            if fm is not None and (out is None or fm.published):
                out = fm
        self._cache[match_id] = out
        return out

    # ------------------------------------------------------------ FotMob (reserv)
    def fotmob(self, home: str, away: str, start: float) -> Lineup | None:
        from datetime import datetime, timezone
        from .sources.props_text import same_match
        day = datetime.fromtimestamp(start, timezone.utc).strftime("%Y%m%d")
        self._fm_days = getattr(self, "_fm_days", {})
        try:
            if day not in self._fm_days:
                raw = self.c.get(f"{FOTMOB}/matches", {"date": day}, ttl=900) or {}
                self._fm_days[day] = [m for lg in raw.get("leagues", []) or [] for m in lg.get("matches", []) or []]
            hit = None
            for m in self._fm_days[day]:
                try:
                    st = datetime.fromisoformat((m.get("status") or {}).get("utcTime", "").replace("Z", "+00:00")).timestamp()
                except ValueError:
                    continue
                if same_match(home, away, start, (m.get("home") or {}).get("name", ""), (m.get("away") or {}).get("name", ""), st):
                    hit = m
                    break
            if hit is None:
                return None
            d = self.c.get(f"{FOTMOB}/matchDetails", {"matchId": hit["id"]}, ttl=300) or {}
        except SourceError:
            return None
        lu = (d.get("content") or {}).get("lineup") or {}
        typ = lu.get("lineupType")
        if typ not in ("standard", "lastStarting11"):
            return None
        starters, bench, unav, n = [], [], [], []
        for side in ("homeTeam", "awayTeam"):
            tm = lu.get(side) or {}
            st = [p.get("name", "") for p in tm.get("starters") or []]
            starters += st
            n.append(len(st))
            bench += [p.get("name", "") for p in tm.get("subs") or []]
            unav += [p.get("name", "") for p in tm.get("unavailable") or []]
        confirmed = typ == "standard" and len(n) == 2 and min(n) >= 11
        # Förra matchens elva är inte en startelva – bara frånvarolistan används då.
        return Lineup(published=confirmed, starters=starters if confirmed else [], bench=bench if confirmed else [],
                      source="FotMob", unavailable=unav)


def gate(lu: Lineup | None, minutes_to_kickoff: float, s: dict) -> str | None:
    """Skäl att vänta, eller None om startelvorna är kända (eller tidsregeln uppfylld)."""
    if not s.get("lineup_required", True):
        return None
    if lu is None:
        return None      # ingen källa för startelvan (ESPN saknar matchen, t.ex. mindre ligor) – bortse från den
    if lu.published:
        return None
    if minutes_to_kickoff <= s.get("lineup_fallback_minutes", 55):
        return None      # elvorna är normalt ute nu, ESPN har bara inte markerat dem än
    return "väntar på startelvor (släpps ca 1 h före avspark)"
