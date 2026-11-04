"""Kambi's public offering feed (the JSON Unibet, ATG, Svenska Spel, Expekt, BetMGM SE ... use).

No key, no credits. Unofficial: the format can change, so parsing is defensive and
raw responses can be saved to data/diagnos/ for inspection.

Odds and lines are given in thousandths (1850 = 1.85, 2500 = 2.5).
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..http import HttpError, JsonClient
from ..market import Quote

log = logging.getLogger(__name__)

BASES = (
    "https://eu-offering-api.kambicdn.com/offering/v2018",
    "https://eu-offering.kambicdn.org/offering/v2018",
)
LIST_PATH = "listView/ice_hockey/nhl/all/all/matches.json"

_AT_LEAST = re.compile(r"(?:at least|or more)\s*(\d+)|(\d+)\s*\+", re.IGNORECASE)


@dataclass(frozen=True)
class KambiEvent:
    event_id: int
    home: str
    away: str
    start: datetime
    state: str


def is_sog_label(label: str) -> bool:
    """True for player shots-on-goal criteria ('Player's shots on goal', 'Shots on Goal - Including Overtime' ...)."""
    low = label.lower()
    if "shot" not in low:
        return False
    if any(bad in low for bad in ("blocked", "against", "attempt", "missed", "save", "first shot", "period")):
        return False
    return True


def person_name(raw: str) -> str:
    """'Thompson, Tage' -> 'Tage Thompson'."""
    raw = raw.strip()
    if "," in raw:
        last, _, first = raw.partition(",")
        return f"{first.strip()} {last.strip()}".strip()
    return raw


def _threshold_line(text: str) -> float | None:
    m = _AT_LEAST.search(text)
    if not m:
        return None
    n = int(m.group(1) or m.group(2))
    return n - 0.5


def parse_sog_betoffers(raw: dict, book: str, playable: bool, now: float | None = None) -> tuple[list[Quote], list[str]]:
    """Return (quotes, shot-related criterion labels seen)."""
    now = now if now is not None else time.time()
    pairs: dict[tuple[str, float], dict[str, float]] = {}
    labels: list[str] = []
    for bo in raw.get("betOffers", []) or []:
        crit = bo.get("criterion", {}) or {}
        label = crit.get("englishLabel") or crit.get("label") or ""
        if "shot" in label.lower():
            labels.append(label)
        if not is_sog_label(label):
            continue
        for o in bo.get("outcomes", []) or []:
            if o.get("status", "OPEN") != "OPEN" or not o.get("odds"):
                continue
            odds = o["odds"] / 1000.0
            if odds <= 1.0:
                continue
            player = o.get("participant") or ""
            if not player:
                continue  # team / match totals have no participant
            olabel = (o.get("englishLabel") or o.get("label") or "").strip().lower()
            otype = (o.get("type") or "").upper()
            if otype == "OT_UNDER" or olabel in ("under", "no"):
                side = "under"
            elif otype == "OT_OVER" or olabel in ("over", "yes"):
                side = "over"
            else:
                continue
            if o.get("line") is not None:
                line = o["line"] / 1000.0
            else:
                line = _threshold_line(label) or _threshold_line(olabel)
                if line is None:
                    continue
            pairs.setdefault((person_name(player), line), {})[side] = odds
    quotes = [
        Quote(source=book, group="kambi", player=p, line=ln, over=s.get("over"), under=s.get("under"), ts=now, playable=playable)
        for (p, ln), s in pairs.items()
    ]
    return quotes, labels


class KambiClient:
    def __init__(self, client: JsonClient, market: str = "SE", diagnose_dir: Path | None = None) -> None:
        self.client = client
        self.market = market
        self.diagnose_dir = diagnose_dir
        self._base_for: dict[str, str] = {}
        self.last_raw: dict[tuple[str, int], dict] = {}

    def _get(self, offering: str, path: str, params: dict | None = None) -> dict | None:
        query = {"lang": "en_GB", "market": self.market, **(params or {})}
        bases = [self._base_for[offering]] if offering in self._base_for else list(BASES)
        last: HttpError | None = None
        for base in bases:
            try:
                data, _ = self.client.get(f"{base}/{offering}/{path}", query, ttl=0)
            except HttpError as exc:
                if exc.status == 404:
                    return None
                last = exc
                continue
            self._base_for[offering] = base
            return data
        if last:
            raise last
        return None

    def events(self, offering: str) -> list[KambiEvent]:
        raw = self._get(offering, LIST_PATH, {"useCombined": "true"}) or {}
        events = []
        for item in raw.get("events", []) or []:
            ev = item.get("event", item)
            try:
                start = datetime.fromisoformat(ev["start"].replace("Z", "+00:00")).astimezone(timezone.utc)
            except (KeyError, ValueError):
                continue
            home = ev.get("homeName") or ev.get("name", " - ").split(" - ")[0]
            away = ev.get("awayName") or ev.get("name", " - ").split(" - ")[-1]
            events.append(KambiEvent(int(ev["id"]), home, away, start, str(ev.get("state", ""))))
        return events

    def sog_quotes(self, offering: str, book: str, event_id: int, playable: bool) -> tuple[list[Quote], list[str]]:
        raw = self._get(offering, f"betoffer/event/{event_id}.json", {"includeParticipants": "true"})
        if not raw:
            return [], []
        self.last_raw[(offering, int(event_id))] = raw   # reused by the NHL test markets (points/assists/goals)
        quotes, labels = parse_sog_betoffers(raw, book, playable)
        if self.diagnose_dir and (labels and not quotes):
            self._dump(f"kambi_{offering}_{event_id}.json", raw)
            log.warning("Kambi %s event %s has shot criteria %s but none parsed; raw saved", offering, event_id, labels[:3])
        return quotes, labels

    def raw_event(self, offering: str, event_id: int) -> dict | None:
        return self._get(offering, f"betoffer/event/{event_id}.json", {"includeParticipants": "true"})

    def _dump(self, name: str, raw: dict) -> None:
        assert self.diagnose_dir is not None
        self.diagnose_dir.mkdir(parents=True, exist_ok=True)
        (self.diagnose_dir / name).write_text(json.dumps(raw, indent=1, ensure_ascii=False), encoding="utf-8")
