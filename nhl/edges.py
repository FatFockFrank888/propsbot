"""Compare model probabilities with bookmaker prices and pick +EV bets."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, replace
from typing import Iterable

from .config import Settings
from .names import NameMatcher, normalize_book
from .odds import PropQuote
from .pricing import consensus, devig_two_way, expected_value, implied_prob, kelly_fraction
from .slate import Projection

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Evaluation:
    projection: Projection
    line: float
    side: str  # 'over' / 'under'
    book: str
    odds: float  # best decimal price at a bet book
    p_win: float
    p_push: float
    model_prob: float  # P(win | no push)
    market_prob: float | None  # de-vigged consensus P(side | no push)
    market_source: str  # 'reference', 'bet_books' or 'single'
    books_quoting: int
    edge: float  # model_prob - market_prob (or minus implied prob if no market)
    ev: float  # expected profit per 1 unit staked
    kelly: float  # full-Kelly fraction
    stake: float  # recommended stake in currency units
    is_pick: bool
    reject_reason: str


def _assign_quotes(
    projections: list[Projection], quotes: Iterable[PropQuote]
) -> tuple[dict[tuple[int, float], list[PropQuote]], list[PropQuote]]:
    by_game: dict[int, list[Projection]] = defaultdict(list)
    by_team: dict[str, list[Projection]] = defaultdict(list)
    for p in projections:
        by_game[p.game.game_id].append(p)
        by_team[p.skater.team].append(p)
    # Prefer active players when two roster entries share a name.
    ordered = sorted(projections, key=lambda p: not p.active)
    slate_matcher = NameMatcher((p.skater.name, p) for p in ordered)
    game_matchers = {gid: NameMatcher((p.skater.name, p) for p in ps) for gid, ps in by_game.items()}
    team_matchers = {t: NameMatcher((p.skater.name, p) for p in ps) for t, ps in by_team.items()}

    grouped: dict[tuple[int, float], list[PropQuote]] = defaultdict(list)
    unmatched: list[PropQuote] = []
    for q in quotes:
        if q.game_id is not None and q.game_id in game_matchers:
            proj = game_matchers[q.game_id].match(q.player)
        elif q.team and q.team in team_matchers:
            proj = team_matchers[q.team].match(q.player)
        else:
            proj = slate_matcher.match(q.player)
        if proj is None:
            unmatched.append(q)
            continue
        grouped[(proj.skater.player_id, q.line)].append(q)
    return grouped, unmatched


def evaluate(
    projections: list[Projection], quotes: Iterable[PropQuote], s: Settings
) -> tuple[list[Evaluation], list[PropQuote]]:
    bet_books = {normalize_book(b) for b in s.bet_books}
    proj_by_id = {p.skater.player_id: p for p in projections}
    grouped, unmatched = _assign_quotes(projections, quotes)

    results: list[Evaluation] = []
    for (player_id, line), qs in grouped.items():
        proj = proj_by_id[player_id]
        # One quote per book: last one wins (CSV entries override API for the same book).
        per_book: dict[str, PropQuote] = {}
        for q in sorted(qs, key=lambda q: q.source == "csv"):
            per_book[q.book] = q
        two_way = {b: q for b, q in per_book.items() if q.over and q.under}
        reference = [devig_two_way(q.over, q.under)[0] for b, q in two_way.items() if b not in bet_books]
        own = [devig_two_way(q.over, q.under)[0] for b, q in two_way.items() if b in bet_books]
        if reference:
            fair_over, source = consensus(reference), "reference"
        elif own:
            fair_over, source = consensus(own), "bet_books" if len(own) > 1 else "single"
        else:
            fair_over, source = None, "none"

        probs = proj.probs(line, s.dispersion)
        for side in ("over", "under"):
            offers = [(q.over if side == "over" else q.under, b) for b, q in per_book.items() if b in bet_books]
            offers = [(o, b) for o, b in offers if o]
            if not offers:
                continue
            odds, book = max(offers)
            p_win = probs.side(side)
            p_push = probs.push
            decisive = 1.0 - p_push
            model_prob = p_win / decisive if decisive > 0 else 0.0
            market_prob = None if fair_over is None else (fair_over if side == "over" else 1.0 - fair_over)
            edge = model_prob - (market_prob if market_prob is not None else implied_prob(odds))
            ev = expected_value(p_win, p_push, odds)
            kelly = kelly_fraction(p_win, p_push, odds)
            stake = min(kelly * s.kelly_fraction, s.max_stake_pct) * s.bankroll

            reason = ""
            if not proj.active:
                reason = "not in last lineup"
            elif proj.estimate.games_used < s.min_games:
                reason = f"only {proj.estimate.games_used} games"
            elif odds < s.min_odds or odds > s.max_odds:
                reason = "odds outside range"
            elif ev < s.min_ev:
                reason = "EV below threshold"
            elif edge < s.min_edge:
                reason = "edge below threshold"
            results.append(
                Evaluation(
                    projection=proj, line=line, side=side, book=book, odds=odds, p_win=p_win, p_push=p_push,
                    model_prob=model_prob, market_prob=market_prob, market_source=source,
                    books_quoting=len(per_book), edge=edge, ev=ev, kelly=kelly,
                    stake=round(stake, 0) if not reason else 0.0, is_pick=not reason, reject_reason=reason,
                )
            )

    # Never recommend both sides of the same player/line.
    best: dict[tuple[int, float], Evaluation] = {}
    for r in results:
        if r.is_pick:
            key = (r.projection.skater.player_id, r.line)
            if key not in best or r.ev > best[key].ev:
                best[key] = r
    keep = {id(r) for r in best.values()}
    final = [
        r if (not r.is_pick or id(r) in keep) else _demote(r, "other side better")
        for r in results
    ]
    final.sort(key=lambda r: (not r.is_pick, -r.ev))
    if unmatched:
        log.info("%d quote(s) could not be matched to a player on the slate", len(unmatched))
    return final, unmatched


def _demote(r: Evaluation, reason: str) -> Evaluation:
    return replace(r, is_pick=False, reject_reason=reason, stake=0.0)
