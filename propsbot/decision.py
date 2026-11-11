"""Beslutsregler: edge, 'spela från', filter, insats och korrelationstak."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .config import MARKET_FAMILY, DecisionConfig
from .models import OddsQuote


@dataclass
class Candidate:
    match_id: str
    player_id: str
    player_name: str
    market: str
    line: float
    p: float                       # slutlig sannolikhet (blandad + kalibrerad)
    best: OddsQuote                # bästa spelbara pris
    consensus_odds: float | None   # Kambis huvudpris eller konsensus
    now: float
    lineup_confirmed: bool
    minutes_to_kickoff: float
    notes: list[str] = field(default_factory=list)

    @property
    def edge(self) -> float:
        return self.p * self.best.odds - 1.0


def play_from_odds(p: float, min_edge: float, min_odds: float) -> float:
    """Lägsta odds som räcker: max(min_odds, (1 + edge) / p), avrundat UPPÅT till två decimaler
    (vanlig avrundning kunde visa ett odds strax under den verkliga tröskeln)."""
    import math
    return max(min_odds, math.ceil((1.0 + min_edge) / p * 100 - 1e-9) / 100)


def kelly_stake(p: float, odds: float, fraction: float, cap: float) -> float:
    b = odds - 1.0
    f = (p * b - (1 - p)) / b if b > 0 else 0.0
    return max(0.0, min(cap, f * fraction))


@dataclass
class Decision:
    cand: Candidate
    playable: bool
    show: bool
    play_from: float
    stake: float
    reasons: list[str]


def evaluate(c: Candidate, cfg: DecisionConfig) -> Decision:
    min_edge = cfg.min_edge_by_market.get(c.market, cfg.min_edge)
    pf = play_from_odds(c.p, min_edge, cfg.min_odds_play)
    reasons: list[str] = []
    ok = True
    if c.edge < min_edge:
        ok = False
        reasons.append(f"edge {c.edge:.1%} < {min_edge:.0%}")
    if c.best.odds < cfg.min_odds_play:
        ok = False
        reasons.append(f"odds {c.best.odds:.2f} < {cfg.min_odds_play:.2f}")
    if c.best.odds > cfg.max_odds_play:
        ok = False
        reasons.append(f"odds {c.best.odds:.2f} > {cfg.max_odds_play:.2f}")
    age = c.now - c.best.ts
    if age > cfg.max_odds_age_s:
        ok = False
        reasons.append(f"oddset är {age:.0f} s gammalt")
    if c.consensus_odds:
        dev = 1.0 / c.consensus_odds - 1.0 / c.best.odds
        if dev > cfg.max_dev_from_consensus:
            ok = False
            reasons.append(f"avviker {dev:.0%} från konsensus – kontrollera manuellt")
    if c.minutes_to_kickoff <= 0:
        ok = False
        reasons.append("matchen har startat – inga spel under match")
    if not c.lineup_confirmed and c.minutes_to_kickoff < cfg.lineup_required_minutes:
        ok = False
        reasons.append("startelvan okänd nära avspark")
    show = cfg.min_odds_show <= c.best.odds <= cfg.max_odds_play
    stake = kelly_stake(c.p, c.best.odds, cfg.kelly_fraction, cfg.max_stake_per_bet) if ok else 0.0
    return Decision(c, ok, show, pf, stake, reasons)


def apply_portfolio_limits(decisions: list[Decision], cfg: DecisionConfig) -> list[Decision]:
    """Max ett ben per spelare och marknadsfamilj (skott + skott på mål = samma),
    störst edge vinner. Tak för total insats per match (skalas ned proportionellt)."""
    best: dict[tuple[str, str, str], Decision] = {}
    for d in decisions:
        if not d.playable:
            continue
        key = (d.cand.match_id, d.cand.player_id, MARKET_FAMILY.get(d.cand.market, d.cand.market))
        if key not in best or d.cand.edge > best[key].cand.edge:
            best[key] = d
    kept = set(id(d) for d in best.values())
    for d in decisions:
        if d.playable and id(d) not in kept:
            d.playable = False
            d.stake = 0.0
            d.reasons.append("annat ben för samma spelare har större edge")
    per_match: dict[str, list[Decision]] = defaultdict(list)
    for d in decisions:
        if d.playable:
            per_match[d.cand.match_id].append(d)
    for ds in per_match.values():
        tot = sum(d.stake for d in ds)
        if tot > cfg.max_stake_per_match:
            f = cfg.max_stake_per_match / tot
            for d in ds:
                d.stake *= f
    return decisions
