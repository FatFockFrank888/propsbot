"""Sjätte källan för fotbollens slutresultat och matchstatus: SportScore (sportscore.com, nyckel SPORTSCORE_API_KEY).

Data från TheSports – djup täckning även i Asien och lägre divisioner (prövat 21/11: Hongkongs ligacup och
First/Second Division, japanska JFL och regionligor, engelska Conference North). Villkor: gratisnivån kräver
att "Powered by SportScore" syns där datan används – länken finns i webbsidans sidfot och i arkets översikt.

  GET https://sportscore.com/api/v1/fixtures/?sport=football&date=YYYY-MM-DD&limit=200   (header X-API-Key)
  GET …&team=<lag-slug>                                                                 (bara det lagets matcher)

Svaret har högst 200 matcher per dag (från 00:00 UTC, ingen sidindelning). Därför: hela dagen hämtas en gång
(täcker Asiens tidiga avsparkar), och matcher som inte finns där slås upp per lag med team=<slug>.
Fält per match: home, away, home_score, away_score, status (finished/upcoming/…), status_text
(Finished, Delayed, …), time (ISO, UTC), competition.

Rättning bara vid status "finished" med status_text "Finished" och ifyllda mål. Uppskjutna matcher står kvar
som "upcoming" med status_text "Delayed" (South Shields 17/11 var fortfarande "Delayed" 21/11) – det,
och Postponed/Cancelled/Abandoned m.fl., ger void-orsak (sides.py kräver dessutom 48 h efter avspark).

Försiktigt med kvoten (~1 000 anrop/dygn och IP enligt dokumentationen): färdiga dagar och lag-uppslag sparas
i läget (sportscore_lage.json), hårt tak DAILY_CAP, och 401/403/429 pausar resten av dygnet.
"""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://sportscore.com/api/v1/fixtures/"
ATTRIBUTION = '<a href="https://sportscore.com/" rel="dofollow">Powered by SportScore</a>'
DAILY_CAP = 300
REFRESH_S = 6 * 3600
DONE_AFTER_S = 2 * 86400
KEEP_DAYS = 16
VOID = {"DELAYED": "uppskjuten", "POSTPONED": "uppskjuten", "CANCELLED": "inställd", "CANCELED": "inställd",
        "ABANDONED": "avbruten", "INTERRUPTED": "avbruten", "SUSPENDED": "avbruten", "AWARDED": "inställd"}
_AFFIX = {"fc", "afc", "sc", "cf", "ac", "fk", "sk", "cd", "sa", "ud", "club", "the", "w", "women"}


def slugs(name: str) -> list[str]:
    """Troliga lag-slugs: "South Shields FC" -> ["south-shields-fc", "south-shields"]."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    words = [w for w in re.split(r"[^a-z0-9]+", s) if w]
    out = ["-".join(words)]
    core = [w for w in words if w not in _AFFIX]
    if core and core != words:
        out.append("-".join(core))
    return [x for x in dict.fromkeys(out) if x]


class SportScoreResults:
    def __init__(self, state_path: Path, api_key: str | None = None, opener=None):
        self.key = api_key if api_key is not None else os.environ.get("SPORTSCORE_API_KEY", "").strip()
        self.path = state_path
        self.open = opener or urllib.request.urlopen
        try:
            self.st = json.loads(state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            self.st = {}
        self.st.setdefault("dagar", {})   # "dag" eller "dag|slug" -> {"ts", "klar", "m": [[hemma, borta, avspark, status, text, h, b]]}
        self.st.setdefault("anrop", {})
        self.st.setdefault("stopp", "")
        self.error = ""

    @property
    def enabled(self) -> bool:
        return bool(self.key)

    def _today(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    def calls_today(self) -> int:
        return self.st["anrop"].get(self._today(), 0)

    def _get(self, query: str) -> dict | None:
        if self.st.get("stopp") == self._today():
            self.error = "pausad resten av dygnet (nyckel- eller kvotfel)"
            return None
        if self.calls_today() >= DAILY_CAP:
            self.error = f"dagstak {DAILY_CAP} anrop nått"
            return None
        self.st["anrop"][self._today()] = self.calls_today() + 1
        req = urllib.request.Request(f"{URL}?sport=football&{query}",
                                     headers={"X-API-Key": self.key, "Accept": "application/json",
                                              "User-Agent": "propsbot (+https://fatfockfrank888.github.io/propsbot/)"})
        try:
            with self.open(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            self.error = f"HTTP {e.code}" + (" (fel nyckel?)" if e.code in (401, 403) else "")
            if e.code in (401, 403, 429):
                self.st["stopp"] = self._today()
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            self.error = type(e).__name__
        return None

    def _list(self, day: str, slug: str | None, now: float) -> list:
        key = day if slug is None else f"{day}|{slug}"
        cached = self.st["dagar"].get(key)
        if cached and (cached.get("klar") or now - cached["ts"] < REFRESH_S):
            return cached["m"]
        d = self._get(f"date={day}&limit=200" + (f"&team={slug}" if slug else ""))
        if d is None:
            return cached["m"] if cached else []
        rows = []
        for m in d.get("matches", []) or []:
            try:
                ko = datetime.fromisoformat(str(m["time"]).replace("Z", "+00:00")).timestamp()
                rows.append([m["home"], m["away"], ko, str(m.get("status") or "").lower(),
                             str(m.get("status_text") or ""), m.get("home_score"), m.get("away_score")])
            except (KeyError, TypeError, ValueError):
                continue
        day_ts = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
        self.st["dagar"][key] = {"ts": now, "klar": now - day_ts > DONE_AFTER_S, "m": rows}
        return rows

    def _find(self, home: str, away: str, start: float, now: float | None) -> list | None:
        if not self.enabled:
            return None
        from ..results import espn_match
        now = now or time.time()
        day = datetime.fromtimestamp(start, timezone.utc).strftime("%Y-%m-%d")
        for slug in [None] + slugs(home) + slugs(away):   # hela dagen först, sedan per lag
            for row in self._list(day, slug, now):
                if espn_match(home, away, start, row[0], row[1], row[2]):
                    return row
            if self.error.startswith(("pausad", "dagstak")):
                break
        return None

    def final_score(self, home: str, away: str, start: float, now: float | None = None) -> tuple[int, int] | None:
        """(hemmamål, bortamål) bara vid status finished / "Finished" med ifyllda mål."""
        row = self._find(home, away, start, now)
        if not row or row[3] != "finished" or row[4].strip().lower() != "finished":
            return None
        try:
            return int(row[5]), int(row[6])
        except (TypeError, ValueError):
            return None

    def void_reason(self, home: str, away: str, start: float, now: float | None = None) -> str | None:
        row = self._find(home, away, start, now)
        return VOID.get(row[4].strip().upper()) if row else None

    def save(self, now: float | None = None) -> None:
        now = now or time.time()
        self.st["dagar"] = {k: v for k, v in self.st["dagar"].items()
                            if now - datetime.strptime(k[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
                            < KEEP_DAYS * 86400}
        self.st["anrop"] = dict(sorted(self.st["anrop"].items())[-10:])
        self.path.write_text(json.dumps(self.st, ensure_ascii=False), encoding="utf-8")
