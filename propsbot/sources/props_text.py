"""Tolka marknads- och spelarnamn från olika källor till vårt format."""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from .the_odds_api import normalize_name


EXCLUDE_WORDS = ("first", "last", "team", "header", "outside", "inside", "hat", "brace",
                 "half", "minute", "card", "foul", "tackle", "save", "pass", "offside",
                 "corner", "combined", "both", "and ", "headed", "penalt", "own goal", "exactly", " or ")


def market_from_label(label: str) -> tuple[str, float | None] | None:
    """'Player's shots on target' -> ('shots_on_target', None)
    'To have 2+ shots' -> ('shots', 1.5). None för marknader vi inte använder
    (första/sista målskytt, halvlek, nick, utanför boxen, kort, kombinationer m.m.)."""
    s = label.lower()
    if any(w in s for w in EXCLUDE_WORDS):
        return None
    line = None
    m = re.search(r"(\d+)\s*\+", s) or re.search(r"(\d+) or more", s)
    if m:
        line = int(m.group(1)) - 0.5
    if "on target" in s:
        return "shots_on_target", line
    if "shot" in s:
        return "shots", line
    if "assist" in s:
        return "assist", line
    if "score" in s or "goal" in s:
        return "goal", line if line is not None else 0.5
    return None


def person_name(raw: str) -> str:
    """'Saka, Bukayo' -> 'Bukayo Saka'. Tar bort tillägg i parentes."""
    raw = re.sub(r"\(.*?\)", "", raw).strip()
    if raw.count(",") == 1:
        last, first = [x.strip() for x in raw.split(",")]
        raw = f"{first} {last}"
    return " ".join(raw.split())


def name_key(name: str) -> str:
    return normalize_name(person_name(name))


def same_person(a: str, b: str) -> bool:
    """Robust jämförelse: exakt, efternamn + förnamnsinitial, eller hög likhet."""
    ka, kb = name_key(a), name_key(b)
    if ka == kb:
        return True
    ta, tb = ka.split(), kb.split()
    if ta and tb and ta[-1] == tb[-1] and ta[0][:1] == tb[0][:1]:
        return True
    return SequenceMatcher(None, ka, kb).ratio() >= 0.88


def team_key(name: str) -> str:
    s = normalize_name(name)
    for w in ("fc", "cf", "afc", "sc", "ac", "ssc", "as", "tsg", "vfb", "vfl", "rb", "bk", "if",
              "ff", "fk", "sk", "the", "club", "calcio", "1899", "04", "05"):
        s = re.sub(rf"\b{w}\b", " ", s)
    return " ".join(s.split())


def same_match(home_a: str, away_a: str, start_a: float, home_b: str, away_b: str,
               start_b: float, max_dt_s: float = 3 * 3600) -> bool:
    if abs(start_a - start_b) > max_dt_s:
        return False
    r1 = SequenceMatcher(None, team_key(home_a), team_key(home_b)).ratio()
    r2 = SequenceMatcher(None, team_key(away_a), team_key(away_b)).ratio()
    return min(r1, r2) >= 0.6 and (r1 + r2) / 2 >= 0.72
