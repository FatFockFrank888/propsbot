"""Player / team / bookmaker name normalisation and fuzzy-but-safe matching."""

from __future__ import annotations

import re
import unicodedata
from typing import Generic, Iterable, TypeVar

T = TypeVar("T")

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_name(name: str) -> str:
    """'J.T. Miller' -> 'jt miller', 'Stützle, Tim' -> 'tim stutzle', "Ryan O'Reilly" -> 'ryan oreilly'."""
    if name.count(",") == 1:
        last, first = (part.strip() for part in name.split(","))
        if first and first.lower().rstrip(".") not in _SUFFIXES:
            name = f"{first} {last}"
    text = strip_accents(name).lower().replace("'", "").replace("’", "")
    tokens = [t for t in re.sub(r"[^a-z]+", " ", text).split() if t not in _SUFFIXES]
    merged: list[str] = []
    prev_single = False
    for tok in tokens:
        # Join runs of single-letter initials so "j t miller" == "jt miller".
        if len(tok) == 1 and prev_single:
            merged[-1] += tok
        else:
            merged.append(tok)
        prev_single = len(tok) == 1
    return " ".join(merged)


def normalize_book(name: str) -> str:
    """'Svenska Spel' / 'svenskaspel_se' -> 'svenskaspel', 'Unibet (SE)' -> 'unibet'."""
    text = strip_accents(name).lower()
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"_(se|eu|uk|us|us2|au|fr|it|nl|fi)$", "", text.strip())
    text = re.sub(r"[^a-z0-9]+", "", text)
    aliases = {"oddset": "svenskaspel", "svenskaspeloddset": "svenskaspel", "atgse": "atg", "unibetse": "unibet"}
    return aliases.get(text, text)


class NameMatcher(Generic[T]):
    """Maps bookmaker player names to objects. Only returns unambiguous matches."""

    def __init__(self, items: Iterable[tuple[str, T]]) -> None:
        self._exact: dict[str, list[T]] = {}
        self._initial_last: dict[str, list[T]] = {}
        self._last: dict[str, list[T]] = {}
        for name, obj in items:
            norm = normalize_name(name)
            if not norm:
                continue
            tokens = norm.split()
            self._exact.setdefault(norm, []).append(obj)
            self._last.setdefault(tokens[-1], []).append(obj)
            if len(tokens) >= 2:
                self._initial_last.setdefault(f"{tokens[0][0]} {tokens[-1]}", []).append(obj)

    def match(self, name: str) -> T | None:
        norm = normalize_name(name)
        if not norm:
            return None
        tokens = norm.split()
        for table, key in (
            (self._exact, norm),
            (self._initial_last, f"{tokens[0][0]} {tokens[-1]}" if len(tokens) >= 2 else None),
            (self._last, tokens[-1]),
        ):
            if key is None:
                continue
            hits = table.get(key, [])
            if len(hits) == 1:
                return hits[0]
            if len(hits) > 1:
                return None  # ambiguous: refuse to guess
        return None
