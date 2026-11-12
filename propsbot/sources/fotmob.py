"""Reservkälla för slutresultat i fotboll: FotMobs öppna JSON (ingen nyckel).

www.fotmob.com/api/data/matches?date=YYYYMMDD ger alla matcher en dag (cirka 170 ligor, även lägre
divisioner som ESPN saknar). Används bara när ESPN inte hittar matchen. Inofficiellt: parsningen är
defensiv och allt som inte går att läsa ger None, så spelet ligger kvar som öppet.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .http import SourceError

URL = "https://www.fotmob.com/api/data/matches"


class FotmobResults:
    def __init__(self, client):
        self.c = client
        self._days: dict[str, list[dict]] = {}

    def _matches(self, day: str) -> list[dict]:
        if day not in self._days:
            try:
                raw = self.c.get(URL, {"date": day}, ttl=1800) or {}
            except SourceError:
                raw = {}
            self._days[day] = [m for lg in raw.get("leagues", []) or [] for m in lg.get("matches", []) or []]
        return self._days[day]

    def final_score(self, home: str, away: str, start: float) -> tuple[int, int] | None:
        """(hemmamål, bortamål) efter 90 min, eller None (saknas, inte klar, förlängning/straffar, struken)."""
        from ..results import espn_match
        days = dict.fromkeys(datetime.fromtimestamp(t, timezone.utc).strftime("%Y%m%d")
                             for t in (start, start - 5 * 3600, start + 3 * 3600))
        for day in days:
            for m in self._matches(day):
                st = m.get("status") or {}
                try:
                    ts = datetime.fromisoformat(st["utcTime"].replace("Z", "+00:00")).timestamp()
                except (KeyError, ValueError, AttributeError):
                    continue
                h, a = m.get("home") or {}, m.get("away") or {}
                if not espn_match(home, away, start, h.get("name", ""), a.get("name", ""), ts):
                    continue
                reason = ((st.get("reason") or {}).get("short") or "").upper()
                if not st.get("finished") or st.get("cancelled") or st.get("awarded") or reason != "FT":
                    return None
                try:
                    return int(h["score"]), int(a["score"])
                except (KeyError, TypeError, ValueError):
                    return None
        return None
