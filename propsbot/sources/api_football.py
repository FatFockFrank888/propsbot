"""Femte källan för fotbollens slutresultat och matchstatus: API-Football (api-sports.io, nyckel API_FOOTBALL_KEY).

Varför: ESPN, FotMob, LiveScore och goal-api saknar bl.a. Hongkongs cuper (Sapling Cup) och japanska JFL, och
ingen av dem skiljer på ett pålitligt sätt "uppskjuten" från "hittas inte". API-Football har en bred ligakatalog
och en uttrycklig status per match (NS, 1H, HT, 2H, FT, AET, PEN, PST, CANC, ABD, AWD, WO …).

Ett anrop per dag räcker: GET /fixtures?date=YYYY-MM-DD ger ALLA matcher den dagen, i alla ligor, med status
och ställningen efter ordinarie tid (score.fulltime). Därför behövs ingen ligakatalog eller polling per liga –
bara matchningen på lagnamn + avsparkstid (espn_match, samma som övriga källor).

Försiktigt med kvoten (gratisnivån 100 anrop/dygn; ett tidigare konto stängdes av när källtestet gick för ofta):
  * dagar som är färdiga (äldre än DONE_AFTER_S) hämtas EN gång och sparas i läget (api_football_lage.json)
  * en dag som kan få fler resultat hämtas om högst var REFRESH_S
  * hårt tak DAILY_CAP anrop per UTC-dygn; används bara för spel som de andra källorna saknar
  * får vi ett kvot- eller planfel slutar vi anropa resten av dygnet
Rättning bara på entydig slutstatus (FT / AET / PEN med ifyllt fulltime-resultat). PST / CANC / ABD / AWD / WO
rapporteras som void-orsak; övrigt (NS, TBD, live) = inget besked.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://v3.football.api-sports.io/fixtures"
DAILY_CAP = 40            # av 100 på gratisnivån – marginal för källtest och manuella anrop
REFRESH_S = 6 * 3600
DONE_AFTER_S = 2 * 86400
KEEP_DAYS = 16
FINISHED = ("FT", "AET", "PEN")
VOID = {"PST": "uppskjuten", "CANC": "inställd", "ABD": "avbruten", "AWD": "inställd", "WO": "inställd"}


class ApiFootballResults:
    def __init__(self, state_path: Path, api_key: str | None = None, opener=None):
        self.key = api_key if api_key is not None else os.environ.get("API_FOOTBALL_KEY", "").strip()
        self.path = state_path
        self.open = opener or urllib.request.urlopen
        try:
            self.st = json.loads(state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            self.st = {}
        self.st.setdefault("dagar", {})   # dag -> {"ts", "klar", "m": [[hemma, borta, avspark, status, h, b, id], …]}
        self.st.setdefault("anrop", {})   # UTC-datum -> antal anrop
        self.st.setdefault("stopp", "")   # UTC-datum då kvot-/planfel kom (inga fler anrop det dygnet)
        self.error = ""

    @property
    def enabled(self) -> bool:
        return bool(self.key)

    def _today(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    def _calls_today(self) -> int:
        return self.st["anrop"].get(self._today(), 0)

    def _get(self, day: str) -> dict | None:
        if self.st.get("stopp") == self._today():
            self.error = "pausad resten av dygnet (kvot- eller planfel)"
            return None
        if self._calls_today() >= DAILY_CAP:
            self.error = f"dagstak {DAILY_CAP} anrop nått"
            return None
        self.st["anrop"][self._today()] = self._calls_today() + 1
        req = urllib.request.Request(f"{URL}?date={day}", headers={"x-apisports-key": self.key,
                                                                   "Accept": "application/json",
                                                                   "User-Agent": "propsbot"})
        try:
            with self.open(req, timeout=30) as r:
                d = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            self.error = f"HTTP {e.code}" + (" (fel nyckel?)" if e.code in (401, 403) else "")
            if e.code in (401, 403, 429):
                self.st["stopp"] = self._today()
            return None
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            self.error = type(e).__name__
            return None
        errs = d.get("errors")
        if errs:   # t.ex. {"requests": "You have reached the request limit…"} eller {"plan": "…season…"}
            self.error = "API-fel: " + "; ".join(f"{k}: {v}" for k, v in (errs.items() if isinstance(errs, dict) else
                                                                        enumerate(errs)))[:200]
            self.st["stopp"] = self._today()
            return None
        return d

    def _day(self, day: str, now: float) -> list:
        cached = self.st["dagar"].get(day)
        if cached and (cached.get("klar") or now - cached["ts"] < REFRESH_S):
            return cached["m"]
        d = self._get(day)
        if d is None:
            return cached["m"] if cached else []
        rows = []
        for m in d.get("response", []) or []:
            fx, tm = m.get("fixture") or {}, m.get("teams") or {}
            st = ((fx.get("status") or {}).get("short") or "").upper()
            ft = (m.get("score") or {}).get("fulltime") or {}
            try:
                rows.append([tm["home"]["name"], tm["away"]["name"], float(fx["timestamp"]), st,
                             ft.get("home"), ft.get("away"), fx.get("id")])
            except (KeyError, TypeError, ValueError):
                continue
        day_ts = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
        self.st["dagar"][day] = {"ts": now, "klar": now - day_ts > DONE_AFTER_S, "m": rows}
        return rows

    def _find(self, home: str, away: str, start: float, now: float | None) -> list | None:
        if not self.enabled:
            return None
        from ..results import espn_match
        now = now or time.time()
        for day in dict.fromkeys(datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
                                 for t in (start, start - 5 * 3600, start + 3 * 3600)):
            for row in self._day(day, now):
                if espn_match(home, away, start, row[0], row[1], row[2]):
                    return row
        return None

    def final_score(self, home: str, away: str, start: float, now: float | None = None) -> tuple[int, int] | None:
        """(hemmamål, bortamål) efter ordinarie tid, bara vid entydig slutstatus (FT/AET/PEN)."""
        row = self._find(home, away, start, now)
        if not row or row[3] not in FINISHED or row[4] is None or row[5] is None:
            return None
        try:
            return int(row[4]), int(row[5])
        except (TypeError, ValueError):
            return None

    def void_reason(self, home: str, away: str, start: float, now: float | None = None) -> str | None:
        row = self._find(home, away, start, now)
        return VOID.get(row[3]) if row else None

    def save(self, now: float | None = None) -> None:
        now = now or time.time()
        self.st["dagar"] = {d: v for d, v in self.st["dagar"].items()
                            if now - datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
                            < KEEP_DAYS * 86400}
        self.st["anrop"] = dict(sorted(self.st["anrop"].items())[-10:])
        self.path.write_text(json.dumps(self.st, ensure_ascii=False), encoding="utf-8")
