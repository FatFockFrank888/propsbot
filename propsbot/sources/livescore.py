"""Tredje källan för slutresultat i fotboll: LiveScores publika JSON (ingen nyckel).

prod-public-api.livescore.com/v1/api/app/date/soccer/YYYYMMDD/0 ger alla matcher en dag i UTC
(cirka 220 turneringar och 850 matcher). Används när varken ESPN eller FotMob har matchen.
Inofficiellt: parsningen är defensiv och allt som inte går att läsa ger None.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .http import SourceError

URL = "https://prod-public-api.livescore.com/v1/api/app/date/soccer/{day}/0"


class LivescoreResults:
    def __init__(self, client):
        self.c = client
        self._days: dict[str, list[dict]] = {}

    def _events(self, day: str) -> list[dict]:
        if day not in self._days:
            try:
                raw = self.c.get(URL.format(day=day), {"MD": 1}, ttl=1800) or {}
            except SourceError:
                raw = {}
            self._days[day] = [e for s in raw.get("Stages", []) or [] for e in s.get("Events", []) or []]
        return self._days[day]

    def final_score(self, home: str, away: str, start: float) -> tuple[int, int] | None:
        """(hemmamål, bortamål) efter 90 min, eller None (saknas, inte klar, uppskjuten, avbruten)."""
        from ..results import espn_match
        days = dict.fromkeys(datetime.fromtimestamp(t, timezone.utc).strftime("%Y%m%d") for t in (start, start + 3 * 3600))
        for day in days:
            for e in self._events(day):
                try:
                    ts = datetime.strptime(str(e["Esd"]), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).timestamp()
                    h, a = e["T1"][0]["Nm"], e["T2"][0]["Nm"]
                except (KeyError, IndexError, TypeError, ValueError):
                    continue
                if not espn_match(home, away, start, h, a, ts):
                    continue
                eps = (e.get("Eps") or "").upper()
                if eps not in ("FT", "AET", "AP"):   # Postp., Int., Abd. … eller inte klar
                    return None
                try:
                    # Tr1OR/Tr2OR = ställningen efter ordinarie tid (90 min), finns även när matchen gick till
                    # förlängning eller straffar; utan den duger bara FT.
                    if "Tr1OR" in e and "Tr2OR" in e:
                        return int(e["Tr1OR"]), int(e["Tr2OR"])
                    return (int(e["Tr1"]), int(e["Tr2"])) if eps == "FT" else None
                except (KeyError, TypeError, ValueError):
                    return None
        return None
