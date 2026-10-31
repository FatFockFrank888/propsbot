"""Kambi-bolagen: hitta vilka bolag som delar leverantör, räkna fram Kambis
huvudpris och mät hur snabbt varje bolag följer när priset rör sig.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

from .config import MarketConfig
from .models import OddsQuote

Key = tuple[str, str, str, float, str]  # match, player, market, line, side


def _key(q: OddsQuote) -> Key:
    return (q.match_id, q.player_id, q.market, q.line, q.side)


def group_books_by_provider(quotes: Iterable[OddsQuote], cfg: MarketConfig,
                            min_common: int = 30) -> list[set[str]]:
    """Gruppera bolag som har nästan identiska priser (samma leverantör).

    Två bolag kopplas ihop om de har minst min_common gemensamma linjer,
    korrelation i implied probability ≥ same_provider_corr och medelavvikelse
    ≤ same_provider_max_mad. Grupperna bildas med union-find.
    """
    latest: dict[str, dict[Key, float]] = defaultdict(dict)
    for q in sorted(quotes, key=lambda q: q.ts):
        latest[q.book][_key(q)] = 1.0 / q.odds
    books = sorted(latest)
    parent = {b: b for b in books}

    def find(b: str) -> str:
        while parent[b] != b:
            parent[b] = parent[parent[b]]
            b = parent[b]
        return b

    for i, a in enumerate(books):
        for b in books[i + 1:]:
            common = latest[a].keys() & latest[b].keys()
            if len(common) < min_common:
                continue
            x = np.array([latest[a][k] for k in common])
            y = np.array([latest[b][k] for k in common])
            if x.std() == 0 or y.std() == 0:
                continue
            corr = float(np.corrcoef(x, y)[0, 1])
            mad = float(np.abs(x - y).mean())
            if corr >= cfg.same_provider_corr and mad <= cfg.same_provider_max_mad:
                parent[find(a)] = find(b)

    groups: dict[str, set[str]] = defaultdict(set)
    for b in books:
        groups[find(b)].add(b)
    return sorted(groups.values(), key=lambda g: (-len(g), sorted(g)))


def master_prices(quotes: Iterable[OddsQuote], group: set[str],
                  max_age_s: float | None = None, now: float | None = None
                  ) -> dict[Key, float]:
    """Kambis huvudpris = medianen av gruppens senaste odds per linje."""
    latest: dict[Key, dict[str, OddsQuote]] = defaultdict(dict)
    for q in quotes:
        if q.book not in group:
            continue
        if max_age_s is not None and now is not None and now - q.ts > max_age_s:
            continue
        cur = latest[_key(q)].get(q.book)
        if cur is None or q.ts > cur.ts:
            latest[_key(q)][q.book] = q
    return {k: statistics.median(q.odds for q in v.values()) for k, v in latest.items()}


@dataclass
class LagStats:
    book: str
    n_moves: int = 0
    lags_s: list[float] = field(default_factory=list)
    n_never_followed: int = 0

    @property
    def median_lag_s(self) -> float | None:
        return statistics.median(self.lags_s) if self.lags_s else None


def measure_lag(snapshots: list[tuple[float, list[OddsQuote]]], group: set[str],
                move_threshold: float = 0.03, tol: float = 0.01) -> dict[str, LagStats]:
    """Mät eftersläpning per bolag.

    snapshots = [(ts, quotes_vid_ts), ...] i tidsordning. När Kambis huvudpris
    (i implied prob) flyttar sig mer än move_threshold räknas hur länge varje
    bolag ligger kvar på det gamla priset (inom tol från nya priset = följt).
    """
    stats = {b: LagStats(b) for b in group}
    prev_master: dict[Key, float] = {}
    pending: dict[tuple[str, Key], tuple[float, float]] = {}  # (book,key) -> (ts_move, new_p)
    for ts, quotes in snapshots:
        master = master_prices(quotes, group)
        book_p = {(q.book, _key(q)): 1.0 / q.odds for q in quotes if q.book in group}
        for k, mo in master.items():
            p_new = 1.0 / mo
            if k in prev_master and abs(p_new - 1.0 / prev_master[k]) > move_threshold:
                for b in group:
                    if (b, k) in pending:
                        stats[b].n_never_followed += 1
                    pending[(b, k)] = (ts, p_new)
                    stats[b].n_moves += 1
        for (b, k), (ts_move, p_new) in list(pending.items()):
            p_b = book_p.get((b, k))
            if p_b is not None and abs(p_b - p_new) <= tol:
                stats[b].lags_s.append(ts - ts_move)
                del pending[(b, k)]
        prev_master.update(master)
    for (b, _k) in pending:
        stats[b].n_never_followed += 1
    return stats


def stale_candidates(quotes: list[OddsQuote], group: set[str], min_gap: float = 0.03
                     ) -> list[tuple[OddsQuote, float]]:
    """Bolag vars over-odds är klart högre än Kambis huvudpris just nu.

    Returnerar (quote, master_odds). Själva spelbeslutet tas mot den blandade
    sannolikheten i decision.py; detta är bara en signal.
    """
    master = master_prices(quotes, group)
    out = []
    for q in quotes:
        if q.book not in group or q.side != "over":
            continue
        mo = master.get(_key(q))
        if mo and (1.0 / mo - 1.0 / q.odds) > min_gap:
            out.append((q, mo))
    return out
