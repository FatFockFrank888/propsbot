"""Bovada's public coupon feed: two-sided player shots-on-goal lines. Free, no key.

Used as an independent reference (never playable). Bovada posts NHL player SOG
props roughly a day ahead, so it gives a reference on every scan, including the
closing line used for CLV.
"""

from __future__ import annotations

import logging
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from ..http import HttpError, JsonClient
from ..market import Quote
from ..model import line_probs

log = logging.getLogger(__name__)

BASE = "https://www.bovada.lv/services/sports/event/coupon/events/A/description"
LIST = f"{BASE}/hockey/nhl"
PREFIX = "total shots on goal - "
LADDER_PREFIX = "shots on goal milestones - "
_RUNG = re.compile(r"^(\d+)\s*\+")
# Bovada answers '{}' to event requests that advertise gzip, so ask for plain JSON.
HEADERS = {"Accept-Encoding": "identity"}


@dataclass(frozen=True)
class BovadaEvent:
    event_id: str
    home: str
    away: str
    start: datetime
    link: str


class BovadaClient:
    def __init__(self, client: JsonClient, ttl: float = 120.0, alpha: float = 0.05) -> None:
        self.client = client
        self.ttl = ttl
        self.alpha = alpha

    def events(self) -> list[BovadaEvent]:
        data, _ = self.client.get(LIST, {"marketFilterId": "def", "preMatchOnly": "true", "lang": "en"},
                                  ttl=self.ttl, headers=HEADERS)
        return parse_events(data)

    def sog_quotes(self, link: str) -> list[Quote]:
        try:
            data, _ = self.client.get(f"{BASE}{link}", {"lang": "en"}, ttl=self.ttl, headers=HEADERS)
        except HttpError as exc:
            if exc.status == 404:
                return []
            raise
        return parse_sog(data, alpha=self.alpha)


def parse_events(data) -> list[BovadaEvent]:
    out = []
    for block in data or []:
        for ev in block.get("events", []) or []:
            if ev.get("live"):
                continue
            teams = {bool(c.get("home")): c.get("name", "") for c in ev.get("competitors", [])}
            if True not in teams or False not in teams or not ev.get("link"):
                continue
            try:
                start = datetime.fromtimestamp(int(ev["startTime"]) / 1000, tz=timezone.utc)
            except (KeyError, ValueError, TypeError):
                continue
            out.append(BovadaEvent(str(ev.get("id")), teams[True], teams[False], start, ev["link"]))
    return out


def fit_ladder(rungs: dict[int, float], alpha: float) -> tuple[float, float] | None:
    """Fit (mu, margin) of a negative binomial to a one-sided 'N+ shots' ladder.

    rungs: N -> decimal odds for 'N or more'. Model: implied_N = (1 + margin) * P(X >= N | mu).
    For a given mu the best log-margin is the mean log gap, so only mu needs a 1-D search.
    """
    # Long-shot rungs carry a heavier margin (favourite-longshot bias); only fit the bettable range.
    pts = [(n, 1.0 / o) for n, o in rungs.items() if 1.0 < o <= 6.0 and n >= 1]
    if len(pts) < 3:
        return None

    def sse(mu: float) -> tuple[float, float]:
        gaps = []
        for n, imp in pts:
            p = line_probs(n - 0.5, mu, alpha).over
            if p <= 1e-9:
                return float("inf"), 0.0
            gaps.append(math.log(imp) - math.log(p))
        lm = sum(gaps) / len(gaps)
        return sum((g - lm) ** 2 for g in gaps), lm

    lo, hi = 0.05, 12.0
    phi = (math.sqrt(5) - 1) / 2
    a, b = hi - phi * (hi - lo), lo + phi * (hi - lo)
    for _ in range(80):
        if sse(a)[0] < sse(b)[0]:
            hi = b
        else:
            lo = a
        a, b = hi - phi * (hi - lo), lo + phi * (hi - lo)
    mu = (lo + hi) / 2
    err, log_margin = sse(mu)
    margin = math.exp(log_margin) - 1.0
    if not (-0.02 <= margin <= 0.40) or err > 0.05 * len(pts):
        return None  # ladder inconsistent with a NB shape: don't trust it
    return mu, margin


def ladder_quotes(player: str, rungs: dict[int, float], alpha: float, now: float) -> list[Quote]:
    fit = fit_ladder(rungs, alpha)
    if fit is None:
        return []
    mu, _ = fit
    quotes = []
    for n in sorted(rungs):
        p = line_probs(n - 0.5, mu, alpha).over
        if 0.02 < p < 0.98:
            # Fair (margin-free) two-way prices implied by the fitted distribution.
            quotes.append(Quote("bovada:ladder", "bovada", player, n - 0.5, round(1 / p, 4), round(1 / (1 - p), 4), now))
    return quotes


def parse_sog(data, now: float | None = None, alpha: float = 0.05) -> list[Quote]:
    now = now if now is not None else time.time()
    pairs: dict[tuple[str, float], dict[str, float]] = {}
    ladders: dict[str, dict[int, float]] = {}
    for block in data or []:
        for ev in block.get("events", []) or []:
            for group in ev.get("displayGroups", []) or []:
                for m in group.get("markets", []) or []:
                    desc = (m.get("descriptionKey") or m.get("description") or "")
                    if m.get("status", "O") != "O":
                        continue
                    period = m.get("period") or {}
                    if period and not period.get("main", True):
                        continue
                    if desc.lower().startswith(LADDER_PREFIX):
                        player = desc[len(LADDER_PREFIX):].split("(")[0].strip()
                        for o in m.get("outcomes", []) or []:
                            hit = _RUNG.match((o.get("description") or "").strip())
                            price = (o.get("price") or {}).get("decimal")
                            if hit and price and o.get("status", "O") == "O":
                                try:
                                    ladders.setdefault(player, {})[int(hit.group(1))] = float(price)
                                except ValueError:
                                    continue
                        continue
                    if not desc.lower().startswith(PREFIX):
                        continue
                    player = desc[len(PREFIX):].split("(")[0].strip()
                    for o in m.get("outcomes", []) or []:
                        if o.get("status", "O") != "O":
                            continue
                        side = {"O": "over", "U": "under"}.get(o.get("type")) or (o.get("description") or "").lower()
                        price = o.get("price") or {}
                        if side not in ("over", "under") or price.get("handicap") is None:
                            continue
                        try:
                            dec = float(price["decimal"])
                            line = float(price["handicap"])
                        except (KeyError, ValueError, TypeError):
                            continue
                        if dec > 1.0:
                            pairs.setdefault((player, line), {})[side] = round(dec, 4)
    quotes = [
        Quote(source="bovada", group="bovada", player=p, line=ln, over=s.get("over"), under=s.get("under"), ts=now)
        for (p, ln), s in pairs.items()
    ]
    for player, rungs in ladders.items():
        quotes += ladder_quotes(player, rungs, alpha, now)
    return quotes
