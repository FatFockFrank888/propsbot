"""Fjärde källan för slutresultat i fotboll: goal-api.com (nyckel GOAL_API_KEY, 1 000 anrop/dygn).

GET https://api.goal-api.com/v1/results?from=YYYY-MM-DD&to=YYYY-MM-DD&limit=500&offset=N
med "Authorization: Bearer <nyckel>" ger alla avgjorda matcher en dag (cirka 1 400, 1 000+ ligor),
med ställningen efter ordinarie tid (homeTeamFtScore/awayTeamFtScore) skild från förlängning och straffar.

Används sist, bara för spel som ESPN, FotMob och LiveScore saknar. Boten körs ~140 gånger per dygn utan
bestående HTTP-cache, så färdiga dagar sparas i läget (goal_api_lage.json) och hämtas en gång; en dag som
kan få fler resultat hämtas om högst var 6:e timme, och anropen per dygn har ett tak (DAILY_CAP).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://api.goal-api.com/v1/results"
DAILY_CAP = 300          # av 1 000 – resten lämnas åt framtida användning
REFRESH_S = 6 * 3600     # en dag som inte är färdig hämtas om högst så här ofta
DONE_AFTER_S = 2 * 86400  # en dag äldre än så räknas som färdig (sparas för gott)


class GoalApiResults:
    def __init__(self, state_path: Path, api_key: str | None = None, opener=None):
        self.key = api_key if api_key is not None else os.environ.get("GOAL_API_KEY", "").strip()
        self.path = state_path
        self.open = opener or urllib.request.urlopen
        try:
            self.st = json.loads(state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            self.st = {}
        self.st.setdefault("dagar", {})       # dag -> {"ts": hämtad, "m": [[hemma, borta, avspark, h, b], …]}
        self.st.setdefault("anrop", {})       # UTC-datum -> antal anrop
        self.error = ""

    @property
    def enabled(self) -> bool:
        return bool(self.key)

    def _calls_today(self) -> int:
        return self.st["anrop"].get(time.strftime("%Y-%m-%d", time.gmtime()), 0)

    def _get(self, day: str, offset: int) -> dict | None:
        if self._calls_today() >= DAILY_CAP:
            self.error = f"dagstak {DAILY_CAP} anrop nått"
            return None
        today = time.strftime("%Y-%m-%d", time.gmtime())
        self.st["anrop"][today] = self._calls_today() + 1
        url = f"{URL}?from={day}&to={day}&limit=500&offset={offset}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.key}", "Accept": "application/json",
                                                   "User-Agent": "propsbot"})
        try:
            with self.open(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            self.error = f"HTTP {e.code}" + (" (fel nyckel?)" if e.code in (401, 403) else "")
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            self.error = f"{type(e).__name__}"
        return None

    def _day(self, day: str, now: float) -> list:
        cached = self.st["dagar"].get(day)
        day_ts = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
        if cached and (cached.get("klar") or now - cached["ts"] < REFRESH_S):
            return cached["m"]
        rows, offset = [], 0
        while True:
            d = self._get(day, offset)
            if d is None:
                return cached["m"] if cached else []
            for m in d.get("data", []) or []:
                ft_h, ft_a = m.get("homeTeamFtScore"), m.get("awayTeamFtScore")
                if m.get("matchStatus") not in ("FINISHED", "AFTER_ET", "AFTER_PEN") or ft_h in (None, "") or ft_a in (None, ""):
                    continue
                try:
                    ko = datetime.fromisoformat(m["kickoffUtc"].replace("Z", "+00:00")).timestamp()
                    rows.append([m["homeTeamName"], m["awayTeamName"], ko, int(ft_h), int(ft_a)])
                except (KeyError, TypeError, ValueError):
                    continue
            pg = d.get("pagination") or {}
            if not pg.get("hasMore") or offset > 5000:
                break
            offset += 500
        self.st["dagar"][day] = {"ts": now, "klar": now - day_ts > DONE_AFTER_S, "m": rows}
        return rows

    def final_score(self, home: str, away: str, start: float, now: float | None = None) -> tuple[int, int] | None:
        """(hemmamål, bortamål) efter ordinarie tid, eller None."""
        if not self.enabled:
            return None
        from ..results import espn_match
        now = now or time.time()
        for day in dict.fromkeys(datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d") for t in (start, start + 3 * 3600)):
            for h, a, ko, gh, ga in self._day(day, now):
                if espn_match(home, away, start, h, a, ko):
                    return gh, ga
        return None

    def save(self, now: float | None = None) -> None:
        now = now or time.time()
        self.st["dagar"] = {d: v for d, v in self.st["dagar"].items()
                            if now - datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() < 16 * 86400}
        self.st["anrop"] = dict(sorted(self.st["anrop"].items())[-10:])
        self.path.write_text(json.dumps(self.st, ensure_ascii=False), encoding="utf-8")
