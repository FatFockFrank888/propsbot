"""F1 (docs/PLAN_FOOTBALL_PROPS.md): speltid och elvagrind för fotbollens spelarprops.

Minuter ur ESPN:s matchsammanfattning: startspelare = bytesminut eller 90, inhoppare = 90 − inhoppsminut
(minst 1), ej spelat = 0. Tillägg ("90'+3'") räknas som 90. Rött kort syns inte i ESPN:s bytesrader
och ger 90 (liten överskattning, sällsynt).

Förväntade minuter givet start: avtagande vikt per MATCH (halveringstid i matcher), krympt mot en prior
(standard 80 min ≈ toppligornas snitt för startande utespelare) värd prior_n matcher.
"""
from __future__ import annotations

import math
import re
from enum import Enum

MATCH_LEN = 90.0
START_PRIOR = 80.0
SUB_PRIOR = 20.0


class Status(str, Enum):
    CONFIRMED_XI = "CONFIRMED_XI"
    BENCH = "BENCH"
    DOUBTFUL = "DOUBTFUL"
    UNKNOWN = "UNKNOWN"


def clock_minute(text: str | None) -> int | None:
    m = re.match(r"^\s*(\d+)'(?:\s*\+\s*\d+')?\s*$", text or "")
    return int(m.group(1)) if m else None


def minutes_from_espn(entry: dict, match_len: float = MATCH_LEN) -> float | None:
    """Minuter för en rad i ESPN:s roster. None om det inte går att avgöra (otolkbar bytesklocka)."""
    started = bool(entry.get("starter"))
    sub_min = None
    for pl in entry.get("plays") or []:
        if pl.get("substitution"):
            sub_min = clock_minute((pl.get("clock") or {}).get("displayValue"))
            if sub_min is None:
                return None
    if started:
        if entry.get("subbedOut"):
            return float(min(sub_min, match_len)) if sub_min is not None else None
        return match_len
    if entry.get("subbedIn"):
        if sub_min is None:
            return None
        return max(1.0, match_len - min(sub_min, match_len))
    return 0.0


def status(starts: bool | None, injury: str | None = None) -> Status:
    """starts: True/False från bekräftad elva, None = okänd. injury: 'doubtful'/'out'/… från nyheter."""
    if injury and injury.lower() in ("out", "doubtful", "injured", "suspended"):
        return Status.DOUBTFUL
    if starts is True:
        return Status.CONFIRMED_XI
    if starts is False:
        return Status.BENCH
    return Status.UNKNOWN


def expected_minutes(history: list[tuple[bool, float]], st: Status = Status.CONFIRMED_XI,
                     half_life_matches: float = 13.0, prior_start: float = START_PRIOR,
                     prior_sub: float = SUB_PRIOR, prior_n: float = 3.0) -> float:
    """history: [(startade, minuter)], nyaste först. E[min | start] (eller | inhopp om BENCH)."""
    if st in (Status.DOUBTFUL, Status.UNKNOWN):
        return 0.0
    want_start = st is Status.CONFIRMED_XI
    prior = prior_start if want_start else prior_sub
    num = den = 0.0
    k = 0
    for started, mins in history:
        if mins is None or (isinstance(mins, float) and math.isnan(mins)):
            continue
        if bool(started) == want_start and mins > 0:
            w = 0.5 ** (k / half_life_matches)
            num += w * mins
            den += w
        k += 1
    e = (num + prior_n * prior) / (den + prior_n)
    return float(min(max(e, 0.0), 95.0))


def gate(st: Status) -> tuple[bool, float, float, str]:
    """(spelbar, extra EV-krav, Kelly-multiplikator, orsak). Bara bekräftad startspelare får spelas."""
    if st is Status.CONFIRMED_XI:
        return True, 0.0, 1.0, ""
    if st is Status.BENCH:
        return False, 0.0, 0.0, "inte i startelvan"
    if st is Status.DOUBTFUL:
        return False, 0.0, 0.0, "tveksam/skadad"
    return False, 0.025, 0.5, "startelvan okänd (PRE_LINEUP, bara logg)"
