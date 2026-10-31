"""Hela kedjan för en match:
simulator -> modellens p -> marknadens p (Pinnacle + Kambi som en röst)
-> blandning -> nivåkalibrering -> beslut -> portföljtak -> logg.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from .blend import LevelCalibration, blend, model_weight
from .config import Config
from .decision import Candidate, Decision, apply_portfolio_limits, evaluate
from .kambi import master_prices
from .market import prop_market_prob
from .models import MatchContext, OddsQuote
from .simulator import MatchSimulator, SimResult
from .store import Store


@dataclass
class BookSetup:
    pinnacle: str = "pinnacle"
    kambi_group: frozenset[str] = frozenset({"unibet"})
    playable: frozenset[str] = frozenset({"unibet"})  # bolag ni har konto hos (licensierade)


@dataclass
class Row:
    decision: Decision
    p_model: float
    p_market: float | None
    w_model: float


def _minutes_to_kickoff(match: MatchContext, now: float) -> float:
    ko = datetime.fromisoformat(match.kickoff_utc.replace("Z", "+00:00"))
    if ko.tzinfo is None:
        ko = ko.replace(tzinfo=timezone.utc)
    return (ko.timestamp() - now) / 60.0


def evaluate_match(match: MatchContext, quotes: list[OddsQuote], books: BookSetup,
                   cfg: Config | None = None, calibration: LevelCalibration | None = None,
                   now: float | None = None, store: Store | None = None,
                   sim: SimResult | None = None) -> list[Row]:
    cfg = cfg or Config()
    now = now if now is not None else time.time()
    sim = sim or MatchSimulator(match, cfg).run()
    names = {p.player_id: p.name for p in match.home.players + match.away.players}
    quotes = [q for q in quotes if q.match_id == match.match_id and q.player_id in names]

    kambi_master = master_prices(quotes, set(books.kambi_group))
    by_line: dict[tuple, list[OddsQuote]] = defaultdict(list)
    for q in quotes:
        by_line[(q.player_id, q.market, q.line)].append(q)

    rows: list[Row] = []
    mtk = _minutes_to_kickoff(match, now)
    for (pid, market, line), qs in by_line.items():
        if sim.n_played(pid) < 200:
            continue  # för få simuleringar där spelaren spelar
        p_model = sim.prob_over(pid, market, line)
        pin_over = next((q.odds for q in qs if q.book == books.pinnacle and q.side == "over"), None)
        pin_under = next((q.odds for q in qs if q.book == books.pinnacle and q.side == "under"), None)
        k_over = kambi_master.get((match.match_id, pid, market, line, "over"))
        mv = prop_market_prob(market, cfg.market, pin_over, pin_under, k_over)
        w = model_weight(market, match.lineup_confirmed, mv.pinnacle_present, p_model,
                         mv.p_market if mv.p_market is not None else p_model, cfg.blend)
        p = blend(p_model, mv.p_market, w)
        if calibration:
            p = calibration.apply(market, p)

        playable = [q for q in qs if q.side == "over" and q.book in books.playable]
        if not playable:
            continue
        best = max(playable, key=lambda q: q.odds)
        cand = Candidate(match.match_id, pid, names[pid], market, line, p, best,
                         consensus_odds=k_over, now=now,
                         lineup_confirmed=match.lineup_confirmed, minutes_to_kickoff=mtk)
        rows.append(Row(evaluate(cand, cfg.decision), p_model, mv.p_market, w))

    apply_portfolio_limits([r.decision for r in rows], cfg.decision)

    if store:
        for r in rows:
            d = r.decision
            store.log_prediction(dict(
                ts=now, match_id=d.cand.match_id, player_id=d.cand.player_id,
                player_name=d.cand.player_name, market=d.cand.market, line=d.cand.line,
                p_model=r.p_model, p_market=r.p_market, p_final=d.cand.p, w_model=r.w_model,
                lineup_confirmed=int(match.lineup_confirmed), best_book=d.cand.best.book,
                best_odds=d.cand.best.odds, edge=d.cand.edge, play_from=d.play_from,
                playable=int(d.playable), shown=int(d.show), stake=d.stake,
                reasons="; ".join(d.reasons)))
    rows.sort(key=lambda r: -r.decision.cand.edge)
    return rows


MARKET_LABEL = {"shots": "Skott", "shots_on_target": "Skott på mål", "goal": "Mål", "assist": "Assist"}


def format_table(rows: list[Row], only_shown: bool = True) -> str:
    head = f"{'Spelare':<22}{'Marknad':<15}{'Linje':>6}{'p':>7}{'Bolag':>13}{'Odds':>7}" \
           f"{'Edge':>8}{'Spela från':>12}{'Insats':>8}  Status"
    out = [head, "-" * len(head)]
    for r in rows:
        d = r.decision
        if only_shown and not d.show:
            continue
        c = d.cand
        status = "SPELA" if d.playable else ("– " + "; ".join(d.reasons))
        out.append(f"{c.player_name:<22}{MARKET_LABEL.get(c.market, c.market):<15}"
                   f"{'+' + str(c.line):>6}{c.p:>7.1%}{c.best.book:>13}{c.best.odds:>7.2f}"
                   f"{c.edge:>8.1%}{d.play_from:>12.2f}{d.stake:>8.2%}  {status}")
    return "\n".join(out)
